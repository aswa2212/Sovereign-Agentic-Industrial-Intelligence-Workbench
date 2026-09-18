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
    from app.services.agent.base import AgentState, ToolExecutionError
    from app.services.agent.models import AgentContext, Plan, PlanStep, StepObservation
    from app.services.agent.orchestrator import AgentStateMachineOrchestrator
    from app.services.agent.planner import Planner
    from app.services.agent.tools import SandboxedCalculationTool, ToolRegistry
    from app.services.ingestion.evidence import EngineeringEvidence
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
    from backend.app.services.agent.base import AgentState, ToolExecutionError
    from backend.app.services.agent.models import AgentContext, Plan, PlanStep, StepObservation
    from backend.app.services.agent.orchestrator import AgentStateMachineOrchestrator
    from backend.app.services.agent.planner import Planner
    from backend.app.services.agent.tools import SandboxedCalculationTool, ToolRegistry
    from backend.app.services.ingestion.evidence import EngineeringEvidence
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


# ── 8. EngineeringEvidence Authority Tests ────────────────────────────────────

class TestEngineeringEvidenceAuthority:
    """Verifies that context.evidence remains authoritative over payload/prompt values."""

    @pytest.mark.anyio
    async def test_conflicting_payload_measurement_evidence_wins(self):
        """Prompt/payload passes 99.9mm (PASS), but authoritative evidence is 3.0mm (RETIRE). Evidence must win."""
        tool = SandboxedCalculationTool()
        evidence_dict = {
            "source_filename": "UT_Report_V101.pdf",
            "source_sha256": "abcdef1234567890",
            "current_thickness_mm": 3.0,
            "current_thickness_source": "DOCUMENT_TABLE_ROW_4",
            "minimum_required_thickness_mm": 3.2,
            "minimum_thickness_source": "API_570_TABLE_4",
        }
        ctx = AgentContext(
            task_id="ev_auth_task",
            user_request="Verify thickness",
            evidence=evidence_dict,
        )

        out = await tool.execute(
            {
                "tool_name": "minimum_wall_thickness_check",
                "measured_thickness_mm": 99.9,  # Conflicting payload
                "minimum_required_mm": 1.0,     # Conflicting minimum
                "execution_mode": "in_process",
            },
            ctx,
        )

        # Authoritative evidence must win: 3.0 - 3.2 = -0.2 (RETIRE)
        assert out["margin_mm"] == -0.2
        assert out["status"] == "RETIRE"
        assert out["is_acceptable"] is False
        assert out["evidence_authoritative"] is True
        assert out["evidence_source"] == "UT_Report_V101.pdf"
        assert out["evidence_sha256"] == "abcdef1234567890"
        assert out["field_provenance"]["measured_thickness_mm"] == "DOCUMENT_TABLE_ROW_4"
        assert out["field_provenance"]["minimum_required_mm"] == "API_570_TABLE_4"

    @pytest.mark.anyio
    async def test_corrosion_rate_with_evidence_authority(self):
        """Authoritative evidence fields override corrosion rate calculation inputs."""
        tool = SandboxedCalculationTool()
        evidence_dict = {
            "source_filename": "Piping_UT_Record.pdf",
            "source_sha256": "deadbeef98765432",
            "current_thickness_mm": 8.0,
            "current_thickness_source": "INSPECTION_TABLE",
            "nominal_thickness_mm": 10.0,
            "nominal_thickness_source": "DESIGN_SPEC_P101",
            "elapsed_time_years": 4.0,
            "elapsed_time_source": "OPERATING_LOGS",
            "minimum_required_thickness_mm": 4.0,
            "minimum_thickness_source": "CORROSION_ALLOWANCE_TABLE",
        }
        ctx = AgentContext(
            task_id="ev_corrosion_task",
            user_request="Calculate corrosion rate",
            evidence=evidence_dict,
        )

        # Conflicting payload claiming zero loss over 100 years
        out = await tool.execute(
            {
                "tool_name": "corrosion_rate_calc",
                "previous_thickness_mm": 50.0,
                "current_thickness_mm": 50.0,
                "elapsed_time_years": 100.0,
                "minimum_required_mm": 1.0,
                "execution_mode": "in_process",
            },
            ctx,
        )

        # Evidence values: metal_loss = 10.0 - 8.0 = 2.0; rate = 2.0 / 4.0 = 0.5 mm/yr; remaining = (8.0 - 4.0) / 0.5 = 8.0 yrs
        assert out["metal_loss_mm"] == 2.0
        assert out["corrosion_rate_mm_per_year"] == 0.5
        assert out["remaining_life_years"] == 8.0
        assert out["evidence_authoritative"] is True
        assert out["field_provenance"]["current_thickness_mm"] == "INSPECTION_TABLE"
        assert out["field_provenance"]["previous_thickness_mm"] == "DESIGN_SPEC_P101"
        assert out["field_provenance"]["elapsed_time_years"] == "OPERATING_LOGS"
        assert out["field_provenance"]["minimum_required_mm"] == "CORROSION_ALLOWANCE_TABLE"

    @pytest.mark.anyio
    async def test_engineering_evidence_pydantic_model_supported(self):
        """Verifies that EngineeringEvidence Pydantic model is dumped and handled seamlessly."""
        tool = SandboxedCalculationTool()
        evidence_model = EngineeringEvidence(
            equipment_id="V-102",
            source_filename="V102_Report.pdf",
            source_sha256="1122334455667788",
            current_thickness_mm=5.5,
            current_thickness_source="TABLE_4",
            minimum_required_thickness_mm=3.5,
            minimum_thickness_source="CODE_MIN",
        )
        ctx = AgentContext(
            task_id="model_ev_task",
            user_request="Check V-102",
            evidence=evidence_model.model_dump(),
        )

        out = await tool.execute(
            {
                "tool_name": "minimum_wall_thickness_check",
                "measured_thickness_mm": 9.9,
                "minimum_required_mm": 1.0,
                "execution_mode": "in_process",
            },
            ctx,
        )
        assert out["margin_mm"] == 2.0
        assert out["status"] == "PASS"
        assert out["evidence_authoritative"] is True
        assert out["field_provenance"]["measured_thickness_mm"] == "TABLE_4"
        assert out["field_provenance"]["minimum_required_mm"] == "CODE_MIN"

    @pytest.mark.anyio
    async def test_missing_required_evidence_fails_closed(self):
        """Missing required thickness fields with no evidence and empty payload fails closed without fallback."""
        tool = SandboxedCalculationTool()
        ctx = AgentContext(task_id="missing_task", user_request="Empty test", evidence=None)

        with pytest.raises(ToolExecutionError) as exc_info:
            await tool.execute(
                {
                    "tool_name": "minimum_wall_thickness_check",
                    "execution_mode": "in_process",
                },
                ctx,
            )
        assert "VALIDATION_FAILED" in str(exc_info.value) or "failed" in str(exc_info.value).lower()


# ── 9. Phase 7 Agent State Machine Integration Tests ─────────────────────────

class TestPhase7AgentStateMachineIntegration:
    """Verifies end-to-end integration between Phase 7 Agent State Machine and SandboxedCalculationTool."""

    def test_tool_registry_contains_sandboxed_calculation(self):
        registry = ToolRegistry()
        tool = registry.get_tool("sandboxed_calculation")
        assert tool is not None
        assert isinstance(tool, SandboxedCalculationTool)
        assert tool.name == "sandboxed_calculation"
        assert tool.capability == "sandboxed_calculation"

    @pytest.mark.anyio
    async def test_agent_state_machine_dispatches_sandboxed_calculation(self):
        """Agent State Machine executes sandboxed_calculation step via ToolRegistry and captures observation."""
        registry = ToolRegistry()
        orchestrator = AgentStateMachineOrchestrator(tool_registry=registry)

        class SingleStepSandboxPlanner(Planner):
            async def create_plan(self, task, task_id, routing_decision=None):
                return Plan(
                    plan_id="p_sandbox_test",
                    task_id=task_id,
                    goal=task,
                    steps=[
                        PlanStep(
                            id="step_1",
                            description="Run sandboxed wall thickness evaluation",
                            capability="sandboxed_calculation",
                            tool_name="sandboxed_calculation",
                            input_payload={
                                "tool_name": "minimum_wall_thickness_check",
                                "measured_thickness_mm": 5.2,
                                "minimum_required_mm": 3.2,
                                "execution_mode": "in_process",
                            },
                        )
                    ],
                )

        orchestrator.planner = SingleStepSandboxPlanner()
        ctx = await orchestrator.execute_task("Run sandboxed calculation")

        assert ctx.current_state == AgentState.DELIVER
        assert len(ctx.observations) == 1
        obs = ctx.observations[0]
        assert obs.success is True
        assert obs.tool_name == "sandboxed_calculation"
        assert obs.output["margin_mm"] == 2.0
        assert obs.output["status"] == "PASS"
        assert ctx.tool_results["step_1"]["margin_mm"] == 2.0

    @pytest.mark.anyio
    async def test_agent_state_machine_handles_sandboxed_calculation_failure(self):
        """When sandboxed calculation fails validation, failure observation is recorded and reaches failure machinery."""
        registry = ToolRegistry()
        orchestrator = AgentStateMachineOrchestrator(tool_registry=registry)

        class FailingSandboxPlanner(Planner):
            async def create_plan(self, task, task_id, routing_decision=None):
                return Plan(
                    plan_id="p_sandbox_fail",
                    task_id=task_id,
                    goal=task,
                    steps=[
                        PlanStep(
                            id="step_1",
                            description="Run invalid sandboxed calculation",
                            capability="sandboxed_calculation",
                            tool_name="sandboxed_calculation",
                            input_payload={
                                "tool_name": "minimum_wall_thickness_check",
                                "measured_thickness_mm": -1.0,
                                "minimum_required_mm": 3.2,
                                "execution_mode": "in_process",
                            },
                        )
                    ],
                )

        orchestrator.planner = FailingSandboxPlanner()
        ctx = await orchestrator.execute_task("Run invalid calculation")

        # Terminal state must be FAILED after reflector retries fail
        assert ctx.current_state == AgentState.FAILED
        assert any(not obs.success for obs in ctx.observations)
        failed_obs = [obs for obs in ctx.observations if not obs.success]
        assert "Sandboxed tool 'minimum_wall_thickness_check' failed" in failed_obs[0].error


# ── 10. Compatibility Re-export Modules & Security Guarantees ─────────────────

class TestCompatibilityModulesAndSecurityGuarantees:
    """Verifies thin re-export compatibility modules and core security guarantees."""

    def test_compatibility_process_runner_reexports(self):
        try:
            from app.services.sandbox.process_runner import (
                SubprocessSandboxExecutor as RunnerExec,
                ExecutionStatus as RunnerStatus,
                ToolExecutionRequest as RunnerReq,
            )
        except ImportError:
            from backend.app.services.sandbox.process_runner import (
                SubprocessSandboxExecutor as RunnerExec,
                ExecutionStatus as RunnerStatus,
                ToolExecutionRequest as RunnerReq,
            )
        assert RunnerExec is SubprocessSandboxExecutor
        assert RunnerStatus is ExecutionStatus

    def test_compatibility_validator_reexports(self):
        try:
            from app.services.sandbox.validator import (
                PythonASTPreScreener as ValScreener,
                validate_tool_payload as val_payload,
                FORBIDDEN_CALLS,
                FORBIDDEN_MODULES,
            )
        except ImportError:
            from backend.app.services.sandbox.validator import (
                PythonASTPreScreener as ValScreener,
                validate_tool_payload as val_payload,
                FORBIDDEN_CALLS,
                FORBIDDEN_MODULES,
            )
        assert ValScreener is PythonASTPreScreener
        assert "os" in FORBIDDEN_MODULES
        assert "eval" in FORBIDDEN_CALLS

    @pytest.mark.anyio
    async def test_command_injection_attempt_rejected(self, tmp_path):
        """Payload values containing shell metacharacters cannot execute arbitrary commands."""
        policy = SandboxPolicy(scratch_dir=tmp_path)
        executor = SubprocessSandboxExecutor(policy=policy)

        req = ToolExecutionRequest(
            tool_name="minimum_wall_thickness_check",
            input={
                "component_id": "C-101; rm -rf /; echo injected",
                "measured_thickness_mm": 4.5,
                "minimum_required_mm": 3.2,
            },
            execution_mode="subprocess",
        )
        res = await executor.execute_tool(req)
        assert res.status == ExecutionStatus.SUCCESS
        assert res.structured_result["component_id"] == "C-101; rm -rf /; echo injected"

    def test_subprocess_executor_shell_false_contract(self):
        """SubprocessSandboxExecutor must invoke create_subprocess_exec with explicit args, never shell=True."""
        import inspect
        source = inspect.getsource(SubprocessSandboxExecutor)
        assert "create_subprocess_exec" in source
        assert "create_subprocess_shell" not in source
        assert "shell=True" not in source
