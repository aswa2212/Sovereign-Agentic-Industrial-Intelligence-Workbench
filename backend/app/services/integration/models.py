"""
SIH26117 — Phase 13: End-to-End System Integration Models

Data contracts and telemetry schemas for the integrated Primary Corrosion Audit Workflow.
Provides unified visibility across all 11 subsystems:
Ingestion -> OCR/Vision -> Router -> Model Manager -> Agent -> RAG -> Sandbox ->
Validation -> Deliverables -> Audit -> Sovereignty Evidence.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class WorkflowExecutionMode(str, Enum):
    """Execution mode for the integrated workflow."""
    DETERMINISTIC = "deterministic"
    LIVE = "live"


class WorkflowStatus(str, Enum):
    """Overall status of the workflow execution."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"
    FAILED = "FAILED"


class StageStatus(str, Enum):
    """Execution status for an individual stage."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class WorkflowStageTelemetry(BaseModel):
    """Telemetry captured for each stage of the integrated workflow."""
    model_config = ConfigDict(extra="forbid")

    stage_name: str = Field(..., description="Name of the pipeline stage")
    stage_index: int = Field(..., description="Zero-based stage order")
    status: StageStatus = Field(default=StageStatus.PENDING)
    duration_ms: float = Field(default=0.0, description="Stage latency in milliseconds")
    started_at: Optional[str] = Field(default=None)
    completed_at: Optional[str] = Field(default=None)
    details: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = Field(default=None)


class CorrosionAuditWorkflowRequest(BaseModel):
    """Request specification for triggering the corrosion audit workflow."""
    model_config = ConfigDict(extra="forbid")

    objective: str = Field(
        default="Audit thickness readings against MRPL piping specification, calculate corrosion rate, and generate executive approval note.",
        description="Operator task objective / user prompt",
    )
    document_filename: Optional[str] = Field(
        default=None,
        description="Source document name in samples or storage",
    )
    execution_mode: WorkflowExecutionMode = Field(
        default=WorkflowExecutionMode.DETERMINISTIC,
        description="Deterministic (reproducible test mode) or live local models",
    )
    requested_formats: List[str] = Field(
        default=["docx", "xlsx"],
        description="Office deliverable formats to compile upon successful validation",
    )
    task_id: Optional[str] = Field(
        default=None,
        description="Optional custom task/correlation ID",
    )
    component_id: Optional[str] = Field(
        default=None,
        description="Equipment or circuit tag identifier",
    )
    elapsed_time_years: Optional[float] = Field(
        default=None,
        description="Operating years elapsed since baseline inspection",
        gt=0.0,
    )
    minimum_required_thickness_mm: Optional[float] = Field(
        default=None,
        description="Allowable retirement limit from standard/SOP (mm)",
        gt=0.0,
    )


class ArtifactSummary(BaseModel):
    """Summary of a generated office deliverable."""
    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    format: str
    filename: str
    relative_path: str
    file_size_bytes: int
    sha256: str
    download_url: str


class CorrosionAuditWorkflowResult(BaseModel):
    """Complete end-to-end telemetry and deliverable package from workflow execution."""
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    workflow_id: str
    task_id: str
    status: WorkflowStatus
    execution_mode: WorkflowExecutionMode
    objective: str
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: float = 0.0

    # Subsystem evidence blocks
    document_summary: Dict[str, Any] = Field(default_factory=dict)
    ocr_vision_summary: Dict[str, Any] = Field(default_factory=dict)
    evidence_summary: Optional[Dict[str, Any]] = None
    routing_decision: Optional[Dict[str, Any]] = None
    model_allocation: Optional[Dict[str, Any]] = None
    agent_summary: Optional[Dict[str, Any]] = None
    rag_citations: List[Dict[str, Any]] = Field(default_factory=list)
    calculation_result: Optional[Dict[str, Any]] = None
    validation_result: Optional[Dict[str, Any]] = None
    deliverables: List[ArtifactSummary] = Field(default_factory=list)
    audit_summary: Dict[str, Any] = Field(default_factory=dict)
    sovereignty_proof: Dict[str, Any] = Field(default_factory=dict)

    # Capability and active model metadata
    execution_capability: Optional[str] = None
    active_model: Optional[str] = None

    # Detailed stage trace
    stages: List[WorkflowStageTelemetry] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


def utc_now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()
