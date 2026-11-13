import uuid
from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.db.models import (
    AuditEvent,
    ConsolidationMember,
    Fact,
    Memory,
    MemoryConsolidation,
)


class ConsolidationResult(BaseModel):
    consolidation_id: str
    consolidation_type: str
    original_count: int
    original_size_bytes: int
    compressed_size_bytes: int
    compression_ratio: float
    summary_content: str
    source_memory_ids: list[str]


class ConsolidationManager:
    """
    Intelligent non-destructive memory consolidation.
    Synthesizes repeated or temporally evolving facts into compact summaries
    while permanently preserving source memories, facts, and provenance links.
    """

    @classmethod
    async def consolidate_memories(
        cls,
        session: AsyncSession,
        tenant_id: str,
        memory_ids: list[str],
        consolidation_type: str = "temporal_summary",
        entity_id: str | None = None,
    ) -> ConsolidationResult | None:
        """
        Consolidates a specific list of memories into a structured summary.
        Links original memories non-destructively through ConsolidationMember.
        """
        if not memory_ids:
            return None

        # Fetch memories
        stmt = select(Memory).where(
            Memory.tenant_id == tenant_id,
            Memory.id.in_(memory_ids),
            Memory.is_active == True,
        ).order_by(Memory.valid_from.asc())
        mems = (await session.execute(stmt)).scalars().all()

        if not mems:
            return None

        original_size = sum(len(m.normalized_content.encode("utf-8")) for m in mems)

        # Synthesize chronological summary
        summary_lines = []
        for m in mems:
            vt_str = m.valid_from.strftime("%Y-%m-%d") if m.valid_from else "Unknown date"
            summary_lines.append(f"[{vt_str}] {m.normalized_content}")

        summary_content = "\n".join(summary_lines)
        compressed_size = len(summary_content.encode("utf-8"))
        comp_ratio = compressed_size / max(1, original_size)

        cons_id = f"cons_{uuid.uuid4().hex[:12]}"
        cons = MemoryConsolidation(
            id=cons_id,
            tenant_id=tenant_id,
            consolidation_type=consolidation_type,
            summary_content=summary_content,
            entity_id=entity_id,
            original_count=len(mems),
            original_size_bytes=original_size,
            compressed_size_bytes=compressed_size,
            compression_ratio=comp_ratio,
            metadata_={"consolidated_at": datetime.now(timezone.utc).isoformat()},
        )
        session.add(cons)

        # Create members and link source memories
        for m in mems:
            member = ConsolidationMember(
                consolidation_id=cons_id,
                memory_id=m.id,
                contribution_weight=1.0 / len(mems),
            )
            session.add(member)
            m.consolidated_into_id = cons_id

        # Audit event
        audit = AuditEvent(
            tenant_id=tenant_id,
            event_type="consolidation",
            entity_type="memory_consolidation",
            entity_id=cons_id,
            actor="consolidation_worker",
            details={
                "consolidation_type": consolidation_type,
                "memory_count": len(mems),
                "compression_ratio": round(comp_ratio, 3),
            },
        )
        session.add(audit)
        await session.flush()

        return ConsolidationResult(
            consolidation_id=cons_id,
            consolidation_type=consolidation_type,
            original_count=len(mems),
            original_size_bytes=original_size,
            compressed_size_bytes=compressed_size,
            compression_ratio=round(comp_ratio, 3),
            summary_content=summary_content,
            source_memory_ids=[m.id for m in mems],
        )

    @classmethod
    async def consolidate_entity_memories(
        cls,
        session: AsyncSession,
        tenant_id: str,
        entity_id: str,
    ) -> ConsolidationResult | None:
        """Consolidates all unconsolidated memories related to a given entity."""
        # Find memory IDs from facts linked to this entity
        fact_stmt = select(Fact.source_memory_id).where(
            Fact.tenant_id == tenant_id,
            (Fact.subject_id == entity_id) | (Fact.object_id == entity_id),
            Fact.source_memory_id.isnot(None),
        ).distinct()
        res = (await session.execute(fact_stmt)).scalars().all()
        memory_ids = [mid for mid in res if mid]

        if len(memory_ids) < 2:
            return None

        return await cls.consolidate_memories(
            session=session,
            tenant_id=tenant_id,
            memory_ids=memory_ids,
            consolidation_type="entity_summary",
            entity_id=entity_id,
        )
