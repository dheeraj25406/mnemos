from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.db.models import Fact, Entity, SENTINEL_MAX_TIME
from mnemos.temporal.bitemporal import BitemporalManager, apply_bitemporal_filters
from mnemos.ingestion.resolver import EntityResolver


@pytest.mark.asyncio
async def test_bitemporal_historical_truth_and_knowledge(db_session: AsyncSession):
    tenant_id = "tenant_test"

    # Create entities
    alice = await EntityResolver.resolve_or_create(db_session, tenant_id, "Alice", "person")
    corp_x = await EntityResolver.resolve_or_create(db_session, tenant_id, "Company X", "organization")
    corp_y = await EntityResolver.resolve_or_create(db_session, tenant_id, "Company Y", "organization")

    # Timeline:
    # 1. On Jan 15 (TT), Mnemos learns that Alice worked at Company X starting Jan 10 (VT)
    fact1 = Fact(
        id="fact_bitemp_1",
        tenant_id=tenant_id,
        subject_id=alice.id,
        predicate="works_at",
        object_id=corp_x.id,
        valid_from=datetime(2024, 1, 10, tzinfo=timezone.utc),
        valid_to=SENTINEL_MAX_TIME,
        recorded_from=datetime(2024, 1, 15, tzinfo=timezone.utc),
        recorded_to=SENTINEL_MAX_TIME,
    )
    db_session.add(fact1)
    await db_session.flush()

    # Query 1: As of Jan 20 (TT), where did Alice work on Jan 12 (VT)?
    # Answer: Company X
    query1 = select(Fact).where(Fact.tenant_id == tenant_id, Fact.subject_id == alice.id)
    query1 = apply_bitemporal_filters(
        query1,
        Fact,
        valid_at=datetime(2024, 1, 12, tzinfo=timezone.utc),
        recorded_at=datetime(2024, 1, 20, tzinfo=timezone.utc),
    )
    results1 = (await db_session.execute(query1)).scalars().all()
    assert len(results1) == 1
    assert results1[0].object_id == corp_x.id

    # Query 2: As of Jan 14 (TT), what did Mnemos know about Alice on Jan 12 (VT)?
    # Answer: Nothing! Because fact1 was not recorded until Jan 15.
    query2 = select(Fact).where(Fact.tenant_id == tenant_id, Fact.subject_id == alice.id)
    query2 = apply_bitemporal_filters(
        query2,
        Fact,
        valid_at=datetime(2024, 1, 12, tzinfo=timezone.utc),
        recorded_at=datetime(2024, 1, 14, tzinfo=timezone.utc),
    )
    results2 = (await db_session.execute(query2)).scalars().all()
    assert len(results2) == 0

    # 2. On Jun 20 (TT), Mnemos learns that Alice changed jobs to Company Y on Jun 15 (VT).
    # We supersede fact1 with fact2.
    fact2 = Fact(
        id="fact_bitemp_2",
        tenant_id=tenant_id,
        subject_id=alice.id,
        predicate="works_at",
        object_id=corp_y.id,
        valid_from=datetime(2024, 6, 15, tzinfo=timezone.utc),
        valid_to=SENTINEL_MAX_TIME,
        recorded_from=datetime(2024, 6, 20, tzinfo=timezone.utc),
        recorded_to=SENTINEL_MAX_TIME,
    )
    db_session.add(fact2)
    await db_session.flush()

    # Update fact1 recorded_to and valid_to
    fact1.valid_to = datetime(2024, 6, 15, tzinfo=timezone.utc)
    fact1.recorded_to = datetime(2024, 6, 20, tzinfo=timezone.utc)
    fact1.superseded_by_id = fact2.id

    # The active historical version of fact1 as of Jun 20
    fact1_closed = Fact(
        id="fact_bitemp_1_closed",
        tenant_id=tenant_id,
        subject_id=alice.id,
        predicate="works_at",
        object_id=corp_x.id,
        valid_from=datetime(2024, 1, 10, tzinfo=timezone.utc),
        valid_to=datetime(2024, 6, 15, tzinfo=timezone.utc),
        recorded_from=datetime(2024, 6, 20, tzinfo=timezone.utc),
        recorded_to=SENTINEL_MAX_TIME,
        superseded_by_id=fact2.id,
    )
    db_session.add(fact1_closed)
    await db_session.flush()

    # Query 3: Where did Alice work in March 2024 (Historical Truth query as of today)?
    # Answer: Company X
    march_query = select(Fact).where(Fact.tenant_id == tenant_id, Fact.subject_id == alice.id)
    march_query = apply_bitemporal_filters(
        march_query,
        Fact,
        valid_at=datetime(2024, 3, 15, tzinfo=timezone.utc),
        recorded_at=datetime(2024, 7, 1, tzinfo=timezone.utc),
    )
    march_results = (await db_session.execute(march_query)).scalars().all()
    assert len(march_results) == 1
    assert march_results[0].object_id == corp_x.id

    # Query 4: Where does Alice work in July 2024 (Current truth)?
    # Answer: Company Y
    july_query = select(Fact).where(Fact.tenant_id == tenant_id, Fact.subject_id == alice.id)
    july_query = apply_bitemporal_filters(
        july_query,
        Fact,
        valid_at=datetime(2024, 7, 1, tzinfo=timezone.utc),
        recorded_at=datetime(2024, 7, 1, tzinfo=timezone.utc),
    )
    july_results = (await db_session.execute(july_query)).scalars().all()
    assert len(july_results) == 1
    assert july_results[0].object_id == corp_y.id
