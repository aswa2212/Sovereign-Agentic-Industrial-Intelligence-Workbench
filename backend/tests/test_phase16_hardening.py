"""
SIH26117 — Phase 16: Final Demo Hardening & Failure Safety Tests

Verifies the 5 Mandatory Failure-Safety Invariants:
Case A: Ollama unavailable -> clear failure, no mock fallback, zero deliverables
Case B: Invalid VLM output -> validation failure, zero deliverables
Case C: Missing input -> structured failure, zero deliverables
Case D: Sovereignty violation -> fail closed, zero deliverables
Case E: Valid execution -> complete workflow, deliverables generated
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.services.audit.models import NetworkObservationReport, SovereigntyStatus
from app.services.audit.service import AuditService
from app.services.integration.exceptions import (
    DocumentIngestionStageError,
    IntegrationError,
    ValidationGateError,
)
from app.services.integration.models import (
    CorrosionAuditWorkflowRequest,
    WorkflowExecutionMode,
    WorkflowStatus,
)
from app.services.integration.workflow import CorrosionAuditWorkflow
from app.services.model_manager.config_loader import ModelEntry, TierConfig
from app.services.model_manager.manager import ModelManager
from app.services.model_manager.mock_adapter import MockInferenceBackend


@pytest.fixture
def mock_tier_config() -> TierConfig:
    return TierConfig(
        description="Phase 16 Hardening Tier",
        vram_budget_gb=8.0,
        max_concurrent_models=1,
        router=ModelEntry(provider="mock", model_tag="qwen2.5:1.5b", context_window=4096),
        reasoning=ModelEntry(provider="mock", model_tag="deepseek-r1:7b", context_window=8192),
        coder=ModelEntry(provider="mock", model_tag="qwen2.5-coder:3b", context_window=8192),
        vision=ModelEntry(provider="ollama", model_tag="qwen2.5vl:3b", context_window=4096),
        embedding=ModelEntry(provider="local", model_tag="nomic-embed-text", context_window=4096),
    )


class TestPhase16FailureSafetyGates:
    """Verify fail-closed guarantees across all pipeline stages."""

    @pytest.mark.anyio
    async def test_case_a_ollama_unavailable_fails_closed_zero_deliverables(self, mock_tier_config):
        """Case A: Ollama unavailable in LIVE mode -> clear failure, no mock fallback, zero deliverables."""
        unhealthy_backend = MockInferenceBackend(always_healthy=False)
        mgr = ModelManager(backend=unhealthy_backend, tier_config=mock_tier_config)

        wf = CorrosionAuditWorkflow(model_manager=mgr)
        req = CorrosionAuditWorkflowRequest(execution_mode=WorkflowExecutionMode.LIVE)

        result = await wf.run(req)

        # Assertions
        assert result.status == WorkflowStatus.FAILED
        assert len(result.deliverables) == 0, "Deliverables must not be generated when provider is unreachable"
        assert result.ocr_vision_summary.get("engine_name") != "mock_ocr", "Must not silently fall back to mock OCR"
        assert any(
            "unreachable" in err.lower() or "failed" in err.lower() or "unavailable" in err.lower()
            for err in result.errors
        )

    @pytest.mark.anyio
    async def test_case_b_invalid_vlm_output_fails_closed_zero_deliverables(self, mock_tier_config):
        """Case B: Invalid VLM output that fails validation -> fail closed, zero deliverables."""
        mock_backend = MockInferenceBackend(always_healthy=True)
        # Mock VLM returning empty / corrupted findings
        mock_backend.generate_structured = AsyncMock(return_value={"corrupted": "payload", "findings": []})
        mgr = ModelManager(backend=mock_backend, tier_config=mock_tier_config)

        wf = CorrosionAuditWorkflow(model_manager=mgr)

        # Force the validation service to reject the payload
        with patch.object(wf.validation_service, "validate") as mock_val:
            mock_res = MagicMock()
            mock_res.valid = False
            mock_res.status = "REJECTED"
            mock_res.checks_passed = ["schema_check"]
            mock_res.checks_failed = ["thickness_bounds_check: thickness exceeds nominal baseline"]
            mock_res.warnings = []
            mock_val.return_value = mock_res

            req = CorrosionAuditWorkflowRequest(execution_mode=WorkflowExecutionMode.DETERMINISTIC)
            result = await wf.run(req)

            assert result.status == WorkflowStatus.VALIDATION_FAILED
            assert len(result.deliverables) == 0, "Deliverables must strictly be withheld on validation failure"
            assert result.validation_result["valid"] is False

    @pytest.mark.anyio
    async def test_case_c_missing_input_fails_structured_zero_deliverables(self, mock_tier_config):
        """Case C: Missing or non-existent document input -> structured failure, zero deliverables."""
        mock_backend = MockInferenceBackend(always_healthy=True)
        mgr = ModelManager(backend=mock_backend, tier_config=mock_tier_config)

        wf = CorrosionAuditWorkflow(model_manager=mgr)
        req = CorrosionAuditWorkflowRequest(
            document_filename="non_existent_schematic_file_xyz.pdf",
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        )

        result = await wf.run(req, pdf_bytes=None)

        assert result.status == WorkflowStatus.FAILED
        assert len(result.deliverables) == 0
        assert any("not found" in err.lower() or "ingestion" in err.lower() for err in result.errors)

    @pytest.mark.anyio
    async def test_case_d_sovereignty_violation_fails_closed_zero_deliverables(self, mock_tier_config):
        """Case D: Sovereignty violation (non-loopback network connection) -> fail closed, zero deliverables."""
        mock_backend = MockInferenceBackend(always_healthy=True)
        mgr = ModelManager(backend=mock_backend, tier_config=mock_tier_config)

        audit_svc = AuditService()

        # Simulate a foreign socket violation detected during sovereignty verification
        fake_sov_status = SovereigntyStatus(
            status="FAIL",
            local_mode_enabled=True,
            external_connections_observed=True,
            violations=["Unauthorized foreign connection observed: 198.51.100.25:443 (ESTABLISHED)"],
            checked_at="2026-09-15T02:00:00Z",
        )
        fake_net_report = NetworkObservationReport(
            timestamp="2026-09-15T02:00:00Z",
            observation_method="psutil_net_connections",
            total_connections=1,
            loopback_connections=0,
            non_loopback_connections=1,
        )

        wf = CorrosionAuditWorkflow(model_manager=mgr, audit_service=audit_svc)
        with patch.object(audit_svc, "check_sovereignty", return_value=fake_sov_status):
            with patch.object(audit_svc, "observe_network", return_value=fake_net_report):
                req = CorrosionAuditWorkflowRequest(execution_mode=WorkflowExecutionMode.DETERMINISTIC)
                result = await wf.run(req)

                assert result.status == WorkflowStatus.FAILED
                assert len(result.deliverables) == 0, "Deliverables must be revoked on sovereignty violation"
                assert any("sovereignty" in err.lower() or "violation" in err.lower() for err in result.errors)

    @pytest.mark.anyio
    async def test_case_e_valid_execution_generates_deliverables(self, mock_tier_config):
        """Case E: Valid execution -> complete workflow, deliverables generated."""
        mock_backend = MockInferenceBackend(always_healthy=True)
        mgr = ModelManager(backend=mock_backend, tier_config=mock_tier_config)

        wf = CorrosionAuditWorkflow(model_manager=mgr)
        req = CorrosionAuditWorkflowRequest(
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
            requested_formats=["docx", "xlsx"],
        )

        result = await wf.run(req)

        assert result.status == WorkflowStatus.COMPLETED
        assert len(result.deliverables) >= 2
        formats = {d.format.lower() for d in result.deliverables}
        assert "docx" in formats
        assert "xlsx" in formats
        assert result.validation_result["valid"] is True
        assert result.sovereignty_proof["status"] == "PASS"
        assert result.audit_summary["ledger_valid"] is True
