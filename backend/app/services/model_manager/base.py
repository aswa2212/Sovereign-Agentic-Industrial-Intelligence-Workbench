"""
SIH26117 — Model Manager Portable Interfaces
Defines model-agnostic and provider-agnostic interfaces.
Decouples application code from specific local inference engines (Ollama, llama.cpp, vLLM).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ModelCapabilities(BaseModel):
    """Declared capabilities of a local model."""

    supports_vision: bool = False
    supports_tools: bool = False
    supports_thinking: bool = False
    max_context_length: int = 4096


class ModelInfo(BaseModel):
    """Metadata describing a loaded or available local model."""

    model_config = {"protected_namespaces": ()}

    model_id: str
    provider: str  # 'ollama', 'llamacpp', 'vllm', 'mock'
    tag: str
    quantization: Optional[str] = None
    capabilities: ModelCapabilities = ModelCapabilities()
    is_resident_in_vram: bool = False


class InferenceBackend(ABC):
    """
    Abstract interface for local inference backends.
    Allows hot-swapping between Ollama, llama.cpp, vLLM, or offline mock runners.
    """

    @abstractmethod
    async def list_available_models(self) -> List[ModelInfo]:
        """List all models registered in the local backend."""
        pass

    @abstractmethod
    async def load_model(self, model_id: str) -> bool:
        """Ensure a model is loaded into memory or VRAM."""
        pass

    @abstractmethod
    async def unload_model(self, model_id: str) -> bool:
        """Unload a model from VRAM to release memory for other models."""
        pass

    @abstractmethod
    async def generate(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> str:
        """Generate a complete text response from the model."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Generate a structured JSON response from the model.
        The backend must instruct the model to return valid JSON.
        Returns a parsed Python dict; raises ValueError if the response is not valid JSON.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verify that the backend process is reachable and responsive.
        Returns True if healthy, False if the backend is unreachable.
        """
        pass
