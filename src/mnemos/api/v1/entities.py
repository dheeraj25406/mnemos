from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.api.deps import get_current_tenant_id
from mnemos.db.models import Entity, EntityAlias
from mnemos.db.session import get_db_session
from mnemos.ingestion.resolver import EntityResolver

router = APIRouter(prefix="/entities", tags=["Entities"])


class MergeEntitiesRequest(BaseModel):
    primary_entity_id: str
    secondary_entity_id: str


@router.get("")
async def list_entities(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    entity_type: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
):
    """List canonical entities with aliases and types."""
    query = select(Entity).where(Entity.tenant_id == tenant_id, Entity.is_active == True)
    if entity_type:
        query = query.where(Entity.entity_type == entity_type)

    total_stmt = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_stmt)).scalar_one()

    query = query.order_by(Entity.name.asc()).offset(offset).limit(limit)
    rows = (await session.execute(query)).scalars().all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": e.id,
                "name": e.name,
                "entity_type": e.entity_type,
                "description": e.description,
                "confidence": e.confidence,
                "created_at": e.created_at.isoformat(),
            }
            for e in rows
        ],
    }


@router.get("/{entity_id}")
async def get_entity(
    entity_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Get entity details and its known aliases."""
    entity = await session.get(Entity, entity_id)
    if not entity or entity.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Entity not found")

    alias_stmt = select(EntityAlias.alias).where(EntityAlias.entity_id == entity_id)
    aliases = (await session.execute(alias_stmt)).scalars().all()

    return {
        "id": entity.id,
        "name": entity.name,
        "entity_type": entity.entity_type,
        "description": entity.description,
        "canonical_id": entity.canonical_id,
        "confidence": entity.confidence,
        "is_active": entity.is_active,
        "aliases": list(aliases),
        "created_at": entity.created_at.isoformat(),
        "updated_at": entity.updated_at.isoformat(),
    }


@router.post("/merge")
async def merge_entities(
    request: MergeEntitiesRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Merge secondary entity into primary canonical entity."""
    try:
        merged = await EntityResolver.merge_entities(
            session=session,
            tenant_id=tenant_id,
            primary_id=request.primary_entity_id,
            secondary_id=request.secondary_entity_id,
        )
        return {
            "status": "merged",
            "primary_id": merged.id,
            "secondary_id": request.secondary_entity_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
