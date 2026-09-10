"""
SIH26117 — Sovereign RAG REST API Schemas
Public request/response DTOs for RAG indexing, semantic retrieval, and status endpoints.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

try:
    from app.services.rag.base import CitationSource, RetrievedChunk
except ImportError:
    from backend.app.services.rag.base import CitationSource, RetrievedChunk


class RAGIndexRequest(BaseModel):
    """Request payload to index a document already ingested and normalized via Phase 4."""

    model_config = ConfigDict(protected_namespaces=())

    document_sha256: str = Field(
        ...,
        description="SHA-256 hash of the processed document stored under data/processed/",
        examples=["e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"],
    )
    target_chunk_tokens: Optional[int] = Field(
        default=500,
        description="Target chunk size in tokens (default ~500)",
    )
    chunk_overlap_tokens: Optional[int] = Field(
        default=50,
        description="Overlap between consecutive chunks in tokens (default ~50)",
    )


class RAGIndexResponse(BaseModel):
    """Response payload returned after successfully chunking and indexing a document."""

    model_config = ConfigDict(protected_namespaces=())

    status: str = Field(default="success")
    document_sha256: str = Field(...)
    source_filename: str = Field(...)
    chunks_indexed: int = Field(...)
    total_index_chunks: int = Field(...)
    index_id: str = Field(...)


class RAGQueryRequest(BaseModel):
    """Semantic query request payload."""

    model_config = ConfigDict(protected_namespaces=())

    query: str = Field(
        ...,
        min_length=1,
        description="Natural language query or standard code reference",
        examples=["minimum wall thickness for class 150 carbon steel"],
    )
    top_k: Optional[int] = Field(
        default=3,
        ge=1,
        le=20,
        description="Maximum number of candidate chunks to return",
    )
    similarity_threshold: Optional[float] = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity threshold; chunks below this are discarded",
    )


class RAGQueryResponse(BaseModel):
    """Search results with structured citation provenance."""

    model_config = ConfigDict(protected_namespaces=())

    query: str = Field(...)
    status: str = Field(
        ...,
        description="'success' if relevant knowledge retrieved; 'insufficient_knowledge' if below threshold",
    )
    retrieved_count: int = Field(...)
    results: List[RetrievedChunk] = Field(default_factory=list)
    citations: List[CitationSource] = Field(default_factory=list)
    message: Optional[str] = Field(default=None)


class RAGStatusResponse(BaseModel):
    """Diagnostic status of the sovereign RAG index and local embedding backend."""

    model_config = ConfigDict(protected_namespaces=())

    status: str = Field(default="ready")
    index_id: str = Field(...)
    backend: str = Field(...)
    total_chunks: int = Field(...)
    indexed_documents_count: int = Field(...)
    dimension: int = Field(...)
    embedding_provider: str = Field(...)
    storage_path: str = Field(...)
