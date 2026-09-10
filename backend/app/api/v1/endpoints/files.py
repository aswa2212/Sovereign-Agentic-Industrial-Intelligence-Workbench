"""
SIH26117 — Files & Ingestion API Endpoints
Provides multipart file upload, format validation, streaming SHA-256 computation,
and processed document status inspection.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

try:
    from app.core.config import Settings, get_settings
    from app.schemas.system import ErrorDetail, ErrorResponse
    from app.services.ingestion.exceptions import (
        FileTooLargeError,
        IngestionError,
        InvalidDocumentError,
        SecurityViolationError,
        UnsupportedFileTypeError,
    )
    from app.services.ingestion.models import DocumentIngestionResult
    from app.services.ingestion.service import IngestionService
except ImportError:
    from backend.app.core.config import Settings, get_settings
    from backend.app.schemas.system import ErrorDetail, ErrorResponse
    from backend.app.services.ingestion.exceptions import (
        FileTooLargeError,
        IngestionError,
        InvalidDocumentError,
        SecurityViolationError,
        UnsupportedFileTypeError,
    )
    from backend.app.services.ingestion.models import DocumentIngestionResult
    from backend.app.services.ingestion.service import IngestionService

router = APIRouter(prefix="/files", tags=["Files & Ingestion"])


def get_ingestion_service(settings: Settings = Depends(get_settings)) -> IngestionService:
    """Dependency provider for IngestionService singleton/instance."""
    return IngestionService(settings=settings)


@router.post(
    "/upload",
    response_model=DocumentIngestionResult,
    status_code=status.HTTP_201_CREATED,
    summary="Upload & Ingest Document",
    description="Accepts industrial files (PDF, DOCX, XLSX, CSV, PNG, JPG), validates format, "
    "computes SHA-256 provenance anchor, persists raw artifact, and extracts normalized structure.",
    responses={
        400: {"model": ErrorResponse, "description": "Security violation or bad request"},
        413: {"model": ErrorResponse, "description": "Payload too large"},
        415: {"model": ErrorResponse, "description": "Unsupported media type"},
        422: {"model": ErrorResponse, "description": "Invalid or corrupted document"},
    },
)
async def upload_document(
    file: UploadFile = File(..., description="Document file artifact"),
    service: IngestionService = Depends(get_ingestion_service),
) -> Any:
    """
    Ingest uploaded file into sovereign raw storage and extract normalized text/tables.
    """
    original_filename = file.filename or "unnamed_artifact"

    try:
        content = await file.read()
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="READ_ERROR",
                    message=f"Failed to read incoming file stream: {str(e)}",
                )
            ).model_dump(),
        )

    try:
        result = service.ingest_file(
            content=content,
            filename=original_filename,
            content_type=file.content_type,
        )
        return result

    except SecurityViolationError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=e.code,
                    message=e.message,
                    details=e.details,
                )
            ).model_dump(),
        )

    except FileTooLargeError as e:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=e.code,
                    message=e.message,
                    details=e.details,
                )
            ).model_dump(),
        )

    except UnsupportedFileTypeError as e:
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=e.code,
                    message=e.message,
                    details=e.details,
                )
            ).model_dump(),
        )

    except InvalidDocumentError as e:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=e.code,
                    message=e.message,
                    details=e.details,
                )
            ).model_dump(),
        )

    except IngestionError as e:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=e.code,
                    message=e.message,
                    details=e.details,
                )
            ).model_dump(),
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="INTERNAL_INGESTION_ERROR",
                    message="An unexpected server error occurred during document ingestion.",
                )
            ).model_dump(),
        )


@router.get(
    "/{sha256}/status",
    summary="Get Processed Document Status",
    description="Fetches normalized document metadata and extraction status by SHA-256 identity.",
    responses={
        404: {"model": ErrorResponse, "description": "Document not found"},
    },
)
async def get_document_status(
    sha256: str,
    service: IngestionService = Depends(get_ingestion_service),
) -> Dict[str, Any]:
    """Retrieve processed document representation from local disk."""
    doc = service.get_document_by_sha256(sha256)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No processed document found for SHA-256: {sha256}",
        )
    return doc
