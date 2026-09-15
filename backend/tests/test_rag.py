"""
SIH26117 — Phase 6 Sovereign Knowledge & RAG Layer Test Suite
Verifies:
1. Hierarchical chunker (token budgeting, overlap, table boundary preservation, hierarchy).
2. Local dense embeddings (MockEmbeddingProvider deterministic semantic clustering, unavailable safety).
3. Local persistent vector store (NumPy cosine similarity, disk persistence/reload, threshold filtering).
4. SovereignRetriever (MRPL SOP clause retrieval, threshold rejection, citation provenance).
5. REST API endpoints (/index, /query, /status, error envelopes).
6. Air-gap sovereignty (zero outbound network requests).
"""

import json
from pathlib import Path
import socket
import pytest
from fastapi.testclient import TestClient

try:
    from app.core.config import get_settings
    from app.main import app
    from app.services.ingestion.models import NormalizedDocument, ParsedTable
    from app.services.ingestion.storage import StorageManager
    from app.services.rag.base import (
        DocumentChunk,
        EmbeddingModelUnavailableError,
        EmptyQueryError,
        RetrievedChunk,
    )
    from app.services.rag.chunker import HierarchicalChunker, estimate_token_count, format_table_as_markdown
    from app.services.rag.embeddings import (
        LocalSentenceTransformerEmbeddingProvider,
        MockEmbeddingProvider,
    )
    from app.services.rag.retriever import SovereignRetriever
    from app.services.rag.vector_store import LocalJsonVectorStore
    from app.api.v1.endpoints.rag import set_retriever
except ImportError:
    from backend.app.core.config import get_settings
    from backend.app.main import app
    from backend.app.services.ingestion.models import NormalizedDocument, ParsedTable
    from backend.app.services.ingestion.storage import StorageManager
    from backend.app.services.rag.base import (
        DocumentChunk,
        EmbeddingModelUnavailableError,
        EmptyQueryError,
        RetrievedChunk,
    )
    from backend.app.services.rag.chunker import (
        HierarchicalChunker,
        estimate_token_count,
        format_table_as_markdown,
    )
    from backend.app.services.rag.embeddings import (
        LocalSentenceTransformerEmbeddingProvider,
        MockEmbeddingProvider,
    )
    from backend.app.services.rag.retriever import SovereignRetriever
    from backend.app.services.rag.vector_store import LocalJsonVectorStore
    from backend.app.api.v1.endpoints.rag import set_retriever

client = TestClient(app)


def get_sample_sop_document() -> NormalizedDocument:
    """Load the synthetic MRPL piping inspection SOP fixture."""
    fixture_path = Path(__file__).resolve().parent.parent.parent / "data" / "samples" / "sop_mrpl_piping_inspection.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return NormalizedDocument.model_validate(data)


# ── 1. Chunking Tests ─────────────────────────────────────────────────────────

class TestHierarchicalChunker:
    """Verifies hierarchy, token bounds, overlap, and table preservation."""

    def test_token_estimator(self):
        text = "For Class 150 carbon steel process piping, minimum allowable retired wall thickness is 3.2 mm."
        tokens = estimate_token_count(text)
        assert 10 <= tokens <= 25

    def test_table_markdown_formatter(self):
        table = ParsedTable(
            table_id="tbl_1",
            headers=["NPS", "Rating", "Min Wall"],
            rows=[["2 inch", "Class 150", "3.2 mm"], ["4 inch", "Class 150", "3.2 mm"]],
            row_count=2,
            col_count=3,
            extraction_method="test",
            provenance={"source_filename": "test.pdf", "source_sha256": "123"},
        )
        md = format_table_as_markdown(table)
        assert "| NPS | Rating | Min Wall |" in md
        assert "| 2 inch | Class 150 | 3.2 mm |" in md
        assert "| 4 inch | Class 150 | 3.2 mm |" in md

    def test_chunk_document_hierarchy_and_provenance(self):
        doc = get_sample_sop_document()
        chunker = HierarchicalChunker(target_chunk_tokens=500, chunk_overlap_tokens=50)
        chunks = chunker.chunk_document(doc)

        assert len(chunks) >= 3
        for c in chunks:
            assert c.document_id == doc.document_id
            assert c.source_sha256 == doc.sha256
            assert c.source_document == doc.original_filename
            assert c.chunk_id.startswith(doc.sha256[:12])
            assert len(c.content_sha256) == 64
            assert c.token_count > 0

    def test_chunk_document_table_preservation(self):
        doc = get_sample_sop_document()
        chunker = HierarchicalChunker(target_chunk_tokens=500)
        chunks = chunker.chunk_document(doc)

        # Find table chunk from page 3
        table_chunks = [c for c in chunks if c.chunk_type == "table"]
        assert len(table_chunks) >= 1
        tbl_chunk = table_chunks[0]

        # Verify full table structure is preserved intact without fragmented rows
        assert "tbl_sop_thickness_specs_p3" in tbl_chunk.metadata.get("table_id", "")
        assert "| Nominal Pipe Size (NPS) |" in tbl_chunk.text
        assert "| 2 inch | Class 150 | ASTM A106 Gr. B | 3.91 | 3.20 |" in tbl_chunk.text
        assert "| 10 inch | Class 150 | ASTM A106 Gr. B | 9.27 | 3.20 |" in tbl_chunk.text

    def test_chunk_document_target_clause_presence(self):
        doc = get_sample_sop_document()
        chunker = HierarchicalChunker(target_chunk_tokens=500)
        chunks = chunker.chunk_document(doc)

        # Page 3 target clause
        target_clause = "minimum allowable retired wall thickness shall not be less than 3.2 mm"
        matching = [c for c in chunks if target_clause in c.text]
        assert len(matching) >= 1
        assert matching[0].page_number == 3


# ── 2. Local Embedding Tests ──────────────────────────────────────────────────

class TestEmbeddings:
    """Verifies deterministic mock embeddings and safe unavailable model handling."""

    @pytest.mark.anyio
    async def test_mock_embedding_deterministic_and_normalized(self):
        provider = MockEmbeddingProvider(dim=384)
        assert provider.dimension() == 384
        assert provider.is_available() is True
        assert provider.model_name() == "mock-minilm-l6-v2"

        text = "minimum wall thickness for class 150 carbon steel"
        v1 = await provider.embed_text(text)
        v2 = await provider.embed_text(text)

        assert len(v1) == 384
        assert v1 == v2  # Perfectly deterministic

        # Verify unit L2 norm
        norm = sum(x * x for x in v1) ** 0.5
        assert pytest.approx(norm, rel=1e-4) == 1.0

    @pytest.mark.anyio
    async def test_mock_embedding_semantic_clustering(self):
        """
        Verify that semantically related queries and SOP clauses produce high cosine similarity (>0.70),
        while unrelated queries produce low similarity (<0.35).
        """
        provider = MockEmbeddingProvider(dim=384)

        query = "minimum wall thickness for class 150 carbon steel"
        sop_clause = (
            "Section 4.2 Minimum Allowable Wall Thickness Requirements:\n"
            "For Class 150 carbon steel process piping (ASTM A106 Grade B), "
            "the minimum allowable retired wall thickness shall not be less than 3.2 mm."
        )
        unrelated = "Daily cafeteria lunch specials featuring south indian thali and dessert menu options."

        q_vec = await provider.embed_text(query)
        sop_vec = await provider.embed_text(sop_clause)
        unrelated_vec = await provider.embed_text(unrelated)

        sim_related = sum(q * s for q, s in zip(q_vec, sop_vec))
        sim_unrelated = sum(q * u for q, u in zip(q_vec, unrelated_vec))

        assert sim_related >= 0.70, f"Expected similarity >= 0.70, got {sim_related}"
        assert sim_unrelated <= 0.35, f"Expected similarity <= 0.35, got {sim_unrelated}"

    @pytest.mark.anyio
    async def test_unavailable_provider_raises_error_without_download(self):
        provider = LocalSentenceTransformerEmbeddingProvider(model_name_or_path="bge-base-en-v1.5")
        assert provider.is_available() is False
        with pytest.raises(EmbeddingModelUnavailableError):
            await provider.embed_text("test")


# ── 3. Persistent Local Vector Store Tests ────────────────────────────────────

class TestVectorStore:
    """Verifies vector store persistence, reload, search, and threshold filtering."""

    @pytest.mark.anyio
    async def test_vector_store_crud_and_persistence(self, tmp_path):
        store = LocalJsonVectorStore(index_id="test_index", storage_dir=tmp_path)
        assert store.count() == 0

        chunks = [
            DocumentChunk(
                chunk_id="chk_001",
                document_id="doc_1",
                source_sha256="sha_1",
                source_document="doc1.pdf",
                page_number=1,
                text="Pipe thickness is 3.2 mm",
                content_sha256="c_sha_1",
                token_count=10,
            ),
            DocumentChunk(
                chunk_id="chk_002",
                document_id="doc_1",
                source_sha256="sha_1",
                source_document="doc1.pdf",
                page_number=2,
                text="Pump discharge pressure is 15 bar",
                content_sha256="c_sha_2",
                token_count=12,
            ),
        ]
        # Vectors of dim=4
        embs = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
        ]

        await store.add_chunks(chunks, embs)
        assert store.count() == 2

        # Verify files exist on disk
        assert (tmp_path / "test_index" / "index.npy").exists()
        assert (tmp_path / "test_index" / "metadata.json").exists()

        # Search matching chunk 1
        res = await store.search(query_embedding=[0.95, 0.05, 0.0, 0.0], top_k=1, threshold=0.5)
        assert len(res) == 1
        assert res[0].chunk_id == "chk_001"
        assert res[0].similarity_score > 0.9

        # Reload in a completely separate store instance
        store2 = LocalJsonVectorStore(index_id="test_index", storage_dir=tmp_path, auto_load=True)
        assert store2.count() == 2
        res2 = await store2.search(query_embedding=[0.0, 0.98, 0.0, 0.0], top_k=1, threshold=0.5)
        assert len(res2) == 1
        assert res2[0].chunk_id == "chk_002"

    @pytest.mark.anyio
    async def test_vector_store_threshold_filtering(self, tmp_path):
        store = LocalJsonVectorStore(index_id="thresh_test", storage_dir=tmp_path)
        chunks = [
            DocumentChunk(
                chunk_id="chk_A",
                document_id="doc_A",
                source_sha256="sha_A",
                source_document="docA.pdf",
                text="Text A",
                content_sha256="sha_a",
                token_count=5,
            )
        ]
        await store.add_chunks(chunks, [[1.0, 0.0]])

        # Query vector with low similarity (0.10)
        results = await store.search(query_embedding=[0.10, 0.99], top_k=3, threshold=0.65)
        assert len(results) == 0  # Discarded below 0.65 threshold


# ── 4. Sovereign Retriever Tests ──────────────────────────────────────────────

class TestSovereignRetriever:
    """Verifies end-to-end industrial SOP retrieval, threshold rejection, and citations."""

    @pytest.mark.anyio
    async def test_retriever_sop_target_clause_retrieval(self, tmp_path):
        store = LocalJsonVectorStore(index_id="mrpl_sop_index", storage_dir=tmp_path)
        provider = MockEmbeddingProvider(dim=384)
        retriever = SovereignRetriever(
            vector_store=store,
            embedding_provider=provider,
            default_top_k=3,
            default_threshold=0.65,
        )

        doc = get_sample_sop_document()
        await retriever.index_document(doc)
        assert store.count() > 0

        # Query for known SOP clause
        query = "minimum wall thickness for class 150 carbon steel"
        chunks, citations = await retriever.retrieve_with_citations(query=query)

        assert len(chunks) >= 1
        # Page 3 target clause retrieved in top results
        assert any("3.2 mm" in c.text and "Class 150 carbon steel" in c.text for c in chunks)
        top_chunk = chunks[0]
        assert top_chunk.page_number == 3
        assert top_chunk.similarity_score >= 0.65

        # Check citation provenance
        assert len(citations) == len(chunks)
        top_cit = citations[0]
        assert top_cit.source_document == "SOP-MRPL-PIP-001.pdf"
        assert top_cit.page_number == 3
        assert top_cit.chunk_id == top_chunk.chunk_id
        assert top_cit.content_sha256 == top_chunk.content_sha256

    @pytest.mark.anyio
    async def test_retriever_irrelevant_query_yields_empty_results(self, tmp_path):
        store = LocalJsonVectorStore(index_id="mrpl_sop_index_2", storage_dir=tmp_path)
        retriever = SovereignRetriever(
            vector_store=store,
            embedding_provider=MockEmbeddingProvider(dim=384),
            default_threshold=0.65,
        )
        await retriever.index_document(get_sample_sop_document())

        # Unrelated query
        unrelated_query = "cafeteria lunch daily menu chicken biryani dessert"
        chunks = await retriever.retrieve(unrelated_query)
        # Must be rejected because similarity < 0.65 threshold
        assert len(chunks) == 0

    @pytest.mark.anyio
    async def test_retriever_empty_query_raises_error(self, tmp_path):
        retriever = SovereignRetriever(
            vector_store=LocalJsonVectorStore(index_id="empty_test", storage_dir=tmp_path),
            embedding_provider=MockEmbeddingProvider(),
        )
        with pytest.raises(EmptyQueryError):
            await retriever.retrieve("   ")


# ── 5. REST API Endpoints Tests ───────────────────────────────────────────────

class TestRAGAPI:
    """Verifies /api/v1/rag endpoints (/index, /query, /status)."""

    @pytest.fixture(autouse=True)
    def setup_api(self, tmp_path):
        """Seed processed storage with synthetic SOP fixture."""
        doc = get_sample_sop_document()
        storage = StorageManager()
        # Ensure processed document is stored under data/processed/
        storage.store_processed_document(doc.sha256, doc.model_dump())
        mock_retriever = SovereignRetriever(
            vector_store=LocalJsonVectorStore(index_id="test_api", storage_dir=tmp_path),
            embedding_provider=MockEmbeddingProvider(dim=384),
        )
        set_retriever(mock_retriever)
        yield
        set_retriever(None)

    def test_api_rag_status_initial(self):
        res = client.get("/api/v1/rag/status")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ready"
        assert data["backend"] == "local_numpy_json"
        assert "total_chunks" in data

    def test_api_rag_index_success(self):
        doc = get_sample_sop_document()
        res = client.post(
            "/api/v1/rag/index",
            json={
                "document_sha256": doc.sha256,
                "target_chunk_tokens": 500,
                "chunk_overlap_tokens": 50,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["document_sha256"] == doc.sha256
        assert data["chunks_indexed"] > 0
        assert data["total_index_chunks"] > 0

    def test_api_rag_index_not_found_returns_404(self):
        res = client.post(
            "/api/v1/rag/index",
            json={"document_sha256": "nonexistent_sha256_hash_12345"},
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "NOT_FOUND"

    def test_api_rag_query_success(self):
        # First ensure indexed
        doc = get_sample_sop_document()
        client.post("/api/v1/rag/index", json={"document_sha256": doc.sha256})

        res = client.post(
            "/api/v1/rag/query",
            json={
                "query": "minimum wall thickness for class 150 carbon steel",
                "top_k": 3,
                "similarity_threshold": 0.65,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["retrieved_count"] >= 1
        assert len(data["results"]) >= 1
        assert len(data["citations"]) >= 1
        assert any("3.2 mm" in r["text"] or "3.20" in r["text"] for r in data["results"])
        assert data["citations"][0]["source_document"] == "SOP-MRPL-PIP-001.pdf"

    def test_api_rag_query_insufficient_knowledge(self):
        res = client.post(
            "/api/v1/rag/query",
            json={
                "query": "daily cafeteria dessert menu options chocolate cake",
                "top_k": 3,
                "similarity_threshold": 0.65,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "insufficient_knowledge"
        assert data["retrieved_count"] == 0
        assert data["results"] == []
        assert data["citations"] == []

    def test_api_rag_query_empty_returns_400(self):
        res = client.post(
            "/api/v1/rag/query",
            json={"query": "   "},
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "BAD_REQUEST"


# ── 6. Air-Gap & Sovereignty Verification ─────────────────────────────────────

def test_air_gap_no_outbound_network_calls(monkeypatch, tmp_path):
    """
    Verify that Phase 6 RAG chunking, embedding, vector search, and API execution
    make zero outbound network connections.
    """
    def forbidden_connect(*args, **kwargs):
        raise AssertionError("Air-gap violation: Outbound network connection attempted during RAG execution!")

    monkeypatch.setattr(socket, "create_connection", forbidden_connect)

    store = LocalJsonVectorStore(index_id="air_gap_test", storage_dir=tmp_path)
    retriever = SovereignRetriever(
        vector_store=store,
        embedding_provider=MockEmbeddingProvider(),
    )

    doc = get_sample_sop_document()

    import asyncio
    # Index and query without any network connection
    asyncio.run(retriever.index_document(doc))
    results = asyncio.run(retriever.retrieve("minimum wall thickness for class 150 carbon steel"))
    assert len(results) > 0
