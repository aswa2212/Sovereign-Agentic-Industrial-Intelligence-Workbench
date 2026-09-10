"""
SIH26117 — Model Tier Configuration Loader
Parses models/configs/model_tiers.yaml and returns strongly-typed Pydantic objects.
The rest of the application receives typed objects — never raw YAML dicts.
"""

from pathlib import Path
from typing import Dict, Optional

import yaml
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Typed schema for a single model entry in the YAML
# ---------------------------------------------------------------------------

class ModelEntry(BaseModel):
    """Typed representation of a single model role entry in model_tiers.yaml."""

    model_config = {"protected_namespaces": ()}

    provider: str = "ollama"
    model_tag: str
    context_window: int = 4096
    quantization: Optional[str] = None
    device: Optional[str] = None  # Used by embedding models (cpu / cuda)


# ---------------------------------------------------------------------------
# Typed schema for a full hardware tier
# ---------------------------------------------------------------------------

class TierConfig(BaseModel):
    """Complete configuration for one hardware tier (dev / target / cpu)."""

    description: str = ""
    vram_budget_gb: float = 8.0
    max_concurrent_models: int = 1
    swap_keep_alive: str = "0m"

    # Named model roles; Optional so a tier need not define every role
    router: Optional[ModelEntry] = None
    reasoning: Optional[ModelEntry] = None
    coder: Optional[ModelEntry] = None
    vision: Optional[ModelEntry] = None
    embedding: Optional[ModelEntry] = None

    def get_model(self, role: str) -> Optional[ModelEntry]:
        """Return the ModelEntry for a named role, or None if not configured."""
        return getattr(self, role, None)

    def list_roles(self) -> Dict[str, ModelEntry]:
        """Return all configured model roles as a dict."""
        return {
            role: entry
            for role in ("router", "reasoning", "coder", "vision", "embedding")
            if (entry := getattr(self, role)) is not None
        }


# ---------------------------------------------------------------------------
# Root YAML schema
# ---------------------------------------------------------------------------

class ModelTiersConfig(BaseModel):
    """Root object parsed from model_tiers.yaml."""

    active_tier: str = "dev"
    tiers: Dict[str, TierConfig] = Field(default_factory=dict)

    def active(self) -> TierConfig:
        """Return the currently-active tier configuration."""
        if self.active_tier not in self.tiers:
            raise KeyError(
                f"active_tier '{self.active_tier}' not found in tiers: "
                f"{list(self.tiers.keys())}"
            )
        return self.tiers[self.active_tier]


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_model_tiers(config_path: Path) -> ModelTiersConfig:
    """
    Load and validate the model tier YAML configuration file.

    Args:
        config_path: Absolute or project-relative path to model_tiers.yaml.

    Returns:
        A fully validated ModelTiersConfig instance.

    Raises:
        FileNotFoundError: If the YAML file does not exist at the given path.
        yaml.YAMLError: If the YAML is malformed.
        pydantic.ValidationError: If the schema does not match the typed models.
    """
    resolved = Path(config_path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(
            f"Model tier config not found: {resolved}\n"
            "Ensure models/configs/model_tiers.yaml exists relative to the project root."
        )

    with resolved.open("r", encoding="utf-8") as fh:
        raw: dict = yaml.safe_load(fh)

    return ModelTiersConfig.model_validate(raw)
