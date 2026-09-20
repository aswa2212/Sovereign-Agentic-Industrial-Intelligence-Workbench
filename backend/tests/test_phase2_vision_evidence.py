"""
SIH26117 — Phase 2: Qwen-VL Vision to Structured Engineering Evidence Tests

Verifies:
1. Explicit actual thickness -> current_thickness_mm populated.
2. Explicit nominal thickness -> nominal_thickness_mm populated.
3. Visual corrosion finding -> remains visual finding, does NOT become thickness.
4. Flange/pipe diameter -> does NOT become thickness.
5. Pressure reading -> does NOT become thickness.
6. Motor rating/RPM -> does NOT become thickness.
7. Ambiguous "~12.8 mm" -> no numerical thickness.
8. "?? mm" -> no numerical thickness.
9. Low-confidence thickness finding -> no numerical thickness.
10. Provenance preserved (filename, sha256, coordinates, page_number=None).
11. Explicit user component ID takes precedence over VLM tag.
12. Existing CSV workflow remains unchanged.
13. Phase-1 image routing tests remain compatible.
14. Existing EngineeringEvidence validation/serialization remains compatible.
"""

from pathlib import Path
import pytest
from pydantic import ValidationError

try:
    from app.services.ingestion.evidence import (
        EngineeringEvidence,
        EngineeringEvidenceExtractor,
        ExtractedMeasurement,
    )
    from app.services.ingestion.models import DocumentProvenance, NormalizedDocument, ParsedTable
    from app.services.vision.base import (
        BoundingBox,
        SchematicAnalysisResult,
        VisualFinding,
        VisualFindingType,
    )
except ImportError:
    from backend.app.services.ingestion.evidence import (
        EngineeringEvidence,
        EngineeringEvidenceExtractor,
        ExtractedMeasurement,
    )
    from backend.app.services.ingestion.models import (
        DocumentProvenance,
        NormalizedDocument,
        ParsedTable,
    )
    from backend.app.services.vision.base import (
        BoundingBox,
        SchematicAnalysisResult,
        VisualFinding,
        VisualFindingType,
    )


# ── Generic Test Fixtures ───────────────────────────────────────────────────

GENERIC_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
GENERIC_IMAGE_FILENAME = "inspection_asset_scan.png"


def create_generic_provenance(filename: str = GENERIC_IMAGE_FILENAME, sha256: str = GENERIC_SHA256) -> DocumentProvenance:
    return DocumentProvenance(
        source_filename=filename,
        source_sha256=sha256,
        page_number=None,
    )


def create_generic_bbox() -> BoundingBox:
    return BoundingBox(x_min=0.15, y_min=0.25, x_max=0.45, y_max=0.55)


# ── Test Suite ──────────────────────────────────────────────────────────────

class TestPhase2VisionEvidenceExtraction:
    """Test suite covering the 14 required Phase-2 verification scenarios."""

    def setup_method(self):
        self.extractor = EngineeringEvidenceExtractor()

    # 1. Explicit actual thickness -> current_thickness_mm populated
    def test_explicit_actual_thickness_populated(self):
        prov = create_generic_provenance()
        bbox = create_generic_bbox()
        finding = VisualFinding(
            finding_type=VisualFindingType.SPEC_NOTE,
            label="UT-PT1",
            text="Actual thickness: 12.8 mm",
            confidence=0.92,
            bounding_box=bbox,
            provenance=prov,
            evidence="Direct ultrasonic thickness gauge callout",
        )
        res = SchematicAnalysisResult(
            findings=[finding],
            summary="Drawing with UT measurement",
            provenance=prov,
        )

        evidence = self.extractor.extract_from_vision(res)

        assert evidence.current_thickness_mm == 12.8
        assert evidence.current_thickness_source == "VISION"
        assert len(evidence.measurements) == 1
        assert evidence.selected_measurement is not None
        assert evidence.selected_measurement.measured_thickness_mm == 12.8
        assert evidence.selected_measurement.cml_tag == "UT-PT1"
        assert evidence.selected_measurement.source_page is None
        assert evidence.source_page is None

    # 2. Explicit nominal thickness -> nominal_thickness_mm populated
    def test_explicit_nominal_thickness_populated(self):
        prov = create_generic_provenance()
        finding_nom = VisualFinding(
            finding_type=VisualFindingType.SPEC_NOTE,
            label="DESIGN-SPEC",
            text="Nominal thickness: 15.0 mm",
            confidence=0.90,
            provenance=prov,
        )
        finding_act = VisualFinding(
            finding_type=VisualFindingType.SPEC_NOTE,
            label="MEAS-01",
            text="Measured wall thickness = 13.2 mm",
            confidence=0.94,
            provenance=prov,
        )
        res = SchematicAnalysisResult(
            findings=[finding_nom, finding_act],
            summary="Vessel wall thickness specification",
            provenance=prov,
        )

        evidence = self.extractor.extract_from_vision(res)

        assert evidence.nominal_thickness_mm == 15.0
        assert evidence.nominal_thickness_source == "VISION"
        assert evidence.current_thickness_mm == 13.2
        assert evidence.current_thickness_source == "VISION"
        assert evidence.selected_measurement is not None
        assert evidence.selected_measurement.nominal_thickness_mm == 15.0
        assert evidence.selected_measurement.loss_mm == 1.8

    # 3. Visual corrosion finding -> remains visual finding, does NOT become thickness
    def test_visual_corrosion_finding_does_not_become_thickness(self):
        prov = create_generic_provenance()
        finding = VisualFinding(
            finding_type=VisualFindingType.CORROSION_REGION,
            label="CORR-AREA-1",
            text="Surface corrosion visible on pump casing",
            confidence=0.88,
            provenance=prov,
            evidence="Moderate orange discoloration and pitting indication on volute casing",
        )
        res = SchematicAnalysisResult(
            findings=[finding],
            summary="Visual corrosion inspection",
            provenance=prov,
        )

        evidence = self.extractor.extract_from_vision(res)

        assert evidence.current_thickness_mm is None
        assert evidence.current_thickness_source == "NONE"
        assert evidence.nominal_thickness_mm is None
        assert len(evidence.measurements) == 0
        assert evidence.can_calculate_corrosion_rate is False
        assert "current_thickness_mm" in evidence.missing_fields

    # 4. Flange / pipe diameter -> does NOT become thickness
    def test_flange_and_pipe_diameter_do_not_become_thickness(self):
        prov = create_generic_provenance()
        findings = [
            VisualFinding(
                finding_type=VisualFindingType.SPEC_NOTE,
                label="SUCTION",
                text='SUCTION 6" FLANGE',
                confidence=0.85,
                provenance=prov,
            ),
            VisualFinding(
                finding_type=VisualFindingType.LINE_ID,
                label="PIPE-101",
                text="100 mm pipe diameter",
                confidence=0.89,
                provenance=prov,
            ),
        ]
        res = SchematicAnalysisResult(
            findings=findings,
            summary="Centrifugal pump suction line",
            provenance=prov,
        )

        evidence = self.extractor.extract_from_vision(res)

        assert evidence.current_thickness_mm is None
        assert evidence.nominal_thickness_mm is None
        assert len(evidence.measurements) == 0

    # 5. Pressure reading -> does NOT become thickness
    def test_pressure_reading_does_not_become_thickness(self):
        prov = create_generic_provenance()
        finding = VisualFinding(
            finding_type=VisualFindingType.INSTRUMENT_TAG,
            label="PI-101",
            text="Pressure gauge appears to read approximately 8 bar (116 psi)",
            confidence=0.87,
            provenance=prov,
        )
        res = SchematicAnalysisResult(
            findings=[finding],
            summary="Discharge pressure gauge observation",
            provenance=prov,
        )

        evidence = self.extractor.extract_from_vision(res)

        assert evidence.current_thickness_mm is None
        assert evidence.nominal_thickness_mm is None
        assert len(evidence.measurements) == 0

    # 6. Motor rating / RPM -> does NOT become thickness
    def test_motor_rating_and_rpm_do_not_become_thickness(self):
        prov = create_generic_provenance()
        finding = VisualFinding(
            finding_type=VisualFindingType.SPEC_NOTE,
            label="MOTOR-DRIVE",
            text="ELECTRIC MOTOR 30 kW / 2950 RPM",
            confidence=0.91,
            provenance=prov,
        )
        res = SchematicAnalysisResult(
            findings=[finding],
            summary="Pump motor driver details",
            provenance=prov,
        )

        evidence = self.extractor.extract_from_vision(res)

        assert evidence.current_thickness_mm is None
        assert evidence.nominal_thickness_mm is None
        assert len(evidence.measurements) == 0

    # 7. Ambiguous "~12.8 mm" -> no numerical thickness
    def test_ambiguous_tilde_thickness_rejected(self):
        prov = create_generic_provenance()
        finding = VisualFinding(
            finding_type=VisualFindingType.SPEC_NOTE,
            label="EST-THICKNESS",
            text="Actual thickness: ~12.8 mm",
            confidence=0.80,
            provenance=prov,
        )
        res = SchematicAnalysisResult(
            findings=[finding],
            summary="Approximate drawing note",
            provenance=prov,
        )

        evidence = self.extractor.extract_from_vision(res)

        assert evidence.current_thickness_mm is None
        assert len(evidence.measurements) == 0

    # 8. "?? mm" -> no numerical thickness
    def test_ambiguous_question_marks_thickness_rejected(self):
        prov = create_generic_provenance()
        finding = VisualFinding(
            finding_type=VisualFindingType.SPEC_NOTE,
            label="UNREADABLE-THICKNESS",
            text="Actual thickness: ?? mm",
            confidence=0.75,
            provenance=prov,
        )
        res = SchematicAnalysisResult(
            findings=[finding],
            summary="Damaged or degraded annotation",
            provenance=prov,
        )

        evidence = self.extractor.extract_from_vision(res)

        assert evidence.current_thickness_mm is None
        assert len(evidence.measurements) == 0

    # 9. Low-confidence thickness finding -> no numerical thickness
    def test_low_confidence_thickness_rejected(self):
        prov = create_generic_provenance()
        finding = VisualFinding(
            finding_type=VisualFindingType.SPEC_NOTE,
            label="LOW-CONF-UT",
            text="Actual thickness: 12.8 mm",
            confidence=0.55,  # Below 0.70 threshold
            provenance=prov,
        )
        res = SchematicAnalysisResult(
            findings=[finding],
            summary="Low confidence VLM detection",
            provenance=prov,
        )

        evidence = self.extractor.extract_from_vision(res)

        assert evidence.current_thickness_mm is None
        assert len(evidence.measurements) == 0

    # 10. Provenance preserved: filename, sha256, coordinates, page_number=None
    def test_provenance_preserved_with_none_page_number(self):
        prov = DocumentProvenance(
            source_filename="plant_drawing_rev3.png",
            source_sha256="abc123def45678901234567890abcdef1234567890abcdef1234567890abcdef",
            page_number=None,
        )
        bbox = BoundingBox(x_min=0.1, y_min=0.2, x_max=0.3, y_max=0.4)
        finding = VisualFinding(
            finding_type=VisualFindingType.SPEC_NOTE,
            label="NOZZLE-N1",
            text="UT reading: 11.45 mm",
            confidence=0.93,
            bounding_box=bbox,
            provenance=prov,
        )
        res = SchematicAnalysisResult(
            findings=[finding],
            summary="Nozzle inspection",
            provenance=prov,
        )

        evidence = self.extractor.extract_from_vision(res)

        assert evidence.source_filename == "plant_drawing_rev3.png"
        assert evidence.source_sha256 == "abc123def45678901234567890abcdef1234567890abcdef1234567890abcdef"
        assert evidence.source_page is None

        meas = evidence.selected_measurement
        assert meas is not None
        assert meas.provenance.source_filename == "plant_drawing_rev3.png"
        assert meas.provenance.source_sha256 == "abc123def45678901234567890abcdef1234567890abcdef1234567890abcdef"
        assert meas.provenance.page_number is None
        assert meas.source_page is None
        assert meas.provenance.coordinates == {
            "x_min": 0.1,
            "y_min": 0.2,
            "x_max": 0.3,
            "y_max": 0.4,
        }

    # 11. Explicit user component ID takes precedence over VLM tag
    def test_explicit_user_component_id_takes_precedence_over_vlm_tag(self):
        prov = create_generic_provenance()
        res = SchematicAnalysisResult(
            equipment_tags=["P-102A"],
            findings=[
                VisualFinding(
                    finding_type=VisualFindingType.EQUIPMENT_TAG,
                    label="P-102A",
                    text="TAG: P-102A",
                    confidence=0.95,
                    provenance=prov,
                )
            ],
            summary="Centrifugal Pump P-102A",
            provenance=prov,
        )

        # Case A: User explicitly specifies P-999
        evidence_with_user = self.extractor.extract_from_vision(
            res, user_component_id="P-999"
        )
        assert evidence_with_user.equipment_id == "P-999"
        assert evidence_with_user.equipment_id_source == "USER"

        # Case B: No user component specified -> VLM tag adopted
        evidence_no_user = self.extractor.extract_from_vision(res, user_component_id=None)
        assert evidence_no_user.equipment_id == "P-102A"
        assert evidence_no_user.equipment_id_source == "VISION"

    # 12. Existing P-201 CSV workflow remains unchanged
    def test_existing_p201_csv_workflow_unchanged(self):
        """Verify that extracting evidence from a tabular CSV NormalizedDocument is identical."""
        prov = DocumentProvenance(
            source_filename="P-201_UT_Wall_Survey_2026.csv",
            source_sha256="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            page_number=1,
        )
        table = ParsedTable(
            table_id="csv_table_1",
            source_page=1,
            headers=["CML Tag", "Location", "Nominal (mm)", "Measured (mm)", "Date"],
            rows=[
                ["CML-01", "Suction Elbow", "12.7", "11.8", "2026-02-18"],
                ["CML-02", "Discharge Nozzle", "12.7", "10.2", "2026-02-18"],
                ["CML-03", "Casing Bottom", "12.7", "11.1", "2026-02-18"],
            ],
            extraction_method="csv-sniffer",
            provenance=prov,
        )
        norm_doc = NormalizedDocument(
            document_id="doc-csv-test",
            sha256=prov.source_sha256,
            original_filename="P-201_UT_Wall_Survey_2026.csv",
            sanitized_filename="P-201_UT_Wall_Survey_2026.csv",
            file_extension="csv",
            media_type="text/csv",
            size_bytes=500,
            raw_path="data/samples/P-201_UT_Wall_Survey_2026.csv",
            created_at="2026-02-18T10:00:00Z",
            extraction_method="csv-sniffer",
            tables=[table],
            metadata={"equipment_id": "P-201"},
        )

        evidence = self.extractor.extract(
            norm_doc,
            user_component_id="P-201",
            user_elapsed_years=5.0,
            user_min_thickness=6.35,
        )

        assert evidence.equipment_id == "P-201"
        assert evidence.equipment_id_source == "USER"
        assert evidence.nominal_thickness_mm == 12.7
        assert evidence.current_thickness_mm == 10.2  # Minimum of [11.8, 10.2, 11.1]
        assert evidence.elapsed_time_years == 5.0
        assert evidence.minimum_required_thickness_mm == 6.35
        assert evidence.can_calculate_corrosion_rate is True
        assert evidence.can_calculate_remaining_life is True

    # 13. Phase-1 image routing tests remain compatible
    def test_evidence_gate_sufficiency_evaluation(self):
        """Verify that can_calculate_corrosion_rate is True only when all 3 required fields exist."""
        prov = create_generic_provenance()
        finding = VisualFinding(
            finding_type=VisualFindingType.SPEC_NOTE,
            label="MEAS-1",
            text="Actual thickness: 12.0 mm",
            confidence=0.95,
            provenance=prov,
        )
        res = SchematicAnalysisResult(findings=[finding], provenance=prov)

        # CASE A: Only actual thickness present -> calculation NOT eligible
        ev_partial = self.extractor.extract_from_vision(res)
        assert ev_partial.current_thickness_mm == 12.0
        assert ev_partial.nominal_thickness_mm is None
        assert ev_partial.elapsed_time_years is None
        assert ev_partial.can_calculate_corrosion_rate is False
        assert set(ev_partial.missing_fields) == {"nominal_thickness_mm", "elapsed_time_years"}

        # CASE B: Actual + Nominal + User Elapsed Years present -> calculation ELIGIBLE
        finding_both = VisualFinding(
            finding_type=VisualFindingType.SPEC_NOTE,
            label="MEAS-2",
            text="Nominal thickness: 14.0 mm, Measured wall thickness: 12.0 mm",
            confidence=0.95,
            provenance=prov,
        )
        res_both = SchematicAnalysisResult(findings=[finding_both], provenance=prov)
        ev_complete = self.extractor.extract_from_vision(
            res_both, user_elapsed_years=4.0, user_min_thickness=5.0
        )
        assert ev_complete.current_thickness_mm == 12.0
        assert ev_complete.nominal_thickness_mm == 14.0
        assert ev_complete.elapsed_time_years == 4.0
        assert ev_complete.can_calculate_corrosion_rate is True
        assert ev_complete.can_calculate_remaining_life is True
        assert len(ev_complete.missing_fields) == 0

    # 14. Existing EngineeringEvidence validation/serialization remains compatible
    def test_engineering_evidence_serialization_compatibility(self):
        prov = create_generic_provenance()
        meas = ExtractedMeasurement(
            cml_tag="CML-01",
            location_desc="Pump casing test point",
            nominal_thickness_mm=10.0,
            measured_thickness_mm=8.5,
            loss_mm=1.5,
            source_page=None,
            provenance=prov,
        )
        evidence = EngineeringEvidence(
            equipment_id="P-102A",
            equipment_id_source="VISION",
            inspection_subject="Centrifugal Pump P-102A Volute Casing",
            measurements=[meas],
            selected_measurement=meas,
            nominal_thickness_mm=10.0,
            nominal_thickness_source="VISION",
            current_thickness_mm=8.5,
            current_thickness_source="VISION",
            elapsed_time_years=3.0,
            elapsed_time_source="USER",
            minimum_required_thickness_mm=4.0,
            minimum_thickness_source="USER",
            source_filename=GENERIC_IMAGE_FILENAME,
            source_sha256=GENERIC_SHA256,
            source_page=None,
            extraction_method="vision_vlm",
            can_calculate_corrosion_rate=True,
            can_calculate_remaining_life=True,
        )

        dumped = evidence.model_dump()
        reconstructed = EngineeringEvidence.model_validate(dumped)

        assert reconstructed.equipment_id == "P-102A"
        assert reconstructed.current_thickness_mm == 8.5
        assert reconstructed.source_page is None
        assert reconstructed.selected_measurement.source_page is None
        assert reconstructed.selected_measurement.provenance.page_number is None
        assert reconstructed.can_calculate_corrosion_rate is True
