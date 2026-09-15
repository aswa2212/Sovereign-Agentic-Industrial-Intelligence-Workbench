"""
SIH26117 — Controlled Industrial Knowledge Corpus Indexer
Indexes the 10 demonstration synthetic PDFs from data/raw/knowledge/ into the sovereign vector store.

CRITICAL POLICY:
Real knowledge indexing MUST FAIL CLOSED if nomic-embed-text:latest is unavailable on Ollama (http://127.0.0.1:11434).
Mock embeddings are NEVER permitted for real corpus indexing.
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone

# Ensure project root and backend are in path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import asyncio
from backend.app.core.config import get_settings
from backend.app.services.ingestion.service import IngestionService
from backend.app.services.rag.chunker import HierarchicalChunker
from backend.app.services.rag.embeddings import OllamaEmbeddingProvider
from backend.app.services.rag.vector_store import LocalJsonVectorStore
from backend.app.services.rag.base import EmbeddingModelUnavailableError


def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


async def main():
    print("=" * 70)
    print("SIH26117 — CONTROLLED INDUSTRIAL KNOWLEDGE CORPUS INDEXER")
    print("Corpus: Controlled Demonstration Industrial Knowledge Corpus")
    print("Watermark: DEMONSTRATION SYNTHETIC CORPUS FOR SIH26117 — NOT OFFICIAL MRPL POLICY")
    print("=" * 70)

    settings = get_settings()
    raw_dir = ROOT_DIR / "data" / "raw" / "knowledge"
    knowledge_dir = ROOT_DIR / "data" / "knowledge" / "default"
    backup_dir = ROOT_DIR / "data" / "knowledge" / "default_backup_phase16"
    manifest_path = ROOT_DIR / "data" / "knowledge" / "corpus_manifest.json"

    # 1. FAIL-CLOSED CHECK FOR REAL LOCAL EMBEDDING MODEL
    print("\n[Stage 1/6] Verifying Local Embedding Engine (Sovereign Loopback)...")
    provider = OllamaEmbeddingProvider(
        base_url=settings.ollama_base_url,
        model_name="nomic-embed-text:latest",
        dim=768,
        timeout_seconds=30.0,
    )

    if not provider.is_available():
        print("\n" + "!" * 70)
        print("FATAL ERROR: Real local embedding model unavailable!")
        print(f"Ollama server must be active on {settings.ollama_base_url}")
        print("and 'nomic-embed-text:latest' (768-d) must be pulled.")
        print("POLICY: Real knowledge indexing must NEVER fall back to mock embeddings.")
        print("!" * 70 + "\n")
        sys.exit(1)

    print(f"  [OK] Ollama reachable on {settings.ollama_base_url}")
    print(f"  [OK] Model '{provider.model_name()}' confirmed active (dimension={provider.dimension()})")

    # Quick test embedding to guarantee model responds correctly
    test_vec = await provider.embed_text("Refinery C-101 atmospheric column corrosion rate test")
    if len(test_vec) != 768:
        print(f"FATAL: Expected 768 dimensions from nomic-embed-text, got {len(test_vec)}")
        sys.exit(1)
    print(f"  [OK] Test embedding validated: vector length = {len(test_vec)}")

    # 2. DISCOVER RAW PDF CORPUS
    print("\n[Stage 2/6] Discovering Raw PDF Documents in data/raw/knowledge/...")
    if not raw_dir.exists():
        print(f"FATAL: Directory {raw_dir} does not exist.")
        sys.exit(1)

    pdf_files = sorted(list(raw_dir.glob("*.pdf")))
    if len(pdf_files) != 10:
        print(f"WARNING: Expected 10 PDFs in {raw_dir}, found {len(pdf_files)}")
    else:
        print(f"  [OK] Found exactly {len(pdf_files)} demonstration PDFs.")

    # 3. BACKUP PREVIOUS 384-DIM MOCK INDEX IF PRESENT
    print("\n[Stage 3/6] Backing up previous index to default_backup_phase16/...")
    backup_dir.mkdir(parents=True, exist_ok=True)
    for fname in ["index.npy", "metadata.json"]:
        src = knowledge_dir / fname
        if src.exists():
            dest = backup_dir / fname
            shutil.copy2(src, dest)
            print(f"  Backed up {src.name} -> {dest}")

    # Initialize fresh 768-dim vector store
    print("\n[Stage 4/6] Initializing Sovereign LocalJsonVectorStore (768-d)...")
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    vector_store = LocalJsonVectorStore(index_id="default", storage_dir=ROOT_DIR / "data" / "knowledge")
    vector_store.clear()  # Start clean for homogeneous 768-dim index
    print(f"  [OK] Vector store cleared for fresh 768-d indexing at {knowledge_dir}")

    # 4. INGEST AND INDEX EACH PDF
    print("\n[Stage 5/6] Ingesting Documents & Generating 768-d Nomic Chunks...")
    ingestion_service = IngestionService(settings)
    chunker = HierarchicalChunker(target_chunk_tokens=500, chunk_overlap_tokens=50)

    indexed_summary = []
    total_chunks_indexed = 0

    for idx, pdf_path in enumerate(pdf_files, 1):
        file_bytes = pdf_path.read_bytes()
        file_sha256 = compute_file_sha256(pdf_path)
        file_size = len(file_bytes)

        print(f"  [{idx:02d}/10] Processing {pdf_path.name} ({file_size / 1024:.1f} KB)...")
        print(f"         SHA-256: {file_sha256}")

        # Ingestion pipeline
        ingest_result = ingestion_service.ingest_file(
            content=file_bytes,
            filename=pdf_path.name,
        )
        norm_doc = ingest_result.normalized_document

        # Structure-preserving hierarchical chunking
        raw_chunks = chunker.chunk_document(norm_doc)
        print(f"         Extracted {len(raw_chunks)} chunks from {len(norm_doc.pages)} pages")

        # Inject demonstration corpus watermark and provenance into chunk metadata
        for chunk in raw_chunks:
            chunk.metadata["source_type"] = "synthetic_demo"
            chunk.metadata["corpus_name"] = "Controlled Demonstration Industrial Knowledge Corpus"
            chunk.metadata["disclaimer"] = "DEMONSTRATION SYNTHETIC CORPUS FOR SIH26117 — NOT OFFICIAL MRPL POLICY"
            chunk.metadata["indexed_at"] = datetime.now(timezone.utc).isoformat()
            chunk.metadata["source_filename"] = pdf_path.name

        # Dense embedding via real Ollama nomic-embed-text
        texts = [c.text for c in raw_chunks]
        embeddings = await provider.embed_texts(texts)

        # Append to vector store
        await vector_store.add_chunks(chunks=raw_chunks, embeddings=embeddings)
        total_chunks_indexed += len(raw_chunks)

        indexed_summary.append({
            "order": idx,
            "filename": pdf_path.name,
            "sha256": file_sha256,
            "size_bytes": file_size,
            "pages": len(norm_doc.pages),
            "tables_extracted": len(norm_doc.tables),
            "chunks_indexed": len(raw_chunks),
            "extraction_status": norm_doc.status.value if hasattr(norm_doc.status, "value") else str(norm_doc.status),
        })

    # Persist vector store
    vector_store.persist()
    print(f"\n  [OK] All 10 documents indexed. Total vectors in store: {vector_store.count()}")

    # 5. GENERATE CORPUS MANIFEST
    print("\n[Stage 6/6] Writing Corpus Manifest (data/knowledge/corpus_manifest.json)...")
    manifest = {
        "corpus_title": "Controlled Demonstration Industrial Knowledge Corpus",
        "provenance": {
            "source_type": "synthetic_demo",
            "policy": "NOT OFFICIAL MRPL POLICY — Controlled demonstration corpus for SIH26117",
            "license": "SIH26117 Educational & Demonstration License",
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        },
        "embedding_configuration": {
            "provider": "OllamaEmbeddingProvider",
            "model_name": "nomic-embed-text:latest",
            "dimension": 768,
            "endpoint": settings.ollama_base_url,
            "metric": "cosine",
            "normalized": True,
        },
        "vector_store": {
            "backend": "LocalJsonVectorStore",
            "index_id": "default",
            "total_chunks": vector_store.count(),
            "index_npy_sha256": compute_file_sha256(knowledge_dir / "index.npy"),
            "metadata_json_sha256": compute_file_sha256(knowledge_dir / "metadata.json"),
        },
        "documents": indexed_summary,
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"  [OK] Manifest saved to {manifest_path}")

    # Final summary display
    print("\n" + "=" * 70)
    print("INDEXING COMPLETE — SUMMARY OF KNOWLEDGE STORE")
    print("=" * 70)
    print(f"{'#':<3} | {'Filename':<38} | {'Chunks':<6} | {'Status'}")
    print("-" * 70)
    for item in indexed_summary:
        print(f"{item['order']:<3} | {item['filename']:<38} | {item['chunks_indexed']:<6} | {item['extraction_status']}")
    print("-" * 70)
    print(f"Total Vectors:     {vector_store.count()} (768 dimensions each)")
    print(f"index.npy SHA:     {manifest['vector_store']['index_npy_sha256']}")
    print(f"metadata.json SHA: {manifest['vector_store']['metadata_json_sha256']}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
