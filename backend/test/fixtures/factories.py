"""Factory definitions for test data generation using factory_boy."""

from datetime import datetime, timedelta

import factory
from app.models.activity import Activity
from app.models.address import Address
from app.models.area import Area
from app.models.competent_authority import CompetentAuthority
from app.models.platform import Platform
from app.models.temporal import Temporal
from factory import Faker
from sqlalchemy.ext.asyncio import AsyncSession


class AsyncSQLAlchemyFactory(factory.Factory):
    """Base factory for async SQLAlchemy models."""

    class Meta:
        abstract = True

    @classmethod
    async def create_async(cls, session: AsyncSession, **kwargs):
        """Create model instance asynchronously."""
        obj = cls.build(**kwargs)
        session.add(obj)
        await session.flush()
        await session.refresh(obj)
        return obj


class CompetentAuthorityFactory(AsyncSQLAlchemyFactory):
    """Factory for CompetentAuthority model."""

    class Meta:
        model = CompetentAuthority

    competent_authority_id = factory.Sequence(
        lambda n: f"{n:04d}"[:64]
    )  # "0001", "0002", etc.
    competent_authority_name = Faker("company")


class AreaFactory(AsyncSQLAlchemyFactory):
    """Factory for Area model."""

    class Meta:
        model = Area

    area_id = factory.Sequence(
        lambda n: f"area{n:016x}"[:20]
    )  # Lowercase hex, e.g. "area000000000000001"
    filename = Faker("file_name", extension="geojson")
    filedata = Faker("binary", length=100)
    # Foreign key to CompetentAuthority - defaults to creating one

    @classmethod
    async def create_async(cls, session: AsyncSession, **kwargs):
        """Create model instance asynchronously."""
        from app.crud import competent_authority as ca_crud

        # Extract competent authority attributes if provided
        ca_id = kwargs.pop("competent_authority_id", None)
        ca_name = kwargs.pop("competent_authority_name", None)

        # If competent_authority_id is provided as a string (the business key, not the database ID)
        # or if competent_authority_name is provided, find or create a CompetentAuthority
        if (isinstance(ca_id, str) and not ca_id.isdigit()) or ca_name:
            # Try to find existing CompetentAuthority by competent_authority_id
            if ca_id:
                existing = await ca_crud.get_by_competent_authority_id(session, ca_id)
                if existing:
                    ca = existing[0]  # get_by_competent_authority_id returns a list
                else:
                    ca = await CompetentAuthorityFactory.create_async(
                        session,
                        competent_authority_id=ca_id,
                        competent_authority_name=ca_name if ca_name else None,
                    )
            else:
                # No ca_id provided, just create a new one
                ca = await CompetentAuthorityFactory.create_async(
                    session,
                    competent_authority_name=ca_name,
                )
            kwargs["competent_authority_id"] = ca.id
        elif ca_id is None:
            # Create a default CompetentAuthority if not provided at all
            ca = await CompetentAuthorityFactory.create_async(session)
            kwargs["competent_authority_id"] = ca.id
        else:
            # Use the provided database ID directly
            kwargs["competent_authority_id"] = ca_id

        return await super().create_async(session, **kwargs)


class PlatformFactory(AsyncSQLAlchemyFactory):
    """Factory for Platform model."""

    class Meta:
        model = Platform

    platform_id = factory.Sequence(
        lambda n: f"platform{n:02d}"
    )  # "platform01", "platform02", etc.
    platform_name = Faker("company")


class AddressFactory(factory.Factory):
    """Factory for Address composite (not a SQLAlchemy model)."""

    class Meta:
        model = Address

    street = Faker("street_name")
    number = Faker("building_number")
    letter = factory.Sequence(lambda n: chr(97 + (n % 26)))  # a, b, c, ...
    addition = factory.Sequence(lambda n: f"{n}h")
    postal_code = Faker("postcode")
    city = Faker("city")


class TemporalFactory(factory.Factory):
    """Factory for Temporal composite (not a SQLAlchemy model)."""

    class Meta:
        model = Temporal

    # Use 2025 as minimum year to satisfy the year >= 2025 constraint
    start_date_time = factory.LazyFunction(lambda: datetime(2025, 6, 1, 12, 0, 0))
    end_date_time = factory.LazyFunction(
        lambda: datetime(2025, 6, 1, 12, 0, 0) + timedelta(days=7)
    )


class ActivityFactory(AsyncSQLAlchemyFactory):
    """Factory for Activity model.

    Note: The combination of url, temporal_start_date_time, and temporal_end_date_time must be unique.
    The factory uses sequences to ensure uniqueness.
    """

    class Meta:
        model = Activity

    activity_id = factory.Sequence(
        lambda n: f"activity{n:016x}"[:20]
    )  # Lowercase hex, e.g. "activity00000000001"
    url = factory.Sequence(lambda n: f"http://example.com/listing-{n}")
    # Address composite fields (street, number, postal_code, city are mandatory)
    address_street = Faker("street_name")
    address_number = Faker("building_number")
    address_letter = factory.Sequence(
        lambda n: chr(97 + (n % 26)) if n % 3 == 0 else None
    )
    address_addition = factory.Sequence(lambda n: f"{n}h" if n % 2 == 0 else None)
    address_postal_code = Faker("postcode")
    address_city = Faker("city")
    registration_number = factory.Sequence(lambda n: f"REG{n:06d}")
    # Foreign key to Area - defaults to creating one
    # Guest information
    number_of_guests = Faker("random_int", min=1, max=8)
    country_of_guests = factory.LazyFunction(
        lambda: ["NLD", "DEU", "BEL"]
    )  # ISO 3166-1 alpha-3
    # Temporal composite fields (both mandatory)
    # Use sequence to ensure unique combinations with URL
    # Start from 2025 to satisfy the year >= 2025 constraint
    temporal_start_date_time = factory.Sequence(
        lambda n: datetime(2025, 6, 1, 12, 0, 0) + timedelta(hours=n)
    )
    temporal_end_date_time = factory.Sequence(
        lambda n: datetime(2025, 6, 1, 12, 0, 0) + timedelta(hours=n, days=7)
    )
    # Foreign key to Platform - defaults to creating one

    @classmethod
    async def create_async(cls, session: AsyncSession, **kwargs):
        """Create model instance asynchronously."""
        # Create Area if not provided
        if "area_id" not in kwargs:
            area = await AreaFactory.create_async(session)
            kwargs["area_id"] = area.id

        # Create Platform if not provided
        if "platform_id" not in kwargs:
            platform = await PlatformFactory.create_async(session)
            kwargs["platform_id"] = platform.id

        return await super().create_async(session, **kwargs)
