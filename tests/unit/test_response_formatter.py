"""
Unit tests for NIGHTWATCH Response Formatter.

Tests natural language formatting for TTS output.
"""

from datetime import datetime
import pytest

from nightwatch.response_formatter import (
    ResponseFormatter,
    format_ra,
    format_dec,
    format_alt_az,
    format_temperature,
    format_wind,
    format_time,
    format_duration,
)


class TestFormatRA:
    """Tests for RA formatting."""

    def test_whole_hours(self):
        """Test formatting whole hours."""
        assert format_ra(10.0, "hours") == "10 hours"
        assert format_ra(0.0, "hours") == "0 hours"
        assert format_ra(23.0, "hours") == "23 hours"

    def test_hours_minutes(self):
        """Test formatting hours and minutes."""
        assert format_ra(10.5, "minutes") == "10 hours 30 minutes"
        assert format_ra(10.0, "minutes") == "10 hours"
        assert format_ra(10.25, "minutes") == "10 hours 15 minutes"

    def test_hours_minutes_seconds(self):
        """Test formatting with seconds."""
        result = format_ra(10.5, "seconds")
        assert "10 hours" in result
        assert "30 minutes" in result


class TestFormatDec:
    """Tests for Declination formatting."""

    def test_positive_degrees(self):
        """Test formatting positive declination."""
        assert format_dec(45.0, "degrees") == "plus 45 degrees"
        assert format_dec(0.0, "degrees") == "plus 0 degrees"

    def test_negative_degrees(self):
        """Test formatting negative declination."""
        assert format_dec(-45.0, "degrees") == "minus 45 degrees"
        assert format_dec(-90.0, "degrees") == "minus 90 degrees"

    def test_degrees_arcmin(self):
        """Test formatting with arcminutes."""
        assert format_dec(45.5, "arcmin") == "plus 45 degrees 30 arcminutes"
        assert format_dec(-45.5, "arcmin") == "minus 45 degrees 30 arcminutes"
        assert format_dec(45.0, "arcmin") == "plus 45 degrees"


class TestFormatAltAz:
    """Tests for Alt/Az formatting."""

    def test_north(self):
        """Test north direction."""
        result = format_alt_az(45.0, 0.0)
        assert "north" in result
        assert "45" in result

    def test_east(self):
        """Test east direction."""
        result = format_alt_az(45.0, 90.0)
        assert "east" in result

    def test_south(self):
        """Test south direction."""
        result = format_alt_az(45.0, 180.0)
        assert "south" in result

    def test_west(self):
        """Test west direction."""
        result = format_alt_az(45.0, 270.0)
        assert "west" in result

    def test_below_horizon(self):
        """Test object below horizon."""
        result = format_alt_az(-10.0, 90.0)
        assert "below" in result.lower()

    def test_low_altitude(self):
        """Test low altitude object."""
        result = format_alt_az(5.0, 180.0)
        assert "low" in result.lower()

    def test_overhead(self):
        """Test nearly overhead object."""
        result = format_alt_az(85.0, 0.0)
        assert "overhead" in result.lower()


class TestFormatTemperature:
    """Tests for temperature formatting."""

    def test_celsius(self):
        """Test Celsius formatting."""
        assert "15 degrees celsius" in format_temperature(15.0)
        assert "0 degrees celsius" in format_temperature(0.0)
        assert "-5 degrees celsius" in format_temperature(-5.0)

    def test_fahrenheit(self):
        """Test Fahrenheit conversion."""
        result = format_temperature(0.0, "fahrenheit")
        assert "32 degrees fahrenheit" in result

        result = format_temperature(100.0, "fahrenheit")
        assert "212 degrees fahrenheit" in result


class TestFormatWind:
    """Tests for wind formatting."""

    def test_calm(self):
        """Test calm wind."""
        assert format_wind(0.0) == "calm"
        assert format_wind(0.5) == "calm"

    def test_light_breeze(self):
        """Test light breeze."""
        assert format_wind(3.0) == "light breeze"

    def test_with_speed(self):
        """Test wind with speed."""
        result = format_wind(15.0)
        assert "15 kilometers per hour" in result

    def test_with_direction(self):
        """Test wind with direction."""
        result = format_wind(15.0, 0.0)
        assert "north" in result

        result = format_wind(15.0, 90.0)
        assert "east" in result

        result = format_wind(15.0, 180.0)
        assert "south" in result

        result = format_wind(15.0, 270.0)
        assert "west" in result


class TestFormatTime:
    """Tests for time formatting."""

    def test_am_time(self):
        """Test morning time."""
        dt = datetime(2024, 1, 15, 8, 30, 0)
        result = format_time(dt)
        assert "8:30 AM" in result

    def test_pm_time(self):
        """Test afternoon time."""
        dt = datetime(2024, 1, 15, 20, 30, 0)
        result = format_time(dt)
        assert "8:30 PM" in result

    def test_midnight(self):
        """Test midnight."""
        dt = datetime(2024, 1, 15, 0, 0, 0)
        result = format_time(dt)
        assert "12 AM" in result

    def test_noon(self):
        """Test noon."""
        dt = datetime(2024, 1, 15, 12, 0, 0)
        result = format_time(dt)
        assert "12 PM" in result

    def test_with_date(self):
        """Test with date included."""
        dt = datetime(2024, 1, 15, 20, 30, 0)
        result = format_time(dt, include_date=True)
        assert "January" in result
        assert "15th" in result


class TestFormatDuration:
    """Tests for duration formatting."""

    def test_seconds(self):
        """Test seconds only."""
        assert format_duration(30) == "30 seconds"
        assert format_duration(1) == "1 seconds"

    def test_minutes(self):
        """Test minutes."""
        assert format_duration(60) == "1 minutes"
        assert format_duration(90) == "1 minutes 30 seconds"
        assert format_duration(120) == "2 minutes"

    def test_hours(self):
        """Test hours."""
        assert format_duration(3600) == "1 hours"
        assert format_duration(5400) == "1 hours 30 minutes"
        assert format_duration(7200) == "2 hours"


class TestResponseFormatter:
    """Tests for ResponseFormatter class."""

    @pytest.fixture
    def formatter(self):
        """Create formatter for testing."""
        return ResponseFormatter()

    def test_init(self, formatter):
        """Test formatter initialization."""
        assert len(formatter.templates) > 0

    def test_custom_templates(self):
        """Test custom template override."""
        custom = {"all_safe": "Everything is good!"}
        formatter = ResponseFormatter(templates=custom)
        assert formatter.templates["all_safe"] == "Everything is good!"

    def test_format_weather(self, formatter):
        """Test weather formatting."""
        data = {
            "temperature": 15.0,
            "humidity": 45,
            "wind_speed": 10,
        }
        result = formatter._format_weather(data)
        assert "Temperature" in result or "temperature" in result.lower()

    def test_format_safety_safe(self, formatter):
        """Test safety formatting when safe."""
        data = {"is_safe": True}
        result = formatter._format_safety(data)
        assert "safe" in result.lower()

    def test_format_safety_unsafe(self, formatter):
        """Test safety formatting when unsafe."""
        data = {"is_safe": False, "unsafe_reasons": ["Wind too high", "Humidity high"]}
        result = formatter._format_safety(data)
        assert "Wind too high" in result

    def test_format_object_info(self, formatter):
        """Test object info formatting."""
        obj_data = {
            "name": "Andromeda Galaxy",
            "type": "galaxy",
            "constellation": "Andromeda",
            "magnitude": 3.4,
        }
        result = formatter.format_object_info(obj_data)
        assert "Andromeda Galaxy" in result
        assert "galaxy" in result.lower()
        assert "Andromeda" in result

    def test_format_object_info_bright(self, formatter):
        """Test object info for bright object."""
        obj_data = {
            "name": "Sirius",
            "type": "star",
            "magnitude": -1.46,
        }
        result = formatter.format_object_info(obj_data)
        assert "brightest" in result.lower()

    def test_format_object_info_faint(self, formatter):
        """Test object info for faint object."""
        obj_data = {
            "name": "NGC 7331",
            "type": "galaxy",
            "magnitude": 10.4,
        }
        result = formatter.format_object_info(obj_data)
        assert "telescope" in result.lower()

    def test_format_coordinates(self, formatter):
        """Test coordinate formatting."""
        result = formatter.format_coordinates(ra=10.5, dec=41.2)
        assert "Right Ascension" in result
        assert "Declination" in result

    def test_format_coordinates_altaz(self, formatter):
        """Test Alt/Az coordinate formatting."""
        result = formatter.format_coordinates(alt=45.0, az=180.0)
        assert "south" in result.lower()

    def test_format_error(self, formatter):
        """Test error formatting."""
        result = formatter.format_error("Connection_failed", "connect to mount")
        assert "Sorry" in result
        assert "connect to mount" in result


class TestTwilightFormatting:
    """Tests for twilight time formatting."""

    @pytest.fixture
    def formatter(self):
        """Create formatter for testing."""
        return ResponseFormatter()

    def test_format_twilight_strings(self, formatter):
        """Test twilight formatting with string times."""
        data = {
            "sunset": "5:30 PM",
            "astronomical_twilight_end": "6:45 PM",
        }
        result = formatter._format_twilight(data)
        assert "Sunset" in result
        assert "5:30 PM" in result

    def test_format_twilight_datetime(self, formatter):
        """Test twilight formatting with datetime objects."""
        data = {
            "sunset": datetime(2024, 1, 15, 17, 30),
        }
        result = formatter._format_twilight(data)
        assert "Sunset" in result
