"""STR activities endpoint.

Transaction Management Architecture (API Layer):
- This API endpoint uses get_async_db_manual_commit for manual transaction management
- Service layer uses nested transactions (savepoints) for partial success/failure support
- API layer performs manual commit if any activities succeeded
- CRUD layer only flushes, never commits

Pattern:
- API layer: Transaction boundary (manual commit)
- Service layer: Business logic with savepoints (nested transactions)
- CRUD layer: Data access (flush only, no commits)
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.config import get_async_db_manual_commit
from app.exceptions.business import BusinessLogicError, DuplicateResourceError
from app.exceptions.validation import ValidationError
from app.schemas.activity import (
    ActivityErrorDetail,
    ActivityListRequest,
    ActivityProcessingResponse,
    ActivityRequest,
    FailedActivity,
    SuccessfulActivity,
)
from app.schemas.auth import UnauthorizedError
from app.security import verify_bearer_token
from app.services import activity as activity_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["str"])


@router.post(
    "/str/activities",
    summary="Submit activities (bulk) for the current authenticated platform",
    description="""Submit activities (bulk) for the current authenticated platform (platformId).

**ID Pattern:**
- `activityId: provided by client as business identitifer (optional), otherwise generated as UUID (RFC 9562 compliant)
- `activityName` (optional): Human-readable name (max 128 chars)
- `areaId` (required): Functional ID referencing existing area

**Versioning:**
- Same `activityId` can be resubmitted → creates new version with different timestamp
- Unique constraint: (activityId, createdAt)

**Processing:**

- Activities are processed independently using nested transactions (savepoints)
- Each activity is validated and processed separately, allowing some to succeed while others can fail

**Limiting:**

- Min. 1 records per request
- Max. 1,000 records per request
- This to ensure predictable performance, control transaction size, and improve overall reliability and error handling

**Response Codes:**
- **201 Created:** All activities processed successfully
- **200 OK:** Mixed results - some activities succeeded, some failed
- **422 Unprocessable Entity:** All activities failed (or validation error)
- **401 Unauthorized:** Invalid or missing authentication token
- **403 Forbidden:** Missing required authorization roles

**Response Structure:**
Returns detailed results including:
- `successes`: Array of successfully created activities (always present, even if empty)
  - Each entry contains: `activityIndex` (0-based position in original request), `activity` object (original request data with generated `activityId`)
- `failures`: Array of failed activities (always present, even if empty)
  - Each entry contains: `activityIndex` (0-based position in original request), `activity` object (original request data), `errors` array (validation/processing errors)
- Summary counts: `totalProcessed`, `succeeded`, `failed`

**Note:** The `activityIndex` values are unique and mutually exclusive between `successes` and `failures` - each index appears in exactly one array, representing whether that specific request item succeeded or failed.

**Example:** If request contains 5 activities [0,1,2,3,4] and items at positions 0,2,4 succeed while 1,3 fail:
- `successes` will contain entries with `activityIndex` values: 0, 2, 4
- `failures` will contain entries with `activityIndex` values: 1, 3""",
    operation_id="postActivity",
    response_model=ActivityProcessingResponse,
    responses={
        "200": {
            "description": "Partial success - some activities succeeded, some failed",
            "model": ActivityProcessingResponse,
            "content": {
                "application/json": {
                    "example": {
                        "message": "Processed 5 activities: 3 succeeded, 2 failed",
                        "totalProcessed": 5,
                        "succeeded": 3,
                        "failed": 2,
                        "successes": [
                            {
                                "activityIndex": 0,
                                "activity": {
                                    "activityId": "550e8400-e29b-41d4-a716-446655440000",
                                    "activityName": "Amsterdam Summer Rental",
                                    "areaId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                                    "url": "http://example.com/listing-001",
                                    "address": {
                                        "street": "Prinsengracht",
                                        "number": 263,
                                        "postalCode": "1016HV",
                                        "city": "Amsterdam",
                                    },
                                    "registrationNumber": "REG0001",
                                    "temporal": {
                                        "startDatetime": "2025-06-01T14:00:00Z",
                                        "endDatetime": "2025-06-07T11:00:00Z",
                                    },
                                },
                            },
                            {
                                "activityIndex": 2,
                                "activity": {
                                    "activityId": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
                                    "areaId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                                    "url": "http://example.com/listing-003",
                                    "address": {
                                        "street": "Keizersgracht",
                                        "number": 123,
                                        "postalCode": "1015CJ",
                                        "city": "Amsterdam",
                                    },
                                    "registrationNumber": "REG0003",
                                    "temporal": {
                                        "startDatetime": "2025-07-01T14:00:00Z",
                                        "endDatetime": "2025-07-07T11:00:00Z",
                                    },
                                },
                            },
                            {
                                "activityIndex": 4,
                                "activity": {
                                    "activityId": "f9e8d7c6-b5a4-3210-fedc-ba9876543210",
                                    "areaId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                                    "url": "http://example.com/listing-005",
                                    "address": {
                                        "street": "Herengracht",
                                        "number": 456,
                                        "postalCode": "1017BV",
                                        "city": "Amsterdam",
                                    },
                                    "registrationNumber": "REG0005",
                                    "temporal": {
                                        "startDatetime": "2025-08-01T14:00:00Z",
                                        "endDatetime": "2025-08-07T11:00:00Z",
                                    },
                                },
                            },
                        ],
                        "failures": [
                            {
                                "activityIndex": 1,
                                "activity": {
                                    "areaId": "invalid-area-id",
                                    "url": "http://example.com/listing-002",
                                    "address": {
                                        "street": "Test Street",
                                        "number": 1,
                                        "postalCode": "1000AA",
                                        "city": "Amsterdam",
                                    },
                                    "registrationNumber": "REG0002",
                                    "temporal": {
                                        "startDatetime": "2025-06-15T14:00:00Z",
                                        "endDatetime": "2025-06-20T11:00:00Z",
                                    },
                                },
                                "errors": [
                                    {
                                        "loc": ["activities", 1, "areaId"],
                                        "msg": "Area with areaId 'invalid-area-id' not found",
                                        "type": "business_logic_error",
                                    }
                                ],
                            },
                            {
                                "activityIndex": 3,
                                "activity": {
                                    "areaId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                                    "url": "invalid-url",
                                    "address": {
                                        "street": "Test Street",
                                        "number": 2,
                                        "postalCode": "1000BB",
                                        "city": "Amsterdam",
                                    },
                                    "registrationNumber": "REG0004",
                                    "temporal": {
                                        "startDatetime": "2025-07-15T14:00:00Z",
                                        "endDatetime": "2025-07-20T11:00:00Z",
                                    },
                                },
                                "errors": [
                                    {
                                        "loc": ["activities", 3, "url"],
                                        "msg": "Invalid URL format",
                                        "type": "value_error",
                                    }
                                ],
                            },
                        ],
                    }
                }
            },
        },
        "201": {
            "description": "Complete success - all activities processed successfully",
            "model": ActivityProcessingResponse,
            "content": {
                "application/json": {
                    "example": {
                        "message": "Processed 3 activities: 3 succeeded, 0 failed",
                        "totalProcessed": 3,
                        "succeeded": 3,
                        "failed": 0,
                        "successes": [
                            {
                                "activityIndex": 0,
                                "activity": {
                                    "activityId": "550e8400-e29b-41d4-a716-446655440000",
                                    "activityName": "Amsterdam Summer Rental",
                                    "areaId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                                    "url": "http://example.com/listing-001",
                                    "address": {
                                        "street": "Prinsengracht",
                                        "number": 263,
                                        "postalCode": "1016HV",
                                        "city": "Amsterdam",
                                    },
                                    "registrationNumber": "REG0001",
                                    "temporal": {
                                        "startDatetime": "2025-06-01T14:00:00Z",
                                        "endDatetime": "2025-06-07T11:00:00Z",
                                    },
                                },
                            },
                            {
                                "activityIndex": 1,
                                "activity": {
                                    "activityId": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
                                    "areaId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                                    "url": "http://example.com/listing-002",
                                    "address": {
                                        "street": "Keizersgracht",
                                        "number": 123,
                                        "postalCode": "1015CJ",
                                        "city": "Amsterdam",
                                    },
                                    "registrationNumber": "REG0002",
                                    "temporal": {
                                        "startDatetime": "2025-07-01T14:00:00Z",
                                        "endDatetime": "2025-07-07T11:00:00Z",
                                    },
                                },
                            },
                            {
                                "activityIndex": 2,
                                "activity": {
                                    "activityId": "f9e8d7c6-b5a4-3210-fedc-ba9876543210",
                                    "areaId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                                    "url": "http://example.com/listing-003",
                                    "address": {
                                        "street": "Herengracht",
                                        "number": 456,
                                        "postalCode": "1017BV",
                                        "city": "Amsterdam",
                                    },
                                    "registrationNumber": "REG0003",
                                    "temporal": {
                                        "startDatetime": "2025-08-01T14:00:00Z",
                                        "endDatetime": "2025-08-07T11:00:00Z",
                                    },
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
            "description": "Unprocessable Entity - All activities failed (or Pydantic validation error)",
            "model": ActivityProcessingResponse,
            "content": {
                "application/json": {
                    "example": {
                        "message": "Processed 2 activities: 0 succeeded, 2 failed",
                        "totalProcessed": 2,
                        "succeeded": 0,
                        "failed": 2,
                        "successes": [],
                        "failures": [
                            {
                                "activityIndex": 0,
                                "activity": {
                                    "areaId": "invalid-area-id",
                                    "url": "http://example.com/listing-001",
                                    "address": {
                                        "street": "Test Street",
                                        "number": 1,
                                        "postalCode": "1000AA",
                                        "city": "Amsterdam",
                                    },
                                    "registrationNumber": "REG0001",
                                    "temporal": {
                                        "startDatetime": "2025-06-01T14:00:00Z",
                                        "endDatetime": "2025-06-07T11:00:00Z",
                                    },
                                },
                                "errors": [
                                    {
                                        "loc": ["activities", 0, "areaId"],
                                        "msg": "Area with areaId 'invalid-area-id' not found",
                                        "type": "business_logic_error",
                                    }
                                ],
                            },
                            {
                                "activityIndex": 1,
                                "activity": {
                                    "areaId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                                    "url": "invalid-url",
                                    "address": {
                                        "street": "Test Street",
                                        "number": 2,
                                        "postalCode": "1000BB",
                                        "city": "Amsterdam",
                                    },
                                    "registrationNumber": "REG0002",
                                    "temporal": {
                                        "startDatetime": "2025-07-01T14:00:00Z",
                                        "endDatetime": "2025-07-07T11:00:00Z",
                                    },
                                },
                                "errors": [
                                    {
                                        "loc": ["activities", 1, "url"],
                                        "msg": "Invalid URL format",
                                        "type": "value_error",
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
                        "required": ["activities"],
                        "properties": {
                            "activities": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 1000,
                                "items": {
                                    "$ref": "#/components/schemas/ActivityRequest"
                                },
                            }
                        },
                    },
                    "examples": {
                        "valid_example": {
                            "summary": "Valid activities",
                            "value": {
                                "activities": [
                                    {
                                        "activityId": "550e8400-e29b-41d4-a716-446655440000",
                                        "activityName": "Amsterdam Summer Rental 2025",
                                        "areaId": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                                        "url": "http://example.com/listing-001",
                                        "address": {
                                            "street": "Prinsengracht",
                                            "number": 263,
                                            "letter": "a",
                                            "addition": "5h",
                                            "postalCode": "1016HV",
                                            "city": "Amsterdam",
                                        },
                                        "registrationNumber": "REG0001",
                                        "numberOfGuests": 4,
                                        "countryOfGuests": ["NLD", "DEU", "BEL"],
                                        "temporal": {
                                            "startDatetime": "2025-06-01T14:00:00Z",
                                            "endDatetime": "2025-06-07T11:00:00Z",
                                        },
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
async def post_activities(
    request: Request,
    session: AsyncSession = Depends(get_async_db_manual_commit),
    token_payload: dict[str, Any] = Depends(verify_bearer_token),
) -> ActivityProcessingResponse:
    """
    Submit rental activities for processing with partial success/failure support.

    Transaction Management:
    - Uses get_async_db_manual_commit for manual transaction control
    - Service layer uses nested transactions (savepoints) for each activity
    - Manual commit at end if any activities succeeded
    - Manual rollback on unexpected exceptions

    System Crash Behavior:
    - If system crashes BEFORE commit, ALL changes are lost
    - Example: 7 activities total, 5 processed (2 succeeded, 3 failed), system crashes:
      * Result: ALL 5 activities rolled back (including the 2 that "succeeded")
      * PostgreSQL automatically rolls back uncommitted transactions on connection loss
      * Savepoints only protect against individual activity failures, NOT system crashes
      * All 7 activities must be resubmitted after recovery

    Processing Approach:
    - Phase 1: Validate all activities (business logic)
    - Phase 2: Process valid activities using savepoints
    - Each activity can succeed or fail independently

    HTTP Status Codes:
    - 200 OK: Partial success - at least one activity succeeded AND at least one failed
      * Returns ActivityProcessingResponse with detailed breakdown
      * Example: 7 activities → 4 succeeded, 3 failed
    - 201 Created: Complete success - all activities processed successfully
      * Returns ActivityProcessingResponse with succeeded count
      * Example: 7 activities → 7 succeeded, 0 failed
    - 401 Unauthorized: Authentication failure
      * Invalid bearer token
      * Missing bearer token
      * Token missing required claims (client_id, client_name)
    - 403 Forbidden: Authorization failure
      * Missing "sdep_str" role in token
      * Missing "sdep_write" role in token
    - 422 Unprocessable Entity: Complete failure - no activities succeeded
      * All activities failed validation or processing
      * Returns ActivityProcessingResponse with detailed failure information
      * Example: 7 activities → 0 succeeded, 7 failed
      * Also returned by FastAPI for Pydantic validation errors (before endpoint is called)
    - 500 Internal Server Error: Unexpected system error
      * Database connection failures
      * Unexpected exceptions during processing

    Authorization:
    - Requires valid bearer token with "sdep_str" and "sdep_write" roles
    - Platform ID extracted from token's "client_id" claim
    - Platform name extracted from token's "client_name" claim

    Args:
        data: ActivityListRequest containing metadata and list of activities
        session: AsyncSession with manual commit mode
        token_payload: JWT token payload from bearer token

    Returns:
        ActivityProcessingResponse with processing results

    Raises:
        HTTPException 401: Unauthorized - Invalid or missing token
        HTTPException 403: Forbidden - Missing required authorization roles
        HTTPException 422: All activities failed (Pydantic validation is automatic)
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
    platform_id = token_payload.get("client_id")
    if not platform_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing 'client_id' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    platform_name = token_payload.get("client_name")
    if not platform_name:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing 'client_name' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Parse request body manually to collect both Pydantic and business logic errors
        body = await request.json()

        # Track Pydantic validation errors per activity
        pydantic_errors_by_index: dict[int, list[dict]] = {}
        validated_data: ActivityListRequest | None = None

        # Attempt Pydantic validation
        top_level_errors = []
        try:
            validated_data = ActivityListRequest(**body)
        except PydanticValidationError as pydantic_exc:
            # Extract errors and group by activity index
            for error in pydantic_exc.errors():
                # Error location format: ('activities', index, 'field', ...) for activity errors
                # or ('activities',) or ('metadata',) for top-level errors
                if len(error["loc"]) >= 2 and error["loc"][0] == "activities":
                    activity_index = error["loc"][1]
                    if activity_index not in pydantic_errors_by_index:
                        pydantic_errors_by_index[activity_index] = []
                    pydantic_errors_by_index[activity_index].append(
                        {
                            "loc": list(error["loc"]),
                            "msg": error["msg"],
                            "type": error.get("type", "validation_error"),
                        }
                    )
                else:
                    # Top-level validation error (e.g., empty list, missing metadata)
                    top_level_errors.append(error)

        # Handle top-level validation errors (e.g., empty activities list)
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

        # Get activities list from body (even if Pydantic validation failed)
        activities_raw = body.get("activities", [])
        total_activities = len(activities_raw)

        if total_activities == 0:
            # This shouldn't happen if Pydantic validation worked, but handle it anyway
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="At least one activity is required",
            )

        # Convert valid activities to service layer format
        # Invalid activities will be tracked with their Pydantic errors
        activities_dict = []
        if validated_data:
            # Pydantic validation succeeded - convert all activities
            activities_dict = validated_data.to_service_list(
                platform_id=platform_id, platform_name=platform_name
            )
        else:
            # Pydantic validation failed - convert activities that passed validation
            # and create placeholder dicts for failed ones
            for idx, activity_raw in enumerate(activities_raw):
                if idx in pydantic_errors_by_index:
                    # This activity failed Pydantic validation
                    # Create a minimal dict with the raw data for error reporting
                    activities_dict.append(
                        {
                            "_pydantic_validation_failed": True,
                            "_raw_data": activity_raw,
                            "platform_id": platform_id,
                            "platform_name": platform_name,
                        }
                    )
                else:
                    # This activity passed Pydantic validation - convert it
                    try:
                        activity_validated = ActivityRequest(**activity_raw)
                        activities_dict.append(
                            activity_validated.to_service_dict(
                                platform_id=platform_id, platform_name=platform_name
                            )
                        )
                    except PydanticValidationError:
                        # Shouldn't happen, but handle it gracefully
                        activities_dict.append(
                            {
                                "_pydantic_validation_failed": True,
                                "_raw_data": activity_raw,
                                "platform_id": platform_id,
                                "platform_name": platform_name,
                            }
                        )

        # Call service layer with manual commit session
        # Service handles nested transactions (savepoints)
        # Pass Pydantic errors so they can be included in the response
        result = await activity_service.process_activity_list(
            session, activities_dict, pydantic_errors_by_index
        )

        # Commit the transaction if any activities succeeded
        # If no activities succeeded, don't commit - the transaction will be
        # automatically rolled back when the session closes
        #
        # If system crashes BEFORE this commit executes, ALL changes
        # are lost (even activities that "succeeded" in their savepoints).
        # PostgreSQL rolls back uncommitted transactions on connection loss.
        if result["succeeded"] > 0:
            await session.commit()

        # Build response
        total = result["total_processed"]
        succeeded = result["succeeded"]
        failed = result["failed"]

        # Convert failures to response schema format
        failed_activities = []
        for failure in result["failures"]:
            activity_dict = failure["activity"]

            # Check if this is a Pydantic validation failure (has _raw_data)
            if activity_dict.get("_pydantic_validation_failed"):
                # For Pydantic failures, use the raw data without validation
                # Validation errors are already captured in the errors array
                raw_data = activity_dict.get("_raw_data", {})

                # Import nested model types
                from datetime import datetime as dt

                from app.schemas.activity import AddressRequest, TemporalRequest

                # Parse datetime strings to avoid serialization warnings
                # Other type mismatches (e.g., str instead of int) are left as-is
                # since they represent the actual invalid data the user submitted
                def parse_datetime(dt_str):
                    """Parse ISO datetime string to datetime object."""
                    if not dt_str or not isinstance(dt_str, str):
                        return dt_str
                    try:
                        # Handle both 'Z' and timezone offset formats
                        return dt.fromisoformat(dt_str.replace("Z", "+00:00"))
                    except:
                        return dt_str  # Return as-is if parsing fails

                # Prepare temporal data with parsed datetimes
                temporal_data = raw_data.get("temporal", {})
                if temporal_data:
                    temporal_parsed = {
                        "startDatetime": parse_datetime(
                            temporal_data.get("startDatetime")
                        ),
                        "endDatetime": parse_datetime(temporal_data.get("endDatetime")),
                    }
                else:
                    temporal_parsed = None

                # Prepare address data (kept as-is, type mismatches are intentional)
                address_data = raw_data.get("address", {})

                activity_request = ActivityRequest.model_construct(
                    **{
                        **raw_data,
                        "address": AddressRequest.model_construct(**address_data)
                        if address_data
                        else None,
                        "temporal": TemporalRequest.model_construct(**temporal_parsed)
                        if temporal_parsed
                        else None,
                    }
                )
            else:
                # Convert back from service dict to request schema (business logic failure)
                activity_request = ActivityRequest(
                    **{
                        "platformActivityId": activity_dict.get("platform_activity_id"),
                        "url": activity_dict["url"],
                        "registrationNumber": activity_dict["registration_number"],
                        "address": {
                            "street": activity_dict["address_street"],
                            "number": activity_dict["address_number"],
                            "letter": activity_dict.get("address_letter"),
                            "addition": activity_dict.get("address_addition"),
                            "postalCode": activity_dict["address_postal_code"],
                            "city": activity_dict["address_city"],
                        },
                        "temporal": {
                            "startDatetime": activity_dict[
                                "temporal_start_date_time"
                            ].isoformat()
                            if isinstance(
                                activity_dict["temporal_start_date_time"], datetime
                            )
                            else activity_dict["temporal_start_date_time"],
                            "endDatetime": activity_dict[
                                "temporal_end_date_time"
                            ].isoformat()
                            if isinstance(
                                activity_dict["temporal_end_date_time"], datetime
                            )
                            else activity_dict["temporal_end_date_time"],
                        },
                        "areaId": activity_dict["area_id"],
                        "numberOfGuests": activity_dict.get("number_of_guests"),
                        "countryOfGuests": activity_dict.get("country_of_guests"),
                    }
                )

            failed_activities.append(
                FailedActivity(
                    activityIndex=failure["activity_index"],
                    activity=activity_request,
                    errors=[
                        ActivityErrorDetail(**error) for error in failure["errors"]
                    ],
                )
            )

        # Convert successes to response schema format
        successful_activities = []
        for success in result["successes"]:
            activity_dict = success["activity"]

            # Convert back from service dict to request schema
            # Include the generated ID in the activity object
            activity_request = ActivityRequest(
                **{
                    "activityId": success["activity_id"],  # Use the generated ID
                    "activityName": activity_dict.get("activity_name"),
                    "url": activity_dict["url"],
                    "registrationNumber": activity_dict["registration_number"],
                    "address": {
                        "street": activity_dict["address_street"],
                        "number": activity_dict["address_number"],
                        "letter": activity_dict.get("address_letter"),
                        "addition": activity_dict.get("address_addition"),
                        "postalCode": activity_dict["address_postal_code"],
                        "city": activity_dict["address_city"],
                    },
                    "temporal": {
                        "startDatetime": activity_dict[
                            "temporal_start_date_time"
                        ].isoformat()
                        if isinstance(
                            activity_dict["temporal_start_date_time"], datetime
                        )
                        else activity_dict["temporal_start_date_time"],
                        "endDatetime": activity_dict[
                            "temporal_end_date_time"
                        ].isoformat()
                        if isinstance(activity_dict["temporal_end_date_time"], datetime)
                        else activity_dict["temporal_end_date_time"],
                    },
                    "areaId": activity_dict["area_id"],
                    "numberOfGuests": activity_dict.get("number_of_guests"),
                    "countryOfGuests": activity_dict.get("country_of_guests"),
                }
            )

            successful_activities.append(
                SuccessfulActivity(
                    activityIndex=success["activity_index"],
                    activity=activity_request,
                )
            )

        response = ActivityProcessingResponse(
            message=f"Processed {total} activities: {succeeded} succeeded, {failed} failed",
            totalProcessed=total,
            succeeded=succeeded,
            failed=failed,
            successes=successful_activities,
            failures=failed_activities,
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
        logger.error(f"Unexpected error processing activities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process activities",
        ) from e
