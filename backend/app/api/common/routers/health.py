"""Health monitoring endpoints"""

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.config import settings
from app.db.config import create_async_session

router = APIRouter(tags=["health"])


async def check_database_available() -> str:
    """Check if database is available.

    Returns:
        str: "OK" if database is available, "NOK" otherwise
    """
    try:
        async with create_async_session() as session:
            # Execute simple query to verify database connectivity
            # SELECT 1 doesn't query any table - it just returns the literal value 1
            # This is the fastest way to test if the database connection works
            await session.execute(text("SELECT 1"))
        return "OK"
    except Exception:
        return "NOK"


@router.get(
    "/health",
    summary="Health check on application incl. database)",
    description="Health check endpoint to verify if application (incl. database) is available",
    operation_id="health",
    include_in_schema=False,
    responses={
        200: {
            "description": "Health check passed",
            "content": {"application/json": {"example": {"database_available": "OK"}}},
        },
        422: {
            "description": "Health check failed - database NOK",
            "content": {"application/json": {"example": {"database_available": "NOK"}}},
        },
    },
)
async def health(response: Response):
    """Health check endpoint to verify if application (incl. database) is available"""

    # Check database status
    database_available = await check_database_available()

    # Set HTTP status code based on database status
    if database_available == "NOK":
        response.status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    else:
        response.status_code = status.HTTP_200_OK

    # Return JSON response
    return {"database_available": database_available}


@router.get(
    "/health-br",
    summary="Health check on backup/restore)",
    description="Health check endpoint to verify if backup/restore status is OK",
    operation_id="health-br",
    include_in_schema=False,
    responses={
        200: {
            "description": "Health check passed",
            "content": {
                "application/json": {"example": {"backup_restore_status": "OK"}}
            },
        },
        422: {
            "description": "Health check failed - backup/restore check failed",
            "content": {
                "application/json": {"example": {"backup_restore_status": "NOK"}}
            },
        },
    },
)
async def health_br(response: Response):
    """Health check endpoint to verify if backup/restore is OK"""

    # Check backup/restore status
    backup_restore_status = settings.BACKUP_RESTORE_STATUS

    # Set HTTP status code based on backup/restore status
    if backup_restore_status == "NOK":
        response.status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    else:
        response.status_code = status.HTTP_200_OK

    # Return JSON response
    return {
        "backup_restore_status": backup_restore_status,
    }
