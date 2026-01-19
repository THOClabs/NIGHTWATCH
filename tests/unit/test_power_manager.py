"""
Unit tests for NIGHTWATCH power management service.

Tests NUT client protocol, UPS status parsing, and threshold logic.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import socket

import pytest

from services.power.power_manager import (
    NUTClient,
    PowerManager,
    PowerConfig,
    PowerState,
    UPSStatus,
    PowerEvent,
    ShutdownReason,
)


class TestNUTClient:
    """Tests for NUT client protocol implementation."""

    def test_init_default_values(self):
        """Test default initialization values."""
        client = NUTClient()
        assert client.host == "localhost"
        assert client.port == 3493
        assert client.timeout == 10.0

    def test_init_custom_values(self):
        """Test custom initialization values."""
        client = NUTClient(host="192.168.1.100", port=3500, timeout=5.0)
        assert client.host == "192.168.1.100"
        assert client.port == 3500
        assert client.timeout == 5.0

    def test_connect_failure(self):
        """Test connection failure handling."""
        client = NUTClient(host="invalid.host.local", port=9999, timeout=0.1)
        result = client.connect()
        assert result is False

    def test_parse_ups_list(self):
        """Test parsing LIST UPS response."""
        client = NUTClient()
        # Simulate response parsing
        response = 'UPS myups "APC Smart-UPS 1500"\nUPS backup "CyberPower 1000"'
        lines = response.split("\n")
        ups_list = {}
        for line in lines:
            if line.startswith("UPS "):
                parts = line.split('"')
                if len(parts) >= 2:
                    name = line.split()[1]
                    desc = parts[1]
                    ups_list[name] = desc

        assert "myups" in ups_list
        assert ups_list["myups"] == "APC Smart-UPS 1500"
        assert "backup" in ups_list

    def test_parse_var_response(self):
        """Test parsing VAR response."""
        response = 'VAR myups battery.charge "95"'
        if response.startswith("VAR "):
            parts = response.split('"')
            if len(parts) >= 2:
                value = parts[1]
                assert value == "95"

    def test_parse_ups_status_flags(self):
        """Test parsing UPS status flags."""
        status_str = "OL CHRG"  # Online and Charging

        on_mains = "OL" in status_str
        on_battery = "OB" in status_str
        low_battery = "LB" in status_str
        charging = "CHRG" in status_str

        assert on_mains is True
        assert on_battery is False
        assert low_battery is False
        assert charging is True

    def test_parse_on_battery_status(self):
        """Test parsing on-battery status."""
        status_str = "OB LB"  # On battery, low battery

        on_mains = "OL" in status_str
        on_battery = "OB" in status_str
        low_battery = "LB" in status_str

        assert on_mains is False
        assert on_battery is True
        assert low_battery is True


class TestUPSStatus:
    """Tests for UPSStatus dataclass."""

    def test_default_values(self):
        """Test default status values."""
        status = UPSStatus()
        assert status.state == PowerState.UNKNOWN
        assert status.battery_percent == 100
        assert status.on_mains is True
        assert status.battery_low is False

    def test_runtime_minutes_property(self):
        """Test runtime_minutes calculation."""
        status = UPSStatus(battery_runtime_sec=1800)  # 30 minutes
        assert status.runtime_minutes == 30.0

        status2 = UPSStatus(battery_runtime_sec=90)  # 1.5 minutes
        assert status2.runtime_minutes == 1.5

    def test_custom_values(self):
        """Test custom status values."""
        status = UPSStatus(
            state=PowerState.ON_BATTERY,
            battery_percent=75,
            battery_voltage=52.5,
            input_voltage=0.0,
            load_percent=45,
            on_mains=False,
            battery_low=False,
        )

        assert status.state == PowerState.ON_BATTERY
        assert status.battery_percent == 75
        assert status.on_mains is False


class TestPowerConfig:
    """Tests for PowerConfig dataclass."""

    def test_default_thresholds(self):
        """Test default threshold values."""
        config = PowerConfig()
        assert config.park_threshold_pct == 50
        assert config.emergency_threshold_pct == 20
        assert config.resume_threshold_pct == 80

    def test_default_timing(self):
        """Test default timing values."""
        config = PowerConfig()
        assert config.poll_interval_sec == 10.0
        assert config.power_restore_delay_sec == 300.0
        assert config.shutdown_delay_sec == 60.0

    def test_custom_config(self):
        """Test custom configuration."""
        config = PowerConfig(
            ups_name="custom_ups",
            nut_host="192.168.1.50",
            park_threshold_pct=60,
            emergency_threshold_pct=15,
        )

        assert config.ups_name == "custom_ups"
        assert config.nut_host == "192.168.1.50"
        assert config.park_threshold_pct == 60
        assert config.emergency_threshold_pct == 15


class TestPowerEvent:
    """Tests for PowerEvent dataclass."""

    def test_event_creation(self):
        """Test creating power event."""
        event = PowerEvent(
            timestamp=datetime.now(),
            event_type="POWER_LOST",
            description="Mains power lost",
            battery_percent=100,
            on_mains=False,
        )

        assert event.event_type == "POWER_LOST"
        assert event.battery_percent == 100
        assert event.on_mains is False


class TestPowerManager:
    """Tests for PowerManager class."""

    @pytest.fixture
    def manager(self):
        """Create power manager with simulation mode."""
        config = PowerConfig()
        manager = PowerManager(config)
        manager._use_simulation = True
        return manager

    def test_init(self, manager):
        """Test initialization."""
        assert manager.config is not None
        assert manager._running is False
        assert manager._use_simulation is True

    def test_status_property(self, manager):
        """Test status property."""
        status = manager.status
        assert isinstance(status, UPSStatus)

    def test_event_log_property(self, manager):
        """Test event log property."""
        log = manager.event_log
        assert isinstance(log, list)

    def test_log_event(self, manager):
        """Test event logging."""
        manager._log_event("TEST_EVENT", "Test description")

        assert len(manager._event_log) == 1
        assert manager._event_log[0].event_type == "TEST_EVENT"
        assert manager._event_log[0].description == "Test description"

    def test_log_event_limit(self, manager):
        """Test event log size limit."""
        # Add more than 1000 events
        for i in range(1100):
            manager._log_event("TEST", f"Event {i}")

        # Should be capped at 1000
        assert len(manager._event_log) == 1000

    def test_get_events_since(self, manager):
        """Test getting events since timestamp."""
        # Log some events
        manager._log_event("OLD", "Old event")
        cutoff = datetime.now()
        manager._log_event("NEW", "New event")

        events = manager.get_events_since(cutoff)
        assert len(events) == 1
        assert events[0].event_type == "NEW"

    def test_register_callback(self, manager):
        """Test callback registration."""
        callback = Mock()
        manager.register_callback(callback)
        assert callback in manager._callbacks

    @pytest.mark.asyncio
    async def test_start_stop(self, manager):
        """Test starting and stopping manager."""
        await manager.start()
        assert manager._running is True
        assert manager._monitor_task is not None

        await manager.stop()
        assert manager._running is False

    @pytest.mark.asyncio
    async def test_query_nut_simulation(self, manager):
        """Test NUT query in simulation mode."""
        status = await manager._query_nut()
        assert isinstance(status, UPSStatus)
        assert status.state == PowerState.ONLINE
        assert status.battery_percent == 100

    @pytest.mark.asyncio
    async def test_on_power_lost(self, manager):
        """Test power lost handling."""
        callback = Mock()
        manager.register_callback(callback)

        await manager._on_power_lost()

        assert manager._power_lost_time is not None
        assert manager._status.state == PowerState.ON_BATTERY
        assert len(manager._event_log) == 1
        assert manager._event_log[0].event_type == "POWER_LOST"

    @pytest.mark.asyncio
    async def test_initiate_park(self, manager):
        """Test park initiation."""
        mock_mount = Mock()
        mock_mount.park = AsyncMock()
        manager._mount = mock_mount

        await manager._initiate_park()

        assert manager._park_initiated is True
        assert len(manager._event_log) == 1
        assert "PARK" in manager._event_log[0].event_type


class TestPowerManagerThresholds:
    """Integration tests for power threshold logic."""

    @pytest.fixture
    def manager_with_thresholds(self):
        """Create manager with custom thresholds."""
        config = PowerConfig(
            park_threshold_pct=50,
            emergency_threshold_pct=20,
        )
        manager = PowerManager(config)
        manager._use_simulation = True
        return manager

    @pytest.mark.asyncio
    async def test_park_threshold_trigger(self, manager_with_thresholds):
        """Test that park is triggered at threshold."""
        manager = manager_with_thresholds

        # Simulate on-battery with low charge
        manager._status = UPSStatus(
            state=PowerState.ON_BATTERY,
            battery_percent=45,  # Below 50%
            on_mains=False,
        )
        manager._was_on_mains = False

        await manager._process_status()

        assert manager._park_initiated is True

    @pytest.mark.asyncio
    async def test_park_not_triggered_above_threshold(self, manager_with_thresholds):
        """Test that park is not triggered above threshold."""
        manager = manager_with_thresholds

        # Simulate on-battery but above threshold
        manager._status = UPSStatus(
            state=PowerState.ON_BATTERY,
            battery_percent=60,  # Above 50%
            on_mains=False,
        )
        manager._was_on_mains = False

        await manager._process_status()

        assert manager._park_initiated is False

    @pytest.mark.asyncio
    async def test_emergency_threshold_trigger(self, manager_with_thresholds):
        """Test that emergency shutdown is triggered at threshold."""
        manager = manager_with_thresholds

        # Mock the emergency shutdown to prevent actual shutdown
        manager._system_shutdown = AsyncMock()

        # Simulate critically low battery
        manager._status = UPSStatus(
            state=PowerState.ON_BATTERY,
            battery_percent=15,  # Below 20%
            on_mains=False,
        )
        manager._was_on_mains = False
        manager.config.shutdown_delay_sec = 0.01  # Short delay for test

        await manager._process_status()

        assert manager._shutdown_initiated is True

    @pytest.mark.asyncio
    async def test_no_action_on_mains(self, manager_with_thresholds):
        """Test no action when on mains power."""
        manager = manager_with_thresholds

        # Simulate on mains
        manager._status = UPSStatus(
            state=PowerState.ONLINE,
            battery_percent=100,
            on_mains=True,
        )
        manager._was_on_mains = True

        await manager._process_status()

        assert manager._park_initiated is False
        assert manager._shutdown_initiated is False
