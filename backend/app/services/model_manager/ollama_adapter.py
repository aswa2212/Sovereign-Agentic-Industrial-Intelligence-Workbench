"""
SIH26117 — Ollama Inference Backend Adapter
Concrete InferenceBackend implementation communicating with a local Ollama server
via its REST API over httpx.AsyncClient.

All network calls are directed exclusively to 127.0.0.1 (loopback) — no external egress.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

try:
    from app.services.model_manager.base import InferenceBackend, ModelCapabilities, ModelInfo
except ImportError:
    from backend.app.services.model_manager.base import (
        InferenceBackend,
        ModelCapabilities,
        ModelInfo,
    )

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Capability hints from known model families.
# Ollama's API does not expose structured capability metadata, so we derive
# best-effort capabilities from model tag patterns.
# ---------------------------------------------------------------------------

def _infer_capabilities(tag: str) -> ModelCapabilities:
    tag_lower = tag.lower()
    return ModelCapabilities(
        supports_vision="vl" in tag_lower or "vision" in tag_lower or "llava" in tag_lower,
        supports_tools=(
            "coder" in tag_lower
            or "qwen2.5" in tag_lower
            or "mistral" in tag_lower
        ),
        supports_thinking="r1" in tag_lower or "think" in tag_lower,
        max_context_length=(
            8192
            if any(k in tag_lower for k in ("7b", "8b", "14b", "r1"))
            else 4096
        ),
    )


# ---------------------------------------------------------------------------
# Ollama Adapter
# ---------------------------------------------------------------------------

class OllamaAdapter(InferenceBackend):
    """
    InferenceBackend adapter for a locally-running Ollama server.

    Uses httpx.AsyncClient for all HTTP communication.
    The base_url MUST resolve to loopback (127.0.0.1 / localhost) to preserve
    air-gap sovereignty.  Any external address is rejected at construction time.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: int = 120,
    ) -> None:
        # Sovereignty guard: reject non-loopback Ollama URLs at boot time
        if not any(
            base_url.startswith(prefix)
            for prefix in ("http://127.0.0.1", "http://localhost", "http://[::1]")
        ):
            raise ValueError(
                f"OllamaAdapter base_url '{base_url}' points outside loopback. "
                "Air-gap sovereignty requires Ollama on 127.0.0.1."
            )

        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout_seconds, connect=5.0)
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
        )

    # ------------------------------------------------------------------ #
    # InferenceBackend interface
    # ------------------------------------------------------------------ #

    async def list_available_models(self) -> List[ModelInfo]:
        """
        Query `GET /api/tags` on the Ollama server and translate to ModelInfo objects.
        Returns an empty list if Ollama is not running (graceful degradation).
        """
        try:
            resp = await self._client.get("/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = []
            for raw in data.get("models", []):
                tag = raw.get("name", "unknown")
                model_id = tag
                models.append(
                    ModelInfo(
                        model_id=model_id,
                        provider="ollama",
                        tag=tag,
                        quantization=raw.get("details", {}).get("quantization_level"),
                        capabilities=_infer_capabilities(tag),
                        is_resident_in_vram=False,  # Ollama manages VRAM internally
                    )
                )
            return models
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.RemoteProtocolError) as exc:
            logger.warning("Ollama not reachable for list_available_models: %s", exc)
            return []
        except Exception as exc:
            logger.error("Unexpected error listing Ollama models: %s", exc, exc_info=True)
            return []

    async def load_model(self, model_id: str) -> bool:
        """
        Pre-warm a model in Ollama by sending an empty generate request.
        Ollama will pull the model into VRAM if not already resident.
        Returns True on success, False if Ollama is unreachable or the model is unknown.
        """
        try:
            resp = await self._client.post(
                "/api/generate",
                json={"model": model_id, "prompt": "", "stream": False},
            )
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            logger.warning("Ollama not reachable for load_model('%s'): %s", model_id, exc)
            return False

    async def unload_model(self, model_id: str) -> bool:
        """
        Signal Ollama to evict a model from VRAM by setting keep_alive to 0.
        This is advisory — Ollama may choose to keep the model resident.
        """
        try:
            resp = await self._client.post(
                "/api/generate",
                json={
                    "model": model_id,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": "0",
                },
            )
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            logger.warning("Ollama not reachable for unload_model('%s'): %s", model_id, exc)
            return False

    async def generate(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        """
        Send a non-streaming generate request to Ollama.
        Raises httpx.HTTPStatusError on non-2xx responses.
        """
        payload: Dict[str, Any] = {
            "model": model_id,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system_prompt:
            payload["system"] = system_prompt

        resp = await self._client.post("/api/generate", json=payload)
        resp.raise_for_status()
        return resp.json().get("response", "")

    async def generate_structured(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Request JSON-mode generation from Ollama (format=json).
        If the response is not valid JSON, raises ValueError.
        """
        payload: Dict[str, Any] = {
            "model": model_id,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature},
        }
        if system_prompt:
            payload["system"] = system_prompt

        resp = await self._client.post("/api/generate", json=payload)
        resp.raise_for_status()

        raw_text = resp.json().get("response", "")
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Ollama returned non-JSON response for model '{model_id}': {raw_text[:200]}"
            ) from exc

    async def health_check(self) -> bool:
        """
        Ping the Ollama root endpoint.
        Returns True if Ollama responds 200, False otherwise.
        """
        try:
            resp = await self._client.get("/", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def aclose(self) -> None:
        """Close the underlying httpx.AsyncClient. Call during application shutdown."""
        await self._client.aclose()
