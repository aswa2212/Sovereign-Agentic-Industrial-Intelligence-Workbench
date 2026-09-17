"""
SIH26117 — Phase 1: Document Provenance Repair Test Suite

Validates that:
- Uploaded documents provide real engineering inputs instead of discarded data.
- Hardcoded C-101 demonstration constants are removed from the operational calculation path.
- Different documents produce different calculations and results (Tests A & B).
- Insufficient documents fail closed without fabricated calculations (Test C).
- Explicit C-101 demo preset continues to function (Test D).
- Agent failure halts downstream calculations and deliverables (Test E).
- Operational endpoints fail transparently with ApiError without mock fallbacks (Test F).
- Multiple measurements preserve all data and deterministically select the minimum (Test G).
- Conflicting equipment IDs halt the calculation with EVIDENCE_CONFLICT (Test H).
- Missing retirement thickness computes corrosion rate while withholding remaining life (Test I).
"""

import io
import pytest
from unittest.mock import AsyncMock, patch

from pathlib import Path
import pypdf
from app.services.agent.models import AgentContext, Plan, AgentState
from app.services.ingestion.evidence import EngineeringEvidenceExtractor
from app.services.ingestion.service import IngestionService
from app.services.integration.exceptions import IntegrationError
from app.services.integration.models import (
    CorrosionAuditWorkflowRequest,
    CorrosionAuditWorkflowResult,
    StageStatus,
    WorkflowExecutionMode,
    WorkflowStatus,
)
from app.services.integration.workflow import CorrosionAuditWorkflow


@pytest.fixture
def workflow() -> CorrosionAuditWorkflow:
    """Create fresh workflow instance with deterministic execution mode."""
    return CorrosionAuditWorkflow()


@pytest.fixture
def doc_a_csv() -> bytes:
    """Document A: nominal=15.0, current=13.2, interval=4.0, minimum=9.0."""
    return (
        b"Point,Location,Nominal_mm,Actual_mm,Minimum_mm\n"
        b"P-01,Top Head,15.0,14.5,9.0\n"
        b"P-02,Shell Middle,15.0,13.2,9.0\n"
    )


@pytest.fixture
def doc_b_csv() -> bytes:
    """Document B: nominal=20.0, current=18.0, interval=2.0, minimum=10.0."""
    return (
        b"Point,Location,Nominal_mm,Actual_mm,Minimum_mm\n"
        b"PT-10,Inlet Nozzle,20.0,19.2,10.0\n"
        b"PT-20,Elbow Section,20.0,18.0,10.0\n"
    )


@pytest.mark.asyncio
async def test_a_document_a_provenance_and_calculation(workflow: CorrosionAuditWorkflow, doc_a_csv: bytes):
    """
    TEST A:
    Document A: nominal=15.0, current=13.2, interval=4 yrs, minimum=9.0
    Expected: corrosion rate = 0.45 mm/year, remaining life ≈ 9.33 years.
    Verify that these values originated from Document A.
    """
    req = CorrosionAuditWorkflowRequest(
        component_id="P-201",
        elapsed_time_years=4.0,
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        document_filename="inspection_doc_a.csv",
    )
    result: CorrosionAuditWorkflowResult = await workflow.run(req, pdf_bytes=doc_a_csv)

    assert result.status == WorkflowStatus.COMPLETED
    assert result.calculation_result is not None

    # Verify deterministic calculation results
    calc = result.calculation_result
    assert calc["previous_thickness_mm"] == 15.0
    assert calc["current_thickness_mm"] == 13.2
    assert calc["elapsed_time_years"] == 4.0
    assert calc["corrosion_rate_mm_per_year"] == 0.45
    assert pytest.approx(calc["remaining_life_years"], rel=1e-2) == 9.33

    # Verify primary provenance links directly to Document A
    assert result.evidence_summary is not None
    assert result.evidence_summary["source_filename"] == "inspection_doc_a.csv"
    assert result.evidence_summary["current_thickness_mm"] == 13.2
    assert result.evidence_summary["nominal_thickness_mm"] == 15.0


@pytest.mark.asyncio
async def test_b_document_b_differs_from_document_a(
    workflow: CorrosionAuditWorkflow, doc_a_csv: bytes, doc_b_csv: bytes
):
    """
    TEST B:
    Document B: nominal=20.0, current=18.0, interval=2 yrs, minimum=10.0
    Expected: corrosion rate = 1.0 mm/year, remaining life = 8.0 years.
    Verify the result differs from Test A.
    """
    req_a = CorrosionAuditWorkflowRequest(
        component_id="P-201",
        elapsed_time_years=4.0,
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        document_filename="inspection_doc_a.csv",
    )
    res_a = await workflow.run(req_a, pdf_bytes=doc_a_csv)

    req_b = CorrosionAuditWorkflowRequest(
        component_id="P-202",
        elapsed_time_years=2.0,
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        document_filename="inspection_doc_b.csv",
    )
    res_b = await workflow.run(req_b, pdf_bytes=doc_b_csv)

    assert res_b.status == WorkflowStatus.COMPLETED
    calc_b = res_b.calculation_result
    assert calc_b is not None

    assert calc_b["previous_thickness_mm"] == 20.0
    assert calc_b["current_thickness_mm"] == 18.0
    assert calc_b["elapsed_time_years"] == 2.0
    assert calc_b["corrosion_rate_mm_per_year"] == 1.0
    assert calc_b["remaining_life_years"] == 8.0

    # Explicitly assert that Document B results differ from Document A results
    assert res_b.calculation_result != res_a.calculation_result
    assert calc_b["corrosion_rate_mm_per_year"] != res_a.calculation_result["corrosion_rate_mm_per_year"]
    assert calc_b["remaining_life_years"] != res_a.calculation_result["remaining_life_years"]


@pytest.mark.asyncio
async def test_c_unrelated_document_insufficient_evidence(workflow: CorrosionAuditWorkflow):
    """
    TEST C:
    Unrelated document without thickness measurements.
    Expected: INSUFFICIENT_EVIDENCE.
    No fabricated calculation. No engineering deliverables.
    """
    unrelated_csv = (
        b"EmployeeID,Department,Role,Shift\n"
        b"E-101,Refinery Operations,Operator,Day\n"
        b"E-102,Maintenance,Fitter,Night\n"
    )
    req = CorrosionAuditWorkflowRequest(
        component_id="P-999",
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        document_filename="unrelated_staff.csv",
    )
    result = await workflow.run(req, pdf_bytes=unrelated_csv)

    assert result.status == WorkflowStatus.INSUFFICIENT_EVIDENCE
    # Verify no fabricated calculation
    assert result.calculation_result is None
    # Verify no deliverables generated
    assert len(result.deliverables) == 0


@pytest.mark.asyncio
async def test_d_explicit_c101_demo_preset(workflow: CorrosionAuditWorkflow):
    """
    TEST D:
    Explicit C-101 demo preset.
    Expected: Existing C-101 demo continues to work with is_demo_preset=True.
    """
    req = CorrosionAuditWorkflowRequest(
        component_id="C-101",
        is_demo_preset=True,
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
    )
    result = await workflow.run(req, pdf_bytes=None)

    assert result.status == WorkflowStatus.COMPLETED
    assert result.calculation_result is not None
    assert result.calculation_result["previous_thickness_mm"] == 12.0
    assert result.calculation_result["current_thickness_mm"] == 10.1
    assert result.calculation_result["corrosion_rate_mm_per_year"] == 0.38
    assert len(result.deliverables) > 0


@pytest.mark.asyncio
async def test_e_agent_failure_stops_pipeline(workflow: CorrosionAuditWorkflow, doc_a_csv: bytes):
    """
    TEST E:
    Agent state machine reaches FAILED state.
    Expected: Calculation does not execute, deliverables not generated, explicit failure returned.
    """
    failed_ctx = AgentContext(
        task_id="failed-task-1",
        user_request="Audit task",
        current_state=AgentState.FAILED,
        plan=Plan(plan_id="p-1", task_id="failed-task-1", goal="Audit task", steps=[]),
    )

    with patch.object(workflow.agent_orchestrator, "execute_task", new_callable=AsyncMock) as mock_agent:
        mock_agent.return_value = failed_ctx

        req = CorrosionAuditWorkflowRequest(
            component_id="P-201",
            elapsed_time_years=4.0,
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
            document_filename="inspection_doc_a.csv",
        )
        result = await workflow.run(req, pdf_bytes=doc_a_csv)

        assert result.status == WorkflowStatus.FAILED
        assert result.calculation_result is None
        assert len(result.deliverables) == 0
        assert any("FAILED" in err for err in result.errors)


def test_f_backend_unavailable_frontend_contract():
    """
    TEST F:
    Backend unavailable.
    Inspects frontend API service logic ensuring operational endpoints throw ApiError
    and never silently substitute mock C-101 results.
    """
    from pathlib import Path
    api_ts = Path(__file__).parents[2] / "frontend" / "src" / "services" / "api.ts"
    content = api_ts.read_text(encoding="utf-8")

    # Verify that getMockFallback rejects operational endpoints
    assert "cleanEndpoint.startsWith('/workflows')" in content
    assert "cleanEndpoint.startsWith('/agent')" in content
    assert "cleanEndpoint.startsWith('/files')" in content
    assert "cleanEndpoint.startsWith('/deliverables')" in content
    # Verify throw ApiError exists
    assert "throw new ApiError" in content


def test_g_multiple_measurements_minimum_selected(workflow: CorrosionAuditWorkflow):
    """
    TEST G:
    Multiple measurements present in document.
    Expected: Minimum valid measurement selected, all measurements preserved in evidence.
    """
    csv_multi = (
        b"Point,Location,Nominal_mm,Actual_mm,Minimum_mm\n"
        b"CML-01,Shell Top,14.0,13.8,8.5\n"
        b"CML-02,Shell Mid,14.0,12.4,8.5\n"
        b"CML-03,Shell Btm,14.0,11.9,8.5\n"
        b"CML-04,Nozzle N1,14.0,13.1,8.5\n"
    )
    ingest_res = IngestionService().ingest_file(csv_multi, "multi_gauge.csv")
    norm_doc = ingest_res.normalized_document
    assert norm_doc is not None

    evidence = EngineeringEvidenceExtractor().extract(norm_doc)

    # All 4 measurements preserved
    assert len(evidence.measurements) == 4
    # Minimum measurement deterministically selected (11.9 mm at CML-03)
    assert evidence.current_thickness_mm == 11.9
    assert evidence.selected_measurement is not None
    assert evidence.selected_measurement.cml_tag == "CML-03"
    assert evidence.selected_measurement.measured_thickness_mm == 11.9


@pytest.mark.asyncio
async def test_h_equipment_id_conflict_stops_calculation(workflow: CorrosionAuditWorkflow):
    """
    TEST H:
    User component is P-204, but document equipment header specifies P-205.
    Expected: EVIDENCE_CONFLICT, calculation does not run.
    """
    # Create document specifying P-205 in header/point tags
    doc_conflict = (
        b"Point,Location,Nominal_mm,Actual_mm,Minimum_mm\n"
        b"P-205-01,Inlet,16.0,14.2,9.0\n"
    )
    norm_doc = IngestionService().ingest_file(doc_conflict, "inspection_p205.csv").normalized_document
    assert norm_doc is not None

    evidence = EngineeringEvidenceExtractor().extract(
        norm_doc=norm_doc,
        user_component_id="P-204",
        user_elapsed_years=3.0,
    )

    assert evidence.conflict_detected is True
    assert "P-204" in (evidence.conflict_details or "")
    assert "P-205" in (evidence.conflict_details or "")

    # Running workflow with conflict must return EVIDENCE_CONFLICT
    req = CorrosionAuditWorkflowRequest(
        component_id="P-204",
        elapsed_time_years=3.0,
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        document_filename="inspection_p205.csv",
    )
    result = await workflow.run(req, pdf_bytes=doc_conflict)
    assert result.status == WorkflowStatus.EVIDENCE_CONFLICT
    assert result.calculation_result is None
    assert len(result.deliverables) == 0


@pytest.mark.asyncio
async def test_i_missing_minimum_threshold_withholds_remaining_life(workflow: CorrosionAuditWorkflow):
    """
    TEST I:
    Document contains nominal, current, and elapsed time, but NO minimum threshold.
    Expected: Corrosion rate can be calculated; remaining life is withheld / marked insufficient;
    no silent 8.0 mm fallback.
    """
    doc_no_min = (
        b"Point,Location,Nominal_mm,Actual_mm\n"
        b"PT-1,Pipe Elbow,12.0,10.8\n"
    )
    req = CorrosionAuditWorkflowRequest(
        component_id="P-301",
        elapsed_time_years=3.0,
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        document_filename="pipe_no_threshold.csv",
    )
    result = await workflow.run(req, pdf_bytes=doc_no_min)

    assert result.status == WorkflowStatus.COMPLETED
    assert result.calculation_result is not None

    # Corrosion rate is calculated: (12.0 - 10.8) / 3.0 = 0.4 mm/yr
    assert result.calculation_result["previous_thickness_mm"] == 12.0
    assert result.calculation_result["current_thickness_mm"] == 10.8
    assert result.calculation_result["corrosion_rate_mm_per_year"] == 0.4

    # Remaining life is withheld (None) and NO 8.0 mm fallback was used
    assert result.calculation_result["remaining_life_years"] is None
    assert result.calculation_result.get("remaining_life_status") in ("NOT_APPLICABLE", "INSUFFICIENT_EVIDENCE", None)

    # Wall thickness margin check marked insufficient
    margin_check = result.calculation_result.get("margin_check", {})
    assert margin_check.get("status") == "INSUFFICIENT_EVIDENCE"


@pytest.mark.asyncio
async def test_j_non_demo_pdf_live_mode_no_pid_sample(workflow: CorrosionAuditWorkflow):
    """
    TEST J:
    Non-demo PDF in LIVE mode:
    - pid_sample.png is NEVER loaded.
    - Either uploaded PDF is rendered or vision stage is SKIPPED.
    - Non-visual uploads (e.g. CSV) explicitly set StageStatus.SKIPPED.
    """
    # 1. Generate real minimal PDF bytes
    pdf_writer = pypdf.PdfWriter()
    pdf_writer.add_blank_page(width=300, height=200)
    buf = io.BytesIO()
    pdf_writer.write(buf)
    pdf_bytes = buf.getvalue()

    accessed_files = []
    original_read_bytes = Path.read_bytes

    def tracking_read_bytes(self):
        accessed_files.append(str(self))
        return original_read_bytes(self)

    with patch.object(workflow.model_manager, "health_check", new_callable=AsyncMock) as mock_health, \
         patch.object(workflow.vision_engine, "analyze_schematic", new_callable=AsyncMock) as mock_vision, \
         patch("pathlib.Path.read_bytes", side_effect=tracking_read_bytes):

        mock_health.return_value = True
        from app.services.vision.vlm_client import SchematicAnalysisResult
        from app.services.ingestion.models import DocumentProvenance
        mock_vision.return_value = SchematicAnalysisResult(
            model_used="qwen2.5-vl:7b",
            findings=[],
            equipment_tags=["P-101"],
            instrument_tags=[],
            summary="Processed uploaded PDF page rendering",
            status="SUCCESS",
            provenance=DocumentProvenance(
                source_filename="real_upload.pdf",
                source_sha256="mock_sha",
                page_number=1,
            ),
        )

        req = CorrosionAuditWorkflowRequest(
            component_id="P-101",
            elapsed_time_years=2.0,
            execution_mode=WorkflowExecutionMode.LIVE,
            document_filename="real_upload.pdf",
            is_demo_preset=False,
        )
        result = await workflow.run(req, pdf_bytes=pdf_bytes)

        # Confirm pid_sample.png was NEVER read for non-demo upload
        assert not any("pid_sample.png" in f for f in accessed_files), "pid_sample.png was accessed during non-demo upload!"

        # Confirm vision stage either ran with rendered PDF or was SKIPPED
        vision_stage = next((s for s in result.stages if s.stage_name == "ocr_vision_analysis"), None)
        assert vision_stage is not None
        assert vision_stage.status in (StageStatus.SUCCESS, StageStatus.SKIPPED)
        assert vision_stage.details.get("is_demo_fixture") is False

        # 2. Non-visual upload (CSV) in LIVE mode -> must explicitly be SKIPPED
        req_csv = CorrosionAuditWorkflowRequest(
            component_id="P-101",
            elapsed_time_years=2.0,
            execution_mode=WorkflowExecutionMode.LIVE,
            document_filename="inspection_data.csv",
            is_demo_preset=False,
        )
        csv_bytes = b"Point,Location,Nominal_mm,Actual_mm\nPT-1,Shell,12.0,10.5\n"
        result_csv = await workflow.run(req_csv, pdf_bytes=csv_bytes)
        vision_csv_stage = next((s for s in result_csv.stages if s.stage_name == "ocr_vision_analysis"), None)
        assert vision_csv_stage is not None
        assert vision_csv_stage.status == StageStatus.SKIPPED
        assert not any("pid_sample.png" in f for f in accessed_files), "pid_sample.png accessed for non-visual upload!"


@pytest.mark.asyncio
async def test_k_non_demo_c101_no_dates_blocks_calculation(workflow: CorrosionAuditWorkflow):
    """
    TEST K:
    Non-demo C-101 document with nominal/current thickness but NO dates.
    Expected:
    - elapsed_time_years remains None.
    - corrosion-rate calculation is blocked.
    - no 5.0-year fallback.
    - status = INSUFFICIENT_EVIDENCE.
    """
    doc_k = (
        b"Equipment,Point,Nominal_mm,Actual_mm\n"
        b"C-101,PT-1,12.0,10.1\n"
    )
    # Unit level evidence check
    norm_doc = IngestionService().ingest_file(doc_k, "c101_nodates.csv").normalized_document
    assert norm_doc is not None
    ev = EngineeringEvidenceExtractor().extract(norm_doc=norm_doc, is_demo_preset=False)
    assert ev.equipment_id == "C-101"
    assert ev.elapsed_time_years is None
    assert ev.elapsed_time_source == "NONE"
    assert "elapsed_time_years" in ev.missing_fields
    assert ev.can_calculate_corrosion_rate is False

    # Workflow level check
    req = CorrosionAuditWorkflowRequest(
        component_id="C-101",
        is_demo_preset=False,
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        document_filename="c101_nodates.csv",
    )
    result = await workflow.run(req, pdf_bytes=doc_k)
    assert result.status == WorkflowStatus.INSUFFICIENT_EVIDENCE
    assert result.calculation_result is None


@pytest.mark.asyncio
async def test_l_non_demo_c101_no_threshold_withholds_remaining_life(workflow: CorrosionAuditWorkflow):
    """
    TEST L:
    Non-demo C-101 document with nominal/current thickness but NO minimum threshold.
    Expected:
    - minimum_required_thickness_mm remains None.
    - corrosion rate may calculate if interval exists.
    - remaining life is withheld (None).
    - no 8.0-mm fallback.
    """
    doc_l = (
        b"Equipment,Point,Nominal_mm,Actual_mm\n"
        b"C-101,PT-1,12.0,10.1\n"
    )
    # Unit level evidence check
    norm_doc = IngestionService().ingest_file(doc_l, "c101_nothreshold.csv").normalized_document
    assert norm_doc is not None
    ev = EngineeringEvidenceExtractor().extract(
        norm_doc=norm_doc,
        user_elapsed_years=4.0,
        is_demo_preset=False,
    )
    assert ev.equipment_id == "C-101"
    assert ev.minimum_required_thickness_mm is None
    assert ev.minimum_thickness_source == "NONE"
    assert ev.can_calculate_corrosion_rate is True
    assert ev.can_calculate_remaining_life is False

    # Workflow level check
    req = CorrosionAuditWorkflowRequest(
        component_id="C-101",
        elapsed_time_years=4.0,
        is_demo_preset=False,
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        document_filename="c101_nothreshold.csv",
    )
    result = await workflow.run(req, pdf_bytes=doc_l)
    assert result.status == WorkflowStatus.COMPLETED
    assert result.calculation_result is not None
    # Corrosion rate is calculated: (12.0 - 10.1) / 4.0 = 0.475
    assert result.calculation_result["previous_thickness_mm"] == 12.0
    assert result.calculation_result["current_thickness_mm"] == 10.1
    assert result.calculation_result["corrosion_rate_mm_per_year"] == 0.475
    # Remaining life is withheld with no 8.0 mm fallback
    assert result.calculation_result["remaining_life_years"] is None
    assert result.calculation_result.get("remaining_life_status") in ("NOT_APPLICABLE", "INSUFFICIENT_EVIDENCE")


@pytest.mark.asyncio
async def test_m_filename_p205_body_p204_selects_p204(workflow: CorrosionAuditWorkflow):
    """
    TEST M:
    Filename says P-205, document body/table explicitly says P-204.
    Expected:
    - Stronger body/table evidence takes precedence.
    - P-204 is selected.
    - Filename inference does not override document body evidence.
    """
    # Test CSV with filename saying P-205 but body explicitly saying P-204
    doc_m = (
        b"Point,Location,Nominal_mm,Actual_mm,Minimum_mm\n"
        b"PT-1,Vessel Shell,14.0,12.5,8.0\n"
        b"EQUIPMENT ID: P-204\n"
    )
    norm_doc = IngestionService().ingest_file(doc_m, "P-205_preliminary.csv").normalized_document
    assert norm_doc is not None

    ev = EngineeringEvidenceExtractor().extract(norm_doc=norm_doc, is_demo_preset=False)
    assert ev.equipment_id == "P-204"
    assert ev.equipment_id_source == "DOCUMENT_BODY"
    assert ev.conflict_detected is False

    # Also test PDF with filename saying P-205 but page text saying P-204
    pdf_writer = pypdf.PdfWriter()
    pdf_writer.add_blank_page(width=300, height=200)
    buf = io.BytesIO()
    pdf_writer.write(buf)
    pdf_bytes = buf.getvalue()
    norm_doc_pdf = IngestionService().ingest_file(pdf_bytes, "P-205_report.pdf").normalized_document
    assert norm_doc_pdf is not None
    from app.services.ingestion.models import DocumentPage, DocumentProvenance
    norm_doc_pdf.pages = [DocumentPage(
        page_number=1,
        text="INSPECTION SURVEY\nEQUIPMENT ID: P-204\nThickness: 12.5mm",
        provenance=DocumentProvenance(
            source_filename="P-205_report.pdf",
            source_sha256=norm_doc_pdf.sha256,
            page_number=1,
        ),
    )]
    ev_pdf = EngineeringEvidenceExtractor().extract(norm_doc=norm_doc_pdf, is_demo_preset=False)
    assert ev_pdf.equipment_id == "P-204"
    assert ev_pdf.equipment_id_source == "DOCUMENT_BODY"
    assert ev_pdf.conflict_detected is False


@pytest.mark.asyncio
async def test_n_strong_document_evidence_conflict_stops_pipeline(workflow: CorrosionAuditWorkflow):
    """
    TEST N:
    Strong document evidence conflicts:
    - document header/table says P-204
    - document body says P-205
    Expected:
    - EVIDENCE_CONFLICT or explicit ambiguity surfaced.
    - Does NOT silently choose based on filename.
    """
    doc_n = (
        b"Equipment,Point,Nominal_mm,Actual_mm,Minimum_mm\n"
        b"P-204,PT-1,14.0,12.5,8.0\n"
        b"EQUIPMENT ID: P-205\n"
    )
    norm_doc = IngestionService().ingest_file(doc_n, "inspection_survey.csv").normalized_document
    assert norm_doc is not None

    ev = EngineeringEvidenceExtractor().extract(norm_doc=norm_doc, is_demo_preset=False)
    assert ev.conflict_detected is True
    assert "P-204" in (ev.conflict_details or "")
    assert "P-205" in (ev.conflict_details or "")

    # Workflow must halt and return EVIDENCE_CONFLICT
    req = CorrosionAuditWorkflowRequest(
        elapsed_time_years=3.0,
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        document_filename="inspection_survey.csv",
    )
    result = await workflow.run(req, pdf_bytes=doc_n)
    assert result.status == WorkflowStatus.EVIDENCE_CONFLICT
    assert result.calculation_result is None

