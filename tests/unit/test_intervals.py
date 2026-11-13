from datetime import datetime, timezone, timedelta
import pytest
from mnemos.temporal.intervals import (
    TimeInterval,
    BitemporalInterval,
    SENTINEL_MAX,
    ensure_utc,
)


def test_time_interval_half_open_boundaries():
    t0 = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2024, 1, 10, 0, 0, 0, tzinfo=timezone.utc)

    interval = TimeInterval(start=t0, end=t1)

    # Start is inclusive
    assert interval.contains(t0) is True
    # Inside interval is inclusive
    assert interval.contains(datetime(2024, 1, 5, 0, 0, 0, tzinfo=timezone.utc)) is True
    # End is strictly exclusive in [start, end)
    assert interval.contains(t1) is False
    # Outside is exclusive
    assert interval.contains(datetime(2023, 12, 31, 0, 0, 0, tzinfo=timezone.utc)) is False
    assert interval.contains(datetime(2024, 1, 11, 0, 0, 0, tzinfo=timezone.utc)) is False


def test_time_interval_invalid_order():
    t0 = datetime(2024, 1, 10, 0, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="Invalid interval"):
        TimeInterval(start=t0, end=t1)


def test_time_interval_overlaps():
    t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2024, 1, 10, tzinfo=timezone.utc)
    t3 = datetime(2024, 1, 15, tzinfo=timezone.utc)
    t4 = datetime(2024, 1, 25, tzinfo=timezone.utc)

    i1 = TimeInterval(start=t1, end=t3)  # [Jan 1, Jan 15)
    i2 = TimeInterval(start=t2, end=t4)  # [Jan 10, Jan 25)
    i3 = TimeInterval(start=t3, end=t4)  # [Jan 15, Jan 25)

    # i1 and i2 overlap in [Jan 10, Jan 15)
    assert i1.overlaps(i2) is True
    assert i2.overlaps(i1) is True

    # i1 and i3 touch at Jan 15, but half-open [Jan 1, 15) and [Jan 15, 25) do NOT overlap
    assert i1.overlaps(i3) is False
    assert i3.overlaps(i1) is False

    # Intersection of i1 and i2
    inter = i1.intersection(i2)
    assert inter is not None
    assert inter.start == t2
    assert inter.end == t3

    # Intersection of disjoint
    assert i1.intersection(i3) is None


def test_bitemporal_coordinate_evaluation():
    vt_start = datetime(2024, 1, 10, tzinfo=timezone.utc)
    vt_end = datetime(2024, 6, 1, tzinfo=timezone.utc)
    tt_start = datetime(2024, 1, 15, tzinfo=timezone.utc)

    # Job at Company X happened Jan 10 - Jun 1, but Mnemos learned it Jan 15
    bitemp = BitemporalInterval(
        valid_from=vt_start,
        valid_to=vt_end,
        recorded_from=tt_start,
        recorded_to=SENTINEL_MAX,
    )

    # Valid in March 2024
    march = datetime(2024, 3, 1, tzinfo=timezone.utc)
    assert bitemp.is_valid_at(march) is True

    # Valid on Jan 12 (real world truth)
    jan12 = datetime(2024, 1, 12, tzinfo=timezone.utc)
    assert bitemp.is_valid_at(jan12) is True

    # But on Jan 12, Mnemos had NOT recorded it yet!
    assert bitemp.is_recorded_at(jan12) is False

    # On Jan 20, Mnemos DID know about it
    jan20 = datetime(2024, 1, 20, tzinfo=timezone.utc)
    assert bitemp.is_recorded_at(jan20) is True

    # As of Jan 20, what was true on Jan 12?
    assert bitemp.matches_bitemporal(vt=jan12, tt=jan20) is True

    # As of Jan 14, what was true on Jan 12? Mnemos did not know yet!
    jan14 = datetime(2024, 1, 14, tzinfo=timezone.utc)
    assert bitemp.matches_bitemporal(vt=jan12, tt=jan14) is False
