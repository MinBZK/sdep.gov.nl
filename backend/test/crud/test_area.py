"""Tests for Area CRUD operations."""

from datetime import datetime

import pytest
from app.crud import area
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from test.fixtures.factories import AreaFactory, CompetentAuthorityFactory


@pytest.mark.database
class TestAreaCRUD:
    """Test suite for Area CRUD operations."""

    async def test_create_area(self, async_session: AsyncSession):
        """Test creating a new area."""
        # Arrange
        ca = await CompetentAuthorityFactory.create_async(async_session)
        filename = "area1.zip"
        filedata = b"binary_geo_data"

        # Act
        result = await area.create(
            async_session,
            competent_authority_area_id=None,
            competent_authority_id=ca.id,
            filename=filename,
            filedata=filedata,
        )

        # Assert
        assert result.id is not None
        assert result.competent_authority_area_id is None  # Should be None when not provided
        assert result.competent_authority_id == ca.id
        assert result.filename == filename
        assert result.filedata == filedata
        assert result.created_at is not None
        assert isinstance(result.created_at, datetime)

    async def test_create_area_with_explicit_competent_authority_area_id(self, async_session: AsyncSession):
        """Test creating a new area with explicit competent_authority_area_id."""
        # Arrange
        ca = await CompetentAuthorityFactory.create_async(async_session)
        explicit_competent_authority_area_id = "custom-area-123abc"
        filename = "area1.zip"
        filedata = b"binary_geo_data"

        # Act
        result = await area.create(
            async_session,
            competent_authority_area_id=explicit_competent_authority_area_id,
            competent_authority_id=ca.id,
            filename=filename,
            filedata=filedata,
        )

        # Assert
        assert result.id is not None
        assert result.competent_authority_area_id == explicit_competent_authority_area_id  # Should use provided value
        assert result.competent_authority_id == ca.id
        assert result.filename == filename
        assert result.filedata == filedata
        assert result.created_at is not None
        assert isinstance(result.created_at, datetime)

    async def test_delete_area(self, async_session: AsyncSession):
        """Test deleting an existing area."""
        # Arrange
        ca = await CompetentAuthorityFactory.create_async(async_session)
        a = await AreaFactory.create_async(
            async_session,
            competent_authority_id=ca.id,
            filename="test.zip",
            filedata=b"test_data",
        )

        # Act
        result = await area.delete(async_session, a.id)

        # Assert
        assert result is True
        retrieved = await area.get_by_id(async_session, a.id)
        assert retrieved is None

    async def test_delete_area_not_found(self, async_session: AsyncSession):
        """Test deleting a non-existent area."""
        # Act
        result = await area.delete(async_session, "99999999999999999999")

        # Assert
        assert result is False

    async def test_exists_area(self, async_session: AsyncSession):
        """Test checking if an area exists."""
        # Arrange
        ca = await CompetentAuthorityFactory.create_async(async_session)
        a = await AreaFactory.create_async(
            async_session,
            competent_authority_id=ca.id,
            filename="test.zip",
            filedata=b"test_data",
        )

        # Act
        exists = await area.exists(async_session, a.id)
        not_exists = await area.exists(async_session, "99999999999999999999")

        # Assert
        assert exists is True
        assert not_exists is False

    async def test_count_areas(self, async_session: AsyncSession):
        """Test counting areas."""
        # Arrange
        ca = await CompetentAuthorityFactory.create_async(async_session)
        for i in range(3):
            await AreaFactory.create_async(
                async_session,
                competent_authority_id=ca.id,
                filename=f"area{i}.zip",
                filedata=b"test_data",
            )

        # Act
        total = await area.count(async_session)

        # Assert
        assert total == 3

    async def test_get_all_areas(self, async_session: AsyncSession):
        """Test getting all areas."""
        # Arrange
        ca1 = await CompetentAuthorityFactory.create_async(async_session)
        ca2 = await CompetentAuthorityFactory.create_async(async_session)
        await AreaFactory.create_async(
            async_session,
            competent_authority_id=ca1.id,
            filename="area1.zip",
            filedata=b"test_data1",
        )
        await AreaFactory.create_async(
            async_session,
            competent_authority_id=ca2.id,
            filename="area2.zip",
            filedata=b"test_data2",
        )

        # Act
        results = await area.get_all(async_session)

        # Assert
        assert len(results) == 2

    async def test_get_all_areas_with_pagination(self, async_session: AsyncSession):
        """Test getting areas with pagination."""
        # Arrange
        ca = await CompetentAuthorityFactory.create_async(async_session)
        for i in range(5):
            await AreaFactory.create_async(
                async_session,
                competent_authority_id=ca.id,
                filename=f"area{i}.zip",
                filedata=b"test_data",
            )

        # Act
        page1 = await area.get_all(async_session, offset=0, limit=2)
        page2 = await area.get_all(async_session, offset=2, limit=2)
        page3 = await area.get_all(async_session, offset=4, limit=2)

        # Assert
        assert len(page1) == 2
        assert len(page2) == 2
        assert len(page3) == 1

    async def test_get_by_id(self, async_session: AsyncSession):
        """Test getting an area by id."""
        # Arrange
        ca = await CompetentAuthorityFactory.create_async(async_session)
        a = await AreaFactory.create_async(
            async_session,
            competent_authority_id=ca.id,
            filename="test.zip",
            filedata=b"test_data",
        )

        # Act
        result = await area.get_by_id(async_session, a.id)

        # Assert
        assert result is not None
        assert result.id == a.id
        assert result.competent_authority_id == ca.id

    async def test_get_by_id_not_found(self, async_session: AsyncSession):
        """Test getting a non-existent area by id."""
        # Act
        result = await area.get_by_id(async_session, "99999999999999999999")

        # Assert
        assert result is None

    async def test_get_by_competent_authority_id(self, async_session: AsyncSession):
        """Test getting areas by competent authority id (foreign key)."""
        # Arrange
        ca = await CompetentAuthorityFactory.create_async(async_session)
        await AreaFactory.create_async(
            async_session,
            competent_authority_id=ca.id,
            filename="area1.zip",
            filedata=b"test_data1",
        )
        await AreaFactory.create_async(
            async_session,
            competent_authority_id=ca.id,
            filename="area2.zip",
            filedata=b"test_data2",
        )

        # Act
        results = await area.get_by_competent_authority_id(async_session, ca.id)

        # Assert
        assert len(results) == 2
        assert all(r.competent_authority_id == ca.id for r in results)

    async def test_get_by_competent_authority_id_not_found(
        self, async_session: AsyncSession
    ):
        """Test getting areas by non-existent competent authority id."""
        # Act
        results = await area.get_by_competent_authority_id(async_session, 99999)

        # Assert
        assert len(results) == 0

    async def test_get_by_filename(self, async_session: AsyncSession):
        """Test getting areas by filename."""
        # Arrange
        ca = await CompetentAuthorityFactory.create_async(async_session)
        filename = "special_area.zip"
        await AreaFactory.create_async(
            async_session,
            competent_authority_id=ca.id,
            filename=filename,
            filedata=b"test_data",
        )

        # Act
        results = await area.get_by_filename(async_session, filename)

        # Assert
        assert len(results) == 1
        assert results[0].filename == filename
