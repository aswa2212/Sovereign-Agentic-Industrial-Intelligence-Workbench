"""
SIH26117 — Sovereign Knowledge & RAG Layer Package
"""

from app.services.rag.base import (
    BaseVectorStore,
    CitationSource,
    DocumentChunk,
    DocumentNotIngestedError,
    EmbeddingModelUnavailableError,
    EmbeddingProvider,
    EmptyQueryError,
    RAGError,
    RetrievedChunk,
    VectorStoreError,
)
from app.services.rag.chunker import HierarchicalChunker
from app.services.rag.embeddings import (
    LocalSentenceTransformerEmbeddingProvider,
    MockEmbeddingProvider,
    ModelManagerEmbeddingProvider,
)
from app.services.rag.retriever import SovereignRetriever
from app.services.rag.vector_store import LocalJsonVectorStore

__all__ = [
    "BaseVectorStore",
    "CitationSource",
    "DocumentChunk",
    "DocumentNotIngestedError",
    "EmbeddingModelUnavailableError",
    "EmbeddingProvider",
    "EmptyQueryError",
    "HierarchicalChunker",
    "LocalJsonVectorStore",
    "LocalSentenceTransformerEmbeddingProvider",
    "MockEmbeddingProvider",
    "ModelManagerEmbeddingProvider",
    "RAGError",
    "RetrievedChunk",
    "SovereignRetriever",
    "VectorStoreError",
]
