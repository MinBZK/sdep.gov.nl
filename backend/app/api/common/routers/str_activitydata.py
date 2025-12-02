"""STR Activity Data endpoint.

Transaction Management Architecture (API Layer):
- This API endpoint uses get_async_db dependency for automatic transaction management
- get_async_db provides a session with automatic commit/rollback via context manager
- Transaction boundary is at the API layer (aligned with HTTP request boundary)
- Service layer contains business logic without transaction management
- CRUD layer only flushes, never commits

Pattern:
- API layer: Transaction boundary (auto-commit via dependency)
- Service layer: Business logic (no transaction management)
- CRUD layer: Data access (flush only, no commits)
"""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.config import get_async_db
from app.exceptions.business import BusinessLogicError, DuplicateResourceError
from app.exceptions.validation import ValidationError
from app.schemas.activity_data import ActivityDataListRequest
from app.schemas.auth import UnauthorizedError
from app.security import verify_bearer_token
from app.services import activity_data as activity_data_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["str"])


@router.post(
    "/str/activity-data",
    status_code=status.HTTP_201_CREATED,
    summary="Submit activity data",
    description="Submit a list of rental activity data. All activities are processed atomically (all succeed or all fail). Validation is performed on all fields before processing. Requires 'sdep_str' and 'sdep_write' roles. Platform ID and name are extracted from the JWT token.",
    operation_id="postActivityData",
    responses={
        "201": {
            "description": "Activity data successfully processed and saved",
        },
        "400": {
            "description": "Bad Request - Validation error in submitted data",
        },
        "401": {
            "model": UnauthorizedError,
            "description": "Unauthorized - Invalid or missing token",
        },
        "403": {
            "description": "Forbidden - Missing required 'sdep_str' or 'sdep_write' role",
        },
        "409": {
            "description": "Conflict - Duplicate activity data (same URL and temporal dates) or constraint violation",
        },
    },
)
async def post_activity_data(
    data: ActivityDataListRequest,
    session: AsyncSession = Depends(get_async_db),
    token_payload: dict[str, Any] = Depends(verify_bearer_token),
) -> dict[str, str]:
    """
    Submit rental activity data for processing.

    Transaction Management:
    - API uses get_async_db which provides automatic transaction management
    - Transaction starts when dependency is invoked (via AsyncSessionLocal.begin())
    - Transaction commits automatically on success
    - Transaction rolls back automatically on exception
    - Service layer contains business logic only (no transaction management)

    Validation:
    - Pydantic validates all fields (syntax, types, constraints)
    - Service performs no validation (already validated by Pydantic)

    Authorization:
    - Requires valid bearer token with "sdep_str" and "sdep_write" roles in realm_access
    - Platform ID is extracted from token's "client_id" claim
    - Platform name is extracted from token's "client_name" claim

    Request Body:
    - metadata: Batch-level metadata (placeholder for future use)
    - activities: List of activity data (minimum 1 required)
    - Each activity contains:
      - url: Advertisement URL (max 128 chars, unique in combination with temporal dates)
      - registrationNumber: Registration number (max 32 chars)
      - address: Street, number, postalCode, city (all mandatory), letter and addition (optional)
      - areaId: Area identifier (max 64 chars)
      - numberOfGuests: Number of guests (1-1024)
      - countryOfGuests: List of country codes (1-1024 items)
      - temporal: Start and end datetime (end must be after start)

    Note: Platform ID and name (from token) are normalized to each activity at the API layer before passing
    to service layer. This keeps service layer focused on business logic. The platform is created
    automatically if it doesn't exist yet.

    Returns:
        Success message with count of processed activities

    Raises:
        HTTPException 400: Validation error
        HTTPException 403: Forbidden - Missing required "sdep_str" role
        HTTPException 409: Duplicate activity data (same URL and temporal dates) or constraint violation
        HTTPException 500: Internal server error
    """

    # Authorization check: Verify user has "sdep_str" and "sdep_write" roles
    realm_access = token_payload.get("realm_access", {})
    roles = realm_access.get("roles", [])

    if "sdep_str" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: 'sdep_str' role required",
        )

    if "sdep_write" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: 'sdep_write' role required",
        )

    # Extract platform ID and name from token
    # platformId comes from client_id claim
    platform_id = token_payload.get("client_id")
    if not platform_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing 'client_id' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # platformName comes from client_name claim
    platform_name = token_payload.get("client_name")
    if not platform_name:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing 'client_name' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Convert Pydantic models to service layer format
        # This flattens nested composites and converts to snake_case
        # Platform ID and name are extracted from the token, not from the request payload
        activities_dict = data.to_service_list(platform_id=platform_id, platform_name=platform_name)

        # Call service layer with injected session
        # Transaction is managed by get_async_db dependency (auto-commit on success)
        await activity_data_service.process_activity_data_list(session, activities_dict)

        return {
            "message": f"Successfully processed {len(data.activities)} activity data record(s)"
        }

    except DuplicateResourceError as e:
        # Handle duplicate resource errors (HTTP 409 via global handler)
        # Global handler logs and converts to proper HTTP response
        raise e
    except BusinessLogicError as e:
        # Handle business logic errors (HTTP 422 via global handler)
        # Global handler logs and converts to proper HTTP response
        raise e
    except ValidationError as e:
        # Handle validation errors (HTTP 422 via global handler)
        # Global handler logs and converts to proper HTTP response
        raise e
    except Exception as e:
        # Convert unexpected errors to HTTP 500
        # Global handler logs with full stack trace
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process activity data",
        ) from e
