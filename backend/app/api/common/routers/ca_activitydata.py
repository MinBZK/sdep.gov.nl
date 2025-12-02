"""Competent authority endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.config import get_async_db_read_only
from app.schemas.activity_data import (
    ActivityDataCountResponse,
    ActivityDataListResponse,
    ActivityDataResponse,
    AddressResponse,
    TemporalResponse,
)
from app.schemas.auth import UnauthorizedError
from app.security import verify_bearer_token
from app.services import activity_data

router = APIRouter(tags=["ca"])


@router.get(
    "/ca/activity-data",
    response_model=ActivityDataListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get activity data for competent authority",
    description="Get activity data for a competent authority. By default, returns all activity data (unlimited). Use optional pagination parameters to limit results. Requires 'sdep_ca' and 'sdep_read' roles. Competent authority ID is extracted from the JWT token.",
    operation_id="getActivityDataByCompetentAuthority",
    responses={
        "401": {
            "model": UnauthorizedError,
            "description": "Unauthorized - Invalid or missing token",
        },
        "403": {
            "description": "Forbidden - Missing required 'sdep_ca' or 'sdep_read' role",
        },
    },
)
async def get_activity_data(
    offset: Annotated[int, Query(ge=0, description="Number of records to skip (default: 0)")] = 0,
    limit: Annotated[
        int | None, Query(ge=1, le=1000, description="Maximum number of records to return (default: unlimited, max: 1000 when specified)")
    ] = None,
    session: AsyncSession = Depends(get_async_db_read_only),
    token_payload: dict[str, Any] = Depends(verify_bearer_token),
) -> ActivityDataListResponse:
    """
    Get activity data for a competent authority.

    Authorization:
    - Requires valid bearer token with "sdep_ca" and "sdep_read" roles in realm_access
    - Competent authority ID is extracted from token's "client_id" claim

    Returns a list of activity data, each containing:
    - url: URL of the advertisement
    - address: Address composite (street, number, postalCode, city, letter, addition)
    - registrationNumber: Registration number
    - areaId: Area ID (foreign key)
    - numberOfGuests: Number of guests
    - countryOfGuests: Array of country codes
    - temporal: Temporal composite (startDatetime, endDatetime)
    - platformId: Platform ID
    - platformName: Platform name
    - createdAt: Creation timestamp

    Pagination parameters:
    - offset: Number of records to skip (default: 0)
    - limit: Maximum number of records to return (default: no limit, max: 1000)
    """
    # Authorization check: Verify user has "sdep_ca" and "sdep_read" roles
    realm_access = token_payload.get("realm_access", {})
    roles = realm_access.get("roles", [])

    if "sdep_ca" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: 'sdep_ca' role required",
        )

    if "sdep_read" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: 'sdep_read' role required",
        )

    # Extract competent authority ID from token's client_id claim
    competent_authority_id = token_payload.get("client_id")
    if not competent_authority_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing 'client_id' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Call business service with competent authority ID from token
    activity_data_list = await activity_data.get_activity_data_list(
        session, competent_authority_id=competent_authority_id, offset=offset, limit=limit
    )

    # Transform to API response format
    activity_responses = [
        ActivityDataResponse(
            url=activity_dict["url"],
            address=AddressResponse(
                street=activity_dict["address_street"],
                number=activity_dict["address_number"],
                postalCode=activity_dict["address_postal_code"],
                city=activity_dict["address_city"],
                letter=activity_dict["address_letter"],
                addition=activity_dict["address_addition"],
            ),
            registrationNumber=activity_dict["registration_number"],
            areaId=str(activity_dict["area_id"]),
            numberOfGuests=activity_dict["number_of_guests"],
            countryOfGuests=activity_dict["country_of_guests"],
            temporal=TemporalResponse(
                startDatetime=activity_dict["temporal_start_date_time"],
                endDatetime=activity_dict["temporal_end_date_time"],
            ),
            platformId=activity_dict["platform_id"],
            platformName=activity_dict["platform_name"],
            createdAt=activity_dict["created_at"],
        )
        for activity_dict in activity_data_list
    ]

    return ActivityDataListResponse(activities=activity_responses)


@router.get(
    "/ca/activity-data/count",
    response_model=ActivityDataCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get activity data count for competent authority",
    description="Get the total count of activity data records for a competent authority. Requires 'sdep_ca' and 'sdep_read' roles. Competent authority ID is extracted from the JWT token.",
    operation_id="countActivityData",
    responses={
        "401": {
            "model": UnauthorizedError,
            "description": "Unauthorized - Invalid or missing token",
        },
        "403": {
            "description": "Forbidden - Missing required 'sdep_ca' or 'sdep_read' role",
        },
    },
)
async def count_activity_data(
    session: AsyncSession = Depends(get_async_db_read_only),
    token_payload: dict[str, Any] = Depends(verify_bearer_token),
) -> ActivityDataCountResponse:
    """
    Count activity data records for a competent authority.

    Authorization:
    - Requires valid bearer token with "sdep_ca" and "sdep_read" roles in realm_access
    - Competent authority ID is extracted from token's "client_id" claim

    Returns:
    - count: Total number of activity data records for the given competent authority
    """
    # Authorization check: Verify user has "sdep_ca" and "sdep_read" roles
    realm_access = token_payload.get("realm_access", {})
    roles = realm_access.get("roles", [])

    if "sdep_ca" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: 'sdep_ca' role required",
        )

    if "sdep_read" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: 'sdep_read' role required",
        )

    # Extract competent authority ID from token's client_id claim
    competent_authority_id = token_payload.get("client_id")
    if not competent_authority_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing 'client_id' claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Call business service with competent authority ID from token
    total_count = await activity_data.count_activity_data_by_competent_authority(
        session, competent_authority_id
    )

    return ActivityDataCountResponse(count=total_count)
