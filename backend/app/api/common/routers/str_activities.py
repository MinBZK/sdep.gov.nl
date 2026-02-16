"""STR activities endpoint.

Transaction Management Architecture (API Layer):
- This API endpoint uses get_async_db for automatic transaction management
- Transaction commits automatically on success, rolls back on exception
- CRUD layer only flushes, never commits

Pattern:
- API layer: Transaction boundary (auto-commit via dependency)
- Service layer: Business logic (no transaction management)
- CRUD layer: Data access (flush only, no commits)
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.config import get_async_db, get_async_db_read_only
from app.schemas.activity import (
    ActivityCountResponse,
    ActivityOwnListResponse,
    ActivityOwnResponse,
    ActivityRequest,
    ActivityResponse,
    AddressResponse,
    TemporalResponse,
)
from app.schemas.auth import UnauthorizedError
from app.security import verify_bearer_token
from app.services import activity as activity_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["str"])


@router.post(
    "/str/activities",
    summary="Submit a single activity for the current authenticated platform",
    description="""Submit a single activity for the current authenticated platform (platformId).

**ID Pattern:**
- `activityId`: provided by platform as business identifier (optional), otherwise generated as UUID (RFC 9562 compliant)
- `activityName` (optional): human-readable name (max 64 chars)
- `areaId` (required): Functional ID referencing existing area

**Versioning:**
- Same `activityId` can be resubmitted → creates new version with different timestamp
- Unique constraint: (activityId, createdAt)

**Response Codes:**
- **201 Created:** Activity processed successfully
- **401 Unauthorized:** Invalid or missing authentication token
- **403 Forbidden:** Missing required authorization roles
- **422 Unprocessable Entity:** Validation error
""",
    operation_id="postActivity",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        "201": {
            "description": "Activity created successfully",
            "model": ActivityResponse,
        },
        "401": {
            "model": UnauthorizedError,
            "description": "Unauthorized - Invalid or missing token",
        },
        "403": {
            "description": "Forbidden - Missing required authorization roles",
        },
        "422": {
            "description": "Unprocessable Entity - Validation error",
        },
    },
)
async def post_activity(
    activity: ActivityRequest,
    session: AsyncSession = Depends(get_async_db),
    token_payload: dict[str, Any] = Depends(verify_bearer_token),
) -> Response:
    """
    Submit a single rental activity.

    Authorization:
    - Requires valid bearer token with "sdep_str" and "sdep_write" roles
    - Platform ID extracted from token's "client_id" claim
    - Platform name extracted from token's "client_name" claim
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

    # Convert request to service layer format
    activity_data = activity.to_service_dict(platform_id, platform_name)

    # Create activity via service layer
    activity_obj = await activity_service.create_activity(session, activity_data)

    # Eager-load relationships for response building
    await session.refresh(activity_obj, ["platform", "area"])

    # Build response from ORM object
    response = ActivityResponse(
        activityId=activity_obj.activity_id,
        activityName=activity_obj.activity_name,
        createdAt=activity_obj.created_at,
        platformId=activity_obj.platform.platform_id,
        platformName=activity_obj.platform.platform_name,
        areaId=activity_obj.area.area_id,
        url=activity_obj.url,
        address=AddressResponse(
            street=activity_obj.address_street,
            number=activity_obj.address_number,
            letter=activity_obj.address_letter,
            addition=activity_obj.address_addition,
            postalCode=activity_obj.address_postal_code,
            city=activity_obj.address_city,
        ),
        registrationNumber=activity_obj.registration_number,
        numberOfGuests=activity_obj.number_of_guests,
        countryOfGuests=activity_obj.country_of_guests,
        temporal=TemporalResponse(
            startDatetime=activity_obj.temporal_start_date_time,
            endDatetime=activity_obj.temporal_end_date_time,
        ),
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=response.model_dump(by_alias=True, mode="json"),
    )


@router.get(
    "/str/activities",
    summary="Get activities for the current authenticated platform",
    description="""Get all activities submitted by the current authenticated platform.

**Scoping:**
- Only returns activities belonging to the authenticated STR platform (based on JWT client_id)

**Pagination:**
- `offset`: Number of records to skip (default: 0)
- `limit`: Maximum number of records to return (default: no limit)

**Response Codes:**
- **200 OK:** Activities retrieved successfully
- **401 Unauthorized:** Invalid or missing authentication token
- **403 Forbidden:** Missing required authorization roles
""",
    operation_id="getOwnActivities",
    response_model=ActivityOwnListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        "200": {
            "description": "Activities retrieved successfully",
            "model": ActivityOwnListResponse,
        },
        "401": {
            "model": UnauthorizedError,
            "description": "Unauthorized - Invalid or missing token",
        },
        "403": {
            "description": "Forbidden - Missing required authorization roles",
        },
    },
)
async def get_own_activities(
    session: AsyncSession = Depends(get_async_db),
    token_payload: dict[str, Any] = Depends(verify_bearer_token),
    offset: int = 0,
    limit: int | None = None,
) -> Response:
    """
    Get activities for the current authenticated platform.

    Authorization:
    - Requires valid bearer token with "sdep_str" and "sdep_read" roles
    - Platform ID extracted from token's "client_id" claim
    """

    # Authorization check: Verify user has "sdep_str" and "sdep_read" roles
    realm_access = token_payload.get("realm_access", {})
    roles = realm_access.get("roles", [])

    if "sdep_str" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: 'sdep_str' role required",
        )

    if "sdep_read" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: 'sdep_read' role required",
        )

    # Extract platform ID from token
    platform_id = token_payload.get("client_id")
    if not platform_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing 'client_id' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get activities for this platform
    activity_dicts = await activity_service.get_activities_by_platform(
        session,
        platform_id_str=platform_id,
        offset=offset,
        limit=limit,
    )

    # Build response
    activities = [
        ActivityOwnResponse(
            activityId=act["activity_id"],
            activityName=act["activity_name"],
            areaId=act["area_id"],
            url=act["url"],
            address=AddressResponse(
                street=act["address_street"],
                number=act["address_number"],
                letter=act["address_letter"],
                addition=act["address_addition"],
                postalCode=act["address_postal_code"],
                city=act["address_city"],
            ),
            registrationNumber=act["registration_number"],
            numberOfGuests=act["number_of_guests"],
            countryOfGuests=act["country_of_guests"],
            temporal=TemporalResponse(
                startDatetime=act["temporal_start_date_time"],
                endDatetime=act["temporal_end_date_time"],
            ),
            createdAt=act["created_at"],
        )
        for act in activity_dicts
    ]

    response = ActivityOwnListResponse(activities=activities)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response.model_dump(by_alias=True, mode="json"),
    )


@router.get(
    "/str/activities/count",
    response_model=ActivityCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get activities count for the current authenticated platform.",
    description="Get activities count for the current authenticated platform.",
    operation_id="countOwnActivities",
    responses={
        "401": {
            "model": UnauthorizedError,
            "description": "Unauthorized - Invalid or missing token",
        },
        "403": {
            "description": "Forbidden - Missing required authorization roles",
        },
    },
)
async def count_own_activities(
    session: AsyncSession = Depends(get_async_db_read_only),
    token_payload: dict[str, Any] = Depends(verify_bearer_token),
) -> ActivityCountResponse:
    """
    Count activities for the current authenticated platform.

    Authorization:
    - Requires valid bearer token with "sdep_str" and "sdep_read" roles in realm_access
    - Platform ID is extracted from token's "client_id" claim

    Returns:
    - count: Total number of activities for the given platform
    """
    # Authorization check: Verify user has "sdep_str" and "sdep_read" roles
    realm_access = token_payload.get("realm_access", {})
    roles = realm_access.get("roles", [])

    if "sdep_str" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: 'sdep_str' role required",
        )

    if "sdep_read" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: 'sdep_read' role required",
        )

    # Extract platform ID from token's client_id claim
    platform_id = token_payload.get("client_id")
    if not platform_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing 'client_id' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Call business service with platform ID from token
    total_count = await activity_service.count_activities_by_platform(
        session, platform_id
    )

    return ActivityCountResponse(count=total_count)
