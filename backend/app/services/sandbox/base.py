"""
SIH26117 — Portable Sandbox Execution Interface
Defines the boundary for isolated local code execution.
Swappable between local subprocess, Docker container, or hardened on-premise environments.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pydantic import BaseModel


class SandboxExecutionResult(BaseModel):
    """Result of sandboxed code execution."""

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False
    artifacts_created: List[str] = []


class SandboxExecutor(ABC):
    """
    Abstract execution boundary for safe code evaluation.
    Isolates application business logic from platform-specific process management.
    """

    @abstractmethod
    async def execute_python(
        self,
        code: str,
        timeout_seconds: int = 15,
        environment_vars: Optional[Dict[str, str]] = None,
    ) -> SandboxExecutionResult:
        """
        Execute Python code within the configured containment boundary.
        """
        pass
