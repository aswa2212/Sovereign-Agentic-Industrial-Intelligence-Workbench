"""
SIH26117 — Sovereign RAG REST Endpoints
Provides endpoints for:
1. POST /api/v1/rag/index — Index an already ingested NormalizedDocument by SHA-256.
2. POST /api/v1/rag/query — Query the sovereign knowledge base with threshold guardrails.
3. GET  /api/v1/rag/status — Diagnostic metadata on active vector index and local embedding engine.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status

try:
    from app.schemas.rag import (
        RAGIndexRequest,
        RAGIndexResponse,
        RAGQueryRequest,
        RAGQueryResponse,
        RAGStatusResponse,
    )
    from app.services.ingestion.models import NormalizedDocument
    from app.services.ingestion.storage import StorageManager
    from app.services.rag.chunker import HierarchicalChunker
    from app.services.rag.retriever import SovereignRetriever
except ImportError:
    from backend.app.schemas.rag import (
        RAGIndexRequest,
        RAGIndexResponse,
        RAGQueryRequest,
        RAGQueryResponse,
        RAGStatusResponse,
    )
    from backend.app.services.ingestion.models import NormalizedDocument
    from backend.app.services.ingestion.storage import StorageManager
    from backend.app.services.rag.chunker import HierarchicalChunker
    from backend.app.services.rag.retriever import SovereignRetriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])

# Shared retriever instance
_retriever_instance: Optional[SovereignRetriever] = None


def get_retriever() -> SovereignRetriever:
    """Return singleton SovereignRetriever instance."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = SovereignRetriever()
    return _retriever_instance


def set_retriever(retriever: SovereignRetriever) -> None:
    """Override singleton retriever (useful for testing)."""
    global _retriever_instance
    _retriever_instance = retriever


@router.post(
    "/index",
    response_model=RAGIndexResponse,
    status_code=status.HTTP_200_OK,
    summary="Index an ingested document into the local knowledge store",
)
async def index_document(req: RAGIndexRequest) -> RAGIndexResponse:
    """
    Consumes a document already processed by Phase 4 Ingestion.
    Extracts structure-preserving chunks, generates dense local embeddings,
    and appends to the persistent local vector store.
    """
    storage = StorageManager()
    processed_data = storage.get_processed_document(req.document_sha256)

    if not processed_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "DOCUMENT_NOT_FOUND",
                "message": (
                    f"Document with SHA-256 '{req.document_sha256}' not found in processed store. "
                    "Upload and ingest the document first via /api/v1/files/upload."
                ),
            },
        )

    try:
        norm_doc = NormalizedDocument.model_validate(processed_data)
    except Exception as e:
        logger.error("Corrupted processed document %s: %s", req.document_sha256, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "DOCUMENT_PARSE_ERROR", "message": f"Failed to parse stored document: {str(e)}"},
        ) from e

    chunker = HierarchicalChunker(
        target_chunk_tokens=req.target_chunk_tokens or 500,
        chunk_overlap_tokens=req.chunk_overlap_tokens or 50,
    )

    retriever = get_retriever()
    # Temporarily set custom chunker for this request
    retriever.chunker = chunker

    try:
        chunks = await retriever.index_document(norm_doc)
    except Exception as e:
        logger.error("Failed to index document %s: %s", req.document_sha256, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INDEXING_FAILED", "message": f"Indexing error: {str(e)}"},
        ) from e

    return RAGIndexResponse(
        status="success",
        document_sha256=norm_doc.sha256,
        source_filename=norm_doc.original_filename,
        chunks_indexed=len(chunks),
        total_index_chunks=retriever.vector_store.count(),
        index_id=getattr(retriever.vector_store, "index_id", "default"),
    )


@router.post(
    "/query",
    response_model=RAGQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query the sovereign knowledge base",
)
async def query_knowledge_base(req: RAGQueryRequest) -> RAGQueryResponse:
    """
    Search the local vector store for relevant SOP and standard clauses.
    Enforces minimum similarity threshold to prevent hallucinations.
    """
    clean_query = req.query.strip()
    if not clean_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_QUERY", "message": "Query parameter cannot be empty or whitespace."},
        )

    retriever = get_retriever()

    try:
        chunks, citations = await retriever.retrieve_with_citations(
            query=clean_query,
            top_k=req.top_k,
            threshold=req.similarity_threshold,
        )
    except Exception as e:
        logger.error("Retrieval failed for query '%s': %s", clean_query, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "RETRIEVAL_ERROR", "message": f"Vector search error: {str(e)}"},
        ) from e

    if not chunks:
        return RAGQueryResponse(
            query=clean_query,
            status="insufficient_knowledge",
            retrieved_count=0,
            results=[],
            citations=[],
            message="No sufficiently relevant knowledge found in the indexed standards for this query.",
        )

    return RAGQueryResponse(
        query=clean_query,
        status="success",
        retrieved_count=len(chunks),
        results=chunks,
        citations=citations,
    )


@router.get(
    "/status",
    response_model=RAGStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get RAG vector store and embedding engine status",
)
async def get_rag_status() -> RAGStatusResponse:
    """Return diagnostic telemetry for local vector store and embeddings."""
    retriever = get_retriever()
    store_status = retriever.vector_store.get_status()

    return RAGStatusResponse(
        status="ready",
        index_id=store_status.get("index_id", "default"),
        backend=store_status.get("backend", "local_numpy_json"),
        total_chunks=store_status.get("total_chunks", 0),
        indexed_documents_count=store_status.get("indexed_documents_count", 0),
        dimension=store_status.get("dimension", retriever.embedding_provider.dimension()),
        embedding_provider=retriever.embedding_provider.model_name(),
        storage_path=store_status.get("storage_path", ""),
    )
