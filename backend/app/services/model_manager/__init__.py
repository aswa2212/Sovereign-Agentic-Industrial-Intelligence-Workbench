"""
SIH26117 — Local Model Manager Package

Public exports for the rest of the application:
- ModelManager      → high-level role-based orchestrator
- OllamaAdapter     → production Ollama HTTP backend
- MockInferenceBackend → offline test backend
- InferenceBackend  → abstract base for custom adapters
- ModelInfo, ModelCapabilities → shared type contracts
- load_model_tiers  → YAML config loader
"""

from .base import InferenceBackend, ModelCapabilities, ModelInfo
from .config_loader import ModelTiersConfig, TierConfig, load_model_tiers
from .manager import ModelManager
from .mock_adapter import MockInferenceBackend
from .ollama_adapter import OllamaAdapter

__all__ = [
    "ModelManager",
    "OllamaAdapter",
    "MockInferenceBackend",
    "InferenceBackend",
    "ModelInfo",
    "ModelCapabilities",
    "ModelTiersConfig",
    "TierConfig",
    "load_model_tiers",
]
