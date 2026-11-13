import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.db.models import (
    AuditEvent,
    ConsolidationMember,
    Fact,
    Memory,
    MemoryEmbedding,
    Relationship,
)


class LifecycleManager:
    """
    Manages memory lifecycle: importance decay, access tracking,
    soft archival, retention policies, and cascade purging.
    """

    @classmethod
    async def apply_importance_decay(
        cls,
        session: AsyncSession,
        tenant_id: str,
        half_life_days: float = 30.0,
    ) -> int:
        """
        Applies exponential half-life decay to memory importance based on days since last access.
        importance = max(0.05, initial_importance * (0.5 ** (idle_days / half_life_days)))
        """
        now = datetime.now(timezone.utc)
        stmt = select(Memory).where(
            Memory.tenant_id == tenant_id,
            Memory.is_active == True,
        )
        memories = (await session.execute(stmt)).scalars().all()
        updated_count = 0

        for m in memories:
            last_time = m.last_accessed_at or m.created_at
            idle_days = (now - last_time).total_seconds() / 86400.0
            if idle_days > 1.0:
                decay = math.pow(0.5, idle_days / half_life_days)
                new_importance = max(0.05, round(m.importance * decay, 4))
                if new_importance != m.importance:
                    m.importance = new_importance
                    updated_count += 1

        await session.flush()
        return updated_count

    @classmethod
    async def archive_memories(
        cls,
        session: AsyncSession,
        tenant_id: str,
        older_than_days: int = 365,
    ) -> int:
        """Soft archival: marks memories inactive without deleting them."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        stmt = (
            update(Memory)
            .where(
                Memory.tenant_id == tenant_id,
                Memory.is_active == True,
                Memory.created_at < cutoff,
            )
            .values(is_active=False)
        )
        res = await session.execute(stmt)
        await session.flush()
        return res.rowcount

    @classmethod
    async def purge_memory(
        cls,
        session: AsyncSession,
        tenant_id: str,
        memory_id: str,
    ) -> bool:
        """
        Hard deletion: removes memory, cascades to embeddings, facts,
        relationships, and logs audit event.
        """
        memory = await session.get(Memory, memory_id)
        if not memory or memory.tenant_id != tenant_id:
            return False

        # Cascade delete embeddings
        await session.execute(
            delete(MemoryEmbedding).where(MemoryEmbedding.memory_id == memory_id)
        )
        # Cascade delete consolidation member links
        await session.execute(
            delete(ConsolidationMember).where(ConsolidationMember.memory_id == memory_id)
        )
        # Delete relationships derived from this memory
        await session.execute(
            delete(Relationship).where(Relationship.source_memory_id == memory_id)
        )
        # Delete facts derived from this memory
        await session.execute(
            delete(Fact).where(Fact.source_memory_id == memory_id)
        )
        # Delete memory itself
        await session.delete(memory)

        # Record deletion audit log
        audit = AuditEvent(
            tenant_id=tenant_id,
            event_type="deletion",
            entity_type="memory",
            entity_id=memory_id,
            actor="lifecycle_service",
            details={"purged_at": datetime.now(timezone.utc).isoformat()},
        )
        session.add(audit)
        await session.flush()
        return True
