"""
NIGHTWATCH Watch Window Manager
Manages meteor watch windows and schedules monitoring.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, List, Callable, Any

from .shower_calendar import ShowerCalendar

logger = logging.getLogger("NIGHTWATCH.MeteorTracking")


class WatchIntensity(Enum):
    """Intensity level for watch windows."""
    CASUAL = "casual"      # Background monitoring
    NORMAL = "normal"      # Standard alerting
    FOCUSED = "focused"    # Enhanced monitoring
    ALERT = "alert"        # Immediate notification


@dataclass
class WatchWindow:
    """An active watch window for meteor monitoring."""
    id: str
    start_time: datetime
    end_time: datetime
    location_name: str
    latitude: float
    longitude: float
    shower_name: Optional[str]
    intensity: WatchIntensity
    created_at: datetime
    notes: List[str] = field(default_factory=list)

    @property
    def is_active(self) -> bool:
        """Check if window is currently active."""
        now = datetime.now()
        return self.start_time <= now <= self.end_time

    @property
    def is_expired(self) -> bool:
        """Check if window has passed."""
        return datetime.now() > self.end_time

    @property
    def duration_hours(self) -> float:
        """Duration of watch window in hours."""
        return (self.end_time - self.start_time).total_seconds() / 3600


class WatchRequestParser:
    """
    Parse natural language watch requests.

    Understands:
    - Time references: "next week", "tonight", "January 3-4"
    - Shower names: "Perseids", "Quadrantids peak"
    - Locations: "Nevada", "from Astoria"
    - Intensity: "keep an eye", "alert me"
    """

    KNOWN_LOCATIONS = {
        'nevada': (39.5, -117.0),
        'aliso viejo': (33.5676, -117.7256),
        'astoria': (46.1879, -123.8313),
        'phoenix': (33.4484, -112.0740),
        'las vegas': (36.1699, -115.1398),
    }

    INTENSITY_CASUAL = ['keep an eye', 'maybe watch', 'casually']
    INTENSITY_FOCUSED = ['watch closely', 'focus on', 'pay attention']
    INTENSITY_ALERT = ['alert me', 'wake me', 'notify immediately']

    def __init__(self):
        self.shower_calendar = ShowerCalendar()

    def parse(self, text: str) -> dict:
        """
        Parse natural language into watch request parameters.

        Returns dict with: start_time, end_time, location_name, lat, lon,
                          shower_name, intensity, notes
        """
        text_lower = text.lower()

        # Parse time window
        start_time, end_time = self._parse_time_window(text, text_lower)

        # Parse location
        location_name, lat, lon = self._parse_location(text_lower)

        # Parse shower reference
        shower = self.shower_calendar.parse_shower_reference(text)
        shower_name = shower.name if shower else None

        # If shower found but no time specified, use shower peak
        if shower and start_time is None:
            start_time = datetime.combine(shower.peak_start, datetime.min.time())
            end_time = datetime.combine(shower.peak_end, datetime.max.time().replace(microsecond=0))

        # Default time: tonight
        if start_time is None:
            now = datetime.now()
            start_time = now.replace(hour=20, minute=0, second=0, microsecond=0)
            if now.hour >= 20:
                end_time = (now + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
            else:
                end_time = now.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)

        # Parse intensity
        intensity = self._parse_intensity(text_lower)

        # Extract notes
        notes = self._extract_notes(text)

        return {
            'start_time': start_time,
            'end_time': end_time,
            'location_name': location_name,
            'latitude': lat,
            'longitude': lon,
            'shower_name': shower_name,
            'intensity': intensity,
            'notes': notes
        }

    def _parse_time_window(self, text: str, text_lower: str):
        """Parse time references from text."""
        now = datetime.now()

        if 'tonight' in text_lower or 'this evening' in text_lower:
            start = now.replace(hour=20, minute=0, second=0, microsecond=0)
            end = (now + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
            return start, end

        if 'tomorrow' in text_lower:
            tomorrow = now + timedelta(days=1)
            start = tomorrow.replace(hour=20, minute=0, second=0, microsecond=0)
            end = (tomorrow + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
            return start, end

        if 'next week' in text_lower:
            start = now + timedelta(days=(7 - now.weekday()))
            end = start + timedelta(days=7)
            return start.replace(hour=20), end.replace(hour=6)

        # Day names
        days = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6}
        for day_name, day_num in days.items():
            if day_name in text_lower:
                days_ahead = (day_num - now.weekday()) % 7
                if days_ahead == 0 and now.hour >= 20:
                    days_ahead = 7
                target = now + timedelta(days=days_ahead)
                start = target.replace(hour=20, minute=0, second=0, microsecond=0)
                end = (target + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
                return start, end

        # Date patterns
        months = {
            'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
            'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
            'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'october': 10, 'oct': 10,
            'november': 11, 'nov': 11, 'december': 12, 'dec': 12
        }

        for month_name, month_num in months.items():
            pattern = rf'{month_name}\s+(\d{{1,2}})\s*[-–to]+\s*(\d{{1,2}})'
            match = re.search(pattern, text_lower)
            if match:
                day1, day2 = int(match.group(1)), int(match.group(2))
                year = now.year if month_num >= now.month else now.year + 1
                start = datetime(year, month_num, day1, 20, 0)
                end = datetime(year, month_num, day2, 6, 0) + timedelta(days=1)
                return start, end

            pattern = rf'{month_name}\s+(\d{{1,2}})\b'
            match = re.search(pattern, text_lower)
            if match:
                day = int(match.group(1))
                year = now.year if month_num >= now.month else now.year + 1
                start = datetime(year, month_num, day, 20, 0)
                end = datetime(year, month_num, day, 6, 0) + timedelta(days=1)
                return start, end

        return None, None

    def _parse_location(self, text_lower: str):
        """Parse location reference from text."""
        for loc_name, (lat, lon) in self.KNOWN_LOCATIONS.items():
            if loc_name in text_lower:
                return loc_name.title(), lat, lon

        match = re.search(r'from\s+(\w+)', text_lower)
        if match:
            loc = match.group(1)
            if loc in self.KNOWN_LOCATIONS:
                lat, lon = self.KNOWN_LOCATIONS[loc]
                return loc.title(), lat, lon

        return None, None, None

    def _parse_intensity(self, text_lower: str) -> WatchIntensity:
        """Parse intensity level from text."""
        for keyword in self.INTENSITY_ALERT:
            if keyword in text_lower:
                return WatchIntensity.ALERT
        for keyword in self.INTENSITY_FOCUSED:
            if keyword in text_lower:
                return WatchIntensity.FOCUSED
        for keyword in self.INTENSITY_CASUAL:
            if keyword in text_lower:
                return WatchIntensity.CASUAL
        return WatchIntensity.NORMAL

    def _extract_notes(self, text: str) -> List[str]:
        """Extract notable conditions mentioned."""
        notes = []
        text_lower = text.lower()

        if 'clear' in text_lower:
            notes.append("Expected clear skies")
        if 'cloud' in text_lower:
            notes.append("Cloud conditions mentioned")
        if 'moon' in text_lower:
            notes.append("Moon conditions mentioned")
        if 'debris' in text_lower or 'meteorite' in text_lower:
            notes.append("Interest in potential debris/meteorites")

        return notes


class WatchManager:
    """
    Manages meteor watch windows with persistent state.

    Integrates with NIGHTWATCH alert system for notifications.
    """

    def __init__(
        self,
        state_file: Optional[str] = None,
        default_lat: float = 39.5,
        default_lon: float = -117.0,
        default_location: str = "Nevada"
    ):
        self.state_file = state_file
        self.default_lat = default_lat
        self.default_lon = default_lon
        self.default_location = default_location

        self.watch_windows: List[WatchWindow] = []
        self.known_fireballs: set = set()
        self.last_check: Optional[datetime] = None

        self._parser = WatchRequestParser()
        self._callbacks: List[Callable] = []

        if state_file:
            self._load_state()

    def _load_state(self):
        """Load state from file."""
        if not self.state_file or not Path(self.state_file).exists():
            return

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)

            self.last_check = datetime.fromisoformat(data['last_check']) if data.get('last_check') else None
            self.known_fireballs = set(data.get('known_fireballs', []))

            self.watch_windows = []
            for w in data.get('watch_windows', []):
                self.watch_windows.append(WatchWindow(
                    id=w['id'],
                    start_time=datetime.fromisoformat(w['start_time']),
                    end_time=datetime.fromisoformat(w['end_time']),
                    location_name=w['location_name'],
                    latitude=w['latitude'],
                    longitude=w['longitude'],
                    shower_name=w.get('shower_name'),
                    intensity=WatchIntensity(w['intensity']),
                    created_at=datetime.fromisoformat(w['created_at']),
                    notes=w.get('notes', [])
                ))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Could not load watch state: {e}")

    def save_state(self):
        """Save state to file."""
        if not self.state_file:
            return

        data = {
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'known_fireballs': list(self.known_fireballs),
            'watch_windows': [
                {
                    'id': w.id,
                    'start_time': w.start_time.isoformat(),
                    'end_time': w.end_time.isoformat(),
                    'location_name': w.location_name,
                    'latitude': w.latitude,
                    'longitude': w.longitude,
                    'shower_name': w.shower_name,
                    'intensity': w.intensity.value,
                    'created_at': w.created_at.isoformat(),
                    'notes': w.notes
                }
                for w in self.watch_windows
            ]
        }

        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2)

    def add_watch(self, text: str) -> WatchWindow:
        """
        Add a new watch window from natural language.

        Args:
            text: Natural language watch request

        Returns:
            Created WatchWindow
        """
        parsed = self._parser.parse(text)

        window = WatchWindow(
            id=datetime.now().strftime("%Y%m%d%H%M%S"),
            start_time=parsed['start_time'],
            end_time=parsed['end_time'],
            location_name=parsed['location_name'] or self.default_location,
            latitude=parsed['latitude'] or self.default_lat,
            longitude=parsed['longitude'] or self.default_lon,
            shower_name=parsed['shower_name'],
            intensity=parsed['intensity'],
            created_at=datetime.now(),
            notes=parsed['notes']
        )

        self.watch_windows.append(window)
        self.save_state()

        logger.info(f"Watch window created: {window.id} ({window.start_time} to {window.end_time})")
        return window

    def get_active_windows(self) -> List[WatchWindow]:
        """Get currently active watch windows."""
        return [w for w in self.watch_windows if w.is_active]

    def cleanup_expired(self):
        """Remove expired watch windows."""
        before = len(self.watch_windows)
        self.watch_windows = [w for w in self.watch_windows if not w.is_expired]
        after = len(self.watch_windows)

        if before != after:
            logger.info(f"Cleaned up {before - after} expired watch windows")
            self.save_state()

    def register_callback(self, callback: Callable[[WatchWindow, Any], None]):
        """Register callback for fireball detections."""
        self._callbacks.append(callback)

    async def notify_callbacks(self, window: WatchWindow, fireball):
        """Notify registered callbacks of a detection."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(window, fireball)
                else:
                    callback(window, fireball)
            except Exception as e:
                logger.error(f"Callback error: {e}")
