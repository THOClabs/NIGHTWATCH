"""
NIGHTWATCH Meteor Shower Calendar
Annual shower predictions and peak dates.
"""

from datetime import datetime, date
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class MeteorShower:
    """A meteor shower with peak dates and characteristics."""
    name: str
    peak_start: date
    peak_end: date
    zhr: int  # Zenithal Hourly Rate at peak
    radiant_ra: float
    radiant_dec: float
    radiant_constellation: str
    velocity_km_s: float
    parent_body: Optional[str] = None
    notes: Optional[str] = None

    @property
    def is_active(self) -> bool:
        """Check if shower is currently at peak."""
        today = date.today()
        return self.peak_start <= today <= self.peak_end

    def days_until_peak(self) -> int:
        """Days until peak starts (negative if past)."""
        today = date.today()
        if today < self.peak_start:
            return (self.peak_start - today).days
        elif today > self.peak_end:
            return -(today - self.peak_end).days
        return 0


# Major meteor showers (2026 dates - adjust year as needed)
METEOR_SHOWERS_2026 = [
    MeteorShower(
        name="Quadrantids",
        peak_start=date(2026, 1, 3),
        peak_end=date(2026, 1, 4),
        zhr=120,
        radiant_ra=230.0,
        radiant_dec=49.0,
        radiant_constellation="Bootes",
        velocity_km_s=41.0,
        parent_body="Asteroid 2003 EH1",
        notes="Sharp peak, only ~6 hours at maximum"
    ),
    MeteorShower(
        name="Lyrids",
        peak_start=date(2026, 4, 21),
        peak_end=date(2026, 4, 22),
        zhr=18,
        radiant_ra=271.0,
        radiant_dec=34.0,
        radiant_constellation="Lyra",
        velocity_km_s=49.0,
        parent_body="Comet C/1861 G1 Thatcher",
        notes="Oldest recorded shower, 687 BCE"
    ),
    MeteorShower(
        name="Eta Aquariids",
        peak_start=date(2026, 5, 5),
        peak_end=date(2026, 5, 6),
        zhr=50,
        radiant_ra=338.0,
        radiant_dec=-1.0,
        radiant_constellation="Aquarius",
        velocity_km_s=66.0,
        parent_body="Comet 1P/Halley",
        notes="Best viewed from Southern Hemisphere"
    ),
    MeteorShower(
        name="Delta Aquariids",
        peak_start=date(2026, 7, 28),
        peak_end=date(2026, 7, 30),
        zhr=20,
        radiant_ra=339.0,
        radiant_dec=-16.0,
        radiant_constellation="Aquarius",
        velocity_km_s=41.0,
        parent_body="Comet 96P/Machholz",
        notes="Broad peak, good for Southern Hemisphere"
    ),
    MeteorShower(
        name="Perseids",
        peak_start=date(2026, 8, 11),
        peak_end=date(2026, 8, 13),
        zhr=100,
        radiant_ra=46.0,
        radiant_dec=58.0,
        radiant_constellation="Perseus",
        velocity_km_s=59.0,
        parent_body="Comet 109P/Swift-Tuttle",
        notes="Most popular shower, warm summer nights"
    ),
    MeteorShower(
        name="Orionids",
        peak_start=date(2026, 10, 20),
        peak_end=date(2026, 10, 22),
        zhr=20,
        radiant_ra=95.0,
        radiant_dec=16.0,
        radiant_constellation="Orion",
        velocity_km_s=66.0,
        parent_body="Comet 1P/Halley",
        notes="Second Halley shower of the year"
    ),
    MeteorShower(
        name="Leonids",
        peak_start=date(2026, 11, 17),
        peak_end=date(2026, 11, 18),
        zhr=15,
        radiant_ra=152.0,
        radiant_dec=22.0,
        radiant_constellation="Leo",
        velocity_km_s=71.0,
        parent_body="Comet 55P/Tempel-Tuttle",
        notes="Famous for historic meteor storms (1833, 1966)"
    ),
    MeteorShower(
        name="Geminids",
        peak_start=date(2026, 12, 13),
        peak_end=date(2026, 12, 14),
        zhr=150,
        radiant_ra=112.0,
        radiant_dec=33.0,
        radiant_constellation="Gemini",
        velocity_km_s=35.0,
        parent_body="Asteroid 3200 Phaethon",
        notes="King of meteor showers, multicolored"
    ),
    MeteorShower(
        name="Ursids",
        peak_start=date(2026, 12, 21),
        peak_end=date(2026, 12, 22),
        zhr=10,
        radiant_ra=217.0,
        radiant_dec=76.0,
        radiant_constellation="Ursa Minor",
        velocity_km_s=33.0,
        parent_body="Comet 8P/Tuttle",
        notes="Winter solstice shower"
    ),
]


class ShowerCalendar:
    """Meteor shower calendar for NIGHTWATCH."""

    def __init__(self, year: int = None):
        self.year = year or datetime.now().year
        self.showers = self._get_showers_for_year(self.year)

    def _get_showers_for_year(self, year: int) -> List[MeteorShower]:
        """Get showers for a given year."""
        # For simplicity, use 2026 dates (adjust in production)
        return METEOR_SHOWERS_2026

    def get_active_showers(self) -> List[MeteorShower]:
        """Get currently active meteor showers."""
        return [s for s in self.showers if s.is_active]

    def get_upcoming_showers(self, days: int = 30) -> List[MeteorShower]:
        """Get showers peaking within the next N days."""
        upcoming = []
        for shower in self.showers:
            days_until = shower.days_until_peak()
            if 0 <= days_until <= days:
                upcoming.append(shower)
        return sorted(upcoming, key=lambda s: s.peak_start)

    def get_shower_by_name(self, name: str) -> Optional[MeteorShower]:
        """Find a shower by name (case-insensitive partial match)."""
        name_lower = name.lower()
        for shower in self.showers:
            if name_lower in shower.name.lower():
                return shower
        return None

    def parse_shower_reference(self, text: str) -> Optional[MeteorShower]:
        """Parse natural language shower reference."""
        text_lower = text.lower()

        # Direct name match
        for shower in self.showers:
            if shower.name.lower() in text_lower:
                return shower

        # Month-based matching
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }

        for month_name, month_num in months.items():
            if month_name in text_lower:
                for shower in self.showers:
                    if shower.peak_start.month == month_num:
                        return shower

        return None


def get_current_shower() -> Optional[MeteorShower]:
    """Get currently active shower, if any."""
    calendar = ShowerCalendar()
    active = calendar.get_active_showers()
    return active[0] if active else None


def get_next_major_shower() -> Optional[MeteorShower]:
    """Get next major shower (ZHR > 50)."""
    calendar = ShowerCalendar()
    upcoming = calendar.get_upcoming_showers(days=365)
    major = [s for s in upcoming if s.zhr >= 50]
    return major[0] if major else None
