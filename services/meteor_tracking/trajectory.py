"""
NIGHTWATCH Fireball Trajectory Calculator
Vector tracing, entry angles, and debris field prediction.
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Vector:
    """A 3D vector for trajectory calculations."""
    x: float
    y: float
    z: float

    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self) -> 'Vector':
        mag = self.magnitude()
        if mag == 0:
            return Vector(0, 0, 0)
        return Vector(self.x/mag, self.y/mag, self.z/mag)

    def to_compass(self) -> str:
        """Convert to compass direction (N, NE, E, etc.)."""
        angle = math.degrees(math.atan2(self.x, self.y))
        if angle < 0:
            angle += 360

        directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        idx = int((angle + 22.5) / 45) % 8
        return directions[idx]


@dataclass
class TrajectoryResult:
    """Result of trajectory calculation."""
    entry_direction: str       # Compass direction fireball came from
    travel_direction: str      # Compass direction fireball traveled toward
    entry_angle_deg: float     # Angle from horizontal (90 = straight down)
    velocity_km_s: float       # Entry velocity
    last_seen_lat: Optional[float] = None
    last_seen_lon: Optional[float] = None
    debris_field_center: Optional[Tuple[float, float]] = None
    debris_field_radius_km: Optional[float] = None

    @property
    def vector_trace_str(self) -> str:
        """Format for Lexicon prayer output."""
        return f"{self.entry_direction} to {self.travel_direction}, {self.entry_angle_deg:.0f} entry"


def calculate_trajectory(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    start_alt_km: Optional[float] = None,
    end_alt_km: Optional[float] = None,
    velocity_km_s: Optional[float] = None
) -> TrajectoryResult:
    """
    Calculate fireball trajectory from observed points.

    Args:
        start_lat, start_lon: First observed position
        end_lat, end_lon: Last observed position
        start_alt_km: Altitude at first observation
        end_alt_km: Altitude at last observation
        velocity_km_s: Observed velocity

    Returns:
        TrajectoryResult with direction, angle, and potential debris field
    """
    # Calculate horizontal displacement (flat-earth approximation for small distances)
    km_per_deg_lat = 111.0
    km_per_deg_lon = 111.0 * math.cos(math.radians((start_lat + end_lat) / 2))

    delta_lat = end_lat - start_lat
    delta_lon = end_lon - start_lon

    delta_y = delta_lat * km_per_deg_lat  # North-South
    delta_x = delta_lon * km_per_deg_lon  # East-West

    # Altitude change
    delta_z = 0.0
    if start_alt_km is not None and end_alt_km is not None:
        delta_z = end_alt_km - start_alt_km

    # Trajectory vectors
    horizontal = Vector(delta_x, delta_y, 0)

    # Entry direction (where it came from)
    entry_compass = Vector(-delta_x, -delta_y, 0).normalize().to_compass() if horizontal.magnitude() > 0 else "unknown"

    # Travel direction (where it was going)
    travel_compass = horizontal.normalize().to_compass() if horizontal.magnitude() > 0 else "unknown"

    # Entry angle (from horizontal, 90 = straight down)
    horizontal_dist = horizontal.magnitude()
    if horizontal_dist > 0 and delta_z != 0:
        entry_angle = math.degrees(math.atan(abs(delta_z) / horizontal_dist))
    else:
        entry_angle = 45.0  # Default assumption

    # Estimate debris field if low terminal altitude
    debris_center = None
    debris_radius = None

    if end_alt_km is not None and end_alt_km < 25:
        # Fireball survived to low altitude - debris possible
        if entry_angle > 10 and horizontal_dist > 0:
            # Project forward from last seen point
            ground_dist_km = end_alt_km / math.tan(math.radians(entry_angle))
            extend_factor = ground_dist_km / horizontal_dist if horizontal_dist > 0 else 1

            debris_lat = end_lat + (delta_lat * extend_factor * 0.5)
            debris_lon = end_lon + (delta_lon * extend_factor * 0.5)
            debris_center = (debris_lat, debris_lon)

            # Debris scatter depends on velocity
            base_radius = 5.0
            if velocity_km_s:
                debris_radius = base_radius * (velocity_km_s / 20.0)
            else:
                debris_radius = base_radius

    return TrajectoryResult(
        entry_direction=entry_compass,
        travel_direction=travel_compass,
        entry_angle_deg=entry_angle,
        velocity_km_s=velocity_km_s or 20.0,
        last_seen_lat=end_lat,
        last_seen_lon=end_lon,
        debris_field_center=debris_center,
        debris_field_radius_km=debris_radius
    )


def estimate_trajectory_from_single_point(
    lat: float,
    lon: float,
    velocity_km_s: Optional[float] = None
) -> TrajectoryResult:
    """Estimate trajectory when only one point is known."""
    return TrajectoryResult(
        entry_direction="unknown",
        travel_direction="unknown",
        entry_angle_deg=45.0,
        velocity_km_s=velocity_km_s or 20.0,
        last_seen_lat=lat,
        last_seen_lon=lon,
        debris_field_center=None,
        debris_field_radius_km=None
    )


def is_visible_from(
    observer_lat: float,
    observer_lon: float,
    event_lat: float,
    event_lon: float,
    event_alt_km: float = 80.0,
    min_elevation_deg: float = 10.0
) -> bool:
    """
    Check if a fireball at given position would be visible from observer location.

    Args:
        observer_lat, observer_lon: Observer position
        event_lat, event_lon: Fireball position
        event_alt_km: Altitude of fireball
        min_elevation_deg: Minimum elevation above horizon to be visible

    Returns:
        True if fireball would be visible
    """
    R_EARTH = 6371.0  # km

    lat1, lon1 = math.radians(observer_lat), math.radians(observer_lon)
    lat2, lon2 = math.radians(event_lat), math.radians(event_lon)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    distance_km = R_EARTH * c

    if distance_km < 1:
        return True

    elevation = math.degrees(math.atan(event_alt_km / distance_km))
    return elevation >= min_elevation_deg


def get_visibility_radius_km(altitude_km: float, min_elevation_deg: float = 10.0) -> float:
    """Calculate how far away a fireball at given altitude can be seen."""
    return altitude_km / math.tan(math.radians(min_elevation_deg))
