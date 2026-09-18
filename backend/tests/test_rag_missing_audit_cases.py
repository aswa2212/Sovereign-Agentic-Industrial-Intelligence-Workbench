"""
SIH26117 — Phase 5 Sovereign RAG Missing Forensic Audit Tests
Tests explicitly requested by the Phase 5 Forensic Audit:

TEST A: metadata.json missing while index.npy exists.
- Verifies no fabricated metadata
- Verifies no mismatched vector/chunk pairing
- Verifies safe empty/failure behavior per vector-store contract
- Verifies count mismatch protection

TEST B: Mock embeddings vs Production 768-d Neural Index Non-Collision.
- Verifies that mock embeddings cannot accidentally match production neural vectors
  above the 0.65 similarity threshold
- Verifies test environment strictly distinguishes mock vs production embeddings

P5-FINDING-04: Controlled Demonstration Disclaimer Invariant.
- Verifies synthetic demo disclaimer is present in manifest and metadata
- Verifies no document is labeled as official MRPL policy
"""

import json
from pathlib import Path
import numpy as np
import pytest

from app.core.config import get_settings
from app.services.rag.base import VectorStoreError
from app.services.rag.embeddings import MockEmbeddingProvider
from app.services.rag.vector_store import LocalJsonVectorStore


# ── TEST A: Missing Metadata While Index Exists ───────────────────────────────

@pytest.mark.asyncio
async def test_audit_case_a_missing_metadata_safe_failure(tmp_path: Path):
    """
    TEST A: metadata.json is missing while index.npy exists.
    Vector store must fail safe, return empty, not fabricate metadata,
    and never pair vectors with nonexistent or mismatched chunks.
    """
    index_dir = tmp_path / "orphan_index"
    index_dir.mkdir(parents=True, exist_ok=True)

    # Create orphan index.npy without metadata.json
    fake_matrix = np.random.randn(5, 768).astype(np.float32)
    np.save(index_dir / "index.npy", fake_matrix)

    assert (index_dir / "index.npy").exists()
    assert not (index_dir / "metadata.json").exists()

    # Instantiate store with auto_load=True
    store = LocalJsonVectorStore(storage_dir=tmp_path, index_id="orphan_index", auto_load=True)

    # 1. State must be empty — no fabricated chunks
    assert store.count() == 0
    assert store.is_empty() is True
    assert store._matrix is None
    assert store._chunks == []

    # 2. Explicit load() returns False safely
    assert store.load() is False

    # 3. Search over orphan store returns empty list without exception
    query_vec = [0.1] * 768
    results = await store.search(query_vec, top_k=3, threshold=0.5)
    assert results == []


@pytest.mark.asyncio
async def test_audit_case_a_mismatched_matrix_and_metadata_count(tmp_path: Path):
    """
    TEST A (Edge Case): index.npy and metadata.json exist but have unequal row counts.
    Must raise VectorStoreError and reset state to avoid mismatched pairings.
    """
    index_dir = tmp_path / "mismatched_index"
    index_dir.mkdir(parents=True, exist_ok=True)

    # 5 vectors in numpy matrix
    matrix = np.random.randn(5, 768).astype(np.float32)
    np.save(index_dir / "index.npy", matrix)

    # Only 2 metadata entries
    dummy_meta = [
        {
            "chunk_id": f"chunk_{i}",
            "document_id": "doc_1",
            "source_sha256": "abcdef",
            "source_document": "test.pdf",
            "page_number": 1,
            "section_index": i,
            "section_header": None,
            "text": f"text {i}",
            "content_sha256": "123456",
            "token_count": 10,
            "metadata": {},
        }
        for i in range(2)
    ]
    with open(index_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(dummy_meta, f)

    store = LocalJsonVectorStore(storage_dir=tmp_path, index_id="mismatched_index", auto_load=False)

    with pytest.raises(VectorStoreError) as exc_info:
        store.load()
    assert "Vector/metadata count mismatch" in str(exc_info.value)
    assert store.count() == 0
    assert store._matrix is None


# ── TEST B: Mock Embeddings vs Production 768-d Index Non-Collision ───────────

@pytest.mark.asyncio
async def test_audit_case_b_mock_embeddings_do_not_collide_with_production_index():
    """
    TEST B: Mock embeddings must NOT accidentally collide with the production
    768-dimensional neural index (which was embedded with nomic-embed-text).
    Querying the production index with mock 768-d vectors must return 0 results
    above the 0.65 threshold, proving mock vectors cannot corrupt or fabricate
    grounding against real production weights.
    """
    settings = get_settings()
    store = LocalJsonVectorStore(
        storage_dir=settings.knowledge_dir,
        index_id="default",
        auto_load=True,
    )
    assert store.count() == 11
    assert store.get_status()["dimension"] == 768

    mock_provider = MockEmbeddingProvider(dim=768)

    test_queries = [
        "minimum wall thickness for C-101 distillation column",
        "ultrasonic thickness measurement procedure",
        "corrosion rate formula and calculation",
        "operating pressure and temperature envelope",
    ]

    for q in test_queries:
        mock_vec = await mock_provider.embed_text(q)
        assert len(mock_vec) == 768
        # Search production store using mock query vector
        results = await store.search(mock_vec, top_k=3, threshold=0.65)
        # Mock embeddings must NOT collide with neural embeddings above the 0.65 threshold
        assert len(results) == 0, (
            f"Query '{q}' unexpectedly matched production neural vectors "
            f"with score >= 0.65: {[r.similarity_score for r in results]}"
        )


# ── P5-FINDING-04: Synthetic Demo Disclaimer Invariant ────────────────────────

def test_p5_finding_04_synthetic_demo_disclaimer_present():
    """
    P5-FINDING-04: Verify the synthetic demonstration disclaimer is present
    and intact across all production knowledge metadata and manifest.
    Must state: 'NOT OFFICIAL MRPL POLICY — Controlled demonstration corpus for SIH26117'
    """
    settings = get_settings()
    manifest_path = settings.get_resolved_path("data/knowledge/corpus_manifest.json")
    assert manifest_path.exists(), f"Manifest missing at {manifest_path}"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest.get("provenance", {}).get("source_type") == "synthetic_demo"
    assert "NOT OFFICIAL MRPL POLICY" in manifest.get("provenance", {}).get("policy", "")

    metadata_path = settings.get_resolved_path("data/knowledge/default/metadata.json")
    assert metadata_path.exists(), f"Metadata missing at {metadata_path}"

    with open(metadata_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    assert len(chunks) == 11
    for c in chunks:
        meta = c.get("metadata", {})
        assert meta.get("source_type") == "synthetic_demo"
        assert "NOT OFFICIAL MRPL POLICY" in meta.get("disclaimer", "")
