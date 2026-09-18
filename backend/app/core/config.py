"""
SIH26117 — Sovereign AI Workbench Portable Configuration Module
Fully OS-agnostic configuration system utilizing pathlib.Path.
Supports Windows development, Linux workstations, and on-premise container deployments.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_project_root() -> Path:
    """
    Locate the project root directory portably by walking up from the current file
    until a landmark file (.gitignore or README.md) or parent directory is found.
    Falls back safely to the current working directory.
    """
    current = Path(__file__).resolve()
    # Path(__file__) is backend/app/core/config.py -> 3 levels up is backend/ -> 4 levels up is SIH 2026/
    for parent in current.parents:
        if (parent / "README.md").exists() and (parent / "backend").exists():
            return parent
    return Path.cwd()


class Settings(BaseSettings):
    """Application settings backed by environment variables with portable defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=(),
    )

    # Application Identity
    app_name: str = "SIH26117 Sovereign AI Workbench"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    # Server Binding
    host: str = "127.0.0.1"
    port: int = 8000

    # Sovereignty & Air-Gap Enforcement Policy
    air_gapped_mode: bool = True
    allow_external_connections: bool = False

    # Hardware & Model Architecture Abstraction
    # Tiers: 'dev' (laptop/edge), 'target' (24-48GB workstation), 'cpu' (fallback)
    hardware_tier: str = "dev"
    gpu_backend: str = "cuda"  # 'cuda', 'rocm', 'cpu', etc.
    vram_budget_gb: float = 8.0

    # Local Inference Provider Abstraction
    # Supported future backends: 'ollama', 'llamacpp', 'vllm', 'mock'
    inference_provider: str = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    llamacpp_base_url: str = "http://127.0.0.1:8080"
    vllm_base_url: str = "http://127.0.0.1:8000"
    model_timeout_seconds: int = 120

    # Logging
    log_level: str = "INFO"

    # Base Filesystem Roots (Fully portable pathlib.Path resolution)
    project_root: Path = Field(default_factory=find_project_root)
    data_dir: Path = Field(default=Path("data"))
    raw_data_dir: Path = Field(default=Path("data/raw"))
    processed_data_dir: Path = Field(default=Path("data/processed"))
    model_dir: Path = Field(default=Path("models"))
    output_dir: Path = Field(default=Path("outputs"))
    log_dir: Path = Field(default=Path("logs"))
    knowledge_dir: Path = Field(default=Path("data/knowledge"))
    config_dir: Path = Field(default=Path("models/configs"))
    model_config_path: Path = Field(default=Path("models/configs/model_tiers.yaml"))

    # Ingestion Pipeline Configuration (Phase 4)
    max_upload_size_bytes: int = Field(
        default=52428800, description="Max upload size in bytes (default 50 MB)"
    )
    allowed_upload_extensions: List[str] = Field(
        default=["pdf", "docx", "xlsx", "csv", "png", "jpg", "jpeg"],
        description="Permitted file extensions for ingestion",
    )

    # OCR & Vision Pipeline Configuration (Phase 5)
    tesseract_cmd: Optional[str] = Field(
        default=None, description="Optional custom executable path for tesseract"
    )
    ocr_confidence_threshold: float = Field(
        default=0.60, description="Minimum confidence for OCR tokens to be considered high-confidence"
    )

    # Sovereign RAG & Knowledge Configuration (Phase 6)
    rag_top_k: int = Field(
        default=3, description="Default number of top semantic chunks to retrieve"
    )
    rag_similarity_threshold: float = Field(
        default=0.65, description="Minimum cosine similarity threshold to consider chunk relevant"
    )

    # Agent State Machine & Orchestrator Configuration (Phase 7)
    agent_max_steps: int = Field(
        default=8, description="Maximum execution steps allowed per agent task"
    )
    agent_max_retries: int = Field(
        default=2, description="Maximum retry attempts allowed per plan step"
    )
    agent_step_timeout_seconds: float = Field(
        default=45.0, description="Timeout ceiling for individual plan step execution in seconds"
    )
    agent_global_timeout_seconds: float = Field(
        default=180.0, description="Global wall-clock timeout for entire agent workflow in seconds"
    )

    # Sandboxed Tool Execution Configuration (Phase 8)
    sandbox_enabled: bool = Field(
        default=True, description="Whether tool execution sandbox is enabled"
    )
    sandbox_timeout_seconds: float = Field(
        default=15.0, description="Maximum wall-clock execution timeout per tool invocation in seconds"
    )
    sandbox_memory_limit_mb: int = Field(
        default=512, description="Memory ceiling limit for tool process in megabytes"
    )
    sandbox_max_output_bytes: int = Field(
        default=65536, description="Maximum allowed stdout/stderr capture size in bytes (64 KB)"
    )
    sandbox_max_input_bytes: int = Field(
        default=65536, description="Maximum allowed tool input payload size in bytes (64 KB)"
    )
    sandbox_scratch_dir: str = Field(
        default="data/sandbox/scratch", description="Isolated scratch directory for sandbox execution"
    )

    # Task Router Configuration (Phase 3)
    # Threshold below which confidence triggers fallback to the fallback_role.
    # The implementation plan specifies 0.70 as the design target.
    # NOTE: This is a configurable target, NOT a measured accuracy guarantee.
    router_fallback_threshold: float = 0.70
    # Model role used as universal fallback when confidence is below threshold.
    router_fallback_role: str = "reasoning"
    # Active routing method: 'rules' (Level 0) | 'semantic' (Level 1) | 'classifier' (Level 2)
    router_method: str = "rules"

    # CORS Allowed Origins
    cors_origins: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    @model_validator(mode="after")
    def _resolve_paths(self) -> "Settings":
        if not self.knowledge_dir.is_absolute():
            self.knowledge_dir = self.get_resolved_path(self.knowledge_dir)
        return self

    def get_resolved_path(self, relative_or_absolute: Union[str, Path]) -> Path:
        """
        Resolve a path portably. If relative, anchors it to the project root.
        """
        p = Path(relative_or_absolute)
        if p.is_absolute():
            return p
        return (self.project_root / p).resolve()


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton instance of portable application settings."""
    return Settings()
