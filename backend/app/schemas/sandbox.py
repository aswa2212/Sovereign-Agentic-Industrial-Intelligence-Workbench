"""
SIH26117 — Sandbox API Schemas
Defines request and response schemas for POST /api/v1/sandbox/execute and GET /api/v1/sandbox/status.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SandboxExecuteRequest(BaseModel):
    """Request body for POST /api/v1/sandbox/execute."""

    model_config = ConfigDict(protected_namespaces=(), extra="forbid")

    tool_name: str = Field(
        ...,
        min_length=1,
        description="Name of approved whitelisted tool to execute",
        examples=["minimum_wall_thickness_check"],
    )
    input: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured input parameters for the target tool",
        examples=[{"measured_thickness_mm": 3.8, "minimum_required_mm": 3.2}],
    )
    timeout_seconds: Optional[float] = Field(
        default=None,
        description="Optional execution timeout override in seconds",
        gt=0,
        le=60.0,
    )
    execution_mode: Optional[str] = Field(
        default="subprocess",
        description="Execution mode: 'subprocess' (isolated process) or 'in_process'",
    )


class SandboxExecuteResponse(BaseModel):
    """Response body for POST /api/v1/sandbox/execute."""

    model_config = ConfigDict(protected_namespaces=())

    execution_id: str = Field(..., description="Unique execution transaction ID")
    tool_name: str = Field(..., description="Executed tool name")
    status: str = Field(..., description="Execution status: SUCCESS, VALIDATION_FAILED, TIMEOUT, POLICY_DENIED, etc.")
    duration_ms: float = Field(..., description="Execution duration in milliseconds")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Calculated structured output payload")
    error_message: Optional[str] = Field(default=None, description="Diagnostic error message if failed")
    error_category: Optional[str] = Field(default=None, description="Categorized failure classification")


class SandboxStatusResponse(BaseModel):
    """Response body for GET /api/v1/sandbox/status."""

    model_config = ConfigDict(protected_namespaces=())

    enabled: bool = Field(..., description="Whether tool execution sandbox is enabled")
    backend: str = Field(..., description="Active executor backend (e.g. SubprocessSandboxExecutor)")
    allowed_tools: List[str] = Field(..., description="Whitelisted deterministic tool names")
    limits: Dict[str, Any] = Field(..., description="Configured resource limits and ceilings")
