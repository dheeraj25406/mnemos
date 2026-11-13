from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.api.deps import get_current_tenant_id
from mnemos.db.session import get_db_session
from mnemos.graph.engine import TemporalGraphEngine
from mnemos.graph.traversal import PathResult, SubgraphResult

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])


@router.get("/subgraph", response_model=SubgraphResult)
async def traverse_subgraph(
    seed_entity_id: str = Query(...),
    max_depth: int = Query(default=2, ge=1, le=5),
    valid_at: datetime | None = Query(default=None),
    recorded_at: datetime | None = Query(default=None),
    direction: Literal["out", "in", "both"] = Query(default="both"),
    max_nodes: int = Query(default=100, le=500),
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Traverse temporal knowledge graph starting at seed_entity_id.
    Filters edges based on bitemporal valid time and transaction time.
    """
    return await TemporalGraphEngine.traverse_subgraph(
        session=session,
        tenant_id=tenant_id,
        seed_entity_id=seed_entity_id,
        max_depth=max_depth,
        valid_at=valid_at,
        recorded_at=recorded_at,
        direction=direction,
        max_nodes=max_nodes,
    )


@router.get("/path", response_model=PathResult)
async def find_shortest_path(
    start_entity_id: str = Query(...),
    end_entity_id: str = Query(...),
    max_depth: int = Query(default=4, ge=1, le=6),
    valid_at: datetime | None = Query(default=None),
    recorded_at: datetime | None = Query(default=None),
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Find shortest temporal connection path between two entities."""
    return await TemporalGraphEngine.find_path(
        session=session,
        tenant_id=tenant_id,
        start_entity_id=start_entity_id,
        end_entity_id=end_entity_id,
        max_depth=max_depth,
        valid_at=valid_at,
        recorded_at=recorded_at,
    )
