# SIH26117 — SOVEREIGN ON-PREMISE AGENTIC AI WORKBENCH
## Master Project Report & Complete Architecture Blueprint (Single Source of Truth)

---

> **Project Name:** Sovereign On-Premise Agentic AI Workbench for MRPL  
> **Problem Statement ID:** SIH26117  
> **Sponsoring Organization:** Mangalore Refinery and Petrochemicals Limited (MRPL)  
> **Category / Theme:** Software / Smart Automation  
> **Hardware Profile Baseline:** Single On-Premise Workstation / Laptop (NVIDIA RTX 4060 8 GB VRAM, 16 GB RAM)  
> **Target Production Profile:** Enterprise Edge Server / Workstation (24 GB – 48 GB VRAM, Linux)  
> **Core Architecture Stack:** Python 3.11, FastAPI, React 18, TypeScript, Vite, Vanilla CSS Design System, Ollama  
> **Air-Gap Invariant:** Pure Loopback (`127.0.0.1`), Zero Cloud APIs, Zero Outbound Sockets  
> **Document Purpose:** Complete, authoritative single-file source of truth for understanding the full system, explaining the technical achievements, evaluating architecture/benchmarks, and **redesigning or extending the frontend**.

---

## Table of Contents

1. [Executive Summary & Problem Statement](#1-executive-summary--problem-statement)
2. [End-to-End System Architecture](#2-end-to-end-system-architecture)
3. [Multi-Model Portfolio & Local Inference Management](#3-multi-model-portfolio--local-inference-management)
4. [The 11 Operational Pipeline Stages](#4-the-11-operational-pipeline-stages)
5. [Backend Architecture & Complete REST API Reference](#5-backend-architecture--complete-rest-api-reference)
6. [Complete Frontend Architecture & UI Redesign Specification](#6-complete-frontend-architecture--ui-redesign-specification)
   - [6.1 Industrial Design System & Design Tokens](#61-industrial-design-system--design-tokens)
   - [6.2 Complete TypeScript Type Contracts](#62-complete-typescript-type-contracts)
   - [6.3 Frontend State Management & Hooks](#63-frontend-state-management--hooks)
   - [6.4 Page-by-Page Specifications & Layout Blueprint](#64-page-by-page-specifications--layout-blueprint)
   - [6.5 Component Architecture & Hierarchy Tree](#65-component-architecture--hierarchy-tree)
   - [6.6 Frontend Redesign Guidelines & UI Modernization Blueprint](#66-frontend-redesign-guidelines--ui-modernization-blueprint)
7. [Primary Industrial Demonstration Scenario (Refinery Asset C-101)](#7-primary-industrial-demonstration-scenario-refinery-asset-c-101)
8. [Empirical Benchmarks & Performance Telemetry](#8-empirical-benchmarks--performance-telemetry)
9. [Failure Safety & Security Invariants](#9-failure-safety--security-invariants)
10. [Single-Command Execution & Developer Runbook](#10-single-command-execution--developer-runbook)

---

# 1. Executive Summary & Problem Statement

### 1.1 The Industrial Challenge (MRPL Context)
Continuous-process hydrocarbon refining complexes such as Mangalore Refinery and Petrochemicals Limited (MRPL), along with defense manufacturing units, intelligence-linked research facilities, and public sector undertakings (PSUs), generate massive volumes of proprietary and classified operational data:
- Piping & Instrumentation Diagrams (P&IDs), process flow diagrams (PFDs), and equipment isometric drawings.
- Non-Destructive Testing (NDT) inspection sheets, ultrasonic wall thickness surveys, and corrosion coupons.
- Proprietary crude assay evaluations, yield models, and blending formulations.
- High-level administrative approval notes, capital expenditure proposals, and board memoranda.

### 1.2 The Sovereign Imperative
Enterprise IT security policies strictly prohibit sending this operational data to public cloud AI services (e.g., ChatGPT, Claude, Azure OpenAI) due to national critical infrastructure protection policies. Consequently, technical personnel face an untenable choice:
1. Perform labor-intensive calculations and report drafting manually, throttling operational agility.
2. Compromise operational security by covertly pasting technical fragments into external consumer AI tools.

### 1.3 The SIH26117 Solution
The **SIH26117 Sovereign Agentic AI Workbench** delivers an air-gapped, on-premise industrial intelligence platform operating entirely within the enterprise perimeter:
- **Zero Cloud Leakage:** All foundation models run locally on consumer/enterprise GPU hardware over `127.0.0.1`.
- **Model-Agnostic Portfolio:** Dynamically allocates 6 open-weight models across dedicated roles (`router`, `reasoning`, `coder`, `vision`, `embedding`) without hardcoding model IDs in business logic.
- **Autonomous Multi-Step Agent:** Decomposes industrial objectives into an 11-stage pipeline executing Plan $\rightarrow$ Act $\rightarrow$ Observe $\rightarrow$ Reflect $\rightarrow$ Validate cycles.
- **Deterministic Sandboxed Math:** Eliminates model arithmetic hallucinations by executing strict Python calculations inside an isolated subprocess sandbox.
- **Fail-Closed Validation Gate:** Withholds deliverable release unless 12 engineering tolerances, monotonicity rules, and standard bounds pass 100%.
- **Deterministic Office Factory:** Compiles branded, publication-quality `.docx` memoranda and `.xlsx` calculation workbooks.
- **Tamper-Evident Audit & Sovereignty Proof:** Logs all operations to a SHA-256 hash-chained immutable JSONL ledger while continuously auditing host network sockets to guarantee zero non-loopback egress.

---

# 2. End-to-End System Architecture

```
                                  AIR-GAP BOUNDARY (127.0.0.1)
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │                                REACT WORKBENCH FRONTEND                                │
  │    (WorkbenchPage | DocumentsPage | KnowledgePage | ModelsPage | Audit | Sovereignty)   │
  └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │ HTTP REST (/api/v1)
  ┌───────────────────────────────────────────▼────────────────────────────────────────────┐
  │                           FASTAPI MASTER GATEWAY & ROUTER                              │
  │                  (app.api.v1: Health, Models, Router, Files, Workflows)                │
  └───────┬────────────────────────────────────────────────────────────────────────┬───────┘
          │                                                                        │
   [Stage 0: Ingestion]                                                    [Stage 7: Validation Gate]
   IngestionService.ingest_file()                                          StructuredOutputService.validate()
          │ (PDF/XLSX/PNG, SHA-256 bound)                                          │ (12 Fail-Closed Invariants)
   [Stage 1: Vision / VLM]                                                 [Stage 8: Deliverables]
   VisionEngine → ModelManagerVisionProvider                               DeliverablesFactory.generate()
          │ (Base64 image buffer → qwen2.5vl:3b)                                   │ (.docx memorandum & .xlsx sheet)
   [Stage 2: Intent Routing]                                               [Stage 9: Audit Ledger]
   RuleRouter.route()                                                      AuditService.verify_ledger()
          │ (Deterministic taxonomy matching)                                      │ (SHA-256 append-only chain)
   [Stage 3: Model Allocation]                                             [Stage 10: Sovereignty Proof]
   ModelManager.get_tier_config()                                          RuntimeNetworkMonitor.observe()
          │ (Serial GPU swap on 8GB VRAM)                                          │ (Assert: 0 foreign sockets)
   [Stage 4: Sovereign RAG]                                                        ▼
   SovereignRetriever.retrieve_with_citations()                            COMPLETE TELEMETRY PACKAGE
          │ (Dense vector search over MRPL SOPs)                           CorrosionAuditWorkflowResult
   [Stage 5: Agent Lifecycle]                                                      ▲
   AgentStateMachineOrchestrator.execute_task()                                    │
          │ (11-state autonomous reasoning loop)                                   │
   [Stage 6: Sandboxed Calculation] ───────────────────────────────────────────────┘
   SubprocessSandboxExecutor.execute_tool()
   (Deterministic Python math: API 570 remaining life)
```

---

# 3. Multi-Model Portfolio & Local Inference Management

### 3.1 The 6 Configured Local Models

The workbench configures and operates a curated portfolio of 6 open-weight models resident in local Ollama storage:

| Model Role | Installed Tag | Parameter Count | Quantization | Size on Disk | Primary Responsibility |
|:---|:---|:---|:---|:---|:---|
| **`router`** | `qwen2.5:1.5b` | 1.5B | Q4_K_M | 986 MB | Lightweight intent parsing, keyword classification, sub-second routing |
| **`coder`** | `qwen2.5-coder:3b` | 3.1B | Q4_K_M | 1.93 GB | Python automation scripting, sandbox script generation, syntax validation |
| **`reasoning`** | `deepseek-r1:7b` | 7.6B | Q4_K_M | 4.68 GB | Deep multi-step engineering analysis, recommendation synthesis, chain-of-thought |
| **`vision`** | `qwen2.5vl:3b` | 3.8B | Q4_K_M | 3.20 GB | P&ID schematic understanding, symbol/tag extraction, visual geometry parsing |
| **`embedding`** | `nomic-embed-text:latest` | 137M | F16 | 274 MB | Primary dense semantic vector retrieval over MRPL SOPs (768 dimensions) |
| **`embedding2`** | `bge-m3:latest` | 567M | F16 | 1.16 GB | Secondary multi-lingual/multi-granularity semantic retrieval (1,024 dimensions) |

### 3.2 Hardware Tiers & Memory Budgeting (`models/configs/model_tiers.yaml`)

- **`dev` Profile (Current Baseline):**
  - Target: RTX 4060 Laptop (8 GB VRAM, 16 GB RAM)
  - `vram_budget_gb`: `8.0`
  - `max_concurrent_models`: `1` (Serial swapping via `asyncio.Semaphore(1)`)
  - `swap_keep_alive`: `"0m"` (Immediate VRAM release after invocation)
  - Embedding offloaded to CPU device to preserve 100% of GPU VRAM for LLM generation.
- **`target` Profile (Lab Server / Edge Node):**
  - Target: Workstation with 24 GB – 48 GB VRAM (RTX 4090 / A5000 / A6000)
  - `vram_budget_gb`: `24.0`
  - `max_concurrent_models`: `3` (Concurrent colocation with PagedAttention)
  - `swap_keep_alive`: `"60m"`

### 3.3 Dynamic Model Resolution Architecture
Applications and UI components never hardcode strings like `qwen2.5vl:3b`. Instead:
1. `RuleRouter` classifies tasks into abstract `ModelRole` enums (`ROUTER`, `CODER`, `REASONING`, `VISION`, `EMBEDDING`).
2. `ModelManager` queries `model_tiers.yaml` to resolve the role into a configured tag.
3. `OllamaAdapter._resolve_model_tag()` normalizes hyphenation/underscores against live `GET /api/tags`, transparently binding aliases (e.g., `qwen2.5-vl:3b` $\rightarrow$ `qwen2.5vl:3b`).

---

# 4. The 11 Operational Pipeline Stages

Every end-to-end task runs through an autonomous, monitored 11-stage workflow orchestrated by `CorrosionAuditWorkflow`:

| Step | Stage Identifier | Service / Class | Operation Executed | Failure Mode / Invariant |
|:---:|:---|:---|:---|:---|
| **0** | `document_ingestion` | `IngestionService` | Extracts text, tables, and calculates SHA-256 digest of input PDF/image | Rejects corrupt or missing bytes (`FAILED`, 0 deliverables) |
| **1** | `ocr_vision_analysis` | `VisionEngine` | Sends image bytes to `qwen2.5vl:3b`; extracts equipment, instruments, and geometries | In LIVE mode, fails closed if Ollama unreachable (`FAILED`) |
| **2** | `task_routing` | `RuleRouter` | Categorizes intent into `TaskType` and `ModelRole` using deterministic rules | Returns audit-logged match evidence and confidence score |
| **3** | `model_allocation` | `ModelManager` | Verifies model tier slots, VRAM headroom, and allocates inference provider | Enforces serial semaphore lock on 8 GB profile |
| **4** | `knowledge_retrieval` | `SovereignRetriever` | Computes dense embedding and queries local vector index of MRPL standards | Attaches verbatim page/chunk provenance to findings |
| **5** | `agent_orchestration` | `AgentStateMachineOrchestrator` | Runs 11-state autonomous reasoning loop: Plan $\rightarrow$ Act $\rightarrow$ Observe $\rightarrow$ Reflect | Step timeout (45s), global workflow timeout (120s) |
| **6** | `sandboxed_calculation` | `SubprocessSandboxExecutor` | Executes deterministic Python tool (`corrosion_rate_calc`) in isolated subprocess | Zero `eval()` or `exec()`; strict Pydantic typed I/O |
| **7** | `engineering_validation_gate` | `StructuredOutputService` | Evaluates 12 engineering math and schema rules against calculated results | **Fail-closed:** Rejects deliverable compile if any check fails |
| **8** | `deliverables_factory` | `DeliverablesFactory` | Compiles publication-quality `.docx` memorandum and `.xlsx` calculation sheet | Validates ZIP header and internal XML archive structures |
| **9** | `audit_chain_verification` | `AuditService` | Records append-only events and validates unbroken SHA-256 hash chaining | Verifies tamper-evident cryptographic integrity |
| **10**| `sovereignty_verification` | `RuntimeNetworkMonitor` | Queries OS socket tables; asserts zero non-loopback connections | **Fail-closed:** Revokes deliverables if foreign socket exists |

---

# 5. Backend Architecture & Complete REST API Reference

The backend is built with **FastAPI**, structured into modular domain services under `backend/app/services/` and exposed via versioned endpoints under `/api/v1`.

### 5.1 Base Configuration & Environment
- **Root URL:** `http://127.0.0.1:8000/api/v1`
- **CORS Policy:** Restricted to `http://localhost:5173` and `http://127.0.0.1:5173`.
- **Timeout Defaults:** 120s overall task timeout, 45s single-step tool timeout.

### 5.2 Complete API Endpoints

#### A. Health & Sovereignty Probes
- **`GET /api/v1/health`**
  - *Description:* Gateway health probe verifying loopback binding.
  - *Response:* `{"status": "ok", "app": "SIH26117 Sovereign Workbench", "version": "0.1.0", "air_gapped": true}`
- **`GET /api/v1/system/status`**
  - *Description:* Host telemetry (CPU, RAM, disk, network isolation).
  - *Response:* `SystemStatusResponse` (host metrics and loopback connection verification).

#### B. Model Manager & Tier Discovery
- **`GET /api/v1/models/health`**
  - *Description:* Checks whether local Ollama daemon is reachable on `127.0.0.1:11434`.
  - *Response:* `{"healthy": true, "provider": "ollama", "message": "Backend is responsive."}`
- **`GET /api/v1/models`**
  - *Description:* Returns catalogue of all discovered local models.
  - *Response:* `ModelListResponse` (array of `ModelInfoSchema`: tag, provider, quantization, capabilities).
- **`GET /api/v1/models/tier`**
  - *Description:* Returns the active hardware tier configuration (`dev` or `target`) and role mappings.
  - *Response:* `TierConfigResponse`:
    ```json
    {
      "tier_name": "dev",
      "description": "Laptop Development Profile (RTX 4060, 8 GB VRAM, 16 GB RAM)",
      "vram_budget_gb": 8.0,
      "max_concurrent_models": 1,
      "models": [
        {"role": "router", "provider": "ollama", "model_tag": "qwen2.5:1.5b", "context_window": 4096},
        {"role": "reasoning", "provider": "ollama", "model_tag": "deepseek-r1:7b", "context_window": 8192},
        {"role": "coder", "provider": "ollama", "model_tag": "qwen2.5-coder:3b", "context_window": 8192},
        {"role": "vision", "provider": "ollama", "model_tag": "qwen2.5vl:3b", "context_window": 4096},
        {"role": "embedding", "provider": "local", "model_tag": "nomic-embed-text", "device": "cpu"}
      ]
    }
    ```

#### C. Task Router
- **`POST /api/v1/router/route`**
  - *Payload:* `{"task": "Analyze corrosion in overhead column C-101", "context": {}}`
  - *Response:* `RoutingDecisionResponse` (derived `task_type`, `model_role`, `capability`, `confidence`, `matched_rules`).

#### D. Document Ingestion
- **`POST /api/v1/files/upload`** (Multipart Form: `file`)
  - *Response:* `DocumentIngestionResult` (`document_id`, `filename`, `sha256`, `pages`, `tables`, `is_scanned`).
- **`GET /api/v1/files/{document_id}`**
  - *Response:* Returns parsed document JSON structure with page geometries and extracted tables.

#### E. Sovereign RAG Knowledge
- **`GET /api/v1/rag/status`**
  - *Response:* `RAGStatusResponse` (`indexed_documents`, `total_chunks`, `embedding_dimension`, `vector_index_path`).
- **`POST /api/v1/rag/query`**
  - *Payload:* `{"query": "API 570 retirement thickness formula", "top_k": 3, "similarity_threshold": 0.65}`
  - *Response:* `RAGQueryResponse` (array of `RetrievedChunk` with verbatim text, page number, and source filename).

#### F. Autonomous Agent Orchestrator
- **`POST /api/v1/agent/task`**
  - *Payload:* `{"task": "Execute corrosion audit on C-101", "max_steps": 8}`
  - *Response:* `AgentTaskResponse` (`task_id`, `state`, `steps`, `deliverables`, `validation_result`).

#### G. Deterministic Office Deliverables
- **`GET /api/v1/deliverables`**
  - *Response:* List of generated deliverables across tasks.
- **`GET /api/v1/deliverables/{artifact_id}/download`**
  - *Response:* Binary file stream (`application/vnd.openxmlformats-officedocument...`) for download.

#### H. Cryptographic Audit & Sovereignty
- **`GET /api/v1/audit/events`** (Query: `limit=50&offset=0`)
  - *Response:* Array of `AuditEvent` (`event_id`, `timestamp`, `event_type`, `action`, `previous_hash`, `event_hash`).
- **`GET /api/v1/audit/verify`**
  - *Response:* `{"valid": true, "events_checked": 1723, "first_invalid_index": null, "error_detail": null}`
- **`GET /api/v1/audit/sovereignty`**
  - *Response:* `SovereigntyStatus` (`status: "PASS"`, `external_connections_observed: false`, `violations: []`).

#### I. End-to-End North-Star Workflow
- **`POST /api/v1/workflows/corrosion-audit`** (Multipart Form)
  - *Parameters:*
    - `objective` (string): Audit goal description.
    - `mode` (string): `"deterministic"` or `"live"`.
    - `component_id` (string): Equipment tag (default: `"C-101"`).
    - `file` (optional binary): Uploaded PDF or schematic image.
  - *Response:* `CorrosionAuditWorkflowResult` (complete 11-stage telemetry package with calculation, validation, deliverables, audit, and sovereignty proof).

---

# 6. Complete Frontend Architecture & UI Redesign Specification

This section provides the **exact specifications, design tokens, data contracts, and component architecture** needed to understand or completely redesign the frontend interface.

### 6.1 Industrial Design System & Design Tokens

The styling architecture is encapsulated in `frontend/src/styles/workbench.css` using pure **Vanilla CSS custom properties** (zero Tailwind dependencies):

```css
:root {
  /* Surfaces & Backgrounds */
  --bg-app: #f8fafc;              /* Slate-50: Main application canvas */
  --bg-surface: #ffffff;          /* Pure White: Card surfaces, panels */
  --bg-surface-muted: #f1f5f9;    /* Slate-100: Table headers, toolbars */
  --bg-surface-hover: #e2e8f0;    /* Slate-200: Interactive hover states */
  --bg-surface-active: #cbd5e1;   /* Slate-300: Selected items */

  /* Borders & Dividers */
  --border-subtle: #e2e8f0;       /* Fine separator lines */
  --border-medium: #cbd5e1;       /* Component bounding borders */
  --border-strong: #94a3b8;       /* Emphasized inputs and active tabs */

  /* Typography & Text */
  --text-primary: #0f172a;        /* Slate-900: High-contrast headings */
  --text-secondary: #334155;      /* Slate-700: Body copy, table cells */
  --text-muted: #64748b;          /* Slate-500: Metadata, timestamps */
  --text-light: #94a3b8;          /* Slate-400: Placeholder text */
  --text-inverse: #ffffff;        /* White text for badges/buttons */

  /* Corporate Industrial Accents (MRPL Brand Palette) */
  --accent-primary: #1e3a8a;       /* Blue-900: Deep Refinery Navy */
  --accent-primary-hover: #1e40af; /* Blue-800: Button hover */
  --accent-secondary: #0284c7;     /* Sky-600: Highlights, active indicators */

  /* Restrained Industrial Status Tokens */
  --status-success-bg: #ecfdf5;
  --status-success-border: #a7f3d0;
  --status-success-text: #065f46;
  --status-success-dot: #059669;

  --status-warning-bg: #fffbeb;
  --status-warning-border: #fde68a;
  --status-warning-text: #92400e;
  --status-warning-dot: #d97706;

  --status-error-bg: #fef2f2;
  --status-error-border: #fecaca;
  --status-error-text: #991b1b;
  --status-error-dot: #dc2626;

  --status-info-bg: #f0f9ff;
  --status-info-border: #bae6fd;
  --status-info-text: #075985;
  --status-info-dot: #0284c7;

  /* Typography Stacks */
  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
  --font-mono: 'SF Mono', Menlo, Monaco, Consolas, monospace;

  /* Elevation & Geometry */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --shadow-sm: 0 1px 2px 0 rgba(15, 23, 42, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(15, 23, 42, 0.08);
}
```

---

### 6.2 Complete TypeScript Type Contracts

The frontend types represent the definitive contracts between frontend and backend:

#### A. Agent & Workflow Types (`frontend/src/types/agent.ts`)
```typescript
export type AgentState =
  | 'IDLE'
  | 'INITIALIZING'
  | 'ANALYZING'
  | 'ROUTING'
  | 'RETRIEVING'
  | 'REASONING'
  | 'EXECUTING_TOOL'
  | 'OBSERVING'
  | 'EVALUATING'
  | 'VALIDATING'
  | 'GENERATING_OUTPUT'
  | 'COMPLETED'
  | 'FAILED'
  | 'PAUSED';

export interface AgentStepTrace {
  step_number: number;
  state: AgentState;
  thought: string;
  action?: string;
  action_input?: Record<string, any>;
  observation?: string;
  timestamp: string;
  duration_ms: number;
}

export interface WallThicknessMeasurement {
  value_mm: number;
  measurement_date: string;
  location_tag: string;
}

export interface CorrosionCalculation {
  metal_loss_mm: number;
  elapsed_time_years: number;
  corrosion_rate_mm_per_year: number;
  remaining_life_years: number;
  minimum_thickness_mm: number;
  formula_used: string;
}

export interface CorrosionAuditResult {
  task_id: string;
  equipment_id: string;
  inspection_subject: string;
  current_measurement: WallThicknessMeasurement;
  initial_measurement: WallThicknessMeasurement;
  minimum_required_thickness_mm: number;
  calculation: CorrosionCalculation;
  findings: Array<{
    finding_id: string;
    description: string;
    severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    supporting_citation?: any;
  }>;
  conclusion: string;
  recommendation: 'CONTINUE_SERVICE' | 'REPAIR_REQUIRED' | 'IMMEDIATE_SHUTDOWN';
  citations: Array<{
    source_document: string;
    page_number: number;
    chunk_id?: string;
    text?: string;
  }>;
  confidence: number;
}
```

#### B. Deliverables Types (`frontend/src/types/deliverables.ts`)
```typescript
export interface GeneratedArtifact {
  artifact_id: string;
  format: 'docx' | 'xlsx' | 'pptx';
  filename: string;
  relative_path: string;
  file_size_bytes: number;
  sha256_hash: string;
  created_at: string;
  download_url: string;
}
```

#### C. Cryptographic Audit Types (`frontend/src/types/audit.ts`)
```typescript
export type AuditEventType =
  | 'TASK_STARTED'
  | 'TASK_COMPLETED'
  | 'TASK_FAILED'
  | 'TOOL_INVOKED'
  | 'TOOL_RESULT'
  | 'MODEL_ROUTED'
  | 'MODEL_INVOKED'
  | 'DOCUMENT_INGESTED'
  | 'VALIDATION_PASSED'
  | 'VALIDATION_FAILED'
  | 'DELIVERABLE_GENERATED'
  | 'SOVEREIGNTY_VIOLATION'
  | 'LEDGER_VERIFIED';

export interface AuditEvent {
  event_id: string;
  timestamp: string;
  event_type: AuditEventType;
  action: string;
  actor: string;
  task_id?: string;
  status: 'SUCCESS' | 'FAILED' | 'WARNING';
  duration_ms?: number;
  message?: string;
  metadata: Record<string, any>;
  previous_hash: string;
  event_hash: string;
}

export interface SovereigntyStatus {
  status: 'PASS' | 'FAIL';
  local_mode_enabled: boolean;
  external_connections_observed: boolean;
  violations: string[];
  checked_at: string;
}
```

---

### 6.3 Frontend State Management & Hooks

#### A. Task Execution Hook (`frontend/src/hooks/useAgentTask.ts`)
Manages task initiation, live vs. deterministic mode toggling, progress telemetry, and state aggregation:
```typescript
export function useAgentTask() {
  const [state, setState] = useState<AgentWorkbenchState>({
    taskId: null,
    currentState: 'IDLE',
    stepTraces: [],
    auditResult: null,
    artifacts: [],
    citations: [],
    errors: [],
    isRunning: false,
    durationSeconds: 0,
  });

  const executeTask = async (
    taskText: string,
    maxSteps = 8,
    mode: 'deterministic' | 'live' = 'deterministic',
    componentId = 'C-101'
  ) => {
    // In LIVE mode: calls agentService.runWorkflow() executing POST /workflows/corrosion-audit
    // In DETERMINISTIC mode: calls agentService.runTask() executing POST /agent/task
  };

  return { ...state, executeTask, resetTask };
}
```

#### B. Sovereignty Monitoring Hook (`frontend/src/hooks/useSovereignty.ts`)
Polls `/api/v1/audit/sovereignty` every 5 seconds, exposing live air-gap health:
```typescript
export function useSovereignty(pollIntervalMs = 5000) {
  const [status, setStatus] = useState<SovereigntyStatus | null>(null);
  const [isLoopbackOnly, setIsLoopbackOnly] = useState(true);
  const [activeModel, setActiveModel] = useState<string>('Local Model');
  // Polls backend safely; updates status badges across the UI
  return { status, isLoopbackOnly, activeModel, refresh };
}
```

---

### 6.4 Page-by-Page Specifications & Layout Blueprint

The UI features a master top header bar and 6 primary full-screen views rendered via `Navigation.tsx`:

#### 1. Top Header & Sovereignty Bar (`SovereigntyBar.tsx`)
- **Left:** Sponsoring logo badge: `MRPL | SIH26117`. Title: `Sovereign On-Premise AI Workbench`.
- **Center:** Navigation Tabs: `Workbench`, `Documents`, `Knowledge (RAG)`, `Models`, `Audit Ledger`, `Sovereignty`.
- **Right:**
  - Air-gap badge: Green pill `AIR-GAP: VERIFIED` (`127.0.0.1 Loopback Only`).
  - Active Model Badge: `Model: qwen2.5vl:3b` / `deepseek-r1:7b`.
  - Refresh and settings triggers.

#### 2. Primary Workbench (`WorkbenchPage.tsx`) — *3-Column Engineering Layout*
- **Top Control Bar:**
  - Task Presets Dropdown (`C-101 Corrosion Audit`, `API 570 Retirement Thickness Check`, `NDT Ingestion`).
  - Task Objective Input box.
  - **Execution Mode Selector:** Dropdown between `Deterministic` and `Live Local Model`.
  - Max Steps selector (`4`, `8`, `12`).
  - `Run Task` Button with spinner state.
- **Dynamic Live Local Banner (when Live mode is selected):**
  - Blue glassmorphic banner displaying: `LIVE LOCAL MODEL` | `Provider: Ollama` | `Model: {dynamically fetched model}` | `127.0.0.1 (On-Prem Sovereign)`.
- **Column 1: Source Document Viewer (`DocumentViewer.tsx`)**
  - Document switcher (`corrosion_inspection_c101.pdf`, `pid_sample.png`).
  - Document metadata: SHA-256 fingerprint, page count, table count.
  - Interactive ultrasonic thickness survey data table.
  - Extracted engineering parameters card.
- **Column 2: Evidence & Validation Panel (`EvidencePanel.tsx`)**
  - Real-time Intent Routing card: Detected Task Type, Target Capability, Model Role, Confidence score.
  - Sovereign RAG Citations: Verbatim excerpts from `SOP-MRPL-PIP-001` with page provenance badges.
  - Engineering Validation Gate: 12-check badge list (Schema, bounds, tolerances, monotonicity).
- **Column 3: Agent Lifecycle & Deliverables (`AgentGraphTrace.tsx` & `DeliverablesPanel.tsx`)**
  - Top: Agent state transition sequence (Plan $\rightarrow$ Act $\rightarrow$ Observe $\rightarrow$ Reflect $\rightarrow$ Validate).
  - Bottom: Native deliverable artifact cards (`.docx` and `.xlsx`), file sizes, SHA-256 hashes, and direct download buttons.

#### 3. Documents Page (`DocumentsPage.tsx`)
- Secure drag-and-drop document upload area.
- Ingested files table: Filename, Document ID, SHA-256 digest, File type, Parsing status (`PARSED`), Actions.

#### 4. Knowledge Store Page (`KnowledgePage.tsx`)
- Vector database statistics: Total indexed chunks, vector dimension (768), similarity metric (Cosine).
- Interactive vector search test bench: Input query, adjust top-K and similarity thresholds, inspect raw retrieved chunks.

#### 5. Models Management Page (`ModelsPage.tsx`)
- Hardware tier card: Active profile (`dev`), VRAM budget (`8.0 GB`), Max concurrent (`1`).
- Role assignment grid: Cards for `router`, `reasoning`, `coder`, `vision`, `embedding`.
- Discovered Ollama models table: Tag, size on disk, quantization level, capabilities flags (`vision`, `tools`, `thinking`).

#### 6. Audit Ledger Page (`AuditPage.tsx`)
- Ledger integrity card: Verification status (`VERIFIED VALID`), total sequential events, cryptographic check button.
- Real-time event table: Event ID, timestamp, event type, action taken, actor, SHA-256 event hash.

#### 7. Sovereignty Page (`SovereigntyPage.tsx`)
- Network isolation summary: Active sockets count, non-loopback connections (`0`), foreign IP connections (`0`).
- Local provider compliance audit: Verifies `127.0.0.1:11434` binding and asserts physical/logical air-gap integrity.

---

### 6.5 Component Architecture & Hierarchy Tree

```
<App>
  ├── <SovereigntyBar>              (Persistent header with air-gap & model badge)
  ├── <Navigation>                  (Tab switcher: Workbench, Docs, RAG, Models, Audit, Sov)
  └── <MainContent>
       ├── <WorkbenchPage>
       │    ├── <PresetSelector>
       │    ├── <ExecutionModeBanner> (Dynamic Live Model vs Deterministic Indicator)
       │    ├── <TaskControls>
       │    └── <WorkbenchGrid> (3-Column Layout)
       │         ├── <DocumentViewer>     (Source PDF/P&ID inspection & NDT tables)
       │         ├── <EvidencePanel>       (Router intent, RAG citations, validation gate)
       │         ├── <AgentGraphTrace>     (State machine timeline & tool executions)
       │         └── <DeliverablesPanel>   (Branded DOCX/XLSX download cards)
       ├── <DocumentsPage>
       │    ├── <FileUploadZone>
       │    └── <DocumentsTable>
       ├── <KnowledgePage>
       │    ├── <VectorStoreStats>
       │    └── <SemanticSearchTester>
       ├── <ModelsPage>
       │    ├── <HardwareTierSummary>
       │    └── <ModelRolesGrid>
       ├── <AuditPage>
       │    ├── <LedgerVerificationBanner>
       │    └── <AuditEventsTable>
       └── <SovereigntyPage>
            ├── <SocketMonitorCard>
            └── <ProviderAuditList>
```

---

### 6.6 Frontend Redesign Guidelines & UI Modernization Blueprint

If redesigning the frontend (e.g., modernizing aesthetics, implementing Dark Mode, or migrating to Next.js), follow these authoritative design rules:

1. **Retain the 3-Column Workbench Paradigm:**
   Refinery engineers must see the **Source Evidence (left)**, the **Reasoning & Validation (center)**, and the **Finished Deliverables (right)** simultaneously. Do not collapse these into multi-page wizards.

2. **Never Hardcode Model Names in UI Elements:**
   Always query `systemService.getModelTier()`. The vision banner must read `Model: {configuredVisionModel}` so that switching models in `model_tiers.yaml` updates the UI automatically.

3. **Restrained Engineering Color Semantics:**
   - **Primary:** Deep Industrial Navy (`#1e3a8a` / `#0f172a`).
   - **Accent:** Technical Cyan (`#0284c7`).
   - **Success (Validation Passed):** Emerald Green (`#059669`).
   - **Error / Fail-Closed:** Crimson Red (`#dc2626`).
   - **Warning:** Amber (`#d97706`).
   - Avoid saturated neon gradients or decorative animations that distract from technical readability.

4. **Typography Consistency:**
   - Primary interface: `Inter` or system sans-serif.
   - Engineering metrics, tags, formulas, hashes, and code: Monospace (`SF Mono`, `Menlo`, `Consolas`).

5. **Expose Sovereignty & Validation Evidences at all times:**
   Judges and refinery auditors look for the `AIR-GAP: VERIFIED` badge and the `12/12 CHECKS PASSED` validation gate. Keep these permanently visible in the viewport.

---

# 7. Primary Industrial Demonstration Scenario (Refinery Asset C-101)

### 7.1 Asset & Inspection Profile
- **Asset ID:** `C-101`
- **Asset Name:** Atmospheric Distillation Column Overhead Condenser Piping System
- **Location:** Crude Distillation Unit (CDU-1), Mangalore Refinery Complex
- **Governing Standard:** `API 570` (Piping Inspection Code) / MRPL Standard `SOP-MRPL-PIP-001`
- **Material:** Carbon Steel ASTM A106 Grade B (Class 150)
- **Baseline Wall Thickness ($t_{\text{nominal}}$):** `12.00 mm` (commissioned 2021)
- **Current Minimum Thickness ($t_{\text{actual}}$):** `10.10 mm` (measured March 2026 at CML-4)
- **Minimum Retirement Thickness ($t_{\text{min}}$):** `8.00 mm`

### 7.2 Deterministic Mathematical Execution
All calculations are computed deterministically inside the sandbox subprocess using strict engineering formulas:

1. **Metal Loss ($\Delta t$):**
   $$\Delta t = t_{\text{initial}} - t_{\text{actual}} = 12.00\,\text{mm} - 10.10\,\text{mm} = 1.90\,\text{mm}$$
2. **Elapsed Service Time ($T$):**
   $$T = 2026.20 - 2021.20 = 5.00\,\text{years}$$
3. **Corrosion Rate ($CR$):**
   $$CR = \frac{\Delta t}{T} = \frac{1.90\,\text{mm}}{5.00\,\text{years}} = 0.380\,\text{mm/year}$$
4. **Remaining Corrosion Margin ($M$):**
   $$M = t_{\text{actual}} - t_{\text{min}} = 10.10\,\text{mm} - 8.00\,\text{mm} = +2.10\,\text{mm}$$
5. **Estimated Remaining Service Life ($RSL$):**
   $$RSL = \frac{t_{\text{actual}} - t_{\text{min}}}{CR} = \frac{2.10\,\text{mm}}{0.380\,\text{mm/year}} = 5.526\,\text{years} \approx 5.53\,\text{years}$$
6. **Statutory Inspection Interval ($I_{\text{next}}$ per API 570):**
   $$I_{\text{next}} = \min\left(5\,\text{years},\, \frac{RSL}{2}\right) = \frac{5.53}{2} = 2.76\,\text{years}$$
7. **Recommendation Code:** `CONTINUE_SERVICE` with re-inspection mandated prior to September 2028.

### 7.3 Structured Engineering Validation Gate (12 Rules)
Before deliverables can be built, `StructuredOutputService` validates the data structure against 12 strict rules:
1. Schema conformity to `CorrosionAuditResult`.
2. Required fields present: `equipment_id`, `current_measurement`, `initial_measurement`, `calculation`.
3. Non-negative thickness constraint ($t > 0$).
4. Baseline monotonicity ($t_{\text{actual}} \le t_{\text{nominal}}$).
5. Retirement threshold check ($t_{\text{actual}} > t_{\text{min}}$).
6. Metal loss numerical consistency ($\Delta t = t_{\text{initial}} - t_{\text{actual}} \pm 0.01$).
7. Elapsed time positivity ($T > 0$).
8. Corrosion rate formula check ($CR = \Delta t / T \pm 0.001$).
9. Remaining life formula check ($RSL = (t_{\text{actual}} - t_{\text{min}}) / CR \pm 0.01$).
10. Valid recommendation enum mapping (`CONTINUE_SERVICE`).
11. Verbatim RAG source citation attached (`SOP-MRPL-PIP-001.pdf`, Page 3).
12. Minimum confidence threshold ($\ge 0.85$).

---

# 8. Empirical Benchmarks & Performance Telemetry

The following execution metrics were captured during verified, non-simulated live runs on the baseline hardware (NVIDIA RTX 4060 8 GB VRAM, Intel Core i7, 16 GB RAM, Windows 11):

### 8.1 Live Model Latency Breakdown

| Subsystem / Operation | Model / Engine Used | Device / Mode | Wall-Clock Latency |
|:---|:---|:---|:---|
| **Document Ingestion (SHA-256 + PDF Parse)** | Pure Python / PDFMiner | CPU | `15.0 ms` |
| **VLM Schematic Inspection (P&ID Analysis)** | `qwen2.5vl:3b` | GPU (Ollama) | **`13.72 s`** |
| **Task Intent Classification** | `RuleRouter` (Level 0) | CPU | `16.0 ms` |
| **Model Role Allocation & Semaphores** | `ModelManager` | CPU | `< 1.0 ms` |
| **Sovereign RAG Dense Retrieval** | `nomic-embed-text` | CPU (Loopback) | `15.0 ms` |
| **Agent State Machine Lifecycle (11 states)** | `AgentStateMachineOrchestrator`| CPU / In-Process | `172.0 ms` |
| **Sandboxed Mathematical Calculation** | Subprocess Python Sandbox | Isolated Process | `1.50 s` |
| **Structured Output Validation Gate** | `StructuredOutputService` | CPU | `< 1.0 ms` |
| **Office Deliverables Factory (.docx + .xlsx)**| `DeliverablesFactory` (ZIP/XML) | CPU | `235.0 ms` |
| **Cryptographic Audit Ledger (Append & Verify)**| `AuditService` (SHA-256 Chain) | CPU / Disk | `125.0 ms` |
| **Runtime Network Sovereignty Audit** | `RuntimeNetworkMonitor` (Sockets)| Host OS Table | `< 1.0 ms` |
| **Total End-to-End Execution Time** | Full 11-Stage Workflow | **LIVE LOCAL** | **`15.81 s`** |

*(Deterministic mode executes the identical call graph with mock vision in `< 2.0 s` total)*

### 8.2 Sequential Model Swapping Benchmarks (8 GB VRAM Constraint)

| Transition Sequence | Source Model $\rightarrow$ Target Model | Unload Status | Load & Inference Time | Peak VRAM |
|:---|:---|:---|:---|:---|
| **Step 1: Router** | Idle $\rightarrow$ `qwen2.5:1.5b` | Released | `0.09 s` | 1.1 GB |
| **Step 2: Coder** | `qwen2.5:1.5b` $\rightarrow$ `qwen2.5-coder:3b` | Unloaded | `5.05 s` | 2.1 GB |
| **Step 3: Vision** | `qwen2.5-coder:3b` $\rightarrow$ `qwen2.5vl:3b` | Unloaded | `19.56 s` | 3.4 GB |
| **Step 4: Reasoning**| `qwen2.5vl:3b` $\rightarrow$ `deepseek-r1:7b` | Unloaded | `36.05 s` | 4.8 GB |

*Empirical Result:* Zero Out-Of-Memory (OOM) errors encountered during serial model transitions.

---

# 9. Failure Safety & Security Invariants

The workbench enforces five non-negotiable failure-safety invariants verified by automated regression tests:

```
                  ┌────────────────────────────────────────────────────────┐
                  │                 INCOMING TASK / DATA                   │
                  └───────────────────────────┬────────────────────────────┘
                                              │
                                              ▼
                             [Safety Gate A: Provider Liveness]
                             Is local Ollama responsive on 127.0.0.1?
                                              │
                                     NO ──────┴────── YES
                                     │                 │
                           [ABORT & FAIL CLOSED]       ▼
                           (0 deliverables)   [Safety Gate B: Input Integrity]
                                              Is document readable & uncorrupted?
                                                       │
                                              NO ──────┴────── YES
                                              │                 │
                                    [ABORT & FAIL CLOSED]       ▼
                                    (0 deliverables)   [Safety Gate C: Mathematical Sandbox]
                                                       Did sandbox math compute valid numbers?
                                                                │
                                                       NO ──────┴────── YES
                                                       │                 │
                                             [ABORT & FAIL CLOSED]       ▼
                                             (0 deliverables)   [Safety Gate D: Validation Gate]
                                                                Did all 12 engineering rules pass?
                                                                         │
                                                                NO ──────┴────── YES
                                                                │                 │
                                                      [ABORT & FAIL CLOSED]       ▼
                                                      (0 deliverables)   [Safety Gate E: Sovereignty Proof]
                                                                         Are foreign connections == 0?
                                                                                  │
                                                                         NO ──────┴────── YES
                                                                         │                 │
                                                               [REVOKE DELIVERABLES]       ▼
                                                               (Fail Closed)      [RELEASE DELIVERABLES]
                                                                                  (DOCX + XLSX Emitted)
```

### Verified Test Cases (`backend/tests/test_phase16_hardening.py`):
1. **Case A (Ollama Unavailable):** In `LIVE` mode, an unreachable Ollama daemon immediately transitions workflow to `FAILED`. Zero mock fallback. Zero deliverables emitted.
2. **Case B (Invalid VLM / Mathematical Output):** If visual extraction or math violates constraints, validation transitions to `VALIDATION_FAILED`. Deliverables strictly withheld.
3. **Case C (Missing Input):** Missing or corrupted files raise structured `DocumentIngestionStageError`. Execution stops cleanly.
4. **Case D (Sovereignty Violation):** Detection of an unauthorized non-loopback socket triggers `IntegrationError`, revoking all compiled deliverables.
5. **Case E (Valid Execution):** Complete 11-stage workflow succeeds, generating signed `.docx` and `.xlsx` artifacts.

---

# 10. Single-Command Execution & Developer Runbook

### 10.1 System Prerequisites
- **OS:** Windows 11 / Linux (Ubuntu 22.04+)
- **Python:** Version 3.11+
- **Node.js:** Version 20+
- **Ollama:** Running on `http://127.0.0.1:11434` with resident models:
  - `ollama pull qwen2.5vl:3b`
  - `ollama pull deepseek-r1:7b`
  - `ollama pull qwen2.5-coder:3b`
  - `ollama pull qwen2.5:1.5b`
  - `ollama pull nomic-embed-text`

### 10.2 Starting Development & Demonstration Servers
1. **Start Backend Server:**
   ```powershell
   $env:PYTHONPATH='backend'
   # Run without --reload to preserve WindowsProactorEventLoopPolicy for deterministic subprocess sandbox execution:
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. **Start Frontend Dev Server:**
   ```powershell
   cd frontend
   npm run dev
   # Accessible at http://127.0.0.1:5173
   ```

### 10.3 Running the Official North-Star Demonstration Runner
Execute the unified, presentation-ready single-command demonstrator:
```powershell
$env:PYTHONPATH='backend'
python scripts/run_demo.py --mode live
```
*(Executes real `qwen2.5vl:3b` inference, 11-stage workflow, sandbox math, validation, and emits `.docx` and `.xlsx` in `outputs/`)*

### 10.4 Running Automated Verification & Regression Suites
1. **Full Backend Regression Suite (434 tests):**
   ```powershell
   $env:PYTHONPATH='backend'
   python -m pytest backend/tests/ -q
   ```
   *Expected Output: `434 passed in ~42s` (100% pass rate across Phases 1–16)*

2. **Frontend Production Build Check:**
   ```powershell
   npm --prefix frontend run build
   ```
   *Expected Output: `✓ built in ~3s` (0 TypeScript / bundling errors)*

---

# Summary of Project Truth & Frozen Baselines

- **Phase 1–16 Status:** **100% COMPLETE & FROZEN**
- **Repository Commit:** `4e788c1` (*Declutter project: remove redundant draft plan markdown files*)
- **Regression Pass Rate:** **434 / 434 (100%)**
- **Frontend Production Build:** **PASS**
- **Air-Gap Compliance:** **127.0.0.1 Loopback Only, 0 Foreign Sockets**
- **North-Star Demonstrator:** `scripts/run_demo.py`
