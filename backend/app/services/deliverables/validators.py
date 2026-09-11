"""
SIH26117 — Phase 10: Deliverables Input and Output Validators

Enforces pre-generation validation bounds and post-generation structural verification.
Guarantees that unvalidated data NEVER generates deliverables (fail-closed).
"""

import logging
from pathlib import Path
from typing import Any, Union
import zipfile

try:
    from app.services.deliverables.exceptions import (
        InvalidDeliverableInputError,
        OutputVerificationError,
        UnvalidatedInputError,
    )
    from app.services.deliverables.models import DeliverableFormat
    from app.services.validation.models import CorrosionAuditResult, ValidationResult
except ImportError:
    from backend.app.services.deliverables.exceptions import (
        InvalidDeliverableInputError,
        OutputVerificationError,
        UnvalidatedInputError,
    )
    from backend.app.services.deliverables.models import DeliverableFormat
    from backend.app.services.validation.models import CorrosionAuditResult, ValidationResult

logger = logging.getLogger(__name__)


def validate_deliverable_input(
    payload: Union[CorrosionAuditResult, ValidationResult, dict]
) -> CorrosionAuditResult:
    """
    Validates that the input is a valid Phase 9 engineering result.
    Rejects unvalidated, failed, or malformed inputs.
    """
    if payload is None:
        raise InvalidDeliverableInputError("Input deliverable payload cannot be None.")

    # Case 1: Already a CorrosionAuditResult
    if isinstance(payload, CorrosionAuditResult):
        _assert_basic_engineering_fields(payload)
        return payload

    # Case 2: ValidationResult from StructuredOutputService
    if isinstance(payload, ValidationResult):
        if not payload.valid or payload.status != "VALID":
            reasons = [e.message for e in payload.errors] or [f"Status: {payload.status}"]
            raise UnvalidatedInputError(
                f"Cannot generate deliverable from invalid Phase 9 result: {'; '.join(reasons)}"
            )
        if not payload.validated_data:
            raise UnvalidatedInputError("ValidationResult marked valid but validated_data is missing.")
        _assert_basic_engineering_fields(payload.validated_data)
        return payload.validated_data

    # Case 3: Raw dictionary
    if isinstance(payload, dict):
        # Check if it's a serialized ValidationResult
        if "valid" in payload and "status" in payload:
            if not payload.get("valid") or payload.get("status") != "VALID":
                raise UnvalidatedInputError(
                    f"Payload indicates failed validation (status: {payload.get('status')})."
                )
            inner = payload.get("validated_data")
            if not inner:
                raise UnvalidatedInputError("Serialized ValidationResult missing validated_data.")
            return validate_deliverable_input(inner)

        # Direct dictionary representation of CorrosionAuditResult
        try:
            audit_result = CorrosionAuditResult.model_validate(payload)
            _assert_basic_engineering_fields(audit_result)
            return audit_result
        except Exception as e:
            raise InvalidDeliverableInputError(f"Schema validation failed for deliverable input: {str(e)}")

    raise InvalidDeliverableInputError(f"Unsupported input type for deliverable generation: {type(payload).__name__}")


def _assert_basic_engineering_fields(data: CorrosionAuditResult) -> None:
    """Enforces essential non-empty fields on the validated model."""
    if not data.equipment_id or not data.equipment_id.strip():
        raise InvalidDeliverableInputError("Equipment identifier (equipment_id) is mandatory.")
    if not data.inspection_subject or not data.inspection_subject.strip():
        raise InvalidDeliverableInputError("Inspection subject (inspection_subject) is mandatory.")


def verify_file_integrity(output_path: Path, expected_format: DeliverableFormat) -> bool:
    """
    Verifies that the generated file exists, is non-empty, has the correct extension,
    and can be opened and parsed by the relevant format reader.
    """
    if not output_path.exists():
        raise OutputVerificationError(f"Generated artifact does not exist on disk: {output_path}")

    size = output_path.stat().st_size
    if size <= 0:
        raise OutputVerificationError(f"Generated artifact is empty (0 bytes): {output_path}")

    expected_ext = f".{expected_format.value.lower()}"
    if output_path.suffix.lower() != expected_ext:
        raise OutputVerificationError(
            f"File extension mismatch: expected {expected_ext}, got {output_path.suffix}"
        )

    # Format-specific deep structural verification
    if expected_format == DeliverableFormat.DOCX:
        _verify_docx_structure(output_path)
    elif expected_format == DeliverableFormat.XLSX:
        _verify_xlsx_structure(output_path)
    elif expected_format == DeliverableFormat.PPTX:
        _verify_pptx_structure(output_path)

    return True


def _verify_docx_structure(path: Path) -> None:
    """Re-opens DOCX with python-docx and verifies paragraphs and tables."""
    try:
        import docx
        doc = docx.Document(path)
        if len(doc.paragraphs) == 0 and len(doc.tables) == 0:
            raise OutputVerificationError(f"DOCX {path.name} contains no paragraphs or tables.")
    except Exception as e:
        if isinstance(e, OutputVerificationError):
            raise
        raise OutputVerificationError(f"DOCX structural validation failed for {path.name}: {str(e)}")


def _verify_xlsx_structure(path: Path) -> None:
    """Re-opens XLSX with openpyxl and verifies sheets and cell content."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=False)
        if len(wb.sheetnames) == 0:
            raise OutputVerificationError(f"XLSX {path.name} contains no worksheets.")
        # Ensure at least one sheet has rows
        ws = wb.active
        if ws.max_row < 1:
            raise OutputVerificationError(f"XLSX {path.name} active sheet is empty.")
    except Exception as e:
        if isinstance(e, OutputVerificationError):
            raise
        raise OutputVerificationError(f"XLSX structural validation failed for {path.name}: {str(e)}")


def _verify_pptx_structure(path: Path) -> None:
    """Verifies that PPTX is a valid OpenXML presentation zip package."""
    try:
        # Check if python-pptx is available
        try:
            import pptx
            prs = pptx.Presentation(path)
            if len(prs.slides) == 0:
                raise OutputVerificationError(f"PPTX {path.name} contains no slides.")
            return
        except ImportError:
            pass

        # Fallback verification: inspect OpenXML ZIP package structure
        with zipfile.ZipFile(path, "r") as zf:
            namelist = zf.namelist()
            required_entries = ["[Content_Types].xml", "ppt/presentation.xml"]
            for req in required_entries:
                if req not in namelist:
                    raise OutputVerificationError(
                        f"PPTX {path.name} is missing mandatory OpenXML part '{req}'."
                    )
            # Verify presentation.xml is non-empty
            pres_bytes = zf.read("ppt/presentation.xml")
            if len(pres_bytes) < 50:
                raise OutputVerificationError(f"PPTX {path.name} presentation.xml is corrupt or too small.")
    except Exception as e:
        if isinstance(e, OutputVerificationError):
            raise
        raise OutputVerificationError(f"PPTX structural validation failed for {path.name}: {str(e)}")
