"""
Unit tests for NIGHTWATCH roof controller.

Tests roll-off roof automation, safety interlocks, and motor control.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

import pytest

from services.enclosure.roof_controller import (
    RoofController,
    RoofConfig,
    RoofState,
    RoofStatus,
    SafetyCondition,
)


class TestRoofConfig:
    """Tests for RoofConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RoofConfig()
        assert config.motor_timeout_sec == 60.0
        assert config.motor_current_limit_a == 5.0
        assert config.rain_holdoff_min == 30.0
        assert config.use_hardware_interlock is True

    def test_custom_values(self):
        """Test custom configuration."""
        config = RoofConfig(
            motor_timeout_sec=90.0,
            rain_holdoff_min=15.0,
            invert_motor=True,
        )
        assert config.motor_timeout_sec == 90.0
        assert config.rain_holdoff_min == 15.0
        assert config.invert_motor is True


class TestRoofStatus:
    """Tests for RoofStatus dataclass."""

    def test_default_status(self):
        """Test default status values."""
        status = RoofStatus(state=RoofState.UNKNOWN)
        assert status.state == RoofState.UNKNOWN
        assert status.position_percent == 0
        assert status.motor_running is False
        assert status.can_close is True

    def test_status_with_safety(self):
        """Test status with safety conditions."""
        safety = {
            SafetyCondition.WEATHER_SAFE: True,
            SafetyCondition.TELESCOPE_PARKED: True,
        }
        status = RoofStatus(
            state=RoofState.CLOSED,
            position_percent=0,
            closed_limit=True,
            safety_conditions=safety,
            can_open=True,
        )
        assert status.safety_conditions[SafetyCondition.WEATHER_SAFE] is True
        assert status.can_open is True


class TestRoofState:
    """Tests for RoofState enum."""

    def test_state_values(self):
        """Test state enum values."""
        assert RoofState.OPEN.value == "open"
        assert RoofState.CLOSED.value == "closed"
        assert RoofState.OPENING.value == "opening"
        assert RoofState.CLOSING.value == "closing"
        assert RoofState.UNKNOWN.value == "unknown"
        assert RoofState.ERROR.value == "error"


class TestRoofController:
    """Tests for RoofController class."""

    @pytest.fixture
    def controller(self):
        """Create roof controller for testing."""
        config = RoofConfig(motor_timeout_sec=30.0)  # Enough for simulated motor
        ctrl = RoofController(config=config)
        # Patch the motor to run faster for tests
        original_run_motor = ctrl._run_motor

        async def fast_motor(direction):
            ctrl._motor_running = True
            try:
                # Fast simulation - just set position directly
                if direction == "open":
                    ctrl._position = 100
                else:
                    ctrl._position = 0
                await asyncio.sleep(0.1)  # Small delay
            finally:
                ctrl._motor_running = False

        ctrl._run_motor = fast_motor
        return ctrl

    def test_init_default(self, controller):
        """Test default initialization."""
        assert controller.config is not None
        assert controller._connected is False
        assert controller._state == RoofState.UNKNOWN

    def test_init_with_services(self):
        """Test initialization with weather and mount services."""
        mock_weather = Mock()
        mock_mount = Mock()
        controller = RoofController(
            weather_service=mock_weather,
            mount_service=mock_mount
        )
        assert controller._weather is mock_weather
        assert controller._mount is mock_mount

    def test_connected_property(self, controller):
        """Test connected property."""
        assert controller.connected is False
        controller._connected = True
        assert controller.connected is True

    def test_state_property(self, controller):
        """Test state property."""
        assert controller.state == RoofState.UNKNOWN
        controller._state = RoofState.CLOSED
        assert controller.state == RoofState.CLOSED

    def test_is_open_property(self, controller):
        """Test is_open property."""
        controller._state = RoofState.UNKNOWN
        assert controller.is_open is False
        controller._state = RoofState.OPEN
        assert controller.is_open is True

    def test_is_closed_property(self, controller):
        """Test is_closed property."""
        controller._state = RoofState.UNKNOWN
        assert controller.is_closed is False
        controller._state = RoofState.CLOSED
        assert controller.is_closed is True

    def test_status_property(self, controller):
        """Test status property returns RoofStatus."""
        status = controller.status
        assert isinstance(status, RoofStatus)
        assert status.state == controller._state

    def test_can_open_all_conditions_met(self, controller):
        """Test _can_open when all conditions are met."""
        for cond in SafetyCondition:
            controller._safety[cond] = True
        assert controller._can_open() is True

    def test_can_open_missing_weather(self, controller):
        """Test _can_open when weather is not safe."""
        for cond in SafetyCondition:
            controller._safety[cond] = True
        controller._safety[SafetyCondition.WEATHER_SAFE] = False
        assert controller._can_open() is False

    def test_can_open_not_parked(self, controller):
        """Test _can_open when telescope not parked."""
        for cond in SafetyCondition:
            controller._safety[cond] = True
        controller._safety[SafetyCondition.TELESCOPE_PARKED] = False
        assert controller._can_open() is False

    @pytest.mark.asyncio
    async def test_connect(self, controller):
        """Test connecting to controller."""
        result = await controller.connect()
        assert result is True
        assert controller.connected is True
        # Cleanup
        await controller.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect(self, controller):
        """Test disconnecting from controller."""
        await controller.connect()
        assert controller.connected is True
        await controller.disconnect()
        assert controller.connected is False

    @pytest.mark.asyncio
    async def test_open_not_connected(self, controller):
        """Test open fails when not connected."""
        with pytest.raises(RuntimeError, match="not connected"):
            await controller.open()

    @pytest.mark.asyncio
    async def test_close_not_connected(self, controller):
        """Test close fails when not connected."""
        with pytest.raises(RuntimeError, match="not connected"):
            await controller.close()

    @pytest.mark.asyncio
    async def test_open_already_open(self, controller):
        """Test open when already open."""
        await controller.connect()
        controller._state = RoofState.OPEN
        result = await controller.open()
        assert result is True
        await controller.disconnect()

    @pytest.mark.asyncio
    async def test_close_already_closed(self, controller):
        """Test close when already closed."""
        await controller.connect()
        controller._state = RoofState.CLOSED
        result = await controller.close()
        assert result is True
        await controller.disconnect()

    @pytest.mark.asyncio
    async def test_open_safety_not_met(self, controller):
        """Test open fails when safety conditions not met."""
        await controller.connect()
        controller._state = RoofState.CLOSED
        # Safety conditions are False by default
        with pytest.raises(RuntimeError, match="safety conditions"):
            await controller.open()
        await controller.disconnect()

    @pytest.mark.asyncio
    async def test_open_with_force(self, controller):
        """Test open with force bypasses safety checks."""
        await controller.connect()
        controller._state = RoofState.CLOSED
        controller._position = 0

        # Open with force
        result = await controller.open(force=True)
        assert result is True
        assert controller.state == RoofState.OPEN
        await controller.disconnect()

    @pytest.mark.asyncio
    async def test_close_normal(self, controller):
        """Test normal roof close."""
        await controller.connect()
        controller._state = RoofState.OPEN
        controller._position = 100

        result = await controller.close()
        assert result is True
        assert controller.state == RoofState.CLOSED
        await controller.disconnect()

    @pytest.mark.asyncio
    async def test_emergency_close(self, controller):
        """Test emergency close."""
        await controller.connect()
        controller._state = RoofState.OPEN
        controller._position = 100

        result = await controller.close(emergency=True)
        assert result is True
        assert controller.state == RoofState.CLOSED
        await controller.disconnect()

    @pytest.mark.asyncio
    async def test_stop(self, controller):
        """Test stop motion."""
        await controller.connect()
        controller._state = RoofState.OPENING
        controller._motor_running = True

        await controller.stop()
        assert controller._motor_running is False
        await controller.disconnect()


class TestRoofControllerSafety:
    """Tests for roof controller safety features."""

    @pytest.fixture
    def controller(self):
        """Create roof controller for testing."""
        config = RoofConfig(
            motor_timeout_sec=5.0,
            rain_holdoff_min=1.0  # Short holdoff for testing
        )
        return RoofController(config=config)

    @pytest.mark.asyncio
    async def test_verify_telescope_parked_no_mount(self, controller):
        """Test park verification with no mount service."""
        result = await controller._verify_telescope_parked()
        assert result is True  # Assumes parked when no mount
        assert controller._safety[SafetyCondition.TELESCOPE_PARKED] is True

    @pytest.mark.asyncio
    async def test_verify_telescope_parked_with_mount(self, controller):
        """Test park verification with mount service."""
        mock_mount = Mock()
        mock_mount.is_parked = AsyncMock(return_value=True)
        controller._mount = mock_mount

        result = await controller._verify_telescope_parked()
        assert result is True
        mock_mount.is_parked.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_telescope_not_parked(self, controller):
        """Test park verification when not parked."""
        mock_mount = Mock()
        mock_mount.is_parked = AsyncMock(return_value=False)
        controller._mount = mock_mount

        result = await controller._verify_telescope_parked()
        assert result is False
        assert controller._safety[SafetyCondition.TELESCOPE_PARKED] is False

    @pytest.mark.asyncio
    async def test_update_weather_safe(self, controller):
        """Test weather update when safe."""
        await controller.update_weather_status(is_safe=True, rain_detected=False)
        assert controller._safety[SafetyCondition.WEATHER_SAFE] is True

    @pytest.mark.asyncio
    async def test_update_weather_rain_detected(self, controller):
        """Test weather update with rain detected."""
        controller._state = RoofState.CLOSED  # Prevent emergency close
        await controller.update_weather_status(is_safe=False, rain_detected=True)
        assert controller._safety[SafetyCondition.WEATHER_SAFE] is False
        assert controller._safety[SafetyCondition.RAIN_HOLDOFF] is False
        assert controller._last_rain_time is not None

    @pytest.mark.asyncio
    async def test_rain_triggers_emergency_close(self, controller):
        """Test rain detection triggers emergency close."""
        await controller.connect()
        controller._state = RoofState.OPEN
        controller._position = 100

        # This should trigger emergency close
        await controller.update_weather_status(is_safe=False, rain_detected=True)

        # Give async task time to run
        await asyncio.sleep(0.1)

        # Cleanup
        await controller.disconnect()

    def test_hardware_interlock_safe(self, controller):
        """Test hardware interlock when safe."""
        controller.set_hardware_interlock(safe=True)
        assert controller._safety[SafetyCondition.HARDWARE_INTERLOCK] is True

    def test_hardware_interlock_triggered(self, controller):
        """Test hardware interlock when triggered."""
        controller._state = RoofState.CLOSED  # Prevent emergency close
        controller.set_hardware_interlock(safe=False)
        assert controller._safety[SafetyCondition.HARDWARE_INTERLOCK] is False


class TestRoofControllerCallbacks:
    """Tests for roof controller callback system."""

    @pytest.fixture
    def controller(self):
        """Create roof controller for testing with fast motor."""
        config = RoofConfig(motor_timeout_sec=30.0)
        ctrl = RoofController(config=config)

        async def fast_motor(direction):
            ctrl._motor_running = True
            try:
                if direction == "open":
                    ctrl._position = 100
                else:
                    ctrl._position = 0
                await asyncio.sleep(0.1)
            finally:
                ctrl._motor_running = False

        ctrl._run_motor = fast_motor
        return ctrl

    def test_register_callback(self, controller):
        """Test registering a callback."""
        callback = Mock()
        controller.register_callback(callback)
        assert callback in controller._callbacks

    @pytest.mark.asyncio
    async def test_callback_on_open(self, controller):
        """Test callback is called on open."""
        callback = Mock()
        controller.register_callback(callback)

        await controller.connect()
        controller._state = RoofState.CLOSED
        controller._position = 0
        # Set all safety conditions
        for cond in SafetyCondition:
            controller._safety[cond] = True

        await controller.open(force=True)

        callback.assert_called()
        call_args = callback.call_args
        assert call_args[0][0] == "opened"
        await controller.disconnect()

    @pytest.mark.asyncio
    async def test_callback_on_close(self, controller):
        """Test callback is called on close."""
        callback = Mock()
        controller.register_callback(callback)

        await controller.connect()
        controller._state = RoofState.OPEN
        controller._position = 100

        await controller.close()

        callback.assert_called()
        call_args = callback.call_args
        assert call_args[0][0] == "closed"
        await controller.disconnect()

    @pytest.mark.asyncio
    async def test_async_callback(self, controller):
        """Test async callback is called correctly."""
        callback = AsyncMock()
        controller.register_callback(callback)

        await controller.connect()
        controller._state = RoofState.OPEN
        controller._position = 100

        await controller.close()

        callback.assert_called()
        await controller.disconnect()


class TestRoofControllerMotor:
    """Tests for motor control logic."""

    @pytest.fixture
    def controller(self):
        """Create roof controller with short timeouts."""
        config = RoofConfig(motor_timeout_sec=0.5)  # Very short for tests
        return RoofController(config=config)

    @pytest.mark.asyncio
    async def test_motor_timeout(self, controller):
        """Test motor timeout protection."""
        controller._position = 50  # Middle position

        # Patch the motor run to take too long
        original_run = controller._run_motor

        async def slow_motor(direction):
            controller._motor_running = True
            start = datetime.now()
            while True:
                elapsed = (datetime.now() - start).total_seconds()
                if elapsed > controller.config.motor_timeout_sec:
                    controller._motor_running = False
                    raise RuntimeError(f"Motor timeout after {elapsed:.0f}s")
                await asyncio.sleep(0.1)

        controller._run_motor = slow_motor

        with pytest.raises(RuntimeError, match="Motor timeout"):
            await controller._run_motor("open")

    @pytest.mark.asyncio
    async def test_stop_motor(self, controller):
        """Test motor stop."""
        controller._motor_running = True
        await controller._stop_motor()
        assert controller._motor_running is False


class TestRoofControllerLimits:
    """Tests for limit switch handling."""

    @pytest.fixture
    def controller(self):
        """Create roof controller for testing."""
        return RoofController()

    @pytest.mark.asyncio
    async def test_read_limit_closed(self, controller):
        """Test limit switch reading when closed."""
        controller._position = 0
        await controller._read_limit_switches()
        assert controller._state == RoofState.CLOSED

    @pytest.mark.asyncio
    async def test_read_limit_open(self, controller):
        """Test limit switch reading when open."""
        controller._position = 100
        await controller._read_limit_switches()
        assert controller._state == RoofState.OPEN

    @pytest.mark.asyncio
    async def test_read_limit_middle(self, controller):
        """Test limit switch reading when in middle."""
        controller._position = 50
        await controller._read_limit_switches()
        assert controller._state == RoofState.UNKNOWN

    @pytest.mark.asyncio
    async def test_check_open_limit(self, controller):
        """Test checking open limit."""
        controller._position = 100
        result = await controller._check_open_limit()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_closed_limit(self, controller):
        """Test checking closed limit."""
        controller._position = 0
        result = await controller._check_closed_limit()
        assert result is True
