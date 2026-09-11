# Phase 11 — Audit & Sovereignty Evidence Architecture

## 1. Overview & Purpose
Phase 11 introduces a local, tamper-evident audit ledger and software-level sovereignty evidence subsystem to the **SIH26117 — Sovereign Agentic Industrial Intelligence Workbench**.

The objective is to provide verifiable, reproducible, and mathematically bound evidence of:
- What tasks were executed across the autonomous lifecycle.
- Which agent state transitions and tool invocations took place.
- Which model roles and capabilities were selected by the Task Router.
- Provenance of knowledge chunks retrieved through the Sovereign RAG engine.
- Deterministic deliverable generation (DOCX, XLSX, PPTX).
- Whether the audit ledger has suffered post-hoc tampering, omission, or corruption.
- Observed runtime network connections.
- Strict locality compliance of configured AI/model provider endpoints when sovereign air-gapped mode is enabled.

---

## 2. Core Architecture & Components

```
                     ┌──────────────────────────────────────┐
                     │          Client / User API           │
                     └──────────────────┬───────────────────┘
                                        │
                                        ▼
                     ┌──────────────────────────────────────┐
                     │       FastAPI /api/v1/audit/         │
                     │  /events  /integrity  /sovereignty   │
                     └──────────────────┬───────────────────┘
                                        │
                                        ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                              AuditService                                 │
│  ├── sanitize_metadata() (Automatic secret scrubbing)                     │
│  ├── record_event() (Thread-safe sequential hash linkage)                 │
│  ├── verify_ledger()                                                      │
│  ├── observe_network()                                                    │
│  └── check_sovereignty()                                                  │
└───────┬───────────────────┬───────────────────┬───────────────────┬───────┘
        │                   │                   │                   │
        ▼                   ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  EventStore  │    │  HashChain   │    │  Integrity   │    │ Sovereignty  │
│  (JSONL log) │    │  (SHA-256)   │    │   Verifier   │    │   Checker    │
└──────────────┘    └──────────────┘    └──────────────┘    └───────┬──────┘
                                                                    │
                                                                    ▼
                                                            ┌──────────────┐
                                                            │RuntimeNetwork│
                                                            │   Monitor    │
                                                            └──────────────┘
```

### 2.1 Component Responsibilities
1. **`AuditEvent` Model (`backend/app/services/audit/models.py`)**:
   - Strongly typed Pydantic V2 schema with UUIDs, UTC ISO-8601 timestamps, controlled taxonomy `AuditEventType`, action, state, role, tool name, sanitized metadata, `previous_hash`, and `event_hash`.
2. **`LocalAuditEventStore` (`backend/app/services/audit/event_store.py`)**:
   - Thread-safe, append-only JSONL file storage (`data/audit/events.jsonl`). Immediate write flushing ensures durability. Strictly prohibits in-place editing or deletion.
3. **`HashChain` (`backend/app/services/audit/hash_chain.py`)**:
   - Deterministic canonical JSON serialization (`sort_keys=True`, `separators=(',', ':')`, UTF-8 encoded).
   - SHA-256 cryptographic chaining:
     - `Event 0: previous_hash = GENESIS_HASH`
     - `Event N: previous_hash = Event[N-1].event_hash`
     - `event_hash = SHA-256(canonical_bytes + previous_hash.encode('utf-8'))`
4. **`AuditIntegrityVerifier` (`backend/app/services/audit/integrity.py`)**:
   - Full ledger verifier checking canonical hashes, chronological ordering, and pointer continuity. Fails closed upon modification, deletion, reordering, or corruption without silent repair.
5. **`RuntimeNetworkMonitor` (`backend/app/services/audit/network_monitor.py`)**:
   - Capability-aware runtime socket observer. If `psutil` is present, inspects process sockets; otherwise utilizes standard-library socket introspection (`stdlib_socket_inspection`) without requiring external package installation or internet access.
6. **`SovereigntyChecker` (`backend/app/services/audit/sovereignty.py`)**:
   - Validates that configured model endpoints (`Ollama`, `LlamaCPP`, `vLLM`) resolve strictly to local addresses (`127.0.0.1`, `localhost`, `::1`). Rejects public IPs, external hostnames, or cloud APIs when `AIR_GAPPED_MODE` is active.

---

## 3. Secret Filtering & Privacy Preservation
To prevent credential leaks into persistent audit logs, `AuditService.record_event()` applies recursive key scrubbing:
- Fields with keys matching substrings: `api_key`, `secret`, `password`, `token`, `authorization`, `credential`, `private_key`, `access_token` are automatically replaced with `"[REDACTED]"`.
- Neither raw environment tables nor unrestrained tool inputs are ever dumped to disk.

---

## 4. Frozen-Phase Integration Boundaries
Integration with frozen phases is strictly additive, minimal, and non-intrusive:
- **Phase 7 Agent Orchestrator (`backend/app/services/agent/orchestrator.py`)**:
  - Receives optional `audit_service: Optional[AuditService] = None`.
  - When provided, logs `TASK_STARTED`, `MODEL_ROUTED`, `PLAN_CREATED`, `TOOL_STARTED`, `TOOL_COMPLETED`, `VALIDATION_STARTED`, `VALIDATION_COMPLETED`, `TASK_COMPLETED`, and `TASK_FAILED`.
  - When omitted (`None`), behaves with 100% frozen baseline fidelity (all 383 regression tests pass unchanged).
- **Phase 10 Deliverables Factory (`backend/app/services/deliverables/factory.py`)**:
  - Receives optional `audit_service: Optional[AuditService] = None`.
  - Emits `DELIVERABLE_CREATED` with safe artifact metadata upon successful generation of DOCX, XLSX, or PPTX.
- **Phase 6 RAG Engine**:
  - Can record retrieval provenance (`KNOWLEDGE_RETRIEVED`) including document filename, page number, chunk ID, and similarity score without exposing internal vector store matrices or modifying `index.npy` / `metadata.json`.

---

## 5. Network Claims & System Boundaries

### Technical Reality & Compliance Note
> [!IMPORTANT]
> **What the system proves:**
> Local-only provider enforcement and runtime network evidence were implemented and tested. The system verifies that configured endpoints are local loopback addresses and records all observable socket states.
> 
> **What the system does NOT prove:**
> The network monitor does **NOT** prove that physical air-gap isolation exists on the underlying hardware. Physical air-gap isolation remains a deployment and environmental control.
