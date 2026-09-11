"""
SIH26117 — Subprocess Sandbox Executor Implementation
Provides constrained subprocess isolation for whitelisted deterministic tools.
Enforces wall-clock timeout, output size ceilings, and fail-closed security.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
import sys
import time
import uuid
from typing import Any, Dict, Optional

try:
    from app.services.sandbox.base import (
        ExecutionStatus,
        PolicyViolationError,
        ResourceLimitError,
        SandboxExecutionResult,
        SandboxExecutor,
        ToolExecutionRequest,
        ToolExecutionResult,
        ToolExecutor,
        ToolNotFoundError,
        ToolValidationError,
    )
    from app.services.sandbox.policy import SandboxPolicy
    from app.services.sandbox.tools import ToolWhitelistRegistry
    from app.services.sandbox.validators import PythonASTPreScreener
except ImportError:
    from backend.app.services.sandbox.base import (
        ExecutionStatus,
        PolicyViolationError,
        ResourceLimitError,
        SandboxExecutionResult,
        SandboxExecutor,
        ToolExecutionRequest,
        ToolExecutionResult,
        ToolExecutor,
        ToolNotFoundError,
        ToolValidationError,
    )
    from backend.app.services.sandbox.policy import SandboxPolicy
    from backend.app.services.sandbox.tools import ToolWhitelistRegistry
    from backend.app.services.sandbox.validators import PythonASTPreScreener

logger = logging.getLogger(__name__)


class SubprocessSandboxExecutor(SandboxExecutor, ToolExecutor):
    """
    Subprocess-backed sandbox executor for deterministic tools.
    Enforces process isolation, minimal scrubbed environment, and fail-closed security.
    """

    def __init__(
        self,
        policy: Optional[SandboxPolicy] = None,
        registry: Optional[ToolWhitelistRegistry] = None,
    ) -> None:
        self.policy = policy or SandboxPolicy()
        self.registry = registry or ToolWhitelistRegistry()

    async def execute_tool(
        self,
        request: ToolExecutionRequest,
    ) -> ToolExecutionResult:
        """
        Execute a whitelisted tool request within the configured sandbox containment boundary.
        """
        exec_id = uuid.uuid4().hex[:12]
        start_time = time.monotonic()

        # 1. Policy Gate: Check if sandbox is enabled
        if not self.policy.enabled:
            return ToolExecutionResult(
                execution_id=exec_id,
                tool_name=request.tool_name,
                status=ExecutionStatus.POLICY_DENIED,
                error_message="Sandbox execution is disabled by policy.",
                error_category="POLICY_DENIED",
                duration_ms=0.0,
            )

        # 2. Whitelist Gate: Verify tool is approved
        if not self.registry.is_whitelisted(request.tool_name):
            return ToolExecutionResult(
                execution_id=exec_id,
                tool_name=request.tool_name,
                status=ExecutionStatus.POLICY_DENIED,
                error_message=f"Tool '{request.tool_name}' is not in the approved sandbox whitelist.",
                error_category="POLICY_DENIED",
                duration_ms=0.0,
            )

        # 3. Input Size & Serialization Gate
        try:
            payload_str = json.dumps(request.input)
            payload_bytes = payload_str.encode("utf-8")
            self.policy.validate_input_size(len(payload_bytes))
        except ResourceLimitError as e:
            return ToolExecutionResult(
                execution_id=exec_id,
                tool_name=request.tool_name,
                status=ExecutionStatus.RESOURCE_LIMIT,
                error_message=str(e),
                error_category="RESOURCE_LIMIT",
                duration_ms=0.0,
            )
        except Exception as e:
            return ToolExecutionResult(
                execution_id=exec_id,
                tool_name=request.tool_name,
                status=ExecutionStatus.VALIDATION_FAILED,
                error_message=f"Payload serialization failed: {str(e)}",
                error_category="VALIDATION_FAILED",
                duration_ms=0.0,
            )

        # 4. Filesystem Path Gate: Validate allowed files
        if request.allowed_files:
            try:
                for f_path in request.allowed_files:
                    self.policy.resolve_safe_scratch_path(f_path)
            except PolicyViolationError as e:
                return ToolExecutionResult(
                    execution_id=exec_id,
                    tool_name=request.tool_name,
                    status=ExecutionStatus.POLICY_DENIED,
                    error_message=str(e),
                    error_category="POLICY_DENIED",
                    duration_ms=0.0,
                )

        # 5. In-Process Execution Mode (Fast-path / Fallback)
        if request.execution_mode == "in_process":
            try:
                tool = self.registry.get_tool(request.tool_name)
                result = tool.execute(request.input)
                duration_ms = round((time.monotonic() - start_time) * 1000, 2)
                return ToolExecutionResult(
                    execution_id=exec_id,
                    tool_name=request.tool_name,
                    status=ExecutionStatus.SUCCESS,
                    structured_result=result,
                    exit_code=0,
                    duration_ms=duration_ms,
                    provenance={"execution_mode": "in_process", "scratch_dir": str(self.policy.scratch_dir)},
                )
            except ToolValidationError as e:
                duration_ms = round((time.monotonic() - start_time) * 1000, 2)
                return ToolExecutionResult(
                    execution_id=exec_id,
                    tool_name=request.tool_name,
                    status=ExecutionStatus.VALIDATION_FAILED,
                    error_message=str(e),
                    error_category="VALIDATION_FAILED",
                    duration_ms=duration_ms,
                )
            except Exception as e:
                duration_ms = round((time.monotonic() - start_time) * 1000, 2)
                return ToolExecutionResult(
                    execution_id=exec_id,
                    tool_name=request.tool_name,
                    status=ExecutionStatus.EXECUTION_ERROR,
                    error_message=str(e),
                    error_category="EXECUTION_ERROR",
                    duration_ms=duration_ms,
                )

        # 6. Subprocess Execution Mode (Standard Containment)
        timeout = request.timeout_seconds or self.policy.timeout_seconds
        clean_env = self.policy.build_clean_environment()

        # Build command: python -m app.services.sandbox.runner <tool_name>
        cmd = [
            sys.executable,
            "-m",
            "app.services.sandbox.runner",
            request.tool_name,
        ]

        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.policy.scratch_dir),
                env=clean_env,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=payload_bytes),
                timeout=timeout,
            )
            duration_ms = round((time.monotonic() - start_time) * 1000, 2)

            # Enforce output size ceiling
            if len(stdout_bytes) > self.policy.max_output_bytes:
                stdout_bytes = stdout_bytes[: self.policy.max_output_bytes]
            if len(stderr_bytes) > self.policy.max_output_bytes:
                stderr_bytes = stderr_bytes[: self.policy.max_output_bytes]

            stdout_str = stdout_bytes.decode("utf-8", errors="replace")
            stderr_str = stderr_bytes.decode("utf-8", errors="replace")

            if proc.returncode == 0:
                try:
                    structured = json.loads(stdout_str)
                    return ToolExecutionResult(
                        execution_id=exec_id,
                        tool_name=request.tool_name,
                        status=ExecutionStatus.SUCCESS,
                        stdout=stdout_str,
                        stderr=stderr_str,
                        exit_code=0,
                        duration_ms=duration_ms,
                        structured_result=structured,
                        provenance={"backend": "subprocess", "timeout_seconds": timeout},
                    )
                except Exception as e:
                    return ToolExecutionResult(
                        execution_id=exec_id,
                        tool_name=request.tool_name,
                        status=ExecutionStatus.INTERNAL_ERROR,
                        stdout=stdout_str,
                        stderr=f"Output parsing error: {str(e)}",
                        exit_code=proc.returncode,
                        duration_ms=duration_ms,
                    )
            else:
                # Subprocess exited with failure code
                status = ExecutionStatus.EXECUTION_ERROR
                if proc.returncode == 2 or "validation" in stderr_str.lower():
                    status = ExecutionStatus.VALIDATION_FAILED

                return ToolExecutionResult(
                    execution_id=exec_id,
                    tool_name=request.tool_name,
                    status=status,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    exit_code=proc.returncode,
                    duration_ms=duration_ms,
                    error_message=stderr_str.strip() or f"Process exited with code {proc.returncode}",
                    error_category=status.value,
                )

        except asyncio.TimeoutError:
            duration_ms = round((time.monotonic() - start_time) * 1000, 2)
            if proc:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass

            return ToolExecutionResult(
                execution_id=exec_id,
                tool_name=request.tool_name,
                status=ExecutionStatus.TIMEOUT,
                error_message=f"Execution timed out after {timeout} seconds.",
                error_category="TIMEOUT",
                exit_code=-1,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = round((time.monotonic() - start_time) * 1000, 2)
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass

            return ToolExecutionResult(
                execution_id=exec_id,
                tool_name=request.tool_name,
                status=ExecutionStatus.INTERNAL_ERROR,
                error_message=f"Subprocess launcher error: {str(e)}",
                error_category="INTERNAL_ERROR",
                duration_ms=duration_ms,
            )

    async def execute_python(
        self,
        code: str,
        timeout_seconds: int = 15,
        environment_vars: Optional[Dict[str, str]] = None,
    ) -> SandboxExecutionResult:
        """
        Legacy SandboxExecutor contract: executes Python snippet with AST safety pre-screening.
        """
        start_time = time.monotonic()

        # 1. AST Pre-screener Gate
        try:
            PythonASTPreScreener.screen_code(code)
        except PolicyViolationError as e:
            return SandboxExecutionResult(
                exit_code=1,
                stdout="",
                stderr=str(e),
                duration_ms=0.0,
                timed_out=False,
            )

        clean_env = self.policy.build_clean_environment(extra_env=environment_vars)
        cmd = [sys.executable, "-c", code]
        proc = None

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.policy.scratch_dir),
                env=clean_env,
            )

            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout_seconds,
            )
            duration_ms = round((time.monotonic() - start_time) * 1000, 2)

            return SandboxExecutionResult(
                exit_code=proc.returncode,
                stdout=stdout_b.decode("utf-8", errors="replace"),
                stderr=stderr_b.decode("utf-8", errors="replace"),
                duration_ms=duration_ms,
                timed_out=False,
            )

        except asyncio.TimeoutError:
            duration_ms = round((time.monotonic() - start_time) * 1000, 2)
            if proc:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass

            return SandboxExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=f"Execution timed out after {timeout_seconds} seconds.",
                duration_ms=duration_ms,
                timed_out=True,
            )
