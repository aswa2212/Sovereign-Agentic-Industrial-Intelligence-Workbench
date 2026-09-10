"""
SIH26117 — Sovereign RAG & Knowledge Layer Data Contracts & Interfaces
Defines immutable citation provenance, chunk representations, embedding provider abstractions,
and vector store protocols.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ── Exceptions ────────────────────────────────────────────────────────────────

class RAGError(Exception):
    """Base exception for all Sovereign RAG subsystem errors."""
    pass


class EmbeddingModelUnavailableError(RAGError):
    """Raised when the configured embedding provider is not available or weights missing."""
    pass


class VectorStoreError(RAGError):
    """Raised on index corruption, I/O errors, or dimensionality mismatches."""
    pass


class DocumentNotIngestedError(RAGError):
    """Raised when requesting RAG indexing for a document SHA-256 not found in Phase 4 storage."""
    pass


class EmptyQueryError(RAGError):
    """Raised when a search query is empty or whitespace-only."""
    pass


# ── Data Contracts ────────────────────────────────────────────────────────────

class CitationSource(BaseModel):
    """
    Traceable citation pointing back to the verified source artifact and page.
    Preserves exact provenance for auditability under MRPL and industrial standards.
    """

    model_config = ConfigDict(protected_namespaces=())

    source_document: str = Field(..., description="Original filename (e.g. SOP-MRPL-PIP-001.pdf)")
    page_number: Optional[int] = Field(default=None, description="1-based page number if available")
    chunk_id: str = Field(..., description="Unique chunk identifier")
    content_sha256: str = Field(..., description="Cryptographic hash of chunk text")
    similarity_score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")


class DocumentChunk(BaseModel):
    """
    Atomic text or table unit produced by the hierarchical chunker.
    Retains parent document provenance, section hierarchy, and content hashes.
    """

    model_config = ConfigDict(protected_namespaces=())

    chunk_id: str = Field(..., description="Unique deterministic identifier for this chunk")
    document_id: str = Field(..., description="Parent document identifier")
    source_sha256: str = Field(..., description="SHA-256 hash of the parent raw document")
    source_document: str = Field(..., description="Original filename of parent document")
    page_number: Optional[int] = Field(default=None, description="1-based page number where chunk starts")
    section_index: Optional[int] = Field(default=None, description="Section or paragraph index")
    section_header: Optional[str] = Field(default=None, description="Current heading or title context")
    text: str = Field(..., description="Extracted chunk text or markdown table")
    content_sha256: str = Field(..., description="SHA-256 of the chunk text itself")
    token_count: int = Field(..., description="Estimated or exact token count")
    chunk_type: str = Field(default="text", description="'text', 'table', or 'header'")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary extraction metadata")


class RetrievedChunk(BaseModel):
    """
    Search candidate returned by the SovereignRetriever.
    Includes vector similarity score and citation information.
    """

    model_config = ConfigDict(protected_namespaces=())

    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: str = Field(..., description="Parent document identifier")
    source_sha256: str = Field(..., description="Parent document SHA-256")
    source_document: str = Field(..., description="Original filename")
    page_number: Optional[int] = Field(default=None, description="1-based page number")
    section_index: Optional[int] = Field(default=None, description="Section index")
    section_header: Optional[str] = Field(default=None, description="Heading context")
    text: str = Field(..., description="Retrieved chunk text")
    similarity_score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    content_sha256: str = Field(..., description="SHA-256 of the chunk text")
    token_count: int = Field(..., description="Chunk token count")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary metadata")

    def to_citation(self) -> CitationSource:
        """Convert retrieved chunk to structured citation anchor."""
        return CitationSource(
            source_document=self.source_document,
            page_number=self.page_number,
            chunk_id=self.chunk_id,
            content_sha256=self.content_sha256,
            similarity_score=self.similarity_score,
        )


# ── Provider & Store Interfaces ───────────────────────────────────────────────

class EmbeddingProvider(ABC):
    """
    Abstract interface for local dense text embeddings.
    Strictly local/on-premise; decoupled from cloud APIs.
    """

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate normalized embedding vector for a single text."""
        ...

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate batch normalized embedding vectors."""
        ...

    @abstractmethod
    def dimension(self) -> int:
        """Vector dimensionality (e.g. 384, 768, 1024)."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if local model or weights are present."""
        ...

    @abstractmethod
    def model_name(self) -> str:
        """Canonical model tag or identifier."""
        ...


class BaseVectorStore(ABC):
    """
    Abstract interface for local persistent vector storage.
    Persists vectors and metadata portably under data/knowledge/.
    """

    @abstractmethod
    async def add_chunks(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
    ) -> None:
        """Insert chunks with corresponding normalized embedding vectors."""
        ...

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 3,
        threshold: float = 0.65,
    ) -> List[RetrievedChunk]:
        """
        Execute vector similarity search.
        Discards candidates below threshold.
        """
        ...

    @abstractmethod
    def persist(self) -> Any:
        """Save vector index and chunk metadata to disk."""
        ...

    @abstractmethod
    def load(self) -> bool:
        """Load vector index and chunk metadata from disk."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Return total number of indexed chunks."""
        ...

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic metrics (indexed docs, total vectors, backend)."""
        ...
