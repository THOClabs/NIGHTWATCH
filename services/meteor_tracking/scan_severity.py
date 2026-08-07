"""
NIGHTWATCH Scan Event Severity Classification
Classifies astronomical events by threat level and distance from home.

Used by the hourly scanner to prioritize events and determine
which warrant alerts vs. informational logging.

presa-nightwatch. velmu-sky-severity.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from .fireball_client import Fireball
from .hopi_circles import haversine_miles
from .lexicon_prayers import LexiconFormatter


class EventSeverity(Enum):
    """Event severity classification for scan results."""
    INFO = "info"                # Background monitoring, logged only
    NOTABLE = "notable"          # Worth mentioning in scan report
    SIGNIFICANT = "significant"  # Elevated attention, possible alert
    CRITICAL = "critical"        # Immediate alert required


class ScanCircleZone(Enum):
    """Zone classification based on distance from home base."""
    HOME_BASE = "home-base"           # 0 mi — local conditions
    INNER = "inner"                   # 0-20 mi — immediate vicinity
    MIDDLE = "middle"                 # 20-80 mi — local region
    OUTER = "outer"                   # 80-200 mi — extended region
    HOME_BASES_EXTENDED = "extended"  # 200-500 mi — home base network
    NEW_DAYS = "new-days"             # 500+ mi — global / space


# Default zone boundaries in miles
ZONE_BOUNDARIES = {
    ScanCircleZone.HOME_BASE: 0,
    ScanCircleZone.INNER: 20,
    ScanCircleZone.MIDDLE: 80,
    ScanCircleZone.OUTER: 200,
    ScanCircleZone.HOME_BASES_EXTENDED: 500,
    ScanCircleZone.NEW_DAYS: float('inf'),
}


@dataclass
class SpaceWeatherConditions:
    """Current space weather conditions from NOAA SWPC."""
    kp_index: Optional[float] = None
    storm_level: Optional[str] = None
    solar_flare_class: Optional[str] = None
    solar_flare_region: Optional[str] = None
    cme_watch: bool = False
    aurora_possible: bool = False
    radio_blackout_level: Optional[str] = None
    description: str = ""
    last_updated: Optional[datetime] = None

    @property
    def severity(self) -> EventSeverity:
        """Derive severity from storm level."""
        if not self.storm_level:
            return EventSeverity.INFO
        if "G5" in self.storm_level:
            return EventSeverity.CRITICAL
        if "G3" in self.storm_level or "G4" in self.storm_level:
            return EventSeverity.SIGNIFICANT
        if "G2" in self.storm_level:
            return EventSeverity.NOTABLE
        return EventSeverity.INFO

    def to_lexicon_lines(self) -> list:
        """Generate Lexicon-format lines for space weather."""
        lines = ["sky-conditions:"]
        if self.storm_level:
            lines.append(f"  geomagnetic: {self.storm_level}")
        if self.solar_flare_class:
            lines.append(f"  solar-flare: {self.solar_flare_class}")
            if self.solar_flare_region:
                lines.append(f"  flare-region: {self.solar_flare_region}")
        if self.aurora_possible:
            lines.append("  aurora: possible-at-horizon")
        if self.kp_index is not None:
            lines.append(f"  kp-index: {self.kp_index:.1f}")
        if self.radio_blackout_level:
            lines.append(f"  radio-blackout: {self.radio_blackout_level}")
        if self.cme_watch:
            lines.append("  cme-watch: active")
        return lines


def classify_zone_by_distance(distance_miles: float) -> ScanCircleZone:
    """Classify a distance into a Hopi circle zone."""
    if distance_miles <= 0:
        return ScanCircleZone.HOME_BASE
    if distance_miles <= 20:
        return ScanCircleZone.INNER
    if distance_miles <= 80:
        return ScanCircleZone.MIDDLE
    if distance_miles <= 200:
        return ScanCircleZone.OUTER
    if distance_miles <= 500:
        return ScanCircleZone.HOME_BASES_EXTENDED
    return ScanCircleZone.NEW_DAYS


def classify_fireball_severity(
    fireball: Fireball,
    home_lat: float = 38.9,
    home_lon: float = -117.4,
    bright_threshold: float = -8.0,
    very_bright_threshold: float = -15.0,
) -> EventSeverity:
    """
    Classify fireball severity based on magnitude and proximity.

    Args:
        fireball: The fireball event
        home_lat, home_lon: Home base coordinates
        bright_threshold: Magnitude for SIGNIFICANT (default -8)
        very_bright_threshold: Magnitude for CRITICAL (default -15)

    Returns:
        EventSeverity classification
    """
    mag = fireball.magnitude_estimate

    if mag is not None and mag < very_bright_threshold:
        return EventSeverity.CRITICAL
    if mag is not None and mag < bright_threshold:
        return EventSeverity.SIGNIFICANT

    # Check proximity to home base
    if fireball.latitude is not None and fireball.longitude is not None:
        dist = haversine_miles(home_lat, home_lon,
                               fireball.latitude, fireball.longitude)
        if dist < 200:
            return EventSeverity.NOTABLE

    return EventSeverity.INFO


def classify_neo_severity(
    distance_au: float,
    diameter_m: Optional[float] = None,
    close_threshold_au: float = 0.01,
    very_close_threshold_au: float = 0.003,
) -> EventSeverity:
    """
    Classify near-Earth object severity.

    Args:
        distance_au: Close approach distance in AU
        diameter_m: Estimated diameter in meters
        close_threshold_au: AU threshold for NOTABLE/SIGNIFICANT
        very_close_threshold_au: AU threshold for CRITICAL

    Returns:
        EventSeverity classification
    """
    if distance_au < very_close_threshold_au:
        return EventSeverity.CRITICAL
    if distance_au < close_threshold_au:
        if diameter_m and diameter_m > 50:
            return EventSeverity.SIGNIFICANT
        return EventSeverity.NOTABLE
    return EventSeverity.INFO


def distance_from_home(
    lat: float,
    lon: float,
    home_lat: float = 38.9,
    home_lon: float = -117.4,
) -> float:
    """Calculate distance from home base in miles."""
    return haversine_miles(home_lat, home_lon, lat, lon)
