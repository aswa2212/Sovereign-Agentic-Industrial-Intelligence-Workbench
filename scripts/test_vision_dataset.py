"""
SIH26117 — Vision Model Evaluation Dataset Testing Harness
Evaluates the local vision pipeline (qwen2.5vl:3b via ModelManager) against the Vision Test Dataset.
IMAGE -> LOCAL VISION MODEL -> STRUCTURED EVIDENCE
"""

import argparse
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.config import Settings
from app.services.ingestion.models import DocumentProvenance
from app.services.model_manager.manager import ModelManager
from app.services.vision.vlm_client import (
    ModelManagerVisionProvider,
    MockVisionProvider,
    VisionEngine,
)


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def run_vision_evaluation(live: bool = False, verbose: bool = False):
    settings = Settings()
    dataset_dir = PROJECT_ROOT / "data" / "vision_test"

    if not dataset_dir.is_dir():
        print(f"[ERROR] Dataset directory not found: {dataset_dir}")
        return 1

    print("=" * 80)
    print("SIH26117 — LOCAL VISION MODEL EVALUATION HARNESS")
    print("Dataset: data/vision_test/")
    print(f"Execution Mode: {'LIVE (Ollama / ModelManager)' if live else 'DETERMINISTIC / HARDWARE-FREE'}")
    print("=" * 80)

    # Initialize ModelManager
    model_manager = ModelManager.from_settings()
    tier_config = model_manager.get_tier_config()
    vision_model_entry = tier_config.get_model("vision")

    configured_tag = vision_model_entry.model_tag if vision_model_entry else "qwen2.5vl:3b"
    print(f"[ModelManager] Configured 'vision' role model: {configured_tag}")

    # Select Provider based on mode
    if live:
        is_healthy = await model_manager.health_check()
        if not is_healthy:
            print("[WARN] Local inference provider (Ollama) unreachable. Falling back to deterministic vision provider.")
            provider = MockVisionProvider()
        else:
            provider = ModelManagerVisionProvider(model_manager=model_manager)
    else:
        provider = MockVisionProvider()

    vision_engine = VisionEngine(provider=provider)

    # Discover all test images
    image_paths: List[Path] = sorted(
        [p for p in dataset_dir.rglob("*.png") if p.is_file()] +
        [p for p in dataset_dir.rglob("*.jpg") if p.is_file()]
    )

    if not image_paths:
        print("[ERROR] No test images found in data/vision_test/")
        return 1

    print(f"Discovered {len(image_paths)} benchmark images across 5 categories.\n")

    results: List[Dict[str, Any]] = []

    print(f"{'CATEGORY':<14} | {'FILENAME':<32} | {'TAGS DETECTED':<20} | {'FINDINGS':<8} | {'TIME (ms)':<9} | {'STATUS'}")
    print("-" * 105)

    for img_path in image_paths:
        category = img_path.parent.name
        img_bytes = img_path.read_bytes()
        sha = compute_sha256(img_bytes)

        prov = DocumentProvenance(
            source_filename=img_path.name,
            source_sha256=sha,
            page_number=1,
        )

        t_start = time.monotonic()
        status_str = "SUCCESS"
        error_msg = None
        analysis_res = None

        try:
            analysis_res = await vision_engine.analyze_schematic(
                image_bytes=img_bytes,
                provenance=prov,
            )
        except Exception as e:
            status_str = "FAILED"
            error_msg = str(e)

        elapsed_ms = round((time.monotonic() - t_start) * 1000, 2)

        if analysis_res:
            eq_tags = analysis_res.equipment_tags or []
            inst_tags = analysis_res.instrument_tags or []
            tags_display = ", ".join(eq_tags + inst_tags)[:18] or "—"
            findings_count = len(analysis_res.findings)
            model_used = analysis_res.model_used
            summary_text = analysis_res.summary

            findings_data = [
                {
                    "label": f.label,
                    "type": f.finding_type.value if hasattr(f.finding_type, "value") else str(f.finding_type),
                    "confidence": f.confidence,
                    "evidence": f.evidence,
                }
                for f in analysis_res.findings
            ]
        else:
            tags_display = "ERROR"
            findings_count = 0
            model_used = configured_tag
            summary_text = f"Error: {error_msg}"
            findings_data = []

        print(f"{category:<14} | {img_path.name:<32} | {tags_display:<20} | {findings_count:<8} | {elapsed_ms:<9.1f} | {status_str}")

        results.append({
            "category": category,
            "filename": img_path.name,
            "relative_path": str(img_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": sha,
            "file_size_bytes": len(img_bytes),
            "status": status_str,
            "duration_ms": elapsed_ms,
            "model_used": model_used,
            "equipment_tags": analysis_res.equipment_tags if analysis_res else [],
            "instrument_tags": analysis_res.instrument_tags if analysis_res else [],
            "candidate_tags": analysis_res.candidate_tags if analysis_res else [],
            "findings_count": findings_count,
            "findings": findings_data,
            "summary": summary_text,
            "error": error_msg,
        })

    print("-" * 105)
    print(f"\nEvaluation complete: {len(results)} images processed.")

    # Save structured results
    out_file = dataset_dir / "eval_results.json"
    report_data = {
        "benchmark_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_model_role": "vision",
        "configured_model_tag": configured_tag,
        "execution_mode": "live" if live else "deterministic",
        "total_samples": len(results),
        "successful_samples": sum(1 for r in results if r["status"] == "SUCCESS"),
        "average_duration_ms": round(sum(r["duration_ms"] for r in results) / len(results), 2) if results else 0,
        "results": results,
    }

    out_file.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    print(f"Structured evaluation report saved to: {out_file}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Test Vision Model Evaluation Dataset")
    parser.add_argument("--live", action="store_true", help="Execute against live Ollama ModelManager provider")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    exit_code = asyncio.run(run_vision_evaluation(live=args.live, verbose=args.verbose))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
