"""
SIH26117 — Agent Domain Models and Execution Context
Defines strongly-typed representations for Plan, PlanStep, StepObservation,
StepReflection, ValidationResult, and the central AgentContext.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

try:
    from app.services.router.decision import RoutingDecision
    from app.services.agent.base import AgentEvent, AgentState
    from app.services.rag.base import CitationSource, RetrievedChunk
except ImportError:
    from backend.app.services.router.decision import RoutingDecision
    from backend.app.services.agent.base import AgentEvent, AgentState
    from backend.app.services.rag.base import CitationSource, RetrievedChunk


def utc_now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


class PlanStep(BaseModel):
    """A discrete, structured operational step within an agent plan."""

    model_config = ConfigDict(protected_namespaces=())

    id: str = Field(..., description="Step identifier (e.g. 'step_1')")
    description: str = Field(..., description="Human-readable goal of this step")
    capability: str = Field(..., description="Required capability (e.g. 'rag_retrieval', 'vision_analysis')")
    tool_name: str = Field(..., description="Target tool name to invoke")
    status: str = Field(default="pending", description="'pending', 'in_progress', 'completed', 'failed', 'skipped'")
    input_payload: Dict[str, Any] = Field(default_factory=dict, description="Structured parameters for the tool")
    output_payload: Optional[Dict[str, Any]] = Field(default=None, description="Output returned by the tool")
    retry_count: int = Field(default=0, description="Number of times this step has been retried")


class Plan(BaseModel):
    """Structured plan composed of ordered discrete steps."""

    model_config = ConfigDict(protected_namespaces=())

    plan_id: str = Field(..., description="Unique plan identifier")
    task_id: str = Field(..., description="Associated agent task ID")
    goal: str = Field(..., description="High-level decomposed task objective")
    steps: List[PlanStep] = Field(default_factory=list, description="Ordered execution steps")
    created_at: str = Field(default_factory=utc_now_iso)


class StepObservation(BaseModel):
    """Empirical output recorded immediately after executing a step."""

    model_config = ConfigDict(protected_namespaces=())

    step_id: str = Field(..., description="ID of step that was executed")
    tool_name: str = Field(..., description="Tool that executed")
    capability: str = Field(..., description="Capability invoked")
    success: bool = Field(..., description="Whether execution succeeded without uncaught errors")
    output: Any = Field(default=None, description="Raw or structured tool output")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary timing and environment data")
    timestamp: str = Field(default_factory=utc_now_iso)


class StepReflection(BaseModel):
    """Assessment of the last executed step and directive for next action."""

    model_config = ConfigDict(protected_namespaces=())

    step_id: str = Field(..., description="Evaluated step identifier")
    decision: str = Field(..., description="'CONTINUE', 'RETRY', 'FAIL', 'COMPLETE'")
    reason: str = Field(..., description="Explanation of why this decision was reached")
    suggested_action: Optional[str] = Field(default=None, description="Next suggested operational tweak")
    retry_suggested: bool = Field(default=False, description="Whether the step should immediately retry")


class ValidationResult(BaseModel):
    """Outcome of rigorous post-execution deterministic validation checks."""

    model_config = ConfigDict(protected_namespaces=())

    is_valid: bool = Field(..., description="Whether all validation rules passed")
    checks_passed: List[str] = Field(default_factory=list, description="Names of passed validation assertions")
    checks_failed: List[str] = Field(default_factory=list, description="Names of failed validation assertions")
    confidence: float = Field(default=1.0, description="Overall validation confidence score (0.0 to 1.0)")
    notes: Optional[str] = Field(default=None, description="Explanatory notes on validation status")


class AgentContext(BaseModel):
    """
    Central state container tracking execution history, intermediate results,
    routing decisions, and citations across all state transitions.
    """

    model_config = ConfigDict(protected_namespaces=())

    task_id: str = Field(..., description="Unique task identifier UUID")
    user_request: str = Field(..., description="Original user prompt or command")
    current_state: AgentState = Field(default=AgentState.IDLE, description="Current lifecycle state")
    routing_decision: Optional[RoutingDecision] = Field(default=None, description="Phase 3 Task Router decision")
    plan: Optional[Plan] = Field(default=None, description="Generated plan")
    current_step_index: int = Field(default=0, description="Index of the currently executing plan step")
    observations: List[StepObservation] = Field(default_factory=list, description="Cumulative step observations")
    reflection: Optional[StepReflection] = Field(default=None, description="Latest step reflection")
    validation_result: Optional[ValidationResult] = Field(default=None, description="Outcome of VALIDATE phase")
    retrieved_context: List[RetrievedChunk] = Field(default_factory=list, description="Knowledge retrieved from RAG")
    tool_results: Dict[str, Any] = Field(default_factory=dict, description="Mapped tool outputs by step_id")
    final_result: Optional[Dict[str, Any]] = Field(default=None, description="Final deliverable payload")
    evidence: Optional[Dict[str, Any]] = Field(default=None, description="Structured engineering evidence provided to agent")
    errors: List[str] = Field(default_factory=list, description="Cumulative non-fatal or fatal error messages")
    step_count: int = Field(default=0, description="Total executed steps across life of task")
    retry_count: int = Field(default=0, description="Total retries invoked")
    started_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    execution_trace: List[AgentEvent] = Field(default_factory=list, description="Chronological trace of state events")

    def get_citations(self) -> List[CitationSource]:
        """Extract structured citations from retrieved chunks."""
        return [chunk.to_citation() for chunk in self.retrieved_context]
