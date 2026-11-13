export interface MemoryItem {
  id: string;
  memory_type: string;
  content: string;
  source: string;
  confidence: number;
  importance: number;
  valid_from: string | null;
  valid_to: string | null;
  recorded_from: string | null;
  created_at: string;
  metadata?: Record<string, any>;
}

export interface MemoryDetail extends MemoryItem {
  original_content: string;
  normalized_content: string;
  access_count: number;
  superseded_by_id: string | null;
  consolidated_into_id: string | null;
  facts: Array<{
    id: string;
    subject_id: string;
    predicate: string;
    object_id: string | null;
    object_literal: string | null;
    valid_from: string | null;
    valid_to: string | null;
    confidence: number;
  }>;
  relationships: Array<{
    id: string;
    source_entity_id: string;
    target_entity_id: string;
    relation_type: string;
  }>;
}

export interface EntityItem {
  id: string;
  name: string;
  entity_type: string;
  description: string | null;
  confidence: number;
  created_at: string;
}

export interface GraphNode {
  id: string;
  name: string;
  entity_type: string;
  description: string | null;
  depth: number;
}

export interface GraphEdge {
  id: string;
  source_entity_id: string;
  target_entity_id: string;
  relation_type: string;
  weight: number;
  valid_from: string;
  valid_to: string;
  depth: number;
}

export interface SubgraphResponse {
  seed_entity_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  max_depth_reached: number;
  total_nodes: number;
  total_edges: number;
}

export interface SearchResultMemory {
  memory_id: string;
  content: string;
  final_score: number;
  rrf_score: number;
  vector_score: number;
  keyword_score: number;
  graph_proximity: number;
  importance: number;
  confidence: number;
  explanation: Record<string, any>;
}

export interface SearchResponse {
  query: string;
  total_found: number;
  memories: SearchResultMemory[];
  evidence_entities: string[];
  temporal_anchor: string | null;
}

export interface TimelineDiffResult {
  subject_name: string;
  time_start: string;
  time_end: string;
  changes: Array<{
    subject: string;
    predicate: string;
    previous_value: string | null;
    new_value: string | null;
    effective_time: string;
    recorded_time: string;
    confidence: number;
  }>;
  unchanged_facts: string[];
}

export interface SystemMetrics {
  tenant_id: string;
  memories_total: number;
  entities_total: number;
  facts_total: number;
  relationships_total: number;
  consolidations_total: number;
  audit_events_total: number;
}

export interface SystemHealth {
  status: string;
  product: string;
  tagline: string;
  version: string;
  timestamp: string;
  database: { connected: boolean; type: string };
  cache: { connected: boolean; type: string };
}
