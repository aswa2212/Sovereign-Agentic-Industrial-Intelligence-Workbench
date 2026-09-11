"""
SIH26117 — Agent Reflector & Loop Protection Guardrails
Evaluates step outcomes, manages explicit retries (maximum 2), prevents unbounded loops,
and decides whether to continue, retry, fail, or proceed to validation.
"""

import logging
from typing import Optional

try:
    from app.core.config import get_settings
    from app.services.agent.models import AgentContext, StepObservation, StepReflection
except ImportError:
    from backend.app.core.config import get_settings
    from backend.app.services.agent.models import AgentContext, StepObservation, StepReflection

logger = logging.getLogger(__name__)


class Reflector:
    """
    Evaluates step execution results and produces explicit operational directives.
    Enforces loop protection against runaway retries and excessive step counts.
    """

    def __init__(
        self,
        max_steps: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        settings = get_settings()
        self.max_steps = max_steps or settings.agent_max_steps
        self.max_retries = max_retries or settings.agent_max_retries

    async def reflect(
        self,
        context: AgentContext,
        observation: StepObservation,
    ) -> StepReflection:
        """
        Analyze step observation and decide next lifecycle direction:
        - 'CONTINUE': proceed to next planned step.
        - 'RETRY': re-execute current step up to max_retries limit.
        - 'FAIL': abort workflow due to fatal error or safety ceiling.
        - 'COMPLETE': all plan steps successfully executed; proceed to VALIDATE.
        """
        step_id = observation.step_id

        # Safety Invariant 1: Total Step Ceiling
        if context.step_count >= self.max_steps:
            logger.warning("Task [%s] hit max steps ceiling (%d)", context.task_id[:8], self.max_steps)
            return StepReflection(
                step_id=step_id,
                decision="FAIL",
                reason=f"Safety limit exceeded: total steps reached maximum allowable ceiling ({self.max_steps}).",
                suggested_action="Terminate execution with MAX_STEPS_EXCEEDED.",
            )

        # Safety Invariant 2: Handle step failures and retries
        if not observation.success:
            current_step = None
            if context.plan and context.current_step_index < len(context.plan.steps):
                current_step = context.plan.steps[context.current_step_index]

            current_retries = current_step.retry_count if current_step else 0

            if current_retries < self.max_retries:
                if current_step:
                    current_step.retry_count += 1
                context.retry_count += 1

                logger.info(
                    "Task [%s] step %s failed; triggering retry %d/%d",
                    context.task_id[:8],
                    step_id,
                    current_retries + 1,
                    self.max_retries,
                )
                return StepReflection(
                    step_id=step_id,
                    decision="RETRY",
                    reason=f"Step execution failed: {observation.error}. Retrying ({current_retries + 1}/{self.max_retries}).",
                    suggested_action="Re-execute step with adjusted parameters.",
                    retry_suggested=True,
                )
            else:
                logger.error(
                    "Task [%s] step %s exceeded max retries (%d)",
                    context.task_id[:8],
                    step_id,
                    self.max_retries,
                )
                return StepReflection(
                    step_id=step_id,
                    decision="FAIL",
                    reason=f"Step {step_id} failed after {self.max_retries} retries: {observation.error}",
                    suggested_action="Terminate execution with MAX_RETRIES_EXCEEDED.",
                )

        # Step succeeded: Check whether more steps remain
        if context.plan:
            next_idx = context.current_step_index + 1
            if next_idx < len(context.plan.steps):
                return StepReflection(
                    step_id=step_id,
                    decision="CONTINUE",
                    reason=f"Step {step_id} succeeded. Advancing to step {context.plan.steps[next_idx].id}.",
                    suggested_action="Execute next plan step.",
                )

        # All steps exhausted successfully
        return StepReflection(
            step_id=step_id,
            decision="COMPLETE",
            reason=f"All plan steps completed successfully.",
            suggested_action="Proceed to VALIDATE phase.",
        )
