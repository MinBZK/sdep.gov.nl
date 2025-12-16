"""CRUD operations for Activity model."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.activity import Activity
from app.models.area import Area
from app.models.competent_authority import CompetentAuthority


async def create(
    session: AsyncSession,
    platform_activity_id: str | None,
    platform_id: int,
    area_id: str,
    url: str,
    address_street: str,
    address_number: int,
    address_letter: str | None,
    address_addition: str | None,
    address_postal_code: str,
    address_city: str,
    registration_number: str,
    number_of_guests: int | None,
    country_of_guests: list[str] | None,
    temporal_start_date_time: datetime,
    temporal_end_date_time: datetime,
) -> Activity:
    """
    Create a new activity.

    Args:
        session: Async database session
        platform_activity_id: Optional activity identifier (64 characters max, lowercase alphanumeric). If not provided, a random value will be generated.
        platform_id: Platform id (foreign key to Platform, mandatory)
        area_id: Area id (foreign key to Area, mandatory)
        url: URL (128 characters, mandatory)
        address_street: Address street (mandatory, max 64 chars)
        address_number: Address number (mandatory)
        address_letter: Address letter (optional)
        address_addition: Address addition (optional)
        address_postal_code: Address postal code (mandatory, max 8 chars)
        address_city: Address city (mandatory, max 64 chars)
        registration_number: Registration number (mandatory, max 32 chars)
        number_of_guests: Number of guests (optional)
        country_of_guests: Array of country codes (optional)
        temporal_start_date_time: Temporal start datetime (mandatory)
        temporal_end_date_time: Temporal end datetime (mandatory)

    Returns:
        Created Activity instance
    """
    # Only set platform_activity_id if explicitly provided; otherwise let the model default handle it
    if platform_activity_id is not None:
        activity = Activity(
            platform_activity_id=platform_activity_id,
            platform_id=platform_id,
            area_id=area_id,
            url=url,
            address_street=address_street,
            address_number=address_number,
            address_letter=address_letter,
            address_addition=address_addition,
            address_postal_code=address_postal_code,
            address_city=address_city,
            registration_number=registration_number,
            number_of_guests=number_of_guests,
            country_of_guests=country_of_guests,
            temporal_start_date_time=temporal_start_date_time,
            temporal_end_date_time=temporal_end_date_time,
        )
    else:
        activity = Activity(
            platform_id=platform_id,
            area_id=area_id,
            url=url,
            address_street=address_street,
            address_number=address_number,
            address_letter=address_letter,
            address_addition=address_addition,
            address_postal_code=address_postal_code,
            address_city=address_city,
            registration_number=registration_number,
            number_of_guests=number_of_guests,
            country_of_guests=country_of_guests,
            temporal_start_date_time=temporal_start_date_time,
            temporal_end_date_time=temporal_end_date_time,
        )
    session.add(activity)
    await session.flush()
    await session.refresh(activity)
    return activity


async def delete(session: AsyncSession, activity_id: str) -> bool:
    """
    Delete an activity by id.

    Args:
        session: Async database session
        activity_id: Activity id

    Returns:
        True if deleted, False if not found
    """
    activity = await get_by_id(session, activity_id)
    if activity is None:
        return False

    await session.delete(activity)
    await session.flush()
    return True


async def exists(session: AsyncSession, activity_id: str) -> bool:
    """
    Check if an activity exists by id.

    Args:
        session: Async database session
        activity_id: Activity id

    Returns:
        True if exists, False otherwise
    """
    stmt = select(Activity.id).where(Activity.id == activity_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def count(session: AsyncSession) -> int:
    """
    Count all activities.

    Args:
        session: Async database session

    Returns:
        Total number of activities
    """
    stmt = select(func.count()).select_from(Activity)
    result = await session.execute(stmt)
    return result.scalar_one()


async def get_all(
    session: AsyncSession, offset: int = 0, limit: int | None = None
) -> list[Activity]:
    """
    Get all activities with pagination.

    Args:
        session: Async database session
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of Activity instances
    """
    stmt = select(Activity).offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_id(
    session: AsyncSession, activity_id: str
) -> Activity | None:
    """
    Get an activity by id.

    Args:
        session: Async database session
        activity_id: Activity id

    Returns:
        Activity instance or None if not found
    """
    stmt = select(Activity).where(Activity.id == activity_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_url(
    session: AsyncSession, url: str, offset: int = 0, limit: int | None = None
) -> list[Activity]:
    """
    Get activities by url with pagination.

    Args:
        session: Async database session
        url: URL
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of Activity instances matching the url
    """
    stmt = select(Activity).where(Activity.url == url).offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_registration_number(
    session: AsyncSession,
    registration_number: str,
    offset: int = 0,
    limit: int | None = None,
) -> list[Activity]:
    """
    Get activities by registration number with pagination.

    Args:
        session: Async database session
        registration_number: Registration number
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of Activity instances matching the registration number
    """
    stmt = (
        select(Activity)
        .where(Activity.registration_number == registration_number)
        .offset(offset)
    )
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_platform_id(
    session: AsyncSession, platform_id: int, offset: int = 0, limit: int | None = None
) -> list[Activity]:
    """
    Get activities by platform_id (foreign key) with pagination.

    Args:
        session: Async database session
        platform_id: Platform id (foreign key to Platform)
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of Activity instances matching the platform_id
    """
    stmt = (
        select(Activity)
        .where(Activity.platform_id == platform_id)
        .offset(offset)
    )
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_area_id(
    session: AsyncSession, area_id: str, offset: int = 0, limit: int | None = None
) -> list[Activity]:
    """
    Get activities by area_id (foreign key) with pagination.

    Args:
        session: Async database session
        area_id: Area id (foreign key to Area)
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of Activity instances for the given area_id
    """
    stmt = select(Activity).where(Activity.area_id == area_id).offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_competent_authority_id(
    session: AsyncSession,
    competent_authority_id: str,
    offset: int = 0,
    limit: int | None = None,
) -> list[Activity]:
    """
    Get activities by competent authority ID with pagination.

    Uses a JOIN query through Area to get all Activity for a given competent authority.
    Eagerly loads the Platform relationship to avoid lazy loading issues.

    Args:
        session: Async database session
        competent_authority_id: Competent authority ID string (e.g., "0363")
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of Activity instances for the given competent authority
    """
    stmt = (
        select(Activity)
        .options(
            selectinload(Activity.platform),  # Eagerly load platform relationship
            selectinload(Activity.area).selectinload(Area.competent_authority),
        )
        .join(Area, Activity.area_id == Area.id)
        .join(CompetentAuthority, Area.competent_authority_id == CompetentAuthority.id)
        .where(CompetentAuthority.competent_authority_id == competent_authority_id)
        .offset(offset)
    )
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_by_competent_authority_id(
    session: AsyncSession,
    competent_authority_id: str,
) -> int:
    """
    Count activities by competent authority ID.

    Uses a JOIN query through Area to count all Activity for a given competent authority.

    Args:
        session: Async database session
        competent_authority_id: Competent authority ID string (e.g., "0363")

    Returns:
        Total number of activities for the given competent authority
    """
    stmt = (
        select(func.count())
        .select_from(Activity)
        .join(Area, Activity.area_id == Area.id)
        .join(CompetentAuthority, Area.competent_authority_id == CompetentAuthority.id)
        .where(CompetentAuthority.competent_authority_id == competent_authority_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one()
