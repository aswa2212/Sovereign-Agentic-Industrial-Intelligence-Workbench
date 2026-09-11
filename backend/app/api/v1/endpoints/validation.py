"""
SIH26117 — Phase 9: Validation REST API Endpoints

POST /api/v1/validation/validate
    Accept a structured agent/model payload and return a full ValidationResult.

SECURITY:
- No external network calls.
- Internal stack traces are never exposed in the response body.
- The endpoint is purely deterministic and local.
- No model inference is triggered.
"""

import logging
from fastapi import APIRouter, HTTPException, status as http_status

try:
    from app.schemas.validation import ValidationRequest
    from app.services.validation.models import ValidationResult
    from app.services.validation.service import StructuredOutputService
    from app.services.validation.engineering_validator import DEFAULT_RATE_TOLERANCE_MM_PER_YEAR
except ImportError:
    from backend.app.schemas.validation import ValidationRequest
    from backend.app.services.validation.models import ValidationResult
    from backend.app.services.validation.service import StructuredOutputService
    from backend.app.services.validation.engineering_validator import DEFAULT_RATE_TOLERANCE_MM_PER_YEAR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/validation", tags=["validation"])


@router.post(
    "/validate",
    response_model=ValidationResult,
    status_code=http_status.HTTP_200_OK,
    summary="Validate a structured engineering output payload",
    description=(
        "Runs the full Phase 9 validation pipeline (parsing → schema → engineering) "
        "on a structured corrosion-audit payload and returns a structured ValidationResult. "
        "No LLM inference is triggered. Validation is deterministic and local."
    ),
)
async def validate_structured_output(req: ValidationRequest) -> ValidationResult:
    """
    Validate a structured corrosion-audit payload through the Phase 9 pipeline.

    Returns HTTP 200 with a ValidationResult regardless of whether the payload is
    valid or invalid — the valid field indicates the outcome.
    HTTP 4xx is returned only for malformed API requests (FastAPI handles 422).
    Internal errors return HTTP 500 with a safe, non-stack-trace message.
    """
    rate_tol = req.rate_tolerance if req.rate_tolerance is not None else DEFAULT_RATE_TOLERANCE_MM_PER_YEAR
    require_cit = req.require_citations if req.require_citations is not None else True

    try:
        service = StructuredOutputService(
            rate_tolerance=rate_tol,
            require_citations_when_findings=require_cit,
        )
        result = service.validate(req.payload)
        return result
    except Exception as exc:
        logger.error("Validation endpoint unexpected error: %s", str(exc))
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_ERROR", "message": "An unexpected internal error occurred."},
        ) from exc
