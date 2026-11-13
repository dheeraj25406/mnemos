import React, { useEffect, useState } from "react";
import { Clock, Filter, Layers, RefreshCw, Share2 } from "lucide-react";
import { fetchEntities, fetchSubgraph } from "../api";
import { EntityItem, GraphEdge, GraphNode, SubgraphResponse } from "../types";

export const KnowledgeGraphView: React.FC = () => {
  const [entities, setEntities] = useState<EntityItem[]>([]);
  const [selectedEntityId, setSelectedEntityId] = useState<string>("");
  const [maxDepth, setMaxDepth] = useState<number>(2);
  const [validAt, setValidAt] = useState<string>("");
  const [subgraph, setSubgraph] = useState<SubgraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  useEffect(() => {
    fetchEntities(50)
      .then((res) => {
        setEntities(res.items);
        if (res.items.length > 0) {
          setSelectedEntityId(res.items[0].id);
        }
      })
      .catch(console.error);
  }, []);

  const loadGraph = async () => {
    if (!selectedEntityId) return;
    setLoading(true);
    try {
      const data = await fetchSubgraph(selectedEntityId, maxDepth, validAt || undefined);
      setSubgraph(data);
      if (data.nodes.length > 0) {
        setSelectedNode(data.nodes[0]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedEntityId) {
      loadGraph();
    }
  }, [selectedEntityId, maxDepth, validAt]);

  // Color mapping by entity type
  const getTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case "person":
        return "#A3E635"; // Lime
      case "organization":
        return "#60A5FA"; // Blue
      case "project":
        return "#F472B6"; // Pink
      case "location":
        return "#FBBF24"; // Amber
      default:
        return "#E5E7EB"; // Light grey
    }
  };

  // Node position calculation in a radial layout
  const getNodePositions = (nodes: GraphNode[]) => {
    const width = 700;
    const height = 450;
    const centerX = width / 2;
    const centerY = height / 2;

    const positions: Record<string, { x: number; y: number }> = {};
    if (nodes.length === 0) return positions;

    // Seed entity at center
    positions[nodes[0].id] = { x: centerX, y: centerY };

    // Group other nodes by depth
    const outerNodes = nodes.slice(1);
    const angleStep = (2 * Math.PI) / Math.max(1, outerNodes.length);

    outerNodes.forEach((node, i) => {
      const radius = 130 + (node.depth || 1) * 35;
      const angle = i * angleStep;
      positions[node.id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      };
    });

    return positions;
  };

  const positions = subgraph ? getNodePositions(subgraph.nodes) : {};

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-mnemos-border pb-6">
        <div>
          <h1 className="text-xl font-mono font-bold tracking-tight text-mnemos-text">
            TEMPORAL KNOWLEDGE GRAPH
          </h1>
          <p className="text-xs font-mono text-mnemos-muted mt-1">
            Recursive multi-hop graph exploration with bitemporal edge filtering
          </p>
        </div>
        <button
          onClick={loadGraph}
          className="flex items-center space-x-2 px-3 py-1.5 text-xs font-mono rounded bg-neutral-900 border border-mnemos-border text-mnemos-muted hover:text-white hover:border-neutral-600 transition"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Control Bar */}
      <div className="bg-mnemos-surface border border-mnemos-border rounded p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono text-mnemos-muted">Seed Entity:</span>
            <select
              value={selectedEntityId}
              onChange={(e) => setSelectedEntityId(e.target.value)}
              className="bg-mnemos-bg border border-mnemos-border rounded px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-neutral-500"
            >
              {entities.map((ent) => (
                <option key={ent.id} value={ent.id}>
                  {ent.name} ({ent.entity_type})
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono text-mnemos-muted">Max Depth:</span>
            <select
              value={maxDepth}
              onChange={(e) => setMaxDepth(Number(e.target.value))}
              className="bg-mnemos-bg border border-mnemos-border rounded px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-neutral-500"
            >
              <option value={1}>1 Hop</option>
              <option value={2}>2 Hops</option>
              <option value={3}>3 Hops</option>
              <option value={4}>4 Hops</option>
            </select>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <Clock size={14} className="text-mnemos-muted" />
          <span className="text-xs font-mono text-mnemos-muted">Valid As Of:</span>
          <input
            type="date"
            value={validAt}
            onChange={(e) => setValidAt(e.target.value)}
            className="bg-mnemos-bg border border-mnemos-border rounded px-3 py-1 text-xs text-white font-mono focus:outline-none focus:border-neutral-500"
          />
          {validAt && (
            <button
              onClick={() => setValidAt("")}
              className="text-[10px] font-mono text-neutral-400 hover:text-white underline"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Main Canvas & Inspection Pane */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* SVG Graph Canvas */}
        <div className="lg:col-span-3 bg-mnemos-surface border border-mnemos-border rounded p-4 relative min-h-[500px] flex items-center justify-center overflow-hidden">
          {loading ? (
            <div className="text-xs font-mono text-mnemos-muted animate-pulse">
              Traversing recursive knowledge graph...
            </div>
          ) : !subgraph || subgraph.nodes.length === 0 ? (
            <div className="text-xs font-mono text-mnemos-muted">
              No graph nodes discovered for this entity seed.
            </div>
          ) : (
            <svg width={700} height={450} className="w-full h-full">
              {/* Edges */}
              {subgraph.edges.map((edge) => {
                const src = positions[edge.source_entity_id];
                const tgt = positions[edge.target_entity_id];
                if (!src || !tgt) return null;

                const midX = (src.x + tgt.x) / 2;
                const midY = (src.y + tgt.y) / 2;

                return (
                  <g key={edge.id}>
                    <line
                      x1={src.x}
                      y1={src.y}
                      x2={tgt.x}
                      y2={tgt.y}
                      stroke="#374151"
                      strokeWidth={1.5}
                      strokeDasharray="4 2"
                    />
                    {/* Edge Label */}
                    <text
                      x={midX}
                      y={midY - 4}
                      fill="#9CA3AF"
                      fontSize={9}
                      fontFamily="JetBrains Mono, monospace"
                      textAnchor="middle"
                      className="bg-black/60 px-1"
                    >
                      {edge.relation_type}
                    </text>
                  </g>
                );
              })}

              {/* Nodes */}
              {subgraph.nodes.map((node) => {
                const pos = positions[node.id];
                if (!pos) return null;
                const isSelected = selectedNode?.id === node.id;
                const color = getTypeColor(node.entity_type);

                return (
                  <g
                    key={node.id}
                    className="cursor-pointer transition-transform"
                    onClick={() => setSelectedNode(node)}
                  >
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r={isSelected ? 18 : 14}
                      fill="#16181B"
                      stroke={color}
                      strokeWidth={isSelected ? 3 : 1.5}
                      className="transition-all"
                    />
                    <text
                      x={pos.x}
                      y={pos.y + 26}
                      fill="#E5E7EB"
                      fontSize={10}
                      fontFamily="JetBrains Mono, monospace"
                      textAnchor="middle"
                      fontWeight={isSelected ? 700 : 500}
                    >
                      {node.name}
                    </text>
                  </g>
                );
              })}
            </svg>
          )}

          {/* Subgraph stats overlay */}
          {subgraph && (
            <div className="absolute bottom-4 left-4 text-[10px] font-mono text-mnemos-muted bg-mnemos-bg/80 border border-mnemos-border px-2.5 py-1 rounded">
              Nodes: {subgraph.total_nodes} • Edges: {subgraph.total_edges} • Depth: {subgraph.max_depth_reached}
            </div>
          )}
        </div>

        {/* Node Inspection Pane */}
        <div className="bg-mnemos-surface border border-mnemos-border rounded p-5 space-y-4">
          <h2 className="text-xs font-mono font-bold text-white uppercase tracking-wider border-b border-mnemos-border pb-3">
            Selected Entity Detail
          </h2>
          {selectedNode ? (
            <div className="space-y-4 text-xs font-mono">
              <div>
                <span className="text-[10px] text-mnemos-muted block">Entity Name</span>
                <span className="text-sm font-semibold text-white">{selectedNode.name}</span>
              </div>
              <div>
                <span className="text-[10px] text-mnemos-muted block">Entity Type</span>
                <span className="px-2 py-0.5 rounded bg-neutral-900 border border-neutral-700 text-neutral-300 uppercase text-[10px]">
                  {selectedNode.entity_type}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-mnemos-muted block">Node ID</span>
                <span className="text-neutral-400 break-all">{selectedNode.id}</span>
              </div>
              <div>
                <span className="text-[10px] text-mnemos-muted block">Graph Depth From Seed</span>
                <span className="text-white">{selectedNode.depth} hop(s)</span>
              </div>
              {selectedNode.description && (
                <div>
                  <span className="text-[10px] text-mnemos-muted block">Description</span>
                  <span className="text-neutral-300 font-sans leading-relaxed">
                    {selectedNode.description}
                  </span>
                </div>
              )}
            </div>
          ) : (
            <div className="text-xs font-mono text-mnemos-muted">
              Click any node on the graph to inspect entity attributes.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
