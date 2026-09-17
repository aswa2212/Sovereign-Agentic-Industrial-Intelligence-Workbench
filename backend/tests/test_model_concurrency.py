"""
SIH26117 - Phase 2 Step 2: VRAM Serial Concurrency & Active Model Residency Tests

Tests the ModelManager concurrency contract:
- Serialized execution when max_concurrent_models == 1
- Active role/model residency tracking
- Proactive model eviction on role change
- No redundant unload on identical role requests
- keep_alive forwarding from tier configuration
- Structured generation lifecycle parity
- Public load_model_for_role / unload_model_for_role safety (no self-deadlock)
- Exception safety (failure releases lock and does not corrupt state)
- Non-serialization when max_concurrent_models > 1
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest

from app.services.model_manager.base import InferenceBackend, ModelCapabilities, ModelInfo
from app.services.model_manager.config_loader import ModelEntry, TierConfig
from app.services.model_manager.manager import ModelManager
from app.services.model_manager.mock_adapter import MockInferenceBackend


# ---------------------------------------------------------------------------
# Test Fixtures & Instrumented Mock Backends
# ---------------------------------------------------------------------------

@pytest.fixture
def single_model_tier() -> TierConfig:
    """Hardware tier with max_concurrent_models=1 and swap_keep_alive='0m'."""
    return TierConfig(
        description="Dev Laptop 8GB VRAM (Single Model)",
        vram_budget_gb=8.0,
        max_concurrent_models=1,
        swap_keep_alive="0m",
        router=ModelEntry(provider="mock", model_tag="mock-router:1.5b"),
        reasoning=ModelEntry(provider="mock", model_tag="mock-reasoning:7b"),
        coder=ModelEntry(provider="mock", model_tag="mock-coder:3b"),
        vision=ModelEntry(provider="mock", model_tag="mock-vision:3b"),
    )


@pytest.fixture
def multi_model_tier() -> TierConfig:
    """Hardware tier with max_concurrent_models=3 (multi-model colocation)."""
    return TierConfig(
        description="Workstation 24GB VRAM (Multi Model)",
        vram_budget_gb=24.0,
        max_concurrent_models=3,
        swap_keep_alive="60m",
        router=ModelEntry(provider="mock", model_tag="mock-router:1.5b"),
        reasoning=ModelEntry(provider="mock", model_tag="mock-reasoning:7b"),
        coder=ModelEntry(provider="mock", model_tag="mock-coder:3b"),
        vision=ModelEntry(provider="mock", model_tag="mock-vision:3b"),
    )


class InstrumentedMockBackend(MockInferenceBackend):
    """
    Mock backend instrumented with execution timelines and call history
    to verify concurrency invariants without needing a physical GPU.
    """

    def __init__(self, delay_s: float = 0.05, always_healthy: bool = True) -> None:
        super().__init__(always_healthy=always_healthy)
        self.delay_s = delay_s
        self.execution_intervals: List[Dict[str, Any]] = []
        self.unloaded_tags: List[str] = []
        self.loaded_tags: List[str] = []
        self.active_inferences = 0
        self.peak_concurrent_inferences = 0

    async def load_model(self, model_id: str) -> bool:
        self.loaded_tags.append(model_id)
        return await super().load_model(model_id)

    async def unload_model(self, model_id: str) -> bool:
        self.unloaded_tags.append(model_id)
        return await super().unload_model(model_id)

    async def generate(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        keep_alive: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        t_start = time.monotonic()
        self.active_inferences += 1
        self.peak_concurrent_inferences = max(
            self.peak_concurrent_inferences, self.active_inferences
        )

        interval_entry = {
            "model_id": model_id,
            "type": "text",
            "start": t_start,
            "end": None,
            "keep_alive": keep_alive,
        }
        self.execution_intervals.append(interval_entry)

        try:
            if self.delay_s > 0:
                await asyncio.sleep(self.delay_s)
            res = await super().generate(
                model_id=model_id,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                keep_alive=keep_alive,
                **kwargs,
            )
            return res
        finally:
            t_end = time.monotonic()
            interval_entry["end"] = t_end
            self.active_inferences -= 1

    async def generate_structured(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        keep_alive: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        t_start = time.monotonic()
        self.active_inferences += 1
        self.peak_concurrent_inferences = max(
            self.peak_concurrent_inferences, self.active_inferences
        )

        interval_entry = {
            "model_id": model_id,
            "type": "structured",
            "start": t_start,
            "end": None,
            "keep_alive": keep_alive,
        }
        self.execution_intervals.append(interval_entry)

        try:
            if self.delay_s > 0:
                await asyncio.sleep(self.delay_s)
            res = await super().generate_structured(
                model_id=model_id,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                keep_alive=keep_alive,
                **kwargs,
            )
            return res
        finally:
            t_end = time.monotonic()
            interval_entry["end"] = t_end
            self.active_inferences -= 1


# ---------------------------------------------------------------------------
# Test Suite: VRAM Serial Concurrency & Active Model Residency
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestModelConcurrencyAndResidency:

    async def test_a_serial_concurrent_execution(self, single_model_tier):
        """
        A. SERIAL CONCURRENT EXECUTION
        Launch concurrent generation requests (reasoning & vision) with asyncio.gather().
        Verify:
        - execution intervals do not overlap
        - second request waits for first
        - peak concurrent inferences == 1 (no simultaneous backend execution).
        """
        backend = InstrumentedMockBackend(delay_s=0.06)
        manager = ModelManager(backend=backend, tier_config=single_model_tier)

        task_reasoning = manager.generate(
            role="reasoning",
            prompt="Analyze ultrasonic thickness logs",
        )
        task_vision = manager.generate(
            role="vision",
            prompt="Detect equipment tags in P&ID",
        )

        res_reasoning, res_vision = await asyncio.gather(task_reasoning, task_vision)

        assert res_reasoning is not None
        assert res_vision is not None

        # Verify exactly 2 executions were captured
        assert len(backend.execution_intervals) == 2

        first = backend.execution_intervals[0]
        second = backend.execution_intervals[1]

        # Invariant: Non-overlapping execution intervals
        # The second execution must start AFTER or at the exact time the first completed
        assert second["start"] >= first["end"], (
            f"Execution intervals overlapped! First ended at {first['end']}, "
            f"second started at {second['start']}"
        )

        # Invariant: Peak concurrent inferences never exceeded 1 on single_model_tier
        assert backend.peak_concurrent_inferences == 1

    async def test_b_role_switch_eviction(self, single_model_tier):
        """
        B. ROLE SWITCH EVICTION
        Call generate(reasoning) then generate(vision).
        Verify:
        - reasoning model executes first
        - reasoning model tag is explicitly unloaded before vision executes
        - vision becomes active in manager state.
        """
        backend = InstrumentedMockBackend(delay_s=0.01)
        manager = ModelManager(backend=backend, tier_config=single_model_tier)

        # 1. First invocation: reasoning
        await manager.generate(role="reasoning", prompt="Step 1")
        assert manager.active_role == "reasoning"
        assert manager.active_model_tag == "mock-reasoning:7b"
        assert len(backend.unloaded_tags) == 0

        # 2. Second invocation: vision (role transition reasoning -> vision)
        await manager.generate(role="vision", prompt="Step 2")
        assert manager.active_role == "vision"
        assert manager.active_model_tag == "mock-vision:3b"

        # Verify explicit unload of reasoning model occurred
        assert "mock-reasoning:7b" in backend.unloaded_tags
        assert backend.unloaded_tags == ["mock-reasoning:7b"]

    async def test_c_same_role_no_redundant_unload(self, single_model_tier):
        """
        C. SAME ROLE NO REDUNDANT UNLOAD
        Call generate(reasoning) followed by generate(reasoning).
        Verify:
        - no unload occurs between them
        - model is not unnecessarily swapped or evicted.
        """
        backend = InstrumentedMockBackend(delay_s=0.01)
        manager = ModelManager(backend=backend, tier_config=single_model_tier)

        await manager.generate(role="reasoning", prompt="Query 1")
        assert manager.active_role == "reasoning"
        assert len(backend.unloaded_tags) == 0

        await manager.generate(role="reasoning", prompt="Query 2")
        assert manager.active_role == "reasoning"
        # No unload should have been performed
        assert len(backend.unloaded_tags) == 0

    async def test_d_keep_alive_forwarding(self, single_model_tier):
        """
        D. KEEP_ALIVE FORWARDING
        Verify tier.swap_keep_alive ('0m') is forwarded to the backend.
        Also verify explicit override via argument is honored.
        """
        backend = InstrumentedMockBackend(delay_s=0.01)
        manager = ModelManager(backend=backend, tier_config=single_model_tier)

        # Default keep_alive from tier config ('0m')
        await manager.generate(role="reasoning", prompt="Default keep_alive test")
        assert backend.execution_intervals[-1]["keep_alive"] == "0m"

        # Explicit override
        await manager.generate(
            role="reasoning",
            prompt="Explicit override test",
            keep_alive="5m",
        )
        assert backend.execution_intervals[-1]["keep_alive"] == "5m"

    async def test_e_structured_generation_parity(self, single_model_tier):
        """
        E. STRUCTURED GENERATION
        Repeat role-switch tests through generate_structured().
        Verify reasoning -> vision -> coder role transitions unload appropriately.
        """
        backend = InstrumentedMockBackend(delay_s=0.01)
        manager = ModelManager(backend=backend, tier_config=single_model_tier)

        # 1. Reasoning structured
        res1 = await manager.generate_structured(role="reasoning", prompt="Extract reasoning")
        assert isinstance(res1, dict)
        assert manager.active_role == "reasoning"
        assert len(backend.unloaded_tags) == 0

        # 2. Vision structured (triggers reasoning unload)
        res2 = await manager.generate_structured(role="vision", prompt="Extract visual tags")
        assert isinstance(res2, dict)
        assert manager.active_role == "vision"
        assert backend.unloaded_tags == ["mock-reasoning:7b"]

        # 3. Coder structured (triggers vision unload)
        res3 = await manager.generate_structured(role="coder", prompt="Extract code tags")
        assert isinstance(res3, dict)
        assert manager.active_role == "coder"
        assert backend.unloaded_tags == ["mock-reasoning:7b", "mock-vision:3b"]

    async def test_f_public_load_unload_safety(self, single_model_tier):
        """
        F. PUBLIC LOAD/UNLOAD SAFETY
        Verify direct calls to load_model_for_role() and unload_model_for_role()
        do not deadlock and correctly update active residency state.
        """
        backend = InstrumentedMockBackend(delay_s=0.01)
        manager = ModelManager(backend=backend, tier_config=single_model_tier)

        # Direct public load
        ok_load = await manager.load_model_for_role("router")
        assert ok_load is True
        assert manager.active_role == "router"
        assert manager.active_model_tag == "mock-router:1.5b"

        # Direct public load of another role (triggers unload of router)
        ok_load2 = await manager.load_model_for_role("reasoning")
        assert ok_load2 is True
        assert manager.active_role == "reasoning"
        assert "mock-router:1.5b" in backend.unloaded_tags

        # Direct public unload
        ok_unload = await manager.unload_model_for_role("reasoning")
        assert ok_unload is True
        assert manager.active_role is None
        assert manager.active_model_tag is None
        assert "mock-reasoning:7b" in backend.unloaded_tags

    async def test_g_failure_safety_releases_lock(self, single_model_tier):
        """
        G. FAILURE SAFETY
        Make backend generation fail with an exception.
        Verify:
        - lock is released via try/finally
        - subsequent generation can proceed immediately
        - error is not swallowed
        - no silent fallback occurs.
        """
        backend = InstrumentedMockBackend(delay_s=0.01)
        manager = ModelManager(backend=backend, tier_config=single_model_tier)

        # Configure backend to fail on first call
        with patch.object(
            backend, "generate", new=AsyncMock(side_effect=RuntimeError("GPU OOM / Backend crash"))
        ):
            with pytest.raises(RuntimeError, match="GPU OOM / Backend crash"):
                await manager.generate(role="reasoning", prompt="Will fail")

        # Invariant: Lock must NOT remain acquired
        assert not manager._execution_lock.locked()

        # Subsequent generation must succeed without hanging
        success_res = await manager.generate(role="coder", prompt="Should succeed after failure")
        assert success_res is not None
        assert manager.active_role == "coder"

    async def test_h_max_concurrent_models_greater_than_one(self, multi_model_tier):
        """
        H. MAX_CONCURRENT_MODELS > 1
        Verify the manager does not enforce single-model serialization
        when the active tier explicitly permits greater concurrency (e.g. max_concurrent_models=3).
        """
        # Set delay long enough to verify parallel overlap
        backend = InstrumentedMockBackend(delay_s=0.08)
        manager = ModelManager(backend=backend, tier_config=multi_model_tier)

        task1 = manager.generate(role="reasoning", prompt="Task 1")
        task2 = manager.generate(role="coder", prompt="Task 2")

        res1, res2 = await asyncio.gather(task1, task2)
        assert res1 is not None
        assert res2 is not None

        # On multi_model_tier (max_concurrent_models=3), concurrent requests can run in parallel
        assert backend.peak_concurrent_inferences >= 2, (
            f"Expected parallel execution with peak concurrency >= 2, "
            f"got {backend.peak_concurrent_inferences}"
        )

        # Neither model should have been unloaded since multi-model tier permits colocation
        assert len(backend.unloaded_tags) == 0
