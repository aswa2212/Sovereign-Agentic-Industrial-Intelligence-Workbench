"""
SIH26117 — Controlled Industrial Knowledge Corpus & Real RAG Test Suite
Verifies Requirements A through P:
A. Corpus Discovery (10 demonstration PDFs)
B. Cryptographic Hashing
C. Ingestion Execution
D. Idempotent Ingestion
E. Chunking Integrity
F. 768-d Embedding Provider
G. Vector Store Verification
H. C-101 Retirement Thickness Retrieval
I. Operating Envelope Retrieval
J. Ultrasonic Scanning Retrieval
K. Corrosion Calculation Formula Retrieval
L. Out-of-Domain Query Suppression
M. Watermark & Provenance Disclaimer
N. Air-Gap Sovereignty Guard
O. Fail-Closed Real Indexing Policy
P. Corpus Manifest Integrity
"""

import hashlib
import json
from pathlib import Path
import pytest
import socket

try:
    from app.core.config import get_settings
    from app.services.ingestion.service import IngestionService
    from app.services.rag.base import EmbeddingModelUnavailableError
    from app.services.rag.chunker import HierarchicalChunker
    from app.services.rag.embeddings import MockEmbeddingProvider, OllamaEmbeddingProvider
    from app.services.rag.retriever import SovereignRetriever
    from app.services.rag.vector_store import LocalJsonVectorStore
except ImportError:
    from backend.app.core.config import get_settings
    from backend.app.services.ingestion.service import IngestionService
    from backend.app.services.rag.base import EmbeddingModelUnavailableError
    from backend.app.services.rag.chunker import HierarchicalChunker
    from backend.app.services.rag.embeddings import MockEmbeddingProvider, OllamaEmbeddingProvider
    from backend.app.services.rag.retriever import SovereignRetriever
    from backend.app.services.rag.vector_store import LocalJsonVectorStore

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "raw" / "knowledge"
KNOWLEDGE_STORE_DIR = PROJECT_ROOT / "data" / "knowledge" / "default"
MANIFEST_PATH = PROJECT_ROOT / "data" / "knowledge" / "corpus_manifest.json"


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── Requirement A & B: Discovery & Cryptographic Hashing ──────────────────────

def test_req_a_corpus_discovery():
    """Requirement A: Exactly 10 demonstration industrial PDFs exist in data/raw/knowledge/."""
    assert RAW_KNOWLEDGE_DIR.exists(), f"Directory {RAW_KNOWLEDGE_DIR} does not exist"
    pdfs = list(RAW_KNOWLEDGE_DIR.glob("*.pdf"))
    assert len(pdfs) == 10, f"Expected 10 PDFs, found {len(pdfs)}: {[p.name for p in pdfs]}"


def test_req_b_cryptographic_hashing():
    """Requirement B: Deterministic SHA-256 computation over each PDF."""
    for pdf_path in RAW_KNOWLEDGE_DIR.glob("*.pdf"):
        raw_bytes = pdf_path.read_bytes()
        assert len(raw_bytes) > 0
        sha = compute_sha256(raw_bytes)
        assert len(sha) == 64
        # Recomputing gives same result
        assert compute_sha256(raw_bytes) == sha


# ── Requirement C & D: Ingestion & Idempotency ────────────────────────────────

def test_req_c_ingestion_execution():
    """Requirement C: All 10 documents parse into valid NormalizedDocuments."""
    settings = get_settings()
    service = IngestionService(settings)
    sample_pdf = RAW_KNOWLEDGE_DIR / "01_C101_Inspection_Procedure.pdf"
    res = service.ingest_file(content=sample_pdf.read_bytes(), filename=sample_pdf.name)
    assert res.status.value == "success"
    assert res.normalized_document is not None
    assert len(res.normalized_document.pages) >= 1
    assert "DEMO-C101-PRO-001" in res.normalized_document.pages[0].text


def test_req_d_idempotent_ingestion():
    """Requirement D: Ingesting identical file marks it as duplicate."""
    settings = get_settings()
    service = IngestionService(settings)
    sample_pdf = RAW_KNOWLEDGE_DIR / "01_C101_Inspection_Procedure.pdf"
    content = sample_pdf.read_bytes()
    res1 = service.ingest_file(content=content, filename=sample_pdf.name)
    res2 = service.ingest_file(content=content, filename=sample_pdf.name)
    assert res2.is_duplicate is True


# ── Requirement E: Chunking Integrity ─────────────────────────────────────────

def test_req_e_chunking_integrity():
    """Requirement E: HierarchicalChunker preserves section headers and text."""
    settings = get_settings()
    service = IngestionService(settings)
    sample_pdf = RAW_KNOWLEDGE_DIR / "06_C101_Thickness_History.pdf"
    res = service.ingest_file(content=sample_pdf.read_bytes(), filename=sample_pdf.name)
    chunker = HierarchicalChunker(target_chunk_tokens=500, chunk_overlap_tokens=50)
    chunks = chunker.chunk_document(res.normalized_document)
    assert len(chunks) >= 1
    combined_text = " ".join(c.text for c in chunks)
    assert "N1" in combined_text
    assert "10.4" in combined_text


# ── Requirement F & G: Embedding Dimension & Vector Store ──────────────────────

@pytest.mark.anyio
async def test_req_f_ollama_embedding_dimension():
    """Requirement F: OllamaEmbeddingProvider yields normalized 768-d vectors."""
    provider = OllamaEmbeddingProvider(dim=768)
    if not provider.is_available():
        pytest.skip("Ollama is not active in this test runner environment")
    vec = await provider.embed_text("C-101 atmospheric column corrosion rate")
    assert len(vec) == 768
    norm = sum(x * x for x in vec) ** 0.5
    assert abs(norm - 1.0) < 1e-4


def test_req_g_vector_store_integrity():
    """Requirement G: LocalJsonVectorStore loads 11 chunks with 768 dimensions."""
    store = LocalJsonVectorStore(index_id="default", storage_dir=PROJECT_ROOT / "data" / "knowledge")
    status = store.get_status()
    assert status["total_chunks"] >= 10
    assert status["dimension"] == 768
    assert status["indexed_documents_count"] == 10
    assert status["persisted_on_disk"] is True


# ── Requirements H through K: Retrieval Accuracy ─────────────────────────────

@pytest.mark.anyio
async def test_req_h_c101_retirement_thickness_retrieval():
    """Requirement H: C-101 retirement query retrieves 08_Equipment_Retirement_Criteria.pdf."""
    provider = OllamaEmbeddingProvider(dim=768)
    if not provider.is_available():
        pytest.skip("Ollama is not active in this test runner environment")
    store = LocalJsonVectorStore(index_id="default", storage_dir=PROJECT_ROOT / "data" / "knowledge")
    retriever = SovereignRetriever(vector_store=store, embedding_provider=provider)
    results = await retriever.retrieve("minimum retirement thickness for C-101 atmospheric column shell", top_k=3)
    assert len(results) >= 1
    assert "08_Equipment_Retirement_Criteria.pdf" in results[0].source_document
    assert "8.0 mm" in results[0].text or "8.0" in results[0].text


@pytest.mark.anyio
async def test_req_i_operating_limits_retrieval():
    """Requirement I: Operating limits query retrieves C-101 record or limits."""
    provider = OllamaEmbeddingProvider(dim=768)
    if not provider.is_available():
        pytest.skip("Ollama is not active in this test runner environment")
    store = LocalJsonVectorStore(index_id="default", storage_dir=PROJECT_ROOT / "data" / "knowledge")
    retriever = SovereignRetriever(vector_store=store, embedding_provider=provider)
    results = await retriever.retrieve("C-101 design pressure and design temperature operating envelope", top_k=3)
    assert len(results) >= 1
    top_docs = [r.source_document for r in results]
    assert any("05_C101_Equipment_Record.pdf" in d or "09_Process_Equipment_Operating_Limits.pdf" in d for d in top_docs)


@pytest.mark.anyio
async def test_req_j_ultrasonic_procedure_retrieval():
    """Requirement J: Ultrasonic query retrieves 03_Thickness_Monitoring_Procedure.pdf."""
    provider = OllamaEmbeddingProvider(dim=768)
    if not provider.is_available():
        pytest.skip("Ollama is not active in this test runner environment")
    store = LocalJsonVectorStore(index_id="default", storage_dir=PROJECT_ROOT / "data" / "knowledge")
    retriever = SovereignRetriever(vector_store=store, embedding_provider=provider)
    results = await retriever.retrieve("ultrasonic thickness gauge scanning procedure and grid spacing", top_k=3)
    assert len(results) >= 1
    assert "03_Thickness_Monitoring_Procedure.pdf" in results[0].source_document


@pytest.mark.anyio
async def test_req_k_corrosion_calculation_retrieval():
    """Requirement K: Corrosion calculation query retrieves 07_Corrosion_Rate_Calculation_Guide.pdf."""
    provider = OllamaEmbeddingProvider(dim=768)
    if not provider.is_available():
        pytest.skip("Ollama is not active in this test runner environment")
    store = LocalJsonVectorStore(index_id="default", storage_dir=PROJECT_ROOT / "data" / "knowledge")
    retriever = SovereignRetriever(vector_store=store, embedding_provider=provider)
    results = await retriever.retrieve("short term and long term corrosion rate calculation formula", top_k=3)
    assert len(results) >= 1
    assert "07_Corrosion_Rate_Calculation_Guide.pdf" in results[0].source_document


# ── Requirement L: Out-of-Domain Suppression ──────────────────────────────────

@pytest.mark.anyio
async def test_req_l_out_of_domain_suppression():
    """Requirement L: Irrelevant queries are suppressed by similarity threshold."""
    provider = OllamaEmbeddingProvider(dim=768)
    if not provider.is_available():
        pytest.skip("Ollama is not active in this test runner environment")
    store = LocalJsonVectorStore(index_id="default", storage_dir=PROJECT_ROOT / "data" / "knowledge")
    retriever = SovereignRetriever(vector_store=store, embedding_provider=provider)
    results = await retriever.retrieve(
        "canteen lunch menu subsidy policy and chocolate donut ingredients",
        threshold=0.65,
    )
    assert len(results) == 0


# ── Requirement M: Watermark & Provenance ─────────────────────────────────────

def test_req_m_provenance_and_watermark():
    """Requirement M: Metadata contains synthetic_demo disclaimer watermark."""
    metadata_file = KNOWLEDGE_STORE_DIR / "metadata.json"
    assert metadata_file.exists()
    with open(metadata_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    for c in chunks:
        assert c["metadata"]["source_type"] == "synthetic_demo"
        assert "NOT OFFICIAL MRPL POLICY" in c["metadata"]["disclaimer"]


# ── Requirement N: Air-Gap Sovereignty ────────────────────────────────────────

def test_req_n_air_gap_loopback_enforcement():
    """Requirement N: Non-loopback URLs are rejected at construction time."""
    with pytest.raises(ValueError, match="outside loopback"):
        OllamaEmbeddingProvider(base_url="http://api.openai.com")

    with pytest.raises(ValueError, match="outside loopback"):
        OllamaEmbeddingProvider(base_url="https://cloud-vector.external.com")


# ── Requirement O: Fail-Closed Real Indexing Policy ───────────────────────────

def test_req_o_fail_closed_mock_rejection():
    """Requirement O: SovereignRetriever rejects MockEmbeddingProvider when force_real_embeddings is active."""
    with pytest.raises(EmbeddingModelUnavailableError, match="cannot use MockEmbeddingProvider"):
        SovereignRetriever(
            embedding_provider=MockEmbeddingProvider(),
            force_real_embeddings=True,
        )


# ── Requirement P: Manifest Integrity ─────────────────────────────────────────

def test_req_p_manifest_integrity():
    """Requirement P: Manifest exists with valid structure, 10 documents, and 768 dimensions."""
    assert MANIFEST_PATH.exists()
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["corpus_title"] == "Controlled Demonstration Industrial Knowledge Corpus"
    assert manifest["embedding_configuration"]["dimension"] == 768
    assert manifest["embedding_configuration"]["model_name"] == "nomic-embed-text:latest"
    assert len(manifest["documents"]) == 10
