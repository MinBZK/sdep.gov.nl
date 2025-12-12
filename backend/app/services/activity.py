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
from app.crud import competent_authority as competent_authority_crud
from app.crud import platform as platform_crud
from app.exceptions.business import BusinessLogicError, DuplicateResourceError


async def process_activity_list(
    session: AsyncSession, activities: list[dict]
) -> None:
    """
    Process and save a list of activities.

    Business logic for processing activity submissions.
    Validation is handled by Pydantic schemas in the API layer.

    Transaction Management:
    - Transaction is managed by the API layer via get_async_db dependency
    - Service contains only business logic
    - All activities are saved atomically (transaction commits at API layer)
    - If any activity fails, entire transaction rolls back automatically

    Args:
        session: Async database session (transaction managed by API layer)
        activities: List of validated activity dictionaries (validated by Pydantic), each containing:
            - activity_id: Activity ID string (optional, auto-generated if not provided)
            - url: Unique URL
            - address_street: Street name
            - address_number: House number
            - address_letter: House letter (optional)
            - address_addition: House addition (optional)
            - address_postal_code: Postal code
            - address_city: City name
            - registration_number: Registration number
            - area_id: Area ID string
            - competent_authority_id: Competent Authority ID string
            - number_of_guests: Number of guests (optional)
            - country_of_guests: Array of country codes (optional)
            - temporal_start_date_time: Start datetime
            - temporal_end_date_time: End datetime
            - platform_id_str: Platform ID string from JWT token
            - platform_name: Platform name from JWT token

    Raises:
        Exception: Any exception during processing will rollback the entire transaction

    Returns:
        None (activities are saved to database)
    """
    # Service layer contains business logic only (no transaction management)
    try:
        for activity in activities:
            # Look up CompetentAuthority by competent_authority_id string to get the FK
            competent_authority_id_str = activity["competent_authority_id"]
            competent_authority = await competent_authority_crud.get_by_competent_authority_id(
                session, competent_authority_id_str
            )

            if competent_authority is None:
                raise BusinessLogicError(
                    f"Competent authority with competent_authority_id '{competent_authority_id_str}' not found",
                    details={"competent_authority_id": competent_authority_id_str},
                )

            # Look up Area by area_id string and competent_authority FK to get the Area FK
            area_id_str = activity["area_id"]
            area = await area_crud.get_by_area_id_and_competent_authority_id(
                session, area_id_str, competent_authority.id
            )

            if area is None:
                raise BusinessLogicError(
                    f"Area with area_id '{area_id_str}' and competent_authority_id '{competent_authority_id_str}' not found",
                    details={
                        "area_id": area_id_str,
                        "competent_authority_id": competent_authority_id_str,
                    },
                )

            # Look up or create Platform by platform_id string
            platform_id_str = activity["platform_id_str"]
            platform_name = activity["platform_name"]
            platform = await platform_crud.get_by_platform_id(session, platform_id_str)

            if platform is None:
                # Create platform if it doesn't exist
                platform = await platform_crud.create(
                    session=session,
                    platform_id=platform_id_str,
                    platform_name=platform_name,
                )

            # Save to database using CRUD layer (which only flushes)
            await activity_crud.create(
                session=session,
                activity_id=activity.get("activity_id"),  # Use provided ID or let model generate it
                url=activity["url"],
                address_street=activity["address_street"],
                address_number=activity["address_number"],
                address_letter=activity.get("address_letter"),
                address_addition=activity.get("address_addition"),
                address_postal_code=activity["address_postal_code"],
                address_city=activity["address_city"],
                registration_number=activity["registration_number"],
                area_id=area.id,  # Use the FK (int) instead of area_id string
                number_of_guests=activity["number_of_guests"],
                country_of_guests=activity["country_of_guests"],
                temporal_start_date_time=activity["temporal_start_date_time"],
                temporal_end_date_time=activity["temporal_end_date_time"],
                platform_id=platform.id,  # Use the FK (int) to Platform
            )
    except IntegrityError as e:
        # Convert database integrity errors to domain exceptions
        error_message = str(e).lower()
        if "unique constraint" in error_message or "duplicate" in error_message:
            # Extract details from activity for better error message
            activity_id = activity.get("activity_id", "auto-generated")
            platform_id = activity.get("platform_id_str", "unknown")
            url = activity.get("url", "unknown")
            start_time = activity.get("temporal_start_date_time", "unknown")
            end_time = activity.get("temporal_end_date_time", "unknown")
            raise DuplicateResourceError(
                f"Activity with activityId '{activity_id}', platform '{platform_id}', "
                f"URL '{url}', start time '{start_time}', and end time '{end_time}' already exists"
            ) from e
        # Other integrity errors (foreign key, check constraints, etc.)
        raise BusinessLogicError(f"Database constraint violation: {e}") from e
    # Transaction commits at API layer automatically on success
    # Transaction rolls back at API layer automatically on exception


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
        session, competent_authority_id, offset=offset, limit=limit
    )

    # Convert SQLAlchemy models to dictionaries for API layer
    # Platform information is accessed via the relationship
    return [
        {
            "activity_id": activity.activity_id,
            "url": activity.url,
            "address_street": activity.address_street,
            "address_number": activity.address_number,
            "address_letter": activity.address_letter,
            "address_addition": activity.address_addition,
            "address_postal_code": activity.address_postal_code,
            "address_city": activity.address_city,
            "registration_number": activity.registration_number,
            "area_id": activity.area.area_id,  # Access via relationship to get string area_id
            "number_of_guests": activity.number_of_guests,
            "country_of_guests": activity.country_of_guests,
            "temporal_start_date_time": activity.temporal_start_date_time,
            "temporal_end_date_time": activity.temporal_end_date_time,
            "platform_id": activity.platform.platform_id,  # Access via relationship
            "platform_name": activity.platform.platform_name,  # Access via relationship
            "created_at": activity.created_at,
        }
        for activity in activity_list
    ]
