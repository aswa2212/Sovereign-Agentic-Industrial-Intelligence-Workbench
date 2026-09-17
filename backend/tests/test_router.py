"""
SIH26117 — Phase 3 Task Router Unit Tests

Tests the taxonomy, RoutingDecision, RuleRouter (Level 0), extension point stubs,
API endpoint, and configuration loading.

All tests execute OFFLINE:
- No Ollama required
- No GPU required
- No network required
- No model downloads

Test classes:
1. TestTaxonomy           — enum values, mapping tables
2. TestRoutingDecision    — Pydantic schema validation
3. TestRuleDefinitions    — rule registry structure
4. TestRuleRouter         — core routing logic
5. TestRuleRouterFallback — fallback threshold behaviour
6. TestRuleRouterPriority — explicit priority ordering
7. TestRouterBoundary     — architectural boundary (no Ollama imports)
8. TestExtensionPoints    — Level 1/2 stubs raise NotImplementedError
9. TestRouterAPIEndpoint  — REST endpoint behaviour
10. TestRouterConfig      — settings integration
"""

import time

import pytest
from fastapi.testclient import TestClient

try:
    from app.main import app
    from app.services.router import (
        Capability,
        ClassifierRouter,
        ModelRole,
        RuleRouter,
        SemanticRouter,
        TaskType,
        capability_for_task,
        role_for_task,
    )
    from app.services.router.decision import RoutingDecision, RuleMatchEvidence
    from app.services.router.rules import ROUTING_RULES, ROUTING_RULES_SORTED
    from app.api.v1.endpoints.router import set_task_router
    from app.core.config import get_settings
except ImportError:
    from backend.app.main import app
    from backend.app.services.router import (
        Capability,
        ClassifierRouter,
        ModelRole,
        RuleRouter,
        SemanticRouter,
        TaskType,
        capability_for_task,
        role_for_task,
    )
    from backend.app.services.router.decision import RoutingDecision, RuleMatchEvidence
    from backend.app.services.router.rules import ROUTING_RULES, ROUTING_RULES_SORTED
    from backend.app.api.v1.endpoints.router import set_task_router
    from backend.app.core.config import get_settings


@pytest.fixture(autouse=True)
def reset_router():
    """Reset the global task router singleton between tests."""
    set_task_router(None)
    yield
    set_task_router(None)


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def router():
    """Default RuleRouter with standard production rules."""
    return RuleRouter()


@pytest.fixture()
def strict_router():
    """RuleRouter with threshold=1.0 — forces every decision to fallback."""
    return RuleRouter(fallback_threshold=1.0)


# ===========================================================================
# 1. Taxonomy Tests
# ===========================================================================

class TestTaxonomy:

    def test_task_type_enum_has_required_values(self):
        expected = {
            "coding", "vision", "document_analysis", "summarization",
            "calculation", "extraction", "reasoning", "general",
        }
        actual = {t.value for t in TaskType}
        assert expected == actual, f"Missing task types: {expected - actual}"

    def test_capability_enum_values(self):
        expected = {"reasoning", "coding", "vision", "extraction", "calculation", "general"}
        actual = {c.value for c in Capability}
        assert expected == actual

    def test_model_role_enum_values(self):
        expected = {"router", "reasoning", "coder", "vision", "embedding"}
        actual = {r.value for r in ModelRole}
        assert expected == actual

    def test_all_task_types_have_capability_mapping(self):
        for task_type in TaskType:
            cap = capability_for_task(task_type)
            assert cap is not None, f"TaskType.{task_type} missing capability mapping"

    def test_all_task_types_resolve_to_model_role(self):
        for task_type in TaskType:
            role = role_for_task(task_type)
            assert role is not None, f"TaskType.{task_type} could not resolve to a model role"

    def test_coding_maps_to_coder_role(self):
        assert role_for_task(TaskType.CODING) == ModelRole.CODER

    def test_vision_maps_to_vision_role(self):
        assert role_for_task(TaskType.VISION) == ModelRole.VISION

    def test_calculation_maps_to_reasoning_role(self):
        # Calculation requires reasoning model (sandbox tool handles the math)
        assert role_for_task(TaskType.CALCULATION) == ModelRole.REASONING

    def test_document_analysis_maps_to_reasoning_role(self):
        assert role_for_task(TaskType.DOCUMENT_ANALYSIS) == ModelRole.REASONING

    def test_general_maps_to_reasoning_role(self):
        assert role_for_task(TaskType.GENERAL) == ModelRole.REASONING


# ===========================================================================
# 2. RoutingDecision Schema Tests
# ===========================================================================

class TestRoutingDecision:

    def test_decision_requires_mandatory_fields(self):
        decision = RoutingDecision(
            task_type=TaskType.CODING,
            capability=Capability.CODING,
            model_role=ModelRole.CODER,
            confidence=0.90,
            routing_method="rules",
            reason="Test decision",
        )
        assert decision.task_type == TaskType.CODING
        assert decision.confidence == 0.90
        assert decision.fallback_used is False

    def test_confidence_bounds_enforced(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            RoutingDecision(
                task_type=TaskType.CODING,
                capability=Capability.CODING,
                model_role=ModelRole.CODER,
                confidence=1.5,  # > 1.0 → invalid
                routing_method="rules",
                reason="test",
            )

    def test_decision_defaults(self):
        decision = RoutingDecision(
            task_type=TaskType.GENERAL,
            capability=Capability.GENERAL,
            model_role=ModelRole.REASONING,
            confidence=0.5,
            routing_method="fallback",
            reason="test",
        )
        assert decision.fallback_used is False
        assert decision.matched_rule_ids == []
        assert decision.primary_rule_id is None
        assert decision.candidates == []
        assert decision.request_id is None
        assert decision.timestamp > 0

    def test_decision_serialises_to_dict(self):
        decision = RoutingDecision(
            task_type=TaskType.VISION,
            capability=Capability.VISION,
            model_role=ModelRole.VISION,
            confidence=0.92,
            routing_method="rules",
            reason="Vision signal detected.",
        )
        d = decision.model_dump()
        assert d["task_type"] == "vision"
        assert d["model_role"] == "vision"


# ===========================================================================
# 3. Rule Registry Tests
# ===========================================================================

class TestRuleDefinitions:

    def test_all_rules_have_unique_ids(self):
        ids = [r.rule_id for r in ROUTING_RULES]
        assert len(ids) == len(set(ids)), "Duplicate rule_ids found"

    def test_rules_sorted_by_priority(self):
        priorities = [r.priority for r in ROUTING_RULES_SORTED]
        assert priorities == sorted(priorities), "ROUTING_RULES_SORTED is not sorted by priority"

    def test_all_rules_have_non_empty_patterns(self):
        for rule in ROUTING_RULES:
            assert len(rule.patterns) > 0, f"Rule '{rule.rule_id}' has no patterns"

    def test_all_rules_have_valid_confidence(self):
        for rule in ROUTING_RULES:
            assert 0.0 <= rule.base_confidence <= 1.0, (
                f"Rule '{rule.rule_id}' has invalid confidence {rule.base_confidence}"
            )

    def test_vision_rule_has_highest_priority(self):
        """Vision rule must win on ambiguous tasks containing both vision and other signals."""
        vision_rule = next(r for r in ROUTING_RULES if r.rule_id == "vision_pid_signal")
        other_rules = [r for r in ROUTING_RULES if r.rule_id != "vision_pid_signal"]
        for other in other_rules:
            assert vision_rule.priority < other.priority, (
                f"Vision rule priority {vision_rule.priority} must be < "
                f"{other.rule_id} priority {other.priority}"
            )

    def test_catchall_rule_has_lowest_priority(self):
        """Catch-all must have lower confidence than the fallback threshold."""
        catchall = next(r for r in ROUTING_RULES if r.rule_id == "general_catchall")
        assert catchall.base_confidence < 0.70, (
            "Catch-all rule confidence must be below the default fallback threshold (0.70) "
            "so that truly unknown tasks trigger the fallback path."
        )


# ===========================================================================
# 4. RuleRouter — Core Routing Logic
# ===========================================================================

class TestRuleRouter:

    def test_coding_task_routes_to_coder(self, router):
        decision = router.route("Write a Python function to parse a CSV file.")
        assert decision.task_type == TaskType.CODING
        assert decision.model_role == ModelRole.CODER
        assert decision.routing_method == "rules"
        assert decision.confidence >= 0.70

    def test_vision_task_routes_to_vision(self, router):
        decision = router.route(
            "Identify the instrument tags in this P&ID diagram."
        )
        assert decision.task_type == TaskType.VISION
        assert decision.model_role == ModelRole.VISION
        assert decision.confidence >= 0.70

    def test_user_pid_vision_objective(self, router):
        objective = (
            "Analyze the uploaded P&ID image for C-101. Identify all visible equipment tags, "
            "piping lines, valves, instruments, nozzles, and major process connections. "
            "Extract the labels and describe their spatial relationships. "
            "Do not perform corrosion calculations, numerical engineering analysis, "
            "or remaining-life estimation. Return structured visual findings only."
        )
        decision = router.route(objective)
        assert decision.task_type == TaskType.VISION
        assert decision.model_role == ModelRole.VISION
        assert decision.confidence >= 0.70

    def test_c101_corrosion_assessment_routes_to_reasoning(self, router):
        objective = (
            "Perform an end-to-end corrosion and remaining-life assessment for column C-101 "
            "based on inspection records."
        )
        decision = router.route(objective)
        assert decision.model_role == ModelRole.REASONING
        assert decision.task_type in (TaskType.CALCULATION, TaskType.DOCUMENT_ANALYSIS, TaskType.REASONING)

    def test_document_analysis_task_routes_to_reasoning(self, router):
        decision = router.route(
            "Analyze this corrosion inspection report for pipe P-104."
        )
        assert decision.task_type == TaskType.DOCUMENT_ANALYSIS
        assert decision.model_role == ModelRole.REASONING

    def test_summarization_task(self, router):
        decision = router.route("Summarize the maintenance report from last quarter.")
        assert decision.task_type == TaskType.SUMMARIZATION
        assert decision.model_role == ModelRole.REASONING

    def test_calculation_task(self, router):
        decision = router.route(
            "Calculate the corrosion rate from these thickness measurements."
        )
        assert decision.task_type == TaskType.CALCULATION
        assert decision.model_role == ModelRole.REASONING

    def test_reasoning_task(self, router):
        decision = router.route(
            "Compare these two engineering recommendations for the pipeline."
        )
        assert decision.task_type == TaskType.REASONING
        assert decision.model_role == ModelRole.REASONING

    def test_extraction_task(self, router):
        decision = router.route(
            "Extract all equipment tags from the line list in this document."
        )
        assert decision.task_type == TaskType.EXTRACTION
        assert decision.model_role == ModelRole.REASONING

    def test_general_greeting_triggers_fallback(self, router):
        """'Hello' triggers the low-confidence catch-all, which is below 0.70 threshold."""
        decision = router.route("Hello, what can you do?")
        assert decision.fallback_used is True
        assert decision.model_role == ModelRole.REASONING

    def test_empty_task_triggers_fallback(self, router):
        decision = router.route("")
        assert decision.fallback_used is True
        assert decision.confidence == 0.0

    def test_whitespace_only_triggers_fallback(self, router):
        decision = router.route("   ")
        assert decision.fallback_used is True

    def test_unknown_task_triggers_fallback(self, router):
        decision = router.route(
            "xyzzy plugh frobozz magic word completely unrelated content 12345"
        )
        assert decision.fallback_used is True
        assert decision.model_role == ModelRole.REASONING

    def test_routing_decision_has_timestamp(self, router):
        before = time.time()
        decision = router.route("Analyze the report.")
        assert decision.timestamp >= before

    def test_routing_decision_has_reason(self, router):
        decision = router.route("Write a Python script to process sensor data.")
        assert decision.reason
        assert len(decision.reason) > 10

    def test_matched_rule_ids_populated(self, router):
        decision = router.route("Write a Python function to parse CSV.")
        assert len(decision.matched_rule_ids) > 0
        assert decision.primary_rule_id in decision.matched_rule_ids

    def test_candidates_preserved(self, router):
        """All matching rules must be preserved in candidates for audit."""
        decision = router.route(
            "Write a Python script to extract data from the report."
        )
        # Both coding and extraction signals could fire
        assert len(decision.candidates) >= 1

    def test_request_id_propagated(self, router):
        decision = router.route("Analyze report.", request_id="test-req-001")
        assert decision.request_id == "test-req-001"

    def test_pid_task_is_vision(self, router):
        decision = router.route(
            "Please review this P&ID and identify all control valves."
        )
        assert decision.task_type == TaskType.VISION
        assert decision.model_role == ModelRole.VISION

    def test_ndt_report_is_document_analysis(self, router):
        decision = router.route(
            "Review the NDT ultrasonic inspection report for pipe segment 14."
        )
        assert decision.task_type == TaskType.DOCUMENT_ANALYSIS

    def test_corrosion_rate_is_calculation(self, router):
        decision = router.route(
            "Calculate the corrosion rate from the wall thickness measurements."
        )
        assert decision.task_type == TaskType.CALCULATION

    def test_no_model_ids_in_decision(self, router):
        """The routing decision must not contain any model IDs or model filenames."""
        decision = router.route("Analyze the corrosion report.")
        d = decision.model_dump()
        decision_str = str(d).lower()
        # Check that no concrete model IDs appear
        for model_id in ("qwen2.5", "deepseek", "llama", "ollama", "nomic", "bge"):
            assert model_id not in decision_str, (
                f"Router decision contains model ID '{model_id}' — "
                "model IDs must never appear in routing decisions."
            )

    def test_router_does_not_import_ollama(self):
        """The router module must have zero dependency on Ollama or any HTTP client."""
        import sys
        # Import the rule_router module and inspect its dependencies
        try:
            import app.services.router.rule_router as rr_module
        except ImportError:
            import backend.app.services.router.rule_router as rr_module

        # None of the Ollama / HTTP client modules should be imported by the router
        forbidden = {"httpx", "requests", "aiohttp", "ollama"}
        module_imports = set(vars(rr_module).keys())
        for lib in forbidden:
            assert lib not in sys.modules.get(
                "app.services.router.rule_router", type("m", (), {"__dict__": {}})
            ).__dict__, (
                f"Router unexpectedly imports '{lib}' — violates architectural boundary."
            )


# ===========================================================================
# 5. Fallback Behaviour
# ===========================================================================

class TestRuleRouterFallback:

    def test_fallback_fires_when_confidence_below_threshold(self):
        """Custom router with threshold=0.95 — coding rule (0.90) triggers fallback."""
        r = RuleRouter(fallback_threshold=0.95)
        decision = r.route("Write a Python function to parse CSV.")
        assert decision.fallback_used is True
        assert decision.model_role == ModelRole.REASONING

    def test_fallback_preserves_original_task_type(self):
        """Even when fallback fires, the original task_type is preserved."""
        r = RuleRouter(fallback_threshold=0.95)
        decision = r.route("Write a Python function to parse CSV.")
        # task_type stays as detected (CODING), only model_role is overridden
        assert decision.task_type == TaskType.CODING
        assert decision.fallback_used is True

    def test_custom_fallback_role(self):
        """Custom fallback_role should be used instead of default."""
        r = RuleRouter(fallback_threshold=1.0, fallback_role=ModelRole.ROUTER)
        decision = r.route("Write a Python script.")
        assert decision.fallback_used is True
        assert decision.model_role == ModelRole.ROUTER

    def test_no_fallback_when_confidence_above_threshold(self):
        """Vision signal confidence=0.92 > default threshold=0.70 → no fallback."""
        r = RuleRouter(fallback_threshold=0.70)
        decision = r.route("Identify all instrument tags in this P&ID diagram.")
        assert decision.fallback_used is False
        assert decision.model_role == ModelRole.VISION

    def test_empty_task_always_fallback(self, strict_router):
        decision = strict_router.route("")
        assert decision.fallback_used is True
        assert decision.confidence == 0.0

    def test_fallback_routing_method_is_reported(self, router):
        decision = router.route("xyzzy completely unknown input zork frobozz")
        assert decision.routing_method == "fallback"

    def test_rule_routing_method_when_successful(self, router):
        decision = router.route("Write Python code to process the CSV.")
        if not decision.fallback_used:
            assert decision.routing_method == "rules"


# ===========================================================================
# 6. Rule Priority Tests
# ===========================================================================

class TestRuleRouterPriority:

    def test_vision_wins_over_reasoning_on_ambiguous_task(self, router):
        """
        Task: 'Analyze this P&ID diagram'
        Both 'vision_pid_signal' (priority 1) and 'reasoning_signal'/'document_analysis_signal'
        may fire. Vision must win by priority.
        """
        decision = router.route(
            "Analyze this P&ID diagram and explain the control logic."
        )
        assert decision.task_type == TaskType.VISION, (
            "Vision must win over reasoning when P&ID signal is present."
        )

    def test_coding_wins_over_reasoning_on_ambiguous_task(self, router):
        """
        Task: 'Write a Python function to analyze the report'
        Coding (priority 2) wins over reasoning (priority 7).
        """
        decision = router.route(
            "Write a Python function to analyze the maintenance report."
        )
        assert decision.task_type == TaskType.CODING, (
            "Coding must win over reasoning when explicit code generation is requested."
        )

    def test_calculation_wins_over_document_analysis(self, router):
        """
        Task: 'Calculate the corrosion rate from the inspection report'
        Calculation (priority 3) wins over document_analysis (priority 5).
        """
        decision = router.route(
            "Calculate the corrosion rate from this inspection report."
        )
        assert decision.task_type == TaskType.CALCULATION

    def test_priority_is_explicit_not_insertion_order(self):
        """ROUTING_RULES_SORTED must be sorted by priority regardless of list insertion order."""
        from app.services.router.rules import ROUTING_RULES_SORTED
        priorities = [r.priority for r in ROUTING_RULES_SORTED]
        assert priorities == sorted(priorities)


# ===========================================================================
# 7. Architectural Boundary Tests
# ===========================================================================

class TestRouterBoundary:

    def test_rule_router_has_no_ollama_dependency(self):
        """
        Import the rule_router module and confirm it does not import httpx,
        requests, or any inference backend.
        """
        try:
            import app.services.router.rule_router as rr
        except ImportError:
            import backend.app.services.router.rule_router as rr

        module_source = open(rr.__file__, "r").read()
        forbidden_imports = ["import httpx", "import requests", "import ollama",
                             "OllamaAdapter", "MockInferenceBackend"]
        for imp in forbidden_imports:
            assert imp not in module_source, (
                f"rule_router.py must not contain '{imp}' — "
                "the router must not depend on any inference backend."
            )

    def test_taxonomy_has_no_network_imports(self):
        try:
            import app.services.router.taxonomy as tx
        except ImportError:
            import backend.app.services.router.taxonomy as tx

        source = open(tx.__file__, "r").read()
        for lib in ["httpx", "requests", "ollama", "torch", "transformers"]:
            assert lib not in source, f"taxonomy.py must not import '{lib}'"

    def test_rule_router_is_synchronous(self, router):
        """route() must be a regular function, not a coroutine."""
        import inspect
        assert not inspect.iscoroutinefunction(router.route), (
            "RuleRouter.route() must be synchronous (no async) for near-zero latency."
        )

    def test_routing_decision_contains_no_model_ids(self, router):
        for task in [
            "Analyze the corrosion report.",
            "Write a Python script.",
            "Identify tags in the P&ID.",
            "Calculate the corrosion rate.",
        ]:
            decision = router.route(task)
            assert not any(
                mid in decision.model_role
                for mid in ["qwen", "deepseek", "llama", "nomic"]
            ), f"model_role '{decision.model_role}' contains a hardcoded model ID"


# ===========================================================================
# 8. Extension Point Tests
# ===========================================================================

class TestExtensionPoints:

    def test_semantic_router_raises_not_implemented(self):
        sr = SemanticRouter()
        with pytest.raises(NotImplementedError):
            sr.route("Test task")

    def test_semantic_router_not_available(self):
        sr = SemanticRouter()
        assert sr.is_available() is False

    def test_classifier_router_raises_not_implemented(self):
        cr = ClassifierRouter()
        with pytest.raises(NotImplementedError):
            cr.route("Test task")

    def test_classifier_router_not_available(self):
        cr = ClassifierRouter()
        assert cr.is_available() is False

    def test_hybrid_router_falls_back_to_rule_router(self):
        """HybridRouter with only a RuleRouter should delegate to rules."""
        from app.services.router import HybridRouter
        rule_r = RuleRouter()
        hybrid = HybridRouter(rule_router=rule_r)
        decision = hybrid.route("Write a Python function.")
        assert decision.task_type == TaskType.CODING

    def test_hybrid_router_is_available(self):
        from app.services.router import HybridRouter
        hybrid = HybridRouter(rule_router=RuleRouter())
        assert hybrid.is_available() is True


# ===========================================================================
# 9. Router API Endpoint Tests
# ===========================================================================

class TestRouterAPIEndpoint:

    def test_route_coding_task(self, client):
        response = client.post(
            "/api/v1/router/route",
            json={"task": "Write a Python function to parse a CSV file."},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_type"] == "coding"
        assert data["model_role"] == "coder"
        assert data["routing_method"] == "rules"
        assert data["fallback_used"] is False
        assert data["confidence"] >= 0.70

    def test_route_vision_task(self, client):
        response = client.post(
            "/api/v1/router/route",
            json={"task": "Identify the instrument tags in this P&ID diagram."},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_type"] == "vision"
        assert data["model_role"] == "vision"

    def test_route_document_analysis(self, client):
        response = client.post(
            "/api/v1/router/route",
            json={"task": "Analyze this corrosion inspection report."},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_type"] == "document_analysis"

    def test_route_calculation(self, client):
        response = client.post(
            "/api/v1/router/route",
            json={"task": "Calculate the corrosion rate from these thickness measurements."},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_type"] == "calculation"

    def test_route_unknown_task_fallback(self, client):
        response = client.post(
            "/api/v1/router/route",
            json={"task": "xyzzy plugh frobozz something completely unrelated"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["fallback_used"] is True
        assert data["model_role"] == "reasoning"

    def test_route_empty_task_returns_422(self, client):
        """Empty task must fail Pydantic min_length validation → 422."""
        response = client.post(
            "/api/v1/router/route",
            json={"task": ""},
        )
        assert response.status_code == 422

    def test_route_missing_task_returns_422(self, client):
        response = client.post("/api/v1/router/route", json={})
        assert response.status_code == 422

    def test_route_response_has_audit_evidence(self, client):
        response = client.post(
            "/api/v1/router/route",
            json={"task": "Write a Python function."},
        )
        assert response.status_code == 200
        data = response.json()
        assert "matched_rule_ids" in data
        assert "primary_rule_id" in data
        assert "candidates" in data
        assert "timestamp" in data

    def test_route_request_id_propagated(self, client):
        response = client.post(
            "/api/v1/router/route",
            json={"task": "Analyze the report.", "request_id": "test-42"},
        )
        assert response.status_code == 200
        assert response.json()["request_id"] == "test-42"

    def test_route_response_has_no_hardcoded_model_ids(self, client):
        response = client.post(
            "/api/v1/router/route",
            json={"task": "Analyze this corrosion report."},
        )
        assert response.status_code == 200
        response_text = response.text.lower()
        for model_id in ("qwen2.5", "deepseek-r1", "nomic-embed", "llama"):
            assert model_id not in response_text, (
                f"API response contains hardcoded model ID '{model_id}'"
            )


# ===========================================================================
# 10. Configuration Tests
# ===========================================================================

class TestRouterConfig:

    def test_settings_has_router_fallback_threshold(self):
        settings = get_settings()
        assert hasattr(settings, "router_fallback_threshold")
        assert 0.0 <= settings.router_fallback_threshold <= 1.0

    def test_settings_has_router_fallback_role(self):
        settings = get_settings()
        assert hasattr(settings, "router_fallback_role")
        assert settings.router_fallback_role in ("reasoning", "router", "coder", "vision")

    def test_settings_has_router_method(self):
        settings = get_settings()
        assert hasattr(settings, "router_method")
        assert settings.router_method in ("rules", "semantic", "classifier", "hybrid")

    def test_rule_router_from_settings(self):
        r = RuleRouter.from_settings()
        assert r is not None
        assert r.fallback_threshold == get_settings().router_fallback_threshold
