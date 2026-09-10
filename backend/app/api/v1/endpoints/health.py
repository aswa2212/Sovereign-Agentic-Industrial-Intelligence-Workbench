"""
SIH26117 — Health API Endpoint
Provides lightweight health check ensuring the API gateway is responsive.
"""

from fastapi import APIRouter, Depends

try:
    from app.core.config import Settings, get_settings
    from app.schemas.system import HealthResponse
except ImportError:
    from backend.app.core.config import Settings, get_settings
    from backend.app.schemas.system import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Gateway Health Check",
    description="Returns basic gateway health status and verifies air-gapped configuration.",
)
async def check_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Return basic gateway health and sovereign policy status."""
    return HealthResponse(
        status="ok",
        service=f"{settings.app_name} Gateway",
        version=settings.app_version,
        air_gapped_mode=settings.air_gapped_mode,
    )
