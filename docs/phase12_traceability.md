# Phase 12 Traceability Matrix: Frontend Workbench UI

This document maps every requirement specified for **Phase 12 — Frontend Workbench UI** in `docs/implementation_plan.md` to its implementation files, UI components, backend API endpoints, and test verifications.

---

## 1. Requirement Traceability Matrix

| Requirement ID | Requirement Description | Implementation Files | UI Component | Target Backend API Endpoint | Verification / Test |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **REQ-12.1** | **Sovereignty Header:** Display active local/air-gap status, 0 outbound connections, and audit chain verification | `frontend/src/components/SovereigntyBar.tsx`, `frontend/src/hooks/useSovereignty.ts` | `<SovereigntyBar />` | `GET /health`, `GET /api/v1/audit/sovereignty`, `GET /api/v1/audit/network`, `GET /api/v1/audit/integrity` | `npm run build` succeeds; verifies 0 external connections and local provider mode |
| **REQ-12.2** | **Document Upload & Inspection:** Technical document ingestion pane displaying filename, file type, processing status, SHA-256, page count, and OCR/table preview | `frontend/src/components/DocumentViewer.tsx`, `frontend/src/services/documents.ts` | `<DocumentViewer />` | `POST /api/v1/files/upload`, `GET /api/v1/files/{sha256}/status` | TypeScript compilation; drag & drop upload handler with validation |
| **REQ-12.3** | **Agent Lifecycle Visualization:** Dynamic 11-state machine timeline showing `RECEIVE` $\rightarrow$ `UNDERSTAND` $\rightarrow$ `PLAN` $\rightarrow$ `EXECUTE` $\rightarrow$ `OBSERVE` $\rightarrow$ `REFLECT` $\rightarrow$ `VALIDATE` $\rightarrow$ `FINALIZE` $\rightarrow$ `DELIVER` | `frontend/src/components/AgentGraphTrace.tsx`, `frontend/src/hooks/useAgentTask.ts` | `<AgentGraphTrace />` | `POST /api/v1/agent/run`, `GET /api/v1/agent/{task_id}` | Visual pipeline indicator with step numbers, active pulse, and transition ledger |
| **REQ-12.4** | **Routing & Model Visibility:** Display dynamically selected capability tier, model role, and routing confidence | `frontend/src/pages/WorkbenchPage.tsx`, `frontend/src/services/agent.ts` | `<WorkbenchPage />` | `POST /api/v1/router/route` | Real-time classification preview upon query typing |
| **REQ-12.5** | **Grounded Evidence Citations:** Display retrieved RAG chunks with source document, page number, chunk ID, relevance score, and excerpt | `frontend/src/components/EvidencePanel.tsx` | `<EvidencePanel />` | `POST /api/v1/agent/run` (citations payload) | Source document and page number displayed for every finding |
| **REQ-12.6** | **Deterministic Deliverables:** Cards for generated `.docx`, `.xlsx`, and `.pptx` documents with direct download links | `frontend/src/components/DeliverablesPanel.tsx`, `frontend/src/services/deliverables.ts` | `<DeliverablesPanel />` | `POST /api/v1/deliverables/generate`, `GET /api/v1/deliverables/download/{format}/{name}` | Compiles and downloads native Office files |
| **REQ-12.7** | **Audit Ledger:** Compact technical table of tamper-evident events with SHA-256 hash chaining and verify action | `frontend/src/components/AuditLedger.tsx`, `frontend/src/pages/AuditPage.tsx` | `<AuditLedger />` | `GET /api/v1/audit/events`, `GET /api/v1/audit/integrity` | Cryptographic verification button reports verified count |
| **REQ-12.8** | **Restrained Navigation & Layout:** Desktop-first industrial operator console with sidebar sections | `frontend/src/main.tsx`, `frontend/src/components/Navigation.tsx`, `frontend/src/App.tsx`, `frontend/src/styles/workbench.css` | `<Navigation />`, `<App />` | Internal Client Navigation Router | Responsive layout with clear technical styling |
| **REQ-12.9** | **Real-Time Updates & Polling Fallback:** Decoupled event transport with graceful fallback | `frontend/src/hooks/useAgentTask.ts`, `frontend/src/hooks/useSovereignty.ts` | Isolated in hooks layer | `GET /api/v1/agent/{task_id}`, `POST /api/v1/agent/run` | Non-blocking reactive updates |
| **REQ-12.10**| **Air-Gap Compliance Wording:** Exact legal/technical semantics without marketing exaggerations | `frontend/src/components/SovereigntyBar.tsx`, `frontend/src/pages/SovereigntyPage.tsx` | UI text copy | N/A | Strict adherence to deployment control wording |

---

## 2. Test & Build Verification Summary

1. **Frontend Production Build:**
   - Command: `npm run build` in `frontend/`
   - Output: `tsc && vite build` $\rightarrow$ 1489 modules transformed, 0 errors, generated `dist/index.html`, `dist/assets/index-*.css`, and `dist/assets/index-*.js`.
2. **Backend Regression Verification:**
   - Command: `$env:PYTHONPATH='backend'; python -m pytest backend/tests/ -q`
   - Output: **409 passed, 1 warning in 15.80s** (100% frozen baseline integrity).
3. **Knowledge Store Immutability:**
   - `index.npy` SHA-256: `5a6c60960431365c10c8df3ec322ba39f7266c9e040fcd3d24b68e0953781192` (unchanged)
   - `metadata.json` SHA-256: `b5990e246d51515c18dedeb415a01281c157735b487d85f5239263806da5366e` (unchanged)
   - `git diff 81f7bc1 -- backend/data/knowledge` is empty.
4. **Frozen Phase Protection:**
   - Zero files modified in `backend/`.
   - Only `frontend/` received additions and the necessary entry point wiring.
