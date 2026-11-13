"""MNEMOS Empirical Benchmark Runner.

Evaluates 5 retrieval baselines against a 100-query benchmark corpus covering:
1. Semantic memory retrieval
2. Historical & temporal queries
3. Fact updates & contradiction resolution
4. Multi-hop relationship graph traversal
5. Outdated vs. current state disambiguation
"""

import asyncio
import csv
import json
import os
import platform
import random
import sys
import time
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.abspath("src"))

from mnemos.core.security import hash_api_key
from mnemos.db.models import APIKey, Tenant
from mnemos.db.session import AsyncSessionLocal, init_db
from mnemos.ingestion.pipeline import IngestionItem, IngestionPipeline
from mnemos.retrieval.hybrid import HybridRetrievalEngine, HybridRetrievalRequest

# Ensure deterministic execution
random.seed(42)
np.random.seed(42)


async def setup_benchmark_tenant(session, tenant_id: str):
    t = await session.get(Tenant, tenant_id)
    if not t:
        tenant = Tenant(id=tenant_id, name="Benchmark Tenant", config={})
        session.add(tenant)
        key = APIKey(
            id=f"key_{tenant_id}",
            tenant_id=tenant_id,
            key_hash=hash_api_key(f"mnk_bench_{tenant_id}"),
            key_prefix="mnk_bench_",
            name="bench_key",
            rate_limit=50000,
        )
        session.add(key)
        await session.commit()


async def run_benchmarks():
    print("=" * 88)
    print("MNEMOS COMPREHENSIVE BENCHMARK SUITE — REAL EMPIRICAL EVALUATION (100 QUERIES)")
    print("=" * 88)

    await init_db()

    tenant_id = f"bench_run_{int(time.time())}"
    dataset_path = "benchmarks/datasets/temporal_qa.json"
    results_dir = "benchmarks/results"
    os.makedirs(results_dir, exist_ok=True)

    with open(dataset_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    categories = [
        "semantic_retrieval",
        "historical_temporal",
        "fact_updates_contradictions",
        "multihop_graph",
        "outdated_vs_current",
    ]

    async with AsyncSessionLocal() as session:
        await setup_benchmark_tenant(session, tenant_id)

        # 1. Ingestion Phase & Throughput Measurement
        print(f"\n[1/4] Ingesting memory corpus into isolated tenant '{tenant_id}'...")
        ingest_start = time.perf_counter()
        total_ingested = 0
        seen_contents = set()

        for case in cases:
            for seed in case.get("facts_to_seed", []):
                content = seed["content"]
                if content in seen_contents:
                    continue
                seen_contents.add(content)

                vf = None
                if "valid_from" in seed:
                    vf = datetime.fromisoformat(seed["valid_from"].replace("Z", "+00:00"))

                item = IngestionItem(
                    content=content,
                    memory_type="observation",
                    valid_from=vf,
                    confidence=seed.get("confidence", 1.0),
                )
                await IngestionPipeline.ingest(session, tenant_id, item)
                total_ingested += 1

        await session.commit()
        ingest_duration = time.perf_counter() - ingest_start
        ingest_tps = total_ingested / max(0.0001, ingest_duration)
        print(
            f"-> Ingested {total_ingested} unique memories in {ingest_duration:.3f}s "
            f"({ingest_tps:.1f} items/sec throughput)"
        )

        # 2. Baselines Specification
        baselines = [
            ("keyword_only", {"vector": False, "keyword": True, "graph": False, "temporal": False}),
            ("vector_only", {"vector": True, "keyword": False, "graph": False, "temporal": False}),
            ("graph_only", {"vector": False, "keyword": False, "graph": True, "temporal": False}),
            ("hybrid_no_temporal", {"vector": True, "keyword": True, "graph": True, "temporal": False}),
            ("full_mnemos", {"vector": True, "keyword": True, "graph": True, "temporal": True}),
        ]

        print(f"\n[2/4] Evaluating {len(baselines)} baselines across {len(cases)} queries (5 categories)...")

        baseline_overall_reports = []
        category_breakdown_reports = []

        for b_name, flags in baselines:
            print(f"  -> Testing baseline: {b_name} ...", end="", flush=True)
            latencies_ms = []
            recalls_1 = []
            recalls_5 = []
            mrrs = []
            temporal_accs = []

            # Per-category tracking
            cat_metrics = {cat: {"r1": [], "r5": [], "mrr": [], "tacc": [], "lat": []} for cat in categories}

            for case in cases:
                target = case["expected_target"].lower()
                invalid_target = case.get("invalid_outdated_target")
                if invalid_target:
                    invalid_target = invalid_target.lower()

                query = case["query"]
                cat = case.get("category", "general")

                vt = None
                if flags["temporal"] and "valid_at" in case and case["valid_at"]:
                    vt = datetime.fromisoformat(case["valid_at"].replace("Z", "+00:00"))

                req = HybridRetrievalRequest(
                    query=query,
                    top_k=5,
                    valid_at=vt,
                    enable_vector=flags["vector"],
                    enable_keyword=flags["keyword"],
                    enable_graph=flags["graph"],
                    enable_temporal_filtering=flags["temporal"],
                )

                t0 = time.perf_counter()
                resp = await HybridRetrievalEngine.search(session, tenant_id, req)
                lat_ms = (time.perf_counter() - t0) * 1000.0

                latencies_ms.append(lat_ms)
                retrieved_texts = [m.content.lower() for m in resp.memories]

                # Metric 1: Recall@1
                r1 = 1.0 if (retrieved_texts and target in retrieved_texts[0]) else 0.0

                # Metric 2: Recall@5
                r5 = 1.0 if any(target in t for t in retrieved_texts[:5]) else 0.0

                # Metric 3: MRR
                mrr = 0.0
                for rank, txt in enumerate(retrieved_texts[:5], start=1):
                    if target in txt:
                        mrr = 1.0 / rank
                        break

                # Metric 4: Temporal Accuracy
                # For temporal/contradiction/current queries with an invalid outdated target:
                # Top result must match expected target AND NOT match outdated target.
                if invalid_target:
                    if retrieved_texts and target in retrieved_texts[0] and invalid_target not in retrieved_texts[0]:
                        tacc = 1.0
                    else:
                        tacc = 0.0
                else:
                    tacc = r1

                recalls_1.append(r1)
                recalls_5.append(r5)
                mrrs.append(mrr)
                temporal_accs.append(tacc)

                if cat in cat_metrics:
                    cat_metrics[cat]["r1"].append(r1)
                    cat_metrics[cat]["r5"].append(r5)
                    cat_metrics[cat]["mrr"].append(mrr)
                    cat_metrics[cat]["tacc"].append(tacc)
                    cat_metrics[cat]["lat"].append(lat_ms)

            # Overall Percentiles
            p50 = float(np.percentile(latencies_ms, 50))
            p95 = float(np.percentile(latencies_ms, 95))
            p99 = float(np.percentile(latencies_ms, 99))

            b_rep = {
                "baseline": b_name,
                "queries_evaluated": len(cases),
                "recall@1": round(float(np.mean(recalls_1)), 4),
                "recall@5": round(float(np.mean(recalls_5)), 4),
                "mrr": round(float(np.mean(mrrs)), 4),
                "temporal_accuracy": round(float(np.mean(temporal_accs)), 4),
                "latency_p50_ms": round(p50, 2),
                "latency_p95_ms": round(p95, 2),
                "latency_p99_ms": round(p99, 2),
            }
            baseline_overall_reports.append(b_rep)

            # Record category reports
            for cat in categories:
                c_data = cat_metrics[cat]
                category_breakdown_reports.append({
                    "baseline": b_name,
                    "category": cat,
                    "queries": len(c_data["r1"]),
                    "recall@1": round(float(np.mean(c_data["r1"])), 4) if c_data["r1"] else 0.0,
                    "recall@5": round(float(np.mean(c_data["r5"])), 4) if c_data["r5"] else 0.0,
                    "mrr": round(float(np.mean(c_data["mrr"])), 4) if c_data["mrr"] else 0.0,
                    "temporal_accuracy": round(float(np.mean(c_data["tacc"])), 4) if c_data["tacc"] else 0.0,
                    "latency_p50_ms": round(float(np.percentile(c_data["lat"], 50)), 2) if c_data["lat"] else 0.0,
                })

            print(f" done (Recall@5={b_rep['recall@5']:.2f}, P50={b_rep['latency_p50_ms']}ms)")

        # 3. Print Results Summary Table
        print("\n[3/4] Overall Results Across All 100 Queries:")
        header = f"{'Baseline':<22} | {'Recall@1':<8} | {'Recall@5':<8} | {'MRR':<6} | {'TemporalAcc':<11} | {'P50 (ms)':<8} | {'P95 (ms)':<8} | {'P99 (ms)':<8}"
        print("-" * len(header))
        print(header)
        print("-" * len(header))
        for rep in baseline_overall_reports:
            print(
                f"{rep['baseline']:<22} | "
                f"{rep['recall@1']:<8.4f} | "
                f"{rep['recall@5']:<8.4f} | "
                f"{rep['mrr']:<6.4f} | "
                f"{rep['temporal_accuracy']:<11.4f} | "
                f"{rep['latency_p50_ms']:<8.2f} | "
                f"{rep['latency_p95_ms']:<8.2f} | "
                f"{rep['latency_p99_ms']:<8.2f}"
            )
        print("-" * len(header))

        # 4. Print Per-Category Breakdown
        print("\n[4/4] Per-Category Performance Breakdown:")
        cat_header = f"{'Category':<28} | {'Baseline':<20} | {'Recall@1':<8} | {'Recall@5':<8} | {'MRR':<6} | {'TemporalAcc':<11} | {'P50 (ms)':<8}"
        print("-" * len(cat_header))
        print(cat_header)
        print("-" * len(cat_header))
        for r in category_breakdown_reports:
            print(
                f"{r['category']:<28} | "
                f"{r['baseline']:<20} | "
                f"{r['recall@1']:<8.4f} | "
                f"{r['recall@5']:<8.4f} | "
                f"{r['mrr']:<6.4f} | "
                f"{r['temporal_accuracy']:<11.4f} | "
                f"{r['latency_p50_ms']:<8.2f}"
            )
        print("-" * len(cat_header))

        # Save Overall JSON
        out_json_path = os.path.join(results_dir, "benchmark_report.json")
        system_meta = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "os": platform.system(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "total_queries": len(cases),
            "total_memories_seeded": total_ingested,
            "ingestion_throughput_tps": round(ingest_tps, 2),
            "categories": categories,
            "baselines": baseline_overall_reports,
            "category_breakdown": category_breakdown_reports,
        }
        with open(out_json_path, "w", encoding="utf-8") as f:
            json.dump(system_meta, f, indent=2)
        print(f"\n[Saved JSON]: {out_json_path}")

        # Save Overall CSV
        out_csv_path = os.path.join(results_dir, "benchmark_report.csv")
        with open(out_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "baseline",
                    "queries_evaluated",
                    "recall@1",
                    "recall@5",
                    "mrr",
                    "temporal_accuracy",
                    "latency_p50_ms",
                    "latency_p95_ms",
                    "latency_p99_ms",
                ],
            )
            writer.writeheader()
            for rep in baseline_overall_reports:
                writer.writerow(rep)
        print(f"[Saved CSV]:  {out_csv_path}")

        # Save Category Breakdown CSV
        out_cat_csv_path = os.path.join(results_dir, "benchmark_categories.csv")
        with open(out_cat_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "baseline",
                    "category",
                    "queries",
                    "recall@1",
                    "recall@5",
                    "mrr",
                    "temporal_accuracy",
                    "latency_p50_ms",
                ],
            )
            writer.writeheader()
            for r in category_breakdown_reports:
                writer.writerow(r)
        print(f"[Saved Category CSV]: {out_cat_csv_path}")
        print("=" * 88)


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
