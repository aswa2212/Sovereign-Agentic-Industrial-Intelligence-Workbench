"""
SIH26117 — Agent REST API Schemas
Public request/response DTOs for agent execution, trace inspection, and status reporting.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

try:
    from app.services.agent.base import AgentEvent, AgentState
    from app.services.rag.base import CitationSource
except ImportError:
    from backend.app.services.agent.base import AgentEvent, AgentState
    from backend.app.services.rag.base import CitationSource


class AgentRunRequest(BaseModel):
    """Payload for submitting a task to the autonomous agent state machine."""

    model_config = ConfigDict(protected_namespaces=())

    task: str = Field(
        ...,
        min_length=1,
        description="User engineering inquiry, calculation prompt, or inspection task",
        examples=["Find the minimum wall thickness requirement for Class 150 carbon steel process piping."],
    )
    max_steps: Optional[int] = Field(
        default=None,
        ge=1,
        le=8,
        description="Optional override for maximum plan steps ceiling (default 8)",
    )


class AgentRunResponse(BaseModel):
    """Execution outcome containing finalized result, citations, and observable trace."""

    model_config = ConfigDict(protected_namespaces=())

    task_id: str = Field(...)
    status: str = Field(..., description="'completed' or 'failed'")
    final_state: AgentState = Field(...)
    result: Optional[Dict[str, Any]] = Field(default=None)
    execution_trace: List[AgentEvent] = Field(default_factory=list)
    citations: List[CitationSource] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class AgentTaskStatusResponse(BaseModel):
    """Diagnostic state and execution trace for a previously submitted task."""

    model_config = ConfigDict(protected_namespaces=())

    task_id: str = Field(...)
    current_state: AgentState = Field(...)
    step_count: int = Field(...)
    started_at: str = Field(...)
    updated_at: str = Field(...)
    execution_trace: List[AgentEvent] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
