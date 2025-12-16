"""Tests for STR Activities API endpoint."""

from typing import Any

import pytest
import pytest_asyncio
from app.api.v0.main import app_v0
from app.crud import activity as activity_crud
from app.db.config import get_async_db_manual_commit
from app.security import verify_bearer_token
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from test.fixtures.factories import AreaFactory, CompetentAuthorityFactory


def mock_verify_bearer_token() -> dict[str, Any]:
    """Mock token verification for testing with str role."""
    return {
        "sub": "test_user",
        "client_id": "str01",
        "client_name": "STR Platform 01",
        "realm_access": {"roles": ["sdep_str", "sdep_read", "sdep_write"]},
    }


@pytest.mark.database
class TestSTRActivitiesAPI:
    """Test suite for POST /str/activities API endpoint."""

    @pytest.fixture
    def setup_overrides(self, async_session: AsyncSession):
        """Setup dependency overrides for authenticated tests."""
        # Override token verification
        app_v0.dependency_overrides[verify_bearer_token] = mock_verify_bearer_token

        # Override database session with manual commit
        async def override_get_db_manual():
            yield async_session

        app_v0.dependency_overrides[get_async_db_manual_commit] = override_get_db_manual

        yield

        # Clean up overrides after test
        app_v0.dependency_overrides.clear()

    @pytest.fixture
    def setup_db_only(self, async_session: AsyncSession):
        """Setup database override only (no auth override)."""

        # Override database session with manual commit
        async def override_get_db_manual():
            yield async_session

        app_v0.dependency_overrides[get_async_db_manual_commit] = override_get_db_manual

        yield

        # Clean up overrides after test
        app_v0.dependency_overrides.clear()

    @pytest_asyncio.fixture
    async def test_areas(self, async_session: AsyncSession):
        """Create test areas for activities tests."""
        # Get or create competent authority (may already exist from previous test)
        from app.crud import competent_authority as ca_crud

        ca = await ca_crud.get_by_competent_authority_id(async_session, "test")
        if ca is None:
            ca = await CompetentAuthorityFactory.create_async(
                async_session,
                competent_authority_id="test",
                competent_authority_name="Test Authority",
            )

        # Create areas with specific competent_authority_area_ids needed by tests
        competent_authority_area_ids = ["0363", "0344", "ceaba747-15ca-4d8a-81f7", "ceaba747-15ca"]

        # Also create areas for transaction atomicity test (0000-0009)
        # Note: This already includes "0001" so don't add it separately above
        for i in range(10):
            competent_authority_area_ids.append(f"{i:04d}")

        # Create areas (each test gets fresh database)
        areas = {}
        for ca_area_id in competent_authority_area_ids:
            area = await AreaFactory.create_async(
                async_session,
                competent_authority_area_id=ca_area_id,
                competent_authority_id=ca.id,
                filename=f"{ca_area_id}.zip",
                filedata=b"test_data",
            )
            areas[ca_area_id] = area

        return areas

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup_activities(self, async_session: AsyncSession):
        """Setup fixture for test isolation.

        Note: With function-scoped async_engine, each test gets a fresh database.
        Transaction rollback is handled automatically by conftest.py.
        No manual cleanup is needed.
        """
        yield

    async def test_post_activities_single(
        self, async_session: AsyncSession, setup_overrides, test_areas
    ):
        """Test POST /str/activities with single activity."""
        # Arrange
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/listing-001",
                    "registrationNumber": "REG123456",
                    "address": {
                        "street": "Turfmarkt",
                        "number": 147,
                        "postalCode": "2500EA",
                        "city": "Den Haag",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": test_areas["0363"].id,
                    "countryOfGuests": ["NLD", "DEU", "BEL"],
                    "numberOfGuests": 4,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "message" in data
        assert "totalProcessed" in data
        assert data["totalProcessed"] == 1
        assert data["succeeded"] == 1
        assert data["failed"] == 0
        assert len(data["failures"]) == 0

        # Verify data was saved
        saved = await activity_crud.get_by_url(
            async_session, "http://example.com/listing-001"
        )
        assert len(saved) == 1
        assert saved[0].registration_number == "REG123456"

    async def test_post_activities_multiple(
        self, async_session: AsyncSession, setup_overrides, test_areas
    ):
        """Test POST /str/activities with multiple activities."""
        # Arrange
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/listing-001",
                    "registrationNumber": "REG001",
                    "address": {
                        "street": "Turfmarkt",
                        "number": 147,
                        "postalCode": "2500EA",
                        "city": "Den Haag",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": test_areas["0363"].id,
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                },
                {
                    "url": "http://example.com/listing-002",
                    "registrationNumber": "REG002",
                    "address": {
                        "street": "Kalverstraat",
                        "number": 123,
                        "postalCode": "1000AA",
                        "city": "Amsterdam",
                        "letter": "A",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-02T15:00:00Z",
                        "endDatetime": "2025-06-08T10:00:00Z",
                    },
                    "areaId": test_areas["0363"].id,
                    "countryOfGuests": ["DEU", "BEL"],
                    "numberOfGuests": 4,
                },
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["totalProcessed"] == 2
        assert data["succeeded"] == 2
        assert data["failed"] == 0
        assert len(data["failures"]) == 0

        # Verify both activities were saved
        all_activities = await activity_crud.get_all(async_session)
        assert len(all_activities) == 2

    async def test_post_activities_with_optional_fields(
        self, async_session: AsyncSession, setup_overrides, test_areas
    ):
        """Test POST /str/activities with all optional fields populated."""
        # Arrange
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/listing-full",
                    "registrationNumber": "REGFULL",
                    "address": {
                        "street": "Main Street",
                        "number": 999,
                        "postalCode": "5000CC",
                        "city": "Utrecht",
                        "letter": "B",
                        "addition": "3rd floor",
                    },
                    "temporal": {
                        "startDatetime": "2025-07-01T14:00:00Z",
                        "endDatetime": "2025-07-07T11:00:00Z",
                    },
                    "areaId": test_areas["0344"].id,
                    "countryOfGuests": ["NLD", "DEU", "BEL", "FRA"],
                    "numberOfGuests": 8,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["totalProcessed"] == 1
        assert data["succeeded"] == 1
        assert data["failed"] == 0

        # Verify optional fields were saved
        saved = await activity_crud.get_by_url(
            async_session, "http://example.com/listing-full"
        )
        assert len(saved) == 1
        assert saved[0].address.letter == "B"
        assert saved[0].address.addition == "3rd floor"

    async def test_post_activities_without_authentication(
        self, async_session: AsyncSession, setup_db_only
    ):
        """Test POST /str/activities without authentication token."""
        # Arrange
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Street",
                        "number": 1,
                        "postalCode": "1000AA",
                        "city": "City",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": 1,
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post("/str/activities", json=payload)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_post_activities_without_str_role(
        self, async_session: AsyncSession, test_areas
    ):
        """Test POST /str/activities without 'sdep_str' role returns 403."""

        # Setup override with token missing 'sdep_str' role
        def mock_verify_bearer_token_without_str_role() -> dict[str, Any]:
            """Mock token verification without str role."""
            return {
                "sub": "test_user",
                "client_id": "ca01",
                "client_name": "CA 01",
                "realm_access": {
                    "roles": ["ca", "sdep_read"]  # Missing 'sdep_str' role
                },
            }

        app_v0.dependency_overrides[verify_bearer_token] = (
            mock_verify_bearer_token_without_str_role
        )

        async def override_get_db():
            yield async_session

        app_v0.dependency_overrides[get_async_db_manual_commit] = override_get_db

        # Arrange
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test-no-role",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Street",
                        "number": 1,
                        "postalCode": "1000AA",
                        "city": "City",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": test_areas["0363"].id,
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "detail" in data
        detail_str = str(data["detail"]).lower()
        assert "sdep_str" in detail_str
        assert "role" in detail_str

        # Clean up overrides
        app_v0.dependency_overrides.clear()

    async def test_post_activities_without_client_id_claim(
        self, async_session: AsyncSession, test_areas
    ):
        """Test POST /str/activities without 'client_id' claim returns 401."""

        # Setup override with token missing 'client_id' claim
        def mock_verify_bearer_token_without_client_id() -> dict[str, Any]:
            """Mock token verification without client_id claim."""
            return {
                "sub": "test_user",
                # "client_id": "str01",  # Missing client_id!
                "client_name": "STR Platform 01",
                "realm_access": {"roles": ["sdep_str", "sdep_read", "sdep_write"]},
            }

        app_v0.dependency_overrides[verify_bearer_token] = (
            mock_verify_bearer_token_without_client_id
        )

        async def override_get_db():
            yield async_session

        app_v0.dependency_overrides[get_async_db_manual_commit] = override_get_db

        # Arrange
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test-no-client-id",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Street",
                        "number": 1,
                        "postalCode": "1000AA",
                        "city": "City",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": test_areas["0363"].id,
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
        detail_str = str(data["detail"]).lower()
        assert "client_id" in detail_str

        # Clean up overrides
        app_v0.dependency_overrides.clear()

    async def test_post_activities_validation_error_missing_required_field(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /str/activities with missing required field."""
        # Arrange - missing 'url' field
        payload = {
            "metadata": {},
            "activities": [
                {
                    # "url": "http://example.com/test",  # Missing!
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Street",
                        "number": 1,
                        "postalCode": "1000AA",
                        "city": "City",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": 1,
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == 422

    async def test_post_activities_validation_error_postal_code_with_space(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /str/activities with invalid postal code (contains space)."""
        # Arrange
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Street",
                        "number": 1,
                        "postalCode": "2500 EA",  # Invalid - has space
                        "city": "City",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": 1,
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == 422
        data = response.json()
        # Validation errors now return batch processing format
        assert data["totalProcessed"] == 1
        assert data["succeeded"] == 0
        assert data["failed"] == 1

    async def test_post_activities_validation_error_end_before_start(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /str/activities with end datetime before start datetime."""
        # Arrange
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Street",
                        "number": 1,
                        "postalCode": "1000AA",
                        "city": "City",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-07T14:00:00Z",
                        "endDatetime": "2025-06-01T11:00:00Z",  # Before start!
                    },
                    "areaId": 1,
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == 422

    async def test_post_activities_same_url_different_temporal(
        self, async_session: AsyncSession, setup_overrides, test_areas
    ):
        """Test POST /str/activities with same URL but different temporal dates (should succeed)."""
        # Arrange - same URL but different temporal periods
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/same-url",
                    "registrationNumber": "REG001",
                    "address": {
                        "street": "Street One",
                        "number": 1,
                        "postalCode": "1000AA",
                        "city": "City One",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": test_areas["0001"].id,
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                },
                {
                    "url": "http://example.com/same-url",  # Same URL!
                    "registrationNumber": "REG002",
                    "address": {
                        "street": "Street Two",
                        "number": 2,
                        "postalCode": "2000BB",
                        "city": "City Two",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-08T14:00:00Z",  # Different temporal!
                        "endDatetime": "2025-06-14T11:00:00Z",  # Different temporal!
                    },
                    "areaId": test_areas["0002"].id,
                    "countryOfGuests": ["DEU"],
                    "numberOfGuests": 4,
                },
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert - should succeed because temporal dates are different
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["totalProcessed"] == 2
        assert data["succeeded"] == 2
        assert data["failed"] == 0
        assert len(data["failures"]) == 0

        # Verify both activities were saved
        saved = await activity_crud.get_by_url(
            async_session, "http://example.com/same-url"
        )
        assert len(saved) == 2
        # Verify they have different temporal periods
        temporal_periods = {
            (r.temporal_start_date_time, r.temporal_end_date_time) for r in saved
        }
        assert len(temporal_periods) == 2

    async def test_post_activities_empty_list(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /str/activities with empty activities list."""
        # Arrange
        payload = {"activities": []}

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert - should fail validation (min 1 activity required)
        assert response.status_code == 422

    async def test_post_activities_transaction_atomicity(
        self, async_session: AsyncSession, setup_overrides, test_areas
    ):
        """Test that all activities are processed atomically (all or nothing)."""
        # Arrange - valid payload
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": f"http://example.com/listing-{i:03d}",
                    "registrationNumber": f"REG{i:03d}",
                    "address": {
                        "street": f"Street {i}",
                        "number": i,
                        "postalCode": f"{i:04d}AA",
                        "city": f"City {i}",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": test_areas["0363"].id,
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                }
                for i in range(1, 6)  # 5 activities
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["totalProcessed"] == 5
        assert data["succeeded"] == 5
        assert data["failed"] == 0

        # Verify all 5 activities were saved
        all_activities = await activity_crud.get_all(async_session)
        assert len(all_activities) == 5

    async def test_post_activities_validation_error_letter_instead_of_number(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /str/activities with letter instead of number for address.number field."""
        # Arrange - address.number should be int, providing string instead
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Main Street",
                        "number": "ABC",  # Invalid: should be int, not string
                        "postalCode": "1000AA",
                        "city": "Amsterdam",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": 1,
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == 422
        data = response.json()
        # Validation errors now return batch processing format
        assert data["totalProcessed"] == 1
        assert data["succeeded"] == 0
        assert data["failed"] == 1
        assert isinstance(data["failures"], list)

    async def test_post_activities_validation_error_number_instead_of_letter(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /str/activities with number instead of letter for address.letter field."""
        # Arrange - address.letter should be str, providing int instead
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Main Street",
                        "number": 123,
                        "letter": 456,  # Invalid: should be str, not int
                        "postalCode": "1000AA",
                        "city": "Amsterdam",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": 1,
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == 422
        data = response.json()
        # Validation errors now return batch processing format
        assert data["totalProcessed"] == 1
        assert data["succeeded"] == 0
        assert data["failed"] == 1
        assert isinstance(data["failures"], list)

    async def test_post_activities_validation_error_letter_numeric_string(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /str/activities with numeric string for address.letter field."""
        # Arrange - address.letter should be alphabetic only, providing numeric string
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Main Street",
                        "number": 123,
                        "letter": "6",  # Invalid: numeric string
                        "postalCode": "1000AA",
                        "city": "Amsterdam",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": 1,
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == 422
        data = response.json()
        # Validation errors now return batch processing format
        assert data["totalProcessed"] == 1
        assert data["succeeded"] == 0
        assert data["failed"] == 1
        assert isinstance(data["failures"], list)

    async def test_post_activities_validation_error_letter_special_char(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /str/activities with special character for address.letter field."""
        # Arrange - address.letter should be alphabetic only
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Main Street",
                        "number": 123,
                        "letter": "-",  # Invalid: special character
                        "postalCode": "1000AA",
                        "city": "Amsterdam",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": 1,
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == 422
        data = response.json()
        # Validation errors now return batch processing format
        assert data["totalProcessed"] == 1
        assert data["succeeded"] == 0
        assert data["failed"] == 1

    async def test_post_activities_validation_error_postal_code_special_char(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /str/activities with special character in postal code."""
        # Arrange - postal code should be alphanumeric only
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Main Street",
                        "number": 123,
                        "postalCode": "1000-AA",  # Invalid: contains hyphen
                        "city": "Amsterdam",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": 1,
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == 422
        data = response.json()
        # Validation errors now return batch processing format
        assert data["totalProcessed"] == 1
        assert data["succeeded"] == 0
        assert data["failed"] == 1

    async def test_post_activities_validation_error_competent_authority_area_id_uppercase(
        self, async_session: AsyncSession, setup_overrides, test_areas
    ):
        """Test POST /str/activities - obsolete test (competentAuthorityId field removed)."""
        # This test is now obsolete since competentAuthorityId was removed from Activity schema
        # Keeping as a successful activity submission test
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test-obsolete-uppercase",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Main Street",
                        "number": 123,
                        "postalCode": "1000AA",
                        "city": "Amsterdam",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": test_areas["0363"].id,
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert - now expects success since field was removed
        assert response.status_code == 201
        data = response.json()
        assert data["totalProcessed"] == 1
        assert data["succeeded"] == 1
        assert data["failed"] == 0

    async def test_post_activities_validation_error_competent_authority_area_id_non_alphanumeric_chars(
        self, async_session: AsyncSession, setup_overrides, test_areas
    ):
        """Test POST /str/activities - obsolete test (competentAuthorityId field removed)."""
        # This test is now obsolete since competentAuthorityId was removed from Activity schema
        # Keeping as a successful activity submission test
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test-obsolete-nonalpha",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Main Street",
                        "number": 123,
                        "postalCode": "1000AA",
                        "city": "Amsterdam",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": test_areas["0363"].id,
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert - now expects success since field was removed
        assert response.status_code == 201
        data = response.json()
        assert data["totalProcessed"] == 1
        assert data["succeeded"] == 1
        assert data["failed"] == 0

    async def test_post_activities_validation_success_competent_authority_area_id_with_hyphens(
        self, async_session: AsyncSession, setup_overrides, test_areas
    ):
        """Test POST /str/activities accepts valid alphanumeric competent_authority_area_id with hyphens."""
        # Arrange - valid lowercase alphanumeric with hyphens should be accepted
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test-hex-hyphens",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Main Street",
                        "number": 123,
                        "postalCode": "1000AA",
                        "city": "Amsterdam",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": test_areas["ceaba747-15ca-4d8a-81f7"].id,  # Valid: alphanumeric with hyphens
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Processed 1 activities: 1 succeeded, 0 failed"

    async def test_post_activities_validation_error_country_code_lowercase(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /str/activities with lowercase country code."""
        # Arrange - country codes should be uppercase
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Main Street",
                        "number": 123,
                        "postalCode": "1000AA",
                        "city": "Amsterdam",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": 1,
                    "countryOfGuests": [
                        "nld"
                    ],  # Invalid: lowercase (ISO 3166-1 alpha-3)
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == 422
        data = response.json()
        # Validation errors now return batch processing format
        assert data["totalProcessed"] == 1
        assert data["succeeded"] == 0
        assert data["failed"] == 1

    async def test_post_activities_validation_error_country_code_too_short(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /str/activities with country code too short."""
        # Arrange - country codes must be exactly 3 characters (ISO 3166-1 alpha-3)
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Main Street",
                        "number": 123,
                        "postalCode": "1000AA",
                        "city": "Amsterdam",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": 1,
                    "countryOfGuests": ["NL"],  # Invalid: 2 characters instead of 3
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == 422
        data = response.json()
        # Validation errors now return batch processing format
        assert data["totalProcessed"] == 1
        assert data["succeeded"] == 0
        assert data["failed"] == 1

    async def test_post_activities_validation_error_country_code_too_long(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /str/activities with country code too long."""
        # Arrange - country codes must be exactly 3 characters (ISO 3166-1 alpha-3)
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Main Street",
                        "number": 123,
                        "postalCode": "1000AA",
                        "city": "Amsterdam",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": 1,
                    "countryOfGuests": ["ABCD"],  # Invalid: 4 characters instead of 3
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == 422
        data = response.json()
        # Validation errors now return batch processing format
        assert data["totalProcessed"] == 1
        assert data["succeeded"] == 0
        assert data["failed"] == 1

    async def test_post_activities_validation_error_country_code_with_numbers(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /str/activities with country code containing numbers."""
        # Arrange - country codes should be alphabetic only
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Main Street",
                        "number": 123,
                        "postalCode": "1000AA",
                        "city": "Amsterdam",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": 1,
                    "countryOfGuests": ["N1D"],  # Invalid: contains number
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == 422
        data = response.json()
        # Validation errors now return batch processing format
        assert data["totalProcessed"] == 1
        assert data["succeeded"] == 0
        assert data["failed"] == 1

    async def test_post_activities_validation_success_country_codes_alpha3(
        self, async_session: AsyncSession, setup_overrides, test_areas
    ):
        """Test POST /str/activities accepts valid ISO 3166-1 alpha-3 country codes."""
        # Arrange - valid 3-character country codes should be accepted
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test-alpha3-countries",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Main Street",
                        "number": 123,
                        "postalCode": "1000AA",
                        "city": "Amsterdam",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": test_areas["ceaba747-15ca"].id,
                    "countryOfGuests": [
                        "NLD",
                        "USA",
                        "DEU",
                        "GBR",
                    ],  # Valid: ISO 3166-1 alpha-3 codes
                    "numberOfGuests": 4,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Processed 1 activities: 1 succeeded, 0 failed"

    async def test_post_activities_platform_from_token(
        self, async_session: AsyncSession, setup_overrides, test_areas
    ):
        """Test that platform is extracted from JWT token (client_id and client_name claims)."""
        # Arrange
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": "http://example.com/test-platform-from-token",
                    "registrationNumber": "REGTOKEN",
                    "address": {
                        "street": "Test Street",
                        "number": 123,
                        "postalCode": "1000AA",
                        "city": "Test City",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": test_areas["0363"].id,
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["totalProcessed"] == 1
        assert data["succeeded"] == 1
        assert data["failed"] == 0

        # Verify platform was extracted from token's client_id and client_name claims and created
        saved = await activity_crud.get_by_url(
            async_session, "http://example.com/test-platform-from-token"
        )
        assert len(saved) == 1
        # Need to eagerly load the platform to avoid lazy loading issues
        await async_session.refresh(saved[0], ["platform"])
        assert (
            saved[0].platform.platform_id == "str01"
        )  # From mock token's client_id claim
        assert (
            saved[0].platform.platform_name == "STR Platform 01"
        )  # From mock token's client_name claim

    async def test_post_activities_validation_error_start_year_before_2025(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /str/activities with start year before 2025."""
        # Arrange - start datetime year must be >= 2025
        payload = {
            "metadata": {
                "platform": "str01",
            },
            "activities": [
                {
                    "url": "http://example.com/test",
                    "registrationNumber": "REG123",
                    "address": {
                        "street": "Main Street",
                        "number": 123,
                        "postalCode": "1000AA",
                        "city": "Amsterdam",
                    },
                    "temporal": {
                        "startDatetime": "2024-12-31T23:59:59Z",  # Invalid: year 2024
                        "endDatetime": "2025-01-07T11:00:00Z",
                    },
                    "areaId": 1,
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == 422
        data = response.json()
        # Validation errors now return batch processing format
        assert data["totalProcessed"] == 1
        assert data["succeeded"] == 0
        assert data["failed"] == 1

    async def test_post_activities_with_platform_activity_id(
        self, async_session: AsyncSession, setup_overrides, test_areas
    ):
        """Test POST /str/activities with optional platformActivityId field provided."""
        # Arrange
        payload = {
            "metadata": {},
            "activities": [
                {
                    "platformActivityId": "custom-activity-id-001",
                    "url": "http://example.com/listing-with-id",
                    "registrationNumber": "REG123456",
                    "address": {
                        "street": "Turfmarkt",
                        "number": 147,
                        "postalCode": "2500EA",
                        "city": "Den Haag",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": test_areas["0363"].id,
                    "countryOfGuests": ["NLD", "DEU", "BEL"],
                    "numberOfGuests": 4,
                }
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "message" in data
        assert data["totalProcessed"] == 1
        assert data["succeeded"] == 1
        assert data["failed"] == 0
        assert len(data["failures"]) == 0

        # Verify data was saved with the specified platform_activity_id
        saved = await activity_crud.get_by_url(
            async_session, "http://example.com/listing-with-id"
        )
        assert len(saved) == 1
        assert saved[0].platform_activity_id == "custom-activity-id-001"
        assert saved[0].registration_number == "REG123456"

    async def test_post_activities_all_succeed(
        self, async_session: AsyncSession, setup_overrides, test_areas
    ):
        """Test POST /str/activities with 5 activities - all succeed (201 Created)."""
        # Arrange - 5 unique activities
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": f"http://example.com/all-succeed-{i}",
                    "registrationNumber": f"REG{i:03d}",
                    "address": {
                        "street": f"Street {i}",
                        "number": i,
                        "postalCode": f"{i:04d}AA",
                        "city": f"City {i}",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": test_areas["0363"].id,
                    "numberOfGuests": 2,
                }
                for i in range(1, 6)
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert - 201 Created (all succeeded)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["totalProcessed"] == 5
        assert data["succeeded"] == 5
        assert data["failed"] == 0
        assert len(data["failures"]) == 0

        # Verify all 5 saved
        all_activities = await activity_crud.get_all(async_session)
        assert len(all_activities) == 5

    async def test_post_activities_partial_success(
        self, async_session: AsyncSession, setup_overrides, test_areas
    ):
        """Test POST /str/activities with partial success - some succeed, some fail (200 OK)."""
        # Submit 2 activities: 1 valid, 1 invalid area
        payload = {
            "metadata": {},
            "activities": [
                # Activity 0: Valid - should succeed
                {
                    "url": "http://example.com/valid-1",
                    "registrationNumber": "REG100",
                    "address": {
                        "street": "Valid Street",
                        "number": 100,
                        "postalCode": "1000BB",
                        "city": "Valid City",
                    },
                    "temporal": {
                        "startDatetime": "2025-07-01T14:00:00Z",
                        "endDatetime": "2025-07-07T11:00:00Z",
                    },
                    "areaId": test_areas["0363"].id,
                    "numberOfGuests": 3,
                },
                # Activity 1: Invalid area - should fail validation
                {
                    "url": "http://example.com/invalid-area",
                    "registrationNumber": "REG200",
                    "address": {
                        "street": "Invalid Street",
                        "number": 200,
                        "postalCode": "2000CC",
                        "city": "Invalid City",
                    },
                    "temporal": {
                        "startDatetime": "2025-08-01T14:00:00Z",
                        "endDatetime": "2025-08-07T11:00:00Z",
                    },
                    "areaId": "99999999999999999999",  # Non-existent 20-char area ID
                    "numberOfGuests": 5,
                },
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert - 200 OK (partial success)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["totalProcessed"] == 2
        assert data["succeeded"] == 1
        assert data["failed"] == 1
        assert len(data["failures"]) == 1

        # Verify failure details
        area_failure = data["failures"][0]
        assert area_failure["activityIndex"] == 1
        assert len(area_failure["errors"]) >= 1
        assert any(
            "area" in e["msg"].lower() and "not found" in e["msg"].lower()
            for e in area_failure["errors"]
        )

        # Verify only 1 activity was saved
        all_activities = await activity_crud.get_all(async_session)
        assert len(all_activities) == 1

    async def test_post_activities_all_fail(
        self, async_session: AsyncSession, setup_overrides, test_areas
    ):
        """Test POST /str/activities with all failures - all fail (422 Unprocessable Entity)."""
        # Arrange - All activities have invalid areas
        payload = {
            "metadata": {},
            "activities": [
                {
                    "url": f"http://example.com/all-fail-{i}",
                    "registrationNumber": f"REGFAIL{i:03d}",
                    "address": {
                        "street": f"Fail Street {i}",
                        "number": i,
                        "postalCode": f"{i:04d}FF",
                        "city": f"Fail City {i}",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",
                        "endDatetime": "2025-06-07T11:00:00Z",
                    },
                    "areaId": f"99999999999999999{i:03d}",  # Non-existent 20-char area IDs
                    "numberOfGuests": i,
                }
                for i in range(1, 4)
            ],
        }

        async with AsyncClient(
            transport=ASGITransport(app=app_v0), base_url="http://test"
        ) as client:
            # Act
            response = await client.post(
                "/str/activities",
                json=payload,
                headers={"Authorization": "Bearer test_token"},
            )

        # Assert - 422 Unprocessable Entity (all failed)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        data = response.json()
        assert data["totalProcessed"] == 3
        assert data["succeeded"] == 0
        assert data["failed"] == 3
        assert len(data["failures"]) == 3

        # Verify all failures have area errors
        for failure in data["failures"]:
            assert len(failure["errors"]) >= 1
            assert any("area" in e["msg"].lower() for e in failure["errors"])

        # Verify nothing was saved
        all_activities = await activity_crud.get_all(async_session)
        assert len(all_activities) == 0
