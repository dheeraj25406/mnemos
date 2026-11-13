import React, { useState } from "react";
import { BarChart2, CheckCircle2, Cpu, HardDrive, RefreshCw, Zap } from "lucide-react";

// Live measured data from benchmarks/results/benchmark_report.json
const BENCHMARK_DATA = {
  timestamp: "2026-11-13T03:38:22Z",
  machine: "Apple Silicon (arm64)",
  python: "3.11.14",
  ingestion_throughput_tps: 14.3,
  baselines: [
    {
      baseline: "keyword_only",
      label: "Keyword (BM25)",
      recall_1: 0.0,
      recall_5: 0.0,
      mrr: 0.0,
      temporal_acc: 0.0,
      p50_ms: 0.96,
      p95_ms: 6.03,
    },
    {
      baseline: "vector_only",
      label: "Vector (pgvector HNSW)",
      recall_1: 0.4,
      recall_5: 0.8,
      mrr: 0.6,
      temporal_acc: 0.4,
      p50_ms: 5.57,
      p95_ms: 6.8,
    },
    {
      baseline: "hybrid_no_temporal",
      label: "Vector + Keyword",
      recall_1: 0.4,
      recall_5: 0.8,
      mrr: 0.6,
      temporal_acc: 0.4,
      p50_ms: 5.39,
      p95_ms: 6.0,
    },
    {
      baseline: "graph_only",
      label: "Graph Traversal (CTE)",
      recall_1: 0.4,
      recall_5: 0.6,
      mrr: 0.5,
      temporal_acc: 0.3,
      p50_ms: 2.45,
      p95_ms: 11.89,
    },
    {
      baseline: "full_mnemos",
      label: "Full Mnemos Engine",
      recall_1: 0.6,
      recall_5: 1.0,
      mrr: 0.8,
      temporal_acc: 0.6,
      p50_ms: 8.5,
      p95_ms: 11.02,
    },
  ],
};

export const BenchmarkDashboardView: React.FC = () => {
  const [activeMetric, setActiveMetric] = useState<"recall_5" | "mrr" | "temporal_acc" | "p50_ms">("recall_5");

  const metricTitles = {
    recall_5: "Recall@5 (Target Retrieved in Top 5)",
    mrr: "Mean Reciprocal Rank (MRR)",
    temporal_acc: "Temporal Accuracy (Strict Historical Match)",
    p50_ms: "P50 Latency (milliseconds)",
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-mnemos-border pb-6">
        <div>
          <h1 className="text-xl font-mono font-bold tracking-tight text-mnemos-text">
            BENCHMARKS & EMPIRICAL EVALUATION
          </h1>
          <p className="text-xs font-mono text-mnemos-muted mt-1">
            Measured baseline comparisons, latency profiles, and ablation studies on real hardware
          </p>
        </div>
        <div className="text-xs font-mono text-neutral-400 flex items-center space-x-3">
          <span className="flex items-center space-x-1">
            <Cpu size={14} className="text-neutral-500" />
            <span>{BENCHMARK_DATA.machine}</span>
          </span>
          <span className="text-neutral-600">•</span>
          <span>Python {BENCHMARK_DATA.python}</span>
        </div>
      </div>

      {/* Throughput and Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-mnemos-surface border border-mnemos-border rounded p-5 space-y-2">
          <span className="text-xs font-mono text-mnemos-muted uppercase tracking-wider">
            Ingestion Throughput
          </span>
          <div className="text-2xl font-mono font-bold text-white">
            {BENCHMARK_DATA.ingestion_throughput_tps} <span className="text-sm font-normal text-neutral-500">TPS</span>
          </div>
          <p className="text-[11px] font-mono text-neutral-500">
            End-to-end memory pipeline with entity extraction, bitemporal facts, and FastEmbed ONNX embedding.
          </p>
        </div>

        <div className="bg-mnemos-surface border border-mnemos-border rounded p-5 space-y-2">
          <span className="text-xs font-mono text-mnemos-muted uppercase tracking-wider">
            Full Mnemos Recall@5
          </span>
          <div className="text-2xl font-mono font-bold text-emerald-400">
            100.0%
          </div>
          <p className="text-[11px] font-mono text-neutral-500">
            Achieves 1.0 Recall@5 on temporal reasoning and multi-hop queries compared to 0.0% on BM25.
          </p>
        </div>

        <div className="bg-mnemos-surface border border-mnemos-border rounded p-5 space-y-2">
          <span className="text-xs font-mono text-mnemos-muted uppercase tracking-wider">
            P50 Retrieval Latency
          </span>
          <div className="text-2xl font-mono font-bold text-white">
            8.50 <span className="text-sm font-normal text-neutral-500">ms</span>
          </div>
          <p className="text-[11px] font-mono text-neutral-500">
            Sub-10ms response time combining vector cosine search, FTS, and multi-hop graph expansion.
          </p>
        </div>
      </div>

      {/* Interactive Metric Comparison Chart */}
      <div className="bg-mnemos-surface border border-mnemos-border rounded p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-mnemos-border pb-4">
          <h2 className="text-sm font-mono font-bold text-white uppercase tracking-wider">
            {metricTitles[activeMetric]}
          </h2>
          <div className="flex items-center space-x-2 text-xs font-mono">
            {(["recall_5", "mrr", "temporal_acc", "p50_ms"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setActiveMetric(m)}
                className={`px-3 py-1 rounded text-xs transition ${
                  activeMetric === m
                    ? "bg-white text-black font-semibold"
                    : "bg-neutral-900 border border-mnemos-border text-neutral-400 hover:text-white"
                }`}
              >
                {m === "recall_5"
                  ? "Recall@5"
                  : m === "mrr"
                  ? "MRR"
                  : m === "temporal_acc"
                  ? "Temporal Acc"
                  : "Latency P50"}
              </button>
            ))}
          </div>
        </div>

        {/* Visual Bar Comparison */}
        <div className="space-y-4">
          {BENCHMARK_DATA.baselines.map((b) => {
            const val = b[activeMetric];
            const isFullMnemos = b.baseline === "full_mnemos";
            // Normalization for visual bar
            const maxVal = activeMetric === "p50_ms" ? 12.0 : 1.0;
            const pct = Math.min(100, Math.max(5, (val / maxVal) * 100));

            return (
              <div key={b.baseline} className="space-y-1">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className={isFullMnemos ? "text-white font-bold" : "text-neutral-400"}>
                    {b.label}
                  </span>
                  <span className={isFullMnemos ? "text-emerald-400 font-bold" : "text-neutral-300"}>
                    {activeMetric === "p50_ms" ? `${val.toFixed(2)} ms` : `${(val * 100).toFixed(1)}%`}
                  </span>
                </div>
                <div className="w-full bg-neutral-900 rounded-full h-3 overflow-hidden p-0.5 border border-neutral-800">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      isFullMnemos
                        ? "bg-gradient-to-r from-emerald-500 to-emerald-400"
                        : "bg-neutral-600"
                    }`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Detailed Empirical Table */}
      <div className="bg-mnemos-surface border border-mnemos-border rounded overflow-hidden">
        <div className="p-4 border-b border-mnemos-border font-mono text-xs font-bold text-white uppercase tracking-wider">
          Complete Benchmark Telemetry Table
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-neutral-900 border-b border-mnemos-border text-neutral-400">
              <tr>
                <th className="p-3">Baseline</th>
                <th className="p-3">Recall@1</th>
                <th className="p-3">Recall@5</th>
                <th className="p-3">MRR</th>
                <th className="p-3">Temporal Acc</th>
                <th className="p-3">P50 Latency</th>
                <th className="p-3">P95 Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-mnemos-border">
              {BENCHMARK_DATA.baselines.map((b) => {
                const isFull = b.baseline === "full_mnemos";
                return (
                  <tr key={b.baseline} className={isFull ? "bg-neutral-900/60 font-semibold" : ""}>
                    <td className={`p-3 ${isFull ? "text-white" : "text-neutral-300"}`}>
                      {b.label}
                    </td>
                    <td className="p-3 text-neutral-300">{(b.recall_1 * 100).toFixed(0)}%</td>
                    <td className={`p-3 ${isFull ? "text-emerald-400" : "text-neutral-300"}`}>
                      {(b.recall_5 * 100).toFixed(0)}%
                    </td>
                    <td className="p-3 text-neutral-300">{b.mrr.toFixed(2)}</td>
                    <td className="p-3 text-neutral-300">{(b.temporal_acc * 100).toFixed(0)}%</td>
                    <td className="p-3 text-neutral-300">{b.p50_ms.toFixed(2)} ms</td>
                    <td className="p-3 text-neutral-300">{b.p95_ms.toFixed(2)} ms</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
