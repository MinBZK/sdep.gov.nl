"""CA Area endpoints.

Transaction Management Architecture (API Layer):
- This API endpoint uses get_async_db_manual_commit for manual transaction management
- Service layer uses nested transactions (savepoints) for partial success/failure support
- API layer performs manual commit if any areas succeeded
- CRUD layer only flushes, never commits

Pattern:
- API layer: Transaction boundary (manual commit)
- Service layer: Business logic with savepoints (nested transactions)
- CRUD layer: Data access (flush only, no commits)
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.config import get_async_db_manual_commit
from app.exceptions.business import BusinessLogicError, DuplicateResourceError
from app.exceptions.validation import ValidationError
from app.schemas.area import (
    AreaErrorDetail,
    AreaListRequest,
    AreaProcessingResponse,
    AreaRequest,
    FailedArea,
    SuccessfulArea,
)
from app.schemas.auth import UnauthorizedError
from app.security import verify_bearer_token
from app.services import area as area_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ca"])


@router.post(
    "/ca/areas",
    summary="Submit areas (bulk) for the current authenticated competent authority",
    description="""Submit areas (bulk) for the current authenticated competent authority (competentAuthorityId).

**ID Pattern:**
- `areaId`: provided by client as business identitifer (optional), otherwise generated as UUID (RFC 9562 compliant)
- `areaName` (optional): Human-readable name (max 128 chars)

**Versioning:**
- Same `areaId` can be resubmitted → creates new version with different timestamp
- Unique constraint: (areaId, createdAt)

**Processing:**

- Areas are processed independently, typically using nested transactions (savepoints)
- Each area is validated and processed separately, allowing some to succeed while others can fail

**Limiting:**

- Min. 1 records per request
- Max. 1,000 records per request
- Max. 1 MiB (1,048,576 bytes) per filedata field
- This to ensure predictable performance, reduce abuse risk, control transaction size, and improve overall reliability and error handling

**Response Codes:**
- **201 Created:** All areas processed successfully
- **200 OK:** Mixed results - some areas succeeded, some failed
- **422 Unprocessable Entity:** All areas failed (or validation error)
- **401 Unauthorized:** Invalid or missing authentication token
- **403 Forbidden:** Missing required authorization roles

**Response Structure:**
Returns detailed results including:
- `successes`: Array of successfully created areas (always present, even if empty)
  - Each entry contains: `areaIndex` (0-based position in original request), `area` object (original request data with generated `areaId`)
- `failures`: Array of failed areas (always present, even if empty)
  - Each entry contains: `areaIndex` (0-based position in original request), `area` object (original request data), `errors` array (validation/processing errors)
- Summary counts: `totalProcessed`, `succeeded`, `failed`

**Note:** The `areaIndex` values are unique and mutually exclusive between `successes` and `failures` - each index appears in exactly one array, representing whether that specific request item succeeded or failed.

**Example:** If request contains 5 areas [0,1,2,3,4] and items at positions 0,2,4 succeed while 1,3 fail:
- `successes` will contain entries with `areaIndex` values: 0, 2, 4
- `failures` will contain entries with `areaIndex` values: 1, 3
""",
    operation_id="postAreas",
    response_model=AreaProcessingResponse,
    responses={
        "200": {
            "description": "Partial success - some areas succeeded, some failed",
            "model": AreaProcessingResponse,
            "content": {
                "application/json": {
                    "example": {
                        "message": "Processed 5 areas: 3 succeeded, 2 failed",
                        "totalProcessed": 5,
                        "succeeded": 3,
                        "failed": 2,
                        "successes": [
                            {
                                "areaIndex": 0,
                                "area": {
                                    "areaId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                                    "areaName": "Amsterdam Central",
                                    "filename": "Amsterdam.zip",
                                    "filedata": "UEsDBBQAAAA...",
                                },
                            },
                            {
                                "areaIndex": 2,
                                "area": {
                                    "areaId": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
                                    "filename": "Rotterdam.zip",
                                    "filedata": "UEsDBBQAAAA...",
                                },
                            },
                            {
                                "areaIndex": 4,
                                "area": {
                                    "areaId": "f9e8d7c6-b5a4-3210-fedc-ba9876543210",
                                    "filename": "Utrecht.zip",
                                    "filedata": "UEsDBBQAAAA...",
                                },
                            },
                        ],
                        "failures": [
                            {
                                "areaIndex": 1,
                                "area": {
                                    "filename": "Invalid.zip",
                                    "filedata": "corrupted...",
                                },
                                "errors": [
                                    {
                                        "loc": ["areas", 1, "filedata"],
                                        "msg": "Invalid file format",
                                        "type": "value_error",
                                    }
                                ],
                            },
                            {
                                "areaIndex": 3,
                                "area": {
                                    "areaId": "duplicate-id",
                                    "filename": "Duplicate.zip",
                                    "filedata": "UEsDBBQAAAA...",
                                },
                                "errors": [
                                    {
                                        "loc": ["areas", 3],
                                        "msg": "Duplicate area ID",
                                        "type": "integrity_error",
                                    }
                                ],
                            },
                        ],
                    }
                }
            },
        },
        "201": {
            "description": "Complete success - all areas processed successfully",
            "model": AreaProcessingResponse,
            "content": {
                "application/json": {
                    "example": {
                        "message": "Processed 3 areas: 3 succeeded, 0 failed",
                        "totalProcessed": 3,
                        "succeeded": 3,
                        "failed": 0,
                        "successes": [
                            {
                                "areaIndex": 0,
                                "area": {
                                    "areaId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                                    "areaName": "Amsterdam Central",
                                    "filename": "Amsterdam.zip",
                                    "filedata": "UEsDBBQAAAA...",
                                },
                            },
                            {
                                "areaIndex": 1,
                                "area": {
                                    "areaId": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
                                    "filename": "Rotterdam.zip",
                                    "filedata": "UEsDBBQAAAA...",
                                },
                            },
                            {
                                "areaIndex": 2,
                                "area": {
                                    "areaId": "f9e8d7c6-b5a4-3210-fedc-ba9876543210",
                                    "filename": "Utrecht.zip",
                                    "filedata": "UEsDBBQAAAA...",
                                },
                            },
                        ],
                        "failures": [],
                    }
                }
            },
        },
        "401": {
            "model": UnauthorizedError,
            "description": "Unauthorized - Invalid or missing token",
        },
        "403": {
            "description": "Forbidden - Missing required authorization roles",
        },
        "422": {
            "description": "Unprocessable Entity - All areas failed (or Pydantic validation error)",
            "model": AreaProcessingResponse,
            "content": {
                "application/json": {
                    "example": {
                        "message": "Processed 2 areas: 0 succeeded, 2 failed",
                        "totalProcessed": 2,
                        "succeeded": 0,
                        "failed": 2,
                        "successes": [],
                        "failures": [
                            {
                                "areaIndex": 0,
                                "area": {
                                    "filename": "Invalid1.zip",
                                    "filedata": "corrupted...",
                                },
                                "errors": [
                                    {
                                        "loc": ["areas", 0, "filedata"],
                                        "msg": "Invalid file format",
                                        "type": "value_error",
                                    }
                                ],
                            },
                            {
                                "areaIndex": 1,
                                "area": {
                                    "filename": "Invalid2.zip",
                                    "filedata": "corrupted...",
                                },
                                "errors": [
                                    {
                                        "loc": ["areas", 1, "filename"],
                                        "msg": "Filename too short",
                                        "type": "string_too_short",
                                    }
                                ],
                            },
                        ],
                    }
                }
            },
        },
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["areas"],
                        "properties": {
                            "areas": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 1000,
                                "items": {"$ref": "#/components/schemas/AreaRequest"},
                            }
                        },
                    },
                    "examples": {
                        "valid_example": {
                            "summary": "Valid areas",
                            "value": {
                                "areas": [
                                    {
                                        "areaId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                                        "areaName": "Amsterdam Central District",
                                        "filename": "Amsterdam.zip",
                                        "filedata": "UEsDBBQAAAAIAG1heFkAAAAAAAAAAAAAAAAOAAAAQW1zdGVyZGFtLnNocA==",
                                    }
                                ]
                            },
                        }
                    },
                }
            },
        }
    },
)
async def post_areas(
    request: Request,
    session: AsyncSession = Depends(get_async_db_manual_commit),
    token_payload: dict[str, Any] = Depends(verify_bearer_token),
) -> Response:
    """
    Submit areas for processing with partial success/failure support.

    Transaction Management:
    - Uses get_async_db_manual_commit for manual transaction control
    - Service layer uses nested transactions (savepoints) for each area
    - Manual commit at end if any areas succeeded
    - Manual rollback on unexpected exceptions

    System Crash Behavior:
    - If system crashes BEFORE commit, ALL changes are lost
    - Example: 7 areas total, 5 processed (2 succeeded, 3 failed), system crashes:
      * Result: ALL 5 areas rolled back (including the 2 that "succeeded")
      * PostgreSQL automatically rolls back uncommitted transactions on connection loss
      * Savepoints only protect against individual area failures, NOT system crashes
      * All 7 areas must be resubmitted after recovery

    Processing Approach:
    - Phase 0: Collect Pydantic validation errors
    - Phase 1: Validate all areas (business logic)
    - Phase 2: Process valid areas using savepoints
    - Each area can succeed or fail independently

    HTTP Status Codes:
    - 200 OK: Partial success - at least one area succeeded AND at least one failed
    - 201 Created: Complete success - all areas processed successfully
    - 401 Unauthorized: Authentication failure
    - 403 Forbidden: Authorization failure (missing sdep_ca or sdep_write role)
    - 422 Unprocessable Entity: Complete failure - no areas succeeded
    - 500 Internal Server Error: Unexpected system error

    Authorization:
    - Requires valid bearer token with "sdep_ca" and "sdep_write" roles
    - Competent authority ID extracted from token's "client_id" claim
    - Competent authority name extracted from token's "client_name" claim

    Args:
        request: FastAPI Request object for manual body parsing
        session: AsyncSession with manual commit mode
        token_payload: JWT token payload from bearer token

    Returns:
        AreaProcessingResponse with processing results

    Raises:
        HTTPException 401: Unauthorized - Invalid or missing token
        HTTPException 403: Forbidden - Missing required authorization roles
        HTTPException 422: All areas failed (Pydantic validation is automatic)
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
    competent_authority_id = token_payload.get("client_id")
    if not competent_authority_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing 'client_id' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    competent_authority_name = token_payload.get("client_name")
    if not competent_authority_name:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing 'client_name' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Parse request body manually to collect both Pydantic and business logic errors
        body = await request.json()

        # Track Pydantic validation errors per area
        pydantic_errors_by_index: dict[int, list[dict]] = {}
        validated_data: AreaListRequest | None = None

        # Attempt Pydantic validation
        top_level_errors = []
        try:
            validated_data = AreaListRequest(**body)
        except PydanticValidationError as pydantic_exc:
            # Extract errors and group by area index
            for error in pydantic_exc.errors():
                # Error location format: ('areas', index, 'field', ...) for area errors
                # or ('areas',) or ('metadata',) for top-level errors
                if len(error["loc"]) >= 2 and error["loc"][0] == "areas":
                    area_index = int(error["loc"][1])
                    if area_index not in pydantic_errors_by_index:
                        pydantic_errors_by_index[area_index] = []
                    pydantic_errors_by_index[area_index].append(
                        {
                            "loc": list(error["loc"]),
                            "msg": error["msg"],
                            "type": error.get("type", "validation_error"),
                        }
                    )
                else:
                    # Top-level validation error (e.g., empty list, missing metadata)
                    top_level_errors.append(error)

        # Handle top-level validation errors (e.g., empty areas list)
        if top_level_errors:
            # Return standard error response for top-level validation errors
            from datetime import UTC

            from app.schemas.error import ErrorDetail, ErrorResponse

            error_response = ErrorResponse(
                detail=[
                    ErrorDetail(
                        msg=error["msg"],
                        type=error.get("type", "validation_error"),
                    )
                    for error in top_level_errors
                ],
                timestamp=datetime.now(UTC),
                path=str(request.url.path),
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            )
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content=error_response.model_dump(mode="json"),
            )

        # Get areas list from body (even if Pydantic validation failed)
        areas_raw = body.get("areas", [])
        total_areas = len(areas_raw)

        if total_areas == 0:
            # This shouldn't happen if Pydantic validation worked, but handle it anyway
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="At least one area is required",
            )

        # Convert valid areas to service layer format
        # Invalid areas will be tracked with their Pydantic errors
        areas_dict = []
        if validated_data:
            # Pydantic validation succeeded - convert all areas
            areas_dict = validated_data.to_service_list(
                competent_authority_id=competent_authority_id,
                competent_authority_name=competent_authority_name,
            )
        else:
            # Pydantic validation failed - convert areas that passed validation
            # and create placeholder dicts for failed ones
            for idx, area_raw in enumerate(areas_raw):
                if idx in pydantic_errors_by_index:
                    # This area failed Pydantic validation
                    # Create a minimal dict with the raw data for error reporting
                    areas_dict.append(
                        {
                            "_pydantic_validation_failed": True,
                            "_raw_data": area_raw,
                            "competent_authority_id_str": competent_authority_id,
                            "competent_authority_name": competent_authority_name,
                        }
                    )
                else:
                    # This area passed Pydantic validation - convert it
                    try:
                        area_validated = AreaRequest(**area_raw)
                        areas_dict.append(
                            area_validated.to_service_dict(
                                competent_authority_id=competent_authority_id,
                                competent_authority_name=competent_authority_name,
                            )
                        )
                    except PydanticValidationError:
                        # Shouldn't happen, but handle it gracefully
                        areas_dict.append(
                            {
                                "_pydantic_validation_failed": True,
                                "_raw_data": area_raw,
                                "competent_authority_id_str": competent_authority_id,
                                "competent_authority_name": competent_authority_name,
                            }
                        )

        # Call service layer with manual commit session
        # Service handles nested transactions (savepoints)
        # Pass Pydantic errors so they can be included in the response
        result = await area_service.process_area_list(
            session, areas_dict, pydantic_errors_by_index
        )

        # Commit the transaction if any areas succeeded
        # If no areas succeeded, don't commit - the transaction will be
        # automatically rolled back when the session closes
        #
        # If system crashes BEFORE this commit executes, ALL changes
        # are lost (even areas that "succeeded" in their savepoints).
        # PostgreSQL rolls back uncommitted transactions on connection loss.
        if result["succeeded"] > 0:
            await session.commit()

        # Build response
        total = result["total_processed"]
        succeeded = result["succeeded"]
        failed = result["failed"]

        # Convert failures to response schema format
        failed_areas = []
        for failure in result["failures"]:
            area_dict = failure["area"]

            # Check if this is a Pydantic validation failure (has _raw_data)
            if area_dict.get("_pydantic_validation_failed"):
                # For Pydantic failures, use the raw data without validation
                # Validation errors are already captured in the errors array
                raw_data = area_dict.get("_raw_data", {})

                area_request = AreaRequest.model_construct(**raw_data)
            else:
                # Convert back from service dict to request schema (business logic failure)
                area_request = AreaRequest(
                    **{
                        "areaId": area_dict.get("area_id"),
                        "areaName": area_dict.get("area_name"),
                        "filename": area_dict["filename"],
                        "filedata": area_dict["filedata"],
                    }
                )

            failed_areas.append(
                FailedArea(
                    areaIndex=failure["area_index"],
                    area=area_request,
                    errors=[AreaErrorDetail(**error) for error in failure["errors"]],
                )
            )

        # Convert successes to response schema format
        successful_areas = []
        for success in result["successes"]:
            area_dict = success["area"]

            # Convert back from service dict to request schema
            # Include the generated ID in the area object
            area_request = AreaRequest(
                **{
                    "areaId": success["area_id"],  # Use the generated ID
                    "areaName": area_dict.get("area_name"),
                    "filename": area_dict["filename"],
                    "filedata": area_dict["filedata"],
                }
            )

            successful_areas.append(
                SuccessfulArea(
                    areaIndex=success["area_index"],
                    area=area_request,
                )
            )

        response = AreaProcessingResponse(
            message=f"Processed {total} areas: {succeeded} succeeded, {failed} failed",
            totalProcessed=total,
            succeeded=succeeded,
            failed=failed,
            successes=successful_areas,
            failures=failed_areas,
        )

        # Determine HTTP status code
        if failed == 0:
            # All succeeded - 201 Created
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content=response.model_dump(by_alias=True, mode="json"),
            )
        elif succeeded == 0:
            # All failed - 422 Unprocessable Entity
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content=response.model_dump(by_alias=True, mode="json"),
            )
        else:
            # Mixed results - 200 OK
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=response.model_dump(by_alias=True, mode="json"),
            )

    except DuplicateResourceError as e:
        # Should not reach here (handled in service layer)
        await session.rollback()
        raise e
    except BusinessLogicError as e:
        # Should not reach here (handled in service layer)
        await session.rollback()
        raise e
    except ValidationError as e:
        # Should not reach here (Pydantic validates)
        await session.rollback()
        raise e
    except Exception as e:
        # Unexpected errors - rollback and raise
        await session.rollback()
        logger.error(f"Unexpected error processing areas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process areas",
        ) from e
