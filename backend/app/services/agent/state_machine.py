"""
SIH26117 — Agent State Machine Transition Rules & Validation
Enforces strict deterministic transitions between lifecycle states and records observable events.
"""

import logging
import uuid
from typing import Any, Dict, Optional, Set

try:
    from app.services.agent.base import (
        AgentEvent,
        AgentState,
        InvalidStateTransitionError,
    )
    from app.services.agent.models import AgentContext, utc_now_iso
except ImportError:
    from backend.app.services.agent.base import (
        AgentEvent,
        AgentState,
        InvalidStateTransitionError,
    )
    from backend.app.services.agent.models import AgentContext, utc_now_iso

logger = logging.getLogger(__name__)

# Strict transition matrix governing permissible state transitions
ALLOWED_TRANSITIONS: Dict[AgentState, Set[AgentState]] = {
    AgentState.IDLE: {AgentState.RECEIVE, AgentState.FAILED},
    AgentState.RECEIVE: {AgentState.UNDERSTAND, AgentState.FAILED},
    AgentState.UNDERSTAND: {AgentState.PLAN, AgentState.FAILED},
    AgentState.PLAN: {AgentState.EXECUTE, AgentState.FAILED},
    AgentState.EXECUTE: {AgentState.OBSERVE, AgentState.FAILED},
    AgentState.OBSERVE: {AgentState.REFLECT, AgentState.FAILED},
    AgentState.REFLECT: {AgentState.EXECUTE, AgentState.VALIDATE, AgentState.FAILED},
    AgentState.VALIDATE: {AgentState.FINALIZE, AgentState.REFLECT, AgentState.FAILED},
    AgentState.FINALIZE: {AgentState.DELIVER, AgentState.FAILED},
    AgentState.DELIVER: set(),  # Terminal state
    AgentState.FAILED: set(),   # Terminal state
}


class AgentStateMachine:
    """
    Manages deterministic transitions across the 11 Agent lifecycle states.
    Emits structured AgentEvent entries into the execution trace.
    """

    @staticmethod
    def is_transition_allowed(from_state: AgentState, to_state: AgentState) -> bool:
        """Check whether a transition between two states is valid."""
        allowed = ALLOWED_TRANSITIONS.get(from_state, set())
        return to_state in allowed

    @staticmethod
    def transition(
        context: AgentContext,
        new_state: AgentState,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentEvent:
        """
        Transition context to new_state if permissible under transition rules.
        Appends event to context execution trace.
        Raises InvalidStateTransitionError if transition is forbidden.
        """
        curr = context.current_state
        if not AgentStateMachine.is_transition_allowed(curr, new_state):
            err_msg = f"Invalid state transition attempted: {curr.value} -> {new_state.value}"
            logger.error(err_msg)
            raise InvalidStateTransitionError(err_msg)

        step_id = None
        if context.plan and context.current_step_index < len(context.plan.steps):
            step_id = context.plan.steps[context.current_step_index].id

        now = utc_now_iso()
        event = AgentEvent(
            event_id=uuid.uuid4().hex[:16],
            task_id=context.task_id,
            state=new_state,
            timestamp=now,
            step_id=step_id,
            message=message or f"State transitioned: {curr.value} -> {new_state.value}",
            metadata=metadata or {},
        )

        context.current_state = new_state
        context.updated_at = now
        context.execution_trace.append(event)

        logger.info(
            "Task [%s] transition: %s -> %s (%s)",
            context.task_id[:8],
            curr.value,
            new_state.value,
            event.message,
        )
        return event
