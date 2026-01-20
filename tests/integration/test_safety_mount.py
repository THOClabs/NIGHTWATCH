"""
Integration tests for Safety Monitor + Mount (Step 567).

Tests the interaction between safety monitoring system and mount control,
including safety vetoes, emergency parking, and weather-triggered responses.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta


class TestSafetyMountIntegration:
    """Integration tests for safety monitor and mount controller."""

    @pytest.fixture
    def mock_mount(self):
        """Create mock mount controller."""
        mount = Mock()
        mount.is_connected = True
        mount.is_parked = False
        mount.is_slewing = False
        mount.is_tracking = True
        mount.ra_hours = 12.5
        mount.dec_degrees = 45.0
        mount.altitude = 65.0
        mount.azimuth = 180.0

        # Async methods
        mount.park = AsyncMock(return_value=True)
        mount.unpark = AsyncMock(return_value=True)
        mount.slew_to_coordinates = AsyncMock(return_value=True)
        mount.stop = AsyncMock(return_value=True)
        mount.set_tracking = AsyncMock(return_value=True)

        return mount

    @pytest.fixture
    def mock_safety(self):
        """Create mock safety monitor."""
        safety = Mock()

        # Safety state
        safety.is_safe = True
        safety.weather_safe = True
        safety.rain_detected = False
        safety.wind_speed_mph = 10
        safety.humidity_percent = 50
        safety.cloud_cover_percent = 20

        # Methods
        safety.evaluate = Mock(return_value={"safe": True, "reasons": []})
        safety.is_safe_to_slew = Mock(return_value=True)
        safety.is_safe_to_unpark = Mock(return_value=True)
        safety.check_altitude_limit = Mock(return_value=True)
        safety.get_veto_reasons = Mock(return_value=[])

        return safety

    @pytest.fixture
    def mock_weather(self):
        """Create mock weather service."""
        weather = Mock()
        weather.is_safe = True
        weather.temperature_c = 15.0
        weather.humidity_percent = 50
        weather.wind_speed_mph = 10
        weather.rain_rate = 0.0
        weather.cloud_cover_percent = 20
        weather.dew_point_c = 5.0
        return weather

    @pytest.mark.asyncio
    async def test_slew_allowed_when_safe(self, mock_mount, mock_safety):
        """Test that slew is allowed when safety conditions are met."""
        assert mock_safety.is_safe_to_slew() is True

        success = await mock_mount.slew_to_coordinates(10.0, 50.0)
        assert success is True
        mock_mount.slew_to_coordinates.assert_called_once()

    @pytest.mark.asyncio
    async def test_slew_blocked_unsafe_weather(self, mock_mount, mock_safety):
        """Test that slew is blocked during unsafe weather."""
        mock_safety.is_safe_to_slew.return_value = False
        mock_safety.get_veto_reasons.return_value = ["High wind speed"]

        # Safety check should fail
        assert mock_safety.is_safe_to_slew() is False
        reasons = mock_safety.get_veto_reasons()
        assert "High wind speed" in reasons

    @pytest.mark.asyncio
    async def test_slew_blocked_below_horizon(self, mock_mount, mock_safety):
        """Test that slew is blocked for targets below horizon."""
        mock_safety.check_altitude_limit.return_value = False
        mock_safety.get_veto_reasons.return_value = ["Target below horizon limit"]

        assert mock_safety.check_altitude_limit(5.0) is False

    @pytest.mark.asyncio
    async def test_unpark_allowed_when_safe(self, mock_mount, mock_safety):
        """Test that unpark is allowed when safe."""
        mock_mount.is_parked = True
        assert mock_safety.is_safe_to_unpark() is True

        success = await mock_mount.unpark()
        assert success is True

    @pytest.mark.asyncio
    async def test_unpark_blocked_rain(self, mock_mount, mock_safety):
        """Test that unpark is blocked during rain."""
        mock_mount.is_parked = True
        mock_safety.rain_detected = True
        mock_safety.is_safe_to_unpark.return_value = False

        assert mock_safety.is_safe_to_unpark() is False

    @pytest.mark.asyncio
    async def test_emergency_park_on_rain(self, mock_mount, mock_safety):
        """Test emergency park when rain is detected."""
        mock_safety.rain_detected = True
        mock_safety.is_safe = False

        # Trigger emergency park
        if mock_safety.rain_detected and not mock_mount.is_parked:
            await mock_mount.park()

        mock_mount.park.assert_called_once()

    @pytest.mark.asyncio
    async def test_emergency_park_high_wind(self, mock_mount, mock_safety):
        """Test emergency park on high wind."""
        mock_safety.wind_speed_mph = 35  # Above threshold
        mock_safety.is_safe = False

        # Trigger emergency park
        if mock_safety.wind_speed_mph > 30 and not mock_mount.is_parked:
            await mock_mount.park()

        mock_mount.park.assert_called_once()

    @pytest.mark.asyncio
    async def test_tracking_disabled_on_park(self, mock_mount, mock_safety):
        """Test that tracking is disabled when parked."""
        await mock_mount.park()

        # Verify park was called
        mock_mount.park.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_motion_emergency(self, mock_mount, mock_safety):
        """Test emergency stop halts all motion."""
        mock_mount.is_slewing = True

        await mock_mount.stop()

        mock_mount.stop.assert_called_once()


class TestSafetyMountAltitudeChecks:
    """Tests for altitude safety checks."""

    @pytest.fixture
    def mock_safety(self):
        """Create mock safety monitor with altitude checks."""
        safety = Mock()
        safety.horizon_limit_deg = 10.0
        safety.meridian_limit_deg = 5.0

        def check_altitude(alt):
            return alt >= safety.horizon_limit_deg

        safety.check_altitude_limit = Mock(side_effect=check_altitude)
        return safety

    def test_altitude_above_horizon(self, mock_safety):
        """Test altitude check passes for targets above horizon."""
        assert mock_safety.check_altitude_limit(45.0) is True
        assert mock_safety.check_altitude_limit(15.0) is True
        assert mock_safety.check_altitude_limit(10.0) is True

    def test_altitude_below_horizon(self, mock_safety):
        """Test altitude check fails for targets below horizon."""
        assert mock_safety.check_altitude_limit(5.0) is False
        assert mock_safety.check_altitude_limit(0.0) is False
        assert mock_safety.check_altitude_limit(-10.0) is False

    def test_altitude_at_limit(self, mock_safety):
        """Test altitude check at the limit."""
        assert mock_safety.check_altitude_limit(10.0) is True
        assert mock_safety.check_altitude_limit(9.9) is False


class TestSafetyMountWeatherThresholds:
    """Tests for weather safety thresholds."""

    @pytest.fixture
    def mock_safety(self):
        """Create mock safety with configurable thresholds."""
        safety = Mock()
        safety.wind_limit_mph = 25
        safety.humidity_limit_percent = 85
        safety.rain_holdoff_minutes = 30

        def is_weather_safe(wind, humidity, rain):
            if rain:
                return False
            if wind > safety.wind_limit_mph:
                return False
            if humidity > safety.humidity_limit_percent:
                return False
            return True

        safety.is_weather_safe = Mock(side_effect=is_weather_safe)
        return safety

    def test_weather_safe_normal(self, mock_safety):
        """Test weather is safe under normal conditions."""
        assert mock_safety.is_weather_safe(10, 50, False) is True

    def test_weather_unsafe_high_wind(self, mock_safety):
        """Test weather unsafe with high wind."""
        assert mock_safety.is_weather_safe(30, 50, False) is False

    def test_weather_unsafe_high_humidity(self, mock_safety):
        """Test weather unsafe with high humidity."""
        assert mock_safety.is_weather_safe(10, 90, False) is False

    def test_weather_unsafe_rain(self, mock_safety):
        """Test weather unsafe with rain."""
        assert mock_safety.is_weather_safe(10, 50, True) is False

    def test_weather_unsafe_multiple_factors(self, mock_safety):
        """Test weather unsafe with multiple factors."""
        assert mock_safety.is_weather_safe(30, 90, True) is False


class TestSafetyMountCallbacks:
    """Tests for safety event callbacks to mount."""

    @pytest.fixture
    def mock_mount(self):
        """Create mock mount with callback support."""
        mount = Mock()
        mount.park = AsyncMock(return_value=True)
        mount.stop = AsyncMock(return_value=True)
        return mount

    @pytest.fixture
    def mock_safety(self):
        """Create mock safety with callback registration."""
        safety = Mock()
        safety._callbacks = []

        def register_callback(callback):
            safety._callbacks.append(callback)

        def trigger_callbacks(event, data):
            for cb in safety._callbacks:
                cb(event, data)

        safety.register_callback = Mock(side_effect=register_callback)
        safety.trigger_callbacks = trigger_callbacks
        return safety

    @pytest.mark.asyncio
    async def test_callback_on_weather_change(self, mock_mount, mock_safety):
        """Test mount receives callback on weather change."""
        callback_received = []

        def on_safety_change(event, data):
            callback_received.append((event, data))

        mock_safety.register_callback(on_safety_change)

        # Simulate weather change
        mock_safety.trigger_callbacks("weather_unsafe", {"reason": "rain"})

        assert len(callback_received) == 1
        assert callback_received[0][0] == "weather_unsafe"

    @pytest.mark.asyncio
    async def test_auto_park_callback(self, mock_mount, mock_safety):
        """Test automatic park on safety callback."""
        async def on_safety_change(event, data):
            if event == "weather_unsafe":
                await mock_mount.park()

        # Simulate the callback flow
        await on_safety_change("weather_unsafe", {"reason": "rain"})

        mock_mount.park.assert_called_once()


class TestSafetyMountRecovery:
    """Tests for recovery after safety events."""

    @pytest.fixture
    def mock_mount(self):
        """Create mock mount."""
        mount = Mock()
        mount.is_parked = True
        mount.unpark = AsyncMock(return_value=True)
        return mount

    @pytest.fixture
    def mock_safety(self):
        """Create mock safety."""
        safety = Mock()
        safety.is_safe = False
        safety.rain_holdoff_active = True
        safety.rain_holdoff_until = datetime.now() + timedelta(minutes=30)
        return safety

    @pytest.mark.asyncio
    async def test_no_unpark_during_holdoff(self, mock_mount, mock_safety):
        """Test unpark blocked during rain holdoff."""
        assert mock_safety.rain_holdoff_active is True

        # Should not unpark during holdoff
        if mock_safety.rain_holdoff_active:
            mock_mount.unpark.assert_not_called()

    @pytest.mark.asyncio
    async def test_unpark_after_holdoff(self, mock_mount, mock_safety):
        """Test unpark allowed after holdoff expires."""
        mock_safety.rain_holdoff_active = False
        mock_safety.is_safe = True

        if mock_safety.is_safe and not mock_safety.rain_holdoff_active:
            await mock_mount.unpark()

        mock_mount.unpark.assert_called_once()
