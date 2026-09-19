"""
Concern 3 Regression Tests: Workbench Document Data Isolation & C-101 Fallback Removal

Verifies:
A. Explicit C-101 demo preset continues to function and identify demo sources.
B. Non-demo document with real measurements displays actual uploaded measurements and does not fabricate C-101 values.
C. Non-demo document with no measurements produces empty measurements, avoiding fabricated sample survey data.
D. Non-demo document with another equipment ID (e.g. P-201) uses P-201 and does not force C-101.
E. Non-demo document with missing equipment ID remains None without inventing C-101.
F. IngestionService extracts evidence correctly under supported import paths without silent evidence=None fallback.
"""

import pytest
from app.services.ingestion.service import IngestionService
from app.services.ingestion.evidence import EngineeringEvidenceExtractor
from app.services.ingestion.models import ExtractionStatus
from app.services.integration.models import (
    CorrosionAuditWorkflowRequest,
    WorkflowExecutionMode,
    WorkflowStatus,
)
from app.services.integration.workflow import CorrosionAuditWorkflow


@pytest.fixture
def workflow() -> CorrosionAuditWorkflow:
    return CorrosionAuditWorkflow()


def test_import_fallback_engineering_evidence_extractor():
    """Verify that EngineeringEvidenceExtractor imports cleanly under both app and backend.app paths."""
    try:
        from app.services.ingestion.evidence import EngineeringEvidenceExtractor as E1
        assert E1 is not None
    except ImportError:
        from backend.app.services.ingestion.evidence import EngineeringEvidenceExtractor as E2
        assert E2 is not None


def test_ingestion_service_extracts_evidence():
    """Verify IngestionService.ingest_file produces non-None evidence for tabular data."""
    csv_bytes = (
        b"Point,Location,Nominal_mm,Actual_mm,Minimum_mm,Date\n"
        b"CML-01,Shell-1,14.0,11.2,8.5,2026-01-10\n"
        b"CML-02,Shell-2,14.0,10.8,8.5,2026-01-10\n"
    )
    svc = IngestionService()
    res = svc.ingest_file(
        content=csv_bytes,
        filename="p201_survey.csv",
        content_type="text/csv",
    )
    assert res.status == ExtractionStatus.SUCCESS
    assert res.evidence is not None
    assert len(res.evidence.get("measurements", [])) == 2
    assert res.evidence["measurements"][0]["measured_thickness_mm"] == 11.2


def test_non_demo_document_with_real_measurements_no_c101_fabrication():
    """Verify non-demo document retains its own measurements and does not use C-101 constants."""
    csv_bytes = (
        b"Point,Location,Nominal_mm,Actual_mm,Minimum_mm,Date\n"
        b"P1,Elbow E1,16.0,13.4,9.5,2026-01-01\n"
        b"P2,Reducer R1,16.0,12.8,9.5,2026-01-01\n"
        b"EQUIPMENT ID: P-201\n"
    )
    svc = IngestionService()
    res = svc.ingest_file(content=csv_bytes, filename="p201_report.csv")
    norm_doc = res.normalized_document
    assert norm_doc is not None

    extractor = EngineeringEvidenceExtractor()
    ev = extractor.extract(norm_doc=norm_doc, is_demo_preset=False)

    assert ev.equipment_id == "P-201"
    assert ev.nominal_thickness_mm == 16.0
    assert ev.minimum_required_thickness_mm == 9.5
    assert ev.current_thickness_mm == 12.8
    assert len(ev.measurements) == 2
    # Verify C-101 constants are NOT fabricated
    assert ev.nominal_thickness_mm != 12.0
    assert ev.current_thickness_mm != 10.1
    assert ev.minimum_required_thickness_mm != 8.0
    assert ev.elapsed_time_source != "DEMO_PRESET"


def test_non_demo_document_no_measurements():
    """Verify non-demo document without measurements returns empty measurements without C-101 fallback."""
    txt_bytes = b"General refinery maintenance guidelines for CDU unit."
    svc = IngestionService()
    res = svc.ingest_file(content=txt_bytes, filename="general_memo.csv")
    norm_doc = res.normalized_document
    assert norm_doc is not None

    extractor = EngineeringEvidenceExtractor()
    ev = extractor.extract(norm_doc=norm_doc, is_demo_preset=False)

    assert ev.measurements == []
    assert ev.nominal_thickness_mm is None
    assert ev.current_thickness_mm is None
    assert ev.minimum_required_thickness_mm is None
    assert ev.elapsed_time_years is None
    assert ev.equipment_id is None


def test_non_demo_document_missing_equipment_id():
    """Verify non-demo document with no equipment ID keeps equipment_id as None."""
    csv_bytes = (
        b"Point,Actual_mm\n"
        b"PT-1,9.8\n"
    )
    svc = IngestionService()
    res = svc.ingest_file(content=csv_bytes, filename="unidentified_survey.csv")
    norm_doc = res.normalized_document
    assert norm_doc is not None

    extractor = EngineeringEvidenceExtractor()
    ev = extractor.extract(norm_doc=norm_doc, is_demo_preset=False)

    assert ev.equipment_id is None
    assert ev.equipment_id != "C-101"


@pytest.mark.asyncio
async def test_explicit_demo_preset_preserves_c101_workflow(workflow: CorrosionAuditWorkflow):
    """Verify explicit demo preset request (is_demo_preset=True) loads C-101 cleanly."""
    req = CorrosionAuditWorkflowRequest(
        objective="Run demo C-101 audit",
        is_demo_preset=True,
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
    )
    res = await workflow.run(request=req)
    assert res.status == WorkflowStatus.COMPLETED
    assert res.calculation_result is not None
    assert res.evidence_summary is not None
    assert res.evidence_summary["equipment_id"] == "C-101"


@pytest.mark.asyncio
async def test_non_demo_without_document_fails_closed(workflow: CorrosionAuditWorkflow):
    """Verify non-demo request without uploaded document fails closed without fabricating C-101."""
    req = CorrosionAuditWorkflowRequest(
        objective="Run non-demo audit without document",
        is_demo_preset=False,
        execution_mode=WorkflowExecutionMode.DETERMINISTIC,
    )
    res = await workflow.run(request=req)
    assert res.status == WorkflowStatus.FAILED
    assert any("No document uploaded and is_demo_preset is False" in err for err in res.errors)
