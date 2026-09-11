"""
SIH26117 — Portable Sandbox Execution Interface
Defines the boundary for isolated local code execution.
Swappable between local subprocess, Docker container, or hardened on-premise environments.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ExecutionStatus(str, Enum):
    """Execution status outcomes for sandboxed tool execution."""

    SUCCESS = "SUCCESS"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    TIMEOUT = "TIMEOUT"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    POLICY_DENIED = "POLICY_DENIED"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class SandboxExecutionResult(BaseModel):
    """Result of sandboxed code execution (Phase 1 legacy contract)."""

    model_config = ConfigDict(protected_namespaces=())

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False
    artifacts_created: List[str] = Field(default_factory=list)


class ToolExecutionRequest(BaseModel):
    """Strongly-typed request for executing a registered tool in the sandbox."""

    model_config = ConfigDict(protected_namespaces=())

    tool_name: str = Field(..., description="Unique registered name of the whitelisted tool")
    input: Dict[str, Any] = Field(default_factory=dict, description="Structured input payload for tool")
    timeout_seconds: Optional[float] = Field(default=None, description="Optional override timeout in seconds")
    memory_limit_mb: Optional[int] = Field(default=None, description="Optional memory ceiling in MB")
    allowed_files: List[str] = Field(default_factory=list, description="Explicitly allowed input file paths")
    execution_mode: str = Field(default="subprocess", description="Sandbox mode: 'subprocess' | 'in_process'")


class ToolExecutionResult(BaseModel):
    """Comprehensive result of sandboxed tool invocation with audit provenance."""

    model_config = ConfigDict(protected_namespaces=())

    execution_id: str = Field(..., description="Unique execution identifier")
    tool_name: str = Field(..., description="Name of executed tool")
    status: ExecutionStatus = Field(..., description="Structured execution status")
    stdout: str = Field(default="", description="Captured standard output")
    stderr: str = Field(default="", description="Captured standard error")
    exit_code: int = Field(default=0, description="Process exit code")
    duration_ms: float = Field(default=0.0, description="Execution duration in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Human-readable error description")
    error_category: Optional[str] = Field(default=None, description="Categorized failure type")
    structured_result: Optional[Dict[str, Any]] = Field(default=None, description="Typed output payload")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic audit metadata")


class SandboxExecutor(ABC):
    """
    Abstract execution boundary for safe code and tool evaluation.
    Isolates application business logic from platform-specific process management.
    """

    @abstractmethod
    async def execute_python(
        self,
        code: str,
        timeout_seconds: int = 15,
        environment_vars: Optional[Dict[str, str]] = None,
    ) -> SandboxExecutionResult:
        """Execute Python code within the configured containment boundary."""
        pass


class ToolExecutor(ABC):
    """
    Abstract boundary for executing approved tools in a sandboxed runtime.
    """

    @abstractmethod
    async def execute_tool(
        self,
        request: ToolExecutionRequest,
    ) -> ToolExecutionResult:
        """Execute a whitelisted tool request and return structured result."""
        pass


# ── Exception Hierarchy ───────────────────────────────────────────────────────

class SandboxError(Exception):
    """Base exception for all Sandbox subsystem errors."""
    pass


class PolicyViolationError(SandboxError):
    """Raised when an operation violates sandbox policy (unauthorized access, path traversal, forbidden module)."""
    pass


class SandboxTimeoutError(SandboxError):
    """Raised when tool execution exceeds wall-clock timeout."""
    pass


class ToolValidationError(SandboxError):
    """Raised when tool input schema validation fails."""
    pass


class ResourceLimitError(SandboxError):
    """Raised when memory, file size, or output size limits are exceeded."""
    pass


class ToolNotFoundError(SandboxError):
    """Raised when a requested tool is not found in the approved whitelist."""
    pass


class SubprocessExecutionError(SandboxError):
    """Raised when the underlying process fails unexpectedly."""
    pass

