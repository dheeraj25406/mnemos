import React, { useEffect, useState } from "react";
import { Activity, Clock, Database, Layers, Plus, RefreshCw, Share2, ShieldCheck } from "lucide-react";
import { fetchHealth, fetchMemories, fetchMetrics, ingestMemory } from "../api";
import { MemoryItem, SystemHealth, SystemMetrics } from "../types";

export const OverviewView: React.FC = () => {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [recentMemories, setRecentMemories] = useState<MemoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [ingestModalOpen, setIngestModalOpen] = useState(false);
  const [newContent, setNewContent] = useState("");
  const [ingesting, setIngesting] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [m, h, mems] = await Promise.all([
        fetchMetrics(),
        fetchHealth(),
        fetchMemories(6, 0),
      ]);
      setMetrics(m);
      setHealth(h);
      setRecentMemories(mems.items);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;
    setIngesting(true);
    try {
      await ingestMemory({ content: newContent });
      setNewContent("");
      setIngestModalOpen(false);
      await loadData();
    } catch (err) {
      console.error(err);
    } finally {
      setIngesting(false);
    }
  };

  const statCards = [
    { label: "Active Memories", value: metrics?.memories_total ?? 0, icon: Database },
    { label: "Resolved Entities", value: metrics?.entities_total ?? 0, icon: Layers },
    { label: "Bitemporal Facts", value: metrics?.facts_total ?? 0, icon: Clock },
    { label: "Graph Relationships", value: metrics?.relationships_total ?? 0, icon: Share2 },
    { label: "Consolidations", value: metrics?.consolidations_total ?? 0, icon: Activity },
    { label: "Audit Events", value: metrics?.audit_events_total ?? 0, icon: ShieldCheck },
  ];

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Top Bar */}
      <div className="flex items-center justify-between border-b border-mnemos-border pb-6">
        <div>
          <h1 className="text-xl font-mono font-bold tracking-tight text-mnemos-text">
            OVERVIEW
          </h1>
          <p className="text-xs font-mono text-mnemos-muted mt-1">
            Real-time bitemporal memory state and telemetry
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={loadData}
            className="flex items-center space-x-2 px-3 py-1.5 text-xs font-mono rounded bg-neutral-900 border border-mnemos-border text-mnemos-muted hover:text-white hover:border-neutral-600 transition"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => setIngestModalOpen(true)}
            className="flex items-center space-x-2 px-3 py-1.5 text-xs font-mono rounded bg-neutral-200 text-black font-semibold hover:bg-white transition"
          >
            <Plus size={14} />
            <span>Ingest Memory</span>
          </button>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {statCards.map((stat, i) => {
          const Icon = stat.icon;
          return (
            <div
              key={i}
              className="bg-mnemos-surface border border-mnemos-border rounded p-4 flex flex-col justify-between"
            >
              <div className="flex items-center justify-between text-mnemos-muted">
                <span className="text-[11px] font-mono uppercase tracking-wider">{stat.label}</span>
                <Icon size={14} />
              </div>
              <div className="mt-3 text-2xl font-mono font-bold text-mnemos-text tracking-tight">
                {stat.value.toLocaleString()}
              </div>
            </div>
          );
        })}
      </div>

      {/* Subsystem Health Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-mnemos-surface border border-mnemos-border rounded p-5">
          <div className="text-xs font-mono text-mnemos-muted uppercase tracking-wider">
            Primary Relational Store
          </div>
          <div className="mt-2 text-sm font-mono font-semibold text-white flex items-center justify-between">
            <span>{health?.database.type ?? "PostgreSQL 16 + pgvector"}</span>
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
          </div>
          <div className="mt-2 text-[11px] font-mono text-neutral-500">
            HNSW Indexing • Recursive SQL CTEs • Bitemporal
          </div>
        </div>

        <div className="bg-mnemos-surface border border-mnemos-border rounded p-5">
          <div className="text-xs font-mono text-mnemos-muted uppercase tracking-wider">
            Cache & Coordination
          </div>
          <div className="mt-2 text-sm font-mono font-semibold text-white flex items-center justify-between">
            <span>{health?.cache.type ?? "Redis 7.2"}</span>
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
          </div>
          <div className="mt-2 text-[11px] font-mono text-neutral-500">
            Distributed Locks • Result Caching • Pub/Sub
          </div>
        </div>

        <div className="bg-mnemos-surface border border-mnemos-border rounded p-5">
          <div className="text-xs font-mono text-mnemos-muted uppercase tracking-wider">
            Embedding Provider
          </div>
          <div className="mt-2 text-sm font-mono font-semibold text-white flex items-center justify-between">
            <span>FastEmbed (BAAI/bge-small-en-v1.5)</span>
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
          </div>
          <div className="mt-2 text-[11px] font-mono text-neutral-500">
            384 Dimensions • Local ONNX Runtime • Zero API Tax
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-mnemos-surface border border-mnemos-border rounded p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-mono font-semibold text-mnemos-text tracking-wider uppercase">
            Recent Ingested Memories
          </h2>
          <span className="text-xs font-mono text-mnemos-muted">
            Showing latest {recentMemories.length}
          </span>
        </div>

        {recentMemories.length === 0 ? (
          <div className="text-xs font-mono text-mnemos-muted py-8 text-center border border-dashed border-mnemos-border rounded">
            No memories recorded in this tenant yet.
          </div>
        ) : (
          <div className="divide-y divide-mnemos-border">
            {recentMemories.map((mem) => (
              <div key={mem.id} className="py-3 flex items-start justify-between">
                <div className="space-y-1 max-w-4xl">
                  <p className="text-xs text-neutral-200 leading-relaxed">
                    {mem.content}
                  </p>
                  <div className="flex items-center space-x-3 text-[10px] font-mono text-mnemos-muted">
                    <span className="bg-neutral-900 border border-neutral-700 px-1.5 py-0.5 rounded text-neutral-300">
                      {mem.id}
                    </span>
                    <span>Type: {mem.memory_type}</span>
                    <span>Confidence: {Math.round(mem.confidence * 100)}%</span>
                    <span>Importance: {Math.round(mem.importance * 100)}%</span>
                    {mem.valid_from && (
                      <span className="text-neutral-400">
                        VT: {new Date(mem.valid_from).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
                <div className="text-[10px] font-mono text-neutral-500 whitespace-nowrap ml-4">
                  {new Date(mem.created_at).toLocaleTimeString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Ingestion Modal */}
      {ingestModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-mnemos-surface border border-mnemos-border rounded-lg max-w-xl w-full p-6 space-y-4">
            <h3 className="text-sm font-mono font-bold text-white uppercase tracking-wider">
              Ingest New Memory Unit
            </h3>
            <p className="text-xs font-mono text-mnemos-muted">
              Entities, temporal validity, and relationships will be automatically extracted and indexed.
            </p>
            <form onSubmit={handleIngest} className="space-y-4">
              <textarea
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                rows={4}
                placeholder="e.g. Elena Rostova works at HyperScale as Lead Architect as of 2024-04-01"
                className="w-full bg-mnemos-bg border border-mnemos-border rounded p-3 text-xs text-white font-mono focus:outline-none focus:border-neutral-500 resize-none"
              />
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setIngestModalOpen(false)}
                  className="px-4 py-2 text-xs font-mono rounded border border-mnemos-border text-neutral-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={ingesting || !newContent.trim()}
                  className="px-4 py-2 text-xs font-mono font-semibold rounded bg-white text-black hover:bg-neutral-200 disabled:opacity-50"
                >
                  {ingesting ? "Ingesting..." : "Ingest & Index"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
