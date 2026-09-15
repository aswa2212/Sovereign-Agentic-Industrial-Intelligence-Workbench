"""
SIH26117 — Phase 9: Structured Output Pydantic Models

Defines the public schema for corrosion-audit structured engineering results.
All fields use explicit types. Unknown fields are rejected (extra="forbid").

DESIGN PRINCIPLES:
- schema-valid ≠ engineering-valid
- Never fabricate values, citations, or calculations
- Provenance is preserved exactly as supplied by Phase 6 RAG / Phase 7 Agent
"""

from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Enums ──────────────────────────────────────────────────────────────────────

class RecommendationCode(str, Enum):
    """Standardised recommendation codes for corrosion audit findings."""
    CONTINUE_SERVICE = "CONTINUE_SERVICE"
    INCREASE_MONITORING = "INCREASE_MONITORING"
    SCHEDULE_MAINTENANCE = "SCHEDULE_MAINTENANCE"
    IMMEDIATE_ACTION = "IMMEDIATE_ACTION"
    RETIRE_FROM_SERVICE = "RETIRE_FROM_SERVICE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class MeasurementUnit(str, Enum):
    """Supported units of measure for wall-thickness measurements."""
    MM = "mm"
    INCH = "inch"
    M = "m"


# ── Sub-models ─────────────────────────────────────────────────────────────────

class SourceCitation(BaseModel):
    """
    Provenance record linking a finding to a specific source document chunk.
    All fields are preserved exactly as supplied by Phase 6; none are fabricated.
    """
    model_config = ConfigDict(extra="forbid")

    source_document: str = Field(
        ...,
        description="Filename of the source document (e.g. SOP-MRPL-PIP-001.pdf)",
    )
    page_number: Optional[int] = Field(
        default=None,
        description="Page number within the source document, if applicable",
        ge=1,
    )
    chunk_id: Optional[str] = Field(
        default=None,
        description="Chunk identifier as assigned by the Phase 6 knowledge index",
    )
    content_sha256: Optional[str] = Field(
        default=None,
        description="SHA-256 hash of the chunk content for tamper-evident provenance",
    )
    similarity_score: Optional[float] = Field(
        default=None,
        description="Cosine similarity score returned by Phase 6 retrieval (0.0–1.0)",
        ge=0.0,
        le=1.0,
    )
    excerpt: Optional[str] = Field(
        default=None,
        description="Short verbatim excerpt from the source chunk supporting the finding",
    )


class WallThicknessMeasurement(BaseModel):
    """A single measured or recorded wall-thickness data point."""
    model_config = ConfigDict(extra="forbid")

    value_mm: float = Field(
        ...,
        description="Measured wall thickness in millimeters",
        gt=0.0,
    )
    unit: MeasurementUnit = Field(
        default=MeasurementUnit.MM,
        description="Unit of the measurement (must be explicitly declared)",
    )
    measurement_date: Optional[str] = Field(
        default=None,
        description="ISO 8601 date of the measurement (YYYY-MM-DD)",
    )
    location_tag: Optional[str] = Field(
        default=None,
        description="Equipment or circuit location identifier (e.g. 10-HC-101-CML-A)",
    )


class CorrosionCalculation(BaseModel):
    """
    Deterministic corrosion-rate and remaining-life calculation payload.

    Schema-valid ≠ engineering-valid.
    The engineering_validator independently recomputes these values and
    raises CalculationMismatchError if they deviate beyond tolerance.
    """
    model_config = ConfigDict(extra="forbid")

    initial_thickness_mm: float = Field(
        ..., description="Baseline / previous wall thickness in mm", gt=0.0
    )
    current_thickness_mm: float = Field(
        ..., description="Most recently measured wall thickness in mm", gt=0.0
    )
    inspection_interval_years: float = Field(
        ..., description="Time elapsed between measurements in years", gt=0.0
    )
    minimum_required_mm: Optional[float] = Field(
        default=None, description="Retirement / minimum allowable thickness in mm", gt=0.0
    )
    corrosion_rate_mm_per_year: float = Field(
        ..., description="Claimed corrosion rate in mm/year"
    )
    remaining_life_years: Optional[float] = Field(
        default=None, description="Claimed remaining operational life in years"
    )
    formula_applied: Optional[str] = Field(
        default=None,
        description="Human-readable description of the formula used",
    )

    @field_validator("corrosion_rate_mm_per_year")
    @classmethod
    def validate_corrosion_rate(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError("Corrosion rate cannot be negative.")
        return v


class InspectionFinding(BaseModel):
    """A single observed / reported finding from an inspection activity."""
    model_config = ConfigDict(extra="forbid")

    finding_id: Optional[str] = Field(
        default=None, description="Identifier for this finding within the report"
    )
    description: str = Field(
        ..., description="Factual description of the observed finding", min_length=1
    )
    severity: Optional[str] = Field(
        default=None, description="Assessed severity level (e.g. LOW, MEDIUM, HIGH, CRITICAL)"
    )
    supporting_citation: Optional[SourceCitation] = Field(
        default=None, description="Source citation grounding this finding"
    )


# ── Primary Structured Result ───────────────────────────────────────────────────

class CorrosionAuditResult(BaseModel):
    """
    Primary structured output contract for a corrosion-audit engineering task.

    This is the authoritative schema that the Phase 9 validation pipeline
    validates, enriches with engineering checks, and passes to Phase 10
    deliverable generation.

    INVARIANTS:
    - Unknown fields are rejected (extra="forbid").
    - No field defaults fabricate engineering values.
    - Citations are preserved as supplied; none are injected by the validator.
    """
    model_config = ConfigDict(extra="forbid")

    # ── Identification ──────────────────────────────────────────────────────
    task_id: Optional[str] = Field(
        default=None, description="Task identifier linking this result to the agent execution"
    )
    equipment_id: str = Field(
        ...,
        description="Equipment or piping circuit identifier (e.g. C-101, 10-HC-101)",
        min_length=1,
    )
    inspection_subject: str = Field(
        ...,
        description="Description of what was inspected (e.g. Overhead condenser piping)",
        min_length=1,
    )

    # ── Measurements ────────────────────────────────────────────────────────
    current_measurement: Optional[WallThicknessMeasurement] = Field(
        default=None, description="Most recent wall thickness measurement"
    )
    initial_measurement: Optional[WallThicknessMeasurement] = Field(
        default=None, description="Baseline wall thickness measurement"
    )
    minimum_required_thickness_mm: Optional[float] = Field(
        default=None,
        description="Minimum allowable retirement thickness in mm",
        gt=0.0,
    )

    # ── Calculations ────────────────────────────────────────────────────────
    calculation: Optional[CorrosionCalculation] = Field(
        default=None, description="Corrosion-rate and remaining-life calculation payload"
    )

    # ── Findings and Conclusions ─────────────────────────────────────────────
    findings: List[InspectionFinding] = Field(
        default_factory=list, description="Ordered list of inspection findings"
    )
    conclusion: Optional[str] = Field(
        default=None, description="Overall conclusion of the inspection analysis"
    )
    recommendation: Optional[RecommendationCode] = Field(
        default=None, description="Standardised recommended action code"
    )

    # ── Evidence and Provenance ──────────────────────────────────────────────
    citations: List[SourceCitation] = Field(
        default_factory=list,
        description=(
            "Source citations from Phase 6 RAG retrieval grounding this result. "
            "Preserved verbatim; never fabricated by the validation layer."
        ),
    )
    confidence: Optional[float] = Field(
        default=None,
        description="Overall confidence score (0.0–1.0) as supplied by Phase 7 Agent",
        ge=0.0,
        le=1.0,
    )


# ── Validation Result ───────────────────────────────────────────────────────────

class ValidationErrorDetail(BaseModel):
    """Structured error detail for one validation failure."""
    model_config = ConfigDict(extra="forbid")

    field: Optional[str] = Field(default=None, description="Dot-path field that failed")
    code: str = Field(..., description="Machine-readable error code (e.g. INVALID_TYPE)")
    message: str = Field(..., description="Human-readable explanation of the failure")
    stage: Optional[str] = Field(default=None, description="Validation stage that raised this error")


class ValidationResult(BaseModel):
    """
    Authoritative Phase 9 validation result returned by StructuredOutputService.

    Differentiates:
      VALID               — all checks passed
      INVALID             — engineering or schema checks failed
      INSUFFICIENT_EVIDENCE — structure is valid but lacks required provenance
      CALCULATION_MISMATCH — independently recomputed value differs from claimed value
      SCHEMA_ERROR        — Pydantic validation failure
      PARSING_ERROR       — JSON parsing failure

    The validated_data field is only populated when status == VALID.
    """
    model_config = ConfigDict(extra="forbid")

    valid: bool = Field(..., description="True if and only if all validation checks passed")
    status: str = Field(..., description="Validation outcome status code")
    validated_data: Optional[Union[CorrosionAuditResult, CorrosionCalculation]] = Field(
        default=None,
        description="The fully validated structured result (only populated when valid=True)",
    )
    errors: List[ValidationErrorDetail] = Field(
        default_factory=list, description="Structured list of validation errors"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Non-fatal warnings that do not invalidate the result"
    )
    validation_checks: List[str] = Field(
        default_factory=list, description="Names of all validation checks that were run"
    )
    checks_passed: List[str] = Field(
        default_factory=list, description="Names of checks that passed"
    )
    checks_failed: List[str] = Field(
        default_factory=list, description="Names of checks that failed"
    )
    calculation_tolerance_mm_per_year: Optional[float] = Field(
        default=None, description="Tolerance used in corrosion-rate calculation verification"
    )
