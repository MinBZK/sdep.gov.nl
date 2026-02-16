"""Tests for CA Area API endpoints."""

from typing import Any

import pytest
from app.api.v0.main import app_v0
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

    @pytest.fixture(autouse=True)
    async def cleanup(self, async_session: AsyncSession):
        """Auto-cleanup fixture that runs before and after each test."""
        yield
        app_v0.dependency_overrides.clear()

    @pytest.fixture
    def setup_overrides(self, async_session: AsyncSession):
        """Setup dependency overrides for authenticated tests."""
        app_v0.dependency_overrides[verify_bearer_token] = mock_verify_bearer_token

        async def override_get_db():
            yield async_session

        app_v0.dependency_overrides[get_async_db] = override_get_db

        yield

    @pytest.fixture
    def setup_db_only(self, async_session: AsyncSession):
        """Setup database override only (no auth override)."""

        async def override_get_db():
            yield async_session

        app_v0.dependency_overrides[get_async_db] = override_get_db

        yield

    # Tests for POST /ca/areas

    async def test_post_area_success(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /ca/areas with a single area file upload (201 Created)."""
        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            response = await client.post(
                "/ca/areas",
                files={"file": ("Area.zip", b"zipdata", "application/zip")},
                headers={"Authorization": "Bearer test_token"},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "areaId" in data
        assert data["filename"] == "Area.zip"
        assert "createdAt" in data
        assert data["competentAuthorityId"] == "0363"
        assert data["competentAuthorityName"] == "Gemeente Amsterdam"

    async def test_post_area_with_area_id(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /ca/areas with custom areaId preserved."""
        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            response = await client.post(
                "/ca/areas",
                files={"file": ("Area.zip", b"zipdata", "application/zip")},
                data={"areaId": "my-custom-id"},
                headers={"Authorization": "Bearer test_token"},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["areaId"] == "my-custom-id"

    async def test_post_area_with_area_name(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /ca/areas with areaName."""
        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            response = await client.post(
                "/ca/areas",
                files={"file": ("Area.zip", b"zipdata", "application/zip")},
                data={"areaName": "Amsterdam Central"},
                headers={"Authorization": "Bearer test_token"},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["areaName"] == "Amsterdam Central"

    async def test_post_area_auto_generates_id(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /ca/areas without areaId generates a UUID."""
        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            response = await client.post(
                "/ca/areas",
                files={"file": ("Area.zip", b"zipdata", "application/zip")},
                headers={"Authorization": "Bearer test_token"},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "areaId" in data
        assert len(data["areaId"]) == 36  # UUID format

    async def test_post_area_creates_competent_authority(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test that POST /ca/areas auto-creates competent authority."""
        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            response = await client.post(
                "/ca/areas",
                files={"file": ("Area.zip", b"zipdata", "application/zip")},
                headers={"Authorization": "Bearer test_token"},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["competentAuthorityId"] == "0363"
        assert data["competentAuthorityName"] == "Gemeente Amsterdam"

    async def test_post_area_file_too_large(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /ca/areas with file exceeding 1 MiB returns 422."""
        large_data = b"x" * (1048576 + 1)  # 1 MiB + 1 byte

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            response = await client.post(
                "/ca/areas",
                files={"file": ("Large.zip", large_data, "application/zip")},
                headers={"Authorization": "Bearer test_token"},
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_post_area_unauthorized_no_token(
        self, async_session: AsyncSession, setup_db_only
    ):
        """Test POST /ca/areas without authentication token."""
        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            response = await client.post(
                "/ca/areas",
                files={"file": ("Area.zip", b"zipdata", "application/zip")},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_post_area_forbidden_missing_write_role(
        self, async_session: AsyncSession
    ):
        """Test POST /ca/areas with missing sdep_write role."""

        def mock_token_without_write_role():
            return {
                "sub": "test_user",
                "client_id": "0363",
                "client_name": "Gemeente Amsterdam",
                "realm_access": {
                    "roles": ["sdep_ca", "sdep_read"]
                },  # Missing sdep_write
            }

        app_v0.dependency_overrides[verify_bearer_token] = mock_token_without_write_role

        async def override_get_db():
            yield async_session

        app_v0.dependency_overrides[get_async_db] = override_get_db

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            response = await client.post(
                "/ca/areas",
                files={"file": ("Area.zip", b"zipdata", "application/zip")},
                headers={"Authorization": "Bearer test_token"},
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "sdep_write" in response.json()["detail"][0]["msg"]

    async def test_post_area_invalid_area_id_pattern(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /ca/areas with invalid areaId pattern returns 422."""
        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            response = await client.post(
                "/ca/areas",
                files={"file": ("Area.zip", b"zipdata", "application/zip")},
                data={"areaId": "INVALID_ID"},
                headers={"Authorization": "Bearer test_token"},
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
