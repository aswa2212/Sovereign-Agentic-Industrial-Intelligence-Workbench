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
        if context.plan and context.plan.steps:
            rag_planned = any(s.capability == "rag_retrieval" for s in context.plan.steps)

        if not rag_planned:
            # Case 4: RAG not planned
            checks_passed.append("retrieval_not_planned")
        else:
            rag_obs = [
                obs for obs in context.observations
                if obs.capability == "rag_retrieval" or obs.tool_name == "rag_retrieval"
            ]
            if not rag_obs:
                # Case 5: RAG planned but tool never executed
                checks_failed.append("planned_retrieval_step_not_executed")
                checks_failed.append("missing_required_retrieval_grounding")
            elif any(not obs.success for obs in rag_obs):
                # Case 1: RAG tool execution raised an exception or failed
                checks_failed.append("retrieval_tool_execution_failed")
                checks_failed.append("missing_required_retrieval_grounding")
            elif context.retrieved_context:
                # Case 3: RAG tool successful and retrieved relevant chunks
                checks_passed.append("grounding_citations_present")
            else:
                # Check if the tool explicitly executed and returned a verified zero-result payload
                zero_result_verified = any(
                    isinstance(obs.output, dict) and obs.output.get("retrieved_count") == 0
                    for obs in rag_obs
                )
                if zero_result_verified:
                    # Case 2: RAG tool executed successfully but returned zero relevant chunks (insufficient knowledge).
                    # Valid execution with no matching knowledge; represents insufficient knowledge without fabricating grounding.
                    checks_passed.append("retrieval_completed_insufficient_knowledge")
                else:
                    # Missing grounding without verified zero-result retrieval payload
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
