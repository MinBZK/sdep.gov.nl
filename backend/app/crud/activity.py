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
    activity_id: str | None,
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
) -> Activity:
    """
    Create a new activity.

    Args:
        session: Async database session
        activity_id: Optional activity identifier (64 characters max, lowercase alphanumeric). If not provided, a random value will be generated.
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
        Created Activity instance

    Note:
        Two unique constraints apply:
        1. The combination of url, temporal_start_date_time, and temporal_end_date_time must be unique.
        2. The combination of activity_id and platform_id must be unique.
    """
    # Only set activity_id if explicitly provided; otherwise let the model default handle it
    if activity_id is not None:
        activity = Activity(
            activity_id=activity_id,
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
    else:
        activity = Activity(
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
    session.add(activity)
    await session.flush()
    await session.refresh(activity)
    return activity


async def update(
    session: AsyncSession,
    activity_id: int,
    activity_id_value: str | None = None,
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
) -> Activity | None:
    """
    Update an existing activity by id.

    Args:
        session: Async database session
        activity_id: Activity id (primary key)
        activity_id_value: New activity identifier (lowercase alphanumeric)
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
        Updated Activity instance or None if not found
    """
    activity = await get_by_id(session, activity_id)
    if activity is None:
        return None

    if activity_id_value is not None:
        activity.activity_id = activity_id_value
    if url is not None:
        activity.url = url
    if registration_number is not None:
        activity.registration_number = registration_number
    if platform_id is not None:
        activity.platform_id = platform_id
    if address_street is not None:
        activity.address_street = address_street
    if temporal_start_date_time is not None:
        activity.temporal_start_date_time = temporal_start_date_time
    if temporal_end_date_time is not None:
        activity.temporal_end_date_time = temporal_end_date_time
    if area_id is not None:
        activity.area_id = area_id
    if country_of_guests is not None:
        activity.country_of_guests = country_of_guests
    if number_of_guests is not None:
        activity.number_of_guests = number_of_guests
    if address_number is not None:
        activity.address_number = address_number
    if address_letter is not None:
        activity.address_letter = address_letter
    if address_addition is not None:
        activity.address_addition = address_addition
    if address_postal_code is not None:
        activity.address_postal_code = address_postal_code
    if address_city is not None:
        activity.address_city = address_city

    await session.flush()
    await session.refresh(activity)
    return activity


async def delete(session: AsyncSession, activity_id: int) -> bool:
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


async def exists(session: AsyncSession, activity_id: int) -> bool:
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
    session: AsyncSession, activity_id: int
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


async def get_by_activity_id(session: AsyncSession, activity_id: str) -> Activity | None:
    """
    Get an activity by activity_id (business identifier).

    Args:
        session: Async database session
        activity_id: Activity identifier (lowercase alphanumeric string)

    Returns:
        Activity instance or None if not found

    Note:
        This function returns the first activity with the given activity_id.
        Since activity_id alone is not unique (the unique constraint is activity_id + platform_id),
        use get_by_activity_id_and_platform_id() to get a specific activity by the unique constraint.
    """
    stmt = select(Activity).where(Activity.activity_id == activity_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_activity_id_and_platform_id(
    session: AsyncSession, activity_id: str, platform_id: int
) -> Activity | None:
    """
    Get an activity by the unique constraint (activity_id, platform_id).

    Args:
        session: Async database session
        activity_id: Activity identifier (lowercase alphanumeric string)
        platform_id: Platform id (foreign key to Platform)

    Returns:
        Activity instance or None if not found
    """
    stmt = select(Activity).where(
        Activity.activity_id == activity_id,
        Activity.platform_id == platform_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_url(
    session: AsyncSession, url: str, offset: int = 0, limit: int | None = None
) -> list[Activity]:
    """
    Get activities by url with pagination.

    Note: URL alone is not unique. Use get_by_unique_constraint() to get a specific activity.

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


async def get_by_unique_constraint(
    session: AsyncSession,
    url: str,
    temporal_start_date_time: datetime,
    temporal_end_date_time: datetime,
) -> Activity | None:
    """
    Get activity by unique constraint (url + temporal dates).

    Args:
        session: Async database session
        url: URL
        temporal_start_date_time: Temporal start datetime
        temporal_end_date_time: Temporal end datetime

    Returns:
        Activity instance or None if not found
    """
    stmt = select(Activity).where(
        Activity.url == url,
        Activity.temporal_start_date_time == temporal_start_date_time,
        Activity.temporal_end_date_time == temporal_end_date_time,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


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
    session: AsyncSession, area_id: int, offset: int = 0, limit: int | None = None
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
            selectinload(Activity.area)  # Eagerly load area relationship
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
