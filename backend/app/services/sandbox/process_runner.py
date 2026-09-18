"""
SIH26117 — Sandbox Process Runner Compatibility Layer
Thin compatibility re-export module satisfying docs/implementation_plan.md naming.
Re-exports SubprocessSandboxExecutor and related execution contracts.
"""

try:
    from app.services.sandbox.subprocess_executor import SubprocessSandboxExecutor
    from app.services.sandbox.base import (
        ExecutionStatus,
        SandboxExecutionResult,
        SandboxExecutor,
        ToolExecutionRequest,
        ToolExecutionResult,
        ToolExecutor,
    )
    from app.services.sandbox.runner import main as runner_main
except ImportError:
    from backend.app.services.sandbox.subprocess_executor import SubprocessSandboxExecutor
    from backend.app.services.sandbox.base import (
        ExecutionStatus,
        SandboxExecutionResult,
        SandboxExecutor,
        ToolExecutionRequest,
        ToolExecutionResult,
        ToolExecutor,
    )
    from backend.app.services.sandbox.runner import main as runner_main

__all__ = [
    "SubprocessSandboxExecutor",
    "SandboxExecutionResult",
    "SandboxExecutor",
    "ToolExecutionRequest",
    "ToolExecutionResult",
    "ToolExecutor",
    "ExecutionStatus",
    "runner_main",
]
