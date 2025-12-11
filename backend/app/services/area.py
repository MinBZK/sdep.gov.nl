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
    return [
        {
            "areaId": area.area_id,
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


async def get_area_by_area_id(session: AsyncSession, area_id_value: str) -> dict | None:
    """
    Get a specific area.

    Args:
        session: Async database session
        area_id_value: Area identifier (lowercase alphanumeric string with dashes, unique)

    Returns:
        Dictionary containing area:
        - filename: area filename
        - filedata: area filedata (binary)
        Returns None if area not found
    """
    # Call CRUD function to get area by area_id (unique identifier)
    area = await area_crud.get_by_area_id(session, area_id_value)

    if area is None:
        return None

    # Transform to business layer response format
    return {
        "filename": area.filename,
        "filedata": area.filedata,
    }


async def process_area_list(session: AsyncSession, areas: list[dict]) -> None:
    """
    Process and save a list of areas.

    Business logic for processing area submissions.
    Validation is handled by Pydantic schemas in the API layer.

    Transaction Management:
    - Transaction is managed by the API layer via get_async_db dependency
    - Service contains only business logic
    - All areas are saved atomically (transaction commits at API layer)
    - If any area fails, entire transaction rolls back automatically

    Args:
        session: Async database session (transaction managed by API layer)
        areas: List of validated area dictionaries (validated by Pydantic), each containing:
            - area_id: Optional area identifier (auto-generated if None)
            - filename: Filename (64 characters max)
            - filedata: Binary file data
            - competent_authority_id_str: Competent authority ID from JWT token
            - competent_authority_name: Competent authority name from JWT token

    Raises:
        Exception: Any exception during processing will rollback the entire transaction

    Returns:
        None (areas are saved to database)
    """
    # Service layer contains business logic only (no transaction management)
    try:
        for area_dict in areas:
            # Look up or create CompetentAuthority by competent_authority_id string
            competent_authority_id_str = area_dict["competent_authority_id_str"]
            competent_authority_name = area_dict["competent_authority_name"]

            # Get competent authority by ID (should be unique)
            competent_authority = (
                await competent_authority_crud.get_by_competent_authority_id(
                    session, competent_authority_id_str
                )
            )

            if competent_authority is None:
                # Create competent authority if it doesn't exist
                competent_authority = await competent_authority_crud.create(
                    session=session,
                    competent_authority_id=competent_authority_id_str,
                    competent_authority_name=competent_authority_name,
                )

            # Save to database using CRUD layer (which only flushes)
            await area_crud.create(
                session=session,
                area_id=area_dict.get("area_id"),  # Can be None (auto-generated)
                filename=area_dict["filename"],
                filedata=area_dict["filedata"],
                competent_authority_id=competent_authority.id,  # Use the FK (int)
            )
    except IntegrityError as e:
        # Convert database integrity errors to domain exceptions
        error_message = str(e).lower()
        if "unique constraint" in error_message or "duplicate" in error_message:
            # Extract details for better error message
            area_id = area_dict.get("area_id", "auto-generated")
            filename = area_dict.get("filename", "unknown")
            raise DuplicateResourceError(
                f"Area with area_id '{area_id}' already exists"
            ) from e
        # Other integrity errors (foreign key, check constraints, etc.)
        raise BusinessLogicError(f"Database constraint violation: {e}") from e
    # Transaction commits at API layer automatically on success
    # Transaction rolls back at API layer automatically on exception
