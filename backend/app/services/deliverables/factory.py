"""
SIH26117 — Phase 10: Deterministic Deliverables Factory

Coordinates multi-format Office document generation from Phase 9 validated engineering results.
Enforces validation preconditions (fail-closed), dispatches to deterministic format builders,
and ensures post-generation structural verification.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from app.core.config import get_settings
    from app.services.deliverables.base import BaseDocumentBuilder
    from app.services.deliverables.docx_builder import DocxDeliverableBuilder
    from app.services.deliverables.exceptions import (
        DeliverableError,
        InvalidDeliverableInputError,
        UnsupportedFormatError,
    )
    from app.services.deliverables.models import (
        DeliverableFormat,
        DeliverableGenerationResult,
        GeneratedArtifact,
        ReportMetadata,
    )
    from app.services.deliverables.naming import (
        generate_artifact_filename,
        resolve_and_verify_output_path,
    )
    from app.services.deliverables.pptx_builder import PptxDeliverableBuilder
    from app.services.deliverables.validators import validate_deliverable_input
    from app.services.deliverables.xlsx_builder import XlsxDeliverableBuilder
    from app.services.validation.models import CorrosionAuditResult, ValidationResult
except ImportError:
    from backend.app.core.config import get_settings
    from backend.app.services.deliverables.base import BaseDocumentBuilder
    from backend.app.services.deliverables.docx_builder import DocxDeliverableBuilder
    from backend.app.services.deliverables.exceptions import (
        DeliverableError,
        InvalidDeliverableInputError,
        UnsupportedFormatError,
    )
    from backend.app.services.deliverables.models import (
        DeliverableFormat,
        DeliverableGenerationResult,
        GeneratedArtifact,
        ReportMetadata,
    )
    from backend.app.services.deliverables.naming import (
        generate_artifact_filename,
        resolve_and_verify_output_path,
    )
    from backend.app.services.deliverables.pptx_builder import PptxDeliverableBuilder
    from backend.app.services.deliverables.validators import validate_deliverable_input
    from backend.app.services.deliverables.xlsx_builder import XlsxDeliverableBuilder
    from backend.app.services.validation.models import CorrosionAuditResult, ValidationResult

logger = logging.getLogger(__name__)


class DeliverablesFactory:
    """
    Central orchestration engine for deterministic Office deliverable generation.
    Enforces Phase 9 validation bounds before permitting document construction.
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        audit_service: Optional[Any] = None,
    ) -> None:
        settings = get_settings()
        self.base_output_dir = output_dir or (settings.project_root / settings.output_dir)
        self.audit_service = audit_service

        # Output sub-folders for each format
        self.format_dirs: Dict[DeliverableFormat, Path] = {
            DeliverableFormat.DOCX: self.base_output_dir / "docx",
            DeliverableFormat.XLSX: self.base_output_dir / "xlsx",
            DeliverableFormat.PPTX: self.base_output_dir / "pptx",
        }

        for d in self.format_dirs.values():
            d.mkdir(parents=True, exist_ok=True)

        # Registry of builders
        self.builders: Dict[DeliverableFormat, BaseDocumentBuilder] = {
            DeliverableFormat.DOCX: DocxDeliverableBuilder(),
            DeliverableFormat.XLSX: XlsxDeliverableBuilder(),
            DeliverableFormat.PPTX: PptxDeliverableBuilder(),
        }

        # Cache of generated artifacts by artifact_id
        self._artifacts: Dict[str, GeneratedArtifact] = {}

    def generate(
        self,
        payload: Union[CorrosionAuditResult, ValidationResult, dict],
        formats: Optional[List[Union[DeliverableFormat, str]]] = None,
        metadata: Optional[ReportMetadata] = None,
        task_id: Optional[str] = None,
    ) -> DeliverableGenerationResult:
        """
        Generates deterministic deliverables across one or more requested formats.
        Fails closed if the input has not passed Phase 9 engineering validation.
        """
        # 1. Precondition check: Validate input data
        validated_data = validate_deliverable_input(payload)
        rep_meta = metadata or ReportMetadata()

        # 2. Normalize requested formats
        req_formats = self._normalize_formats(formats)

        effective_task_id = task_id or validated_data.task_id
        artifacts_produced: List[GeneratedArtifact] = []

        # 3. Deterministic construction per format
        for fmt in req_formats:
            builder = self.builders.get(fmt)
            if not builder:
                raise UnsupportedFormatError(fmt.value if isinstance(fmt, DeliverableFormat) else str(fmt))

            fmt_dir = self.format_dirs[fmt]
            filename = generate_artifact_filename(
                equipment_id=validated_data.equipment_id,
                fmt=fmt,
                task_id=effective_task_id,
            )
            target_path = resolve_and_verify_output_path(fmt_dir, filename)

            logger.info("Building %s deliverable for %s at %s", fmt.value.upper(), validated_data.equipment_id, target_path)
            artifact = builder.build(validated_data, rep_meta, target_path)

            self._artifacts[artifact.artifact_id] = artifact
            artifacts_produced.append(artifact)

            if self.audit_service:
                try:
                    from app.services.audit.models import AuditEventType
                    self.audit_service.record_event(
                        event_type=AuditEventType.DELIVERABLE_CREATED,
                        action=f"Created {artifact.format.value.upper()} deliverable: {artifact.filename}",
                        task_id=effective_task_id,
                        status="SUCCESS",
                        metadata={
                            "artifact_id": artifact.artifact_id,
                            "format": artifact.format.value,
                            "filename": artifact.filename,
                            "file_size_bytes": artifact.file_size_bytes,
                            "equipment_id": validated_data.equipment_id,
                        },
                    )
                except Exception as audit_err:
                    logger.warning("Audit logging for deliverable failed: %s", audit_err)

        summary_msg = (
            f"Successfully generated {len(artifacts_produced)} verified Office deliverable(s) "
            f"for {validated_data.equipment_id} ({', '.join(f.value.upper() for f in req_formats)})."
        )

        return DeliverableGenerationResult(
            success=True,
            task_id=effective_task_id,
            equipment_id=validated_data.equipment_id,
            inspection_subject=validated_data.inspection_subject,
            artifacts=artifacts_produced,
            formats_requested=req_formats,
            summary=summary_msg,
            validation_status="PHASE9_VALIDATED",
        )

    def generate_docx(
        self,
        payload: Union[CorrosionAuditResult, ValidationResult, dict],
        metadata: Optional[ReportMetadata] = None,
        task_id: Optional[str] = None,
    ) -> GeneratedArtifact:
        """Convenience method to generate only the DOCX memorandum."""
        res = self.generate(payload, formats=[DeliverableFormat.DOCX], metadata=metadata, task_id=task_id)
        return res.artifacts[0]

    def generate_xlsx(
        self,
        payload: Union[CorrosionAuditResult, ValidationResult, dict],
        metadata: Optional[ReportMetadata] = None,
        task_id: Optional[str] = None,
    ) -> GeneratedArtifact:
        """Convenience method to generate only the XLSX calculation sheet."""
        res = self.generate(payload, formats=[DeliverableFormat.XLSX], metadata=metadata, task_id=task_id)
        return res.artifacts[0]

    def generate_pptx(
        self,
        payload: Union[CorrosionAuditResult, ValidationResult, dict],
        metadata: Optional[ReportMetadata] = None,
        task_id: Optional[str] = None,
    ) -> GeneratedArtifact:
        """Convenience method to generate only the PPTX presentation."""
        res = self.generate(payload, formats=[DeliverableFormat.PPTX], metadata=metadata, task_id=task_id)
        return res.artifacts[0]

    def get_artifact(self, artifact_id: str) -> Optional[GeneratedArtifact]:
        """Retrieves generated artifact metadata by artifact ID."""
        return self._artifacts.get(artifact_id)

    def get_artifact_path(self, fmt: DeliverableFormat, filename: str) -> Path:
        """Resolves and verifies the path of an artifact on disk."""
        fmt_dir = self.format_dirs.get(fmt)
        if not fmt_dir:
            raise UnsupportedFormatError(str(fmt))
        return resolve_and_verify_output_path(fmt_dir, filename)

    def _normalize_formats(
        self, formats: Optional[List[Union[DeliverableFormat, str]]]
    ) -> List[DeliverableFormat]:
        """Converts strings and enums into a clean list of DeliverableFormat enums."""
        if not formats:
            return [DeliverableFormat.DOCX, DeliverableFormat.XLSX, DeliverableFormat.PPTX]

        normalized: List[DeliverableFormat] = []
        for f in formats:
            if isinstance(f, DeliverableFormat):
                if f not in normalized:
                    normalized.append(f)
            elif isinstance(f, str):
                cleaned = f.strip().lower()
                try:
                    fmt_enum = DeliverableFormat(cleaned)
                    if fmt_enum not in normalized:
                        normalized.append(fmt_enum)
                except ValueError:
                    raise UnsupportedFormatError(cleaned)
            else:
                raise UnsupportedFormatError(str(f))

        return normalized
