"""Tests for CA Area API endpoints."""

from typing import Any

import pytest
import pytest_asyncio
from app.api.v0.main import app_v0
from app.crud import area as area_crud
from app.db.config import get_async_db
from app.security import verify_bearer_token
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


def mock_verify_bearer_token() -> dict[str, Any]:
    """Mock token verification for testing with ca role."""
    return {
        "sub": "test_user",
        "client_id": "0363",
        "client_name": "Gemeente Amsterdam",
        "realm_access": {"roles": ["sdep_ca", "sdep_read", "sdep_write"]},
    }


@pytest.mark.database
class TestCAAreaAPI:
    """Test suite for POST /ca/areas API endpoint."""

    @pytest.fixture
    def setup_overrides(self, async_session: AsyncSession):
        """Setup dependency overrides for authenticated tests."""
        # Override token verification
        app_v0.dependency_overrides[verify_bearer_token] = mock_verify_bearer_token

        # Override database session
        async def override_get_db():
            yield async_session

        app_v0.dependency_overrides[get_async_db] = override_get_db

        yield

        # Clean up overrides after test
        app_v0.dependency_overrides.clear()

    @pytest.fixture
    def setup_db_only(self, async_session: AsyncSession):
        """Setup database override only (no auth override)."""

        # Override database session
        async def override_get_db():
            yield async_session

        app_v0.dependency_overrides[get_async_db] = override_get_db

        yield

        # Clean up overrides after test
        app_v0.dependency_overrides.clear()

    # Tests for POST /ca/areas

    async def test_post_areas_multiple(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /ca/areas with multiple areas"""
        # Arrange
        payload = {
            "metadata": {},
            "areas": [
                {
                    "areaId": f"area-{i:03d}",
                    "filename": f"Area{i:03d}.zip",
                    "filedata": f"ZGF0YV97aX0=",  # base64 encoded
                }
                for i in range(1, 4)
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/ca/areas",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "message" in data
        assert "3" in data["message"]

        # Verify data was saved
        from app.services import area as area_service

        count = await area_service.count_areas(async_session)
        assert count == 3

    async def test_post_areas_single_area_in_list(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /ca/areas with single area in list"""
        # Arrange
        payload = {
            "metadata": {},
            "areas": [
                {
                    "areaId": "single-area",
                    "filename": "SingleArea.zip",
                    "filedata": "c2luZ2xlX2RhdGE=",
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/ca/areas",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "1" in data["message"]

    async def test_post_areas_creates_single_competent_authority(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test that POST /ca/areas creates only one competent authority for multiple areas"""
        # Arrange
        payload = {
            "metadata": {},
            "areas": [
                {
                    "areaId": f"multi-area-{i}",
                    "filename": f"MultiArea{i}.zip",
                    "filedata": "ZGF0YQ==",
                }
                for i in range(1, 4)
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/ca/areas",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED

        # Verify only one competent authority was created
        from app.models.competent_authority import CompetentAuthority
        from sqlalchemy import select

        cas = await async_session.execute(select(CompetentAuthority))
        ca_count = len(cas.scalars().all())
        assert ca_count == 1

    async def test_post_areas_unauthorized_no_token(
        self, async_session: AsyncSession, setup_db_only
    ):
        """Test POST /ca/areas without authentication token"""
        # Arrange
        payload = {
            "metadata": {},
            "areas": [
                {
                    "areaId": "test-area",
                    "filename": "Test.zip",
                    "filedata": "dGVzdA==",
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/ca/areas",
                json=payload,
            )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_post_areas_forbidden_missing_write_role(
        self, async_session: AsyncSession
    ):
        """Test POST /ca/areas with missing sdep_write role"""
        # Arrange
        def mock_token_without_write_role():
            return {
                "sub": "test_user",
                "client_id": "0363",
                "client_name": "Gemeente Amsterdam",
                "realm_access": {"roles": ["sdep_ca", "sdep_read"]},  # Missing sdep_write
            }

        app_v0.dependency_overrides[verify_bearer_token] = mock_token_without_write_role

        async def override_get_db():
            yield async_session

        app_v0.dependency_overrides[get_async_db] = override_get_db

        payload = {
            "metadata": {},
            "areas": [
                {
                    "areaId": "test-area",
                    "filename": "Test.zip",
                    "filedata": "dGVzdA==",
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/ca/areas",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "sdep_write" in response.json()["detail"][0]["msg"]

        # Clean up
        app_v0.dependency_overrides.clear()

    async def test_post_areas_validation_error_empty_list(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /ca/areas with empty areas list"""
        # Arrange
        payload = {
            "metadata": {},
            "areas": [],  # Empty list should fail validation
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/ca/areas",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
