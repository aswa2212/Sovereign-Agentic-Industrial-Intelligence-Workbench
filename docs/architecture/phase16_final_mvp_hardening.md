# Phase 16 Architecture Specification: Final Demo Hardening & MVP Baseline

## 1. Overview & Architectural Goal

Phase 16 establishes the final hardened, repeatable, presentation-ready MVP baseline for SIH26117. It integrates all prior architectural milestones (Phases 1–15) into an authoritative North-Star industrial demonstration workflow:
$$\text{Schematic Drawing (P&ID)} \rightarrow \text{Ingestion} \rightarrow \text{VLM Vision} \rightarrow \text{Routing} \rightarrow \text{Allocation} \rightarrow \text{RAG} \rightarrow \text{Agent} \rightarrow \text{Sandbox} \rightarrow \text{Validation Gate} \rightarrow \text{Deliverables} \rightarrow \text{Audit} \rightarrow \text{Sovereignty}$$

---

## 2. Hardened Fail-Closed Invariants

Phase 16 solidifies five essential safety invariants, verified across unit tests and live execution:

1. **Local Provider Liveness Invariant (Case A):**
   When operating in `LIVE` execution mode, the local inference provider (Ollama on `127.0.0.1:11434`) is verified for liveness prior to model invocation. If the provider is unreachable, execution halts immediately with status `FAILED`. Under no circumstances is a mock or synthetic result silently substituted.

2. **Validation Gate Invariant (Case B):**
   Raw model outputs (visual annotations or text) cannot directly trigger deliverable compilation. All outputs pass through `StructuredOutputService.validate()`, checking 12 formula, schema, and engineering tolerance rules. If any check fails, status is marked `VALIDATION_FAILED` and all deliverables are withheld (0 artifacts emitted).

3. **Input Integrity Invariant (Case C):**
   Missing or corrupted document files trigger structured `DocumentIngestionStageError` events and prevent pipeline advancement.

4. **Sovereignty Invariant (Case D):**
   During workflow execution, runtime host network connections are inspected by `RuntimeNetworkMonitor`. If any non-loopback or foreign IP connection is detected, the workflow immediately revokes deliverables and halts with status `FAILED`.

5. **Deterministic Office Compilation Invariant (Case E):**
   Upon successful validation and sovereignty checks, `DeliverablesFactory` deterministically compiles native `.docx` executive notes and `.xlsx` calculation workbooks, verifying ZIP archive structures and SHA-256 hashes.

---

## 3. Demonstration Architecture & Single-Command Runner

The North-Star industrial scenario is packaged into a standalone, reproducible runner:
```powershell
python scripts/run_demo.py [--mode live|deterministic] [--component C-101] [--image path/to/image.png]
```

### Components Exercised:
- **P&ID Schematic:** `data/samples/pid_sample.png` (800x600 PNG, C-101 Atmospheric Distillation Column Overheads)
- **Local VLM Engine:** Resident `qwen2.5vl:3b` executed via `ModelManagerVisionProvider`
- **Rule Router:** Matches engineering keywords and mathematical objectives to appropriate model roles
- **Sovereign RAG:** Retrieves verbatim procedural sections from `SOP-MRPL-PIP-001`
- **Agent Lifecycle:** 11-state autonomous state machine (`IDLE` to `COMPLETED`)
- **Subprocess Sandbox:** Computes wall loss (`1.9 mm`), corrosion rate (`0.38 mm/yr`), and remaining life (`5.53 yrs`)
- **Office Deliverables:** Generates valid, non-empty, branded `.docx` and `.xlsx`
- **Audit Ledger:** Appends SHA-256 hash-chained JSONL records
- **Sovereignty Verification:** Validates 0 non-loopback network connections
