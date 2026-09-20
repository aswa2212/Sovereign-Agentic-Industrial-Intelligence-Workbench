"""
SIH26117 -- Phase 3 Test Suite: Engineering Evidence -> Existing Calculation Engine Bridge

Validates:
1. Synthetic valid vision evidence -> Existing calculation engine produces verified calculation.
2. Missing vision thickness -> INSUFFICIENT_EVIDENCE, calculation skipped, 0 deliverables.
3. Visual-only pump image -> Visual findings preserved, no thickness, calculation withheld.
4. Existing P-201 CSV workflow remains completely unaffected.
5. User component ID precedence preserved into calculation and deliverables.
6. Missing elapsed time correctly triggers INSUFFICIENT_EVIDENCE strict gate.
"""

import io
from pathlib import Path
from PIL import Image
import pytest

from app.core.config import get_settings
from app.services.ingestion.models import DocumentProvenance
from app.services.integration.models import (
    CorrosionAuditWorkflowRequest,
    StageStatus,
    WorkflowExecutionMode,
    WorkflowStatus,
)
from app.services.integration.workflow import CorrosionAuditWorkflow
from app.services.vision.base import (
    BoundingBox,
    SchematicAnalysisResult,
    VisualFinding,
    VisualFindingType,
)
from app.services.vision.vlm_client import (
    MockVisionProvider,
    VisionEngine,
)


def _make_dummy_png() -> bytes:
    """Create minimal valid PNG image bytes."""
    img = Image.new("RGB", (64, 64), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_controlled_vision_provider(findings, equipment_tags=None):
    """Create a MockVisionProvider returning specified findings."""
    mock_prov = MockVisionProvider()
    eq_tags = equipment_tags or ["P-101"]

    async def _analyze(image_bytes, prompt=None, provenance=None):
        return SchematicAnalysisResult(
            raw_response="Controlled synthetic VLM output for testing",
            findings=findings,
            equipment_tags=eq_tags,
            instrument_tags=[],
            summary="Controlled synthetic VLM analysis",
            provenance=provenance,
            status="success",
            model_used="qwen2.5vl:3b",
        )

    mock_prov.analyze_image = _analyze
    return mock_prov


# ===========================================================================
# Test Suite: Phase 3 Calculation Bridge
# ===========================================================================

class TestPhase3CalculationBridge:
    """Verify the connection from Vision-derived EngineeringEvidence to the calculation engine."""

    @pytest.mark.anyio
    async def test_synthetic_valid_vision_evidence_executes_calculation(self):
        """
        Scenario A:
        Synthetic valid vision evidence:
        nominal_thickness = 15.0 mm
        current_thickness = 12.8 mm
        elapsed_time = 4.0 years
        minimum_required = 10.0 mm
        -> Existing calculation engine executes normally.
        -> corrosion_rate = (15.0 - 12.8) / 4.0 = 0.55 mm/yr
        -> metal_loss = 2.2 mm
        -> remaining_life = (12.8 - 10.0) / 0.55 = 5.09 yrs
        -> Validation passes, deliverables produced.
        """
        prov = DocumentProvenance(source_filename="test_vessel.png", source_sha256="sha_vessel_123")
        findings = [
            VisualFinding(
                finding_type=VisualFindingType.SPEC_NOTE,
                label="thickness_reading",
                text="Nominal thickness: 15.0 mm",
                confidence=0.95,
                provenance=prov,
            ),
            VisualFinding(
                finding_type=VisualFindingType.SPEC_NOTE,
                label="thickness_reading",
                text="Measured wall thickness: 12.8 mm",
                confidence=0.96,
                provenance=prov,
            ),
        ]
        provider = _make_controlled_vision_provider(findings, equipment_tags=["V-301"])
        wf = CorrosionAuditWorkflow(vision_engine=VisionEngine(provider=provider))

        req = CorrosionAuditWorkflowRequest(
            objective="Inspect vessel image and calculate corrosion metrics.",
            document_filename="test_vessel.png",
            component_id="V-301",
            elapsed_time_years=4.0,
            minimum_required_thickness_mm=10.0,
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
            requested_formats=["docx", "xlsx"],
        )

        result = await wf.run(req, pdf_bytes=_make_dummy_png())

        assert result.status == WorkflowStatus.COMPLETED
        assert result.calculation_result is not None

        calc = result.calculation_result
        assert calc["component_id"] == "V-301"
        assert calc["previous_thickness_mm"] == 15.0
        assert calc["current_thickness_mm"] == 12.8
        assert calc["metal_loss_mm"] == 2.2
        assert calc["corrosion_rate_mm_per_year"] == 0.55
        assert calc["remaining_life_years"] == pytest.approx(5.09, abs=0.02)

        # Validation gate verified
        assert result.validation_result is not None
        assert result.validation_result["valid"] is True
        assert result.validation_result["status"] == "VALID"

        # Deliverables produced
        assert len(result.deliverables) == 2
        formats = {d.format for d in result.deliverables}
        assert formats == {"docx", "xlsx"}

        # Stages verified
        stage_map = {s.stage_name: s.status for s in result.stages}
        assert stage_map["sandboxed_calculation"] == StageStatus.SUCCESS
        assert stage_map["engineering_validation_gate"] == StageStatus.SUCCESS
        assert stage_map["deliverables_factory"] == StageStatus.SUCCESS

    @pytest.mark.anyio
    async def test_missing_vision_thickness_withholds_calculation(self):
        """
        Scenario B:
        Image contains visual features but NO numerical thickness measurements.
        -> can_calculate_corrosion_rate == False
        -> sandboxed_calculation is SKIPPED with INSUFFICIENT_EVIDENCE details
        -> 0 deliverables produced
        -> no calculation result
        """
        prov = DocumentProvenance(source_filename="equipment.png", source_sha256="sha_equip_456")
        findings = [
            VisualFinding(
                finding_type=VisualFindingType.EQUIPMENT_TAG,
                label="pump_casing",
                text="Centrifugal pump casing showing minor surface oxidation",
                confidence=0.92,
                provenance=prov,
            ),
            VisualFinding(
                finding_type=VisualFindingType.EQUIPMENT_TAG,
                label="flange_connection",
                text="6 inch class 150 suction flange connection",
                confidence=0.90,
                provenance=prov,
            ),
        ]
        provider = _make_controlled_vision_provider(findings, equipment_tags=["P-202"])
        wf = CorrosionAuditWorkflow(vision_engine=VisionEngine(provider=provider))

        req = CorrosionAuditWorkflowRequest(
            objective="Inspect pump image for integrity.",
            document_filename="equipment.png",
            component_id="P-202",
            elapsed_time_years=4.0,
            minimum_required_thickness_mm=8.0,
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
            requested_formats=["docx", "xlsx"],
        )

        result = await wf.run(req, pdf_bytes=_make_dummy_png())

        assert result.status == WorkflowStatus.COMPLETED
        assert result.calculation_result is None
        assert result.validation_result is None
        assert result.deliverables == []

        stage_map = {s.stage_name: s for s in result.stages}
        calc_stage = stage_map["sandboxed_calculation"]
        assert calc_stage.status == StageStatus.SKIPPED
        assert calc_stage.details["status"] == "INSUFFICIENT_EVIDENCE"
        assert calc_stage.details["can_calculate_corrosion_rate"] is False
        assert "current_thickness_mm" in calc_stage.details["missing_fields"]

    @pytest.mark.anyio
    async def test_visual_only_pump_image_withholds_calculation(self):
        """
        Scenario C:
        The benchmark equipment_centrifugal_pump.png contains no thickness readings.
        Verify that passing it through the workflow preserves visual findings,
        identifies tag P-102A (if returned), reports INSUFFICIENT_EVIDENCE,
        and produces NO fabricated calculation or deliverables.
        """
        settings = get_settings()
        pump_path = (
            settings.project_root
            / "data"
            / "vision_test"
            / "equipment"
            / "equipment_centrifugal_pump.png"
        )
        if not pump_path.is_file():
            pytest.skip("Test image equipment_centrifugal_pump.png not found on disk")

        real_pump_bytes = pump_path.read_bytes()
        wf = CorrosionAuditWorkflow()

        req = CorrosionAuditWorkflowRequest(
            objective="Analyze uploaded pump image for equipment condition.",
            document_filename="equipment_centrifugal_pump.png",
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        )

        result = await wf.run(req, pdf_bytes=real_pump_bytes)

        assert result.status == WorkflowStatus.COMPLETED
        # Visual findings preserved
        assert result.ocr_vision_summary is not None
        assert result.ocr_vision_summary.get("image_input") is True

        # No fabricated calculation
        assert result.calculation_result is None
        assert result.validation_result is None
        assert result.deliverables == []

        # Evidence gate reports insufficient
        calc_stage = next(s for s in result.stages if s.stage_name == "sandboxed_calculation")
        assert calc_stage.status == StageStatus.SKIPPED
        assert calc_stage.details["status"] == "INSUFFICIENT_EVIDENCE"
        assert calc_stage.details["can_calculate_corrosion_rate"] is False

    @pytest.mark.anyio
    async def test_existing_p201_csv_workflow_unchanged(self):
        """
        Scenario D:
        Existing P-201 CSV workflow remains completely unaffected by Phase 3 changes.
        """
        settings = get_settings()
        csv_path = settings.project_root / "data" / "samples" / "P-201_UT_Wall_Survey_2026.csv"
        if not csv_path.is_file():
            pytest.skip("P-201 CSV sample not available")

        csv_bytes = csv_path.read_bytes()
        wf = CorrosionAuditWorkflow()

        req = CorrosionAuditWorkflowRequest(
            objective="Audit P-201 survey readings and calculate corrosion rate.",
            component_id="P-201",
            document_filename="P-201_UT_Wall_Survey_2026.csv",
            elapsed_time_years=5.0,
            minimum_required_thickness_mm=6.0,
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
            requested_formats=["docx", "xlsx"],
        )

        result = await wf.run(req, pdf_bytes=csv_bytes)

        assert result.status == WorkflowStatus.COMPLETED
        assert result.calculation_result is not None
        assert result.calculation_result["component_id"] == "P-201"
        assert result.calculation_result["corrosion_rate_mm_per_year"] > 0
        assert result.validation_result is not None
        assert result.validation_result["valid"] is True
        assert len(result.deliverables) == 2

    @pytest.mark.anyio
    async def test_missing_elapsed_time_gate_blocks_calculation(self):
        """
        Scenario E:
        Vision finds nominal and actual thickness, but elapsed_time_years is absent.
        -> can_calculate_corrosion_rate == False
        -> calculation is NOT executed
        -> missing_fields contains elapsed_time_years
        """
        prov = DocumentProvenance(source_filename="plate.png", source_sha256="sha_plate")
        findings = [
            VisualFinding(
                finding_type=VisualFindingType.SPEC_NOTE,
                label="nominal",
                text="Nominal thickness = 14.0 mm",
                confidence=0.95,
                provenance=prov,
            ),
            VisualFinding(
                finding_type=VisualFindingType.SPEC_NOTE,
                label="measured",
                text="Measured wall thickness: 11.5 mm",
                confidence=0.95,
                provenance=prov,
            ),
        ]
        provider = _make_controlled_vision_provider(findings)
        wf = CorrosionAuditWorkflow(vision_engine=VisionEngine(provider=provider))

        req = CorrosionAuditWorkflowRequest(
            objective="Inspect plate image.",
            document_filename="plate.png",
            component_id="PL-01",
            elapsed_time_years=None,  # Missing!
            minimum_required_thickness_mm=8.0,
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
        )

        result = await wf.run(req, pdf_bytes=_make_dummy_png())

        assert result.status == WorkflowStatus.COMPLETED
        assert result.calculation_result is None
        assert result.deliverables == []

        calc_stage = next(s for s in result.stages if s.stage_name == "sandboxed_calculation")
        assert calc_stage.status == StageStatus.SKIPPED
        assert calc_stage.details["status"] == "INSUFFICIENT_EVIDENCE"
        assert "elapsed_time_years" in calc_stage.details["missing_fields"]

    @pytest.mark.anyio
    async def test_user_component_id_precedence_in_calculation(self):
        """
        Scenario F:
        Explicit user component ID ('USER-TNK-99') takes precedence over VLM tag ('TAG-VLM-01')
        in the calculation payload and deliverables.
        """
        prov = DocumentProvenance(source_filename="tank.png", source_sha256="sha_tank")
        findings = [
            VisualFinding(
                finding_type=VisualFindingType.SPEC_NOTE,
                label="measurement",
                text="Nominal thickness: 20.0 mm | Actual thickness: 18.0 mm",
                confidence=0.95,
                provenance=prov,
            ),
        ]
        provider = _make_controlled_vision_provider(findings, equipment_tags=["TAG-VLM-01"])
        wf = CorrosionAuditWorkflow(vision_engine=VisionEngine(provider=provider))

        req = CorrosionAuditWorkflowRequest(
            objective="Inspect tank image.",
            document_filename="tank.png",
            component_id="USER-TNK-99",  # User precedence!
            elapsed_time_years=5.0,
            minimum_required_thickness_mm=12.0,
            execution_mode=WorkflowExecutionMode.DETERMINISTIC,
            requested_formats=["docx"],
        )

        result = await wf.run(req, pdf_bytes=_make_dummy_png())

        assert result.status == WorkflowStatus.COMPLETED
        assert result.calculation_result is not None
        assert result.calculation_result["component_id"] == "USER-TNK-99"
        assert len(result.deliverables) == 1
        assert "USER-TNK-99" in result.deliverables[0].filename
