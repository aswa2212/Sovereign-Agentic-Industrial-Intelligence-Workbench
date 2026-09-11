# Phase 10 — Deterministic Office Deliverables Architecture Specification

**Document Version:** 1.0.0  
**Phase:** 10 — Deterministic Office Deliverables Factory  
**Problem Statement:** SIH26117 — Sovereign On-Premise Agentic AI Workbench for MRPL  
**Target Hardware:** Linux On-Premise Workstation (24–48 GB VRAM) / Windows 11 Edge Dev  
**Execution Mode:** 100% Air-Gapped, Zero External Transmission  

---

## 1. Executive Summary & Core Architectural Invariants

In high-consequence refining operations at Mangalore Refinery and Petrochemicals Limited (MRPL), engineering documents—such as corrosion inspection memoranda, calculation sheets, and turnaround executive briefings—govern critical maintenance, isolation tagging, and asset retirement decisions.

### Strict Architectural Invariants:
1. **"LLMs do not directly generate Office files."**
   Under no circumstances is a foundation model permitted to emit raw binary streams, XML fragments, or uncontrolled markup intended for direct file serialization.
2. **"Only validated structured engineering results enter the document factory."**
   The deliverable generation subsystem consumes exclusively Pydantic models validated by Phase 9 (`CorrosionAuditResult` or `ValidationResult` with `valid == True`). Unvalidated, raw, or failing inputs are rejected immediately (fail-closed).
3. **Deterministic Construction:**
   Given the identical structured engineering input, document generation executes purely through deterministic Python component templates, yielding semantically and structurally identical artifacts without model variability.

---

## 2. Deliverables Subsystem Architecture

```
                                 [ Local Model / Phase 7 Agent ]
                                                │
                                                ▼
                                    [ Structured JSON Output ]
                                                │
                                                ▼
                                [ Phase 9 Pydantic & Math Validation ]
                                                │
                                                ▼
                                    [ CorrosionAuditResult ]
                                                │
                    ┌───────────────────────────┴───────────────────────────┐
                    │               DeliverablesFactory                     │
                    │               (Precondition Gate)                     │
                    └───────────────────────────┬───────────────────────────┘
                                                │
                    ┌───────────────────────────┼───────────────────────────┐
                    ▼                           ▼                           ▼
        [ DocxDeliverableBuilder ]   [ XlsxDeliverableBuilder ]   [ PptxDeliverableBuilder ]
        (python-docx)                (openpyxl)                  (OpenXML Presentation)
                    │                           │                           │
                    ▼                           ▼                           ▼
        Technical Memorandum         Calculation Workbook         Executive Briefing
        (outputs/docx/*.docx)        (outputs/xlsx/*.xlsx)        (outputs/pptx/*.pptx)
                    │                           │                           │
                    └───────────────────────────┬───────────────────────────┘
                                                │
                                                ▼
                                  [ Post-Generation Validator ]
                                  (Integrity & Structural Checks)
                                                │
                                                ▼
                                  [ Verified Office Deliverable ]
```

---

## 3. Input Contract & Precondition Validation

The deliverables subsystem receives domain data through strongly typed Pydantic models:

### Authoritative Contract: `CorrosionAuditResult`
- **Equipment Tag:** Mandatory non-empty string (`equipment_id`, e.g., `C-101`).
- **Inspection Subject:** Mandatory boundary description (`inspection_subject`).
- **Wall Thickness Gauging:** Baseline nominal thickness and current ultrasonic measurement points (`WallThicknessMeasurement`, values in mm > 0.0).
- **Calculations:** Independently recomputed corrosion rate (mm/yr) and remaining life (years) (`CorrosionCalculation`).
- **Inspection Findings:** Itemized observations with severity ratings (`InspectionFinding`).
- **Directives:** Standardized recommendation codes (`RecommendationCode`).
- **Citations & Provenance:** Unaltered source document references (`SourceCitation`).

### Fail-Closed Validation Gate (`validators.py`)
- If a `ValidationResult` is provided, `payload.valid` MUST be `True` and `payload.status` MUST be `"VALID"`.
- If an input payload lacks required equipment identification or contains unvalidated schema errors, an `UnvalidatedInputError` or `InvalidDeliverableInputError` is raised.
- No Office file is ever created for an invalid input.

---

## 4. Format Builders

### 4.1 DOCX Builder (`docx_builder.py`)
- **Technology:** `python-docx`
- **Output:** Publication-quality MRPL technical memorandum.
- **Key Sections:**
  1. Organizational Header Block (MRPL Asset Integrity Division).
  2. Document Metadata Box (Document code, equipment ID, inspection date, revision).
  3. Executive Summary & Action Directive (Alert callout block).
  4. Equipment Specification & Inspection Boundary.
  5. Ultrasonic Thickness Gauging (UTG) Data Table.
  6. Deterministic Corrosion Rate & Remaining Life Derivation (Equations and numbers).
  7. Observed Technical Findings & Defect Catalog.
  8. Technical Evidence & Provenance Grounding (Source document, page, chunk, SHA-256).
  9. Quality Assurance & Engineering Authorization (Sign-off signature blocks).

### 4.2 XLSX Builder (`xlsx_builder.py`)
- **Technology:** `openpyxl`
- **Output:** Multi-tabbed engineering calculation workbook.
- **Worksheet Layout:**
  - `Summary`: Executive overview, equipment metadata, recommendation directive.
  - `Measurements`: Baseline, current UTG, and retirement limit wall-thickness logs.
  - `Calculations`: Mathematical derivations with **controlled dynamic Excel formulas**:
    - Corrosion Rate: `=(C5-C6)/C7`
    - Remaining Life: `=(C6-C8)/C9`
    - *Anti-Injection Guard:* Formulas are strictly constructed from static templates using fixed cell coordinates; no arbitrary model-generated strings are parsed or evaluated as formulas.
  - `Evidence`: Provenance metadata, chunk references, and SHA-256 hashes.
  - `Validation`: Audit trail of Phase 9 validation checks.
- **Security:** Zero VBA macros, zero external links.

### 4.3 PPTX Builder (`pptx_builder.py`)
- **Technology:** Standards-compliant OpenXML Presentation Engine (with fallback wrapper for `python-pptx`).
- **Output:** 5-slide Executive Technical Briefing.
- **Slide Progression:**
  1. **Title Slide:** MRPL Asset Integrity Briefing, equipment tag, date, authority.
  2. **Inspection Overview & Scope:** System boundary, governing codes (ASME B31.3 / API 570).
  3. **Ultrasonic Thickness Gauging Data:** Baseline, current readings, observed thinning.
  4. **Engineering Calculations:** Recomputed corrosion rate and projected remaining useful life.
  5. **Action Directive & Provenance Evidence:** Action code, SOP citation, sovereign pedigree.
- **OpenXML Standards:** Generates valid OpenXML ZIP package (`[Content_Types].xml`, `_rels/.rels`, `ppt/presentation.xml`, `ppt/slides/slide*.xml`).

---

## 5. Provenance Grounding & Anti-Fabrication

All generated deliverables maintain traceable pedigree to the Phase 6 Sovereign Knowledge Base:
- Document citations (`source_document`, `page_number`, `chunk_id`, `content_sha256`) are propagated directly from Phase 9.
- No builder synthesizes, fabricates, or modifies citations.
- If citations are absent or empty, the deliverable explicitly indicates standard baseline parameters without fabricating references.

---

## 6. Determinism Strategy

Office binary files contain container timestamps that cause raw byte-level variances across runs. Determinism is defined and enforced as follows:
- **DOCX Determinism:** 100% semantic identity across all paragraph runs, formatting styles, table rows, cell values, and document structure.
- **XLSX Determinism:** 100% structural identity across all sheet names, cell coordinates, numeric values, formula definitions, and dimensions.
- **PPTX Determinism:** 100% XML structural identity across all slide definitions, text elements, and presentation metadata.
- **Naming Determinism:** Sanitized, collision-resistant filenames derived deterministically from equipment ID, task ID, and deliverable format.

---

## 7. Security Architecture

1. **No Code Execution Primitives:**
   Zero occurrences of `eval()`, `exec()`, `os.system()`, or `subprocess` across the entire deliverables package.
2. **Path Traversal Prevention:**
   All requested artifact filenames and paths are sanitized and verified via `resolve_and_verify_output_path()`. Attempts to use `..`, `/`, `\`, or null bytes are rejected with `PathTraversalSecurityError`.
3. **Formula Injection Defense:**
   Formulas in spreadsheets are exclusively generated from hardcoded mathematical templates referencing fixed cell coordinates.
4. **Air-Gap Sovereignty:**
   The entire generation pipeline executes offline with zero network socket operations or external API calls.

---

## 8. REST API Endpoints

### `POST /api/v1/deliverables/generate`
- Consumes a validated `CorrosionAuditResult` or raw validated dictionary.
- Supports format selection (`formats: ["docx", "xlsx", "pptx"]`).
- Returns `DeliverableGenerateResponse` with artifact IDs, filenames, SHA-256 digests, and file sizes.

### `GET /api/v1/deliverables/download/{fmt}/{filename}`
- Securely streams generated Office deliverables using `FileResponse`.
- Enforces strict path traversal bounds.

---

## 9. Boundary with Phase 11 (Audit & Sovereignty Monitor)

Phase 10 deliverables factory produces files in the local filesystem (`outputs/`). Phase 11 will consume these artifact generation events to record immutable tamper-evident cryptographic audit logs and provide host socket monitoring to continuously verify air-gap enforcement.
