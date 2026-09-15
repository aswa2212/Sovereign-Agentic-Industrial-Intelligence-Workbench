"""
SIH26117 — Sovereign Knowledge & RAG Layer Package
"""

try:
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
        OllamaEmbeddingProvider,
    )
    from app.services.rag.retriever import SovereignRetriever
    from app.services.rag.vector_store import LocalJsonVectorStore
except ImportError:
    from backend.app.services.rag.base import (
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
    from backend.app.services.rag.chunker import HierarchicalChunker
    from backend.app.services.rag.embeddings import (
        LocalSentenceTransformerEmbeddingProvider,
        MockEmbeddingProvider,
        ModelManagerEmbeddingProvider,
        OllamaEmbeddingProvider,
    )
    from backend.app.services.rag.retriever import SovereignRetriever
    from backend.app.services.rag.vector_store import LocalJsonVectorStore

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
    "OllamaEmbeddingProvider",
    "RAGError",
    "RetrievedChunk",
    "SovereignRetriever",
    "VectorStoreError",
]

