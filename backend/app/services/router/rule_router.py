"""
SIH26117 — Rule Router (Level 0)
Deterministic keyword-rule based task classifier.

DESIGN:
- Evaluates the ROUTING_RULES_SORTED list in ascending priority order.
- Collects all rules that fire (one or more pattern matches).
- Selects the winner: the fired rule with the lowest priority number
  (ties broken by higher base_confidence, then rule_id alphabetically).
- Applies confidence threshold and fallback policy.
- Returns a fully populated RoutingDecision with complete audit evidence.

PERFORMANCE:
- All classification is pure string matching (no LLM, no network, no disk I/O).
- Target latency: < 1 ms for typical prompts on any modern CPU.

PORTABILITY:
- No OS-specific code.  No GPU.  No CUDA.  No Ollama.  No cloud APIs.
- Operates identically on Windows development machines and Linux deployments.

ACCURACY DISCLAIMER:
- Rule routing accuracy has NOT been formally benchmarked against a held-out test set.
- The confidence values are the rule author's signal-strength estimates, not measured
  classification accuracy.

CONFIGURATION:
- fallback_threshold: confidence value below which fallback is engaged (default 0.70).
- fallback_role:      model role used when fallback fires (default 'reasoning').
- Custom rules can be injected at construction time for testing.
"""

import logging
import time
from typing import Dict, List, Optional

try:
    from app.services.router.base import TaskRouter
    from app.services.router.decision import RoutingDecision, RuleMatchEvidence
    from app.services.router.rules import ROUTING_RULES_SORTED, RoutingRule
    from app.services.router.taxonomy import (
        Capability,
        ModelRole,
        TaskType,
        capability_for_task,
        role_for_task,
    )
except ImportError:
    from backend.app.services.router.base import TaskRouter
    from backend.app.services.router.decision import RoutingDecision, RuleMatchEvidence
    from backend.app.services.router.rules import ROUTING_RULES_SORTED, RoutingRule
    from backend.app.services.router.taxonomy import (
        Capability,
        ModelRole,
        TaskType,
        capability_for_task,
        role_for_task,
    )

logger = logging.getLogger(__name__)

# Default router configuration values
_DEFAULT_FALLBACK_THRESHOLD: float = 0.70
_DEFAULT_FALLBACK_ROLE: ModelRole = ModelRole.REASONING
_DEFAULT_FALLBACK_TASK_TYPE: TaskType = TaskType.GENERAL


class RuleRouter(TaskRouter):
    """
    Level 0 deterministic rule-based task router.

    Args:
        rules:               Ordered list of RoutingRules to evaluate.
                             Defaults to ROUTING_RULES_SORTED.
        fallback_threshold:  Confidence below which fallback is engaged.
        fallback_role:       ModelRole used when fallback fires.
        fallback_task_type:  TaskType reported when fallback fires with no rule match.
    """

    def __init__(
        self,
        rules: Optional[List[RoutingRule]] = None,
        fallback_threshold: float = _DEFAULT_FALLBACK_THRESHOLD,
        fallback_role: ModelRole = _DEFAULT_FALLBACK_ROLE,
        fallback_task_type: TaskType = _DEFAULT_FALLBACK_TASK_TYPE,
    ) -> None:
        self._rules = rules if rules is not None else ROUTING_RULES_SORTED
        self._fallback_threshold = fallback_threshold
        self._fallback_role = fallback_role
        self._fallback_task_type = fallback_task_type

    # ------------------------------------------------------------------ #
    # TaskRouter interface
    # ------------------------------------------------------------------ #

    def route(
        self,
        task: str,
        context: Optional[Dict] = None,
        request_id: Optional[str] = None,
    ) -> RoutingDecision:
        """
        Classify the task and return a RoutingDecision.

        Algorithm:
        1. Normalise task text to lowercase.
        2. Evaluate all enabled rules; collect firing rules + their matches.
        3. Sort candidates: primary sort = priority (ascending), secondary = confidence (desc).
        4. Select winner = candidates[0] (lowest priority = highest precedence).
        5. If no rule fires → produce a low-confidence fallback decision.
        6. Apply fallback threshold: if confidence < threshold → override model_role.
        7. Build and return RoutingDecision with full audit evidence.

        Note: Does NOT make any network calls, LLM calls, or disk I/O.
        """
        if not task or not task.strip():
            return self._empty_task_decision(request_id)

        text = task.strip().lower()
        candidates: List[RuleMatchEvidence] = self._evaluate_rules(text)

        if not candidates:
            return self._no_match_decision(task, request_id)

        # Winner = lowest priority (ascending), then highest confidence (descending)
        candidates_sorted = sorted(
            candidates, key=lambda c: (
                next(
                    r.priority for r in self._rules if r.rule_id == c.rule_id
                ),
                -c.confidence,
            )
        )
        winner = candidates_sorted[0]

        task_type = winner.task_type
        capability = capability_for_task(task_type)
        model_role = role_for_task(task_type)
        confidence = winner.confidence

        # Fallback check
        fallback_used = confidence < self._fallback_threshold
        if fallback_used:
            model_role = self._fallback_role
            logger.info(
                "RuleRouter: confidence %.2f < threshold %.2f → fallback to role '%s'. "
                "Original task_type='%s', rule='%s'.",
                confidence,
                self._fallback_threshold,
                self._fallback_role,
                task_type,
                winner.rule_id,
            )

        reason = self._format_reason(winner, fallback_used)

        return RoutingDecision(
            task_type=task_type,
            capability=capability,
            model_role=model_role,
            confidence=confidence,
            routing_method="rules",
            fallback_used=fallback_used,
            reason=reason,
            matched_rule_ids=[c.rule_id for c in candidates],
            primary_rule_id=winner.rule_id,
            candidates=candidates_sorted,
            request_id=request_id,
            timestamp=time.time(),
        )

    def is_available(self) -> bool:
        return True

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _evaluate_rules(self, text: str) -> List[RuleMatchEvidence]:
        """Evaluate all rules against text; return evidence for all that fire."""
        results: List[RuleMatchEvidence] = []
        for rule in self._rules:
            matched, patterns = rule.match(text)
            if matched:
                results.append(
                    RuleMatchEvidence(
                        rule_id=rule.rule_id,
                        matched_patterns=patterns,
                        task_type=rule.task_type,
                        confidence=rule.base_confidence,
                        reason=rule.reason_template.format(
                            matched=patterns[0] if patterns else ""
                        ),
                    )
                )
        return results

    def _format_reason(self, winner: RuleMatchEvidence, fallback_used: bool) -> str:
        """Format a human-readable reason string for the routing decision."""
        base = winner.reason
        if fallback_used:
            base += (
                f" However, confidence {winner.confidence:.2f} is below the "
                f"fallback threshold {self._fallback_threshold:.2f}. "
                f"Routing to fallback role '{self._fallback_role}'."
            )
        return base

    def _empty_task_decision(self, request_id: Optional[str]) -> RoutingDecision:
        """Return a low-confidence fallback decision for empty or whitespace-only tasks."""
        return RoutingDecision(
            task_type=self._fallback_task_type,
            capability=Capability.GENERAL,
            model_role=self._fallback_role,
            confidence=0.0,
            routing_method="fallback",
            fallback_used=True,
            reason="Task is empty or whitespace-only. Routing to fallback role.",
            matched_rule_ids=[],
            primary_rule_id=None,
            candidates=[],
            request_id=request_id,
            timestamp=time.time(),
        )

    def _no_match_decision(self, task: str, request_id: Optional[str]) -> RoutingDecision:
        """Return a low-confidence fallback decision when no rule matches."""
        logger.info(
            "RuleRouter: no rule matched task (len=%d). Routing to fallback.", len(task)
        )
        return RoutingDecision(
            task_type=self._fallback_task_type,
            capability=Capability.GENERAL,
            model_role=self._fallback_role,
            confidence=0.0,
            routing_method="fallback",
            fallback_used=True,
            reason=(
                "No routing rule matched the task. "
                f"Routing to fallback role '{self._fallback_role}'."
            ),
            matched_rule_ids=[],
            primary_rule_id=None,
            candidates=[],
            request_id=request_id,
            timestamp=time.time(),
        )

    # ------------------------------------------------------------------ #
    # Introspection helpers (used by tests and documentation)
    # ------------------------------------------------------------------ #

    @property
    def fallback_threshold(self) -> float:
        """The confidence threshold below which fallback is triggered."""
        return self._fallback_threshold

    @property
    def rules(self) -> List[RoutingRule]:
        """The list of rules this router evaluates, in evaluation order."""
        return list(self._rules)

    @classmethod
    def from_settings(cls) -> "RuleRouter":
        """
        Build a production RuleRouter from the application's Settings singleton.
        Router-specific settings (threshold, fallback role) are read from config.
        """
        try:
            from app.core.config import get_settings
        except ImportError:
            from backend.app.core.config import get_settings

        settings = get_settings()
        return cls(
            fallback_threshold=getattr(
                settings, "router_fallback_threshold", _DEFAULT_FALLBACK_THRESHOLD
            ),
            fallback_role=ModelRole(
                getattr(settings, "router_fallback_role", _DEFAULT_FALLBACK_ROLE.value)
            ),
        )
