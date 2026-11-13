import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.core.logging import logger
from mnemos.db.models import (
    SENTINEL_MAX_TIME,
    AuditEvent,
    Memory,
    MemoryEmbedding,
    Relationship,
)
from mnemos.evolution.policies import ResolutionPolicy
from mnemos.evolution.resolver import EvolutionManager
from mnemos.ingestion.extractor import MemoryExtractor
from mnemos.ingestion.resolver import EntityResolver
from mnemos.retrieval.embeddings import get_embedding_provider
from mnemos.temporal.intervals import ensure_utc


class IngestionItem(BaseModel):
    content: str
    memory_type: str = "observation"  # raw_conversation, fact, observation, event, summary
    source: str = "agent"
    confidence: float = 1.0
    importance: float = 0.5
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestionResult(BaseModel):
    memory_id: str
    is_duplicate: bool
    entities_count: int
    facts_count: int
    relationships_count: int
    content_hash: str


class IngestionPipeline:
    """Production memory ingestion pipeline with bitemporal anchoring and provenance tracking."""

    @classmethod
    def compute_hash(cls, content: str) -> str:
        clean = content.strip().lower()
        return hashlib.sha256(clean.encode("utf-8")).hexdigest()

    @classmethod
    async def ingest(
        cls,
        session: AsyncSession,
        tenant_id: str,
        item: IngestionItem,
    ) -> IngestionResult:
        now = datetime.now(timezone.utc)
        content_hash = cls.compute_hash(item.content)

        # 1. Idempotency Check
        existing_stmt = (
            select(Memory)
            .where(
                Memory.tenant_id == tenant_id,
                Memory.content_hash == content_hash,
                Memory.is_active == True,
            )
            .limit(1)
        )
        existing = (await session.execute(existing_stmt)).scalars().first()
        if existing:
            existing.access_count += 1
            existing.last_accessed_at = now
            await session.flush()
            return IngestionResult(
                memory_id=existing.id,
                is_duplicate=True,
                entities_count=0,
                facts_count=0,
                relationships_count=0,
                content_hash=content_hash,
            )

        # 2. Determine Temporal Coordinates
        valid_from = ensure_utc(item.valid_from) if item.valid_from else now
        valid_to = ensure_utc(item.valid_to, default_max=True) if item.valid_to else SENTINEL_MAX_TIME

        # 3. Create Memory Record
        memory_id = f"mem_{uuid.uuid4().hex[:12]}"
        memory = Memory(
            id=memory_id,
            tenant_id=tenant_id,
            memory_type=item.memory_type,
            original_content=item.content,
            normalized_content=item.content.strip(),
            content_hash=content_hash,
            source=item.source,
            confidence=item.confidence,
            importance=item.importance,
            valid_from=valid_from,
            valid_to=valid_to,
            recorded_from=now,
            recorded_to=SENTINEL_MAX_TIME,
            is_active=True,
            metadata_=item.metadata,
        )
        session.add(memory)

        # 4. Extract Entities and Facts
        extracted_entities, extracted_facts = MemoryExtractor.extract(
            item.content, default_valid_time=valid_from
        )

        resolved_entities: dict[str, Any] = {}
        for ent in extracted_entities:
            resolved = await EntityResolver.resolve_or_create(
                session=session,
                tenant_id=tenant_id,
                name=ent.name,
                entity_type=ent.entity_type,
                confidence=ent.confidence,
            )
            resolved_entities[ent.name.lower()] = resolved

        # 5. Create Facts and Graph Relationships
        facts_created = 0
        relationships_created = 0
        rels_to_create = []

        for f in extracted_facts:
            subj_entity = resolved_entities.get(f.subject.lower())
            if not subj_entity:
                subj_entity = await EntityResolver.resolve_or_create(
                    session=session,
                    tenant_id=tenant_id,
                    name=f.subject,
                    entity_type="concept",
                )
                resolved_entities[f.subject.lower()] = subj_entity

            obj_entity = None
            if not f.is_literal:
                obj_entity = resolved_entities.get(f.object.lower())
                if not obj_entity:
                    obj_entity = await EntityResolver.resolve_or_create(
                        session=session,
                        tenant_id=tenant_id,
                        name=f.object,
                        entity_type="concept",
                    )
                    resolved_entities[f.object.lower()] = obj_entity

            fact_valid_from = f.valid_from or valid_from
            fact_valid_to = f.valid_to or valid_to

            policy = (
                ResolutionPolicy.SOURCE_RELIABILITY
                if f.confidence != 1.0 or item.confidence != 1.0
                else ResolutionPolicy.TEMPORAL_RECENCY
            )

            fact = await EvolutionManager.process_fact_evolution(
                session=session,
                tenant_id=tenant_id,
                subject_id=subj_entity.id,
                predicate=f.predicate,
                object_id=obj_entity.id if obj_entity else None,
                object_literal=f.object if f.is_literal else None,
                valid_from=fact_valid_from,
                valid_to=fact_valid_to,
                confidence=f.confidence * item.confidence,
                importance=item.importance,
                source_memory_id=memory_id,
                policy=policy,
                metadata=f.metadata,
            )
            fact_id = fact.id
            facts_created += 1

            # If relationship between two entities, prepare graph edge
            if obj_entity and subj_entity.id != obj_entity.id:
                rel_id = f"rel_{uuid.uuid4().hex[:12]}"
                rel = Relationship(
                    id=rel_id,
                    tenant_id=tenant_id,
                    source_entity_id=subj_entity.id,
                    target_entity_id=obj_entity.id,
                    relation_type=f.predicate,
                    weight=1.0,
                    fact_id=fact_id,
                    source_memory_id=memory_id,
                    valid_from=fact_valid_from,
                    valid_to=fact_valid_to,
                    recorded_from=now,
                    recorded_to=SENTINEL_MAX_TIME,
                    is_active=True,
                    properties=f.metadata,
                )
                rels_to_create.append(rel)

        # Flush facts first so foreign key references to facts exist
        await session.flush()

        for rel in rels_to_create:
            session.add(rel)
            relationships_created += 1

        if rels_to_create:
            await session.flush()

        # 6. Generate Vector Embedding
        provider = get_embedding_provider()
        try:
            vec = provider.embed_query(item.content)
            emb = MemoryEmbedding(
                id=f"emb_{uuid.uuid4().hex[:12]}",
                tenant_id=tenant_id,
                memory_id=memory_id,
                embedding=vec,
                dimension=len(vec),
                model_name=getattr(provider, "_model_name", "BAAI/bge-small-en-v1.5"),
            )
            session.add(emb)
        except Exception as e:
            logger.warning(f"Embedding generation failed for memory {memory_id}: {e}")

        # 7. Audit Event
        audit = AuditEvent(
            tenant_id=tenant_id,
            event_type="ingest",
            entity_type="memory",
            entity_id=memory_id,
            actor=item.source,
            details={
                "content_hash": content_hash,
                "facts_count": facts_created,
                "entities_count": len(resolved_entities),
            },
        )
        session.add(audit)
        await session.flush()

        return IngestionResult(
            memory_id=memory_id,
            is_duplicate=False,
            entities_count=len(resolved_entities),
            facts_count=facts_created,
            relationships_count=relationships_created,
            content_hash=content_hash,
        )

    @classmethod
    async def ingest_batch(
        cls,
        session: AsyncSession,
        tenant_id: str,
        items: list[IngestionItem],
    ) -> list[IngestionResult]:
        """Batch ingestion with transaction safety."""
        results = []
        for it in items:
            res = await cls.ingest(session, tenant_id, it)
            results.append(res)
        return results
