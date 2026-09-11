"""
SIH26117 — Agent Deterministic Validator
Performs rigorous structural, provenance, and output integrity checks before task finalization.
Does NOT rely on subjective LLM assertions.
"""

import logging
from typing import List

try:
    from app.services.agent.models import AgentContext, ValidationResult
except ImportError:
    from backend.app.services.agent.models import AgentContext, ValidationResult

logger = logging.getLogger(__name__)


class Validator:
    """
    Validates completed agent workflows to ensure audit integrity and grounded facts.
    """

    async def validate(self, context: AgentContext) -> ValidationResult:
        """
        Execute deterministic validation assertions on context.
        """
        checks_passed: List[str] = []
        checks_failed: List[str] = []

        # Check 1: Plan completion
        if context.plan and context.plan.steps:
            all_completed = all(s.status == "completed" for s in context.plan.steps)
            if all_completed:
                checks_passed.append("all_plan_steps_completed")
            else:
                checks_failed.append("uncompleted_plan_steps_remain")
        else:
            checks_passed.append("no_plan_required")

        # Check 2: Observations recorded
        if context.observations:
            checks_passed.append("observations_recorded")
        else:
            checks_failed.append("no_step_observations_found")

        # Check 3: Retrieval grounding (if RAG capability was requested)
        rag_planned = False
        if context.plan:
            rag_planned = any(s.capability == "rag_retrieval" for s in context.plan.steps)

        if rag_planned:
            if context.retrieved_context:
                checks_passed.append("grounding_citations_present")
            else:
                checks_failed.append("missing_required_retrieval_grounding")

        # Check 4: Unresolved fatal execution errors
        if not context.errors:
            checks_passed.append("zero_unresolved_errors")
        else:
            checks_failed.append("unresolved_execution_errors")

        is_valid = len(checks_failed) == 0
        conf = 1.0 if is_valid else round(len(checks_passed) / (len(checks_passed) + len(checks_failed)), 2)

        result = ValidationResult(
            is_valid=is_valid,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            confidence=conf,
            notes="All deterministic validation assertions passed." if is_valid else f"Failed checks: {', '.join(checks_failed)}",
        )

        logger.info(
            "Task [%s] validation result: valid=%s (passed=%d, failed=%d)",
            context.task_id[:8],
            is_valid,
            len(checks_passed),
            len(checks_failed),
        )
        return result
