from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.core.logging import logger
from mnemos.db.models import Entity, Memory
from mnemos.graph.engine import TemporalGraphEngine
from mnemos.ingestion.extractor import MemoryExtractor
from mnemos.retrieval.embeddings import get_embedding_provider
from mnemos.retrieval.keyword import KeywordRetriever
from mnemos.retrieval.ranker import FusionRanker, RankedMemory
from mnemos.retrieval.vector import VectorRetriever


class HybridRetrievalRequest(BaseModel):
    query: str
    top_k: int = 10
    valid_at: datetime | None = None
    recorded_at: datetime | None = None
    enable_vector: bool = True
    enable_keyword: bool = True
    enable_graph: bool = True
    enable_temporal_filtering: bool = True
    max_graph_hops: int = 2
    weight_vector: float = 1.0
    weight_keyword: float = 0.8
    weight_graph: float = 0.6


class HybridRetrievalResponse(BaseModel):
    query: str
    total_found: int
    memories: list[RankedMemory]
    evidence_entities: list[str] = Field(default_factory=list)
    temporal_anchor: str | None = None


class HybridRetrievalEngine:
    """
    Unified multi-channel memory retrieval combining:
    - Vector semantic search (pgvector HNSW)
    - Keyword lexical search (PostgreSQL FTS)
    - Knowledge graph multi-hop expansion
    - Bitemporal validity and knowledge constraints
    - Reciprocal Rank Fusion & multi-factor re-ranking
    """

    @classmethod
    async def search(
        cls,
        session: AsyncSession,
        tenant_id: str,
        request: HybridRetrievalRequest,
    ) -> HybridRetrievalResponse:
        vector_items: list[dict[str, Any]] = []
        keyword_items: list[dict[str, Any]] = []
        graph_items: list[dict[str, Any]] = []
        evidence_entities: list[str] = []

        # 1. Parse query temporal anchor if request.valid_at is not explicitly provided
        valid_at = request.valid_at if request.enable_temporal_filtering else None
        if request.enable_temporal_filtering and valid_at is None:
            extracted_anchor = MemoryExtractor.extract_temporal_anchor(request.query)
            if extracted_anchor:
                valid_at = extracted_anchor
            else:
                # Default to CURRENT valid time so historical superseded facts are excluded from current queries
                valid_at = datetime.now(timezone.utc)

        # 2. Vector Channel
        if request.enable_vector:
            provider = get_embedding_provider()
            try:
                qvec = provider.embed_query(request.query)
                vec_res = await VectorRetriever.retrieve(
                    session=session,
                    tenant_id=tenant_id,
                    query_vector=qvec,
                    top_k=request.top_k * 2,
                    valid_at=valid_at,
                    recorded_at=request.recorded_at,
                )
                for r in vec_res:
                    vector_items.append({
                        "memory_id": r.memory_id,
                        "content": r.content,
                        "rank": r.rank,
                        "score": r.similarity,
                        "confidence": r.confidence,
                        "importance": r.importance,
                    })
            except Exception as e:
                logger.warning(f"Vector search failed: {e}")

        # 3. Keyword / BM25 Channel
        if request.enable_keyword:
            kw_res = await KeywordRetriever.retrieve(
                session=session,
                tenant_id=tenant_id,
                query=request.query,
                top_k=request.top_k * 2,
                valid_at=valid_at,
                recorded_at=request.recorded_at,
            )
            for r in kw_res:
                keyword_items.append({
                    "memory_id": r.memory_id,
                    "content": r.content,
                    "rank": r.rank,
                    "score": r.bm25_score,
                    "confidence": r.confidence,
                    "importance": r.importance,
                })

        # 4. Knowledge Graph Channel (Entity-centered multi-hop expansion)
        if request.enable_graph:
            extracted_ents, _ = MemoryExtractor.extract(request.query)
            if extracted_ents:
                names = [e.name for e in extracted_ents]
                evidence_entities.extend(names)
                # Batch lookup entities in single SQL query
                conds = [Entity.name.ilike(f"%{n}%") for n in names[:5]]
                db_ent_stmt = select(Entity).where(
                    Entity.tenant_id == tenant_id,
                    Entity.is_active == True,
                    or_(*conds) if len(conds) > 1 else conds[0],
                )
                db_ents = (await session.execute(db_ent_stmt)).scalars().all()
                for db_ent in db_ents:
                    subgraph = await TemporalGraphEngine.traverse_subgraph(
                        session=session,
                        tenant_id=tenant_id,
                        seed_entity_id=db_ent.id,
                        max_depth=max(request.max_graph_hops, 3),
                        valid_at=valid_at,
                        recorded_at=request.recorded_at,
                    )
                    # Collect memories linked to subgraph edges
                    edge_memory_hops: dict[str, int] = {}
                    for ed in subgraph.edges:
                        if ed.source_memory_id:
                            edge_memory_hops.setdefault(ed.source_memory_id, getattr(ed, "hops", 1))

                    if edge_memory_hops:
                        mem_ids = list(edge_memory_hops.keys())
                        mem_stmt = select(Memory).where(Memory.id.in_(mem_ids))
                        mems = (await session.execute(mem_stmt)).scalars().all()
                        for idx, m in enumerate(mems):
                            hops = edge_memory_hops.get(m.id, 1)
                            graph_items.append({
                                "memory_id": m.id,
                                "content": m.normalized_content,
                                "rank": idx + 1,
                                "hops": hops,
                                "confidence": m.confidence,
                                "importance": m.importance,
                            })

        # 5. Reciprocal Rank Fusion & Ranking
        fused = FusionRanker.rrf_fuse(
            vector_ranked=vector_items,
            keyword_ranked=keyword_items,
            graph_ranked=graph_items,
            w_vec=request.weight_vector,
            w_kw=request.weight_keyword,
            w_graph=request.weight_graph,
        )

        top_results = fused[: request.top_k]

        return HybridRetrievalResponse(
            query=request.query,
            total_found=len(top_results),
            memories=top_results,
            evidence_entities=evidence_entities,
            temporal_anchor=valid_at.isoformat() if valid_at else None,
        )
