"""Activity business service.

Transaction Management Architecture:
- Service layer contains business logic only (no transaction management)
- API layer manages transaction boundaries via get_async_db dependency
- Transaction commits automatically on success, rolls back on exception
- CRUD layer only flushes (session.flush()), never commits

Pattern:
- API layer: Transaction boundary (auto-commit via dependency)
- Service layer: Business logic (no transaction management)
- CRUD layer: Data access (flush only, no commits)

This pattern aligns transaction boundaries with HTTP request boundaries,
making it simple and straightforward for typical REST APIs.

Exception Handling:
- Service layer catches database exceptions and converts to domain exceptions
- DuplicateResourceError for unique constraint violations (HTTP 409)
- BusinessLogicError for other database constraint violations (HTTP 422)
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import activity as activity_crud
from app.crud import area as area_crud
from app.crud import platform as platform_crud
from app.models.activity import Activity


async def validate_activity(
    session: AsyncSession, activity: dict, activity_index: int
) -> list[dict]:
    """
    Validate a single activity (business logic validation only).

    Phase 1 validation: Check that referenced entities exist.
    Does NOT attempt to save to database.
    Resolves functional area_id (UUID) to technical ID for later use.

    Args:
        session: Async database session
        activity: Activity dictionary (validated by Pydantic)
        activity_index: Index of activity in original request (0-based)

    Returns:
        List of error dictionaries (empty if valid). Each error has:
        - loc: ["activities", index, field_name]
        - msg: Error message
        - type: Error type ("business_logic_error")
    """
    errors = []

    # Validate Area exists by functional ID (UUID) and resolve to technical ID
    area_id_uuid = activity["area_id"]  # Functional ID (UUID string)
    area = await area_crud.get_by_area_id(session, area_id_uuid)
    if area is None:
        errors.append(
            {
                "loc": ["activities", activity_index, "areaId"],
                "msg": f"Area with areaId '{area_id_uuid}' not found",
                "type": "business_logic_error",
            }
        )
    else:
        # Store resolved technical ID for Phase 2 processing
        activity["_area_technical_id"] = area.id  # Integer FK

    return errors


async def process_single_activity(session: AsyncSession, activity: dict) -> Activity:
    """
    Process and save a single activity (assumes validation already passed).

    Called within a savepoint context. Raises exceptions on database errors.
    Uses resolved technical area_id from validation phase.

    Args:
        session: Async database session (within savepoint)
        activity: Activity dictionary (already validated, contains _area_technical_id)

    Returns:
        Created Activity object with generated ID

    Raises:
        IntegrityError: Database constraint violation
        Any other database error
    """
    # Get resolved technical area_id (set in validate_activity)
    area_technical_id = activity["_area_technical_id"]  # Integer FK

    # Look up or create Platform
    platform_id_str = activity["platform_id_str"]
    platform_name = activity["platform_name"]
    platform = await platform_crud.get_by_platform_id(session, platform_id_str)

    if platform is None:
        platform = await platform_crud.create(
            session=session,
            platform_id=platform_id_str,
            platform_name=platform_name,
        )

    # Save activity (CRUD only flushes)
    activity_obj = await activity_crud.create(
        session=session,
        activity_id=activity.get("activity_id"),
        activity_name=activity.get("activity_name"),
        url=activity["url"],
        address_street=activity["address_street"],
        address_number=activity["address_number"],
        address_letter=activity.get("address_letter"),
        address_addition=activity.get("address_addition"),
        address_postal_code=activity["address_postal_code"],
        address_city=activity["address_city"],
        registration_number=activity["registration_number"],
        area_id=area_technical_id,  # Use resolved technical ID
        number_of_guests=activity["number_of_guests"],
        country_of_guests=activity["country_of_guests"],
        temporal_start_date_time=activity["temporal_start_date_time"],
        temporal_end_date_time=activity["temporal_end_date_time"],
        platform_id=platform.id,
    )

    return activity_obj


async def process_activity_list(
    session: AsyncSession,
    activities: list[dict],
    pydantic_errors_by_index: dict[int, list[dict]] | None = None,
) -> dict:
    """
    Process and save a list of activities using two-phase approach with nested transactions.

    Phase 0: Collect Pydantic validation errors (from API layer)
    Phase 1: Validate all activities (business logic: entities exist)
    Phase 2: Process valid activities using savepoints (each activity independently)

    Transaction Management:
    - Transaction is managed by the API layer (manual commit required)
    - Service uses nested transactions (savepoints) for each activity
    - Each activity can succeed or fail independently
    - Overall transaction commits at API layer after all processing

    System Crash Behavior (Before API Commit):
    - Savepoints protect against individual activity failures during processing
    - Savepoints do NOT protect against system crashes before final commit
    - If system crashes after this function returns but before API commits:
      * ALL changes are lost (including activities that "succeeded" in savepoints)
      * PostgreSQL automatically rolls back uncommitted transactions on connection loss
      * Example: 7 activities, 5 processed (2 succeeded, 3 failed), crash → ALL 5 rolled back
    - This is PostgreSQL's ACID guarantee: uncommitted work is never persisted

    Args:
        session: Async database session (manual commit mode)
        activities: List of activity dictionaries (may include invalid ones)
        pydantic_errors_by_index: Dict mapping activity index to Pydantic validation errors

    Returns:
        Dictionary with processing results:
        {
            "total_processed": int,
            "succeeded": int,
            "failed": int,
            "successes": [
                {
                    "activity_index": int,
                    "activity_id": str,
                    "activity": dict
                }
            ],
            "failures": [
                {
                    "activity_index": int,
                    "activity": dict,
                    "errors": [{"loc": [...], "msg": str, "type": str}]
                }
            ]
        }
    """
    if pydantic_errors_by_index is None:
        pydantic_errors_by_index = {}

    total_processed = len(activities)
    succeeded = 0
    failed = 0
    successes = []
    failures = []

    # PHASE 0: Handle Pydantic validation failures
    # These activities failed schema validation and cannot be processed
    pydantic_failures = []
    for idx, errors in pydantic_errors_by_index.items():
        activity = activities[idx]
        pydantic_failures.append(
            {
                "activity_index": idx,
                "activity": activity,
                "errors": errors,
            }
        )

    # PHASE 1: Validate all activities (business logic validation)
    # Skip activities that already failed Pydantic validation
    # Collect all validation errors without stopping
    validation_failures = []
    valid_indices = []

    for idx, activity in enumerate(activities):
        # Skip if already failed Pydantic validation
        if idx in pydantic_errors_by_index:
            continue

        # Skip if marked as Pydantic validation failed
        if activity.get("_pydantic_validation_failed"):
            continue

        errors = await validate_activity(session, activity, idx)
        if errors:
            validation_failures.append(
                {
                    "activity_index": idx,
                    "activity": activity,
                    "errors": errors,
                }
            )
        else:
            valid_indices.append(idx)

    # PHASE 2: Process valid activities, typically using nested transactions (savepoints)
    # Each activity processes in its own savepoint
    # NOTE: Savepoints only protect against individual activity failures.
    # If system crashes before API commit, ALL savepoints are rolled back.
    for idx in valid_indices:
        activity = activities[idx]

        # Create savepoint for this activity
        savepoint = await session.begin_nested()

        try:
            # Process the activity
            activity_obj = await process_single_activity(session, activity)

            # Flush to detect database errors within savepoint
            await session.flush()

            # Success - track it
            successes.append(
                {
                    "activity_index": idx,
                    "activity_id": activity_obj.activity_id,
                    "activity": activity,
                }
            )
            succeeded += 1

        except IntegrityError as e:
            # Rollback this savepoint only
            await savepoint.rollback()

            # Classify error type
            error_message = str(e).lower()
            if "unique constraint" in error_message or "duplicate" in error_message:
                error_type = "duplicate_resource"
                activity_id = activity.get("activity_id", "auto-generated")
                msg = f"Activity with activityId '{activity_id}' and timestamp already exists (versioning constraint violated)"
            else:
                error_type = "integrity_error"
                msg = f"Database constraint violation: {e!s}"

            failures.append(
                {
                    "activity_index": idx,
                    "activity": activity,
                    "errors": [
                        {
                            "loc": ["activities", idx],
                            "msg": msg,
                            "type": error_type,
                        }
                    ],
                }
            )
            failed += 1

        except Exception as e:
            # Rollback this savepoint only
            await savepoint.rollback()

            # Other errors
            failures.append(
                {
                    "activity_index": idx,
                    "activity": activity,
                    "errors": [
                        {
                            "loc": ["activities", idx],
                            "msg": f"Unexpected error: {e!s}",
                            "type": "processing_error",
                        }
                    ],
                }
            )
            failed += 1

    # Combine all failures: Pydantic + business logic validation + processing errors
    failures.extend(pydantic_failures)
    failures.extend(validation_failures)
    failed += len(pydantic_failures) + len(validation_failures)

    return {
        "total_processed": total_processed,
        "succeeded": succeeded,
        "failed": failed,
        "successes": successes,
        "failures": failures,
    }


async def count_activity(session: AsyncSession) -> int:
    """
    Count all activities.

    Args:
        session: Async database session

    Returns:
        Total number of activity records
    """
    return await activity_crud.count(session)


async def count_activity_by_competent_authority(
    session: AsyncSession, competent_authority_id: str
) -> int:
    """
    Count activities for a competent authority.

    Business logic for counting activities filtered by competent authority.

    Transaction Management:
    - Uses read-only session (no transaction needed for queries)
    - Service contains only business logic

    Args:
        session: Async database session (read-only)
        competent_authority_id: Competent authority ID string (e.g., "0363")

    Returns:
        Total number of activity records for the given competent authority
    """
    return await activity_crud.count_by_competent_authority_id(
        session, competent_authority_id
    )


async def get_activity_list(
    session: AsyncSession,
    competent_authority_id: str,
    offset: int = 0,
    limit: int | None = None,
) -> list[dict]:
    """
    Get activity list for a competent authority.

    Business logic for retrieving activities filtered by competent authority.
    Returns data in dictionary format for API layer serialization.

    Transaction Management:
    - Uses read-only session (no transaction needed for queries)
    - Service contains only business logic

    Args:
        session: Async database session (read-only)
        competent_authority_id: Competent authority ID string (e.g., "0363")
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of dictionaries containing activities
    """
    # Get activities from CRUD layer
    activity_list = await activity_crud.get_by_competent_authority_id(
        session,
        competent_authority_id,
        offset=offset,
        limit=limit,
    )

    # Convert SQLAlchemy models to dictionaries for API layer
    # Platform and Area information accessed via relationships
    # Return functional IDs (UUIDs), never expose technical IDs
    return [
        {
            "activity_id": activity.activity_id,  # Functional UUID
            "activity_name": activity.activity_name,  # Functional name (optional)
            "platform_id": activity.platform.platform_id,  # Functional ID via relationship
            "platform_name": activity.platform.platform_name,  # Name via relationship
            "url": activity.url,
            "address_street": activity.address_street,
            "address_number": activity.address_number,
            "address_letter": activity.address_letter,
            "address_addition": activity.address_addition,
            "address_postal_code": activity.address_postal_code,
            "address_city": activity.address_city,
            "registration_number": activity.registration_number,
            "area_id": activity.area.area_id,  # Functional UUID via relationship
            "number_of_guests": activity.number_of_guests,
            "country_of_guests": activity.country_of_guests,
            "temporal_start_date_time": activity.temporal_start_date_time,
            "temporal_end_date_time": activity.temporal_end_date_time,
            "created_at": activity.created_at,
        }
        for activity in activity_list
    ]
