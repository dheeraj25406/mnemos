from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.api.deps import get_current_tenant_id
from mnemos.db.session import get_db_session
from mnemos.temporal.reasoning import (
    TemporalReasoningEngine,
    TimelineDiffResult,
)

router = APIRouter(prefix="/temporal", tags=["Temporal Reasoning"])


@router.get("/timeline-diff", response_model=TimelineDiffResult)
async def get_timeline_diff(
    subject: str = Query(...),
    t1: datetime = Query(...),
    t2: datetime = Query(...),
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Compare an entity's facts between two valid times t1 and t2.
    Identifies what changed (superseded or evolved) and what remained invariant.
    """
    return await TemporalReasoningEngine.compare_timeline(
        session=session,
        tenant_id=tenant_id,
        subject_name=subject,
        t1=t1,
        t2=t2,
    )


@router.get("/acquisition-time")
async def get_knowledge_acquisition_time(
    subject: str = Query(...),
    predicate: str = Query(...),
    tenant_id: str = Depends(get_current_tenant_id),
    session: AsyncSession = Depends(get_db_session),
):
    """Answers: 'When did Mnemos first learn about fact X?' (Transaction time audit)."""
    res = await TemporalReasoningEngine.get_knowledge_acquisition_time(
        session=session,
        tenant_id=tenant_id,
        subject_name=subject,
        predicate=predicate,
    )
    if not res:
        raise HTTPException(status_code=404, detail="No matching knowledge acquisition record found.")
    return res
