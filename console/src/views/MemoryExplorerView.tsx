import React, { useEffect, useState } from "react";
import { Clock, Database, Eye, Filter, RefreshCw, Search, Trash2, X } from "lucide-react";
import { deleteMemory, fetchMemories, fetchMemoryDetail } from "../api";
import { MemoryDetail, MemoryItem } from "../types";

export const MemoryExplorerView: React.FC = () => {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedDetail, setSelectedDetail] = useState<MemoryDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [memoryType, setMemoryType] = useState<string>("");

  const loadMemories = async () => {
    setLoading(true);
    try {
      const res = await fetchMemories(50, 0, memoryType || undefined);
      setMemories(res.items);
      setTotal(res.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMemories();
  }, [memoryType]);

  const handleInspect = async (id: string) => {
    setDetailLoading(true);
    try {
      const detail = await fetchMemoryDetail(id);
      setSelectedDetail(detail);
    } catch (e) {
      console.error(e);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm(`Purge memory ${id}? This will cascade delete its derived facts and vector embeddings.`)) return;
    try {
      await deleteMemory(id);
      setSelectedDetail(null);
      await loadMemories();
    } catch (e) {
      console.error(e);
    }
  };

  const filteredMemories = memories.filter((m) =>
    m.content.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-mnemos-border pb-6">
        <div>
          <h1 className="text-xl font-mono font-bold tracking-tight text-mnemos-text">
            MEMORY EXPLORER
          </h1>
          <p className="text-xs font-mono text-mnemos-muted mt-1">
            Inspect raw memory units, provenance chains, and derived bitemporal facts
          </p>
        </div>
        <button
          onClick={loadMemories}
          className="flex items-center space-x-2 px-3 py-1.5 text-xs font-mono rounded bg-neutral-900 border border-mnemos-border text-mnemos-muted hover:text-white hover:border-neutral-600 transition"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-4 justify-between items-center bg-mnemos-surface border border-mnemos-border rounded p-4">
        <div className="relative w-full sm:w-96">
          <Search size={14} className="absolute left-3 top-3 text-mnemos-muted" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Filter memories by keyword..."
            className="w-full bg-mnemos-bg border border-mnemos-border rounded pl-9 pr-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-neutral-500"
          />
        </div>
        <div className="flex items-center space-x-3 w-full sm:w-auto">
          <Filter size={14} className="text-mnemos-muted" />
          <select
            value={memoryType}
            onChange={(e) => setMemoryType(e.target.value)}
            className="bg-mnemos-bg border border-mnemos-border rounded px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-neutral-500"
          >
            <option value="">All Memory Types</option>
            <option value="observation">Observation</option>
            <option value="fact">Fact</option>
            <option value="raw_conversation">Conversation</option>
            <option value="event">Event</option>
            <option value="summary">Summary</option>
          </select>
          <span className="text-xs font-mono text-mnemos-muted whitespace-nowrap">
            Total: {total}
          </span>
        </div>
      </div>

      {/* Memory List */}
      <div className="bg-mnemos-surface border border-mnemos-border rounded divide-y divide-mnemos-border">
        {filteredMemories.length === 0 ? (
          <div className="py-12 text-center text-xs font-mono text-mnemos-muted">
            No memory units match the active filters.
          </div>
        ) : (
          filteredMemories.map((mem) => (
            <div
              key={mem.id}
              className="p-4 hover:bg-neutral-900/40 transition flex items-start justify-between group"
            >
              <div className="space-y-1.5 max-w-4xl">
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-neutral-900 border border-neutral-700 text-neutral-300">
                    {mem.id}
                  </span>
                  <span className="text-[10px] font-mono uppercase text-neutral-400">
                    {mem.memory_type}
                  </span>
                  {mem.valid_from && (
                    <span className="text-[10px] font-mono text-neutral-400 flex items-center space-x-1">
                      <Clock size={10} />
                      <span>VT: {new Date(mem.valid_from).toLocaleDateString()}</span>
                    </span>
                  )}
                </div>
                <p className="text-xs text-neutral-200 leading-relaxed font-sans">
                  {mem.content}
                </p>
                <div className="flex items-center space-x-4 text-[10px] font-mono text-mnemos-muted">
                  <span>Source: {mem.source}</span>
                  <span>Confidence: {Math.round(mem.confidence * 100)}%</span>
                  <span>Importance: {Math.round(mem.importance * 100)}%</span>
                  <span>Recorded: {new Date(mem.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <div className="flex items-center space-x-2 opacity-80 group-hover:opacity-100 transition">
                <button
                  onClick={() => handleInspect(mem.id)}
                  className="px-2.5 py-1 text-xs font-mono rounded bg-neutral-900 border border-mnemos-border text-neutral-300 hover:text-white hover:border-neutral-600 transition flex items-center space-x-1"
                >
                  <Eye size={12} />
                  <span>Inspect</span>
                </button>
                <button
                  onClick={() => handleDelete(mem.id)}
                  className="p-1 text-xs font-mono rounded text-neutral-500 hover:text-rose-400 transition"
                  title="Purge Memory"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Memory Detail Modal / Drawer */}
      {selectedDetail && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-mnemos-surface border border-mnemos-border rounded-lg max-w-2xl w-full max-h-[85vh] overflow-y-auto p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-mnemos-border pb-4">
              <div>
                <h3 className="text-sm font-mono font-bold text-white uppercase tracking-wider">
                  Memory Inspection • {selectedDetail.id}
                </h3>
                <span className="text-[10px] font-mono text-mnemos-muted">
                  Type: {selectedDetail.memory_type} • Source: {selectedDetail.source}
                </span>
              </div>
              <button
                onClick={() => setSelectedDetail(null)}
                className="text-neutral-500 hover:text-white"
              >
                <X size={18} />
              </button>
            </div>

            {/* Original Content */}
            <div className="space-y-1">
              <span className="text-[10px] font-mono text-mnemos-muted uppercase tracking-wider">
                Original Content
              </span>
              <div className="bg-mnemos-bg border border-mnemos-border rounded p-3 text-xs text-white font-mono leading-relaxed">
                {selectedDetail.original_content}
              </div>
            </div>

            {/* Bitemporal Timeline Coordinates */}
            <div className="space-y-2">
              <span className="text-[10px] font-mono text-mnemos-muted uppercase tracking-wider">
                Bitemporal Coordinates
              </span>
              <div className="grid grid-cols-2 gap-3 text-xs font-mono bg-mnemos-bg border border-mnemos-border rounded p-3">
                <div>
                  <span className="text-neutral-500 block text-[10px]">Valid Time (VT)</span>
                  <span className="text-neutral-200">
                    {selectedDetail.valid_from ? new Date(selectedDetail.valid_from).toISOString() : "Unspecified"}
                  </span>
                </div>
                <div>
                  <span className="text-neutral-500 block text-[10px]">Transaction Time (TT)</span>
                  <span className="text-neutral-200">
                    {selectedDetail.recorded_from ? new Date(selectedDetail.recorded_from).toISOString() : "Recorded Now"}
                  </span>
                </div>
              </div>
            </div>

            {/* Derived Atomic Facts */}
            <div className="space-y-2">
              <span className="text-[10px] font-mono text-mnemos-muted uppercase tracking-wider">
                Derived Bitemporal Facts ({selectedDetail.facts.length})
              </span>
              {selectedDetail.facts.length === 0 ? (
                <div className="text-xs font-mono text-neutral-500 italic p-2 border border-dashed border-mnemos-border rounded">
                  No structured relation facts extracted for this memory unit.
                </div>
              ) : (
                <div className="space-y-1.5">
                  {selectedDetail.facts.map((f) => (
                    <div
                      key={f.id}
                      className="bg-mnemos-bg border border-mnemos-border rounded p-2 text-xs font-mono flex items-center justify-between"
                    >
                      <div className="space-x-2">
                        <span className="text-neutral-400">{f.subject_id}</span>
                        <span className="text-emerald-400 font-semibold">{f.predicate}</span>
                        <span className="text-neutral-200">{f.object_id || f.object_literal}</span>
                      </div>
                      <span className="text-[10px] text-neutral-500">
                        Conf: {Math.round(f.confidence * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Derived Graph Edges */}
            <div className="space-y-2">
              <span className="text-[10px] font-mono text-mnemos-muted uppercase tracking-wider">
                Derived Knowledge Graph Relationships ({selectedDetail.relationships.length})
              </span>
              {selectedDetail.relationships.length === 0 ? (
                <div className="text-xs font-mono text-neutral-500 italic p-2 border border-dashed border-mnemos-border rounded">
                  No graph edges attached.
                </div>
              ) : (
                <div className="space-y-1.5">
                  {selectedDetail.relationships.map((r) => (
                    <div
                      key={r.id}
                      className="bg-mnemos-bg border border-mnemos-border rounded p-2 text-xs font-mono flex items-center justify-between text-neutral-300"
                    >
                      <span>
                        {r.source_entity_id} —[{r.relation_type}]→ {r.target_entity_id}
                      </span>
                      <span className="text-[10px] text-neutral-500">{r.id}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="pt-4 border-t border-mnemos-border flex justify-between">
              <button
                onClick={() => handleDelete(selectedDetail.id)}
                className="px-3 py-1.5 text-xs font-mono rounded bg-rose-950/40 border border-rose-800/60 text-rose-300 hover:bg-rose-900/60 transition flex items-center space-x-1.5"
              >
                <Trash2 size={12} />
                <span>Cascade Purge Memory</span>
              </button>
              <button
                onClick={() => setSelectedDetail(null)}
                className="px-4 py-1.5 text-xs font-mono rounded bg-neutral-900 border border-mnemos-border text-neutral-300 hover:text-white"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
