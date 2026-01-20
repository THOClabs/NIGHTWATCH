"""
NIGHTWATCH Ephemeris Service
Skyfield-based Astronomical Calculations

This module provides ephemeris calculations for:
- Planet positions (Mercury through Neptune, plus Pluto)
- Sun and Moon positions
- Rise/set/transit times
- Altitude/azimuth for any object
- Coordinate transformations (J2000 <-> JNow)
- Twilight calculations

Uses the Skyfield library with JPL DE440 ephemeris data.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, List, Tuple
import math

try:
    from skyfield.api import load, Topos, Star, wgs84
    from skyfield.almanac import find_discrete, risings_and_settings, dark_twilight_day
    from skyfield import almanac
    SKYFIELD_AVAILABLE = True
except ImportError:
    SKYFIELD_AVAILABLE = False
    print("Warning: Skyfield not installed. Run: pip install skyfield")


class CelestialBody(Enum):
    """Solar system bodies available for ephemeris."""
    SUN = "sun"
    MOON = "moon"
    MERCURY = "mercury"
    VENUS = "venus"
    MARS = "mars"
    JUPITER = "jupiter"
    SATURN = "saturn"
    URANUS = "uranus"
    NEPTUNE = "neptune"
    PLUTO = "pluto"


class TwilightPhase(Enum):
    """Twilight phases."""
    DAY = "day"                      # Sun > 0°
    CIVIL = "civil"                  # Sun -6° to 0°
    NAUTICAL = "nautical"            # Sun -12° to -6°
    ASTRONOMICAL = "astronomical"    # Sun -18° to -12°
    NIGHT = "night"                  # Sun < -18°


@dataclass
class Position:
    """Celestial position."""
    ra_hours: float          # Right Ascension (hours, 0-24)
    dec_degrees: float       # Declination (degrees, -90 to +90)
    distance_au: float       # Distance in AU

    # Apparent position (corrected for precession, nutation, aberration)
    ra_apparent: Optional[float] = None
    dec_apparent: Optional[float] = None

    # Proper motion corrected position (Step 211)
    ra_corrected: Optional[float] = None
    dec_corrected: Optional[float] = None
    epoch_corrected: Optional[str] = None  # Epoch of corrected coords

    @property
    def ra_hms(self) -> str:
        """RA in HH:MM:SS format."""
        h = int(self.ra_hours)
        m = int((self.ra_hours - h) * 60)
        s = ((self.ra_hours - h) * 60 - m) * 60
        return f"{h:02d}:{m:02d}:{s:05.2f}"

    @property
    def dec_dms(self) -> str:
        """DEC in sDD:MM:SS format."""
        sign = "+" if self.dec_degrees >= 0 else "-"
        d = abs(self.dec_degrees)
        deg = int(d)
        m = int((d - deg) * 60)
        s = ((d - deg) * 60 - m) * 60
        return f"{sign}{deg:02d}:{m:02d}:{s:05.2f}"


@dataclass
class HorizontalPosition:
    """Altitude/Azimuth position."""
    altitude_degrees: float  # Degrees above horizon (-90 to +90)
    azimuth_degrees: float   # Degrees from North (0-360)

    @property
    def is_visible(self) -> bool:
        """Check if object is above horizon."""
        return self.altitude_degrees > 0

    @property
    def compass_direction(self) -> str:
        """Get compass direction string."""
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                      "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        index = round(self.azimuth_degrees / 22.5) % 16
        return directions[index]


@dataclass
class RiseTransitSet:
    """Rise, transit, and set times for an object."""
    rise_time: Optional[datetime]
    transit_time: Optional[datetime]
    set_time: Optional[datetime]
    rise_azimuth: Optional[float] = None
    transit_altitude: Optional[float] = None
    set_azimuth: Optional[float] = None


@dataclass
class StarData:
    """
    Star data with proper motion for epoch correction (Step 211).

    Proper motion values are typically from star catalogs like Hipparcos
    or Gaia. Units are milliarcseconds per year (mas/yr).

    Example bright stars:
    - Sirius: pmra=-546.05 mas/yr, pmdec=-1223.14 mas/yr
    - Vega: pmra=200.94 mas/yr, pmdec=286.23 mas/yr
    - Polaris: pmra=44.22 mas/yr, pmdec=-11.74 mas/yr
    """
    name: str                           # Star name
    ra_hours: float                     # J2000 RA in hours
    dec_degrees: float                  # J2000 Dec in degrees
    pmra_mas_per_year: float = 0.0      # Proper motion in RA (mas/yr)
    pmdec_mas_per_year: float = 0.0     # Proper motion in Dec (mas/yr)
    parallax_mas: float = 0.0           # Parallax in mas (distance)
    radial_velocity_km_s: float = 0.0   # Radial velocity (km/s)
    epoch: float = 2000.0               # Catalog epoch (J2000 = 2000.0)

    @property
    def distance_pc(self) -> Optional[float]:
        """Distance in parsecs from parallax."""
        if self.parallax_mas > 0:
            return 1000.0 / self.parallax_mas
        return None


@dataclass
class ObserverLocation:
    """Observer's location on Earth."""
    latitude: float       # Degrees
    longitude: float      # Degrees (negative = West)
    elevation_m: float    # Meters above sea level
    name: str = "Observer"

    @classmethod
    def nevada_site(cls) -> "ObserverLocation":
        """Default NIGHTWATCH location in central Nevada."""
        return cls(
            latitude=39.0,
            longitude=-117.0,
            elevation_m=1800,
            name="NIGHTWATCH Nevada"
        )


class EphemerisService:
    """
    Skyfield-based ephemeris service for NIGHTWATCH.

    Provides high-precision astronomical calculations for
    telescope pointing and observing session planning.
    """

    # Ephemeris data directory
    DATA_DIR = Path(__file__).parent / "data"

    # Body name mappings for Skyfield
    BODY_NAMES = {
        CelestialBody.SUN: "sun",
        CelestialBody.MOON: "moon",
        CelestialBody.MERCURY: "mercury barycenter",
        CelestialBody.VENUS: "venus barycenter",
        CelestialBody.MARS: "mars barycenter",
        CelestialBody.JUPITER: "jupiter barycenter",
        CelestialBody.SATURN: "saturn barycenter",
        CelestialBody.URANUS: "uranus barycenter",
        CelestialBody.NEPTUNE: "neptune barycenter",
        CelestialBody.PLUTO: "pluto barycenter",
    }

    def __init__(self, location: Optional[ObserverLocation] = None):
        """
        Initialize ephemeris service.

        Args:
            location: Observer location (defaults to Nevada site)
        """
        self.location = location or ObserverLocation.nevada_site()
        self._ts = None
        self._eph = None
        self._earth = None
        self._observer = None
        self._initialized = False

    def initialize(self):
        """Load ephemeris data (can be slow on first run)."""
        if not SKYFIELD_AVAILABLE:
            raise RuntimeError("Skyfield library not available")

        # Create data directory
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Load timescale
        self._ts = load.timescale()

        # Load ephemeris (downloads if not cached)
        # DE440 is the current JPL ephemeris (1550-2650)
        self._eph = load('de440s.bsp')

        # Get Earth
        self._earth = self._eph['earth']

        # Create observer position
        self._observer = self._earth + wgs84.latlon(
            self.location.latitude,
            self.location.longitude,
            elevation_m=self.location.elevation_m
        )

        self._initialized = True

    def _ensure_initialized(self):
        """Ensure service is initialized."""
        if not self._initialized:
            self.initialize()

    def _get_time(self, dt: Optional[datetime] = None):
        """Get Skyfield time object."""
        if dt is None:
            dt = datetime.now(timezone.utc)
        elif dt.tzinfo is None:
            # Assume UTC if no timezone
            dt = dt.replace(tzinfo=timezone.utc)
        return self._ts.from_datetime(dt)

    def get_body_position(
        self,
        body: CelestialBody,
        when: Optional[datetime] = None
    ) -> Position:
        """
        Get position of a solar system body.

        Args:
            body: Celestial body to locate
            when: Time for calculation (default: now)

        Returns:
            Position with RA/DEC coordinates
        """
        self._ensure_initialized()
        t = self._get_time(when)

        # Get body from ephemeris
        target = self._eph[self.BODY_NAMES[body]]

        # Compute astrometric position from observer
        astrometric = self._observer.at(t).observe(target)

        # Get apparent position (includes aberration, etc.)
        apparent = astrometric.apparent()
        ra_app, dec_app, dist = apparent.radec()

        # Get J2000 position
        ra, dec, _ = astrometric.radec(epoch='J2000')

        return Position(
            ra_hours=ra.hours,
            dec_degrees=dec.degrees,
            distance_au=dist.au,
            ra_apparent=ra_app.hours,
            dec_apparent=dec_app.degrees
        )

    def get_body_altaz(
        self,
        body: CelestialBody,
        when: Optional[datetime] = None
    ) -> HorizontalPosition:
        """
        Get altitude/azimuth of a solar system body.

        Args:
            body: Celestial body to locate
            when: Time for calculation (default: now)

        Returns:
            HorizontalPosition with alt/az
        """
        self._ensure_initialized()
        t = self._get_time(when)

        target = self._eph[self.BODY_NAMES[body]]
        astrometric = self._observer.at(t).observe(target)
        apparent = astrometric.apparent()

        alt, az, _ = apparent.altaz()

        return HorizontalPosition(
            altitude_degrees=alt.degrees,
            azimuth_degrees=az.degrees
        )

    def get_star_altaz(
        self,
        ra_hours: float,
        dec_degrees: float,
        when: Optional[datetime] = None
    ) -> HorizontalPosition:
        """
        Get altitude/azimuth for fixed coordinates (star/DSO).

        Args:
            ra_hours: Right Ascension in hours (J2000)
            dec_degrees: Declination in degrees (J2000)
            when: Time for calculation (default: now)

        Returns:
            HorizontalPosition with alt/az
        """
        self._ensure_initialized()
        t = self._get_time(when)

        # Create a "star" at fixed coordinates
        star = Star(ra_hours=ra_hours, dec_degrees=dec_degrees)

        astrometric = self._observer.at(t).observe(star)
        apparent = astrometric.apparent()

        alt, az, _ = apparent.altaz()

        return HorizontalPosition(
            altitude_degrees=alt.degrees,
            azimuth_degrees=az.degrees
        )

    def get_sun_altitude(self, when: Optional[datetime] = None) -> float:
        """Get current sun altitude in degrees."""
        pos = self.get_body_altaz(CelestialBody.SUN, when)
        return pos.altitude_degrees

    def get_moon_phase(self, when: Optional[datetime] = None) -> float:
        """
        Get moon phase as illumination percentage.

        Returns:
            Float from 0.0 (new) to 1.0 (full)
        """
        self._ensure_initialized()
        t = self._get_time(when)

        sun = self._eph['sun']
        moon = self._eph['moon']
        earth = self._eph['earth']

        # Calculate phase angle
        e = earth.at(t)
        s = e.observe(sun).apparent()
        m = e.observe(moon).apparent()

        # Elongation angle between sun and moon
        elongation = s.separation_from(m)

        # Phase illumination (simplified)
        phase = (1 - math.cos(elongation.radians)) / 2

        return phase

    def get_twilight_phase(self, when: Optional[datetime] = None) -> TwilightPhase:
        """
        Determine current twilight phase.

        Returns:
            TwilightPhase enum value
        """
        sun_alt = self.get_sun_altitude(when)

        if sun_alt > 0:
            return TwilightPhase.DAY
        elif sun_alt > -6:
            return TwilightPhase.CIVIL
        elif sun_alt > -12:
            return TwilightPhase.NAUTICAL
        elif sun_alt > -18:
            return TwilightPhase.ASTRONOMICAL
        else:
            return TwilightPhase.NIGHT

    def is_astronomical_night(self, when: Optional[datetime] = None) -> bool:
        """Check if it's astronomical night (sun < -18°)."""
        return self.get_twilight_phase(when) == TwilightPhase.NIGHT

    def get_visible_planets(
        self,
        when: Optional[datetime] = None,
        min_altitude: float = 10.0
    ) -> List[Tuple[CelestialBody, HorizontalPosition]]:
        """
        Get list of planets currently above horizon.

        Args:
            when: Time for calculation
            min_altitude: Minimum altitude in degrees

        Returns:
            List of (body, position) tuples, sorted by altitude
        """
        planets = [
            CelestialBody.MERCURY,
            CelestialBody.VENUS,
            CelestialBody.MARS,
            CelestialBody.JUPITER,
            CelestialBody.SATURN,
            CelestialBody.URANUS,
            CelestialBody.NEPTUNE,
        ]

        visible = []
        for planet in planets:
            pos = self.get_body_altaz(planet, when)
            if pos.altitude_degrees >= min_altitude:
                visible.append((planet, pos))

        # Sort by altitude (highest first)
        visible.sort(key=lambda x: x[1].altitude_degrees, reverse=True)
        return visible

    def get_best_planet_tonight(
        self,
        when: Optional[datetime] = None
    ) -> Optional[Tuple[CelestialBody, HorizontalPosition]]:
        """
        Get the best planet for observation tonight.

        Prioritizes Mars for NIGHTWATCH planetary focus.

        Returns:
            Tuple of (body, position) or None
        """
        visible = self.get_visible_planets(when)

        if not visible:
            return None

        # Priority order for NIGHTWATCH (planetary focus)
        priority = [
            CelestialBody.MARS,
            CelestialBody.JUPITER,
            CelestialBody.SATURN,
            CelestialBody.VENUS,
            CelestialBody.MERCURY,
            CelestialBody.URANUS,
            CelestialBody.NEPTUNE,
        ]

        for planet in priority:
            for body, pos in visible:
                if body == planet:
                    return (body, pos)

        return visible[0]  # Fallback to highest

    def j2000_to_jnow(
        self,
        ra_hours: float,
        dec_degrees: float,
        when: Optional[datetime] = None
    ) -> Tuple[float, float]:
        """
        Convert J2000 coordinates to JNow (current epoch).

        Applies precession, nutation, and aberration corrections.

        Args:
            ra_hours: J2000 Right Ascension in hours
            dec_degrees: J2000 Declination in degrees
            when: Target time (default: now)

        Returns:
            Tuple of (ra_hours, dec_degrees) in JNow
        """
        self._ensure_initialized()
        t = self._get_time(when)

        star = Star(ra_hours=ra_hours, dec_degrees=dec_degrees)
        astrometric = self._observer.at(t).observe(star)
        apparent = astrometric.apparent()

        ra, dec, _ = apparent.radec(epoch=t)
        return (ra.hours, dec.degrees)

    def jnow_to_j2000(
        self,
        ra_hours: float,
        dec_degrees: float,
        when: Optional[datetime] = None
    ) -> Tuple[float, float]:
        """
        Convert JNow coordinates to J2000.

        This is an approximation using reverse precession.

        Args:
            ra_hours: JNow Right Ascension in hours
            dec_degrees: JNow Declination in degrees
            when: Source time (default: now)

        Returns:
            Tuple of (ra_hours, dec_degrees) in J2000
        """
        self._ensure_initialized()
        t = self._get_time(when)

        # This is approximate - proper inversion is complex
        # For most telescope work, the difference is small
        star = Star(ra_hours=ra_hours, dec_degrees=dec_degrees, epoch=t)
        astrometric = self._observer.at(t).observe(star)

        ra, dec, _ = astrometric.radec(epoch='J2000')
        return (ra.hours, dec.degrees)

    # =========================================================================
    # PROPER MOTION CORRECTION (Step 211)
    # =========================================================================

    def get_star_position_with_proper_motion(
        self,
        star_data: StarData,
        when: Optional[datetime] = None
    ) -> Position:
        """
        Get star position with proper motion correction (Step 211).

        Applies proper motion, parallax, and radial velocity corrections
        to compute the star's position at the specified time.

        This is critical for high-precision pointing, especially for:
        - Nearby stars with large proper motion
        - Long time differences from catalog epoch
        - Astrometric calibration

        Args:
            star_data: StarData object with proper motion values
            when: Time for calculation (default: now)

        Returns:
            Position with corrected coordinates
        """
        self._ensure_initialized()
        t = self._get_time(when)

        # Create Skyfield Star with proper motion
        star = Star(
            ra_hours=star_data.ra_hours,
            dec_degrees=star_data.dec_degrees,
            ra_mas_per_year=star_data.pmra_mas_per_year,
            dec_mas_per_year=star_data.pmdec_mas_per_year,
            parallax_mas=star_data.parallax_mas if star_data.parallax_mas > 0 else 0.0,
            radial_km_per_s=star_data.radial_velocity_km_s,
        )

        # Observe from our location
        astrometric = self._observer.at(t).observe(star)
        apparent = astrometric.apparent()

        # Get apparent (JNow) position with all corrections
        ra_app, dec_app, dist = apparent.radec()

        # Get J2000 position (useful for comparison)
        ra_j2000, dec_j2000, _ = astrometric.radec(epoch='J2000')

        return Position(
            ra_hours=ra_j2000.hours,
            dec_degrees=dec_j2000.degrees,
            distance_au=dist.au,
            ra_apparent=ra_app.hours,
            dec_apparent=dec_app.degrees,
            ra_corrected=ra_app.hours,
            dec_corrected=dec_app.degrees,
            epoch_corrected=f"J{t.J:.3f}",
        )

    def apply_proper_motion(
        self,
        ra_hours: float,
        dec_degrees: float,
        pmra_mas_per_year: float,
        pmdec_mas_per_year: float,
        from_epoch: float = 2000.0,
        to_epoch: Optional[float] = None,
        when: Optional[datetime] = None
    ) -> Tuple[float, float]:
        """
        Apply proper motion correction to coordinates (Step 211).

        Simple linear proper motion correction for quick calculations
        without full Skyfield observation. For highest precision, use
        get_star_position_with_proper_motion() instead.

        Args:
            ra_hours: Right Ascension in hours
            dec_degrees: Declination in degrees
            pmra_mas_per_year: Proper motion in RA (mas/yr)
            pmdec_mas_per_year: Proper motion in Dec (mas/yr)
            from_epoch: Source epoch (default J2000.0)
            to_epoch: Target epoch (default: current Julian year)
            when: Time for target epoch (used if to_epoch not specified)

        Returns:
            Tuple of (ra_hours, dec_degrees) at target epoch
        """
        self._ensure_initialized()

        # Determine target epoch
        if to_epoch is None:
            t = self._get_time(when)
            to_epoch = t.J  # Julian year

        # Time difference in years
        dt_years = to_epoch - from_epoch

        # Convert proper motion from mas/yr to degrees/yr
        pmra_deg_per_year = pmra_mas_per_year / 3600000.0
        pmdec_deg_per_year = pmdec_mas_per_year / 3600000.0

        # Apply correction
        # Note: RA proper motion must be corrected for declination
        cos_dec = math.cos(math.radians(dec_degrees))
        if cos_dec > 0.001:  # Avoid division by near-zero at poles
            ra_correction_deg = (pmra_deg_per_year / cos_dec) * dt_years
        else:
            ra_correction_deg = 0.0

        dec_correction_deg = pmdec_deg_per_year * dt_years

        # Apply corrections
        new_ra_hours = ra_hours + (ra_correction_deg / 15.0)  # degrees to hours
        new_dec_degrees = dec_degrees + dec_correction_deg

        # Normalize RA to 0-24 range
        new_ra_hours = new_ra_hours % 24.0

        # Clamp Dec to -90 to +90
        new_dec_degrees = max(-90.0, min(90.0, new_dec_degrees))

        return (new_ra_hours, new_dec_degrees)

    def get_proper_motion_displacement(
        self,
        pmra_mas_per_year: float,
        pmdec_mas_per_year: float,
        years: float
    ) -> Tuple[float, float]:
        """
        Calculate total proper motion displacement (Step 211).

        Useful for understanding how much a star has moved
        from its catalog position.

        Args:
            pmra_mas_per_year: Proper motion in RA (mas/yr)
            pmdec_mas_per_year: Proper motion in Dec (mas/yr)
            years: Time span in years

        Returns:
            Tuple of (ra_displacement_arcsec, dec_displacement_arcsec)
        """
        # Convert mas to arcsec
        ra_displacement = (pmra_mas_per_year * years) / 1000.0
        dec_displacement = (pmdec_mas_per_year * years) / 1000.0

        return (ra_displacement, dec_displacement)

    def calculate_total_proper_motion(
        self,
        pmra_mas_per_year: float,
        pmdec_mas_per_year: float
    ) -> float:
        """
        Calculate total proper motion magnitude (Step 211).

        Args:
            pmra_mas_per_year: Proper motion in RA (mas/yr)
            pmdec_mas_per_year: Proper motion in Dec (mas/yr)

        Returns:
            Total proper motion in mas/yr
        """
        return math.sqrt(pmra_mas_per_year**2 + pmdec_mas_per_year**2)

    def get_star_altaz_with_proper_motion(
        self,
        star_data: StarData,
        when: Optional[datetime] = None
    ) -> HorizontalPosition:
        """
        Get altitude/azimuth for a star with proper motion (Step 211).

        Args:
            star_data: StarData object with proper motion values
            when: Time for calculation (default: now)

        Returns:
            HorizontalPosition with alt/az
        """
        self._ensure_initialized()
        t = self._get_time(when)

        # Create Star with proper motion
        star = Star(
            ra_hours=star_data.ra_hours,
            dec_degrees=star_data.dec_degrees,
            ra_mas_per_year=star_data.pmra_mas_per_year,
            dec_mas_per_year=star_data.pmdec_mas_per_year,
            parallax_mas=star_data.parallax_mas if star_data.parallax_mas > 0 else 0.0,
            radial_km_per_s=star_data.radial_velocity_km_s,
        )

        astrometric = self._observer.at(t).observe(star)
        apparent = astrometric.apparent()

        alt, az, _ = apparent.altaz()

        return HorizontalPosition(
            altitude_degrees=alt.degrees,
            azimuth_degrees=az.degrees
        )

    def format_planet_info(self, body: CelestialBody, when: Optional[datetime] = None) -> str:
        """
        Get formatted info string for voice output.

        Args:
            body: Planet to describe
            when: Time for calculation

        Returns:
            Human-readable description
        """
        pos = self.get_body_position(body, when)
        altaz = self.get_body_altaz(body, when)

        name = body.value.capitalize()

        if altaz.is_visible:
            return (
                f"{name} is currently at {altaz.altitude_degrees:.1f} degrees altitude, "
                f"in the {altaz.compass_direction}. "
                f"Right Ascension {pos.ra_hms}, Declination {pos.dec_dms}."
            )
        else:
            return f"{name} is currently below the horizon at {altaz.altitude_degrees:.1f} degrees."


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_default_service: Optional[EphemerisService] = None


def get_service(location: Optional[ObserverLocation] = None) -> EphemerisService:
    """Get or create default ephemeris service."""
    global _default_service
    if _default_service is None:
        _default_service = EphemerisService(location)
        _default_service.initialize()
    return _default_service


def planet_position(body: str) -> Optional[Position]:
    """Quick lookup of planet position by name."""
    try:
        body_enum = CelestialBody(body.lower())
        return get_service().get_body_position(body_enum)
    except (ValueError, KeyError):
        return None


def is_dark() -> bool:
    """Check if it's astronomical night."""
    return get_service().is_astronomical_night()


def sun_altitude() -> float:
    """Get current sun altitude."""
    return get_service().get_sun_altitude()


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    print("NIGHTWATCH Ephemeris Service Test\n")

    if not SKYFIELD_AVAILABLE:
        print("Skyfield not installed. Install with: pip install skyfield")
        exit(1)

    service = EphemerisService()
    print("Initializing (may download ephemeris data)...")
    service.initialize()
    print(f"Location: {service.location.name}")
    print(f"  Lat: {service.location.latitude}°, Lon: {service.location.longitude}°")
    print()

    # Current conditions
    twilight = service.get_twilight_phase()
    sun_alt = service.get_sun_altitude()
    moon_phase = service.get_moon_phase()

    print(f"Current Conditions:")
    print(f"  Twilight: {twilight.value}")
    print(f"  Sun altitude: {sun_alt:.1f}°")
    print(f"  Moon phase: {moon_phase*100:.0f}% illuminated")
    print()

    # Planet positions
    print("Planet Positions:")
    for body in [CelestialBody.MARS, CelestialBody.JUPITER, CelestialBody.SATURN]:
        pos = service.get_body_position(body)
        altaz = service.get_body_altaz(body)
        status = "visible" if altaz.is_visible else "below horizon"
        print(f"  {body.value.capitalize():10} RA {pos.ra_hms}  DEC {pos.dec_dms}  Alt {altaz.altitude_degrees:+6.1f}° ({status})")

    print()

    # Visible planets
    visible = service.get_visible_planets()
    if visible:
        print("Visible Planets (>10° altitude):")
        for body, pos in visible:
            print(f"  {body.value.capitalize()}: {pos.altitude_degrees:.1f}° alt, {pos.compass_direction}")
    else:
        print("No planets currently visible above 10°")

    print()

    # Best planet
    best = service.get_best_planet_tonight()
    if best:
        body, pos = best
        print(f"Best planet for tonight: {body.value.capitalize()}")
        print(service.format_planet_info(body))
