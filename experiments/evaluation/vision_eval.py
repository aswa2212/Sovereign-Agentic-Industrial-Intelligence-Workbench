"""
SIH26117 — Phase 14: OCR & Vision Evaluation Benchmark

Evaluates:
1. Local OCR capabilities:
   - Probes Tesseract executable availability (records REAL OCR PROVIDER UNAVAILABLE when absent).
   - Evaluates MockOCRProvider for token-level bounding box geometry, confidence, and degradation.
2. P&ID and Engineering Drawing parsing:
   - Evaluates equipment tag detection (C-101)
   - Evaluates instrument tag detection (PT-101, FT-202, TT-101)
   - Evaluates line ID detection (10-CDU-0101-CS150)
   - Calculates bounding box overlap IoU against ground-truth coordinates
3. Local VLM (qwen2.5vl:3b):
   - Probes Ollama VLM readiness and evaluates prompt-based schematic visual understanding.
"""

import asyncio
import base64
import io
import json
import time
import urllib.request
from typing import Any, Dict, List, Optional
from PIL import Image, ImageDraw

from app.services.vision.ocr_engine import LocalOCREngine, MockOCRProvider, TesseractOCRProvider
from app.services.vision.vlm_client import MockVisionProvider
from experiments.evaluation.config import get_ollama_base_url
from experiments.evaluation.datasets import PID_GROUND_TRUTH
from experiments.evaluation.metrics import calculate_iou, calculate_latency_stats


def _generate_synthetic_pid_image() -> bytes:
    """Generate a clean synthetic P&ID drawing image with labeled symbols and text."""
    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Draw distillation column vessel C-101 [0.20, 0.15, 0.45, 0.75] -> [160, 90, 360, 450]
    draw.rectangle([160, 90, 360, 450], outline=(0, 0, 0), width=3)
    draw.text((200, 250), "C-101", fill=(0, 0, 0))
    draw.text((180, 270), "ATMOSPHERIC COLUMN", fill=(0, 0, 0))

    # Draw instrument bubble PT-101 [0.48, 0.30, 0.55, 0.38] -> [384, 180, 440, 228]
    draw.ellipse([384, 180, 440, 228], outline=(0, 0, 0), width=2)
    draw.text((395, 198), "PT-101", fill=(0, 0, 0))

    # Draw instrument bubble FT-202 [0.10, 0.50, 0.18, 0.58] -> [80, 300, 144, 348]
    draw.ellipse([80, 300, 144, 348], outline=(0, 0, 0), width=2)
    draw.text((92, 318), "FT-202", fill=(0, 0, 0))

    # Draw piping line annotation [0.25, 0.80, 0.60, 0.85] -> [200, 480, 480, 510]
    draw.line([100, 495, 700, 495], fill=(0, 0, 0), width=3)
    draw.text((260, 475), '10"-CDU-0101-CS150', fill=(0, 0, 0))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def run_ocr_vision_evaluation() -> Dict[str, Any]:
    """Execute evaluation across OCR, VLM, and P&ID ground-truth sets."""
    synthetic_png = _generate_synthetic_pid_image()

    # 1. OCR Provider Availability & Evaluation
    tess = TesseractOCRProvider()
    tesseract_available = tess.is_available()

    ocr_results: Dict[str, Any] = {
        "real_ocr_provider": "tesseract",
        "real_ocr_available": tesseract_available,
        "real_ocr_status": "AVAILABLE" if tesseract_available else "REAL OCR PROVIDER UNAVAILABLE",
    }

    if tesseract_available:
        engine = LocalOCREngine(provider=tess)
        t0 = time.perf_counter()
        res = asyncio.run(engine.extract_from_image(synthetic_png))
        ocr_results["real_ocr_extraction"] = {
            "latency_sec": round(time.perf_counter() - t0, 4),
            "tokens_count": len(res.tokens),
            "confidence_avg": res.mean_confidence,
            "status": res.status,
        }
    else:
        # Evaluate mock OCR provider as fallback baseline
        mock_engine = LocalOCREngine(provider=MockOCRProvider())
        t0 = time.perf_counter()
        mock_res = asyncio.run(mock_engine.extract_from_image(synthetic_png))
        ocr_results["mock_ocr_baseline"] = {
            "provider": "MockOCRProvider",
            "latency_sec": round(time.perf_counter() - t0, 4),
            "tokens_count": len(mock_res.tokens),
            "confidence_avg": mock_res.mean_confidence,
            "sample_tokens": [t.text for t in mock_res.tokens[:5]],
            "status": mock_res.status,
        }

    # 2. P&ID Tag Detection & IoU Evaluation (using Vision provider against synthetic GT)
    mock_vlm = MockVisionProvider()
    t0 = time.perf_counter()
    schematic_res = asyncio.run(mock_vlm.analyze_image(synthetic_png))
    vlm_mock_lat = round(time.perf_counter() - t0, 4)

    expected_tags = PID_GROUND_TRUTH["expected_tags"]
    detected_findings = schematic_res.findings

    detections_summary: List[Dict[str, Any]] = []
    ious: List[float] = []
    tp_count = 0
    fn_count = 0

    for exp in expected_tags:
        exp_tag = exp["tag"]
        exp_bbox = exp["bbox"]

        # Search match in detected findings
        matched_f = next((f for f in detected_findings if f.label == exp_tag or exp_tag in f.text), None)
        if matched_f and matched_f.bounding_box:
            tp_count += 1
            pred_box = [
                matched_f.bounding_box.x_min,
                matched_f.bounding_box.y_min,
                matched_f.bounding_box.x_max,
                matched_f.bounding_box.y_max,
            ]
            iou_score = calculate_iou(exp_bbox, pred_box)
            ious.append(iou_score)
            detections_summary.append({
                "tag": exp_tag,
                "type": exp["type"],
                "detected": True,
                "confidence": matched_f.confidence,
                "iou": iou_score,
            })
        else:
            fn_count += 1
            detections_summary.append({
                "tag": exp_tag,
                "type": exp["type"],
                "detected": False,
                "confidence": 0.0,
                "iou": 0.0,
            })

    # False positives: findings not in ground truth
    exp_labels = {e["tag"] for e in expected_tags}
    fp_count = sum(1 for f in detected_findings if f.label not in exp_labels and not any(e in f.text for e in exp_labels))

    mean_iou = round(sum(ious) / len(ious), 4) if ious else 0.0
    detection_rate = round(tp_count / len(expected_tags), 4) if expected_tags else 0.0

    pid_eval_results = {
        "ground_truth_tags_count": len(expected_tags),
        "detected_tags_count": len(detected_findings),
        "true_positives": tp_count,
        "false_positives": fp_count,
        "false_negatives": fn_count,
        "detection_rate": detection_rate,
        "mean_bounding_box_iou": mean_iou,
        "detections": detections_summary,
        "provider_evaluated": schematic_res.model_used,
        "latency_sec": vlm_mock_lat,
        "limitation_note": (
            "Evaluated against controlled synthetic schematic ground truth. "
            "Does not represent industrial-scale P&ID accuracy across messy full-scale refinery scans."
        ),
    }

    # 3. Real Local VLM Evaluation (qwen2.5vl:3b via Ollama)
    base_url = get_ollama_base_url()
    b64_img = base64.b64encode(synthetic_png).decode("utf-8")
    vlm_req_data = {
        "model": "qwen2.5vl:3b",
        "prompt": "List the equipment tags and instrument bubbles you see in this drawing image in bullet points.",
        "images": [b64_img],
        "stream": False,
        "options": {"num_predict": 128, "temperature": 0.1},
    }

    vlm_real_results: Dict[str, Any] = {
        "model": "qwen2.5vl:3b",
        "provider": "ollama_local",
        "status": "UNAVAILABLE",
    }

    try:
        t0 = time.perf_counter()
        req = urllib.request.Request(
            f"{base_url}/api/generate",
            data=json.dumps(vlm_req_data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            vlm_elapsed = round(time.perf_counter() - t0, 4)
            vlm_resp = json.loads(resp.read().decode("utf-8"))
            vlm_real_results = {
                "model": "qwen2.5vl:3b",
                "provider": "ollama_local",
                "status": "AVAILABLE",
                "latency_sec": vlm_elapsed,
                "response_text": vlm_resp.get("response", "").strip(),
                "eval_count": vlm_resp.get("eval_count"),
                "tokens_per_sec": (
                    round(vlm_resp.get("eval_count", 0) / (vlm_resp.get("eval_duration", 1) / 1e9), 2)
                    if vlm_resp.get("eval_duration")
                    else None
                ),
            }
    except Exception as e:
        vlm_real_results["error"] = str(e)
        vlm_real_results["status"] = "REAL VLM INFERENCE FAILED / TIMED OUT"

    return {
        "benchmark_name": "ocr_vision_evaluation",
        "ocr_evaluation": ocr_results,
        "pid_schematic_evaluation": pid_eval_results,
        "real_vlm_evaluation": vlm_real_results,
    }
