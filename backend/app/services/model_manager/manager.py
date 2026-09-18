"""
SIH26117 — Local Model Manager
Central orchestrator for all local model lifecycle operations.

Responsibilities:
- Load the active hardware tier configuration from model_tiers.yaml.
- Bootstrap the correct InferenceBackend (Ollama or Mock) from settings.
- Enforce serial VRAM loading via asyncio.Semaphore (prevents OOM on 8 GB VRAM).
- Expose a high-level role-based generate() / generate_structured() API to
  the rest of the application so callers never reference model IDs directly.
- Report live health and model availability for the system status endpoint.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from app.core.config import get_settings
    from app.services.model_manager.base import InferenceBackend, ModelInfo
    from app.services.model_manager.config_loader import ModelEntry, ModelTiersConfig, TierConfig, load_model_tiers
    from app.services.model_manager.mock_adapter import MockInferenceBackend
    from app.services.model_manager.ollama_adapter import OllamaAdapter
except ImportError:
    from backend.app.core.config import get_settings
    from backend.app.services.model_manager.base import InferenceBackend, ModelInfo
    from backend.app.services.model_manager.config_loader import (
        ModelEntry,
        ModelTiersConfig,
        TierConfig,
        load_model_tiers,
    )
    from backend.app.services.model_manager.mock_adapter import MockInferenceBackend
    from backend.app.services.model_manager.ollama_adapter import OllamaAdapter

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Provider-agnostic model lifecycle manager.

    The manager is intentionally constructed with a pre-built InferenceBackend so
    that tests can inject a MockInferenceBackend without touching the filesystem or
    network.  Use the class-method factory `from_settings()` to build a production
    instance backed by the application's Settings object.
    """

    def __init__(
        self,
        backend: InferenceBackend,
        tier_config: TierConfig,
        max_concurrent_loads: int = 1,
    ) -> None:
        """
        Args:
            backend:              Concrete inference backend (Ollama or Mock).
            tier_config:          Active hardware tier configuration.
            max_concurrent_loads: Semaphore limit for concurrent VRAM load operations.
                                  Must be 1 on the 8 GB dev laptop to prevent OOM.
        """
        self._backend = backend
        self._tier = tier_config
        # Semaphore prevents concurrent heavy-model loads on constrained hardware
        self._load_semaphore = asyncio.Semaphore(max_concurrent_loads)
        # Execution lock serialises heavyweight model execution on max_concurrent_models == 1
        self._execution_lock = asyncio.Lock()
        self._active_role: Optional[str] = None
        self._active_model_tag: Optional[str] = None
        self._initialized = False

    # ------------------------------------------------------------------ #
    # Factory
    # ------------------------------------------------------------------ #

    @classmethod
    def from_settings(cls) -> "ModelManager":
        """
        Build a production ModelManager from the application's Settings singleton.

        - If inference_provider == 'mock', returns a MockInferenceBackend.
        - Otherwise returns an OllamaAdapter.
        - Loads model_tiers.yaml from the project root.
        """
        settings = get_settings()

        # Resolve YAML path portably relative to project root
        tier_yaml = settings.get_resolved_path(settings.model_config_path)
        tier_config_root = load_model_tiers(tier_yaml)
        active_tier = tier_config_root.active()

        if settings.inference_provider == "mock":
            backend: InferenceBackend = MockInferenceBackend()
        else:
            backend = OllamaAdapter(
                base_url=settings.ollama_base_url,
                timeout_seconds=settings.model_timeout_seconds,
            )

        return cls(
            backend=backend,
            tier_config=active_tier,
            max_concurrent_loads=active_tier.max_concurrent_models,
        )

    # ------------------------------------------------------------------ #
    # Initialization & teardown
    # ------------------------------------------------------------------ #

    async def initialize(self) -> None:
        """
        Perform an initial health check.  Called during FastAPI startup.
        Does not pre-load models — models are loaded on first use to avoid
        consuming all VRAM before the operator needs them.
        """
        healthy = await self._backend.health_check()
        if healthy:
            logger.info("ModelManager initialized — backend is healthy.")
        else:
            logger.warning(
                "ModelManager initialized — backend health check FAILED. "
                "Inference calls will fail until the backend is reachable."
            )
        self._initialized = True

    async def shutdown(self) -> None:
        """
        Release resources.  Called during FastAPI shutdown.
        Closes the httpx client if the backend owns one.
        """
        if hasattr(self._backend, "aclose"):
            await self._backend.aclose()  # type: ignore[attr-defined]
        logger.info("ModelManager shut down.")

    # ------------------------------------------------------------------ #
    # Health & discovery
    # ------------------------------------------------------------------ #

    async def is_backend_healthy(self) -> bool:
        """Return live backend health status."""
        return await self._backend.health_check()

    async def health_check(self) -> bool:
        """Alias for is_backend_healthy returning live backend health status."""
        return await self._backend.health_check()

    async def list_models(self) -> List[ModelInfo]:
        """Return all models the backend reports as available."""
        return await self._backend.list_available_models()

    def get_tier_config(self) -> TierConfig:
        """Return the active hardware tier configuration."""
        return self._tier

    @property
    def active_role(self) -> Optional[str]:
        """Return the role of the model currently active/resident in VRAM."""
        return self._active_role

    @property
    def active_model_tag(self) -> Optional[str]:
        """Return the tag of the model currently active/resident in VRAM."""
        return self._active_model_tag

    # ------------------------------------------------------------------ #
    # Internal lifecycle helpers (assumes _execution_lock is held)
    # ------------------------------------------------------------------ #

    async def _ensure_model_resident(self, role: str, entry: ModelEntry) -> None:
        """
        Ensure the requested model is resident, unloading any previously active
        heavyweight model when max_concurrent_models == 1.

        CRITICAL: Assumes self._execution_lock is already held by the caller.
        """
        if self._tier.max_concurrent_models == 1:
            if self._active_role is not None and (
                self._active_role != role or self._active_model_tag != entry.model_tag
            ):
                if self._active_model_tag:
                    logger.info(
                        "VRAM serial swap: unloading active role '%s' (%s) before activating '%s' (%s)",
                        self._active_role,
                        self._active_model_tag,
                        role,
                        entry.model_tag,
                    )
                    await self._backend.unload_model(self._active_model_tag)
                self._active_role = None
                self._active_model_tag = None

        self._active_role = role
        self._active_model_tag = entry.model_tag

    # ------------------------------------------------------------------ #
    # Model lifecycle (public methods)
    # ------------------------------------------------------------------ #

    async def load_model_for_role(self, role: str) -> bool:
        """
        Load the model assigned to the given role in the active tier.

        When max_concurrent_models == 1, acquires _execution_lock, evicts any
        previously loaded model, and loads the requested model.

        Args:
            role: One of 'router', 'reasoning', 'coder', 'vision', 'embedding'.

        Returns:
            True if the model was loaded (or already loaded), False on failure.
        """
        entry = self._tier.get_model(role)
        if entry is None:
            logger.warning("No model configured for role '%s' in active tier.", role)
            return False

        if self._tier.max_concurrent_models == 1:
            async with self._execution_lock:
                await self._ensure_model_resident(role, entry)
                logger.info("Loading model '%s' for role '%s'.", entry.model_tag, role)
                success = await self._backend.load_model(entry.model_tag)
                if success:
                    logger.info("Model '%s' loaded successfully.", entry.model_tag)
                else:
                    logger.error("Failed to load model '%s'.", entry.model_tag)
                return success
        else:
            async with self._load_semaphore:
                logger.info("Loading model '%s' for role '%s'.", entry.model_tag, role)
                success = await self._backend.load_model(entry.model_tag)
                if success:
                    self._active_role = role
                    self._active_model_tag = entry.model_tag
                    logger.info("Model '%s' loaded successfully.", entry.model_tag)
                else:
                    logger.error("Failed to load model '%s'.", entry.model_tag)
                return success

    async def unload_model_for_role(self, role: str) -> bool:
        """
        Unload the model assigned to the given role to free VRAM.

        Returns:
            True if the model was unloaded, False if the role is unconfigured or
            the backend reports failure.
        """
        entry = self._tier.get_model(role)
        if entry is None:
            logger.warning("No model configured for role '%s' in active tier.", role)
            return False

        logger.info("Unloading model '%s' for role '%s'.", entry.model_tag, role)
        if self._tier.max_concurrent_models == 1:
            async with self._execution_lock:
                success = await self._backend.unload_model(entry.model_tag)
                if success and (self._active_role == role or self._active_model_tag == entry.model_tag):
                    self._active_role = None
                    self._active_model_tag = None
                return success
        else:
            success = await self._backend.unload_model(entry.model_tag)
            if success and (self._active_role == role or self._active_model_tag == entry.model_tag):
                self._active_role = None
                self._active_model_tag = None
            return success

    # ------------------------------------------------------------------ #
    # High-level generation (role-based, never model-ID-based in callers)
    # ------------------------------------------------------------------ #

    async def generate(
        self,
        role: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        keep_alive: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """
        Generate text using the model assigned to the given role.

        When max_concurrent_models == 1, execution is serialised under _execution_lock,
        ensuring any differing active model is unloaded before execution starts.

        Args:
            role:          Model role ('router', 'reasoning', 'coder', 'vision', 'embedding').
            prompt:        The user prompt.
            system_prompt: Optional system/instruction prompt.
            temperature:   Sampling temperature (lower -> more deterministic).
            keep_alive:    Optional override for model unload duration (defaults to tier.swap_keep_alive).

        Returns:
            Generated text string.

        Raises:
            ValueError: If no model is configured for the requested role.
        """
        entry = self._tier.get_model(role)
        if entry is None:
            raise ValueError(
                f"No model configured for role '{role}' in active tier "
                f"'{self._tier.description}'."
            )

        ka = kwargs.pop("keep_alive", keep_alive)
        effective_keep_alive = ka if ka is not None else getattr(self._tier, "swap_keep_alive", None)

        if self._tier.max_concurrent_models == 1:
            async with self._execution_lock:
                await self._ensure_model_resident(role, entry)
                return await self._backend.generate(
                    model_id=entry.model_tag,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    keep_alive=effective_keep_alive,
                    **kwargs,
                )
        else:
            return await self._backend.generate(
                model_id=entry.model_tag,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                keep_alive=effective_keep_alive,
                **kwargs,
            )

    async def generate_structured(
        self,
        role: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        keep_alive: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Generate a structured JSON response using the model assigned to the role.

        When max_concurrent_models == 1, execution is serialised under _execution_lock,
        ensuring any differing active model is unloaded before execution starts.

        Returns:
            Parsed Python dict.

        Raises:
            ValueError: If no model is configured for the requested role,
                        or the model returns non-JSON output.
        """
        entry = self._tier.get_model(role)
        if entry is None:
            raise ValueError(
                f"No model configured for role '{role}' in active tier "
                f"'{self._tier.description}'."
            )

        ka = kwargs.pop("keep_alive", keep_alive)
        effective_keep_alive = ka if ka is not None else getattr(self._tier, "swap_keep_alive", None)

        if self._tier.max_concurrent_models == 1:
            async with self._execution_lock:
                await self._ensure_model_resident(role, entry)
                return await self._backend.generate_structured(
                    model_id=entry.model_tag,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    keep_alive=effective_keep_alive,
                    **kwargs,
                )
        else:
            return await self._backend.generate_structured(
                model_id=entry.model_tag,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                keep_alive=effective_keep_alive,
                **kwargs,
            )

    async def embed(
        self,
        role: str,
        texts: List[str],
    ) -> List[List[float]]:
        """
        Generate dense embeddings for a list of texts using the model assigned to the role.

        Embedding models run on CPU (or local memory) and do not participate in
        heavyweight GPU VRAM residency eviction, preserving serial generation model
        lifecycle without GPU contention.

        Args:
            role: Model role, typically 'embedding'.
            texts: List of text strings to embed.

        Returns:
            List of normalized embedding vectors (floats).

        Raises:
            ValueError: If no model is configured for the role.
        """
        entry = self._tier.get_model(role)
        if entry is None:
            raise ValueError(
                f"No model configured for role '{role}' in active tier "
                f"'{self._tier.description}'."
            )

        return await self._backend.embed(model_id=entry.model_tag, texts=texts)
