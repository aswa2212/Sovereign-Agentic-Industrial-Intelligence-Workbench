"""
SIH26117 — Phase 5 Agent Validator Grounding Suite
Verifies the five semantic distinctions for retrieval grounding:
1. RAG tool exception -> validation fails (retrieval_tool_execution_failed).
2. RAG tool successful + zero retrieved chunks -> validation succeeds with
   explicit insufficient knowledge (retrieval_completed_insufficient_knowledge),
   without fabricating grounding citations.
3. RAG tool successful + one or more retrieved chunks -> validation succeeds with
   grounding_citations_present.
4. RAG not planned -> validation succeeds with retrieval_not_planned.
5. RAG planned but tool never executed -> validation fails (planned_retrieval_step_not_executed).
"""

import pytest
from app.services.agent.models import (
    AgentContext,
    Plan,
    PlanStep,
    StepObservation,
)
from app.services.agent.validator import Validator
from app.services.rag.base import RetrievedChunk


@pytest.mark.anyio
async def test_case_1_rag_tool_exception_fails_validation():
    """Case 1: RAG tool execution raised an exception / failed."""
    validator = Validator()
    step = PlanStep(id="s1", description="s1", capability="rag_retrieval", tool_name="rag_retrieval", status="failed")
    plan = Plan(plan_id="p1", task_id="t1", goal="Search SOP", steps=[step])
    ctx = AgentContext(
        task_id="t1",
        user_request="Search SOP",
        plan=plan,
        observations=[
            StepObservation(
                step_id="s1",
                tool_name="rag_retrieval",
                capability="rag_retrieval",
                success=False,
                error="Ollama connection refused",
            )
        ],
        retrieved_context=[],
    )

    res = await validator.validate(ctx)
    assert res.is_valid is False
    assert "retrieval_tool_execution_failed" in res.checks_failed
    assert "missing_required_retrieval_grounding" in res.checks_failed


@pytest.mark.anyio
async def test_case_2_rag_tool_successful_zero_chunks_insufficient_knowledge():
    """Case 2: RAG tool executed successfully but returned zero relevant chunks (insufficient knowledge)."""
    validator = Validator()
    step = PlanStep(id="s1", description="s1", capability="rag_retrieval", tool_name="rag_retrieval", status="completed")
    plan = Plan(plan_id="p1", task_id="t1", goal="Search SOP", steps=[step])
    ctx = AgentContext(
        task_id="t1",
        user_request="Search SOP",
        plan=plan,
        observations=[
            StepObservation(
                step_id="s1",
                tool_name="rag_retrieval",
                capability="rag_retrieval",
                success=True,
                output={
                    "query": "Search SOP",
                    "retrieved_count": 0,
                    "chunks": [],
                    "citations": [],
                    "summary": "No relevant knowledge found.",
                },
            )
        ],
        retrieved_context=[],  # Zero chunks retrieved
    )

    res = await validator.validate(ctx)
    # Must NOT fail execution
    assert res.is_valid is True
    # Must explicitly record insufficient knowledge
    assert "retrieval_completed_insufficient_knowledge" in res.checks_passed
    # Must NOT claim grounding citations are present
    assert "grounding_citations_present" not in res.checks_passed


@pytest.mark.anyio
async def test_case_3_rag_tool_successful_with_chunks_grounded():
    """Case 3: RAG tool executed successfully and returned one or more relevant chunks."""
    validator = Validator()
    step = PlanStep(id="s1", description="s1", capability="rag_retrieval", tool_name="rag_retrieval", status="completed")
    plan = Plan(plan_id="p1", task_id="t1", goal="Search SOP", steps=[step])
    sample_chunk = RetrievedChunk(
        chunk_id="chk_001",
        document_id="doc_1",
        source_sha256="sha123",
        source_document="SOP-001.pdf",
        page_number=1,
        text="Minimum thickness is 8.0 mm.",
        similarity_score=0.88,
        content_sha256="csha123",
        token_count=15,
    )
    ctx = AgentContext(
        task_id="t1",
        user_request="Search SOP",
        plan=plan,
        observations=[
            StepObservation(
                step_id="s1",
                tool_name="rag_retrieval",
                capability="rag_retrieval",
                success=True,
                output={"retrieved_count": 1},
            )
        ],
        retrieved_context=[sample_chunk],
    )

    res = await validator.validate(ctx)
    assert res.is_valid is True
    assert "grounding_citations_present" in res.checks_passed
    assert "retrieval_completed_insufficient_knowledge" not in res.checks_passed


@pytest.mark.anyio
async def test_case_4_rag_not_planned():
    """Case 4: RAG retrieval was not planned."""
    validator = Validator()
    step = PlanStep(id="s1", description="Calculate", capability="calculation", tool_name="calculation", status="completed")
    plan = Plan(plan_id="p1", task_id="t1", goal="Calculate only", steps=[step])
    ctx = AgentContext(
        task_id="t1",
        user_request="Calculate only",
        plan=plan,
        observations=[
            StepObservation(
                step_id="s1",
                tool_name="calculation",
                capability="calculation",
                success=True,
                output={"rate": 0.35},
            )
        ],
        retrieved_context=[],
    )

    res = await validator.validate(ctx)
    assert res.is_valid is True
    assert "retrieval_not_planned" in res.checks_passed
    assert "missing_required_retrieval_grounding" not in res.checks_failed


@pytest.mark.anyio
async def test_case_5_rag_planned_never_executed_fails_validation():
    """Case 5: RAG was planned but the tool step was never executed."""
    validator = Validator()
    step = PlanStep(id="s1", description="Search SOP", capability="rag_retrieval", tool_name="rag_retrieval", status="pending")
    plan = Plan(plan_id="p1", task_id="t1", goal="Search SOP", steps=[step])
    ctx = AgentContext(
        task_id="t1",
        user_request="Search SOP",
        plan=plan,
        observations=[],  # No observations recorded
        retrieved_context=[],
    )

    res = await validator.validate(ctx)
    assert res.is_valid is False
    assert "planned_retrieval_step_not_executed" in res.checks_failed
    assert "missing_required_retrieval_grounding" in res.checks_failed
