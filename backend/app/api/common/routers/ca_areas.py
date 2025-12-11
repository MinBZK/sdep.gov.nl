"""CA Area endpoints.

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
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.config import get_async_db
from app.exceptions.business import BusinessLogicError, DuplicateResourceError
from app.exceptions.validation import ValidationError
from app.schemas.area import AreaListRequest
from app.schemas.auth import UnauthorizedError
from app.security import verify_bearer_token
from app.services import area as area_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ca"])


@router.post(
    "/ca/areas",
    status_code=status.HTTP_201_CREATED,
    summary="Submit areas for competent authority (authorized by the current bearer token)",
    description="Submit a list of geographical areas with shapefile data for competent authority (authorized by the current bearer token). All areas are processed atomically (all succeed or all fail). Validation is performed on all fields before processing. Use areaId (functional, optional, otherwise randomized) when having (wanting to submit) double-entries from your own adminstation. **IMPORTANT:** The 'filedata' field must contain base64-encoded file data. Use base64 encoding to convert your binary files before sending them in the JSON payload.",
    operation_id="postAreas",
    responses={
        "201": {
            "description": "Areas successfully processed and saved",
        },
        "400": {
            "description": "Bad Request - Validation error in submitted data",
        },
        "401": {
            "model": UnauthorizedError,
            "description": "Unauthorized - Invalid or missing token",
        },
        "403": {
            "description": "Forbidden - Missing required authorization roles",
        },
        "409": {
            "description": "Conflict - Duplicate area (same area_id) or constraint violation",
        },
    },
)
async def post_areas(
    data: AreaListRequest,
    session: AsyncSession = Depends(get_async_db),
    token_payload: dict[str, Any] = Depends(verify_bearer_token),
) -> dict[str, str]:
    """
    Submit multiple geographical areas for processing.

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
    - Requires valid bearer token with "sdep_ca" and "sdep_write" roles in realm_access
    - Competent authority ID is extracted from token's "client_id" claim
    - Competent authority name is extracted from token's "client_name" claim

    Request Body:
    - metadata: Batch-level metadata (placeholder for future use)
    - areas: List of areas (minimum 1 required, maximum 100)
    - Each area contains:
      - areaId: Optional area identifier (auto-generated if not provided)
      - filename: Filename of the shapefile
      - filedata: Base64-encoded binary file data (e.g., base64-encoded .zip with ESRI shapefile files)
        Example (bash): base64 -w 0 file.zip
        Example (Python): base64.b64encode(file_bytes).decode('utf-8')

    Note: Competent authority ID and name (from token) are normalized to each area at the API layer
    before passing to service layer. This keeps service layer focused on business logic. The competent
    authority is created automatically if it doesn't exist yet.

    Returns:
        Success message with count of processed areas

    Raises:
        HTTPException 400: Validation error
        HTTPException 403: Forbidden - Missing required authorization roles
        HTTPException 409: Duplicate area or constraint violation
        HTTPException 500: Internal server error
    """

    # Authorization check: Verify user has "sdep_ca" and "sdep_write" roles
    realm_access = token_payload.get("realm_access", {})
    roles = realm_access.get("roles", [])

    if "sdep_ca" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: 'sdep_ca' role required",
        )

    if "sdep_write" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: 'sdep_write' role required",
        )

    # Extract competent authority ID and name from token
    # competentAuthorityId comes from client_id claim
    competent_authority_id = token_payload.get("client_id")
    if not competent_authority_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing 'client_id' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # competentAuthorityName comes from client_name claim
    competent_authority_name = token_payload.get("client_name")
    if not competent_authority_name:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing 'client_name' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Convert Pydantic models to service layer format
        # Competent authority ID and name are extracted from the token, not from the request payload
        areas_list = data.to_service_list(
            competent_authority_id=competent_authority_id,
            competent_authority_name=competent_authority_name,
        )

        # Call service layer with injected session
        # Transaction is managed by get_async_db dependency (auto-commit on success)
        await area_service.process_area_list(session, areas_list)

        return {
            "message": f"Successfully processed {len(data.areas)} area(s)"
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
            detail="Failed to process areas",
        ) from e
