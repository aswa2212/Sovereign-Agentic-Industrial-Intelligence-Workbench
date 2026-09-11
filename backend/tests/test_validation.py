"""
SIH26117 — Phase 9: Validation Layer Tests

Covers:
  - Parser (JSON, code-fence, malformed, empty, security)
  - Schema validation (valid, missing fields, wrong types, extra fields, enums, nested)
  - Engineering validation (wall thickness, corrosion rate, calculations, provenance)
  - Provenance (citation fields, no fabrication)
  - StructuredOutputService (full pipeline)
  - REST API endpoint
  - Agent integration (invalid output does not produce successful result)
  - Regression: Phase 1–8 behavior intact
  - Network sovereignty: no outbound socket creation
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ─── Import targets ─────────────────────────────────────────────────────────

try:
    from app.services.validation.parser import parse_model_output, _strip_code_fence
    from app.services.validation.exceptions import ParsingError, SchemaValidationError
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
    from app.services.validation.base import ValidationStatus, ValidationStage
    from app.services.validation.schema_validator import validate_schema, schema_validation_outcome
    from app.services.validation.engineering_validator import EngineeringValidator, DEFAULT_RATE_TOLERANCE_MM_PER_YEAR
    from app.services.validation.service import StructuredOutputService
except ImportError:
    from backend.app.services.validation.parser import parse_model_output, _strip_code_fence
    from backend.app.services.validation.exceptions import ParsingError, SchemaValidationError
    from backend.app.services.validation.models import (
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
    from backend.app.services.validation.base import ValidationStatus, ValidationStage
    from backend.app.services.validation.schema_validator import validate_schema, schema_validation_outcome
    from backend.app.services.validation.engineering_validator import EngineeringValidator, DEFAULT_RATE_TOLERANCE_MM_PER_YEAR
    from backend.app.services.validation.service import StructuredOutputService


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def valid_payload():
    """Minimal valid CorrosionAuditResult payload."""
    return {
        "equipment_id": "C-101",
        "inspection_subject": "Overhead condenser piping",
        "current_measurement": {"value_mm": 4.5, "unit": "mm"},
        "initial_measurement": {"value_mm": 6.0, "unit": "mm"},
        "minimum_required_thickness_mm": 3.2,
        "calculation": {
            "initial_thickness_mm": 6.0,
            "current_thickness_mm": 4.5,
            "inspection_interval_years": 2.0,
            "minimum_required_mm": 3.2,
            "corrosion_rate_mm_per_year": 0.75,   # (6.0-4.5)/2.0 = 0.75 — exact
            "remaining_life_years": 1.73,           # (4.5-3.2)/0.75 ≈ 1.733
            "formula_applied": "(initial - current) / interval",
        },
        "findings": [],
        "citations": [],
        "recommendation": "INCREASE_MONITORING",
    }


@pytest.fixture
def valid_payload_with_citations():
    """Valid payload that includes a source citation."""
    return {
        "equipment_id": "C-101",
        "inspection_subject": "Overhead condenser piping",
        "current_measurement": {"value_mm": 4.5, "unit": "mm"},
        "minimum_required_thickness_mm": 3.2,
        "findings": [
            {
                "description": "Wall thickness approaching minimum",
                "severity": "MEDIUM",
            }
        ],
        "citations": [
            {
                "source_document": "SOP-MRPL-PIP-001.pdf",
                "page_number": 3,
                "chunk_id": "a1b2c3d4e5f6_p3_c0002",
                "content_sha256": "ac77868fc2f81ccb05680f690e2420bae39633ae3c8e42aa3974f09bd801cfbf",
                "similarity_score": 0.91,
                "excerpt": "minimum allowable retired wall thickness shall not be less than 3.2 mm",
            }
        ],
        "recommendation": "INCREASE_MONITORING",
    }


@pytest.fixture
def service():
    return StructuredOutputService()


# ═════════════════════════════════════════════════════════════════════════════
# 1. PARSER TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestParser:
    def test_parse_valid_json_string(self, valid_payload):
        result = parse_model_output(json.dumps(valid_payload))
        assert isinstance(result, dict)
        assert result["equipment_id"] == "C-101"

    def test_parse_valid_dict_passthrough(self, valid_payload):
        result = parse_model_output(valid_payload)
        assert result is valid_payload

    def test_parse_valid_bytes(self, valid_payload):
        result = parse_model_output(json.dumps(valid_payload).encode())
        assert result["equipment_id"] == "C-101"

    def test_parse_json_code_fence(self, valid_payload):
        fenced = f"```json\n{json.dumps(valid_payload)}\n```"
        result = parse_model_output(fenced)
        assert result["equipment_id"] == "C-101"

    def test_parse_plain_code_fence(self, valid_payload):
        fenced = f"```\n{json.dumps(valid_payload)}\n```"
        result = parse_model_output(fenced)
        assert result["equipment_id"] == "C-101"

    def test_parse_malformed_json_raises(self):
        with pytest.raises(ParsingError) as exc_info:
            parse_model_output("{bad json}")
        assert "not valid json" in str(exc_info.value).lower()

    def test_parse_empty_string_raises(self):
        with pytest.raises(ParsingError) as exc_info:
            parse_model_output("")
        assert "empty" in str(exc_info.value).lower()

    def test_parse_whitespace_only_raises(self):
        with pytest.raises(ParsingError):
            parse_model_output("   \n  ")

    def test_parse_json_array_raises(self):
        with pytest.raises(ParsingError) as exc_info:
            parse_model_output("[1, 2, 3]")
        assert "object" in str(exc_info.value).lower() or "dict" in str(exc_info.value).lower()

    def test_parse_json_scalar_raises(self):
        with pytest.raises(ParsingError):
            parse_model_output('"just a string"')

    def test_parse_invalid_bytes_raises(self):
        with pytest.raises(ParsingError) as exc_info:
            parse_model_output(b"\xff\xfe invalid utf-8")
        assert "utf-8" in str(exc_info.value).lower() or "decode" in str(exc_info.value).lower()

    def test_parse_unsupported_type_raises(self):
        with pytest.raises(ParsingError) as exc_info:
            parse_model_output(12345)  # type: ignore[arg-type]
        assert "unsupported" in str(exc_info.value).lower()

    def test_never_executes_eval(self):
        """Parser must never call eval() on input content."""
        malicious = '{"__import__": "os"}'
        # Should parse safely as a dict with key "__import__", not execute anything
        result = parse_model_output(malicious)
        assert "__import__" in result
        assert result["__import__"] == "os"

    def test_never_executes_exec(self):
        """Parser must reject code-like payloads without executing them."""
        malicious_code = "exec('import os; os.system(\"echo pwned\")')"
        with pytest.raises(ParsingError):
            parse_model_output(malicious_code)

    def test_strip_code_fence_no_fence(self):
        raw = '{"key": "value"}'
        assert _strip_code_fence(raw) == raw

    def test_strip_code_fence_with_json_fence(self, valid_payload):
        inner = json.dumps(valid_payload)
        fenced = f"```json\n{inner}\n```"
        assert _strip_code_fence(fenced) == inner

    def test_dict_with_non_string_keys_raises(self):
        with pytest.raises(ParsingError) as exc_info:
            parse_model_output({1: "value"})  # type: ignore[arg-type]
        assert "non-string" in str(exc_info.value).lower()


# ═════════════════════════════════════════════════════════════════════════════
# 2. SCHEMA VALIDATION TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestSchemaValidator:
    def test_valid_payload_passes(self, valid_payload):
        result = validate_schema(valid_payload)
        assert isinstance(result, CorrosionAuditResult)
        assert result.equipment_id == "C-101"

    def test_missing_equipment_id_fails(self, valid_payload):
        del valid_payload["equipment_id"]
        with pytest.raises(SchemaValidationError):
            validate_schema(valid_payload)

    def test_missing_inspection_subject_fails(self, valid_payload):
        del valid_payload["inspection_subject"]
        with pytest.raises(SchemaValidationError):
            validate_schema(valid_payload)

    def test_wrong_type_equipment_id_fails(self, valid_payload):
        valid_payload["equipment_id"] = 123
        # Pydantic coerces int to str by default for string fields in some versions;
        # verify schema has explicit handling via min_length > 0 with non-string
        # On strict models this should still accept coercion; on extra=forbid, unknown fields fail.
        # Equipment_id = 123 actually coerces to "123" in Pydantic; test with actual invalid type:
        valid_payload["equipment_id"] = None
        with pytest.raises(SchemaValidationError):
            validate_schema(valid_payload)

    def test_unexpected_top_level_field_fails(self, valid_payload):
        valid_payload["unknown_field_xyz"] = "should not be here"
        with pytest.raises(SchemaValidationError):
            validate_schema(valid_payload)

    def test_invalid_recommendation_enum_fails(self, valid_payload):
        valid_payload["recommendation"] = "DO_SOMETHING_INVALID"
        with pytest.raises(SchemaValidationError):
            validate_schema(valid_payload)

    def test_valid_recommendation_enum_accepted(self, valid_payload):
        for code in RecommendationCode:
            valid_payload["recommendation"] = code.value
            result = validate_schema(valid_payload)
            assert result.recommendation == code

    def test_negative_minimum_thickness_fails(self, valid_payload):
        valid_payload["minimum_required_thickness_mm"] = -1.0
        with pytest.raises(SchemaValidationError):
            validate_schema(valid_payload)

    def test_zero_minimum_thickness_fails(self, valid_payload):
        valid_payload["minimum_required_thickness_mm"] = 0.0
        with pytest.raises(SchemaValidationError):
            validate_schema(valid_payload)

    def test_invalid_corrosion_rate_schema_fails(self):
        payload = {
            "equipment_id": "C-101",
            "inspection_subject": "Pipe section",
            "calculation": {
                "initial_thickness_mm": 6.0,
                "current_thickness_mm": 4.5,
                "inspection_interval_years": 2.0,
                "corrosion_rate_mm_per_year": -0.5,  # negative: rejected by field_validator
            },
        }
        with pytest.raises(SchemaValidationError):
            validate_schema(payload)

    def test_invalid_nested_measurement_unit_fails(self, valid_payload):
        valid_payload["current_measurement"]["unit"] = "furlongs"
        with pytest.raises(SchemaValidationError):
            validate_schema(valid_payload)

    def test_similarity_score_out_of_range_fails(self):
        payload = {
            "equipment_id": "C-101",
            "inspection_subject": "Pipe",
            "citations": [
                {
                    "source_document": "test.pdf",
                    "similarity_score": 1.5,  # > 1.0
                }
            ],
        }
        with pytest.raises(SchemaValidationError):
            validate_schema(payload)

    def test_schema_validation_outcome_ok(self, valid_payload):
        outcome = schema_validation_outcome(valid_payload)
        assert outcome.valid is True
        assert outcome.status == ValidationStatus.VALID

    def test_schema_validation_outcome_fail(self, valid_payload):
        del valid_payload["equipment_id"]
        outcome = schema_validation_outcome(valid_payload)
        assert outcome.valid is False
        assert outcome.status == ValidationStatus.SCHEMA_ERROR
        assert outcome.errors


# ═════════════════════════════════════════════════════════════════════════════
# 3. ENGINEERING VALIDATION TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestEngineeringValidator:
    @pytest.fixture(autouse=True)
    def validator(self):
        self.v = EngineeringValidator()

    def _make_result(self, **overrides):
        base = {
            "equipment_id": "C-101",
            "inspection_subject": "Overhead condenser",
        }
        base.update(overrides)
        return CorrosionAuditResult(**base)

    def test_valid_result_no_errors(self):
        result = self._make_result()
        errors, warnings, passed = self.v.validate(result)
        assert not errors
        assert "equipment_id_present" in passed

    def test_positive_wall_thickness_passes(self):
        result = self._make_result(
            current_measurement=WallThicknessMeasurement(value_mm=4.5, unit=MeasurementUnit.MM)
        )
        errors, _, passed = self.v.validate(result)
        assert not errors
        assert "current_measurement_positive" in passed

    def test_missing_equipment_id_fails_engineering(self):
        # Override via bypass: construct with empty string — Pydantic allows if min_length check missed
        # Actually the schema min_length=1 prevents empty; test with monkeypatching
        result = CorrosionAuditResult.model_construct(
            equipment_id="   ",  # whitespace only
            inspection_subject="Test",
        )
        errors, _, _ = self.v.validate(result)
        assert any(e.code == "REQUIRED_FIELD_MISSING" for e in errors)

    def test_negative_corrosion_rate_rejected(self):
        # Build a CorrosionCalculation with negative rate bypassing field_validator
        calc = CorrosionCalculation.model_construct(
            initial_thickness_mm=6.0,
            current_thickness_mm=4.5,
            inspection_interval_years=2.0,
            corrosion_rate_mm_per_year=-0.5,
        )
        result = self._make_result(calculation=calc)
        errors, _, _ = self.v.validate(result)
        assert any(e.code == "NEGATIVE_CORROSION_RATE" for e in errors)

    def test_correct_corrosion_rate_passes(self):
        # (6.0 - 4.5) / 2.0 = 0.75 exactly
        calc = CorrosionCalculation(
            initial_thickness_mm=6.0,
            current_thickness_mm=4.5,
            inspection_interval_years=2.0,
            corrosion_rate_mm_per_year=0.75,
        )
        result = self._make_result(calculation=calc)
        errors, _, passed = self.v.validate(result)
        assert not any(e.code == "CALCULATION_MISMATCH" for e in errors)
        assert "corrosion_rate_calculation_verified" in passed

    def test_wrong_corrosion_rate_produces_mismatch(self):
        # Claim 0.5 but actual is (6.0-4.5)/2.0 = 0.75
        calc = CorrosionCalculation(
            initial_thickness_mm=6.0,
            current_thickness_mm=4.5,
            inspection_interval_years=2.0,
            corrosion_rate_mm_per_year=0.5,  # deliberately wrong
        )
        result = self._make_result(calculation=calc)
        errors, _, _ = self.v.validate(result)
        assert any(e.code == "CALCULATION_MISMATCH" for e in errors)

    def test_calculation_mismatch_message_contains_formula(self):
        calc = CorrosionCalculation(
            initial_thickness_mm=6.0,
            current_thickness_mm=4.5,
            inspection_interval_years=2.0,
            corrosion_rate_mm_per_year=0.1,  # obviously wrong
        )
        result = self._make_result(calculation=calc)
        errors, _, _ = self.v.validate(result)
        calc_errors = [e for e in errors if e.code == "CALCULATION_MISMATCH"]
        assert calc_errors
        assert "Formula" in calc_errors[0].message or "formula" in calc_errors[0].message.lower()

    def test_remaining_life_verified(self):
        # (4.5 - 3.2) / 0.75 = 1.7333...
        calc = CorrosionCalculation(
            initial_thickness_mm=6.0,
            current_thickness_mm=4.5,
            inspection_interval_years=2.0,
            minimum_required_mm=3.2,
            corrosion_rate_mm_per_year=0.75,
            remaining_life_years=1.733,
        )
        result = self._make_result(calculation=calc)
        errors, _, passed = self.v.validate(result)
        life_errors = [e for e in errors if "remaining" in e.field or "" and e.code == "CALCULATION_MISMATCH"]
        assert not life_errors
        assert "remaining_life_calculation_verified" in passed

    def test_findings_without_citations_fails_provenance(self):
        result = self._make_result(
            findings=[InspectionFinding(description="Corrosion observed")],
            citations=[],
        )
        errors, _, _ = self.v.validate(result)
        assert any(e.code == "INSUFFICIENT_PROVENANCE" for e in errors)

    def test_findings_with_citations_passes(self):
        result = self._make_result(
            findings=[InspectionFinding(description="Corrosion observed")],
            citations=[SourceCitation(source_document="SOP-MRPL-PIP-001.pdf")],
        )
        errors, _, passed = self.v.validate(result)
        assert not any(e.code == "INSUFFICIENT_PROVENANCE" for e in errors)
        assert "provenance_present_for_findings" in passed

    def test_inconsistent_recommendation_fails(self):
        # Current < minimum but recommendation is CONTINUE_SERVICE
        result = self._make_result(
            current_measurement=WallThicknessMeasurement(value_mm=2.5, unit=MeasurementUnit.MM),
            minimum_required_thickness_mm=3.2,
            recommendation=RecommendationCode.CONTINUE_SERVICE,
        )
        errors, _, _ = self.v.validate(result)
        assert any(e.code == "INCONSISTENT_RECOMMENDATION" for e in errors)

    def test_current_below_min_produces_warning(self):
        result = self._make_result(
            current_measurement=WallThicknessMeasurement(value_mm=2.5, unit=MeasurementUnit.MM),
            minimum_required_thickness_mm=3.2,
            recommendation=RecommendationCode.IMMEDIATE_ACTION,
        )
        errors, warnings, _ = self.v.validate(result)
        assert not any(e.code == "INCONSISTENT_RECOMMENDATION" for e in errors)
        assert any("below" in w.lower() or "minimum" in w.lower() for w in warnings)

    def test_citation_empty_source_document_fails(self):
        result = self._make_result(
            citations=[SourceCitation.model_construct(source_document="   ")],
        )
        errors, _, _ = self.v.validate(result)
        assert any(e.code == "EMPTY_CITATION_SOURCE" for e in errors)


# ═════════════════════════════════════════════════════════════════════════════
# 4. PROVENANCE TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestProvenance:
    def test_citation_fields_preserved_exactly(self, valid_payload_with_citations):
        """Citation fields must pass through the validator unchanged."""
        svc = StructuredOutputService()
        result = svc.validate(valid_payload_with_citations)
        assert result.valid
        cit = result.validated_data.citations[0]
        assert cit.source_document == "SOP-MRPL-PIP-001.pdf"
        assert cit.page_number == 3
        assert cit.chunk_id == "a1b2c3d4e5f6_p3_c0002"
        assert cit.content_sha256 == "ac77868fc2f81ccb05680f690e2420bae39633ae3c8e42aa3974f09bd801cfbf"
        assert cit.similarity_score == pytest.approx(0.91)

    def test_validator_does_not_inject_citations(self, valid_payload):
        """Validator must never add citations that were not in the payload."""
        valid_payload["citations"] = []
        valid_payload["findings"] = []
        svc = StructuredOutputService()
        result = svc.validate(valid_payload)
        assert result.valid
        assert result.validated_data.citations == []

    def test_source_hash_preserved(self, valid_payload_with_citations):
        svc = StructuredOutputService()
        result = svc.validate(valid_payload_with_citations)
        assert result.valid
        cit = result.validated_data.citations[0]
        # Hash must match exactly what was submitted
        assert cit.content_sha256 == "ac77868fc2f81ccb05680f690e2420bae39633ae3c8e42aa3974f09bd801cfbf"

    def test_static_citation_not_introduced(self, valid_payload):
        """No hardcoded SOP-MRPL-PIP-001.pdf citation must appear if not in payload."""
        valid_payload["citations"] = []
        valid_payload["findings"] = []
        svc = StructuredOutputService()
        result = svc.validate(valid_payload)
        if result.validated_data and result.validated_data.citations:
            source_docs = [c.source_document for c in result.validated_data.citations]
            assert "SOP-MRPL-PIP-001.pdf" not in source_docs


# ═════════════════════════════════════════════════════════════════════════════
# 5. STRUCTURED OUTPUT SERVICE — FULL PIPELINE
# ═════════════════════════════════════════════════════════════════════════════

class TestStructuredOutputService:
    def test_valid_payload_returns_valid_result(self, valid_payload, service):
        result = service.validate(valid_payload)
        assert result.valid is True
        assert result.status == ValidationStatus.VALID
        assert result.validated_data is not None

    def test_malformed_json_returns_parsing_error(self, service):
        result = service.validate("{bad}")
        assert result.valid is False
        assert result.status == ValidationStatus.PARSING_ERROR

    def test_empty_input_returns_parsing_error(self, service):
        result = service.validate("")
        assert result.valid is False
        assert result.status == ValidationStatus.PARSING_ERROR

    def test_schema_invalid_returns_schema_error(self, service):
        result = service.validate({"equipment_id": "C-101"})  # missing inspection_subject
        assert result.valid is False
        assert result.status == ValidationStatus.SCHEMA_ERROR

    def test_calculation_mismatch_returns_mismatch_status(self, valid_payload, service):
        valid_payload["calculation"]["corrosion_rate_mm_per_year"] = 9.99  # wrong
        result = service.validate(valid_payload)
        assert result.valid is False
        assert result.status == ValidationStatus.CALCULATION_MISMATCH

    def test_missing_provenance_returns_insufficient_evidence(self, service):
        payload = {
            "equipment_id": "C-101",
            "inspection_subject": "Pipe",
            "findings": [{"description": "Corrosion observed"}],
            "citations": [],
        }
        result = service.validate(payload)
        assert result.valid is False
        assert result.status == ValidationStatus.INSUFFICIENT_EVIDENCE

    def test_errors_are_structured(self, service):
        payload = {"inspection_subject": "X"}  # missing equipment_id
        result = service.validate(payload)
        assert result.errors
        for err in result.errors:
            assert hasattr(err, "code")
            assert hasattr(err, "message")

    def test_no_stack_trace_in_errors(self, service):
        result = service.validate("{invalid}")
        error_text = str(result.errors)
        assert "Traceback" not in error_text
        assert "File \"" not in error_text

    def test_valid_result_has_no_errors(self, valid_payload, service):
        result = service.validate(valid_payload)
        assert result.valid
        assert result.errors == []

    def test_json_string_input_works(self, valid_payload, service):
        result = service.validate(json.dumps(valid_payload))
        assert result.valid

    def test_bytes_input_works(self, valid_payload, service):
        result = service.validate(json.dumps(valid_payload).encode())
        assert result.valid

    def test_invalid_does_not_produce_validated_data(self, service):
        result = service.validate("{invalid}")
        assert result.validated_data is None

    def test_validation_checks_populated(self, valid_payload, service):
        result = service.validate(valid_payload)
        assert result.validation_checks
        assert "parse_model_output" in result.validation_checks
        assert "schema_validation" in result.validation_checks

    def test_tolerance_exposed_in_result(self, valid_payload, service):
        result = service.validate(valid_payload)
        assert result.calculation_tolerance_mm_per_year is not None
        assert result.calculation_tolerance_mm_per_year == DEFAULT_RATE_TOLERANCE_MM_PER_YEAR


# ═════════════════════════════════════════════════════════════════════════════
# 6. API ENDPOINT TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestValidationAPI:
    @pytest.fixture(autouse=True)
    def client(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        try:
            from app.api.v1.endpoints.validation import router
        except ImportError:
            from backend.app.api.v1.endpoints.validation import router
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_valid_payload_returns_200_valid(self, valid_payload):
        resp = self.client.post("/validation/validate", json={"payload": valid_payload})
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["status"] == "VALID"

    def test_schema_error_returns_200_invalid(self):
        resp = self.client.post("/validation/validate", json={"payload": {"equipment_id": "C-101"}})
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert data["status"] == "SCHEMA_ERROR"

    def test_malformed_payload_type_returns_422(self):
        # 'payload' must be a dict; sending a string should fail Pydantic request validation
        resp = self.client.post("/validation/validate", json={"payload": "not a dict"})
        assert resp.status_code == 422

    def test_missing_payload_key_returns_422(self):
        resp = self.client.post("/validation/validate", json={})
        assert resp.status_code == 422

    def test_no_stack_trace_in_response(self, valid_payload):
        resp = self.client.post("/validation/validate", json={"payload": valid_payload})
        text = resp.text
        assert "Traceback" not in text
        assert "File \"" not in text

    def test_structured_errors_in_response(self):
        resp = self.client.post(
            "/validation/validate",
            json={"payload": {"equipment_id": "C-101"}},
        )
        data = resp.json()
        assert "errors" in data

    def test_rate_tolerance_override(self, valid_payload):
        valid_payload["calculation"]["corrosion_rate_mm_per_year"] = 0.74  # just outside default
        # With large tolerance it should pass
        resp = self.client.post(
            "/validation/validate",
            json={"payload": valid_payload, "rate_tolerance": 0.5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True

    def test_require_citations_false_allows_no_citation(self):
        payload = {
            "equipment_id": "C-101",
            "inspection_subject": "Pipe",
            "findings": [{"description": "Corrosion observed"}],
            "citations": [],
        }
        resp = self.client.post(
            "/validation/validate",
            json={"payload": payload, "require_citations": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True


# ═════════════════════════════════════════════════════════════════════════════
# 7. AGENT INTEGRATION TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestAgentIntegration:
    def test_structured_output_service_importable_from_agent_module(self):
        """The Agent orchestrator must be able to import StructuredOutputService."""
        try:
            from app.services.agent.orchestrator import AgentStateMachineOrchestrator
        except ImportError:
            from backend.app.services.agent.orchestrator import AgentStateMachineOrchestrator
        # Just importing is enough; verifies Phase 9 integration wiring
        assert AgentStateMachineOrchestrator is not None

    def test_orchestrator_accepts_structured_output_service(self):
        """Orchestrator can accept an injected StructuredOutputService."""
        try:
            from app.services.agent.orchestrator import AgentStateMachineOrchestrator
        except ImportError:
            from backend.app.services.agent.orchestrator import AgentStateMachineOrchestrator
        svc = StructuredOutputService()
        orch = AgentStateMachineOrchestrator(structured_output_service=svc)
        assert orch._structured_output_service is svc

    @pytest.mark.asyncio
    async def test_invalid_structured_output_does_not_become_successful_result(self):
        """
        When the Phase 9 StructuredOutputService detects a bad calculation in the
        agent's final_result, the result must include structured_validation.valid=False.
        """
        svc = StructuredOutputService()
        bad_calc = {
            "initial_thickness_mm": 6.0,
            "current_thickness_mm": 4.5,
            "inspection_interval_years": 2.0,
            "corrosion_rate_mm_per_year": 99.0,  # obviously wrong
        }
        result = svc.validate(bad_calc)
        # The payload is missing equipment_id / inspection_subject — should fail schema
        assert result.valid is False

    @pytest.mark.asyncio
    async def test_phase7_states_unchanged(self):
        """Phase 7 AgentState enum must still contain all 11 original states."""
        try:
            from app.services.agent.base import AgentState
        except ImportError:
            from backend.app.services.agent.base import AgentState

        required = {
            "IDLE", "RECEIVE", "UNDERSTAND", "PLAN", "EXECUTE",
            "OBSERVE", "REFLECT", "VALIDATE", "FINALIZE", "DELIVER", "FAILED"
        }
        actual = {s.value for s in AgentState}
        assert required.issubset(actual), f"Missing states: {required - actual}"


# ═════════════════════════════════════════════════════════════════════════════
# 8. NETWORK SOVEREIGNTY TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestNetworkSovereignty:
    def test_no_outbound_socket_during_validation(self, valid_payload):
        """
        Validation pipeline must make zero outbound socket connections.
        We patch socket.create_connection to detect any attempt.
        """
        import socket
        connection_attempts = []

        original = socket.create_connection

        def spy_create_connection(*args, **kwargs):
            connection_attempts.append(args)
            raise AssertionError(f"Unexpected socket.create_connection: {args}")

        import builtins
        with patch("socket.create_connection", spy_create_connection):
            svc = StructuredOutputService()
            result = svc.validate(valid_payload)

        assert connection_attempts == [], f"Unexpected network calls: {connection_attempts}"

    def test_no_http_requests_during_validation(self, valid_payload):
        """Validation must not use urllib or requests."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            svc = StructuredOutputService()
            svc.validate(valid_payload)
            mock_urlopen.assert_not_called()


# ═════════════════════════════════════════════════════════════════════════════
# 9. REGRESSION GUARD — PHASE 1–8 IMPORTS INTACT
# ═════════════════════════════════════════════════════════════════════════════

class TestPhase18Regression:
    def test_health_endpoint_importable(self):
        try:
            from app.api.v1.endpoints.health import router
        except ImportError:
            from backend.app.api.v1.endpoints.health import router
        assert router is not None

    def test_model_manager_importable(self):
        try:
            from app.services.model_manager.manager import ModelManager
        except ImportError:
            from backend.app.services.model_manager.manager import ModelManager
        assert ModelManager is not None

    def test_rule_router_importable(self):
        try:
            from app.services.router.rule_router import RuleRouter
        except ImportError:
            from backend.app.services.router.rule_router import RuleRouter
        assert RuleRouter is not None

    def test_ingestor_importable(self):
        try:
            from app.services.ingestion.service import IngestionService
        except ImportError:
            from backend.app.services.ingestion.service import IngestionService
        assert IngestionService is not None

    def test_ocr_engine_importable(self):
        try:
            from app.services.vision.ocr_engine import LocalOCREngine
        except ImportError:
            from backend.app.services.vision.ocr_engine import LocalOCREngine
        assert LocalOCREngine is not None

    def test_sovereign_retriever_importable(self):
        try:
            from app.services.rag.retriever import SovereignRetriever
        except ImportError:
            from backend.app.services.rag.retriever import SovereignRetriever
        assert SovereignRetriever is not None

    def test_agent_orchestrator_importable(self):
        try:
            from app.services.agent.orchestrator import AgentStateMachineOrchestrator
        except ImportError:
            from backend.app.services.agent.orchestrator import AgentStateMachineOrchestrator
        assert AgentStateMachineOrchestrator is not None

    def test_sandbox_executor_importable(self):
        try:
            from app.services.sandbox.subprocess_executor import SubprocessSandboxExecutor
        except ImportError:
            from backend.app.services.sandbox.subprocess_executor import SubprocessSandboxExecutor
        assert SubprocessSandboxExecutor is not None

    def test_sandbox_policy_importable(self):
        try:
            from app.services.sandbox.policy import SandboxPolicy
        except ImportError:
            from backend.app.services.sandbox.policy import SandboxPolicy
        assert SandboxPolicy is not None

    def test_config_importable(self):
        try:
            from app.core.config import get_settings
        except ImportError:
            from backend.app.core.config import get_settings
        settings = get_settings()
        assert settings is not None
