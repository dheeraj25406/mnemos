from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.api.deps import get_current_tenant_id
from mnemos.consolidation.summarizer import (
    ConsolidationManager,
    ConsolidationResult,
)
from mnemos.db.models import MemoryConsolidation
from mnemos.db.session import get_db_session

router = APIRouter(prefix="/consolidation", tags=["Consolidation"])


class TriggerEntityConsolidationRequest(BaseModel):
    entity_id: str


class TriggerCustomConsolidationRequest(BaseModel):
    memory_ids: list[str]
    consolidation_type: str = "temporal_summary"


@router.post("/entity", response_model=ConsolidationResult)
async def trigger_entity_consolidation(
    request: TriggerEntityConsolidationRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Trigger non-destructive consolidation of memories linked to an entity."""
    res = await ConsolidationManager.consolidate_entity_memories(
        session=session,
        tenant_id=tenant_id,
        entity_id=request.entity_id,
    )
    if not res:
        raise HTTPException(status_code=400, detail="Insufficient memories to consolidate.")
    return res


@router.post("/custom", response_model=ConsolidationResult)
async def trigger_custom_consolidation(
    request: TriggerCustomConsolidationRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Trigger consolidation for explicit list of memory IDs."""
    res = await ConsolidationManager.consolidate_memories(
        session=session,
        tenant_id=tenant_id,
        memory_ids=request.memory_ids,
        consolidation_type=request.consolidation_type,
    )
    if not res:
        raise HTTPException(status_code=400, detail="Failed to consolidate provided memories.")
    return res


@router.get("")
async def list_consolidations(
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
):
    """List consolidation runs."""
    stmt = (
        select(MemoryConsolidation)
        .where(MemoryConsolidation.tenant_id == tenant_id)
        .order_by(MemoryConsolidation.created_at.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "id": c.id,
            "type": c.consolidation_type,
            "original_count": c.original_count,
            "compression_ratio": c.compression_ratio,
            "summary": c.summary_content,
            "created_at": c.created_at.isoformat(),
        }
        for c in rows
    ]
