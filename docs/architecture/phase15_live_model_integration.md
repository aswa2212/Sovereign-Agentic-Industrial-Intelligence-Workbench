# Phase 15 Architecture Specification: Live Local Model Integration

## 1. Overview & Architectural Goal

Phase 15 connects the resident on-premise Ollama vision-language model (`qwen2.5vl:3b`) directly into the production workbench architecture while strictly preserving:
1. **Zero Cloud Dependencies:** Pure on-premise execution bound to `127.0.0.1`.
2. **Frozen Contract Preservation:** No modifications to Phase 1–13 interfaces; integration accomplished via existing extension points (`**kwargs` and Pydantic schema validation).
3. **Fail-Closed Execution:** In live mode, failure or unreachability of the local model immediately halts processing and strictly forbids silent degradation to synthetic mocks.
4. **Dynamic Model Configuration:** Model identifiers are dynamically resolved from `models/configs/model_tiers.yaml` rather than hardcoded in application logic or UI components.

---

## 2. Subsystem Interaction Architecture

```
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                 CORROSION AUDIT WORKFLOW ORCHESTRATOR                    │
  │                  (app.services.integration.workflow)                    │
  └───────┬──────────────────────────────────────────────────────────┬───────┘
          │                                                          │
   [Stage 0: Ingestion]                                      [Stage 7: Validation Gate]
   Extracts bytes & metadata                                 Verifies VLM extraction bounds
          │                                                          │
   [Stage 1: VLM Vision Engine]                              [Stage 8: Deliverables]
   ModelManagerVisionProvider.analyze_schematic()            Native .docx & .xlsx generation
          │ (Passes base64 image bytes)                              │
   [ModelManager & OllamaAdapter]                            [Stage 9: Audit Ledger]
   POST /api/generate (format="json", stream=False)          Verifies unbroken hash chain
          │ (qwen2.5vl:3b on 127.0.0.1)                              │
   [Stage 2: Intent Routing]                                 [Stage 10: Sovereignty Proof]
   RuleRouter (Vision + Reasoning role matching)             Confirms 0 foreign sockets
          │                                                          │
   [Stages 3-6: RAG, Agent, Sandbox Execution] ──────────────┘
```

---

## 3. Key Architectural Components

### 3.1 Dynamic Tag Normalization (`OllamaAdapter._resolve_model_tag`)
Ollama model tags can vary in punctuation conventions across installations (e.g., `qwen2.5vl:3b` vs `qwen2.5-vl:3b`). The adapter queries `/api/tags` on initialization and dynamically normalizes target tags by stripping hyphens and underscores, mapping configured identifiers to the exact local daemon tag.

### 3.2 Multimodal Payload Forwarding
`OllamaAdapter.generate_json()` forwards multimodal visual buffers via `payload["images"] = kwargs["images"]` when provided, passing base64-encoded image data directly to Ollama's vision API without cloud leakage.

### 3.3 Robust Structured Output Parsing (`ModelManagerVisionProvider._parse_structured_response`)
VLM responses may represent equipment and instrument tags as string literals or structured dictionaries. The parser handles both representations flexibly, standardizes bounding boxes within $[0.0, 1.0]$, and enforces confidence floor thresholds before passing extracted findings to downstream validation.

### 3.4 Dual-Mode Execution in Orchestrator (`CorrosionAuditWorkflow`)
- **`DETERMINISTIC` Mode:** Fast, zero-VRAM execution for CI/CD, regression testing, and reproducible demonstrations.
- **`LIVE` Mode:** Full execution of live on-premise `qwen2.5vl:3b` inference with fail-closed error handling and audit logging.

### 3.5 Dynamic UI Model Display (`WorkbenchPage.tsx`)
The frontend workbench queries `/api/v1/system/models/tier` dynamically via `systemService.getModelTier()`. The active vision provider and model tag (`qwen2.5vl:3b`) are rendered dynamically in the Live Local Model indicator, ensuring zero hardcoded model strings in frontend components.

---

## 4. Operational Invariants

1. **Air-Gap Verification:** Live model inference communicates exclusively over the local loopback interface (`http://127.0.0.1:11434`). System telemetry confirms 0 non-loopback network connections during execution.
2. **Fail-Closed Integrity:** If Ollama is offline or encounters an unrecoverable inference error in live mode, the workflow transitions to `FAILED` and halts deliverable generation.
3. **Audit Ledger Verification:** All inference requests, model allocations, and validation events are recorded to the append-only SHA-256 hash-chained audit ledger.
