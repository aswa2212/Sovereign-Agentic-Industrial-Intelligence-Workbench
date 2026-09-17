"""
SIH26117 — Document Ingestion Service Package
Public interface for multimodal document ingestion and normalization.
"""

try:
    from app.services.ingestion.exceptions import (
        ExtractionError,
        FileTooLargeError,
        IngestionError,
        InvalidDocumentError,
        SecurityViolationError,
        UnsupportedFileTypeError,
    )
    from app.services.ingestion.file_detector import detect_file_type
    from app.services.ingestion.hasher import (
        compute_sha256_bytes,
        compute_sha256_file,
        compute_sha256_stream,
    )
    from app.services.ingestion.models import (
        DocumentIngestionResult,
        DocumentPage,
        DocumentProvenance,
        DocumentSection,
        ExtractionStatus,
        ImageInfo,
        MediaType,
        NormalizedDocument,
        ParsedTable,
        SheetData,
    )
    from app.services.ingestion.service import IngestionService
    from app.services.ingestion.storage import StorageManager, sanitize_filename
except ImportError:
    from backend.app.services.ingestion.exceptions import (
        ExtractionError,
        FileTooLargeError,
        IngestionError,
        InvalidDocumentError,
        SecurityViolationError,
        UnsupportedFileTypeError,
    )
    from backend.app.services.ingestion.file_detector import detect_file_type
    from backend.app.services.ingestion.hasher import (
        compute_sha256_bytes,
        compute_sha256_file,
        compute_sha256_stream,
    )
    from backend.app.services.ingestion.models import (
        DocumentIngestionResult,
        DocumentPage,
        DocumentProvenance,
        DocumentSection,
        ExtractionStatus,
        ImageInfo,
        MediaType,
        NormalizedDocument,
        ParsedTable,
        SheetData,
    )
    from backend.app.services.ingestion.service import IngestionService
    from backend.app.services.ingestion.storage import StorageManager, sanitize_filename

__all__ = [
    "IngestionService",
    "StorageManager",
    "sanitize_filename",
    "compute_sha256_bytes",
    "compute_sha256_stream",
    "compute_sha256_file",
    "detect_file_type",
    "IngestionError",
    "UnsupportedFileTypeError",
    "InvalidDocumentError",
    "FileTooLargeError",
    "SecurityViolationError",
    "ExtractionError",
    "ExtractionStatus",
    "MediaType",
    "DocumentProvenance",
    "ParsedTable",
    "DocumentPage",
    "DocumentSection",
    "SheetData",
    "ImageInfo",
    "NormalizedDocument",
    "DocumentIngestionResult",
]
