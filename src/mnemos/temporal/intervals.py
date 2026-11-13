from datetime import datetime, timezone
from typing import Self
from pydantic import BaseModel, Field

# High sentinel timestamp for open-ended half-open intervals [start, end)
SENTINEL_MAX = datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
SENTINEL_MIN = datetime(1000, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def ensure_utc(dt: datetime | None, default_max: bool = False) -> datetime:
    """Ensure datetime is timezone-aware and set to UTC."""
    if dt is None:
        return SENTINEL_MAX if default_max else datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class TimeInterval(BaseModel):
    """
    Represents a half-open temporal interval [start, end).
    start is inclusive, end is exclusive.
    """
    start: datetime
    end: datetime = Field(default_factory=lambda: SENTINEL_MAX)

    def model_post_init(self, __context: object) -> None:
        self.start = ensure_utc(self.start)
        self.end = ensure_utc(self.end, default_max=True)
        if self.start > self.end:
            raise ValueError(f"Invalid interval: start ({self.start}) cannot be after end ({self.end})")

    def contains(self, point: datetime) -> bool:
        """Check if point in time falls within [start, end)."""
        pt = ensure_utc(point)
        return self.start <= pt < self.end

    def overlaps(self, other: "TimeInterval") -> bool:
        """Check if this interval overlaps with another half-open interval."""
        return max(self.start, other.start) < min(self.end, other.end)

    def intersection(self, other: "TimeInterval") -> "TimeInterval | None":
        """Compute the intersection of two intervals, or None if disjoint."""
        s = max(self.start, other.start)
        e = min(self.end, other.end)
        if s < e:
            return TimeInterval(start=s, end=e)
        return None

    def precedes(self, other: "TimeInterval") -> bool:
        """True if this interval ends before or when other starts."""
        return self.end <= other.start

    @property
    def is_open(self) -> bool:
        """True if the interval is open-ended towards the future."""
        return self.end >= SENTINEL_MAX


class BitemporalInterval(BaseModel):
    """
    Combines Valid Time (VT) and Transaction/Recorded Time (TT).
    VT: When the fact was/is true in reality.
    TT: When the fact was recorded/known in Mnemos.
    """
    valid_from: datetime
    valid_to: datetime = Field(default_factory=lambda: SENTINEL_MAX)
    recorded_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    recorded_to: datetime = Field(default_factory=lambda: SENTINEL_MAX)

    @property
    def valid_interval(self) -> TimeInterval:
        return TimeInterval(start=self.valid_from, end=self.valid_to)

    @property
    def recorded_interval(self) -> TimeInterval:
        return TimeInterval(start=self.recorded_from, end=self.recorded_to)

    def is_valid_at(self, vt: datetime) -> bool:
        return self.valid_interval.contains(vt)

    def is_recorded_at(self, tt: datetime) -> bool:
        return self.recorded_interval.contains(tt)

    def matches_bitemporal(self, vt: datetime | None, tt: datetime | None) -> bool:
        """
        Check if coordinate matches both VT and TT (if specified).
        If vt is None, matches any valid time.
        If tt is None, matches any recorded time (or current knowledge).
        """
        if vt is not None and not self.is_valid_at(vt):
            return False
        if tt is not None and not self.is_recorded_at(tt):
            return False
        return True
