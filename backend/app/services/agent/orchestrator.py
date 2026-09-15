"""
SIH26117 — Agent State Machine Orchestrator
Coordinates the complete 11-state autonomous reasoning lifecycle:
RECEIVE -> UNDERSTAND -> PLAN -> EXECUTE -> OBSERVE -> REFLECT -> VALIDATE -> FINALIZE -> DELIVER
Enforces per-step timeouts (45s) and global execution timeouts (180s).
Phase 9: VALIDATE state strengthened with StructuredOutputService when final_result is available.
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
    from app.services.validation.service import StructuredOutputService as _StructuredOutputService
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
    from backend.app.services.validation.service import StructuredOutputService as _StructuredOutputService

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
        structured_output_service: Optional[_StructuredOutputService] = None,
        audit_service: Optional[Any] = None,
    ) -> None:
        settings = get_settings()
        self.router = router or RuleRouter()
        self.planner = planner or Planner()
        self.tool_registry = tool_registry or ToolRegistry()
        self.reflector = reflector or Reflector()
        self.validator = validator or Validator()
        # Phase 9: optional structured output service (Agent → Service, never reverse)
        self._structured_output_service = structured_output_service or _StructuredOutputService()
        # Phase 11: optional audit service for recording lifecycle evidence
        self.audit_service = audit_service

        self.step_timeout = settings.agent_step_timeout_seconds
        self.global_timeout = settings.agent_global_timeout_seconds

        # In-memory store of executed tasks
        self._tasks: Dict[str, AgentContext] = {}

    def _record_audit(
        self,
        event_type: str,
        action: str,
        task_id: Optional[str] = None,
        agent_state: Optional[str] = None,
        model_role: Optional[str] = None,
        capability: Optional[str] = None,
        tool_name: Optional[str] = None,
        status: str = "SUCCESS",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Safely record an audit event if audit_service is configured."""
        if not self.audit_service:
            return
        try:
            from app.services.audit.models import AuditEventType
            ev_type = AuditEventType(event_type) if isinstance(event_type, str) else event_type
            self.audit_service.record_event(
                event_type=ev_type,
                action=action,
                task_id=task_id,
                agent_state=agent_state,
                model_role=model_role,
                capability=capability,
                tool_name=tool_name,
                status=status,
                metadata=metadata or {},
            )
        except Exception as audit_err:
            logger.warning("Agent audit logging skipped: %s", audit_err)

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
            self._record_audit(
                "TASK_STARTED",
                action=f"Received task: {task[:80]}",
                task_id=context.task_id,
                agent_state="RECEIVE",
            )

            # ── 2. UNDERSTAND (Call Phase 3 Task Router) ──────────────────────
            AgentStateMachine.transition(
                context, AgentState.UNDERSTAND, message="Classifying task intent via Task Router"
            )
            context.routing_decision = self.router.route(
                task=context.user_request,
                request_id=context.task_id,
            )
            self._record_audit(
                "MODEL_ROUTED",
                action=f"Routing intent: {context.routing_decision.task_type.value}",
                task_id=context.task_id,
                agent_state="UNDERSTAND",
                model_role=context.routing_decision.model_role.value,
                capability=context.routing_decision.capability.value,
                metadata={"confidence": context.routing_decision.confidence},
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
            self._record_audit(
                "PLAN_CREATED",
                action=f"Plan generated with {len(context.plan.steps)} step(s)",
                task_id=context.task_id,
                agent_state="PLAN",
                metadata={"step_count": len(context.plan.steps)},
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
                    self._record_audit(
                        "TOOL_STARTED",
                        action=f"Invoking {step.tool_name}",
                        task_id=context.task_id,
                        agent_state="EXECUTE",
                        tool_name=step.tool_name,
                        capability=step.capability,
                        metadata={"step_id": step.id},
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
                    self._record_audit(
                        "TOOL_COMPLETED",
                        action=f"Completed {step.tool_name}",
                        task_id=context.task_id,
                        agent_state="OBSERVE",
                        tool_name=step.tool_name,
                        capability=step.capability,
                        status="SUCCESS" if obs.success else "FAILED",
                        metadata={"step_id": step.id, "success": obs.success, "error": obs.error},
                    )

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
                        self._record_audit(
                            "TASK_FAILED",
                            action=f"Aborted during reflection: {reflection.reason}",
                            task_id=context.task_id,
                            agent_state="FAILED",
                            status="FAILED",
                            metadata={"reason": reflection.reason},
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
                self._record_audit(
                    "VALIDATION_STARTED",
                    action="Validating final outputs and provenance",
                    task_id=context.task_id,
                    agent_state="VALIDATE",
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
                    self._record_audit(
                        "TASK_FAILED",
                        action=f"Validation checks failed: {', '.join(val_res.checks_failed)}",
                        task_id=context.task_id,
                        agent_state="FAILED",
                        status="FAILED",
                        metadata={"checks_failed": val_res.checks_failed},
                    )
                    return context

                # ── 6. FINALIZE ───────────────────────────────────────────────
                AgentStateMachine.transition(
                    context, AgentState.FINALIZE, message="Packaging intermediate results into deliverable"
                )
                self._record_audit(
                    "VALIDATION_COMPLETED",
                    action="Validation succeeded",
                    task_id=context.task_id,
                    agent_state="FINALIZE",
                    status="SUCCESS",
                    metadata={"checks_passed": val_res.checks_passed},
                )
                context.final_result = self._build_final_result(context)

                # Phase 9: validate the structured final_result through StructuredOutputService
                # This is additive strengthening of the VALIDATE->FINALIZE boundary.
                # Only runs when calculation data is present; failures set a warning in context.
                if context.final_result.get("calculation"):
                    try:
                        structured_result = context.final_result.get("calculation", {})
                        if hasattr(self._structured_output_service, "validate_calculation"):
                            svc_result = self._structured_output_service.validate_calculation(structured_result)
                        else:
                            svc_result = self._structured_output_service.validate(structured_result)
                        context.final_result["structured_validation"] = {
                            "valid": svc_result.valid,
                            "status": svc_result.status.value if hasattr(svc_result.status, "value") else str(svc_result.status),
                            "checks_passed": svc_result.checks_passed,
                            "checks_failed": svc_result.checks_failed,
                            "warnings": svc_result.warnings,
                        }
                    except Exception as sv_exc:
                        logger.warning(
                            "Phase 9 structured output validation raised during finalize: %s", str(sv_exc)
                        )
                        context.final_result["structured_validation"] = {
                            "valid": False,
                            "status": "INTERNAL_ERROR",
                            "checks_passed": [],
                            "checks_failed": ["structured_output_service"],
                            "warnings": [str(sv_exc)],
                        }

                # ── 7. DELIVER ────────────────────────────────────────────────
                AgentStateMachine.transition(
                    context, AgentState.DELIVER, message="Delivering finalized result"
                )
                self._record_audit(
                    "TASK_COMPLETED",
                    action="Delivering finalized result",
                    task_id=context.task_id,
                    agent_state="DELIVER",
                    status="SUCCESS",
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
            self._record_audit(
                "TASK_FAILED",
                action=f"Fatal exception: {str(e)}",
                task_id=context.task_id,
                agent_state="FAILED",
                status="FAILED",
                metadata={"error": str(e)},
            )

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
