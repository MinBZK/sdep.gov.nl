"""Tests for ActivityData CRUD operations."""

from datetime import datetime

import pytest
from app.crud import activity_data
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from test.fixtures.factories import ActivityDataFactory, AreaFactory, PlatformFactory


@pytest.mark.database
class TestActivityDataCRUD:
    """Test suite for ActivityData CRUD operations."""

    async def test_create_activity_data(self, async_session: AsyncSession):
        """Test creating a new activity data."""
        # Arrange
        area = await AreaFactory.create_async(async_session)
        platform = await PlatformFactory.create_async(async_session)
        url = "http://example.com/listing-1"
        address_street = "Main Street"
        address_number = 123
        address_postal_code = "1234AB"
        address_city = "Amsterdam"
        registration_number = "REG123456"
        number_of_guests = 4
        country_of_guests = ["NLD", "DEU"]
        temporal_start = datetime(2025, 6, 1, 12, 0, 0)
        temporal_end = datetime(2025, 6, 8, 12, 0, 0)

        # Act
        result = await activity_data.create(
            session=async_session,
            url=url,
            address_street=address_street,
            address_number=address_number,
            address_letter=None,
            address_addition=None,
            address_postal_code=address_postal_code,
            address_city=address_city,
            registration_number=registration_number,
            area_id=area.id,
            number_of_guests=number_of_guests,
            country_of_guests=country_of_guests,
            temporal_start_date_time=temporal_start,
            temporal_end_date_time=temporal_end,
            platform_id=platform.id,
        )

        # Assert
        assert result.id is not None
        assert result.url == url
        assert result.address_street == address_street
        assert result.address_number == address_number
        assert result.address_letter is None
        assert result.address_addition is None
        assert result.address_postal_code == address_postal_code
        assert result.address_city == address_city
        assert result.registration_number == registration_number
        assert result.area_id == area.id
        assert result.number_of_guests == number_of_guests
        assert result.country_of_guests == country_of_guests
        assert result.temporal_start_date_time == temporal_start
        assert result.temporal_end_date_time == temporal_end
        assert result.platform_id == platform.id
        assert result.created_at is not None
        assert isinstance(result.created_at, datetime)

    async def test_create_activity_data_with_optional_fields(
        self, async_session: AsyncSession
    ):
        """Test creating activity data with optional address fields."""
        # Arrange
        area = await AreaFactory.create_async(async_session)
        platform = await PlatformFactory.create_async(async_session)
        address_letter = "A"
        address_addition = "1hoog"

        # Act
        result = await activity_data.create(
            session=async_session,
            url="http://example.com/listing-2",
            address_street="Side Street",
            address_number=456,
            address_letter=address_letter,
            address_addition=address_addition,
            address_postal_code="5678CD",
            address_city="Rotterdam",
            registration_number="REG789012",
            area_id=area.id,
            number_of_guests=2,
            country_of_guests=["BEL"],
            temporal_start_date_time=datetime(2025, 7, 1, 14, 0, 0),
            temporal_end_date_time=datetime(2025, 7, 5, 14, 0, 0),
            platform_id=platform.id,
        )

        # Assert
        assert result.address_letter == address_letter
        assert result.address_addition == address_addition

    async def test_create_activity_data_with_duplicate_unique_constraint(
        self, async_session: AsyncSession
    ):
        """Test that duplicate url+temporal combination raises IntegrityError."""
        # Arrange
        area = await AreaFactory.create_async(async_session)
        platform = await PlatformFactory.create_async(async_session)
        url = "http://example.com/same-listing"
        temporal_start = datetime(2025, 8, 1, 10, 0, 0)
        temporal_end = datetime(2025, 8, 7, 10, 0, 0)

        # Create first activity data
        await activity_data.create(
            session=async_session,
            url=url,
            address_street="Test Street",
            address_number=100,
            address_letter=None,
            address_addition=None,
            address_postal_code="1111AA",
            address_city="TestCity",
            registration_number="REG111",
            area_id=area.id,
            number_of_guests=3,
            country_of_guests=["NLD"],
            temporal_start_date_time=temporal_start,
            temporal_end_date_time=temporal_end,
            platform_id=platform.id,
        )
        await async_session.flush()

        # Act & Assert - Try to create duplicate
        with pytest.raises(IntegrityError):
            await activity_data.create(
                session=async_session,
                url=url,
                address_street="Different Street",
                address_number=200,
                address_letter=None,
                address_addition=None,
                address_postal_code="2222BB",
                address_city="OtherCity",
                registration_number="REG222",
                area_id=area.id,
                number_of_guests=5,
                country_of_guests=["DEU"],
                temporal_start_date_time=temporal_start,
                temporal_end_date_time=temporal_end,
                platform_id=platform.id,
            )
            await async_session.flush()

    async def test_update_activity_data(self, async_session: AsyncSession):
        """Test updating an existing activity data."""
        # Arrange
        ad = await ActivityDataFactory.create_async(async_session)
        new_url = "http://example.com/updated-listing"
        new_registration_number = "REG999999"

        # Act
        result = await activity_data.update(
            async_session,
            ad.id,
            url=new_url,
            registration_number=new_registration_number,
        )

        # Assert
        assert result is not None
        assert result.id == ad.id
        assert result.url == new_url
        assert result.registration_number == new_registration_number

    async def test_update_activity_data_address_fields(
        self, async_session: AsyncSession
    ):
        """Test updating address fields of activity data."""
        # Arrange
        ad = await ActivityDataFactory.create_async(async_session)
        new_street = "New Street Name"
        new_number = 999
        new_postal_code = "9999ZZ"
        new_city = "New City"

        # Act
        result = await activity_data.update(
            async_session,
            ad.id,
            address_street=new_street,
            address_number=new_number,
            address_postal_code=new_postal_code,
            address_city=new_city,
        )

        # Assert
        assert result is not None
        assert result.address_street == new_street
        assert result.address_number == new_number
        assert result.address_postal_code == new_postal_code
        assert result.address_city == new_city

    async def test_update_activity_data_temporal_fields(
        self, async_session: AsyncSession
    ):
        """Test updating temporal fields of activity data."""
        # Arrange
        ad = await ActivityDataFactory.create_async(async_session)
        new_start = datetime(2025, 12, 1, 15, 0, 0)
        new_end = datetime(2025, 12, 10, 15, 0, 0)

        # Act
        result = await activity_data.update(
            async_session,
            ad.id,
            temporal_start_date_time=new_start,
            temporal_end_date_time=new_end,
        )

        # Assert
        assert result is not None
        assert result.temporal_start_date_time == new_start
        assert result.temporal_end_date_time == new_end

    async def test_update_activity_data_not_found(self, async_session: AsyncSession):
        """Test updating a non-existent activity data."""
        # Act
        result = await activity_data.update(
            async_session, 99999, url="http://example.com/nonexistent"
        )

        # Assert
        assert result is None

    async def test_delete_activity_data(self, async_session: AsyncSession):
        """Test deleting an existing activity data."""
        # Arrange
        ad = await ActivityDataFactory.create_async(async_session)

        # Act
        result = await activity_data.delete(async_session, ad.id)

        # Assert
        assert result is True
        retrieved = await activity_data.get_by_id(async_session, ad.id)
        assert retrieved is None

    async def test_delete_activity_data_not_found(self, async_session: AsyncSession):
        """Test deleting a non-existent activity data."""
        # Act
        result = await activity_data.delete(async_session, 99999)

        # Assert
        assert result is False

    async def test_exists_activity_data(self, async_session: AsyncSession):
        """Test checking if activity data exists."""
        # Arrange
        ad = await ActivityDataFactory.create_async(async_session)

        # Act
        exists = await activity_data.exists(async_session, ad.id)
        not_exists = await activity_data.exists(async_session, 99999)

        # Assert
        assert exists is True
        assert not_exists is False

    async def test_count_activity_data(self, async_session: AsyncSession):
        """Test counting activity data."""
        # Arrange
        await ActivityDataFactory.create_async(async_session)
        await ActivityDataFactory.create_async(async_session)
        await ActivityDataFactory.create_async(async_session)

        # Act
        total = await activity_data.count(async_session)

        # Assert
        assert total == 3

    async def test_get_all_activity_data(self, async_session: AsyncSession):
        """Test getting all activity data."""
        # Arrange
        await ActivityDataFactory.create_async(async_session)
        await ActivityDataFactory.create_async(async_session)

        # Act
        results = await activity_data.get_all(async_session)

        # Assert
        assert len(results) == 2

    async def test_get_all_activity_data_with_pagination(
        self, async_session: AsyncSession
    ):
        """Test getting activity data with pagination."""
        # Arrange
        for _ in range(5):
            await ActivityDataFactory.create_async(async_session)

        # Act
        page1 = await activity_data.get_all(async_session, offset=0, limit=2)
        page2 = await activity_data.get_all(async_session, offset=2, limit=2)
        page3 = await activity_data.get_all(async_session, offset=4, limit=2)

        # Assert
        assert len(page1) == 2
        assert len(page2) == 2
        assert len(page3) == 1

    async def test_get_by_id(self, async_session: AsyncSession):
        """Test getting activity data by id."""
        # Arrange
        ad = await ActivityDataFactory.create_async(async_session)

        # Act
        result = await activity_data.get_by_id(async_session, ad.id)

        # Assert
        assert result is not None
        assert result.id == ad.id
        assert result.url == ad.url

    async def test_get_by_id_not_found(self, async_session: AsyncSession):
        """Test getting a non-existent activity data by id."""
        # Act
        result = await activity_data.get_by_id(async_session, 99999)

        # Assert
        assert result is None

    async def test_get_by_url(self, async_session: AsyncSession):
        """Test getting activity data by url."""
        # Arrange
        test_url = "http://example.com/special-listing"
        ad = await ActivityDataFactory.create_async(async_session, url=test_url)

        # Act
        results = await activity_data.get_by_url(async_session, test_url)

        # Assert
        assert len(results) == 1
        assert results[0].id == ad.id
        assert results[0].url == test_url

    async def test_get_by_url_multiple_results(self, async_session: AsyncSession):
        """Test getting multiple activity data with same url but different temporal."""
        # Arrange
        test_url = "http://example.com/multi-listing"
        await ActivityDataFactory.create_async(
            async_session,
            url=test_url,
            temporal_start_date_time=datetime(2025, 6, 1, 12, 0, 0),
            temporal_end_date_time=datetime(2025, 6, 8, 12, 0, 0),
        )
        await ActivityDataFactory.create_async(
            async_session,
            url=test_url,
            temporal_start_date_time=datetime(2025, 7, 1, 12, 0, 0),
            temporal_end_date_time=datetime(2025, 7, 8, 12, 0, 0),
        )

        # Act
        results = await activity_data.get_by_url(async_session, test_url)

        # Assert
        assert len(results) == 2
        assert all(r.url == test_url for r in results)

    async def test_get_by_url_not_found(self, async_session: AsyncSession):
        """Test getting activity data by non-existent url."""
        # Act
        results = await activity_data.get_by_url(
            async_session, "http://example.com/nonexistent"
        )

        # Assert
        assert len(results) == 0

    async def test_get_by_unique_constraint(self, async_session: AsyncSession):
        """Test getting activity data by unique constraint."""
        # Arrange
        test_url = "http://example.com/unique-listing"
        test_start = datetime(2025, 9, 1, 10, 0, 0)
        test_end = datetime(2025, 9, 7, 10, 0, 0)
        ad = await ActivityDataFactory.create_async(
            async_session,
            url=test_url,
            temporal_start_date_time=test_start,
            temporal_end_date_time=test_end,
        )

        # Act
        result = await activity_data.get_by_unique_constraint(
            async_session, test_url, test_start, test_end
        )

        # Assert
        assert result is not None
        assert result.id == ad.id
        assert result.url == test_url

    async def test_get_by_unique_constraint_not_found(
        self, async_session: AsyncSession
    ):
        """Test getting activity data by non-existent unique constraint."""
        # Act
        result = await activity_data.get_by_unique_constraint(
            async_session,
            "http://example.com/nonexistent",
            datetime(2025, 10, 1, 10, 0, 0),
            datetime(2025, 10, 7, 10, 0, 0),
        )

        # Assert
        assert result is None

    async def test_get_by_registration_number(self, async_session: AsyncSession):
        """Test getting activity data by registration number."""
        # Arrange
        test_reg_number = "REG555555"
        ad = await ActivityDataFactory.create_async(
            async_session, registration_number=test_reg_number
        )

        # Act
        results = await activity_data.get_by_registration_number(
            async_session, test_reg_number
        )

        # Assert
        assert len(results) == 1
        assert results[0].id == ad.id
        assert results[0].registration_number == test_reg_number

    async def test_get_by_registration_number_not_found(
        self, async_session: AsyncSession
    ):
        """Test getting activity data by non-existent registration number."""
        # Act
        results = await activity_data.get_by_registration_number(
            async_session, "NONEXISTENT"
        )

        # Assert
        assert len(results) == 0

    async def test_get_by_platform_id(self, async_session: AsyncSession):
        """Test getting activity data by platform_id (foreign key)."""
        # Arrange
        platform = await PlatformFactory.create_async(async_session)
        ad1 = await ActivityDataFactory.create_async(
            async_session, platform_id=platform.id
        )
        ad2 = await ActivityDataFactory.create_async(
            async_session, platform_id=platform.id
        )

        # Act
        results = await activity_data.get_by_platform_id(async_session, platform.id)

        # Assert
        assert len(results) == 2
        assert all(r.platform_id == platform.id for r in results)

    async def test_get_by_platform_id_not_found(self, async_session: AsyncSession):
        """Test getting activity data by non-existent platform_id."""
        # Act
        results = await activity_data.get_by_platform_id(async_session, 99999)

        # Assert
        assert len(results) == 0

    async def test_get_by_area_id(self, async_session: AsyncSession):
        """Test getting activity data by area_id (foreign key)."""
        # Arrange
        area = await AreaFactory.create_async(async_session)
        ad1 = await ActivityDataFactory.create_async(async_session, area_id=area.id)
        ad2 = await ActivityDataFactory.create_async(async_session, area_id=area.id)

        # Act
        results = await activity_data.get_by_area_id(async_session, area.id)

        # Assert
        assert len(results) == 2
        assert all(r.area_id == area.id for r in results)

    async def test_get_by_area_id_not_found(self, async_session: AsyncSession):
        """Test getting activity data by non-existent area_id."""
        # Act
        results = await activity_data.get_by_area_id(async_session, 99999)

        # Assert
        assert len(results) == 0

    async def test_get_by_competent_authority_id(self, async_session: AsyncSession):
        """Test getting activity data by competent_authority_id."""
        # Arrange
        area = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        ad = await ActivityDataFactory.create_async(async_session, area_id=area.id)

        # Act
        results = await activity_data.get_by_competent_authority_id(
            async_session, "0363"
        )

        # Assert
        assert len(results) == 1
        assert results[0].id == ad.id

    async def test_get_by_competent_authority_id_not_found(
        self, async_session: AsyncSession
    ):
        """Test getting activity data by non-existent competent_authority_id."""
        # Act
        results = await activity_data.get_by_competent_authority_id(
            async_session, "9999"
        )

        # Assert
        assert len(results) == 0

    async def test_count_by_competent_authority_id(self, async_session: AsyncSession):
        """Test counting activity data by competent_authority_id."""
        # Arrange
        area = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0518",
            competent_authority_name="Gemeente Den Haag",
        )
        await ActivityDataFactory.create_async(async_session, area_id=area.id)
        await ActivityDataFactory.create_async(async_session, area_id=area.id)
        await ActivityDataFactory.create_async(async_session, area_id=area.id)

        # Act
        total = await activity_data.count_by_competent_authority_id(
            async_session, "0518"
        )

        # Assert
        assert total == 3

    async def test_count_by_competent_authority_id_not_found(
        self, async_session: AsyncSession
    ):
        """Test counting activity data by non-existent competent_authority_id."""
        # Act
        total = await activity_data.count_by_competent_authority_id(
            async_session, "9999"
        )

        # Assert
        assert total == 0
