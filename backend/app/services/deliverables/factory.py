"""
SIH26117 — Phase 10: Deterministic Deliverables Factory

Coordinates multi-format Office document generation from Phase 9 validated engineering results.
Enforces validation preconditions (fail-closed), dispatches to deterministic format builders,
and ensures post-generation structural verification.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from app.core.config import get_settings
    from app.services.deliverables.base import BaseDocumentBuilder, compute_file_sha256
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
    from backend.app.services.deliverables.base import BaseDocumentBuilder, compute_file_sha256
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
        self.registry_path = self.base_output_dir / "deliverables_registry.json"
        self._load_registry()

    def _load_registry(self) -> None:
        """Loads artifact metadata from the persistent JSON registry file if it exists."""
        try:
            if self.registry_path.exists():
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    items = json.load(f)
                    for item in items:
                        art = GeneratedArtifact(**item)
                        self._artifacts[art.artifact_id] = art
        except Exception as e:
            logger.warning("Failed to load deliverables registry from %s: %s", self.registry_path, e)

    def _save_registry(self) -> None:
        """Saves artifact metadata to the persistent JSON registry file."""
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump([art.model_dump() for art in self._artifacts.values()], f, indent=2)
        except Exception as e:
            logger.warning("Failed to save deliverables registry to %s: %s", self.registry_path, e)

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
            self._save_registry()
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
        if artifact_id not in self._artifacts:
            self._load_registry()
        return self._artifacts.get(artifact_id)

    def list_artifacts(self) -> List[GeneratedArtifact]:
        """Lists all known generated artifacts, scanning output folders if registry is unpopulated."""
        self._load_registry()
        if not self._artifacts:
            # Scan format dirs
            for fmt, fdir in self.format_dirs.items():
                if fdir.exists():
                    for f in sorted(fdir.glob(f"*.{fmt.value}"), key=lambda p: p.stat().st_mtime, reverse=True):
                        try:
                            file_size = f.stat().st_size
                            sha256 = compute_file_sha256(f)
                            art = GeneratedArtifact(
                                artifact_id=f"{fmt.value}_{f.stem}",
                                format=fmt,
                                filename=f.name,
                                relative_path=f"{fmt.value}/{f.name}",
                                file_size_bytes=file_size,
                                sha256_hash=sha256,
                                generated_at=datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat(),
                                verification_status="VERIFIED",
                            )
                            self._artifacts[art.artifact_id] = art
                        except Exception:
                            pass
            if self._artifacts:
                self._save_registry()
        return sorted(self._artifacts.values(), key=lambda a: a.generated_at, reverse=True)

    def find_artifact_file(self, identifier: str) -> Optional[Tuple[Path, DeliverableFormat, str]]:
        """
        Robustly resolves an artifact file on disk by:
        1. Exact artifact_id match in memory or registry
        2. Known baseline IDs (art-c101-memorandum, art-c101-workbook)
        3. Filename match across output and deliverables directories
        4. Substring / task_id / hash match in filenames
        5. Format fallback (latest file for that format)
        Returns (file_path, DeliverableFormat, filename) or None.
        """
        # 1. Direct artifact_id lookup
        art = self.get_artifact(identifier)
        if art:
            try:
                p = self.get_artifact_path(art.format, art.filename)
                if p.exists() and p.is_file():
                    return (p, art.format, art.filename)
            except Exception:
                pass

        deliv_dir = self.base_output_dir / "deliverables"
        id_lower = identifier.lower().strip()

        # 2. Known baseline / mock IDs
        if "memorandum" in id_lower or id_lower == "art-c101-memorandum":
            cand = deliv_dir / "MRPL_Corrosion_Audit_Memorandum_C101.docx"
            if cand.exists():
                return (cand, DeliverableFormat.DOCX, cand.name)
            docx_files = sorted(self.format_dirs[DeliverableFormat.DOCX].glob("*.docx"), key=lambda p: p.stat().st_mtime, reverse=True)
            if docx_files:
                return (docx_files[0], DeliverableFormat.DOCX, docx_files[0].name)

        if "workbook" in id_lower or id_lower == "art-c101-workbook":
            cand = deliv_dir / "C101_API570_Corrosion_Calculation_Sheet.xlsx"
            if cand.exists():
                return (cand, DeliverableFormat.XLSX, cand.name)
            xlsx_files = sorted(self.format_dirs[DeliverableFormat.XLSX].glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
            if xlsx_files:
                return (xlsx_files[0], DeliverableFormat.XLSX, xlsx_files[0].name)

        # 3. Direct filename match across format dirs and deliverables dir
        all_dirs = [deliv_dir] + list(self.format_dirs.values())
        for d in all_dirs:
            if not d.exists():
                continue
            cand = d / identifier
            if cand.exists() and cand.is_file():
                ext = cand.suffix.lstrip(".").lower()
                try:
                    fmt = DeliverableFormat(ext)
                except ValueError:
                    fmt = DeliverableFormat.DOCX
                return (cand, fmt, cand.name)

        # 4. Search by substring / task_id / hash in filename
        clean_id = "".join(c for c in identifier if c.isalnum() or c in ("-", "_")).lower()
        chunks = [clean_id]
        if "-" in clean_id:
            chunks.extend(clean_id.split("-"))

        for chunk in chunks:
            if len(chunk) < 4:
                continue
            for fmt, fdir in self.format_dirs.items():
                if not fdir.exists():
                    continue
                for f in fdir.glob(f"*.{fmt.value}"):
                    if chunk in f.name.lower():
                        return (f, fmt, f.name)

        # 5. Format fallback if identifier starts or ends with format prefix
        for fmt in DeliverableFormat:
            if id_lower.startswith(f"{fmt.value}_") or id_lower.endswith(f".{fmt.value}"):
                fdir = self.format_dirs[fmt]
                if fdir.exists():
                    files = sorted(fdir.glob(f"*.{fmt.value}"), key=lambda p: p.stat().st_mtime, reverse=True)
                    if files:
                        return (files[0], fmt, files[0].name)

        return None

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
