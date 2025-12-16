"""Area business service.

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

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud import area as area_crud
from app.crud import competent_authority as competent_authority_crud
from app.exceptions.business import BusinessLogicError, DuplicateResourceError
from app.models.area import Area


async def get_areas(
    session: AsyncSession, offset: int = 0, limit: int | None = None
) -> list[dict]:
    """
    Get areas in context of the current SDEP/member state.

    Args:
        session: Async database session
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of area dictionaries, each containing:
        - areaId: Area unique identifier
        - competentAuthorityId: Competent authority (id) who submitted the area
        - competentAuthorityName: Competent authority (name) who submitted the area
        - filename: Area filename
        - createdAt: Timestamp when the area was created
    """
    # Use eager loading to fetch competent_authority relationship
    stmt = select(Area).options(selectinload(Area.competent_authority)).offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    areas = result.scalars().all()

    # Transform to business layer response format
    # Return functional IDs (UUIDs), never expose technical IDs
    return [
        {
            "areaId": area.area_id,  # Functional UUID
            "areaName": area.area_name,  # Functional name (optional)
            "competentAuthorityId": area.competent_authority.competent_authority_id,
            "competentAuthorityName": area.competent_authority.competent_authority_name,
            "filename": area.filename,
            "createdAt": area.created_at,
        }
        for area in areas
    ]


async def count_areas(session: AsyncSession) -> int:
    """
    Count all areas in context of the current SDEP/member state.

    Args:
        session: Async database session

    Returns:
        Total number of areas
    """
    return await area_crud.count(session)


async def get_area_by_id(session: AsyncSession, area_id: str) -> dict | None:
    """
    Get a specific area by functional ID (UUID).

    Args:
        session: Async database session
        area_id: Functional area ID (UUID string)

    Returns:
        Dictionary containing area:
        - filename: area filename
        - filedata: area filedata (binary)
        Returns None if area not found
    """
    area = await area_crud.get_by_area_id(session, area_id)

    if area is None:
        return None

    return {
        "filename": area.filename,
        "filedata": area.filedata,
    }


async def validate_area(
    session: AsyncSession, area: dict, area_index: int
) -> list[dict]:
    """
    Validate a single area (business logic validation only).

    Phase 1 validation: Check if any custom validations are needed.
    Does NOT attempt to save to database.

    For areas, CompetentAuthority is auto-created if it doesn't exist,
    so no validation is needed here. This function is kept for consistency
    with the str_activities pattern and for future extensions.

    Args:
        session: Async database session
        area: Area dictionary (validated by Pydantic)
        area_index: Index of area in original request (0-based)

    Returns:
        List of error dictionaries (empty if valid). Each error has:
        - loc: ["areas", index, field_name]
        - msg: Error message
        - type: Error type ("business_logic_error")
    """
    errors = []

    # For areas, we auto-create CompetentAuthority if it doesn't exist,
    # so no validation is needed here.
    # Add any future business logic validation here.

    return errors


async def process_single_area(
    session: AsyncSession, area: dict
) -> None:
    """
    Process and save a single area (assumes validation already passed).

    Called within a savepoint context. Raises exceptions on database errors.

    Args:
        session: Async database session (within savepoint)
        area: Area dictionary (already validated)

    Raises:
        IntegrityError: Database constraint violation
        Any other database error
    """
    # Look up or create CompetentAuthority
    competent_authority_id_str = area["competent_authority_id_str"]
    competent_authority_name = area["competent_authority_name"]

    competent_authority = await competent_authority_crud.get_by_competent_authority_id(
        session, competent_authority_id_str
    )

    if competent_authority is None:
        competent_authority = await competent_authority_crud.create(
            session=session,
            competent_authority_id=competent_authority_id_str,
            competent_authority_name=competent_authority_name,
        )

    # Save area (CRUD only flushes)
    await area_crud.create(
        session=session,
        area_id=area.get("area_id"),  # Can be None (auto-generated UUID)
        area_name=area.get("area_name"),  # Optional name
        filename=area["filename"],
        filedata=area["filedata"],
        competent_authority_id=competent_authority.id,  # Use the FK (int)
    )


async def process_area_list(
    session: AsyncSession,
    areas: list[dict],
    pydantic_errors_by_index: dict[int, list[dict]] | None = None,
) -> dict:
    """
    Process and save a list of areas using three-phase approach with nested transactions.

    Phase 0: Collect Pydantic validation errors (from API layer)
    Phase 1: Validate all areas (business logic: any custom validations)
    Phase 2: Process valid areas using savepoints (each area independently)

    Transaction Management:
    - Transaction is managed by the API layer (manual commit required)
    - Service uses nested transactions (savepoints) for each area
    - Each area can succeed or fail independently
    - Overall transaction commits at API layer after all processing

    System Crash Behavior (Before API Commit):
    - Savepoints protect against individual area failures during processing
    - Savepoints do NOT protect against system crashes before final commit
    - If system crashes after this function returns but before API commits:
      * ALL changes are lost (including areas that "succeeded" in savepoints)
      * PostgreSQL automatically rolls back uncommitted transactions on connection loss
      * Example: 7 areas, 5 processed (2 succeeded, 3 failed), crash → ALL 5 rolled back
    - This is PostgreSQL's ACID guarantee: uncommitted work is never persisted

    Args:
        session: Async database session (manual commit mode)
        areas: List of area dictionaries (may include invalid ones), each containing:
            - area_id: Optional functional ID (RFC 4122 UUID, auto-generated if None)
            - area_name: Optional human-readable name
            - filename: Filename (64 characters max)
            - filedata: Binary file data
            - competent_authority_id_str: Competent authority ID from JWT token
            - competent_authority_name: Competent authority name from JWT token
        pydantic_errors_by_index: Dict mapping area index to Pydantic validation errors

    Returns:
        Dictionary with processing results:
        {
            "total_processed": int,
            "succeeded": int,
            "failed": int,
            "failures": [
                {
                    "area_index": int,
                    "area": dict,
                    "errors": [{"loc": [...], "msg": str, "type": str}]
                }
            ]
        }
    """
    if pydantic_errors_by_index is None:
        pydantic_errors_by_index = {}

    total_processed = len(areas)
    succeeded = 0
    failed = 0
    failures = []

    # PHASE 0: Handle Pydantic validation failures
    # These areas failed schema validation and cannot be processed
    pydantic_failures = []
    for idx, errors in pydantic_errors_by_index.items():
        area = areas[idx]
        pydantic_failures.append({
            "area_index": idx,
            "area": area,
            "errors": errors,
        })

    # PHASE 1: Validate all areas (business logic validation)
    # Skip areas that already failed Pydantic validation
    # Collect all validation errors without stopping
    validation_failures = []
    valid_indices = []

    for idx, area in enumerate(areas):
        # Skip if already failed Pydantic validation
        if idx in pydantic_errors_by_index:
            continue

        # Skip if marked as Pydantic validation failed
        if area.get("_pydantic_validation_failed"):
            continue

        errors = await validate_area(session, area, idx)
        if errors:
            validation_failures.append({
                "area_index": idx,
                "area": area,
                "errors": errors,
            })
        else:
            valid_indices.append(idx)

    # PHASE 2: Process valid areas using nested transactions (savepoints)
    # Each area processes in its own savepoint
    # NOTE: Savepoints only protect against individual area failures.
    # If system crashes before API commit, ALL savepoints are rolled back.
    for idx in valid_indices:
        area = areas[idx]

        # Create savepoint for this area
        savepoint = await session.begin_nested()

        try:
            # Process the area
            await process_single_area(session, area)

            # Flush to detect database errors within savepoint
            await session.flush()

            # Success - savepoint commits automatically
            succeeded += 1

        except IntegrityError as e:
            # Rollback this savepoint only
            await savepoint.rollback()

            # Classify error type
            error_message = str(e).lower()
            if "unique constraint" in error_message or "duplicate" in error_message:
                error_type = "duplicate_resource"
                area_id = area.get("area_id", "auto-generated")
                msg = f"Area with areaId '{area_id}' and timestamp already exists (versioning constraint violated)"
            else:
                error_type = "integrity_error"
                msg = f"Database constraint violation: {str(e)}"

            failures.append({
                "area_index": idx,
                "area": area,
                "errors": [{
                    "loc": ["areas", idx],
                    "msg": msg,
                    "type": error_type,
                }],
            })
            failed += 1

        except Exception as e:
            # Rollback this savepoint only
            await savepoint.rollback()

            # Other errors
            failures.append({
                "area_index": idx,
                "area": area,
                "errors": [{
                    "loc": ["areas", idx],
                    "msg": f"Unexpected error: {str(e)}",
                    "type": "processing_error",
                }],
            })
            failed += 1

    # Combine all failures
    failures.extend(pydantic_failures)
    failures.extend(validation_failures)
    failed += len(pydantic_failures) + len(validation_failures)

    return {
        "total_processed": total_processed,
        "succeeded": succeeded,
        "failed": failed,
        "failures": failures,
    }
