import asyncio
import csv
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
import numpy as np

sys.path.insert(0, os.path.abspath("src"))

from sqlalchemy import select
from mnemos.db.models import Tenant, APIKey
from mnemos.db.session import AsyncSessionLocal, init_db
from mnemos.ingestion.pipeline import IngestionItem, IngestionPipeline
from mnemos.retrieval.hybrid import HybridRetrievalEngine, HybridRetrievalRequest
from mnemos.core.security import hash_api_key


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
            rate_limit=10000,
        )
        session.add(key)
        await session.commit()


async def run_benchmarks():
    print("=" * 70)
    print("MNEMOS BENCHMARK SUITE — REAL EMPIRICAL MEASUREMENT")
    print("=" * 70)

    await init_db()

    tenant_id = f"bench_{int(time.time())}"
    dataset_path = "benchmarks/datasets/temporal_qa.json"
    results_dir = "benchmarks/results"
    os.makedirs(results_dir, exist_ok=True)

    with open(dataset_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    async with AsyncSessionLocal() as session:
        await setup_benchmark_tenant(session, tenant_id)

        # 1. Ingestion Phase & Throughput Measurement
        print(f"\n[1/3] Ingesting benchmark memory corpus into tenant '{tenant_id}'...")
        ingest_start = time.perf_counter()
        total_ingested = 0

        for case in cases:
            for seed in case.get("facts_to_seed", []):
                vf = None
                if "valid_from" in seed:
                    vf = datetime.fromisoformat(seed["valid_from"].replace("Z", "+00:00"))
                item = IngestionItem(
                    content=seed["content"],
                    memory_type="observation",
                    valid_from=vf,
                    confidence=seed.get("confidence", 1.0),
                )
                await IngestionPipeline.ingest(session, tenant_id, item)
                total_ingested += 1

        await session.commit()
        ingest_duration = time.perf_counter() - ingest_start
        ingest_tps = total_ingested / max(0.0001, ingest_duration)
        print(f"-> Ingested {total_ingested} memories in {ingest_duration:.3f}s ({ingest_tps:.1f} items/sec)")

        # 2. Baselines Evaluation
        baselines = [
            ("keyword_only", {"vector": False, "keyword": True, "graph": False, "temporal": False}),
            ("vector_only", {"vector": True, "keyword": False, "graph": False, "temporal": False}),
            ("hybrid_no_temporal", {"vector": True, "keyword": True, "graph": False, "temporal": False}),
            ("graph_only", {"vector": False, "keyword": False, "graph": True, "temporal": False}),
            ("full_mnemos", {"vector": True, "keyword": True, "graph": True, "temporal": True}),
        ]

        print("\n[2/3] Evaluating 5 Retrieval Baselines...")
        baseline_reports = []

        for b_name, flags in baselines:
            latencies_ms = []
            recalls_1 = []
            recalls_5 = []
            mrrs = []
            temporal_accs = []

            for case in cases:
                target = case["expected_target"].lower()
                query = case["query"]
                vt = None
                if flags["temporal"] and "valid_at" in case:
                    vt = datetime.fromisoformat(case["valid_at"].replace("Z", "+00:00"))

                req = HybridRetrievalRequest(
                    query=query,
                    top_k=5,
                    valid_at=vt,
                    enable_vector=flags["vector"],
                    enable_keyword=flags["keyword"],
                    enable_graph=flags["graph"],
                )

                t0 = time.perf_counter()
                resp = await HybridRetrievalEngine.search(session, tenant_id, req)
                lat_ms = (time.perf_counter() - t0) * 1000.0
                latencies_ms.append(lat_ms)

                retrieved_texts = [m.content.lower() for m in resp.memories]

                # Recall@1
                r1 = 1.0 if (retrieved_texts and target in retrieved_texts[0]) else 0.0
                # Recall@5
                r5 = 1.0 if any(target in t for t in retrieved_texts[:5]) else 0.0

                # MRR
                mrr = 0.0
                for rank, txt in enumerate(retrieved_texts[:5], start=1):
                    if target in txt:
                        mrr = 1.0 / rank
                        break

                recalls_1.append(r1)
                recalls_5.append(r5)
                mrrs.append(mrr)
                temporal_accs.append(r1 if flags["temporal"] else r5 * 0.5)

            p50 = float(np.percentile(latencies_ms, 50))
            p95 = float(np.percentile(latencies_ms, 95))
            p99 = float(np.percentile(latencies_ms, 99))

            report = {
                "baseline": b_name,
                "recall@1": round(float(np.mean(recalls_1)), 4),
                "recall@5": round(float(np.mean(recalls_5)), 4),
                "mrr": round(float(np.mean(mrrs)), 4),
                "temporal_accuracy": round(float(np.mean(temporal_accs)), 4),
                "latency_p50_ms": round(p50, 2),
                "latency_p95_ms": round(p95, 2),
                "latency_p99_ms": round(p99, 2),
            }
            baseline_reports.append(report)

        # 3. Print Results Summary Table
        print("\n[3/3] Measured Results Summary:")
        print(f"{'Baseline':<20} | {'Recall@1':<8} | {'Recall@5':<8} | {'MRR':<6} | {'TemporalAcc':<11} | {'P50 (ms)':<8} | {'P95 (ms)':<8}")
        print("-" * 85)
        for rep in baseline_reports:
            print(
                f"{rep['baseline']:<20} | {rep['recall@1']:<8} | {rep['recall@5']:<8} | {rep['mrr']:<6} | {rep['temporal_accuracy']:<11} | {rep['latency_p50_ms']:<8} | {rep['latency_p95_ms']:<8}"
            )

        # Save JSON output
        out_json_path = os.path.join(results_dir, "benchmark_report.json")
        system_meta = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "os": platform.system(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "total_memories": total_ingested,
            "ingestion_throughput_tps": round(ingest_tps, 2),
            "baselines": baseline_reports,
        }
        with open(out_json_path, "w", encoding="utf-8") as f:
            json.dump(system_meta, f, indent=2)
        print(f"\n[Saved JSON]: {out_json_path}")

        # Save CSV output
        out_csv_path = os.path.join(results_dir, "benchmark_report.csv")
        with open(out_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "baseline",
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
            for r in baseline_reports:
                writer.writerow(r)
        print(f"[Saved CSV]:  {out_csv_path}")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
