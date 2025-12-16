"""CRUD operations for Area model."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.area import Area


async def create(
    session: AsyncSession,
    competent_authority_area_id: str | None,
    competent_authority_id: int,
    filename: str,
    filedata: bytes,
) -> Area:
    """
    Create a new area.

    Args:
        session: Async database session
        competent_authority_area_id: Optional area identifier (64 characters max, lowercase alphanumeric with dashes). If not provided, a random value will be generated.
        competent_authority_id: Foreign key to CompetentAuthority
        filename: Filename (64 characters max)
        filedata: File data (binary)

    Returns:
        Created Area instance

    Note:
        The combination of competent_authority_id, competent_authority_area_id, and created_at must be unique.
        This enables versioning/stapling (same IDs with different timestamps).
    """
    # Only set competent_authority_area_id if explicitly provided; otherwise let the model default handle it
    if competent_authority_area_id is not None:
        area = Area(
            competent_authority_area_id=competent_authority_area_id,
            competent_authority_id=competent_authority_id,
            filename=filename,
            filedata=filedata,
        )
    else:
        area = Area(
            competent_authority_id=competent_authority_id,
            filename=filename,
            filedata=filedata,
        )
    session.add(area)
    await session.flush()
    await session.refresh(area)
    return area


async def delete(session: AsyncSession, area_id: str) -> bool:
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


async def exists(session: AsyncSession, area_id: str) -> bool:
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


async def get_by_id(session: AsyncSession, area_id: str) -> Area | None:
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
