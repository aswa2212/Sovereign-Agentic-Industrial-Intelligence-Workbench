"""
SIH26117 — Phase 10: Deliverables Service Pydantic Models

Defines the input options and output artifact schemas for Office deliverable generation.
Strict validation is enforced (extra="forbid").
"""

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DeliverableFormat(str, Enum):
    """Supported deterministic Office deliverable output formats."""
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"


class ReportMetadata(BaseModel):
    """Metadata displayed on generated technical reports and memorandum headers."""
    model_config = ConfigDict(extra="forbid")

    title: str = Field(
        default="CORROSION INSPECTION & ASSET INTEGRITY TECHNICAL MEMORANDUM",
        description="Official title of the technical memorandum or briefing",
    )
    organization: str = Field(
        default="MANGALORE REFINERY AND PETROCHEMICALS LIMITED (MRPL)",
        description="Sponsoring operating organization",
    )
    facility: str = Field(
        default="Mangalore Refinery Complex",
        description="Refinery or facility name",
    )
    division: str = Field(
        default="Inspection & Asset Integrity Division",
        description="Issuing department or division",
    )
    prepared_by: str = Field(
        default="Autonomous Sovereign Inspection Agent (SIH26117)",
        description="Author or agent preparing the report",
    )
    approved_by: str = Field(
        default="Chief Inspection Engineer, MRPL",
        description="Designated approval authority",
    )
    report_code: Optional[str] = Field(
        default=None,
        description="Custom technical report document code (e.g. MRPL-CORR-2026-001)",
    )
    revision: str = Field(
        default="01",
        description="Document revision number",
    )


class GeneratedArtifact(BaseModel):
    """Metadata describing a single successfully generated and verified Office document."""
    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(..., description="Unique identifier for the generated artifact")
    format: DeliverableFormat = Field(..., description="Deliverable format (docx, xlsx, pptx)")
    filename: str = Field(..., description="Base filename on disk")
    relative_path: str = Field(..., description="Relative path within output directory")
    file_size_bytes: int = Field(..., description="Size of generated file in bytes", ge=1)
    sha256_hash: str = Field(..., description="Cryptographic SHA-256 hash of the generated file")
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of generation",
    )
    verification_status: str = Field(
        default="VERIFIED",
        description="Result of post-generation integrity inspection",
    )


class DeliverableGenerationResult(BaseModel):
    """Overall outcome of a deliverable generation request across one or more formats."""
    model_config = ConfigDict(extra="forbid")

    success: bool = Field(..., description="True if all requested deliverables were generated and verified")
    task_id: Optional[str] = Field(default=None, description="Task identifier associated with the request")
    equipment_id: str = Field(..., description="Target equipment identifier (e.g. C-101)")
    inspection_subject: str = Field(..., description="Inspection activity subject")
    artifacts: List[GeneratedArtifact] = Field(
        default_factory=list,
        description="List of verified Office deliverable artifacts produced",
    )
    formats_requested: List[DeliverableFormat] = Field(
        default_factory=list,
        description="List of requested formats",
    )
    summary: str = Field(..., description="Human-readable execution summary")
    validation_status: str = Field(
        default="PHASE9_VALIDATED",
        description="Phase 9 validation pedigree status",
    )
