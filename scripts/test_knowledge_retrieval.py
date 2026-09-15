"""
SIH26117 — Controlled Industrial Knowledge Corpus Retrieval Benchmark
Executes an 8-query evaluation against the 768-d Nomic-indexed sovereign vector store.

Queries 1-7: Domain queries covering C-101 and refinery inspection standards.
Query 8: Out-of-domain query testing similarity threshold suppression.
"""

import asyncio
import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.app.services.rag.embeddings import OllamaEmbeddingProvider
from backend.app.services.rag.retriever import SovereignRetriever
from backend.app.services.rag.vector_store import LocalJsonVectorStore

TEST_QUERIES = [
    {
        "id": 1,
        "query": "minimum retirement thickness for C-101 atmospheric column shell",
        "expected_docs": ["08_Equipment_Retirement_Criteria.pdf", "05_C101_Equipment_Record.pdf"],
        "expected_terms": ["8.0 mm", "retirement", "shell"],
        "is_ood": False,
    },
    {
        "id": 2,
        "query": "C-101 design pressure and design temperature operating envelope",
        "expected_docs": ["09_Process_Equipment_Operating_Limits.pdf", "05_C101_Equipment_Record.pdf"],
        "expected_terms": ["0.35", "380", "operating"],
        "is_ood": False,
    },
    {
        "id": 3,
        "query": "ultrasonic thickness gauge scanning procedure and grid spacing",
        "expected_docs": ["03_Thickness_Monitoring_Procedure.pdf", "01_C101_Inspection_Procedure.pdf"],
        "expected_terms": ["grid", "50mm", "ultrasonic"],
        "is_ood": False,
    },
    {
        "id": 4,
        "query": "short term and long term corrosion rate calculation formula",
        "expected_docs": ["07_Corrosion_Rate_Calculation_Guide.pdf"],
        "expected_terms": ["formula", "corrosion rate", "t_initial"],
        "is_ood": False,
    },
    {
        "id": 5,
        "query": "corrosion rate threshold for Class 1 critical inspection finding",
        "expected_docs": ["10_Inspection_Finding_Classification.pdf", "02_Corrosion_Assessment_Guideline.pdf"],
        "expected_terms": ["class 1", "critical", "0.40"],
        "is_ood": False,
    },
    {
        "id": 6,
        "query": "C-101 historical thickness survey readings at nozzle N1",
        "expected_docs": ["06_C101_Thickness_History.pdf"],
        "expected_terms": ["n1", "10.4", "feed inlet"],
        "is_ood": False,
    },
    {
        "id": 7,
        "query": "inspection interval determination based on remaining life half life rule",
        "expected_docs": ["04_Inspection_Interval_Guideline.pdf"],
        "expected_terms": ["half-life", "interval", "5 years"],
        "is_ood": False,
    },
    {
        "id": 8,
        "query": "canteen lunch menu subsidy policy and chocolate donut ingredients",
        "expected_docs": [],
        "expected_terms": [],
        "is_ood": True,
    },
]


async def run_benchmark():
    print("=" * 80)
    print("SIH26117 — SOVEREIGN KNOWLEDGE RETRIEVAL BENCHMARK (8-QUERY EVALUATION)")
    print("=" * 80)

    store = LocalJsonVectorStore(index_id="default", storage_dir=ROOT_DIR / "data" / "knowledge")
    provider = OllamaEmbeddingProvider(dim=768)
    retriever = SovereignRetriever(
        vector_store=store,
        embedding_provider=provider,
        default_top_k=3,
        default_threshold=0.60,
    )

    domain_hits_r1 = 0
    domain_hits_r3 = 0
    mrr_sum = 0.0
    ood_suppressed = 0
    total_domain_queries = sum(1 for q in TEST_QUERIES if not q["is_ood"])
    results_table = []

    for q in TEST_QUERIES:
        query_text = q["query"]
        is_ood = q["is_ood"]

        chunks = await retriever.retrieve(query=query_text, top_k=3, threshold=0.58)

        if is_ood:
            # For OOD query, success means 0 results pass high threshold (0.65) or low similarity scores
            high_conf_chunks = [c for c in chunks if c.similarity_score >= 0.65]
            if len(high_conf_chunks) == 0:
                ood_suppressed += 1
                status = "SUPPRESSED (Pass)"
            else:
                status = f"FAILED SUPPRESSION ({len(high_conf_chunks)} chunks >= 0.65)"

            results_table.append({
                "id": q["id"],
                "query": query_text[:45] + "...",
                "top_doc": chunks[0].source_document if chunks else "NONE",
                "top_score": chunks[0].similarity_score if chunks else 0.0,
                "r1": "N/A (OOD)",
                "r3": "N/A (OOD)",
                "status": status,
            })
            continue

        # Domain query evaluation
        top_docs = [c.source_document for c in chunks]
        top1_doc = top_docs[0] if top_docs else "NONE"
        top1_score = chunks[0].similarity_score if chunks else 0.0

        r1 = 1 if any(exp in top1_doc for exp in q["expected_docs"]) else 0
        r3 = 1 if any(any(exp in td for exp in q["expected_docs"]) for td in top_docs) else 0

        # Calculate reciprocal rank
        rr = 0.0
        for rank, td in enumerate(top_docs, 1):
            if any(exp in td for exp in q["expected_docs"]):
                rr = 1.0 / rank
                break

        domain_hits_r1 += r1
        domain_hits_r3 += r3
        mrr_sum += rr

        status = "HIT" if r1 == 1 else ("HIT@3" if r3 == 1 else "MISS")
        results_table.append({
            "id": q["id"],
            "query": query_text[:45] + "...",
            "top_doc": top1_doc,
            "top_score": top1_score,
            "r1": r1,
            "r3": r3,
            "status": status,
        })

    # Display results table
    print(f"{'#':<2} | {'Query':<48} | {'Top Retrieved Doc':<34} | {'Score':<6} | {'Status'}")
    print("-" * 115)
    for row in results_table:
        print(f"{row['id']:<2} | {row['query']:<48} | {row['top_doc']:<34} | {row['top_score']:<6.4f} | {row['status']}")
    print("-" * 115)

    recall_at_1 = domain_hits_r1 / total_domain_queries
    recall_at_3 = domain_hits_r3 / total_domain_queries
    mrr = mrr_sum / total_domain_queries
    ood_rate = ood_suppressed / 1.0

    print("\nBENCHMARK METRICS SUMMARY:")
    print(f"  Recall@1 (Domain Queries):      {recall_at_1 * 100:.1f}% ({domain_hits_r1}/{total_domain_queries})")
    print(f"  Recall@3 (Domain Queries):      {recall_at_3 * 100:.1f}% ({domain_hits_r3}/{total_domain_queries})")
    print(f"  MRR (Mean Reciprocal Rank):     {mrr:.4f}")
    print(f"  Out-of-Domain Suppression Rate: {ood_rate * 100:.1f}% ({ood_suppressed}/1)")
    print("=" * 80)

    # Save benchmark report to data/knowledge/retrieval_benchmark.json
    benchmark_report = {
        "metrics": {
            "recall_at_1": recall_at_1,
            "recall_at_3": recall_at_3,
            "mrr": mrr,
            "out_of_domain_suppression_rate": ood_rate,
        },
        "query_results": results_table,
    }
    out_path = ROOT_DIR / "data" / "knowledge" / "retrieval_benchmark.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_report, f, indent=2)
    print(f"Report saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
