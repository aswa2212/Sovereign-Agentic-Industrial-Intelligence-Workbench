"""
SIH26117 — Model Manager API Schemas
Pydantic models for the /api/v1/models endpoints request and response contracts.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ModelCapabilitiesSchema(BaseModel):
    """API representation of a model's capabilities."""

    supports_vision: bool = False
    supports_tools: bool = False
    supports_thinking: bool = False
    max_context_length: int = 4096


class ModelInfoSchema(BaseModel):
    """API representation of a locally available model."""

    model_config = {"protected_namespaces": ()}

    model_id: str
    provider: str
    tag: str
    quantization: Optional[str] = None
    capabilities: ModelCapabilitiesSchema = Field(default_factory=ModelCapabilitiesSchema)
    is_resident_in_vram: bool = False


class ModelListResponse(BaseModel):
    """Response for GET /api/v1/models — lists all available local models."""

    models: List[ModelInfoSchema]
    total: int
    backend_healthy: bool
    active_tier: str


class TierModelEntry(BaseModel):
    """One model role entry from the active tier configuration."""

    model_config = {"protected_namespaces": ()}

    role: str
    provider: str
    model_tag: str
    context_window: int
    quantization: Optional[str] = None
    device: Optional[str] = None


class TierConfigResponse(BaseModel):
    """Response for GET /api/v1/models/tier — active hardware tier details."""

    tier_name: str
    description: str
    vram_budget_gb: float
    max_concurrent_models: int
    models: List[TierModelEntry]


class BackendHealthResponse(BaseModel):
    """Response for GET /api/v1/models/health — backend liveness probe."""

    healthy: bool
    provider: str
    message: str


# ---------------------------------------------------------------------------
# Request + Response schemas for generation
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    """
    Request body for POST /api/v1/models/generate.
    Callers specify a model role, not a model ID — routing remains encapsulated.
    """

    role: str = Field(
        ...,
        description=(
            "Model role to use for generation: 'router', 'reasoning', "
            "'coder', 'vision', or 'embedding'."
        ),
        examples=["reasoning"],
    )
    prompt: str = Field(..., description="User prompt text.", min_length=1)
    system_prompt: Optional[str] = Field(
        None, description="Optional system / instruction prompt."
    )
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Sampling temperature. Lower = more deterministic.",
    )
    structured: bool = Field(
        default=False,
        description=(
            "If true, request JSON-structured output and return parsed dict. "
            "If false, return plain text."
        ),
    )


class GenerateResponse(BaseModel):
    """Response for POST /api/v1/models/generate."""

    model_config = {"protected_namespaces": ()}

    role: str
    model_tag: str
    text: Optional[str] = None           # Set when structured=False
    structured: Optional[Dict[str, Any]] = None  # Set when structured=True
    provider: str
