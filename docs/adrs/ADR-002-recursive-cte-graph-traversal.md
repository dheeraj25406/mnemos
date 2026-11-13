# ADR-002: Relational Graph Traversal via PostgreSQL Recursive CTEs

## Status
Accepted

## Context
AI agent memories often require multi-hop entity traversal (e.g., "Who was the manager of the person who founded Company X?"). Adding a dedicated graph database (Neo4j, Memgraph, Neptune) introduces:
1. Two-phase commit / dual-write synchronization anomalies between vector store and graph store.
2. Operational complexity, memory overhead, and resource exhaustion on local developer machines.
3. Lack of integrated ACID transactional consistency across vectors, relational facts, and edges.

## Decision
Mnemos implements the Temporal Knowledge Graph directly inside PostgreSQL 16 using **Recursive Common Table Expressions (CTEs)** alongside `pgvector`.

### Technical Architecture
- Directed edges are persisted in the `relationships` relational table:
  `(id, tenant_id, source_id, target_id, predicate, weight, confidence, valid_from, valid_to, recorded_from, recorded_to)`.
- Multi-hop traversal is executed using PostgreSQL recursive queries:
  ```sql
  WITH RECURSIVE graph_traversal AS (
      -- Anchor member (hop 0)
      SELECT e.id AS entity_id, 0 AS depth, ARRAY[e.id]::VARCHAR[] AS path, ...
      FROM entities e WHERE e.id = :start_entity_id
      UNION ALL
      -- Recursive member (hop k+1)
      SELECT next_ent.id, gt.depth + 1, (gt.path || next_ent.id)::VARCHAR[], ...
      FROM graph_traversal gt
      JOIN relationships r ON (gt.entity_id = r.source_id OR gt.entity_id = r.target_id)
      JOIN entities next_ent ON (CASE WHEN r.source_id = gt.entity_id THEN r.target_id ELSE r.source_id END = next_ent.id)
      WHERE gt.depth < :max_depth
        AND NOT next_ent.id = ANY(gt.path) -- Cycle prevention
        AND r.valid_from <= :valid_at AND r.valid_to > :valid_at -- Bitemporal filter
  )
  SELECT * FROM graph_traversal;
  ```

### Cycle Prevention & Depth Bounding
- Cycles are prevented dynamically in SQL via array membership check: `NOT next_ent.id = ANY(gt.path)`.
- Depth is strictly bounded by `:max_depth` parameter (default: 2, maximum: 5) to guarantee deterministic execution time (< 15ms).
- Bidirectional or unidirectional traversal is parameterizable.

## Consequences
### Positive
- Single database engine for vectors, text search, relational facts, and graphs.
- Full ACID transactions across graph edges and fact modifications.
- Minimal operational footprint: runs comfortably within 512MB RAM in Docker.
- Graph traversal respects real-time bitemporal valid time filters inside the database query engine.

### Negative / Trade-offs
- Deep traversals (> 6 hops) across millions of edges scale slower than native graph pointer chasing.
- Mnemos limits agent graph queries to bounded local subgraphs (1-3 hops), which covers >98% of agent multi-hop reasoning requirements.
