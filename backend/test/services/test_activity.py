"""Tests for Activity business service"""

from datetime import datetime, timedelta

import pytest
from app.services import activity as activity_service
from sqlalchemy.ext.asyncio import AsyncSession

from test.fixtures.factories import (
    ActivityFactory,
    AreaFactory,
    PlatformFactory,
)


@pytest.mark.database
class TestActivityService:
    """Test suite for Activity business service"""

    # Tests for process_activity_list

    async def test_process_activity_list_single_activity(
        self, async_session: AsyncSession
    ):
        """Test processing a single activity"""
        # Arrange
        area = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        activities = [
            {
                "url": "http://example.com/listing-1",
                "address_street": "Damstraat",
                "address_number": "1",
                "address_letter": None,
                "address_addition": None,
                "address_postal_code": "1012JS",
                "address_city": "Amsterdam",
                "registration_number": "REG001",
                "area_id": area.area_id,
                "number_of_guests": 4,
                "country_of_guests": ["NLD", "DEU"],
                "temporal_start_date_time": datetime(2025, 6, 1, 12, 0, 0),
                "temporal_end_date_time": datetime(2025, 6, 8, 12, 0, 0),
                "platform_id_str": "platform01",
                "platform_name": "Booking Platform",
            }
        ]

        # Act
        result = await activity_service.process_activity_list(async_session, activities)

        # Assert
        assert result["succeeded"] == 1
        assert result["failed"] == 0
        count = await activity_service.count_activity(async_session)
        assert count == 1

    async def test_process_activity_list_multiple_activities(
        self, async_session: AsyncSession
    ):
        """Test processing multiple activities"""
        # Arrange
        area = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        activities = [
            {
                "url": f"http://example.com/listing-{i}",
                "address_street": "Damstraat",
                "address_number": str(i),
                "address_letter": None,
                "address_addition": None,
                "address_postal_code": "1012JS",
                "address_city": "Amsterdam",
                "registration_number": f"REG{i:03d}",
                "area_id": area.area_id,
                "number_of_guests": 4,
                "country_of_guests": ["NLD", "DEU"],
                "temporal_start_date_time": datetime(2025, 6, 1, 12, 0, 0)
                + timedelta(hours=i),
                "temporal_end_date_time": datetime(2025, 6, 8, 12, 0, 0)
                + timedelta(hours=i),
                "platform_id_str": "platform01",
                "platform_name": "Booking Platform",
            }
            for i in range(1, 6)
        ]

        # Act
        result = await activity_service.process_activity_list(async_session, activities)

        # Assert
        assert result["succeeded"] == 5
        assert result["failed"] == 0
        count = await activity_service.count_activity(async_session)
        assert count == 5

    async def test_process_activity_list_creates_platform_if_not_exists(
        self, async_session: AsyncSession
    ):
        """Test that platform is created if it doesn't exist"""
        # Arrange
        area = await AreaFactory.create_async(async_session)
        # Need to refresh to get the competent_authority relationship loaded
        await async_session.refresh(area, ["competent_authority"])

        activities = [
            {
                "url": "http://example.com/listing-1",
                "address_street": "Damstraat",
                "address_number": "1",
                "address_letter": None,
                "address_addition": None,
                "address_postal_code": "1012JS",
                "address_city": "Amsterdam",
                "registration_number": "REG001",
                "area_id": area.area_id,
                "number_of_guests": 4,
                "country_of_guests": ["NLD", "DEU"],
                "temporal_start_date_time": datetime(2025, 6, 1, 12, 0, 0),
                "temporal_end_date_time": datetime(2025, 6, 8, 12, 0, 0),
                "platform_id_str": "new_platform",
                "platform_name": "New Platform",
            }
        ]

        # Act
        result = await activity_service.process_activity_list(async_session, activities)

        # Assert - verify success and platform was created
        assert result["succeeded"] == 1
        assert result["failed"] == 0
        from app.crud import platform as platform_crud

        platform = await platform_crud.get_by_platform_id(async_session, "new_platform")
        assert platform is not None
        assert platform.platform_name == "New Platform"

    async def test_process_activity_list_reuses_existing_platform(
        self, async_session: AsyncSession
    ):
        """Test that existing platform is reused if it exists"""
        # Arrange
        area = await AreaFactory.create_async(async_session)
        # Need to refresh to get the competent_authority relationship loaded
        await async_session.refresh(area, ["competent_authority"])

        _existing_platform = await PlatformFactory.create_async(
            async_session,
            platform_id="existing_platform",
            platform_name="Existing Platform",
        )
        activities = [
            {
                "url": "http://example.com/listing-1",
                "address_street": "Damstraat",
                "address_number": "1",
                "address_letter": None,
                "address_addition": None,
                "address_postal_code": "1012JS",
                "address_city": "Amsterdam",
                "registration_number": "REG001",
                "area_id": area.area_id,
                "number_of_guests": 4,
                "country_of_guests": ["NLD", "DEU"],
                "temporal_start_date_time": datetime(2025, 6, 1, 12, 0, 0),
                "temporal_end_date_time": datetime(2025, 6, 8, 12, 0, 0),
                "platform_id_str": "existing_platform",
                "platform_name": "Existing Platform",
            }
        ]

        # Act
        result = await activity_service.process_activity_list(async_session, activities)

        # Assert - verify success and no new platform was created
        assert result["succeeded"] == 1
        assert result["failed"] == 0
        from app.models.platform import Platform
        from sqlalchemy import select

        platforms = await async_session.execute(select(Platform))
        platform_count = len(platforms.scalars().all())
        assert platform_count == 1

    async def test_process_activity_list_with_optional_address_fields(
        self, async_session: AsyncSession
    ):
        """Test processing activities with optional address fields"""
        # Arrange
        area = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        activities = [
            {
                "url": "http://example.com/listing-1",
                "address_street": "Damstraat",
                "address_number": "1",
                "address_letter": "A",
                "address_addition": "2h",
                "address_postal_code": "1012JS",
                "address_city": "Amsterdam",
                "registration_number": "REG001",
                "area_id": area.area_id,
                "number_of_guests": 4,
                "country_of_guests": ["NLD", "DEU"],
                "temporal_start_date_time": datetime(2025, 6, 1, 12, 0, 0),
                "temporal_end_date_time": datetime(2025, 6, 8, 12, 0, 0),
                "platform_id_str": "platform01",
                "platform_name": "Booking Platform",
            }
        ]

        # Act
        result = await activity_service.process_activity_list(async_session, activities)

        # Assert
        assert result["succeeded"] == 1
        assert result["failed"] == 0
        count = await activity_service.count_activity(async_session)
        assert count == 1

    async def test_process_activity_list_raises_error_for_nonexistent_area(
        self, async_session: AsyncSession
    ):
        """Test that processing fails when area doesn't exist"""
        # Arrange
        activities = [
            {
                "url": "http://example.com/listing-1",
                "address_street": "Damstraat",
                "address_number": "1",
                "address_letter": None,
                "address_addition": None,
                "address_postal_code": "1012JS",
                "address_city": "Amsterdam",
                "registration_number": "REG001",
                "area_id": "00000000-0000-0000-0000-000000000000",
                "number_of_guests": 4,
                "country_of_guests": ["NLD", "DEU"],
                "temporal_start_date_time": datetime(2025, 6, 1, 12, 0, 0),
                "temporal_end_date_time": datetime(2025, 6, 8, 12, 0, 0),
                "platform_id_str": "platform01",
                "platform_name": "Booking Platform",
            }
        ]

        # Act
        result = await activity_service.process_activity_list(async_session, activities)

        # Assert - Activity fails validation due to nonexistent area
        assert result["total_processed"] == 1
        assert result["succeeded"] == 0
        assert result["failed"] == 1
        assert len(result["failures"]) == 1
        assert (
            "Area with areaId '00000000-0000-0000-0000-000000000000' not found"
            in result["failures"][0]["errors"][0]["msg"]
        )

    # Tests for count_activity

    async def test_count_activity_empty(self, async_session: AsyncSession):
        """Test counting activities when database is empty"""
        # Act
        result = await activity_service.count_activity(async_session)

        # Assert
        assert result == 0

    async def test_count_activity_single(self, async_session: AsyncSession):
        """Test counting activities with single record"""
        # Arrange
        await ActivityFactory.create_async(async_session)

        # Act
        result = await activity_service.count_activity(async_session)

        # Assert
        assert result == 1

    async def test_count_activity_multiple(self, async_session: AsyncSession):
        """Test counting activities with multiple records"""
        # Arrange
        await ActivityFactory.create_async(async_session)
        await ActivityFactory.create_async(async_session)
        await ActivityFactory.create_async(async_session)

        # Act
        result = await activity_service.count_activity(async_session)

        # Assert
        assert result == 3

    # Tests for count_activity_by_competent_authority

    async def test_count_activity_by_competent_authority_empty(
        self, async_session: AsyncSession
    ):
        """Test counting activities by competent authority when database is empty"""
        # Act
        result = await activity_service.count_activity_by_competent_authority(
            async_session, "0363"
        )

        # Assert
        assert result == 0

    async def test_count_activity_by_competent_authority_no_match(
        self, async_session: AsyncSession
    ):
        """Test counting activities by competent authority with no matching records"""
        # Arrange
        area = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        await ActivityFactory.create_async(async_session, area_id=area.id)

        # Act
        result = await activity_service.count_activity_by_competent_authority(
            async_session, "0599"
        )

        # Assert
        assert result == 0

    async def test_count_activity_by_competent_authority_single_match(
        self, async_session: AsyncSession
    ):
        """Test counting activities by competent authority with single match"""
        # Arrange
        area = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        await ActivityFactory.create_async(async_session, area_id=area.id)

        # Act
        result = await activity_service.count_activity_by_competent_authority(
            async_session, "0363"
        )

        # Assert
        assert result == 1

    async def test_count_activity_by_competent_authority_multiple_matches(
        self, async_session: AsyncSession
    ):
        """Test counting activities by competent authority with multiple matches"""
        # Arrange
        area1 = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        area2 = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        await ActivityFactory.create_async(async_session, area_id=area1.id)
        await ActivityFactory.create_async(async_session, area_id=area1.id)
        await ActivityFactory.create_async(async_session, area_id=area2.id)

        # Act
        result = await activity_service.count_activity_by_competent_authority(
            async_session, "0363"
        )

        # Assert
        assert result == 3

    async def test_count_activity_by_competent_authority_filters_correctly(
        self, async_session: AsyncSession
    ):
        """Test that counting filters by competent authority correctly"""
        # Arrange
        area1 = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        area2 = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0599",
            competent_authority_name="Gemeente Rotterdam",
        )
        await ActivityFactory.create_async(async_session, area_id=area1.id)
        await ActivityFactory.create_async(async_session, area_id=area1.id)
        await ActivityFactory.create_async(async_session, area_id=area2.id)

        # Act
        result1 = await activity_service.count_activity_by_competent_authority(
            async_session, "0363"
        )
        result2 = await activity_service.count_activity_by_competent_authority(
            async_session, "0599"
        )

        # Assert
        assert result1 == 2
        assert result2 == 1

    # Tests for get_activity_list

    async def test_get_activity_list_empty(self, async_session: AsyncSession):
        """Test getting activities list when database is empty"""
        # Act
        result = await activity_service.get_activity_list(async_session, "0363")

        # Assert
        assert result == []

    async def test_get_activity_list_no_match(self, async_session: AsyncSession):
        """Test getting activities list with no matching records"""
        # Arrange
        area = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        await ActivityFactory.create_async(async_session, area_id=area.id)

        # Act
        result = await activity_service.get_activity_list(async_session, "0599")

        # Assert
        assert result == []

    async def test_get_activity_list_single_record(self, async_session: AsyncSession):
        """Test getting activities list with single record"""
        # Arrange
        area = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        platform = await PlatformFactory.create_async(
            async_session,
            platform_id="platform01",
            platform_name="Test Platform",
        )
        _activity = await ActivityFactory.create_async(
            async_session,
            url="http://example.com/listing-1",
            area_id=area.id,
            platform_id=platform.id,
        )

        # Act
        result = await activity_service.get_activity_list(async_session, "0363")

        # Assert
        assert len(result) == 1
        assert result[0]["url"] == "http://example.com/listing-1"
        assert result[0]["platform_id"] == "platform01"
        assert result[0]["platform_name"] == "Test Platform"

    async def test_get_activity_list_response_structure(
        self, async_session: AsyncSession
    ):
        """Test that response structure matches specification"""
        # Arrange
        area = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        platform = await PlatformFactory.create_async(async_session)
        await ActivityFactory.create_async(
            async_session, area_id=area.id, platform_id=platform.id
        )

        # Act
        result = await activity_service.get_activity_list(async_session, "0363")

        # Assert
        assert len(result) == 1
        activity_dict = result[0]

        # Verify all required keys are present
        required_keys = {
            "activity_id",
            "activity_name",
            "platform_id",
            "platform_name",
            "url",
            "address_street",
            "address_number",
            "address_letter",
            "address_addition",
            "address_postal_code",
            "address_city",
            "registration_number",
            "area_id",
            "number_of_guests",
            "country_of_guests",
            "temporal_start_date_time",
            "temporal_end_date_time",
            "created_at",
        }
        assert set(activity_dict.keys()) == required_keys

        # Verify types
        assert isinstance(activity_dict["activity_id"], str)
        assert len(activity_dict["activity_id"]) == 36  # Functional ID
        assert isinstance(
            activity_dict["activity_name"], (str, type(None))
        )  # Optional field
        assert isinstance(activity_dict["platform_id"], str)
        assert isinstance(activity_dict["platform_name"], str)
        assert isinstance(activity_dict["url"], str)
        assert isinstance(activity_dict["address_street"], str)
        assert isinstance(activity_dict["address_number"], int)
        assert isinstance(activity_dict["address_postal_code"], str)
        assert isinstance(activity_dict["address_city"], str)
        assert isinstance(activity_dict["registration_number"], str)
        assert isinstance(activity_dict["area_id"], str)  # Functional ID
        assert len(activity_dict["area_id"]) == 36  # RFC 9562 UUID format
        assert isinstance(activity_dict["number_of_guests"], int)
        assert isinstance(activity_dict["country_of_guests"], list)
        assert isinstance(activity_dict["temporal_start_date_time"], datetime)
        assert isinstance(activity_dict["temporal_end_date_time"], datetime)
        assert isinstance(activity_dict["platform_id"], str)
        assert isinstance(activity_dict["platform_name"], str)
        assert isinstance(activity_dict["created_at"], datetime)

    async def test_get_activity_list_multiple_records(
        self, async_session: AsyncSession
    ):
        """Test getting activities list with multiple records"""
        # Arrange
        area = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        platform = await PlatformFactory.create_async(async_session)
        await ActivityFactory.create_async(
            async_session, area_id=area.id, platform_id=platform.id
        )
        await ActivityFactory.create_async(
            async_session, area_id=area.id, platform_id=platform.id
        )
        await ActivityFactory.create_async(
            async_session, area_id=area.id, platform_id=platform.id
        )

        # Act
        result = await activity_service.get_activity_list(async_session, "0363")

        # Assert
        assert len(result) == 3

    async def test_get_activity_list_filters_by_competent_authority(
        self, async_session: AsyncSession
    ):
        """Test that listing filters by competent authority correctly"""
        # Arrange
        area1 = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        area2 = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0599",
            competent_authority_name="Gemeente Rotterdam",
        )
        platform = await PlatformFactory.create_async(async_session)
        await ActivityFactory.create_async(
            async_session, area_id=area1.id, platform_id=platform.id
        )
        await ActivityFactory.create_async(
            async_session, area_id=area1.id, platform_id=platform.id
        )
        await ActivityFactory.create_async(
            async_session, area_id=area2.id, platform_id=platform.id
        )

        # Act
        result1 = await activity_service.get_activity_list(async_session, "0363")
        result2 = await activity_service.get_activity_list(async_session, "0599")

        # Assert
        assert len(result1) == 2
        assert len(result2) == 1

    async def test_get_activity_list_with_pagination_offset(
        self, async_session: AsyncSession
    ):
        """Test getting activities list with offset pagination"""
        # Arrange
        area = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        platform = await PlatformFactory.create_async(async_session)
        await ActivityFactory.create_async(
            async_session, area_id=area.id, platform_id=platform.id
        )
        await ActivityFactory.create_async(
            async_session, area_id=area.id, platform_id=platform.id
        )
        await ActivityFactory.create_async(
            async_session, area_id=area.id, platform_id=platform.id
        )
        await ActivityFactory.create_async(
            async_session, area_id=area.id, platform_id=platform.id
        )

        # Act
        result = await activity_service.get_activity_list(
            async_session, "0363", offset=2
        )

        # Assert
        assert len(result) == 2

    async def test_get_activity_list_with_pagination_limit(
        self, async_session: AsyncSession
    ):
        """Test getting activities list with limit pagination"""
        # Arrange
        area = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        platform = await PlatformFactory.create_async(async_session)
        await ActivityFactory.create_async(
            async_session, area_id=area.id, platform_id=platform.id
        )
        await ActivityFactory.create_async(
            async_session, area_id=area.id, platform_id=platform.id
        )
        await ActivityFactory.create_async(
            async_session, area_id=area.id, platform_id=platform.id
        )

        # Act
        result = await activity_service.get_activity_list(
            async_session, "0363", limit=2
        )

        # Assert
        assert len(result) == 2

    async def test_get_activity_list_with_pagination_offset_and_limit(
        self, async_session: AsyncSession
    ):
        """Test getting activities list with both offset and limit pagination"""
        # Arrange
        area = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        platform = await PlatformFactory.create_async(async_session)
        await ActivityFactory.create_async(
            async_session, area_id=area.id, platform_id=platform.id
        )
        await ActivityFactory.create_async(
            async_session, area_id=area.id, platform_id=platform.id
        )
        await ActivityFactory.create_async(
            async_session, area_id=area.id, platform_id=platform.id
        )
        await ActivityFactory.create_async(
            async_session, area_id=area.id, platform_id=platform.id
        )
        await ActivityFactory.create_async(
            async_session, area_id=area.id, platform_id=platform.id
        )

        # Act
        result = await activity_service.get_activity_list(
            async_session, "0363", offset=1, limit=2
        )

        # Assert
        assert len(result) == 2

    async def test_get_activity_list_pagination_offset_beyond_results(
        self, async_session: AsyncSession
    ):
        """Test pagination with offset beyond available results"""
        # Arrange
        area = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        platform = await PlatformFactory.create_async(async_session)
        await ActivityFactory.create_async(
            async_session, area_id=area.id, platform_id=platform.id
        )
        await ActivityFactory.create_async(
            async_session, area_id=area.id, platform_id=platform.id
        )

        # Act
        result = await activity_service.get_activity_list(
            async_session, "0363", offset=10
        )

        # Assert
        assert len(result) == 0

    async def test_get_activity_list_includes_platform_info(
        self, async_session: AsyncSession
    ):
        """Test that activities list includes platform information via relationship"""
        # Arrange
        area = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        platform = await PlatformFactory.create_async(
            async_session,
            platform_id="platform99",
            platform_name="Super Platform",
        )
        await ActivityFactory.create_async(
            async_session,
            url="http://example.com/test",
            area_id=area.id,
            platform_id=platform.id,
        )

        # Act
        result = await activity_service.get_activity_list(async_session, "0363")

        # Assert
        assert len(result) == 1
        assert result[0]["platform_id"] == "platform99"
        assert result[0]["platform_name"] == "Super Platform"

    async def test_process_activity_list_with_activity_id(
        self, async_session: AsyncSession
    ):
        """Test processing activity with optional activity_id provided"""
        # Arrange
        area = await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        activities = [
            {
                "activity_id": "550e8400-e29b-41d4-a716-446655440123",
                "activity_name": "Custom Activity Name",
                "url": "http://example.com/listing-with-id",
                "address_street": "Damstraat",
                "address_number": "1",
                "address_letter": None,
                "address_addition": None,
                "address_postal_code": "1012JS",
                "address_city": "Amsterdam",
                "registration_number": "REG001",
                "area_id": area.area_id,
                "number_of_guests": 4,
                "country_of_guests": ["NLD", "DEU"],
                "temporal_start_date_time": datetime(2025, 6, 1, 12, 0, 0),
                "temporal_end_date_time": datetime(2025, 6, 8, 12, 0, 0),
                "platform_id_str": "platform01",
                "platform_name": "Booking Platform",
            }
        ]

        # Act
        result = await activity_service.process_activity_list(async_session, activities)

        # Assert
        assert result["succeeded"] == 1
        assert result["failed"] == 0
        count = await activity_service.count_activity(async_session)
        assert count == 1

        # Verify activity was created with the specified activity_id and activity_name
        from app.crud import activity as activity_crud

        saved = await activity_crud.get_by_url(
            async_session, "http://example.com/listing-with-id"
        )
        assert len(saved) == 1
        assert saved[0].activity_id == "550e8400-e29b-41d4-a716-446655440123"
        assert saved[0].activity_name == "Custom Activity Name"
