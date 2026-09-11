"""
SIH26117 — Agent State Machine Orchestrator
Coordinates the complete 11-state autonomous reasoning lifecycle:
RECEIVE -> UNDERSTAND -> PLAN -> EXECUTE -> OBSERVE -> REFLECT -> VALIDATE -> FINALIZE -> DELIVER
Enforces per-step timeouts (45s) and global execution timeouts (180s).
"""

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, Optional

try:
    from app.core.config import get_settings
    from app.services.agent.base import (
        AgentEvent,
        AgentState,
        AgentTimeoutError,
    )
    from app.services.agent.models import (
        AgentContext,
        StepObservation,
        utc_now_iso,
    )
    from app.services.agent.planner import Planner
    from app.services.agent.reflector import Reflector
    from app.services.agent.state_machine import AgentStateMachine
    from app.services.agent.tools import ToolRegistry
    from app.services.agent.validator import Validator
    from app.services.router.rule_router import RuleRouter
except ImportError:
    from backend.app.core.config import get_settings
    from backend.app.services.agent.base import (
        AgentEvent,
        AgentState,
        AgentTimeoutError,
    )
    from backend.app.services.agent.models import (
        AgentContext,
        StepObservation,
        utc_now_iso,
    )
    from backend.app.services.agent.planner import Planner
    from backend.app.services.agent.reflector import Reflector
    from backend.app.services.agent.state_machine import AgentStateMachine
    from backend.app.services.agent.tools import ToolRegistry
    from backend.app.services.agent.validator import Validator
    from backend.app.services.router.rule_router import RuleRouter

logger = logging.getLogger(__name__)


class AgentStateMachineOrchestrator:
    """
    State machine orchestrator managing end-to-end task execution.
    """

    def __init__(
        self,
        router: Optional[RuleRouter] = None,
        planner: Optional[Planner] = None,
        tool_registry: Optional[ToolRegistry] = None,
        reflector: Optional[Reflector] = None,
        validator: Optional[Validator] = None,
    ) -> None:
        settings = get_settings()
        self.router = router or RuleRouter()
        self.planner = planner or Planner()
        self.tool_registry = tool_registry or ToolRegistry()
        self.reflector = reflector or Reflector()
        self.validator = validator or Validator()

        self.step_timeout = settings.agent_step_timeout_seconds
        self.global_timeout = settings.agent_global_timeout_seconds

        # In-memory store of executed tasks
        self._tasks: Dict[str, AgentContext] = {}

    def get_task_context(self, task_id: str) -> Optional[AgentContext]:
        """Retrieve stored task execution context."""
        return self._tasks.get(task_id)

    async def execute_task(
        self,
        task: str,
        task_id: Optional[str] = None,
        max_steps: Optional[int] = None,
    ) -> AgentContext:
        """
        Execute an agent task through the deterministic 11-state lifecycle.
        """
        t_id = task_id or uuid.uuid4().hex
        now = utc_now_iso()
        start_time = time.monotonic()

        context = AgentContext(
            task_id=t_id,
            user_request=task.strip(),
            current_state=AgentState.IDLE,
            started_at=now,
            updated_at=now,
        )
        self._tasks[t_id] = context

        try:
            # ── 1. RECEIVE ────────────────────────────────────────────────────
            AgentStateMachine.transition(
                context, AgentState.RECEIVE, message=f"Received task: {task[:80]}"
            )

            # ── 2. UNDERSTAND (Call Phase 3 Task Router) ──────────────────────
            AgentStateMachine.transition(
                context, AgentState.UNDERSTAND, message="Classifying task intent via Task Router"
            )
            context.routing_decision = self.router.route(
                task=context.user_request,
                request_id=context.task_id,
            )

            # ── 3. PLAN ───────────────────────────────────────────────────────
            AgentStateMachine.transition(
                context, AgentState.PLAN, message="Generating structured execution plan"
            )
            planner = self.planner if max_steps is None else Planner(max_steps=max_steps)
            context.plan = await planner.create_plan(
                task=context.user_request,
                task_id=context.task_id,
                routing_decision=context.routing_decision,
            )

            if not context.plan.steps:
                # No steps generated -> proceed directly to validation
                AgentStateMachine.transition(
                    context, AgentState.VALIDATE, message="No plan steps required; verifying directly"
                )
            else:
                # ── 4. EXECUTE / OBSERVE / REFLECT Loop ────────────────────────
                while context.current_step_index < len(context.plan.steps):
                    # Check global timeout
                    if time.monotonic() - start_time > self.global_timeout:
                        raise AgentTimeoutError(
                            f"Global execution timeout exceeded ({self.global_timeout}s)."
                        )

                    step = context.plan.steps[context.current_step_index]
                    step.status = "in_progress"
                    context.step_count += 1

                    # EXECUTE state
                    AgentStateMachine.transition(
                        context,
                        AgentState.EXECUTE,
                        message=f"Executing {step.id}: {step.description}",
                        metadata={"capability": step.capability, "tool": step.tool_name},
                    )

                    tool = self.tool_registry.get_tool(step.tool_name)
                    obs = None

                    if not tool:
                        obs = StepObservation(
                            step_id=step.id,
                            tool_name=step.tool_name,
                            capability=step.capability,
                            success=False,
                            error=f"Tool '{step.tool_name}' not found in registry.",
                        )
                    else:
                        try:
                            # Step timeout protection
                            tool_output = await asyncio.wait_for(
                                tool.execute(step.input_payload, context),
                                timeout=self.step_timeout,
                            )
                            step.status = "completed"
                            step.output_payload = tool_output
                            context.tool_results[step.id] = tool_output

                            obs = StepObservation(
                                step_id=step.id,
                                tool_name=step.tool_name,
                                capability=step.capability,
                                success=True,
                                output=tool_output,
                            )
                        except asyncio.TimeoutError:
                            err = f"Step {step.id} timed out after {self.step_timeout}s."
                            obs = StepObservation(
                                step_id=step.id,
                                tool_name=step.tool_name,
                                capability=step.capability,
                                success=False,
                                error=err,
                            )
                        except Exception as e:
                            logger.error("Tool execution failed: %s", str(e))
                            obs = StepObservation(
                                step_id=step.id,
                                tool_name=step.tool_name,
                                capability=step.capability,
                                success=False,
                                error=str(e),
                            )

                    context.observations.append(obs)

                    # OBSERVE state
                    AgentStateMachine.transition(
                        context,
                        AgentState.OBSERVE,
                        message=f"Observation recorded for {step.id}: success={obs.success}",
                        metadata={"success": obs.success},
                    )

                    # REFLECT state
                    AgentStateMachine.transition(
                        context,
                        AgentState.REFLECT,
                        message=f"Reflecting on outcome of {step.id}",
                    )
                    reflection = await self.reflector.reflect(context, obs)
                    context.reflection = reflection

                    if reflection.decision == "FAIL":
                        context.errors.append(reflection.reason)
                        AgentStateMachine.transition(
                            context,
                            AgentState.FAILED,
                            message=f"Aborted during reflection: {reflection.reason}",
                        )
                        return context
                    elif reflection.decision == "RETRY":
                        # Loop continues on the same step
                        continue
                    elif reflection.decision == "CONTINUE":
                        context.current_step_index += 1
                    elif reflection.decision == "COMPLETE":
                        context.current_step_index += 1
                        break

            # ── 5. VALIDATE ───────────────────────────────────────────────────
            if time.monotonic() - start_time > self.global_timeout:
                raise AgentTimeoutError(
                    f"Global execution timeout exceeded ({self.global_timeout}s)."
                )

            if context.current_state != AgentState.FAILED:
                AgentStateMachine.transition(
                    context, AgentState.VALIDATE, message="Validating final outputs and provenance"
                )
                val_res = await self.validator.validate(context)
                context.validation_result = val_res

                if not val_res.is_valid:
                    context.errors.extend(val_res.checks_failed)
                    AgentStateMachine.transition(
                        context,
                        AgentState.FAILED,
                        message=f"Validation checks failed: {', '.join(val_res.checks_failed)}",
                    )
                    return context

                # ── 6. FINALIZE ───────────────────────────────────────────────
                AgentStateMachine.transition(
                    context, AgentState.FINALIZE, message="Packaging intermediate results into deliverable"
                )
                context.final_result = self._build_final_result(context)

                # ── 7. DELIVER ────────────────────────────────────────────────
                AgentStateMachine.transition(
                    context, AgentState.DELIVER, message="Delivering finalized result"
                )

        except Exception as e:
            logger.error("Agent workflow error on task [%s]: %s", context.task_id[:8], str(e))
            context.errors.append(str(e))
            if context.current_state != AgentState.FAILED:
                try:
                    AgentStateMachine.transition(
                        context, AgentState.FAILED, message=f"Fatal exception: {str(e)}"
                    )
                except Exception:
                    context.current_state = AgentState.FAILED

        return context

    def _build_final_result(self, context: AgentContext) -> Dict[str, Any]:
        """Synthesize final deliverable payload from observations and citations."""
        citations = context.get_citations()
        summary_lines = []

        if context.retrieved_context:
            top_chunk = context.retrieved_context[0]
            summary_lines.append(f"Grounded in {top_chunk.source_document} (Page {top_chunk.page_number}):")
            summary_lines.append(top_chunk.text)

        calc_result = None
        for obs in context.observations:
            if obs.capability == "calculation" and obs.success:
                calc_result = obs.output

        return {
            "task": context.user_request,
            "status": "success",
            "summary": "\n\n".join(summary_lines) if summary_lines else "Task completed successfully.",
            "citations_count": len(citations),
            "citations": [c.model_dump() for c in citations],
            "calculation": calc_result,
            "total_steps_executed": context.step_count,
            "total_retries": context.retry_count,
        }
