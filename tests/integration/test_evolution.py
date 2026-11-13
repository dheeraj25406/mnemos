from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.db.models import Fact
from mnemos.evolution.policies import ResolutionPolicy
from mnemos.evolution.resolver import EvolutionManager
from mnemos.ingestion.resolver import EntityResolver
from mnemos.temporal.bitemporal import apply_bitemporal_filters


@pytest.mark.asyncio
async def test_temporal_evolution_job_change(db_session: AsyncSession):
    tenant_id = "tenant_test"

    alice = await EntityResolver.resolve_or_create(db_session, tenant_id, "Alice", "person")
    corp_x = await EntityResolver.resolve_or_create(db_session, tenant_id, "Company X", "organization")
    corp_y = await EntityResolver.resolve_or_create(db_session, tenant_id, "Company Y", "organization")

    # T1: In January 2024, Alice works at Company X
    fact1 = await EvolutionManager.process_fact_evolution(
        session=db_session,
        tenant_id=tenant_id,
        subject_id=alice.id,
        predicate="works_at",
        object_id=corp_x.id,
        object_literal=None,
        valid_from=datetime(2024, 1, 10, tzinfo=timezone.utc),
        valid_to=None,
        confidence=1.0,
    )
    assert fact1.object_id == corp_x.id

    # T2: In June 2024, Alice transitions to Company Y
    fact2 = await EvolutionManager.process_fact_evolution(
        session=db_session,
        tenant_id=tenant_id,
        subject_id=alice.id,
        predicate="works_at",
        object_id=corp_y.id,
        object_literal=None,
        valid_from=datetime(2024, 6, 15, tzinfo=timezone.utc),
        valid_to=None,
        confidence=1.0,
    )
    assert fact2.object_id == corp_y.id

    # Query historical truth in March 2024 -> must be Company X
    q_march = select(Fact).where(Fact.tenant_id == tenant_id, Fact.subject_id == alice.id, Fact.predicate == "works_at")
    q_march = apply_bitemporal_filters(q_march, Fact, valid_at=datetime(2024, 3, 15, tzinfo=timezone.utc))
    facts_march = (await db_session.execute(q_march)).scalars().all()
    assert len(facts_march) == 1
    assert facts_march[0].object_id == corp_x.id

    # Query truth in July 2024 -> must be Company Y
    q_july = select(Fact).where(Fact.tenant_id == tenant_id, Fact.subject_id == alice.id, Fact.predicate == "works_at")
    q_july = apply_bitemporal_filters(q_july, Fact, valid_at=datetime(2024, 7, 1, tzinfo=timezone.utc))
    facts_july = (await db_session.execute(q_july)).scalars().all()
    assert len(facts_july) == 1
    assert facts_july[0].object_id == corp_y.id


@pytest.mark.asyncio
async def test_direct_contradiction_source_reliability(db_session: AsyncSession):
    tenant_id = "tenant_test"

    bob = await EntityResolver.resolve_or_create(db_session, tenant_id, "Bob", "person")
    loc_paris = await EntityResolver.resolve_or_create(db_session, tenant_id, "Paris", "location")
    loc_london = await EntityResolver.resolve_or_create(db_session, tenant_id, "London", "location")

    same_time = datetime(2024, 4, 1, tzinfo=timezone.utc)

    # Low reliability source claims Bob located in Paris (confidence 0.4)
    fact_paris = await EvolutionManager.process_fact_evolution(
        session=db_session,
        tenant_id=tenant_id,
        subject_id=bob.id,
        predicate="located_in",
        object_id=loc_paris.id,
        object_literal=None,
        valid_from=same_time,
        valid_to=None,
        confidence=0.4,
        policy=ResolutionPolicy.SOURCE_RELIABILITY,
    )

    # High reliability verified source claims Bob located in London at same time (confidence 0.95)
    fact_london = await EvolutionManager.process_fact_evolution(
        session=db_session,
        tenant_id=tenant_id,
        subject_id=bob.id,
        predicate="located_in",
        object_id=loc_london.id,
        object_literal=None,
        valid_from=same_time,
        valid_to=None,
        confidence=0.95,
        policy=ResolutionPolicy.SOURCE_RELIABILITY,
    )

    # fact_paris should have been retracted, fact_london should be active
    refreshed_paris = await db_session.get(Fact, fact_paris.id)
    assert refreshed_paris.is_retracted is True
    assert fact_london.is_retracted is False

    # Historical query as of today returns London
    q = select(Fact).where(Fact.tenant_id == tenant_id, Fact.subject_id == bob.id, Fact.is_retracted == False)
    q = apply_bitemporal_filters(q, Fact, valid_at=same_time)
    res = (await db_session.execute(q)).scalars().all()
    assert len(res) == 1
    assert res[0].object_id == loc_london.id


@pytest.mark.asyncio
async def test_direct_contradiction_human_review_policy(db_session: AsyncSession):
    tenant_id = "tenant_test"

    charlie = await EntityResolver.resolve_or_create(db_session, tenant_id, "Charlie", "person")
    status_single = "single"
    status_married = "married"

    t = datetime(2024, 8, 1, tzinfo=timezone.utc)

    # Source 1 claims single
    fact1 = await EvolutionManager.process_fact_evolution(
        session=db_session,
        tenant_id=tenant_id,
        subject_id=charlie.id,
        predicate="marital_status",
        object_id=None,
        object_literal=status_single,
        valid_from=t,
        valid_to=None,
        confidence=0.8,
        policy=ResolutionPolicy.HUMAN_REVIEW,
    )

    # Source 2 claims married at exact same time with HUMAN_REVIEW policy
    fact2 = await EvolutionManager.process_fact_evolution(
        session=db_session,
        tenant_id=tenant_id,
        subject_id=charlie.id,
        predicate="marital_status",
        object_id=None,
        object_literal=status_married,
        valid_from=t,
        valid_to=None,
        confidence=0.8,
        policy=ResolutionPolicy.HUMAN_REVIEW,
    )

    # Both facts preserved, fact2 flagged for review
    assert fact2.metadata_["conflict_status"] == "pending_human_review"
    assert fact2.metadata_["conflicts_with"] == fact1.id
