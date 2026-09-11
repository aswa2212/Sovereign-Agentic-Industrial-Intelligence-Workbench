# Phase 13 Traceability Matrix: End-to-End System Integration

This document maps all requirements for **Phase 13 — End-to-End System Integration** specified in `docs/implementation_plan.md` to implementation files, APIs, CLI tools, and automated tests.

---

## 1. Requirement Traceability Matrix

| Requirement ID | Requirement Description | Implementation Files | Primary Service / Endpoint | Verification / Test |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-13.1** | **North-Star Workflow Execution:** Connect Ingestion $\rightarrow$ Vision $\rightarrow$ Router $\rightarrow$ Model Manager $\rightarrow$ RAG $\rightarrow$ Agent $\rightarrow$ Sandbox $\rightarrow$ Validation $\rightarrow$ Deliverables $\rightarrow$ Audit $\rightarrow$ Sovereignty | `backend/app/services/integration/workflow.py`, `backend/app/services/integration/models.py` | `CorrosionAuditWorkflow.run()` | `test_e2e_c101_northstar_workflow_success` (11 stages pass in < 60s) |
| **REQ-13.2** | **Document & Ultrasonic Extraction:** Extract C-101 equipment tag, baseline thickness (12.0 mm), and ultrasonic readings (11.2, 10.9, 10.5, 10.1 mm) | `backend/app/services/ingestion/service.py`, `backend/app/services/integration/workflow.py` | `IngestionService.ingest_file()` | Verified in `test_e2e_c101_northstar_workflow_success` and `test_e2e_c101_with_uploaded_bytes` |
| **REQ-13.3** | **OCR / Vision Analysis & Fallback:** Process technical scans with graceful degradation when vision binaries are missing | `backend/app/services/vision/ocr_engine.py`, `backend/app/services/integration/workflow.py` | `LocalOCREngine.extract_from_image()` | `test_e2e_vision_degraded_fallback` (reports `DEGRADED` without workflow failure) |
| **REQ-13.4** | **Task Intent Routing:** Classify objective prompt into model roles (`REASONING`, `FAST`, `VISION`) with confidence scores | `backend/app/services/router/rule_router.py`, `backend/app/services/integration/workflow.py` | `RuleRouter.route()` | Verified in `test_e2e_c101_northstar_workflow_success` (`calculation_signal` rule match) |
| **REQ-13.5** | **Local Model Allocation:** Verify tier model allocation without hardcoded model IDs in application code | `backend/app/services/model_manager/manager.py`, `backend/app/services/integration/workflow.py` | `ModelManager.get_tier_config()` | Verified in `test_e2e_c101_northstar_workflow_success` (queries active tier configuration) |
| **REQ-13.6** | **Sovereign RAG Retrieval:** Retrieve MRPL SOP and API 570 guidelines with verbatim chunk and page provenance | `backend/app/services/rag/retriever.py`, `backend/app/services/integration/workflow.py` | `SovereignRetriever.retrieve_with_citations()` | Verified in `test_e2e_c101_northstar_workflow_success` (retrieves `SOP-MRPL-PIP-001.pdf` p.3) |
| **REQ-13.7** | **Sandboxed Calculation:** Compute metal loss (1.9 mm), corrosion rate (0.38 mm/yr), and remaining life (5.53 yrs) inside subprocess sandbox | `backend/app/services/sandbox/subprocess_executor.py`, `backend/app/services/sandbox/tools.py` | `SubprocessSandboxExecutor.execute_tool()` | Verified in `test_e2e_c101_northstar_workflow_success` (`corrosion_rate_calc` execution) |
| **REQ-13.8** | **Fail-Closed Validation Gate:** Verify schema compliance, numeric tolerances, formula correctness, and citations before deliverable construction | `backend/app/services/validation/service.py`, `backend/app/services/integration/workflow.py` | `StructuredOutputService.validate()` | `test_e2e_validation_gate_fails_closed` (unvalidated output yields 0 deliverables) |
| **REQ-13.9** | **Deterministic Office Deliverables:** Generate valid, non-empty, branded `.docx` memorandum and `.xlsx` calculation sheet (and optional `.pptx`) | `backend/app/services/deliverables/factory.py`, `backend/app/services/integration/workflow.py` | `DeliverablesFactory.generate()` | Verified in `test_e2e_c101_northstar_workflow_success` and `test_e2e_c101_with_pptx_format` |
| **REQ-13.10**| **Audit Chain & Sovereignty Verification:** Verify append-only hash chain and confirm 0 non-loopback network connections | `backend/app/services/audit/service.py`, `backend/app/services/audit/network_monitor.py` | `AuditService.verify_ledger()`, `AuditService.observe_network()` | Verified in `test_e2e_c101_northstar_workflow_success` (`ledger_valid=True`, `airgap_confirmed=True`) |
| **REQ-13.11**| **Workflows REST API:** Provide HTTP REST endpoints for execution, health, and historical inspection | `backend/app/api/v1/endpoints/workflows.py`, `backend/app/api/v1/router.py` | `POST /api/v1/workflows/corrosion-audit`, `GET /api/v1/workflows/{id}`, `GET /api/v1/workflows/health` | `test_api_workflows_health`, `test_api_post_corrosion_audit_workflow`, `test_api_get_workflow_result` |
| **REQ-13.12**| **CLI Demonstration Script:** Provide single-command unattended demonstrator with clear terminal progress output | `scripts/run_e2e_demo.py` | `python scripts/run_e2e_demo.py` | Executed and verified (runs in ~1.8s, prints all 11 stages and deliverable summaries) |

---

## 2. Test Verification Summary

1. **Phase 13 Integration Test Suite:**
   - Command: `$env:PYTHONPATH='backend'; python -m pytest backend/tests/test_e2e_workflow.py -v`
   - Output: **11 passed in 17.61s**
2. **Full System Regression Suite:**
   - Command: `$env:PYTHONPATH='backend'; python -m pytest backend/tests/ -q`
   - Output: **420 passed, 1 warning in 28.27s** (Phases 1–12 regression-free).
3. **Knowledge Store Immutability:**
   - `index.npy` SHA-1 blob: `172f7fbd37aaeafea99784e4399d74ced424f860` (verified unchanged).
   - `metadata.json` SHA-1 blob: `47678dff875b6d26583a4cd639155cc507760ba1` (verified unchanged).
4. **Frozen Phase Protection:**
   - Zero modifications to Phase 1–11 services.
   - New code strictly scoped to `backend/app/services/integration/`, `backend/app/api/v1/endpoints/workflows.py`, `backend/tests/test_e2e_workflow.py`, and `scripts/run_e2e_demo.py`.
