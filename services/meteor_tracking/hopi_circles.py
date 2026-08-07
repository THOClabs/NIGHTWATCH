"""
NIGHTWATCH Hopi Circles Search Pattern
Expanding concentric circles for meteorite ground search.

Named for the sacred geometry of expanding awareness.
When debris is possible, generate systematic search patterns.

Pattern flow: starting coords -> hopi circles -> home bases -> new days,
marking things along the outward going circles.
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class Waypoint:
    """A single search waypoint with metadata."""
    lat: float
    lon: float
    circle_index: int  # Which circle this waypoint belongs to (0 = center)
    waypoint_index: int  # Position within the circle
    label: str = ""  # Human-readable label

    @property
    def coordinates_str(self) -> str:
        lat_dir = "N" if self.lat >= 0 else "S"
        lon_dir = "W" if self.lon < 0 else "E"
        return f"{abs(self.lat):.4f}{lat_dir} {abs(self.lon):.4f}{lon_dir}"


@dataclass
class SearchRoute:
    """A connected search route through waypoints across circles."""
    waypoints: List[Waypoint]
    total_distance_miles: float
    num_circles_covered: int
    center_lat: float
    center_lon: float

    def to_prayer_string(self) -> str:
        """Format for Lexicon prayer output."""
        lat_dir = "N" if self.center_lat >= 0 else "S"
        lon_dir = "W" if self.center_lon < 0 else "E"
        center = f"{abs(self.center_lat):.1f}{lat_dir} {abs(self.center_lon):.1f}{lon_dir}"
        return (
            f"spiral-route {len(self.waypoints)} waypoints, "
            f"{self.total_distance_miles:.1f}mi total, "
            f"{self.num_circles_covered} circles from {center}"
        )

    def segment_distances(self) -> List[float]:
        """Calculate distance between consecutive waypoints."""
        distances = []
        for i in range(1, len(self.waypoints)):
            d = haversine_miles(
                self.waypoints[i-1].lat, self.waypoints[i-1].lon,
                self.waypoints[i].lat, self.waypoints[i].lon
            )
            distances.append(d)
        return distances


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

    def waypoints(self, num_points: int = 8, start_bearing: float = 0.0) -> List[Waypoint]:
        """Generate waypoints evenly distributed around this circle."""
        points = []
        for i in range(num_points):
            bearing = start_bearing + (360.0 * i / num_points)
            lat, lon = destination_point(
                self.center_lat, self.center_lon,
                bearing, self.radius_miles
            )
            points.append(Waypoint(
                lat=lat, lon=lon,
                circle_index=self.priority,
                waypoint_index=i,
                label=f"C{self.priority}-W{i}"
            ))
        return points


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

    def generate_full_waypoints(self, points_per_circle: int = 8) -> List[Waypoint]:
        """Generate waypoints for all circles, starting with center point."""
        all_waypoints = [
            Waypoint(
                lat=self.center_lat, lon=self.center_lon,
                circle_index=0, waypoint_index=0,
                label="CENTER"
            )
        ]
        for circle in self.circles:
            all_waypoints.extend(circle.waypoints(points_per_circle))
        return all_waypoints

    def generate_spiral_route(self, points_per_circle: int = 8) -> SearchRoute:
        """
        Generate a connected spiral search route through all circles.

        Route pattern: center -> first circle waypoints (clockwise) ->
        step outward -> second circle waypoints (clockwise) -> ...

        Each circle's waypoints are offset by half a step from the previous
        circle, creating a true spiral rather than concentric rings.
        """
        route_waypoints = [
            Waypoint(
                lat=self.center_lat, lon=self.center_lon,
                circle_index=0, waypoint_index=0,
                label="CENTER-START"
            )
        ]

        for ci, circle in enumerate(self.circles):
            # Offset each circle's start bearing by half a waypoint step
            # to create spiral interleaving
            offset = (180.0 / points_per_circle) * ci
            circle_wps = circle.waypoints(points_per_circle, start_bearing=offset)
            route_waypoints.extend(circle_wps)

        # Calculate total route distance
        total_dist = 0.0
        for i in range(1, len(route_waypoints)):
            total_dist += haversine_miles(
                route_waypoints[i-1].lat, route_waypoints[i-1].lon,
                route_waypoints[i].lat, route_waypoints[i].lon
            )

        return SearchRoute(
            waypoints=route_waypoints,
            total_distance_miles=total_dist,
            num_circles_covered=len(self.circles),
            center_lat=self.center_lat,
            center_lon=self.center_lon
        )


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in miles."""
    R = 3959.0  # Earth radius in miles

    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    return R * c


def destination_point(
    lat: float, lon: float,
    bearing_deg: float, distance_miles: float
) -> Tuple[float, float]:
    """
    Calculate destination point given start, bearing, and distance.

    Uses the spherical law of cosines for accurate geodesic calculation.

    Args:
        lat, lon: Starting point in degrees
        bearing_deg: Bearing in degrees (0=N, 90=E, 180=S, 270=W)
        distance_miles: Distance in miles

    Returns:
        (lat, lon) tuple of destination point in degrees
    """
    R = 3959.0  # Earth radius in miles

    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    brng = math.radians(bearing_deg)
    d_over_R = distance_miles / R

    lat2 = math.asin(
        math.sin(lat1) * math.cos(d_over_R) +
        math.cos(lat1) * math.sin(d_over_R) * math.cos(brng)
    )
    lon2 = lon1 + math.atan2(
        math.sin(brng) * math.sin(d_over_R) * math.cos(lat1),
        math.cos(d_over_R) - math.sin(lat1) * math.sin(lat2)
    )

    return (math.degrees(lat2), math.degrees(lon2))


def initial_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate initial bearing from point 1 to point 2.

    Returns bearing in degrees (0-360).
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1

    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


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


def generate_spiral_route(
    center_lat: float,
    center_lon: float,
    initial_radius_miles: float = 10.0,
    expansion_factor: float = 2.0,
    max_radius_miles: float = 100.0,
    num_circles: int = 5,
    points_per_circle: int = 8
) -> SearchRoute:
    """
    Generate a connected spiral search route from center outward.

    This is the main entry point for generating ground search navigation.
    Follows the pattern: starting coords -> hopi circles -> outward spiral.

    Args:
        center_lat, center_lon: Starting coordinates (estimated landing point)
        initial_radius_miles: Radius of innermost circle
        expansion_factor: How much each circle expands
        max_radius_miles: Maximum search radius
        num_circles: Number of concentric circles
        points_per_circle: Waypoints per circle

    Returns:
        SearchRoute with connected waypoints and total distance
    """
    pattern = generate_hopi_circles(
        center_lat, center_lon,
        initial_radius_miles, expansion_factor,
        max_radius_miles, num_circles
    )
    return pattern.generate_spiral_route(points_per_circle)
