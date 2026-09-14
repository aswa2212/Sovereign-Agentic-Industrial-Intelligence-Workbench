"""
SIH26117 — Phase 14: Router Accuracy Evaluation

Evaluates Phase 3 RuleRouter against the labeled synthetic benchmark dataset.
Measures:
- Overall accuracy
- Per-class precision, recall, and F1 score
- Confusion matrix
- Fallback rate
- Confidence distribution
- Detailed false-routing analysis
"""

import time
from typing import Any, Dict, List

from app.services.router.rule_router import RuleRouter
from app.services.router.taxonomy import TaskType

from experiments.evaluation.datasets import ROUTER_BENCHMARK_DATASET
from experiments.evaluation.metrics import (
    calculate_classification_metrics,
    calculate_latency_stats,
)


def run_routing_evaluation() -> Dict[str, Any]:
    """Execute evaluation of RuleRouter on labeled dataset without modifying router rules."""
    router = RuleRouter()
    dataset = ROUTER_BENCHMARK_DATASET

    y_true: List[str] = []
    y_pred: List[str] = []
    confidences: List[float] = []
    latencies: List[float] = []
    false_routings: List[Dict[str, Any]] = []
    fallback_count = 0

    all_task_types = [t.value for t in TaskType]

    for item in dataset:
        task_text = item["task"]
        expected_type = item["expected_task_type"]
        y_true.append(expected_type)

        t0 = time.perf_counter()
        decision = router.route(task_text)
        lat = time.perf_counter() - t0

        latencies.append(lat)
        pred_type = decision.task_type.value
        conf = decision.confidence
        y_pred.append(pred_type)
        confidences.append(conf)

        if decision.fallback_used:
            fallback_count += 1

        if pred_type != expected_type:
            false_routings.append({
                "task_id": item.get("task_id"),
                "task": task_text,
                "expected_task_type": expected_type,
                "predicted_task_type": pred_type,
                "predicted_capability": decision.capability.value,
                "predicted_role": decision.model_role.value,
                "confidence": conf,
                "reason": decision.reason,
                "matched_rule_id": decision.primary_rule_id,
            })

    # Calculate metrics
    class_metrics = calculate_classification_metrics(
        y_true=y_true,
        y_pred=y_pred,
        classes=all_task_types,
    )
    latency_stats = calculate_latency_stats(latencies)

    # Confidence distribution
    mean_conf = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
    min_conf = round(min(confidences), 4) if confidences else 0.0
    max_conf = round(max(confidences), 4) if confidences else 0.0

    return {
        "benchmark_name": "router_accuracy_evaluation",
        "total_samples": len(dataset),
        "target_accuracy": 0.90,
        "overall_accuracy": class_metrics["overall_accuracy"],
        "target_met": bool(class_metrics["overall_accuracy"] >= 0.90),
        "fallback_count": fallback_count,
        "fallback_rate": round(fallback_count / len(dataset), 4),
        "confidence_distribution": {
            "mean_confidence": mean_conf,
            "min_confidence": min_conf,
            "max_confidence": max_conf,
        },
        "per_class_metrics": class_metrics["per_class"],
        "confusion_matrix": class_metrics["confusion_matrix"],
        "false_routings_count": len(false_routings),
        "false_routings": false_routings,
        "routing_latency_stats": latency_stats,
    }
