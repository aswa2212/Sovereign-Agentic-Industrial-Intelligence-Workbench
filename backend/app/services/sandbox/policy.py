"""
SIH26117 — Sandbox Security Policy & Isolation Controls
Defines resource ceilings, path traversal defense, and environment variable scrubbing.
"""

import os
from pathlib import Path
import re
from typing import Dict, Optional

try:
    from app.core.config import get_settings
    from app.services.sandbox.base import PolicyViolationError, ResourceLimitError
except ImportError:
    from backend.app.core.config import get_settings
    from backend.app.services.sandbox.base import PolicyViolationError, ResourceLimitError


# Sensitive patterns that must never be exposed to sandboxed execution
SENSITIVE_ENV_REGEX = re.compile(
    r"(KEY|SECRET|PASSWORD|PASSWD|TOKEN|CREDENTIAL|AUTH|DATABASE|URL|CONN|PRIVATE|API|AWS|GCP|AZURE|OLLAMA)",
    re.IGNORECASE,
)

# Standard safe environment variables required for basic runtime functionality
SAFE_ENV_WHITELIST = {
    "PATH",
    "SYSTEMROOT",
    "SYSTEMDRIVE",
    "COMSPEC",
    "PATHEXT",
    "PYTHONPATH",
    "PYTHONHOME",
    "PYTHONIOENCODING",
    "LANG",
    "LC_ALL",
    "TEMP",
    "TMP",
}


class SandboxPolicy:
    """
    Enforces operational boundaries and resource limits for sandboxed execution.
    """

    def __init__(
        self,
        timeout_seconds: Optional[float] = None,
        memory_limit_mb: Optional[int] = None,
        max_output_bytes: Optional[int] = None,
        max_input_bytes: Optional[int] = None,
        scratch_dir: Optional[Path] = None,
        enabled: Optional[bool] = None,
    ) -> None:
        settings = get_settings()
        self.enabled = enabled if enabled is not None else settings.sandbox_enabled
        self.timeout_seconds = timeout_seconds or settings.sandbox_timeout_seconds
        self.memory_limit_mb = memory_limit_mb or settings.sandbox_memory_limit_mb
        self.max_output_bytes = max_output_bytes or settings.sandbox_max_output_bytes
        self.max_input_bytes = max_input_bytes or settings.sandbox_max_input_bytes

        # Resolve scratch directory
        base_scratch = scratch_dir or Path(settings.sandbox_scratch_dir)
        if not base_scratch.is_absolute():
            # Place relative to backend or project directory
            base_scratch = Path.cwd() / base_scratch
        self.scratch_dir = base_scratch.resolve()
        self.scratch_dir.mkdir(parents=True, exist_ok=True)

    def validate_input_size(self, input_bytes_len: int) -> None:
        """Ensure input payload does not exceed ceiling."""
        if input_bytes_len > self.max_input_bytes:
            raise ResourceLimitError(
                f"Input payload size ({input_bytes_len} bytes) exceeds sandbox limit of {self.max_input_bytes} bytes."
            )

    def resolve_safe_scratch_path(self, relative_path: str) -> Path:
        """
        Resolves a path strictly within the sandbox scratch folder.
        Rejects directory traversal (../ or ..\\) and absolute paths outside the scratch folder.
        """
        clean_path = str(relative_path).strip()

        # Reject obvious traversal sequences
        if ".." in clean_path or clean_path.startswith("/") or clean_path.startswith("\\"):
            # Check if it's already an absolute path
            as_path = Path(clean_path)
            if as_path.is_absolute():
                resolved = as_path.resolve()
                try:
                    resolved.relative_to(self.scratch_dir)
                    return resolved
                except ValueError:
                    raise PolicyViolationError(
                        f"Access denied: Path '{clean_path}' lies outside the sandbox scratch directory."
                    )
            raise PolicyViolationError(
                f"Path traversal detected: '{clean_path}' is forbidden."
            )

        resolved = (self.scratch_dir / clean_path).resolve()
        try:
            resolved.relative_to(self.scratch_dir)
        except ValueError:
            raise PolicyViolationError(
                f"Path traversal detected: Path '{clean_path}' escapes sandbox scratch directory."
            )

        return resolved

    def build_clean_environment(self, extra_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Constructs a minimal, scrubbed environment dictionary.
        Explicitly scrubs all credentials, secrets, and API tokens.
        """
        clean_env: Dict[str, str] = {}

        # Copy safe host variables
        for key, value in os.environ.items():
            if key.upper() in SAFE_ENV_WHITELIST:
                if not SENSITIVE_ENV_REGEX.search(key):
                    clean_env[key] = value

        # Standard Python hardening flags
        clean_env["PYTHONUNBUFFERED"] = "1"
        clean_env["PYTHONDONTWRITEBYTECODE"] = "1"
        clean_env["PYTHONUTF8"] = "1"

        # Ensure PYTHONPATH includes backend root so runner can load in isolated scratch cwd
        backend_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
        project_root = str(Path(__file__).resolve().parent.parent.parent.parent.parent)
        paths_to_add = [backend_dir, project_root]
        existing_pp = clean_env.get("PYTHONPATH", "")
        if existing_pp:
            paths_to_add.append(existing_pp)
        clean_env["PYTHONPATH"] = os.pathsep.join(paths_to_add)

        # Apply allowed extras if provided
        if extra_env:
            for k, v in extra_env.items():
                if not SENSITIVE_ENV_REGEX.search(k):
                    clean_env[k] = str(v)

        return clean_env
