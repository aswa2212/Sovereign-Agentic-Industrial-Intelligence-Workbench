"""
SIH26117 — Mock Inference Backend
Deterministic offline adapter for unit tests and development without a GPU.
Returns predictable responses keyed to model_id and prompt prefix.
Zero network calls — operates entirely in-process.
"""

import json
from typing import Any, Dict, List, Optional

try:
    from app.services.model_manager.base import InferenceBackend, ModelCapabilities, ModelInfo
except ImportError:
    from backend.app.services.model_manager.base import (
        InferenceBackend,
        ModelCapabilities,
        ModelInfo,
    )


# ---------------------------------------------------------------------------
# Static catalogue of mock models that the adapter reports as "available"
# ---------------------------------------------------------------------------

_MOCK_MODELS: List[ModelInfo] = [
    ModelInfo(
        model_id="qwen2.5:1.5b",
        provider="mock",
        tag="qwen2.5:1.5b",
        quantization="Q4_K_M",
        capabilities=ModelCapabilities(
            supports_vision=False,
            supports_tools=False,
            max_context_length=4096,
        ),
        is_resident_in_vram=False,
    ),
    ModelInfo(
        model_id="deepseek-r1:7b",
        provider="mock",
        tag="deepseek-r1:7b",
        quantization="Q4_K_M",
        capabilities=ModelCapabilities(
            supports_vision=False,
            supports_tools=False,
            supports_thinking=True,
            max_context_length=8192,
        ),
        is_resident_in_vram=False,
    ),
    ModelInfo(
        model_id="qwen2.5-coder:3b",
        provider="mock",
        tag="qwen2.5-coder:3b",
        quantization="Q4_K_M",
        capabilities=ModelCapabilities(
            supports_tools=True,
            max_context_length=8192,
        ),
        is_resident_in_vram=False,
    ),
    ModelInfo(
        model_id="qwen2.5-vl:3b",
        provider="mock",
        tag="qwen2.5-vl:3b",
        quantization="Q4_K_M",
        capabilities=ModelCapabilities(
            supports_vision=True,
            max_context_length=4096,
        ),
        is_resident_in_vram=False,
    ),
    ModelInfo(
        model_id="nomic-embed-text",
        provider="mock",
        tag="nomic-embed-text",
        capabilities=ModelCapabilities(
            max_context_length=8192,
        ),
        is_resident_in_vram=False,
    ),
]

_LOADED_MODELS: set[str] = set()

# Static response templates used by generate()
_RESPONSE_TEMPLATES: Dict[str, str] = {
    "default": (
        "[MOCK] Sovereign AI Workbench response. "
        "This is a deterministic offline mock reply from {model_id}."
    ),
    "json": json.dumps(
        {
            "result": "mock_structured_result",
            "model": "{model_id}",
            "sovereign": True,
            "confidence": 0.95,
        }
    ),
}


class MockInferenceBackend(InferenceBackend):
    """
    Offline deterministic mock adapter for the InferenceBackend interface.
    Safe for CI, unit tests, and development without local GPU or Ollama.
    """

    def __init__(self, always_healthy: bool = True) -> None:
        """
        Args:
            always_healthy: If False, health_check() returns False,
                            simulating a backend outage for failure-path tests.
        """
        self._always_healthy = always_healthy
        self.loaded_models: set[str] = set()
        self.unloaded_history: List[str] = []
        self.generation_calls: List[Dict[str, Any]] = []
        self.active_concurrency: int = 0
        self.max_observed_concurrency: int = 0

    async def list_available_models(self) -> List[ModelInfo]:
        """Return the static mock model catalogue."""
        result = []
        for m in _MOCK_MODELS:
            result.append(
                ModelInfo(
                    **{
                        **m.model_dump(),
                        "is_resident_in_vram": (m.model_id in _LOADED_MODELS or m.model_id in self.loaded_models),
                    }
                )
            )
        return result

    async def load_model(self, model_id: str) -> bool:
        """
        Simulate loading a model.  Only succeeds if the model is in the catalogue
        or starts with 'mock'.
        """
        known_ids = {m.model_id for m in _MOCK_MODELS}
        if model_id not in known_ids and not model_id.startswith("mock"):
            return False
        _LOADED_MODELS.add(model_id)
        self.loaded_models.add(model_id)
        return True

    async def unload_model(self, model_id: str) -> bool:
        """Simulate unloading a model from VRAM."""
        _LOADED_MODELS.discard(model_id)
        was_loaded = model_id in self.loaded_models
        self.loaded_models.discard(model_id)
        self.unloaded_history.append(model_id)
        return True

    async def generate(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        keep_alive: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Return a deterministic mock text response."""
        self.active_concurrency += 1
        self.max_observed_concurrency = max(self.max_observed_concurrency, self.active_concurrency)
        self.generation_calls.append(
            {
                "model_id": model_id,
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperature": temperature,
                "keep_alive": keep_alive,
                "structured": False,
                **kwargs,
            }
        )
        _LOADED_MODELS.add(model_id)
        self.loaded_models.add(model_id)
        try:
            template = _RESPONSE_TEMPLATES["default"]
            return template.format(model_id=model_id)
        finally:
            self.active_concurrency -= 1

    async def generate_structured(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        keep_alive: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Return a deterministic mock structured JSON response."""
        self.active_concurrency += 1
        self.max_observed_concurrency = max(self.max_observed_concurrency, self.active_concurrency)
        self.generation_calls.append(
            {
                "model_id": model_id,
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperature": temperature,
                "keep_alive": keep_alive,
                "structured": True,
                **kwargs,
            }
        )
        _LOADED_MODELS.add(model_id)
        self.loaded_models.add(model_id)
        try:
            raw = _RESPONSE_TEMPLATES["json"].replace("{model_id}", model_id)
            return json.loads(raw)
        finally:
            self.active_concurrency -= 1

    async def health_check(self) -> bool:
        """Return the configured health state (default: always healthy)."""
        return self._always_healthy

    async def embed(self, model_id: str, texts: List[str]) -> List[List[float]]:
        """Return deterministic mock dense embeddings for testing."""
        if not texts:
            return []
        try:
            from app.services.rag.embeddings import MockEmbeddingProvider
        except ImportError:
            from backend.app.services.rag.embeddings import MockEmbeddingProvider

        dim = 768 if any(k in model_id.lower() for k in ("nomic", "768", "bge-base")) else 384
        provider = MockEmbeddingProvider(dim=dim)
        return await provider.embed_texts(texts)
