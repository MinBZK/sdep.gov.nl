"""Platform CRUD operations.

CRUD Pattern - Transaction Management:
- CRUD layer contains data access logic only (no business logic, no transaction management)
- All CRUD functions use session.flush() instead of session.commit()
- Transaction boundaries are managed by the API layer (via get_async_db dependency)
- This keeps CRUD functions simple, reusable, and testable

Pattern:
- API layer: Transaction boundary (auto-commit via dependency)
- Service layer: Business logic (no transaction management)
- CRUD layer: Data access (flush only, no commits)
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform import Platform


async def create(
    session: AsyncSession,
    platform_id: str,
    platform_name: str,
) -> Platform:
    """
    Create a new platform.

    Transaction Management:
    - Only flushes data (session.flush())
    - Never commits (transaction managed by API layer)
    - Flush makes ID available immediately for foreign key relationships

    Args:
        session: Async database session (transaction managed by API layer)
        platform_id: Platform ID string (unique identifier, e.g., "platform01")
        platform_name: Platform name (e.g., "Booking.com")

    Returns:
        Created Platform instance with ID populated

    Raises:
        IntegrityError: If platform_id already exists (unique constraint violation)
    """
    platform = Platform(
        platform_id=platform_id,
        platform_name=platform_name,
    )
    session.add(platform)
    await session.flush()  # Flush only, no commit (transaction managed by API layer)
    return platform


async def get_by_platform_id(
    session: AsyncSession, platform_id: str
) -> Platform | None:
    """
    Get a platform by platform_id string (latest version).

    Args:
        session: Async database session
        platform_id: Platform ID string (e.g., "platform01")

    Returns:
        Latest Platform instance for the given platform_id, or None if not found
    """
    stmt = (
        select(Platform)
        .where(Platform.platform_id == platform_id)
        .order_by(Platform.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, platform_id: int) -> Platform | None:
    """
    Get a platform by primary key ID.

    Args:
        session: Async database session
        platform_id: Primary key ID (integer)

    Returns:
        Platform instance if found, None otherwise
    """
    result = await session.execute(select(Platform).where(Platform.id == platform_id))
    return result.scalar_one_or_none()


async def get_all(session: AsyncSession) -> list[Platform]:
    """
    Get all platforms (latest versions only).

    Args:
        session: Async database session

    Returns:
        List of all Platform instances (latest version per platform_id)
    """
    stmt = (
        select(Platform)
        .distinct(Platform.platform_id)
        .order_by(Platform.platform_id, Platform.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def delete(session: AsyncSession, platform_id: int) -> bool:
    """
    Delete a platform by primary key id.

    Args:
        session: Async database session
        platform_id: Platform id (primary key)

    Returns:
        True if deleted, False if not found
    """
    platform = await get_by_id(session, platform_id)
    if platform is None:
        return False

    await session.delete(platform)
    await session.flush()
    return True


async def exists(session: AsyncSession, platform_id: int) -> bool:
    """
    Check if a platform exists by primary key id.

    Args:
        session: Async database session
        platform_id: Platform id (primary key)

    Returns:
        True if exists, False otherwise
    """
    stmt = select(Platform.id).where(Platform.id == platform_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def count(session: AsyncSession) -> int:
    """
    Count total number of platforms.

    Args:
        session: Async database session

    Returns:
        Total count of platforms
    """
    stmt = select(func.count()).select_from(Platform)
    result = await session.execute(stmt)
    return result.scalar_one()
