"""CRUD operations for Area model."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.area import Area


async def create(
    session: AsyncSession,
    area_id: str | None,
    filename: str,
    filedata: bytes,
    competent_authority_id: int,
) -> Area:
    """
    Create a new area.

    Args:
        session: Async database session
        area_id: Optional area identifier (64 characters max, lowercase alphanumeric with dashes). If not provided, a random value will be generated.
        filename: Filename (64 characters max)
        filedata: File data (binary)
        competent_authority_id: Foreign key to CompetentAuthority

    Returns:
        Created Area instance

    Note:
        The combination of area_id and competent_authority_id must be unique.
    """
    # Only set area_id if explicitly provided; otherwise let the model default handle it
    if area_id is not None:
        area = Area(
            area_id=area_id,
            filename=filename,
            filedata=filedata,
            competent_authority_id=competent_authority_id,
        )
    else:
        area = Area(
            filename=filename,
            filedata=filedata,
            competent_authority_id=competent_authority_id,
        )
    session.add(area)
    await session.flush()
    await session.refresh(area)
    return area


async def update(
    session: AsyncSession,
    area_id: int,
    area_id_value: str | None = None,
    filename: str | None = None,
    filedata: bytes | None = None,
    competent_authority_id: int | None = None,
) -> Area | None:
    """
    Update an existing area by id.

    Args:
        session: Async database session
        area_id: Area id (primary key)
        area_id_value: New area identifier (lowercase alphanumeric with dashes)
        filename: New filename
        filedata: New filedata (binary)
        competent_authority_id: Foreign key to CompetentAuthority

    Returns:
        Updated Area instance or None if not found
    """
    area = await get_by_id(session, area_id)
    if area is None:
        return None

    if area_id_value is not None:
        area.area_id = area_id_value
    if filename is not None:
        area.filename = filename
    if filedata is not None:
        area.filedata = filedata
    if competent_authority_id is not None:
        area.competent_authority_id = competent_authority_id

    await session.flush()
    await session.refresh(area)
    return area


async def delete(session: AsyncSession, area_id: int) -> bool:
    """
    Delete an area by id.

    Args:
        session: Async database session
        area_id: Area id

    Returns:
        True if deleted, False if not found
    """
    area = await get_by_id(session, area_id)
    if area is None:
        return False

    await session.delete(area)
    await session.flush()
    return True


async def exists(session: AsyncSession, area_id: int) -> bool:
    """
    Check if an area exists by id.

    Args:
        session: Async database session
        area_id: Area id

    Returns:
        True if exists, False otherwise
    """
    stmt = select(Area.id).where(Area.id == area_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def count(session: AsyncSession) -> int:
    """
    Count all areas.

    Args:
        session: Async database session

    Returns:
        Total number of areas
    """
    stmt = select(func.count()).select_from(Area)
    result = await session.execute(stmt)
    return result.scalar_one()


async def get_all(
    session: AsyncSession, offset: int = 0, limit: int | None = None
) -> list[Area]:
    """
    Get areas with pagination.

    Args:
        session: Async database session
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of Area instances
    """
    stmt = select(Area).offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_id(session: AsyncSession, area_id: int) -> Area | None:
    """
    Get an area by id.

    Args:
        session: Async database session
        area_id: Area id

    Returns:
        Area instance or None if not found
    """
    stmt = select(Area).where(Area.id == area_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_area_id(session: AsyncSession, area_id: str) -> Area | None:
    """
    Get an area by area_id (business identifier).

    Args:
        session: Async database session
        area_id: Area identifier (lowercase alphanumeric string with dashes)

    Returns:
        Area instance or None if not found

    Note:
        This function returns the first area with the given area_id.
        Since area_id alone is not unique (the unique constraint is area_id + competent_authority_id),
        use get_by_area_id_and_competent_authority_id() to get a specific area by the unique constraint.
    """
    stmt = select(Area).where(Area.area_id == area_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_area_id_and_competent_authority_id(
    session: AsyncSession, area_id: str, competent_authority_id: int
) -> Area | None:
    """
    Get an area by area_id and competent_authority_id (unique constraint).

    Args:
        session: Async database session
        area_id: Area identifier (lowercase alphanumeric string with dashes)
        competent_authority_id: Competent authority id (foreign key)

    Returns:
        Area instance or None if not found
    """
    stmt = select(Area).where(
        Area.area_id == area_id,
        Area.competent_authority_id == competent_authority_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_competent_authority_id(
    session: AsyncSession,
    competent_authority_id: int,
    offset: int = 0,
    limit: int | None = None,
) -> list[Area]:
    """
    Get areas by competent authority id (foreign key) with pagination.

    Args:
        session: Async database session
        competent_authority_id: Competent authority id (foreign key)
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of Area instances for the given competent authority
    """
    stmt = (
        select(Area)
        .where(Area.competent_authority_id == competent_authority_id)
        .offset(offset)
    )
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_filename(
    session: AsyncSession, filename: str, offset: int = 0, limit: int | None = None
) -> list[Area]:
    """
    Get areas by filename with pagination.

    Args:
        session: Async database session
        filename: Area filename
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of Area instances matching the filename
    """
    stmt = select(Area).where(Area.filename == filename).offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())
