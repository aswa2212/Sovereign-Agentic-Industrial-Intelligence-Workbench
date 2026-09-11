# Phase 13 Architecture Specification: End-to-End System Integration

## 1. Overview & Architectural Goal

Phase 13 unifies all previous subsystems into an autonomous, deterministic, fail-closed operational workflow:
$$\text{Document} \rightarrow \text{Ingestion} \rightarrow \text{OCR/Vision} \rightarrow \text{Router} \rightarrow \text{Model Manager} \rightarrow \text{RAG} \rightarrow \text{Agent} \rightarrow \text{Sandbox} \rightarrow \text{Validation} \rightarrow \text{Deliverables} \rightarrow \text{Audit} \rightarrow \text{Sovereignty}$$

The primary demonstrator targets the **Refining Equipment Corrosion Audit Workflow** for Mangalore Refinery and Petrochemicals Limited (MRPL), using the synthetic ultrasonic Non-Destructive Testing (NDT) inspection sheet for the **Atmospheric Distillation Column Overheads (C-101)** (`data/samples/corrosion_inspection_c101.pdf`).

---

## 2. Subsystem Interface Map

```
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                 CORROSION AUDIT WORKFLOW ORCHESTRATOR                    │
  │                  (app.services.integration.workflow)                    │
  └───────┬──────────────────────────────────────────────────────────┬───────┘
          │                                                          │
   [Stage 0: Ingestion]                                      [Stage 7: Validation Gate]
   IngestionService.ingest_file()                            StructuredOutputService.validate()
          │                                                          │
   [Stage 1: OCR/Vision]                                     [Stage 8: Deliverables]
   LocalOCREngine.extract_from_image()                       DeliverablesFactory.generate()
          │ (Graceful Degradation)                                   │ (.docx, .xlsx, .pptx)
   [Stage 2: Intent Routing]                                 [Stage 9: Audit Ledger]
   RuleRouter.route()                                        AuditService.verify_ledger()
          │                                                          │
   [Stage 3: Model Allocation]                               [Stage 10: Sovereignty Proof]
   ModelManager.get_tier_config()                            AuditService.check_sovereignty()
          │                                                  RuntimeNetworkMonitor.observe()
   [Stage 4: Sovereign RAG]                                          │
   SovereignRetriever.retrieve_with_citations()              [Complete Telemetry Package]
          │                                                  CorrosionAuditWorkflowResult
   [Stage 5: Agent Lifecycle]                                        ▲
   AgentStateMachineOrchestrator.execute_task()                      │
          │ (11-state transition chain)                              │
   [Stage 6: Sandboxed Calculation] ─────────────────────────────────┘
   SubprocessSandboxExecutor.execute_tool()
   (corrosion_rate_calc & minimum_wall_thickness_check)
```

---

## 3. The 11 Pipeline Stages

| Step | Stage Name | Component / Service | Core Responsibility | Failure Mode / Fallback |
| :--- | :--- | :--- | :--- | :--- |
| **0** | `document_ingestion` | `IngestionService` | Extract text, tables, compute SHA-256 | Rejects invalid PDF bytes (`FAILED`) |
| **1** | `ocr_vision_analysis` | `LocalOCREngine` | Scan image extraction & token geometries | Degrades gracefully to text extraction (`DEGRADED`) |
| **2** | `task_routing` | `RuleRouter` | Categorize intent to model role & capability | Level 0 rule match with fallback role |
| **3** | `model_allocation` | `ModelManager` | Verify model tier assignment & VRAM allocation | Serial model swapping semaphore |
| **4** | `knowledge_retrieval`| `SovereignRetriever` | Vector search over indexed MRPL SOPs | Pure CPU dense retrieval with provenance |
| **5** | `agent_orchestration`| `AgentStateMachineOrchestrator`| 11-state autonomous reasoning lifecycle | Timeout protection (45s step, 120s global) |
| **6** | `sandboxed_calculation`| `SubprocessSandboxExecutor` | Isolated execution of deterministic tools | Zero `eval`/`exec`, strictly typed Pydantic I/O |
| **7** | `engineering_validation_gate`| `StructuredOutputService` | Fail-closed validation of recomputed math | Rejects invalid math (`VALIDATION_FAILED`, 0 deliverables) |
| **8** | `deliverables_factory`| `DeliverablesFactory` | Compiles native `.docx`, `.xlsx`, `.pptx` | Structural inspection of compiled ZIP archives |
| **9** | `audit_chain_verification`| `AuditService` | Tamper-evident append-only JSONL ledger | Verifies unbroken SHA-256 hash chaining |
| **10**| `sovereignty_verification`| `RuntimeNetworkMonitor` | Host socket table inspection | Validates zero unauthorized outbound foreign sockets |

---

## 4. Fail-Closed Invariants

1. **Precondition Validation Gate:** Deliverable builders are never invoked directly by raw agent outputs. `DeliverablesFactory.generate()` mandates a valid `CorrosionAuditResult` verified by `StructuredOutputService`. If validation fails, status transitions to `VALIDATION_FAILED` and deliverables are strictly withheld (0 files emitted).
2. **Deterministic Reproducibility:** Automated test execution runs in `deterministic` mode without reliance on external networks or live GPU VRAM availability, ensuring 100% test reproducibility across any CI/CD or host environment.
3. **Hardware Sovereignty Guarantee:** Throughout workflow execution, the socket monitor confirms zero non-loopback connections, empirically demonstrating compliance with MRPL air-gap operational mandates.
