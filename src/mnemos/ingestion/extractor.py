import re
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field

# Month name mapping for lightweight temporal extraction
MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


class ExtractedEntity(BaseModel):
    name: str
    entity_type: str = "concept"  # person, organization, project, location, concept, tool
    confidence: float = 0.9
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractedFact(BaseModel):
    subject: str
    predicate: str
    object: str
    is_literal: bool = False
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    confidence: float = 0.85
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryExtractor:
    """
    Extracts entities, relationships, and temporal anchors from text.
    Combines rule-based linguistic patterns with structured parsing.
    """

    # Common relation patterns: (regex, predicate, subject_type, object_type, is_literal)
    PATTERNS = [
        (
            re.compile(r"([A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*)\s+(?i:works at|is employed at|joined)\s+([A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*)"),
            "works_at",
            "person",
            "organization",
            False,
        ),
        (
            re.compile(r"([A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*)\s+(?i:left|resigned from|quit)\s+([A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*)"),
            "left_organization",
            "person",
            "organization",
            False,
        ),
        (
            re.compile(r"([A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*)\s+(?i:lives in|moved to|relocated to|located in)\s+([A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*)"),
            "located_in",
            "person",
            "location",
            False,
        ),
        (
            re.compile(r"([A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*)\s+(?i:is the|serves as|works as)\s+(?:a |an )?([a-zA-Z\s]+?)\s+at\s+([A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*)"),
            "has_role_at",
            "person",
            "organization",
            False,
        ),
        (
            re.compile(r"([A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*)\s+(?i:collaborates with|partnered with|works with)\s+([A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*)"),
            "collaborates_with",
            "person",
            "person",
            False,
        ),
        (
            re.compile(r"([A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*)\s+(?i:owns|founded|created|built)\s+([A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*)"),
            "created",
            "person",
            "project",
            False,
        ),
        (
            re.compile(r"([A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*)\s+(?i:uses|adopted)\s+([A-Z][a-zA-Z0-9_]+(?:\s+[A-Z][a-zA-Z0-9_]+)*)"),
            "uses_tool",
            "concept",
            "tool",
            False,
        ),
    ]

    @classmethod
    def extract_temporal_anchor(cls, text: str) -> datetime | None:
        """Extract explicit temporal reference from text if present."""
        # Check for ISO date: YYYY-MM-DD
        iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
        if iso_match:
            try:
                y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
                return datetime(y, m, d, 0, 0, 0, tzinfo=timezone.utc)
            except ValueError:
                pass

        # Check for Month Day, Year (e.g. "January 15, 2024" or "Jan 10 2024")
        mdy_match = re.search(r"\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", text)
        if mdy_match:
            month_str = mdy_match.group(1).lower()
            if month_str in MONTHS:
                try:
                    return datetime(
                        int(mdy_match.group(3)),
                        MONTHS[month_str],
                        int(mdy_match.group(2)),
                        0, 0, 0,
                        tzinfo=timezone.utc,
                    )
                except ValueError:
                    pass

        # Check for "in Month Year" (e.g. "in March 2024")
        my_match = re.search(r"\b(?:in|since|from|as of)\s+([A-Za-z]+)\s+(\d{4})\b", text, re.I)
        if my_match:
            month_str = my_match.group(1).lower()
            if month_str in MONTHS:
                return datetime(
                    int(my_match.group(2)),
                    MONTHS[month_str],
                    1,
                    0, 0, 0,
                    tzinfo=timezone.utc,
                )

        # Check for Year only: e.g. "in 2024"
        year_match = re.search(r"\b(?:in|since|from|as of)\s+(\d{4})\b", text, re.I)
        if year_match:
            return datetime(int(year_match.group(1)), 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        return None

    @classmethod
    def extract(cls, text: str, default_valid_time: datetime | None = None) -> tuple[list[ExtractedEntity], list[ExtractedFact]]:
        """Extract entities and structured facts from text."""
        entities: dict[str, ExtractedEntity] = {}
        facts: list[ExtractedFact] = []

        valid_time = cls.extract_temporal_anchor(text) or default_valid_time

        # Match relation patterns
        for pattern, predicate, subj_type, obj_type, is_lit in cls.PATTERNS:
            for match in pattern.finditer(text):
                groups = match.groups()
                if len(groups) == 2:
                    subj = groups[0].strip()
                    obj = groups[1].strip()
                    if subj and obj:
                        entities[subj.lower()] = ExtractedEntity(name=subj, entity_type=subj_type)
                        if not is_lit:
                            entities[obj.lower()] = ExtractedEntity(name=obj, entity_type=obj_type)
                        facts.append(
                            ExtractedFact(
                                subject=subj,
                                predicate=predicate,
                                object=obj,
                                is_literal=is_lit,
                                valid_from=valid_time,
                            )
                        )
                elif len(groups) == 3:
                    # Role at organization
                    subj = groups[0].strip()
                    role = groups[1].strip()
                    org = groups[2].strip()
                    if subj and org:
                        entities[subj.lower()] = ExtractedEntity(name=subj, entity_type=subj_type)
                        entities[org.lower()] = ExtractedEntity(name=org, entity_type=obj_type)
                        facts.append(
                            ExtractedFact(
                                subject=subj,
                                predicate="works_at",
                                object=org,
                                is_literal=False,
                                valid_from=valid_time,
                            )
                        )
                        facts.append(
                            ExtractedFact(
                                subject=subj,
                                predicate="has_role",
                                object=role,
                                is_literal=True,
                                valid_from=valid_time,
                            )
                        )

        # Fallback: Named Entity recognition heuristic for capitalized terms if none found
        if not entities:
            cap_words = re.findall(r"\b[A-Z][a-zA-Z0-9_]{2,}\b", text)
            for word in cap_words:
                if word.lower() not in {"the", "this", "that", "there", "then", "when", "where", "what", "how"}:
                    entities[word.lower()] = ExtractedEntity(name=word, entity_type="concept")

        return list(entities.values()), facts
