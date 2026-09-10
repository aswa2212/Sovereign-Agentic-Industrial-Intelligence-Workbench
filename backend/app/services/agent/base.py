"""
SIH26117 — Agent Orchestrator Interface
Defines the boundary for multi-step agentic planning and state-machine execution.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional
from pydantic import BaseModel


class AgentState(str, Enum):
    """Core state-machine lifecycle states."""

    IDLE = "idle"
    PLANNING = "planning"
    ACTING = "acting"
    OBSERVING = "observing"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentStepEvent(BaseModel):
    """Observable intermediate event emitted by the agent."""

    step_number: int
    state: AgentState
    action_type: Optional[str] = None
    action_payload: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None
    thought: Optional[str] = None


class AgentOrchestrator(ABC):
    """
    Abstract interface for multi-step agentic execution.
    Decomposes workflows into plan -> act -> observe -> reflect loops.
    """

    @abstractmethod
    async def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[AgentStepEvent]:
        """Execute a task and yield observable intermediate steps for UI rendering."""
        pass
