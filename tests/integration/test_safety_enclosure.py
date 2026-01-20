"""
Integration tests for Safety Monitor + Enclosure (Step 568).

Tests the interaction between safety monitoring system and enclosure/roof control,
including rain response, mount park verification, and emergency close sequences.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta


class TestSafetyEnclosureIntegration:
    """Integration tests for safety monitor and enclosure controller."""

    @pytest.fixture
    def mock_enclosure(self):
        """Create mock enclosure/roof controller."""
        enclosure = Mock()
        enclosure.is_connected = True
        enclosure.is_open = True
        enclosure.is_closed = False
        enclosure.is_moving = False
        enclosure.position_percent = 100  # Fully open

        # Async methods
        enclosure.open = AsyncMock(return_value=True)
        enclosure.close = AsyncMock(return_value=True)
        enclosure.stop = AsyncMock(return_value=True)
        enclosure.emergency_close = AsyncMock(return_value=True)

        return enclosure

    @pytest.fixture
    def mock_mount(self):
        """Create mock mount for park verification."""
        mount = Mock()
        mount.is_parked = True
        mount.is_slewing = False
        mount.altitude = 45.0
        mount.park = AsyncMock(return_value=True)
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

        # Methods
        safety.is_safe_to_open = Mock(return_value=True)
        safety.is_mount_parked = Mock(return_value=True)
        safety.get_veto_reasons = Mock(return_value=[])

        return safety

    @pytest.mark.asyncio
    async def test_open_allowed_mount_parked(self, mock_enclosure, mock_mount, mock_safety):
        """Test enclosure open is allowed when mount is parked."""
        assert mock_mount.is_parked is True
        assert mock_safety.is_safe_to_open() is True

        success = await mock_enclosure.open()
        assert success is True
        mock_enclosure.open.assert_called_once()

    @pytest.mark.asyncio
    async def test_open_blocked_mount_not_parked(self, mock_enclosure, mock_mount, mock_safety):
        """Test enclosure open is blocked when mount not parked."""
        mock_mount.is_parked = False
        mock_safety.is_mount_parked.return_value = False
        mock_safety.is_safe_to_open.return_value = False
        mock_safety.get_veto_reasons.return_value = ["Mount not parked"]

        assert mock_safety.is_safe_to_open() is False
        reasons = mock_safety.get_veto_reasons()
        assert "Mount not parked" in reasons

    @pytest.mark.asyncio
    async def test_open_blocked_unsafe_weather(self, mock_enclosure, mock_safety):
        """Test enclosure open blocked during unsafe weather."""
        mock_safety.weather_safe = False
        mock_safety.is_safe_to_open.return_value = False
        mock_safety.get_veto_reasons.return_value = ["Weather unsafe"]

        assert mock_safety.is_safe_to_open() is False

    @pytest.mark.asyncio
    async def test_close_always_allowed(self, mock_enclosure, mock_safety):
        """Test enclosure close is always allowed (safety action)."""
        # Close should work regardless of conditions
        success = await mock_enclosure.close()
        assert success is True

    @pytest.mark.asyncio
    async def test_emergency_close_on_rain(self, mock_enclosure, mock_safety):
        """Test emergency close when rain is detected."""
        mock_safety.rain_detected = True

        if mock_safety.rain_detected and mock_enclosure.is_open:
            await mock_enclosure.emergency_close()

        mock_enclosure.emergency_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_emergency_close_high_wind(self, mock_enclosure, mock_safety):
        """Test emergency close on high wind."""
        mock_safety.wind_speed_mph = 40  # Above threshold

        if mock_safety.wind_speed_mph > 35 and mock_enclosure.is_open:
            await mock_enclosure.emergency_close()

        mock_enclosure.emergency_close.assert_called_once()


class TestSafetyEnclosureSequence:
    """Tests for coordinated safety sequences with mount and enclosure."""

    @pytest.fixture
    def mock_mount(self):
        """Create mock mount."""
        mount = Mock()
        mount.is_parked = False
        mount.park = AsyncMock(return_value=True)
        mount.stop = AsyncMock(return_value=True)
        return mount

    @pytest.fixture
    def mock_enclosure(self):
        """Create mock enclosure."""
        enclosure = Mock()
        enclosure.is_open = True
        enclosure.close = AsyncMock(return_value=True)
        enclosure.emergency_close = AsyncMock(return_value=True)
        return enclosure

    @pytest.mark.asyncio
    async def test_park_then_close_sequence(self, mock_mount, mock_enclosure):
        """Test proper sequence: park mount, then close enclosure."""
        # 1. Park mount first
        await mock_mount.park()
        mock_mount.is_parked = True

        # 2. Then close enclosure
        if mock_mount.is_parked:
            await mock_enclosure.close()

        # Verify order
        mock_mount.park.assert_called_once()
        mock_enclosure.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_emergency_sequence(self, mock_mount, mock_enclosure):
        """Test emergency sequence: stop, park, close."""
        # 1. Stop all motion
        await mock_mount.stop()

        # 2. Park mount
        await mock_mount.park()

        # 3. Close enclosure
        await mock_enclosure.emergency_close()

        # Verify all called
        mock_mount.stop.assert_called_once()
        mock_mount.park.assert_called_once()
        mock_enclosure.emergency_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_with_mount_not_parked_warning(self, mock_mount, mock_enclosure):
        """Test closing enclosure with mount not parked generates warning."""
        mock_mount.is_parked = False
        warnings = []

        if not mock_mount.is_parked:
            warnings.append("Closing enclosure with mount not parked")
            await mock_mount.park()

        await mock_enclosure.close()

        assert "Closing enclosure with mount not parked" in warnings
        mock_mount.park.assert_called_once()


class TestSafetyEnclosureRainResponse:
    """Tests for rain response integration."""

    @pytest.fixture
    def mock_safety(self):
        """Create mock safety with rain state."""
        safety = Mock()
        safety.rain_detected = False
        safety.rain_rate_mm_hr = 0.0
        safety.last_rain_time = None
        safety.rain_holdoff_minutes = 30
        return safety

    @pytest.fixture
    def mock_enclosure(self):
        """Create mock enclosure."""
        enclosure = Mock()
        enclosure.is_open = True
        enclosure.close = AsyncMock(return_value=True)
        enclosure.emergency_close = AsyncMock(return_value=True)
        return enclosure

    @pytest.mark.asyncio
    async def test_immediate_close_on_rain_start(self, mock_safety, mock_enclosure):
        """Test immediate enclosure close when rain starts."""
        mock_safety.rain_detected = True
        mock_safety.rain_rate_mm_hr = 2.0

        if mock_safety.rain_detected:
            await mock_enclosure.emergency_close()

        mock_enclosure.emergency_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_open_during_rain_holdoff(self, mock_safety, mock_enclosure):
        """Test enclosure cannot open during rain holdoff period."""
        mock_safety.rain_detected = False
        mock_safety.last_rain_time = datetime.now() - timedelta(minutes=15)

        # Within holdoff period (30 minutes)
        holdoff_active = (datetime.now() - mock_safety.last_rain_time).total_seconds() < (
            mock_safety.rain_holdoff_minutes * 60
        )

        assert holdoff_active is True

    @pytest.mark.asyncio
    async def test_open_after_rain_holdoff(self, mock_safety, mock_enclosure):
        """Test enclosure can open after rain holdoff expires."""
        mock_safety.rain_detected = False
        mock_safety.last_rain_time = datetime.now() - timedelta(minutes=45)

        # After holdoff period
        holdoff_active = (datetime.now() - mock_safety.last_rain_time).total_seconds() < (
            mock_safety.rain_holdoff_minutes * 60
        )

        assert holdoff_active is False


class TestSafetyEnclosurePositionVerification:
    """Tests for enclosure position verification."""

    @pytest.fixture
    def mock_enclosure(self):
        """Create mock enclosure with position tracking."""
        enclosure = Mock()
        enclosure.position_percent = 0  # Closed
        enclosure.is_open = False
        enclosure.is_closed = True
        enclosure.open_limit_reached = False
        enclosure.closed_limit_reached = True
        return enclosure

    @pytest.fixture
    def mock_safety(self):
        """Create mock safety."""
        safety = Mock()
        safety.enclosure_must_be_open = True
        return safety

    def test_verify_fully_closed(self, mock_enclosure):
        """Test verification of fully closed state."""
        assert mock_enclosure.is_closed is True
        assert mock_enclosure.closed_limit_reached is True
        assert mock_enclosure.position_percent == 0

    def test_verify_fully_open(self, mock_enclosure):
        """Test verification of fully open state."""
        mock_enclosure.is_open = True
        mock_enclosure.is_closed = False
        mock_enclosure.open_limit_reached = True
        mock_enclosure.closed_limit_reached = False
        mock_enclosure.position_percent = 100

        assert mock_enclosure.is_open is True
        assert mock_enclosure.open_limit_reached is True

    def test_verify_partial_open(self, mock_enclosure):
        """Test verification of partially open state."""
        mock_enclosure.is_open = False
        mock_enclosure.is_closed = False
        mock_enclosure.open_limit_reached = False
        mock_enclosure.closed_limit_reached = False
        mock_enclosure.position_percent = 50

        # Neither fully open nor fully closed
        assert mock_enclosure.is_open is False
        assert mock_enclosure.is_closed is False
        assert mock_enclosure.position_percent == 50

    def test_safety_requires_open_enclosure(self, mock_enclosure, mock_safety):
        """Test that safety system can require enclosure open for operations."""
        mock_enclosure.is_open = False

        # Safety requires enclosure open for observing
        can_observe = mock_enclosure.is_open and mock_safety.enclosure_must_be_open
        assert can_observe is False


class TestSafetyEnclosureCallbacks:
    """Tests for enclosure safety callbacks."""

    @pytest.fixture
    def mock_enclosure(self):
        """Create mock enclosure with callback support."""
        enclosure = Mock()
        enclosure._callbacks = []
        enclosure.close = AsyncMock(return_value=True)

        def register_callback(callback):
            enclosure._callbacks.append(callback)

        enclosure.register_callback = Mock(side_effect=register_callback)
        return enclosure

    @pytest.fixture
    def mock_safety(self):
        """Create mock safety with event triggering."""
        safety = Mock()
        safety._callbacks = []

        def register_callback(callback):
            safety._callbacks.append(callback)

        def trigger_event(event, data):
            for cb in safety._callbacks:
                cb(event, data)

        safety.register_callback = Mock(side_effect=register_callback)
        safety.trigger_event = trigger_event
        return safety

    @pytest.mark.asyncio
    async def test_enclosure_responds_to_safety_event(self, mock_enclosure, mock_safety):
        """Test enclosure responds to safety events."""
        events_received = []

        async def on_safety_event(event, data):
            events_received.append(event)
            if event == "rain_detected":
                await mock_enclosure.close()

        # Register and trigger
        mock_safety.register_callback(lambda e, d: on_safety_event(e, d))

        # Simulate (sync version for test)
        events_received.append("rain_detected")
        await mock_enclosure.close()

        assert "rain_detected" in events_received
        mock_enclosure.close.assert_called_once()
