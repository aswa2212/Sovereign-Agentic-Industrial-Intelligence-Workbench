# Phase 4 — Multimodal Document Ingestion Pipeline Architecture

> **Component:** Document Ingestion & Provenance Engine  
> **Subsystem Location:** `backend/app/services/ingestion/`  
> **API Mount:** `/api/v1/files/`  
> **Authoritative Specification:** `docs/implementation_plan.md`  
> **Compliance:** Air-Gapped, Local-Only, OS-Portable (pathlib)  

---

## 1. Architectural Overview

The Phase 4 Multimodal Document Ingestion Pipeline provides a secure, deterministic intake subsystem for industrial engineering documents within the sovereign MRPL AI Workbench. It ingests raw source files, anchors them cryptographically using SHA-256, isolates raw files from processed data, sanitizes filenames against path traversal attacks, and extracts structured text, tables, and metadata into a strongly typed `NormalizedDocument` contract.

```
Incoming Upload (Multipart Form)
           │
           ▼
[ Size & Path Traversal Validator ]
           │
           ▼
[ Streaming SHA-256 Hasher ] ──► (Generates Cryptographic Identity)
           │
           ▼
[ Content-Aware File Detector ] (Magic Byte Signature Verification)
           │
           ▼
[ Immutable Raw Storage ] ──► (Saved to data/raw/{sha256}_{filename})
           │
    ┌──────┴────────────────────────────────────────────────┐
    ▼                          ▼                            ▼
[ PDF Parser ]           [ DOCX Parser ]           [ XLSX/CSV Parser ]
(pypdf + pdfplumber)      (python-docx)             (openpyxl / sniffer)
    │                          │                            │
    └──────────────────────────┼────────────────────────────┘
                               │
                               ▼
                 [ NormalizedDocument Contract ]
               (Pages, Sections, Sheets, Tables,
               Provenance Links, OCR Handoff Flags)
                               │
                               ▼
                 [ Processed Artifact Storage ]
                  (data/processed/{sha256}.json)
                               │
                               ▼
                 [ DocumentIngestionResult ]
                   (Returned to API Client)
```

---

## 2. Supported Formats & Extraction Methods

| Format | MIME Type | Parser Engine | Extracted Structures | Provenance Granularity |
|---|---|---|---|---|
| **PDF** | `application/pdf` | `pypdf` + `pdfplumber` | Metadata, per-page text, digital tables, vector heuristics | `page_number`, `source_sha256` |
| **DOCX** | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | `python-docx` | Core properties, headings, paragraphs, structured tables | `section_index`, `table_id` |
| **XLSX** | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | `openpyxl` (read-only, data-only) | Sheet names, dimensions, cell values, structured tables | `sheet_name`, `row_index`, `col_index` |
| **CSV** | `text/csv` | `csv` + dialect sniffer | Delimiter, encoding, sanitized rows, column headers | `sheet_name`, row index |
| **PNG** | `image/png` | `Pillow` (PIL) | Width, height, color mode, alpha channel, channels | `source_sha256`, dimensions |
| **JPEG** | `image/jpeg` | `Pillow` (PIL) | Width, height, color mode, channels | `source_sha256`, dimensions |

---

## 3. Cryptographic SHA-256 Identity & Duplicate Handling

1. **Deterministic Hashing:** SHA-256 is computed over the **exact original raw file bytes**, never over extracted text or post-processed strings.
2. **Chunked Streaming:** Large files are read in 64 KB chunks (`compute_sha256_stream`), guaranteeing that memory consumption remains constant regardless of file size.
3. **Collision-Safe Storage:** Raw files are saved as `data/raw/{sha256}_{sanitized_filename}`.
4. **Duplicate Detection:** If an upload matches an existing SHA-256 digest and file size, the existing raw file is reused without mutation, and the response sets `is_duplicate: true`.

---

## 4. Provenance & Normalized Document Contract

The system establishes an explicit `DocumentProvenance` link on every extracted component (page, section, table, cell). Future subsystems (Phase 5 Vision, Phase 6 RAG, Phase 7 Agent) can deterministically trace any fact or reading back to:
- Source file name
- Source SHA-256 hash
- Page number (1-based)
- Paragraph / section index
- Spreadsheet name and row/column index

### NormalizedDocument Hierarchy
```
NormalizedDocument
├── document_id (UUID4)
├── sha256 (64-char hex digest)
├── original_filename & sanitized_filename
├── file_extension & media_type
├── size_bytes
├── raw_path & processed_path
├── status (SUCCESS | NEEDS_OCR | PARTIAL | FAILED)
├── extraction_method
├── metadata (author, created, title, page_count, etc.)
├── pages: List[DocumentPage]
│   └── tables: List[ParsedTable]
├── sections: List[DocumentSection]
├── sheets: List[SheetData]
├── tables: List[ParsedTable]
├── image_info: Optional[ImageInfo]
├── is_scanned: bool
├── needs_ocr: bool
└── is_drawing: bool
```

---

## 5. Scanned PDF Detection & Phase 5 Handoff

Refineries possess historical scanned inspection records that lack native digital text.
- **Scanned Detection Logic:** When a PDF page contains zero digital characters or has fewer than 40 characters while containing image/graphics objects, the pipeline marks:
  - `page.is_scanned = True`
  - `page.status = ExtractionStatus.NEEDS_OCR`
  - `document.is_scanned = True`
  - `document.needs_ocr = True`
- **Strict Boundary:** Detection $\neq$ OCR. **No OCR or VLM inference is run in Phase 4.** The pipeline sets `needs_ocr: true` as the explicit contract handoff to Phase 5.

---

## 6. Engineering Schematic / P&ID Heuristic

For technical schematics, a non-semantic geometry heuristic detects wide landscape sheets (`width > 800` or `aspect_ratio > 1.35`) with low text density (`char_count < 250`) and dense vector lines/curves (`curve_count > 30`).
- Flags `is_drawing: true`.
- Does NOT attempt to recognize P&ID symbols, valves, or instruments (deferred to Phase 5).

---

## 7. Security & Path Sanitization

1. **Path Traversal Defenses:** `sanitize_filename()` strips all path traversal tokens (`../`, `..\`, `/`, `\`), null bytes (`\x00`), and Windows drive prefixes (`C:`).
2. **Directory Isolation:** Files are written strictly under `data/raw/` and `data/processed/`. Any path resolution escaping these directories triggers `SecurityViolationError`.
3. **Executable Rejection:** Executable extensions (`.exe`, `.dll`, `.bat`, `.cmd`, `.sh`, `.ps1`) are rejected outright regardless of magic bytes.
4. **MIME/Extension Mismatch:** Magic byte validation checks headers (`%PDF-`, `\x89PNG`, `\xff\xd8\xff`, `PK\x03\x04`). Contradictory extensions raise `InvalidDocumentError`.
5. **CSV Formula Injection:** Cells starting with `=`, `+`, `-`, or `@` are sanitized with a leading quote to neutralize dynamic spreadsheet execution.
6. **Configurable Size Limits:** File size is validated against `settings.max_upload_size_bytes` (default 50 MB) before parsing.

---

## 8. Explicit Boundary Declarations

- **OCR is NOT implemented in Phase 4.** (Deferred to Phase 5)
- **Vision / VLM inference is NOT implemented in Phase 4.** (Deferred to Phase 5)
- **Vector embedding and semantic chunking are NOT implemented in Phase 4.** (Deferred to Phase 6)
- **Agent planning and tool execution are NOT implemented in Phase 4.** (Deferred to Phase 7)
