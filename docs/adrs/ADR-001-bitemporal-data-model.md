# ADR-001: Bitemporal Data Model for AI Agent Knowledge

## Status
Accepted

## Context
Standard agent architectures and vector stores operate on a uni-temporal or snapshot paradigm: facts are either overwritten when updated or blindly appended as unstructured text. This causes severe failure modes:
1. **Destructive Overwrites**: An agent loses historical truth when updating an entity attribute (e.g., "Alice works at Company X" overwritten by "Alice works at Company Y").
2. **Temporal Reasoning Failures**: Inability to differentiate between **when an event happened in reality** (Valid Time) versus **when the system recorded that knowledge** (Transaction Time).
3. **Retroactive Correction Anomalies**: When an agent receives retroactive corrections (e.g., learning on October 10 that a policy changed on September 1), naive systems cannot reproduce what was believed on September 15.

## Decision
Mnemos adopts a strict **Bitemporal Data Model** based on Richard Snodgrass's bitemporal relational theory:
- **Valid Time (VT)**: Half-open interval `[valid_from, valid_to)` defining when a fact was true in the real world.
- **Transaction Time (TT)**: Half-open interval `[recorded_from, recorded_to)` defining when Mnemos committed the assertion into storage.

### Mathematical Representation
Every fact $F$ is a tuple:
$$F = (E_{sub}, P, E_{obj}, [v_s, v_e), [t_s, t_e))$$
where:
- $v_e = \infty$ (modeled via sentinel timestamp `9999-12-31T23:59:59Z`) denotes currently active real-world truth.
- $t_e = \infty$ denotes the active recorded state in the system.

### Query Dimensions
Mnemos supports two distinct temporal query modes:
1. **Historical Truth (Valid-Time Query)**:
   $$\text{Select } F \text{ where } valid\_from \le T_{valid} < valid\_to \text{ and } recorded\_to = \infty$$
   *"What was true in reality on March 15, 2024 according to our current knowledge?"*
2. **Historical State of Knowledge (Transaction-Time / As-Of Query)**:
   $$\text{Select } F \text{ where } recorded\_from \le T_{record} < recorded\_to$$
   *"What did the agent believe on April 1, 2024, regardless of subsequent corrections?"*

## Consequences
### Positive
- Zero destructive data loss.
- Complete auditability and provenance for agent memory.
- Exact reproducibility of past agent reasoning sessions.
- Clean separation between facts changing over time vs retroactive knowledge updates.

### Negative / Trade-offs
- Increased storage footprint for historical revisions (mitigated through clustering and consolidation).
- SQL queries require explicit temporal range filtering on `[from, to)` intervals.
- Indexes must cover `(valid_from, valid_to)` and `(recorded_from, recorded_to)` to avoid table scans.
