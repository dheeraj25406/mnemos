# ADR-003: Multi-Channel Hybrid Retrieval with Reciprocal Rank Fusion (RRF)

## Status
Accepted

## Context
Standard RAG architectures rely exclusively on semantic dense vector retrieval (bi-encoders). This introduces critical failures in agent workloads:
1. **Exact-Match & Identifier Blindness**: Vector embeddings struggle with exact entity IDs, dates, model numbers, or rare proper nouns (e.g., "TX-900", "0.0034%", "March 15, 2024").
2. **Temporal Collapse**: Dense embeddings cluster texts with similar topical vocabulary regardless of their temporal validity.
3. **Multi-Hop Blindness**: Dense embeddings cannot navigate topological entity relationships without explicit graph expansion.

## Decision
Mnemos implements a **Tri-Channel Hybrid Retrieval Pipeline** combined through **Reciprocal Rank Fusion (RRF)** and post-fusion heuristic re-ranking.

### Retrieval Channels
1. **Dense Vector Channel**:
   - `pgvector` HNSW index with cosine distance metric.
   - Embeddings generated via local ONNX runtime (`BAAI/bge-small-en-v1.5`, 384 dimensions).
2. **Lexical Keyword Channel**:
   - PostgreSQL Full-Text Search (FTS) using `to_tsvector('english', ...)` and GIN indexes.
   - Ranking via Cover Density Ranking `ts_rank_cd(fts_vector, websearch_to_tsquery('english', :query))`.
3. **Knowledge Graph Traversal Channel**:
   - Entity extraction from query terms.
   - 1-to-2 hop recursive CTE traversal to surface connected entities, facts, and their associated source memories.

### Reciprocal Rank Fusion (RRF)
Candidates from all channels are deduplicated and scored using standard RRF:
$$RRF(d) = \sum_{c \in Channels} \frac{1}{k + rank_c(d)}$$
where smoothing constant $k = 60$.

### Multi-Factor Re-Ranking
The fused candidates undergo final re-ranking incorporating:
$$Score_{final}(d) = RRF(d) \times (1 + \alpha_{imp} \cdot Importance + \alpha_{conf} \cdot Confidence + \alpha_{temp} \cdot TemporalRelevance)$$
- Fact valid time filters strictly eliminate expired or superseded facts when a temporal query constraint (`valid_at`) is active.

## Consequences
### Positive
- High precision on exact entity names and dates alongside deep semantic matching.
- Surfacing of non-obvious multi-hop connected facts.
- Fully local and deterministic: no external API dependencies required for baseline ranking.

### Negative / Trade-offs
- Tri-channel retrieval requires running three concurrent database queries before fusion (P50 latency remains < 10ms on modern PostgreSQL).
