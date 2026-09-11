"""
SIH26117 — Phase 8 Sandboxed Tool Execution Security & Unit Test Suite
Verifies tool whitelist enforcement, deterministic calculations, timeout guardrails,
output/input limits, environment variable scrubbing, path traversal defense, and API endpoints.
"""

import asyncio
import json
import os
from pathlib import Path
import time
import pytest
from fastapi.testclient import TestClient

try:
    from app.core.config import get_settings
    from app.main import app
    from app.services.agent.models import AgentContext
    from app.services.agent.tools import SandboxedCalculationTool
    from app.services.sandbox.base import (
        ExecutionStatus,
        PolicyViolationError,
        ResourceLimitError,
        ToolExecutionRequest,
        ToolExecutionResult,
        ToolNotFoundError,
        ToolValidationError,
    )
    from app.services.sandbox.policy import SandboxPolicy
    from app.services.sandbox.subprocess_executor import SubprocessSandboxExecutor
    from app.services.sandbox.tools import (
        CorrosionRateCalculation,
        MinimumWallThicknessCheck,
        ToolWhitelistRegistry,
    )
    from app.services.sandbox.validators import PythonASTPreScreener, validate_tool_payload
except ImportError:
    from backend.app.core.config import get_settings
    from backend.app.main import app
    from backend.app.services.agent.models import AgentContext
    from backend.app.services.agent.tools import SandboxedCalculationTool
    from backend.app.services.sandbox.base import (
        ExecutionStatus,
        PolicyViolationError,
        ResourceLimitError,
        ToolExecutionRequest,
        ToolExecutionResult,
        ToolNotFoundError,
        ToolValidationError,
    )
    from backend.app.services.sandbox.policy import SandboxPolicy
    from backend.app.services.sandbox.subprocess_executor import SubprocessSandboxExecutor
    from backend.app.services.sandbox.tools import (
        CorrosionRateCalculation,
        MinimumWallThicknessCheck,
        ToolWhitelistRegistry,
    )
    from backend.app.services.sandbox.validators import PythonASTPreScreener, validate_tool_payload

client = TestClient(app)


# ── 1. Deterministic Engineering Tools Tests ─────────────────────────────────

class TestDeterministicTools:
    """Verifies exact deterministic calculation logic for approved tools."""

    def test_minimum_wall_thickness_pass(self):
        tool = MinimumWallThicknessCheck()
        res = tool.execute({"measured_thickness_mm": 5.0, "minimum_required_mm": 3.2})
        assert res["margin_mm"] == 1.8
        assert res["status"] == "PASS"
        assert res["is_acceptable"] is True

    def test_minimum_wall_thickness_monitor(self):
        tool = MinimumWallThicknessCheck()
        res = tool.execute({"measured_thickness_mm": 3.4, "minimum_required_mm": 3.2})
        assert res["margin_mm"] == 0.2
        assert res["status"] == "MONITOR"
        assert res["is_acceptable"] is True

    def test_minimum_wall_thickness_retire(self):
        tool = MinimumWallThicknessCheck()
        res = tool.execute({"measured_thickness_mm": 3.0, "minimum_required_mm": 3.2})
        assert res["margin_mm"] == -0.2
        assert res["status"] == "RETIRE"
        assert res["is_acceptable"] is False

    def test_minimum_wall_thickness_invalid_negative_values(self):
        tool = MinimumWallThicknessCheck()
        with pytest.raises(ToolValidationError) as exc:
            tool.execute({"measured_thickness_mm": -2.0, "minimum_required_mm": 3.2})
        assert "strictly positive" in str(exc.value)

    def test_corrosion_rate_normal_loss(self):
        tool = CorrosionRateCalculation()
        res = tool.execute({
            "previous_thickness_mm": 10.0,
            "current_thickness_mm": 9.0,
            "elapsed_time_years": 2.0,
            "minimum_required_mm": 3.0,
        })
        assert res["metal_loss_mm"] == 1.0
        assert res["corrosion_rate_mm_per_year"] == 0.5
        assert res["remaining_life_years"] == 12.0  # (9.0 - 3.0) / 0.5 = 12.0
        assert res["remaining_life_status"] == "CALCULATED"

    def test_corrosion_rate_zero_loss_stable(self):
        tool = CorrosionRateCalculation()
        res = tool.execute({
            "previous_thickness_mm": 8.5,
            "current_thickness_mm": 8.5,
            "elapsed_time_years": 3.0,
            "minimum_required_mm": 3.0,
        })
        assert res["metal_loss_mm"] == 0.0
        assert res["corrosion_rate_mm_per_year"] == 0.0
        assert res["remaining_life_years"] is None
        assert res["remaining_life_status"] == "STABLE"

    def test_corrosion_rate_zero_elapsed_time_rejected(self):
        tool = CorrosionRateCalculation()
        with pytest.raises(ToolValidationError):
            tool.execute({
                "previous_thickness_mm": 10.0,
                "current_thickness_mm": 9.0,
                "elapsed_time_years": 0.0,
            })


# ── 2. Whitelist Registry Tests ───────────────────────────────────────────────

class TestToolWhitelistRegistry:
    """Verifies that unknown tools and shell attempts fail closed."""

    def test_whitelist_contains_approved_tools(self):
        reg = ToolWhitelistRegistry()
        tools = reg.list_tools()
        assert "minimum_wall_thickness_check" in tools
        assert "corrosion_rate_calc" in tools

    def test_whitelist_rejects_arbitrary_commands(self):
        reg = ToolWhitelistRegistry()
        for forbidden in ["shell", "cmd", "powershell", "bash", "sh", "python", "system", "exec", "dir", "rm"]:
            assert not reg.is_whitelisted(forbidden)
            with pytest.raises(ToolNotFoundError):
                reg.get_tool(forbidden)


# ── 3. Sandbox Policy & Filesystem Defense Tests ──────────────────────────────

class TestSandboxPolicy:
    """Verifies path traversal blocking, resource ceilings, and environment scrubbing."""

    def test_resolve_safe_scratch_path_valid(self, tmp_path):
        policy = SandboxPolicy(scratch_dir=tmp_path)
        safe = policy.resolve_safe_scratch_path("output.json")
        assert safe == (tmp_path / "output.json").resolve()

    def test_resolve_path_traversal_relative_rejected(self, tmp_path):
        policy = SandboxPolicy(scratch_dir=tmp_path)
        with pytest.raises(PolicyViolationError) as exc:
            policy.resolve_safe_scratch_path("../secret.env")
        assert "Path traversal detected" in str(exc.value)

    def test_resolve_path_traversal_parent_escape_rejected(self, tmp_path):
        policy = SandboxPolicy(scratch_dir=tmp_path)
        with pytest.raises(PolicyViolationError):
            policy.resolve_safe_scratch_path("subfolder/../../passwords.txt")

    def test_resolve_absolute_path_outside_scratch_rejected(self, tmp_path):
        policy = SandboxPolicy(scratch_dir=tmp_path)
        outside_path = Path.cwd().resolve()
        with pytest.raises(PolicyViolationError):
            policy.resolve_safe_scratch_path(str(outside_path))

    def test_environment_variable_scrubbing(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-secret123")
        monkeypatch.setenv("DB_PASSWORD", "supersecret")
        monkeypatch.setenv("AUTH_TOKEN", "bearer-token")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "awssecret")
        monkeypatch.setenv("SAFE_TEST_VAR", "visible")

        policy = SandboxPolicy()
        clean_env = policy.build_clean_environment()

        # Sensitive variables must be scrubbed
        assert "OPENAI_API_KEY" not in clean_env
        assert "DB_PASSWORD" not in clean_env
        assert "AUTH_TOKEN" not in clean_env
        assert "AWS_SECRET_ACCESS_KEY" not in clean_env

        # Hardening flags present
        assert clean_env.get("PYTHONUNBUFFERED") == "1"
        assert clean_env.get("PYTHONDONTWRITEBYTECODE") == "1"

    def test_input_size_limit_enforced(self):
        policy = SandboxPolicy(max_input_bytes=100)
        policy.validate_input_size(50)  # within limit
        with pytest.raises(ResourceLimitError):
            policy.validate_input_size(150)  # exceeds limit


# ── 4. AST Pre-Screener Tests (Defense-in-Depth) ──────────────────────────────

class TestASTPreScreener:
    """Verifies static code pre-screener blocks forbidden modules and dynamic eval."""

    def test_safe_math_code_allowed(self):
        safe_code = "import math\nx = math.sqrt(16.0)\n"
        PythonASTPreScreener.screen_code(safe_code)  # Must not raise

    def test_os_module_blocked(self):
        with pytest.raises(PolicyViolationError) as exc:
            PythonASTPreScreener.screen_code("import os\nos.system('echo 1')")
        assert "Prohibited module 'os'" in str(exc.value)

    def test_subprocess_module_blocked(self):
        with pytest.raises(PolicyViolationError):
            PythonASTPreScreener.screen_code("from subprocess import Popen")

    def test_socket_module_blocked(self):
        with pytest.raises(PolicyViolationError) as exc:
            PythonASTPreScreener.screen_code("import socket\ns = socket.socket()")
        assert "Prohibited module 'socket'" in str(exc.value)

    def test_urllib_requests_blocked(self):
        with pytest.raises(PolicyViolationError):
            PythonASTPreScreener.screen_code("import urllib.request")
        with pytest.raises(PolicyViolationError):
            PythonASTPreScreener.screen_code("import requests")

    def test_eval_exec_calls_blocked(self):
        with pytest.raises(PolicyViolationError) as exc:
            PythonASTPreScreener.screen_code("x = eval('2 + 2')")
        assert "Dynamic evaluation call 'eval'" in str(exc.value)

        with pytest.raises(PolicyViolationError) as exc:
            PythonASTPreScreener.screen_code("exec('import sys')")
        assert "Dynamic evaluation call 'exec'" in str(exc.value)


# ── 5. Subprocess Sandbox Executor Tests ──────────────────────────────────────

class TestSubprocessExecutor:
    """Verifies process isolation, timeout handling, and structured results."""

    @pytest.mark.anyio
    async def test_subprocess_execute_wall_thickness_tool_success(self, tmp_path):
        policy = SandboxPolicy(scratch_dir=tmp_path)
        executor = SubprocessSandboxExecutor(policy=policy)

        req = ToolExecutionRequest(
            tool_name="minimum_wall_thickness_check",
            input={"measured_thickness_mm": 4.5, "minimum_required_mm": 3.2},
            execution_mode="subprocess",
        )
        res = await executor.execute_tool(req)
        assert res.status == ExecutionStatus.SUCCESS
        assert res.exit_code == 0
        assert res.structured_result is not None
        assert res.structured_result["margin_mm"] == 1.3
        assert res.structured_result["status"] == "PASS"

    @pytest.mark.anyio
    async def test_subprocess_execute_corrosion_rate_tool_success(self, tmp_path):
        policy = SandboxPolicy(scratch_dir=tmp_path)
        executor = SubprocessSandboxExecutor(policy=policy)

        req = ToolExecutionRequest(
            tool_name="corrosion_rate_calc",
            input={
                "previous_thickness_mm": 12.0,
                "current_thickness_mm": 11.0,
                "elapsed_time_years": 2.0,
                "minimum_required_mm": 4.0,
            },
            execution_mode="subprocess",
        )
        res = await executor.execute_tool(req)

        assert res.status == ExecutionStatus.SUCCESS
        assert res.structured_result["corrosion_rate_mm_per_year"] == 0.5
        assert res.structured_result["remaining_life_years"] == 14.0

    @pytest.mark.anyio
    async def test_subprocess_execute_unknown_tool_fails_closed(self, tmp_path):
        policy = SandboxPolicy(scratch_dir=tmp_path)
        executor = SubprocessSandboxExecutor(policy=policy)

        req = ToolExecutionRequest(
            tool_name="malicious_shell_exec",
            input={"command": "whoami"},
        )
        res = await executor.execute_tool(req)

        assert res.status == ExecutionStatus.POLICY_DENIED
        assert "not in the approved sandbox whitelist" in res.error_message

    @pytest.mark.anyio
    async def test_subprocess_execute_invalid_payload_returns_validation_failed(self, tmp_path):
        policy = SandboxPolicy(scratch_dir=tmp_path)
        executor = SubprocessSandboxExecutor(policy=policy)

        req = ToolExecutionRequest(
            tool_name="minimum_wall_thickness_check",
            input={"measured_thickness_mm": -5.0, "minimum_required_mm": 3.2},
            execution_mode="subprocess",
        )
        res = await executor.execute_tool(req)

        assert res.status == ExecutionStatus.VALIDATION_FAILED
        assert res.error_message is not None

    @pytest.mark.anyio
    async def test_subprocess_timeout_kills_process_and_returns_timeout(self, tmp_path):
        policy = SandboxPolicy(scratch_dir=tmp_path)
        executor = SubprocessSandboxExecutor(policy=policy)

        # Use legacy execute_python with an infinite loop and 1.0s timeout
        infinite_loop = "import time\nwhile True:\n    time.sleep(0.1)\n"
        result = await executor.execute_python(infinite_loop, timeout_seconds=1)

        assert result.timed_out is True
        assert result.exit_code == -1
        assert "timed out" in result.stderr.lower()

    @pytest.mark.anyio
    async def test_subprocess_legacy_execute_python_prohibited_module_blocked(self, tmp_path):
        policy = SandboxPolicy(scratch_dir=tmp_path)
        executor = SubprocessSandboxExecutor(policy=policy)

        bad_code = "import socket\ns = socket.socket()\n"
        result = await executor.execute_python(bad_code, timeout_seconds=5)

        assert result.exit_code == 1
        assert "Prohibited module 'socket'" in result.stderr

    @pytest.mark.anyio
    async def test_sandbox_disabled_policy_denies_execution(self, tmp_path):
        policy = SandboxPolicy(scratch_dir=tmp_path, enabled=False)
        executor = SubprocessSandboxExecutor(policy=policy)

        req = ToolExecutionRequest(
            tool_name="minimum_wall_thickness_check",
            input={"measured_thickness_mm": 5.0, "minimum_required_mm": 3.2},
        )
        res = await executor.execute_tool(req)

        assert res.status == ExecutionStatus.POLICY_DENIED
        assert "disabled by policy" in res.error_message

    @pytest.mark.anyio
    async def test_deterministic_repeated_execution(self, tmp_path):
        policy = SandboxPolicy(scratch_dir=tmp_path)
        executor = SubprocessSandboxExecutor(policy=policy)

        req = ToolExecutionRequest(
            tool_name="minimum_wall_thickness_check",
            input={"measured_thickness_mm": 4.0, "minimum_required_mm": 3.2},
            execution_mode="in_process",
        )
        res1 = await executor.execute_tool(req)
        res2 = await executor.execute_tool(req)

        assert res1.status == ExecutionStatus.SUCCESS
        assert res1.structured_result == res2.structured_result


# ── 6. Agent Integration Boundary Tests ──────────────────────────────────────

class TestAgentToolIntegration:
    """Verifies that the Agent can consume sandboxed tools via the AgentTool abstraction."""

    @pytest.mark.anyio
    async def test_sandboxed_calculation_tool_integration(self):
        tool = SandboxedCalculationTool()
        ctx = AgentContext(task_id="test_task", user_request="Check wall thickness")

        out = await tool.execute(
            {
                "tool_name": "minimum_wall_thickness_check",
                "measured_thickness_mm": 6.2,
                "minimum_required_mm": 3.2,
                "execution_mode": "in_process",
            },
            ctx,
        )

        assert out["margin_mm"] == 3.0
        assert out["status"] == "PASS"
        assert out["is_acceptable"] is True


# ── 7. REST API Endpoints Tests ───────────────────────────────────────────────

class TestSandboxAPI:
    """Verifies /api/v1/sandbox/execute and /api/v1/sandbox/status endpoints."""

    def test_api_sandbox_status(self):
        res = client.get("/api/v1/sandbox/status")
        assert res.status_code == 200
        data = res.json()
        assert data["enabled"] is True
        assert "minimum_wall_thickness_check" in data["allowed_tools"]
        assert "corrosion_rate_calc" in data["allowed_tools"]
        assert "timeout_seconds" in data["limits"]

    def test_api_sandbox_execute_success(self):
        res = client.post(
            "/api/v1/sandbox/execute",
            json={
                "tool_name": "minimum_wall_thickness_check",
                "input": {"measured_thickness_mm": 4.8, "minimum_required_mm": 3.2},
                "execution_mode": "in_process",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SUCCESS"
        assert data["tool_name"] == "minimum_wall_thickness_check"
        assert data["result"]["margin_mm"] == 1.6
        assert data["result"]["status"] == "PASS"

    def test_api_sandbox_execute_unknown_tool_returns_400(self):
        res = client.post(
            "/api/v1/sandbox/execute",
            json={
                "tool_name": "unapproved_bash_tool",
                "input": {},
            },
        )
        assert res.status_code == 400
        data = res.json()
        assert data["error"]["code"] == "BAD_REQUEST"
        assert "POLICY_DENIED" in data["error"]["message"] or "not in the approved sandbox whitelist" in data["error"]["message"]

    def test_api_sandbox_execute_invalid_numeric_returns_422(self):
        res = client.post(
            "/api/v1/sandbox/execute",
            json={
                "tool_name": "minimum_wall_thickness_check",
                "input": {"measured_thickness_mm": -1.0, "minimum_required_mm": 3.2},
                "execution_mode": "in_process",
            },
        )
        assert res.status_code == 422
        data = res.json()
        assert data["error"]["code"] in ("UNPROCESSABLE_ENTITY", "HTTP_422")
        assert "VALIDATION_FAILED" in data["error"]["message"] or "strictly positive" in data["error"]["message"]
