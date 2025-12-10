"""Tests for Area business service"""

import pytest
from app.services import area
from sqlalchemy.ext.asyncio import AsyncSession

from test.fixtures.factories import AreaFactory


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
        assert "competentAuthorityId" in area_dict
        assert "competentAuthorityName" in area_dict
        assert "filename" in area_dict
        assert "createdAt" in area_dict

        # Verify no extra keys
        assert set(area_dict.keys()) == {
            "areaId",
            "competentAuthorityId",
            "competentAuthorityName",
            "filename",
            "createdAt",
        }

        # Verify types
        assert isinstance(area_dict["areaId"], str)
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

    async def test_get_area_by_area_id_not_found(self, async_session: AsyncSession):
        """Test getting area by area_id when area does not exist"""
        # Act
        result = await area.get_area_by_area_id(async_session, "non-existent-area-id")

        # Assert
        assert result is None

    async def test_get_area_by_area_id_with_data(self, async_session: AsyncSession):
        """Test getting area by area_id when area has geo data"""
        # Arrange
        test_geo_data = b"test_geo_binary_data"
        test_filename = "test_area.zip"
        test_area_id = "test-area-12345"
        test_area = await AreaFactory.create_async(
            async_session,
            area_id=test_area_id,
            filename=test_filename,
            filedata=test_geo_data,
        )

        # Act
        result = await area.get_area_by_area_id(async_session, test_area_id)

        # Assert
        assert result is not None
        assert result["filename"] == test_filename
        assert result["filedata"] == test_geo_data

    async def test_get_area_by_area_id_response_structure(
        self, async_session: AsyncSession
    ):
        """Test that get_area_by_area_id response structure matches specification"""
        # Arrange
        test_area_id = "test-area-xyz"
        test_area = await AreaFactory.create_async(
            async_session,
            area_id=test_area_id,
            filename="test.zip",
            filedata=b"test_data",
        )

        # Act
        result = await area.get_area_by_area_id(async_session, test_area_id)

        # Assert
        assert result is not None

        # Verify all required keys are present
        assert "filename" in result
        assert "filedata" in result

        # Verify no extra keys
        assert set(result.keys()) == {"filename", "filedata"}

        # Verify types
        assert isinstance(result["filename"], str)
        assert isinstance(result["filedata"], bytes)

    async def test_get_area_by_area_id_with_large_binary_data(
        self, async_session: AsyncSession
    ):
        """Test getting area by area_id with large binary content"""
        # Arrange
        large_geo_data = b"x" * 10000  # 10KB of data
        test_area_id = "large-area-999"
        test_area = await AreaFactory.create_async(
            async_session,
            area_id=test_area_id,
            filename="large_area.zip",
            filedata=large_geo_data,
        )

        # Act
        result = await area.get_area_by_area_id(async_session, test_area_id)

        # Assert
        assert result is not None
        assert result["filename"] == "large_area.zip"
        assert result["filedata"] == large_geo_data
        assert len(result["filedata"]) == 10000

    async def test_get_area_by_area_id_multiple_areas_different_data(
        self, async_session: AsyncSession
    ):
        """Test getting area by area_id when multiple areas exist with different geo data"""
        # Arrange
        test_area1 = await AreaFactory.create_async(
            async_session,
            area_id="area-001",
            filename="area1.zip",
            filedata=b"data1",
        )
        test_area2 = await AreaFactory.create_async(
            async_session,
            area_id="area-002",
            filename="area2.zip",
            filedata=b"data2",
        )
        test_area3 = await AreaFactory.create_async(
            async_session,
            area_id="area-003",
            filename="area3.zip",
            filedata=b"data3",
        )

        # Act
        result1 = await area.get_area_by_area_id(async_session, "area-001")
        result2 = await area.get_area_by_area_id(async_session, "area-002")
        result3 = await area.get_area_by_area_id(async_session, "area-003")

        # Assert
        assert result1 is not None
        assert result1["filename"] == "area1.zip"
        assert result1["filedata"] == b"data1"

        assert result2 is not None
        assert result2["filename"] == "area2.zip"
        assert result2["filedata"] == b"data2"

        assert result3 is not None
        assert result3["filename"] == "area3.zip"
        assert result3["filedata"] == b"data3"

    # Tests for process_area_list

    async def test_process_area_list_single_area(self, async_session: AsyncSession):
        """Test processing a single area in a list"""
        # Arrange
        areas_list = [
            {
                "area_id": "list-area-001",
                "filename": "ListArea001.zip",
                "filedata": b"data1",
                "competent_authority_id_str": "0363",
                "competent_authority_name": "Gemeente Amsterdam",
            }
        ]

        # Act
        await area.process_area_list(async_session, areas_list)

        # Assert
        count = await area.count_areas(async_session)
        assert count == 1

    async def test_process_area_list_multiple_areas(
        self, async_session: AsyncSession
    ):
        """Test processing multiple areas in a list"""
        # Arrange
        areas_list = [
            {
                "area_id": f"area-{i:03d}",
                "filename": f"Area{i:03d}.zip",
                "filedata": f"data{i}".encode(),
                "competent_authority_id_str": "0363",
                "competent_authority_name": "Gemeente Amsterdam",
            }
            for i in range(1, 6)
        ]

        # Act
        await area.process_area_list(async_session, areas_list)

        # Assert
        count = await area.count_areas(async_session)
        assert count == 5

    async def test_process_area_list_creates_competent_authority_if_not_exists(
        self, async_session: AsyncSession
    ):
        """Test that competent authority is created if it doesn't exist"""
        # Arrange
        areas_list = [
            {
                "area_id": "new-ca-area-001",
                "filename": "NewCA001.zip",
                "filedata": b"data1",
                "competent_authority_id_str": "8888",
                "competent_authority_name": "Test Authority",
            }
        ]

        # Act
        await area.process_area_list(async_session, areas_list)

        # Assert - verify competent authority was created
        from app.crud import competent_authority as ca_crud

        cas = await ca_crud.get_by_competent_authority_id(async_session, "8888")
        assert len(cas) == 1
        assert cas[0].competent_authority_name == "Test Authority"

    async def test_process_area_list_multiple_areas_same_authority(
        self, async_session: AsyncSession
    ):
        """Test processing multiple areas from the same competent authority"""
        # Arrange
        areas_list = [
            {
                "area_id": f"amsterdam-{i}",
                "filename": f"Amsterdam{i}.zip",
                "filedata": f"data{i}".encode(),
                "competent_authority_id_str": "0363",
                "competent_authority_name": "Gemeente Amsterdam",
            }
            for i in range(1, 4)
        ]

        # Act
        await area.process_area_list(async_session, areas_list)

        # Assert
        from app.models.competent_authority import CompetentAuthority
        from sqlalchemy import select

        cas = await async_session.execute(select(CompetentAuthority))
        ca_count = len(cas.scalars().all())
        assert ca_count == 1  # Only one CA should be created

        area_count = await area.count_areas(async_session)
        assert area_count == 3  # But three areas
