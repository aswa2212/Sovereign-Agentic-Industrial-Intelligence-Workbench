"""
SIH26117 — Phase 14: Statistical and Evaluation Metrics

Computes:
- Classification metrics: Accuracy, Per-class Precision/Recall/F1, Confusion Matrix
- Ranking & Retrieval metrics: Recall@K, Precision@K, Mean Reciprocal Rank (MRR)
- Latency statistics: Mean, Median, P95, Min, Max (with sample size guard)
- Vision / Spatial metrics: Intersection over Union (IoU) for bounding boxes
"""

from typing import Any, Dict, List, Optional, Tuple
import math


def calculate_latency_stats(latencies: List[float]) -> Dict[str, Any]:
    """
    Calculate latency distribution statistics.
    Guards statistical claims against tiny sample sizes.
    """
    if not latencies:
        return {
            "count": 0,
            "mean_sec": None,
            "median_sec": None,
            "p95_sec": None,
            "min_sec": None,
            "max_sec": None,
            "note": "Empty sample set",
        }

    sorted_vals = sorted(latencies)
    n = len(sorted_vals)
    mean_val = sum(sorted_vals) / n
    median_val = (
        sorted_vals[n // 2]
        if n % 2 != 0
        else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0
    )

    # Statistical validity check: P95 is statistically unsound if n < 20
    if n >= 20:
        idx = int(math.ceil(0.95 * n)) - 1
        p95_val = sorted_vals[min(idx, n - 1)]
        note = "Statistically sufficient sample size"
    else:
        p95_val = None
        note = f"Sample size (N={n}) is too small for statistically valid P95 calculation"

    return {
        "count": n,
        "mean_sec": round(mean_val, 4),
        "median_sec": round(median_val, 4),
        "p95_sec": round(p95_val, 4) if p95_val is not None else None,
        "min_sec": round(sorted_vals[0], 4),
        "max_sec": round(sorted_vals[-1], 4),
        "note": note,
    }


def calculate_classification_metrics(
    y_true: List[str],
    y_pred: List[str],
    classes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Calculate multi-class classification accuracy, per-class metrics, and confusion matrix.
    """
    if len(y_true) != len(y_pred):
        raise ValueError(f"Length mismatch: {len(y_true)} true vs {len(y_pred)} pred")

    total = len(y_true)
    if total == 0:
        return {"total": 0, "overall_accuracy": 0.0, "per_class": {}, "confusion_matrix": {}}

    unique_classes = sorted(list(set(y_true) | set(y_pred))) if not classes else sorted(classes)
    confusion: Dict[str, Dict[str, int]] = {c: {c2: 0 for c2 in unique_classes} for c in unique_classes}

    correct = 0
    for true_val, pred_val in zip(y_true, y_pred):
        if true_val == pred_val:
            correct += 1
        if true_val in confusion and pred_val in confusion[true_val]:
            confusion[true_val][pred_val] += 1

    overall_accuracy = round(correct / total, 4)

    per_class: Dict[str, Dict[str, Any]] = {}
    for c in unique_classes:
        tp = confusion[c].get(c, 0)
        fn = sum(confusion[c][other] for other in unique_classes if other != c)
        fp = sum(confusion[other].get(c, 0) for other in unique_classes if other != c)

        precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
        recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
        f1 = (
            round(2 * (precision * recall) / (precision + recall), 4)
            if (precision + recall) > 0
            else 0.0
        )
        support = tp + fn

        per_class[c] = {
            "support": support,
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
        }

    return {
        "total_samples": total,
        "correct_predictions": correct,
        "overall_accuracy": overall_accuracy,
        "per_class": per_class,
        "confusion_matrix": confusion,
    }


def calculate_retrieval_metrics(
    retrieved_doc_ids: List[List[str]],
    ground_truth_doc_ids: List[List[str]],
    k_values: Tuple[int, ...] = (1, 3, 5),
) -> Dict[str, Any]:
    """
    Calculate Recall@K, Precision@K, and MRR for document retrieval evaluations.
    """
    num_queries = len(ground_truth_doc_ids)
    if num_queries == 0:
        return {"queries_count": 0}

    results: Dict[str, Any] = {
        "queries_count": num_queries,
        "empty_retrieval_count": 0,
        "reciprocal_ranks": [],
        "mean_reciprocal_rank": 0.0,
    }

    for k in k_values:
        results[f"recall@{k}"] = []
        results[f"precision@{k}"] = []

    for retrieved, gt in zip(retrieved_doc_ids, ground_truth_doc_ids):
        if not retrieved:
            results["empty_retrieval_count"] += 1

        gt_set = set(gt)
        if not gt_set:
            continue

        # Reciprocal rank (first relevant item)
        rr = 0.0
        for rank, doc_id in enumerate(retrieved, start=1):
            if doc_id in gt_set:
                rr = 1.0 / rank
                break
        results["reciprocal_ranks"].append(rr)

        # Precision@K and Recall@K
        for k in k_values:
            top_k = retrieved[:k]
            relevant_in_top_k = sum(1 for doc_id in top_k if doc_id in gt_set)
            prec_k = relevant_in_top_k / k if k > 0 else 0.0
            rec_k = relevant_in_top_k / len(gt_set) if len(gt_set) > 0 else 0.0
            results[f"precision@{k}"].append(prec_k)
            results[f"recall@{k}"].append(rec_k)

    # Aggregate averages
    results["mean_reciprocal_rank"] = (
        round(sum(results["reciprocal_ranks"]) / len(results["reciprocal_ranks"]), 4)
        if results["reciprocal_ranks"]
        else 0.0
    )
    for k in k_values:
        p_list = results[f"precision@{k}"]
        r_list = results[f"recall@{k}"]
        results[f"mean_precision@{k}"] = round(sum(p_list) / len(p_list), 4) if p_list else 0.0
        results[f"mean_recall@{k}"] = round(sum(r_list) / len(r_list), 4) if r_list else 0.0
        # Clean up per-query raw lists from top-level summary
        del results[f"precision@{k}"]
        del results[f"recall@{k}"]

    del results["reciprocal_ranks"]
    results["empty_retrieval_rate"] = round(results["empty_retrieval_count"] / num_queries, 4)
    return results


def calculate_iou(boxA: List[float], boxB: List[float]) -> float:
    """
    Calculate Intersection over Union (IoU) between two bounding boxes.
    Boxes formatted as [x1, y1, x2, y2].
    """
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0.0, xB - xA) * max(0.0, yB - yA)
    boxAArea = max(0.0, boxA[2] - boxA[0]) * max(0.0, boxA[3] - boxA[1])
    boxBArea = max(0.0, boxB[2] - boxB[0]) * max(0.0, boxB[3] - boxB[1])

    unionArea = boxAArea + boxBArea - interArea
    if unionArea <= 0:
        return 0.0
    return round(interArea / unionArea, 4)
