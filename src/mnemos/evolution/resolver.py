import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.core.logging import logger
from mnemos.db.models import AuditEvent, Fact, Relationship, SENTINEL_MAX_TIME
from mnemos.evolution.detector import ContradictionDetector
from mnemos.evolution.policies import (
    ConflictClassification,
    ResolutionPolicy,
)
from mnemos.temporal.intervals import ensure_utc


class EvolutionManager:
    """
    Manages non-destructive fact evolution, contradiction resolution,
    and confidence recalibration.
    """

    @classmethod
    async def process_fact_evolution(
        cls,
        session: AsyncSession,
        tenant_id: str,
        subject_id: str,
        predicate: str,
        object_id: str | None,
        object_literal: str | None,
        valid_from: datetime,
        valid_to: datetime | None,
        confidence: float = 1.0,
        importance: float = 0.5,
        source_memory_id: str | None = None,
        policy: ResolutionPolicy = ResolutionPolicy.TEMPORAL_RECENCY,
        metadata: dict | None = None,
    ) -> Fact:
        """
        Ingests a new fact while detecting and non-destructively resolving conflicts.
        Preserves all historical truth and knowledge records.
        """
        now = datetime.now(timezone.utc)
        vf = ensure_utc(valid_from)
        vt = ensure_utc(valid_to, default_max=True) if valid_to else SENTINEL_MAX_TIME
        meta = metadata or {}

        # 1. Detect conflicts
        conflicts = await ContradictionDetector.detect_conflicts(
            session=session,
            tenant_id=tenant_id,
            subject_id=subject_id,
            predicate=predicate,
            object_id=object_id,
            object_literal=object_literal,
            valid_from=vf,
            valid_to=vt,
        )

        new_fact_id = f"fact_{uuid.uuid4().hex[:12]}"
        new_fact = Fact(
            id=new_fact_id,
            tenant_id=tenant_id,
            source_memory_id=source_memory_id,
            subject_id=subject_id,
            predicate=predicate,
            object_id=object_id,
            object_literal=object_literal,
            valid_from=vf,
            valid_to=vt,
            recorded_from=now,
            recorded_to=SENTINEL_MAX_TIME,
            confidence=confidence,
            importance=importance,
            is_retracted=False,
            metadata_=meta,
        )

        if not conflicts:
            session.add(new_fact)
            await session.flush()
            return new_fact

        # 2. Process conflicts
        for conflict in conflicts:
            old_fact = await session.get(Fact, conflict.existing_fact_id)
            if not old_fact:
                continue

            if conflict.classification == ConflictClassification.TEMPORAL_EVOLUTION:
                # Sequential state evolution: e.g. Person A left Company X on vf to work at Company Y
                session.add(new_fact)
                await session.flush()

                # Close transaction window for old fact's previous view
                old_fact.recorded_to = now
                old_fact.valid_to = vf
                old_fact.superseded_by_id = new_fact.id

                # Create updated active version of old fact with closed valid time [old.vf, new.vf)
                old_fact_closed = Fact(
                    id=f"fact_{uuid.uuid4().hex[:12]}",
                    tenant_id=tenant_id,
                    source_memory_id=old_fact.source_memory_id,
                    subject_id=old_fact.subject_id,
                    predicate=old_fact.predicate,
                    object_id=old_fact.object_id,
                    object_literal=old_fact.object_literal,
                    valid_from=old_fact.valid_from,
                    valid_to=vf,  # Closed at the moment of evolution
                    recorded_from=now,
                    recorded_to=SENTINEL_MAX_TIME,
                    confidence=old_fact.confidence,
                    importance=old_fact.importance,
                    superseded_by_id=new_fact.id,
                    metadata_=old_fact.metadata_,
                )
                session.add(old_fact_closed)

                # Record audit trail
                audit = AuditEvent(
                    tenant_id=tenant_id,
                    event_type="conflict_resolution",
                    entity_type="fact",
                    entity_id=new_fact.id,
                    actor="evolution_manager",
                    details={
                        "resolution": "temporal_evolution_supersession",
                        "superseded_fact_id": old_fact.id,
                        "transition_time": vf.isoformat(),
                    },
                )
                session.add(audit)

            elif conflict.classification == ConflictClassification.DIRECT_CONTRADICTION:
                if policy == ResolutionPolicy.HUMAN_REVIEW:
                    new_fact.metadata_["conflict_status"] = "pending_human_review"
                    new_fact.metadata_["conflicts_with"] = old_fact.id
                    session.add(new_fact)

                    audit = AuditEvent(
                        tenant_id=tenant_id,
                        event_type="conflict_resolution",
                        entity_type="fact",
                        entity_id=new_fact.id,
                        actor="evolution_manager",
                        details={
                            "resolution": "flagged_for_human_review",
                            "conflicting_fact_id": old_fact.id,
                        },
                    )
                    session.add(audit)

                elif policy == ResolutionPolicy.SOURCE_RELIABILITY:
                    if confidence >= old_fact.confidence:
                        # New fact wins: retract old fact
                        session.add(new_fact)
                        await session.flush()
                        old_fact.recorded_to = now
                        old_fact.is_retracted = True
                        old_fact.superseded_by_id = new_fact.id
                    else:
                        # Old fact wins: retract new fact immediately
                        new_fact.is_retracted = True
                        new_fact.recorded_to = now
                        session.add(new_fact)

                elif policy == ResolutionPolicy.CONFIDENCE_WEIGHTED:
                    score_new = confidence * importance
                    score_old = old_fact.confidence * old_fact.importance
                    if score_new >= score_old:
                        session.add(new_fact)
                        await session.flush()
                        old_fact.recorded_to = now
                        old_fact.superseded_by_id = new_fact.id
                    else:
                        new_fact.is_retracted = True
                        new_fact.recorded_to = now
                        session.add(new_fact)

                else:  # TEMPORAL_RECENCY
                    session.add(new_fact)
                    await session.flush()
                    old_fact.recorded_to = now
                    old_fact.superseded_by_id = new_fact.id

        await session.flush()
        return new_fact

    @classmethod
    async def recalibrate_confidence(
        cls,
        session: AsyncSession,
        tenant_id: str,
        fact_id: str,
        new_confidence: float,
        reason: str = "source_verification",
    ) -> Fact:
        """Recalibrate fact confidence with an audit trail."""
        fact = await session.get(Fact, fact_id)
        if not fact or fact.tenant_id != tenant_id:
            raise ValueError(f"Fact {fact_id} not found")

        old_conf = fact.confidence
        fact.confidence = max(0.0, min(1.0, new_confidence))

        audit = AuditEvent(
            tenant_id=tenant_id,
            event_type="update",
            entity_type="fact",
            entity_id=fact.id,
            actor="recalibration_service",
            details={
                "previous_confidence": old_conf,
                "new_confidence": fact.confidence,
                "reason": reason,
            },
        )
        session.add(audit)
        await session.flush()
        return fact
