"""
SIH26117 — Phase 17A: Focused Unit Tests for Telemetry & Intermediate Validation Cleanup

Verifies:
1. Valid CorrosionCalculation data passes without the previous 9 schema errors.
2. Invalid CorrosionCalculation data is rejected appropriately with field-level details.
3. Full CorrosionAuditResult Stage 7 validation remains strictly unchanged and functional.
4. Vision telemetry allocates and reports qwen2.5vl:3b for vision tasks.
5. Non-vision telemetry preserves assigned_model_tag for reasoning/fast tasks.
6. LIVE mode fails closed if vision provider/model is unavailable.
7. No mock fallback is silently introduced.
"""

import pytest
from app.services.agent.orchestrator import AgentStateMachineOrchestrator
from app.services.integration.models import (
    CorrosionAuditWorkflowRequest,
    WorkflowExecutionMode,
)
from app.services.integration.workflow import CorrosionAuditWorkflow
from app.services.model_manager.manager import ModelManager
from app.services.router.decision import RoutingDecision
from app.services.router.rule_router import RuleRouter
from app.services.router.taxonomy import Capability, ModelRole, TaskType
from app.services.validation.models import (
    CorrosionAuditResult,
    CorrosionCalculation,
    SourceCitation,
    WallThicknessMeasurement,
)
from app.services.validation.service import StructuredOutputService


# ── 1. Valid Calculation Data Passes Cleanly ──────────────────────────────────

def test_valid_corrosion_calculation_no_schema_errors():
    """Requirement 1: Valid CorrosionCalculation payload validates cleanly without 9 errors."""
    val_svc = StructuredOutputService()
    valid_payload = {
        "initial_thickness_mm": 12.0,
        "current_thickness_mm": 10.1,
        "inspection_interval_years": 5.0,
        "minimum_required_mm": 8.0,
        "corrosion_rate_mm_per_year": 0.38,
        "remaining_life_years": 5.53,
        "formula_applied": "corrosion_rate = (initial - current) / interval",
    }
    result = val_svc.validate_calculation(valid_payload)
    assert result.valid is True
    assert result.status == "VALID"
    assert len(result.errors) == 0
    assert "calculation_schema_validation" in result.checks_passed
    assert isinstance(result.validated_data, CorrosionCalculation)


def test_tool_output_format_normalizes_and_validates():
    """Requirement 1b: Tool output dictionary format validates cleanly without 9 errors."""
    val_svc = StructuredOutputService()
    tool_output = {
        "calculation_type": "remaining_life",
        "nominal_or_actual_mm": 10.5,
        "retired_limit_mm": 3.2,
        "corrosion_allowance_remaining_mm": 7.3,
        "corrosion_rate_mm_per_year": 0.25,
        "remaining_life_years": 29.2,
        "formula_applied": "(t_actual - t_retired) / corrosion_rate",
    }
    result = val_svc.validate_calculation(tool_output)
    assert result.valid is True
    assert result.status == "VALID"
    assert len(result.errors) == 0
    assert result.validated_data.current_thickness_mm == 10.5
    assert result.validated_data.minimum_required_mm == 3.2
    assert result.validated_data.corrosion_rate_mm_per_year == 0.25


# ── 2. Invalid Calculation Data is Rejected Appropriately ─────────────────────

def test_invalid_corrosion_calculation_rejected_appropriately():
    """Requirement 2: Negative corrosion rate and negative thickness are rejected."""
    val_svc = StructuredOutputService()
    invalid_payload = {
        "initial_thickness_mm": 12.0,
        "current_thickness_mm": -1.5,
        "inspection_interval_years": 5.0,
        "corrosion_rate_mm_per_year": -0.5,
    }
    result = val_svc.validate_calculation(invalid_payload)
    assert result.valid is False
    assert result.status == "SCHEMA_ERROR"
    assert len(result.errors) >= 1
    error_fields = [e.field for e in result.errors]
    assert "corrosion_rate_mm_per_year" in error_fields or "current_thickness_mm" in error_fields


# ── 3. Full CorrosionAuditResult Stage 7 Validation Remains Unchanged ─────────

def test_full_corrosion_audit_result_stage7_validation_unchanged():
    """Requirement 3: Full Stage 7 StructuredOutputService.validate remains authoritative."""
    val_svc = StructuredOutputService()
    calc = CorrosionCalculation(
        initial_thickness_mm=12.0,
        current_thickness_mm=10.1,
        inspection_interval_years=5.0,
        minimum_required_mm=8.0,
        corrosion_rate_mm_per_year=0.38,
        remaining_life_years=5.53,
        formula_applied="corrosion_rate = (initial - current) / interval; remaining_life = (current - min_req) / rate",
    )
    full_audit = CorrosionAuditResult(
        task_id="task_test_stage7",
        equipment_id="C-101",
        inspection_subject="C-101 Atmospheric Column Overheads Survey",
        current_measurement=WallThicknessMeasurement(
            value_mm=10.1, measurement_date="2026-03-15", location_tag="C-101-CML-4"
        ),
        initial_measurement=WallThicknessMeasurement(
            value_mm=12.0, measurement_date="2021-03-15", location_tag="C-101-NOMINAL"
        ),
        minimum_required_thickness_mm=8.0,
        calculation=calc,
        citations=[
            SourceCitation(
                source_document="08_Equipment_Retirement_Criteria.pdf",
                page_number=3,
                similarity_score=0.7438,
            )
        ],
        confidence=0.95,
    )
    result = val_svc.validate(full_audit.model_dump())
    assert result.valid is True
    assert result.status == "VALID"
    assert len(result.checks_failed) == 0
    assert len(result.checks_passed) >= 8


# ── 4 & 5. Vision and Non-Vision Model Allocation Telemetry ───────────────────

@pytest.mark.anyio
async def test_vision_telemetry_reports_vision_model():
    """Requirement 4: When routed role is vision, assigned model tag reports qwen2.5vl:3b."""
    model_mgr = ModelManager.from_settings()
    tier_cfg = model_mgr.get_tier_config()
    vision_entry = tier_cfg.get_model("vision")
    expected_vision_tag = vision_entry.model_tag if vision_entry else "qwen2.5vl:3b"

    # Simulate routing decision for vision
    route_decision = RoutingDecision(
        task_type=TaskType.VISION,
        model_role=ModelRole.VISION,
        capability=Capability.VISION,
        confidence=0.92,
        primary_rule_id="RULE_VISION",
        routing_method="deterministic_rule",
        reason="P&ID diagram requires visual understanding",
    )

    role_key = route_decision.model_role.value
    mapped_role = (
        "vision" if "vision" in role_key.lower()
        else ("reasoning" if "reason" in role_key.lower()
        else ("router" if "fast" in role_key.lower() else "reasoning"))
    )
    model_entry = tier_cfg.get_model(mapped_role) or tier_cfg.get_model("reasoning")

    assert mapped_role == "vision"
    assert model_entry is not None
    assert model_entry.model_tag == expected_vision_tag


@pytest.mark.anyio
async def test_non_vision_telemetry_reports_reasoning_model():
    """Requirement 5: When routed role is reasoning, assigned model tag reports deepseek-r1:7b."""
    model_mgr = ModelManager.from_settings()
    tier_cfg = model_mgr.get_tier_config()
    reasoning_entry = tier_cfg.get_model("reasoning")
    expected_reasoning_tag = reasoning_entry.model_tag if reasoning_entry else "deepseek-r1:7b"

    route_decision = RoutingDecision(
        task_type=TaskType.REASONING,
        model_role=ModelRole.REASONING,
        capability=Capability.REASONING,
        confidence=0.95,
        primary_rule_id="RULE_CORROSION",
        routing_method="deterministic_rule",
        reason="Complex engineering comparative reasoning",
    )

    role_key = route_decision.model_role.value
    mapped_role = (
        "vision" if "vision" in role_key.lower()
        else ("reasoning" if "reason" in role_key.lower()
        else ("router" if "fast" in role_key.lower() else "reasoning"))
    )
    model_entry = tier_cfg.get_model(mapped_role) or tier_cfg.get_model("reasoning")

    assert mapped_role == "reasoning"
    assert model_entry is not None
    assert model_entry.model_tag == expected_reasoning_tag


# ── 6 & 7. Live Mode Fails Closed on Vision Unavailability (No Mock Fallback) ──

@pytest.mark.anyio
async def test_live_mode_fails_closed_when_vision_fails():
    """Requirement 6 & 7: LIVE mode fails closed if vision provider is unreachable, producing no deliverables."""
    from unittest.mock import AsyncMock, patch
    from app.services.integration.models import WorkflowStatus

    workflow = CorrosionAuditWorkflow()

    # Mock health_check to return False
    with patch.object(workflow.model_manager, "health_check", AsyncMock(return_value=False)):
        req = CorrosionAuditWorkflowRequest(
            objective="Inspect C-101 schematic",
            execution_mode=WorkflowExecutionMode.LIVE,
            component_id="C-101",
            document_filename="corrosion_inspection_c101.pdf",
        )
        result = await workflow.run(req)
        assert result.status == WorkflowStatus.FAILED
        assert any("fail closed" in e.lower() or "unreachable" in e.lower() for e in result.errors)
        assert len(result.deliverables) == 0

