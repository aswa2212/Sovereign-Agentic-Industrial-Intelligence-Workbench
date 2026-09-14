"""
SIH26117 — Phase 14: Master Benchmark Runner

Orchestrates the entire Phase 14 evaluation suite:
1. Environment & hardware detection (GPU VRAM, CPU, RAM, OS)
2. Local model probing (Ollama candidate models)
3. Task router accuracy evaluation (overall, per-class, confusion matrix)
4. Local model inference benchmark (cold vs warm, tokens/sec, VRAM delta)
5. Sequential model switching benchmark (reasoning -> vision -> reasoning)
6. Sovereign RAG retrieval evaluation & embedding model comparison
7. OCR, Vision, and P&ID bounding box IoU evaluation
8. End-to-End C-101 workflow performance breakdown & failure degradation
9. Results serialization to experiments/evaluation/results/*.json
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from experiments.evaluation.config import (
    DOCS_EVAL_DIR,
    RESULTS_DIR,
    detect_hardware_environment,
)
from experiments.evaluation.e2e_eval import (
    run_e2e_performance_benchmark,
    run_failure_degradation_benchmark,
)
from experiments.evaluation.model_eval import (
    probe_ollama_models,
    run_model_inference_benchmark,
    run_sequential_switching_benchmark,
)
from experiments.evaluation.rag_eval import (
    run_embedding_comparison_benchmark,
    run_rag_retrieval_evaluation,
)
from experiments.evaluation.routing_eval import run_routing_evaluation
from experiments.evaluation.vision_eval import run_ocr_vision_evaluation


def run_full_evaluation_suite() -> Dict[str, Any]:
    """Execute all benchmarks and compile unified results object."""
    timestamp = datetime.now(timezone.utc).isoformat()
    print("=" * 60)
    print(f"SIH26117 — Phase 14: Accuracy & Performance Evaluation Suite")
    print(f"Started at: {timestamp}")
    print("=" * 60)

    # 1. Environment Detection
    print("\n[1/8] Detecting hardware environment...")
    hw_env = detect_hardware_environment()
    print(f"  OS: {hw_env.get('os')}")
    print(f"  RAM: {hw_env.get('total_ram_gb')} GB (Avail: {hw_env.get('available_ram_gb')} GB)")
    print(f"  GPU: {hw_env.get('gpu_name')} | VRAM Free: {hw_env.get('gpu_free_vram_mib')} MiB / {hw_env.get('gpu_total_vram_mib')} MiB")

    # 2. Local Model Probing
    print("\n[2/8] Probing local Ollama candidate models...")
    model_probe = probe_ollama_models()
    for c in model_probe.get("candidates", []):
        print(f"  - {c['model_tag']}: {c['status']} ({c.get('size_gb')} GB, {c.get('parameter_size')})")

    # 3. Router Accuracy
    print("\n[3/8] Benchmarking RuleRouter accuracy...")
    routing_results = run_routing_evaluation()
    print(f"  Overall Accuracy: {routing_results['overall_accuracy'] * 100:.2f}% (Target: >=90%) -> Met: {routing_results['target_met']}")
    print(f"  False routings: {routing_results['false_routings_count']} / {routing_results['total_samples']}")

    # 4. Model Inference & Sequential Switching
    print("\n[4/8] Benchmarking model inference (Cold vs Warm) & Sequential Switching...")
    model_inference_results = run_model_inference_benchmark()
    for m in model_inference_results.get("models_evaluated", []):
        cold_lat = m["cold_run"]["latency_sec"]
        warm_mean = m["warm_latency_stats"]["mean_sec"]
        tok_sec = m["warm_mean_tokens_per_sec"]
        print(f"  - {m['model_tag']}: Cold={cold_lat}s, Warm Mean={warm_mean}s, Speed={tok_sec} tok/s")

    switching_results = run_sequential_switching_benchmark()
    print(f"  Sequential model switching viable: {switching_results.get('serial_execution_viable')}")

    # 5. RAG Retrieval & Embedding Comparison
    print("\n[5/8] Benchmarking RAG retrieval & embedding models...")
    rag_results = run_rag_retrieval_evaluation()
    print(f"  RAG Mean Reciprocal Rank (MRR): {rag_results['retrieval_metrics']['mean_reciprocal_rank']}")
    print(f"  Citation Document Accuracy: {rag_results['citation_doc_accuracy'] * 100:.1f}%")

    embedding_results = run_embedding_comparison_benchmark()
    for em in embedding_results.get("models_evaluated", []):
        print(f"  - Embedding {em['model']}: dim={em.get('dimension')}, margin={em.get('discrimination_margin')}, latency={em.get('latency_stats', {}).get('mean_sec')}s")

    # 6. OCR & Vision Evaluation
    print("\n[6/8] Benchmarking OCR, P&ID Schematic, and VLM...")
    vision_results = run_ocr_vision_evaluation()
    print(f"  OCR Provider Status: {vision_results['ocr_evaluation']['real_ocr_status']}")
    print(f"  P&ID Tag Detection Rate: {vision_results['pid_schematic_evaluation']['detection_rate'] * 100:.1f}% (Mean IoU: {vision_results['pid_schematic_evaluation']['mean_bounding_box_iou']})")
    print(f"  VLM Status: {vision_results['real_vlm_evaluation']['status']} (Latency: {vision_results['real_vlm_evaluation'].get('latency_sec')}s)")

    # 7. End-to-End Performance
    print("\n[7/8] Benchmarking E2E C-101 Primary Workflow (Deterministic mode)...")
    e2e_results = run_e2e_performance_benchmark(trials_count=5)
    print(f"  E2E Deterministic Latency: Mean={e2e_results['overall_latency_stats']['mean_sec']}s, Median={e2e_results['overall_latency_stats']['median_sec']}s")

    # 8. Failure & Degradation Benchmark
    print("\n[8/8] Benchmarking failure and degradation behavior...")
    failure_results = run_failure_degradation_benchmark()
    print(f"  All failure scenarios safe & contained: {failure_results['all_scenarios_safe']}")

    # Assemble master report payload
    full_suite_data: Dict[str, Any] = {
        "suite_name": "SIH26117_Phase14_Evaluation_Suite",
        "timestamp": timestamp,
        "environment": hw_env,
        "models_probed": model_probe,
        "routing_evaluation": routing_results,
        "model_inference_benchmark": model_inference_results,
        "sequential_switching_benchmark": switching_results,
        "rag_retrieval_evaluation": rag_results,
        "embedding_comparison_benchmark": embedding_results,
        "ocr_vision_evaluation": vision_results,
        "e2e_performance_benchmark": e2e_results,
        "failure_degradation_benchmark": failure_results,
    }

    # Save to experiments/evaluation/results/
    out_file = RESULTS_DIR / "phase14_evaluation_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_suite_data, f, indent=2)
    print(f"\n[OK] Raw results saved to: {out_file}")

    return full_suite_data


if __name__ == "__main__":
    run_full_evaluation_suite()
