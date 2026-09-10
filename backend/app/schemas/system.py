"""
SIH26117 — System and Gateway Pydantic Schemas
Defines request and response schemas for system health, status, and capabilities.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Schema for /api/v1/health endpoint."""

    status: str = Field(default="ok", description="Overall service health status")
    service: str = Field(default="SIH26117 Backend", description="Service identifier")
    version: str = Field(..., description="Application semantic version")
    air_gapped_mode: bool = Field(
        default=True, description="Enforcement flag for air-gapped sovereign operation"
    )


class ModuleStatus(BaseModel):
    """Granular initialization states for upcoming workbench subsystems."""

    model_config = ConfigDict(protected_namespaces=())

    router: str = Field(default="not_initialized")
    agent: str = Field(default="not_initialized")
    model_manager: str = Field(default="not_initialized")
    rag: str = Field(default="not_initialized")
    vision: str = Field(default="not_initialized")
    sandbox: str = Field(default="not_initialized")
    deliverables: str = Field(default="not_initialized")
    audit: str = Field(default="not_initialized")
    network_monitor: str = Field(default="not_initialized")


class SystemStatusResponse(BaseModel):
    """Schema for /api/v1/system/status endpoint."""

    status: str = Field(default="operational", description="Core gateway operational state")
    air_gapped_mode: bool = Field(default=True, description="Air-gap containment mode")
    inference_provider: str = Field(default="ollama", description="Local inference provider")
    ollama_url: str = Field(default="http://127.0.0.1:11434", description="Local Ollama endpoint")
    hardware_tier: str = Field(default="dev", description="Current hardware profile (dev | target)")
    modules: ModuleStatus = Field(default_factory=ModuleStatus)


class CapabilitiesMap(BaseModel):
    """Flag set indicating planned architectural capabilities."""

    routing: bool = True
    agentic_execution: bool = True
    rag: bool = True
    multimodal_ingestion: bool = True
    vision: bool = True
    sandbox_execution: bool = True
    office_generation: bool = True
    air_gap_monitoring: bool = True


class ImplementationStatusMap(BaseModel):
    """Current implementation state of each planned capability."""

    routing: str = "planned"
    agentic_execution: str = "planned"
    rag: str = "planned"
    multimodal_ingestion: str = "planned"
    vision: str = "planned"
    sandbox_execution: str = "planned"
    office_generation: str = "planned"
    air_gap_monitoring: str = "planned"


class SystemCapabilitiesResponse(BaseModel):
    """Schema for /api/v1/system/capabilities endpoint."""

    capabilities: CapabilitiesMap = Field(default_factory=CapabilitiesMap)
    implementation_status: ImplementationStatusMap = Field(
        default_factory=ImplementationStatusMap
    )


class ErrorDetail(BaseModel):
    """Standard error envelope payload."""

    code: str = Field(..., description="Machine-readable error classification code")
    message: str = Field(..., description="Human-readable error explanation")
    details: Optional[Any] = Field(
        default=None, description="Optional diagnostic details or validation issues"
    )


class ErrorResponse(BaseModel):
    """Standardized error response wrapping."""

    error: ErrorDetail
