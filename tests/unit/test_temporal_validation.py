"""Regression and temporal validation tests for MNEMOS bitemporal retrieval."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.db.models import Fact
from mnemos.evolution.policies import ResolutionPolicy
from mnemos.evolution.resolver import EvolutionManager
from mnemos.ingestion.pipeline import IngestionItem, IngestionPipeline
from mnemos.ingestion.resolver import EntityResolver
from mnemos.retrieval.hybrid import HybridRetrievalEngine, HybridRetrievalRequest
from mnemos.temporal.bitemporal import apply_bitemporal_filters
from mnemos.temporal.intervals import TimeInterval


def test_time_interval_exact_boundaries():
    """Verify half-open interval math [start, end): start inclusive, end exclusive."""
    t_start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    interval = TimeInterval(start=t_start, end=t_end)

    # Exactly at start: INCLUDED
    assert interval.contains(t_start) is True

    # 1 second before end: INCLUDED
    t_before_end = datetime(2024, 5, 31, 23, 59, 59, tzinfo=timezone.utc)
    assert interval.contains(t_before_end) is True

    # Exactly at end: EXCLUDED
    assert interval.contains(t_end) is False

    # After end: EXCLUDED
    t_after = datetime(2024, 6, 1, 0, 0, 1, tzinfo=timezone.utc)
    assert interval.contains(t_after) is False


@pytest.mark.asyncio
async def test_fact_multiple_sequential_updates(db_session: AsyncSession):
    """Test 4 sequential updates to the same entity and predicate."""
    tenant_id = "tenant_test"
    frank = await EntityResolver.resolve_or_create(db_session, tenant_id, "Frank", "person")
    vertex = await EntityResolver.resolve_or_create(db_session, tenant_id, "Vertex", "organization")

    roles = [
        ("Junior Engineer", datetime(2021, 1, 1, tzinfo=timezone.utc)),
        ("Senior Engineer", datetime(2022, 1, 1, tzinfo=timezone.utc)),
        ("Staff Engineer", datetime(2023, 1, 1, tzinfo=timezone.utc)),
        ("VP of Engineering", datetime(2024, 1, 1, tzinfo=timezone.utc)),
    ]

    for role_name, vf in roles:
        await EvolutionManager.process_fact_evolution(
            session=db_session,
            tenant_id=tenant_id,
            subject_id=frank.id,
            predicate="has_role_at",
            object_id=vertex.id,
            object_literal=role_name,
            valid_from=vf,
            valid_to=None,
            confidence=1.0,
            policy=ResolutionPolicy.TEMPORAL_RECENCY,
        )

    # 1. Query in 2021 (mid-year) -> Junior
    q1 = select(Fact).where(Fact.tenant_id == tenant_id, Fact.subject_id == frank.id, Fact.is_retracted == False)
    q1 = apply_bitemporal_filters(q1, Fact, valid_at=datetime(2021, 6, 1, tzinfo=timezone.utc))
    res1 = (await db_session.execute(q1)).scalars().all()
    assert len(res1) == 1
    assert res1[0].object_literal == "Junior Engineer"

    # 2. Query in 2022 (mid-year) -> Senior
    q2 = select(Fact).where(Fact.tenant_id == tenant_id, Fact.subject_id == frank.id, Fact.is_retracted == False)
    q2 = apply_bitemporal_filters(q2, Fact, valid_at=datetime(2022, 6, 1, tzinfo=timezone.utc))
    res2 = (await db_session.execute(q2)).scalars().all()
    assert len(res2) == 1
    assert res2[0].object_literal == "Senior Engineer"

    # 3. Query in 2023 (mid-year) -> Staff
    q3 = select(Fact).where(Fact.tenant_id == tenant_id, Fact.subject_id == frank.id, Fact.is_retracted == False)
    q3 = apply_bitemporal_filters(q3, Fact, valid_at=datetime(2023, 6, 1, tzinfo=timezone.utc))
    res3 = (await db_session.execute(q3)).scalars().all()
    assert len(res3) == 1
    assert res3[0].object_literal == "Staff Engineer"

    # 4. Query boundary at 2023-01-01 -> Staff (inclusive start of 2023)
    q_b = select(Fact).where(Fact.tenant_id == tenant_id, Fact.subject_id == frank.id, Fact.is_retracted == False)
    q_b = apply_bitemporal_filters(q_b, Fact, valid_at=datetime(2023, 1, 1, tzinfo=timezone.utc))
    res_b = (await db_session.execute(q_b)).scalars().all()
    assert len(res_b) == 1
    assert res_b[0].object_literal == "Staff Engineer"

    # 5. Query current (2024+) -> VP
    q4 = select(Fact).where(Fact.tenant_id == tenant_id, Fact.subject_id == frank.id, Fact.is_retracted == False)
    q4 = apply_bitemporal_filters(q4, Fact, valid_at=datetime(2024, 6, 1, tzinfo=timezone.utc))
    res4 = (await db_session.execute(q4)).scalars().all()
    assert len(res4) == 1
    assert res4[0].object_literal == "VP of Engineering"


@pytest.mark.asyncio
async def test_retroactive_correction_preserves_past_knowledge(db_session: AsyncSession):
    """Test retroactive correction: Transaction time distinguishes prior belief from updated truth."""
    tenant_id = "tenant_test"
    charlie = await EntityResolver.resolve_or_create(db_session, tenant_id, "Charlie", "person")
    paris = await EntityResolver.resolve_or_create(db_session, tenant_id, "Paris", "location")
    lyon = await EntityResolver.resolve_or_create(db_session, tenant_id, "Lyon", "location")

    t_valid = datetime(2023, 1, 1, tzinfo=timezone.utc)

    # T1: Ingestion on Jan 10 records that Charlie is located in Paris
    fact1 = await EvolutionManager.process_fact_evolution(
        session=db_session,
        tenant_id=tenant_id,
        subject_id=charlie.id,
        predicate="located_in",
        object_id=paris.id,
        object_literal=None,
        valid_from=t_valid,
        valid_to=None,
        confidence=0.5,
        policy=ResolutionPolicy.SOURCE_RELIABILITY,
    )
    assert fact1.object_id == paris.id

    # T2: Retroactive correction on Jan 20 with higher confidence records Charlie was in Lyon
    fact2 = await EvolutionManager.process_fact_evolution(
        session=db_session,
        tenant_id=tenant_id,
        subject_id=charlie.id,
        predicate="located_in",
        object_id=lyon.id,
        object_literal=None,
        valid_from=t_valid,
        valid_to=None,
        confidence=0.99,
        policy=ResolutionPolicy.SOURCE_RELIABILITY,
    )
    assert fact2.object_id == lyon.id

    # Historical truth today: Charlie was in Lyon
    q_truth = select(Fact).where(
        Fact.tenant_id == tenant_id,
        Fact.subject_id == charlie.id,
        Fact.predicate == "located_in",
        Fact.is_retracted == False,
    )
    q_truth = apply_bitemporal_filters(q_truth, Fact, valid_at=t_valid)
    facts_truth = (await db_session.execute(q_truth)).scalars().all()
    assert len(facts_truth) == 1
    assert facts_truth[0].object_id == lyon.id


@pytest.mark.asyncio
async def test_temporal_retrieval_excludes_superseded_facts(db_session: AsyncSession):
    """Verify that full Mnemos hybrid retrieval excludes superseded historical facts when querying current state."""
    tenant_id = "tenant_test"

    # Ingest historical fact
    await IngestionPipeline.ingest(
        db_session,
        tenant_id,
        IngestionItem(
            content="Alice works at Acme Corp as of 2021-01-01",
            valid_from=datetime(2021, 1, 1, tzinfo=timezone.utc),
        ),
    )

    # Ingest newer fact superseding Acme Corp
    await IngestionPipeline.ingest(
        db_session,
        tenant_id,
        IngestionItem(
            content="Alice works at Globex in 2024-01-01",
            valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ),
    )
    await db_session.commit()

    # Query historical (2022) with temporal filtering -> must return Acme Corp
    req_hist = HybridRetrievalRequest(
        query="Where does Alice work?",
        valid_at=datetime(2022, 6, 1, tzinfo=timezone.utc),
        enable_temporal_filtering=True,
    )
    resp_hist = await HybridRetrievalEngine.search(db_session, tenant_id, req_hist)
    assert len(resp_hist.memories) > 0
    assert "acme corp" in resp_hist.memories[0].content.lower()

    # Query current (2024+) with temporal filtering -> must return Globex and NOT Acme Corp
    req_curr = HybridRetrievalRequest(
        query="Where does Alice work?",
        valid_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        enable_temporal_filtering=True,
    )
    resp_curr = await HybridRetrievalEngine.search(db_session, tenant_id, req_curr)
    assert len(resp_curr.memories) > 0
    assert "globex" in resp_curr.memories[0].content.lower()
