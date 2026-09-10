"""
SIH26117 — Vision & OCR API Endpoints
Provides endpoints for local optical character recognition and P&ID visual understanding.
"""

from typing import Any, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

try:
    from app.core.config import Settings, get_settings
    from app.schemas.system import ErrorDetail, ErrorResponse
    from app.schemas.vision import OCRExtractionResult, SchematicAnalysisResult
    from app.services.ingestion.models import DocumentProvenance
    from app.services.ingestion.storage import StorageManager
    from app.services.model_manager.manager import ModelManager
    from app.services.vision.base import (
        InvalidImageError,
        OCREngineUnavailableError,
        VisionModelUnavailableError,
    )
    from app.services.vision.ocr_engine import LocalOCREngine
    from app.services.vision.schematic_parser import SchematicParser
    from app.services.vision.vlm_client import (
        MockVisionProvider,
        ModelManagerVisionProvider,
        VisionEngine,
    )
except ImportError:
    from backend.app.core.config import Settings, get_settings
    from backend.app.schemas.system import ErrorDetail, ErrorResponse
    from backend.app.schemas.vision import OCRExtractionResult, SchematicAnalysisResult
    from backend.app.services.ingestion.models import DocumentProvenance
    from backend.app.services.ingestion.storage import StorageManager
    from backend.app.services.model_manager.manager import ModelManager
    from backend.app.services.vision.base import (
        InvalidImageError,
        OCREngineUnavailableError,
        VisionModelUnavailableError,
    )
    from backend.app.services.vision.ocr_engine import LocalOCREngine
    from backend.app.services.vision.schematic_parser import SchematicParser
    from backend.app.services.vision.vlm_client import (
        MockVisionProvider,
        ModelManagerVisionProvider,
        VisionEngine,
    )

router = APIRouter(prefix="/vision", tags=["Vision & OCR"])


def get_ocr_engine(settings: Settings = Depends(get_settings)) -> LocalOCREngine:
    """Dependency provider for LocalOCREngine."""
    prefer_mock = settings.inference_provider == "mock"
    return LocalOCREngine(prefer_mock_if_unavailable=prefer_mock)


def get_vision_engine(settings: Settings = Depends(get_settings)) -> VisionEngine:
    """Dependency provider for VisionEngine."""
    if settings.inference_provider == "mock":
        return VisionEngine(provider=MockVisionProvider())
    model_mgr = ModelManager.from_settings()
    return VisionEngine(provider=ModelManagerVisionProvider(model_mgr))


def get_schematic_parser(
    ocr_engine: LocalOCREngine = Depends(get_ocr_engine),
    vision_engine: VisionEngine = Depends(get_vision_engine),
) -> SchematicParser:
    """Dependency provider for SchematicParser."""
    return SchematicParser(ocr_engine=ocr_engine, vision_engine=vision_engine)


@router.post(
    "/ocr",
    response_model=OCRExtractionResult,
    status_code=status.HTTP_200_OK,
    summary="Extract Local OCR Text & Bounding Boxes",
    description="Executes localized OCR on an uploaded image or an existing raw artifact referenced by SHA-256.",
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        404: {"model": ErrorResponse, "description": "Referenced document not found"},
        422: {"model": ErrorResponse, "description": "Invalid image format"},
        503: {"model": ErrorResponse, "description": "Local OCR engine unavailable"},
    },
)
async def perform_ocr(
    file: Optional[UploadFile] = File(None, description="Optional direct image upload"),
    document_sha256: Optional[str] = Form(None, description="SHA-256 of stored document"),
    page_number: int = Form(1, description="1-based page number if multi-page"),
    preprocess: bool = Form(True, description="Apply contrast normalization"),
    ocr_engine: LocalOCREngine = Depends(get_ocr_engine),
    settings: Settings = Depends(get_settings),
) -> Any:
    """Execute local OCR with bounding box and confidence score tracking."""
    storage = StorageManager(settings)
    image_bytes: Optional[bytes] = None
    filename = "uploaded_image.png"

    if file:
        image_bytes = await file.read()
        filename = file.filename or "uploaded_image.png"
        prov = DocumentProvenance(source_filename=filename, source_sha256="direct_upload")
    elif document_sha256:
        raw_path = storage.get_raw_file_path(document_sha256, "artifact")
        if not raw_path or not raw_path.is_file():
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=ErrorResponse(
                    error=ErrorDetail(
                        code="DOCUMENT_NOT_FOUND",
                        message=f"No raw artifact found for SHA-256: {document_sha256}",
                    )
                ).model_dump(),
            )
        image_bytes = raw_path.read_bytes()
        prov = DocumentProvenance(
            source_filename=raw_path.name,
            source_sha256=document_sha256,
            page_number=page_number,
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="MISSING_INPUT",
                    message="Either an uploaded 'file' or a 'document_sha256' must be provided.",
                )
            ).model_dump(),
        )

    try:
        result = await ocr_engine.extract_from_image(
            image_bytes=image_bytes,
            provenance=prov,
            preprocess=preprocess,
        )
        return result
    except OCREngineUnavailableError as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=e.code,
                    message=e.message,
                    details=e.details,
                )
            ).model_dump(),
        )
    except InvalidImageError as e:
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
                    code="OCR_FAILED",
                    message=f"OCR execution failed unexpectedly: {str(e)}",
                )
            ).model_dump(),
        )


@router.post(
    "/analyze-drawing",
    response_model=SchematicAnalysisResult,
    status_code=status.HTTP_200_OK,
    summary="Analyze P&ID / Engineering Drawing",
    description="Extracts candidate instrument tags, equipment IDs, and line numbers using local vision & OCR.",
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        404: {"model": ErrorResponse, "description": "Referenced document not found"},
        422: {"model": ErrorResponse, "description": "Invalid drawing image"},
        503: {"model": ErrorResponse, "description": "Vision model or OCR unavailable"},
    },
)
async def analyze_drawing(
    file: Optional[UploadFile] = File(None, description="Drawing image file"),
    document_sha256: Optional[str] = Form(None, description="SHA-256 of stored drawing"),
    page_number: int = Form(1, description="1-based page number"),
    mode: str = Form("hybrid", description="Mode: 'hybrid', 'ocr_only', 'vision_only'"),
    parser: SchematicParser = Depends(get_schematic_parser),
    settings: Settings = Depends(get_settings),
) -> Any:
    """Analyze engineering drawing and return structured visual findings."""
    storage = StorageManager(settings)
    image_bytes: Optional[bytes] = None

    if file:
        image_bytes = await file.read()
        prov = DocumentProvenance(
            source_filename=file.filename or "drawing.png",
            source_sha256="direct_upload",
            page_number=page_number,
        )
    elif document_sha256:
        raw_path = storage.get_raw_file_path(document_sha256, "drawing")
        if not raw_path or not raw_path.is_file():
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=ErrorResponse(
                    error=ErrorDetail(
                        code="DOCUMENT_NOT_FOUND",
                        message=f"No raw artifact found for SHA-256: {document_sha256}",
                    )
                ).model_dump(),
            )
        image_bytes = raw_path.read_bytes()
        prov = DocumentProvenance(
            source_filename=raw_path.name,
            source_sha256=document_sha256,
            page_number=page_number,
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="MISSING_INPUT",
                    message="Either an uploaded 'file' or a 'document_sha256' must be provided.",
                )
            ).model_dump(),
        )

    try:
        result = await parser.parse_drawing(
            image_bytes=image_bytes,
            provenance=prov,
            mode=mode,
        )
        return result
    except (OCREngineUnavailableError, VisionModelUnavailableError) as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=e.code,
                    message=e.message,
                    details=e.details,
                )
            ).model_dump(),
        )
    except InvalidImageError as e:
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
                    code="ANALYSIS_FAILED",
                    message=f"Drawing analysis failed: {str(e)}",
                )
            ).model_dump(),
        )
