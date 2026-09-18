"""
SIH26117 — Knowledge Directory Deterministic Resolution Tests (P5-FINDING-02)
Verifies:
- knowledge_dir resolves deterministically from project root regardless of CWD
- When simulated running from project root vs backend/ directory:
  - resolved path is identical
  - dimension is identical (768)
  - production index is loaded
  - historical 384-d fixture (in backend/data/knowledge) is never accidentally selected
"""

import os
from pathlib import Path
import pytest

from app.core.config import Settings
from app.services.rag.vector_store import LocalJsonVectorStore


def test_knowledge_path_resolution_across_cwds(monkeypatch):
    """
    Simulate running from project root vs running from backend/ directory.
    Verifies that settings.knowledge_dir and LocalJsonVectorStore resolve
    to the identical production directory with 768-d dimension.
    """
    # 1. Inspect current root
    base_settings = Settings()
    project_root = base_settings.project_root
    canonical_prod_knowledge = project_root / "data" / "knowledge"
    canonical_index = canonical_prod_knowledge / "default" / "index.npy"

    assert canonical_index.exists(), f"Production index missing at {canonical_index}"

    # 2. Simulate CWD == project_root
    monkeypatch.chdir(project_root)
    settings_root = Settings()
    assert settings_root.knowledge_dir.resolve() == canonical_prod_knowledge.resolve()

    store_root = LocalJsonVectorStore(index_id="default")
    assert store_root.storage_dir.resolve() == (canonical_prod_knowledge / "default").resolve()
    assert store_root.get_status()["dimension"] == 768
    assert store_root.count() == 11

    # 3. Simulate CWD == backend/
    backend_dir = project_root / "backend"
    monkeypatch.chdir(backend_dir)
    settings_backend = Settings()
    assert settings_backend.knowledge_dir.resolve() == canonical_prod_knowledge.resolve()

    store_backend = LocalJsonVectorStore(index_id="default")
    assert store_backend.storage_dir.resolve() == (canonical_prod_knowledge / "default").resolve()
    assert store_backend.get_status()["dimension"] == 768
    assert store_backend.count() == 11

    # 4. Verify historical 384-d fixture in backend/data/knowledge is NEVER selected
    historical_fixture = backend_dir / "data" / "knowledge" / "default"
    assert store_root.storage_dir.resolve() != historical_fixture.resolve()
    assert store_backend.storage_dir.resolve() != historical_fixture.resolve()
