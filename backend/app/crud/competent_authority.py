"""CRUD operations for CompetentAuthority model."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competent_authority import CompetentAuthority


async def create(
    session: AsyncSession,
    competent_authority_id: str,
    competent_authority_name: str,
) -> CompetentAuthority:
    """
    Create a new competent authority.

    Args:
        session: Async database session
        competent_authority_id: Competent authority identifier (64 characters max, unique)
        competent_authority_name: Competent authority name (128 characters max)

    Returns:
        Created CompetentAuthority instance
    """
    competent_authority = CompetentAuthority(
        competent_authority_id=competent_authority_id,
        competent_authority_name=competent_authority_name,
    )
    session.add(competent_authority)
    await session.flush()
    await session.refresh(competent_authority)
    return competent_authority


async def update(
    session: AsyncSession,
    id: int,
    competent_authority_id: str | None = None,
    competent_authority_name: str | None = None,
) -> CompetentAuthority | None:
    """
    Update an existing competent authority by id.

    Args:
        session: Async database session
        id: CompetentAuthority id (primary key)
        competent_authority_id: New competent authority identifier
        competent_authority_name: New competent authority name

    Returns:
        Updated CompetentAuthority instance or None if not found
    """
    competent_authority = await get_by_id(session, id)
    if competent_authority is None:
        return None

    if competent_authority_id is not None:
        competent_authority.competent_authority_id = competent_authority_id
    if competent_authority_name is not None:
        competent_authority.competent_authority_name = competent_authority_name

    await session.flush()
    await session.refresh(competent_authority)
    return competent_authority


async def delete(session: AsyncSession, id: int) -> bool:
    """
    Delete a competent authority by id.

    Args:
        session: Async database session
        id: CompetentAuthority id

    Returns:
        True if deleted, False if not found
    """
    competent_authority = await get_by_id(session, id)
    if competent_authority is None:
        return False

    await session.delete(competent_authority)
    await session.flush()
    return True


async def exists(session: AsyncSession, id: int) -> bool:
    """
    Check if a competent authority exists by id.

    Args:
        session: Async database session
        id: CompetentAuthority id

    Returns:
        True if exists, False otherwise
    """
    stmt = select(CompetentAuthority.id).where(CompetentAuthority.id == id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def count(session: AsyncSession) -> int:
    """
    Count all competent authorities.

    Args:
        session: Async database session

    Returns:
        Total number of competent authorities
    """
    stmt = select(func.count()).select_from(CompetentAuthority)
    result = await session.execute(stmt)
    return result.scalar_one()


async def get_all(session: AsyncSession, offset: int = 0, limit: int | None = None) -> list[CompetentAuthority]:
    """
    Get competent authorities with pagination.

    Args:
        session: Async database session
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of CompetentAuthority instances
    """
    stmt = select(CompetentAuthority).offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_id(session: AsyncSession, id: int) -> CompetentAuthority | None:
    """
    Get a competent authority by id.

    Args:
        session: Async database session
        id: CompetentAuthority id

    Returns:
        CompetentAuthority instance or None if not found
    """
    stmt = select(CompetentAuthority).where(CompetentAuthority.id == id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_competent_authority_id(
    session: AsyncSession, competent_authority_id: str, offset: int = 0, limit: int | None = None
) -> list[CompetentAuthority]:
    """
    Get competent authorities by competent_authority_id with pagination.

    Args:
        session: Async database session
        competent_authority_id: Competent authority identifier
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of CompetentAuthority instances matching the competent_authority_id
    """
    stmt = (
        select(CompetentAuthority)
        .where(CompetentAuthority.competent_authority_id == competent_authority_id)
        .offset(offset)
    )
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_competent_authority_name(
    session: AsyncSession, competent_authority_name: str, offset: int = 0, limit: int | None = None
) -> list[CompetentAuthority]:
    """
    Get competent authorities by competent_authority_name with pagination.

    Args:
        session: Async database session
        competent_authority_name: Competent authority name
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of CompetentAuthority instances matching the competent_authority_name
    """
    stmt = (
        select(CompetentAuthority)
        .where(CompetentAuthority.competent_authority_name == competent_authority_name)
        .offset(offset)
    )
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())
