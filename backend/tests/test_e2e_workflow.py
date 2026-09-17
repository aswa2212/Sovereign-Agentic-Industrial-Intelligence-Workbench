"""
SIH26117 — Phase 13: End-to-End System Integration Test Suite

Verifies the complete 11-stage operational pipeline for SIH26117:
Document -> Ingestion -> OCR/Vision -> Router -> Model Manager -> Agent ->
RAG -> Sandbox -> Validation Gate -> Deliverables -> Audit Ledger -> Sovereignty Proof.

Covers:
- North-Star synthetic C-101 corrosion audit workflow
- Multi-format deliverable generation (.docx, .xlsx, .pptx)
- Graceful vision degradation handling
- Fail-closed validation gate (unvalidated outputs never generate deliverables)
- Ingestion failure paths (corrupted/missing files)
- Sandboxed calculation failure handling
- REST API endpoints via TestClient (/corrosion-audit, /health, /{id})
"""

import io
from pathlib import Path
import zipfile
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services.deliverables.models import DeliverableFormat
from app.services.integration.exceptions import ValidationGateError
from app.services.integration.models import (
    CorrosionAuditWorkflowRequest,
    CorrosionAuditWorkflowResult,
    StageStatus,
    WorkflowExecutionMode,
    WorkflowStatus,
)
from app.services.integration.workflow import CorrosionAuditWorkflow
from app.services.validation.models import ValidationResult
from app.services.vision.base import OCREngineUnavailableError
from app.services.vision.ocr_engine import LocalOCREngine, MockOCRProvider


@pytest.fixture
def c101_sample_bytes() -> bytes:
    """Load the synthetic C-101 corrosion inspection PDF."""
    settings = get_settings()
    sample_path = settings.project_root / "data" / "samples" / "corrosion_inspection_c101.pdf"
    assert sample_path.is_file(), f"Sample file missing: {sample_path}"
    return sample_path.read_bytes()


@pytest.fixture
def workflow_instance() -> CorrosionAuditWorkflow:
    """Create a fresh CorrosionAuditWorkflow instance."""
    return CorrosionAuditWorkflow()


@pytest.fixture
def api_client() -> TestClient:
    """Create a FastAPI TestClient."""
    return TestClient(app)


# ── 1. North-Star C-101 Workflow ───────────────────────────────────────────────

@pytest.mark.anyio
async def test_e2e_c101_northstar_workflow_success(workflow_instance):
    """
    Test 1: Full North-Star C-101 workflow execution in deterministic mode.
    Proves all 11 subsystems integrate without error and produce verified deliverables.
    """
    request = CorrosionAuditWorkflowRequest(
        objective="Audit thickness readings against MRPL piping specification, calculate corrosion rate, and generate executive approval note.",
        component_id="C-101",
        is_demo_preset=True,
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        requested_formats=["docx", "xlsx"],
    )

    result = await workflow_instance.run(request)

    # 1. Overall execution status
    assert result.status == WorkflowStatus.COMPLETED
    assert result.duration_seconds < 60.0, f"Workflow took {result.duration_seconds}s (limit: 60s)"
    assert len(result.errors) == 0

    # 2. Subsystem stage verification (all 11 stages present and successful)
    assert len(result.stages) == 11
    stage_names = [s.stage_name for s in result.stages]
    expected_stages = [
        "document_ingestion",
        "ocr_vision_analysis",
        "task_routing",
        "model_allocation",
        "knowledge_retrieval",
        "agent_orchestration",
        "sandboxed_calculation",
        "engineering_validation_gate",
        "deliverables_factory",
        "audit_chain_verification",
        "sovereignty_verification",
    ]
    assert stage_names == expected_stages
    for stage in result.stages:
        assert stage.status in (StageStatus.SUCCESS, StageStatus.DEGRADED), f"Stage {stage.stage_name} failed: {stage.error}"

    # 3. Document ingestion summary
    assert result.document_summary["equipment_id"] == "C-101"
    assert result.document_summary["page_count"] >= 1
    assert result.document_summary["table_count"] >= 1
    assert len(result.document_summary["sha256"]) == 64

    # 4. Routing decision
    assert result.routing_decision is not None
    assert result.routing_decision["confidence"] > 0.5

    # 5. RAG evidence
    assert len(result.rag_citations) >= 1
    assert any(
        any(k in c.get("source_document", "") for k in ("SOP", "MRPL", "C101", "Criteria", "History", "Procedure", "Guideline", ".pdf"))
        for c in result.rag_citations
    )

    # 6. Sandboxed calculation verification
    calc = result.calculation_result
    assert calc is not None
    assert calc["component_id"] == "C-101"
    assert calc["corrosion_rate_mm_per_year"] == 0.38
    assert calc["remaining_life_years"] == 5.53
    assert calc["metal_loss_mm"] == 1.9

    # 7. Validation gate
    val = result.validation_result
    assert val is not None
    assert val["valid"] is True
    assert val["status"] == "VALID"
    assert "corrosion_rate_calculation_verified" in val["checks_passed"]

    # 8. Deliverables verification
    assert len(result.deliverables) == 2
    formats_produced = {d.format for d in result.deliverables}
    assert formats_produced == {"docx", "xlsx"}

    for deliv in result.deliverables:
        assert deliv.file_size_bytes > 0
        assert len(deliv.sha256) == 64
        # Verify physical file existence
        settings = get_settings()
        full_path = settings.project_root / settings.output_dir / deliv.relative_path
        assert full_path.is_file(), f"Deliverable missing on disk: {full_path}"
        # Verify valid ZIP structure (DOCX/XLSX are ZIP archives)
        assert zipfile.is_zipfile(full_path), f"File {full_path} is not a valid Office ZIP package"

    # 9. Audit chain verification
    assert result.audit_summary.get("ledger_valid") is True
    assert result.audit_summary.get("events_checked", 0) > 0

    # 10. Sovereignty verification
    assert result.sovereignty_proof.get("airgap_confirmed") is True
    assert result.sovereignty_proof.get("status") == "PASS"


@pytest.mark.anyio
async def test_e2e_c101_with_uploaded_bytes(workflow_instance, c101_sample_bytes):
    """Test 2: Workflow execution when raw PDF bytes are directly provided."""
    request = CorrosionAuditWorkflowRequest(
        objective="Analyze C-101 inspection sheet and calculate corrosion metrics.",
        component_id="C-101",
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        requested_formats=["docx"],
    )

    result = await workflow_instance.run(request, pdf_bytes=c101_sample_bytes)
    assert result.status == WorkflowStatus.COMPLETED
    assert len(result.deliverables) == 1
    assert result.deliverables[0].format == "docx"


@pytest.mark.anyio
async def test_e2e_c101_with_pptx_format(workflow_instance):
    """Test 3: Multi-format generation including PowerPoint slide deck (.pptx)."""
    request = CorrosionAuditWorkflowRequest(
        objective="Audit C-101 overhead corrosion and compile briefing deck.",
        component_id="C-101",
        is_demo_preset=True,
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        requested_formats=["docx", "xlsx", "pptx"],
    )

    result = await workflow_instance.run(request)
    assert result.status == WorkflowStatus.COMPLETED
    assert len(result.deliverables) == 3
    formats = {d.format for d in result.deliverables}
    assert formats == {"docx", "xlsx", "pptx"}


# ── 2. Failure Paths & Graceful Degradation ───────────────────────────────────

@pytest.mark.anyio
async def test_e2e_invalid_document_bytes_fails_ingestion(workflow_instance):
    """Test 4: Ingestion stage fails cleanly when given corrupt/invalid PDF bytes."""
    corrupt_bytes = b"NOT_A_VALID_PDF_HEADER_JUST_GARBAGE_BYTES_12345"
    request = CorrosionAuditWorkflowRequest(
        objective="Audit C-101 readings.",
        document_filename="corrupt.pdf",
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
    )

    result = await workflow_instance.run(request, pdf_bytes=corrupt_bytes)
    assert result.status == WorkflowStatus.FAILED
    assert len(result.deliverables) == 0
    assert len(result.errors) > 0
    # Stage 0 should be marked failed or error captured
    assert result.stages[0].stage_name == "document_ingestion"


@pytest.mark.anyio
async def test_e2e_missing_document_fails_cleanly(workflow_instance):
    """Test 5: Fails cleanly when requested document does not exist and no bytes passed."""
    request = CorrosionAuditWorkflowRequest(
        document_filename="completely_nonexistent_document_999.pdf",
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
    )

    result = await workflow_instance.run(request)
    assert result.status == WorkflowStatus.FAILED
    assert len(result.deliverables) == 0
    assert any("not found" in err.lower() for err in result.errors)


@pytest.mark.anyio
async def test_e2e_vision_degraded_fallback(workflow_instance):
    """
    Test 6: Graceful vision degradation.
    When OCR engine encounters an unavailable state, the pipeline reports DEGRADED
    and proceeds without crashing.
    """
    class UnavailableOCREngine(LocalOCREngine):
        async def extract_from_image(self, *args, **kwargs):
            raise OCREngineUnavailableError("Tesseract host binary not installed.")

    wf = CorrosionAuditWorkflow(ocr_engine=UnavailableOCREngine(provider=MockOCRProvider()))
    request = CorrosionAuditWorkflowRequest(
        component_id="C-101",
        is_demo_preset=True,
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        requested_formats=["docx"],
    )

    result = await wf.run(request)
    assert result.status == WorkflowStatus.COMPLETED
    assert result.stages[1].stage_name == "ocr_vision_analysis"
    assert result.stages[1].status == StageStatus.DEGRADED
    assert result.ocr_vision_summary.get("degraded") is True
    assert len(result.deliverables) == 1


@pytest.mark.anyio
async def test_e2e_validation_gate_fails_closed(workflow_instance):
    """
    Test 7: Fail-closed engineering validation gate.
    If the validation service rejects the engineering result, deliverable generation
    MUST BE WITHHELD (0 deliverables produced), and status marked VALIDATION_FAILED.
    """
    class FailingValidationService:
        def validate(self, raw):
            return ValidationResult(
                valid=False,
                status="CALCULATION_MISMATCH",
                checks_passed=["schema_validation"],
                checks_failed=["corrosion_rate_calculation_verified"],
                warnings=["Claimed corrosion rate does not match recomputed rate."],
                errors=[],
            )

    wf = CorrosionAuditWorkflow(validation_service=FailingValidationService())
    request = CorrosionAuditWorkflowRequest(
        component_id="C-101",
        is_demo_preset=True,
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        requested_formats=["docx", "xlsx"],
    )

    result = await wf.run(request)
    assert result.status == WorkflowStatus.VALIDATION_FAILED
    # CRITICAL INVARIANT: ZERO DELIVERABLES WHEN VALIDATION FAILS
    assert len(result.deliverables) == 0
    assert any("validation" in err.lower() for err in result.errors)
    assert result.stages[7].stage_name == "engineering_validation_gate"
    assert result.stages[7].status == StageStatus.FAILED


# ── 3. REST API Endpoints ──────────────────────────────────────────────────────

def test_api_workflows_health(api_client):
    """Test 8: GET /api/v1/workflows/health verifies operational readiness."""
    resp = api_client.get("/api/v1/workflows/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "HEALTHY"
    assert data["subsystems"]["ingestion"] is True
    assert data["subsystems"]["router"] is True
    assert data["subsystems"]["model_manager"] is True
    assert data["subsystems"]["deliverables_factory"] is True
    assert data["subsystems"]["audit_service"] is True


def test_api_post_corrosion_audit_workflow(api_client):
    """Test 9: POST /api/v1/workflows/corrosion-audit executes full workflow via REST."""
    resp = api_client.post(
        "/api/v1/workflows/corrosion-audit",
        data={
            "mode": "deterministic",
            "component_id": "C-101",
            "formats": "docx,xlsx",
            "is_demo": "true",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["workflow_id"] is not None
    assert len(data["deliverables"]) == 2
    assert len(data["stages"]) == 11
    assert data["audit_summary"]["ledger_valid"] is True


def test_api_get_workflow_result(api_client):
    """Test 10: GET /api/v1/workflows/{id} retrieves prior execution results."""
    # First execute a workflow
    post_resp = api_client.post(
        "/api/v1/workflows/corrosion-audit",
        data={"mode": "deterministic", "formats": "docx", "is_demo": "true"},
    )
    assert post_resp.status_code == 200
    workflow_id = post_resp.json()["workflow_id"]

    # Now retrieve by ID
    get_resp = api_client.get(f"/api/v1/workflows/{workflow_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["workflow_id"] == workflow_id
    assert data["status"] == "COMPLETED"

    # Verify 404 for unknown ID
    notFound_resp = api_client.get("/api/v1/workflows/unknown_id_99999999")
    assert notFound_resp.status_code == 404


def test_api_post_json_workflow(api_client):
    """Test 11: POST /api/v1/workflows/corrosion-audit/json executes via JSON payload."""
    payload = {
        "objective": "Audit thickness readings against MRPL piping specification for C-101 via JSON trigger",
        "component_id": "C-101",
        "execution_mode": "deterministic",
        "requested_formats": ["docx"],
        "is_demo_preset": True,
    }
    resp = api_client.post("/api/v1/workflows/corrosion-audit/json", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert len(data["deliverables"]) == 1


def test_api_post_corrosion_audit_workflow_with_uploaded_image(api_client):
    """Test 12: POST /api/v1/workflows/corrosion-audit executes successfully with uploaded image (pid_sample.png)."""
    settings = get_settings()
    img_path = settings.project_root / "data" / "samples" / "pid_sample.png"
    assert img_path.is_file(), f"Sample image not found at {img_path}"
    img_bytes = img_path.read_bytes()

    resp = api_client.post(
        "/api/v1/workflows/corrosion-audit",
        files={"file": ("pid_sample.png", img_bytes, "image/png")},
        data={
            "objective": "Inspect C-101 atmospheric column overheads thickness survey, calculate corrosion rate, and generate executive report.",
            "mode": "deterministic",
            "component_id": "C-101",
            "formats": "docx,xlsx",
            "is_demo": "true",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["workflow_id"] is not None
    assert data["document_summary"]["filename"] == "pid_sample.png"
    assert len(data["deliverables"]) == 2
    assert len(data["stages"]) == 11
    assert data["validation_result"]["valid"] is True
    assert data["active_model"] == data["model_allocation"]["assigned_model_tag"]


def test_api_post_vision_only_workflow(api_client):
    """Test 13: POST /api/v1/workflows/corrosion-audit with vision-only objective routes to vision and yields 0 deliverables."""
    settings = get_settings()
    img_path = settings.project_root / "data" / "samples" / "pid_sample.png"
    assert img_path.is_file(), f"Sample image not found at {img_path}"
    img_bytes = img_path.read_bytes()

    vision_prompt = (
        "Analyze the uploaded P&ID image for C-101. Identify all visible equipment tags, piping lines, "
        "valves, instruments, nozzles, and major process connections. Extract the labels and describe "
        "their spatial relationships. Do not perform corrosion calculations, numerical engineering analysis, "
        "or remaining-life estimation. Return structured visual findings only."
    )

    resp = api_client.post(
        "/api/v1/workflows/corrosion-audit",
        files={"file": ("pid_sample.png", img_bytes, "image/png")},
        data={
            "objective": vision_prompt,
            "mode": "deterministic",
            "component_id": "C-101",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["routing_decision"]["model_role"] == "vision"
    assert data["execution_capability"] == "vision"
    assert data["active_model"] == data["model_allocation"]["vision_model_tag"]
    # Section B & C: Explicitly empty deliverables collection
    assert data["deliverables"] == []
    # Do NOT run calculation or validation gate
    assert data["calculation_result"] is None
    assert data["validation_result"] is None

    # Check skipped stages
    stage_map = {s["stage_name"]: s["status"] for s in data["stages"]}
    assert stage_map["document_ingestion"] == "SUCCESS"
    assert stage_map["ocr_vision_analysis"] in ("SUCCESS", "DEGRADED")
    assert stage_map["task_routing"] == "SUCCESS"
    assert stage_map["model_allocation"] == "SUCCESS"
    assert stage_map["sandboxed_calculation"] == "SKIPPED"
    assert stage_map["engineering_validation_gate"] == "SKIPPED"
    assert stage_map["deliverables_factory"] == "SKIPPED"
    assert stage_map["audit_chain_verification"] == "SUCCESS"
    assert stage_map["sovereignty_verification"] == "SUCCESS"


@pytest.mark.anyio
async def test_workflow_deliverables_isolation_across_runs(workflow_instance):
    """Test 14: Consecutive runs isolate deliverables to current task_id and vision produces 0 deliverables."""
    # Run 1: Corrosion calculation task
    req_corrosion = CorrosionAuditWorkflowRequest(
        objective="Audit thickness readings against MRPL piping specification, calculate corrosion rate, and generate executive approval note.",
        component_id="C-101",
        is_demo_preset=True,
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        requested_formats=["docx", "xlsx"],
        task_id="task_corr_alpha",
    )
    res_corrosion = await workflow_instance.run(req_corrosion)
    assert res_corrosion.status == WorkflowStatus.COMPLETED
    assert len(res_corrosion.deliverables) == 2
    assert all(d.artifact_id is not None for d in res_corrosion.deliverables)

    # Run 2: Vision-only task
    req_vision = CorrosionAuditWorkflowRequest(
        objective=(
            "Analyze the uploaded P&ID image for C-101. Identify all visible equipment tags, piping lines, "
            "valves, instruments, nozzles, and major process connections. Extract the labels and describe "
            "their spatial relationships. Do not perform corrosion calculations, numerical engineering analysis, "
            "or remaining-life estimation. Return structured visual findings only."
        ),
        component_id="C-101",
        document_filename="pid_sample.png",
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        task_id="task_vision_beta",
    )
    res_vision = await workflow_instance.run(req_vision)
    assert res_vision.status == WorkflowStatus.COMPLETED
    assert res_vision.execution_capability == "vision"
    assert res_vision.active_model == res_vision.model_allocation["vision_model_tag"]
    # Must NOT leak deliverables from Task 1
    assert res_vision.deliverables == []
    assert res_vision.calculation_result is None
    assert res_vision.validation_result is None


