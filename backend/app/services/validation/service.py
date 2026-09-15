"""
SIH26117 — Phase 9: Structured Output Service

The single public boundary for the Phase 9 validation pipeline.

Pipeline:
    raw input (str | bytes | dict)
        ↓
    Parser (safe JSON / code-fence stripping)
        ↓
    Schema Validator (Pydantic CorrosionAuditResult)
        ↓
    Engineering Validator (deterministic business checks + calculation verification)
        ↓
    ValidationResult

INVARIANTS:
- Never calls LLM / Ollama / external APIs.
- Never fabricates citations or calculations.
- Fails closed: any pipeline stage failure returns a structured INVALID result.
- Internal stack traces are never exposed in the returned ValidationResult.
- The service is callable by the Phase 7 Agent but does NOT depend on it.
  Dependency direction: Agent -> StructuredOutputService (not the reverse).
"""

import logging
from typing import Any, Union

try:
    from app.services.validation.base import ValidationStatus, ValidationStage
    from app.services.validation.engineering_validator import (
        DEFAULT_RATE_TOLERANCE_MM_PER_YEAR,
        EngineeringValidator,
    )
    from app.services.validation.exceptions import ParsingError, SchemaValidationError
    from app.services.validation.models import (
        CorrosionAuditResult,
        CorrosionCalculation,
        ValidationErrorDetail,
        ValidationResult,
    )
    from app.services.validation.parser import parse_model_output
    from app.services.validation.schema_validator import validate_schema
except ImportError:
    from backend.app.services.validation.base import ValidationStatus, ValidationStage
    from backend.app.services.validation.engineering_validator import (
        DEFAULT_RATE_TOLERANCE_MM_PER_YEAR,
        EngineeringValidator,
    )
    from backend.app.services.validation.exceptions import ParsingError, SchemaValidationError
    from backend.app.services.validation.models import (
        CorrosionAuditResult,
        CorrosionCalculation,
        ValidationErrorDetail,
        ValidationResult,
    )
    from backend.app.services.validation.parser import parse_model_output
    from backend.app.services.validation.schema_validator import validate_schema

logger = logging.getLogger(__name__)


class StructuredOutputService:
    """
    Orchestrates the full Phase 9 structured-output validation pipeline.
    Callable by Phase 7 Agent or REST API endpoint without any LLM involvement.
    """

    def __init__(
        self,
        rate_tolerance: float = DEFAULT_RATE_TOLERANCE_MM_PER_YEAR,
        require_citations_when_findings: bool = True,
    ) -> None:
        self._engineering_validator = EngineeringValidator(
            rate_tolerance=rate_tolerance,
            require_citations_when_findings=require_citations_when_findings,
        )
        self._rate_tolerance = rate_tolerance

    def validate(self, raw: Union[str, bytes, dict]) -> ValidationResult:
        """
        Execute the full validation pipeline on raw model/agent output.

        Returns a ValidationResult with valid=True only if ALL pipeline stages pass.
        All failure paths return structured, safe ValidationResult instances.
        Internal exceptions are caught and classified — never surfaced as raw tracebacks.
        """
        # ── Stage 1: Parsing ─────────────────────────────────────────────────
        try:
            payload = parse_model_output(raw)
        except ParsingError as exc:
            logger.warning("StructuredOutputService: parsing failed — %s", str(exc))
            return ValidationResult(
                valid=False,
                status=ValidationStatus.PARSING_ERROR,
                errors=[ValidationErrorDetail(
                    field=None,
                    code="PARSING_ERROR",
                    message=str(exc),
                    stage=ValidationStage.PARSING.value,
                )],
                validation_checks=["parse_model_output"],
                checks_failed=["parse_model_output"],
            )
        except Exception as exc:
            logger.error("StructuredOutputService: unexpected parsing exception — %s", str(exc))
            return ValidationResult(
                valid=False,
                status=ValidationStatus.PARSING_ERROR,
                errors=[ValidationErrorDetail(
                    code="INTERNAL_PARSING_ERROR",
                    message="An unexpected error occurred during parsing.",
                    stage=ValidationStage.PARSING.value,
                )],
                validation_checks=["parse_model_output"],
                checks_failed=["parse_model_output"],
            )

        # ── Stage 2: Schema Validation ───────────────────────────────────────
        validated: CorrosionAuditResult
        try:
            validated = validate_schema(payload)
        except SchemaValidationError as exc:
            cause = exc.__cause__
            errors: list[ValidationErrorDetail] = []
            if cause is not None:
                from pydantic import ValidationError as PydanticValidationError
                if isinstance(cause, PydanticValidationError):
                    from app.services.validation.schema_validator import _format_pydantic_errors
                    try:
                        errors = _format_pydantic_errors(cause)
                    except Exception:
                        pass

            if not errors:
                errors = [ValidationErrorDetail(
                    code="SCHEMA_ERROR",
                    message=str(exc),
                    stage=ValidationStage.SCHEMA.value,
                )]

            logger.warning(
                "StructuredOutputService: schema validation failed — %d error(s)", len(errors)
            )
            return ValidationResult(
                valid=False,
                status=ValidationStatus.SCHEMA_ERROR,
                errors=errors,
                validation_checks=["parse_model_output", "schema_validation"],
                checks_passed=["parse_model_output"],
                checks_failed=["schema_validation"],
            )
        except Exception as exc:
            logger.error("StructuredOutputService: unexpected schema exception — %s", str(exc))
            return ValidationResult(
                valid=False,
                status=ValidationStatus.SCHEMA_ERROR,
                errors=[ValidationErrorDetail(
                    code="INTERNAL_SCHEMA_ERROR",
                    message="An unexpected error occurred during schema validation.",
                    stage=ValidationStage.SCHEMA.value,
                )],
                validation_checks=["parse_model_output", "schema_validation"],
                checks_passed=["parse_model_output"],
                checks_failed=["schema_validation"],
            )

        # ── Stage 3: Engineering Validation ─────────────────────────────────
        try:
            eng_errors, eng_warnings, eng_passed = self._engineering_validator.validate(validated)
        except Exception as exc:
            logger.error(
                "StructuredOutputService: unexpected engineering validation exception — %s", str(exc)
            )
            return ValidationResult(
                valid=False,
                status=ValidationStatus.INVALID,
                errors=[ValidationErrorDetail(
                    code="INTERNAL_ENGINEERING_ERROR",
                    message="An unexpected error occurred during engineering validation.",
                    stage=ValidationStage.ENGINEERING.value,
                )],
                validation_checks=["parse_model_output", "schema_validation", "engineering_validation"],
                checks_passed=["parse_model_output", "schema_validation"],
                checks_failed=["engineering_validation"],
            )

        all_checks = ["parse_model_output", "schema_validation"] + eng_passed + [
            e.code for e in eng_errors
        ]
        checks_passed = ["parse_model_output", "schema_validation"] + eng_passed
        checks_failed = [e.code for e in eng_errors]

        if eng_errors:
            # Classify the primary error category
            has_calc_mismatch = any(e.code == "CALCULATION_MISMATCH" for e in eng_errors)
            has_provenance = any(e.stage == ValidationStage.PROVENANCE.value for e in eng_errors)

            if has_calc_mismatch:
                status = ValidationStatus.CALCULATION_MISMATCH
            elif has_provenance:
                status = ValidationStatus.INSUFFICIENT_EVIDENCE
            else:
                status = ValidationStatus.INVALID

            logger.warning(
                "StructuredOutputService: engineering validation failed — %d error(s), status=%s",
                len(eng_errors), status,
            )
            return ValidationResult(
                valid=False,
                status=status,
                errors=eng_errors,
                warnings=eng_warnings,
                validation_checks=all_checks,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                calculation_tolerance_mm_per_year=self._rate_tolerance,
            )

        logger.info(
            "StructuredOutputService: all checks passed (equipment_id=%s)", validated.equipment_id
        )
        return ValidationResult(
            valid=True,
            status=ValidationStatus.VALID,
            validated_data=validated,
            warnings=eng_warnings,
            validation_checks=all_checks,
            checks_passed=checks_passed,
            checks_failed=[],
            calculation_tolerance_mm_per_year=self._rate_tolerance,
        )

    def validate_calculation(
        self, raw: Union[str, bytes, dict, CorrosionCalculation]
    ) -> ValidationResult:
        """
        Validate an intermediate calculation payload against the CorrosionCalculation schema.
        Accepts dicts, bytes/strings (JSON), or existing CorrosionCalculation instances.
        Normalizes legacy tool outputs while enforcing engineering bounds and extra='forbid'.
        """
        if isinstance(raw, CorrosionCalculation):
            return ValidationResult(
                valid=True,
                status=ValidationStatus.VALID,
                validated_data=raw,
                validation_checks=["calculation_schema_validation"],
                checks_passed=["calculation_schema_validation"],
                checks_failed=[],
            )

        # Stage 1: Parse if string or bytes
        payload: Any = raw
        if isinstance(raw, (str, bytes)):
            try:
                payload = parse_model_output(raw)
            except ParsingError as exc:
                return ValidationResult(
                    valid=False,
                    status=ValidationStatus.PARSING_ERROR,
                    errors=[
                        ValidationErrorDetail(
                            code="PARSING_ERROR",
                            message=str(exc),
                            stage=ValidationStage.PARSING.value,
                        )
                    ],
                    validation_checks=["parse_calculation_output"],
                    checks_failed=["parse_calculation_output"],
                )

        if not isinstance(payload, dict):
            return ValidationResult(
                valid=False,
                status=ValidationStatus.SCHEMA_ERROR,
                errors=[
                    ValidationErrorDetail(
                        code="SCHEMA_ERROR",
                        message=f"Expected dictionary payload for calculation, got {type(payload).__name__}",
                        stage=ValidationStage.SCHEMA.value,
                    )
                ],
                validation_checks=["calculation_schema_validation"],
                checks_failed=["calculation_schema_validation"],
            )

        # Stage 2: Schema normalization for tool outputs
        calc_data = dict(payload)
        # Handle field aliases from calculation tools
        if "current_thickness_mm" not in calc_data and "nominal_or_actual_mm" in calc_data:
            calc_data["current_thickness_mm"] = calc_data["nominal_or_actual_mm"]
        if "minimum_required_mm" not in calc_data and "retired_limit_mm" in calc_data:
            calc_data["minimum_required_mm"] = calc_data["retired_limit_mm"]
        if "initial_thickness_mm" not in calc_data:
            curr = calc_data.get("current_thickness_mm")
            rate = calc_data.get("corrosion_rate_mm_per_year", calc_data.get("corrosion_rate", 0.0))
            interval = calc_data.get("inspection_interval_years", 5.0)
            if curr is not None and rate is not None:
                try:
                    calc_data["initial_thickness_mm"] = round(
                        float(curr) + float(rate) * float(interval), 4
                    )
                except (ValueError, TypeError):
                    pass
        if "inspection_interval_years" not in calc_data:
            calc_data["inspection_interval_years"] = 5.0
        if "corrosion_rate_mm_per_year" not in calc_data and "corrosion_rate" in calc_data:
            calc_data["corrosion_rate_mm_per_year"] = calc_data["corrosion_rate"]

        # Filter strictly to CorrosionCalculation fields to comply with extra="forbid"
        allowed_fields = {
            "initial_thickness_mm",
            "current_thickness_mm",
            "inspection_interval_years",
            "minimum_required_mm",
            "corrosion_rate_mm_per_year",
            "remaining_life_years",
            "formula_applied",
        }
        filtered_payload = {k: v for k, v in calc_data.items() if k in allowed_fields}

        # Stage 3: Pydantic Schema Validation
        try:
            from pydantic import ValidationError as PydanticValidationError

            validated = CorrosionCalculation.model_validate(filtered_payload)
            return ValidationResult(
                valid=True,
                status=ValidationStatus.VALID,
                validated_data=validated,
                validation_checks=["calculation_schema_validation"],
                checks_passed=["calculation_schema_validation"],
                checks_failed=[],
            )
        except PydanticValidationError as exc:
            from app.services.validation.schema_validator import _format_pydantic_errors

            errors = _format_pydantic_errors(exc)
            logger.warning(
                "StructuredOutputService: calculation schema validation failed — %d error(s)",
                len(errors),
            )
            return ValidationResult(
                valid=False,
                status=ValidationStatus.SCHEMA_ERROR,
                errors=errors,
                validation_checks=["calculation_schema_validation"],
                checks_passed=[],
                checks_failed=["calculation_schema_validation"],
                warnings=[f"{e.field or 'root'}: {e.message}" for e in errors],
            )

