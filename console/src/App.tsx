import React, { useEffect, useState } from "react";
import { fetchHealth } from "./api";
import { NavTab, Sidebar } from "./components/Sidebar";
import { BenchmarkDashboardView } from "./views/BenchmarkDashboardView";
import { KnowledgeGraphView } from "./views/KnowledgeGraphView";
import { MemoryExplorerView } from "./views/MemoryExplorerView";
import { OverviewView } from "./views/OverviewView";
import { RetrievalPlaygroundView } from "./views/RetrievalPlaygroundView";
import { SystemMetricsView } from "./views/SystemMetricsView";
import { TimelineExplorerView } from "./views/TimelineExplorerView";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>("overview");
  const [healthy, setHealthy] = useState<boolean>(true);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetchHealth();
        setHealthy(res.status === "healthy" || res.status === "ok");
      } catch {
        setHealthy(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const renderContent = () => {
    switch (activeTab) {
      case "overview":
        return <OverviewView />;
      case "explorer":
        return <MemoryExplorerView />;
      case "graph":
        return <KnowledgeGraphView />;
      case "timeline":
        return <TimelineExplorerView />;
      case "playground":
        return <RetrievalPlaygroundView />;
      case "benchmarks":
        return <BenchmarkDashboardView />;
      case "metrics":
        return <SystemMetricsView />;
      default:
        return <OverviewView />;
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-mnemos-bg text-mnemos-text font-sans">
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        healthy={healthy}
      />
      <main className="flex-1 h-screen overflow-y-auto">
        {renderContent()}
      </main>
    </div>
  );
};
