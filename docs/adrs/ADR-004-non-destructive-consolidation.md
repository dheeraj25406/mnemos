# ADR-004: Non-Destructive Memory Consolidation and Evolution

## Status
Accepted

## Context
As an AI agent operates continuously, raw conversation logs and observations accumulate rapidly. Naive memory management approaches either:
1. Retain everything indefinitely, degrading retrieval latency and precision while bloating context windows with redundant observations.
2. Destructively replace, overwrite, or delete older memories, destroying historical provenance and auditability.

## Decision
Mnemos implements **Non-Destructive Memory Consolidation and Evolution**:
- Source memories are **never physically modified or deleted** during consolidation or evolution.
- Consolidated memories are created as first-class, higher-order memories (`memory_type = 'consolidated'`) that link back to their parent source memories through the `memory_consolidation_members` relational table.
- When conflicting facts are resolved or updated, the superseded fact's `valid_to` or `recorded_to` timestamp is bounded, and its `superseded_by_id` pointer is populated, maintaining a complete immutable chain of custody.

### Consolidation Workflow
1. **Agglomerative Vector Clustering**:
   - Embeddings of active memories within a tenant are clustered using cosine similarity (threshold default: 0.85).
2. **Entity-Centric Summarization**:
   - Clusters with $\ge 2$ memories produce a consolidated summary distilling repetitive statements while extracting unioned entity references.
3. **Audit Trail & Soft Linking**:
   - `MemoryConsolidation` record created.
   - Child memories marked with `is_consolidated = TRUE` and `consolidated_into_id`.
   - Source memories remain queryable in historical / raw audits, but can be filtered out of primary agent context to eliminate redundancy.

### Lifecycle Management
- **Exponential Half-Life Importance Decay**:
  $$I(t) = I_0 \cdot 2^{-\frac{\Delta t}{t_{half}}}$$
- **Cascading Purge**:
  When an explicit deletion or tenant retention policy triggers a purge, foreign key relationships and derived embeddings are cleaned up transactionally with full audit logging.

## Consequences
### Positive
- Strict auditability: agents and human operators can always trace any consolidated fact back to original verbatim user inputs.
- Continuous context compression without information loss.
- Contradiction resolution preserves prior beliefs for temporal counterfactual reasoning.

### Negative / Trade-offs
- Storage footprint includes both consolidated summaries and source inputs (addressed by cold storage archival policies).
