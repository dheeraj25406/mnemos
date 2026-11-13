from datetime import datetime, timezone
from typing import Literal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.core.logging import logger
from mnemos.graph.traversal import GraphEdge, GraphNode, PathResult, SubgraphResult
from mnemos.temporal.intervals import ensure_utc


class TemporalGraphEngine:
    """
    High-performance temporal graph engine leveraging PostgreSQL Recursive CTEs
    for multi-hop traversal, bounded depth, cycle prevention, and bitemporal filtering.
    """

    @classmethod
    async def traverse_subgraph(
        cls,
        session: AsyncSession,
        tenant_id: str,
        seed_entity_id: str,
        max_depth: int = 2,
        valid_at: datetime | None = None,
        recorded_at: datetime | None = None,
        direction: Literal["out", "in", "both"] = "both",
        relation_types: list[str] | None = None,
        max_nodes: int = 100,
    ) -> SubgraphResult:
        """
        Extracts the temporal subgraph reachable from seed_entity_id within max_depth hops.
        Applies bitemporal filters to ensure only temporally valid edges are traversed.
        """
        now = datetime.now(timezone.utc)
        vt = ensure_utc(valid_at) if valid_at else now
        tt = ensure_utc(recorded_at) if recorded_at else now

        # Build recursive SQL CTE with cycle prevention
        query_sql = """
        WITH RECURSIVE graph_traversal AS (
            -- Base case: seed entity
            SELECT 
                e.id AS node_id,
                e.name AS node_name,
                e.entity_type AS node_type,
                e.description AS node_desc,
                0 AS depth,
                ARRAY[e.id]::VARCHAR[] AS path,
                NULL::VARCHAR AS edge_id,
                NULL::VARCHAR AS edge_src,
                NULL::VARCHAR AS edge_tgt,
                NULL::VARCHAR AS edge_rel,
                1.0::FLOAT AS edge_weight,
                NULL::TIMESTAMPTZ AS edge_vf,
                NULL::TIMESTAMPTZ AS edge_vt,
                NULL::TIMESTAMPTZ AS edge_rf,
                NULL::TIMESTAMPTZ AS edge_rt,
                NULL::VARCHAR AS fact_id,
                NULL::VARCHAR AS source_memory_id
            FROM entities e
            WHERE e.id = :seed_id AND e.tenant_id = :tenant_id AND e.is_active = true

            UNION

            -- Recursive step: traverse adjacent edges
            SELECT
                next_ent.id AS node_id,
                next_ent.name AS node_name,
                next_ent.entity_type AS node_type,
                next_ent.description AS node_desc,
                gt.depth + 1 AS depth,
                (gt.path || next_ent.id)::VARCHAR[] AS path,
                r.id AS edge_id,
                r.source_entity_id AS edge_src,
                r.target_entity_id AS edge_tgt,
                r.relation_type AS edge_rel,
                r.weight AS edge_weight,
                r.valid_from AS edge_vf,
                r.valid_to AS edge_vt,
                r.recorded_from AS edge_rf,
                r.recorded_to AS edge_rt,
                r.fact_id AS fact_id,
                r.source_memory_id AS source_memory_id
            FROM graph_traversal gt
            JOIN relationships r ON (
                r.tenant_id = :tenant_id 
                AND r.is_active = true
                AND (
                    (:direction = 'out' AND r.source_entity_id = gt.node_id)
                    OR (:direction = 'in' AND r.target_entity_id = gt.node_id)
                    OR (:direction = 'both' AND (r.source_entity_id = gt.node_id OR r.target_entity_id = gt.node_id))
                )
                AND r.valid_from <= :vt AND r.valid_to > :vt
                AND r.recorded_from <= :tt AND r.recorded_to > :tt
            )
            JOIN entities next_ent ON (
                next_ent.id = (CASE WHEN r.source_entity_id = gt.node_id THEN r.target_entity_id ELSE r.source_entity_id END)
                AND next_ent.tenant_id = :tenant_id
                AND next_ent.is_active = true
            )
            WHERE gt.depth < :max_depth
              AND NOT next_ent.id = ANY(gt.path) -- Cycle prevention
        )
        SELECT * FROM graph_traversal LIMIT :max_nodes;
        """

        result = await session.execute(
            text(query_sql),
            {
                "tenant_id": tenant_id,
                "seed_id": seed_entity_id,
                "direction": direction,
                "vt": vt,
                "tt": tt,
                "max_depth": max_depth,
                "max_nodes": max_nodes,
            },
        )
        rows = result.mappings().all()

        nodes_dict: dict[str, GraphNode] = {}
        edges_dict: dict[str, GraphEdge] = {}
        max_depth_seen = 0

        for r in rows:
            nid = r["node_id"]
            depth = r["depth"]
            if depth > max_depth_seen:
                max_depth_seen = depth

            if nid not in nodes_dict:
                nodes_dict[nid] = GraphNode(
                    id=nid,
                    name=r["node_name"],
                    entity_type=r["node_type"],
                    description=r["node_desc"],
                    depth=depth,
                )

            edge_id = r["edge_id"]
            if edge_id and edge_id not in edges_dict:
                edges_dict[edge_id] = GraphEdge(
                    id=edge_id,
                    source_entity_id=r["edge_src"],
                    target_entity_id=r["edge_tgt"],
                    relation_type=r["edge_rel"],
                    weight=r["edge_weight"],
                    valid_from=r["edge_vf"],
                    valid_to=r["edge_vt"],
                    recorded_from=r["edge_rf"],
                    recorded_to=r["edge_rt"],
                    fact_id=r["fact_id"],
                    source_memory_id=r["source_memory_id"],
                    depth=depth,
                )

        nodes_list = list(nodes_dict.values())
        edges_list = list(edges_dict.values())

        return SubgraphResult(
            seed_entity_id=seed_entity_id,
            nodes=nodes_list,
            edges=edges_list,
            max_depth_reached=max_depth_seen,
            total_nodes=len(nodes_list),
            total_edges=len(edges_list),
        )

    @classmethod
    async def find_path(
        cls,
        session: AsyncSession,
        tenant_id: str,
        start_entity_id: str,
        end_entity_id: str,
        max_depth: int = 4,
        valid_at: datetime | None = None,
        recorded_at: datetime | None = None,
    ) -> PathResult:
        """Finds the shortest temporal connection path between two entities."""
        if start_entity_id == end_entity_id:
            start_node = await session.execute(
                text("SELECT id, name, entity_type FROM entities WHERE id = :id AND tenant_id = :tenant_id"),
                {"id": start_entity_id, "tenant_id": tenant_id},
            )
            row = start_node.mappings().first()
            if row:
                node = GraphNode(id=row["id"], name=row["name"], entity_type=row["entity_type"], depth=0)
                return PathResult(
                    start_entity_id=start_entity_id,
                    end_entity_id=end_entity_id,
                    nodes=[node],
                    edges=[],
                    length_hops=0,
                    exists=True,
                )

        now = datetime.now(timezone.utc)
        vt = ensure_utc(valid_at) if valid_at else now
        tt = ensure_utc(recorded_at) if recorded_at else now

        path_sql = """
        WITH RECURSIVE path_finder AS (
            SELECT
                e.id AS current_id,
                ARRAY[e.id]::VARCHAR[] AS path,
                ARRAY[]::VARCHAR[] AS edge_path,
                0 AS depth
            FROM entities e
            WHERE e.id = :start_id AND e.tenant_id = :tenant_id AND e.is_active = true

            UNION ALL

            SELECT
                CASE WHEN r.source_entity_id = pf.current_id THEN r.target_entity_id ELSE r.source_entity_id END AS current_id,
                (pf.path || (CASE WHEN r.source_entity_id = pf.current_id THEN r.target_entity_id ELSE r.source_entity_id END))::VARCHAR[] AS path,
                (pf.edge_path || r.id)::VARCHAR[] AS edge_path,
                pf.depth + 1 AS depth
            FROM path_finder pf
            JOIN relationships r ON (
                r.tenant_id = :tenant_id
                AND r.is_active = true
                AND (r.source_entity_id = pf.current_id OR r.target_entity_id = pf.current_id)
                AND r.valid_from <= :vt AND r.valid_to > :vt
                AND r.recorded_from <= :tt AND r.recorded_to > :tt
            )
            WHERE pf.depth < :max_depth
              AND NOT (CASE WHEN r.source_entity_id = pf.current_id THEN r.target_entity_id ELSE r.source_entity_id END) = ANY(pf.path)
        )
        SELECT path, edge_path, depth FROM path_finder
        WHERE current_id = :end_id
        ORDER BY depth ASC
        LIMIT 1;
        """

        result = await session.execute(
            text(path_sql),
            {
                "tenant_id": tenant_id,
                "start_id": start_entity_id,
                "end_id": end_entity_id,
                "max_depth": max_depth,
                "vt": vt,
                "tt": tt,
            },
        )
        row = result.mappings().first()

        if not row:
            return PathResult(
                start_entity_id=start_entity_id,
                end_entity_id=end_entity_id,
                nodes=[],
                edges=[],
                length_hops=0,
                exists=False,
            )

        node_ids = row["path"]
        edge_ids = row["edge_path"]

        # Fetch nodes
        nodes_res = await session.execute(
            text("SELECT id, name, entity_type, description FROM entities WHERE id = ANY(:ids)"),
            {"ids": node_ids},
        )
        nodes_by_id = {
            nr["id"]: GraphNode(
                id=nr["id"],
                name=nr["name"],
                entity_type=nr["entity_type"],
                description=nr["description"],
            )
            for nr in nodes_res.mappings().all()
        }
        ordered_nodes = [nodes_by_id[nid] for nid in node_ids if nid in nodes_by_id]

        # Fetch edges
        edges_res = await session.execute(
            text("SELECT id, source_entity_id, target_entity_id, relation_type, weight, valid_from, valid_to, recorded_from, recorded_to, fact_id, source_memory_id FROM relationships WHERE id = ANY(:ids)"),
            {"ids": edge_ids},
        )
        edges_by_id = {
            er["id"]: GraphEdge(
                id=er["id"],
                source_entity_id=er["source_entity_id"],
                target_entity_id=er["target_entity_id"],
                relation_type=er["relation_type"],
                weight=er["weight"],
                valid_from=er["valid_from"],
                valid_to=er["valid_to"],
                recorded_from=er["recorded_from"],
                recorded_to=er["recorded_to"],
                fact_id=er["fact_id"],
                source_memory_id=er["source_memory_id"],
            )
            for er in edges_res.mappings().all()
        }
        ordered_edges = [edges_by_id[eid] for eid in edge_ids if eid in edges_by_id]

        return PathResult(
            start_entity_id=start_entity_id,
            end_entity_id=end_entity_id,
            nodes=ordered_nodes,
            edges=ordered_edges,
            length_hops=row["depth"],
            exists=True,
        )
