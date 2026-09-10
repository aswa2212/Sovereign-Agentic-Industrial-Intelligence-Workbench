"""
SIH26117 — Sovereign Knowledge Retriever Engine
Coordinates query embedding, vector search, top-k ranking, similarity threshold guardrails,
and citation provenance generation.
"""

import logging
from typing import List, Optional, Tuple

try:
    from app.core.config import get_settings
    from app.services.ingestion.models import NormalizedDocument
    from app.services.rag.base import (
        BaseVectorStore,
        CitationSource,
        DocumentChunk,
        EmbeddingProvider,
        EmptyQueryError,
        RetrievedChunk,
    )
    from app.services.rag.chunker import HierarchicalChunker
    from app.services.rag.embeddings import MockEmbeddingProvider
    from app.services.rag.vector_store import LocalJsonVectorStore
except ImportError:
    from backend.app.core.config import get_settings
    from backend.app.services.ingestion.models import NormalizedDocument
    from backend.app.services.rag.base import (
        BaseVectorStore,
        CitationSource,
        DocumentChunk,
        EmbeddingProvider,
        EmptyQueryError,
        RetrievedChunk,
    )
    from backend.app.services.rag.chunker import HierarchicalChunker
    from backend.app.services.rag.embeddings import MockEmbeddingProvider
    from backend.app.services.rag.vector_store import LocalJsonVectorStore

logger = logging.getLogger(__name__)


class SovereignRetriever:
    """
    High-level retriever orchestrating dense vector search over indexed MRPL SOPs and standards.
    Strictly local/air-gapped. Enforces minimum similarity threshold to avoid hallucinations.
    """

    def __init__(
        self,
        vector_store: Optional[BaseVectorStore] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        chunker: Optional[HierarchicalChunker] = None,
        default_top_k: Optional[int] = None,
        default_threshold: Optional[float] = None,
    ) -> None:
        settings = get_settings()
        self.vector_store = vector_store or LocalJsonVectorStore()
        self.embedding_provider = embedding_provider or MockEmbeddingProvider()
        self.chunker = chunker or HierarchicalChunker()
        self.default_top_k = default_top_k or settings.rag_top_k
        self.default_threshold = default_threshold or settings.rag_similarity_threshold

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        """
        Execute semantic retrieval for a query string.
        Returns candidates scoring >= threshold, capped at top_k.
        If no candidates meet threshold, returns empty list.
        """
        if not query or not query.strip():
            raise EmptyQueryError("Retrieval query cannot be empty or whitespace-only.")

        k = top_k if top_k is not None else self.default_top_k
        min_thresh = threshold if threshold is not None else self.default_threshold

        query_vec = await self.embedding_provider.embed_text(query.strip())
        results = await self.vector_store.search(
            query_embedding=query_vec,
            top_k=k,
            threshold=min_thresh,
        )

        logger.info(
            "Retriever query '%s': found %d chunks (top_k=%d, threshold=%.2f)",
            query[:60],
            len(results),
            k,
            min_thresh,
        )
        return results

    async def retrieve_with_citations(
        self,
        query: str,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> Tuple[List[RetrievedChunk], List[CitationSource]]:
        """
        Retrieve chunks and return alongside structured citation anchors.
        """
        chunks = await self.retrieve(query=query, top_k=top_k, threshold=threshold)
        citations = [chunk.to_citation() for chunk in chunks]
        return chunks, citations

    async def index_document(
        self,
        doc: NormalizedDocument,
    ) -> List[DocumentChunk]:
        """
        Ingest a NormalizedDocument into the vector store:
        1. Hierarchical chunking
        2. Batch dense embedding
        3. Vector store insertion & persistence
        """
        chunks = self.chunker.chunk_document(doc)
        if not chunks:
            logger.warning("Document '%s' produced zero chunks", doc.original_filename)
            return []

        texts = [c.text for c in chunks]
        embeddings = await self.embedding_provider.embed_texts(texts)

        await self.vector_store.add_chunks(chunks=chunks, embeddings=embeddings)
        logger.info(
            "Successfully indexed document '%s' (SHA: %s) -> %d chunks",
            doc.original_filename,
            doc.sha256[:12],
            len(chunks),
        )
        return chunks
