import React, { useState } from "react";
import { Check, Filter, Layers, Search, Sparkles, Zap } from "lucide-react";
import { searchMemories } from "../api";
import { SearchResponse } from "../types";

export const RetrievalPlaygroundView: React.FC = () => {
  const [query, setQuery] = useState("Where did Alice work in March?");
  const [topK, setTopK] = useState(5);
  const [validAt, setValidAt] = useState("");
  const [enableVector, setEnableVector] = useState(true);
  const [enableKeyword, setEnableKeyword] = useState(true);
  const [enableGraph, setEnableGraph] = useState(true);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await searchMemories({
        query,
        top_k: topK,
        valid_at: validAt || undefined,
        enable_vector: enableVector,
        enable_keyword: enableKeyword,
        enable_graph: enableGraph,
      });
      setResponse(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-mnemos-border pb-6">
        <div>
          <h1 className="text-xl font-mono font-bold tracking-tight text-mnemos-text">
            RETRIEVAL PLAYGROUND
          </h1>
          <p className="text-xs font-mono text-mnemos-muted mt-1">
            Test multi-channel hybrid retrieval: dense vector, BM25 keyword, and recursive graph traversal
          </p>
        </div>
      </div>

      {/* Query Form & Channel Toggles */}
      <form onSubmit={handleSearch} className="space-y-4 bg-mnemos-surface border border-mnemos-border rounded p-5">
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Submit natural language or temporal question..."
            className="w-full bg-mnemos-bg border border-mnemos-border rounded pl-4 pr-24 py-3 text-sm text-white font-mono focus:outline-none focus:border-neutral-500"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="absolute right-2 top-2 px-4 py-1.5 text-xs font-mono font-semibold rounded bg-white text-black hover:bg-neutral-200 transition disabled:opacity-50 flex items-center space-x-1.5"
          >
            <Search size={14} className={loading ? "animate-spin" : ""} />
            <span>Search</span>
          </button>
        </div>

        {/* Channel Toggles & Parameters */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-mnemos-border text-xs font-mono">
          <div className="flex items-center space-x-4">
            <span className="text-mnemos-muted">Channels:</span>
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={enableVector}
                onChange={(e) => setEnableVector(e.target.checked)}
                className="rounded bg-neutral-900 border-neutral-700 text-white focus:ring-0"
              />
              <span className={enableVector ? "text-white" : "text-neutral-500"}>Dense Vector</span>
            </label>

            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={enableKeyword}
                onChange={(e) => setEnableKeyword(e.target.checked)}
                className="rounded bg-neutral-900 border-neutral-700 text-white focus:ring-0"
              />
              <span className={enableKeyword ? "text-white" : "text-neutral-500"}>Keyword / BM25</span>
            </label>

            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={enableGraph}
                onChange={(e) => setEnableGraph(e.target.checked)}
                className="rounded bg-neutral-900 border-neutral-700 text-white focus:ring-0"
              />
              <span className={enableGraph ? "text-white" : "text-neutral-500"}>Graph Traversal</span>
            </label>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <span className="text-mnemos-muted">Valid At:</span>
              <input
                type="date"
                value={validAt}
                onChange={(e) => setValidAt(e.target.value)}
                className="bg-mnemos-bg border border-mnemos-border rounded px-2 py-1 text-xs text-white font-mono focus:outline-none"
              />
              {validAt && (
                <button
                  type="button"
                  onClick={() => setValidAt("")}
                  className="text-[10px] text-neutral-400 hover:text-white"
                >
                  Clear
                </button>
              )}
            </div>

            <div className="flex items-center space-x-2">
              <span className="text-mnemos-muted">Top K:</span>
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="bg-mnemos-bg border border-mnemos-border rounded px-2 py-1 text-xs text-white font-mono focus:outline-none"
              >
                <option value={3}>3</option>
                <option value={5}>5</option>
                <option value={10}>10</option>
              </select>
            </div>
          </div>
        </div>
      </form>

      {/* Results Section */}
      {response && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs font-mono text-mnemos-muted">
            <span>
              Retrieved <strong className="text-white">{response.total_found}</strong> relevant memories
            </span>
            {response.evidence_entities.length > 0 && (
              <span className="space-x-1">
                <span>Entities Detected:</span>
                {response.evidence_entities.map((ent, i) => (
                  <span
                    key={i}
                    className="bg-neutral-900 border border-neutral-700 px-1.5 py-0.5 rounded text-neutral-300"
                  >
                    {ent}
                  </span>
                ))}
              </span>
            )}
          </div>

          <div className="space-y-3">
            {response.memories.map((mem, index) => (
              <div
                key={mem.memory_id}
                className="bg-mnemos-surface border border-mnemos-border rounded p-5 space-y-3"
              >
                <div className="flex items-start justify-between">
                  <div className="space-y-1 max-w-4xl">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-neutral-900 border border-neutral-700 text-white">
                        #{index + 1}
                      </span>
                      <span className="text-[10px] font-mono text-neutral-500">
                        {mem.memory_id}
                      </span>
                      <span className="text-[10px] font-mono text-emerald-400 font-semibold">
                        RRF Score: {mem.final_score.toFixed(4)}
                      </span>
                    </div>
                    <p className="text-xs text-neutral-100 font-sans leading-relaxed pt-1">
                      {mem.content}
                    </p>
                  </div>
                </div>

                {/* Score Breakdown Pills */}
                <div className="flex flex-wrap gap-2 pt-2 border-t border-mnemos-border text-[10px] font-mono">
                  <span className="bg-mnemos-bg border border-mnemos-border px-2 py-1 rounded text-neutral-400">
                    Vector Sim:{" "}
                    <strong className="text-white">
                      {(mem.vector_score * 100).toFixed(1)}%
                    </strong>
                  </span>
                  <span className="bg-mnemos-bg border border-mnemos-border px-2 py-1 rounded text-neutral-400">
                    BM25 Score:{" "}
                    <strong className="text-white">
                      {mem.keyword_score.toFixed(3)}
                    </strong>
                  </span>
                  <span className="bg-mnemos-bg border border-mnemos-border px-2 py-1 rounded text-neutral-400">
                    Graph Proximity:{" "}
                    <strong className="text-white">
                      {mem.graph_proximity.toFixed(2)}
                    </strong>
                  </span>
                  <span className="bg-mnemos-bg border border-mnemos-border px-2 py-1 rounded text-neutral-400">
                    Confidence:{" "}
                    <strong className="text-white">
                      {Math.round(mem.confidence * 100)}%
                    </strong>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
