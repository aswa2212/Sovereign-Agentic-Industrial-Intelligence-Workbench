"""
SIH26117 — Model Manager REST API Endpoints
Exposes model discovery, tier configuration, health probes, and role-based generation.

All endpoints are offline-capable: if Ollama is not running, the health check
returns False and model lists are empty — the gateway stays online and reports
the backend outage without crashing.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

try:
    from app.core.config import Settings, get_settings
    from app.schemas.models import (
        BackendHealthResponse,
        GenerateRequest,
        GenerateResponse,
        ModelInfoSchema,
        ModelListResponse,
        TierConfigResponse,
        TierModelEntry,
    )
    from app.services.model_manager import ModelManager, ModelInfo
except ImportError:
    from backend.app.core.config import Settings, get_settings
    from backend.app.schemas.models import (
        BackendHealthResponse,
        GenerateRequest,
        GenerateResponse,
        ModelInfoSchema,
        ModelListResponse,
        TierConfigResponse,
        TierModelEntry,
    )
    from backend.app.services.model_manager import ModelManager, ModelInfo

router = APIRouter(prefix="/models", tags=["Models"])


# ---------------------------------------------------------------------------
# Application-level ModelManager dependency (lazy singleton)
# ---------------------------------------------------------------------------

_model_manager: ModelManager | None = None


def get_model_manager() -> ModelManager:
    """
    FastAPI dependency that returns the initialized ModelManager singleton.

    The singleton is created on first call (lazy) so that import-time
    side effects (YAML loading, adapter construction) are deferred until
    the first actual request — this keeps test collection fast.
    """
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager.from_settings()
    return _model_manager


def set_model_manager(manager: ModelManager) -> None:
    """
    Override the global ModelManager instance.
    Used in tests to inject a MockInferenceBackend without touching the filesystem.
    """
    global _model_manager
    _model_manager = manager


def _to_schema(info: ModelInfo) -> ModelInfoSchema:
    """Convert an internal ModelInfo to its API schema representation."""
    return ModelInfoSchema(
        model_id=info.model_id,
        provider=info.provider,
        tag=info.tag,
        quantization=info.quantization,
        capabilities=info.capabilities.model_dump(),
        is_resident_in_vram=info.is_resident_in_vram,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    response_model=BackendHealthResponse,
    summary="Backend Health Check",
    description="Check whether the local inference backend (Ollama) is reachable.",
)
async def model_backend_health(
    settings: Settings = Depends(get_settings),
    manager: ModelManager = Depends(get_model_manager),
) -> BackendHealthResponse:
    healthy = await manager.is_backend_healthy()
    return BackendHealthResponse(
        healthy=healthy,
        provider=settings.inference_provider,
        message="Backend is responsive." if healthy else "Backend is unreachable.",
    )


@router.get(
    "",
    response_model=ModelListResponse,
    summary="List Available Models",
    description="Return all models discovered in the local inference backend.",
)
async def list_models(
    settings: Settings = Depends(get_settings),
    manager: ModelManager = Depends(get_model_manager),
) -> ModelListResponse:
    healthy = await manager.is_backend_healthy()
    raw_models = await manager.list_models()
    tier = manager.get_tier_config()

    return ModelListResponse(
        models=[_to_schema(m) for m in raw_models],
        total=len(raw_models),
        backend_healthy=healthy,
        active_tier=settings.hardware_tier,
    )


@router.get(
    "/tier",
    response_model=TierConfigResponse,
    summary="Active Tier Configuration",
    description="Return the active hardware tier and all configured model roles.",
)
async def get_tier_config(
    settings: Settings = Depends(get_settings),
    manager: ModelManager = Depends(get_model_manager),
) -> TierConfigResponse:
    tier = manager.get_tier_config()
    role_entries: list[TierModelEntry] = []
    for role, entry in tier.list_roles().items():
        role_entries.append(
            TierModelEntry(
                role=role,
                provider=entry.provider,
                model_tag=entry.model_tag,
                context_window=entry.context_window,
                quantization=entry.quantization,
                device=entry.device,
            )
        )

    return TierConfigResponse(
        tier_name=settings.hardware_tier,
        description=tier.description,
        vram_budget_gb=tier.vram_budget_gb,
        max_concurrent_models=tier.max_concurrent_models,
        models=role_entries,
    )


@router.post(
    "/generate",
    response_model=GenerateResponse,
    summary="Role-Based Text Generation",
    description=(
        "Generate text (or structured JSON) using the model assigned to the given role "
        "in the active hardware tier. The caller never specifies a model ID — routing "
        "is encapsulated in the tier configuration."
    ),
)
async def generate(
    request: GenerateRequest,
    manager: ModelManager = Depends(get_model_manager),
    settings: Settings = Depends(get_settings),
) -> GenerateResponse:
    tier = manager.get_tier_config()
    entry = tier.get_model(request.role)

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"No model configured for role '{request.role}' in "
                f"active tier. Configured roles: {list(tier.list_roles().keys())}."
            ),
        )

    try:
        if request.structured:
            result_dict = await manager.generate_structured(
                role=request.role,
                prompt=request.prompt,
                system_prompt=request.system_prompt,
                temperature=request.temperature,
            )
            return GenerateResponse(
                role=request.role,
                model_tag=entry.model_tag,
                structured=result_dict,
                provider=settings.inference_provider,
            )
        else:
            text = await manager.generate(
                role=request.role,
                prompt=request.prompt,
                system_prompt=request.system_prompt,
                temperature=request.temperature,
            )
            return GenerateResponse(
                role=request.role,
                model_tag=entry.model_tag,
                text=text,
                provider=settings.inference_provider,
            )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Inference backend error: {exc}",
        )
