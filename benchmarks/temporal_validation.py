"""MNEMOS Dedicated Temporal Retrieval Validation Suite.

Executes deterministic temporal retrieval evaluation across:
1. Fact changes over time
2. Historical queries before and after state transitions
3. Current-state queries
4. Semantically identical facts with different validity periods
5. Retroactive corrections (valid time vs. transaction time)
6. Superseded facts remaining historically retrievable
7. Queries exactly at interval boundaries
8. Multiple sequential updates to the same entity and predicate

Compares:
- Vector-only
- Hybrid without temporal filtering
- Full MNEMOS

Measures:
- Semantic Recall@5
- Correct historical-version accuracy
- Current-state accuracy
- Temporal contamination rate
- P50, P95, P99 latency
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

# Deterministic execution
random.seed(42)
np.random.seed(42)


def get_temporal_test_cases():
    """Generates deterministic temporal test cases with independent ground truth."""
    cases = []

    # --------------------------------------------------------------------------
    # Case Group 1: Fact changes over time + Historical queries before & after + Current
    # --------------------------------------------------------------------------
    alice_seeds = [
        {
            "content": "Alice works at Acme Corp as of 2021-01-01",
            "valid_from": "2021-01-01T00:00:00Z",
            "confidence": 1.0,
        },
        {
            "content": "Alice works at Globex as of 2024-01-01",
            "valid_from": "2024-01-01T00:00:00Z",
            "confidence": 1.0,
        },
    ]

    # 1. Historical query BEFORE change (2022)
    cases.append({
        "id": "tc01_hist_before_change",
        "case_type": "historical_before_after",
        "query_type": "historical",
        "query": "Where did Alice work in 2022?",
        "valid_at": "2022-06-01T00:00:00Z",
        "expected_target": "Acme Corp",
        "invalid_contaminant": "Globex",
        "facts_to_seed": alice_seeds,
    })

    # 2. Historical query AFTER change (early 2024)
    cases.append({
        "id": "tc02_hist_after_change",
        "case_type": "historical_before_after",
        "query_type": "historical",
        "query": "Where did Alice work in March 2024?",
        "valid_at": "2024-03-01T00:00:00Z",
        "expected_target": "Globex",
        "invalid_contaminant": "Acme Corp",
        "facts_to_seed": [],
    })

    # 3. Current-state query (Now)
    cases.append({
        "id": "tc03_current_state",
        "case_type": "current_state",
        "query_type": "current",
        "query": "Where does Alice currently work?",
        "valid_at": None,
        "expected_target": "Globex",
        "invalid_contaminant": "Acme Corp",
        "facts_to_seed": [],
    })

    # --------------------------------------------------------------------------
    # Case Group 2: Two semantically identical facts with different validity periods (Cycle / Re-join)
    # Bob works at Initech (2020-2022), Umbrella (2022-2024), Initech (2024-present)
    # --------------------------------------------------------------------------
    bob_seeds = [
        {
            "content": "Bob works at Initech as of 2020-01-01",
            "valid_from": "2020-01-01T00:00:00Z",
            "confidence": 1.0,
        },
        {
            "content": "Bob works at Umbrella Corp as of 2022-01-01",
            "valid_from": "2022-01-01T00:00:00Z",
            "confidence": 1.0,
        },
        {
            "content": "Bob works at Initech as of 2024-01-01",
            "valid_from": "2024-01-01T00:00:00Z",
            "confidence": 1.0,
        },
    ]

    cases.append({
        "id": "tc04_identical_period_1",
        "case_type": "identical_facts_different_periods",
        "query_type": "historical",
        "query": "Where was Bob employed in 2021?",
        "valid_at": "2021-06-01T00:00:00Z",
        "expected_target": "Initech",
        "invalid_contaminant": "Umbrella Corp",
        "facts_to_seed": bob_seeds,
    })

    cases.append({
        "id": "tc05_identical_period_middle",
        "case_type": "identical_facts_different_periods",
        "query_type": "historical",
        "query": "Where was Bob employed in 2023?",
        "valid_at": "2023-06-01T00:00:00Z",
        "expected_target": "Umbrella Corp",
        "invalid_contaminant": "Initech",
        "facts_to_seed": [],
    })

    cases.append({
        "id": "tc06_identical_period_return",
        "case_type": "identical_facts_different_periods",
        "query_type": "current",
        "query": "Where does Bob work today?",
        "valid_at": None,
        "expected_target": "Initech",
        "invalid_contaminant": "Umbrella Corp",
        "facts_to_seed": [],
    })

    # --------------------------------------------------------------------------
    # Case Group 3: Retroactive Correction (Transaction Time vs Valid Time)
    # --------------------------------------------------------------------------
    charlie_seeds = [
        {
            "content": "Preliminary memo reported Charlie relocated to Paris in 2023-01-01",
            "valid_from": "2023-01-01T00:00:00Z",
            "confidence": 0.40,
        },
        {
            "content": "Official passport audit certifies Charlie relocated to Lyon in 2023-01-01",
            "valid_from": "2023-01-01T00:00:00Z",
            "confidence": 0.99,
        },
    ]

    cases.append({
        "id": "tc07_retroactive_correction",
        "case_type": "retroactive_correction",
        "query_type": "historical",
        "query": "Where did Charlie relocate to in 2023?",
        "valid_at": "2023-06-01T00:00:00Z",
        "expected_target": "Lyon",
        "invalid_contaminant": "Paris",
        "facts_to_seed": charlie_seeds,
    })

    # --------------------------------------------------------------------------
    # Case Group 4: Superseded fact remaining historically retrievable
    # --------------------------------------------------------------------------
    starlight_seeds = [
        {
            "content": "David serves as Chief Technology Officer at Starlight in 2021-01-01",
            "valid_from": "2021-01-01T00:00:00Z",
            "confidence": 1.0,
        },
        {
            "content": "David serves as Board Advisor at Starlight in 2023-06-01",
            "valid_from": "2023-06-01T00:00:00Z",
            "confidence": 1.0,
        },
    ]

    cases.append({
        "id": "tc08_superseded_historically_retrievable",
        "case_type": "superseded_historically_retrievable",
        "query_type": "historical",
        "query": "What was David's role at Starlight in 2022?",
        "valid_at": "2022-06-01T00:00:00Z",
        "expected_target": "Chief Technology Officer",
        "invalid_contaminant": "Board Advisor",
        "facts_to_seed": starlight_seeds,
    })

    cases.append({
        "id": "tc09_superseded_current_not_old",
        "case_type": "superseded_historically_retrievable",
        "query_type": "current",
        "query": "What is David's current role at Starlight?",
        "valid_at": None,
        "expected_target": "Board Advisor",
        "invalid_contaminant": "Chief Technology Officer",
        "facts_to_seed": [],
    })

    # --------------------------------------------------------------------------
    # Case Group 5: Queries exactly at interval boundaries [start, end)
    # Transition boundary: 2024-06-01T00:00:00Z
    # [2024-01-01, 2024-06-01) -> Alpha Lab
    # [2024-06-01, 9999-12-31) -> Beta Lab
    # --------------------------------------------------------------------------
    boundary_seeds = [
        {
            "content": "Project Apollo operates in Alpha Lab as of 2024-01-01",
            "valid_from": "2024-01-01T00:00:00Z",
            "confidence": 1.0,
        },
        {
            "content": "Project Apollo operates in Beta Lab as of 2024-06-01",
            "valid_from": "2024-06-01T00:00:00Z",
            "confidence": 1.0,
        },
    ]

    # Exact start boundary of interval 1: INCLUSIVE -> Alpha Lab
    cases.append({
        "id": "tc10_boundary_exact_start",
        "case_type": "interval_boundary",
        "query_type": "historical",
        "query": "Where did Project Apollo operate on 2024-01-01?",
        "valid_at": "2024-01-01T00:00:00Z",
        "expected_target": "Alpha Lab",
        "invalid_contaminant": "Beta Lab",
        "facts_to_seed": boundary_seeds,
    })

    # 1 second before transition boundary -> Alpha Lab
    cases.append({
        "id": "tc11_boundary_one_sec_before",
        "case_type": "interval_boundary",
        "query_type": "historical",
        "query": "Where did Project Apollo operate right before June 2024?",
        "valid_at": "2024-05-31T23:59:59Z",
        "expected_target": "Alpha Lab",
        "invalid_contaminant": "Beta Lab",
        "facts_to_seed": [],
    })

    # Exact transition boundary point: interval 1 EXCLUDED (half-open), interval 2 INCLUDED -> Beta Lab
    cases.append({
        "id": "tc12_boundary_exact_transition",
        "case_type": "interval_boundary",
        "query_type": "historical",
        "query": "Where did Project Apollo operate on 2024-06-01 exactly?",
        "valid_at": "2024-06-01T00:00:00Z",
        "expected_target": "Beta Lab",
        "invalid_contaminant": "Alpha Lab",
        "facts_to_seed": [],
    })

    # --------------------------------------------------------------------------
    # Case Group 6: Multiple updates to the same entity and predicate (4-step career progression)
    # --------------------------------------------------------------------------
    frank_seeds = [
        {
            "content": "Frank is Junior Engineer at Vertex in 2021-01-01",
            "valid_from": "2021-01-01T00:00:00Z",
            "confidence": 1.0,
        },
        {
            "content": "Frank is Senior Engineer at Vertex in 2022-01-01",
            "valid_from": "2022-01-01T00:00:00Z",
            "confidence": 1.0,
        },
        {
            "content": "Frank is Staff Engineer at Vertex in 2023-01-01",
            "valid_from": "2023-01-01T00:00:00Z",
            "confidence": 1.0,
        },
        {
            "content": "Frank is VP of Engineering at Vertex in 2024-01-01",
            "valid_from": "2024-01-01T00:00:00Z",
            "confidence": 1.0,
        },
    ]

    cases.append({
        "id": "tc13_multi_update_v1",
        "case_type": "multiple_sequential_updates",
        "query_type": "historical",
        "query": "What was Frank's role at Vertex in 2021?",
        "valid_at": "2021-06-01T00:00:00Z",
        "expected_target": "Junior Engineer",
        "invalid_contaminant": "Senior Engineer",
        "facts_to_seed": frank_seeds,
    })

    cases.append({
        "id": "tc14_multi_update_v2",
        "case_type": "multiple_sequential_updates",
        "query_type": "historical",
        "query": "What was Frank's role at Vertex in 2022?",
        "valid_at": "2022-06-01T00:00:00Z",
        "expected_target": "Senior Engineer",
        "invalid_contaminant": "Junior Engineer",
        "facts_to_seed": [],
    })

    cases.append({
        "id": "tc15_multi_update_v3",
        "case_type": "multiple_sequential_updates",
        "query_type": "historical",
        "query": "What was Frank's role at Vertex in 2023?",
        "valid_at": "2023-06-01T00:00:00Z",
        "expected_target": "Staff Engineer",
        "invalid_contaminant": "VP of Engineering",
        "facts_to_seed": [],
    })

    cases.append({
        "id": "tc16_multi_update_v4_current",
        "case_type": "multiple_sequential_updates",
        "query_type": "current",
        "query": "What is Frank's current role at Vertex?",
        "valid_at": None,
        "expected_target": "VP of Engineering",
        "invalid_contaminant": "Junior Engineer",
        "facts_to_seed": [],
    })

    # --------------------------------------------------------------------------
    # Case Group 7: System Infrastructure State Transitions
    # --------------------------------------------------------------------------
    infra_seeds = [
        {
            "content": "Primary database host is db-primary-01 as of 2021-01-01",
            "valid_from": "2021-01-01T00:00:00Z",
            "confidence": 1.0,
        },
        {
            "content": "Primary database host is aurora-cluster-main in 2024-01-01",
            "valid_from": "2024-01-01T00:00:00Z",
            "confidence": 1.0,
        },
    ]

    cases.append({
        "id": "tc17_infra_hist",
        "case_type": "fact_change_over_time",
        "query_type": "historical",
        "query": "What was the primary database host in 2022?",
        "valid_at": "2022-05-01T00:00:00Z",
        "expected_target": "db-primary-01",
        "invalid_contaminant": "aurora-cluster-main",
        "facts_to_seed": infra_seeds,
    })

    cases.append({
        "id": "tc18_infra_current",
        "case_type": "current_state",
        "query_type": "current",
        "query": "What is the current primary database host?",
        "valid_at": None,
        "expected_target": "aurora-cluster-main",
        "invalid_contaminant": "db-primary-01",
        "facts_to_seed": [],
    })

    # Port changes
    port_seeds = [
        {
            "content": "Production API gateway listens on port 8080 as of 2021-01-01",
            "valid_from": "2021-01-01T00:00:00Z",
            "confidence": 1.0,
        },
        {
            "content": "Production API gateway listens on port 443 with TLS termination in 2023-06-01",
            "valid_from": "2023-06-01T00:00:00Z",
            "confidence": 1.0,
        },
    ]

    cases.append({
        "id": "tc19_port_hist",
        "case_type": "fact_change_over_time",
        "query_type": "historical",
        "query": "What port did the API gateway listen on in 2022?",
        "valid_at": "2022-01-01T00:00:00Z",
        "expected_target": "8080",
        "invalid_contaminant": "443",
        "facts_to_seed": port_seeds,
    })

    cases.append({
        "id": "tc20_port_current",
        "case_type": "current_state",
        "query_type": "current",
        "query": "What port does the API gateway currently listen on?",
        "valid_at": None,
        "expected_target": "443",
        "invalid_contaminant": "8080",
        "facts_to_seed": [],
    })

    return cases


async def setup_validation_tenant(session, tenant_id: str):
    t = await session.get(Tenant, tenant_id)
    if not t:
        tenant = Tenant(id=tenant_id, name="Temporal Validation Tenant", config={})
        session.add(tenant)
        key = APIKey(
            id=f"key_{tenant_id}",
            tenant_id=tenant_id,
            key_hash=hash_api_key(f"mnk_val_{tenant_id}"),
            key_prefix="mnk_val_",
            name="val_key",
            rate_limit=50000,
        )
        session.add(key)
        await session.commit()


async def run_temporal_validation():
    print("=" * 95)
    print("MNEMOS TEMPORAL RETRIEVAL VALIDATION BENCHMARK — AUDIT & COMPARISON")
    print("=" * 95)

    await init_db()

    tenant_id = f"temporal_val_{int(time.time())}"
    cases = get_temporal_test_cases()
    results_dir = "benchmarks/results"
    os.makedirs(results_dir, exist_ok=True)

    systems = [
        ("vector_only", {"vector": True, "keyword": False, "graph": False, "temporal": False}),
        ("hybrid_no_temporal", {"vector": True, "keyword": True, "graph": True, "temporal": False}),
        ("full_mnemos", {"vector": True, "keyword": True, "graph": True, "temporal": True}),
    ]

    async with AsyncSessionLocal() as session:
        await setup_validation_tenant(session, tenant_id)

        # 1. Corpus Ingestion
        print(f"\n[1/3] Ingesting temporal validation corpus into tenant '{tenant_id}'...")
        total_seeded = 0
        seen_texts = set()

        for case in cases:
            for seed in case.get("facts_to_seed", []):
                txt = seed["content"]
                if txt in seen_texts:
                    continue
                seen_texts.add(txt)

                vf = None
                if "valid_from" in seed:
                    vf = datetime.fromisoformat(seed["valid_from"].replace("Z", "+00:00"))

                item = IngestionItem(
                    content=txt,
                    memory_type="observation",
                    valid_from=vf,
                    confidence=seed.get("confidence", 1.0),
                )
                await IngestionPipeline.ingest(session, tenant_id, item)
                total_seeded += 1

        await session.commit()
        print(f"-> Seeded {total_seeded} distinct temporal memories across {len(cases)} test scenarios.")

        # 2. System Evaluation
        print(f"\n[2/3] Evaluating 3 systems across {len(cases)} deterministic temporal cases...")
        system_reports = []
        detailed_case_logs = []

        for sys_name, flags in systems:
            print(f"  -> Testing system: {sys_name:<20} ...", end="", flush=True)

            latencies_ms = []
            recalls_5 = []
            hist_accuracies = []
            curr_accuracies = []
            contaminations = []

            for case in cases:
                expected = case["expected_target"].lower()
                contaminant = case.get("invalid_contaminant", "").lower()
                q_type = case["query_type"]

                vt = None
                if flags["temporal"]:
                    if case.get("valid_at"):
                        vt = datetime.fromisoformat(case["valid_at"].replace("Z", "+00:00"))
                    else:
                        # For current state queries in full_mnemos, validate against current time
                        vt = datetime.now(timezone.utc)

                req = HybridRetrievalRequest(
                    query=case["query"],
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
                top1_text = retrieved_texts[0] if retrieved_texts else ""

                # Metric 1: Semantic Recall@5 (Did top 5 contain target topic?)
                r5 = 1.0 if any(expected in t for t in retrieved_texts[:5]) else 0.0
                recalls_5.append(r5)

                # Metric 2 & 3: Historical or Current Accuracy
                # Requires Rank 1 to contain expected target and NOT contaminant
                is_correct = 1.0 if (expected in top1_text and contaminant not in top1_text) else 0.0

                if q_type == "historical":
                    hist_accuracies.append(is_correct)
                elif q_type == "current":
                    curr_accuracies.append(is_correct)

                # Metric 4: Temporal Contamination Rate
                # Occurs if contaminant appeared at Rank 1 (outdated fact returned for current query, or future fact for past query)
                is_contaminated = 1.0 if (contaminant and contaminant in top1_text) else 0.0
                contaminations.append(is_contaminated)

                detailed_case_logs.append({
                    "system": sys_name,
                    "case_id": case["id"],
                    "case_type": case["case_type"],
                    "query_type": q_type,
                    "query": case["query"],
                    "expected_target": case["expected_target"],
                    "invalid_contaminant": case.get("invalid_contaminant"),
                    "top1_retrieved": top1_text,
                    "is_correct": is_correct,
                    "is_contaminated": is_contaminated,
                    "latency_ms": round(lat_ms, 2),
                })

            p50 = float(np.percentile(latencies_ms, 50))
            p95 = float(np.percentile(latencies_ms, 95))
            p99 = float(np.percentile(latencies_ms, 99))

            rep = {
                "system": sys_name,
                "cases_evaluated": len(cases),
                "semantic_recall@5": round(float(np.mean(recalls_5)), 4),
                "historical_version_accuracy": round(float(np.mean(hist_accuracies)), 4) if hist_accuracies else 0.0,
                "current_state_accuracy": round(float(np.mean(curr_accuracies)), 4) if curr_accuracies else 0.0,
                "temporal_contamination_rate": round(float(np.mean(contaminations)), 4),
                "latency_p50_ms": round(p50, 2),
                "latency_p95_ms": round(p95, 2),
                "latency_p99_ms": round(p99, 2),
            }
            system_reports.append(rep)
            print(f" done (HistAcc={rep['historical_version_accuracy']:.2f}, CurrAcc={rep['current_state_accuracy']:.2f}, Contam={rep['temporal_contamination_rate']:.2f})")

        # 3. Print Results Table
        print("\n[3/3] Temporal Retrieval Evaluation Summary:")
        header = f"{'System':<22} | {'Recall@5':<8} | {'HistVerAcc':<10} | {'CurrStateAcc':<12} | {'ContamRate':<10} | {'P50 (ms)':<8} | {'P95 (ms)':<8} | {'P99 (ms)':<8}"
        print("-" * len(header))
        print(header)
        print("-" * len(header))
        for r in system_reports:
            print(
                f"{r['system']:<22} | "
                f"{r['semantic_recall@5']:<8.4f} | "
                f"{r['historical_version_accuracy']:<10.4f} | "
                f"{r['current_state_accuracy']:<12.4f} | "
                f"{r['temporal_contamination_rate']:<10.4f} | "
                f"{r['latency_p50_ms']:<8.2f} | "
                f"{r['latency_p95_ms']:<8.2f} | "
                f"{r['latency_p99_ms']:<8.2f}"
            )
        print("-" * len(header))

        # Save JSON
        out_json_path = os.path.join(results_dir, "temporal_validation.json")
        meta = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "os": platform.system(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "total_cases": len(cases),
            "total_seeded_memories": total_seeded,
            "system_reports": system_reports,
            "detailed_case_logs": detailed_case_logs,
        }
        with open(out_json_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        print(f"\n[Saved JSON]: {out_json_path}")

        # Save CSV
        out_csv_path = os.path.join(results_dir, "temporal_validation.csv")
        with open(out_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "system",
                    "cases_evaluated",
                    "semantic_recall@5",
                    "historical_version_accuracy",
                    "current_state_accuracy",
                    "temporal_contamination_rate",
                    "latency_p50_ms",
                    "latency_p95_ms",
                    "latency_p99_ms",
                ],
            )
            writer.writeheader()
            for r in system_reports:
                writer.writerow(r)
        print(f"[Saved CSV]:  {out_csv_path}")
        print("=" * 95)


if __name__ == "__main__":
    asyncio.run(run_temporal_validation())
