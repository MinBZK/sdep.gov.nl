"""Areas business service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud import area as area_crud
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
    Get area data for a specific area by area_id string.

    Args:
        session: Async database session
        area_id_value: Area identifier (lowercase alphanumeric string with dashes, unique)

    Returns:
        Dictionary containing area data:
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
