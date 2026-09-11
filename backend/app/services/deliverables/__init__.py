"""
SIH26117 — Phase 10: Deliverables Service Package

Provides deterministic Office document generation for MRPL technical deliverables.
Exposes the DeliverablesFactory and individual document builders.
"""

from app.services.deliverables.base import BaseDocumentBuilder
from app.services.deliverables.docx_builder import DocxDeliverableBuilder
from app.services.deliverables.exceptions import (
    DeliverableError,
    DocumentGenerationError,
    InvalidDeliverableInputError,
    OutputVerificationError,
    PathTraversalSecurityError,
    UnsupportedFormatError,
    UnvalidatedInputError,
)
from app.services.deliverables.factory import DeliverablesFactory
from app.services.deliverables.models import (
    DeliverableFormat,
    DeliverableGenerationResult,
    GeneratedArtifact,
    ReportMetadata,
)
from app.services.deliverables.naming import (
    generate_artifact_filename,
    resolve_and_verify_output_path,
    sanitize_identifier,
)
from app.services.deliverables.pptx_builder import PptxDeliverableBuilder
from app.services.deliverables.validators import (
    validate_deliverable_input,
    verify_file_integrity,
)
from app.services.deliverables.xlsx_builder import XlsxDeliverableBuilder

__all__ = [
    "BaseDocumentBuilder",
    "DocxDeliverableBuilder",
    "XlsxDeliverableBuilder",
    "PptxDeliverableBuilder",
    "DeliverablesFactory",
    "DeliverableFormat",
    "ReportMetadata",
    "GeneratedArtifact",
    "DeliverableGenerationResult",
    "DeliverableError",
    "InvalidDeliverableInputError",
    "UnvalidatedInputError",
    "UnsupportedFormatError",
    "DocumentGenerationError",
    "OutputVerificationError",
    "PathTraversalSecurityError",
    "validate_deliverable_input",
    "verify_file_integrity",
    "generate_artifact_filename",
    "resolve_and_verify_output_path",
    "sanitize_identifier",
]
