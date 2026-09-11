"""
SIH26117 — Phase 10: Deliverables REST API Schemas

Defines the request and response models for the /api/v1/deliverables endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

try:
    from app.services.deliverables.models import (
        DeliverableFormat,
        GeneratedArtifact,
        ReportMetadata,
    )
    from app.services.validation.models import CorrosionAuditResult
except ImportError:
    from backend.app.services.deliverables.models import (
        DeliverableFormat,
        GeneratedArtifact,
        ReportMetadata,
    )
    from backend.app.services.validation.models import CorrosionAuditResult


class DeliverableGenerateRequest(BaseModel):
    """Request payload to generate Office deliverables from validated engineering data."""
    model_config = ConfigDict(extra="forbid")

    data: Optional[CorrosionAuditResult] = Field(
        default=None,
        description="Strongly typed Phase 9 CorrosionAuditResult model",
    )
    raw_payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Serialized dictionary representation of a validated result",
    )
    formats: Optional[List[DeliverableFormat]] = Field(
        default=None,
        description="Target formats to generate (default: docx, xlsx, pptx)",
    )
    metadata: Optional[ReportMetadata] = Field(
        default=None,
        description="Optional technical report metadata to display in headers",
    )
    task_id: Optional[str] = Field(
        default=None,
        description="Optional task ID override for filename and traceability",
    )


class DeliverableGenerateResponse(BaseModel):
    """Response payload returning generated Office deliverable artifact metadata."""
    model_config = ConfigDict(extra="forbid")

    success: bool = Field(..., description="True if deliverables were generated and verified")
    task_id: Optional[str] = Field(default=None, description="Task identifier associated with request")
    equipment_id: str = Field(..., description="Equipment tag identifier (e.g. C-101)")
    inspection_subject: str = Field(..., description="Inspection activity subject")
    artifacts: List[GeneratedArtifact] = Field(
        default_factory=list,
        description="List of verified Office deliverable artifacts produced",
    )
    formats_requested: List[DeliverableFormat] = Field(
        default_factory=list,
        description="List of requested formats",
    )
    summary: str = Field(..., description="Execution outcome summary")
    validation_status: str = Field(
        default="PHASE9_VALIDATED",
        description="Phase 9 validation pedigree status",
    )
