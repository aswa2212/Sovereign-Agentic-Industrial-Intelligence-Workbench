# Phase 6 — Sovereign Knowledge & RAG Layer: Master Plan Traceability

> **Document Type:** Traceability Matrix & Architectural Audit  
> **Target Phase:** Phase 6 — Sovereign Knowledge & RAG Layer  
> **Authoritative Baseline:** `docs/implementation_plan.md` (Sections 14, 18, 19, 20, 21, 33)  
> **Status:** VERIFIED & COMPLETE  

---

## 1. Master Plan Requirement Mapping

| Master Plan Requirement | Architectural Intent | Implementation Module / File | Function / Class | Test Name(s) in `tests/test_rag.py` | Compliance Status |
|---|---|---|---|---|---|
| **Hierarchical Structure Chunking** | Preserves headings, sections, page bounds, and narrative paragraphs | `app/services/rag/chunker.py` | `HierarchicalChunker._chunk_text_block`, `chunk_document` | `test_chunk_document_hierarchy_and_provenance`, `test_chunk_document_target_clause_presence` | **IMPLEMENTED** (PASS) |
| **Token Budget & Overlap** | Target ~500 tokens with ~50-token overlap using portable token estimator | `app/services/rag/chunker.py` | `estimate_token_count`, `HierarchicalChunker` | `test_token_estimator`, `test_chunk_document_hierarchy_and_provenance` | **IMPLEMENTED** (PASS) |
| **Table Boundary Preservation** | Converts tables to Markdown; keeps rows as atomic units without row splitting | `app/services/rag/chunker.py` | `format_table_as_markdown`, `HierarchicalChunker._chunk_table` | `test_table_markdown_formatter`, `test_chunk_document_table_preservation` | **IMPLEMENTED** (PASS) |
| **Deterministic Chunk IDs & Hashes** | Computes deterministic chunk IDs and content SHA-256 for audit tracking | `app/services/rag/chunker.py` | `HierarchicalChunker._create_chunk` | `test_chunk_document_hierarchy_and_provenance` | **IMPLEMENTED** (PASS) |
| **Local Dense Embedding Abstraction** | Decoupled provider interface supporting local model swapping | `app/services/rag/base.py` | `EmbeddingProvider` (abstract base) | `test_mock_embedding_deterministic_and_normalized`, `test_unavailable_provider_raises_error_without_download` | **IMPLEMENTED** (PASS) |
| **Deterministic Mock Embedding Engine** | Air-gapped pseudo-semantic embedding with term clustering (dim=384) | `app/services/rag/embeddings.py` | `MockEmbeddingProvider` | `test_mock_embedding_deterministic_and_normalized`, `test_mock_embedding_semantic_clustering` | **IMPLEMENTED** (PASS) |
| **Safe Unavailable Provider Handling** | Explicit error handling on missing local weights without internet calls | `app/services/rag/embeddings.py` | `LocalSentenceTransformerEmbeddingProvider` | `test_unavailable_provider_raises_error_without_download` | **IMPLEMENTED** (PASS) |
| **Model Manager Integration** | Pluggable bridge to Phase 2 ModelManager role `embedding` | `app/services/rag/embeddings.py` | `ModelManagerEmbeddingProvider` | Covered via interface contract | **IMPLEMENTED** (PASS) |
| **Persistent Local Vector Store** | Portable NumPy float32 matrix (`index.npy`) and JSON metadata under `data/knowledge/` | `app/services/rag/vector_store.py` | `LocalJsonVectorStore` | `test_vector_store_crud_and_persistence` | **IMPLEMENTED** (PASS) |
| **Vector Store Disk Reload** | Hot-reload vector store from disk and retain vector/metadata parity | `app/services/rag/vector_store.py` | `LocalJsonVectorStore.load` | `test_vector_store_crud_and_persistence` | **IMPLEMENTED** (PASS) |
| **Cosine Similarity Search** | Fast dot-product cosine similarity over normalized unit vectors | `app/services/rag/vector_store.py` | `LocalJsonVectorStore.search` | `test_vector_store_crud_and_persistence` | **IMPLEMENTED** (PASS) |
| **Minimum Similarity Threshold** | Discards irrelevant results falling below threshold (default 0.65) | `app/services/rag/vector_store.py`, `app/services/rag/retriever.py` | `LocalJsonVectorStore.search`, `SovereignRetriever.retrieve` | `test_vector_store_threshold_filtering`, `test_retriever_irrelevant_query_yields_empty_results` | **IMPLEMENTED** (PASS) |
| **Synthetic MRPL SOP Corpus** | Synthetic piping inspection SOP fixture with Class 150 3.2mm clause | `data/samples/sop_mrpl_piping_inspection.json` | Synthetic `NormalizedDocument` | `test_retriever_sop_target_clause_retrieval`, `test_api_rag_query_success` | **IMPLEMENTED** (PASS) |
| **Target Clause Semantic Retrieval** | Query for *"minimum wall thickness for class 150 carbon steel"* returns target clause | `app/services/rag/retriever.py` | `SovereignRetriever.retrieve` | `test_retriever_sop_target_clause_retrieval`, `test_api_rag_query_success` | **IMPLEMENTED** (PASS) |
| **Irrelevant Query Rejection** | Returns empty candidates / `insufficient_knowledge` rather than hallucinating | `app/services/rag/retriever.py`, `app/api/v1/endpoints/rag.py` | `SovereignRetriever.retrieve`, `query_knowledge_base` | `test_retriever_irrelevant_query_yields_empty_results`, `test_api_rag_query_insufficient_knowledge` | **IMPLEMENTED** (PASS) |
| **Traceable Citation Provenance** | Returns `CitationSource` with `source_document`, `page_number`, `chunk_id`, `content_sha256` | `app/services/rag/base.py`, `app/services/rag/retriever.py` | `RetrievedChunk.to_citation`, `SovereignRetriever.retrieve_with_citations` | `test_retriever_sop_target_clause_retrieval`, `test_api_rag_query_success` | **IMPLEMENTED** (PASS) |
| **RAG Indexing REST API** | `POST /api/v1/rag/index` consumes Phase 4 document by SHA-256 | `app/api/v1/endpoints/rag.py` | `index_document` | `test_api_rag_index_success`, `test_api_rag_index_not_found_returns_404` | **IMPLEMENTED** (PASS) |
| **RAG Query REST API** | `POST /api/v1/rag/query` executes retrieval and returns results + citations | `app/api/v1/endpoints/rag.py` | `query_knowledge_base` | `test_api_rag_query_success`, `test_api_rag_query_insufficient_knowledge`, `test_api_rag_query_empty_returns_400` | **IMPLEMENTED** (PASS) |
| **RAG Status REST API** | `GET /api/v1/rag/status` returns operational telemetry and index counts | `app/api/v1/endpoints/rag.py` | `get_rag_status` | `test_api_rag_status_initial` | **IMPLEMENTED** (PASS) |
| **Air-Gap Network Interception** | Confirms zero outbound socket or internet calls during RAG pipeline execution | Complete `app/services/rag/` subsystem | Pipeline execution | `test_air_gap_no_outbound_network_calls` | **IMPLEMENTED** (PASS) |

---

## 2. Intentional Phase Boundaries & Deferred Capabilities

To maintain strict architectural cleanliness and avoid premature scope contamination:

1. **Agent State Machine & Planning (Plan $\rightarrow$ Act $\rightarrow$ Observe):** **DEFERRED — PHASE 7**  
   - Phase 6 provides atomic semantic retrieval and citation provenance. The multi-step agent orchestrator in Phase 7 invokes `POST /api/v1/rag/query` or `SovereignRetriever` as a tool.
2. **Computational Sandbox Execution:** **DEFERRED — PHASE 8**  
   - Numerical calculations (e.g. remaining life derivations) derived from retrieved clauses are executed in the Phase 8 sandbox.
3. **Office Deliverable Generation (`.docx`, `.xlsx`, `.pptx`):** **DEFERRED — PHASE 9 & 10**  
   - Document templating and report formatting belong to Phases 9 and 10.
4. **Physical System-Wide Air-Gap Auditing:** **DEFERRED — PHASE 11**  
   - Phase 6 verifies zero socket connections during unit test execution path; system-wide hardware monitoring belongs to Phase 11.
