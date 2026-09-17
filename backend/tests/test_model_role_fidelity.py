"""
SIH26117 — Phase 2 Step 1: Router -> Model Manager Role Fidelity Regression Tests

Verifies:
A. ModelRole.CODER resolves to coder.
B. ModelRole.REASONING resolves to reasoning.
C. ModelRole.VISION resolves to vision.
D. A missing configured role fails explicitly.
E. Missing role never silently resolves to reasoning.
F. Existing Router tests remain unchanged/passing.
G. Existing Phase 1 provenance behavior remains unchanged.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.integration.exceptions import ModelAllocationError
from app.services.integration.models import (
    CorrosionAuditWorkflowRequest,
    WorkflowExecutionMode,
    WorkflowStatus,
)
from app.services.integration.workflow import CorrosionAuditWorkflow
from app.services.model_manager.config_loader import ModelEntry, TierConfig
from app.services.model_manager.manager import ModelManager
from app.services.model_manager.mock_adapter import MockInferenceBackend
from app.services.router.decision import RoutingDecision
from app.services.router.taxonomy import Capability, ModelRole, TaskType


@pytest.fixture
def mock_tier_config() -> TierConfig:
    """Configured hardware tier with distinct model tags for each role."""
    return TierConfig(
        description="Fidelity Test Tier Profile (8 GB VRAM)",
        vram_budget_gb=8.0,
        max_concurrent_models=1,
        router=ModelEntry(provider="mock", model_tag="mock-router:1.5b", context_window=4096),
        reasoning=ModelEntry(provider="mock", model_tag="mock-reasoning:7b", context_window=8192),
        coder=ModelEntry(provider="mock", model_tag="mock-coder:3b", context_window=8192),
        vision=ModelEntry(provider="mock", model_tag="mock-vision:3b", context_window=4096),
        embedding=ModelEntry(provider="local", model_tag="nomic-embed-text", context_window=4096),
    )


@pytest.fixture
def tier_missing_coder() -> TierConfig:
    """Configured tier where the 'coder' role is explicitly absent (None)."""
    return TierConfig(
        description="Tier Missing Coder Role",
        vram_budget_gb=8.0,
        max_concurrent_models=1,
        router=ModelEntry(provider="mock", model_tag="mock-router:1.5b", context_window=4096),
        reasoning=ModelEntry(provider="mock", model_tag="mock-reasoning:7b", context_window=8192),
        coder=None,  # Intentionally missing
        vision=ModelEntry(provider="mock", model_tag="mock-vision:3b", context_window=4096),
        embedding=ModelEntry(provider="local", model_tag="nomic-embed-text", context_window=4096),
    )


@pytest.mark.asyncio
async def test_a_model_role_coder_resolves_to_coder(mock_tier_config: TierConfig):
    """
    TEST A:
    ModelRole.CODER must resolve strictly to role 'coder' and allocate
    the configured coder model tag (mock-coder:3b), never collapsing into reasoning.
    """
    mock_backend = MockInferenceBackend(always_healthy=True)
    mgr = ModelManager(backend=mock_backend, tier_config=mock_tier_config)
    wf = CorrosionAuditWorkflow(model_manager=mgr)

    # Force router to return ModelRole.CODER
    coder_decision = RoutingDecision(
        task_type=TaskType.CODING,
        capability=Capability.CODING,
        model_role=ModelRole.CODER,
        confidence=0.95,
        routing_method="rules",
        reason="Test forced coding route",
    )

    with patch.object(wf.router, "route", return_value=coder_decision):
        req = CorrosionAuditWorkflowRequest(
            objective="Audit thickness readings and generate code to calculate corrosion rate",
            is_demo_preset=True,
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        )
        result = await wf.run(req)

        assert result.status == WorkflowStatus.COMPLETED
        assert result.model_allocation["assigned_role"] == "coder"
        assert result.model_allocation["tier_role"] == "coder"
        assert result.model_allocation["assigned_model_tag"] == "mock-coder:3b"
        assert result.model_allocation["resolved_model_tag"] == "mock-coder:3b"
        assert result.active_model == "mock-coder:3b"


@pytest.mark.asyncio
async def test_b_model_role_reasoning_resolves_to_reasoning(mock_tier_config: TierConfig):
    """
    TEST B:
    ModelRole.REASONING must resolve strictly to role 'reasoning' and allocate
    the configured reasoning model tag (mock-reasoning:7b).
    """
    mock_backend = MockInferenceBackend(always_healthy=True)
    mgr = ModelManager(backend=mock_backend, tier_config=mock_tier_config)
    wf = CorrosionAuditWorkflow(model_manager=mgr)

    reasoning_decision = RoutingDecision(
        task_type=TaskType.DOCUMENT_ANALYSIS,
        capability=Capability.REASONING,
        model_role=ModelRole.REASONING,
        confidence=0.92,
        routing_method="rules",
        reason="Test forced reasoning route",
    )

    with patch.object(wf.router, "route", return_value=reasoning_decision):
        req = CorrosionAuditWorkflowRequest(
            objective="Analyze metallurgical degradation mechanisms in crude distillation column",
            is_demo_preset=True,
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        )
        result = await wf.run(req)

        assert result.status == WorkflowStatus.COMPLETED
        assert result.model_allocation["assigned_role"] == "reasoning"
        assert result.model_allocation["tier_role"] == "reasoning"
        assert result.model_allocation["assigned_model_tag"] == "mock-reasoning:7b"
        assert result.model_allocation["resolved_model_tag"] == "mock-reasoning:7b"
        assert result.active_model == "mock-reasoning:7b"


@pytest.mark.asyncio
async def test_c_model_role_vision_resolves_to_vision(mock_tier_config: TierConfig):
    """
    TEST C:
    ModelRole.VISION must resolve strictly to role 'vision', set execution_capability to 'vision',
    and allocate the configured vision model tag (mock-vision:3b).
    """
    mock_backend = MockInferenceBackend(always_healthy=True)
    mgr = ModelManager(backend=mock_backend, tier_config=mock_tier_config)
    wf = CorrosionAuditWorkflow(model_manager=mgr)

    vision_decision = RoutingDecision(
        task_type=TaskType.VISION,
        capability=Capability.VISION,
        model_role=ModelRole.VISION,
        confidence=0.94,
        routing_method="rules",
        reason="Test forced vision route",
    )

    with patch.object(wf.router, "route", return_value=vision_decision):
        req = CorrosionAuditWorkflowRequest(
            objective="Inspect P&ID schematic diagram for overhead condenser circuit",
            is_demo_preset=True,
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        )
        result = await wf.run(req)

        assert result.status == WorkflowStatus.COMPLETED
        assert result.execution_capability == "vision"
        assert result.model_allocation["assigned_role"] == "vision"
        assert result.model_allocation["tier_role"] == "vision"
        assert result.model_allocation["vision_model_tag"] == "mock-vision:3b"
        assert result.active_model == "mock-vision:3b"


@pytest.mark.asyncio
async def test_d_missing_configured_role_fails_explicitly(tier_missing_coder: TierConfig):
    """
    TEST D:
    When the router requests a role that is NOT configured in the active tier,
    the workflow must fail explicitly with ModelAllocationError and identify
    the missing role and active tier description.
    """
    mock_backend = MockInferenceBackend(always_healthy=True)
    mgr = ModelManager(backend=mock_backend, tier_config=tier_missing_coder)
    wf = CorrosionAuditWorkflow(model_manager=mgr)

    coder_decision = RoutingDecision(
        task_type=TaskType.CODING,
        capability=Capability.CODING,
        model_role=ModelRole.CODER,
        confidence=0.90,
        routing_method="rules",
        reason="Route to coder",
    )

    with patch.object(wf.router, "route", return_value=coder_decision):
        req = CorrosionAuditWorkflowRequest(
            objective="Generate code for parsing piping specs",
            is_demo_preset=True,
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        )
        result = await wf.run(req)

        # Must fail closed with FAILED status
        assert result.status == WorkflowStatus.FAILED
        assert len(result.errors) > 0
        error_msg = result.errors[0]
        # Must explicitly mention the requested role and tier description
        assert "coder" in error_msg.lower()
        assert "Tier Missing Coder Role" in error_msg
        assert "Fail closed without silent fallback" in error_msg

        # The model_allocation stage telemetry must record the failure
        model_stage = next((s for s in result.stages if s.stage_name == "model_allocation"), None)
        assert model_stage is not None
        assert model_stage.status.value == "FAILED"


@pytest.mark.asyncio
async def test_e_missing_role_never_silently_resolves_to_reasoning(tier_missing_coder: TierConfig):
    """
    TEST E:
    Verify that an unconfigured role (coder) NEVER silently falls back to the reasoning model.
    """
    mock_backend = MockInferenceBackend(always_healthy=True)
    mgr = ModelManager(backend=mock_backend, tier_config=tier_missing_coder)
    wf = CorrosionAuditWorkflow(model_manager=mgr)

    coder_decision = RoutingDecision(
        task_type=TaskType.CODING,
        capability=Capability.CODING,
        model_role=ModelRole.CODER,
        confidence=0.90,
        routing_method="rules",
        reason="Route to coder",
    )

    with patch.object(wf.router, "route", return_value=coder_decision):
        req = CorrosionAuditWorkflowRequest(
            objective="Generate code",
            is_demo_preset=True,
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        )
        result = await wf.run(req)

        # Confirm result is NOT successful and active_model was NOT set to reasoning
        assert result.status != WorkflowStatus.COMPLETED
        assert result.active_model != "mock-reasoning:7b"
        if result.model_allocation:
            assert result.model_allocation.get("assigned_model_tag") != "mock-reasoning:7b"
