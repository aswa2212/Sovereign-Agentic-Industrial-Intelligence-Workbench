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
    Upholds Frozen Contract 1: EngineeringEvidence is authoritative for physical measurements.
    """

    name = "calculation"
    capability = "calculation"
    description = "Computes deterministic refinery corrosion rates and equipment remaining life."

    async def execute(self, input_payload: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        calc_type = input_payload.get("calc_type", "remaining_life")

        t_actual = None
        t_retired = None
        corrosion_rate = None
        evidence_authoritative = False
        evidence_source = None
        evidence_sha256 = None

        # Frozen Contract 1: EngineeringEvidence remains authoritative for physical measurements
        if context.evidence:
            ev = context.evidence
            evidence_source = ev.get("source_filename")
            evidence_sha256 = ev.get("source_sha256")

            # Physical thickness measurement from authoritative evidence
            if ev.get("current_thickness_mm") is not None:
                t_actual = float(ev["current_thickness_mm"])
                evidence_authoritative = True
            elif ev.get("selected_measurement") and isinstance(ev["selected_measurement"], dict):
                sel = ev["selected_measurement"]
                if sel.get("thickness_mm") is not None:
                    t_actual = float(sel["thickness_mm"])
                    evidence_authoritative = True

            # Minimum required thickness from evidence if specified
            if ev.get("minimum_required_thickness_mm") is not None:
                t_retired = float(ev["minimum_required_thickness_mm"])

            # Corrosion rate from evidence if specified
            if ev.get("corrosion_rate_mm_per_year") is not None:
                corrosion_rate = float(ev["corrosion_rate_mm_per_year"])

        # If not populated from authoritative evidence, use input_payload or defaults
        if t_actual is None:
            t_actual = float(input_payload.get("t_actual", 10.5))

        if t_retired is None:
            t_retired = float(input_payload.get("t_retired", 3.2))

        if corrosion_rate is None:
            corrosion_rate = float(input_payload.get("corrosion_rate", 0.25))

        if corrosion_rate <= 0:
            raise ToolExecutionError("Corrosion rate must be positive for remaining life estimation.")

        remaining_thickness = round(t_actual - t_retired, 3)
        remaining_years = round(remaining_thickness / corrosion_rate, 2)

        res: Dict[str, Any] = {
            "calculation_type": calc_type,
            "nominal_or_actual_mm": t_actual,
            "retired_limit_mm": t_retired,
            "corrosion_allowance_remaining_mm": remaining_thickness,
            "corrosion_rate_mm_per_year": corrosion_rate,
            "remaining_life_years": remaining_years,
            "formula_applied": "(t_actual - t_retired) / corrosion_rate",
        }
        if evidence_authoritative:
            res["evidence_authoritative"] = True
            res["evidence_source"] = evidence_source
            res["evidence_sha256"] = evidence_sha256

        return res



class SandboxedCalculationTool(AgentTool):
    """
    Sandboxed calculation tool wrapping SubprocessSandboxExecutor.
    Enforces process isolation, policy restrictions, and fail-closed validation.
    Upholds Frozen Contract 1: EngineeringEvidence is authoritative for physical measurements.
    """

    name = "sandboxed_calculation"
    capability = "sandboxed_calculation"
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
            tool_input = dict(input_payload["input"])
        else:
            tool_input = {k: v for k, v in input_payload.items() if k not in ("tool_name", "execution_mode")}

        evidence_authoritative = False
        evidence_source = None
        evidence_sha256 = None
        field_provenance: Dict[str, str] = {}

        # Frozen Contract 1: EngineeringEvidence remains authoritative for physical measurements
        if context.evidence:
            ev = context.evidence.model_dump() if hasattr(context.evidence, "model_dump") else (
                dict(context.evidence) if isinstance(context.evidence, dict) else {}
            )
            evidence_source = ev.get("source_filename")
            evidence_sha256 = ev.get("source_sha256")

            # Resolve physical thickness measurement
            meas_thickness = None
            if ev.get("current_thickness_mm") is not None:
                meas_thickness = float(ev["current_thickness_mm"])
            elif ev.get("selected_measurement"):
                sel = ev["selected_measurement"]
                sel_dict = sel.model_dump() if hasattr(sel, "model_dump") else (sel if isinstance(sel, dict) else {})
                if sel_dict.get("thickness_mm") is not None:
                    meas_thickness = float(sel_dict["thickness_mm"])

            # 1. minimum_wall_thickness_check
            if tool_name == "minimum_wall_thickness_check":
                if meas_thickness is not None:
                    tool_input["measured_thickness_mm"] = meas_thickness
                    evidence_authoritative = True
                    field_provenance["measured_thickness_mm"] = ev.get("current_thickness_source", "ENGINEERING_EVIDENCE")

                if ev.get("minimum_required_thickness_mm") is not None:
                    tool_input["minimum_required_mm"] = float(ev["minimum_required_thickness_mm"])
                    evidence_authoritative = True
                    field_provenance["minimum_required_mm"] = ev.get("minimum_thickness_source", "ENGINEERING_EVIDENCE")

                if ev.get("equipment_id") and "component_id" not in tool_input:
                    tool_input["component_id"] = str(ev["equipment_id"])

            # 2. corrosion_rate_calc
            elif tool_name == "corrosion_rate_calc":
                if meas_thickness is not None:
                    tool_input["current_thickness_mm"] = meas_thickness
                    evidence_authoritative = True
                    field_provenance["current_thickness_mm"] = ev.get("current_thickness_source", "ENGINEERING_EVIDENCE")

                if ev.get("nominal_thickness_mm") is not None:
                    tool_input["previous_thickness_mm"] = float(ev["nominal_thickness_mm"])
                    evidence_authoritative = True
                    field_provenance["previous_thickness_mm"] = ev.get("nominal_thickness_source", "ENGINEERING_EVIDENCE")

                if ev.get("elapsed_time_years") is not None:
                    tool_input["elapsed_time_years"] = float(ev["elapsed_time_years"])
                    evidence_authoritative = True
                    field_provenance["elapsed_time_years"] = ev.get("elapsed_time_source", "ENGINEERING_EVIDENCE")

                if ev.get("minimum_required_thickness_mm") is not None:
                    tool_input["minimum_required_mm"] = float(ev["minimum_required_thickness_mm"])
                    evidence_authoritative = True
                    field_provenance["minimum_required_mm"] = ev.get("minimum_thickness_source", "ENGINEERING_EVIDENCE")

                if ev.get("equipment_id") and "component_id" not in tool_input:
                    tool_input["component_id"] = str(ev["equipment_id"])

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

        output = dict(res.structured_result or {})
        if evidence_authoritative:
            output["evidence_authoritative"] = True
            output["evidence_source"] = evidence_source
            output["evidence_sha256"] = evidence_sha256
            output["field_provenance"] = field_provenance

        return output


class ToolRegistry:
    """Registry maintaining active agent tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, AgentTool] = {}
        # Register core standard tools including Phase 8 SandboxedCalculationTool
        self.register(RAGRetrievalTool())
        self.register(MockCalculationTool())
        self.register(SandboxedCalculationTool())

    def register(self, tool: AgentTool) -> None:
        self._tools[tool.name] = tool
        # Also map by capability if distinct
        self._tools[tool.capability] = tool

    def get_tool(self, name_or_capability: str) -> Optional[AgentTool]:
        return self._tools.get(name_or_capability)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())
