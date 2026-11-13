from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ResolutionPolicy(str, Enum):
    TEMPORAL_RECENCY = "temporal_recency"        # Latest valid_from supersedes previous
    SOURCE_RELIABILITY = "source_reliability"    # Highest source confidence wins
    CONFIDENCE_WEIGHTED = "confidence_weighted"  # Weighted score (confidence * importance)
    HUMAN_REVIEW = "human_review"                # Flag as conflicted without auto-resolving


class ConflictClassification(str, Enum):
    NO_CONFLICT = "no_conflict"
    TEMPORAL_EVOLUTION = "temporal_evolution"    # Sequential change over time (e.g., job switch)
    DIRECT_CONTRADICTION = "direct_contradiction"# Overlapping valid times claiming opposing states


# Predicates that are inherently single-valued (mutually exclusive) for a given subject at any point in time
MUTUALLY_EXCLUSIVE_PREDICATES = {
    "works_at",
    "employed_at",
    "has_role",
    "located_in",
    "lives_in",
    "resides_in",
    "marital_status",
    "headquarters_in",
    "primary_language",
}


class ConflictReport(BaseModel):
    has_conflict: bool
    classification: ConflictClassification = ConflictClassification.NO_CONFLICT
    existing_fact_id: str | None = None
    candidate_fact_subject: str
    candidate_fact_predicate: str
    reason: str
    suggested_action: str
    metadata: dict[str, Any] = Field(default_factory=dict)
