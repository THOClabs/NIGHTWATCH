"""
Unit tests for NIGHTWATCH Safety Monitor.

Tests the safety evaluation logic including thresholds, hysteresis,
rain holdoff, altitude limits, power safety, and enclosure integration.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

import pytest

# Import safety monitor components
import sys
sys.path.insert(0, "/workspaces/NIGHTWATCH/services/safety_monitor")
from monitor import (
    SafetyMonitor,
    SafetyStatus,
    SafetyAction,
    SafetyThresholds,
    AlertLevel,
    ObservatoryState,
    SensorInput,
)


class TestSafetyThresholds:
    """Tests for SafetyThresholds dataclass."""

    def test_default_thresholds(self):
        """Test default threshold values."""
        thresholds = SafetyThresholds()

        assert thresholds.wind_limit_mph == 25.0
        assert thresholds.humidity_limit == 85.0
        assert thresholds.temp_min_f == 20.0
        assert thresholds.twilight_altitude == -12.0

    def test_rain_holdoff_threshold(self):
        """Test Step 465 rain holdoff threshold."""
        thresholds = SafetyThresholds()
        assert thresholds.rain_holdoff_minutes == 30.0

    def test_altitude_limit_threshold(self):
        """Test Step 467 altitude limit thresholds."""
        thresholds = SafetyThresholds()
        assert thresholds.min_altitude_deg == 10.0
        assert thresholds.horizon_altitude_buffer == 2.0

    def test_power_thresholds(self):
        """Test Step 469 UPS power thresholds."""
        thresholds = SafetyThresholds()
        assert thresholds.ups_warning_percent == 50.0
        assert thresholds.ups_critical_percent == 25.0
        assert thresholds.ups_emergency_percent == 15.0

    def test_enclosure_threshold(self):
        """Test Step 470 enclosure threshold."""
        thresholds = SafetyThresholds()
        assert thresholds.require_enclosure_open is True

    def test_custom_thresholds(self):
        """Test custom threshold values."""
        thresholds = SafetyThresholds(
            wind_limit_mph=30.0,
            rain_holdoff_minutes=60.0,
            min_altitude_deg=15.0,
        )

        assert thresholds.wind_limit_mph == 30.0
        assert thresholds.rain_holdoff_minutes == 60.0
        assert thresholds.min_altitude_deg == 15.0


class TestSafetyStatus:
    """Tests for SafetyStatus dataclass."""

    def test_status_fields(self):
        """Test all status fields are present."""
        status = SafetyStatus(
            timestamp=datetime.now(),
            action=SafetyAction.SAFE_TO_OBSERVE,
            is_safe=True,
            reasons=["All clear"],
            alert_level=AlertLevel.INFO,
        )

        assert status.weather_ok is True
        assert status.clouds_ok is True
        assert status.daylight_ok is True
        assert status.power_ok is True
        assert status.enclosure_ok is True
        assert status.altitude_ok is True

    def test_rain_holdoff_fields(self):
        """Test Step 465 rain holdoff fields."""
        status = SafetyStatus(
            timestamp=datetime.now(),
            action=SafetyAction.PARK_AND_WAIT,
            is_safe=False,
            reasons=["Rain holdoff"],
            alert_level=AlertLevel.WARNING,
            rain_holdoff_active=True,
            rain_holdoff_remaining_min=15.0,
        )

        assert status.rain_holdoff_active is True
        assert status.rain_holdoff_remaining_min == 15.0

    def test_power_status_fields(self):
        """Test Step 469 power status fields."""
        status = SafetyStatus(
            timestamp=datetime.now(),
            action=SafetyAction.SAFE_TO_OBSERVE,
            is_safe=True,
            reasons=["All clear"],
            alert_level=AlertLevel.INFO,
            ups_battery_percent=75.0,
            ups_on_battery=False,
        )

        assert status.ups_battery_percent == 75.0
        assert status.ups_on_battery is False


class TestSafetyMonitor:
    """Tests for SafetyMonitor class."""

    @pytest.fixture
    def monitor(self):
        """Create a monitor instance for testing."""
        return SafetyMonitor()

    @pytest.fixture
    def mock_weather_ok(self):
        """Create mock weather data that is OK."""
        class MockWeather:
            is_raining = False
            rain_rate_in_hr = 0.0
            wind_speed_mph = 10.0
            wind_gust_mph = 15.0
            humidity_percent = 50.0
            temperature_f = 60.0
            dew_point_f = 40.0
        return MockWeather()

    @pytest.fixture
    def mock_weather_rain(self):
        """Create mock weather data with rain."""
        class MockWeather:
            is_raining = True
            rain_rate_in_hr = 0.5
            wind_speed_mph = 5.0
            wind_gust_mph = 10.0
            humidity_percent = 90.0
            temperature_f = 55.0
            dew_point_f = 50.0
        return MockWeather()

    def test_init(self, monitor):
        """Test monitor initialization."""
        assert monitor.state == ObservatoryState.UNKNOWN
        assert monitor.last_status is None
        assert monitor._running is False

    @pytest.mark.asyncio
    async def test_update_weather(self, monitor, mock_weather_ok):
        """Test weather data update."""
        await monitor.update_weather(mock_weather_ok)

        assert monitor._weather_data is not None
        assert monitor._weather_data.value == mock_weather_ok

    @pytest.mark.asyncio
    async def test_update_power_status(self, monitor):
        """Test Step 469 power status update."""
        await monitor.update_power_status(75.0, on_battery=False)

        assert monitor._ups_battery_percent == 75.0
        assert monitor._ups_on_battery is False

    @pytest.mark.asyncio
    async def test_update_enclosure_status(self, monitor):
        """Test Step 470 enclosure status update."""
        await monitor.update_enclosure_status(is_open=True)

        assert monitor._enclosure_open is True

    @pytest.mark.asyncio
    async def test_update_target_altitude(self, monitor):
        """Test Step 467 target altitude update."""
        await monitor.update_target_altitude(45.0)

        assert monitor._target_altitude == 45.0


class TestRainHoldoff:
    """Tests for Step 465 rain holdoff functionality."""

    @pytest.fixture
    def monitor(self):
        """Create monitor with short holdoff for testing."""
        thresholds = SafetyThresholds(rain_holdoff_minutes=5.0)
        return SafetyMonitor(thresholds=thresholds)

    def test_no_rain_no_holdoff(self, monitor):
        """Test no holdoff when no rain has occurred."""
        is_ok, reasons, remaining = monitor._evaluate_rain_holdoff()

        assert is_ok is True
        assert remaining is None

    def test_holdoff_active_after_rain(self, monitor):
        """Test holdoff is active after rain."""
        # Simulate recent rain
        monitor._last_rain_time = datetime.now()

        is_ok, reasons, remaining = monitor._evaluate_rain_holdoff()

        assert is_ok is False
        assert remaining is not None
        assert remaining > 0
        assert "Rain holdoff" in reasons[0]

    def test_holdoff_clears_after_time(self, monitor):
        """Test holdoff clears after configured time."""
        # Simulate rain 10 minutes ago (longer than 5 min holdoff)
        monitor._last_rain_time = datetime.now() - timedelta(minutes=10)

        is_ok, reasons, remaining = monitor._evaluate_rain_holdoff()

        assert is_ok is True
        assert remaining is None


class TestAltitudeLimit:
    """Tests for Step 467 altitude limit functionality."""

    @pytest.fixture
    def monitor(self):
        """Create monitor for testing."""
        thresholds = SafetyThresholds(
            min_altitude_deg=10.0,
            horizon_altitude_buffer=2.0,
        )
        return SafetyMonitor(thresholds=thresholds)

    def test_no_target_ok(self, monitor):
        """Test OK when no target altitude set."""
        is_ok, reasons = monitor._evaluate_altitude_limit()

        assert is_ok is True
        assert len(reasons) == 0

    def test_target_above_limit_ok(self, monitor):
        """Test OK when target is above minimum."""
        monitor._target_altitude = 45.0

        is_ok, reasons = monitor._evaluate_altitude_limit()

        assert is_ok is True

    def test_target_below_limit_fail(self, monitor):
        """Test fail when target is below minimum."""
        monitor._target_altitude = 5.0  # Below 10 degree limit

        is_ok, reasons = monitor._evaluate_altitude_limit()

        assert is_ok is False
        assert "below minimum" in reasons[0]

    def test_target_in_buffer_zone_warning(self, monitor):
        """Test warning when target is in buffer zone."""
        monitor._target_altitude = 11.0  # Between 10 and 12 (10 + 2 buffer)

        is_ok, reasons = monitor._evaluate_altitude_limit()

        assert is_ok is True  # Still OK
        assert "near horizon limit" in reasons[0]


class TestPowerSafety:
    """Tests for Step 469 power safety functionality."""

    @pytest.fixture
    def monitor(self):
        """Create monitor for testing."""
        return SafetyMonitor()

    def test_no_ups_data_ok(self, monitor):
        """Test OK when no UPS data available."""
        is_ok, reasons, is_emergency = monitor._evaluate_power()

        assert is_ok is True
        assert is_emergency is False

    def test_battery_full_ok(self, monitor):
        """Test OK with full battery."""
        monitor._ups_battery_percent = 100.0

        is_ok, reasons, is_emergency = monitor._evaluate_power()

        assert is_ok is True
        assert is_emergency is False

    def test_battery_warning_level(self, monitor):
        """Test warning at 50% battery."""
        monitor._ups_battery_percent = 45.0

        is_ok, reasons, is_emergency = monitor._evaluate_power()

        assert is_ok is True  # Still OK
        assert is_emergency is False
        assert any("warning" in r.lower() for r in reasons)

    def test_battery_critical_level(self, monitor):
        """Test critical at 25% battery."""
        monitor._ups_battery_percent = 20.0

        is_ok, reasons, is_emergency = monitor._evaluate_power()

        assert is_ok is False
        assert is_emergency is False
        assert any("parking" in r.lower() for r in reasons)

    def test_battery_emergency_level(self, monitor):
        """Test emergency at 15% battery."""
        monitor._ups_battery_percent = 10.0

        is_ok, reasons, is_emergency = monitor._evaluate_power()

        assert is_ok is False
        assert is_emergency is True
        assert any("emergency" in r.lower() for r in reasons)

    def test_on_battery_warning(self, monitor):
        """Test warning when on battery power."""
        monitor._ups_battery_percent = 80.0
        monitor._ups_on_battery = True

        is_ok, reasons, is_emergency = monitor._evaluate_power()

        assert is_ok is True
        assert any("battery power" in r.lower() for r in reasons)


class TestEnclosureSafety:
    """Tests for Step 470 enclosure safety functionality."""

    @pytest.fixture
    def monitor(self):
        """Create monitor for testing."""
        return SafetyMonitor()

    def test_no_enclosure_data_ok(self, monitor):
        """Test OK when no enclosure data (with warning)."""
        is_ok, reasons = monitor._evaluate_enclosure()

        assert is_ok is True
        assert "unknown" in reasons[0].lower()

    def test_enclosure_open_ok(self, monitor):
        """Test OK when enclosure is open."""
        monitor._enclosure_open = True

        is_ok, reasons = monitor._evaluate_enclosure()

        assert is_ok is True

    def test_enclosure_closed_fail(self, monitor):
        """Test fail when enclosure is closed."""
        monitor._enclosure_open = False

        is_ok, reasons = monitor._evaluate_enclosure()

        assert is_ok is False
        assert "closed" in reasons[0].lower()

    def test_enclosure_check_disabled(self):
        """Test enclosure check can be disabled."""
        thresholds = SafetyThresholds(require_enclosure_open=False)
        monitor = SafetyMonitor(thresholds=thresholds)
        monitor._enclosure_open = False

        is_ok, reasons = monitor._evaluate_enclosure()

        assert is_ok is True  # Disabled, so OK


class TestFullEvaluation:
    """Tests for full safety evaluation."""

    @pytest.fixture
    def monitor(self):
        """Create monitor for testing."""
        return SafetyMonitor()

    @pytest.fixture
    def mock_weather_ok(self):
        """Create mock weather data that is OK."""
        class MockWeather:
            is_raining = False
            rain_rate_in_hr = 0.0
            wind_speed_mph = 10.0
            wind_gust_mph = 15.0
            humidity_percent = 50.0
            temperature_f = 60.0
            dew_point_f = 40.0
        return MockWeather()

    @pytest.mark.asyncio
    async def test_all_ok_safe(self, monitor, mock_weather_ok):
        """Test safe when all conditions are OK."""
        await monitor.update_weather(mock_weather_ok)
        await monitor.update_sun_altitude(-18.0)  # Night
        await monitor.update_enclosure_status(True)
        await monitor.update_power_status(100.0)

        status = monitor.evaluate()

        assert status.is_safe is True
        assert status.action == SafetyAction.SAFE_TO_OBSERVE
        assert status.weather_ok is True
        assert status.power_ok is True
        assert status.enclosure_ok is True

    @pytest.mark.asyncio
    async def test_rain_triggers_emergency(self, monitor):
        """Test rain triggers emergency action."""
        class RainWeather:
            is_raining = True
            rain_rate_in_hr = 0.5
            wind_speed_mph = 5.0
            wind_gust_mph = 8.0
            humidity_percent = 95.0
            temperature_f = 50.0
            dew_point_f = 48.0

        await monitor.update_weather(RainWeather())
        await monitor.update_sun_altitude(-18.0)

        status = monitor.evaluate()

        assert status.is_safe is False
        assert status.action == SafetyAction.EMERGENCY_CLOSE
        assert status.alert_level == AlertLevel.EMERGENCY

    @pytest.mark.asyncio
    async def test_power_emergency(self, monitor, mock_weather_ok):
        """Test low battery triggers emergency."""
        await monitor.update_weather(mock_weather_ok)
        await monitor.update_sun_altitude(-18.0)
        await monitor.update_power_status(10.0)  # Critical low

        status = monitor.evaluate()

        assert status.is_safe is False
        assert status.action == SafetyAction.EMERGENCY_CLOSE
        assert status.alert_level == AlertLevel.EMERGENCY

    @pytest.mark.asyncio
    async def test_enclosure_closed_parks(self, monitor, mock_weather_ok):
        """Test closed enclosure causes park."""
        await monitor.update_weather(mock_weather_ok)
        await monitor.update_sun_altitude(-18.0)
        await monitor.update_enclosure_status(False)

        status = monitor.evaluate()

        assert status.is_safe is False
        assert status.enclosure_ok is False

    @pytest.mark.asyncio
    async def test_status_includes_all_fields(self, monitor, mock_weather_ok):
        """Test status includes all new fields."""
        await monitor.update_weather(mock_weather_ok)
        await monitor.update_sun_altitude(-18.0)
        await monitor.update_power_status(80.0, on_battery=True)
        await monitor.update_enclosure_status(True)
        await monitor.update_target_altitude(45.0)

        status = monitor.evaluate()

        # Step 465: Rain holdoff fields
        assert hasattr(status, 'rain_holdoff_active')
        assert hasattr(status, 'rain_holdoff_remaining_min')

        # Step 467: Altitude field
        assert hasattr(status, 'target_altitude_deg')
        assert status.target_altitude_deg == 45.0

        # Step 469: Power fields
        assert hasattr(status, 'ups_battery_percent')
        assert status.ups_battery_percent == 80.0
        assert hasattr(status, 'ups_on_battery')
        assert status.ups_on_battery is True

        # Step 470: Enclosure field
        assert hasattr(status, 'enclosure_open')
        assert status.enclosure_open is True


class TestHysteresis:
    """Tests for hysteresis behavior."""

    @pytest.fixture
    def monitor(self):
        """Create monitor for testing."""
        return SafetyMonitor()

    @pytest.fixture
    def mock_weather(self):
        """Create mutable mock weather."""
        class MockWeather:
            is_raining = False
            rain_rate_in_hr = 0.0
            wind_speed_mph = 10.0
            wind_gust_mph = 15.0
            humidity_percent = 50.0
            temperature_f = 60.0
            dew_point_f = 40.0
        return MockWeather()

    @pytest.mark.asyncio
    async def test_wind_hysteresis(self, monitor, mock_weather):
        """Test wind hysteresis prevents oscillation."""
        # Start with safe wind
        await monitor.update_weather(mock_weather)
        status = monitor.evaluate()
        assert status.weather_ok is True

        # Wind exceeds limit
        mock_weather.wind_speed_mph = 30.0
        await monitor.update_weather(mock_weather)
        status = monitor.evaluate()
        assert "Wind" in str(status.reasons)

        # Wind drops but not below hysteresis threshold (25 - 5 = 20)
        mock_weather.wind_speed_mph = 22.0
        await monitor.update_weather(mock_weather)
        status = monitor.evaluate()
        # Should still be triggered due to hysteresis
        assert monitor._wind_triggered is True

        # Wind drops below hysteresis threshold
        mock_weather.wind_speed_mph = 18.0
        await monitor.update_weather(mock_weather)
        status = monitor.evaluate()
        assert monitor._wind_triggered is False
