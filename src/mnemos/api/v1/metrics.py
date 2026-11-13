from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.api.deps import get_current_tenant_id
from mnemos.db.models import (
    AuditEvent,
    Entity,
    Fact,
    Memory,
    MemoryConsolidation,
    Relationship,
)
from mnemos.db.session import get_db_session

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("")
async def get_metrics(
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Real backend metrics for operational observability."""
    mem_count = (
        await session.execute(
            select(func.count(Memory.id)).where(Memory.tenant_id == tenant_id, Memory.is_active == True)
        )
    ).scalar_one()

    ent_count = (
        await session.execute(
            select(func.count(Entity.id)).where(Entity.tenant_id == tenant_id, Entity.is_active == True)
        )
    ).scalar_one()

    fact_count = (
        await session.execute(
            select(func.count(Fact.id)).where(Fact.tenant_id == tenant_id, Fact.is_retracted == False)
        )
    ).scalar_one()

    rel_count = (
        await session.execute(
            select(func.count(Relationship.id)).where(
                Relationship.tenant_id == tenant_id, Relationship.is_active == True
            )
        )
    ).scalar_one()

    cons_count = (
        await session.execute(
            select(func.count(MemoryConsolidation.id)).where(MemoryConsolidation.tenant_id == tenant_id)
        )
    ).scalar_one()

    audit_count = (
        await session.execute(
            select(func.count(AuditEvent.id)).where(AuditEvent.tenant_id == tenant_id)
        )
    ).scalar_one()

    return {
        "tenant_id": tenant_id,
        "memories_total": mem_count,
        "entities_total": ent_count,
        "facts_total": fact_count,
        "relationships_total": rel_count,
        "consolidations_total": cons_count,
        "audit_events_total": audit_count,
    }
