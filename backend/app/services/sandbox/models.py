"""
SIH26117 — Sandboxed Engineering Calculation Models
Defines strongly typed input and output contracts for approved deterministic tools.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class MinimumWallThicknessInput(BaseModel):
    """Input parameters for deterministic minimum wall thickness evaluation."""

    model_config = ConfigDict(extra="forbid")

    measured_thickness_mm: float = Field(
        ...,
        description="Current measured pipe wall thickness in millimeters",
        examples=[3.8],
    )
    minimum_required_mm: float = Field(
        ...,
        description="Minimum allowable retirement wall thickness in millimeters",
        examples=[3.2],
    )
    component_id: Optional[str] = Field(
        default=None,
        description="Optional tag identifier (e.g. 10-HC-101)",
    )

    @field_validator("measured_thickness_mm")
    @classmethod
    def validate_measured_thickness(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Measured wall thickness must be strictly positive (> 0 mm).")
        if v > 500:
            raise ValueError("Measured wall thickness exceeds realistic piping bounds (<= 500 mm).")
        return v

    @field_validator("minimum_required_mm")
    @classmethod
    def validate_minimum_required(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Minimum required wall thickness must be strictly positive (> 0 mm).")
        if v > 500:
            raise ValueError("Minimum required wall thickness exceeds realistic piping bounds (<= 500 mm).")
        return v


class MinimumWallThicknessOutput(BaseModel):
    """Structured calculation result for minimum wall thickness evaluation."""

    model_config = ConfigDict(extra="forbid")

    component_id: Optional[str] = None
    measured_thickness_mm: float
    minimum_required_mm: float
    margin_mm: float
    status: str = Field(
        ...,
        description="Condition status: 'PASS' (margin >= 0.5 mm), 'MONITOR' (0.0 <= margin < 0.5 mm), or 'RETIRE' (margin < 0 mm)",
    )
    is_acceptable: bool
    formula_applied: str = "margin_mm = measured_thickness_mm - minimum_required_mm"


class CorrosionRateInput(BaseModel):
    """Input parameters for deterministic corrosion rate and remaining life estimation."""

    model_config = ConfigDict(extra="forbid")

    previous_thickness_mm: float = Field(
        ...,
        description="Baseline or previous measured wall thickness in millimeters",
        examples=[10.5],
    )
    current_thickness_mm: float = Field(
        ...,
        description="Most recent measured wall thickness in millimeters",
        examples=[9.8],
    )
    elapsed_time_years: float = Field(
        ...,
        description="Time interval between measurements in years",
        examples=[2.5],
    )
    minimum_required_mm: Optional[float] = Field(
        default=None,
        description="Optional retirement wall thickness threshold in millimeters",
        examples=[3.2],
    )
    component_id: Optional[str] = Field(
        default=None,
        description="Optional equipment or pipe circuit tag",
    )

    @field_validator("previous_thickness_mm", "current_thickness_mm")
    @classmethod
    def validate_thickness(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Wall thickness must be strictly positive (> 0 mm).")
        return v

    @field_validator("elapsed_time_years")
    @classmethod
    def validate_elapsed_time(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Elapsed time must be strictly positive (> 0 years).")
        return v


class CorrosionRateOutput(BaseModel):
    """Structured calculation result for corrosion rate and remaining life."""

    model_config = ConfigDict(extra="forbid")

    component_id: Optional[str] = None
    previous_thickness_mm: float
    current_thickness_mm: float
    elapsed_time_years: float
    metal_loss_mm: float
    corrosion_rate_mm_per_year: float
    remaining_life_years: Optional[float] = None
    remaining_life_status: str = Field(
        ...,
        description="Remaining life category: 'CALCULATED', 'STABLE' (zero metal loss), 'NEGATIVE_LOSS' (thickness increased/reading anomaly), or 'NOT_APPLICABLE'",
    )
    formula_applied: str = (
        "corrosion_rate = (previous_thickness - current_thickness) / elapsed_time; "
        "remaining_life = (current_thickness - minimum_required) / corrosion_rate"
    )
