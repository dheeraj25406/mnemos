import React from "react";
import {
  Activity,
  BarChart2,
  Clock,
  Compass,
  Cpu,
  Database,
  Layers,
  Search,
  Share2,
} from "lucide-react";

export type NavTab =
  | "overview"
  | "explorer"
  | "graph"
  | "timeline"
  | "playground"
  | "benchmarks"
  | "metrics";

interface SidebarProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  healthy: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange, healthy }) => {
  const navItems = [
    { id: "overview" as NavTab, label: "Overview", icon: Compass },
    { id: "explorer" as NavTab, label: "Memory Explorer", icon: Database },
    { id: "graph" as NavTab, label: "Knowledge Graph", icon: Share2 },
    { id: "timeline" as NavTab, label: "Timeline Explorer", icon: Clock },
    { id: "playground" as NavTab, label: "Retrieval Playground", icon: Search },
    { id: "benchmarks" as NavTab, label: "Benchmarks", icon: BarChart2 },
    { id: "metrics" as NavTab, label: "System Metrics", icon: Cpu },
  ];

  return (
    <aside className="w-64 h-screen bg-mnemos-surface border-r border-mnemos-border flex flex-col justify-between select-none">
      <div>
        {/* Brand Header */}
        <div className="p-6 border-b border-mnemos-border">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded bg-neutral-900 border border-neutral-700 flex items-center justify-center font-mono font-bold text-sm tracking-widest text-mnemos-text shadow-inner">
              M
            </div>
            <div>
              <div className="font-mono font-bold tracking-widest text-base text-mnemos-text">
                MNEMOS
              </div>
              <div className="text-[10px] tracking-wider text-mnemos-muted uppercase font-mono">
                Temporal Engine
              </div>
            </div>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded text-xs font-mono tracking-wide transition-colors ${
                  isActive
                    ? "bg-neutral-800 text-mnemos-text font-semibold border-l-2 border-neutral-400 pl-2.5"
                    : "text-mnemos-muted hover:text-mnemos-text hover:bg-neutral-900"
                }`}
              >
                <Icon size={16} className={isActive ? "text-neutral-200" : "text-neutral-500"} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Health Status */}
      <div className="p-4 border-t border-mnemos-border bg-mnemos-bg/40">
        <div className="flex items-center justify-between text-[11px] font-mono text-mnemos-muted">
          <span className="flex items-center space-x-2">
            <span
              className={`w-2 h-2 rounded-full ${
                healthy ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-rose-500"
              }`}
            />
            <span>{healthy ? "ENGINE ACTIVE" : "DEGRADED"}</span>
          </span>
          <span className="text-[10px] text-neutral-600">v0.1.0</span>
        </div>
      </div>
    </aside>
  );
};
