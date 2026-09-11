# Phase 12 — Sovereign Frontend Workbench Architecture

## 1. Overview & System Mission

The **MRPL Sovereign Agentic AI Workbench UI** (Phase 12) serves as the primary operator control and verification interface for industrial plant inspection, equipment integrity analysis, and regulatory compliance workflows at Mangalore Refinery and Petrochemicals Limited (MRPL).

The frontend is strictly a **presentation and operator control layer**. In accordance with Phase 1–11 frozen baseline constraints, the frontend contains **no backend business logic**; it interfaces with the frozen FastAPI backend via normalized client service wrappers.

---

## 2. Visual Style & Design System

The interface rejects generic AI tropes (neon/purple gradients, glowing borders, robot avatars, chatbot bubble UI, AI sparkles) in favor of an **industrial engineering workstation** aesthetic:

- **Surface & Background:** Off-white/slate canvas (`#f8fafc`), clean white panels (`#ffffff`), muted technical containers (`#f1f5f9`).
- **Borders & Dividers:** Crisp, thin neutral borders (`#e2e8f0` and `#cbd5e1`).
- **Primary Accent:** Restrained industrial navy/slate-blue (`#1e3a8a`, hover `#1e40af`).
- **Typography:** Professional clean sans-serif (`Inter`, system UI stack) paired with selective monospace (`SF Mono`, `JetBrains Mono`, `Consolas`) for technical identifiers, SHA-256 hashes, equipment IDs, and timestamps.
- **Status Semantics:** Muted green for local/verified, industrial amber for warnings, restrained red for operational errors. All status indicators pair text labels with icons for accessibility.

---

## 3. Component Architecture & Responsibilities

```
frontend/src/
├── main.tsx                 # Standard React 18 / Vite entry point mounting App into #root
├── App.tsx                  # Workbench root layout component (header, sidebar, canvas)
├── components/
│   ├── SovereigntyBar.tsx       # Top persistent status header: local mode, socket count, audit verification
│   ├── Navigation.tsx           # Left sidebar navigation (WORKSPACE, EVIDENCE & ASSURANCE, SYSTEM & SECURITY)
│   ├── AgentGraphTrace.tsx      # Sequential 11-state machine timeline & transition ledger
│   ├── DocumentViewer.tsx       # Technical document ingestion dropzone, metadata rows, and OCR inspection
│   ├── EvidencePanel.tsx        # Traceable RAG citation viewer (source, page, chunk ID, relevance score)
│   ├── DeliverablesPanel.tsx    # Deterministic Office deliverables generator & direct download cards
│   └── AuditLedger.tsx          # Cryptographic tamper-evident audit ledger table with hash verification
├── pages/
│   ├── WorkbenchPage.tsx        # Primary operator demo workspace (task input, router preview, trace, deliverables)
│   ├── DocumentsPage.tsx        # Standalone document repository and extraction inspection view
│   ├── KnowledgePage.tsx        # Sovereign RAG vector store and chunk inspection view
│   ├── AuditPage.tsx            # Full-screen immutable audit ledger and SHA-256 hash-chain verification
│   ├── SovereigntyPage.tsx      # Provider enforcement, socket connection table, and isolation evidence
│   └── ModelsPage.tsx           # Local on-prem model registry and capability tier specifications
├── services/
│   ├── api.ts                   # Centralized HTTP request client with timeout, error handling, and JSON parsing
│   ├── agent.ts                 # Agent task dispatch (`/api/v1/agent/run`), status, and routing preview
│   ├── documents.ts             # File upload (`/api/v1/files/upload`) and document status queries
│   ├── audit.ts                 # Audit events, integrity verification, network observation, sovereignty check
│   ├── deliverables.ts          # Office deliverable generation (`/api/v1/deliverables/generate`) and download URLs
│   └── system.ts                # System health (`/health`), system status, and model metadata
├── hooks/
│   ├── useAgentTask.ts          # State management for task execution, routing preview, trace, and citations
│   └── useSovereignty.ts        # Polling telemetry hook for sovereignty status, socket counts, and audit integrity
├── types/                       # Strict TypeScript interfaces matching backend Pydantic schemas
└── styles/
    └── workbench.css            # Scoped design system tokens, responsive layout, cards, and tables
```

---

## 4. API Integration Map

| UI Feature / Component | Backend API Endpoint | HTTP Method | Response Schema | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Sovereignty Header** | `/health` | GET | `HealthResponse` | Basic service health & air-gap flag |
| **Sovereignty Header** | `/api/v1/audit/sovereignty` | GET | `SovereigntyCheckResponse` | Local provider check & loopback enforcement |
| **Sovereignty Header** | `/api/v1/audit/network` | GET | `NetworkObservationResponse` | Active OS socket connection report |
| **Sovereignty Header** | `/api/v1/audit/integrity` | GET | `AuditVerificationResponse` | Cryptographic hash-chain continuity check |
| **Router Preview** | `/api/v1/agent/route` | POST | `RouteResponse` | Previews capability tier, model role, & confidence |
| **Task Execution** | `/api/v1/agent/run` | POST | `AgentRunResponse` | Executes autonomous 11-state agent cycle |
| **Task Status Polling** | `/api/v1/agent/{task_id}` | GET | `AgentTaskStatusResponse` | Queries background task state & trace |
| **Document Ingestion** | `/api/v1/files/upload` | POST | `DocumentIngestionResult` | Uploads PDF/image, runs OCR & table extraction |
| **Document Status** | `/api/v1/files/{sha256}/status` | GET | `Record<string, any>` | Retrieves extraction status by SHA-256 |
| **Audit Ledger** | `/api/v1/audit/events` | GET | `AuditEventListResponse` | Paginated query over tamper-evident event log |
| **Audit Event Detail** | `/api/v1/audit/events/{id}` | GET | `AuditEventResponse` | Fetches specific event with SHA-256 links |
| **Deliverable Gen** | `/api/v1/deliverables/generate`| POST | `DeliverableGenerateResponse`| Compiles native DOCX/XLSX/PPTX |
| **Deliverable Download**| `/api/v1/deliverables/download/{format}/{name}` | GET | Binary Stream | Direct file download |

---

## 5. State Flow & Real-Time Event Transport

### SSE / Polling Fallback Architecture
The backend provides synchronous and state-tracked task execution (`POST /api/v1/agent/run` returning full execution trace, plus `GET /api/v1/agent/{task_id}`). In accordance with the prompt ("Do NOT invent an SSE endpoint. If SSE is unavailable in the existing backend, use existing task-status API, implement polling fallback, isolate event transport behind a frontend service"):
1. The frontend isolates all transport within `useAgentTask` and `useSovereignty`.
2. **`useAgentTask`:** Initiates execution, immediately transitions to `RECEIVE` state, updates trace reactively upon response, and captures errors cleanly without freezing the UI.
3. **`useSovereignty`:** Polls `/api/v1/audit/sovereignty`, `/api/v1/audit/network`, and `/api/v1/audit/integrity` every 15 seconds to ensure real-time telemetry of network isolation and hash-chain continuity.

---

## 6. Sovereignty UI Semantics & Exact Compliance Wording

To maintain strict regulatory accuracy and avoid over-promising, the workbench UI adheres to precise operational wording:

- **Local Provider Enforcement:** *"Local-only provider enforcement active. No external cloud endpoints configured."*
- **Network Observation:** *"0 non-loopback connections observed. Physical air-gap isolation remains an environment/deployment control."*
- **Tamper-Evident Ledger:** *"Cryptographic hash-chain continuity verified across sequential SHA-256 back-pointers."*
- **Avoided Terms:** The UI explicitly avoids misleading marketing phrases such as "Military Grade", "100% Secure", "Unbreakable", or "AI Super Assistant".

---

## 7. Limitations & Operational Scope

1. **Hardware Prerequisite:** Local inference requires an active on-prem Ollama daemon binding to `127.0.0.1:11434`.
2. **Deployment Control:** The software validates internal socket telemetry; true physical air-gapping requires physical network cable disconnection and firewall rules at the host level.
3. **Deterministic Output:** All Office deliverables are assembled from structured, validated JSON data schemas; LLMs do not directly generate binary files.
