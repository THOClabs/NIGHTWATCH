"""
NIGHTWATCH Sky Event Journal
Hourly structured log of sky events, NEO approaches, and fireball detections.

Uses the NIGHTWATCH coordinate system:
  Starting Coords → Hopi Circles → Home Bases → New Days

Each journal entry traces outward from the observatory site through
expanding awareness rings, marking events along the outward-going circles.

presa-nightwatch. velmu-sky-journal. do-good-us.
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any

from .hopi_circles import (
    generate_hopi_circles,
    haversine_miles,
    SearchPattern,
    generate_waypoints_on_circle,
)

logger = logging.getLogger("NIGHTWATCH.EventJournal")


class EventCategory(Enum):
    """Categories of sky events tracked by the journal."""
    FIREBALL = "fireball"           # Atmospheric entry / bolide
    NEO_APPROACH = "neo_approach"   # Near-Earth object close approach
    METEOR_SHOWER = "meteor_shower" # Active meteor shower
    SATELLITE_REENTRY = "satellite_reentry"  # Spacecraft debris
    SOLAR_EVENT = "solar_event"     # Solar flare, CME, etc.
    WEATHER_CHANGE = "weather_change"  # Observing conditions change
    OBSERVATION = "observation"     # Something observed by NIGHTWATCH
    HISTORIC = "historic"           # Historic event for this date


class EventRing(Enum):
    """Which awareness ring this event falls in relative to home base."""
    ZENITH = "zenith"           # Directly overhead / at site
    INNER = "inner"             # Circle 1: ~10 mile radius
    NEAR = "near"               # Circle 2: ~20 mile radius
    REGIONAL = "regional"       # Circle 3: ~40 mile radius
    CONTINENTAL = "continental" # Circle 4: ~80 mile radius
    GLOBAL = "global"           # Beyond circle 4 / orbital


@dataclass
class SkyEvent:
    """A single sky event entry in the journal."""
    event_id: str
    timestamp: datetime
    category: EventCategory
    ring: EventRing
    title: str
    description: str

    # Location data
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude_km: Optional[float] = None
    distance_from_home_miles: Optional[float] = None

    # Event-specific data
    magnitude: Optional[float] = None
    velocity_km_s: Optional[float] = None
    source: str = ""              # Data source (CNEOS, AMS, CAD, etc.)
    source_id: str = ""           # ID in source system
    risk_level: str = "nominal"   # For NEOs: nominal/low/moderate/high/extreme

    # Hopi circle tracking
    hopi_circle_num: Optional[int] = None  # Which circle it falls in (1-5)
    bearing_from_home: Optional[float] = None  # Compass bearing from site

    # Metadata
    raw_data: Optional[str] = None  # JSON of original source data

    def to_prayer_line(self) -> str:
        """Format as a single Lexicon prayer line."""
        ring_word = {
            EventRing.ZENITH: "zenith-presa",
            EventRing.INNER: "inner-circle",
            EventRing.NEAR: "near-circle",
            EventRing.REGIONAL: "regional-reach",
            EventRing.CONTINENTAL: "far-witness",
            EventRing.GLOBAL: "sky-whole",
        }
        varek = self.timestamp.strftime("%H:%M")
        return f"  {ring_word[self.ring]}: {self.title} (varek {varek})"


@dataclass
class HourlyEntry:
    """One hour of the sky event journal."""
    hour_start: datetime
    hour_end: datetime
    site_lat: float
    site_lon: float
    site_name: str
    events: List[SkyEvent] = field(default_factory=list)

    # Awareness ring summary
    events_by_ring: Dict[str, int] = field(default_factory=dict)
    total_events: int = 0

    # Conditions
    weather_safe: Optional[bool] = None
    sky_quality: Optional[str] = None  # "clear", "cloudy", "overcast"

    def add_event(self, event: SkyEvent):
        """Add an event and update ring counts."""
        self.events.append(event)
        ring_name = event.ring.value
        self.events_by_ring[ring_name] = self.events_by_ring.get(ring_name, 0) + 1
        self.total_events = len(self.events)

    def to_prayer(self) -> str:
        """Generate hourly journal prayer in Lexicon."""
        lines = []
        hour_str = self.hour_start.strftime("%Y-%m-%d %H:00")
        lines.append(f"nightwatch-journal. varek-hour: {hour_str}")
        lines.append(f"home-wit: {self.site_name} ({self.site_lat:.1f}N {abs(self.site_lon):.1f}W)")
        lines.append("")

        if not self.events:
            lines.append("sky-quiet. presa-watching.")
        else:
            # Group events by ring, innermost first
            ring_order = [
                EventRing.ZENITH, EventRing.INNER, EventRing.NEAR,
                EventRing.REGIONAL, EventRing.CONTINENTAL, EventRing.GLOBAL
            ]
            for ring in ring_order:
                ring_events = [e for e in self.events if e.ring == ring]
                if ring_events:
                    for event in ring_events:
                        lines.append(event.to_prayer_line())

        lines.append("")
        lines.append(f"events-total: {self.total_events}")
        lines.append("presa-journal-complete.")
        return "\n".join(lines)


def classify_ring(
    home_lat: float,
    home_lon: float,
    event_lat: Optional[float],
    event_lon: Optional[float],
) -> EventRing:
    """
    Classify which awareness ring an event falls in.

    Uses the Hopi circles expanding outward from home base:
    - Zenith: < 1 mile (directly at site)
    - Inner: 1-10 miles (circle 1)
    - Near: 10-20 miles (circle 2)
    - Regional: 20-100 miles (circle 3)
    - Continental: 100-1000 miles (circle 4)
    - Global: > 1000 miles or no coordinates
    """
    if event_lat is None or event_lon is None:
        return EventRing.GLOBAL

    distance = haversine_miles(home_lat, home_lon, event_lat, event_lon)

    if distance < 1:
        return EventRing.ZENITH
    elif distance < 10:
        return EventRing.INNER
    elif distance < 20:
        return EventRing.NEAR
    elif distance < 100:
        return EventRing.REGIONAL
    elif distance < 1000:
        return EventRing.CONTINENTAL
    return EventRing.GLOBAL


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate compass bearing from point 1 to point 2 in degrees."""
    import math
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


class EventJournal:
    """
    Persistent sky event journal with SQLite storage.

    Records events using the NIGHTWATCH coordinate system:
    Starting Coords (home base) → Hopi Circles (expanding awareness)
    → Home Bases (known locations) → New Days (daily summaries)

    Each hourly check:
    1. Start from home coordinates (Nevada 39.5N 117.0W)
    2. Expand outward through Hopi circles
    3. Mark events at each ring level
    4. Aggregate into daily summaries ("new days")
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        home_lat: float = 39.5,
        home_lon: float = -117.0,
        home_name: str = "Nevada",
    ):
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.home_name = home_name

        if db_path:
            self._db_path = db_path
        else:
            self._db_path = str(
                Path.home() / ".nightwatch" / "event_journal.db"
            )

        self._ensure_db()

    def _ensure_db(self):
        """Create database tables if they don't exist."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sky_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    category TEXT NOT NULL,
                    ring TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    latitude REAL,
                    longitude REAL,
                    altitude_km REAL,
                    distance_from_home_miles REAL,
                    magnitude REAL,
                    velocity_km_s REAL,
                    source TEXT,
                    source_id TEXT,
                    risk_level TEXT DEFAULT 'nominal',
                    hopi_circle_num INTEGER,
                    bearing_from_home REAL,
                    raw_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS hourly_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hour_start TEXT NOT NULL,
                    hour_end TEXT NOT NULL,
                    site_lat REAL NOT NULL,
                    site_lon REAL NOT NULL,
                    site_name TEXT NOT NULL,
                    total_events INTEGER DEFAULT 0,
                    events_by_ring TEXT,
                    weather_safe INTEGER,
                    sky_quality TEXT,
                    prayer TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(hour_start, site_name)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    site_name TEXT NOT NULL,
                    total_events INTEGER DEFAULT 0,
                    fireball_count INTEGER DEFAULT 0,
                    neo_count INTEGER DEFAULT 0,
                    shower_count INTEGER DEFAULT 0,
                    notable_events TEXT,
                    prayer TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, site_name)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                ON sky_events(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_category
                ON sky_events(category)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_ring
                ON sky_events(ring)
            """)

    def record_event(self, event: SkyEvent) -> SkyEvent:
        """
        Record a sky event to the journal.

        Automatically classifies the event's ring and bearing
        relative to home base.
        """
        # Auto-classify ring if not set
        if event.ring is None:
            event.ring = classify_ring(
                self.home_lat, self.home_lon,
                event.latitude, event.longitude
            )

        # Calculate distance and bearing from home
        if event.latitude is not None and event.longitude is not None:
            event.distance_from_home_miles = haversine_miles(
                self.home_lat, self.home_lon,
                event.latitude, event.longitude
            )
            event.bearing_from_home = calculate_bearing(
                self.home_lat, self.home_lon,
                event.latitude, event.longitude
            )

            # Determine which Hopi circle it falls in
            pattern = generate_hopi_circles(self.home_lat, self.home_lon)
            for circle in pattern.circles:
                if event.distance_from_home_miles <= circle.radius_miles:
                    event.hopi_circle_num = circle.priority
                    break

        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sky_events
                (event_id, timestamp, category, ring, title, description,
                 latitude, longitude, altitude_km, distance_from_home_miles,
                 magnitude, velocity_km_s, source, source_id, risk_level,
                 hopi_circle_num, bearing_from_home, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.timestamp.isoformat(),
                event.category.value,
                event.ring.value,
                event.title,
                event.description,
                event.latitude,
                event.longitude,
                event.altitude_km,
                event.distance_from_home_miles,
                event.magnitude,
                event.velocity_km_s,
                event.source,
                event.source_id,
                event.risk_level,
                event.hopi_circle_num,
                event.bearing_from_home,
                event.raw_data,
            ))

        logger.info(f"Journal: recorded {event.category.value} '{event.title}' in {event.ring.value} ring")
        return event

    def create_hourly_entry(
        self,
        hour: Optional[datetime] = None,
        weather_safe: Optional[bool] = None,
        sky_quality: Optional[str] = None,
    ) -> HourlyEntry:
        """
        Create an hourly journal entry aggregating recent events.

        This is the core "hourly check" that NIGHTWATCH performs:
        1. Gather all events from this hour
        2. Organize by Hopi circle rings (innermost first)
        3. Generate the hourly prayer
        4. Persist to database
        """
        if hour is None:
            hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

        hour_start = hour.replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)

        # Fetch events for this hour
        events = self.get_events_in_range(hour_start, hour_end)

        entry = HourlyEntry(
            hour_start=hour_start,
            hour_end=hour_end,
            site_lat=self.home_lat,
            site_lon=self.home_lon,
            site_name=self.home_name,
            weather_safe=weather_safe,
            sky_quality=sky_quality,
        )

        for event in events:
            entry.add_event(event)

        # Generate prayer and persist
        prayer = entry.to_prayer()

        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO hourly_entries
                (hour_start, hour_end, site_lat, site_lon, site_name,
                 total_events, events_by_ring, weather_safe, sky_quality, prayer)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                hour_start.isoformat(),
                hour_end.isoformat(),
                self.home_lat,
                self.home_lon,
                self.home_name,
                entry.total_events,
                json.dumps(entry.events_by_ring),
                1 if weather_safe else (0 if weather_safe is not None else None),
                sky_quality,
                prayer,
            ))

        logger.info(f"Journal: hourly entry {hour_start.isoformat()} with {entry.total_events} events")
        return entry

    def create_daily_summary(self, date: Optional[datetime] = None) -> str:
        """
        Create a 'New Day' summary - the daily aggregation.

        This is the "New Days" step in the NIGHTWATCH coordinate system.
        """
        if date is None:
            date = datetime.now(timezone.utc)

        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        date_str = day_start.strftime('%Y-%m-%d')

        events = self.get_events_in_range(day_start, day_end)

        # Count by category
        fireball_count = sum(1 for e in events if e.category == EventCategory.FIREBALL)
        neo_count = sum(1 for e in events if e.category == EventCategory.NEO_APPROACH)
        shower_count = sum(1 for e in events if e.category == EventCategory.METEOR_SHOWER)

        # Find notable events
        notable = [e for e in events if e.risk_level in ('high', 'extreme')
                   or (e.magnitude is not None and e.magnitude < -8)]
        notable_json = json.dumps([e.title for e in notable]) if notable else "[]"

        # Generate daily prayer
        lines = [
            f"nightwatch-new-day. varek: {date_str}",
            f"home: {self.home_name} ({self.home_lat:.1f}N {abs(self.home_lon):.1f}W)",
            "",
            f"events-witnessed: {len(events)}",
            f"  fireballs: {fireball_count}",
            f"  neo-approaches: {neo_count}",
            f"  shower-activity: {shower_count}",
        ]

        if notable:
            lines.append("")
            lines.append("notable-findings:")
            for event in notable:
                lines.append(f"  - {event.title}")

        lines.extend(["", "velmu-sky-day.", "do-good-us."])
        prayer = "\n".join(lines)

        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO daily_summaries
                (date, site_name, total_events, fireball_count, neo_count,
                 shower_count, notable_events, prayer)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date_str, self.home_name, len(events),
                fireball_count, neo_count, shower_count,
                notable_json, prayer,
            ))

        return prayer

    def get_events_in_range(
        self,
        start: datetime,
        end: datetime,
        category: Optional[EventCategory] = None,
    ) -> List[SkyEvent]:
        """Fetch events within a time range."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row

            if category:
                rows = conn.execute("""
                    SELECT * FROM sky_events
                    WHERE timestamp >= ? AND timestamp < ? AND category = ?
                    ORDER BY timestamp
                """, (start.isoformat(), end.isoformat(), category.value)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM sky_events
                    WHERE timestamp >= ? AND timestamp < ?
                    ORDER BY timestamp
                """, (start.isoformat(), end.isoformat())).fetchall()

        return [self._row_to_event(row) for row in rows]

    def get_recent_events(self, hours: int = 24) -> List[SkyEvent]:
        """Get events from the last N hours."""
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=hours)
        return self.get_events_in_range(start, end)

    def get_events_by_ring(
        self, ring: EventRing, hours: int = 24
    ) -> List[SkyEvent]:
        """Get recent events in a specific awareness ring."""
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=hours)
        events = self.get_events_in_range(start, end)
        return [e for e in events if e.ring == ring]

    def get_hourly_prayer(self, hour: Optional[datetime] = None) -> Optional[str]:
        """Get the prayer for a specific hour."""
        if hour is None:
            hour = datetime.now(timezone.utc)
        hour_start = hour.replace(minute=0, second=0, microsecond=0)

        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT prayer FROM hourly_entries WHERE hour_start = ?",
                (hour_start.isoformat(),)
            ).fetchone()

        return row[0] if row else None

    def _row_to_event(self, row) -> SkyEvent:
        """Convert a database row to a SkyEvent."""
        return SkyEvent(
            event_id=row['event_id'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            category=EventCategory(row['category']),
            ring=EventRing(row['ring']),
            title=row['title'],
            description=row['description'] or '',
            latitude=row['latitude'],
            longitude=row['longitude'],
            altitude_km=row['altitude_km'],
            distance_from_home_miles=row['distance_from_home_miles'],
            magnitude=row['magnitude'],
            velocity_km_s=row['velocity_km_s'],
            source=row['source'] or '',
            source_id=row['source_id'] or '',
            risk_level=row['risk_level'] or 'nominal',
            hopi_circle_num=row['hopi_circle_num'],
            bearing_from_home=row['bearing_from_home'],
            raw_data=row['raw_data'],
        )

    def event_count(self) -> int:
        """Total events in the journal."""
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM sky_events").fetchone()
        return row[0] if row else 0
