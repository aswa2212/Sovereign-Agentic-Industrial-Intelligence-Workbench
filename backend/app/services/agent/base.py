"""
SIH26117 — Agent Orchestrator & State Machine Base Interfaces
Defines the explicit 11-state lifecycle, state event models, and exception hierarchy.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AgentState(str, Enum):
    """
    Explicit state-machine lifecycle states for sovereign multi-step reasoning.
    Enforces deterministic progression:
    IDLE -> RECEIVE -> UNDERSTAND -> PLAN -> EXECUTE -> OBSERVE -> REFLECT -> VALIDATE -> FINALIZE -> DELIVER
    or transitions to FAILED upon unrecoverable error.
    """

    IDLE = "IDLE"
    RECEIVE = "RECEIVE"
    UNDERSTAND = "UNDERSTAND"
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    OBSERVE = "OBSERVE"
    REFLECT = "REFLECT"
    VALIDATE = "VALIDATE"
    FINALIZE = "FINALIZE"
    DELIVER = "DELIVER"
    FAILED = "FAILED"

    # Backward-compatible aliases for Phase 1 scaffolding
    PLANNING = "PLAN"
    ACTING = "EXECUTE"
    OBSERVING = "OBSERVE"
    REFLECTING = "REFLECT"
    COMPLETED = "DELIVER"


class AgentEvent(BaseModel):
    """
    Structured, observable trace event emitted during state transitions.
    Provides verifiable audit trail for UI timeline rendering and security provenance.
    """

    model_config = ConfigDict(protected_namespaces=())

    event_id: str = Field(..., description="Unique event identifier")
    task_id: str = Field(..., description="Parent task identifier")
    state: AgentState = Field(..., description="Lifecycle state associated with this event")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    step_id: Optional[str] = Field(default=None, description="Current plan step identifier if applicable")
    message: str = Field(..., description="Human-readable description of event")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary diagnostic metadata")


class AgentStepEvent(BaseModel):
    """Legacy intermediate event for backward compatibility."""

    model_config = ConfigDict(protected_namespaces=())

    step_number: int
    state: AgentState
    action_type: Optional[str] = None
    action_payload: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    thought: Optional[str] = None


class AgentOrchestrator(ABC):
    """
    Abstract interface for multi-step agentic execution.
    Decomposes workflows into explicit state machine loops.
    """

    @abstractmethod
    async def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[AgentStepEvent]:
        """Execute a task and yield observable intermediate steps for UI rendering."""
        pass


# ── Exception Hierarchy ───────────────────────────────────────────────────────

class AgentStateError(Exception):
    """Base exception for all Agent State Machine errors."""
    pass


class InvalidStateTransitionError(AgentStateError):
    """Raised when an illegal or out-of-order state transition is attempted."""
    pass


class PlanningError(AgentStateError):
    """Raised on plan generation failures or safety bounds violations."""
    pass


class ToolExecutionError(AgentStateError):
    """Raised on tool failure during EXECUTE state."""
    pass


class AgentTimeoutError(AgentStateError):
    """Raised when step or global wall-clock execution timeout is exceeded."""
    pass


class ValidationFailedError(AgentStateError):
    """Raised when validation checks fail during VALIDATE state."""
    pass


class MaxStepsExceededError(AgentStateError):
    """Raised when total executed steps exceed configured agent_max_steps limit."""
    pass


class MaxRetriesExceededError(AgentStateError):
    """Raised when a specific step exceeds configured agent_max_retries limit."""
    pass
