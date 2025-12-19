"""Tests for CA Area API endpoints."""

from typing import Any

import pytest
from app.api.v0.main import app_v0
from app.db.config import get_async_db_manual_commit
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
        # Setup - runs before test
        yield
        # Teardown - runs after test, regardless of success/failure
        # Note: Transaction rollback is handled automatically by conftest.py
        app_v0.dependency_overrides.clear()

    @pytest.fixture
    def setup_overrides(self, async_session: AsyncSession):
        """Setup dependency overrides for authenticated tests."""
        # Override token verification
        app_v0.dependency_overrides[verify_bearer_token] = mock_verify_bearer_token

        # Override database session with manual commit
        async def override_get_db_manual_commit():
            yield async_session

        app_v0.dependency_overrides[get_async_db_manual_commit] = (
            override_get_db_manual_commit
        )

        yield

    @pytest.fixture
    def setup_db_only(self, async_session: AsyncSession):
        """Setup database override only (no auth override)."""

        # Override database session with manual commit
        async def override_get_db_manual_commit():
            yield async_session

        app_v0.dependency_overrides[get_async_db_manual_commit] = (
            override_get_db_manual_commit
        )

        yield

    # Tests for POST /ca/areas

    async def test_post_areas_all_succeed(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /ca/areas with multiple areas - all succeed (201 Created)."""
        # Arrange
        payload = {
            "areas": [
                {
                    "competentAuthorityAreaId": f"area-{i:03d}",
                    "filename": f"Area{i:03d}.zip",
                    "filedata": "ZGF0YV97aX0=",  # base64 encoded
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

        # Assert - 201 Created (all succeeded)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["totalProcessed"] == 3
        assert data["succeeded"] == 3
        assert data["failed"] == 0
        assert len(data["failures"]) == 0
        assert "3 succeeded" in data["message"]

    async def test_post_areas_all_fail_pydantic(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /ca/areas with all Pydantic validation failures (422)."""
        # Arrange - All areas have missing required fields
        payload = {
            "areas": [
                {
                    "competentAuthorityAreaId": "missing-filename-1",
                    # Missing filename and filedata
                },
                {
                    "competentAuthorityAreaId": "missing-filedata-2",
                    "filename": "Test.zip",
                    # Missing filedata
                },
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

        # Assert - 422 Unprocessable Entity (all failed)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        data = response.json()
        assert data["totalProcessed"] == 2
        assert data["succeeded"] == 0
        assert data["failed"] == 2
        assert len(data["failures"]) == 2

    async def test_post_areas_single_area_in_list(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /ca/areas with single area in list (201)."""
        # Arrange
        payload = {
            "areas": [
                {
                    "competentAuthorityAreaId": "single-area",
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
        assert data["totalProcessed"] == 1
        assert data["succeeded"] == 1
        assert data["failed"] == 0

    async def test_post_areas_creates_single_competent_authority(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test that POST /ca/areas creates only one competent authority for multiple areas."""
        # Arrange
        payload = {
            "areas": [
                {
                    "competentAuthorityAreaId": f"multi-area-{i}",
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

    async def test_post_areas_unauthorized_no_token(
        self, async_session: AsyncSession, setup_db_only
    ):
        """Test POST /ca/areas without authentication token."""
        # Arrange
        payload = {
            "areas": [
                {
                    "competentAuthorityAreaId": "test-area",
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
        """Test POST /ca/areas with missing sdep_write role."""

        # Arrange
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

        async def override_get_db_manual_commit():
            yield async_session

        app_v0.dependency_overrides[get_async_db_manual_commit] = (
            override_get_db_manual_commit
        )

        payload = {
            "areas": [
                {
                    "competentAuthorityAreaId": "test-area",
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

    async def test_post_areas_validation_error_empty_list(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /ca/areas with empty areas list."""
        # Arrange
        payload = {
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
