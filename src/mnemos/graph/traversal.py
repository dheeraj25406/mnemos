from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    name: str
    entity_type: str = "concept"
    description: str | None = None
    depth: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source_entity_id: str
    target_entity_id: str
    relation_type: str
    weight: float = 1.0
    valid_from: datetime
    valid_to: datetime
    recorded_from: datetime
    recorded_to: datetime
    fact_id: str | None = None
    source_memory_id: str | None = None
    depth: int = 1


class SubgraphResult(BaseModel):
    seed_entity_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    max_depth_reached: int
    total_nodes: int
    total_edges: int


class PathResult(BaseModel):
    start_entity_id: str
    end_entity_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    length_hops: int
    exists: bool
