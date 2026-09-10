"""
SIH26117 — Task Router API Schemas
Pydantic request and response contracts for POST /api/v1/router/route.
"""

import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RouteRequest(BaseModel):
    """Request body for POST /api/v1/router/route."""

    task: str = Field(
        ...,
        min_length=1,
        description="Raw user task text to classify and route.",
        examples=["Analyze the corrosion inspection report for pipe P-104."],
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Optional caller-supplied correlation ID for audit logging.",
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Optional contextual metadata (e.g. file_ids, mime_type). "
            "Used by future Level 1/2 routers; ignored by Level 0."
        ),
    )


class RuleEvidenceSchema(BaseModel):
    """API representation of one fired routing rule (audit evidence)."""

    rule_id: str
    matched_patterns: List[str]
    task_type: str
    confidence: float
    reason: str


class RouteResponse(BaseModel):
    """Response for POST /api/v1/router/route."""

    model_config = {"protected_namespaces": ()}

    # Core routing output
    task_type: str = Field(..., description="Detected task category.")
    capability: str = Field(..., description="Processing modality required.")
    model_role: str = Field(
        ...,
        description=(
            "Model slot to invoke in ModelManager. "
            "Matches a role key in model_tiers.yaml."
        ),
    )

    # Confidence & method
    confidence: float = Field(..., ge=0.0, le=1.0)
    routing_method: str = Field(
        ...,
        description="Router level: 'rules' | 'semantic' | 'classifier' | 'fallback'.",
    )
    fallback_used: bool = Field(
        ...,
        description="True when confidence was below threshold and fallback role was used.",
    )

    # Human-readable explanation
    reason: str = Field(..., description="Plain-English explanation of the routing decision.")

    # Audit evidence
    matched_rule_ids: List[str] = Field(default_factory=list)
    primary_rule_id: Optional[str] = Field(default=None)
    candidates: List[RuleEvidenceSchema] = Field(default_factory=list)

    # Correlation & timing
    request_id: Optional[str] = Field(default=None)
    timestamp: float = Field(default_factory=time.time)
