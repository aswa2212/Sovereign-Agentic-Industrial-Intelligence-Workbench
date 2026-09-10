# SIH26117 — Sovereign On-Premise Agentic AI Workbench for MRPL
## Master Technical Implementation Plan & Architecture Specification (MVP)

> **Document Type:** Master Implementation Plan & Architectural Contract  
> **Problem Statement ID:** SIH26117  
> **Sponsoring Organization:** Mangalore Refinery and Petrochemicals Limited (MRPL)  
> **Target Audience:** Autonomous Coding Agents, Hackathon Evaluators, Development Team  
> **Baseline Development Hardware:** Windows 11, RTX 4060 Laptop GPU (8 GB VRAM), 16 GB Host RAM, Python 3.11, Node.js 22, Local Ollama  
> **Target Deployment Hardware:** Single On-Premise Linux Workstation / Edge Server (24 GB – 48 GB VRAM)  
> **Author:** Lead Software Architect & Technical Planning Agent  

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [MVP Scope](#2-mvp-scope)
3. [Non-Goals](#3-non-goals)
4. [System Architecture](#4-system-architecture)
5. [Module Responsibilities](#5-module-responsibilities)
6. [Architecture Boundaries](#6-architecture-boundaries)
7. [Data Flow](#7-data-flow)
8. [Primary Demo Workflow](#8-primary-demo-workflow)
9. [Secondary Demo Workflow](#9-secondary-demo-workflow)
10. [Model Strategy](#10-model-strategy)
11. [Model Manager Strategy](#11-model-manager-strategy)
12. [Router Strategy](#12-router-strategy)
13. [Agent Strategy](#13-agent-strategy)
14. [RAG Strategy](#14-rag-strategy)
15. [Multimodal & OCR Strategy](#15-multimodal--ocr-strategy)
16. [Sandbox Strategy](#16-sandbox-strategy)
17. [Deliverable Strategy](#17-deliverable-strategy)
18. [API Plan](#18-api-plan)
19. [Data Contracts](#19-data-contracts)
20. [Database & Storage Strategy](#20-database--storage-strategy)
21. [Configuration Strategy](#21-configuration-strategy)
22. [Security Strategy](#22-security-strategy)
23. [Sovereignty & Air-Gap Strategy](#23-sovereignty--air-gap-strategy)
24. [Observability Strategy](#24-observability-strategy)
25. [Frontend Strategy](#25-frontend-strategy)
26. [Testing Strategy](#26-testing-strategy)
27. [Evaluation Metrics](#27-evaluation-metrics)
28. [Model Evaluation Strategy](#28-model-evaluation-strategy)
29. [Router Training & Evaluation](#29-router-training--evaluation)
30. [Linux Portability Plan](#30-linux-portability-plan)
31. [Deployment Strategy](#31-deployment-strategy)
32. [Offline Installation Strategy](#32-offline-installation-strategy)
33. [Implementation Phases (Phase 0 to Phase 16)](#33-implementation-phases)
34. [Dependency Graph](#34-dependency-graph)
35. [MVP Acceptance Criteria](#35-mvp-acceptance-criteria)
36. [Demo Acceptance Criteria](#36-demo-acceptance-criteria)
37. [Risks](#37-risks)
38. [Mitigations](#38-mitigations)
39. [Future Scaling](#39-future-scaling)
40. [Post-MVP Roadmap](#40-post-mvp-roadmap)

---

## 1. Executive Summary

Hydrocarbon refining complexes such as Mangalore Refinery and Petrochemicals Limited (MRPL) operate under strict regulatory and national critical infrastructure protection mandates (NCIIPC, CERT-In, DPDPA, OISD). Proprietary technical intelligence—including Piping & Instrumentation Diagrams (P&IDs), crude assay valuations, turnaround critical path schedules, ultrasonic corrosion NDT logs, and vendor bidding evaluations—cannot be transmitted across public networks or processed via cloud-hosted foundation models (ChatGPT, Claude, Gemini, commercial APIs). 

The **SIH26117 Sovereign On-Premise Agentic AI Workbench** delivers an air-gapped, model-agnostic, self-hosted system running exclusively on local GPU infrastructure. It replaces shadow AI practices with a verified, deterministic, multi-model agentic workspace that ingests heterogeneous multimodal documents, routes queries dynamically, performs sandboxed mathematical calculations, and deterministically generates audit-ready Microsoft Office deliverables (`.docx`, `.xlsx`, `.pptx`).

---

## 2. MVP Scope

The Minimum Viable Product (MVP) focuses on proving the **5 Core Architectural Pillars** through a single, complete, end-to-end industrial workflow:
1. **Sovereignty & Air-Gap Operation:** Measurable, local-only execution with zero outbound HTTP/DNS sockets, backed by an active host socket audit monitor.
2. **Dynamic Multi-Model Routing:** Intent-based classification dispatching queries across specialized open-weight models (reasoning, coding, vision) without monolithic routing.
3. **Multi-Step Agentic Execution:** An explicit state machine (Plan $\rightarrow$ Act $\rightarrow$ Observe $\rightarrow$ Reflect $\rightarrow$ Validate) executing local tools with full intermediate UI visibility.
4. **Multimodal Industrial Ingestion:** Localized OCR, table extraction, and visual question answering over degraded industrial inspection reports and basic technical schematics.
5. **Deterministic Office Deliverables:** High-fidelity document generation (`.docx`, `.xlsx`, `.pptx`) via Python document engines consuming strictly validated Pydantic JSON schemas (never raw LLM text/byte generation).

---

## 3. Non-Goals

To guarantee delivery within hackathon timelines and hardware constraints, the following items are explicitly designated as **Non-Goals for the MVP**:
- Universal P&ID topological reconstruction or CAD-to-graph vectorization.
- Multi-node distributed GPU clustering or Kubernetes/vLLM enterprise orchestrations.
- Cloud-hosted external AI APIs (OpenAI, Anthropic, Google, Groq, Mistral Cloud).
- Complex enterprise user management, Active Directory/LDAP integration, or multi-tenant billing.
- Autonomous long-horizon web browsing or uncontrolled external scraping.
- LLM fine-tuning during application startup (training is restricted to offline experiments/Colab).

---

## 4. System Architecture

The workbench is architected as a **modular monolith** to eliminate unnecessary microservice networking overhead on single-machine deployments while enforcing strict interface boundaries:

```
                                 [ Operator Browser UI ]
                          (React 18 + TypeScript + Vite + Tailwind)
                                            │
                                            ▼  (Local HTTP REST / WebSocket)
                         ┌───────────────────────────────────────┐
                         │      FastAPI Gateway / Core Host      │
                         │   (Auth, Portability, Request IDs)    │
                         └──────────────────┬────────────────────┘
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     ▼                                             ▼
          [ Dynamic Task Router ]                        [ Audit & Sovereignty Engine ]
       (Semantic Intent Classifier)                      ├── Tamper-evident JSONL Log
                     │                                   └── Local Socket/Net Monitor
                     ▼
          [ Agent Orchestrator ] ◄───────────────────────┐
       (Explicit State-Machine Engine)                   │
                     │                                   │ Tool Feedback
       ┌─────────────┼─────────────┬─────────────┐       │
       ▼             ▼             ▼             ▼       │
   [ Local RAG   [ Multimodal   [ Sandboxed    [ Deliverables ─┘
   Knowledge ]   Ingestion &     Python ]        Factory ]
                 Vision Engine]               (.docx/.xlsx/.pptx)
                     │
                     ▼
        [ Local Model Manager ]
      (Unified ModelHandle Interface)
      (Serial Swapping / Colocation)
                     │
                     ▼
       [ Local Inference Engine (Ollama / llama.cpp) ]
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
  [Reasoning]     [Coding]      [Vision]
  DeepSeek-R1    Qwen2.5-Coder  Qwen2.5-VL
   Distill 7B         3B           3B
```

---

## 5. Module Responsibilities

| Subsystem | Directory | Single Responsibility |
| :--- | :--- | :--- |
| **API Gateway** | `backend/app/api/` | Exposes REST/WS routes, validates payloads, enforces request tracking, handles CORS. |
| **Core & Settings** | `backend/app/core/` | OS-agnostic path resolution, environment loading, centralized exception handling. |
| **Task Router** | `backend/app/services/router/` | Categorizes queries (Reasoning, Coding, Vision, RAG) and selects the appropriate model role. |
| **Agent Orchestrator**| `backend/app/services/agent/` | Drives the Plan $\rightarrow$ Act $\rightarrow$ Observe state-machine; coordinates tool dispatch. |
| **Model Manager** | `backend/app/services/model_manager/` | Provides unified `ModelHandle`, executes serial VRAM swapping (8 GB) or colocation (24 GB+). |
| **Knowledge / RAG** | `backend/app/services/rag/` | Sovereign vector indexing, dense chunk retrieval, and citation provenance over SOPs. |
| **Ingestion & OCR** | `backend/app/services/ingestion/` | Parses PDF, DOCX, XLSX, images; extracts tables; computes SHA-256 hashes. |
| **Vision Engine** | `backend/app/services/vision/` | Coordinates visual QA and coordinate extraction over technical diagrams with Qwen2.5-VL. |
| **Tool / Sandbox** | `backend/app/services/sandbox/` | Executes Python calculations and formula verifications within a constrained local process boundary. |
| **Deliverables** | `backend/app/services/deliverables/`| Deterministically renders styled Office files from Pydantic-validated JSON. |
| **Audit Logger** | `backend/app/services/audit/` | Writes immutable JSONL traces of every state change, model call, and tool execution. |
| **Network Monitor** | `backend/app/services/network/` | Scans host socket bindings to provide real-time proof of zero external egress. |

---

## 6. Architecture Boundaries

To ensure complete decoupling:
1. **Router vs. Agent:** The Router decides *what model/capability* is needed. It does not plan multi-step workflows. The Agent decides *what sequence of actions* to execute.
2. **Model Manager vs. Application Logic:** Business logic never calls Ollama or vLLM directly. It calls `ModelHandle.generate()` or `ModelHandle.generate_structured()`.
3. **Agent vs. Deliverable Generator:** The Agent never writes `.docx` or `.xlsx` files. The Agent outputs a structured JSON payload conformant to a Pydantic schema, which the Deliverables Factory compiles.
4. **Ingestion vs. In-Memory State:** Original uploaded files are permanently stored in `data/raw/` in an immutable state for auditing. Extracted text and crops reside in `data/processed/`.

---

## 7. Data Flow

```
[ Industrial PDF Upload ] ──► [ Ingestion Service ] ──► Compute SHA-256 & Store raw/
                                      │
                                      ▼
                        [ Text/Table Extraction + OCR ] ──► Store processed/
                                      │
                                      ▼
[ User Objective ] ──► [ Task Router ] ──► Decision: REASONING + VISION + RAG
                               │
                               ▼
                   [ Agent Orchestrator ]
                     ├── Step 1: Query RAG for Corrosion Standard (API 570 / MRPL SOP)
                     ├── Step 2: Extract minimum wall thickness from Inspection PDF
                     ├── Step 3: Dispatch Python calculation to Sandbox (Corrosion Rate & Remaining Life)
                     ├── Step 4: Validate calculation against engineering thresholds
                     └── Step 5: Emit structured JSON memo
                               │
                               ▼
                  [ Deliverables Factory ] ──► Compile official MRPL memo (.docx) + (.xlsx)
                               │
                               ▼
                   [ Audit & Egress Check ] ──► Log event ledger & verify 0 outbound sockets
```

---

## 8. Primary Demo Workflow: Refining Equipment Corrosion Audit

**Industrial Scenario:** An inspection engineer uploads a degraded 3-page ultrasonic Non-Destructive Testing (NDT) inspection sheet for Crude Distillation Column Overheads (Atmospheric Column C-101). The sheet contains handwritten equipment IDs, ultrasonic thickness readings, nominal design thickness, and operating temperatures.

**Execution Steps:**
1. **Ingestion:** Engineer uploads `ndt_inspection_c101.pdf`. The Ingestion engine computes SHA-256 hash `d41d8cd...`, parses text, and passes degraded tabular scans to OCR.
2. **Routing:** User submits prompt: *"Audit thickness readings against MRPL piping specification, calculate corrosion rate, and generate executive approval note."* The Router categorizes this as `[Multi-Step: Vision + RAG + Code Execution + Deliverable]`.
3. **Model Allocation:** Router requests `vision` role (Qwen2.5-VL-3B) for table extraction, followed by `reasoning` role (DeepSeek-R1-Distill-7B). Model Manager performs clean serial swapping.
4. **Agent Planning:** State machine enters `PLANNING` and defines 4 discrete steps:
   - *Action 1:* Parse inspection table readings.
   - *Action 2:* Retrieve minimum design thickness criteria from MRPL SOP knowledge base (`rag`).
   - *Action 3:* Run remaining life calculation formula ($t_{actual} - t_{required} / \text{corrosion rate}$) inside Python Sandbox.
   - *Action 4:* Compile administrative approval note and schedule next inspection.
5. **Tool Execution & Observation:** Agent executes Action 3 in Sandbox. Result: *Remaining Life = 1.8 years (Threshold: < 2.0 years requires immediate turnaround repair).*
6. **Validation:** Agent validates that all calculation derivations match API 570 rules.
7. **Deliverable Generation:** Agent emits structured JSON. Deliverables service generates a branded MRPL Executive Approval Note (`.docx`) and an Engineering Calc Sheet (`.xlsx`) with active Excel formulas.
8. **Proof of Sovereignty:** UI displays network monitor ledger proving 0 outbound external bytes throughout the 45-second execution.

---

## 9. Secondary Demo Workflow: P&ID Instrument Tag Identification

**Industrial Scenario:** Engineer uploads a high-resolution P&ID schematic slice for a hydrocracker relief valve manifold. Prompt: *"Identify pressure relief valves connected to line 10-HC-401 and list their safety interlocks."*

**Execution Steps:**
1. Ingestion crops image and generates normalized coordinate grid.
2. Vision model (Qwen2.5-VL) detects instrument bubbles (`PSV-104A`, `PSV-104B`, `PT-108`).
3. Agent cross-references tags against local maintenance SOP.
4. Deliverables factory outputs a tagged summary spreadsheet (`.xlsx`).

---

## 10. Model Strategy

The system enforces a **Model Portfolio Strategy** rather than single-model reliance:

| Model Role | Dev Tier (8 GB VRAM) | Target Tier (24–48 GB VRAM) | Primary Responsibility |
| :--- | :--- | :--- | :--- |
| **Router** | `qwen2.5:1.5b` (Q4_K_M) / Rule Classifier | `deepseek-r1-distill-llama:8b` (Q4_K_M) | Fast intent classification (<50ms). |
| **Reasoning** | `deepseek-r1:7b` (Q4_K_M, ~4.7 GB) | `deepseek-r1-distill-qwen:14b` / 32B | Step decomposition, math modeling, validation. |
| **Coding** | `qwen2.5-coder:3b` (Q4_K_M, ~2.2 GB) | `qwen2.5-coder:14b` (AWQ/FP8) | Script generation for sandboxed execution. |
| **Vision** | `qwen2.5-vl:3b` (Q4_K_M, ~3.1 GB) | `qwen2.5-vl:7b` (AWQ/FP8) | OCR verification, P&ID symbol parsing, visual QA. |
| **Embeddings** | `nomic-embed-text` (CPU, ~0.2 GB) | `bge-base-en-v1.5` (CUDA) | Dense semantic vector search for SOP retrieval. |

*Model Classification Rules:*
- **Models We Use:** Public open-weight weights distributed via GGUF/Ollama.
- **Models We Evaluate:** Benchmark comparisons between 3B vs 7B models on industrial prompts.
- **Models We May Fine-Tune:** Lightweight DeBERTa or 1.5B classification router in Google Colab (if rule baseline accuracy is $< 90\%$).

---

## 11. Model Manager Strategy

The Model Manager isolates application code from local model runtimes:

```
                  [ ModelManager ]
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
[ Dev Tier Swapper ]            [ Target Tier Colocator ]
(8 GB VRAM - Serial)             (24 GB+ VRAM - Co-resident)
- Active Model = 1               - Active Models = 2-3
- Calls unload on switch         - Hot in VRAM via PagedAttention
- keep_alive: "0m"               - keep_alive: "60m"
```

**Serial Model Swapping Protocol (Dev Tier):**
1. Request comes in for `vision`.
2. Model Manager checks current resident model. If `reasoning` is loaded:
   - Dispatches unload request (`POST /api/generate` with `keep_alive: 0`).
   - Polls VRAM until $\ge 5\text{ GB}$ is free.
3. Loads `qwen2.5-vl:3b`.
4. Executes vision inference.
5. Releases VRAM when subsequent step requires `reasoning`.

---

## 12. Router Strategy

Routing evolves across 3 defined operational levels:

- **Level 0 (Deterministic Rule Router — MVP Baseline):** Fast regex and metadata heuristics.
  - If prompt contains image attachments $\rightarrow$ `VISION`.
  - If prompt contains mathematical keywords or calculation request $\rightarrow$ `REASONING + SANDBOX`.
  - If prompt requests document generation $\rightarrow$ `REASONING + DELIVERABLE`.
- **Level 1 (Semantic Vector Router):** Embeds prompt and matches cosine similarity against anchor centroids representing MRPL operational domains (e.g., Corrosion Engineering, Electrical Instrumentation, Procurement).
- **Level 2 (Classifier Model — Colab Experimentation):** Small 1.5B or DeBERTa classification model trained on synthetic refinery prompts to output structured routing JSON.

*Fallback Strategy:* If confidence is $< 0.70$, route to `reasoning` model as the universal fallback.

---

## 13. Agent Strategy

The Agent Orchestrator is implemented as an **explicit deterministic state machine** without bloated third-party agent frameworks:

```
  [IDLE] ──► [RECEIVE] ──► [UNDERSTAND] ──► [PLAN]
                                              │
                ┌─────────────────────────────┴────────┐
                ▼                                      ▼
           [EXECUTE] (Tool Call)                 [VALIDATE]
                │                                      │
                ▼                                      ▼
           [OBSERVE] ──► [REFLECT] ──────────────► [FINALIZE]
                              │                        │
                              ▼                        ▼
                        [RETRY/ABORT]             [DELIVER]
```

**Safety Invariants:**
- Maximum execution steps: 8 steps per workflow.
- Step timeout: 45 seconds per step.
- Global timeout: 180 seconds per workflow.
- Maximum retry attempts on validation error: 2 retries before escalating to operator.
- Every state transition emits an `AgentStepEvent` broadcast to the UI and logged to Audit.

---

## 14. RAG Strategy

- **Document Preparation:** Ingests official MRPL SOPs, equipment specifications, and API standards (e.g., API 570 Piping Inspection Code).
- **Chunking:** Semantic hierarchy chunking (500 tokens with 50-token overlap, respecting table boundaries).
- **Vector Storage:** Local persistent FAISS or Chroma index stored portably in `data/knowledge/`.
- **Retrieval:** Top-$k$ dense retrieval ($k=3$) with minimum cosine similarity threshold of $0.65$.
- **Citation Provenance:** Every chunk returned includes `source_document`, `page_number`, `chunk_id`, and `content_sha256`. The LLM prompt forces verbatim bracketed citations `[Doc: SOP-MRPL-04, Page 12]`.

---

## 15. Multimodal & OCR Strategy

- **Native Text Extraction:** `pypdf` and `pdfplumber` extract embedded digital text and vector tables.
- **Degraded Scans & Handwritten Logs:** `pytesseract` or localized OCR extracts raw text with confidence scores.
- **Visual QA:** `qwen2.5-vl:3b` inspects cropped tables, schematics, and stamps to reconcile ambiguous OCR readings.
- **Provenance:** Raw images preserved under `data/raw/`, extracted crops under `data/processed/`.

---

## 16. Sandbox Strategy

- **Development Sandbox (Phase 8):** Constrained Python subprocess with:
  - Strict wall-clock execution timeout (15 seconds).
  - Restricted standard library whitelist (math, statistics, numpy, json).
  - Memory ceiling limit (512 MB).
  - Working directory restricted to an isolated scratch folder.
- **Target Tier Sandbox (On-Premise Linux):** Containerized rootless Docker or gVisor sandbox with disabled network namespace (`--network none`) and read-only root filesystem.

---

## 17. Deliverable Strategy

The system enforces strict decoupling between LLM reasoning and document byte construction:

```
[ LLM Generation ] ──► [ Structured JSON ] ──► [ Pydantic Schema Validation ]
                                                        │
                                                        ▼
                                          [ Python Deterministic Builder ]
                                          ├── python-docx (Formatted Word Memo)
                                          ├── openpyxl (Excel with Dynamic Formulas)
                                          └── python-pptx (Executive Presentation)
```

- **Word Deliverable:** Standardized MRPL memorandum format: header logo, metadata table, executive summary, findings, calculation derivation, approval signatures.
- **Excel Deliverable:** Data table with real cell calculations (e.g. `=B4-C4/D4`), conditional formatting highlighting out-of-spec readings in red.

---

## 18. API Plan

### Gateway & System
- `GET /api/v1/health` — Basic service health.
- `GET /api/v1/system/status` — Operational status & module initialization registry.
- `GET /api/v1/system/capabilities` — Planned architectural capabilities.

### Files & Ingestion
- `POST /api/v1/files/upload` — Upload raw PDF/image/document; returns `file_id` and SHA-256.
- `GET /api/v1/files/{file_id}/status` — Status of extraction/OCR pipeline.
- `GET /api/v1/files/{file_id}/preview` — Stream processed preview or extracted tables.

### Task & Routing
- `POST /api/v1/tasks/route` — Submit prompt; returns `RoutingDecision` and recommended model.

### Agent Workflow
- `POST /api/v1/agent/execute` — Launch multi-step agent workflow; returns `task_id`.
- `GET /api/v1/agent/tasks/{task_id}` — Polling query for task execution state.
- `GET /api/v1/agent/tasks/{task_id}/events` — Server-Sent Events (SSE) streaming live `AgentStepEvent` sequence.

### Knowledge & RAG
- `POST /api/v1/rag/query` — Test dense retrieval over indexed SOPs.
- `POST /api/v1/rag/index` — Index a new document into local sovereign knowledge base.

### Deliverables
- `POST /api/v1/deliverables/generate` — Generate Office file from validated JSON payload.
- `GET /api/v1/deliverables/{artifact_id}/download` — Secure local download of `.docx`, `.xlsx`, `.pptx`.

### Sovereignty & Audit
- `GET /api/v1/audit/events` — Query immutable audit trail.
- `GET /api/v1/network/status` — Inspect real-time host socket bindings and confirm zero external egress.

---

## 19. Data Contracts

All internal service boundaries communicate via strongly typed Pydantic models:

```python
# Task & Routing
class RoutingDecision(BaseModel):
    task_type: Literal["reasoning", "coding", "vision", "rag", "direct"]
    recommended_model_role: str
    confidence: float
    rationale: str
    required_tools: List[str]

# Agent State
class AgentStepEvent(BaseModel):
    task_id: str
    step_number: int
    state: Literal["idle", "planning", "acting", "observing", "reflecting", "completed", "failed"]
    action_type: Optional[str]
    action_payload: Optional[Dict[str, Any]]
    observation: Optional[str]
    thought: Optional[str]
    timestamp: float

# Deliverable Data Contract
class CorrosionReportSchema(BaseModel):
    equipment_tag: str
    inspection_date: str
    nominal_thickness_mm: float
    actual_thickness_mm: float
    corrosion_rate_mm_per_year: float
    remaining_life_years: float
    turnaround_action_required: bool
    engineering_justification: str
    regulatory_citations: List[str]
```

---

## 20. Database & Storage Strategy

- **Document Storage:** Flat filesystem organized by SHA-256 hash under `data/raw/` and `data/processed/`.
- **Vector Storage:** Portable Chroma or FAISS local index files under `data/knowledge/`.
- **State & Audit Ledger:** High-throughput JSONL append-only files under `logs/audit_events.jsonl`.
- *Future Migration:* Storage abstractions allow drop-in replacement with SQLite (local development) or PostgreSQL/pgvector (on-premise server) without touching application endpoints.

---

## 21. Configuration Strategy

- Implemented via `pydantic-settings` in `backend/app/core/config.py`.
- Dynamic base path resolution via `find_project_root()` and `pathlib.Path`.
- All operational parameters (Ollama URLs, hardware tiers, timeouts, directories) configurable via `.env`.
- Declarative model manifests configured via `models/configs/model_tiers.yaml`.

---

## 22. Security Strategy

- **Zero Outbound Telemetry:** All third-party telemetry, tracking, and remote reporting disabled.
- **Path Traversal Protection:** All file paths normalized and validated against `DATA_DIR` boundaries.
- **Subprocess Isolation:** Execution restricted to pre-validated commands with timeouts and resource ceilings.
- **Dependency Pinning:** Hash-checked requirements preventing remote package poisoning.

---

## 23. Sovereignty & Air-Gap Strategy

The project distinguishes **three levels of air-gap compliance**:
1. **Application Sovereignty:** Configured with `AIR_GAPPED_MODE=True`, prohibiting external endpoints.
2. **Network Containment:** Host socket monitor verifies zero established TCP/UDP sockets to non-loopback addresses (`0.0.0.0`, `127.0.0.1`).
3. **Physical Air-Gap Verification (Demo Protocol):** Procedure for evaluators:
   - Disconnect Wi-Fi / unplug Ethernet cable.
   - Run end-to-end corrosion audit demo.
   - Inspect OS socket monitor: 100% completion achieved with zero dropped connections.

---

## 24. Observability Strategy

- Structured JSON logging tracking `[timestamp] | [level] | [request_id] | [component] | [message]`.
- Every agent step generates an immutable entry in `logs/audit_events.jsonl`.
- Real-time SSE channel streams execution thoughts and tool observations directly to the UI.

---

## 25. Frontend Strategy

- **Industrial Aesthetic:** High-density, professional dark/light UI built with React 18, TypeScript, and Lucide icons.
- **Key Views:**
  - *Sovereignty Bar:* Live air-gap indicator and egress monitor.
  - *Workbench Console:* Document viewer, prompt input, and model selector.
  - *Execution Trace:* Visual state machine showing Agent Plan $\rightarrow$ Act $\rightarrow$ Observe sequence.
  - *Deliverable Viewer:* Instant download and tabular preview of generated DOCX and XLSX artifacts.
  - *Audit Explorer:* Searchable provenance ledger.

---

## 26. Testing Strategy

- **Unit Tests:** Pytest suites covering individual schemas, configuration resolution, and error envelopes.
- **Mock Inference Tests:** Offline mock backends simulating Ollama responses for fast CI verification without requiring GPU.
- **Sandbox Safety Tests:** Execution of timeout traps, infinite loops, and unauthorized filesystem calls to prove containment.
- **Document Regression Tests:** Automated byte-level verification ensuring generated DOCX/XLSX open cleanly without corruption.
- **Network Leak Tests:** Test suite that fails if any test initiates an outbound external socket.

---

## 27. Evaluation Metrics

| Subsystem | Metric | Target Threshold |
| :--- | :--- | :--- |
| **Router** | Intent Classification Accuracy | $\ge 90\%$ on test prompts |
| **Model Swapper**| VRAM Release Latency | $\le 4.0\text{ seconds}$ on swap |
| **RAG** | Retrieval Citation Recall | $\ge 85\%$ against MRPL SOP benchmark |
| **Agent** | Execution Completion Rate | $\ge 95\%$ on standard workflows |
| **Office Factory** | Deliverable Schema Conformance | $100\%$ valid Office binaries |
| **Sovereignty** | Outbound External HTTP Packets | Exactly 0 |

---

## 28. Model Evaluation Strategy

Local models are systematically evaluated using offline benchmark scripts in `experiments/`:
- **DeepSeek-R1-Distill-7B vs. Qwen2.5-Coder-3B:** Evaluated on refinery formula calculation benchmarks for accuracy, chain-of-thought derivation depth, and latency.
- **Qwen2.5-VL-3B vs. 7B:** Evaluated on degraded scan character error rate (CER) and tabular coordinate precision.

---

## 29. Router Training & Evaluation

- **Baseline:** Rule & keyword regex classifier (Level 0).
- **Colab Experimentation:** Synthetic dataset of 500 domain prompts categorized into `Reasoning`, `Coding`, `Vision`, `RAG`, and `Direct`.
- **Training (Optional):** Fine-tuning a lightweight DeBERTa or Qwen-1.5B classifier in Google Colab, exporting weights as GGUF/ONNX for local placement in `models/`.

---

## 30. Linux Portability Plan

| Layer | Windows Development | Linux On-Premise Target | Migration Action |
| :--- | :--- | :--- | :--- |
| **Paths** | `pathlib.Path` | `pathlib.Path` | No code change; driven by `PROJECT_ROOT`. |
| **Inference** | Ollama Windows | Ollama Linux / vLLM | Config change in `model_tiers.yaml`. |
| **Sandbox** | Restricted Subprocess | Rootless Docker / gVisor | Swap `SandboxExecutor` implementation. |
| **Sockets** | `psutil` Windows netstat | `psutil` Linux / `/proc/net` | Handled natively by portable `psutil`. |
| **GPU** | CUDA on RTX 4060 | CUDA on RTX 3090/4090/A5000 | Config change; adjust VRAM budget to 24 GB. |

---

## 31. Deployment Strategy

- **Development:** Direct native execution (`uvicorn` + `vite dev`) using virtual environment.
- **Staging / Evaluation:** Portable `docker-compose.yml` with isolated bridge network (`internal: true`).
- **Production (Air-Gapped Facility):** Tarball container archive loaded via `docker load` onto an air-gapped Linux workstation.

---

## 32. Offline Installation Strategy

1. **Online Build Machine:**
   - Pre-download Python wheels: `pip download -r requirements.txt -d ./wheels`.
   - Pre-fetch Node packages: `npm pack` or vendorized `node_modules`.
   - Pull model weights: `ollama pull deepseek-r1:7b`, export GGUF.
2. **Transfer:** Move artifacts via secure encrypted USB drive to air-gapped workstation.
3. **Offline Installation:** `pip install --no-index --find-links=./wheels -r requirements.txt`.

---

## 33. Implementation Phases

```
Phase 0: Architecture & Contracts (Complete)
Phase 1: Backend Foundation & API Gateway (Complete)
Phase 2: Local Model Manager & Provider Abstraction
Phase 3: Task Router Engine
Phase 4: Document Ingestion Pipeline
Phase 5: OCR & Vision Engine
Phase 6: Sovereign Knowledge & RAG Layer
Phase 7: Agent State Machine Runtime
Phase 8: Sandboxed Tool Execution
Phase 9: Structured Output & Validation
Phase 10: Deterministic Office Deliverables Factory
Phase 11: Audit & Network Sovereignty Monitor
Phase 12: Frontend Workbench UI
Phase 13: End-to-End System Integration
Phase 14: Accuracy & Performance Evaluation
Phase 15: Linux Portability & Container Validation
Phase 16: Demo Hardening & Presentation Runbook
```

---

### Phase 2 — Local Model Manager & Provider Abstraction
- **Objective:** Implement the local model management service capable of communicating with Ollama and performing serial VRAM swapping.
- **Why this phase exists:** To decouple all downstream AI components from direct provider APIs and ensure the system runs within 8 GB VRAM without crashing.
- **Prerequisites:** Phase 1 complete. Local Ollama installed.
- **Components:** `backend/app/services/model_manager/`
- **Files/modules:**
  - `backend/app/services/model_manager/ollama_provider.py`
  - `backend/app/services/model_manager/manager.py`
  - `backend/app/services/model_manager/mock_provider.py`
  - `backend/tests/test_model_manager.py`
- **Interfaces:** Implements `InferenceBackend` from `base.py`.
- **Data flow:** `Task` $\rightarrow$ `ModelManager.get_handle(role)` $\rightarrow$ checks resident model $\rightarrow$ unloads if necessary $\rightarrow$ loads target model $\rightarrow$ returns handle.
- **Dependencies:** `httpx`, `pyyaml`.
- **Implementation tasks:**
  1. Implement `OllamaProvider` connecting to local `127.0.0.1:11434`.
  2. Implement serial swapping logic: unload prior model via `keep_alive: "0m"`.
  3. Implement `MockProvider` for zero-hardware unit testing.
  4. Parse `models/configs/model_tiers.yaml` dynamically based on `HARDWARE_TIER`.
- **Testing tasks:** Test model listing, mock generation, tier config parsing, and swap signal.
- **Acceptance criteria:** Model handle successfully generates text; mock tests pass without Ollama; swap routine properly triggers unload.
- **Expected output:** Working `ModelManager` class ready for Router and Agent.
- **Known risks:** Ollama process not running on developer machine.
- **Fallback:** Automatic fallback to `MockProvider` with clear logged warning.
- **Definition of Done:** All unit tests pass, and Model Manager exposes unified interface.
- **Next phase dependency:** Required by Phase 3 (Router) and Phase 7 (Agent).

---

### Phase 3 — Task Router Engine
- **Objective:** Implement the intent classifier and model capability dispatcher.
- **Why this phase exists:** Core requirement to route queries dynamically rather than hardcoding a single LLM.
- **Prerequisites:** Phase 2 complete.
- **Components:** `backend/app/services/router/`
- **Files/modules:**
  - `backend/app/services/router/rule_router.py`
  - `backend/app/services/router/semantic_router.py`
  - `backend/app/services/router/router.py`
  - `backend/app/api/v1/endpoints/router.py`
  - `backend/tests/test_router.py`
- **Interfaces:** Implements `TaskRouter` from `base.py`.
- **Data flow:** `User Request + Context` $\rightarrow$ `TaskRouter.route_task()` $\rightarrow$ `RoutingDecision`.
- **Dependencies:** None additional.
- **Implementation tasks:**
  1. Build Level 0 Rule & Keyword classifier (handles calculations, images, SOP queries).
  2. Build confidence scoring and fallback mechanism.
  3. Mount `POST /api/v1/tasks/route` endpoint.
- **Testing tasks:** 20 benchmark prompts verifying that math routes to reasoning, scans to vision, and scripts to coding.
- **Acceptance criteria:** $\ge 90\%$ classification accuracy on benchmark suite; confidence scores properly populated.
- **Expected output:** Deterministic router service integrated with API Gateway.
- **Known risks:** Ambiguous multi-domain prompts.
- **Fallback:** Route to `reasoning` model with `confidence: 0.5`.
- **Definition of Done:** Router tests pass; endpoint exposed in `/docs`.
- **Next phase dependency:** Used by Agent in Phase 7.

---

### Phase 4 — Document Ingestion Pipeline
- **Objective:** Ingest, hash, and extract content from industrial documents (PDF, DOCX, XLSX, images).
- **Why this phase exists:** Air-gapped workflows begin with local document ingestion and provenance tracking.
- **Prerequisites:** Phase 1 complete.
- **Components:** `backend/app/services/ingestion/`
- **Files/modules:**
  - `backend/app/services/ingestion/hasher.py`
  - `backend/app/services/ingestion/pdf_parser.py`
  - `backend/app/services/ingestion/table_extractor.py`
  - `backend/app/api/v1/endpoints/files.py`
  - `backend/tests/test_ingestion.py`
- **Interfaces:** `DocumentIngestionResult`, `ParsedTable`.
- **Data flow:** File Upload $\rightarrow$ Compute SHA-256 $\rightarrow$ Save to `data/raw/` $\rightarrow$ Extract text & tables $\rightarrow$ Save to `data/processed/`.
- **Dependencies:** `pypdf`, `pdfplumber`.
- **Implementation tasks:**
  1. Implement secure file persistence with path traversal sanitization.
  2. Implement text and tabular extraction for digital PDFs.
  3. Store document metadata and provenance records.
- **Testing tasks:** Ingest sample PDF; verify extracted text, tables, and hash validity.
- **Acceptance criteria:** Files saved with SHA-256; tables extracted as structured JSON; original files unaltered.
- **Expected output:** File upload API and document parsing engine.
- **Known risks:** Password-protected or corrupt PDFs.
- **Fallback:** Catch parsing exceptions and return structured `INVALID_DOCUMENT` error.
- **Definition of Done:** Endpoints functional; test suite validates extraction.
- **Next phase dependency:** Feeds Phase 5 (OCR/Vision) and Phase 6 (RAG).

---

### Phase 5 — OCR & Vision Engine
- **Objective:** Process scanned inspection logs, degraded technical sheets, and engineering schematics.
- **Why this phase exists:** Public sector refineries have thousands of historical scanned NDT sheets and drawing slices.
- **Prerequisites:** Phase 4 complete.
- **Components:** `backend/app/services/vision/`
- **Files/modules:**
  - `backend/app/services/vision/ocr_engine.py`
  - `backend/app/services/vision/vlm_client.py`
  - `backend/app/services/vision/schematic_parser.py`
  - `backend/tests/test_vision.py`
- **Interfaces:** `OCRExtractionResult`, `VisualQARequest`.
- **Data flow:** Scanned Page $\rightarrow$ OCR engine $\rightarrow$ Visual VLM verification (Qwen2.5-VL) $\rightarrow$ Clean table tokens.
- **Dependencies:** `pillow`, `pytesseract` (optional local wrapper).
- **Implementation tasks:**
  1. Build image preprocessing pipeline (contrast enhancement, binarization).
  2. Build localized OCR runner.
  3. Integrate Qwen2.5-VL prompt template for reading tabular cells and P&ID instrument tags.
- **Testing tasks:** Test OCR extraction on synthetic NDT scan; verify numerical readings match ground truth.
- **Acceptance criteria:** Reads ultrasonic thickness values accurately; flags low-confidence characters for review.
- **Expected output:** Localized vision engine capable of answering questions about technical images.
- **Known risks:** Poor resolution scans causing character confusion (e.g., '8' vs 'B').
- **Fallback:** Dual-check OCR output with VLM reasoning model before passing to Agent.
- **Definition of Done:** Vision engine passes offline unit tests with mock image inputs.
- **Next phase dependency:** Used by Agent during Primary Demo.

---

### Phase 6 — Sovereign Knowledge & RAG Layer
- **Objective:** Build local semantic retrieval over MRPL SOPs and industrial inspection standards.
- **Why this phase exists:** To ground agent reasoning in verified organizational engineering standards with explicit citations.
- **Prerequisites:** Phase 4 complete.
- **Components:** `backend/app/services/rag/`
- **Files/modules:**
  - `backend/app/services/rag/chunker.py`
  - `backend/app/services/rag/vector_store.py`
  - `backend/app/services/rag/retriever.py`
  - `backend/app/api/v1/endpoints/rag.py`
  - `backend/tests/test_rag.py`
- **Interfaces:** `RetrievedChunk`, `CitationSource`.
- **Data flow:** SOP PDF $\rightarrow$ Semantic chunker $\rightarrow$ Local embedding $\rightarrow$ Vector Index $\rightarrow$ Top-$k$ query $\rightarrow$ Prompt context.
- **Dependencies:** `chromadb` or local FAISS (`faiss-cpu`), `sentence-transformers` or CPU embedding runner.
- **Implementation tasks:**
  1. Build hierarchical chunker preserving headers and table rows.
  2. Implement portable local vector store under `data/knowledge/`.
  3. Implement retrieval ranking with minimum similarity threshold.
- **Testing tasks:** Index sample MRPL piping SOP; query for *"minimum wall thickness for class 150 carbon steel"*; assert correct clause retrieved.
- **Acceptance criteria:** Top result contains exact SOP clause; citations include file name, page number, and chunk ID.
- **Expected output:** Sovereign RAG engine with zero external network connectivity.
- **Known risks:** Vector index corruption or memory bloat.
- **Fallback:** In-memory cosine similarity fallback using local JSON vectors.
- **Definition of Done:** RAG endpoints pass unit tests and provide traceable source citations.
- **Next phase dependency:** Invoked as a tool by the Agent in Phase 7.

---

### Phase 7 — Agent State Machine Runtime
- **Objective:** Implement the explicit multi-step agent state machine.
- **Why this phase exists:** To transform the system from a single-turn chatbot into an autonomous multi-step reasoning workbench.
- **Prerequisites:** Phases 2, 3, 4, 6 complete.
- **Components:** `backend/app/services/agent/`
- **Files/modules:**
  - `backend/app/services/agent/state_machine.py`
  - `backend/app/services/agent/planner.py`
  - `backend/app/services/agent/executor.py`
  - `backend/app/api/v1/endpoints/agent.py`
  - `backend/tests/test_agent.py`
- **Interfaces:** Implements `AgentOrchestrator` from `base.py`.
- **Data flow:** Goal $\rightarrow$ Plan $\rightarrow$ State loop (Plan $\rightarrow$ Act $\rightarrow$ Observe $\rightarrow$ Reflect) $\rightarrow$ Yield `AgentStepEvent`.
- **Dependencies:** None additional.
- **Implementation tasks:**
  1. Build explicit state transition engine (`IDLE` $\rightarrow$ `PLANNING` $\rightarrow$ `ACTING` $\rightarrow$ `OBSERVING` $\rightarrow$ `VALIDATING` $\rightarrow$ `COMPLETED`).
  2. Implement tool dispatcher routing actions to RAG, Vision, Sandbox, and Deliverables.
  3. Implement loop safety limits (max 8 steps, step timeouts).
  4. Mount SSE event stream endpoint for real-time UI tracking.
- **Testing tasks:** Execute multi-step task with mock tools; verify state progression and event emission.
- **Acceptance criteria:** State machine handles tool failure gracefully; never enters infinite loop; terminates with valid state.
- **Expected output:** Complete, observable agent execution engine.
- **Known risks:** LLM hallucinating non-existent tool names.
- **Fallback:** State machine catches invalid tool call, enters `REFLECT` state, and prompts model with valid tool catalog.
- **Definition of Done:** Agent executes multi-step synthetic scenario successfully in unit tests.
- **Next phase dependency:** Coordinates tools from Phases 8, 9, 10.

---

### Phase 8 — Sandboxed Tool Execution
- **Objective:** Provide a restricted local execution environment for Python calculations.
- **Why this phase exists:** LLMs are prone to arithmetic errors; engineering calculations must be verified deterministically.
- **Prerequisites:** Phase 1 complete.
- **Components:** `backend/app/services/sandbox/`
- **Files/modules:**
  - `backend/app/services/sandbox/process_runner.py`
  - `backend/app/services/sandbox/validator.py`
  - `backend/tests/test_sandbox.py`
- **Interfaces:** Implements `SandboxExecutor` from `base.py`.
- **Data flow:** Python calculation script $\rightarrow$ Subprocess runner $\rightarrow$ Capture stdout/stderr $\rightarrow$ `SandboxExecutionResult`.
- **Dependencies:** Standard library (`subprocess`, `resource` on Linux / job objects on Windows).
- **Implementation tasks:**
  1. Build subprocess wrapper with 15-second timeout and 512 MB memory limit.
  2. Implement code safety pre-screener (blocks `os.system`, `socket`, `urllib`, `requests`).
  3. Execute calculations in temporary scratch directories.
- **Testing tasks:** Execute valid corrosion calculation; execute infinite loop script (assert timeout); execute socket attempt (assert blocked).
- **Acceptance criteria:** Infinite loops terminate cleanly at 15s; unsafe imports rejected before execution; valid calculations return exact numbers.
- **Expected output:** Safe local calculation runner.
- **Known risks:** Subprocess hanging on Windows.
- **Fallback:** Force kill process tree on timeout.
- **Definition of Done:** Sandbox passes safety and calculation test suites.
- **Next phase dependency:** Invoked by Agent for corrosion and engineering calculations.

---

### Phase 9 — Structured Output & Validation
- **Objective:** Enforce JSON schema validation between LLM reasoning and deliverable generation.
- **Why this phase exists:** To eliminate LLM hallucinations before document rendering.
- **Prerequisites:** Phase 1 complete.
- **Components:** `backend/app/schemas/` & `backend/app/services/deliverables/`
- **Files/modules:**
  - `backend/app/schemas/corrosion_report.py`
  - `backend/app/schemas/pid_inventory.py`
  - `backend/app/services/deliverables/validator.py`
  - `backend/tests/test_structured_output.py`
- **Interfaces:** `ValidatedDeliverablePayload`.
- **Data flow:** LLM raw text $\rightarrow$ JSON extractor $\rightarrow$ Pydantic validation $\rightarrow$ Validated domain object.
- **Dependencies:** `pydantic`.
- **Implementation tasks:**
  1. Create Pydantic schemas for MRPL Executive Notes and Calculation Sheets.
  2. Implement robust JSON extractor (handles markdown fences ` ```json `).
  3. Implement automatic schema repair retry loop.
- **Testing tasks:** Test valid JSON, malformed JSON, and missing fields; assert validation errors caught.
- **Acceptance criteria:** Non-conforming JSON rejected with exact field errors; valid JSON produces typed Pydantic instance.
- **Expected output:** Zero-defect data validation bridge.
- **Known risks:** LLM omitting required fields under low-context conditions.
- **Fallback:** Pass validation errors back to Agent in `REFLECT` state for targeted re-generation.
- **Definition of Done:** Schema validation tests pass with $100\%$ precision.
- **Next phase dependency:** Feeds Phase 10 (Office Generation).

---

### Phase 10 — Deterministic Office Deliverables Factory
- **Objective:** Programmatically generate production-quality `.docx`, `.xlsx`, and `.pptx` documents.
- **Why this phase exists:** Core requirement to produce professional Office artifacts rather than conversational text.
- **Prerequisites:** Phase 9 complete.
- **Components:** `backend/app/services/deliverables/`
- **Files/modules:**
  - `backend/app/services/deliverables/docx_builder.py`
  - `backend/app/services/deliverables/xlsx_builder.py`
  - `backend/app/services/deliverables/pptx_builder.py`
  - `backend/app/services/deliverables/factory.py`
  - `backend/tests/test_deliverables.py`
- **Interfaces:** `DeliverablesFactory`, `OfficeArtifact`.
- **Data flow:** Validated Pydantic Object $\rightarrow$ Template Builder $\rightarrow$ Binary File written to `outputs/` $\rightarrow$ Download URL.
- **Dependencies:** `python-docx`, `openpyxl`, `python-pptx`.
- **Implementation tasks:**
  1. Build MRPL Word template with official styling, headers, metadata box, and signature blocks.
  2. Build Excel generator embedding active calculation formulas (`=B4-C4/D4`) and conditional formatting.
  3. Build PowerPoint slide deck generator for executive briefings.
- **Testing tasks:** Generate sample Word and Excel files; verify file integrity, formatting, and formula syntax.
- **Acceptance criteria:** Files open in Microsoft Office and LibreOffice without warnings; Excel formulas compute dynamically.
- **Expected output:** Deterministic deliverable generation engine.
- **Known risks:** Style misalignment or font substitution across OS platforms.
- **Fallback:** Use standard cross-platform system fonts (Arial, Calibri, Times New Roman).
- **Definition of Done:** Office documents generated and validated via automated tests.
- **Next phase dependency:** Used in Phase 13 (End-to-End Integration).

---

### Phase 11 — Audit & Network Sovereignty Monitor
- **Objective:** Record immutable execution logs and prove host network isolation.
- **Why this phase exists:** High-stakes hackathon judging criteria: empirical proof of sovereignty and zero external transmission.
- **Prerequisites:** Phase 1 complete.
- **Components:** `backend/app/services/audit/` & `backend/app/services/network/`
- **Files/modules:**
  - `backend/app/services/audit/logger.py`
  - `backend/app/services/network/socket_monitor.py`
  - `backend/app/api/v1/endpoints/audit.py`
  - `backend/app/api/v1/endpoints/network.py`
  - `backend/tests/test_sovereignty.py`
- **Interfaces:** `AuditEvent`, `NetworkStatus`.
- **Data flow:** System action $\rightarrow$ Write append-only JSONL; Network scan $\rightarrow$ Read local socket table via `psutil`.
- **Dependencies:** `psutil`.
- **Implementation tasks:**
  1. Implement append-only JSONL audit ledger with SHA-256 hash chaining.
  2. Implement socket monitor inspecting active TCP/UDP connections for non-local egress.
  3. Expose `/api/v1/network/status` endpoint for real-time UI dashboard display.
- **Testing tasks:** Trigger test audit events; inspect log file format; verify socket monitor correctly detects loopback vs foreign connections.
- **Acceptance criteria:** Audit logs immutable and chronologically ordered; socket monitor confirms 0 non-loopback connections during test run.
- **Expected output:** Verifiable sovereignty proof system.
- **Known risks:** OS permission restrictions when reading system sockets.
- **Fallback:** Gracefully degrade to inspecting process-level sockets if system-wide inspection is restricted.
- **Definition of Done:** Sovereignty tests pass; proof endpoint live.
- **Next phase dependency:** Integrated into Frontend in Phase 12.

---

### Phase 12 — Frontend Workbench UI
- **Objective:** Build the operator interface displaying the workbench console, agent execution trace, and sovereignty monitor.
- **Why this phase exists:** To provide an intuitive, high-impact presentation layer for SIH judges.
- **Prerequisites:** Phases 1, 7, 10, 11 complete.
- **Components:** `frontend/src/`
- **Files/modules:**
  - `frontend/src/components/SovereigntyBar.tsx`
  - `frontend/src/components/DocumentViewer.tsx`
  - `frontend/src/components/AgentGraphTrace.tsx`
  - `frontend/src/components/DeliverablesPanel.tsx`
  - `frontend/src/components/AuditLedger.tsx`
  - `frontend/src/pages/WorkbenchPage.tsx`
- **Interfaces:** REST API client bindings and SSE event listeners.
- **Data flow:** User Interaction $\rightarrow$ REST call $\rightarrow$ Backend $\rightarrow$ SSE stream $\rightarrow$ Real-time UI component update.
- **Dependencies:** `lucide-react`, TailwindCSS.
- **Implementation tasks:**
  1. Build Sovereignty header showing active air-gap status and outbound connection count (0).
  2. Build Document upload and inspection pane.
  3. Build dynamic Agent State Machine visualization displaying Plan $\rightarrow$ Act $\rightarrow$ Observe sequence live.
  4. Build Deliverable download card with embedded preview.
- **Testing tasks:** Verify UI renders correctly; verify SSE messages update state machine without page reload.
- **Acceptance criteria:** UI responsive, displays all 5 pillars prominently, updates live during workflow execution.
- **Expected output:** Production-grade operator workbench interface.
- **Known risks:** WebSocket / SSE disconnects during heavy inference.
- **Fallback:** Polling fallback (`GET /api/v1/agent/tasks/{id}`) if SSE stream interrupts.
- **Definition of Done:** Frontend communicates cleanly with backend and displays all execution states.
- **Next phase dependency:** Used in Phase 13.

---

### Phase 13 — End-to-End System Integration
- **Objective:** Connect all subsystems to execute the Primary Corrosion Audit Workflow seamlessly.
- **Why this phase exists:** Proves the complete end-to-end integration required by SIH26117.
- **Prerequisites:** All prior phases (Phases 1 to 12) complete.
- **Components:** Full stack integration.
- **Files/modules:**
  - `backend/tests/test_e2e_workflow.py`
  - `scripts/run_e2e_demo.py`
- **Interfaces:** End-to-end integration tests.
- **Data flow:** Ingestion $\rightarrow$ Routing $\rightarrow$ Agent Planning $\rightarrow$ RAG $\rightarrow$ Vision $\rightarrow$ Sandbox $\rightarrow$ Deliverables $\rightarrow$ Audit.
- **Dependencies:** All project dependencies.
- **Implementation tasks:**
  1. Wire full pipeline with synthetic test files (`data/samples/corrosion_inspection_c101.pdf`).
  2. Execute end-to-end run under both Mock Mode and Live Ollama Mode.
  3. Verify output files generated under `outputs/docx/` and `outputs/xlsx/`.
- **Testing tasks:** Execute `test_e2e_workflow.py`; verify all 5 core capabilities execute in sequence.
- **Acceptance criteria:** Workflow completes in $< 60\text{ seconds}$; Word and Excel documents produced; audit log contains complete event chain; 0 external sockets detected.
- **Expected output:** Fully operational hackathon demonstrator.
- **Known risks:** Bottlenecks during serial model swap causing timeout.
- **Fallback:** Optimize keep-alive unloading parameters in `model_tiers.yaml`.
- **Definition of Done:** Entire workflow runs unattended from a single command.
- **Next phase dependency:** Feeds Phase 14 (Evaluation) and Phase 16 (Demo Hardening).

---

### Phase 14 — Accuracy & Performance Evaluation
- **Objective:** Benchmark the workbench on accuracy, VRAM usage, and latency.
- **Why this phase exists:** Provides empirical evidence and charts for SIH technical evaluation.
- **Prerequisites:** Phase 13 complete.
- **Components:** `experiments/` & evaluation scripts.
- **Files/modules:**
  - `experiments/router/benchmark_router.py`
  - `experiments/rag/eval_retrieval.py`
  - `experiments/vision/eval_ocr_precision.py`
  - `docs/architecture/evaluation_report.md`
- **Interfaces:** Evaluation metrics reporting.
- **Data flow:** Benchmark test sets $\rightarrow$ System execution $\rightarrow$ Metrics calculation (Precision, Recall, F1, Latency).
- **Dependencies:** `scikit-learn`, `matplotlib` (offline scripts).
- **Implementation tasks:**
  1. Evaluate Router on 50 test queries; generate confusion matrix.
  2. Evaluate RAG retrieval recall on MRPL SOP queries.
  3. Measure VRAM consumption curve on RTX 4060 during serial swapping.
- **Testing tasks:** Run evaluation suite and compile metrics into Markdown table.
- **Acceptance criteria:** Documented proof of $\ge 90\%$ router accuracy and $\le 7.5\text{ GB}$ peak VRAM usage on Dev Tier.
- **Expected output:** Technical evaluation report and slide graphics.
- **Known risks:** Out-of-distribution prompts failing classification.
- **Fallback:** Document failure modes and establish boundary constraints.
- **Definition of Done:** Evaluation report committed under `docs/architecture/`.
- **Next phase dependency:** Feeds Phase 15 and 16.

---

### Phase 15 — Linux Portability & Container Validation
- **Objective:** Validate that the application runs identically on Linux without code modification.
- **Why this phase exists:** Enforces the non-negotiable requirement for on-premise industrial deployment.
- **Prerequisites:** Phase 13 complete.
- **Components:** `docker/` & portable core.
- **Files/modules:**
  - `docker/Dockerfile.backend`
  - `docker/Dockerfile.frontend`
  - `docker-compose.yml`
  - `scripts/verify_linux_portability.py`
- **Interfaces:** Cross-platform deployment scripts.
- **Data flow:** Git repository $\rightarrow$ Linux host / Docker container $\rightarrow$ Run unit and E2E tests.
- **Dependencies:** Docker (optional testing on WSL2 / Linux VM).
- **Implementation tasks:**
  1. Verify zero drive letters (`C:\`, `D:\`) or backslashes exist in codebase.
  2. Build and run backend container under Linux environment.
  3. Run `pytest` inside Linux container; verify all tests pass.
- **Testing tasks:** Execute test suite on Linux / WSL2 environment.
- **Acceptance criteria:** $100\%$ of unit tests pass on Linux without modifying a single line of Python code.
- **Expected output:** Certified cross-platform workbench package.
- **Known risks:** Case-sensitive filesystem differences between Windows and Linux.
- **Fallback:** Enforce strict lowercase naming across all files and imports.
- **Definition of Done:** Linux test execution log verified and documented.
- **Next phase dependency:** Feeds Phase 16.

---

### Phase 16 — Demo Hardening & Presentation Runbook
- **Objective:** Finalize offline demonstrator, prepare synthetic assets, and write judge-facing presentation runbook.
- **Why this phase exists:** Guarantees a flawless, high-confidence demonstration during hackathon judging.
- **Prerequisites:** All phases complete.
- **Components:** `docs/demo/` & `data/samples/`.
- **Files/modules:**
  - `docs/demo/runbook.md`
  - `docs/demo/judge_faq.md`
  - `data/samples/corrosion_report_c101.pdf`
  - `data/samples/pid_sample_hc.png`
  - `scripts/demo_reset.py`
- **Interfaces:** Demonstration runner.
- **Data flow:** Reset demo state $\rightarrow$ Execute primary workflow $\rightarrow$ Inspect outputs and audit trail.
- **Dependencies:** None additional.
- **Implementation tasks:**
  1. Create synthetic, anonymized industrial test files representing MRPL refining operations.
  2. Write `demo_reset.py` script to clear cache and outputs between demo runs.
  3. Write step-by-step judge runbook mapping every demo click to the 5 core pillars.
- **Testing tasks:** Perform dry-run demo with disconnected Wi-Fi / Ethernet; record video backup.
- **Acceptance criteria:** Demo executes in $< 60\text{ seconds}$ offline; delivers all 5 core proofs.
- **Expected output:** Complete presentation package and runbook.
- **Known risks:** Live demo hardware glitch or thermal throttling.
- **Fallback:** High-definition pre-recorded walkthrough video and static artifact backups available.
- **Definition of Done:** Project ready for Grand Finale presentation.
- **Next phase dependency:** Project complete.

---

## 34. Dependency Graph

```
[Phase 0: Architecture Contracts]
             │
             ▼
[Phase 1: Backend Foundation]
             │
             ├──────────────────────────────────────────────┐
             ▼                                              ▼
[Phase 2: Local Model Manager]                  [Phase 4: Document Ingestion]
             │                                              │
             ├───────────────────────┐                      ├───────────────────────┐
             ▼                       ▼                      ▼                       ▼
   [Phase 3: Task Router]   [Phase 8: Sandbox]    [Phase 5: Vision/OCR]    [Phase 6: RAG]
             │                       │                      │                       │
             └───────────────┬───────┴──────────────────────┴───────────────────────┘
                             │
                             ▼
                 [Phase 7: Agent Runtime]
                             │
                             ├──────────────────────┐
                             ▼                      ▼
                  [Phase 9: Schemas]      [Phase 11: Audit/Net]
                             │                      │
                             ▼                      │
                  [Phase 10: Deliverables]          │
                             │                      │
                             └───────────┬──────────┘
                                         │
                                         ▼
                             [Phase 12: Frontend UI]
                                         │
                                         ▼
                           [Phase 13: E2E Integration]
                                         │
                             ┌───────────┴───────────┐
                             ▼                       ▼
                   [Phase 14: Evaluation]  [Phase 15: Linux Port]
                             │                       │
                             └───────────┬───────────┘
                                         │
                                         ▼
                             [Phase 16: Demo Hardening]
```

---

## 35. MVP Acceptance Criteria

- [ ] System starts cleanly via portable configuration without hardcoded paths or drive letters.
- [ ] Operates with complete functionality with host network interface disabled (Wi-Fi/Ethernet off).
- [ ] Dynamically routes tasks between reasoning, coding, and vision models without code modification.
- [ ] Agent state machine executes Plan $\rightarrow$ Act $\rightarrow$ Observe loop with UI step visibility.
- [ ] Ingests degraded industrial PDF and extracts tabular data via local OCR/VLM.
- [ ] Executes calculation logic inside an isolated sandbox with memory and timeout enforcement.
- [ ] Outputs native Microsoft Word (`.docx`) and Excel (`.xlsx`) deliverables with dynamic formulas.
- [ ] All deliverable data validated against Pydantic schemas before rendering.
- [ ] Host socket monitor proves 0 outbound non-loopback network connections.
- [ ] All unit and integration tests pass on both Windows and Linux.

---

## 36. Demo Acceptance Criteria

| Requirement | Live Action in Demo | Observable Proof on Screen |
| :--- | :--- | :--- |
| **Sovereignty** | Evaluator turns off Wi-Fi; runs workflow. | Live UI socket monitor shows `Egress: 0 bytes`, `Sockets: Loopback Only`. |
| **Routing** | Submit calculation prompt. | UI Router badge displays `Model: DeepSeek-R1 (Reasoning)` with confidence score. |
| **Agentic Loop** | Workflow executes multi-step task. | UI State Graph animates through `PLAN` $\rightarrow$ `ACT` $\rightarrow$ `OBSERVE` $\rightarrow$ `VALIDATE`. |
| **Multimodal** | Upload scanned NDT corrosion log. | Document viewer displays extracted thickness table with OCR confidence tags. |
| **Safe Sandbox**| Calculation executes. | UI shows sandboxed Python execution trace with verified remaining life value. |
| **Office Output**| Click "Download Memo". | Native `.docx` opens with MRPL header, summary table, and formatted approval notes. |

---

## 37. Risks

1. **Hardware Memory Contention (8 GB VRAM):** Risk of CUDA Out-Of-Memory if models fail to unload cleanly during swapping.
2. **Inference Latency on Dev Hardware:** 7B quantized model may take 20–30 seconds for deep reasoning steps.
3. **OCR Inaccuracy on Degraded Scans:** Heavy noise or skew leading to corrupted numerical extraction.
4. **Cross-Platform Path Discrepancies:** Accidental introduction of Windows backslashes or case-sensitivity bugs.
5. **Demonstration Environment Variables:** Host firewall or antivirus interfering with loopback sockets.

---

## 38. Mitigations

1. **Strict Serial Swapping:** Force `keep_alive: 0` in Ollama on model switch; poll VRAM clearance before next model load.
2. **Deterministic Fallbacks & Streaming:** Stream thoughts via SSE so the user sees continuous progress while the model generates.
3. **VLM Verification:** Pass ambiguous OCR crops to `qwen2.5-vl` for contextual error correction.
4. **Pathlib Enforcement:** Automated CI check banning string concatenation for file paths.
5. **Offline Standalone Runbook:** Prepare pre-cached demo packages and pre-recorded HD video verification backup.

---

## 39. Future Scaling (Target Tier: 24–48 GB Workstation)

When migrating from the 8 GB Laptop to an enterprise workstation (RTX 3090, 4090, or A5000):
- Change single configuration key: `HARDWARE_TIER=target` in `.env`.
- `model_tiers.yaml` activates **Quantized Colocation** via vLLM or multi-model Ollama serving:
  - `deepseek-r1-distill-qwen:14b` permanently resident in VRAM (~12 GB).
  - `qwen2.5-vl:7b` permanently resident in VRAM (~10 GB).
- Model swapping latency drops from $\sim 4.0\text{ seconds}$ to $< 50\text{ ms}$, enabling real-time conversational agent loops.

---

## 40. Post-MVP Roadmap

- **ColPali Multi-Vector Visual Retrieval:** Native page-image indexing for complex P&IDs without OCR downsampling.
- **eBPF Kernel-Level Network Containment:** Enterprise Linux network confinement enforcing hard packet drop policies at the kernel level.
- **32B Analytical Reasoning Engine:** Deployment of DeepSeek-R1 32B for thermodynamic simulation and plant root-cause analysis.
- **Enterprise IAM & Role-Based Access Control:** Integration with refinery Active Directory / LDAP with granular document clearance levels.
- **Automated P&ID Topological Graph Reconstruction:** Vectorization of flow lines, valve connectivity, and instrumentation loops into Neo4j graph databases.
