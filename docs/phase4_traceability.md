# Phase 4 — Multimodal Document Ingestion Pipeline: Master Plan Traceability

> **Document Type:** Traceability Matrix & Architectural Audit  
> **Target Phase:** Phase 4 — Multimodal Document Ingestion Pipeline  
> **Authoritative Baseline:** `docs/implementation_plan.md` (Sections 15, 18, 19, 20, 33)  
> **Status:** VERIFIED & COMPLETE  

---

## 1. Master Plan Requirement Mapping

| Master Plan Requirement | Architectural Intent | Implementation Module / File | Function / Class | Test Name(s) in `tests/test_ingestion.py` | Compliance Status |
|---|---|---|---|---|---|
| **SHA-256 Original Artifact** | Deterministic cryptographic identity over original uploaded raw bytes | `app/services/ingestion/hasher.py` | `compute_sha256_bytes`, `compute_sha256_stream`, `compute_sha256_file` | `test_sha256_correctness`, `test_sha256_stream_chunking`, `test_sha256_file` | **IMPLEMENTED** (PASS) |
| **Path Traversal Sanitization** | Reject directory traversal (`../`, `..\`, absolute paths, null bytes) | `app/services/ingestion/storage.py` | `sanitize_filename` | `test_path_traversal_relative`, `test_path_traversal_absolute_unix`, `test_path_traversal_absolute_windows`, `test_null_byte_rejection` | **IMPLEMENTED** (PASS) |
| **Raw File Persistence** | Immutable storage of original artifacts under `data/raw/{sha256}_{filename}` | `app/services/ingestion/storage.py` | `StorageManager.store_raw_file` | `test_raw_persistence_and_duplicate`, `test_ingest_digital_pdf` | **IMPLEMENTED** (PASS) |
| **Duplicate Detection** | Detect identical uploads by SHA-256 without corrupting or overwriting | `app/services/ingestion/storage.py` | `StorageManager.store_raw_file` | `test_raw_persistence_and_duplicate`, `test_api_upload_duplicate` | **IMPLEMENTED** (PASS) |
| **Processed Storage** | Normalized JSON representation stored under `data/processed/{sha256}.json` | `app/services/ingestion/storage.py` | `StorageManager.store_processed_document` | `test_api_get_document_status`, `test_ingest_digital_pdf` | **IMPLEMENTED** (PASS) |
| **Magic Byte Signature Detection** | Detect MIME type from headers (%PDF, PNG, JPEG, PK zip) without OS registry | `app/services/ingestion/file_detector.py` | `detect_file_type` | `test_detect_valid_pdf`, `test_detect_png`, `test_detect_jpeg`, `test_detect_dangerous_executable` | **IMPLEMENTED** (PASS) |
| **Digital PDF Text Extraction** | Page count, metadata, per-page text, character and word density metrics | `app/services/ingestion/pdf_parser.py` | `PDFParser.parse` | `test_ingest_digital_pdf`, `test_api_upload_pdf_success` | **IMPLEMENTED** (PASS) |
| **Structured Table Extraction** | Extract tables with headers, rows, dimensions, and page provenance | `app/services/ingestion/table_extractor.py` | `extract_tables_from_pdf_page` | `test_ingest_pdf_with_table`, `test_synthetic_industrial_ndt_sample` | **IMPLEMENTED** (PASS) |
| **Scanned PDF Detection** | Detect lack of native text layer; emit `NEEDS_OCR` without calling OCR | `app/services/ingestion/pdf_parser.py` | `PDFParser.parse` (scanned heuristic) | `test_ingest_scanned_pdf_needs_ocr` | **IMPLEMENTED** (PASS) |
| **Drawing / P&ID Heuristic** | Non-semantic geometry heuristic for wide aspect ratio / dense vectors | `app/services/ingestion/pdf_parser.py` | `evaluate_drawing_heuristic` | `test_ingest_drawing_heuristic` | **IMPLEMENTED** (PASS) |
| **DOCX Document Parsing** | Heading levels, paragraphs, tables, and section provenance | `app/services/ingestion/docx_parser.py` | `DOCXParser.parse` | `test_ingest_docx`, `test_api_upload_docx_success` | **IMPLEMENTED** (PASS) |
| **XLSX Spreadsheet Parsing** | Read-only sheets, tabular cells, coordinate provenance; formula safe | `app/services/ingestion/xlsx_parser.py` | `XLSXParser.parse` | `test_ingest_xlsx`, `test_api_upload_xlsx_success` | **IMPLEMENTED** (PASS) |
| **CSV Tabular Ingestion** | Sniff delimiters, detect encoding, sanitize formula injection | `app/services/ingestion/csv_parser.py` | `CSVParser.parse`, `sanitize_csv_cell` | `test_ingest_csv`, `test_csv_formula_injection_sanitization` | **IMPLEMENTED** (PASS) |
| **Image Ingestion (PNG/JPEG)** | Extract width, height, mode, channels; flag `needs_ocr=True` (no OCR call) | `app/services/ingestion/image_parser.py` | `ImageParser.parse` | `test_ingest_image_png`, `test_api_upload_image_jpg_success` | **IMPLEMENTED** (PASS) |
| **Normalized Document Contract** | Strongly typed Pydantic models anchoring provenance and structure | `app/services/ingestion/models.py` | `NormalizedDocument`, `DocumentIngestionResult` | `test_ingest_digital_pdf`, `test_synthetic_industrial_ndt_sample` | **IMPLEMENTED** (PASS) |
| **Structured Error Envelopes** | Standardized `INVALID_DOCUMENT`, `FILE_TOO_LARGE`, `UNSUPPORTED_FILE_TYPE` | `app/services/ingestion/exceptions.py`, `endpoints/files.py` | `IngestionError` hierarchy | `test_api_upload_unsupported_extension`, `test_api_upload_corrupted_pdf`, `test_api_upload_oversized_file` | **IMPLEMENTED** (PASS) |
| **Upload API Endpoint** | `POST /api/v1/files/upload` accepting multipart file form data | `app/api/v1/endpoints/files.py` | `upload_document` | `test_api_upload_pdf_success`, `test_api_upload_duplicate` | **IMPLEMENTED** (PASS) |
| **Status API Endpoint** | `GET /api/v1/files/{sha256}/status` returning normalized representation | `app/api/v1/endpoints/files.py` | `get_document_status` | `test_api_get_document_status`, `test_api_get_document_status_not_found` | **IMPLEMENTED** (PASS) |
| **Synthetic Industrial NDT Sample** | Synthetic C-101 inspection PDF: nominal 12mm, UTG readings, 4 table rows | `data/samples/corrosion_inspection_c101.pdf` | N/A (sample artifact) | `test_synthetic_industrial_ndt_sample` | **IMPLEMENTED** (PASS) |
| **Air-Gap Network Sovereignty** | Zero outbound socket connections during ingestion pipeline execution | `app/services/ingestion/service.py` | Complete pipeline | `test_air_gap_no_outbound_network_calls` | **IMPLEMENTED** (PASS) |

---

## 2. Intentional Phase Boundaries & Deferred Capabilities

To maintain strict architectural cleanliness and avoid scope contamination:

1. **OCR / Tesseract Execution:** **DEFERRED — PHASE 5**  
   - Scanned PDFs and images are flagged with `needs_ocr: true` and `status: "needs_ocr"`. No OCR binary is executed in Phase 4.
2. **Visual Question Answering / VLM (Qwen2.5-VL):** **DEFERRED — PHASE 5**  
   - Image geometry is validated; no VLM model inference is executed in Phase 4.
3. **P&ID Semantic Interpretation / Tag Detection:** **DEFERRED — PHASE 5**  
   - The drawing heuristic only checks spatial dimensions and vector curve density. It does not parse valves or instruments.
4. **Text Chunking for Vector Embeddings:** **DEFERRED — PHASE 6**  
   - Document pages and paragraphs preserve original structure. Chunking and overlapping belong to the Sovereign RAG layer.
5. **Vector Store Indexing (FAISS/Chroma):** **DEFERRED — PHASE 6**  
   - Storage in Phase 4 is flat JSON artifacts under `data/processed/` keyed by SHA-256.
