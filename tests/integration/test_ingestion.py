from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.db.models import Memory, Entity, Fact, Relationship, AuditEvent, MemoryEmbedding
from mnemos.ingestion.pipeline import IngestionPipeline, IngestionItem
from mnemos.ingestion.resolver import EntityResolver


@pytest.mark.asyncio
async def test_memory_ingestion_and_provenance(db_session: AsyncSession):
    tenant_id = "tenant_test"
    item = IngestionItem(
        content="Alice works at Quantum Labs in Boston as of 2024-01-15",
        memory_type="observation",
        source="agent-observer-1",
        confidence=0.95,
        importance=0.8,
        valid_from=datetime(2024, 1, 15, tzinfo=timezone.utc),
        metadata={"session_id": "sess-99"},
    )

    result = await IngestionPipeline.ingest(db_session, tenant_id, item)

    assert result.is_duplicate is False
    assert result.memory_id.startswith("mem_")
    assert result.entities_count >= 2
    assert result.facts_count >= 1

    # Verify memory was saved
    memory = await db_session.get(Memory, result.memory_id)
    assert memory is not None
    assert memory.tenant_id == tenant_id
    assert memory.source == "agent-observer-1"
    assert memory.valid_from == datetime(2024, 1, 15, tzinfo=timezone.utc)
    assert memory.metadata_["session_id"] == "sess-99"

    # Verify entities were extracted and canonicalized
    entities = (
        await db_session.execute(select(Entity).where(Entity.tenant_id == tenant_id))
    ).scalars().all()
    entity_names = {e.name.lower() for e in entities}
    assert "alice" in entity_names
    assert "quantum labs" in entity_names

    # Verify bitemporal fact was created linked to memory
    facts = (
        await db_session.execute(
            select(Fact).where(Fact.source_memory_id == result.memory_id)
        )
    ).scalars().all()
    assert len(facts) >= 1
    fact = facts[0]
    assert fact.predicate == "works_at"
    assert fact.valid_from == datetime(2024, 1, 15, tzinfo=timezone.utc)

    # Verify relationship was created
    rels = (
        await db_session.execute(
            select(Relationship).where(Relationship.source_memory_id == result.memory_id)
        )
    ).scalars().all()
    assert len(rels) >= 1
    assert rels[0].relation_type == "works_at"

    # Verify vector embedding was stored
    emb = (
        await db_session.execute(
            select(MemoryEmbedding).where(MemoryEmbedding.memory_id == result.memory_id)
        )
    ).scalars().first()
    assert emb is not None
    assert len(emb.embedding) == 384

    # Verify Audit log was created
    audits = (
        await db_session.execute(
            select(AuditEvent).where(
                AuditEvent.tenant_id == tenant_id,
                AuditEvent.entity_id == result.memory_id,
            )
        )
    ).scalars().all()
    assert len(audits) == 1
    assert audits[0].event_type == "ingest"
    assert audits[0].actor == "agent-observer-1"


@pytest.mark.asyncio
async def test_idempotent_ingestion_duplicate_detection(db_session: AsyncSession):
    tenant_id = "tenant_test"
    item = IngestionItem(
        content="Idempotent Fact Ingestion Check",
        memory_type="fact",
    )

    res1 = await IngestionPipeline.ingest(db_session, tenant_id, item)
    assert res1.is_duplicate is False

    # Second ingestion of exact same content
    res2 = await IngestionPipeline.ingest(db_session, tenant_id, item)
    assert res2.is_duplicate is True
    assert res2.memory_id == res1.memory_id

    # Verify access count incremented
    mem = await db_session.get(Memory, res1.memory_id)
    assert mem is not None
    assert mem.access_count == 1
