from datetime import datetime, timezone
from typing import Any, TypeVar
from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.db.models import Fact, Relationship, Memory, SENTINEL_MAX_TIME
from mnemos.temporal.intervals import ensure_utc

T = TypeVar("T", Fact, Relationship, Memory)


def apply_bitemporal_filters(
    query: Select[tuple[T]],
    model_cls: type[T],
    valid_at: datetime | None = None,
    recorded_at: datetime | None = None,
) -> Select[tuple[T]]:
    """
    Applies half-open bitemporal interval filters:
    valid_from <= valid_at < valid_to
    recorded_from <= recorded_at < recorded_to
    """
    conditions = []
    if valid_at is not None:
        vt = ensure_utc(valid_at)
        conditions.append(
            and_(
                model_cls.valid_from <= vt,
                model_cls.valid_to > vt,
            )
        )

    if recorded_at is not None:
        tt = ensure_utc(recorded_at)
        conditions.append(
            and_(
                model_cls.recorded_from <= tt,
                model_cls.recorded_to > tt,
            )
        )
    else:
        # Default to current active knowledge in transaction time
        now = datetime.now(timezone.utc)
        conditions.append(
            and_(
                model_cls.recorded_from <= now,
                model_cls.recorded_to > now,
            )
        )

    return query.where(and_(*conditions))


class BitemporalManager:
    """Manages transaction-safe bitemporal updates, retractions, and interval closures."""

    @staticmethod
    async def supersede_fact(
        session: AsyncSession,
        old_fact: Fact,
        new_fact: Fact,
        effective_valid_time: datetime,
    ) -> None:
        """
        Non-destructively supersedes old_fact with new_fact:
        1. Closes old_fact.valid_to at effective_valid_time.
        2. Closes old_fact.recorded_to at transaction current time.
        3. Links old_fact.superseded_by_id = new_fact.id.
        4. Sets new_fact.valid_from = effective_valid_time.
        """
        now = datetime.now(timezone.utc)
        vt = ensure_utc(effective_valid_time)

        # 1. Close transaction time for current version of old_fact
        old_fact.valid_to = vt
        old_fact.superseded_by_id = new_fact.id
        old_fact.recorded_to = now

        # Add new_fact
        new_fact.valid_from = vt
        new_fact.valid_to = SENTINEL_MAX_TIME
        new_fact.recorded_from = now
        new_fact.recorded_to = SENTINEL_MAX_TIME

        session.add(old_fact)
        session.add(new_fact)
        await session.flush()

    @staticmethod
    async def retract_fact(
        session: AsyncSession,
        fact: Fact,
        retraction_time: datetime | None = None,
    ) -> None:
        """
        Logically retracts a fact without deleting historical records:
        Sets is_retracted = True, closes recorded_to at transaction time.
        """
        now = datetime.now(timezone.utc)
        fact.is_retracted = True
        fact.recorded_to = now
        session.add(fact)
        await session.flush()

    @staticmethod
    async def get_facts_at(
        session: AsyncSession,
        tenant_id: str,
        subject_id: str | None = None,
        predicate: str | None = None,
        valid_at: datetime | None = None,
        recorded_at: datetime | None = None,
    ) -> list[Fact]:
        """
        Retrieves facts matching the specified bitemporal coordinates:
        - valid_at: Historical Truth query (what was true at that time)
        - recorded_at: Historical Knowledge query (what Mnemos knew at that time)
        """
        query = select(Fact).where(Fact.tenant_id == tenant_id)
        if subject_id:
            query = query.where(Fact.subject_id == subject_id)
        if predicate:
            query = query.where(Fact.predicate == predicate)

        query = apply_bitemporal_filters(
            query, Fact, valid_at=valid_at, recorded_at=recorded_at
        )
        result = await session.execute(query)
        return list(result.scalars().all())
