"""
SIH26117 — Phase 9: Pydantic Schema Validator

Validates a parsed dict payload against the CorrosionAuditResult Pydantic model.

Distinguishes three failure categories:
  A. PARSING_ERROR  — raised upstream in parser.py
  B. SCHEMA_ERROR   — Pydantic model_validate failure (wrong types, missing fields, etc.)
  C. ENGINEERING    — raised downstream in engineering_validator.py

SECURITY:
- Never exposes internal Pydantic stack traces through structured errors.
- Unknown top-level fields are rejected by the schema (extra="forbid").
"""

import logging
from typing import Any, Dict, List

from pydantic import ValidationError as PydanticValidationError

try:
    from app.services.validation.base import ValidationOutcome, ValidationStatus, ValidationStage
    from app.services.validation.exceptions import SchemaValidationError
    from app.services.validation.models import CorrosionAuditResult, ValidationErrorDetail
except ImportError:
    from backend.app.services.validation.base import ValidationOutcome, ValidationStatus, ValidationStage
    from backend.app.services.validation.exceptions import SchemaValidationError
    from backend.app.services.validation.models import CorrosionAuditResult, ValidationErrorDetail

logger = logging.getLogger(__name__)


def validate_schema(payload: Dict[str, Any]) -> CorrosionAuditResult:
    """
    Validate a parsed dict against CorrosionAuditResult.

    Returns a CorrosionAuditResult instance on success.
    Raises SchemaValidationError with structured field-level error details on failure.
    Never surfaces raw Pydantic internals to callers.
    """
    try:
        result = CorrosionAuditResult.model_validate(payload)
        logger.debug("schema_validator: payload passed schema validation")
        return result
    except PydanticValidationError as exc:
        errors = _format_pydantic_errors(exc)
        msg = f"Schema validation failed with {len(errors)} error(s)"
        logger.warning("schema_validator: %s", msg)
        raise SchemaValidationError(msg) from exc


def _format_pydantic_errors(exc: PydanticValidationError) -> List[ValidationErrorDetail]:
    """
    Convert Pydantic ValidationError errors into structured ValidationErrorDetail list.
    Strips internal Pydantic context from user-facing messages.
    """
    details: List[ValidationErrorDetail] = []
    for err in exc.errors():
        field_path = ".".join(str(loc) for loc in err.get("loc", []))
        code = _pydantic_type_to_code(err.get("type", ""))
        details.append(
            ValidationErrorDetail(
                field=field_path or None,
                code=code,
                message=err.get("msg", "Validation error"),
                stage=ValidationStage.SCHEMA.value,
            )
        )
    return details


def schema_validation_outcome(payload: Dict[str, Any]) -> ValidationOutcome:
    """
    Convenience wrapper returning a ValidationOutcome instead of raising.
    Used by StructuredOutputService to accumulate results cleanly.
    """
    try:
        result = validate_schema(payload)
        return ValidationOutcome(
            valid=True,
            status=ValidationStatus.VALID,
            data=result.model_dump(),
        )
    except SchemaValidationError as exc:
        # Re-parse the Pydantic error for structured output
        try:
            inner: PydanticValidationError = exc.__cause__  # type: ignore[assignment]
            errors = _format_pydantic_errors(inner)
        except Exception:
            errors = [ValidationErrorDetail(
                code="SCHEMA_ERROR",
                message=str(exc),
                stage=ValidationStage.SCHEMA.value,
            )]
        return ValidationOutcome(
            valid=False,
            status=ValidationStatus.SCHEMA_ERROR,
            stage=ValidationStage.SCHEMA,
            errors=[e.model_dump() for e in errors],
        )


# ── Code mapping ───────────────────────────────────────────────────────────────

_PYDANTIC_CODE_MAP: Dict[str, str] = {
    "missing": "REQUIRED_FIELD_MISSING",
    "value_error": "INVALID_VALUE",
    "type_error": "INVALID_TYPE",
    "extra_forbidden": "UNEXPECTED_FIELD",
    "enum": "INVALID_ENUM_VALUE",
    "greater_than": "VALUE_TOO_SMALL",
    "less_than": "VALUE_TOO_LARGE",
    "greater_than_equal": "VALUE_TOO_SMALL",
    "less_than_equal": "VALUE_TOO_LARGE",
    "string_too_short": "STRING_TOO_SHORT",
    "string_too_long": "STRING_TOO_LONG",
    "json_invalid": "INVALID_JSON",
    "float_parsing": "INVALID_FLOAT",
    "int_parsing": "INVALID_INT",
    "bool_parsing": "INVALID_BOOL",
}


def _pydantic_type_to_code(pydantic_type: str) -> str:
    """Map a Pydantic error type string to a stable, user-facing error code."""
    return _PYDANTIC_CODE_MAP.get(pydantic_type, pydantic_type.upper().replace(".", "_"))
