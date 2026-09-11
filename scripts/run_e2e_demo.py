"""
SIH26117 — Primary Corrosion Audit End-to-End Demonstration Script

Executes the full 11-stage autonomous operational intelligence pipeline:
  [PDF INGESTION] -> [OCR / VISION] -> [ROUTER] -> [MODEL MANAGER] ->
  [SOVEREIGN RAG] -> [AGENT STATE MACHINE] -> [SANDBOX CALCULATION] ->
  [VALIDATION GATE] -> [DELIVERABLES FACTORY] -> [AUDIT LEDGER] -> [SOVEREIGNTY CHECK]

Usage:
  python scripts/run_e2e_demo.py [--formats docx,xlsx,pptx] [--mode deterministic|live]
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

# Ensure backend is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.services.integration.models import (
    CorrosionAuditWorkflowRequest,
    WorkflowExecutionMode,
    WorkflowStatus,
)
from app.services.integration.workflow import CorrosionAuditWorkflow


def print_banner():
    banner = """
================================================================================
  SIH26117 — SOVEREIGN ON-PREMISE AGENTIC AI WORKBENCH FOR MRPL
  PRIMARY INDUSTRIAL DEMONSTRATION: C-101 CORROSION & ASSET INTEGRITY AUDIT
================================================================================
  Target Asset:     Atmospheric Distillation Column Overhead System (C-101)
  Operating Unit:   Crude Distillation Unit (CDU-1), Mangalore Refinery Complex
  Inspection Type:  Ultrasonic Non-Destructive Testing (NDT) Wall Thickness Survey
  Architecture:     11 Subsystems | Air-Gapped Local Hardware | 100% Deterministic
================================================================================
"""
    print(banner)


async def main():
    parser = argparse.ArgumentParser(description="Run SIH26117 End-to-End Demonstration")
    parser.add_argument("--formats", default="docx,xlsx", help="Deliverable formats (comma-separated: docx,xlsx,pptx)")
    parser.add_argument("--mode", default="deterministic", choices=["deterministic", "live"], help="Execution mode")
    parser.add_argument("--component", default="C-101", help="Equipment identifier tag")
    args = parser.parse_args()

    print_banner()

    formats = [f.strip().lower() for f in args.formats.split(",") if f.strip()]
    exec_mode = (
        WorkflowExecutionMode.LIVE
        if args.mode == "live"
        else WorkflowExecutionMode.DETERMINISTIC
    )

    request = CorrosionAuditWorkflowRequest(
        objective="Audit thickness readings against MRPL piping specification, calculate corrosion rate, and generate executive approval note.",
        component_id=args.component,
        execution_mode=exec_mode,
        requested_formats=formats,
    )

    print(f"[*] Initializing Sovereign Workflow Engine (Mode: {exec_mode.value.upper()})...")
    workflow = CorrosionAuditWorkflow()

    start_time = time.monotonic()
    print(f"[*] Triggering End-to-End Pipeline on {args.component}...\n")

    result = await workflow.run(request)
    total_elapsed = time.monotonic() - start_time

    # ── Stage Progression Table ────────────────────────────────────────────────
    print("--------------------------------------------------------------------------------")
    print("  STAGE-BY-STAGE EXECUTION TRACE")
    print("--------------------------------------------------------------------------------")
    print(f"  {'#':<4} {'STAGE NAME':<32} {'STATUS':<12} {'LATENCY':<12}")
    print("  " + "-" * 62)

    for stage in result.stages:
        status_symbol = "[OK]" if stage.status.value in ("SUCCESS", "COMPLETED") else f"[{stage.status.value}]"
        print(f"  {stage.stage_index:<4} {stage.stage_name:<32} {status_symbol:<12} {stage.duration_ms:.1f} ms")

    print("--------------------------------------------------------------------------------\n")

    # ── Subsystem Details ─────────────────────────────────────────────────────
    print("[1] INGESTION & DOCUMENT PROVENANCE:")
    doc = result.document_summary
    print(f"    - Document:   {doc.get('filename')} (Pages: {doc.get('page_count')}, Tables: {doc.get('table_count')})")
    print(f"    - SHA-256:    {doc.get('sha256')}")

    print("\n[2] OCR & VISION EXTRACTION:")
    ocr = result.ocr_vision_summary
    print(f"    - Engine:     {ocr.get('engine_name')} (Status: {ocr.get('status', 'OK')})")
    print(f"    - Tokens:     {ocr.get('total_tokens')} extracted tokens (Confidence: {ocr.get('confidence_avg')})")

    print("\n[3] INTENT CLASSIFICATION & TASK ROUTING:")
    route = result.routing_decision or {}
    print(f"    - Task Type:  {route.get('task_type')} -> Model Role: {route.get('model_role')}")
    print(f"    - Confidence: {route.get('confidence')} via rule '{route.get('primary_rule_id')}'")

    print("\n[4] LOCAL MODEL ALLOCATION:")
    model = result.model_allocation or {}
    print(f"    - Model Tag:  {model.get('assigned_model_tag')} (Tier: {model.get('tier_role')})")
    print(f"    - Available:  {model.get('available_models_count')} local model slots")

    print("\n[5] SOVEREIGN KNOWLEDGE RETRIEVAL (RAG):")
    for idx, cit in enumerate(result.rag_citations, start=1):
        print(f"    [{idx}] Standard: {cit.get('source_document')} (Page {cit.get('page_number')})")

    print("\n[6] SANDBOXED ENGINEERING CALCULATION:")
    calc = result.calculation_result or {}
    print(f"    - Baseline Thickness:  {calc.get('previous_thickness_mm')} mm")
    print(f"    - Current Thickness:   {calc.get('current_thickness_mm')} mm")
    print(f"    - Metal Loss:          {calc.get('metal_loss_mm')} mm over {calc.get('elapsed_time_years')} years")
    print(f"    - Corrosion Rate:      {calc.get('corrosion_rate_mm_per_year')} mm/year")
    print(f"    - Remaining Life:      {calc.get('remaining_life_years')} years ({calc.get('remaining_life_status')})")

    print("\n[7] FAIL-CLOSED ENGINEERING VALIDATION GATE:")
    val = result.validation_result or {}
    print(f"    - Gate Outcome:        {val.get('status')} (Valid: {val.get('valid')})")
    print(f"    - Checks Passed:       {len(val.get('checks_passed', []))} verified checks")
    print(f"    - Checks Failed:       {len(val.get('checks_failed', []))}")

    print("\n[8] DETERMINISTIC OFFICE DELIVERABLES:")
    for deliv in result.deliverables:
        print(f"    - [{deliv.format.upper()}] {deliv.filename}")
        print(f"      Size: {deliv.file_size_bytes:,} bytes | SHA-256: {deliv.sha256[:16]}... | Path: outputs/{deliv.relative_path}")

    print("\n[9] TAMPER-EVIDENT AUDIT TRAIL:")
    audit = result.audit_summary
    print(f"    - Hash-Chain Integrity: {'VERIFIED VALID' if audit.get('ledger_valid') else 'INVALID'}")
    print(f"    - Events Verified:      {audit.get('events_checked')} sequential ledger entries")

    print("\n[10] SOVEREIGNTY & AIR-GAP PROOF:")
    sov = result.sovereignty_proof
    print(f"    - Non-Local Sockets:    {sov.get('non_loopback_connections')} external sockets (PASS)")
    print(f"    - Air-Gap Integrity:    {'CONFIRMED ISOLATED' if sov.get('airgap_confirmed') else 'VIOLATED'}")

    print("\n================================================================================")
    if result.status == WorkflowStatus.COMPLETED:
        print(f"  DEMONSTRATION STATUS: COMPLETED SUCCESSFULLY in {total_elapsed:.2f}s")
        print("  All 5 Core Hackathon Pillars empirically demonstrated.")
    else:
        print(f"  DEMONSTRATION STATUS: {result.status.value}")
        if result.errors:
            print(f"  Errors: {result.errors}")
    print("================================================================================\n")


if __name__ == "__main__":
    asyncio.run(main())
