"""
NIGHTWATCH Hopi Circles & Search Pattern Tests
Comprehensive coverage for geodesic calculations, waypoint generation,
spiral routes, and search pattern geometry.

presa-nightwatch. velmu-test.
"""

import math
import pytest

from services.meteor_tracking.hopi_circles import (
    Waypoint,
    SearchCircle,
    SearchPattern,
    SearchRoute,
    haversine_miles,
    destination_point,
    initial_bearing,
    generate_hopi_circles,
    generate_waypoints_on_circle,
    generate_spiral_route,
)


# =============================================================================
# Geodesic Math Tests
# =============================================================================

class TestHaversineMiles:
    """Test haversine distance calculation."""

    def test_same_point_zero_distance(self):
        assert haversine_miles(39.5, -117.0, 39.5, -117.0) == 0.0

    def test_known_distance_new_york_to_los_angeles(self):
        # NYC to LA is roughly 2,451 miles
        dist = haversine_miles(40.7128, -74.0060, 34.0522, -118.2437)
        assert 2400 < dist < 2500

    def test_symmetry(self):
        d1 = haversine_miles(39.5, -117.0, 40.0, -116.5)
        d2 = haversine_miles(40.0, -116.5, 39.5, -117.0)
        assert abs(d1 - d2) < 1e-10

    def test_short_distance_accuracy(self):
        # 1 degree latitude is about 69 miles
        dist = haversine_miles(39.0, -117.0, 40.0, -117.0)
        assert 68.5 < dist < 69.5

    def test_cross_equator(self):
        dist = haversine_miles(1.0, 0.0, -1.0, 0.0)
        assert 137 < dist < 139  # ~138 miles for 2 degrees

    def test_cross_prime_meridian(self):
        dist = haversine_miles(51.5, -0.5, 51.5, 0.5)
        assert dist > 0
        assert dist < 50  # less than 50 miles for 1 degree at this latitude


class TestDestinationPoint:
    """Test geodesic destination point calculation."""

    def test_north(self):
        lat, lon = destination_point(39.5, -117.0, 0.0, 69.0)
        # ~1 degree north
        assert abs(lat - 40.5) < 0.1
        assert abs(lon - (-117.0)) < 0.01

    def test_south(self):
        lat, lon = destination_point(39.5, -117.0, 180.0, 69.0)
        assert abs(lat - 38.5) < 0.1
        assert abs(lon - (-117.0)) < 0.01

    def test_east(self):
        lat, lon = destination_point(39.5, -117.0, 90.0, 50.0)
        assert lat == pytest.approx(39.5, abs=0.1)
        assert lon > -117.0  # should move east

    def test_west(self):
        lat, lon = destination_point(39.5, -117.0, 270.0, 50.0)
        assert lat == pytest.approx(39.5, abs=0.1)
        assert lon < -117.0  # should move west

    def test_roundtrip_consistency(self):
        """Go somewhere and measure the distance back."""
        start_lat, start_lon = 39.5, -117.0
        dest_lat, dest_lon = destination_point(start_lat, start_lon, 45.0, 100.0)
        roundtrip_dist = haversine_miles(start_lat, start_lon, dest_lat, dest_lon)
        assert abs(roundtrip_dist - 100.0) < 0.5

    def test_zero_distance(self):
        lat, lon = destination_point(39.5, -117.0, 0.0, 0.0)
        assert abs(lat - 39.5) < 1e-10
        assert abs(lon - (-117.0)) < 1e-10


class TestInitialBearing:
    """Test initial bearing calculation."""

    def test_due_north(self):
        bearing = initial_bearing(39.0, -117.0, 40.0, -117.0)
        assert abs(bearing - 0.0) < 1.0

    def test_due_south(self):
        bearing = initial_bearing(40.0, -117.0, 39.0, -117.0)
        assert abs(bearing - 180.0) < 1.0

    def test_due_east(self):
        bearing = initial_bearing(39.5, -118.0, 39.5, -117.0)
        assert abs(bearing - 90.0) < 1.0

    def test_due_west(self):
        bearing = initial_bearing(39.5, -117.0, 39.5, -118.0)
        assert abs(bearing - 270.0) < 1.0

    def test_northeast(self):
        bearing = initial_bearing(39.0, -118.0, 40.0, -117.0)
        assert 0 < bearing < 90

    def test_bearing_range(self):
        """Bearing should always be 0-360."""
        bearing = initial_bearing(39.5, -117.0, 38.0, -118.0)
        assert 0 <= bearing < 360


# =============================================================================
# Waypoint Tests
# =============================================================================

class TestWaypoint:
    """Test Waypoint dataclass."""

    def test_coordinates_str_north_west(self):
        wp = Waypoint(lat=39.5123, lon=-117.0456, circle_index=1, waypoint_index=0)
        assert "39.5123N" in wp.coordinates_str
        assert "117.0456W" in wp.coordinates_str

    def test_coordinates_str_south_east(self):
        wp = Waypoint(lat=-33.8688, lon=151.2093, circle_index=1, waypoint_index=0)
        assert "33.8688S" in wp.coordinates_str
        assert "151.2093E" in wp.coordinates_str

    def test_label(self):
        wp = Waypoint(lat=0, lon=0, circle_index=2, waypoint_index=3, label="C2-W3")
        assert wp.label == "C2-W3"


# =============================================================================
# SearchCircle Tests
# =============================================================================

class TestSearchCircle:
    """Test SearchCircle with waypoint generation."""

    def test_radius_km_conversion(self):
        circle = SearchCircle(39.5, -117.0, 10.0, 1)
        assert abs(circle.radius_km - 16.0934) < 0.001

    def test_area(self):
        circle = SearchCircle(39.5, -117.0, 10.0, 1)
        expected = math.pi * 100
        assert abs(circle.area_sq_miles - expected) < 0.01

    def test_contains_point_inside(self):
        circle = SearchCircle(39.5, -117.0, 10.0, 1)
        # A point ~5 miles away should be inside
        assert circle.contains_point(39.57, -117.0)

    def test_contains_point_outside(self):
        circle = SearchCircle(39.5, -117.0, 10.0, 1)
        # A point ~100 miles away should be outside
        assert not circle.contains_point(40.5, -117.0)

    def test_contains_point_on_boundary(self):
        # 1 degree latitude is ~69.1 miles at this latitude
        circle = SearchCircle(39.5, -117.0, 69.2, 1)
        assert circle.contains_point(40.5, -117.0)

    def test_waypoints_count(self):
        circle = SearchCircle(39.5, -117.0, 10.0, 1)
        wps = circle.waypoints(num_points=8)
        assert len(wps) == 8

    def test_waypoints_distance_from_center(self):
        """All waypoints should be approximately radius_miles from center."""
        circle = SearchCircle(39.5, -117.0, 10.0, 1)
        wps = circle.waypoints(num_points=8)
        for wp in wps:
            dist = haversine_miles(circle.center_lat, circle.center_lon, wp.lat, wp.lon)
            assert abs(dist - 10.0) < 0.5  # within 0.5 miles

    def test_waypoints_labels(self):
        circle = SearchCircle(39.5, -117.0, 10.0, 1)
        wps = circle.waypoints(4)
        assert wps[0].label == "C1-W0"
        assert wps[3].label == "C1-W3"

    def test_waypoints_circle_index(self):
        circle = SearchCircle(39.5, -117.0, 10.0, 3)
        wps = circle.waypoints(4)
        for wp in wps:
            assert wp.circle_index == 3

    def test_waypoints_even_spacing(self):
        """Consecutive waypoints should be roughly equally spaced."""
        circle = SearchCircle(39.5, -117.0, 20.0, 1)
        wps = circle.waypoints(8)
        distances = []
        for i in range(len(wps)):
            j = (i + 1) % len(wps)
            d = haversine_miles(wps[i].lat, wps[i].lon, wps[j].lat, wps[j].lon)
            distances.append(d)
        # All segment distances should be within 10% of average
        avg = sum(distances) / len(distances)
        for d in distances:
            assert abs(d - avg) / avg < 0.1

    def test_waypoints_start_bearing(self):
        """First waypoint with bearing=0 should be roughly due north."""
        circle = SearchCircle(39.5, -117.0, 10.0, 1)
        wps = circle.waypoints(8, start_bearing=0.0)
        # First waypoint should be north of center
        assert wps[0].lat > 39.5
        assert abs(wps[0].lon - (-117.0)) < 0.1


# =============================================================================
# SearchPattern Tests
# =============================================================================

class TestSearchPattern:
    """Test SearchPattern with full waypoint and spiral generation."""

    def test_generate_full_waypoints_includes_center(self):
        pattern = generate_hopi_circles(39.5, -117.0, num_circles=3)
        wps = pattern.generate_full_waypoints(points_per_circle=4)
        # First waypoint should be center
        assert wps[0].label == "CENTER"
        assert wps[0].lat == 39.5
        assert wps[0].lon == -117.0
        assert wps[0].circle_index == 0

    def test_generate_full_waypoints_count(self):
        pattern = generate_hopi_circles(39.5, -117.0, num_circles=3)
        wps = pattern.generate_full_waypoints(points_per_circle=8)
        # 1 center + 3 circles * 8 points = 25
        assert len(wps) == 25

    def test_generate_spiral_route(self):
        pattern = generate_hopi_circles(39.5, -117.0, num_circles=3)
        route = pattern.generate_spiral_route(points_per_circle=8)

        assert isinstance(route, SearchRoute)
        assert route.num_circles_covered == 3
        assert route.total_distance_miles > 0
        assert len(route.waypoints) == 25  # 1 + 3*8

    def test_spiral_route_starts_at_center(self):
        pattern = generate_hopi_circles(39.5, -117.0, num_circles=2)
        route = pattern.generate_spiral_route(4)
        assert route.waypoints[0].label == "CENTER-START"
        assert route.waypoints[0].lat == 39.5

    def test_spiral_route_prayer_string(self):
        pattern = generate_hopi_circles(39.5, -117.0, num_circles=3)
        route = pattern.generate_spiral_route(8)
        prayer = route.to_prayer_string()
        assert "spiral-route" in prayer
        assert "25 waypoints" in prayer
        assert "3 circles" in prayer
        assert "39.5N" in prayer

    def test_spiral_route_segment_distances(self):
        pattern = generate_hopi_circles(39.5, -117.0, num_circles=2, initial_radius_miles=5.0)
        route = pattern.generate_spiral_route(4)
        segments = route.segment_distances()
        assert len(segments) == len(route.waypoints) - 1
        assert all(d > 0 for d in segments)

    def test_spiral_route_outward_progression(self):
        """Waypoints should generally move outward from center."""
        pattern = generate_hopi_circles(39.5, -117.0, num_circles=3, initial_radius_miles=10.0)
        route = pattern.generate_spiral_route(8)

        # Average distance from center should increase for each circle's waypoints
        circle_avg_distances = []
        for ci in range(3):
            circle_wps = [w for w in route.waypoints if w.circle_index == ci + 1]
            avg_dist = sum(
                haversine_miles(39.5, -117.0, w.lat, w.lon) for w in circle_wps
            ) / len(circle_wps)
            circle_avg_distances.append(avg_dist)

        # Each circle should be farther out
        for i in range(1, len(circle_avg_distances)):
            assert circle_avg_distances[i] > circle_avg_distances[i-1]


# =============================================================================
# SearchRoute Tests
# =============================================================================

class TestSearchRoute:
    """Test SearchRoute dataclass."""

    def test_prayer_string_format(self):
        route = SearchRoute(
            waypoints=[
                Waypoint(39.5, -117.0, 0, 0, "CENTER"),
                Waypoint(39.6, -117.0, 1, 0, "C1-W0"),
            ],
            total_distance_miles=6.9,
            num_circles_covered=1,
            center_lat=39.5,
            center_lon=-117.0
        )
        s = route.to_prayer_string()
        assert "2 waypoints" in s
        assert "6.9mi total" in s
        assert "1 circles" in s

    def test_segment_distances_consistency(self):
        """Sum of segments should equal total distance (for routes built by spiral)."""
        pattern = generate_hopi_circles(39.5, -117.0, num_circles=2, initial_radius_miles=5.0)
        route = pattern.generate_spiral_route(4)
        segment_sum = sum(route.segment_distances())
        assert abs(segment_sum - route.total_distance_miles) < 0.01


# =============================================================================
# generate_waypoints_on_circle (legacy function) Tests
# =============================================================================

class TestGenerateWaypointsOnCircle:
    """Test the legacy waypoint generation function."""

    def test_returns_correct_count(self):
        wps = generate_waypoints_on_circle(39.5, -117.0, 10.0, 8)
        assert len(wps) == 8

    def test_returns_tuples(self):
        wps = generate_waypoints_on_circle(39.5, -117.0, 10.0, 4)
        for wp in wps:
            assert isinstance(wp, tuple)
            assert len(wp) == 2

    def test_first_waypoint_is_north(self):
        """First waypoint at angle=0 should be due north."""
        wps = generate_waypoints_on_circle(39.5, -117.0, 10.0, 4)
        lat, lon = wps[0]
        assert lat > 39.5  # north
        assert abs(lon - (-117.0)) < 0.01  # same longitude

    def test_waypoints_near_expected_radius(self):
        """All waypoints should be approximately at the specified radius."""
        wps = generate_waypoints_on_circle(39.5, -117.0, 10.0, 8)
        for lat, lon in wps:
            dist = haversine_miles(39.5, -117.0, lat, lon)
            assert abs(dist - 10.0) < 1.0  # within 1 mile

    def test_single_waypoint(self):
        wps = generate_waypoints_on_circle(39.5, -117.0, 10.0, 1)
        assert len(wps) == 1


# =============================================================================
# generate_spiral_route (top-level function) Tests
# =============================================================================

class TestGenerateSpiralRoute:
    """Test the top-level spiral route generation."""

    def test_basic_generation(self):
        route = generate_spiral_route(39.5, -117.0, num_circles=3, points_per_circle=4)
        assert isinstance(route, SearchRoute)
        assert len(route.waypoints) == 1 + 3 * 4

    def test_single_circle(self):
        route = generate_spiral_route(
            39.5, -117.0,
            initial_radius_miles=5.0,
            num_circles=1,
            points_per_circle=4
        )
        assert route.num_circles_covered == 1
        assert len(route.waypoints) == 5  # center + 4

    def test_max_radius_limits_circles(self):
        route = generate_spiral_route(
            39.5, -117.0,
            initial_radius_miles=10.0,
            expansion_factor=2.0,
            max_radius_miles=25.0,
            num_circles=10,
            points_per_circle=4
        )
        # 10, 20 fit; 40 exceeds max_radius_miles=25
        assert route.num_circles_covered == 2

    def test_different_center_coordinates(self):
        """Test with southern hemisphere coordinates."""
        route = generate_spiral_route(-33.8688, 151.2093, num_circles=2, points_per_circle=4)
        assert route.center_lat == -33.8688
        assert route.center_lon == 151.2093
        assert route.total_distance_miles > 0


# =============================================================================
# Integration: Full Flow from Trajectory to Spiral Route
# =============================================================================

class TestHopiCirclesIntegration:
    """Integration tests simulating the full search pattern workflow."""

    def test_chelyabinsk_style_event(self):
        """
        Simulate a Chelyabinsk-style event:
        - Entry from northeast at shallow angle
        - Terminal point around 54.8N, 61.1E
        - Generate search pattern from estimated debris field
        """
        from services.meteor_tracking.trajectory import calculate_trajectory

        trajectory = calculate_trajectory(
            start_lat=55.5, start_lon=60.0,
            end_lat=54.8, end_lon=61.1,
            start_alt_km=95, end_alt_km=20,
            velocity_km_s=19.0
        )

        # Debris field should exist (low terminal altitude)
        assert trajectory.debris_field_center is not None
        debris_lat, debris_lon = trajectory.debris_field_center

        # Generate hopi circles around debris field
        pattern = generate_hopi_circles(
            debris_lat, debris_lon,
            initial_radius_miles=5,
            expansion_factor=2.0,
            max_radius_miles=40,
            num_circles=4
        )
        assert len(pattern.circles) == 4

        # Generate spiral search route
        route = pattern.generate_spiral_route(points_per_circle=8)
        assert route.total_distance_miles > 0
        assert route.waypoints[0].label == "CENTER-START"

        # Verify route covers increasing distances
        center_wp = route.waypoints[0]
        for ci in range(1, 4):
            circle_wps = [w for w in route.waypoints if w.circle_index == ci]
            for wp in circle_wps:
                dist = haversine_miles(center_wp.lat, center_wp.lon, wp.lat, wp.lon)
                expected_radius = 5 * (2.0 ** (ci - 1))
                assert abs(dist - expected_radius) < 1.0

    def test_nevada_site_meteor_search(self):
        """
        Test from NIGHTWATCH's home base in Nevada.
        Starting coords -> hopi circles -> marking outward.
        """
        # Nevada property coordinates
        home_lat, home_lon = 39.5, -117.0

        # Hypothetical fireball terminal point 30 miles NE
        debris_lat, debris_lon = destination_point(home_lat, home_lon, 45.0, 30.0)

        # Generate search from debris point
        pattern = generate_hopi_circles(
            debris_lat, debris_lon,
            initial_radius_miles=2,
            expansion_factor=1.5,
            max_radius_miles=20,
            num_circles=5
        )

        route = pattern.generate_spiral_route(points_per_circle=6)

        # Verify the route stays reasonable
        assert route.total_distance_miles > 0
        assert route.total_distance_miles < 500  # shouldn't be absurdly long

        # Verify all waypoints are on Earth
        for wp in route.waypoints:
            assert -90 <= wp.lat <= 90
            assert -180 <= wp.lon <= 180

        # Verify prayer output works
        prayer = route.to_prayer_string()
        assert "spiral-route" in prayer
        assert "circles" in prayer

        # Verify search pattern prayer
        search_prayer = pattern.to_prayer_string()
        assert "circles-search" in search_prayer


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
