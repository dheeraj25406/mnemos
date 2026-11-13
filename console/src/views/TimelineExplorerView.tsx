import React, { useState } from "react";
import { ArrowRight, CheckCircle2, Clock, GitCommit, GitCompare, RefreshCw } from "lucide-react";
import { fetchTimelineDiff } from "../api";
import { TimelineDiffResult } from "../types";

export const TimelineExplorerView: React.FC = () => {
  const [subject, setSubject] = useState("Alice");
  const [t1, setT1] = useState("2024-03-01");
  const [t2, setT2] = useState("2024-08-01");
  const [diffResult, setDiffResult] = useState<TimelineDiffResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleCompare = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim() || !t1 || !t2) return;
    setLoading(true);
    try {
      const res = await fetchTimelineDiff(subject, t1, t2);
      setDiffResult(res);
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
            TIMELINE & EVOLUTION EXPLORER
          </h1>
          <p className="text-xs font-mono text-mnemos-muted mt-1">
            Compare bitemporal state transitions, historical facts, and knowledge acquisition
          </p>
        </div>
      </div>

      {/* Comparison Control Form */}
      <form
        onSubmit={handleCompare}
        className="bg-mnemos-surface border border-mnemos-border rounded p-5 flex flex-wrap items-center gap-4"
      >
        <div className="flex items-center space-x-2">
          <span className="text-xs font-mono text-mnemos-muted">Subject:</span>
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="e.g. Alice"
            className="bg-mnemos-bg border border-mnemos-border rounded px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-neutral-500 w-44"
          />
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-xs font-mono text-mnemos-muted">Time T1:</span>
          <input
            type="date"
            value={t1}
            onChange={(e) => setT1(e.target.value)}
            className="bg-mnemos-bg border border-mnemos-border rounded px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-neutral-500"
          />
        </div>

        <div className="flex items-center space-x-2">
          <ArrowRight size={14} className="text-mnemos-muted" />
          <span className="text-xs font-mono text-mnemos-muted">Time T2:</span>
          <input
            type="date"
            value={t2}
            onChange={(e) => setT2(e.target.value)}
            className="bg-mnemos-bg border border-mnemos-border rounded px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-neutral-500"
          />
        </div>

        <button
          type="submit"
          disabled={loading || !subject.trim()}
          className="flex items-center space-x-2 px-4 py-1.5 text-xs font-mono font-semibold rounded bg-white text-black hover:bg-neutral-200 transition disabled:opacity-50"
        >
          <GitCompare size={14} className={loading ? "animate-spin" : ""} />
          <span>Compare Timeline</span>
        </button>
      </form>

      {/* Educational Bitemporal Callout */}
      <div className="bg-mnemos-surface/50 border border-mnemos-border rounded p-4 flex items-start space-x-3 text-xs font-mono text-neutral-400">
        <Clock size={16} className="text-neutral-400 mt-0.5 shrink-0" />
        <div>
          <span className="text-white font-semibold block">Bitemporal Reasoning Guarantee</span>
          Mnemos distinguishes <strong className="text-neutral-200">Valid Time</strong> (when the proposition was true in the world) from <strong className="text-neutral-200">Transaction Time</strong> (when Mnemos recorded the knowledge). Historical records are never destructively overwritten.
        </div>
      </div>

      {/* Diff Output */}
      {diffResult && (
        <div className="space-y-6">
          <div className="bg-mnemos-surface border border-mnemos-border rounded p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-mnemos-border pb-3">
              <h2 className="text-sm font-mono font-bold text-white uppercase tracking-wider">
                Timeline Evolution for "{diffResult.subject_name}"
              </h2>
              <span className="text-xs font-mono text-mnemos-muted">
                {new Date(diffResult.time_start).toLocaleDateString()} ➔ {new Date(diffResult.time_end).toLocaleDateString()}
              </span>
            </div>

            {/* Changed Facts */}
            <div className="space-y-3">
              <h3 className="text-xs font-mono text-neutral-400 uppercase tracking-wider flex items-center space-x-2">
                <GitCommit size={14} className="text-emerald-400" />
                <span>State Evolutions & Supersessions ({diffResult.changes.length})</span>
              </h3>

              {diffResult.changes.length === 0 ? (
                <div className="text-xs font-mono text-neutral-500 italic p-3 border border-dashed border-mnemos-border rounded">
                  No state changes recorded between these two dates.
                </div>
              ) : (
                <div className="space-y-2">
                  {diffResult.changes.map((ch, i) => (
                    <div
                      key={i}
                      className="bg-mnemos-bg border border-mnemos-border rounded p-4 text-xs font-mono space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-emerald-400 font-semibold uppercase tracking-wider">
                          {ch.predicate}
                        </span>
                        <span className="text-[10px] text-neutral-500">
                          Transition Time: {new Date(ch.effective_time).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="flex items-center space-x-3 text-sm">
                        <span className="text-rose-400 line-through">
                          {ch.previous_value ?? "(None / Not recorded)"}
                        </span>
                        <ArrowRight size={14} className="text-neutral-500" />
                        <span className="text-emerald-300 font-semibold">
                          {ch.new_value ?? "(Terminated)"}
                        </span>
                      </div>
                      <div className="text-[10px] text-neutral-500">
                        Recorded in Mnemos at: {new Date(ch.recorded_time).toISOString()} • Confidence: {Math.round(ch.confidence * 100)}%
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Invariant / Unchanged Facts */}
            <div className="space-y-2 pt-4 border-t border-mnemos-border">
              <h3 className="text-xs font-mono text-neutral-400 uppercase tracking-wider flex items-center space-x-2">
                <CheckCircle2 size={14} className="text-neutral-500" />
                <span>Invariant Facts ({diffResult.unchanged_facts.length})</span>
              </h3>
              {diffResult.unchanged_facts.length === 0 ? (
                <div className="text-xs font-mono text-neutral-500 italic">None</div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {diffResult.unchanged_facts.map((fact, idx) => (
                    <span
                      key={idx}
                      className="bg-mnemos-bg border border-mnemos-border px-2.5 py-1 rounded text-xs font-mono text-neutral-300"
                    >
                      {fact}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
