from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.api.deps import get_current_tenant_id
from mnemos.consolidation.lifecycle import LifecycleManager
from mnemos.db.models import Fact, Memory, Relationship
from mnemos.db.session import get_db_session
from mnemos.ingestion.pipeline import IngestionItem, IngestionPipeline, IngestionResult
from mnemos.retrieval.hybrid import (
    HybridRetrievalEngine,
    HybridRetrievalRequest,
    HybridRetrievalResponse,
)

router = APIRouter(prefix="/memories", tags=["Memories"])


class IngestMemoryRequest(BaseModel):
    content: str
    memory_type: str = "observation"
    source: str = "agent"
    confidence: float = 1.0
    importance: float = 0.5
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BatchIngestRequest(BaseModel):
    items: list[IngestMemoryRequest]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=IngestionResult)
async def ingest_memory(
    request: IngestMemoryRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Ingest a memory unit with automatic entity extraction, bitemporal coordinates, and provenance."""
    item = IngestionItem(**request.model_dump())
    return await IngestionPipeline.ingest(session, tenant_id, item)


@router.post("/batch", status_code=status.HTTP_201_CREATED, response_model=list[IngestionResult])
async def ingest_memories_batch(
    request: BatchIngestRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Batch ingest memories with transactional consistency."""
    items = [IngestionItem(**it.model_dump()) for it in request.items]
    return await IngestionPipeline.ingest_batch(session, tenant_id, items)


@router.post("/search", response_model=HybridRetrievalResponse)
async def search_memories(
    request: HybridRetrievalRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Perform multi-channel hybrid search combining:
    - Vector semantic similarity (pgvector)
    - Full-text search (BM25)
    - Temporal knowledge graph multi-hop expansion
    - Temporal validity and transaction time filtering
    - RRF fusion and contextual re-ranking
    """
    return await HybridRetrievalEngine.search(session, tenant_id, request)


@router.get("")
async def list_memories(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    memory_type: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
):
    """List memories with pagination and filtering."""
    query = select(Memory).where(Memory.tenant_id == tenant_id, Memory.is_active == True)
    if memory_type:
        query = query.where(Memory.memory_type == memory_type)

    total_stmt = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_stmt)).scalar_one()

    query = query.order_by(Memory.created_at.desc()).offset(offset).limit(limit)
    rows = (await session.execute(query)).scalars().all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": m.id,
                "memory_type": m.memory_type,
                "content": m.normalized_content,
                "source": m.source,
                "confidence": m.confidence,
                "importance": m.importance,
                "valid_from": m.valid_from.isoformat() if m.valid_from else None,
                "valid_to": m.valid_to.isoformat() if m.valid_to else None,
                "recorded_from": m.recorded_from.isoformat() if m.recorded_from else None,
                "created_at": m.created_at.isoformat(),
                "metadata": m.metadata_,
            }
            for m in rows
        ],
    }


@router.get("/{memory_id}")
async def get_memory_detail(
    memory_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieve complete details of a memory including derived facts, relationships, and provenance."""
    memory = await session.get(Memory, memory_id)
    if not memory or memory.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Memory not found")

    # Fetch derived facts
    facts_stmt = select(Fact).where(Fact.source_memory_id == memory_id)
    facts = (await session.execute(facts_stmt)).scalars().all()

    # Fetch derived relationships
    rels_stmt = select(Relationship).where(Relationship.source_memory_id == memory_id)
    rels = (await session.execute(rels_stmt)).scalars().all()

    return {
        "id": memory.id,
        "tenant_id": memory.tenant_id,
        "memory_type": memory.memory_type,
        "original_content": memory.original_content,
        "normalized_content": memory.normalized_content,
        "source": memory.source,
        "confidence": memory.confidence,
        "importance": memory.importance,
        "access_count": memory.access_count,
        "valid_from": memory.valid_from.isoformat() if memory.valid_from else None,
        "valid_to": memory.valid_to.isoformat() if memory.valid_to else None,
        "recorded_from": memory.recorded_from.isoformat() if memory.recorded_from else None,
        "recorded_to": memory.recorded_to.isoformat() if memory.recorded_to else None,
        "superseded_by_id": memory.superseded_by_id,
        "consolidated_into_id": memory.consolidated_into_id,
        "created_at": memory.created_at.isoformat(),
        "metadata": memory.metadata_,
        "facts": [
            {
                "id": f.id,
                "subject_id": f.subject_id,
                "predicate": f.predicate,
                "object_id": f.object_id,
                "object_literal": f.object_literal,
                "valid_from": f.valid_from.isoformat() if f.valid_from else None,
                "valid_to": f.valid_to.isoformat() if f.valid_to else None,
                "confidence": f.confidence,
            }
            for f in facts
        ],
        "relationships": [
            {
                "id": r.id,
                "source_entity_id": r.source_entity_id,
                "target_entity_id": r.target_entity_id,
                "relation_type": r.relation_type,
            }
            for r in rels
        ],
    }


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Purge a memory with complete cascade deletion of embeddings, facts, and edges."""
    success = await LifecycleManager.purge_memory(session, tenant_id, memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "deleted", "memory_id": memory_id}
