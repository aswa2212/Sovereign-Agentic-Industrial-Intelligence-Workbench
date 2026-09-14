"""
SIH26117 — Phase 14: RAG Retrieval Evaluation & Embedding Comparison

Evaluates:
1. Phase 6 SovereignRetriever on the labeled MRPL SOP benchmark dataset.
   - Evaluates Recall@K, Precision@K, and MRR against ground truth chunks.
   - Evaluates citation correctness (source document, page number, chunk ID).
   - Evaluates empty retrieval / noise suppression for out-of-domain queries.
2. Embedding Model Comparison (nomic-embed-text vs bge-m3 via local Ollama).
   - Embedding generation latency
   - Vector dimensions
   - Cosine similarity discrimination between matching vs unrelated queries
"""

import json
import math
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple

from app.services.rag.retriever import SovereignRetriever
from experiments.evaluation.config import get_ollama_base_url
from experiments.evaluation.datasets import RAG_BENCHMARK_DATASET
from experiments.evaluation.metrics import calculate_latency_stats, calculate_retrieval_metrics


def run_rag_retrieval_evaluation() -> Dict[str, Any]:
    """
    Evaluate existing SovereignRetriever without modifying knowledge-store contents.
    Runs retrieval asynchronously/synchronously across the labeled RAG benchmark dataset.
    """
    import asyncio

    retriever = SovereignRetriever()
    dataset = RAG_BENCHMARK_DATASET

    retrieved_chunk_ids_list: List[List[str]] = []
    ground_truth_chunk_ids_list: List[List[str]] = []
    query_latencies: List[float] = []
    query_eval_records: List[Dict[str, Any]] = []

    citation_correct_count = 0
    page_correct_count = 0
    in_domain_queries_count = 0

    async def _evaluate_all():
        nonlocal citation_correct_count, page_correct_count, in_domain_queries_count
        for item in dataset:
            q_id = item["query_id"]
            query = item["query"]
            gt_chunks = item["ground_truth_chunk_ids"]
            exp_doc = item["expected_source_doc"]
            exp_page = item["expected_page"]

            is_in_domain = len(gt_chunks) > 0
            if is_in_domain:
                in_domain_queries_count += 1

            t0 = time.perf_counter()
            retrieved_chunks, citations = await retriever.retrieve_with_citations(
                query=query,
                top_k=3,
                threshold=0.50,
            )
            lat = time.perf_counter() - t0
            query_latencies.append(lat)

            retrieved_ids = [c.chunk_id for c in retrieved_chunks]
            retrieved_chunk_ids_list.append(retrieved_ids)
            ground_truth_chunk_ids_list.append(gt_chunks)

            # Check citation correctness
            doc_matched = False
            page_matched = False
            if citations and exp_doc:
                for cit in citations:
                    if cit.source_document == exp_doc:
                        doc_matched = True
                    if exp_page and cit.page_number == exp_page:
                        page_matched = True

            if doc_matched:
                citation_correct_count += 1
            if page_matched:
                page_correct_count += 1

            query_eval_records.append({
                "query_id": q_id,
                "query": query,
                "is_in_domain": is_in_domain,
                "retrieved_count": len(retrieved_chunks),
                "retrieved_chunk_ids": retrieved_ids,
                "ground_truth_chunk_ids": gt_chunks,
                "citation_doc_matched": doc_matched,
                "page_matched": page_matched,
                "latency_sec": round(lat, 4),
            })

    asyncio.run(_evaluate_all())

    # Retrieval metrics calculation (Recall@K, Precision@K, MRR, empty retrieval rate)
    retrieval_metrics = calculate_retrieval_metrics(
        retrieved_doc_ids=retrieved_chunk_ids_list,
        ground_truth_doc_ids=ground_truth_chunk_ids_list,
        k_values=(1, 2, 3),
    )
    latency_stats = calculate_latency_stats(query_latencies)

    citation_accuracy = (
        round(citation_correct_count / in_domain_queries_count, 4)
        if in_domain_queries_count > 0
        else 0.0
    )
    page_accuracy = (
        round(page_correct_count / in_domain_queries_count, 4)
        if in_domain_queries_count > 0
        else 0.0
    )

    return {
        "benchmark_name": "rag_retrieval_evaluation",
        "total_queries": len(dataset),
        "in_domain_queries": in_domain_queries_count,
        "out_of_domain_queries": len(dataset) - in_domain_queries_count,
        "retrieval_metrics": retrieval_metrics,
        "citation_doc_accuracy": citation_accuracy,
        "citation_page_accuracy": page_accuracy,
        "latency_stats": latency_stats,
        "query_details": query_eval_records,
    }


def _ollama_embed(model_name: str, text: str) -> Tuple[Optional[List[float]], float, Optional[str]]:
    """Compute embedding using local Ollama endpoint."""
    base_url = get_ollama_base_url()
    url = f"{base_url}/api/embeddings"
    payload = {"model": model_name, "prompt": text}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            elapsed = time.perf_counter() - t0
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("embedding"), elapsed, None
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return None, elapsed, str(e)


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if len(vec1) != len(vec2) or not vec1:
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 < 1e-12 or norm2 < 1e-12:
        return 0.0
    return round(dot / (norm1 * norm2), 4)


def run_embedding_comparison_benchmark() -> Dict[str, Any]:
    """
    Compare locally available embedding models: nomic-embed-text:latest vs bge-m3:latest.
    Evaluates:
    - Vector dimensions
    - Query embedding latency (mean, median)
    - Semantic discrimination between paired industrial texts vs noise
    """
    models_to_test = ["nomic-embed-text:latest", "bge-m3:latest"]
    sample_texts = [
        "What is the minimum retirement wall thickness for Class 150 piping?",
        "ASTM A106 Grade B carbon steel minimum allowable wall thickness is 3.2 mm.",
        "Recipe for baking chocolate chip cookies in an electric oven.",
    ]

    model_results: List[Dict[str, Any]] = []

    for model in models_to_test:
        latencies: List[float] = []
        vectors: List[Optional[List[float]]] = []
        errors: List[str] = []

        for txt in sample_texts:
            vec, lat, err = _ollama_embed(model, txt)
            latencies.append(lat)
            vectors.append(vec)
            if err:
                errors.append(err)

        if any(v is None for v in vectors):
            model_results.append({
                "model": model,
                "status": "FAILED",
                "errors": errors,
            })
            continue

        sim_matched = _cosine_similarity(vectors[0], vectors[1])
        sim_unrelated = _cosine_similarity(vectors[0], vectors[2])
        discrimination_margin = round(sim_matched - sim_unrelated, 4)

        lat_stats = calculate_latency_stats(latencies)

        model_results.append({
            "model": model,
            "status": "AVAILABLE",
            "dimension": len(vectors[0]),
            "latency_stats": lat_stats,
            "semantic_similarity_matched": sim_matched,
            "semantic_similarity_unrelated": sim_unrelated,
            "discrimination_margin": discrimination_margin,
            "discrimination_effective": bool(discrimination_margin > 0.25),
        })

    return {
        "benchmark_name": "embedding_comparison_benchmark",
        "models_evaluated": model_results,
    }
