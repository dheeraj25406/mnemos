import {
  EntityItem,
  MemoryDetail,
  MemoryItem,
  SearchResponse,
  SubgraphResponse,
  SystemHealth,
  SystemMetrics,
  TimelineDiffResult,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");
const DEFAULT_API_KEY = import.meta.env.VITE_API_KEY || "mnk_test_secret_key_12345";

function getHeaders(): HeadersInit {
  return {
    "Content-Type": "application/json",
    "X-Mnemos-API-Key": DEFAULT_API_KEY,
  };
}

export async function fetchHealth(): Promise<SystemHealth> {
  const res = await fetch(`${API_BASE}/v1/health`, { headers: getHeaders() });
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function fetchMetrics(): Promise<SystemMetrics> {
  const res = await fetch(`${API_BASE}/v1/metrics`, { headers: getHeaders() });
  if (!res.ok) throw new Error("Metrics fetch failed");
  return res.json();
}

export async function fetchMemories(limit = 50, offset = 0, memoryType?: string): Promise<{ total: number; items: MemoryItem[] }> {
  let url = `${API_BASE}/v1/memories?limit=${limit}&offset=${offset}`;
  if (memoryType) url += `&memory_type=${memoryType}`;
  const res = await fetch(url, { headers: getHeaders() });
  if (!res.ok) throw new Error("Memories fetch failed");
  return res.json();
}

export async function fetchMemoryDetail(id: string): Promise<MemoryDetail> {
  const res = await fetch(`${API_BASE}/v1/memories/${id}`, { headers: getHeaders() });
  if (!res.ok) throw new Error("Memory detail fetch failed");
  return res.json();
}

export async function ingestMemory(payload: {
  content: string;
  memory_type?: string;
  source?: string;
  importance?: number;
  valid_from?: string;
}): Promise<any> {
  const res = await fetch(`${API_BASE}/v1/memories`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Ingestion failed");
  return res.json();
}

export async function deleteMemory(id: string): Promise<any> {
  const res = await fetch(`${API_BASE}/v1/memories/${id}`, {
    method: "DELETE",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("Deletion failed");
  return res.json();
}

export async function searchMemories(payload: {
  query: string;
  top_k?: number;
  valid_at?: string;
  enable_vector?: boolean;
  enable_keyword?: boolean;
  enable_graph?: boolean;
}): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/v1/memories/search`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Search failed");
  return res.json();
}

export async function fetchEntities(limit = 100): Promise<{ total: number; items: EntityItem[] }> {
  const res = await fetch(`${API_BASE}/v1/entities?limit=${limit}`, { headers: getHeaders() });
  if (!res.ok) throw new Error("Entities fetch failed");
  return res.json();
}

export async function fetchSubgraph(seedEntityId: string, maxDepth = 2, validAt?: string): Promise<SubgraphResponse> {
  let url = `${API_BASE}/v1/graph/subgraph?seed_entity_id=${seedEntityId}&max_depth=${maxDepth}`;
  if (validAt) url += `&valid_at=${encodeURIComponent(validAt)}`;
  const res = await fetch(url, { headers: getHeaders() });
  if (!res.ok) throw new Error("Graph traversal failed");
  return res.json();
}

export async function fetchTimelineDiff(subject: string, t1: string, t2: string): Promise<TimelineDiffResult> {
  const url = `${API_BASE}/v1/temporal/timeline-diff?subject=${encodeURIComponent(subject)}&t1=${encodeURIComponent(t1)}&t2=${encodeURIComponent(t2)}`;
  const res = await fetch(url, { headers: getHeaders() });
  if (!res.ok) throw new Error("Timeline diff failed");
  return res.json();
}

export async function fetchConsolidations(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/v1/consolidation`, { headers: getHeaders() });
  if (!res.ok) throw new Error("Consolidations fetch failed");
  return res.json();
}
