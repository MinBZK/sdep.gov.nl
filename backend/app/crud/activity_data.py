"""CRUD operations for ActivityData model."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.activity_data import ActivityData
from app.models.area import Area
from app.models.competent_authority import CompetentAuthority


async def create(
    session: AsyncSession,
    url: str,
    address_street: str,
    address_number: int,
    address_letter: str | None,
    address_addition: str | None,
    address_postal_code: str,
    address_city: str,
    registration_number: str,
    area_id: int,
    number_of_guests: int,
    country_of_guests: list[str],
    temporal_start_date_time: datetime,
    temporal_end_date_time: datetime,
    platform_id: int,
) -> ActivityData:
    """
    Create a new activity data.

    Args:
        session: Async database session
        url: URL (128 characters, mandatory)
        address_street: Address street (mandatory, max 64 chars)
        address_number: Address number (mandatory)
        address_letter: Address letter (optional)
        address_addition: Address addition (optional)
        address_postal_code: Address postal code (mandatory, max 8 chars)
        address_city: Address city (mandatory, max 64 chars)
        registration_number: Registration number (mandatory, max 32 chars)
        area_id: Area id (foreign key to Area, mandatory)
        number_of_guests: Number of guests (mandatory)
        country_of_guests: Array of country codes (mandatory)
        temporal_start_date_time: Temporal start datetime (mandatory)
        temporal_end_date_time: Temporal end datetime (mandatory)
        platform_id: Platform id (foreign key to Platform, mandatory)

    Returns:
        Created ActivityData instance

    Note:
        The combination of url, temporal_start_date_time, and temporal_end_date_time must be unique.
    """
    activity_data = ActivityData(
        url=url,
        address_street=address_street,
        address_number=address_number,
        address_letter=address_letter,
        address_addition=address_addition,
        address_postal_code=address_postal_code,
        address_city=address_city,
        registration_number=registration_number,
        area_id=area_id,
        number_of_guests=number_of_guests,
        country_of_guests=country_of_guests,
        temporal_start_date_time=temporal_start_date_time,
        temporal_end_date_time=temporal_end_date_time,
        platform_id=platform_id,
    )
    session.add(activity_data)
    await session.flush()
    await session.refresh(activity_data)
    return activity_data


async def update(
    session: AsyncSession,
    activity_data_id: int,
    url: str | None = None,
    registration_number: str | None = None,
    platform_id: int | None = None,
    address_street: str | None = None,
    temporal_start_date_time: datetime | None = None,
    temporal_end_date_time: datetime | None = None,
    area_id: int | None = None,
    country_of_guests: list[str] | None = None,
    number_of_guests: int | None = None,
    address_number: int | None = None,
    address_letter: str | None = None,
    address_addition: str | None = None,
    address_postal_code: str | None = None,
    address_city: str | None = None,
) -> ActivityData | None:
    """
    Update an existing activity data by id.

    Args:
        session: Async database session
        activity_data_id: ActivityData id
        url: New URL
        registration_number: New registration number
        platform_id: New platform id (foreign key to Platform)
        address_street: New address street
        temporal_start_date_time: New temporal start datetime
        temporal_end_date_time: New temporal end datetime
        area_id: New area id (foreign key to Area)
        country_of_guests: New array of country codes
        number_of_guests: New number of guests
        address_number: New address number
        address_letter: New address letter
        address_addition: New address addition
        address_postal_code: New address postal code
        address_city: New address city

    Returns:
        Updated ActivityData instance or None if not found
    """
    activity_data = await get_by_id(session, activity_data_id)
    if activity_data is None:
        return None

    if url is not None:
        activity_data.url = url
    if registration_number is not None:
        activity_data.registration_number = registration_number
    if platform_id is not None:
        activity_data.platform_id = platform_id
    if address_street is not None:
        activity_data.address_street = address_street
    if temporal_start_date_time is not None:
        activity_data.temporal_start_date_time = temporal_start_date_time
    if temporal_end_date_time is not None:
        activity_data.temporal_end_date_time = temporal_end_date_time
    if area_id is not None:
        activity_data.area_id = area_id
    if country_of_guests is not None:
        activity_data.country_of_guests = country_of_guests
    if number_of_guests is not None:
        activity_data.number_of_guests = number_of_guests
    if address_number is not None:
        activity_data.address_number = address_number
    if address_letter is not None:
        activity_data.address_letter = address_letter
    if address_addition is not None:
        activity_data.address_addition = address_addition
    if address_postal_code is not None:
        activity_data.address_postal_code = address_postal_code
    if address_city is not None:
        activity_data.address_city = address_city

    await session.flush()
    await session.refresh(activity_data)
    return activity_data


async def delete(session: AsyncSession, activity_data_id: int) -> bool:
    """
    Delete an activity data by id.

    Args:
        session: Async database session
        activity_data_id: ActivityData id

    Returns:
        True if deleted, False if not found
    """
    activity_data = await get_by_id(session, activity_data_id)
    if activity_data is None:
        return False

    await session.delete(activity_data)
    await session.flush()
    return True


async def exists(session: AsyncSession, activity_data_id: int) -> bool:
    """
    Check if an activity data exists by id.

    Args:
        session: Async database session
        activity_data_id: ActivityData id

    Returns:
        True if exists, False otherwise
    """
    stmt = select(ActivityData.id).where(ActivityData.id == activity_data_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def count(session: AsyncSession) -> int:
    """
    Count all activity data.

    Args:
        session: Async database session

    Returns:
        Total number of activity data
    """
    stmt = select(func.count()).select_from(ActivityData)
    result = await session.execute(stmt)
    return result.scalar_one()


async def get_all(
    session: AsyncSession, offset: int = 0, limit: int | None = None
) -> list[ActivityData]:
    """
    Get all activity data with pagination.

    Args:
        session: Async database session
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of ActivityData instances
    """
    stmt = select(ActivityData).offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_id(session: AsyncSession, activity_data_id: int) -> ActivityData | None:
    """
    Get an activity data by id.

    Args:
        session: Async database session
        activity_data_id: ActivityData id

    Returns:
        ActivityData instance or None if not found
    """
    stmt = select(ActivityData).where(ActivityData.id == activity_data_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_url(
    session: AsyncSession, url: str, offset: int = 0, limit: int | None = None
) -> list[ActivityData]:
    """
    Get activity data by url with pagination.

    Note: URL alone is not unique. Use get_by_unique_constraint() to get a specific activity data.

    Args:
        session: Async database session
        url: URL
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of ActivityData instances matching the url
    """
    stmt = select(ActivityData).where(ActivityData.url == url).offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_unique_constraint(
    session: AsyncSession,
    url: str,
    temporal_start_date_time: datetime,
    temporal_end_date_time: datetime,
) -> ActivityData | None:
    """
    Get activity data by unique constraint (url + temporal dates).

    Args:
        session: Async database session
        url: URL
        temporal_start_date_time: Temporal start datetime
        temporal_end_date_time: Temporal end datetime

    Returns:
        ActivityData instance or None if not found
    """
    stmt = select(ActivityData).where(
        ActivityData.url == url,
        ActivityData.temporal_start_date_time == temporal_start_date_time,
        ActivityData.temporal_end_date_time == temporal_end_date_time,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_registration_number(
    session: AsyncSession,
    registration_number: str,
    offset: int = 0,
    limit: int | None = None,
) -> list[ActivityData]:
    """
    Get activity data by registration number with pagination.

    Args:
        session: Async database session
        registration_number: Registration number
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of ActivityData instances matching the registration number
    """
    stmt = (
        select(ActivityData)
        .where(ActivityData.registration_number == registration_number)
        .offset(offset)
    )
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_platform_id(
    session: AsyncSession, platform_id: int, offset: int = 0, limit: int | None = None
) -> list[ActivityData]:
    """
    Get activity data by platform_id (foreign key) with pagination.

    Args:
        session: Async database session
        platform_id: Platform id (foreign key to Platform)
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of ActivityData instances matching the platform_id
    """
    stmt = (
        select(ActivityData).where(ActivityData.platform_id == platform_id).offset(offset)
    )
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_area_id(
    session: AsyncSession, area_id: int, offset: int = 0, limit: int | None = None
) -> list[ActivityData]:
    """
    Get activity data by area_id (foreign key) with pagination.

    Args:
        session: Async database session
        area_id: Area id (foreign key to Area)
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of ActivityData instances for the given area_id
    """
    stmt = (
        select(ActivityData).where(ActivityData.area_id == area_id).offset(offset)
    )
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_competent_authority_id(
    session: AsyncSession,
    competent_authority_id: str,
    offset: int = 0,
    limit: int | None = None,
) -> list[ActivityData]:
    """
    Get activity data by competent authority ID with pagination.

    Uses a JOIN query through Area to get all ActivityData for a given competent authority.
    Eagerly loads the Platform relationship to avoid lazy loading issues.

    Args:
        session: Async database session
        competent_authority_id: Competent authority ID string (e.g., "0363")
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: no limit)

    Returns:
        List of ActivityData instances for the given competent authority
    """
    stmt = (
        select(ActivityData)
        .options(selectinload(ActivityData.platform))  # Eagerly load platform relationship
        .join(Area, ActivityData.area_id == Area.id)
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
    Count activity data by competent authority ID.

    Uses a JOIN query through Area to count all ActivityData for a given competent authority.

    Args:
        session: Async database session
        competent_authority_id: Competent authority ID string (e.g., "0363")

    Returns:
        Total number of activity data for the given competent authority
    """
    stmt = (
        select(func.count())
        .select_from(ActivityData)
        .join(Area, ActivityData.area_id == Area.id)
        .join(CompetentAuthority, Area.competent_authority_id == CompetentAuthority.id)
        .where(CompetentAuthority.competent_authority_id == competent_authority_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one()
