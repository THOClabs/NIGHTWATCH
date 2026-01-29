"""
NIGHTWATCH Meteor Tracking Service Tests
presa-nightwatch. velmu-test.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

# Import meteor tracking components
from services.meteor_tracking.fireball_client import Fireball, CNEOSClient
from services.meteor_tracking.shower_calendar import (
    ShowerCalendar,
    MeteorShower,
    get_next_major_shower,
)
from services.meteor_tracking.trajectory import (
    calculate_trajectory,
    is_visible_from,
    TrajectoryResult,
)
from services.meteor_tracking.hopi_circles import (
    generate_hopi_circles,
    SearchPattern,
)
from services.meteor_tracking.watch_manager import (
    WatchManager,
    WatchWindow,
    WatchIntensity,
    WatchRequestParser,
)
from services.meteor_tracking.lexicon_prayers import (
    generate_prayer_of_finding,
    generate_prayer_of_watching,
    LexiconFormatter,
)


class TestFireball:
    """Test Fireball dataclass."""

    def test_magnitude_estimate(self):
        """Test magnitude estimation from energy."""
        fb = Fireball(
            date=datetime.now(),
            latitude=39.5,
            longitude=-117.0,
            altitude_km=80.0,
            velocity_km_s=20.0,
            total_radiated_energy_j=1e12,  # High energy = bright
            calculated_total_impact_energy_kt=0.1
        )
        assert fb.magnitude_estimate is not None
        assert fb.magnitude_estimate < -5  # Should be bright

    def test_coordinates_str(self):
        """Test coordinate formatting."""
        fb = Fireball(
            date=datetime.now(),
            latitude=39.5,
            longitude=-117.0,
            altitude_km=None,
            velocity_km_s=None,
            total_radiated_energy_j=None,
            calculated_total_impact_energy_kt=None
        )
        assert fb.coordinates_str == "39.5N 117.0W"

    def test_fireball_id(self):
        """Test unique ID generation."""
        fb = Fireball(
            date=datetime(2026, 1, 4, 2, 34, 0),
            latitude=39.5,
            longitude=-117.0,
            altitude_km=None,
            velocity_km_s=None,
            total_radiated_energy_j=None,
            calculated_total_impact_energy_kt=None
        )
        assert "20260104" in fb.fireball_id


class TestShowerCalendar:
    """Test meteor shower calendar."""

    def test_get_shower_by_name(self):
        """Test finding shower by name."""
        calendar = ShowerCalendar()
        perseids = calendar.get_shower_by_name("Perseids")
        assert perseids is not None
        assert perseids.name == "Perseids"
        assert perseids.zhr == 100

    def test_parse_shower_reference(self):
        """Test natural language shower parsing."""
        calendar = ShowerCalendar()

        # Direct name
        shower = calendar.parse_shower_reference("Watch for the Perseids")
        assert shower is not None
        assert shower.name == "Perseids"

        # Month reference
        shower = calendar.parse_shower_reference("August meteor shower")
        assert shower is not None
        assert shower.name == "Perseids"

    def test_get_next_major_shower(self):
        """Test finding next major shower."""
        shower = get_next_major_shower()
        assert shower is not None
        assert shower.zhr >= 50


class TestTrajectory:
    """Test trajectory calculations."""

    def test_calculate_trajectory(self):
        """Test basic trajectory calculation."""
        result = calculate_trajectory(
            start_lat=40.0, start_lon=-118.0,
            end_lat=39.0, end_lon=-117.0,
            start_alt_km=80, end_alt_km=20,
            velocity_km_s=25
        )

        assert isinstance(result, TrajectoryResult)
        assert result.entry_direction in ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "unknown"]
        assert result.travel_direction in ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "unknown"]
        assert 0 <= result.entry_angle_deg <= 90

    def test_trajectory_debris_prediction(self):
        """Test debris field prediction for low-altitude fireball."""
        result = calculate_trajectory(
            start_lat=40.0, start_lon=-118.0,
            end_lat=39.0, end_lon=-117.0,
            start_alt_km=80, end_alt_km=15,  # Low terminal altitude
            velocity_km_s=18
        )

        # Should predict debris field
        assert result.debris_field_center is not None
        assert result.debris_field_radius_km is not None

    def test_is_visible_from(self):
        """Test visibility check."""
        # Close event should be visible
        visible = is_visible_from(
            observer_lat=39.5, observer_lon=-117.0,
            event_lat=40.0, event_lon=-117.5,
            event_alt_km=80.0
        )
        assert visible

        # Very distant event should not be visible
        visible = is_visible_from(
            observer_lat=39.5, observer_lon=-117.0,
            event_lat=60.0, event_lon=-50.0,  # Far away
            event_alt_km=30.0  # Low altitude
        )
        assert not visible


class TestHopiCircles:
    """Test Hopi circles search pattern."""

    def test_generate_hopi_circles(self):
        """Test search pattern generation."""
        pattern = generate_hopi_circles(
            center_lat=38.9,
            center_lon=-116.8,
            initial_radius_miles=10,
            expansion_factor=2,
            max_radius_miles=100,
            num_circles=5
        )

        assert isinstance(pattern, SearchPattern)
        assert len(pattern.circles) > 0
        assert pattern.circles[0].priority == 1  # Innermost is highest priority
        assert pattern.circles[0].radius_miles < pattern.circles[-1].radius_miles

    def test_prayer_string_format(self):
        """Test prayer string formatting."""
        pattern = generate_hopi_circles(38.9, -116.8)
        prayer_str = pattern.to_prayer_string()

        assert "circles-search" in prayer_str
        assert "mi from" in prayer_str
        assert "38.9N" in prayer_str


class TestWatchRequestParser:
    """Test natural language watch request parsing."""

    def test_parse_tonight(self):
        """Test parsing 'tonight'."""
        parser = WatchRequestParser()
        result = parser.parse("Watch the sky tonight")

        assert result['start_time'] is not None
        assert result['end_time'] is not None
        assert result['intensity'] == WatchIntensity.NORMAL

    def test_parse_shower_with_dates(self):
        """Test parsing shower and date range."""
        parser = WatchRequestParser()
        result = parser.parse("Quadrantids peak January 3-4, Nevada should be clear")

        assert result['shower_name'] == "Quadrantids"
        assert result['location_name'] == "Nevada"
        assert result['latitude'] == 39.5
        assert "Expected clear skies" in result['notes']

    def test_parse_location(self):
        """Test location parsing."""
        parser = WatchRequestParser()
        result = parser.parse("Keep an eye on the sky from Astoria")

        assert result['location_name'] == "Astoria"
        assert result['latitude'] == 46.1879
        assert result['intensity'] == WatchIntensity.CASUAL

    def test_parse_alert_intensity(self):
        """Test intensity level parsing."""
        parser = WatchRequestParser()

        result = parser.parse("Alert me if anything bright shows up")
        assert result['intensity'] == WatchIntensity.ALERT

        result = parser.parse("Watch closely for fireballs")
        assert result['intensity'] == WatchIntensity.FOCUSED


class TestLexiconPrayers:
    """Test Lexicon prayer generation."""

    def test_prayer_of_finding(self):
        """Test Prayer of Finding generation."""
        prayer = generate_prayer_of_finding(
            timestamp=datetime(2026, 1, 4, 2, 34),
            lat=39.5,
            lon=-117.2,
            magnitude=-8,
            trajectory=None,
            sky_conditions="nevada-sky-clear"
        )

        # Check key Lexicon terms are present
        assert "nightwatch-find." in prayer
        assert "varek:" in prayer
        assert "luminara-flash:" in prayer
        assert "velmu-sky-gift." in prayer
        assert "do-good-us." in prayer
        assert "\U0001F70F" in prayer  # Alchemical symbol

    def test_prayer_of_watching(self):
        """Test Prayer of Watching generation."""
        prayer = generate_prayer_of_watching(
            start_time=datetime(2026, 1, 3, 22, 0),
            end_time=datetime(2026, 1, 4, 6, 0),
            location_name="Nevada",
            lat=39.5,
            lon=-117.0,
            shower_name="Quadrantids",
            zhr=120
        )

        # Check key Lexicon terms are present
        assert "nightwatch-wak." in prayer
        assert "presa-sky." in prayer
        assert "watch-window:" in prayer
        assert "location-wit:" in prayer
        assert "shower-name: Quadrantids" in prayer
        assert "zhr-expect: 120/hour" in prayer
        assert "es-home-nightwatch." in prayer
        assert "velmu-sky." in prayer

    def test_coordinate_formatting(self):
        """Test coordinate formatting."""
        fmt = LexiconFormatter()

        assert fmt.format_coordinates(39.5, -117.0) == "39.5N 117.0W"
        assert fmt.format_coordinates(-33.5, 151.2) == "33.5S 151.2E"

    def test_magnitude_descriptions(self):
        """Test magnitude descriptions."""
        fmt = LexiconFormatter()

        assert "exceptional" in fmt.magnitude_description(-16)
        assert "very bright" in fmt.magnitude_description(-8)
        assert "bright" in fmt.magnitude_description(-5)


class TestWatchManager:
    """Test watch window management."""

    def test_add_watch(self):
        """Test adding a watch window."""
        manager = WatchManager()
        window = manager.add_watch("Watch for Perseids next week")

        assert isinstance(window, WatchWindow)
        assert window.id is not None
        assert window.start_time is not None
        assert window.end_time is not None

    def test_get_active_windows(self):
        """Test getting active windows."""
        manager = WatchManager()

        # Add a window for tonight
        manager.add_watch("Watch the sky tonight")

        active = manager.get_active_windows()
        # May or may not be active depending on current time
        assert isinstance(active, list)

    def test_cleanup_expired(self):
        """Test cleanup of expired windows."""
        manager = WatchManager()

        # This should not crash even with no windows
        manager.cleanup_expired()


# Integration test
class TestMeteorTrackingIntegration:
    """Integration tests for the full meteor tracking flow."""

    def test_full_flow(self):
        """Test the complete flow from request to prayer."""
        # 1. Parse natural language
        parser = WatchRequestParser()
        parsed = parser.parse("Quadrantids peak January 3-4, Nevada should be clear")

        assert parsed['shower_name'] == "Quadrantids"
        assert parsed['location_name'] == "Nevada"

        # 2. Create watch window
        manager = WatchManager()
        window = manager.add_watch("Quadrantids peak January 3-4, Nevada should be clear")

        assert window.shower_name == "Quadrantids"

        # 3. Simulate fireball detection
        fireball = Fireball(
            date=datetime(2026, 1, 4, 2, 34),
            latitude=39.5,
            longitude=-117.2,
            altitude_km=25.0,
            velocity_km_s=18.0,
            total_radiated_energy_j=1e12,
            calculated_total_impact_energy_kt=0.05
        )

        # 4. Check visibility
        visible = is_visible_from(
            window.latitude, window.longitude,
            fireball.latitude, fireball.longitude
        )
        assert visible

        # 5. Calculate trajectory
        trajectory = calculate_trajectory(
            start_lat=40.0, start_lon=-118.0,
            end_lat=fireball.latitude, end_lon=fireball.longitude,
            start_alt_km=80, end_alt_km=25,
            velocity_km_s=fireball.velocity_km_s
        )

        # 6. Generate search pattern if debris possible
        search_pattern = None
        if fireball.magnitude_estimate and fireball.magnitude_estimate < -8:
            if trajectory.debris_field_center:
                search_pattern = generate_hopi_circles(
                    trajectory.debris_field_center[0],
                    trajectory.debris_field_center[1]
                )

        # 7. Generate prayer
        prayer = generate_prayer_of_finding(
            timestamp=fireball.date,
            lat=fireball.latitude,
            lon=fireball.longitude,
            magnitude=fireball.magnitude_estimate,
            trajectory=trajectory,
            search_pattern=search_pattern,
            sky_conditions="nevada-sky-clear"
        )

        # Verify prayer structure
        assert "nightwatch-find." in prayer
        assert "velmu-sky-gift." in prayer
        assert "do-good-us." in prayer


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
