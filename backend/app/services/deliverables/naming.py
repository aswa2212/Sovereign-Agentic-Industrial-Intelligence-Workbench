"""
SIH26117 — Phase 10: Deterministic & Secure Artifact Naming

Provides deterministic, sanitized filename generation and path-traversal prevention.
Guarantees all output files reside strictly inside configured output folders.
"""

import hashlib
import re
from pathlib import Path
from typing import Optional

try:
    from app.services.deliverables.exceptions import PathTraversalSecurityError
    from app.services.deliverables.models import DeliverableFormat
except ImportError:
    from backend.app.services.deliverables.exceptions import PathTraversalSecurityError
    from backend.app.services.deliverables.models import DeliverableFormat


def sanitize_identifier(identifier: str) -> str:
    """
    Sanitizes an input identifier (e.g. equipment_id, task_id) into a safe filesystem string.
    Removes slashes, backslashes, dots, null bytes, and non-alphanumeric characters except hyphen and underscore.
    """
    if not identifier:
        return "unspecified"

    # Normalize whitespace and hyphens
    cleaned = identifier.strip().replace(" ", "_").replace("/", "-").replace("\\", "-")
    # Whitelist characters: a-z, A-Z, 0-9, -, _
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "", cleaned)
    # Avoid leading dashes or empty strings
    cleaned = cleaned.strip("-_. ")
    return cleaned if cleaned else "unspecified"


def generate_artifact_filename(
    equipment_id: str,
    fmt: DeliverableFormat,
    task_id: Optional[str] = None,
    suffix: Optional[str] = None,
) -> str:
    """
    Generates a deterministic, standard MRPL filename for a deliverable artifact.
    Example: C-101_corrosion_audit_7a8f90.docx
    """
    safe_equipment = sanitize_identifier(equipment_id).upper()
    ext = fmt.value.lower()

    if task_id:
        safe_task = sanitize_identifier(task_id)[:8]
        ident_part = f"_{safe_task}"
    elif suffix:
        safe_suffix = sanitize_identifier(suffix)[:8]
        ident_part = f"_{safe_suffix}"
    else:
        # Compute deterministic 6-char hash of equipment_id
        h = hashlib.sha256(safe_equipment.encode("utf-8")).hexdigest()[:6]
        ident_part = f"_{h}"

    return f"{safe_equipment}_corrosion_audit{ident_part}.{ext}"


def resolve_and_verify_output_path(base_dir: Path, filename: str) -> Path:
    """
    Resolves the target file path and strictly verifies that it does not escape base_dir.
    Raises PathTraversalSecurityError if traversal is attempted.
    """
    # Defensive check on filename
    if ".." in filename or "/" in filename or "\\" in filename or "\x00" in filename:
        raise PathTraversalSecurityError(f"Filename contains illegal traversal tokens: '{filename}'")

    base_resolved = base_dir.resolve()
    target_path = (base_resolved / filename).resolve()

    try:
        target_path.relative_to(base_resolved)
    except ValueError:
        raise PathTraversalSecurityError(f"Target path '{target_path}' escapes base directory '{base_resolved}'")

    return target_path
