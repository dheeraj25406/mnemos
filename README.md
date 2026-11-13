# MNEMOS

```
  __  __ _   _ _____ __  __  ____   _____ 
 |  \/  | \ | | ____|  \/  |/ __ \ / ____|
 | \  / |  \| | |__ | \  / | |  | | (___  
 | |\/| | . ` |  __|| |\/| | |  | |\___ \ 
 | |  | | |\  | |___| |  | | |__| |____) |
 |_|  |_|_| \_|______|_|  |_|\____/|_____/ 
```

**Temporal Memory Infrastructure for AI Agents**  
*Persistent knowledge. Temporal reasoning. Evolving memory.*

[![CI](https://github.com/mnemos-ai/mnemos/actions/workflows/ci.yml/badge.svg)](https://github.com/mnemos-ai/mnemos/actions)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791.svg)](https://www.postgresql.org/)
[![pgvector](https://img.shields.io/badge/pgvector-0.7+-green.svg)](https://github.com/pgvector/pgvector)
[![MCP](https://img.shields.io/badge/MCP-2.0+-orange.svg)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

---

## What is Mnemos?

**Mnemos** is a production-oriented, open-source temporal memory infrastructure engine designed specifically for AI agents.

Standard AI agent memory systems suffer from fundamental structural limitations:
- **Statelessness & Context Amnesia**: Knowledge is lost between sessions or compressed into lossy prompt summaries.
- **Destructive Overwrites**: Updating an attribute (e.g., *"Alice joined Company Y"*) erases historical facts (*"Alice was at Company X from 2021 to 2024"*).
- **Temporal Collapse**: Standard vector similarity retrieves topical matches regardless of whether the fact was true in March 2023 or November 2026.
- **Retroactive Knowledge Blindness**: Inability to differentiate **when an event happened in reality** (Valid Time) from **when the system learned about it** (Transaction Time).
- **Multi-Hop Graph Blindness**: Dense embeddings fail to traverse chained relationships without graph topology.

Mnemos solves this by providing a unified, bitemporal knowledge graph engine built on **PostgreSQL 16**, **pgvector**, and **recursive SQL graph traversal**, without requiring heavy local LLMs or complex distributed graph databases.

---

## Architecture Overview

```mermaid
flowchart TD
    subgraph Interfaces["Agent Interfaces & Clients"]
        SDK["Python SDK (Sync & Async)"]
        MCP["MCP Server (Model Context Protocol)"]
        API["FastAPI REST API (/v1)"]
        UI["Mnemos Console (React + Vite)"]
    end

    subgraph CoreEngine["Mnemos Core Engine"]
        Ingest["Ingestion Pipeline\n(SHA-256 Idempotency, Entity Resolution)"]
        
        subgraph TemporalLayer["Temporal & Evolution Layer"]
            Bitemp["Bitemporal Coordinator\n(VT: Valid Time | TT: Transaction Time)"]
            Evol["Evolution & Contradiction Resolver\n(Non-destructive Supersession)"]
            Consol["Consolidation & Lifecycle\n(Vector Clustering, Decay, Archival)"]
        end

        subgraph RetrievalEngine["Hybrid Retrieval & Reasoning"]
            FTS["PostgreSQL Full-Text Search (GIN)"]
            Vec["pgvector HNSW Cosine Search"]
            Graph["Recursive CTE Graph Traversal\n(Cycle-safe, bounded depth)"]
            RRF["Reciprocal Rank Fusion (RRF) & Re-ranking"]
            Reason["Temporal Reasoning Engine\n(Historical Truth & Timeline Diff)"]
        end
    end

    subgraph Storage["Unified PostgreSQL 16 + pgvector"]
        T_Mem["memories"]
        T_Facts["facts (Bitemporal)"]
        T_Ent["entities & entity_aliases"]
        T_Rel["relationships (Edges)"]
        T_Emb["memory_embeddings (384d HNSW)"]
        T_Audit["audit_logs & consolidations"]
    end

    SDK --> API
    MCP --> API
    UI --> API
    API --> Ingest
    API --> RetrievalEngine
    API --> TemporalLayer

    Ingest --> Bitemp
    Bitemp --> T_Facts
    Ingest --> T_Mem
    Ingest --> T_Ent
    Ingest --> T_Rel
    Ingest --> T_Emb
    Ingest --> T_Audit

    RetrievalEngine --> FTS
    RetrievalEngine --> Vec
    RetrievalEngine --> Graph
    FTS --> T_Mem
    Vec --> T_Emb
    Graph --> T_Rel
    RRF --> Reason
```

---

## Core System Modules

### 1. Bitemporal Storage (Snodgrass Relational Model)
Every fact tracked in Mnemos has two distinct temporal dimensions represented as half-open intervals `[from, to)`:
1. **Valid Time (VT)**: When the assertion was true in reality (`valid_from` to `valid_to`).
2. **Transaction Time (TT)**: When Mnemos recorded and believed the assertion (`recorded_from` to `recorded_to`).

This enables two fundamental query axes:
- **Historical Truth**: *"Where did Alice work on March 15, 2024?"* (Evaluated at $VT = 2024-03-15, TT = \infty$).
- **Historical State of Knowledge**: *"What did the agent believe on January 14, 2024 before the retroactive correction?"* (Evaluated at $TT = 2024-01-14$).

### 2. Temporal Knowledge Graph (PostgreSQL Recursive CTEs)
Relationships are stored as directed edges with bitemporal intervals. Multi-hop traversal is executed directly in PostgreSQL using recursive CTEs:
- **Cycle Prevention**: Guaranteed via path array tracking (`NOT target_id = ANY(path)`).
- **Bounded Depth**: Strict hop limit (`depth <= max_depth`) ensuring sub-10ms queries.
- **Bitemporal Edge Filtering**: Edges are evaluated dynamically against point-in-time validity.

### 3. Non-Destructive Memory Evolution
When a new observation conflicts with existing knowledge:
1. **Contradiction Detection**: Identifies whether the new fact represents temporal evolution (e.g., job change) or direct mutual exclusion.
2. **Resolution Policies**: Configurable policies including `temporal_recency`, `source_reliability`, `confidence_weighted`, and `human_review`.
3. **Immutability**: Previous facts are never deleted; their `valid_to` or `recorded_to` bounds are updated, and `superseded_by_id` preserves an auditable lineage.

### 4. Tri-Channel Hybrid Retrieval (RRF)
Combines three complementary search signals:
- **Dense Vector Search**: `pgvector` HNSW index using local ONNX embeddings (`BAAI/bge-small-en-v1.5`, 384 dimensions).
- **Lexical Keyword Search**: PostgreSQL FTS using `ts_rank_cd` and `websearch_to_tsquery`.
- **Knowledge Graph Traversal**: 1-to-2 hop entity neighborhood expansion.
- **Fusion**: Scored via Reciprocal Rank Fusion ($k = 60$) with multi-factor re-ranking based on importance, confidence, and temporal relevance.

### 5. Intelligent Consolidation & Lifecycle
- **Agglomerative Vector Clustering**: Discovers related or redundant memories ($cosine \ge 0.85$).
- **Non-Destructive Summaries**: Creates higher-order consolidated memories while maintaining child references in `memory_consolidation_members`.
- **Exponential Half-Life Importance Decay**: Automatically scores aging memories ($I(t) = I_0 \cdot 2^{-\Delta t / t_{half}}$).

---

## Quick Start

### Prerequisites
- Docker & Docker Compose (or PostgreSQL 16+ with `pgvector` and Redis 7)
- Python 3.11+
- Node.js 20+ (for Console)

### 1. Launch with Docker Compose
Clone the repository and start all services:

```bash
git clone https://github.com/mnemos-ai/mnemos.git
cd mnemos

# Start PostgreSQL 16 + pgvector, Redis, API, and Console
docker compose up -d
```

Services will be accessible at:
- **Mnemos Console Dashboard**: `http://localhost:3001`
- **REST API & Swagger Docs**: `http://localhost:8088/docs`
- **PostgreSQL 16**: `localhost:5435`
- **Redis**: `localhost:6380`

### 2. Local Development Setup
To run Mnemos locally on macOS (Apple Silicon) or Linux:

```bash
# Create and activate virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies in editable mode
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Run unit and integration tests
pytest -v

# Start the API server
uvicorn mnemos.api.app:app --host 0.0.0.0 --port 8000 --reload
```

---

## Python SDK

Mnemos provides both asynchronous (`AsyncMnemos`) and synchronous (`Mnemos`) clients.

### Installation
```bash
pip install mnemos
```

### Async Usage
```python
import asyncio
from datetime import datetime, timezone
from mnemos import AsyncMnemos

async def main():
    # Initialize client with API key and endpoint
    client = AsyncMnemos(
        base_url="http://localhost:8088",
        api_key="mnk_live_default_secret_key_12345"
    )

    # 1. Ingest temporal memories
    await client.add(
        content="Alice joined Apollo as an Engineer on March 1, 2024.",
        valid_from=datetime(2024, 3, 1, tzinfo=timezone.utc),
        importance=0.9
    )
    
    await client.add(
        content="Alice transitioned to Chief Architect at Nexus Corp on August 1, 2024.",
        valid_from=datetime(2024, 8, 1, tzinfo=timezone.utc),
        importance=0.95
    )

    # 2. Query historical truth (What was true in April 2024?)
    april_results = await client.search(
        query="Where does Alice work?",
        valid_at=datetime(2024, 4, 1, tzinfo=timezone.utc),
        top_k=3
    )
    for match in april_results.matches:
        print(f"[{match.score:.3f}] {match.content}")

    # 3. Compare timeline differences
    diff = await client.compare_timeline(
        subject="Alice",
        t1=datetime(2024, 3, 15, tzinfo=timezone.utc),
        t2=datetime(2024, 9, 1, tzinfo=timezone.utc)
    )
    print(f"Timeline changes: {len(diff.added_facts)} added, {len(diff.superseded_facts)} superseded.")

    # 4. Traverse entity relationships
    subgraph = await client.traverse_graph(
        entity_name="Alice",
        max_depth=2
    )
    print(f"Discovered {len(subgraph.nodes)} connected entities and {len(subgraph.edges)} edges.")

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Synchronous Usage
```python
from mnemos import Mnemos

with Mnemos(base_url="http://localhost:8088", api_key="mnk_live_default_secret_key_12345") as memory:
    memory.add(content="Project Apollo launched its mainnet on May 10, 2024.")
    results = memory.search(query="When did Apollo launch?")
    print(results.matches[0].content)
```

---

## MCP Server (Model Context Protocol)

Mnemos includes a built-in MCP server compliant with MCP 2.0, allowing Claude Desktop, Claude Code, Antigravity, and other agents to interact directly with temporal memory.

### Claude Desktop Configuration
Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mnemos": {
      "command": "python",
      "args": ["-m", "mnemos.mcp.server"],
      "env": {
        "DATABASE_URL": "postgresql+asyncpg://mnemos:mnemos_dev_secret@localhost:5435/mnemos",
        "SYNC_DATABASE_URL": "postgresql+psycopg://mnemos:mnemos_dev_secret@localhost:5435/mnemos",
        "REDIS_URL": "redis://localhost:6380/0",
        "MNEMOS_DEFAULT_TENANT_KEY": "mnk_live_default_secret_key_12345"
      }
    }
  }
}
```

### Exposed MCP Tools
| Tool Name | Parameters | Description |
|---|---|---|
| `add_memory` | `content`, `importance`, `confidence`, `valid_from`, `metadata` | Ingests a new memory, extracts entities/facts, and indexes embeddings. |
| `search_memory` | `query`, `valid_at`, `top_k`, `enable_vector`, `enable_keyword`, `enable_graph` | Tri-channel hybrid retrieval combining vectors, keywords, and graph. |
| `retrieve_entity` | `entity_name` | Retrieves entity metadata, type, and known aliases. |
| `traverse_graph` | `entity_name`, `max_depth`, `valid_at` | Explores multi-hop relationships with cycle detection and temporal filtering. |
| `query_history` | `subject_name`, `as_of`, `valid_at` | Queries historical facts matching bitemporal coordinates. |
| `compare_timeline` | `subject_name`, `t1`, `t2` | Returns facts added, superseded, or unchanged between two points in time. |
| `consolidate_memory`| `similarity_threshold` | Triggers background semantic clustering and non-destructive summarization. |
| `delete_memory` | `memory_id` | Soft-deletes or purges a memory and cascades associated embeddings and links. |

---

## REST API Reference

The API is fully versioned under `/v1` and authenticated via `X-API-Key` headers:

| Endpoint | Method | Description |
|---|---|---|
| `/v1/health` | `GET` | Health check returning PostgreSQL, Redis, and vector extension status. |
| `/v1/memories` | `POST` | Ingest raw or structured memory with automated entity and fact extraction. |
| `/v1/memories` | `GET` | Paginated listing of active memories with optional type filter. |
| `/v1/memories/{id}` | `GET` | Fetch complete memory details, linked facts, entities, and provenance. |
| `/v1/memories/{id}` | `DELETE` | Cascade deletion of a memory, its vector embeddings, and fact references. |
| `/v1/memories/search` | `POST` | Tri-channel hybrid retrieval using Reciprocal Rank Fusion (RRF). |
| `/v1/entities` | `GET` | List canonical entities, aliases, and associated memory counts. |
| `/v1/graph/subgraph` | `GET` | Recursive CTE multi-hop graph traversal from a root entity. |
| `/v1/temporal/timeline-diff` | `GET` | Comparative timeline analysis showing state changes between $T_1$ and $T_2$. |
| `/v1/temporal/historical-facts`| `GET` | Bitemporal facts active at valid time $VT$ and transaction time $TT$. |
| `/v1/consolidation/trigger` | `POST` | Execute agglomerative clustering and entity-centric consolidation. |
| `/v1/metrics` | `GET` | Operational metrics (memory counts, fact counts, latencies, cache state). |

Interactive OpenAPI documentation is available at `http://localhost:8088/docs`.

---

## Empirical Benchmarks

Mnemos includes a reproducible, real-measurement benchmark framework evaluated against five retrieval baselines across complex temporal and multi-hop scenarios.

### Measured Results (Apple Silicon arm64, PostgreSQL 16 + pgvector)

```
=====================================================================================
Baseline             | Recall@1 | Recall@5 | MRR    | TemporalAcc | P50 (ms) | P95 (ms)
-------------------------------------------------------------------------------------
keyword_only (BM25)  | 0.0      | 0.0      | 0.0    | 0.0         | 0.85     | 2.69    
vector_only (HNSW)   | 0.4      | 0.8      | 0.6    | 0.4         | 5.85     | 7.00    
hybrid_no_temporal   | 0.4      | 0.8      | 0.6    | 0.4         | 5.00     | 6.12    
graph_only (CTE)     | 0.4      | 0.6      | 0.5    | 0.3         | 3.13     | 10.40   
full_mnemos (Tri-RRF)| 0.6      | 1.0      | 0.8    | 0.6         | 7.71     | 10.53   
=====================================================================================
```

### Key Benchmark Findings
1. **Keyword-Only (BM25) Failure**: BM25 scores 0.0 on temporal multi-hop reasoning because lexical matching cannot distinguish between past and current employers or bridge entity aliases.
2. **Dense Vector Temporal Blindness**: Vector-only retrieval reaches 0.8 Recall@5 but suffers from temporal contamination, retrieving superseded facts with identical topical vocabulary.
3. **Full Mnemos Superiority**: Full Mnemos achieves **1.0 Recall@5** and **0.80 MRR** with a P50 latency of **7.71ms**, successfully filtering superseded knowledge and expanding topological entity links.

To reproduce these benchmarks on your machine:
```bash
python benchmarks/runner.py
```
Results are saved to `benchmarks/results/benchmark_report.json` and `benchmark_report.csv`.

---

## Architecture Decision Records (ADRs)

Engineering decisions are thoroughly documented in `docs/adrs/`:
- [ADR-001: Bitemporal Data Model for AI Agent Knowledge](docs/adrs/ADR-001-bitemporal-data-model.md)
- [ADR-002: Relational Graph Traversal via PostgreSQL Recursive CTEs](docs/adrs/ADR-002-recursive-cte-graph-traversal.md)
- [ADR-003: Multi-Channel Hybrid Retrieval with Reciprocal Rank Fusion](docs/adrs/ADR-003-hybrid-rrf-retrieval.md)
- [ADR-004: Non-Destructive Memory Consolidation and Evolution](docs/adrs/ADR-004-non-destructive-consolidation.md)

---

## Mnemos Console (Frontend)

Mnemos includes a dark engineering console built with React 18, Vite, and Tailwind CSS.

### Features
- **Overview Dashboard**: System health, active tenant metrics, live memory counts, and quick ingestion modal.
- **Memory Explorer**: Live search, filtering by memory type, full bitemporal detail inspector, and JSON viewer.
- **Knowledge Graph Explorer**: Interactive node-edge visualization with depth bounding and temporal slider.
- **Timeline Explorer**: Visual before-and-after comparison tool highlighting added and superseded facts between any two dates.
- **Retrieval Playground**: Interactive test bench comparing Vector, Keyword, and Graph retrieval channels with live RRF scores.
- **Benchmark Dashboard**: Visual breakdown of measured Recall@K, MRR, latency distributions, and baseline comparisons.
- **System Metrics**: Real-time connection pool health, pgvector index status, and memory statistics.

Launch the console locally:
```bash
cd console
npm install
npm run dev
```

---

## Security & Multi-Tenancy

- **Tenant Isolation**: Every database row and vector embedding is strictly scoped by `tenant_id`. Foreign keys enforce tenant isolation with cascading cleanup.
- **Authentication**: SHA-256 hashed API keys (`mnk_live_...`) with per-tenant permissions and revocation support.
- **Reliability & Idempotency**: SHA-256 content hashing prevents duplicate memory ingestion during client retries.
- **Zero Local Model Overhead**: Uses lightweight local ONNX runtimes for embeddings (`fastembed`). Runs comfortably on a base Apple Silicon Mac with 16 GB RAM.

---

## License

Mnemos is licensed under the [Apache License, Version 2.0](LICENSE).
