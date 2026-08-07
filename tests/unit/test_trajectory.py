"""
NIGHTWATCH Trajectory Calculator Tests
Coverage for trajectory estimation, visibility calculations,
and debris field prediction.

presa-nightwatch. velmu-test.
"""

import math
import pytest

from services.meteor_tracking.trajectory import (
    Vector,
    TrajectoryResult,
    calculate_trajectory,
    estimate_trajectory_from_single_point,
    is_visible_from,
    get_visibility_radius_km,
)


class TestVector:
    """Test Vector operations."""

    def test_magnitude(self):
        v = Vector(3.0, 4.0, 0.0)
        assert abs(v.magnitude() - 5.0) < 1e-10

    def test_magnitude_3d(self):
        v = Vector(1.0, 2.0, 2.0)
        assert abs(v.magnitude() - 3.0) < 1e-10

    def test_zero_vector_magnitude(self):
        v = Vector(0, 0, 0)
        assert v.magnitude() == 0.0

    def test_normalize(self):
        v = Vector(3.0, 4.0, 0.0)
        n = v.normalize()
        assert abs(n.magnitude() - 1.0) < 1e-10
        assert abs(n.x - 0.6) < 1e-10
        assert abs(n.y - 0.8) < 1e-10

    def test_normalize_zero_vector(self):
        v = Vector(0, 0, 0)
        n = v.normalize()
        assert n.x == 0 and n.y == 0 and n.z == 0

    def test_to_compass_north(self):
        v = Vector(0, 1, 0)  # positive y = north
        assert v.to_compass() == "N"

    def test_to_compass_east(self):
        v = Vector(1, 0, 0)  # positive x = east
        assert v.to_compass() == "E"

    def test_to_compass_south(self):
        v = Vector(0, -1, 0)
        assert v.to_compass() == "S"

    def test_to_compass_west(self):
        v = Vector(-1, 0, 0)
        assert v.to_compass() == "W"

    def test_to_compass_northeast(self):
        v = Vector(1, 1, 0)
        assert v.to_compass() == "NE"


class TestTrajectoryResult:
    """Test TrajectoryResult properties."""

    def test_vector_trace_str(self):
        result = TrajectoryResult(
            entry_direction="NW",
            travel_direction="SE",
            entry_angle_deg=45.0,
            velocity_km_s=20.0
        )
        assert result.vector_trace_str == "NW to SE, 45 entry"


class TestCalculateTrajectory:
    """Test trajectory calculation with various scenarios."""

    def test_southward_trajectory(self):
        result = calculate_trajectory(
            start_lat=40.0, start_lon=-117.0,
            end_lat=39.0, end_lon=-117.0
        )
        assert result.travel_direction == "S"
        assert result.entry_direction == "N"

    def test_northward_trajectory(self):
        result = calculate_trajectory(
            start_lat=39.0, start_lon=-117.0,
            end_lat=40.0, end_lon=-117.0
        )
        assert result.travel_direction == "N"

    def test_default_entry_angle(self):
        """Without altitude data, entry angle defaults to 45."""
        result = calculate_trajectory(
            start_lat=40.0, start_lon=-118.0,
            end_lat=39.0, end_lon=-117.0
        )
        assert result.entry_angle_deg == 45.0

    def test_steep_entry_angle(self):
        """With large altitude drop over short distance, angle should be steep."""
        result = calculate_trajectory(
            start_lat=39.5, start_lon=-117.0,
            end_lat=39.51, end_lon=-117.01,
            start_alt_km=80, end_alt_km=20
        )
        assert result.entry_angle_deg > 45.0  # steep

    def test_shallow_entry_angle(self):
        """With small altitude drop over long distance, angle should be shallow."""
        result = calculate_trajectory(
            start_lat=40.0, start_lon=-119.0,
            end_lat=39.0, end_lon=-117.0,
            start_alt_km=80, end_alt_km=70
        )
        assert result.entry_angle_deg < 10.0  # very shallow

    def test_debris_field_predicted_for_low_terminal(self):
        result = calculate_trajectory(
            start_lat=40.0, start_lon=-118.0,
            end_lat=39.0, end_lon=-117.0,
            start_alt_km=80, end_alt_km=15,
            velocity_km_s=18
        )
        assert result.debris_field_center is not None
        assert result.debris_field_radius_km is not None

    def test_no_debris_field_for_high_terminal(self):
        result = calculate_trajectory(
            start_lat=40.0, start_lon=-118.0,
            end_lat=39.0, end_lon=-117.0,
            start_alt_km=80, end_alt_km=40,
            velocity_km_s=30
        )
        assert result.debris_field_center is None

    def test_debris_radius_scales_with_velocity(self):
        slow = calculate_trajectory(
            start_lat=40.0, start_lon=-118.0,
            end_lat=39.0, end_lon=-117.0,
            start_alt_km=80, end_alt_km=15,
            velocity_km_s=10
        )
        fast = calculate_trajectory(
            start_lat=40.0, start_lon=-118.0,
            end_lat=39.0, end_lon=-117.0,
            start_alt_km=80, end_alt_km=15,
            velocity_km_s=40
        )
        assert fast.debris_field_radius_km > slow.debris_field_radius_km

    def test_default_velocity(self):
        result = calculate_trajectory(
            start_lat=40.0, start_lon=-118.0,
            end_lat=39.0, end_lon=-117.0
        )
        assert result.velocity_km_s == 20.0  # default


class TestEstimateTrajectoryFromSinglePoint:
    """Test single-point trajectory estimation."""

    def test_returns_trajectory_result(self):
        result = estimate_trajectory_from_single_point(39.5, -117.0)
        assert isinstance(result, TrajectoryResult)

    def test_unknown_directions(self):
        result = estimate_trajectory_from_single_point(39.5, -117.0)
        assert result.entry_direction == "unknown"
        assert result.travel_direction == "unknown"

    def test_default_entry_angle(self):
        result = estimate_trajectory_from_single_point(39.5, -117.0)
        assert result.entry_angle_deg == 45.0

    def test_preserves_coordinates(self):
        result = estimate_trajectory_from_single_point(39.5, -117.0, velocity_km_s=25.0)
        assert result.last_seen_lat == 39.5
        assert result.last_seen_lon == -117.0
        assert result.velocity_km_s == 25.0

    def test_no_debris_field(self):
        result = estimate_trajectory_from_single_point(39.5, -117.0)
        assert result.debris_field_center is None
        assert result.debris_field_radius_km is None


class TestIsVisibleFrom:
    """Test fireball visibility calculations."""

    def test_overhead_event_visible(self):
        assert is_visible_from(39.5, -117.0, 39.5, -117.0, event_alt_km=80.0)

    def test_nearby_event_visible(self):
        assert is_visible_from(39.5, -117.0, 40.0, -117.5, event_alt_km=80.0)

    def test_distant_low_event_not_visible(self):
        assert not is_visible_from(
            39.5, -117.0, 60.0, -50.0, event_alt_km=30.0
        )

    def test_very_close_always_visible(self):
        """Events < 1km away should always be visible."""
        assert is_visible_from(39.5, -117.0, 39.5001, -117.0001, event_alt_km=0.1)

    def test_high_altitude_visible_from_far(self):
        """High altitude events should be visible from further away."""
        visible = is_visible_from(
            39.5, -117.0, 42.0, -115.0, event_alt_km=100.0
        )
        not_visible = is_visible_from(
            39.5, -117.0, 42.0, -115.0, event_alt_km=10.0
        )
        assert visible
        assert not not_visible

    def test_min_elevation_threshold(self):
        """Higher min elevation should reduce visibility range."""
        visible_low_threshold = is_visible_from(
            39.5, -117.0, 41.0, -117.0, event_alt_km=50.0, min_elevation_deg=5.0
        )
        visible_high_threshold = is_visible_from(
            39.5, -117.0, 41.0, -117.0, event_alt_km=50.0, min_elevation_deg=30.0
        )
        assert visible_low_threshold
        assert not visible_high_threshold


class TestGetVisibilityRadiusKm:
    """Test visibility radius calculation."""

    def test_higher_altitude_larger_radius(self):
        r80 = get_visibility_radius_km(80.0)
        r30 = get_visibility_radius_km(30.0)
        assert r80 > r30

    def test_known_value(self):
        """At 80km altitude with 10 degree min elevation, radius should be ~454km."""
        r = get_visibility_radius_km(80.0, min_elevation_deg=10.0)
        expected = 80.0 / math.tan(math.radians(10.0))
        assert abs(r - expected) < 0.01

    def test_steeper_min_elevation_smaller_radius(self):
        r10 = get_visibility_radius_km(80.0, min_elevation_deg=10.0)
        r30 = get_visibility_radius_km(80.0, min_elevation_deg=30.0)
        assert r10 > r30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
