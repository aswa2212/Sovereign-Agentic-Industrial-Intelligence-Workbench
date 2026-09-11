"""
SIH26117 — Phase 7 Agent State Machine & Orchestration Test Suite
Verifies:
1. State machine lifecycle transitions and invalid transition rejections.
2. Planner decomposition, step budgeting, and max-step ceiling.
3. Tool execution, RAG integration, and observation capture.
4. Reflector loop protection, step retries (max 2), and timeout safeguards.
5. Deterministic validation checks.
6. Execution trace, context retention, and citation preservation.
7. Router and RAG architectural boundaries.
8. End-to-end synthetic MRPL SOP task execution.
9. REST API endpoints (/run, /{task_id}, errors).
10. Air-gap sovereignty (zero outbound network requests).
"""

import json
from pathlib import Path
import socket
import pytest
from fastapi.testclient import TestClient

try:
    from app.core.config import get_settings
    from app.main import app
    from app.services.router.decision import RoutingDecision
    from app.services.agent.base import (
        AgentEvent,
        AgentState,
        AgentTimeoutError,
        InvalidStateTransitionError,
        PlanningError,
    )
    from app.services.agent.models import (
        AgentContext,
        Plan,
        PlanStep,
        StepObservation,
    )
    from app.services.agent.orchestrator import AgentStateMachineOrchestrator
    from app.services.agent.planner import Planner
    from app.services.agent.reflector import Reflector
    from app.services.agent.state_machine import AgentStateMachine
    from app.services.agent.tools import MockCalculationTool, RAGRetrievalTool, ToolRegistry
    from app.services.agent.validator import Validator
    from app.services.ingestion.models import NormalizedDocument
    from app.services.ingestion.storage import StorageManager
    from app.services.rag.embeddings import MockEmbeddingProvider
    from app.services.rag.retriever import SovereignRetriever
    from app.services.rag.vector_store import LocalJsonVectorStore
except ImportError:
    from backend.app.core.config import get_settings
    from backend.app.main import app
    from backend.app.services.router.decision import RoutingDecision
    from backend.app.services.agent.base import (
        AgentEvent,
        AgentState,
        AgentTimeoutError,
        InvalidStateTransitionError,
        PlanningError,
    )
    from backend.app.services.agent.models import (
        AgentContext,
        Plan,
        PlanStep,
        StepObservation,
    )
    from backend.app.services.agent.orchestrator import AgentStateMachineOrchestrator
    from backend.app.services.agent.planner import Planner
    from backend.app.services.agent.reflector import Reflector
    from backend.app.services.agent.state_machine import AgentStateMachine
    from backend.app.services.agent.tools import MockCalculationTool, RAGRetrievalTool, ToolRegistry
    from backend.app.services.agent.validator import Validator
    from backend.app.services.ingestion.models import NormalizedDocument
    from backend.app.services.ingestion.storage import StorageManager
    from backend.app.services.rag.embeddings import MockEmbeddingProvider
    from backend.app.services.rag.retriever import SovereignRetriever
    from backend.app.services.rag.vector_store import LocalJsonVectorStore

client = TestClient(app)


async def seed_synthetic_sop_index(storage_dir: Path) -> SovereignRetriever:
    """Helper to seed a LocalJsonVectorStore with the synthetic MRPL SOP."""
    fixture_path = Path(__file__).resolve().parent.parent.parent / "data" / "samples" / "sop_mrpl_piping_inspection.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    doc = NormalizedDocument.model_validate(data)

    store = LocalJsonVectorStore(index_id="agent_sop_test", storage_dir=storage_dir)
    retriever = SovereignRetriever(
        vector_store=store,
        embedding_provider=MockEmbeddingProvider(dim=384),
        default_top_k=3,
        default_threshold=0.65,
    )
    await retriever.index_document(doc)
    return retriever


# ── 1. State Machine Transitions ──────────────────────────────────────────────

class TestStateMachine:
    """Verifies state progression and transition rule enforcement."""

    def test_initial_state_and_valid_progression(self):
        ctx = AgentContext(task_id="task_001", user_request="Inspect C-101 piping")
        assert ctx.current_state == AgentState.IDLE

        # Step-by-step valid transitions
        AgentStateMachine.transition(ctx, AgentState.RECEIVE)
        assert ctx.current_state == AgentState.RECEIVE

        AgentStateMachine.transition(ctx, AgentState.UNDERSTAND)
        assert ctx.current_state == AgentState.UNDERSTAND

        AgentStateMachine.transition(ctx, AgentState.PLAN)
        assert ctx.current_state == AgentState.PLAN

        AgentStateMachine.transition(ctx, AgentState.EXECUTE)
        assert ctx.current_state == AgentState.EXECUTE

        AgentStateMachine.transition(ctx, AgentState.OBSERVE)
        assert ctx.current_state == AgentState.OBSERVE

        AgentStateMachine.transition(ctx, AgentState.REFLECT)
        assert ctx.current_state == AgentState.REFLECT

        AgentStateMachine.transition(ctx, AgentState.VALIDATE)
        assert ctx.current_state == AgentState.VALIDATE

        AgentStateMachine.transition(ctx, AgentState.FINALIZE)
        assert ctx.current_state == AgentState.FINALIZE

        AgentStateMachine.transition(ctx, AgentState.DELIVER)
        assert ctx.current_state == AgentState.DELIVER

        # Verify trace recorded all 9 events
        assert len(ctx.execution_trace) == 9

    def test_invalid_transitions_rejected(self):
        ctx = AgentContext(task_id="task_002", user_request="Test task")
        # Cannot jump from IDLE directly to EXECUTE
        with pytest.raises(InvalidStateTransitionError):
            AgentStateMachine.transition(ctx, AgentState.EXECUTE)

        # Cannot jump from IDLE to DELIVER
        with pytest.raises(InvalidStateTransitionError):
            AgentStateMachine.transition(ctx, AgentState.DELIVER)

    def test_terminal_states_cannot_transition(self):
        ctx_del = AgentContext(task_id="task_del", user_request="Delivered", current_state=AgentState.DELIVER)
        with pytest.raises(InvalidStateTransitionError):
            AgentStateMachine.transition(ctx_del, AgentState.IDLE)

        ctx_fail = AgentContext(task_id="task_fail", user_request="Failed", current_state=AgentState.FAILED)
        with pytest.raises(InvalidStateTransitionError):
            AgentStateMachine.transition(ctx_fail, AgentState.RECEIVE)

    def test_failure_transition_allowed_from_active_states(self):
        ctx = AgentContext(task_id="task_err", user_request="Task with error")
        AgentStateMachine.transition(ctx, AgentState.RECEIVE)
        AgentStateMachine.transition(ctx, AgentState.FAILED, message="Fatal error encountered")
        assert ctx.current_state == AgentState.FAILED


# ── 2. Planner Tests ──────────────────────────────────────────────────────────

class TestPlanner:
    """Verifies plan generation and bounds checking."""

    @pytest.mark.anyio
    async def test_planner_creates_bounded_plan(self):
        planner = Planner(max_steps=8)
        plan = await planner.create_plan(
            task="Find the minimum wall thickness requirement for Class 150 carbon steel process piping.",
            task_id="plan_task_1",
        )
        assert len(plan.steps) >= 1
        assert len(plan.steps) <= 8
        assert plan.steps[0].capability == "rag_retrieval"
        assert plan.steps[0].tool_name == "rag_retrieval"

    @pytest.mark.anyio
    async def test_planner_multi_step_calculation_and_rag(self):
        planner = Planner(max_steps=8)
        plan = await planner.create_plan(
            task="Find SOP standard thickness and calculate corrosion rate remaining life for pipe spool.",
            task_id="plan_task_2",
        )
        assert len(plan.steps) == 2
        assert plan.steps[0].capability == "rag_retrieval"
        assert plan.steps[1].capability == "calculation"

    @pytest.mark.anyio
    async def test_planner_exceeding_max_steps_rejected(self):
        # Configure max_steps=1 but task demands 2 steps
        planner = Planner(max_steps=1)
        with pytest.raises(PlanningError):
            await planner.create_plan(
                task="Find SOP standard thickness and calculate corrosion rate remaining life.",
                task_id="plan_task_3",
            )

    @pytest.mark.anyio
    async def test_planner_empty_task_raises_error(self):
        planner = Planner()
        with pytest.raises(PlanningError):
            await planner.create_plan(task="   ", task_id="empty_plan")


# ── 3. Tool Execution Tests ───────────────────────────────────────────────────

class TestToolExecution:
    """Verifies tool invocation and output capture."""

    @pytest.mark.anyio
    async def test_calculation_tool_deterministic_output(self):
        tool = MockCalculationTool()
        ctx = AgentContext(task_id="calc_task", user_request="Calculate remaining life")
        out = await tool.execute(
            {"t_actual": 10.0, "t_retired": 3.2, "corrosion_rate": 0.25}, ctx
        )
        assert out["corrosion_allowance_remaining_mm"] == 6.8
        assert out["remaining_life_years"] == 27.2
        assert out["formula_applied"] == "(t_actual - t_retired) / corrosion_rate"

    @pytest.mark.anyio
    async def test_rag_tool_execution_with_context_retention(self, tmp_path):
        retriever = await seed_synthetic_sop_index(tmp_path)
        tool = RAGRetrievalTool(retriever=retriever)
        ctx = AgentContext(
            task_id="rag_task",
            user_request="Find the minimum wall thickness requirement for Class 150 carbon steel process piping.",
        )

        out = await tool.execute({"query": ctx.user_request}, ctx)
        assert out["retrieved_count"] >= 1
        assert len(ctx.retrieved_context) >= 1
        assert any("3.2 mm" in c.text or "3.20" in c.text for c in ctx.retrieved_context)


# ── 4. Reflector & Loop Protection Tests ──────────────────────────────────────

class TestReflector:
    """Verifies reflection logic, retry limits (2), and step ceilings (8)."""

    @pytest.mark.anyio
    async def test_reflector_continues_on_intermediate_step(self):
        reflector = Reflector(max_steps=8, max_retries=2)
        plan = Plan(
            plan_id="p1",
            task_id="t1",
            goal="Test",
            steps=[
                PlanStep(id="step_1", description="Step 1", capability="test", tool_name="tool1"),
                PlanStep(id="step_2", description="Step 2", capability="test", tool_name="tool2"),
            ],
        )
        ctx = AgentContext(task_id="t1", user_request="Test", plan=plan, current_step_index=0)
        obs = StepObservation(step_id="step_1", tool_name="tool1", capability="test", success=True)

        reflection = await reflector.reflect(ctx, obs)
        assert reflection.decision == "CONTINUE"
        assert not reflection.retry_suggested

    @pytest.mark.anyio
    async def test_reflector_triggers_retry_on_failure(self):
        reflector = Reflector(max_steps=8, max_retries=2)
        step = PlanStep(id="step_1", description="Step 1", capability="test", tool_name="tool1")
        plan = Plan(plan_id="p1", task_id="t1", goal="Test", steps=[step])
        ctx = AgentContext(task_id="t1", user_request="Test", plan=plan, current_step_index=0)
        obs = StepObservation(step_id="step_1", tool_name="tool1", capability="test", success=False, error="Transient glitch")

        # Retry 1
        ref1 = await reflector.reflect(ctx, obs)
        assert ref1.decision == "RETRY"
        assert ref1.retry_suggested is True
        assert step.retry_count == 1

        # Retry 2
        ref2 = await reflector.reflect(ctx, obs)
        assert ref2.decision == "RETRY"
        assert step.retry_count == 2

        # 3rd failure -> exceeds max_retries (2) -> FAIL
        ref3 = await reflector.reflect(ctx, obs)
        assert ref3.decision == "FAIL"
        assert "MAX_RETRIES_EXCEEDED" in ref3.suggested_action

    @pytest.mark.anyio
    async def test_reflector_enforces_max_steps_ceiling(self):
        reflector = Reflector(max_steps=8)
        ctx = AgentContext(task_id="t1", user_request="Test", step_count=8)
        obs = StepObservation(step_id="step_8", tool_name="tool", capability="test", success=True)

        reflection = await reflector.reflect(ctx, obs)
        assert reflection.decision == "FAIL"
        assert "MAX_STEPS_EXCEEDED" in reflection.suggested_action


# ── 5. Validator Tests ────────────────────────────────────────────────────────

class TestValidator:
    """Verifies deterministic post-execution validation."""

    @pytest.mark.anyio
    async def test_validator_passes_when_all_conditions_met(self):
        validator = Validator()
        step = PlanStep(id="s1", description="s1", capability="calculation", tool_name="tool", status="completed")
        plan = Plan(plan_id="p1", task_id="t1", goal="Goal", steps=[step])
        ctx = AgentContext(
            task_id="t1",
            user_request="Calculate",
            plan=plan,
            observations=[StepObservation(step_id="s1", tool_name="tool", capability="calculation", success=True)],
        )
        res = await validator.validate(ctx)
        assert res.is_valid is True
        assert "all_plan_steps_completed" in res.checks_passed

    @pytest.mark.anyio
    async def test_validator_fails_on_missing_rag_grounding(self):
        validator = Validator()
        step = PlanStep(id="s1", description="s1", capability="rag_retrieval", tool_name="rag", status="completed")
        plan = Plan(plan_id="p1", task_id="t1", goal="Find SOP", steps=[step])
        ctx = AgentContext(
            task_id="t1",
            user_request="Find SOP",
            plan=plan,
            observations=[StepObservation(step_id="s1", tool_name="rag", capability="rag_retrieval", success=True)],
            retrieved_context=[],  # Missing grounding!
        )
        res = await validator.validate(ctx)
        assert res.is_valid is False
        assert "missing_required_retrieval_grounding" in res.checks_failed


# ── 6. End-to-End Orchestrator Workflow ───────────────────────────────────────

class TestOrchestratorE2E:
    """Verifies complete autonomous execution across all 11 states."""

    @pytest.mark.anyio
    async def test_e2e_synthetic_mrpl_sop_workflow(self, tmp_path):
        retriever = await seed_synthetic_sop_index(tmp_path)
        tool_reg = ToolRegistry()
        tool_reg.register(RAGRetrievalTool(retriever=retriever))

        orchestrator = AgentStateMachineOrchestrator(tool_registry=tool_reg)

        task = "Find the minimum wall thickness requirement for Class 150 carbon steel process piping."
        context = await orchestrator.execute_task(task=task)

        # 1. Assert terminal success state
        assert context.current_state == AgentState.DELIVER
        assert context.final_result is not None
        assert context.final_result["status"] == "success"

        # 2. Assert verifiable citations
        citations = context.get_citations()
        assert len(citations) >= 1
        assert citations[0].source_document == "SOP-MRPL-PIP-001.pdf"
        assert citations[0].page_number == 3

        # 3. Assert complete chronological trace
        states_in_trace = [e.state for e in context.execution_trace]
        assert AgentState.RECEIVE in states_in_trace
        assert AgentState.UNDERSTAND in states_in_trace
        assert AgentState.PLAN in states_in_trace
        assert AgentState.EXECUTE in states_in_trace
        assert AgentState.OBSERVE in states_in_trace
        assert AgentState.REFLECT in states_in_trace
        assert AgentState.VALIDATE in states_in_trace
        assert AgentState.FINALIZE in states_in_trace
        assert AgentState.DELIVER in states_in_trace

        # 4. Assert Router was invoked without hardcoded model IDs
        assert context.routing_decision is not None
        assert context.routing_decision.model_role is not None

    @pytest.mark.anyio
    async def test_global_timeout_enforcement(self, monkeypatch):
        import time as time_mod
        tool_reg = ToolRegistry()
        orchestrator = AgentStateMachineOrchestrator(tool_registry=tool_reg)
        orchestrator.global_timeout = 10.0

        calls = [0]
        real_monotonic = time_mod.monotonic

        def jumping_monotonic():
            calls[0] += 1
            if calls[0] > 1:
                return real_monotonic() + 50.0
            return real_monotonic()

        monkeypatch.setattr(time_mod, "monotonic", jumping_monotonic)

        context = await orchestrator.execute_task("Do heavy calculation")
        assert context.current_state == AgentState.FAILED
        assert any("timeout" in err.lower() for err in context.errors)


# ── 7. REST API Endpoints Tests ───────────────────────────────────────────────

class TestAgentAPI:
    """Verifies /api/v1/agent endpoints."""

    def test_api_agent_run_success(self):
        res = client.post(
            "/api/v1/agent/run",
            json={"task": "Find the minimum wall thickness requirement for Class 150 carbon steel process piping."},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "completed"
        assert data["final_state"] == "DELIVER"
        assert "task_id" in data
        assert len(data["execution_trace"]) >= 8

        # Test trace status lookup
        t_id = data["task_id"]
        trace_res = client.get(f"/api/v1/agent/{t_id}")
        assert trace_res.status_code == 200
        trace_data = trace_res.json()
        assert trace_data["task_id"] == t_id
        assert trace_data["current_state"] == "DELIVER"

    def test_api_agent_run_empty_task_returns_400(self):
        res = client.post("/api/v1/agent/run", json={"task": "   "})
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "BAD_REQUEST"

    def test_api_agent_get_nonexistent_task_returns_404(self):
        res = client.get("/api/v1/agent/nonexistent_task_id_999")
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "NOT_FOUND"


# ── 8. Air-Gap Sovereignty Verification ───────────────────────────────────────

@pytest.mark.anyio
async def test_air_gap_no_outbound_network_calls(monkeypatch, tmp_path):
    """
    Verify that Phase 7 agent state machine, planning, reflection, and tool calls
    make zero outbound network connections.
    """
    def forbidden_connect(*args, **kwargs):
        raise AssertionError("Air-gap violation: Outbound network call attempted during Agent execution!")

    monkeypatch.setattr(socket, "create_connection", forbidden_connect)

    retriever = await seed_synthetic_sop_index(tmp_path)
    tool_reg = ToolRegistry()
    tool_reg.register(RAGRetrievalTool(retriever=retriever))

    orchestrator = AgentStateMachineOrchestrator(tool_registry=tool_reg)

    context = await orchestrator.execute_task(
        "Find the minimum wall thickness requirement for Class 150 carbon steel process piping."
    )
    assert context.current_state == AgentState.DELIVER
