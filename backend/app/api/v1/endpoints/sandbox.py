"""
SIH26117 — Sandbox REST API Endpoints
Provides POST /api/v1/sandbox/execute and GET /api/v1/sandbox/status.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status

try:
    from app.core.config import get_settings
    from app.schemas.sandbox import (
        SandboxExecuteRequest,
        SandboxExecuteResponse,
        SandboxStatusResponse,
    )
    from app.services.sandbox.base import ExecutionStatus, ToolExecutionRequest
    from app.services.sandbox.subprocess_executor import SubprocessSandboxExecutor
except ImportError:
    from backend.app.core.config import get_settings
    from backend.app.schemas.sandbox import (
        SandboxExecuteRequest,
        SandboxExecuteResponse,
        SandboxStatusResponse,
    )
    from backend.app.services.sandbox.base import ExecutionStatus, ToolExecutionRequest
    from backend.app.services.sandbox.subprocess_executor import SubprocessSandboxExecutor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sandbox", tags=["sandbox"])

_executor_instance: Optional[SubprocessSandboxExecutor] = None


def get_sandbox_executor() -> SubprocessSandboxExecutor:
    """Return singleton SubprocessSandboxExecutor instance."""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = SubprocessSandboxExecutor()
    return _executor_instance


def set_sandbox_executor(executor: SubprocessSandboxExecutor) -> None:
    """Override singleton sandbox executor (useful for test isolation)."""
    global _executor_instance
    _executor_instance = executor


@router.post(
    "/execute",
    response_model=SandboxExecuteResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute a whitelisted deterministic engineering tool within the sandbox",
)
async def execute_sandboxed_tool(req: SandboxExecuteRequest) -> SandboxExecuteResponse:
    """
    Submits an approved tool execution request to the sandbox executor.
    Rejects unregistered tools and unvalidated input payloads.
    """
    executor = get_sandbox_executor()

    # Reject unknown tools immediately before launching process
    if not executor.registry.is_whitelisted(req.tool_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "POLICY_DENIED",
                "message": f"Tool '{req.tool_name}' is not in the approved sandbox whitelist.",
                "allowed_tools": executor.registry.list_tools(),
            },
        )

    tool_req = ToolExecutionRequest(
        tool_name=req.tool_name,
        input=req.input,
        timeout_seconds=req.timeout_seconds,
        execution_mode=req.execution_mode or "subprocess",
    )

    result = await executor.execute_tool(tool_req)

    # If policy denied, return HTTP 403
    if result.status == ExecutionStatus.POLICY_DENIED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "POLICY_DENIED",
                "message": result.error_message or "Sandbox policy violation.",
            },
        )

    # If input validation failed, return HTTP 422
    if result.status == ExecutionStatus.VALIDATION_FAILED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_FAILED",
                "message": result.error_message or "Tool input validation failed.",
            },
        )

    return SandboxExecuteResponse(
        execution_id=result.execution_id,
        tool_name=result.tool_name,
        status=result.status.value,
        duration_ms=result.duration_ms,
        result=result.structured_result,
        error_message=result.error_message,
        error_category=result.error_category,
    )


@router.get(
    "/status",
    response_model=SandboxStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve sandbox health, active backend, and resource ceilings",
)
async def get_sandbox_status() -> SandboxStatusResponse:
    """
    Returns current sandbox operating parameters and allowed tool catalog.
    """
    settings = get_settings()
    executor = get_sandbox_executor()

    return SandboxStatusResponse(
        enabled=executor.policy.enabled,
        backend="SubprocessSandboxExecutor (Windows/Linux development isolation)",
        allowed_tools=executor.registry.list_tools(),
        limits={
            "timeout_seconds": executor.policy.timeout_seconds,
            "memory_limit_mb": executor.policy.memory_limit_mb,
            "max_output_bytes": executor.policy.max_output_bytes,
            "max_input_bytes": executor.policy.max_input_bytes,
            "network_disabled": True,
        },
    )
