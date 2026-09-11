"""
SIH26117 — Phase 9: Validation API Schemas
Request and response schemas for POST /api/v1/validation/validate.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class ValidationRequest(BaseModel):
    """Request body for POST /api/v1/validation/validate."""

    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(
        ...,
        description=(
            "Structured agent/model output to validate. "
            "Must be a JSON-serialisable dict conforming to CorrosionAuditResult schema."
        ),
    )
    rate_tolerance: Optional[float] = Field(
        default=None,
        description="Optional override for corrosion-rate calculation tolerance (mm/yr)",
        gt=0.0,
        le=1.0,
    )
    require_citations: Optional[bool] = Field(
        default=None,
        description=(
            "If True (default), citations are required when findings are present. "
            "Set False only for draft/ungrounded analysis."
        ),
    )
