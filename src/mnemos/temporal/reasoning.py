from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.db.models import Entity, Fact
from mnemos.temporal.bitemporal import apply_bitemporal_filters
from mnemos.temporal.intervals import ensure_utc


class TimelineChange(BaseModel):
    subject: str
    predicate: str
    previous_value: str | None = None
    new_value: str | None = None
    effective_time: str
    recorded_time: str
    confidence: float


class TimelineDiffResult(BaseModel):
    subject_name: str
    time_start: str
    time_end: str
    changes: list[TimelineChange]
    unchanged_facts: list[str]


class TemporalReasoningAnswer(BaseModel):
    query: str
    answer: str
    known_facts: list[dict[str, Any]] = Field(default_factory=list)
    inferred_relationships: list[dict[str, Any]] = Field(default_factory=list)
    uncertain_information: list[dict[str, Any]] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    temporal_anchor: str | None = None


class TemporalReasoningEngine:
    """
    Structured temporal reasoning engine. Answers historical truth,
    timeline delta comparisons, and knowledge acquisition audits.
    """

    @classmethod
    async def compare_timeline(
        cls,
        session: AsyncSession,
        tenant_id: str,
        subject_name: str,
        t1: datetime,
        t2: datetime,
    ) -> TimelineDiffResult:
        """
        Computes what changed for subject_name between date t1 and date t2.
        """
        vt1 = ensure_utc(t1)
        vt2 = ensure_utc(t2)

        # 1. Resolve subject entity
        ent_stmt = select(Entity).where(
            Entity.tenant_id == tenant_id,
            Entity.name.ilike(subject_name),
            Entity.is_active == True,
        )
        entity = (await session.execute(ent_stmt)).scalars().first()
        if not entity:
            return TimelineDiffResult(
                subject_name=subject_name,
                time_start=vt1.isoformat(),
                time_end=vt2.isoformat(),
                changes=[],
                unchanged_facts=[],
            )

        # 2. Query facts active at t1
        q1 = select(Fact).where(Fact.tenant_id == tenant_id, Fact.subject_id == entity.id, Fact.is_retracted == False)
        q1 = apply_bitemporal_filters(q1, Fact, valid_at=vt1)
        facts_t1 = (await session.execute(q1)).scalars().all()

        # 3. Query facts active at t2
        q2 = select(Fact).where(Fact.tenant_id == tenant_id, Fact.subject_id == entity.id, Fact.is_retracted == False)
        q2 = apply_bitemporal_filters(q2, Fact, valid_at=vt2)
        facts_t2 = (await session.execute(q2)).scalars().all()

        # Build lookup maps by predicate
        map_t1 = {f.predicate: f for f in facts_t1}
        map_t2 = {f.predicate: f for f in facts_t2}

        all_predicates = set(map_t1.keys()).union(set(map_t2.keys()))
        changes: list[TimelineChange] = []
        unchanged: list[str] = []

        for pred in all_predicates:
            f1 = map_t1.get(pred)
            f2 = map_t2.get(pred)

            val1 = None
            if f1:
                if f1.object_id:
                    target_ent = await session.get(Entity, f1.object_id)
                    val1 = target_ent.name if target_ent else f1.object_id
                else:
                    val1 = f1.object_literal

            val2 = None
            if f2:
                if f2.object_id:
                    target_ent = await session.get(Entity, f2.object_id)
                    val2 = target_ent.name if target_ent else f2.object_id
                else:
                    val2 = f2.object_literal

            if val1 == val2 and val1 is not None:
                unchanged.append(f"{pred}: {val1}")
            else:
                changes.append(
                    TimelineChange(
                        subject=subject_name,
                        predicate=pred,
                        previous_value=val1,
                        new_value=val2,
                        effective_time=f2.valid_from.isoformat() if f2 else vt2.isoformat(),
                        recorded_time=f2.recorded_from.isoformat() if f2 else vt2.isoformat(),
                        confidence=f2.confidence if f2 else 1.0,
                    )
                )

        return TimelineDiffResult(
            subject_name=subject_name,
            time_start=vt1.isoformat(),
            time_end=vt2.isoformat(),
            changes=changes,
            unchanged_facts=unchanged,
        )

    @classmethod
    async def get_knowledge_acquisition_time(
        cls,
        session: AsyncSession,
        tenant_id: str,
        subject_name: str,
        predicate: str,
    ) -> dict[str, Any] | None:
        """Determines when Mnemos first learned a specific fact."""
        stmt = (
            select(Fact)
            .join(Entity, Entity.id == Fact.subject_id)
            .where(
                Fact.tenant_id == tenant_id,
                Entity.name.ilike(subject_name),
                Fact.predicate == predicate,
            )
            .order_by(Fact.recorded_from.asc())
        )
        fact = (await session.execute(stmt)).scalars().first()
        if not fact:
            return None

        target_name = fact.object_literal
        if fact.object_id:
            tgt = await session.get(Entity, fact.object_id)
            if tgt:
                target_name = tgt.name

        return {
            "subject": subject_name,
            "predicate": predicate,
            "object": target_name,
            "first_recorded_at": fact.recorded_from.isoformat(),
            "valid_from": fact.valid_from.isoformat(),
            "confidence": fact.confidence,
        }
