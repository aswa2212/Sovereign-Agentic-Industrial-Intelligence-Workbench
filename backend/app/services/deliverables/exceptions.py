"""
SIH26117 — Phase 10: Deliverables Service Exceptions

Defines domain-specific exception types for the deterministic deliverable generation layer.
All errors provide structured information and never leak sensitive stack traces.
"""


class DeliverableError(Exception):
    """Base exception for all deliverable generation failures."""

    def __init__(self, message: str, code: str = "DELIVERABLE_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class InvalidDeliverableInputError(DeliverableError):
    """Raised when the input engineering payload fails schema or structural preconditions."""

    def __init__(self, message: str, code: str = "INVALID_INPUT") -> None:
        super().__init__(message, code=code)


class UnvalidatedInputError(DeliverableError):
    """Raised when an unvalidated or invalid Phase 9 validation result is passed to the factory."""

    def __init__(self, message: str = "Only validated Phase 9 results can produce deliverables.", code: str = "UNVALIDATED_INPUT") -> None:
        super().__init__(message, code=code)


class UnsupportedFormatError(DeliverableError):
    """Raised when an unrecognized or unsupported document format is requested."""

    def __init__(self, fmt: str, code: str = "UNSUPPORTED_FORMAT") -> None:
        super().__init__(f"Unsupported deliverable format: '{fmt}'. Supported formats: docx, xlsx, pptx.", code=code)


class DocumentGenerationError(DeliverableError):
    """Raised when a specific builder encounters an unrecoverable document formatting error."""

    def __init__(self, message: str, code: str = "GENERATION_ERROR") -> None:
        super().__init__(message, code=code)


class OutputVerificationError(DeliverableError):
    """Raised when an output artifact fails deterministic post-generation integrity checks."""

    def __init__(self, message: str, code: str = "VERIFICATION_FAILED") -> None:
        super().__init__(message, code=code)


class PathTraversalSecurityError(DeliverableError):
    """Raised when an identifier or filename attempts to escape the designated output folder."""

    def __init__(self, message: str = "Path traversal or unauthorized filesystem target detected.", code: str = "PATH_TRAVERSAL_BLOCKED") -> None:
        super().__init__(message, code=code)
