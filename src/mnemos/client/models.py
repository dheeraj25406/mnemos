from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class MemoryItem(BaseModel):
    id: str
    content: str
    memory_type: str = "observation"
    source: str = "agent"
    confidence: float = 1.0
    importance: float = 0.5
    valid_from: str | None = None
    valid_to: str | None = None
    recorded_from: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    query: str
    total_found: int
    memories: list[dict[str, Any]]
    evidence_entities: list[str] = Field(default_factory=list)
    temporal_anchor: str | None = None


class TimelineDiff(BaseModel):
    subject_name: str
    time_start: str
    time_end: str
    changes: list[dict[str, Any]]
    unchanged_facts: list[str]
