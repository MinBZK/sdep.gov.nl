"""Tests for STR Activities API endpoint."""

from typing import Any

import pytest
import pytest_asyncio
from app.api.v0.main import app_v0
from app.crud import activity as activity_crud
from app.db.config import get_async_db
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

    @pytest_asyncio.fixture
    async def test_areas(self, async_session: AsyncSession):
        """Create test areas for activities tests."""
        # Create a single competent authority for all test areas
        ca = await CompetentAuthorityFactory.create_async(
            async_session,
            competent_authority_id="test",
            competent_authority_name="Test Authority",
        )

        # Create areas with specific area_ids needed by tests
        area_ids = ["0363", "0344", "ceaba747-15ca-4d8a-81f7", "ceaba747-15ca"]

        # Also create areas for transaction atomicity test (0000-0009)
        # Note: This already includes "0001" so don't add it separately above
        for i in range(10):
            area_ids.append(f"{i:04d}")

        areas = {}
        for area_id in area_ids:
            area = await AreaFactory.create_async(
                async_session,
                area_id=area_id,
                competent_authority_id=ca.id,
                filename=f"{area_id}.geojson",
                filedata=b"test_data",
            )
            areas[area_id] = area

        return areas

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
                    "areaId": "0363",
                    "competentAuthorityId": "test",
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
        assert "1" in data["message"]

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
                    "areaId": "0363",
                    "competentAuthorityId": "test",
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
                    "areaId": "0363",
                    "competentAuthorityId": "test",
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
        assert "2" in data["message"]

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
                    "areaId": "0344",
                    "competentAuthorityId": "test",
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
                    "areaId": "0001",
                    "competentAuthorityId": "test",
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

        app_v0.dependency_overrides[get_async_db] = override_get_db

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
                    "areaId": "0363",
                    "competentAuthorityId": "test",
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

        app_v0.dependency_overrides[get_async_db] = override_get_db

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
                    "areaId": "0363",
                    "competentAuthorityId": "test",
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
                    "areaId": "0001",
                    "competentAuthorityId": "test",
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
                    "areaId": "0001",
                    "competentAuthorityId": "test",
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
        assert "detail" in data

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
                    "areaId": "0001",
                    "competentAuthorityId": "test",
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

    @pytest.mark.filterwarnings("ignore::sqlalchemy.exc.SAWarning")
    async def test_post_activities_duplicate_constraint(
        self, async_session: AsyncSession, setup_overrides, test_areas
    ):
        """Test POST /str/activities with duplicate unique constraint (activityId + url + temporal dates)."""
        # Arrange - post same activityId, URL, and temporal dates twice
        payload = {
            "metadata": {},
            "activities": [
                {
                    "activityId": "duplicate-activity-id",  # Same activityId!
                    "url": "http://example.com/duplicate",
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
                    "areaId": "0001",
                    "competentAuthorityId": "test",
                    "countryOfGuests": ["NLD"],
                    "numberOfGuests": 2,
                },
                {
                    "activityId": "duplicate-activity-id",  # Same activityId!
                    "url": "http://example.com/duplicate",  # Same URL!
                    "registrationNumber": "REG002",
                    "address": {
                        "street": "Street Two",
                        "number": 2,
                        "postalCode": "2000BB",
                        "city": "City Two",
                    },
                    "temporal": {
                        "startDatetime": "2025-06-01T14:00:00Z",  # Same temporal!
                        "endDatetime": "2025-06-07T11:00:00Z",  # Same temporal!
                    },
                    "areaId": "0002",
                    "competentAuthorityId": "test",
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

        # Assert
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "detail" in data
        # detail is a list of error objects with 'msg' field
        assert isinstance(data["detail"], list)
        assert len(data["detail"]) > 0
        error_msg = data["detail"][0]["msg"].lower()
        assert "duplicate" in error_msg or "already exists" in error_msg

        # Rollback the failed transaction to allow subsequent queries
        await async_session.rollback()
        # Restart savepoint for test isolation
        await async_session.begin_nested()

        # Verify transaction was rolled back - NO activities saved
        all_activities = await activity_crud.get_all(async_session)
        assert len(all_activities) == 0

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
                    "areaId": "0001",
                    "competentAuthorityId": "test",
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
                    "areaId": "0002",
                    "competentAuthorityId": "test",
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
        assert "2" in data["message"]

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
                    "areaId": f"{i:04d}",
                    "competentAuthorityId": "test",
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
                    "areaId": "0001",
                    "competentAuthorityId": "test",
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
        assert "detail" in data
        # Verify error message is functional and points to correct field
        assert isinstance(data["detail"], list)
        assert len(data["detail"]) > 0
        error = data["detail"][0]
        # Check that error message is functional (not JSON decoding error)
        assert "integer" in error["msg"].lower() or "int" in error["type"].lower()

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
                    "areaId": "0001",
                    "competentAuthorityId": "test",
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
        assert "detail" in data
        # Verify error message is functional and points to correct field
        assert isinstance(data["detail"], list)
        assert len(data["detail"]) > 0
        error = data["detail"][0]
        # Check that error points to address.letter field
        # Check that error message is functional (not JSON decoding error)
        assert "string" in error["msg"].lower() or "string" in error["type"].lower()

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
                    "areaId": "ceaba747-15ca-4d8a",
                    "competentAuthorityId": "test",
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
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert len(data["detail"]) > 0
        error = data["detail"][0]
        assert "alphabetic" in error["msg"].lower()

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
                    "areaId": "ceaba747-15ca-4d8a",
                    "competentAuthorityId": "test",
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
        assert "detail" in data
        error = data["detail"][0]
        assert "alphabetic" in error["msg"].lower()

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
                    "areaId": "ceaba747-15ca-4d8a",
                    "competentAuthorityId": "test",
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
        assert "detail" in data
        error = data["detail"][0]
        # Error can be from pattern constraint or validator
        assert (
            "alphanumeric" in error["msg"].lower() or "pattern" in error["msg"].lower()
        )

    async def test_post_activities_validation_error_area_id_uppercase(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /str/activities with uppercase characters in area_id."""
        # Arrange - area_id should be lowercase alphanumeric
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
                    "areaId": "CEABA747-15CA",  # Invalid: uppercase
                    "competentAuthorityId": "test",
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
        assert "detail" in data
        error = data["detail"][0]
        # Error can be from pattern constraint or validator
        assert (
            "lowercase" in error["msg"].lower()
            or "alphanumeric" in error["msg"].lower()
            or "pattern" in error["msg"].lower()
        )

    async def test_post_activities_validation_error_area_id_non_alphanumeric_chars(
        self, async_session: AsyncSession, setup_overrides
    ):
        """Test POST /str/activities with non-alphanumeric characters in area_id."""
        # Arrange - area_id should only contain lowercase alphanumeric chars (0-9, a-z) and dashes
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
                    "areaId": "area_123",  # Invalid: contains underscore
                    "competentAuthorityId": "test",
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
        assert "detail" in data
        error = data["detail"][0]
        # Error can be from pattern constraint or validator
        assert (
            "alphanumeric" in error["msg"].lower() or "pattern" in error["msg"].lower()
        )

    async def test_post_activities_validation_success_area_id_with_hyphens(
        self, async_session: AsyncSession, setup_overrides, test_areas
    ):
        """Test POST /str/activities accepts valid alphanumeric area_id with hyphens."""
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
                    "areaId": "ceaba747-15ca-4d8a-81f7",  # Valid: alphanumeric with hyphens
                    "competentAuthorityId": "test",
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
        assert data["message"] == "Successfully processed 1 activities record(s)"

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
                    "areaId": "ceaba747-15ca",
                    "competentAuthorityId": "test",
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
        assert "detail" in data
        error = data["detail"][0]
        assert "uppercase" in error["msg"].lower()

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
                    "areaId": "ceaba747-15ca",
                    "competentAuthorityId": "test",
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
        assert "detail" in data
        error = data["detail"][0]
        assert "3 characters" in error["msg"]

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
                    "areaId": "ceaba747-15ca",
                    "competentAuthorityId": "test",
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
        assert "detail" in data
        error = data["detail"][0]
        assert "3 characters" in error["msg"]

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
                    "areaId": "ceaba747-15ca",
                    "competentAuthorityId": "test",
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
        assert "detail" in data
        error = data["detail"][0]
        assert "alphabetic" in error["msg"].lower()

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
                    "areaId": "ceaba747-15ca",
                    "competentAuthorityId": "test",
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
        assert data["message"] == "Successfully processed 1 activities record(s)"

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
                    "areaId": "0363",
                    "competentAuthorityId": "test",
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
                    "areaId": "0001",
                    "competentAuthorityId": "test",
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
        assert "detail" in data
        error = data["detail"][0]
        assert "2025" in error["msg"]

    async def test_post_activities_with_activity_id(
        self, async_session: AsyncSession, setup_overrides, test_areas
    ):
        """Test POST /str/activities with optional activityId field provided."""
        # Arrange
        payload = {
            "metadata": {},
            "activities": [
                {
                    "activityId": "custom-activity-id-001",
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
                    "areaId": "0363",
                    "competentAuthorityId": "test",
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
        assert "1" in data["message"]

        # Verify data was saved with the specified activity_id
        saved = await activity_crud.get_by_url(
            async_session, "http://example.com/listing-with-id"
        )
        assert len(saved) == 1
        assert saved[0].activity_id == "custom-activity-id-001"
        assert saved[0].registration_number == "REG123456"
