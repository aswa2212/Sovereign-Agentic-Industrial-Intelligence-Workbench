"""
SIH26117 — Document Ingestion Service Exceptions
Structured exception hierarchy mapping directly to gateway error envelopes.
"""

from typing import Any, Optional


class IngestionError(Exception):
    """Base exception for all document ingestion failures."""

    def __init__(
        self,
        message: str,
        code: str = "INGESTION_ERROR",
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details


class UnsupportedFileTypeError(IngestionError):
    """Raised when an uploaded file extension or MIME type is not supported."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message, code="UNSUPPORTED_FILE_TYPE", details=details)


class InvalidDocumentError(IngestionError):
    """Raised when a document is corrupted, malformed, or cannot be parsed."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message, code="INVALID_DOCUMENT", details=details)


class FileTooLargeError(IngestionError):
    """Raised when an uploaded file exceeds the configured size limit."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message, code="FILE_TOO_LARGE", details=details)


class SecurityViolationError(IngestionError):
    """Raised when malicious patterns such as path traversal are detected."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message, code="SECURITY_VIOLATION", details=details)


class ExtractionError(IngestionError):
    """Raised when text or table extraction fails unexpectedly."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message, code="EXTRACTION_FAILURE", details=details)
