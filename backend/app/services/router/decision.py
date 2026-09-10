"""
SIH26117 — RoutingDecision Contract
Strongly-typed output of the task router pipeline.

FIELD SEMANTICS:
- request_id      — Caller-supplied ID for correlation with audit logs (optional).
- task_type       — The detected task category from the TaskType taxonomy.
- capability      — The processing modality required (from Capability enum).
- model_role      — The model slot name to invoke in ModelManager.
- confidence      — Normalised routing certainty [0.0, 1.0].
- routing_method  — Which router level produced this decision ('rules', 'semantic',
                    'classifier', 'hybrid', 'fallback').
- fallback_used   — True if confidence < threshold and fallback role was substituted.
- reason          — Human-readable English explanation of the routing decision.
- matched_rule_ids — IDs of all rules that fired (for auditability).
- primary_rule_id  — ID of the rule with the highest score (or None for fallback).
- candidates      — All competing rule matches preserved for debugging.
- timestamp       — Unix epoch when the decision was produced.

CONFIDENCE CALCULATION (Level 0 — Rule Router):
- Each RoutingRule carries a base_confidence value (0.0–1.0).
- When a rule fires, its base_confidence becomes the decision confidence.
- If multiple rules fire, the highest-scoring rule wins; all matches are preserved.
- Rules that match on single-keyword patterns carry lower confidence (~0.70–0.80).
- Rules that match on domain-specific multi-pattern signals carry higher (~0.85–0.95).
- If no rule fires, confidence = 0.0 and fallback_used = True.
- Confidence values are ASSERTED by rule definition, not measured statistically.
- Rule routing accuracy has NOT been formally benchmarked against a held-out test set.

FALLBACK POLICY:
- If confidence < router_fallback_threshold (default 0.70), fallback_used = True.
- The model_role is overridden to the configured fallback role (default 'reasoning').
- The original task_type classification is preserved (not overwritten to GENERAL).
"""

import time
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field

try:
    from app.services.router.taxonomy import Capability, ModelRole, TaskType
except ImportError:
    from backend.app.services.router.taxonomy import Capability, ModelRole, TaskType


class RuleMatchEvidence(BaseModel):
    """Preserved evidence from one fired routing rule — for audit and debugging."""

    rule_id: str
    matched_patterns: List[str]
    task_type: TaskType
    confidence: float
    reason: str


class RoutingDecision(BaseModel):
    """
    Strongly-typed, immutable output of the task routing pipeline.
    Consumed by the Agent Orchestrator (Phase 4) and persisted by the Audit System.
    """

    model_config = {"protected_namespaces": ()}

    # ── Core routing output ────────────────────────────────────────────────
    task_type: TaskType = Field(
        ..., description="Detected task category from the TaskType taxonomy."
    )
    capability: Capability = Field(
        ..., description="Processing modality required to fulfil the task."
    )
    model_role: ModelRole = Field(
        ...,
        description=(
            "Model slot name to invoke in ModelManager. "
            "Must match a role key in model_tiers.yaml."
        ),
    )

    # ── Confidence & method ────────────────────────────────────────────────
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalised routing certainty. See module docstring for calculation policy.",
    )
    routing_method: str = Field(
        ...,
        description=(
            "Router level that produced this decision: "
            "'rules' | 'semantic' | 'classifier' | 'hybrid' | 'fallback'."
        ),
    )
    fallback_used: bool = Field(
        default=False,
        description="True when confidence < threshold and the fallback role was substituted.",
    )

    # ── Human-readable explanation ─────────────────────────────────────────
    reason: str = Field(
        ..., description="Plain-English explanation of why this routing decision was made."
    )

    # ── Audit evidence ─────────────────────────────────────────────────────
    matched_rule_ids: List[str] = Field(
        default_factory=list,
        description="IDs of all routing rules that matched the input task.",
    )
    primary_rule_id: Optional[str] = Field(
        default=None,
        description="ID of the winning (highest-confidence) rule, or None for fallback.",
    )
    candidates: List[RuleMatchEvidence] = Field(
        default_factory=list,
        description="All competing rule matches preserved for debugging and audit.",
    )

    # ── Correlation & timing ───────────────────────────────────────────────
    request_id: Optional[str] = Field(
        default=None,
        description="Caller-supplied ID for correlation with request logs and audit events.",
    )
    timestamp: float = Field(
        default_factory=time.time,
        description="Unix epoch time when the routing decision was produced.",
    )

    # ── Optional metadata ─────────────────────────────────────────────────
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary key-value metadata for downstream consumers.",
    )
