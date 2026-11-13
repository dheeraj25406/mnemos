from datetime import datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.db.models import Relationship, SENTINEL_MAX_TIME
from mnemos.graph.engine import TemporalGraphEngine
from mnemos.ingestion.resolver import EntityResolver


@pytest.mark.asyncio
async def test_graph_multihop_traversal_and_cycles(db_session: AsyncSession):
    tenant_id = "tenant_test"

    # Entities: Person A -> Company X -> Project Apollo -> Person B
    # And cycle: Person B -> Person A
    ent_a = await EntityResolver.resolve_or_create(db_session, tenant_id, "Person A", "person")
    ent_x = await EntityResolver.resolve_or_create(db_session, tenant_id, "Company X", "organization")
    ent_apollo = await EntityResolver.resolve_or_create(db_session, tenant_id, "Project Apollo", "project")
    ent_b = await EntityResolver.resolve_or_create(db_session, tenant_id, "Person B", "person")

    now = datetime(2024, 5, 1, tzinfo=timezone.utc)

    # Relationship 1: Person A works_at Company X (2024-01-01 to infinity)
    r1 = Relationship(
        id="rel_test_1",
        tenant_id=tenant_id,
        source_entity_id=ent_a.id,
        target_entity_id=ent_x.id,
        relation_type="works_at",
        valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        valid_to=SENTINEL_MAX_TIME,
        recorded_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        recorded_to=SENTINEL_MAX_TIME,
        is_active=True,
    )
    # Relationship 2: Company X owns Project Apollo (2024-01-01 to infinity)
    r2 = Relationship(
        id="rel_test_2",
        tenant_id=tenant_id,
        source_entity_id=ent_x.id,
        target_entity_id=ent_apollo.id,
        relation_type="owns",
        valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        valid_to=SENTINEL_MAX_TIME,
        recorded_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        recorded_to=SENTINEL_MAX_TIME,
        is_active=True,
    )
    # Relationship 3: Person B leads Project Apollo (2024-01-01 to infinity)
    r3 = Relationship(
        id="rel_test_3",
        tenant_id=tenant_id,
        source_entity_id=ent_b.id,
        target_entity_id=ent_apollo.id,
        relation_type="leads",
        valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        valid_to=SENTINEL_MAX_TIME,
        recorded_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        recorded_to=SENTINEL_MAX_TIME,
        is_active=True,
    )
    # Cycle Edge: Person B collaborates_with Person A
    r4 = Relationship(
        id="rel_test_4",
        tenant_id=tenant_id,
        source_entity_id=ent_b.id,
        target_entity_id=ent_a.id,
        relation_type="collaborates_with",
        valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        valid_to=SENTINEL_MAX_TIME,
        recorded_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        recorded_to=SENTINEL_MAX_TIME,
        is_active=True,
    )
    # Temporal Old Edge: Person A worked at Company Old in 2022 only!
    ent_old = await EntityResolver.resolve_or_create(db_session, tenant_id, "Company Old", "organization")
    r_old = Relationship(
        id="rel_test_old",
        tenant_id=tenant_id,
        source_entity_id=ent_a.id,
        target_entity_id=ent_old.id,
        relation_type="works_at",
        valid_from=datetime(2022, 1, 1, tzinfo=timezone.utc),
        valid_to=datetime(2022, 12, 31, tzinfo=timezone.utc),  # Ended in 2022
        recorded_from=datetime(2022, 1, 1, tzinfo=timezone.utc),
        recorded_to=SENTINEL_MAX_TIME,
        is_active=True,
    )

    db_session.add_all([r1, r2, r3, r4, r_old])
    await db_session.flush()

    # 1-hop traversal from Person A at valid_at=2024-05-01
    res_1hop = await TemporalGraphEngine.traverse_subgraph(
        session=db_session,
        tenant_id=tenant_id,
        seed_entity_id=ent_a.id,
        max_depth=1,
        valid_at=now,
    )
    node_ids_1hop = {n.id for n in res_1hop.nodes}
    assert ent_a.id in node_ids_1hop
    assert ent_x.id in node_ids_1hop
    # Company Old should NOT appear in 2024 query because it expired in 2022!
    assert ent_old.id not in node_ids_1hop

    # Historical traversal from Person A at valid_at=2022-06-01
    res_2022 = await TemporalGraphEngine.traverse_subgraph(
        session=db_session,
        tenant_id=tenant_id,
        seed_entity_id=ent_a.id,
        max_depth=1,
        valid_at=datetime(2022, 6, 1, tzinfo=timezone.utc),
    )
    node_ids_2022 = {n.id for n in res_2022.nodes}
    assert ent_old.id in node_ids_2022
    assert ent_x.id not in node_ids_2022  # Person A didn't work at Company X in 2022

    # Multi-hop 3-hop traversal with cycle handling (should not loop indefinitely)
    res_3hop = await TemporalGraphEngine.traverse_subgraph(
        session=db_session,
        tenant_id=tenant_id,
        seed_entity_id=ent_a.id,
        max_depth=3,
        valid_at=now,
    )
    node_ids_3hop = {n.id for n in res_3hop.nodes}
    assert ent_a.id in node_ids_3hop
    assert ent_x.id in node_ids_3hop
    assert ent_apollo.id in node_ids_3hop
    assert ent_b.id in node_ids_3hop

    # Path finding: shortest path from Person A to Project Apollo
    path_result = await TemporalGraphEngine.find_path(
        session=db_session,
        tenant_id=tenant_id,
        start_entity_id=ent_a.id,
        end_entity_id=ent_apollo.id,
        max_depth=3,
        valid_at=now,
    )
    assert path_result.exists is True
    assert path_result.length_hops == 2
    assert len(path_result.nodes) == 3
    assert path_result.nodes[0].id == ent_a.id
    assert path_result.nodes[1].id in {ent_x.id, ent_b.id}
    assert path_result.nodes[2].id == ent_apollo.id
