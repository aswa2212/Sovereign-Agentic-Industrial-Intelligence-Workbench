"""
SIH26117 — Local Persistent Vector Store
Provides high-performance, offline, local vector storage using NumPy for dot-product
cosine similarity, persisting normalized dense embeddings (index.npy) and structured
chunk metadata (metadata.json) under data/knowledge/{index_id}/.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

try:
    from app.core.config import get_settings
    from app.services.rag.base import (
        BaseVectorStore,
        DocumentChunk,
        RetrievedChunk,
        VectorStoreError,
    )
except ImportError:
    from backend.app.core.config import get_settings
    from backend.app.services.rag.base import (
        BaseVectorStore,
        DocumentChunk,
        RetrievedChunk,
        VectorStoreError,
    )

logger = logging.getLogger(__name__)


class LocalJsonVectorStore(BaseVectorStore):
    """
    Persistent local vector store backed by NumPy and JSON.
    Guarantees portable air-gap execution on Windows/Linux without C++ library compilation issues.
    """

    def __init__(
        self,
        index_id: str = "default",
        storage_dir: Optional[Path] = None,
        auto_load: bool = True,
    ) -> None:
        settings = get_settings()
        base_dir = storage_dir or settings.knowledge_dir
        self.index_id = index_id
        self.storage_dir = Path(base_dir) / index_id
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.index_path = self.storage_dir / "index.npy"
        self.metadata_path = self.storage_dir / "metadata.json"

        self._matrix: Optional[np.ndarray] = None
        self._chunks: List[DocumentChunk] = []

        if auto_load and self.index_path.exists() and self.metadata_path.exists():
            self.load()

    def count(self) -> int:
        """Return total number of active indexed chunks."""
        return len(self._chunks)

    def is_empty(self) -> bool:
        """Check if vector store contains zero vectors."""
        return len(self._chunks) == 0

    async def add_chunks(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
    ) -> None:
        """
        Insert chunks with corresponding normalized embedding vectors.
        Persists automatically to disk upon addition.
        """
        if len(chunks) != len(embeddings):
            raise VectorStoreError(
                f"Chunks count ({len(chunks)}) does not match embeddings count ({len(embeddings)})"
            )

        if not chunks:
            return

        new_matrix = np.array(embeddings, dtype=np.float32)

        # Enforce unit L2 normalization
        norms = np.linalg.norm(new_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        new_matrix = new_matrix / norms

        if self._matrix is None or len(self._chunks) == 0:
            self._matrix = new_matrix
            self._chunks = list(chunks)
        else:
            if new_matrix.shape[1] != self._matrix.shape[1]:
                raise VectorStoreError(
                    f"Dimension mismatch: Existing index has {self._matrix.shape[1]} dims, "
                    f"new embeddings have {new_matrix.shape[1]} dims."
                )
            self._matrix = np.vstack([self._matrix, new_matrix])
            self._chunks.extend(chunks)

        self.persist()
        logger.info(
            "Added %d chunks to vector index '%s'. Total: %d",
            len(chunks),
            self.index_id,
            len(self._chunks),
        )

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 3,
        threshold: float = 0.65,
    ) -> List[RetrievedChunk]:
        """
        Execute cosine similarity search over stored vectors.
        Filters out any candidate with similarity < threshold.
        """
        if self._matrix is None or len(self._chunks) == 0:
            return []

        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm

        # Matrix dot product computes cosine similarities since both matrix and q_vec are unit-normalized
        scores = np.dot(self._matrix, q_vec)

        # Get indices sorted by score descending
        sorted_indices = np.argsort(scores)[::-1]

        results: List[RetrievedChunk] = []
        for idx in sorted_indices:
            score = float(scores[idx])
            if score < threshold:
                break  # Since sorted descending, subsequent items will also be below threshold

            chunk = self._chunks[idx]
            retrieved = RetrievedChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                source_sha256=chunk.source_sha256,
                source_document=chunk.source_document,
                page_number=chunk.page_number,
                section_index=chunk.section_index,
                section_header=chunk.section_header,
                text=chunk.text,
                similarity_score=round(score, 4),
                content_sha256=chunk.content_sha256,
                token_count=chunk.token_count,
                metadata=chunk.metadata,
            )
            results.append(retrieved)
            if len(results) >= top_k:
                break

        return results

    def persist(self) -> Path:
        """Write index matrix to .npy and chunk metadata to .json."""
        if self._matrix is None or not self._chunks:
            return self.storage_dir

        try:
            # 1. Write numpy float32 matrix
            np.save(self.index_path, self._matrix)

            # 2. Write metadata JSON
            metadata_payload = [c.model_dump() for c in self._chunks]
            with open(self.metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata_payload, f, indent=2, ensure_ascii=False)

            return self.storage_dir
        except Exception as e:
            logger.error("Failed to persist vector store index '%s': %s", self.index_id, str(e))
            raise VectorStoreError(f"Vector store persistence failed: {str(e)}") from e

    def load(self) -> bool:
        """Load index matrix and chunk metadata from disk."""
        if not self.index_path.is_file() or not self.metadata_path.is_file():
            return False

        try:
            # 1. Load numpy matrix
            self._matrix = np.load(self.index_path)

            # 2. Load metadata JSON
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._chunks = [DocumentChunk.model_validate(item) for item in data]

            logger.info(
                "Loaded vector store '%s' from disk: %d chunks, %d dimensions",
                self.index_id,
                len(self._chunks),
                self._matrix.shape[1] if self._matrix is not None else 0,
            )
            return True
        except Exception as e:
            logger.error("Failed to load vector store '%s': %s", self.index_id, str(e))
            raise VectorStoreError(f"Vector store load failed: {str(e)}") from e

    def clear(self) -> None:
        """Clear in-memory and on-disk index."""
        self._matrix = None
        self._chunks = []
        if self.index_path.exists():
            self.index_path.unlink()
        if self.metadata_path.exists():
            self.metadata_path.unlink()

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic metrics for this vector store."""
        unique_docs = len({c.source_sha256 for c in self._chunks})
        dim = int(self._matrix.shape[1]) if self._matrix is not None else 0
        return {
            "index_id": self.index_id,
            "backend": "local_numpy_json",
            "storage_path": str(self.storage_dir),
            "total_chunks": len(self._chunks),
            "indexed_documents_count": unique_docs,
            "dimension": dim,
            "persisted_on_disk": self.index_path.exists() and self.metadata_path.exists(),
        }
