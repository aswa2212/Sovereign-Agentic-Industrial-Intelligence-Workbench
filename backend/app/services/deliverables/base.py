"""
SIH26117 — Phase 10: Base Document Builder Abstract Interface

Defines the contract for all deterministic Office deliverable builders.
Every builder must generate the artifact and verify its output integrity.
"""

from abc import ABC, abstractmethod
import hashlib
from pathlib import Path
from typing import Optional

try:
    from app.services.deliverables.models import (
        DeliverableFormat,
        GeneratedArtifact,
        ReportMetadata,
    )
    from app.services.validation.models import CorrosionAuditResult
except ImportError:
    from backend.app.services.deliverables.models import (
        DeliverableFormat,
        GeneratedArtifact,
        ReportMetadata,
    )
    from backend.app.services.validation.models import CorrosionAuditResult


def compute_file_sha256(path: Path) -> str:
    """Computes SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class BaseDocumentBuilder(ABC):
    """Abstract interface for deterministic Office file builders."""

    format: DeliverableFormat

    @abstractmethod
    def build(
        self,
        data: CorrosionAuditResult,
        metadata: ReportMetadata,
        output_path: Path,
    ) -> GeneratedArtifact:
        """
        Synchronously builds the Office artifact from validated engineering data
        and writes it deterministically to output_path.
        """
        ...

    @abstractmethod
    def verify_output(self, output_path: Path) -> bool:
        """
        Performs post-generation structural inspection of the generated file.
        Returns True if structurally valid, False or raises OutputVerificationError if invalid.
        """
        ...
