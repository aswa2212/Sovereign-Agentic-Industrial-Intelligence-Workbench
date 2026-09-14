# Phase 15 Traceability Matrix: Live Local Model Integration

This document maps all requirements for **Phase 15 — Live Local Model Integration** to implementation files, configuration definitions, and verification tests.

---

## 1. Requirement Traceability Matrix

| Requirement ID | Requirement Description | Implementation Files | Primary Service / Endpoint | Verification / Test |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-15.1** | **Dynamic Model Tag Resolution:** Dynamically map configured VLM tag (`qwen2.5-vl:3b` / `qwen2.5vl:3b`) to installed Ollama tags | `backend/app/services/model_manager/ollama_adapter.py` | `OllamaAdapter._resolve_model_tag()` | `test_ollama_adapter_model_tag_resolution`, verified against live Ollama daemon |
| **REQ-15.2** | **Multimodal Image Forwarding:** Pass base64-encoded image buffers to Ollama `/api/generate` payload | `backend/app/services/model_manager/ollama_adapter.py` | `OllamaAdapter.generate_json()` | `test_ollama_adapter_images_parameter_forwarding` |
| **REQ-15.3** | **Structured VLM Parsing Robustness:** Normalize string or dictionary equipment/instrument tags and clamp bounding boxes | `backend/app/services/vision/vlm_client.py` | `ModelManagerVisionProvider._parse_structured_response()` | `test_vlm_parse_structured_response_with_dicts_and_strings`, `test_vlm_parse_fallback_when_findings_empty` |
| **REQ-15.4** | **Workflow Live VLM Execution:** Execute real local VLM visual extraction in Stage 2 with live model allocation | `backend/app/services/integration/workflow.py` | `CorrosionAuditWorkflow.run(execution_mode=LIVE)` | `test_workflow_live_mode_structure`, `scripts/live_vlm_smoke_test.py` |
| **REQ-15.5** | **Fail-Closed Live Error Handling:** Raise `IntegrationError` and abort deliverables if live VLM is unavailable in live mode | `backend/app/services/integration/workflow.py` | `CorrosionAuditWorkflow.run()` | `test_workflow_live_mode_fails_closed_when_vlm_fails` |
| **REQ-15.6** | **Configured Model Configuration:** Update dev tier config to point to resident `qwen2.5vl:3b` tag | `models/configs/model_tiers.yaml` | `ModelManager.get_tier_config()` | `test_model_tier_config_has_qwen25vl` |
| **REQ-15.7** | **Frontend Dynamic Model Display:** Render active VLM model name and provider dynamically from backend `/models/tier` | `frontend/src/pages/WorkbenchPage.tsx`, `frontend/src/services/system.ts` | `systemService.getModelTier()` | Dynamic banner verified in Vite production build |
| **REQ-15.8** | **Frontend Execution Mode Selection:** Support toggling between Deterministic and Live Local Model modes | `frontend/src/pages/WorkbenchPage.tsx`, `frontend/src/hooks/useAgentTask.ts`, `frontend/src/services/agent.ts` | `WorkbenchPage.tsx`, `useAgentTask.ts` | Frontend production build succeeds, REST payload dispatch verified |
| **REQ-15.9** | **Live End-to-End Smoke Test:** Run real local VLM model through full 11-stage pipeline to deliverable creation | `scripts/live_vlm_smoke_test.py` | `CorrosionAuditWorkflow.run(execution_mode=LIVE)` | Live smoke test passes (9.09s VLM inference, 11 stages success, 0 external sockets) |

---

## 2. Test Verification Summary

1. **Phase 15 Unit & Integration Suite:**
   - Command: `$env:PYTHONPATH='backend'; python -m pytest backend/tests/test_phase15_live_model.py -v`
   - Output: **9 passed in 3.65s**
2. **Full System Regression Suite:**
   - Command: `$env:PYTHONPATH='backend'; python -m pytest backend/tests/ -q`
   - Output: **429 passed in 29.83s** (100% pass rate across Phases 1–15).
3. **Frontend Production Build:**
   - Command: `npm run build` (in `frontend/`)
   - Output: **Built in 3.37s with 0 errors**.
4. **Live Smoke Test Script Execution:**
   - Command: `$env:PYTHONPATH='backend'; python scripts/live_vlm_smoke_test.py`
   - Output: **All 11 stages SUCCESS**, 12/12 validation checks valid, DOCX & XLSX generated, 0 non-loopback connections observed.
5. **Frozen Phase Protection:**
   - No changes made to Phases 1–14 frozen interfaces or knowledge data.
   - All network traffic strictly constrained to loopback `127.0.0.1`.
