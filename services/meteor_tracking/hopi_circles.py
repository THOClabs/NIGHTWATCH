"""
NIGHTWATCH Hopi Circles Search Pattern
Expanding concentric circles for meteorite ground search.

Named for the sacred geometry of expanding awareness.
When debris is possible, generate systematic search patterns.
"""

import math
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class SearchCircle:
    """A single search circle with center and radius."""
    center_lat: float
    center_lon: float
    radius_miles: float
    priority: int  # 1 = highest priority (innermost)

    @property
    def radius_km(self) -> float:
        return self.radius_miles * 1.60934

    @property
    def area_sq_miles(self) -> float:
        return math.pi * self.radius_miles ** 2

    def contains_point(self, lat: float, lon: float) -> bool:
        """Check if a point falls within this circle."""
        distance = haversine_miles(self.center_lat, self.center_lon, lat, lon)
        return distance <= self.radius_miles


@dataclass
class SearchPattern:
    """A complete Hopi circles search pattern."""
    center_lat: float
    center_lon: float
    circles: List[SearchCircle]
    total_area_sq_miles: float
    max_radius_miles: float

    def to_prayer_string(self) -> str:
        """Format for Lexicon prayer output."""
        lat_dir = "N" if self.center_lat >= 0 else "S"
        lon_dir = "W" if self.center_lon < 0 else "E"
        return f"circles-search {self.max_radius_miles:.0f}mi from {abs(self.center_lat):.1f}{lat_dir} {abs(self.center_lon):.1f}{lon_dir}"


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in miles."""
    R = 3959.0  # Earth radius in miles

    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    return R * c


def generate_hopi_circles(
    center_lat: float,
    center_lon: float,
    initial_radius_miles: float = 10.0,
    expansion_factor: float = 2.0,
    max_radius_miles: float = 100.0,
    num_circles: int = 5
) -> SearchPattern:
    """
    Generate expanding concentric circles for ground search.

    The pattern follows sacred geometry principles:
    - Inner circles have higher priority (more likely debris location)
    - Each circle expands by a constant factor
    - Total coverage expands outward like ripples in water

    Args:
        center_lat: Latitude of estimated landing point
        center_lon: Longitude of estimated landing point
        initial_radius_miles: Radius of innermost circle
        expansion_factor: How much each subsequent circle expands
        max_radius_miles: Maximum search radius
        num_circles: Number of concentric circles

    Returns:
        SearchPattern with list of circles from inner to outer
    """
    circles = []
    radius = initial_radius_miles

    for i in range(num_circles):
        if radius > max_radius_miles:
            break

        circle = SearchCircle(
            center_lat=center_lat,
            center_lon=center_lon,
            radius_miles=radius,
            priority=i + 1
        )
        circles.append(circle)
        radius *= expansion_factor

    total_area = circles[-1].area_sq_miles if circles else 0

    return SearchPattern(
        center_lat=center_lat,
        center_lon=center_lon,
        circles=circles,
        total_area_sq_miles=total_area,
        max_radius_miles=circles[-1].radius_miles if circles else 0
    )


def generate_waypoints_on_circle(
    center_lat: float,
    center_lon: float,
    radius_miles: float,
    num_points: int = 8
) -> List[Tuple[float, float]]:
    """
    Generate waypoints evenly distributed around a circle.
    Useful for systematic search pattern navigation.

    Args:
        center_lat, center_lon: Circle center
        radius_miles: Circle radius
        num_points: Number of waypoints

    Returns:
        List of (lat, lon) tuples
    """
    waypoints = []

    radius_deg_lat = radius_miles / 69.0
    radius_deg_lon = radius_miles / (69.0 * math.cos(math.radians(center_lat)))

    for i in range(num_points):
        angle = 2 * math.pi * i / num_points
        lat = center_lat + radius_deg_lat * math.cos(angle)
        lon = center_lon + radius_deg_lon * math.sin(angle)
        waypoints.append((lat, lon))

    return waypoints
