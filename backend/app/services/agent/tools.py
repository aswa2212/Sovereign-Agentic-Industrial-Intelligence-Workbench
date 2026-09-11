"""
SIH26117 — Agent Tool Abstraction & Core Adapters
Defines the tool interface decoupling agent execution from underlying subsystem implementations.
Integrates with Phase 6 SovereignRetriever and Phase 5 VisionEngine without direct model selection.
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional

try:
    from app.services.agent.base import ToolExecutionError
    from app.services.agent.models import AgentContext
    from app.services.rag.retriever import SovereignRetriever
except ImportError:
    from backend.app.services.agent.base import ToolExecutionError
    from backend.app.services.agent.models import AgentContext
    from backend.app.services.rag.retriever import SovereignRetriever

logger = logging.getLogger(__name__)


class AgentTool(ABC):
    """Abstract interface for all capabilities executable by the agent."""

    name: str
    capability: str
    description: str

    @abstractmethod
    async def execute(self, input_payload: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Execute tool action and return structured output dictionary."""
        ...


class RAGRetrievalTool(AgentTool):
    """Tool wrapping Phase 6 SovereignRetriever for standard and SOP clause search."""

    name = "rag_retrieval"
    capability = "rag_retrieval"
    description = "Searches indexed MRPL SOPs and engineering standards with citation provenance."

    def __init__(self, retriever: Optional[SovereignRetriever] = None) -> None:
        self.retriever = retriever or SovereignRetriever()

    async def execute(self, input_payload: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        query = input_payload.get("query") or context.user_request
        top_k = input_payload.get("top_k", 3)
        threshold = input_payload.get("similarity_threshold", 0.65)

        try:
            chunks, citations = await self.retriever.retrieve_with_citations(
                query=query,
                top_k=top_k,
                threshold=threshold,
            )
            # Retain in context
            context.retrieved_context.extend(chunks)

            return {
                "query": query,
                "retrieved_count": len(chunks),
                "chunks": [c.model_dump() for c in chunks],
                "citations": [cit.model_dump() for cit in citations],
                "summary": chunks[0].text[:200] if chunks else "No relevant knowledge found.",
            }
        except Exception as e:
            logger.error("RAGRetrievalTool execution error: %s", str(e))
            raise ToolExecutionError(f"RAG retrieval failed: {str(e)}") from e


class MockCalculationTool(AgentTool):
    """
    Deterministic calculation tool for industrial formulas (e.g. wall thickness, corrosion rate).
    Does NOT execute unsandboxed shell or arbitrary Python subprocesses.
    """

    name = "calculation"
    capability = "calculation"
    description = "Computes deterministic refinery corrosion rates and equipment remaining life."

    async def execute(self, input_payload: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        calc_type = input_payload.get("calc_type", "remaining_life")
        t_actual = float(input_payload.get("t_actual", 10.5))
        t_retired = float(input_payload.get("t_retired", 3.2))
        corrosion_rate = float(input_payload.get("corrosion_rate", 0.25))

        if corrosion_rate <= 0:
            raise ToolExecutionError("Corrosion rate must be positive for remaining life estimation.")

        remaining_thickness = round(t_actual - t_retired, 3)
        remaining_years = round(remaining_thickness / corrosion_rate, 2)

        return {
            "calculation_type": calc_type,
            "nominal_or_actual_mm": t_actual,
            "retired_limit_mm": t_retired,
            "corrosion_allowance_remaining_mm": remaining_thickness,
            "corrosion_rate_mm_per_year": corrosion_rate,
            "remaining_life_years": remaining_years,
            "formula_applied": "(t_actual - t_retired) / corrosion_rate",
        }


class SandboxedCalculationTool(AgentTool):
    """
    Sandboxed calculation tool wrapping SubprocessSandboxExecutor.
    Enforces process isolation, policy restrictions, and fail-closed validation.
    """

    name = "sandboxed_calculation"
    capability = "calculation"
    description = "Executes deterministic engineering calculations inside a constrained sandbox."

    def __init__(self, executor: Optional[Any] = None) -> None:
        if executor is None:
            try:
                from app.services.sandbox.subprocess_executor import SubprocessSandboxExecutor
            except ImportError:
                from backend.app.services.sandbox.subprocess_executor import SubprocessSandboxExecutor
            self.executor = SubprocessSandboxExecutor()
        else:
            self.executor = executor

    async def execute(self, input_payload: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        try:
            from app.services.sandbox.base import ExecutionStatus, ToolExecutionRequest
        except ImportError:
            from backend.app.services.sandbox.base import ExecutionStatus, ToolExecutionRequest

        tool_name = input_payload.get("tool_name", "minimum_wall_thickness_check")
        if "input" in input_payload and isinstance(input_payload["input"], dict):
            tool_input = input_payload["input"]
        else:
            tool_input = {k: v for k, v in input_payload.items() if k not in ("tool_name", "execution_mode")}

        req = ToolExecutionRequest(
            tool_name=tool_name,
            input=tool_input,
            execution_mode=input_payload.get("execution_mode", "subprocess"),
        )
        res = await self.executor.execute_tool(req)
        if res.status != ExecutionStatus.SUCCESS:
            raise ToolExecutionError(
                f"Sandboxed tool '{tool_name}' failed with status {res.status.value}: {res.error_message}"
            )
        return res.structured_result or {}


class ToolRegistry:
    """Registry maintaining active agent tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, AgentTool] = {}
        # Register core standard tools
        self.register(RAGRetrievalTool())
        self.register(MockCalculationTool())

    def register(self, tool: AgentTool) -> None:
        self._tools[tool.name] = tool
        # Also map by capability if distinct
        self._tools[tool.capability] = tool

    def get_tool(self, name_or_capability: str) -> Optional[AgentTool]:
        return self._tools.get(name_or_capability)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())
