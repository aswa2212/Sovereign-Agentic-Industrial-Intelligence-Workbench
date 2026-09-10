"""
SIH26117 — System Information API Endpoints
Provides system status, subsystem initialization states, and planned MVP capabilities.
"""

from fastapi import APIRouter, Depends

try:
    from app.core.config import Settings, get_settings
    from app.schemas.system import (
        CapabilitiesMap,
        ImplementationStatusMap,
        ModuleStatus,
        SystemCapabilitiesResponse,
        SystemStatusResponse,
    )
except ImportError:
    from backend.app.core.config import Settings, get_settings
    from backend.app.schemas.system import (
        CapabilitiesMap,
        ImplementationStatusMap,
        ModuleStatus,
        SystemCapabilitiesResponse,
        SystemStatusResponse,
    )

router = APIRouter(prefix="/system", tags=["System"])


@router.get(
    "/status",
    response_model=SystemStatusResponse,
    summary="Get System Status",
    description="Returns current operational status of the gateway and initialization states of subsystems.",
)
async def get_system_status(
    settings: Settings = Depends(get_settings),
) -> SystemStatusResponse:
    """
    Returns the real-time operational status of the gateway and registers
    future subsystems honestly as 'not_initialized'.
    """
    return SystemStatusResponse(
        status="operational",
        air_gapped_mode=settings.air_gapped_mode,
        inference_provider=settings.inference_provider,
        ollama_url=settings.ollama_base_url,
        hardware_tier=settings.hardware_tier,
        modules=ModuleStatus(
            router="not_initialized",
            agent="not_initialized",
            model_manager="not_initialized",
            rag="not_initialized",
            vision="not_initialized",
            sandbox="not_initialized",
            deliverables="not_initialized",
            audit="not_initialized",
            network_monitor="not_initialized",
        ),
    )


@router.get(
    "/capabilities",
    response_model=SystemCapabilitiesResponse,
    summary="Get System Capabilities",
    description="Lists the planned architectural capabilities and their respective implementation phases.",
)
async def get_system_capabilities() -> SystemCapabilitiesResponse:
    """
    Returns planned architectural capabilities and their phased delivery status.
    """
    return SystemCapabilitiesResponse(
        capabilities=CapabilitiesMap(
            routing=True,
            agentic_execution=True,
            rag=True,
            multimodal_ingestion=True,
            vision=True,
            sandbox_execution=True,
            office_generation=True,
            air_gap_monitoring=True,
        ),
        implementation_status=ImplementationStatusMap(
            routing="planned",
            agentic_execution="planned",
            rag="planned",
            multimodal_ingestion="planned",
            vision="planned",
            sandbox_execution="planned",
            office_generation="planned",
            air_gap_monitoring="planned",
        ),
    )
