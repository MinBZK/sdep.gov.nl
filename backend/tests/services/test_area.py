"""Tests for Area business service"""

import pytest
from app.services import area
from sqlalchemy.ext.asyncio import AsyncSession

from tests.fixtures.factories import AreaFactory


@pytest.mark.database
class TestAreaService:
    """Test suite for Area business service"""

    async def test_get_areas_empty(self, async_session: AsyncSession):
        """Test getting areas when database is empty"""
        # Act
        result = await area.get_areas(async_session)

        # Assert
        assert result == []

    async def test_get_areas_single_area(self, async_session: AsyncSession):
        """Test getting a single area"""
        # Arrange
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )

        # Act
        result = await area.get_areas(async_session)

        # Assert
        assert len(result) == 1
        assert result[0]["competentAuthorityId"] == "0363"
        assert result[0]["competentAuthorityName"] == "Gemeente Amsterdam"
        assert "areaId" in result[0]
        assert "filename" in result[0]
        assert "createdAt" in result[0]

    async def test_get_areas_multiple_areas(self, async_session: AsyncSession):
        """Test getting multiple areas"""
        # Arrange
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0599",
            competent_authority_name="Gemeente Rotterdam",
        )
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0518",
            competent_authority_name="Gemeente Den Haag",
        )

        # Act
        result = await area.get_areas(async_session)

        # Assert
        assert len(result) == 3

        # Find each area in results
        area1 = next((a for a in result if a["competentAuthorityId"] == "0363"), None)
        area2 = next((a for a in result if a["competentAuthorityId"] == "0599"), None)
        area3 = next((a for a in result if a["competentAuthorityId"] == "0518"), None)

        assert area1 is not None
        assert area1["competentAuthorityName"] == "Gemeente Amsterdam"

        assert area2 is not None
        assert area2["competentAuthorityName"] == "Gemeente Rotterdam"

        assert area3 is not None
        assert area3["competentAuthorityName"] == "Gemeente Den Haag"

    async def test_get_areas_multiple_areas_same_authority(
        self, async_session: AsyncSession
    ):
        """Test getting multiple areas from the same competent authority"""
        # Arrange
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0363",
            competent_authority_name="Gemeente Amsterdam",
        )

        # Act
        result = await area.get_areas(async_session)

        # Assert
        assert len(result) == 3
        for area_dict in result:
            assert area_dict["competentAuthorityId"] == "0363"
            assert area_dict["competentAuthorityName"] == "Gemeente Amsterdam"

    async def test_get_areas_response_structure(self, async_session: AsyncSession):
        """Test that response structure matches specification"""
        # Arrange
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="TEST",
            competent_authority_name="Test Authority",
        )

        # Act
        result = await area.get_areas(async_session)

        # Assert
        assert len(result) == 1
        area_dict = result[0]

        # Verify all required keys are present
        assert "areaId" in area_dict
        assert "areaName" in area_dict
        assert "competentAuthorityId" in area_dict
        assert "competentAuthorityName" in area_dict
        assert "filename" in area_dict
        assert "createdAt" in area_dict

        # Verify no extra keys
        assert set(area_dict.keys()) == {
            "areaId",
            "areaName",
            "competentAuthorityId",
            "competentAuthorityName",
            "filename",
            "createdAt",
        }

        # Verify types
        assert isinstance(area_dict["areaId"], str)
        assert len(area_dict["areaId"]) == 36  # UUID format
        assert isinstance(area_dict["areaName"], str) or area_dict["areaName"] is None
        assert isinstance(area_dict["competentAuthorityId"], str)
        assert isinstance(area_dict["competentAuthorityName"], str)
        assert isinstance(area_dict["filename"], str)

    async def test_get_areas_with_pagination_offset(self, async_session: AsyncSession):
        """Test getting areas with offset pagination"""
        # Arrange
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0001",
            competent_authority_name="CA 1",
        )
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0002",
            competent_authority_name="CA 2",
        )
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0003",
            competent_authority_name="CA 3",
        )
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0004",
            competent_authority_name="CA 4",
        )

        # Act
        result = await area.get_areas(async_session, offset=2)

        # Assert
        assert len(result) == 2
        ids = {area["competentAuthorityId"] for area in result}
        assert "0003" in ids
        assert "0004" in ids

    async def test_get_areas_with_pagination_limit(self, async_session: AsyncSession):
        """Test getting areas with limit pagination"""
        # Arrange
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0001",
            competent_authority_name="CA 1",
        )
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0002",
            competent_authority_name="CA 2",
        )
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0003",
            competent_authority_name="CA 3",
        )

        # Act
        result = await area.get_areas(async_session, limit=2)

        # Assert
        assert len(result) == 2

    async def test_get_areas_with_pagination_offset_and_limit(
        self, async_session: AsyncSession
    ):
        """Test getting areas with both offset and limit pagination"""
        # Arrange
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0001",
            competent_authority_name="CA 1",
        )
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0002",
            competent_authority_name="CA 2",
        )
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0003",
            competent_authority_name="CA 3",
        )
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0004",
            competent_authority_name="CA 4",
        )
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0005",
            competent_authority_name="CA 5",
        )

        # Act
        result = await area.get_areas(async_session, offset=1, limit=2)

        # Assert
        assert len(result) == 2
        ids = {area["competentAuthorityId"] for area in result}
        assert "0002" in ids
        assert "0003" in ids

    async def test_get_areas_pagination_offset_beyond_results(
        self, async_session: AsyncSession
    ):
        """Test pagination with offset beyond available results"""
        # Arrange
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0001",
            competent_authority_name="CA 1",
        )
        await AreaFactory.create_async(
            async_session,
            competent_authority_id="0002",
            competent_authority_name="CA 2",
        )

        # Act
        result = await area.get_areas(async_session, offset=10)

        # Assert
        assert len(result) == 0

    async def test_count_areas_empty(self, async_session: AsyncSession):
        """Test counting areas when database is empty"""
        # Act
        result = await area.count_areas(async_session)

        # Assert
        assert result == 0

    async def test_count_areas_single(self, async_session: AsyncSession):
        """Test counting areas with single area"""
        # Arrange
        await AreaFactory.create_async(async_session)

        # Act
        result = await area.count_areas(async_session)

        # Assert
        assert result == 1

    async def test_count_areas_multiple(self, async_session: AsyncSession):
        """Test counting areas with multiple areas"""
        # Arrange
        await AreaFactory.create_async(async_session)
        await AreaFactory.create_async(async_session)
        await AreaFactory.create_async(async_session)
        await AreaFactory.create_async(async_session)
        await AreaFactory.create_async(async_session)

        # Act
        result = await area.count_areas(async_session)

        # Assert
        assert result == 5

    # Tests for create_area

    async def test_create_area_success(self, async_session: AsyncSession):
        """Test creating a single area"""
        # Act
        area_obj = await area.create_area(
            session=async_session,
            area_id="test-area-001",
            area_name="Test Area",
            filename="TestArea.zip",
            filedata=b"data1",
            competent_authority_id_str="0363",
            competent_authority_name="Gemeente Amsterdam",
        )

        # Assert
        assert area_obj.area_id == "test-area-001"
        assert area_obj.area_name == "Test Area"
        assert area_obj.filename == "TestArea.zip"
        assert area_obj.filedata == b"data1"

        count = await area.count_areas(async_session)
        assert count == 1

    async def test_create_area_auto_generates_id(self, async_session: AsyncSession):
        """Test that area_id is auto-generated when None"""
        # Act
        area_obj = await area.create_area(
            session=async_session,
            area_id=None,
            area_name=None,
            filename="AutoId.zip",
            filedata=b"data",
            competent_authority_id_str="0363",
            competent_authority_name="Gemeente Amsterdam",
        )

        # Assert
        assert area_obj.area_id is not None
        assert len(area_obj.area_id) == 36  # UUID format

    async def test_create_area_creates_competent_authority(
        self, async_session: AsyncSession
    ):
        """Test that competent authority is created if it doesn't exist"""
        # Act
        await area.create_area(
            session=async_session,
            area_id="new-ca-area",
            area_name=None,
            filename="NewCA.zip",
            filedata=b"data",
            competent_authority_id_str="8888",
            competent_authority_name="Test Authority",
        )

        # Assert
        from app.crud import competent_authority as ca_crud

        ca = await ca_crud.get_by_competent_authority_id(async_session, "8888")
        assert ca is not None
        assert ca.competent_authority_name == "Test Authority"

    async def test_create_area_reuses_existing_competent_authority(
        self, async_session: AsyncSession
    ):
        """Test that existing competent authority is reused"""
        # Arrange - create first area (creates CA)
        await area.create_area(
            session=async_session,
            area_id="area-1",
            area_name=None,
            filename="Area1.zip",
            filedata=b"data1",
            competent_authority_id_str="0363",
            competent_authority_name="Gemeente Amsterdam",
        )

        # Act - create second area (should reuse CA)
        await area.create_area(
            session=async_session,
            area_id="area-2",
            area_name=None,
            filename="Area2.zip",
            filedata=b"data2",
            competent_authority_id_str="0363",
            competent_authority_name="Gemeente Amsterdam",
        )

        # Assert
        from app.models.competent_authority import CompetentAuthority
        from sqlalchemy import select

        cas = await async_session.execute(select(CompetentAuthority))
        ca_count = len(cas.scalars().all())
        assert ca_count == 1  # Only one CA should exist

        area_count = await area.count_areas(async_session)
        assert area_count == 2  # But two areas
