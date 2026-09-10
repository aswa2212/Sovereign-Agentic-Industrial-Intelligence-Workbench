"""
SIH26117 — Phase 2 Model Manager Unit Tests
Tests the config loader, mock adapter, ModelManager, and REST endpoints.

All tests execute OFFLINE: no Ollama, no GPU, no network required.
The MockInferenceBackend is injected via set_model_manager() to isolate
the ModelManager from the filesystem and network.
"""

import json
import os
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Bootstrap: point Settings to the backend/.env so config resolution works
# ---------------------------------------------------------------------------
os.environ.setdefault("INFERENCE_PROVIDER", "mock")

try:
    from app.main import app
    from app.services.model_manager import (
        MockInferenceBackend,
        ModelManager,
        load_model_tiers,
    )
    from app.services.model_manager.config_loader import ModelEntry, TierConfig
    from app.api.v1.endpoints.models import set_model_manager
    from app.core.config import get_settings
except ImportError:
    from backend.app.main import app
    from backend.app.services.model_manager import (
        MockInferenceBackend,
        ModelManager,
        load_model_tiers,
    )
    from backend.app.services.model_manager.config_loader import ModelEntry, TierConfig
    from backend.app.api.v1.endpoints.models import set_model_manager
    from backend.app.core.config import get_settings


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_mock_manager(always_healthy: bool = True) -> ModelManager:
    """Build a ModelManager backed by MockInferenceBackend with a minimal tier."""
    backend = MockInferenceBackend(always_healthy=always_healthy)
    tier = TierConfig(
        description="Test Tier",
        vram_budget_gb=8.0,
        max_concurrent_models=1,
        router=ModelEntry(provider="mock", model_tag="qwen2.5:1.5b", context_window=4096),
        reasoning=ModelEntry(provider="mock", model_tag="deepseek-r1:7b", context_window=8192),
        coder=ModelEntry(provider="mock", model_tag="qwen2.5-coder:3b", context_window=8192),
        vision=ModelEntry(provider="mock", model_tag="qwen2.5-vl:3b", context_window=4096),
        embedding=ModelEntry(provider="mock", model_tag="nomic-embed-text", context_window=8192),
    )
    return ModelManager(backend=backend, tier_config=tier, max_concurrent_loads=1)


@pytest.fixture(autouse=True)
def inject_mock_manager():
    """
    Auto-use fixture: inject a fresh MockInferenceBackend manager before every test
    and reset it afterward.  This prevents tests from sharing VRAM state.
    """
    manager = _make_mock_manager()
    set_model_manager(manager)
    yield manager
    set_model_manager(None)  # type: ignore[arg-type]


@pytest.fixture()
def client():
    return TestClient(app)


# ===========================================================================
# 1. Config Loader Tests
# ===========================================================================

class TestConfigLoader:

    def test_load_model_tiers_from_yaml(self):
        """Config loader must parse model_tiers.yaml and return typed objects."""
        settings = get_settings()
        yaml_path = settings.get_resolved_path(settings.model_config_path)
        config = load_model_tiers(yaml_path)

        assert config.active_tier in config.tiers, (
            f"active_tier '{config.active_tier}' not found in tiers"
        )
        active = config.active()
        assert active.vram_budget_gb > 0
        assert active.max_concurrent_models >= 1

    def test_active_tier_has_required_roles(self):
        """The dev tier must have router, reasoning, coder, vision, and embedding configured."""
        settings = get_settings()
        yaml_path = settings.get_resolved_path(settings.model_config_path)
        config = load_model_tiers(yaml_path)
        active = config.active()

        for role in ("router", "reasoning", "coder", "vision", "embedding"):
            entry = active.get_model(role)
            assert entry is not None, f"Role '{role}' missing from active tier"
            assert entry.model_tag, f"model_tag empty for role '{role}'"

    def test_config_not_found_raises(self, tmp_path):
        """Loading from a nonexistent path must raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_model_tiers(tmp_path / "nonexistent.yaml")

    def test_tier_config_list_roles(self):
        """TierConfig.list_roles() must include all configured entries."""
        tier = TierConfig(
            router=ModelEntry(provider="mock", model_tag="qwen2.5:1.5b", context_window=4096),
            reasoning=ModelEntry(provider="mock", model_tag="deepseek-r1:7b", context_window=8192),
        )
        roles = tier.list_roles()
        assert "router" in roles
        assert "reasoning" in roles
        assert "coder" not in roles  # not configured in this tier


# ===========================================================================
# 2. Mock Adapter Tests
# ===========================================================================

@pytest.mark.asyncio
class TestMockAdapter:

    async def test_health_check_healthy(self):
        backend = MockInferenceBackend(always_healthy=True)
        assert await backend.health_check() is True

    async def test_health_check_unhealthy(self):
        backend = MockInferenceBackend(always_healthy=False)
        assert await backend.health_check() is False

    async def test_list_available_models_returns_catalogue(self):
        backend = MockInferenceBackend()
        models = await backend.list_available_models()
        assert len(models) > 0
        model_ids = {m.model_id for m in models}
        assert "qwen2.5:1.5b" in model_ids

    async def test_load_known_model(self):
        backend = MockInferenceBackend()
        result = await backend.load_model("qwen2.5:1.5b")
        assert result is True

    async def test_load_unknown_model_fails(self):
        backend = MockInferenceBackend()
        result = await backend.load_model("nonexistent-model:99b")
        assert result is False

    async def test_unload_loaded_model(self):
        backend = MockInferenceBackend()
        await backend.load_model("qwen2.5:1.5b")
        result = await backend.unload_model("qwen2.5:1.5b")
        assert result is True

    async def test_generate_returns_string(self):
        backend = MockInferenceBackend()
        response = await backend.generate(
            model_id="deepseek-r1:7b",
            prompt="Summarise the corrosion inspection report.",
        )
        assert isinstance(response, str)
        assert len(response) > 0

    async def test_generate_structured_returns_dict(self):
        backend = MockInferenceBackend()
        result = await backend.generate_structured(
            model_id="qwen2.5-coder:3b",
            prompt="Extract equipment tag from the report.",
        )
        assert isinstance(result, dict)
        assert "result" in result

    async def test_vram_flag_updates_after_load(self):
        backend = MockInferenceBackend()
        await backend.load_model("qwen2.5:1.5b")
        models = await backend.list_available_models()
        loaded = next(m for m in models if m.model_id == "qwen2.5:1.5b")
        assert loaded.is_resident_in_vram is True

    async def test_vram_flag_clears_after_unload(self):
        backend = MockInferenceBackend()
        await backend.load_model("qwen2.5:1.5b")
        await backend.unload_model("qwen2.5:1.5b")
        models = await backend.list_available_models()
        loaded = next(m for m in models if m.model_id == "qwen2.5:1.5b")
        assert loaded.is_resident_in_vram is False


# ===========================================================================
# 3. ModelManager Tests
# ===========================================================================

@pytest.mark.asyncio
class TestModelManager:

    async def test_initialize_succeeds(self, inject_mock_manager):
        await inject_mock_manager.initialize()
        # No exception should be raised

    async def test_is_backend_healthy(self, inject_mock_manager):
        assert await inject_mock_manager.is_backend_healthy() is True

    async def test_list_models_returns_models(self, inject_mock_manager):
        models = await inject_mock_manager.list_models()
        assert len(models) > 0

    async def test_generate_for_role(self, inject_mock_manager):
        response = await inject_mock_manager.generate(
            role="reasoning",
            prompt="What is the corrosion rate for pipe segment P-104?",
        )
        assert isinstance(response, str)
        assert len(response) > 0

    async def test_generate_structured_for_role(self, inject_mock_manager):
        result = await inject_mock_manager.generate_structured(
            role="coder",
            prompt="Extract NDT inspection data as JSON.",
        )
        assert isinstance(result, dict)

    async def test_generate_unknown_role_raises(self, inject_mock_manager):
        with pytest.raises(ValueError, match="No model configured for role"):
            await inject_mock_manager.generate(
                role="nonexistent_role",
                prompt="test",
            )

    async def test_load_model_for_role(self, inject_mock_manager):
        success = await inject_mock_manager.load_model_for_role("router")
        assert success is True

    async def test_unload_model_for_role(self, inject_mock_manager):
        await inject_mock_manager.load_model_for_role("router")
        success = await inject_mock_manager.unload_model_for_role("router")
        assert success is True

    async def test_load_unknown_role(self, inject_mock_manager):
        success = await inject_mock_manager.load_model_for_role("nonexistent")
        assert success is False

    async def test_get_tier_config(self, inject_mock_manager):
        tier = inject_mock_manager.get_tier_config()
        assert tier.vram_budget_gb > 0
        assert tier.max_concurrent_models >= 1


# ===========================================================================
# 4. Model Manager REST API Tests
# ===========================================================================

class TestModelEndpoints:

    def test_backend_health_endpoint_healthy(self, client, inject_mock_manager):
        """GET /api/v1/models/health must report healthy when backend is up."""
        response = client.get("/api/v1/models/health")
        assert response.status_code == 200
        data = response.json()
        assert data["healthy"] is True
        assert "provider" in data
        assert "message" in data

    def test_backend_health_endpoint_unhealthy(self, client):
        """GET /api/v1/models/health must report unhealthy when backend is down."""
        unhealthy_manager = _make_mock_manager(always_healthy=False)
        set_model_manager(unhealthy_manager)
        response = client.get("/api/v1/models/health")
        assert response.status_code == 200
        data = response.json()
        assert data["healthy"] is False

    def test_list_models_endpoint(self, client):
        """GET /api/v1/models must return model list with backend health flag."""
        response = client.get("/api/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "total" in data
        assert "backend_healthy" in data
        assert data["total"] == len(data["models"])

    def test_tier_config_endpoint(self, client):
        """GET /api/v1/models/tier must return active tier and model roles."""
        response = client.get("/api/v1/models/tier")
        assert response.status_code == 200
        data = response.json()
        assert "tier_name" in data
        assert "vram_budget_gb" in data
        assert "models" in data
        # Must include at least one model role
        assert len(data["models"]) > 0
        role_names = {m["role"] for m in data["models"]}
        assert "router" in role_names

    def test_generate_text_endpoint(self, client):
        """POST /api/v1/models/generate must return text for a valid role."""
        payload = {
            "role": "reasoning",
            "prompt": "Summarise corrosion findings for pipe P-104.",
            "temperature": 0.2,
            "structured": False,
        }
        response = client.post("/api/v1/models/generate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "reasoning"
        assert "model_tag" in data
        assert data["text"] is not None
        assert data["structured"] is None

    def test_generate_structured_endpoint(self, client):
        """POST /api/v1/models/generate with structured=True must return dict."""
        payload = {
            "role": "coder",
            "prompt": "Extract equipment data as JSON.",
            "structured": True,
        }
        response = client.post("/api/v1/models/generate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["structured"] is not None
        assert isinstance(data["structured"], dict)
        assert data["text"] is None

    def test_generate_invalid_role_returns_400(self, client):
        """POST /api/v1/models/generate with an unknown role must return 400."""
        payload = {
            "role": "nonexistent_role",
            "prompt": "test",
            "structured": False,
        }
        response = client.post("/api/v1/models/generate", json=payload)
        assert response.status_code == 400

    def test_generate_empty_prompt_returns_422(self, client):
        """POST /api/v1/models/generate with empty prompt must fail validation."""
        payload = {"role": "reasoning", "prompt": "", "structured": False}
        response = client.post("/api/v1/models/generate", json=payload)
        assert response.status_code == 422


# ===========================================================================
# 5. Ollama Adapter Construction Guard
# ===========================================================================

class TestOllamaAdapterGuard:

    def test_external_url_rejected(self):
        """OllamaAdapter must reject non-loopback URLs to protect air-gap sovereignty."""
        from backend.app.services.model_manager.ollama_adapter import OllamaAdapter
        with pytest.raises(ValueError, match="loopback"):
            OllamaAdapter(base_url="http://external-server.example.com:11434")

    def test_localhost_url_accepted(self):
        """OllamaAdapter must accept http://localhost as a valid loopback address."""
        try:
            from app.services.model_manager.ollama_adapter import OllamaAdapter
        except ImportError:
            from backend.app.services.model_manager.ollama_adapter import OllamaAdapter
        adapter = OllamaAdapter(base_url="http://localhost:11434")
        assert adapter is not None

    def test_loopback_url_accepted(self):
        """OllamaAdapter must accept http://127.0.0.1 as a valid loopback address."""
        try:
            from app.services.model_manager.ollama_adapter import OllamaAdapter
        except ImportError:
            from backend.app.services.model_manager.ollama_adapter import OllamaAdapter
        adapter = OllamaAdapter(base_url="http://127.0.0.1:11434")
        assert adapter is not None
