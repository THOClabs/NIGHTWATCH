"""
NIGHTWATCH Emergency Response Unit Tests

Step 491: Write unit tests for emergency response
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from nightwatch.emergency_response import (
    EmergencyResponse,
    EmergencyType,
    EmergencyState,
    AlertLevel,
    EmergencyEvent,
    EmergencyConfig,
    emergency_park_and_close,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def responder():
    """Create an emergency response instance without dependencies."""
    return EmergencyResponse()


@pytest.fixture
def config():
    """Create an emergency config instance."""
    return EmergencyConfig()


@pytest.fixture
def mock_mount():
    """Create a mock mount client."""
    mount = MagicMock()
    mount.stop = MagicMock()
    mount.park = MagicMock(return_value=True)
    mount.get_status = MagicMock(return_value=MagicMock(is_parked=True))
    return mount


@pytest.fixture
def mock_roof():
    """Create a mock roof controller."""
    roof = MagicMock()
    roof.close = AsyncMock(return_value=True)
    roof.get_state = MagicMock(return_value=MagicMock(value="closed"))
    return roof


@pytest.fixture
def configured_responder(mock_mount, mock_roof):
    """Create a responder with mock mount and roof."""
    return EmergencyResponse(
        mount_client=mock_mount,
        roof_controller=mock_roof,
    )


# ============================================================================
# EmergencyType Enum Tests
# ============================================================================

class TestEmergencyType:
    """Tests for EmergencyType enum."""

    def test_all_types_defined(self):
        """Verify all emergency types are defined."""
        assert EmergencyType.RAIN.value == "rain"
        assert EmergencyType.HIGH_WIND.value == "high_wind"
        assert EmergencyType.POWER_FAILURE.value == "power_failure"
        assert EmergencyType.LOW_BATTERY.value == "low_battery"
        assert EmergencyType.WEATHER_UNSAFE.value == "weather_unsafe"
        assert EmergencyType.COMMUNICATION_LOST.value == "communication_lost"
        assert EmergencyType.EQUIPMENT_FAILURE.value == "equipment_failure"
        assert EmergencyType.SENSOR_FAILURE.value == "sensor_failure"
        assert EmergencyType.USER_TRIGGERED.value == "user_triggered"


# ============================================================================
# EmergencyState Enum Tests
# ============================================================================

class TestEmergencyState:
    """Tests for EmergencyState enum."""

    def test_all_states_defined(self):
        """Verify all emergency states are defined."""
        assert EmergencyState.IDLE.value == "idle"
        assert EmergencyState.RESPONDING.value == "responding"
        assert EmergencyState.PARKING.value == "parking"
        assert EmergencyState.CLOSING.value == "closing"
        assert EmergencyState.ALERTING.value == "alerting"
        assert EmergencyState.COMPLETED.value == "completed"
        assert EmergencyState.FAILED.value == "failed"


# ============================================================================
# AlertLevel Enum Tests
# ============================================================================

class TestAlertLevel:
    """Tests for AlertLevel enum."""

    def test_all_levels_defined(self):
        """Verify all alert levels are defined."""
        assert AlertLevel.INFO.value == "info"
        assert AlertLevel.WARNING.value == "warning"
        assert AlertLevel.CRITICAL.value == "critical"
        assert AlertLevel.EMERGENCY.value == "emergency"


# ============================================================================
# EmergencyConfig Tests
# ============================================================================

class TestEmergencyConfig:
    """Tests for EmergencyConfig dataclass."""

    def test_default_config(self, config):
        """Verify default emergency configuration."""
        assert config.park_timeout == 60.0
        assert config.close_timeout == 45.0
        assert config.alert_timeout == 10.0
        assert config.max_park_retries == 3
        assert config.max_close_retries == 3
        assert config.retry_delay == 2.0

    def test_custom_config(self):
        """Verify custom emergency configuration."""
        config = EmergencyConfig(
            park_timeout=30.0,
            close_timeout=20.0,
            max_park_retries=5,
            enable_voice_alerts=False,
        )
        assert config.park_timeout == 30.0
        assert config.close_timeout == 20.0
        assert config.max_park_retries == 5
        assert config.enable_voice_alerts is False

    def test_escalation_delays(self, config):
        """Verify default escalation delay settings."""
        assert config.warning_to_critical_delay == 30.0
        assert config.critical_to_emergency_delay == 60.0


# ============================================================================
# EmergencyEvent Tests
# ============================================================================

class TestEmergencyEvent:
    """Tests for EmergencyEvent dataclass."""

    def test_event_creation(self):
        """Verify EmergencyEvent can be created."""
        event = EmergencyEvent(
            emergency_type=EmergencyType.RAIN,
            timestamp=datetime.now(),
            description="Rain detected",
        )
        assert event.emergency_type == EmergencyType.RAIN
        assert event.description == "Rain detected"
        assert event.state == EmergencyState.IDLE
        assert event.response_started is None
        assert event.response_completed is None
        assert event.alerts_sent == []
        assert event.actions_taken == []
        assert event.errors == []

    def test_event_with_actions(self):
        """Verify EmergencyEvent with actions and errors."""
        event = EmergencyEvent(
            emergency_type=EmergencyType.POWER_FAILURE,
            timestamp=datetime.now(),
            description="Power lost",
            state=EmergencyState.COMPLETED,
            actions_taken=["Mount parked", "Roof closed"],
            errors=["Warning: Low battery"],
        )
        assert len(event.actions_taken) == 2
        assert "Mount parked" in event.actions_taken
        assert len(event.errors) == 1


# ============================================================================
# EmergencyResponse Initialization Tests
# ============================================================================

class TestEmergencyResponseInit:
    """Tests for EmergencyResponse initialization."""

    def test_default_initialization(self, responder):
        """Verify responder initializes with defaults."""
        assert responder.state == EmergencyState.IDLE
        assert responder.is_responding is False
        assert responder._mount is None
        assert responder._roof is None
        assert responder._safety is None

    def test_initialization_with_config(self):
        """Verify responder initializes with custom config."""
        config = EmergencyConfig(park_timeout=30.0)
        responder = EmergencyResponse(config=config)
        assert responder.config.park_timeout == 30.0

    def test_initialization_with_dependencies(self, mock_mount, mock_roof):
        """Verify responder initializes with dependencies."""
        responder = EmergencyResponse(
            mount_client=mock_mount,
            roof_controller=mock_roof,
        )
        assert responder._mount is mock_mount
        assert responder._roof is mock_roof


# ============================================================================
# EmergencyResponse Properties Tests
# ============================================================================

class TestEmergencyResponseProperties:
    """Tests for EmergencyResponse properties."""

    def test_state_property(self, responder):
        """Verify state property."""
        assert responder.state == EmergencyState.IDLE
        responder._state = EmergencyState.RESPONDING
        assert responder.state == EmergencyState.RESPONDING

    def test_is_responding_false_when_idle(self, responder):
        """Verify is_responding is False when idle."""
        responder._state = EmergencyState.IDLE
        assert responder.is_responding is False

    def test_is_responding_false_when_completed(self, responder):
        """Verify is_responding is False when completed."""
        responder._state = EmergencyState.COMPLETED
        assert responder.is_responding is False

    def test_is_responding_false_when_failed(self, responder):
        """Verify is_responding is False when failed."""
        responder._state = EmergencyState.FAILED
        assert responder.is_responding is False

    def test_is_responding_true_when_responding(self, responder):
        """Verify is_responding is True when responding."""
        responder._state = EmergencyState.RESPONDING
        assert responder.is_responding is True

    def test_is_responding_true_when_parking(self, responder):
        """Verify is_responding is True when parking."""
        responder._state = EmergencyState.PARKING
        assert responder.is_responding is True


# ============================================================================
# Alert Callback Tests
# ============================================================================

class TestAlertCallbacks:
    """Tests for alert callback registration."""

    def test_register_alert_callback(self, responder):
        """Verify alert callback registration."""
        callback = MagicMock()
        responder.register_alert_callback(AlertLevel.WARNING, callback)
        assert callback in responder._alert_callbacks[AlertLevel.WARNING]

    def test_register_multiple_callbacks(self, responder):
        """Verify multiple callbacks can be registered."""
        callback1 = MagicMock()
        callback2 = MagicMock()
        responder.register_alert_callback(AlertLevel.CRITICAL, callback1)
        responder.register_alert_callback(AlertLevel.CRITICAL, callback2)
        assert len(responder._alert_callbacks[AlertLevel.CRITICAL]) == 2


# ============================================================================
# Emergency Park Tests
# ============================================================================

class TestEmergencyPark:
    """Tests for emergency park functionality."""

    @pytest.mark.asyncio
    async def test_emergency_park_no_mount(self, responder):
        """Verify emergency_park returns False without mount."""
        result = await responder.emergency_park()
        assert result is False

    @pytest.mark.asyncio
    async def test_emergency_park_success(self, configured_responder, mock_mount):
        """Verify emergency_park succeeds with mock mount."""
        result = await configured_responder.emergency_park()
        assert result is True
        mock_mount.stop.assert_called()
        mock_mount.park.assert_called()

    @pytest.mark.asyncio
    async def test_emergency_park_records_action(self, configured_responder):
        """Verify emergency_park records action in event."""
        configured_responder._current_event = EmergencyEvent(
            emergency_type=EmergencyType.RAIN,
            timestamp=datetime.now(),
            description="Test",
        )
        await configured_responder.emergency_park()
        assert "Mount parked" in configured_responder._current_event.actions_taken


# ============================================================================
# Emergency Close Tests
# ============================================================================

class TestEmergencyClose:
    """Tests for emergency close functionality."""

    @pytest.mark.asyncio
    async def test_emergency_close_no_roof(self, responder):
        """Verify emergency_close returns False without roof."""
        result = await responder.emergency_close()
        assert result is False

    @pytest.mark.asyncio
    async def test_emergency_close_success(self, configured_responder, mock_roof):
        """Verify emergency_close succeeds with mock roof."""
        result = await configured_responder.emergency_close()
        assert result is True
        mock_roof.close.assert_called()


# ============================================================================
# Rain Response Tests
# ============================================================================

class TestRainResponse:
    """Tests for rain emergency response."""

    @pytest.mark.asyncio
    async def test_respond_to_rain_creates_event(self, configured_responder):
        """Verify respond_to_rain creates an event."""
        await configured_responder.respond_to_rain()
        assert len(configured_responder._event_history) == 1
        event = configured_responder._event_history[0]
        assert event.emergency_type == EmergencyType.RAIN

    @pytest.mark.asyncio
    async def test_respond_to_rain_changes_state(self, configured_responder):
        """Verify respond_to_rain changes state."""
        await configured_responder.respond_to_rain()
        assert configured_responder.state in (
            EmergencyState.COMPLETED,
            EmergencyState.FAILED,
        )


# ============================================================================
# Weather Response Tests
# ============================================================================

class TestWeatherResponse:
    """Tests for weather emergency response."""

    @pytest.mark.asyncio
    async def test_respond_to_weather_storm(self, configured_responder):
        """Verify respond_to_weather handles storm condition."""
        await configured_responder.respond_to_weather("storm")
        assert len(configured_responder._event_history) == 1
        event = configured_responder._event_history[0]
        assert event.emergency_type == EmergencyType.WEATHER_UNSAFE

    @pytest.mark.asyncio
    async def test_respond_to_weather_high_wind(self, configured_responder):
        """Verify respond_to_weather detects wind condition."""
        await configured_responder.respond_to_weather("high_wind")
        event = configured_responder._event_history[0]
        assert event.emergency_type == EmergencyType.HIGH_WIND


# ============================================================================
# Generic Emergency Response Tests
# ============================================================================

class TestGenericEmergencyResponse:
    """Tests for generic emergency response."""

    @pytest.mark.asyncio
    async def test_respond_to_emergency_routes_rain(self, configured_responder):
        """Verify respond_to_emergency routes rain to respond_to_rain."""
        await configured_responder.respond_to_emergency(EmergencyType.RAIN)
        event = configured_responder._event_history[0]
        assert event.emergency_type == EmergencyType.RAIN

    @pytest.mark.asyncio
    async def test_respond_to_emergency_generic(self, configured_responder):
        """Verify respond_to_emergency handles generic emergencies."""
        await configured_responder.respond_to_emergency(
            EmergencyType.EQUIPMENT_FAILURE,
            "Camera disconnected",
        )
        event = configured_responder._event_history[0]
        assert event.emergency_type == EmergencyType.EQUIPMENT_FAILURE
        assert "Camera disconnected" in event.description


# ============================================================================
# Status and History Tests
# ============================================================================

class TestStatusAndHistory:
    """Tests for status and history retrieval."""

    def test_get_status_idle(self, responder):
        """Verify get_status returns idle state."""
        status = responder.get_status()
        assert status["state"] == "idle"
        assert status["is_responding"] is False
        assert status["current_event"] is None
        assert status["event_count"] == 0

    @pytest.mark.asyncio
    async def test_get_event_history(self, configured_responder):
        """Verify get_event_history returns events."""
        await configured_responder.respond_to_rain()
        history = configured_responder.get_event_history()
        assert len(history) == 1
        assert history[0]["type"] == "rain"

    @pytest.mark.asyncio
    async def test_get_event_history_limit(self, configured_responder):
        """Verify get_event_history respects limit."""
        for _ in range(5):
            await configured_responder.respond_to_rain()
        history = configured_responder.get_event_history(limit=3)
        assert len(history) == 3

    def test_reset(self, responder):
        """Verify reset returns to idle state."""
        responder._state = EmergencyState.RESPONDING
        responder._current_event = EmergencyEvent(
            emergency_type=EmergencyType.RAIN,
            timestamp=datetime.now(),
            description="Test",
        )
        responder.reset()
        assert responder.state == EmergencyState.IDLE
        assert responder._current_event is None


# ============================================================================
# Alert Escalation Tests
# ============================================================================

class TestAlertEscalation:
    """Tests for alert escalation."""

    @pytest.mark.asyncio
    async def test_escalate_info_to_warning(self, responder):
        """Verify escalation from INFO to WARNING."""
        new_level = await responder.escalate_alert(
            AlertLevel.INFO,
            "Test message",
            EmergencyType.RAIN,
        )
        assert new_level == AlertLevel.WARNING

    @pytest.mark.asyncio
    async def test_escalate_warning_to_critical(self, responder):
        """Verify escalation from WARNING to CRITICAL."""
        new_level = await responder.escalate_alert(
            AlertLevel.WARNING,
            "Test message",
            EmergencyType.RAIN,
        )
        assert new_level == AlertLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_escalate_critical_to_emergency(self, responder):
        """Verify escalation from CRITICAL to EMERGENCY."""
        new_level = await responder.escalate_alert(
            AlertLevel.CRITICAL,
            "Test message",
            EmergencyType.RAIN,
        )
        assert new_level == AlertLevel.EMERGENCY

    @pytest.mark.asyncio
    async def test_escalate_emergency_stays_emergency(self, responder):
        """Verify EMERGENCY level doesn't escalate further."""
        new_level = await responder.escalate_alert(
            AlertLevel.EMERGENCY,
            "Test message",
            EmergencyType.RAIN,
        )
        assert new_level == AlertLevel.EMERGENCY


# ============================================================================
# Convenience Function Tests
# ============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.mark.asyncio
    async def test_emergency_park_and_close_no_deps(self):
        """Verify emergency_park_and_close works without dependencies."""
        result = await emergency_park_and_close()
        # Should return True since no mount/roof to fail
        assert result is True

    @pytest.mark.asyncio
    async def test_emergency_park_and_close_with_deps(self, mock_mount, mock_roof):
        """Verify emergency_park_and_close works with dependencies."""
        result = await emergency_park_and_close(
            mount_client=mock_mount,
            roof_controller=mock_roof,
        )
        assert result is True


# ============================================================================
# Run Configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
