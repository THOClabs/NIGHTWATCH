"""
NIGHTWATCH Close Approach Data Client
NASA CNEOS Close Approach API for near-Earth object monitoring.

Tracks asteroids and comets approaching Earth, providing early warning
for potential atmospheric entry events. This fills the gap between
fireball detection (post-entry) and close approach awareness (pre-entry).

API Documentation: https://ssd-api.jpl.nasa.gov/doc/cad.html
"""

import aiohttp
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List

logger = logging.getLogger("NIGHTWATCH.MeteorTracking")


class ThreatLevel(Enum):
    """Threat classification for close approaches."""
    ROUTINE = "routine"          # > 10 LD, small object
    NOTABLE = "notable"          # < 10 LD or large object
    SIGNIFICANT = "significant"  # < 5 LD and detectable size
    WATCH = "watch"              # < 2 LD or potentially hazardous
    ALERT = "alert"              # < 1 LD or imminent entry predicted


@dataclass
class CloseApproach:
    """A near-Earth object close approach event."""
    designation: str            # Object designation (e.g., "2024 BX1")
    close_approach_date: datetime  # Date/time of closest approach
    distance_au: float          # Nominal miss distance in AU
    distance_ld: float          # Miss distance in lunar distances
    distance_km: float          # Miss distance in km
    relative_velocity_km_s: float  # Relative velocity at close approach
    absolute_magnitude_h: Optional[float]  # Absolute magnitude (H)
    estimated_diameter_m_min: Optional[float]  # Minimum estimated diameter
    estimated_diameter_m_max: Optional[float]  # Maximum estimated diameter
    is_potentially_hazardous: bool  # PHA flag
    orbit_id: Optional[str]     # Orbit solution ID
    fullname: Optional[str]     # Full object name

    @property
    def threat_level(self) -> ThreatLevel:
        """Classify threat level based on distance and size."""
        if self.distance_ld < 1.0 or self.is_potentially_hazardous:
            return ThreatLevel.ALERT
        if self.distance_ld < 2.0:
            return ThreatLevel.WATCH
        if self.distance_ld < 5.0 and self.estimated_diameter_m_max and self.estimated_diameter_m_max > 10:
            return ThreatLevel.SIGNIFICANT
        if self.distance_ld < 10.0 or (self.estimated_diameter_m_max and self.estimated_diameter_m_max > 50):
            return ThreatLevel.NOTABLE
        return ThreatLevel.ROUTINE

    @property
    def estimated_diameter_str(self) -> str:
        """Format diameter range as string."""
        if self.estimated_diameter_m_min is not None and self.estimated_diameter_m_max is not None:
            if self.estimated_diameter_m_max < 1:
                return f"{self.estimated_diameter_m_min*100:.0f}-{self.estimated_diameter_m_max*100:.0f} cm"
            if self.estimated_diameter_m_max < 1000:
                return f"{self.estimated_diameter_m_min:.0f}-{self.estimated_diameter_m_max:.0f} m"
            return f"{self.estimated_diameter_m_min/1000:.1f}-{self.estimated_diameter_m_max/1000:.1f} km"
        return "unknown"

    @property
    def approach_id(self) -> str:
        """Generate unique ID for this approach."""
        date_str = self.close_approach_date.strftime('%Y%m%d')
        return f"cad_{self.designation.replace(' ', '_')}_{date_str}"

    @property
    def lexicon_str(self) -> str:
        """Format for Lexicon prayer output."""
        return (
            f"{self.designation} approach {self.distance_ld:.1f}LD "
            f"at {self.relative_velocity_km_s:.1f}km/s "
            f"({self.threat_level.value})"
        )

    def hours_until_approach(self) -> float:
        """Hours until closest approach (negative if past)."""
        delta = self.close_approach_date - datetime.utcnow()
        return delta.total_seconds() / 3600


def estimate_diameter_from_h(h_mag: float) -> tuple[float, float]:
    """
    Estimate asteroid diameter range from absolute magnitude (H).

    Uses the standard relation: D = 1329 / sqrt(albedo) * 10^(-H/5)
    Assumes albedo range of 0.05 (dark) to 0.25 (bright).

    Args:
        h_mag: Absolute magnitude (H)

    Returns:
        (min_diameter_m, max_diameter_m) tuple
    """
    # D(km) = 1329 / sqrt(albedo) * 10^(-H/5)
    d_bright_km = 1329.0 / math.sqrt(0.25) * (10 ** (-h_mag / 5))
    d_dark_km = 1329.0 / math.sqrt(0.05) * (10 ** (-h_mag / 5))
    return d_bright_km * 1000, d_dark_km * 1000  # Convert to meters


class CADClient:
    """
    Async client for NASA CNEOS Close Approach Data API.

    Monitors near-Earth objects making close approaches to Earth.
    This provides the pre-entry awareness that complements the
    CNEOS Fireball API (post-entry detection).

    API: https://ssd-api.jpl.nasa.gov/cad.api
    No API key required. Rate limiting applies.
    """

    BASE_URL = "https://ssd-api.jpl.nasa.gov/cad.api"

    # 1 Lunar Distance in AU
    LD_TO_AU = 0.00257
    AU_TO_KM = 149_597_870.7

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._session = session
        self._owns_session = session is None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={'User-Agent': 'NIGHTWATCH/1.0 (observatory-neo-tracking)'}
            )
        return self._session

    async def close(self):
        if self._owns_session and self._session:
            await self._session.close()
            self._session = None

    async def fetch_close_approaches(
        self,
        date_min: Optional[datetime] = None,
        date_max: Optional[datetime] = None,
        dist_max_au: float = 0.05,
        min_h_mag: Optional[float] = None,
        sort: str = "dist",
        limit: int = 50
    ) -> List[CloseApproach]:
        """
        Fetch close approach data from CNEOS CAD API.

        Args:
            date_min: Start of date range (default: now)
            date_max: End of date range (default: +7 days)
            dist_max_au: Maximum distance in AU (0.05 AU ~ 19.5 LD)
            min_h_mag: Minimum absolute magnitude (filter small objects)
            sort: Sort field ('dist', 'date', 'h')
            limit: Maximum results

        Returns:
            List of CloseApproach objects sorted by distance
        """
        if date_min is None:
            date_min = datetime.utcnow()
        if date_max is None:
            date_max = datetime.utcnow() + timedelta(days=7)

        params = {
            'date-min': date_min.strftime('%Y-%m-%d'),
            'date-max': date_max.strftime('%Y-%m-%d'),
            'dist-max': f'{dist_max_au}',
            'sort': sort,
            'limit': limit,
        }

        if min_h_mag is not None:
            params['h-max'] = str(min_h_mag)

        try:
            session = await self._get_session()
            async with session.get(
                self.BASE_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return self._parse_approaches(data)

        except aiohttp.ClientError as e:
            logger.error(f"CNEOS CAD API error: {e}")
            return []

    async def fetch_today(self) -> List[CloseApproach]:
        """Fetch close approaches for today and tomorrow."""
        now = datetime.utcnow()
        return await self.fetch_close_approaches(
            date_min=now,
            date_max=now + timedelta(days=2),
            dist_max_au=0.05
        )

    async def fetch_watch_level(self, days: int = 7) -> List[CloseApproach]:
        """Fetch approaches at WATCH level or higher within N days."""
        approaches = await self.fetch_close_approaches(
            date_max=datetime.utcnow() + timedelta(days=days),
            dist_max_au=0.013,  # ~5 LD
        )
        return [a for a in approaches if a.threat_level.value in ('watch', 'alert', 'significant')]

    def _parse_approaches(self, data: dict) -> List[CloseApproach]:
        """Parse CAD API response into CloseApproach objects."""
        approaches = []

        if 'data' not in data or 'fields' not in data:
            logger.warning(f"CAD API returned unexpected format: {list(data.keys())}")
            return approaches

        fields = data['fields']
        field_map = {field: idx for idx, field in enumerate(fields)}

        for row in data['data']:
            try:
                approach = self._parse_row(row, field_map)
                if approach:
                    approaches.append(approach)
            except (IndexError, KeyError, ValueError) as e:
                logger.debug(f"Parse error for CAD row: {e}")
                continue

        return approaches

    def _parse_row(self, row: list, field_map: dict) -> Optional[CloseApproach]:
        """Parse a single row from the CAD API response."""
        designation = self._get_field(row, field_map, 'des', '')
        if not designation:
            return None

        # Parse distance
        dist_au = self._parse_float(self._get_field(row, field_map, 'dist'))
        if dist_au is None:
            return None

        dist_ld = dist_au / self.LD_TO_AU
        dist_km = dist_au * self.AU_TO_KM

        # Parse velocity
        v_rel = self._parse_float(self._get_field(row, field_map, 'v_rel'))

        # Parse absolute magnitude and estimate diameter
        h_mag = self._parse_float(self._get_field(row, field_map, 'h'))
        diameter_min, diameter_max = None, None
        if h_mag is not None:
            diameter_min, diameter_max = estimate_diameter_from_h(h_mag)

        # Parse date
        cd_str = self._get_field(row, field_map, 'cd', '')
        close_date = self._parse_cad_datetime(cd_str)

        # Check fullname
        fullname = self._get_field(row, field_map, 'fullname')

        # Determine PHA status from orbit_id or size
        is_pha = False
        if h_mag is not None and h_mag <= 22.0 and dist_au < 0.05:
            is_pha = True  # Conservative: large + close = potentially hazardous

        return CloseApproach(
            designation=designation,
            close_approach_date=close_date,
            distance_au=dist_au,
            distance_ld=dist_ld,
            distance_km=dist_km,
            relative_velocity_km_s=v_rel or 0.0,
            absolute_magnitude_h=h_mag,
            estimated_diameter_m_min=diameter_min,
            estimated_diameter_m_max=diameter_max,
            is_potentially_hazardous=is_pha,
            orbit_id=self._get_field(row, field_map, 'orbit_id'),
            fullname=fullname.strip() if fullname else None
        )

    def _get_field(self, row: list, field_map: dict, field_name: str, default=None):
        """Safely get a field value from a row."""
        idx = field_map.get(field_name)
        if idx is not None and idx < len(row):
            return row[idx]
        return default

    def _parse_float(self, value) -> Optional[float]:
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _parse_cad_datetime(self, date_str: str) -> datetime:
        """Parse CAD API datetime format (YYYY-Mon-DD HH:MM or variants)."""
        formats = [
            '%Y-%b-%d %H:%M',   # 2026-Mar-21 14:30
            '%Y-%m-%d %H:%M',   # 2026-03-21 14:30
            '%Y-%b-%d',         # 2026-Mar-21
            '%Y-%m-%d',         # 2026-03-21
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        logger.debug(f"Could not parse CAD date: {date_str}")
        return datetime.utcnow()


def generate_approach_prayer(approaches: List[CloseApproach]) -> str:
    """
    Generate a Lexicon-style report for close approaches.

    nightwatch-approach-scan.
    """
    lines = ["nightwatch-approach-scan."]
    lines.append(f"varek: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
    lines.append("")

    if not approaches:
        lines.append("neo-clear: no significant approaches")
        lines.append("")
        lines.append("velmu-sky-quiet.")
        return "\n".join(lines)

    # Group by threat level
    for level in (ThreatLevel.ALERT, ThreatLevel.WATCH, ThreatLevel.SIGNIFICANT, ThreatLevel.NOTABLE):
        level_approaches = [a for a in approaches if a.threat_level == level]
        if not level_approaches:
            continue

        lines.append(f"--- {level.value.upper()} ---")
        for a in level_approaches:
            hours = a.hours_until_approach()
            time_str = f"in {hours:.0f}h" if hours > 0 else f"{abs(hours):.0f}h ago"
            lines.append(f"  {a.designation}: {a.distance_ld:.1f} LD, "
                         f"{a.relative_velocity_km_s:.1f} km/s, "
                         f"~{a.estimated_diameter_str}, "
                         f"{time_str}")
        lines.append("")

    routine_count = sum(1 for a in approaches if a.threat_level == ThreatLevel.ROUTINE)
    if routine_count > 0:
        lines.append(f"routine-passes: {routine_count}")
        lines.append("")

    lines.append("presa-sky-aware.")
    lines.append("do-good-us.")
    return "\n".join(lines)


async def fetch_upcoming_approaches(days: int = 7, dist_max_au: float = 0.05) -> List[CloseApproach]:
    """Convenience function to fetch upcoming close approaches."""
    client = CADClient()
    try:
        return await client.fetch_close_approaches(
            date_max=datetime.utcnow() + timedelta(days=days),
            dist_max_au=dist_max_au
        )
    finally:
        await client.close()
