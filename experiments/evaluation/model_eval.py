"""
SIH26117 — Phase 14: Model Inference and Sequential Switching Benchmark

Measures for local models available in Ollama:
- Model availability and size
- Cold vs Warm inference latency (separated strictly)
- Token generation throughput (tokens/sec)
- VRAM delta and peak consumption during load & inference
- Sequential model switching / memory clearing behavior (e.g. reasoning -> vision -> reasoning)
"""

import json
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

from experiments.evaluation.config import get_ollama_base_url
from experiments.evaluation.metrics import calculate_latency_stats
from experiments.evaluation.resource_monitor import ResourceMonitor, ResourceTracker


# Candidate models targeted by Phase 14
CANDIDATE_MODELS = [
    {"tag": "qwen2.5:1.5b", "role": "router", "type": "text"},
    {"tag": "qwen2.5-coder:3b", "role": "coder", "type": "code"},
    {"tag": "qwen2.5vl:3b", "role": "vision", "type": "multimodal"},
    {"tag": "deepseek-r1:7b", "role": "reasoning", "type": "reasoning"},
    {"tag": "nomic-embed-text:latest", "role": "embedding", "type": "embedding"},
    {"tag": "bge-m3:latest", "role": "embedding", "type": "embedding"},
]

STANDARD_TEXT_PROMPT = (
    "Summarize the primary purpose of ultrasonic thickness gauging on refining process piping in 2 concise sentences."
)


def probe_ollama_models() -> Dict[str, Any]:
    """Inspect local Ollama endpoint to determine available models and sizes."""
    base_url = get_ollama_base_url()
    tags_url = f"{base_url}/api/tags"
    available_map: Dict[str, Dict[str, Any]] = {}

    try:
        req = urllib.request.Request(tags_url, headers={"User-Agent": "SIH26117-Evaluation"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for m in data.get("models", []):
                name = m.get("name")
                available_map[name] = {
                    "name": name,
                    "size_bytes": m.get("size"),
                    "size_gb": round(m.get("size", 0) / (1024 ** 3), 2),
                    "modified_at": m.get("modified_at"),
                    "details": m.get("details", {}),
                }
    except Exception as e:
        return {"error": f"Failed to connect to Ollama at {base_url}: {str(e)}", "available_models": {}}

    candidates_status: List[Dict[str, Any]] = []
    for c in CANDIDATE_MODELS:
        tag = c["tag"]
        # Match either exact tag or tag without/with :latest
        found_key = None
        for k in available_map.keys():
            if k == tag or k == f"{tag}:latest" or (tag.endswith(":latest") and k == tag[:-7]):
                found_key = k
                break

        if found_key:
            info = available_map[found_key]
            candidates_status.append({
                "model_tag": tag,
                "ollama_tag": found_key,
                "role": c["role"],
                "type": c["type"],
                "status": "AVAILABLE",
                "size_gb": info["size_gb"],
                "parameter_size": info.get("details", {}).get("parameter_size", "unknown"),
                "quantization_level": info.get("details", {}).get("quantization_level", "unknown"),
            })
        else:
            candidates_status.append({
                "model_tag": tag,
                "ollama_tag": None,
                "role": c["role"],
                "type": c["type"],
                "status": "UNAVAILABLE",
                "size_gb": None,
                "parameter_size": None,
                "quantization_level": None,
            })

    return {
        "endpoint": base_url,
        "raw_models_count": len(available_map),
        "candidates": candidates_status,
    }


def query_ollama_generate(
    model_tag: str,
    prompt: str,
    stream: bool = False,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """Execute raw inference call to local Ollama /api/generate endpoint."""
    base_url = get_ollama_base_url()
    url = f"{base_url}/api/generate"
    payload = {
        "model": model_tag,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": 0.1,
            "num_predict": 128,
        },
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json"},
    )

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = time.perf_counter() - t0
            res = json.loads(resp.read().decode("utf-8"))
            eval_count = res.get("eval_count", 0)
            eval_duration_ns = res.get("eval_duration", 0)
            prompt_eval_duration_ns = res.get("prompt_eval_duration", 0)
            load_duration_ns = res.get("load_duration", 0)

            tok_per_sec = (
                round(eval_count / (eval_duration_ns / 1e9), 2)
                if eval_duration_ns > 0 and eval_count > 0
                else None
            )

            return {
                "success": True,
                "total_duration_sec": round(elapsed, 4),
                "load_duration_sec": round(load_duration_ns / 1e9, 4),
                "prompt_eval_duration_sec": round(prompt_eval_duration_ns / 1e9, 4),
                "eval_duration_sec": round(eval_duration_ns / 1e9, 4),
                "eval_count_tokens": eval_count,
                "tokens_per_second": tok_per_sec,
                "response_text": res.get("response", "").strip(),
                "error": None,
            }
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return {
            "success": False,
            "total_duration_sec": round(elapsed, 4),
            "load_duration_sec": None,
            "prompt_eval_duration_sec": None,
            "eval_duration_sec": None,
            "eval_count_tokens": 0,
            "tokens_per_second": None,
            "response_text": "",
            "error": str(e),
        }


def unload_ollama_model(model_tag: str) -> None:
    """Prompt Ollama to unload model from VRAM by setting keep_alive to 0."""
    base_url = get_ollama_base_url()
    url = f"{base_url}/api/generate"
    payload = {"model": model_tag, "keep_alive": 0}
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
    except Exception:
        pass


def run_model_inference_benchmark() -> Dict[str, Any]:
    """
    Benchmark inference on available text/code/reasoning models.
    Strictly separates COLD run from WARM runs.
    """
    probing = probe_ollama_models()
    candidates = probing.get("candidates", [])

    results: Dict[str, Any] = {
        "benchmark_name": "model_inference_benchmark",
        "models_evaluated": [],
    }

    # Only benchmark text generation capable models
    text_models = [c for c in candidates if c["status"] == "AVAILABLE" and c["type"] in ("text", "code", "reasoning")]

    for candidate in text_models:
        tag = candidate["model_tag"]
        ollama_tag = candidate["ollama_tag"]

        # Ensure model is cold by requesting keep_alive 0
        unload_ollama_model(ollama_tag)
        time.sleep(2.0)  # Allow VRAM recovery

        # 1. COLD RUN
        with ResourceTracker(f"cold_inference_{tag}") as tracker:
            cold_res = query_ollama_generate(ollama_tag, STANDARD_TEXT_PROMPT, timeout=90.0)
        cold_telemetry = tracker.stop()

        # 2. WARM RUNS (3 trials)
        warm_runs: List[Dict[str, Any]] = []
        warm_latencies: List[float] = []
        warm_tok_rates: List[float] = []

        for trial in range(1, 4):
            time.sleep(0.5)
            with ResourceTracker(f"warm_inference_{tag}_t{trial}") as w_tracker:
                w_res = query_ollama_generate(ollama_tag, STANDARD_TEXT_PROMPT, timeout=60.0)
            w_telemetry = w_tracker.stop()

            warm_runs.append({
                "trial": trial,
                "latency_sec": w_res["total_duration_sec"],
                "eval_tokens": w_res["eval_count_tokens"],
                "tokens_per_sec": w_res["tokens_per_second"],
                "vram_delta_mb": w_telemetry.get("vram_delta_mb"),
                "success": w_res["success"],
                "error": w_res["error"],
            })
            if w_res["success"]:
                warm_latencies.append(w_res["total_duration_sec"])
                if w_res["tokens_per_second"]:
                    warm_tok_rates.append(w_res["tokens_per_second"])

        # Statistics
        warm_stats = calculate_latency_stats(warm_latencies)
        mean_tok_rate = (
            round(sum(warm_tok_rates) / len(warm_tok_rates), 2)
            if warm_tok_rates
            else None
        )

        results["models_evaluated"].append({
            "model_tag": tag,
            "ollama_tag": ollama_tag,
            "role": candidate["role"],
            "parameter_size": candidate["parameter_size"],
            "quantization": candidate["quantization_level"],
            "cold_run": {
                "latency_sec": cold_res["total_duration_sec"],
                "load_duration_sec": cold_res["load_duration_sec"],
                "eval_tokens": cold_res["eval_count_tokens"],
                "tokens_per_sec": cold_res["tokens_per_second"],
                "vram_delta_mb": cold_telemetry.get("vram_delta_mb"),
                "vram_before_mb": cold_telemetry.get("vram_before_mb"),
                "vram_after_mb": cold_telemetry.get("vram_after_mb"),
                "success": cold_res["success"],
                "error": cold_res["error"],
            },
            "warm_runs": warm_runs,
            "warm_latency_stats": warm_stats,
            "warm_mean_tokens_per_sec": mean_tok_rate,
        })

    return results


def run_sequential_switching_benchmark() -> Dict[str, Any]:
    """
    Benchmark sequential model switching under 8 GB VRAM budget:
    deepseek-r1:7b (Reasoning) -> qwen2.5vl:3b (Vision) -> deepseek-r1:7b (Reasoning)
    Measures swap latency, memory clearance, and residency behavior.
    """
    probing = probe_ollama_models()
    candidates = {c["model_tag"]: c for c in probing.get("candidates", [])}

    r1_cand = candidates.get("deepseek-r1:7b")
    vl_cand = candidates.get("qwen2.5vl:3b")

    if not r1_cand or r1_cand["status"] != "AVAILABLE" or not vl_cand or vl_cand["status"] != "AVAILABLE":
        return {
            "status": "SKIPPED",
            "reason": "Required models deepseek-r1:7b or qwen2.5vl:3b not available locally.",
        }

    r1_tag = r1_cand["ollama_tag"]
    vl_tag = vl_cand["ollama_tag"]

    transitions = [
        {"step": 1, "action": "load_reasoning", "model": r1_tag, "prompt": "Assess fitness for service in 1 sentence."},
        {"step": 2, "action": "swap_to_vision", "model": vl_tag, "prompt": "Identify equipment tag in this text prompt."},
        {"step": 3, "action": "swap_back_reasoning", "model": r1_tag, "prompt": "Summarize remaining life in 1 sentence."},
    ]

    transition_records: List[Dict[str, Any]] = []

    for t in transitions:
        step_num = t["step"]
        act_name = t["action"]
        model = t["model"]
        prompt = t["prompt"]

        snap_before = ResourceMonitor.get_snapshot()
        t0 = time.perf_counter()

        res = query_ollama_generate(model, prompt, timeout=90.0)
        elapsed = time.perf_counter() - t0
        snap_after = ResourceMonitor.get_snapshot()

        vram_before = snap_before.get("vram_used_mb")
        vram_after = snap_after.get("vram_used_mb")
        delta_vram = round(vram_after - vram_before, 2) if vram_before and vram_after else None

        transition_records.append({
            "step": step_num,
            "action": act_name,
            "model": model,
            "latency_sec": round(elapsed, 4),
            "load_duration_sec": res["load_duration_sec"],
            "success": res["success"],
            "error": res["error"],
            "vram_before_mb": vram_before,
            "vram_after_mb": vram_after,
            "vram_delta_mb": delta_vram,
        })

    return {
        "benchmark_name": "sequential_model_switching",
        "transitions": transition_records,
        "serial_execution_viable": all(t["success"] for t in transition_records),
    }
