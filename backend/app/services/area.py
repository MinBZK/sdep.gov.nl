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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud import area as area_crud
from app.crud import competent_authority as competent_authority_crud
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


async def create_area(
    session: AsyncSession,
    area_id: str | None,
    area_name: str | None,
    filename: str,
    filedata: bytes,
    competent_authority_id_str: str,
    competent_authority_name: str,
) -> Area:
    """
    Create a single area.

    Looks up or creates the CompetentAuthority, then creates the Area.

    Args:
        session: Async database session
        area_id: Optional functional ID (auto-generated UUID if None)
        area_name: Optional human-readable name
        filename: Filename of the uploaded file
        filedata: Binary file data
        competent_authority_id_str: Competent authority ID from JWT token
        competent_authority_name: Competent authority name from JWT token

    Returns:
        Created Area object
    """
    # Look up or create CompetentAuthority
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
    area_obj = await area_crud.create(
        session=session,
        area_id=area_id,
        area_name=area_name,
        filename=filename,
        filedata=filedata,
        competent_authority_id=competent_authority.id,  # Use the FK (int)
    )

    return area_obj
