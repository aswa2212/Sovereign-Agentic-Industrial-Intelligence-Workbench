"""
SIH26117 — Phase 10: Deliverables REST API Endpoints

Provides endpoints for generating and securely downloading deterministic Office deliverables.
Enforces strict input validation and zero sensitive stack trace exposure.
"""

import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

try:
    from app.schemas.deliverables import (
        DeliverableGenerateRequest,
        DeliverableGenerateResponse,
    )
    from app.services.deliverables.exceptions import (
        DeliverableError,
        InvalidDeliverableInputError,
        PathTraversalSecurityError,
        UnsupportedFormatError,
        UnvalidatedInputError,
    )
    from app.services.deliverables.factory import DeliverablesFactory
    from app.services.deliverables.models import DeliverableFormat
except ImportError:
    from backend.app.schemas.deliverables import (
        DeliverableGenerateRequest,
        DeliverableGenerateResponse,
    )
    from backend.app.services.deliverables.exceptions import (
        DeliverableError,
        InvalidDeliverableInputError,
        PathTraversalSecurityError,
        UnsupportedFormatError,
        UnvalidatedInputError,
    )
    from backend.app.services.deliverables.factory import DeliverablesFactory
    from backend.app.services.deliverables.models import DeliverableFormat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deliverables", tags=["deliverables"])
_factory_instance: Optional[DeliverablesFactory] = None


def get_deliverables_factory() -> DeliverablesFactory:
    """Singleton getter for DeliverablesFactory."""
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = DeliverablesFactory()
    return _factory_instance


def set_deliverables_factory(factory: DeliverablesFactory) -> None:
    """Override singleton factory for testing isolation."""
    global _factory_instance
    _factory_instance = factory


@router.post(
    "/generate",
    response_model=DeliverableGenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate deterministic Office deliverables (DOCX, XLSX, PPTX) from validated engineering data",
)
async def generate_deliverables(req: DeliverableGenerateRequest) -> DeliverableGenerateResponse:
    """
    Consumes a validated Phase 9 engineering result and renders deterministic,
    publication-ready Office documents (DOCX memo, XLSX calculation sheet, PPTX briefing).
    Fails closed if the input has not passed Phase 9 validation.
    """
    payload = req.data or req.raw_payload
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MISSING_PAYLOAD", "message": "Either 'data' or 'raw_payload' must be provided."},
        )

    factory = get_deliverables_factory()

    try:
        result = factory.generate(
            payload=payload,
            formats=req.formats,
            metadata=req.metadata,
            task_id=req.task_id,
        )
        return DeliverableGenerateResponse(
            success=result.success,
            task_id=result.task_id,
            equipment_id=result.equipment_id,
            inspection_subject=result.inspection_subject,
            artifacts=result.artifacts,
            formats_requested=result.formats_requested,
            summary=result.summary,
            validation_status=result.validation_status,
        )
    except UnvalidatedInputError as e:
        logger.warning("Unvalidated input rejected: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": e.code, "message": e.message},
        )
    except (InvalidDeliverableInputError, UnsupportedFormatError) as e:
        logger.warning("Invalid deliverable request: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message},
        )
    except PathTraversalSecurityError as e:
        logger.error("Security violation blocked: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": e.code, "message": e.message},
        )
    except DeliverableError as e:
        logger.error("Deliverable generation failed: %s", e.message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": e.code, "message": e.message},
        )
    except Exception as e:
        logger.error("Unexpected error during deliverable generation: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_ERROR", "message": "An error occurred generating the deliverable."},
        )


@router.get(
    "/download/{fmt}/{filename}",
    response_class=FileResponse,
    summary="Download a generated Office deliverable file",
)
async def download_deliverable(fmt: str, filename: str) -> FileResponse:
    """
    Provides secure local file download for generated deliverables.
    Enforces strict path-traversal validation.
    """
    factory = get_deliverables_factory()

    try:
        format_enum = DeliverableFormat(fmt.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_FORMAT", "message": f"Unsupported format: '{fmt}'."},
        )

    try:
        file_path = factory.get_artifact_path(format_enum, filename)
    except PathTraversalSecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": e.code, "message": e.message},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PATH", "message": "Invalid artifact path requested."},
        )

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "FILE_NOT_FOUND", "message": f"Deliverable file '{filename}' was not found."},
        )

    # Media type mapping
    media_types = {
        DeliverableFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        DeliverableFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        DeliverableFormat.PPTX: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    media_type = media_types.get(format_enum, "application/octet-stream")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
    )
