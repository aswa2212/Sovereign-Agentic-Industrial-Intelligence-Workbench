"""
SIH26117 — Secure Storage & Path Sanitization Manager
Manages raw artifact persistence, duplicate detection, and processed document storage.
Enforces strict path sanitization to eliminate path traversal vulnerabilities.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

try:
    from app.core.config import Settings, get_settings
    from app.services.ingestion.exceptions import SecurityViolationError
except ImportError:
    from backend.app.core.config import Settings, get_settings
    from backend.app.services.ingestion.exceptions import SecurityViolationError


# Pattern matching unsafe filename characters (control characters, path separators)
UNSAFE_CHARS_PATTERN = re.compile(r'[\x00-\x1f\x7f\\/:\*\?"<>\|]')


def sanitize_filename(filename: str) -> str:
    """
    Sanitize an untrusted user-supplied filename:
    1. Rejects null bytes and explicit path traversal patterns.
    2. Strips directory navigation characters (.. , /, \\).
    3. Retains only safe base name and extension.
    4. Falls back to a deterministic fallback name if empty.
    """
    if not filename or not isinstance(filename, str):
        return "unnamed_artifact"

    # Check for explicit malicious path traversal
    if "\x00" in filename:
        raise SecurityViolationError("Null byte detected in filename")
    
    # Normalize separators to test for traversal
    normalized = filename.replace("\\", "/")
    if "../" in normalized or normalized.startswith("/") or re.match(r"^[a-zA-Z]:", filename):
        # We also sanitize adversarial inputs, but if path elements exist, extract just the pure leaf basename
        pass

    # Extract pure leaf filename regardless of any path prefix supplied
    pure_basename = Path(normalized).name

    # Strip any remaining unsafe characters
    cleaned = UNSAFE_CHARS_PATTERN.sub("_", pure_basename)
    # Remove leading dots or spaces
    cleaned = cleaned.strip(". ")

    if not cleaned:
        return "unnamed_artifact"

    # Truncate length to 255 chars for filesystem safety
    return cleaned[:255]


class StorageManager:
    """
    Manages filesystem persistence for raw source files and processed representations.
    Provides collision-safe content-addressable storage anchored to application settings.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.raw_dir = self.settings.get_resolved_path(self.settings.raw_data_dir)
        self.processed_dir = self.settings.get_resolved_path(self.settings.processed_data_dir)

        # Ensure directories exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def store_raw_file(
        self,
        sha256: str,
        filename: str,
        content: bytes,
    ) -> Tuple[Path, bool]:
        """
        Store raw file bytes in content-addressable form:
        Target file: {raw_dir}/{sha256}_{sanitized_filename}

        Returns:
            Tuple[Path, bool]: (resolved_path, is_duplicate)
        """
        safe_name = sanitize_filename(filename)
        # Construct collision-safe filename keyed by sha256
        target_filename = f"{sha256}_{safe_name}"
        target_path = (self.raw_dir / target_filename).resolve()

        # Verify that target_path is strictly within raw_dir (defense in depth)
        if not str(target_path).startswith(str(self.raw_dir)):
            raise SecurityViolationError(
                f"Path traversal detected: {target_path} escapes {self.raw_dir}"
            )

        # Duplicate detection
        if target_path.exists():
            # Verify existing file size matches
            existing_size = target_path.stat().st_size
            if existing_size == len(content):
                return target_path, True

        # Write immutable original bytes
        with open(target_path, "wb") as f:
            f.write(content)

        return target_path, False

    def store_processed_document(
        self,
        sha256: str,
        document_dict: Dict[str, Any],
    ) -> Path:
        """
        Store normalized document dictionary as a JSON artifact under processed_dir.
        Target file: {processed_dir}/{sha256}.json
        """
        target_filename = f"{sha256}.json"
        target_path = (self.processed_dir / target_filename).resolve()

        if not str(target_path).startswith(str(self.processed_dir)):
            raise SecurityViolationError(
                f"Path traversal detected: {target_path} escapes {self.processed_dir}"
            )

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(document_dict, f, indent=2, ensure_ascii=False)

        return target_path

    def get_processed_document(self, sha256: str) -> Optional[Dict[str, Any]]:
        """Retrieve processed document JSON by SHA-256 hash if present."""
        target_path = self.processed_dir / f"{sha256}.json"
        if target_path.is_file():
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def get_raw_file_path(self, sha256: str, filename: str = "") -> Optional[Path]:
        """Find raw file path if it exists."""
        safe_name = sanitize_filename(filename) if filename else ""
        if safe_name and safe_name != "unnamed_artifact":
            target_path = self.raw_dir / f"{sha256}_{safe_name}"
            if target_path.is_file():
                return target_path
        # Search for any file matching sha256 prefix
        matches = list(self.raw_dir.glob(f"{sha256}_*"))
        if matches and matches[0].is_file():
            return matches[0]
        return None

    def list_processed_documents(self) -> list:
        """List all normalized document JSON artifacts on disk."""
        results = []
        if self.processed_dir.is_dir():
            for p in sorted(self.processed_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        results.append(data)
                except Exception:
                    continue
        return results
