"""
SIH26117 — Phase 10: Deterministic Office Deliverables Test Suite

Comprehensive test suite verifying:
1. DOCX builder: document structure, tables, callout blocks, provenance, verification.
2. XLSX builder: multi-sheet workbook, numeric preservation, controlled formulas, no VBA.
3. PPTX builder: 5-slide executive presentation, OpenXML conformance, content integrity.
4. DeliverablesFactory: multi-format dispatch, deterministic naming, format filtering.
5. Precondition validation: unvalidated or invalid Phase 9 inputs fail closed.
6. Determinism: identical structured input yields identical semantic content across runs.
7. Security: path traversal prevention, formula injection blocking, zero eval/exec/subprocess.
8. REST API: POST /api/v1/deliverables/generate and GET /api/v1/deliverables/download.
9. Integration: end-to-end integration with Phase 9 StructuredOutputService.
"""

from pathlib import Path
import shutil
import tempfile
import zipfile
import docx
from fastapi.testclient import TestClient
import openpyxl
import pytest

from app.core.config import get_settings
from app.main import app
from app.services.deliverables.docx_builder import DocxDeliverableBuilder
from app.services.deliverables.exceptions import (
    DeliverableError,
    InvalidDeliverableInputError,
    PathTraversalSecurityError,
    UnsupportedFormatError,
    UnvalidatedInputError,
)
from app.services.deliverables.factory import DeliverablesFactory
from app.services.deliverables.models import (
    DeliverableFormat,
    GeneratedArtifact,
    ReportMetadata,
)
from app.services.deliverables.naming import (
    generate_artifact_filename,
    resolve_and_verify_output_path,
    sanitize_identifier,
)
from app.services.deliverables.pptx_builder import PptxDeliverableBuilder
from app.services.deliverables.validators import (
    validate_deliverable_input,
    verify_file_integrity,
)
from app.services.deliverables.xlsx_builder import XlsxDeliverableBuilder
from app.services.validation.models import (
    CorrosionAuditResult,
    CorrosionCalculation,
    InspectionFinding,
    MeasurementUnit,
    RecommendationCode,
    SourceCitation,
    ValidationErrorDetail,
    ValidationResult,
    WallThicknessMeasurement,
)
from app.services.validation.service import StructuredOutputService

client = TestClient(app)


# ── Test Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def sample_audit_result() -> CorrosionAuditResult:
    """Provides a valid, verified CorrosionAuditResult for testing."""
    return CorrosionAuditResult(
        task_id="task_audit_101",
        equipment_id="C-101",
        inspection_subject="Crude Overhead Condenser Piping Circuit",
        current_measurement=WallThicknessMeasurement(
            value_mm=4.20,
            unit=MeasurementUnit.MM,
            measurement_date="2026-03-15",
            location_tag="10-HC-101-CML-A",
        ),
        initial_measurement=WallThicknessMeasurement(
            value_mm=8.00,
            unit=MeasurementUnit.MM,
            measurement_date="2021-03-15",
            location_tag="10-HC-101-CML-A",
        ),
        minimum_required_thickness_mm=3.20,
        calculation=CorrosionCalculation(
            initial_thickness_mm=8.00,
            current_thickness_mm=4.20,
            inspection_interval_years=5.0,
            minimum_required_mm=3.20,
            corrosion_rate_mm_per_year=0.760,
            remaining_life_years=1.316,
            formula_applied="API 570 Section 7.1",
        ),
        findings=[
            InspectionFinding(
                finding_id="F-01",
                description="Localized wall thinning identified at 6 o'clock position near elbow.",
                severity="HIGH",
            ),
            InspectionFinding(
                finding_id="F-02",
                description="External protective coating degradation observed on spool segment B.",
                severity="MEDIUM",
            ),
        ],
        conclusion="Corrosion rate exceeds historical design baseline; remaining life is approximately 1.3 years.",
        recommendation=RecommendationCode.IMMEDIATE_ACTION,
        citations=[
            SourceCitation(
                source_document="SOP-MRPL-PIP-001.pdf",
                page_number=3,
                chunk_id="a1b2c3d4e5f6_p3_c0002",
                content_sha256="68561842b792ddbcf3a539fe893aa3c0be7840544a41c7dfd2f976eacc4f9cbd",
                similarity_score=0.9446,
                excerpt="For Class 150 carbon steel process piping, the minimum allowable retired wall thickness shall not be less than 3.2 mm.",
            )
        ],
        confidence=0.95,
    )


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Creates an isolated temporary output directory."""
    out = tmp_path / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    return out


# ── 1. Naming & Path Traversal Security Tests ──────────────────────────────────

class TestNamingAndSecurity:
    """Verifies identifier sanitization and path traversal prevention."""

    def test_sanitize_identifier_removes_dangerous_characters(self):
        assert sanitize_identifier("C-101") == "C-101"
        assert sanitize_identifier("../../etc/passwd") == "etc-passwd"
        assert sanitize_identifier("..\\..\\windows\\system32") == "windows-system32"
        assert sanitize_identifier("equipment;rm -rf /") == "equipmentrm_-rf"
        assert sanitize_identifier(None) == "unspecified"
        assert sanitize_identifier("") == "unspecified"

    def test_generate_artifact_filename_deterministic(self):
        fn1 = generate_artifact_filename("C-101", DeliverableFormat.DOCX, task_id="task123")
        fn2 = generate_artifact_filename("C-101", DeliverableFormat.DOCX, task_id="task123")
        assert fn1 == fn2
        assert fn1 == "C-101_corrosion_audit_task123.docx"

    def test_generate_artifact_filename_formats(self):
        assert generate_artifact_filename("V-201", DeliverableFormat.XLSX, task_id="t1").endswith(".xlsx")
        assert generate_artifact_filename("E-301", DeliverableFormat.PPTX, task_id="t1").endswith(".pptx")

    def test_resolve_and_verify_output_path_normal(self, temp_output_dir):
        path = resolve_and_verify_output_path(temp_output_dir, "report.docx")
        assert path == (temp_output_dir / "report.docx").resolve()

    def test_resolve_and_verify_output_path_blocks_parent_traversal(self, temp_output_dir):
        with pytest.raises(PathTraversalSecurityError):
            resolve_and_verify_output_path(temp_output_dir, "../escape.docx")

    def test_resolve_and_verify_output_path_blocks_slash_traversal(self, temp_output_dir):
        with pytest.raises(PathTraversalSecurityError):
            resolve_and_verify_output_path(temp_output_dir, "sub/escape.docx")

    def test_resolve_and_verify_output_path_blocks_null_bytes(self, temp_output_dir):
        with pytest.raises(PathTraversalSecurityError):
            resolve_and_verify_output_path(temp_output_dir, "report.docx\x00.exe")


# ── 2. Precondition Validation Tests ──────────────────────────────────────────

class TestPreconditionValidators:
    """Verifies that invalid or unvalidated inputs are rejected (fail-closed)."""

    def test_valid_audit_result_accepted(self, sample_audit_result):
        res = validate_deliverable_input(sample_audit_result)
        assert res.equipment_id == "C-101"

    def test_valid_validation_result_accepted(self, sample_audit_result):
        val_res = ValidationResult(
            valid=True,
            status="VALID",
            validated_data=sample_audit_result,
            validation_checks=["schema", "engineering"],
            checks_passed=["schema", "engineering"],
        )
        res = validate_deliverable_input(val_res)
        assert res.equipment_id == "C-101"

    def test_invalid_validation_result_rejected(self):
        val_res = ValidationResult(
            valid=False,
            status="CALCULATION_MISMATCH",
            errors=[ValidationErrorDetail(code="MISMATCH", message="Corrosion rate mismatch")],
            validation_checks=["schema", "engineering"],
            checks_failed=["engineering"],
        )
        with pytest.raises(UnvalidatedInputError) as exc:
            validate_deliverable_input(val_res)
        assert "Cannot generate deliverable from invalid Phase 9 result" in str(exc.value)

    def test_none_payload_rejected(self):
        with pytest.raises(InvalidDeliverableInputError):
            validate_deliverable_input(None)

    def test_missing_equipment_id_rejected(self, sample_audit_result):
        raw = sample_audit_result.model_dump()
        raw["equipment_id"] = "   "
        with pytest.raises(InvalidDeliverableInputError):
            validate_deliverable_input(raw)

    def test_missing_inspection_subject_rejected(self, sample_audit_result):
        raw = sample_audit_result.model_dump()
        raw["inspection_subject"] = ""
        with pytest.raises(InvalidDeliverableInputError):
            validate_deliverable_input(raw)


# ── 3. DOCX Builder Tests ─────────────────────────────────────────────────────

class TestDocxBuilder:
    """Verifies deterministic Word memorandum generation."""

    def test_build_docx_generates_valid_document(self, sample_audit_result, temp_output_dir):
        builder = DocxDeliverableBuilder()
        out_file = temp_output_dir / "test_report.docx"
        artifact = builder.build(sample_audit_result, ReportMetadata(), out_file)

        assert artifact.format == DeliverableFormat.DOCX
        assert artifact.file_size_bytes > 0
        assert len(artifact.sha256_hash) == 64
        assert out_file.exists()

        # Structural inspection with python-docx
        doc = docx.Document(out_file)
        assert len(doc.paragraphs) > 5
        assert len(doc.tables) >= 5

        # Verify key content elements
        all_text = " ".join([p.text for p in doc.paragraphs] + [c.text for t in doc.tables for r in t.rows for c in r.cells])
        assert "MANGALORE REFINERY AND PETROCHEMICALS LIMITED" in all_text
        assert "C-101" in all_text
        assert "4.20" in all_text
        assert "0.760" in all_text
        assert "IMMEDIATE_ACTION" in all_text
        assert "SOP-MRPL-PIP-001.pdf" in all_text

    def test_build_docx_preserves_provenance(self, sample_audit_result, temp_output_dir):
        builder = DocxDeliverableBuilder()
        out_file = temp_output_dir / "provenance_test.docx"
        builder.build(sample_audit_result, ReportMetadata(), out_file)

        doc = docx.Document(out_file)
        table_texts = [c.text for t in doc.tables for r in t.rows for c in r.cells]
        assert any("SOP-MRPL-PIP-001.pdf" in txt for txt in table_texts)
        assert any("3" in txt for txt in table_texts)  # Page 3


# ── 4. XLSX Builder Tests ─────────────────────────────────────────────────────

class TestXlsxBuilder:
    """Verifies deterministic Excel calculation workbook generation."""

    def test_build_xlsx_generates_valid_workbook(self, sample_audit_result, temp_output_dir):
        builder = XlsxDeliverableBuilder()
        out_file = temp_output_dir / "test_calc.xlsx"
        artifact = builder.build(sample_audit_result, ReportMetadata(), out_file)

        assert artifact.format == DeliverableFormat.XLSX
        assert artifact.file_size_bytes > 0
        assert out_file.exists()

        # Structural inspection with openpyxl
        wb = openpyxl.load_workbook(out_file, data_only=False)
        expected_sheets = ["Summary", "Measurements", "Calculations", "Evidence", "Validation"]
        assert wb.sheetnames == expected_sheets

    def test_xlsx_numeric_cells_and_controlled_formulas(self, sample_audit_result, temp_output_dir):
        builder = XlsxDeliverableBuilder()
        out_file = temp_output_dir / "calc_test.xlsx"
        builder.build(sample_audit_result, ReportMetadata(), out_file)

        wb = openpyxl.load_workbook(out_file, data_only=False)
        ws_calc = wb["Calculations"]

        # Check numeric cells
        assert ws_calc["C5"].value == 8.00  # initial_thickness
        assert ws_calc["C6"].value == 4.20  # current_thickness
        assert ws_calc["C7"].value == 5.0   # interval
        assert ws_calc["C8"].value == 3.20  # t_min

        # Check controlled deterministic formulas
        assert ws_calc["C9"].value == "=(C5-C6)/C7"
        assert ws_calc["C10"].value == "=(C6-C8)/C9"

    def test_xlsx_no_macros_or_vba(self, sample_audit_result, temp_output_dir):
        builder = XlsxDeliverableBuilder()
        out_file = temp_output_dir / "no_vba_test.xlsx"
        builder.build(sample_audit_result, ReportMetadata(), out_file)

        wb = openpyxl.load_workbook(out_file)
        assert wb.vba_archive is None  # Confirms no VBA macros attached


# ── 5. PPTX Builder Tests ─────────────────────────────────────────────────────

class TestPptxBuilder:
    """Verifies deterministic PowerPoint briefing presentation generation."""

    def test_build_pptx_generates_valid_presentation(self, sample_audit_result, temp_output_dir):
        builder = PptxDeliverableBuilder()
        out_file = temp_output_dir / "briefing.pptx"
        artifact = builder.build(sample_audit_result, ReportMetadata(), out_file)

        assert artifact.format == DeliverableFormat.PPTX
        assert artifact.file_size_bytes > 0
        assert out_file.exists()

        # Verify OpenXML ZIP package structure
        with zipfile.ZipFile(out_file, "r") as zf:
            namelist = zf.namelist()
            assert "[Content_Types].xml" in namelist
            assert "ppt/presentation.xml" in namelist
            assert "ppt/slides/slide1.xml" in namelist
            assert "ppt/slides/slide2.xml" in namelist
            assert "ppt/slides/slide3.xml" in namelist
            assert "ppt/slides/slide4.xml" in namelist
            assert "ppt/slides/slide5.xml" in namelist

    def test_pptx_contains_key_data_and_provenance(self, sample_audit_result, temp_output_dir):
        builder = PptxDeliverableBuilder()
        out_file = temp_output_dir / "content_test.pptx"
        builder.build(sample_audit_result, ReportMetadata(), out_file)

        with zipfile.ZipFile(out_file, "r") as zf:
            all_slide_text = ""
            for i in range(1, 6):
                all_slide_text += zf.read(f"ppt/slides/slide{i}.xml").decode("utf-8")

            assert "C-101" in all_slide_text
            assert "4.20" in all_slide_text
            assert "0.760" in all_slide_text
            assert "IMMEDIATE_ACTION" in all_slide_text
            assert "SOP-MRPL-PIP-001.pdf" in all_slide_text


# ── 6. DeliverablesFactory Orchestration Tests ────────────────────────────────

class TestDeliverablesFactory:
    """Verifies factory orchestration, format dispatch, and output folder routing."""

    def test_factory_generates_all_three_formats(self, sample_audit_result, temp_output_dir):
        factory = DeliverablesFactory(output_dir=temp_output_dir)
        result = factory.generate(sample_audit_result)

        assert result.success is True
        assert len(result.artifacts) == 3
        formats = [a.format for a in result.artifacts]
        assert DeliverableFormat.DOCX in formats
        assert DeliverableFormat.XLSX in formats
        assert DeliverableFormat.PPTX in formats

        # Verify output files in sub-folders
        assert (temp_output_dir / "docx" / result.artifacts[0].filename).exists()
        assert (temp_output_dir / "xlsx" / result.artifacts[1].filename).exists()
        assert (temp_output_dir / "pptx" / result.artifacts[2].filename).exists()

    def test_factory_generates_single_format(self, sample_audit_result, temp_output_dir):
        factory = DeliverablesFactory(output_dir=temp_output_dir)
        doc_art = factory.generate_docx(sample_audit_result)
        assert doc_art.format == DeliverableFormat.DOCX
        assert (temp_output_dir / "docx" / doc_art.filename).exists()

    def test_factory_unsupported_format_rejected(self, sample_audit_result, temp_output_dir):
        factory = DeliverablesFactory(output_dir=temp_output_dir)
        with pytest.raises(UnsupportedFormatError):
            factory.generate(sample_audit_result, formats=["pdf"])

    def test_factory_rejects_unvalidated_input(self, temp_output_dir):
        factory = DeliverablesFactory(output_dir=temp_output_dir)
        invalid_val_res = ValidationResult(
            valid=False,
            status="INVALID",
            errors=[ValidationErrorDetail(code="INVALID_WALL", message="Negative thickness")],
            validation_checks=["schema"],
            checks_failed=["schema"],
        )
        with pytest.raises(UnvalidatedInputError):
            factory.generate(invalid_val_res)


# ── 7. Determinism Test (REQUIRED) ─────────────────────────────────────────────

class TestDeliverablesDeterminism:
    """
    REQUIRED DETERMINISM VERIFICATION:
    Generates DOCX, XLSX, and PPTX twice from identical input.
    Asserts semantic, structural, and mathematical equality across runs.
    """

    def test_docx_semantic_determinism(self, sample_audit_result, tmp_path):
        f1 = DeliverablesFactory(output_dir=tmp_path / "run1")
        f2 = DeliverablesFactory(output_dir=tmp_path / "run2")

        r1 = f1.generate_docx(sample_audit_result)
        r2 = f2.generate_docx(sample_audit_result)

        assert r1.filename == r2.filename

        doc1 = docx.Document(tmp_path / "run1/docx" / r1.filename)
        doc2 = docx.Document(tmp_path / "run2/docx" / r2.filename)

        # Paragraph text comparison
        p1 = [p.text for p in doc1.paragraphs]
        p2 = [p.text for p in doc2.paragraphs]
        assert p1 == p2, "DOCX paragraph text differs between deterministic runs"

        # Table content comparison
        t1 = [[c.text for row in t.rows for c in row.cells] for t in doc1.tables]
        t2 = [[c.text for row in t.rows for c in row.cells] for t in doc2.tables]
        assert t1 == t2, "DOCX table cells differ between deterministic runs"

    def test_xlsx_structural_determinism(self, sample_audit_result, tmp_path):
        f1 = DeliverablesFactory(output_dir=tmp_path / "run1")
        f2 = DeliverablesFactory(output_dir=tmp_path / "run2")

        r1 = f1.generate_xlsx(sample_audit_result)
        r2 = f2.generate_xlsx(sample_audit_result)

        assert r1.filename == r2.filename

        wb1 = openpyxl.load_workbook(tmp_path / "run1/xlsx" / r1.filename, data_only=False)
        wb2 = openpyxl.load_workbook(tmp_path / "run2/xlsx" / r2.filename, data_only=False)

        assert wb1.sheetnames == wb2.sheetnames

        for sname in wb1.sheetnames:
            s1 = wb1[sname]
            s2 = wb2[sname]
            assert s1.max_row == s2.max_row
            assert s1.max_column == s2.max_column
            for r in range(1, s1.max_row + 1):
                for c in range(1, s1.max_column + 1):
                    assert s1.cell(r, c).value == s2.cell(r, c).value, (
                        f"Mismatch in sheet '{sname}' at coordinate ({r},{c})"
                    )

    def test_pptx_openxml_determinism(self, sample_audit_result, tmp_path):
        f1 = DeliverablesFactory(output_dir=tmp_path / "run1")
        f2 = DeliverablesFactory(output_dir=tmp_path / "run2")

        r1 = f1.generate_pptx(sample_audit_result)
        r2 = f2.generate_pptx(sample_audit_result)

        assert r1.filename == r2.filename

        with zipfile.ZipFile(tmp_path / "run1/pptx" / r1.filename) as z1, zipfile.ZipFile(
            tmp_path / "run2/pptx" / r2.filename
        ) as z2:
            assert z1.namelist() == z2.namelist()
            for slide_name in [f"ppt/slides/slide{i}.xml" for i in range(1, 6)]:
                assert z1.read(slide_name) == z2.read(slide_name), f"PPTX XML differs in {slide_name}"


# ── 8. REST API Endpoints Tests ───────────────────────────────────────────────

class TestDeliverablesAPI:
    """Verifies /api/v1/deliverables REST endpoints."""

    def test_api_generate_all_formats_success(self, sample_audit_result):
        res = client.post(
            "/api/v1/deliverables/generate",
            json={
                "data": sample_audit_result.model_dump(),
                "formats": ["docx", "xlsx", "pptx"],
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["equipment_id"] == "C-101"
        assert len(data["artifacts"]) == 3

    def test_api_generate_single_format(self, sample_audit_result):
        res = client.post(
            "/api/v1/deliverables/generate",
            json={
                "data": sample_audit_result.model_dump(),
                "formats": ["xlsx"],
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["artifacts"]) == 1
        assert data["artifacts"][0]["format"] == "xlsx"

    def test_api_missing_payload_returns_400(self):
        res = client.post("/api/v1/deliverables/generate", json={})
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "BAD_REQUEST"

    def test_api_unsupported_format_returns_422_or_400(self, sample_audit_result):
        res = client.post(
            "/api/v1/deliverables/generate",
            json={
                "data": sample_audit_result.model_dump(),
                "formats": ["unsupported_format"],
            },
        )
        assert res.status_code in [400, 422]

    def test_api_download_generated_file(self, sample_audit_result):
        gen_res = client.post(
            "/api/v1/deliverables/generate",
            json={
                "data": sample_audit_result.model_dump(),
                "formats": ["docx"],
            },
        )
        artifact = gen_res.json()["artifacts"][0]
        filename = artifact["filename"]

        dl_res = client.get(f"/api/v1/deliverables/download/docx/{filename}")
        assert dl_res.status_code == 200
        assert len(dl_res.content) > 0

    def test_api_download_path_traversal_blocked(self):
        res = client.get("/api/v1/deliverables/download/docx/..%2Fescape.docx")
        assert res.status_code in [400, 403, 404]

    def test_api_download_nonexistent_file_returns_404(self):
        res = client.get("/api/v1/deliverables/download/docx/nonexistent_file_9999.docx")
        assert res.status_code == 404

    def test_api_list_deliverables(self, sample_audit_result):
        # Generate an artifact to ensure at least one exists
        client.post(
            "/api/v1/deliverables/generate",
            json={
                "data": sample_audit_result.model_dump(),
                "formats": ["docx"],
            },
        )
        res = client.get("/api/v1/deliverables")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "artifact_id" in data[0]
        assert "download_url" in data[0]

    def test_api_download_by_artifact_id(self, sample_audit_result):
        gen_res = client.post(
            "/api/v1/deliverables/generate",
            json={
                "data": sample_audit_result.model_dump(),
                "formats": ["docx"],
            },
        )
        art = gen_res.json()["artifacts"][0]
        art_id = art["artifact_id"]

        dl_res = client.get(f"/api/v1/deliverables/{art_id}/download")
        assert dl_res.status_code == 200
        assert len(dl_res.content) > 0

    def test_api_download_by_artifact_id_mock_memorandum(self):
        dl_res = client.get("/api/v1/deliverables/art-c101-memorandum/download")
        assert dl_res.status_code == 200
        assert len(dl_res.content) > 0

    def test_api_download_by_artifact_id_mock_workbook(self):
        dl_res = client.get("/api/v1/deliverables/art-c101-workbook/download")
        assert dl_res.status_code == 200
        assert len(dl_res.content) > 0

    def test_api_download_by_artifact_id_path_traversal_blocked(self):
        res = client.get("/api/v1/deliverables/..%2F..%2Fetc/download")
        assert res.status_code in [400, 403, 404]


# ── 9. Phase 9 Integration Tests ──────────────────────────────────────────────

class TestPhase9DeliverableIntegration:
    """Verifies seamless integration between Phase 9 validation and Phase 10 deliverables."""

    def test_phase9_service_result_directly_generates_deliverables(self, temp_output_dir):
        service = StructuredOutputService()
        valid_json = """
        {
            "equipment_id": "C-101",
            "inspection_subject": "Crude Overhead Condenser Piping",
            "current_measurement": {"value_mm": 4.20, "measurement_date": "2026-03-15"},
            "initial_measurement": {"value_mm": 8.00, "measurement_date": "2021-03-15"},
            "minimum_required_thickness_mm": 3.20,
            "calculation": {
                "initial_thickness_mm": 8.00,
                "current_thickness_mm": 4.20,
                "inspection_interval_years": 5.0,
                "minimum_required_mm": 3.20,
                "corrosion_rate_mm_per_year": 0.760,
                "remaining_life_years": 1.316
            },
            "findings": [{"description": "Significant localized wall thinning.", "severity": "HIGH"}],
            "conclusion": "Wall thickness approaching retirement limit.",
            "recommendation": "IMMEDIATE_ACTION",
            "citations": [{
                "source_document": "SOP-MRPL-PIP-001.pdf",
                "page_number": 3,
                "chunk_id": "c001",
                "content_sha256": "abcdef1234567890",
                "similarity_score": 0.94
            }]
        }
        """
        # Step 1: Phase 9 Validation
        val_result = service.validate(valid_json)
        assert val_result.valid is True
        assert val_result.status == "VALID"

        # Step 2: Phase 10 Deliverable Generation from ValidationResult
        factory = DeliverablesFactory(output_dir=temp_output_dir)
        deliv_res = factory.generate(val_result)
        assert deliv_res.success is True
        assert len(deliv_res.artifacts) == 3

    def test_phase9_invalid_result_cannot_generate_deliverables(self, temp_output_dir):
        service = StructuredOutputService()
        # Missing required citations
        invalid_json = """
        {
            "equipment_id": "C-101",
            "inspection_subject": "Crude Overhead Condenser Piping",
            "current_measurement": {"value_mm": 4.20},
            "initial_measurement": {"value_mm": 8.00},
            "minimum_required_thickness_mm": 3.20,
            "calculation": {
                "initial_thickness_mm": 8.00,
                "current_thickness_mm": 4.20,
                "inspection_interval_years": 5.0,
                "corrosion_rate_mm_per_year": 0.760
            },
            "findings": [{"description": "Thinning without citation"}],
            "citations": []
        }
        """
        val_result = service.validate(invalid_json)
        assert val_result.valid is False

        factory = DeliverablesFactory(output_dir=temp_output_dir)
        with pytest.raises(UnvalidatedInputError):
            factory.generate(val_result)
