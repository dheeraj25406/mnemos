from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.consolidation.lifecycle import LifecycleManager
from mnemos.consolidation.summarizer import ConsolidationManager
from mnemos.db.models import Memory, MemoryEmbedding
from mnemos.ingestion.pipeline import IngestionItem, IngestionPipeline


@pytest.mark.asyncio
async def test_memory_consolidation_preserves_source(db_session: AsyncSession):
    tenant_id = "tenant_test"

    item1 = IngestionItem(
        content="Meeting with Dr. Smith regarding Project Quantum on 2024-03-01",
        valid_from=datetime(2024, 3, 1, tzinfo=timezone.utc),
    )
    item2 = IngestionItem(
        content="Follow-up call with Dr. Smith regarding budget constraints on 2024-03-10",
        valid_from=datetime(2024, 3, 10, tzinfo=timezone.utc),
    )
    res1 = await IngestionPipeline.ingest(db_session, tenant_id, item1)
    res2 = await IngestionPipeline.ingest(db_session, tenant_id, item2)

    # Consolidate both memories
    result = await ConsolidationManager.consolidate_memories(
        session=db_session,
        tenant_id=tenant_id,
        memory_ids=[res1.memory_id, res2.memory_id],
        consolidation_type="temporal_summary",
    )

    assert result is not None
    assert result.original_count == 2
    assert result.compression_ratio > 0.0
    assert len(result.source_memory_ids) == 2

    # Verify source memories are NOT deleted
    m1 = await db_session.get(Memory, res1.memory_id)
    m2 = await db_session.get(Memory, res2.memory_id)
    assert m1 is not None
    assert m2 is not None
    assert m1.consolidated_into_id == result.consolidation_id
    assert m2.consolidated_into_id == result.consolidation_id


@pytest.mark.asyncio
async def test_importance_decay_and_purge_cascade(db_session: AsyncSession):
    tenant_id = "tenant_test"

    item = IngestionItem(
        content="Temporary log entry for lifecycle testing",
        importance=0.8,
    )
    res = await IngestionPipeline.ingest(db_session, tenant_id, item)

    # Artificially age the memory by setting created_at to 60 days ago
    mem = await db_session.get(Memory, res.memory_id)
    assert mem is not None
    mem.created_at = datetime.now(timezone.utc) - timedelta(days=60)
    await db_session.flush()

    # Apply decay with 30-day half-life: 60 days is 2 half-lives -> ~0.8 * 0.25 = 0.2
    updated = await LifecycleManager.apply_importance_decay(
        session=db_session,
        tenant_id=tenant_id,
        half_life_days=30.0,
    )
    assert updated >= 1
    await db_session.refresh(mem)
    assert mem.importance < 0.3

    # Purge memory: verify cascade to embedding
    emb_stmt = select(MemoryEmbedding).where(MemoryEmbedding.memory_id == res.memory_id)
    emb_before = (await db_session.execute(emb_stmt)).scalars().first()
    assert emb_before is not None

    purged = await LifecycleManager.purge_memory(db_session, tenant_id, res.memory_id)
    assert purged is True

    # Memory and embedding must no longer exist
    assert await db_session.get(Memory, res.memory_id) is None
    emb_after = (await db_session.execute(emb_stmt)).scalars().first()
    assert emb_after is None
