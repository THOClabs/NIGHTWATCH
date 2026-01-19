"""
Unit tests for NIGHTWATCH Watchdog Module.

Tests service health monitoring, heartbeat tracking, timeout detection,
and restart logic.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from nightwatch.watchdog import (
    ServiceState,
    ServiceType,
    ServiceConfig,
    ServiceStatus,
    ServiceWatchdog,
    WatchdogManager,
    MountWatchdog,
    WeatherWatchdog,
    CameraWatchdog,
    DEFAULT_CONFIGS,
    create_watchdog_manager,
)


# =============================================================================
# ServiceState Tests
# =============================================================================

class TestServiceState:
    """Tests for ServiceState enum."""

    def test_all_states_defined(self):
        """Verify all expected states exist."""
        assert ServiceState.UNKNOWN.value == "unknown"
        assert ServiceState.HEALTHY.value == "healthy"
        assert ServiceState.DEGRADED.value == "degraded"
        assert ServiceState.FAILED.value == "failed"
        assert ServiceState.RESTARTING.value == "restarting"
        assert ServiceState.STOPPED.value == "stopped"


# =============================================================================
# ServiceType Tests
# =============================================================================

class TestServiceType:
    """Tests for ServiceType enum."""

    def test_all_service_types_defined(self):
        """Verify all expected service types exist."""
        assert ServiceType.MOUNT.value == "mount"
        assert ServiceType.WEATHER.value == "weather"
        assert ServiceType.CAMERA.value == "camera"
        assert ServiceType.GUIDER.value == "guider"
        assert ServiceType.FOCUSER.value == "focuser"
        assert ServiceType.ENCLOSURE.value == "enclosure"
        assert ServiceType.POWER.value == "power"
        assert ServiceType.LLM.value == "llm"
        assert ServiceType.STT.value == "stt"
        assert ServiceType.TTS.value == "tts"


# =============================================================================
# ServiceConfig Tests
# =============================================================================

class TestServiceConfig:
    """Tests for ServiceConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ServiceConfig(
            service_type=ServiceType.CAMERA,
            name="Test Camera",
        )
        assert config.heartbeat_interval_sec == 30.0
        assert config.timeout_sec == 60.0
        assert config.max_restart_attempts == 3
        assert config.restart_cooldown_sec == 60.0
        assert config.critical is False

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ServiceConfig(
            service_type=ServiceType.MOUNT,
            name="Test Mount",
            heartbeat_interval_sec=10.0,
            timeout_sec=30.0,
            max_restart_attempts=5,
            restart_cooldown_sec=120.0,
            critical=True,
        )
        assert config.heartbeat_interval_sec == 10.0
        assert config.timeout_sec == 30.0
        assert config.max_restart_attempts == 5
        assert config.restart_cooldown_sec == 120.0
        assert config.critical is True

    def test_timeout_validation(self):
        """Test timeout is adjusted if less than heartbeat interval."""
        config = ServiceConfig(
            service_type=ServiceType.CAMERA,
            name="Test Camera",
            heartbeat_interval_sec=30.0,
            timeout_sec=20.0,  # Less than heartbeat
        )
        # Post-init should adjust timeout to 2x heartbeat
        assert config.timeout_sec == 60.0


# =============================================================================
# ServiceStatus Tests
# =============================================================================

class TestServiceStatus:
    """Tests for ServiceStatus dataclass."""

    def test_default_state(self):
        """Test default status values."""
        status = ServiceStatus(
            service_type=ServiceType.CAMERA,
            name="Test Camera",
        )
        assert status.state == ServiceState.UNKNOWN
        assert status.last_heartbeat is None
        assert status.last_error is None
        assert status.restart_count == 0
        assert status.last_restart is None
        assert status.consecutive_failures == 0

    def test_is_healthy(self):
        """Test is_healthy property."""
        status = ServiceStatus(
            service_type=ServiceType.CAMERA,
            name="Test Camera",
        )
        assert status.is_healthy is False

        status.state = ServiceState.HEALTHY
        assert status.is_healthy is True

        status.state = ServiceState.DEGRADED
        assert status.is_healthy is False

    def test_is_failed(self):
        """Test is_failed property."""
        status = ServiceStatus(
            service_type=ServiceType.CAMERA,
            name="Test Camera",
        )
        assert status.is_failed is False

        status.state = ServiceState.FAILED
        assert status.is_failed is True

    def test_seconds_since_heartbeat_none(self):
        """Test seconds_since_heartbeat when no heartbeat received."""
        status = ServiceStatus(
            service_type=ServiceType.CAMERA,
            name="Test Camera",
        )
        assert status.seconds_since_heartbeat is None

    def test_seconds_since_heartbeat(self):
        """Test seconds_since_heartbeat calculation."""
        status = ServiceStatus(
            service_type=ServiceType.CAMERA,
            name="Test Camera",
        )
        status.last_heartbeat = datetime.now() - timedelta(seconds=10)
        elapsed = status.seconds_since_heartbeat
        assert elapsed is not None
        assert 9.5 < elapsed < 11.0  # Allow some tolerance

    def test_to_dict(self):
        """Test conversion to dictionary."""
        status = ServiceStatus(
            service_type=ServiceType.CAMERA,
            name="Test Camera",
            state=ServiceState.HEALTHY,
            restart_count=2,
            consecutive_failures=1,
        )
        status.last_heartbeat = datetime(2024, 1, 15, 12, 0, 0)
        status.last_error = "Test error"

        result = status.to_dict()

        assert result["service_type"] == "camera"
        assert result["name"] == "Test Camera"
        assert result["state"] == "healthy"
        assert result["last_heartbeat"] == "2024-01-15T12:00:00"
        assert result["last_error"] == "Test error"
        assert result["restart_count"] == 2
        assert result["consecutive_failures"] == 1


# =============================================================================
# ServiceWatchdog Tests
# =============================================================================

class TestServiceWatchdog:
    """Tests for ServiceWatchdog class."""

    @pytest.fixture
    def watchdog(self):
        """Create a test watchdog."""
        config = ServiceConfig(
            service_type=ServiceType.CAMERA,
            name="Test Camera",
            heartbeat_interval_sec=10.0,
            timeout_sec=30.0,
            max_restart_attempts=3,
            restart_cooldown_sec=60.0,
        )
        return ServiceWatchdog(config)

    def test_initial_state(self, watchdog):
        """Test initial watchdog state."""
        assert watchdog.status.state == ServiceState.UNKNOWN
        assert watchdog.status.last_heartbeat is None

    def test_record_heartbeat(self, watchdog):
        """Test recording a heartbeat."""
        watchdog.record_heartbeat()

        assert watchdog.status.last_heartbeat is not None
        assert watchdog.status.consecutive_failures == 0
        assert watchdog.status.state == ServiceState.HEALTHY

    def test_heartbeat_clears_degraded(self, watchdog):
        """Test heartbeat clears degraded state."""
        watchdog.status.state = ServiceState.DEGRADED
        watchdog.record_heartbeat()
        assert watchdog.status.state == ServiceState.HEALTHY

    def test_heartbeat_clears_restarting(self, watchdog):
        """Test heartbeat clears restarting state."""
        watchdog.status.state = ServiceState.RESTARTING
        watchdog.record_heartbeat()
        assert watchdog.status.state == ServiceState.HEALTHY

    def test_record_error(self, watchdog):
        """Test recording an error."""
        watchdog.record_error("Connection lost")

        assert watchdog.status.last_error == "Connection lost"
        assert watchdog.status.consecutive_failures == 1
        assert watchdog.status.state == ServiceState.DEGRADED

    def test_multiple_errors_cause_failure(self, watchdog):
        """Test multiple errors transition to failed state."""
        watchdog.record_error("Error 1")
        assert watchdog.status.state == ServiceState.DEGRADED

        watchdog.record_error("Error 2")
        assert watchdog.status.state == ServiceState.DEGRADED

        watchdog.record_error("Error 3")
        assert watchdog.status.state == ServiceState.FAILED

    def test_check_timeout_no_heartbeat(self, watchdog):
        """Test timeout check when no heartbeat received."""
        # Should not timeout if never received heartbeat
        assert watchdog.check_timeout() is False

    def test_check_timeout_recent_heartbeat(self, watchdog):
        """Test timeout check with recent heartbeat."""
        watchdog.record_heartbeat()
        assert watchdog.check_timeout() is False

    def test_check_timeout_expired(self, watchdog):
        """Test timeout check when heartbeat expired."""
        watchdog.status.last_heartbeat = datetime.now() - timedelta(seconds=60)
        assert watchdog.check_timeout() is True
        assert watchdog.status.state == ServiceState.FAILED
        assert "timeout" in watchdog.status.last_error.lower()

    def test_can_restart_initially(self, watchdog):
        """Test restart allowed initially."""
        assert watchdog.can_restart() is True

    def test_can_restart_after_attempts(self, watchdog):
        """Test restart blocked after max attempts."""
        watchdog.status.restart_count = 3  # max_restart_attempts
        assert watchdog.can_restart() is False

    def test_can_restart_cooldown(self, watchdog):
        """Test restart blocked during cooldown."""
        watchdog.status.restart_count = 1
        watchdog.status.last_restart = datetime.now()
        assert watchdog.can_restart() is False

    def test_can_restart_after_cooldown(self, watchdog):
        """Test restart allowed after cooldown."""
        watchdog.status.restart_count = 1
        watchdog.status.last_restart = datetime.now() - timedelta(seconds=120)
        assert watchdog.can_restart() is True

    def test_record_restart_attempt(self, watchdog):
        """Test recording a restart attempt."""
        watchdog.record_restart_attempt()

        assert watchdog.status.restart_count == 1
        assert watchdog.status.last_restart is not None
        assert watchdog.status.state == ServiceState.RESTARTING

    def test_reset_restart_count(self, watchdog):
        """Test resetting restart count."""
        watchdog.status.restart_count = 3
        watchdog.reset_restart_count()
        assert watchdog.status.restart_count == 0

    def test_set_restart_callback(self, watchdog):
        """Test setting restart callback."""
        callback = MagicMock()
        watchdog.set_restart_callback(callback)
        assert watchdog._restart_callback == callback

    def test_set_failure_callback(self, watchdog):
        """Test setting failure callback."""
        callback = MagicMock()
        watchdog.set_failure_callback(callback)
        assert watchdog._failure_callback == callback


# =============================================================================
# WatchdogManager Tests
# =============================================================================

class TestWatchdogManager:
    """Tests for WatchdogManager class."""

    @pytest.fixture
    def manager(self):
        """Create a test watchdog manager."""
        return WatchdogManager()

    def test_initialization(self, manager):
        """Test manager initializes with default watchdogs."""
        # Should have default service watchdogs
        assert ServiceType.MOUNT in manager._watchdogs
        assert ServiceType.WEATHER in manager._watchdogs
        assert ServiceType.CAMERA in manager._watchdogs

    def test_register_service(self, manager):
        """Test registering a new service."""
        config = ServiceConfig(
            service_type=ServiceType.LLM,
            name="LLM Service",
            heartbeat_interval_sec=5.0,
            timeout_sec=15.0,
        )
        manager.register_service(config)

        assert ServiceType.LLM in manager._watchdogs
        watchdog = manager.get_watchdog(ServiceType.LLM)
        assert watchdog is not None
        assert watchdog.config.name == "LLM Service"

    def test_get_watchdog(self, manager):
        """Test getting a watchdog."""
        watchdog = manager.get_watchdog(ServiceType.MOUNT)
        assert watchdog is not None
        assert watchdog.config.service_type == ServiceType.MOUNT

    def test_get_watchdog_nonexistent(self, manager):
        """Test getting a non-existent watchdog."""
        watchdog = manager.get_watchdog(ServiceType.LLM)
        assert watchdog is None

    def test_heartbeat(self, manager):
        """Test recording a heartbeat."""
        manager.heartbeat(ServiceType.MOUNT)

        status = manager.get_status(ServiceType.MOUNT)
        assert status.last_heartbeat is not None
        assert status.state == ServiceState.HEALTHY

    def test_heartbeat_unregistered(self, manager):
        """Test heartbeat for unregistered service."""
        # Should not raise, just log warning
        manager.heartbeat(ServiceType.LLM)

    def test_report_error(self, manager):
        """Test reporting an error."""
        manager.report_error(ServiceType.MOUNT, "Connection lost")

        status = manager.get_status(ServiceType.MOUNT)
        assert status.last_error == "Connection lost"
        assert status.consecutive_failures == 1

    def test_get_status(self, manager):
        """Test getting service status."""
        status = manager.get_status(ServiceType.MOUNT)
        assert status is not None
        assert status.service_type == ServiceType.MOUNT

    def test_get_status_nonexistent(self, manager):
        """Test getting status for non-existent service."""
        status = manager.get_status(ServiceType.LLM)
        assert status is None

    def test_get_all_status(self, manager):
        """Test getting all service status."""
        all_status = manager.get_all_status()

        assert "mount" in all_status
        assert "weather" in all_status
        assert "camera" in all_status

    def test_is_all_healthy_false(self, manager):
        """Test is_all_healthy when services unknown."""
        assert manager.is_all_healthy() is False

    def test_is_all_healthy_true(self, manager):
        """Test is_all_healthy when all healthy."""
        for service_type in manager._watchdogs:
            manager.heartbeat(service_type)

        assert manager.is_all_healthy() is True

    def test_get_failed_services(self, manager):
        """Test getting failed services."""
        # Make mount fail
        manager._watchdogs[ServiceType.MOUNT].status.state = ServiceState.FAILED

        failed = manager.get_failed_services()
        assert ServiceType.MOUNT in failed

    def test_get_critical_failures(self, manager):
        """Test getting critical failures."""
        # Mount is critical
        manager._watchdogs[ServiceType.MOUNT].status.state = ServiceState.FAILED

        critical = manager.get_critical_failures()
        assert ServiceType.MOUNT in critical

    def test_get_critical_failures_non_critical(self, manager):
        """Test non-critical failure not in critical list."""
        # Camera is not critical
        manager._watchdogs[ServiceType.CAMERA].status.state = ServiceState.FAILED

        critical = manager.get_critical_failures()
        assert ServiceType.CAMERA not in critical

    @pytest.mark.asyncio
    async def test_start_stop(self, manager):
        """Test starting and stopping the manager."""
        await manager.start()
        assert manager._running is True
        assert manager._check_task is not None

        await manager.stop()
        assert manager._running is False

    @pytest.mark.asyncio
    async def test_register_status_callback(self, manager):
        """Test registering a status callback."""
        callback = MagicMock()
        manager.register_status_callback(callback)
        assert callback in manager._callbacks

    @pytest.mark.asyncio
    async def test_set_safe_state_callback(self, manager):
        """Test setting safe state callback."""
        callback = MagicMock()
        manager.set_safe_state_callback(callback)
        assert manager._safe_state_callback == callback

    @pytest.mark.asyncio
    async def test_call_async_sync_callback(self, manager):
        """Test calling sync callback."""
        callback = MagicMock()
        await manager._call_async(callback, "arg1", "arg2")
        callback.assert_called_once_with("arg1", "arg2")

    @pytest.mark.asyncio
    async def test_call_async_async_callback(self, manager):
        """Test calling async callback."""
        callback = AsyncMock()
        await manager._call_async(callback, "arg1", "arg2")
        callback.assert_called_once_with("arg1", "arg2")


# =============================================================================
# MountWatchdog Tests
# =============================================================================

class TestMountWatchdog:
    """Tests for MountWatchdog class."""

    @pytest.fixture
    def watchdog(self):
        """Create a test mount watchdog."""
        return MountWatchdog()

    def test_uses_default_config(self, watchdog):
        """Test uses default mount config."""
        assert watchdog.config.service_type == ServiceType.MOUNT
        assert watchdog.config.critical is True

    def test_record_tracking_status_tracking(self, watchdog):
        """Test recording tracking status when tracking."""
        watchdog._tracking_lost_count = 2
        watchdog.record_tracking_status(True)
        assert watchdog._tracking_lost_count == 0

    def test_record_tracking_status_lost(self, watchdog):
        """Test recording tracking status when lost."""
        watchdog.record_tracking_status(False)
        assert watchdog._tracking_lost_count == 1

    def test_tracking_lost_triggers_error(self, watchdog):
        """Test multiple tracking lost triggers error."""
        watchdog.record_tracking_status(False)
        watchdog.record_tracking_status(False)
        watchdog.record_tracking_status(False)

        assert watchdog.status.last_error == "Tracking lost"

    def test_record_position(self, watchdog):
        """Test recording position as heartbeat."""
        watchdog.record_position(12.5, 45.0)
        assert watchdog.status.last_heartbeat is not None


# =============================================================================
# WeatherWatchdog Tests
# =============================================================================

class TestWeatherWatchdog:
    """Tests for WeatherWatchdog class."""

    @pytest.fixture
    def watchdog(self):
        """Create a test weather watchdog."""
        return WeatherWatchdog()

    def test_uses_default_config(self, watchdog):
        """Test uses default weather config."""
        assert watchdog.config.service_type == ServiceType.WEATHER
        assert watchdog.config.critical is True

    def test_record_fresh_weather_data(self, watchdog):
        """Test recording fresh weather data."""
        watchdog.record_weather_data(datetime.now())
        assert watchdog.status.last_heartbeat is not None
        assert watchdog._stale_data_count == 0

    def test_record_stale_weather_data(self, watchdog):
        """Test recording stale weather data."""
        old_time = datetime.now() - timedelta(minutes=5)
        watchdog.record_weather_data(old_time)
        assert watchdog._stale_data_count == 1

    def test_stale_data_triggers_error(self, watchdog):
        """Test multiple stale data triggers error."""
        old_time = datetime.now() - timedelta(minutes=5)
        watchdog.record_weather_data(old_time)
        watchdog.record_weather_data(old_time)
        watchdog.record_weather_data(old_time)

        assert "stale" in watchdog.status.last_error.lower()


# =============================================================================
# CameraWatchdog Tests
# =============================================================================

class TestCameraWatchdog:
    """Tests for CameraWatchdog class."""

    @pytest.fixture
    def watchdog(self):
        """Create a test camera watchdog."""
        return CameraWatchdog()

    def test_uses_default_config(self, watchdog):
        """Test uses default camera config."""
        assert watchdog.config.service_type == ServiceType.CAMERA
        assert watchdog.config.critical is False

    def test_record_exposure_complete(self, watchdog):
        """Test recording exposure complete."""
        watchdog._exposure_timeout_count = 2
        watchdog.record_exposure_complete()

        assert watchdog._exposure_timeout_count == 0
        assert watchdog.status.last_heartbeat is not None

    def test_record_exposure_timeout(self, watchdog):
        """Test recording exposure timeout."""
        watchdog.record_exposure_timeout()
        assert watchdog._exposure_timeout_count == 1

    def test_exposure_timeout_triggers_error(self, watchdog):
        """Test multiple exposure timeouts trigger error."""
        watchdog.record_exposure_timeout()
        watchdog.record_exposure_timeout()
        watchdog.record_exposure_timeout()

        assert "timeout" in watchdog.status.last_error.lower()


# =============================================================================
# Default Configs Tests
# =============================================================================

class TestDefaultConfigs:
    """Tests for default service configurations."""

    def test_mount_config(self):
        """Test default mount configuration."""
        config = DEFAULT_CONFIGS[ServiceType.MOUNT]
        assert config.name == "Mount Controller"
        assert config.heartbeat_interval_sec == 10.0
        assert config.critical is True

    def test_weather_config(self):
        """Test default weather configuration."""
        config = DEFAULT_CONFIGS[ServiceType.WEATHER]
        assert config.name == "Weather Service"
        assert config.heartbeat_interval_sec == 60.0
        assert config.critical is True

    def test_camera_config(self):
        """Test default camera configuration."""
        config = DEFAULT_CONFIGS[ServiceType.CAMERA]
        assert config.name == "Camera Controller"
        assert config.critical is False

    def test_guider_config(self):
        """Test default guider configuration."""
        config = DEFAULT_CONFIGS[ServiceType.GUIDER]
        assert config.name == "Guiding Service"
        assert config.heartbeat_interval_sec == 5.0  # Fast for guiding

    def test_enclosure_config(self):
        """Test default enclosure configuration."""
        config = DEFAULT_CONFIGS[ServiceType.ENCLOSURE]
        assert config.name == "Enclosure Controller"
        assert config.critical is True

    def test_power_config(self):
        """Test default power configuration."""
        config = DEFAULT_CONFIGS[ServiceType.POWER]
        assert config.name == "Power Monitor"
        assert config.critical is True


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactoryFunction:
    """Tests for factory function."""

    def test_create_watchdog_manager(self):
        """Test creating a watchdog manager."""
        manager = create_watchdog_manager()
        assert isinstance(manager, WatchdogManager)
        assert len(manager._watchdogs) > 0
