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

from sqlalchemy import select
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
    Get a platform by platform_id string.

    Args:
        session: Async database session
        platform_id: Platform ID string (e.g., "platform01")

    Returns:
        Platform instance if found, None otherwise
    """
    result = await session.execute(
        select(Platform).where(Platform.platform_id == platform_id)
    )
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
    Get all platforms.

    Args:
        session: Async database session

    Returns:
        List of all Platform instances
    """
    result = await session.execute(select(Platform))
    return list(result.scalars().all())


async def count(session: AsyncSession) -> int:
    """
    Count total number of platforms.

    Args:
        session: Async database session

    Returns:
        Total count of platforms
    """
    result = await session.execute(select(Platform))
    return len(list(result.scalars().all()))
