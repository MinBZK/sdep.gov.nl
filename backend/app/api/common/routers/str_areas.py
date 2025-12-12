"""Areas endpoint."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.config import get_async_db_read_only
from app.schemas.area import (
    AreaResponse,
    AreasCountResponse,
    AreasListResponse,
)
from app.schemas.auth import UnauthorizedError
from app.schemas.validation import HTTPBadRequestError
from app.security import verify_bearer_token
from app.services import area

router = APIRouter(tags=["str"])


@router.get(
    "/str/areas",
    response_model=AreasListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all SDEP areas",
    description="Get all SDEP areas. By default, returns all areas (unlimited). Use optional pagination parameters to limit results.",
    operation_id="getAreas",
    responses={
        "400": {
            "model": HTTPBadRequestError,
            "description": "Bad Request - Invalid query parameters",
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
async def get_areas(
    offset: Annotated[
        int, Query(ge=0, description="Number of records to skip (default: 0)")
    ] = 0,
    limit: Annotated[
        int | None,
        Query(
            ge=1,
            le=1000,
            description="Maximum number of records to return (default: unlimited, max: 1000 when specified)",
        ),
    ] = None,
    session: AsyncSession = Depends(get_async_db_read_only),
    token_payload: dict[str, Any] = Depends(verify_bearer_token),
) -> AreasListResponse:
    """
    Get areas in context of the current SDEP/member state.

    Authorization:
    - Requires valid bearer token with "sdep_str" and "sdep_read" roles in realm_access

    Returns a list of areas, each containing:
    - areaId: Area unique identifier (enables retrieval of area shapefile)
    - competentAuthorityId: Competent authority (id) who submitted the area
    - competentAuthorityName: Competent authority (name) who submitted the area
    - createdAt: Timestamp when the area was created

    Pagination parameters:
    - offset: Number of records to skip (default: 0)
    - limit: Maximum number of records to return (default: no limit, max: 1000)
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

    # Call business service
    areas_data = await area.get_areas(session, offset=offset, limit=limit)

    # Transform to API response format
    area_responses = [
        AreaResponse(
            areaId=area_dict["areaId"],
            competentAuthorityId=area_dict["competentAuthorityId"],
            competentAuthorityName=area_dict["competentAuthorityName"],
            filename=area_dict["filename"],
            created_at=area_dict["createdAt"],
        )
        for area_dict in areas_data
    ]

    return AreasListResponse(areas=area_responses)


@router.get(
    "/str/areas/count",
    response_model=AreasCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get total count of all SDEP areas",
    description="Get total count of all SDEP areas.",
    operation_id="countAreas",
    responses={
        "400": {
            "model": HTTPBadRequestError,
            "description": "Bad Request - Invalid query parameters",
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
async def count_areas(
    session: AsyncSession = Depends(get_async_db_read_only),
    token_payload: dict[str, Any] = Depends(verify_bearer_token),
) -> AreasCountResponse:
    """
    Count all areas in context of the current SDEP/member state.

    Authorization:
    - Requires valid bearer token with "sdep_str" and "sdep_read" roles in realm_access

    Returns:
    - count: Total number of areas
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

    # Call business service
    total_count = await area.count_areas(session)

    return AreasCountResponse(count=total_count)


@router.get(
    "/str/areas/{areaId}",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    summary="Get area (shapefile)",
    description="Get area (shapefile) based on areaId.",
    operation_id="getArea",
    responses={
        "200": {
            "content": {"application/octet-stream": {}},
            "description": "Binary area",
        },
        "400": {
            "model": HTTPBadRequestError,
            "description": "Bad Request - Invalid query parameters",
        },
        "401": {
            "model": UnauthorizedError,
            "description": "Unauthorized - Invalid or missing token",
        },
        "403": {
            "description": "Forbidden - Missing required authorization roles",
        },
        "404": {
            "description": "Area not found",
        },
    },
)
async def get_area(
    areaId: str,
    session: AsyncSession = Depends(get_async_db_read_only),
    token_payload: dict[str, Any] = Depends(verify_bearer_token),
) -> Response:
    """
    Get specific area.

    Authorization:
    - Requires valid bearer token with "sdep_str" and "sdep_read" roles in realm_access

    Returns raw binary area.
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

    # Call business service with area_id string
    area_data = await area.get_area_by_area_id(session, areaId)

    if area_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Area with areaId '{areaId}' not found",
        )

    # Return raw binary data (or empty bytes if filedata is None)
    binary_data = area_data["filedata"] if area_data["filedata"] is not None else b""
    filename = area_data.get("filename", "area.zip")

    return Response(
        content=binary_data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
