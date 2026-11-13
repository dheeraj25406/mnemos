"""MNEMOS Statistically Rigorous Retrieval Benchmark Runner.

Evaluates 6 retrieval strategies across 8 distinct memory categories on held-out test queries:
1. Vector-only
2. Keyword-only (BM25)
3. Graph-only (Recursive CTE Subgraph)
4. Vector + Keyword
5. Vector + Graph
6. Full Hybrid RRF (Vector + Keyword + Graph + Bitemporal)

Measures:
- Recall@1, Recall@5, Recall@10
- Precision@5
- MRR (Mean Reciprocal Rank)
- nDCG@5 (Normalized Discounted Cumulative Gain)
- Latency (P50, P95, P99 in ms)
- 95% Bootstrap Confidence Intervals (1000 resamples)
- Absolute and relative gains vs. Vector-only baseline
- Statistical significance (paired empirical p-values)
- Per-category performance breakdown
"""

import argparse
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


def compute_dcg(relevances: list[float], k: int = 5) -> float:
    """Compute Discounted Cumulative Gain at rank k."""
    dcg = 0.0
    for i, rel in enumerate(relevances[:k], start=1):
        dcg += (2.0**rel - 1.0) / np.log2(i + 1)
    return dcg


def compute_ndcg(retrieved_rels: list[float], ideal_rels: list[float], k: int = 5) -> float:
    """Compute Normalized Discounted Cumulative Gain at rank k."""
    dcg = compute_dcg(retrieved_rels, k=k)
    idcg = compute_dcg(sorted(ideal_rels, reverse=True), k=k)
    if idcg <= 0.0:
        return 1.0 if dcg == 0.0 else 0.0
    return dcg / idcg


def bootstrap_ci(
    values: list[float],
    n_resamples: int = 1000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Calculate empirical mean and bootstrap confidence interval."""
    if not values:
        return 0.0, 0.0, 0.0
    arr = np.array(values, dtype=np.float64)
    mean_val = float(np.mean(arr))
    rng = np.random.default_rng(seed)
    indices = rng.choice(len(arr), size=(n_resamples, len(arr)), replace=True)
    resampled_means = np.mean(arr[indices], axis=1)
    alpha = (1.0 - ci_level) / 2.0
    lower = float(np.percentile(resampled_means, 100 * alpha))
    upper = float(np.percentile(resampled_means, 100 * (1.0 - alpha)))
    return mean_val, lower, upper


def bootstrap_paired_delta(
    test_vals: list[float],
    base_vals: list[float],
    n_resamples: int = 1000,
    seed: int = 42,
) -> tuple[float, float, float, float]:
    """Compute paired difference (test - base), 95% CI, and empirical p-value."""
    t_arr = np.array(test_vals, dtype=np.float64)
    b_arr = np.array(base_vals, dtype=np.float64)
    diff = t_arr - b_arr
    mean_diff = float(np.mean(diff))

    rng = np.random.default_rng(seed)
    indices = rng.choice(len(diff), size=(n_resamples, len(diff)), replace=True)
    resampled_diffs = np.mean(diff[indices], axis=1)

    lower = float(np.percentile(resampled_diffs, 2.5))
    upper = float(np.percentile(resampled_diffs, 97.5))

    # Two-sided empirical p-value
    p_val = float(2.0 * min(np.mean(resampled_diffs <= 0), np.mean(resampled_diffs >= 0)))
    p_val = min(1.0, max(0.0001, p_val))
    return mean_diff, lower, upper, p_val


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


async def run_benchmarks(
    dataset_path: str = "benchmarks/datasets/retrieval_benchmark_240.json",
    split: str = "test",
    output_path: str = "benchmarks/results/benchmark_results.json",
    tag: str = "default",
):
    print("=" * 100)
    print(f"MNEMOS EMPIRICAL RETRIEVAL BENCHMARK — {split.upper()} SPLIT EVALUATION (TAG: {tag})")
    print("=" * 100)

    await init_db()

    tenant_id = f"bench_{int(time.time())}"
    results_dir = os.path.dirname(output_path) or "benchmarks/results"
    os.makedirs(results_dir, exist_ok=True)

    with open(dataset_path, "r", encoding="utf-8") as f:
        all_cases = json.load(f)

    if split == "all":
        cases = all_cases
    else:
        cases = [c for c in all_cases if c.get("split") == split]

    print(f"Loaded {len(cases)} cases for split='{split}' from '{dataset_path}'")

    categories = sorted(list(set(c["category"] for c in cases)))

    async with AsyncSessionLocal() as session:
        await setup_benchmark_tenant(session, tenant_id)

        # 1. Ingestion Phase
        print(f"\n[1/4] Ingesting memory corpus into isolated tenant '{tenant_id}'...")
        ingest_start = time.perf_counter()
        total_ingested = 0
        seen_contents = set()

        # Ingest all seeded facts from the full dataset so the corpus is rich and complete
        for c in all_cases:
            for seed in c.get("facts_to_seed", []):
                content = seed["content"]
                if content in seen_contents:
                    continue
                seen_contents.add(content)

                vf = None
                if "valid_from" in seed:
                    vf = datetime.fromisoformat(seed["valid_from"].replace("Z", "+00:00"))

                vt = None
                if "valid_to" in seed:
                    vt = datetime.fromisoformat(seed["valid_to"].replace("Z", "+00:00"))

                item = IngestionItem(
                    content=content,
                    memory_type="observation",
                    valid_from=vf,
                    valid_to=vt,
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

        # 2. 6 Retrieval Strategies Specification
        strategies = [
            ("vector_only", {"vector": True, "keyword": False, "graph": False, "temporal": False}),
            ("keyword_only", {"vector": False, "keyword": True, "graph": False, "temporal": False}),
            ("graph_only", {"vector": False, "keyword": False, "graph": True, "temporal": False}),
            ("vector_keyword", {"vector": True, "keyword": True, "graph": False, "temporal": False}),
            ("vector_graph", {"vector": True, "keyword": False, "graph": True, "temporal": False}),
            ("full_hybrid_rrf", {"vector": True, "keyword": True, "graph": True, "temporal": True}),
        ]

        print(f"\n[2/4] Evaluating {len(strategies)} strategies across {len(cases)} held-out queries...")

        per_strategy_raw: dict[str, dict[str, list[float]]] = {}
        per_strategy_by_cat: dict[str, dict[str, dict[str, list[float]]]] = {}

        for s_name, flags in strategies:
            print(f"  -> Testing strategy: {s_name:<18} ...", end="", flush=True)

            metrics_collector = {
                "r1": [],
                "r5": [],
                "r10": [],
                "p5": [],
                "mrr": [],
                "ndcg5": [],
                "lat": [],
            }
            cat_collector = {
                cat: {k: [] for k in metrics_collector.keys()} for cat in categories
            }

            for case in cases:
                target = case["expected_target"].lower()
                invalid_target = case.get("invalid_outdated_target")
                if invalid_target:
                    invalid_target = invalid_target.lower()

                query = case["query"]
                cat = case.get("category", "general")

                vt = None
                if flags["temporal"] and case.get("valid_at"):
                    vt = datetime.fromisoformat(case["valid_at"].replace("Z", "+00:00"))

                req = HybridRetrievalRequest(
                    query=query,
                    top_k=10,
                    valid_at=vt,
                    enable_vector=flags["vector"],
                    enable_keyword=flags["keyword"],
                    enable_graph=flags["graph"],
                    enable_temporal_filtering=flags["temporal"],
                )

                t0 = time.perf_counter()
                resp = await HybridRetrievalEngine.search(session, tenant_id, req)
                lat_ms = (time.perf_counter() - t0) * 1000.0

                retrieved_texts = [m.content.lower() for m in resp.memories]

                # Relevance Grading for this query
                # Target memory matching target (and not containing invalid_target) = 2
                # Memory containing only invalid_target = 0
                # Other memory = 0
                retrieved_grades = []
                for txt in retrieved_texts:
                    if invalid_target and invalid_target in txt:
                        retrieved_grades.append(0.0)
                    elif target in txt:
                        retrieved_grades.append(2.0)
                    else:
                        retrieved_grades.append(0.0)

                # Ideal relevance for this query: at least 1 canonical item of grade 2
                ideal_grades = [2.0]

                # Metric 1: Recall@1
                r1 = 1.0 if (retrieved_grades and retrieved_grades[0] > 0) else 0.0

                # Metric 2: Recall@5
                r5 = 1.0 if any(g > 0 for g in retrieved_grades[:5]) else 0.0

                # Metric 3: Recall@10
                r10 = 1.0 if any(g > 0 for g in retrieved_grades[:10]) else 0.0

                # Metric 4: Precision@5
                p5 = sum(1.0 for g in retrieved_grades[:5] if g > 0) / 5.0

                # Metric 5: MRR
                mrr = 0.0
                for rank_idx, g in enumerate(retrieved_grades[:10], start=1):
                    if g > 0:
                        mrr = 1.0 / rank_idx
                        break

                # Metric 6: nDCG@5
                ndcg5 = compute_ndcg(retrieved_grades, ideal_grades, k=5)

                metrics_collector["r1"].append(r1)
                metrics_collector["r5"].append(r5)
                metrics_collector["r10"].append(r10)
                metrics_collector["p5"].append(p5)
                metrics_collector["mrr"].append(mrr)
                metrics_collector["ndcg5"].append(ndcg5)
                metrics_collector["lat"].append(lat_ms)

                if cat in cat_collector:
                    cat_collector[cat]["r1"].append(r1)
                    cat_collector[cat]["r5"].append(r5)
                    cat_collector[cat]["r10"].append(r10)
                    cat_collector[cat]["p5"].append(p5)
                    cat_collector[cat]["mrr"].append(mrr)
                    cat_collector[cat]["ndcg5"].append(ndcg5)
                    cat_collector[cat]["lat"].append(lat_ms)

            per_strategy_raw[s_name] = metrics_collector
            per_strategy_by_cat[s_name] = cat_collector

            p50 = float(np.percentile(metrics_collector["lat"], 50))
            r5_mean = float(np.mean(metrics_collector["r5"]))
            ndcg_mean = float(np.mean(metrics_collector["ndcg5"]))
            print(f" done (Recall@5={r5_mean:.3f}, nDCG@5={ndcg_mean:.3f}, P50={p50:.1f}ms)")

        # 3. Statistical Analysis & Confidence Intervals
        print("\n[3/4] Computing 95% Bootstrap Resampling Confidence Intervals (1000 resamples)...")
        vector_raw = per_strategy_raw["vector_only"]

        strategy_reports = []
        for s_name, _ in strategies:
            s_raw = per_strategy_raw[s_name]
            lat_arr = s_raw["lat"]
            p50 = float(np.percentile(lat_arr, 50))
            p95 = float(np.percentile(lat_arr, 95))
            p99 = float(np.percentile(lat_arr, 99))

            r1_m, r1_l, r1_u = bootstrap_ci(s_raw["r1"])
            r5_m, r5_l, r5_u = bootstrap_ci(s_raw["r5"])
            r10_m, r10_l, r10_u = bootstrap_ci(s_raw["r10"])
            p5_m, p5_l, p5_u = bootstrap_ci(s_raw["p5"])
            mrr_m, mrr_l, mrr_u = bootstrap_ci(s_raw["mrr"])
            ndcg_m, ndcg_l, ndcg_u = bootstrap_ci(s_raw["ndcg5"])

            # Paired deltas against vector_only
            delta_r5, d_r5_l, d_r5_u, p_r5 = bootstrap_paired_delta(s_raw["r5"], vector_raw["r5"])
            delta_mrr, d_mrr_l, d_mrr_u, p_mrr = bootstrap_paired_delta(s_raw["mrr"], vector_raw["mrr"])
            delta_ndcg, d_ndcg_l, d_ndcg_u, p_ndcg = bootstrap_paired_delta(s_raw["ndcg5"], vector_raw["ndcg5"])

            base_r5 = max(0.0001, np.mean(vector_raw["r5"]))
            rel_r5 = (r5_m - base_r5) / base_r5 * 100.0

            base_ndcg = max(0.0001, np.mean(vector_raw["ndcg5"]))
            rel_ndcg = (ndcg_m - base_ndcg) / base_ndcg * 100.0

            rep = {
                "strategy": s_name,
                "queries_evaluated": len(cases),
                "recall@1": round(r1_m, 4),
                "recall@1_ci95": [round(r1_l, 4), round(r1_u, 4)],
                "recall@5": round(r5_m, 4),
                "recall@5_ci95": [round(r5_l, 4), round(r5_u, 4)],
                "recall@10": round(r10_m, 4),
                "recall@10_ci95": [round(r10_l, 4), round(r10_u, 4)],
                "precision@5": round(p5_m, 4),
                "precision@5_ci95": [round(p5_l, 4), round(p5_u, 4)],
                "mrr": round(mrr_m, 4),
                "mrr_ci95": [round(mrr_l, 4), round(mrr_u, 4)],
                "ndcg@5": round(ndcg_m, 4),
                "ndcg@5_ci95": [round(ndcg_l, 4), round(ndcg_u, 4)],
                "delta_recall@5_vs_vector": round(delta_r5, 4),
                "delta_recall@5_ci95": [round(d_r5_l, 4), round(d_r5_u, 4)],
                "relative_recall@5_gain_pct": round(rel_r5, 2),
                "p_value_recall@5": round(p_r5, 4),
                "delta_ndcg@5_vs_vector": round(delta_ndcg, 4),
                "relative_ndcg@5_gain_pct": round(rel_ndcg, 2),
                "p_value_ndcg@5": round(p_ndcg, 4),
                "latency_p50_ms": round(p50, 2),
                "latency_p95_ms": round(p95, 2),
                "latency_p99_ms": round(p99, 2),
            }
            strategy_reports.append(rep)

        # 4. Print Comparison Table
        print("\n" + "=" * 115)
        print("OVERALL RETRIEVAL STRATEGY COMPARISON (HELD-OUT TEST SET, 95% BOOTSTRAP CIs)")
        print("=" * 115)
        header = (
            f"{'Strategy':<18} | {'Recall@1':<15} | {'Recall@5':<15} | {'Recall@10':<15} | "
            f"{'MRR':<15} | {'nDCG@5':<15} | {'P50 (ms)':<8} | {'P95 (ms)':<8}"
        )
        print(header)
        print("-" * len(header))
        for rep in strategy_reports:
            r1_str = f"{rep['recall@1']:.3f} [{rep['recall@1_ci95'][0]:.2f}-{rep['recall@1_ci95'][1]:.2f}]"
            r5_str = f"{rep['recall@5']:.3f} [{rep['recall@5_ci95'][0]:.2f}-{rep['recall@5_ci95'][1]:.2f}]"
            r10_str = f"{rep['recall@10']:.3f} [{rep['recall@10_ci95'][0]:.2f}-{rep['recall@10_ci95'][1]:.2f}]"
            mrr_str = f"{rep['mrr']:.3f} [{rep['mrr_ci95'][0]:.2f}-{rep['mrr_ci95'][1]:.2f}]"
            ndcg_str = f"{rep['ndcg@5']:.3f} [{rep['ndcg@5_ci95'][0]:.2f}-{rep['ndcg@5_ci95'][1]:.2f}]"
            print(
                f"{rep['strategy']:<18} | {r1_str:<15} | {r5_str:<15} | {r10_str:<15} | "
                f"{mrr_str:<15} | {ndcg_str:<15} | {rep['latency_p50_ms']:<8.1f} | {rep['latency_p95_ms']:<8.1f}"
            )
        print("-" * len(header))

        # 5. Category Breakdown Report
        category_reports = []
        for cat in categories:
            for s_name, _ in strategies:
                c_data = per_strategy_by_cat[s_name][cat]
                r1 = float(np.mean(c_data["r1"])) if c_data["r1"] else 0.0
                r5 = float(np.mean(c_data["r5"])) if c_data["r5"] else 0.0
                mrr = float(np.mean(c_data["mrr"])) if c_data["mrr"] else 0.0
                ndcg = float(np.mean(c_data["ndcg5"])) if c_data["ndcg5"] else 0.0
                p50 = float(np.percentile(c_data["lat"], 50)) if c_data["lat"] else 0.0
                category_reports.append({
                    "category": cat,
                    "strategy": s_name,
                    "queries": len(c_data["r1"]),
                    "recall@1": round(r1, 4),
                    "recall@5": round(r5, 4),
                    "mrr": round(mrr, 4),
                    "ndcg@5": round(ndcg, 4),
                    "latency_p50_ms": round(p50, 2),
                })

        # 6. Save JSON Results
        benchmark_payload = {
            "metadata": {
                "tag": tag,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dataset": dataset_path,
                "split": split,
                "queries_evaluated": len(cases),
                "total_ingested_memories": total_ingested,
                "bootstrap_resamples": 1000,
                "random_seed": 42,
                "platform": platform.platform(),
                "python_version": sys.version,
            },
            "overall_strategies": strategy_reports,
            "category_breakdown": category_reports,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(benchmark_payload, f, indent=2)
        print(f"\n[4/4] Saved complete versioned benchmark results to '{output_path}'")

        # 7. Save Aggregate CSVs
        csv_results_path = os.path.join(results_dir, f"benchmark_results_{tag}.csv")
        with open(csv_results_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "strategy",
                    "recall@1",
                    "recall@5",
                    "recall@10",
                    "precision@5",
                    "mrr",
                    "ndcg@5",
                    "delta_recall@5_vs_vector",
                    "relative_recall@5_gain_pct",
                    "p_value_recall@5",
                    "delta_ndcg@5_vs_vector",
                    "relative_ndcg@5_gain_pct",
                    "p_value_ndcg@5",
                    "latency_p50_ms",
                    "latency_p95_ms",
                    "latency_p99_ms",
                ],
            )
            writer.writeheader()
            for r in strategy_reports:
                row = {k: v for k, v in r.items() if k in writer.fieldnames}
                writer.writerow(row)
        print(f"Saved summary CSV to '{csv_results_path}'")

        csv_cat_path = os.path.join(results_dir, f"benchmark_categories_{tag}.csv")
        with open(csv_cat_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["category", "strategy", "queries", "recall@1", "recall@5", "mrr", "ndcg@5", "latency_p50_ms"],
            )
            writer.writeheader()
            for r in category_reports:
                writer.writerow(r)
        print(f"Saved category CSV to '{csv_cat_path}'")

        return benchmark_payload


def main():
    parser = argparse.ArgumentParser(description="MNEMOS Retrieval Benchmark Runner")
    parser.add_argument(
        "--dataset",
        type=str,
        default="benchmarks/datasets/retrieval_benchmark_240.json",
        help="Path to evaluation dataset",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="test",
        choices=["test", "dev", "all"],
        help="Split to evaluate: held-out 'test' (200), 'dev' (40), or 'all' (240)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="benchmarks/results/benchmark_pre_opt.json",
        help="Destination path for JSON benchmark results",
    )
    parser.add_argument(
        "--tag",
        type=str,
        default="pre_opt",
        help="Tag identifying the benchmark run (e.g. pre_opt, post_opt)",
    )
    args = parser.parse_args()

    asyncio.run(
        run_benchmarks(
            dataset_path=args.dataset,
            split=args.split,
            output_path=args.output,
            tag=args.tag,
        )
    )


if __name__ == "__main__":
    main()
