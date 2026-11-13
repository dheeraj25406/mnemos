from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.db.models import Fact
from mnemos.evolution.policies import (
    MUTUALLY_EXCLUSIVE_PREDICATES,
    ConflictClassification,
    ConflictReport,
)
from mnemos.temporal.intervals import TimeInterval, ensure_utc


class ContradictionDetector:
    """Detects semantic and temporal contradictions between candidate facts and existing facts."""

    @classmethod
    async def detect_conflicts(
        cls,
        session: AsyncSession,
        tenant_id: str,
        subject_id: str,
        predicate: str,
        object_id: str | None,
        object_literal: str | None,
        valid_from: datetime,
        valid_to: datetime,
    ) -> list[ConflictReport]:
        """
        Finds existing facts that conflict with the candidate fact.
        Distinguishes between temporal evolution (state changes over time)
        and genuine simultaneous contradictions.
        """
        cand_vf = ensure_utc(valid_from)
        cand_vt = ensure_utc(valid_to, default_max=True)
        cand_interval = TimeInterval(start=cand_vf, end=cand_vt)

        # Retrieve active existing facts for this subject and predicate
        now = datetime.now(timezone.utc)
        stmt = select(Fact).where(
            Fact.tenant_id == tenant_id,
            Fact.subject_id == subject_id,
            Fact.predicate == predicate,
            Fact.is_retracted == False,
            Fact.recorded_from <= now,
            Fact.recorded_to > now,
        )
        existing_facts = (await session.execute(stmt)).scalars().all()

        reports: list[ConflictReport] = []

        is_mutually_exclusive = predicate in MUTUALLY_EXCLUSIVE_PREDICATES

        for ef in existing_facts:
            # Check if target values differ: both object_id and object_literal must match
            same_object_id = (object_id is None and ef.object_id is None) or (object_id == ef.object_id)
            same_literal = (object_literal is None and ef.object_literal is None) or (object_literal == ef.object_literal)
            same_target = same_object_id and same_literal

            if same_target:
                continue  # Identical fact, no contradiction

            # Target is different. Check temporal overlap.
            ef_interval = TimeInterval(start=ef.valid_from, end=ef.valid_to)

            if cand_interval.overlaps(ef_interval) and is_mutually_exclusive:
                # Analyze whether this is a temporal evolution or direct contradiction
                if cand_vf > ef.valid_from:
                    # Sequential change over time: e.g. Left Company X to join Company Y
                    reports.append(
                        ConflictReport(
                            has_conflict=True,
                            classification=ConflictClassification.TEMPORAL_EVOLUTION,
                            existing_fact_id=ef.id,
                            candidate_fact_subject=subject_id,
                            candidate_fact_predicate=predicate,
                            reason=(
                                f"Subject {subject_id} transitioned '{predicate}' from "
                                f"{ef.object_id or ef.object_literal} to {object_id or object_literal} at {cand_vf}"
                            ),
                            suggested_action="supersede_and_close_old_interval",
                            metadata={
                                "old_valid_from": ef.valid_from.isoformat(),
                                "new_valid_from": cand_vf.isoformat(),
                                "existing_fact_id": ef.id,
                            },
                        )
                    )
                else:
                    # Direct simultaneous contradiction
                    reports.append(
                        ConflictReport(
                            has_conflict=True,
                            classification=ConflictClassification.DIRECT_CONTRADICTION,
                            existing_fact_id=ef.id,
                            candidate_fact_subject=subject_id,
                            candidate_fact_predicate=predicate,
                            reason=(
                                f"Direct contradiction: candidate claims '{predicate}' is "
                                f"'{object_id or object_literal}' during {cand_interval}, but existing "
                                f"fact {ef.id} claims '{ef.object_id or ef.object_literal}' during {ef_interval}"
                            ),
                            suggested_action="apply_resolution_policy",
                            metadata={
                                "existing_confidence": ef.confidence,
                                "existing_fact_id": ef.id,
                            },
                        )
                    )

        return reports
