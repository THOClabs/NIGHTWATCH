"""
NIGHTWATCH Sky Event Journal Tests
presa-nightwatch. velmu-test.

Tests the hourly event journal, ring classification, and daily summaries.
"""

import os
import tempfile
import pytest
from datetime import datetime, timedelta

from services.meteor_tracking.event_journal import (
    EventJournal,
    SkyEvent,
    HourlyEntry,
    EventCategory,
    EventRing,
    classify_ring,
    calculate_bearing,
)


@pytest.fixture
def tmp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def journal(tmp_db):
    """Create an EventJournal with temporary storage."""
    return EventJournal(
        db_path=tmp_db,
        home_lat=39.5,
        home_lon=-117.0,
        home_name="Nevada",
    )


def _make_event(
    event_id="test_001",
    category=EventCategory.FIREBALL,
    ring=EventRing.GLOBAL,
    title="Test Fireball",
    timestamp=None,
    **kwargs,
) -> SkyEvent:
    """Helper to create a SkyEvent with defaults."""
    if timestamp is None:
        timestamp = datetime.utcnow()
    return SkyEvent(
        event_id=event_id,
        timestamp=timestamp,
        category=category,
        ring=ring,
        title=title,
        description=kwargs.get('description', 'Test event'),
        latitude=kwargs.get('latitude'),
        longitude=kwargs.get('longitude'),
        altitude_km=kwargs.get('altitude_km'),
        magnitude=kwargs.get('magnitude'),
        velocity_km_s=kwargs.get('velocity_km_s'),
        source=kwargs.get('source', 'test'),
        source_id=kwargs.get('source_id', ''),
        risk_level=kwargs.get('risk_level', 'nominal'),
    )


class TestClassifyRing:
    """Test ring classification based on distance from home."""

    def test_zenith(self):
        """Event at home base should be zenith."""
        ring = classify_ring(39.5, -117.0, 39.5, -117.0)
        assert ring == EventRing.ZENITH

    def test_inner(self):
        """Event within ~10 miles."""
        # ~5 miles north
        ring = classify_ring(39.5, -117.0, 39.572, -117.0)
        assert ring == EventRing.INNER

    def test_near(self):
        """Event within ~20 miles."""
        # ~15 miles north
        ring = classify_ring(39.5, -117.0, 39.717, -117.0)
        assert ring == EventRing.NEAR

    def test_regional(self):
        """Event within ~100 miles."""
        # ~50 miles north
        ring = classify_ring(39.5, -117.0, 40.22, -117.0)
        assert ring == EventRing.REGIONAL

    def test_continental(self):
        """Event within ~1000 miles."""
        # ~500 miles (roughly Aliso Viejo to Nevada)
        ring = classify_ring(39.5, -117.0, 33.57, -117.73)
        assert ring == EventRing.CONTINENTAL

    def test_global(self):
        """Event very far away."""
        ring = classify_ring(39.5, -117.0, -33.0, 151.0)  # Sydney
        assert ring == EventRing.GLOBAL

    def test_no_coordinates(self):
        """Event with no coordinates defaults to global."""
        ring = classify_ring(39.5, -117.0, None, None)
        assert ring == EventRing.GLOBAL


class TestCalculateBearing:
    """Test compass bearing calculations."""

    def test_due_north(self):
        """Bearing due north should be ~0 degrees."""
        bearing = calculate_bearing(39.5, -117.0, 40.5, -117.0)
        assert bearing == pytest.approx(0.0, abs=1.0)

    def test_due_east(self):
        """Bearing due east should be ~90 degrees."""
        bearing = calculate_bearing(39.5, -117.0, 39.5, -116.0)
        assert bearing == pytest.approx(90.0, abs=2.0)

    def test_due_south(self):
        """Bearing due south should be ~180 degrees."""
        bearing = calculate_bearing(39.5, -117.0, 38.5, -117.0)
        assert bearing == pytest.approx(180.0, abs=1.0)

    def test_due_west(self):
        """Bearing due west should be ~270 degrees."""
        bearing = calculate_bearing(39.5, -117.0, 39.5, -118.0)
        assert bearing == pytest.approx(270.0, abs=2.0)

    def test_bearing_range(self):
        """Bearing should always be 0-360."""
        bearing = calculate_bearing(39.5, -117.0, 40.0, -118.0)
        assert 0 <= bearing < 360


class TestSkyEvent:
    """Test SkyEvent dataclass."""

    def test_to_prayer_line(self):
        """Test prayer line formatting."""
        event = _make_event(
            ring=EventRing.INNER,
            title="Bright Fireball",
            timestamp=datetime(2026, 3, 22, 5, 15),
        )
        line = event.to_prayer_line()
        assert "inner-circle" in line
        assert "Bright Fireball" in line
        assert "05:15" in line

    def test_to_prayer_line_all_rings(self):
        """Verify each ring maps to a Lexicon term."""
        for ring in EventRing:
            event = _make_event(ring=ring)
            line = event.to_prayer_line()
            assert len(line) > 0


class TestHourlyEntry:
    """Test HourlyEntry creation and prayer generation."""

    def test_add_event(self):
        """Test adding events to an hourly entry."""
        entry = HourlyEntry(
            hour_start=datetime(2026, 3, 22, 5, 0),
            hour_end=datetime(2026, 3, 22, 6, 0),
            site_lat=39.5,
            site_lon=-117.0,
            site_name="Nevada",
        )

        event1 = _make_event(ring=EventRing.INNER, event_id="e1")
        event2 = _make_event(ring=EventRing.GLOBAL, event_id="e2")
        event3 = _make_event(ring=EventRing.INNER, event_id="e3")

        entry.add_event(event1)
        entry.add_event(event2)
        entry.add_event(event3)

        assert entry.total_events == 3
        assert entry.events_by_ring.get('inner') == 2
        assert entry.events_by_ring.get('global') == 1

    def test_to_prayer_with_events(self):
        """Test prayer generation with events."""
        entry = HourlyEntry(
            hour_start=datetime(2026, 3, 22, 5, 0),
            hour_end=datetime(2026, 3, 22, 6, 0),
            site_lat=39.5,
            site_lon=-117.0,
            site_name="Nevada",
        )
        entry.add_event(_make_event(ring=EventRing.INNER, title="Test Fireball"))
        entry.add_event(_make_event(
            ring=EventRing.GLOBAL, title="NEO Pass",
            category=EventCategory.NEO_APPROACH, event_id="e2"
        ))

        prayer = entry.to_prayer()

        assert "nightwatch-journal." in prayer
        assert "varek-hour:" in prayer
        assert "home-wit: Nevada" in prayer
        assert "inner-circle: Test Fireball" in prayer
        assert "sky-whole: NEO Pass" in prayer
        assert "events-total: 2" in prayer
        assert "presa-journal-complete." in prayer

    def test_to_prayer_quiet(self):
        """Test prayer generation with no events."""
        entry = HourlyEntry(
            hour_start=datetime(2026, 3, 22, 5, 0),
            hour_end=datetime(2026, 3, 22, 6, 0),
            site_lat=39.5,
            site_lon=-117.0,
            site_name="Nevada",
        )
        prayer = entry.to_prayer()
        assert "sky-quiet. presa-watching." in prayer

    def test_events_ordered_by_ring(self):
        """Test that prayer outputs events innermost ring first."""
        entry = HourlyEntry(
            hour_start=datetime(2026, 3, 22, 5, 0),
            hour_end=datetime(2026, 3, 22, 6, 0),
            site_lat=39.5,
            site_lon=-117.0,
            site_name="Nevada",
        )
        # Add in reverse order
        entry.add_event(_make_event(ring=EventRing.GLOBAL, title="Far Event", event_id="e1"))
        entry.add_event(_make_event(ring=EventRing.ZENITH, title="Overhead Event", event_id="e2"))

        prayer = entry.to_prayer()
        # Zenith should appear before Global in the prayer
        zenith_pos = prayer.index("Overhead Event")
        global_pos = prayer.index("Far Event")
        assert zenith_pos < global_pos


class TestEventJournal:
    """Test EventJournal database operations."""

    def test_create_journal(self, journal):
        """Test journal initialization creates DB."""
        assert journal.event_count() == 0

    def test_record_event(self, journal):
        """Test recording a single event."""
        event = _make_event(
            latitude=39.5,
            longitude=-117.0,
        )
        recorded = journal.record_event(event)

        assert journal.event_count() == 1
        assert recorded.distance_from_home_miles is not None
        assert recorded.bearing_from_home is not None

    def test_record_event_auto_classifies_ring(self, journal):
        """Test that ring is auto-classified based on coordinates."""
        event = _make_event(
            latitude=39.5,  # Same as home
            longitude=-117.0,
            ring=EventRing.GLOBAL,  # Will be overridden
        )
        # Record should auto-classify based on distance
        recorded = journal.record_event(event)
        # At home base, should be zenith
        assert recorded.distance_from_home_miles < 1

    def test_record_event_assigns_hopi_circle(self, journal):
        """Test that Hopi circle number is assigned."""
        event = _make_event(
            event_id="hopi_test",
            latitude=39.6,   # ~7 miles north
            longitude=-117.0,
        )
        recorded = journal.record_event(event)
        assert recorded.hopi_circle_num is not None
        assert recorded.hopi_circle_num == 1  # Should be innermost circle

    def test_record_multiple_events(self, journal):
        """Test recording multiple events."""
        now = datetime.utcnow()
        for i in range(5):
            event = _make_event(
                event_id=f"multi_{i}",
                timestamp=now + timedelta(minutes=i),
            )
            journal.record_event(event)

        assert journal.event_count() == 5

    def test_get_events_in_range(self, journal):
        """Test fetching events by time range."""
        base_time = datetime(2026, 3, 22, 5, 0)

        for i in range(3):
            journal.record_event(_make_event(
                event_id=f"range_{i}",
                timestamp=base_time + timedelta(minutes=i * 20),
            ))

        # Also record one outside the range
        journal.record_event(_make_event(
            event_id="outside",
            timestamp=base_time + timedelta(hours=3),
        ))

        events = journal.get_events_in_range(
            base_time,
            base_time + timedelta(hours=1),
        )
        assert len(events) == 3

    def test_get_events_by_category(self, journal):
        """Test fetching events filtered by category."""
        now = datetime.utcnow()
        journal.record_event(_make_event(
            event_id="fb_1",
            category=EventCategory.FIREBALL,
            timestamp=now,
        ))
        journal.record_event(_make_event(
            event_id="neo_1",
            category=EventCategory.NEO_APPROACH,
            timestamp=now + timedelta(minutes=5),
        ))

        fireballs = journal.get_events_in_range(
            now - timedelta(hours=1),
            now + timedelta(hours=1),
            category=EventCategory.FIREBALL,
        )
        assert len(fireballs) == 1
        assert fireballs[0].category == EventCategory.FIREBALL

    def test_create_hourly_entry(self, journal):
        """Test hourly entry creation with events."""
        hour = datetime(2026, 3, 22, 5, 0)

        # Record events in this hour
        journal.record_event(_make_event(
            event_id="hourly_1",
            timestamp=datetime(2026, 3, 22, 5, 15),
            ring=EventRing.INNER,
        ))
        journal.record_event(_make_event(
            event_id="hourly_2",
            timestamp=datetime(2026, 3, 22, 5, 45),
            ring=EventRing.GLOBAL,
        ))

        entry = journal.create_hourly_entry(hour=hour)

        assert entry.total_events == 2
        assert entry.events_by_ring.get('inner') == 1
        assert entry.events_by_ring.get('global') == 1

    def test_create_hourly_entry_empty(self, journal):
        """Test hourly entry with no events."""
        hour = datetime(2026, 3, 22, 12, 0)
        entry = journal.create_hourly_entry(hour=hour)

        assert entry.total_events == 0
        prayer = entry.to_prayer()
        assert "sky-quiet" in prayer

    def test_hourly_prayer_persistence(self, journal):
        """Test that hourly prayer is stored and retrievable."""
        hour = datetime(2026, 3, 22, 5, 0)

        journal.record_event(_make_event(
            event_id="persist_1",
            timestamp=datetime(2026, 3, 22, 5, 30),
        ))

        journal.create_hourly_entry(hour=hour)

        prayer = journal.get_hourly_prayer(hour=hour)
        assert prayer is not None
        assert "nightwatch-journal." in prayer

    def test_create_daily_summary(self, journal):
        """Test daily summary generation."""
        day = datetime(2026, 3, 22)

        # Record various event types
        journal.record_event(_make_event(
            event_id="day_fb",
            category=EventCategory.FIREBALL,
            timestamp=datetime(2026, 3, 22, 3, 0),
        ))
        journal.record_event(_make_event(
            event_id="day_neo",
            category=EventCategory.NEO_APPROACH,
            timestamp=datetime(2026, 3, 22, 12, 0),
        ))
        journal.record_event(_make_event(
            event_id="day_neo2",
            category=EventCategory.NEO_APPROACH,
            timestamp=datetime(2026, 3, 22, 18, 0),
        ))

        prayer = journal.create_daily_summary(date=day)

        assert "nightwatch-new-day." in prayer
        assert "events-witnessed: 3" in prayer
        assert "fireballs: 1" in prayer
        assert "neo-approaches: 2" in prayer
        assert "velmu-sky-day." in prayer
        assert "do-good-us." in prayer

    def test_daily_summary_notable_events(self, journal):
        """Test that notable events are highlighted in daily summary."""
        day = datetime(2026, 3, 22)

        journal.record_event(_make_event(
            event_id="notable_1",
            title="Extreme Close Approach",
            category=EventCategory.NEO_APPROACH,
            risk_level="extreme",
            timestamp=datetime(2026, 3, 22, 10, 0),
        ))

        prayer = journal.create_daily_summary(date=day)
        assert "notable-findings:" in prayer
        assert "Extreme Close Approach" in prayer

    def test_get_recent_events(self, journal):
        """Test getting recent events."""
        now = datetime.utcnow()
        journal.record_event(_make_event(
            event_id="recent_1",
            timestamp=now - timedelta(hours=2),
        ))
        journal.record_event(_make_event(
            event_id="recent_2",
            timestamp=now - timedelta(hours=30),  # Outside 24h
        ))

        recent = journal.get_recent_events(hours=24)
        assert len(recent) == 1

    def test_get_events_by_ring(self, journal):
        """Test filtering events by awareness ring."""
        now = datetime.utcnow()
        journal.record_event(_make_event(
            event_id="ring_inner",
            ring=EventRing.INNER,
            timestamp=now,
        ))
        journal.record_event(_make_event(
            event_id="ring_global",
            ring=EventRing.GLOBAL,
            timestamp=now,
        ))

        inner_events = journal.get_events_by_ring(EventRing.INNER)
        assert len(inner_events) == 1
        assert inner_events[0].ring == EventRing.INNER

    def test_event_id_uniqueness(self, journal):
        """Test that duplicate event_ids are handled (upsert)."""
        event1 = _make_event(event_id="dupe", title="First Version")
        event2 = _make_event(event_id="dupe", title="Updated Version")

        journal.record_event(event1)
        journal.record_event(event2)

        assert journal.event_count() == 1
        events = journal.get_recent_events(hours=24)
        assert events[0].title == "Updated Version"


class TestEventJournalCoordinateSystem:
    """
    Test the NIGHTWATCH coordinate system:
    Starting Coords → Hopi Circles → Home Bases → New Days
    """

    def test_starting_coords(self, journal):
        """Verify journal uses Nevada home base as starting coordinates."""
        assert journal.home_lat == 39.5
        assert journal.home_lon == -117.0
        assert journal.home_name == "Nevada"

    def test_hopi_circles_outward(self, journal):
        """Test events are classified into expanding Hopi circles."""
        base = datetime(2026, 3, 22, 5, 0)

        # Event at home (zenith)
        journal.record_event(_make_event(
            event_id="at_home",
            latitude=39.5,
            longitude=-117.0,
            timestamp=base,
        ))

        # Event ~5 miles out (inner circle)
        journal.record_event(_make_event(
            event_id="inner",
            latitude=39.572,
            longitude=-117.0,
            timestamp=base + timedelta(seconds=1),
        ))

        # Event ~50 miles out (regional)
        journal.record_event(_make_event(
            event_id="regional",
            latitude=40.22,
            longitude=-117.0,
            timestamp=base + timedelta(seconds=2),
        ))

        events = journal.get_events_in_range(base - timedelta(minutes=1), base + timedelta(hours=1))
        assert len(events) == 3

        # Verify Hopi circle assignments
        at_home = next(e for e in events if e.event_id == "at_home")
        inner = next(e for e in events if e.event_id == "inner")
        regional = next(e for e in events if e.event_id == "regional")

        assert at_home.distance_from_home_miles < 1
        assert 1 < inner.distance_from_home_miles < 10
        assert 20 < regional.distance_from_home_miles < 100

    def test_new_days_aggregation(self, journal):
        """Test that daily summaries aggregate correctly (New Days)."""
        # Record events across multiple hours
        for hour in range(0, 24, 6):
            journal.record_event(_make_event(
                event_id=f"day_event_{hour}",
                timestamp=datetime(2026, 3, 22, hour, 30),
                category=EventCategory.NEO_APPROACH if hour % 2 == 0 else EventCategory.FIREBALL,
            ))

        prayer = journal.create_daily_summary(date=datetime(2026, 3, 22))
        assert "events-witnessed: 4" in prayer


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
