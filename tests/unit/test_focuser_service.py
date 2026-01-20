"""
NIGHTWATCH Focuser Service Unit Tests

Step 191: Write unit tests for autofocus algorithms
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

from services.focus.focuser_service import (
    FocuserService,
    FocuserConfig,
    FocuserState,
    AutoFocusMethod,
    FocusMetric,
    FocusRun,
    FocusPositionRecord,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def focuser():
    """Create a focuser service instance with fast settings for testing."""
    config = FocuserConfig(
        autofocus_exposure_sec=0.01,  # Very fast for testing
        autofocus_samples=3,           # Minimal samples for speed
        autofocus_step_size=50,        # Small steps
    )
    return FocuserService(config=config)


@pytest.fixture
def config():
    """Create a focuser configuration."""
    return FocuserConfig()


@pytest.fixture
def custom_config():
    """Create a custom focuser configuration."""
    return FocuserConfig(
        max_position=100000,
        temp_coefficient=-3.0,
        autofocus_samples=11,
    )


# ============================================================================
# FocuserState Enum Tests
# ============================================================================

class TestFocuserState:
    """Tests for FocuserState enum."""

    def test_all_states_defined(self):
        """Verify all focuser states are defined."""
        assert FocuserState.IDLE.value == "idle"
        assert FocuserState.MOVING.value == "moving"
        assert FocuserState.AUTOFOCUS.value == "autofocus"
        assert FocuserState.CALIBRATING.value == "calibrating"
        assert FocuserState.ERROR.value == "error"


# ============================================================================
# AutoFocusMethod Enum Tests
# ============================================================================

class TestAutoFocusMethod:
    """Tests for AutoFocusMethod enum."""

    def test_all_methods_defined(self):
        """Verify all autofocus methods are defined."""
        assert AutoFocusMethod.VCURVE.value == "vcurve"
        assert AutoFocusMethod.BAHTINOV.value == "bahtinov"
        assert AutoFocusMethod.CONTRAST.value == "contrast"
        assert AutoFocusMethod.HFD.value == "hfd"


# ============================================================================
# FocuserConfig Tests
# ============================================================================

class TestFocuserConfig:
    """Tests for FocuserConfig dataclass."""

    def test_default_config(self, config):
        """Verify default focuser configuration."""
        assert config.max_position == 50000
        assert config.step_size_um == 1.0
        assert config.backlash_steps == 100
        assert config.temp_coefficient == -2.5
        assert config.temp_interval_c == 2.0
        assert config.time_interval_min == 30.0

    def test_autofocus_defaults(self, config):
        """Verify autofocus default settings."""
        assert config.autofocus_method == AutoFocusMethod.HFD
        assert config.autofocus_step_size == 100
        assert config.autofocus_samples == 9
        assert config.autofocus_exposure_sec == 2.0
        assert config.hfd_target == 3.0
        assert config.focus_tolerance == 10

    def test_custom_config(self, custom_config):
        """Verify custom focuser configuration."""
        assert custom_config.max_position == 100000
        assert custom_config.temp_coefficient == -3.0
        assert custom_config.autofocus_samples == 11


# ============================================================================
# FocusMetric Tests
# ============================================================================

class TestFocusMetric:
    """Tests for FocusMetric dataclass."""

    def test_focus_metric_creation(self):
        """Verify FocusMetric can be created."""
        metric = FocusMetric(
            timestamp=datetime.now(),
            position=25000,
            hfd=3.5,
            fwhm=2.1,
            peak_value=60000,
            star_count=25,
            temperature_c=15.0,
        )
        assert metric.position == 25000
        assert metric.hfd == 3.5
        assert metric.fwhm == 2.1
        assert metric.star_count == 25


# ============================================================================
# FocusRun Tests
# ============================================================================

class TestFocusRun:
    """Tests for FocusRun dataclass."""

    def test_focus_run_creation(self):
        """Verify FocusRun can be created."""
        run = FocusRun(
            run_id="20240101_120000",
            start_time=datetime.now(),
            method=AutoFocusMethod.VCURVE,
            initial_position=24000,
        )
        assert run.run_id == "20240101_120000"
        assert run.method == AutoFocusMethod.VCURVE
        assert run.initial_position == 24000
        assert run.final_position == 0
        assert run.best_hfd == float('inf')
        assert run.success is False
        assert run.error is None

    def test_focus_run_defaults(self):
        """Verify FocusRun default values."""
        run = FocusRun(
            run_id="test",
            start_time=datetime.now(),
        )
        assert run.method == AutoFocusMethod.HFD
        assert run.measurements == []


# ============================================================================
# FocusPositionRecord Tests (Step 188)
# ============================================================================

class TestFocusPositionRecord:
    """Tests for FocusPositionRecord dataclass."""

    def test_position_record_creation(self):
        """Verify FocusPositionRecord can be created."""
        record = FocusPositionRecord(
            timestamp=datetime.now(),
            position=25000,
            temperature_c=18.0,
            reason="manual",
        )
        assert record.position == 25000
        assert record.temperature_c == 18.0
        assert record.reason == "manual"
        assert record.hfd is None

    def test_position_record_with_hfd(self):
        """Verify FocusPositionRecord with HFD."""
        record = FocusPositionRecord(
            timestamp=datetime.now(),
            position=25000,
            temperature_c=18.0,
            reason="auto_focus_complete",
            hfd=2.8,
        )
        assert record.hfd == 2.8


# ============================================================================
# FocuserService Initialization Tests
# ============================================================================

class TestFocuserServiceInit:
    """Tests for FocuserService initialization."""

    def test_default_initialization(self, focuser):
        """Verify focuser initializes with defaults."""
        assert focuser.connected is False
        assert focuser.state == FocuserState.IDLE
        assert focuser.position == 25000
        assert focuser.temperature == 20.0
        assert focuser.config is not None

    def test_initialization_with_config(self, custom_config):
        """Verify focuser initializes with custom config."""
        focuser = FocuserService(config=custom_config)
        assert focuser.config.max_position == 100000
        assert focuser.config.temp_coefficient == -3.0


# ============================================================================
# FocuserService Properties Tests
# ============================================================================

class TestFocuserServiceProperties:
    """Tests for FocuserService properties."""

    def test_connected_property(self, focuser):
        """Verify connected property."""
        assert focuser.connected is False
        focuser._connected = True
        assert focuser.connected is True

    def test_state_property(self, focuser):
        """Verify state property."""
        assert focuser.state == FocuserState.IDLE
        focuser._state = FocuserState.MOVING
        assert focuser.state == FocuserState.MOVING

    def test_position_property(self, focuser):
        """Verify position property."""
        assert focuser.position == 25000
        focuser._position = 30000
        assert focuser.position == 30000

    def test_temperature_property(self, focuser):
        """Verify temperature property."""
        assert focuser.temperature == 20.0
        focuser._temperature = 15.5
        assert focuser.temperature == 15.5


# ============================================================================
# FocuserService Connection Tests
# ============================================================================

class TestFocuserServiceConnection:
    """Tests for FocuserService connection."""

    @pytest.mark.asyncio
    async def test_connect(self, focuser):
        """Verify focuser connection."""
        result = await focuser.connect()
        assert result is True
        assert focuser.connected is True
        assert focuser.state == FocuserState.IDLE

    @pytest.mark.asyncio
    async def test_disconnect(self, focuser):
        """Verify focuser disconnection."""
        await focuser.connect()
        await focuser.disconnect()
        assert focuser.connected is False


# ============================================================================
# FocuserService Movement Tests
# ============================================================================

class TestFocuserServiceMovement:
    """Tests for FocuserService movement."""

    @pytest.mark.asyncio
    async def test_move_to_requires_connection(self, focuser):
        """Verify move_to requires connection."""
        with pytest.raises(RuntimeError, match="not connected"):
            await focuser.move_to(30000)

    @pytest.mark.asyncio
    async def test_move_to(self, focuser):
        """Verify move_to works when connected."""
        await focuser.connect()
        result = await focuser.move_to(30000)
        assert result is True
        assert focuser.position == 30000

    @pytest.mark.asyncio
    async def test_move_to_clamps_position(self, focuser):
        """Verify move_to clamps position to valid range."""
        await focuser.connect()
        await focuser.move_to(100000)  # Beyond max
        assert focuser.position == focuser.config.max_position

    @pytest.mark.asyncio
    async def test_move_relative(self, focuser):
        """Verify move_relative works."""
        await focuser.connect()
        initial = focuser.position
        result = await focuser.move_relative(1000)
        assert result is True
        # Position should change (may have backlash added)
        assert focuser.position != initial

    @pytest.mark.asyncio
    async def test_halt(self, focuser):
        """Verify halt works."""
        await focuser.connect()
        await focuser.halt()
        assert focuser.state == FocuserState.IDLE


# ============================================================================
# Position History Tests (Step 188)
# ============================================================================

class TestPositionHistory:
    """Tests for focus position history tracking."""

    @pytest.mark.asyncio
    async def test_move_records_history(self, focuser):
        """Verify moves are recorded in history."""
        await focuser.connect()
        await focuser.move_to(26000, reason="test_move")

        history = focuser.get_position_history(limit=1)
        assert len(history) == 1
        assert history[0].position == 26000
        assert history[0].reason == "test_move"

    def test_get_position_history_empty(self, focuser):
        """Verify empty history returns empty list."""
        history = focuser.get_position_history()
        assert history == []

    @pytest.mark.asyncio
    async def test_get_position_history_limit(self, focuser):
        """Verify history limit is respected."""
        await focuser.connect()
        for i in range(5):
            await focuser.move_to(25000 + i * 100, reason=f"move_{i}")

        history = focuser.get_position_history(limit=3)
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_get_position_history_since(self, focuser):
        """Verify history since timestamp works."""
        await focuser.connect()
        await focuser.move_to(25500, reason="early_move")

        cutoff = datetime.now()
        await focuser.move_to(26000, reason="late_move")

        history = focuser.get_position_history_since(cutoff)
        assert len(history) == 1
        assert history[0].reason == "late_move"

    @pytest.mark.asyncio
    async def test_get_position_stats(self, focuser):
        """Verify position statistics calculation."""
        await focuser.connect()
        for i in range(3):
            await focuser.move_to(25000 + i * 1000, reason=f"move_{i}")

        stats = focuser.get_position_stats()
        assert stats["record_count"] == 3
        assert stats["min_position"] is not None
        assert stats["max_position"] is not None
        assert stats["avg_position"] is not None

    def test_get_position_stats_empty(self, focuser):
        """Verify empty stats."""
        stats = focuser.get_position_stats()
        assert stats["record_count"] == 0
        assert stats["min_position"] is None

    @pytest.mark.asyncio
    async def test_clear_position_history(self, focuser):
        """Verify history can be cleared."""
        await focuser.connect()
        await focuser.move_to(26000, reason="test")

        count = focuser.clear_position_history()
        assert count == 1
        assert len(focuser.get_position_history()) == 0


# ============================================================================
# Temperature Compensation Tests
# ============================================================================

class TestTemperatureCompensation:
    """Tests for temperature compensation."""

    def test_enable_temp_compensation(self, focuser):
        """Verify temp compensation can be enabled."""
        focuser.enable_temp_compensation()
        assert focuser._temp_comp_enabled is True

    def test_disable_temp_compensation(self, focuser):
        """Verify temp compensation can be disabled."""
        focuser.enable_temp_compensation()
        focuser.disable_temp_compensation()
        assert focuser._temp_comp_enabled is False

    def test_needs_refocus_no_previous(self, focuser):
        """Verify needs_refocus when no previous focus."""
        needs, reason = focuser.needs_refocus()
        assert needs is True
        assert "No previous focus" in reason

    @pytest.mark.asyncio
    async def test_needs_refocus_after_focus(self, focuser):
        """Verify needs_refocus returns False after recent focus."""
        await focuser.connect()
        await focuser.auto_focus()

        needs, reason = focuser.needs_refocus()
        assert needs is False
        assert "Focus OK" in reason


# ============================================================================
# Temperature Coefficient Storage Tests (Step 186)
# ============================================================================

class TestTempCoefficientStorage:
    """Tests for temperature coefficient storage."""

    def test_save_temp_coefficient(self, focuser, tmp_path):
        """Verify temperature coefficient can be saved."""
        filepath = tmp_path / "test_focus_cal.json"
        result = focuser.save_temp_coefficient(str(filepath))
        assert result is True
        assert filepath.exists()

    def test_load_temp_coefficient(self, focuser, tmp_path):
        """Verify temperature coefficient can be loaded."""
        filepath = tmp_path / "test_focus_cal.json"
        focuser.config.temp_coefficient = -5.0
        focuser.save_temp_coefficient(str(filepath))

        # Reset and load
        focuser.config.temp_coefficient = -2.5
        result = focuser.load_temp_coefficient(str(filepath))
        assert result is True
        assert focuser.config.temp_coefficient == -5.0

    def test_load_temp_coefficient_missing_file(self, focuser, tmp_path):
        """Verify loading missing file returns False."""
        filepath = tmp_path / "nonexistent.json"
        result = focuser.load_temp_coefficient(str(filepath))
        assert result is False

    def test_get_temp_coefficient_info(self, focuser):
        """Verify coefficient info retrieval."""
        info = focuser.get_temp_coefficient_info()
        assert "current_coefficient" in info
        assert info["current_coefficient"] == focuser.config.temp_coefficient


# ============================================================================
# Autofocus Tests
# ============================================================================

class TestAutofocus:
    """Tests for autofocus functionality."""

    @pytest.mark.asyncio
    async def test_autofocus_requires_connection(self, focuser):
        """Verify auto_focus requires connection."""
        with pytest.raises(RuntimeError, match="not connected"):
            await focuser.auto_focus()

    @pytest.mark.asyncio
    async def test_autofocus_vcurve(self, focuser):
        """Verify V-curve autofocus."""
        await focuser.connect()
        run = await focuser.auto_focus(method=AutoFocusMethod.VCURVE)

        assert run.success is True
        assert run.method == AutoFocusMethod.VCURVE
        assert run.best_hfd < float('inf')
        assert len(run.measurements) > 0

    @pytest.mark.asyncio
    async def test_autofocus_hfd(self, focuser):
        """Verify HFD autofocus."""
        await focuser.connect()
        run = await focuser.auto_focus(method=AutoFocusMethod.HFD)

        assert run.success is True
        assert run.method == AutoFocusMethod.HFD
        assert run.best_hfd < float('inf')

    @pytest.mark.asyncio
    async def test_autofocus_updates_tracking(self, focuser):
        """Verify autofocus updates tracking info."""
        await focuser.connect()
        await focuser.auto_focus()

        assert focuser._last_focus_time is not None
        assert focuser._last_focus_temp is not None
        assert len(focuser._focus_history) > 0

    @pytest.mark.asyncio
    async def test_autofocus_records_position_history(self, focuser):
        """Verify autofocus records to position history."""
        await focuser.connect()
        initial_count = len(focuser.get_position_history())

        await focuser.auto_focus()

        final_count = len(focuser.get_position_history())
        assert final_count > initial_count


# ============================================================================
# V-Curve Fitting Tests
# ============================================================================

class TestVCurveFitting:
    """Tests for V-curve fitting algorithm."""

    def test_fit_vcurve_minimum(self, focuser):
        """Verify V-curve fitting finds minimum."""
        # Symmetric V-curve data
        positions = [24000, 24500, 25000, 25500, 26000]
        hfds = [4.0, 3.0, 2.5, 3.0, 4.0]

        best_pos = focuser._fit_vcurve(positions, hfds)

        # Should be near the minimum HFD position
        assert 24500 <= best_pos <= 25500

    def test_fit_vcurve_insufficient_data(self, focuser):
        """Verify V-curve handles insufficient data."""
        positions = [25000, 25500]
        hfds = [3.0, 2.8]

        best_pos = focuser._fit_vcurve(positions, hfds)

        # Should return position of minimum HFD
        assert best_pos == 25500


# ============================================================================
# Run Configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
