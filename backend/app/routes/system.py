"""
System routes for application metadata and health status checks.
"""

from fastapi import APIRouter
from app.config import settings
from app.database import check_db_connection
from app.schemas.health import AppInfoResponse, DatabaseHealth, HealthResponse

router = APIRouter(tags=["System"])


@router.get(
    "/",
    response_model=AppInfoResponse,
    summary="Application Information",
    description="Returns metadata about the VisualGuard AI Backend, current version, and API documentation URLs.",
)
def get_app_info() -> AppInfoResponse:
    """Return core information about the VisualGuard AI API."""
    return AppInfoResponse(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        status="online",
        environment=settings.ENVIRONMENT,
        docs_url="/docs",
        redoc_url="/redoc",
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Server Health Check",
    description="Returns server status and tests PostgreSQL connectivity diagnostics.",
)
def get_health() -> HealthResponse:
    """Check application health and live database connectivity."""
    db_ok, db_details = check_db_connection()
    overall_status = "healthy" if db_ok else "degraded"

    return HealthResponse(
        status=overall_status,
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        database=DatabaseHealth(
            connected=db_ok,
            details=db_details,
        ),
    )

