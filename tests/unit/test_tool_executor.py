"""
Unit tests for NIGHTWATCH Tool Executor.

Tests tool execution, parameter validation, and service integration.
"""

import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock, patch

import pytest

from nightwatch.tool_executor import (
    ToolExecutor,
    ToolResult,
    ToolStatus,
    ToolExecutionError,
)
from nightwatch.tool_params import NoParams
from nightwatch.config import NightwatchConfig
from nightwatch.orchestrator import Orchestrator, ServiceStatus


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_success_result(self):
        """Test successful result."""
        result = ToolResult(
            tool_name="test",
            status=ToolStatus.SUCCESS,
            message="Done",
            data={"key": "value"},
        )
        assert result.success is True
        assert result.tool_name == "test"
        assert result.data["key"] == "value"

    def test_error_result(self):
        """Test error result."""
        result = ToolResult(
            tool_name="test",
            status=ToolStatus.ERROR,
            error="Something failed",
        )
        assert result.success is False
        assert result.error == "Something failed"

    def test_to_dict(self):
        """Test dictionary serialization."""
        result = ToolResult(
            tool_name="test",
            status=ToolStatus.SUCCESS,
            message="Done",
        )
        d = result.to_dict()
        assert d["tool_name"] == "test"
        assert d["status"] == "success"
        assert "timestamp" in d


class TestToolStatus:
    """Tests for ToolStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert ToolStatus.SUCCESS.value == "success"
        assert ToolStatus.ERROR.value == "error"
        assert ToolStatus.TIMEOUT.value == "timeout"
        assert ToolStatus.VETOED.value == "vetoed"
        assert ToolStatus.NOT_FOUND.value == "not_found"
        assert ToolStatus.INVALID_PARAMS.value == "invalid_params"


class TestToolExecutor:
    """Tests for ToolExecutor class."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return NightwatchConfig()

    @pytest.fixture
    def orchestrator(self, config):
        """Create mock orchestrator."""
        return Orchestrator(config)

    @pytest.fixture
    def executor(self, orchestrator):
        """Create tool executor for testing."""
        return ToolExecutor(orchestrator)

    def test_init(self, executor):
        """Test executor initialization."""
        assert executor.orchestrator is not None
        assert executor.default_timeout == 30.0
        assert len(executor._handlers) > 0

    def test_register_handler(self, executor):
        """Test handler registration."""
        handler = AsyncMock()
        # ARCH-001: ad-hoc tools need a param_model so execute() can validate them.
        executor.register_handler("custom_tool", handler, param_model=NoParams)
        assert "custom_tool" in executor._handlers
        assert executor._param_models["custom_tool"] is NoParams

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, executor):
        """Test executing unknown tool."""
        result = await executor.execute("unknown_tool", {})
        assert result.status == ToolStatus.NOT_FOUND
        assert "unknown_tool" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, executor):
        """Test tool execution timeout."""
        async def slow_handler(params):
            await asyncio.sleep(5)
            return ToolResult(
                tool_name="slow",
                status=ToolStatus.SUCCESS,
                message="Done",
            )

        executor.register_handler("slow_tool", slow_handler, param_model=NoParams)
        result = await executor.execute("slow_tool", {}, timeout=0.1)
        assert result.status == ToolStatus.TIMEOUT

    @pytest.mark.asyncio
    async def test_execute_with_exception(self, executor):
        """Test tool execution with exception."""
        async def failing_handler(params):
            raise ValueError("Test error")

        executor.register_handler("failing_tool", failing_handler, param_model=NoParams)
        result = await executor.execute("failing_tool", {})
        assert result.status == ToolStatus.ERROR
        assert "Test error" in result.error

    def test_execution_log(self, executor):
        """Test execution log tracking."""
        # Log should be empty initially
        log = executor.get_execution_log()
        assert len(log) == 0


class TestMountHandlers:
    """Tests for mount-related tool handlers."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return NightwatchConfig()

    @pytest.fixture
    def orchestrator(self, config):
        """Create orchestrator with mock mount.

        ARCH-002: ``register_*`` leaves status as UNKNOWN; the public
        ``orchestrator.mount`` property only returns the service when
        status is RUNNING. The fixture sets RUNNING explicitly to mirror
        the post-``orchestrator.start()`` state.
        """
        orch = Orchestrator(config)
        mock_mount = AsyncMock()
        mock_mount.is_parked = False
        mock_mount.is_tracking = True
        mock_mount.slew_to_coordinates = AsyncMock(return_value=True)
        mock_mount.park = AsyncMock(return_value=True)
        mock_mount.unpark = AsyncMock(return_value=True)
        orch.register_mount(mock_mount)
        orch.registry.set_status("mount", ServiceStatus.RUNNING)
        return orch

    @pytest.fixture
    def executor(self, orchestrator):
        """Create tool executor."""
        return ToolExecutor(orchestrator)

    @pytest.mark.asyncio
    async def test_goto_object_missing_param(self, executor):
        """Test goto_object with missing parameter."""
        result = await executor.execute("goto_object", {})
        assert result.status == ToolStatus.INVALID_PARAMS

    @pytest.mark.asyncio
    async def test_goto_object_not_found(self, executor):
        """Test goto_object with unknown object."""
        result = await executor.execute("goto_object", {"object_name": "XYZ123"})
        assert result.status == ToolStatus.ERROR
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_goto_object_with_catalog(self, executor, orchestrator):
        """Test goto_object with catalog service."""
        mock_catalog = Mock()
        mock_catalog.resolve_object = Mock(return_value=(10.5, 41.2))
        orchestrator.register_catalog(mock_catalog)
        # ARCH-002: gated property requires RUNNING.
        orchestrator.registry.set_status("catalog", ServiceStatus.RUNNING)

        result = await executor.execute("goto_object", {"object_name": "M31"})
        assert result.status == ToolStatus.SUCCESS
        orchestrator.mount.slew_to_coordinates.assert_called_once()

    @pytest.mark.asyncio
    async def test_park_telescope(self, executor, orchestrator):
        """Test park_telescope handler."""
        result = await executor.execute("park_telescope", {})
        assert result.status == ToolStatus.SUCCESS
        orchestrator.mount.park.assert_called_once()

    @pytest.mark.asyncio
    async def test_unpark_telescope(self, executor, orchestrator):
        """Test unpark_telescope handler."""
        result = await executor.execute("unpark_telescope", {})
        assert result.status == ToolStatus.SUCCESS
        orchestrator.mount.unpark.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_mount_status(self, executor, orchestrator):
        """Test get_mount_status handler."""
        result = await executor.execute("get_mount_status", {})
        assert result.status == ToolStatus.SUCCESS
        assert "is_parked" in result.data
        assert "is_tracking" in result.data


class TestSafetyVeto:
    """Tests for safety veto integration."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return NightwatchConfig()

    @pytest.fixture
    def orchestrator(self, config):
        """Create orchestrator with mock services (ARCH-002: mark RUNNING)."""
        orch = Orchestrator(config)

        mock_mount = AsyncMock()
        mock_mount.slew_to_coordinates = AsyncMock(return_value=True)
        orch.register_mount(mock_mount)

        mock_catalog = Mock()
        mock_catalog.resolve_object = Mock(return_value=(10.5, 41.2))
        orch.register_catalog(mock_catalog)

        mock_safety = Mock()
        mock_safety.is_safe = False
        mock_safety.get_unsafe_reasons = Mock(return_value=["Wind too high"])
        orch.register_safety(mock_safety)

        for name in ("mount", "catalog", "safety"):
            orch.registry.set_status(name, ServiceStatus.RUNNING)

        return orch

    @pytest.fixture
    def executor(self, orchestrator):
        """Create tool executor."""
        return ToolExecutor(orchestrator)

    @pytest.mark.asyncio
    async def test_goto_vetoed_by_safety(self, executor, orchestrator):
        """Test that unsafe conditions veto slew."""
        result = await executor.execute("goto_object", {"object_name": "M31"})
        assert result.status == ToolStatus.VETOED
        assert "Wind too high" in result.data["reasons"]

    @pytest.mark.asyncio
    async def test_unpark_vetoed_by_safety(self, executor, orchestrator):
        """Test that unsafe conditions veto unpark."""
        result = await executor.execute("unpark_telescope", {})
        assert result.status == ToolStatus.VETOED


class TestWeatherHandlers:
    """Tests for weather-related tool handlers."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return NightwatchConfig()

    @pytest.fixture
    def orchestrator(self, config):
        """Create orchestrator with mock weather (ARCH-002: mark RUNNING)."""
        orch = Orchestrator(config)
        mock_weather = Mock()
        mock_weather.is_safe = True
        mock_weather.current_conditions = {
            "temperature": 15.0,
            "humidity": 45,
            "wind_speed": 10,
        }
        orch.register_weather(mock_weather)
        orch.registry.set_status("weather", ServiceStatus.RUNNING)
        return orch

    @pytest.fixture
    def executor(self, orchestrator):
        """Create tool executor."""
        return ToolExecutor(orchestrator)

    @pytest.mark.asyncio
    async def test_get_weather(self, executor):
        """Test get_weather handler."""
        result = await executor.execute("get_weather", {})
        assert result.status == ToolStatus.SUCCESS
        assert "temperature" in result.data

    @pytest.mark.asyncio
    async def test_is_weather_safe(self, executor):
        """Test is_weather_safe handler."""
        result = await executor.execute("is_weather_safe", {})
        assert result.status == ToolStatus.SUCCESS
        assert result.data["is_safe"] is True


class TestSessionHandlers:
    """Tests for session management tool handlers."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return NightwatchConfig()

    @pytest.fixture
    def orchestrator(self, config):
        """Create orchestrator."""
        orch = Orchestrator(config)
        orch._running = True  # Simulate running state
        return orch

    @pytest.fixture
    def executor(self, orchestrator):
        """Create tool executor."""
        return ToolExecutor(orchestrator)

    @pytest.mark.asyncio
    async def test_start_session(self, executor):
        """Test start_session handler."""
        result = await executor.execute("start_session", {"session_id": "test123"})
        assert result.status == ToolStatus.SUCCESS
        assert "test123" in result.data["session_id"]

    @pytest.mark.asyncio
    async def test_get_session_status(self, executor, orchestrator):
        """Test get_session_status handler."""
        await orchestrator.start_session("test")
        result = await executor.execute("get_session_status", {})
        assert result.status == ToolStatus.SUCCESS
        assert result.data["is_observing"] is True


class TestArch002HealthGating:
    """ARCH-002: tool handlers fail fast when mount status is not RUNNING.

    Implements the Verify line from the modernization manual: "stop the mount
    service, then invoke goto_object; the tool returns 'mount service not
    available' without crashing instead of waiting on a dead connection."
    """

    @pytest.fixture
    def config(self):
        return NightwatchConfig()

    @pytest.fixture
    def orchestrator(self, config):
        """Orchestrator with mount + catalog registered and RUNNING."""
        orch = Orchestrator(config)

        mock_mount = AsyncMock()
        mock_mount.slew_to_coordinates = AsyncMock(return_value=True)
        orch.register_mount(mock_mount)
        orch.registry.set_status("mount", ServiceStatus.RUNNING)

        mock_catalog = Mock()
        mock_catalog.resolve_object = Mock(return_value=(0.712, 41.269))
        orch.register_catalog(mock_catalog)
        orch.registry.set_status("catalog", ServiceStatus.RUNNING)

        return orch

    @pytest.fixture
    def executor(self, orchestrator):
        return ToolExecutor(orchestrator)

    @pytest.mark.asyncio
    async def test_goto_object_succeeds_when_mount_running(self, executor, orchestrator):
        """Sanity check: with mount RUNNING, goto_object succeeds."""
        result = await executor.execute("goto_object", {"object_name": "M31"})
        assert result.status == ToolStatus.SUCCESS
        orchestrator.registry.get("mount").slew_to_coordinates.assert_called_once()

    @pytest.mark.asyncio
    async def test_goto_object_returns_mount_unavailable_when_stopped(
        self, executor, orchestrator
    ):
        """ARCH-002 Verify line: mount STOPPED -> 'Mount service not available'."""
        # Stop the mount service (status STOPPED), as if `stop_service("mount")` ran.
        orchestrator.registry.set_status("mount", ServiceStatus.STOPPED)

        result = await executor.execute("goto_object", {"object_name": "M31"})

        assert result.status == ToolStatus.ERROR
        assert result.error == "Mount service not available"
        # And critically: slew_to_coordinates was NOT invoked — we short-circuited
        # before reaching the (potentially dead) mount connection.
        orchestrator.registry.get("mount").slew_to_coordinates.assert_not_called()

    @pytest.mark.asyncio
    async def test_goto_object_returns_mount_unavailable_when_errored(
        self, executor, orchestrator
    ):
        """ARCH-002: mount ERROR -> 'Mount service not available' (no dead-connection wait)."""
        orchestrator.registry.set_status("mount", ServiceStatus.ERROR, "comms lost")

        result = await executor.execute("goto_object", {"object_name": "M31"})

        assert result.status == ToolStatus.ERROR
        assert result.error == "Mount service not available"
        orchestrator.registry.get("mount").slew_to_coordinates.assert_not_called()

    @pytest.mark.asyncio
    async def test_goto_object_returns_mount_unavailable_when_restarting(
        self, executor, orchestrator
    ):
        """ARCH-002: mount RESTARTING -> 'Mount service not available'."""
        orchestrator.registry.set_status("mount", ServiceStatus.RESTARTING)

        result = await executor.execute("goto_object", {"object_name": "M31"})

        assert result.status == ToolStatus.ERROR
        assert result.error == "Mount service not available"
        orchestrator.registry.get("mount").slew_to_coordinates.assert_not_called()


class TestCoordinateParsing:
    """Tests for coordinate parsing helpers."""

    @pytest.fixture
    def executor(self):
        """Create executor for testing."""
        config = NightwatchConfig()
        orch = Orchestrator(config)
        return ToolExecutor(orch)

    def test_parse_ra_hms(self, executor):
        """Test RA parsing from HH:MM:SS."""
        assert executor._parse_ra("10:30:00") == pytest.approx(10.5, rel=0.01)
        assert executor._parse_ra("0:0:0") == 0.0
        assert executor._parse_ra("23:59:59") == pytest.approx(24.0, rel=0.01)

    def test_parse_ra_hm(self, executor):
        """Test RA parsing from HH:MM."""
        assert executor._parse_ra("10:30") == pytest.approx(10.5, rel=0.01)

    def test_parse_dec_dms(self, executor):
        """Test Dec parsing from sDD:MM:SS."""
        assert executor._parse_dec("+45:30:00") == pytest.approx(45.5, rel=0.01)
        assert executor._parse_dec("-45:30:00") == pytest.approx(-45.5, rel=0.01)
        assert executor._parse_dec("0:0:0") == 0.0

    def test_parse_dec_dm(self, executor):
        """Test Dec parsing from sDD:MM."""
        assert executor._parse_dec("+45:30") == pytest.approx(45.5, rel=0.01)
        assert executor._parse_dec("-45:30") == pytest.approx(-45.5, rel=0.01)


class TestArch001ParamValidation:
    """ARCH-001: Pydantic param validation at execute() entry.

    Risk #1 from the Phase 1 audit: garbage LLM-generated tool args could
    silently slip through (params.get returns None) and hang downstream
    handlers. After ARCH-001, every tool's parameters are validated against
    a registered Pydantic model before the handler is dispatched.
    """

    @pytest.fixture
    def config(self):
        return NightwatchConfig()

    @pytest.fixture
    def orchestrator(self, config):
        return Orchestrator(config)

    @pytest.fixture
    def executor(self, orchestrator):
        return ToolExecutor(orchestrator)

    @pytest.mark.asyncio
    async def test_goto_object_rejects_non_string_object_name(self, executor):
        """Spec verify line: {object_name: 42} -> INVALID_PARAMS, handler never reached."""
        with patch.object(executor, "_handle_goto_object") as mock_handler:
            result = await executor.execute("goto_object", {"object_name": 42})
        assert result.status == ToolStatus.INVALID_PARAMS
        assert "object_name" in result.error.lower()
        assert "str" in result.error.lower() or "string" in result.error.lower()
        mock_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_goto_object_missing_param_returns_invalid_params(self, executor):
        """Missing required field -> INVALID_PARAMS, not a downstream crash."""
        result = await executor.execute("goto_object", {})
        assert result.status == ToolStatus.INVALID_PARAMS

    @pytest.mark.asyncio
    async def test_zero_arg_tool_accepts_empty_dict(self, executor):
        """park_telescope uses NoParams; {} is valid."""
        result = await executor.execute("park_telescope", {})
        assert result.status != ToolStatus.INVALID_PARAMS

    @pytest.mark.asyncio
    async def test_extra_param_rejected_when_forbid(self, executor):
        """extra='forbid' means stray fields halt before the handler runs."""
        with patch.object(executor, "_handle_goto_object") as mock_handler:
            result = await executor.execute(
                "goto_object", {"object_name": "M31", "extra_field": "x"}
            )
        assert result.status == ToolStatus.INVALID_PARAMS
        mock_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_goto_coordinates_accepts_floats(self, executor):
        """Coordinates as float pass validation (handler-level errors are separate)."""
        result = await executor.execute(
            "goto_coordinates", {"ra": 10.5, "dec": 41.2}
        )
        # Handler will return ERROR (no mount registered) — the point is that
        # validation passed and we got past the INVALID_PARAMS gate.
        assert result.status != ToolStatus.INVALID_PARAMS

    @pytest.mark.asyncio
    async def test_goto_coordinates_accepts_strings(self, executor):
        """RA/Dec as HH:MM:SS / sDD:MM:SS strings pass validation (Union[float, str])."""
        result = await executor.execute(
            "goto_coordinates", {"ra": "10:30:00", "dec": "+41:12:00"}
        )
        assert result.status != ToolStatus.INVALID_PARAMS

    @pytest.mark.asyncio
    async def test_goto_coordinates_missing_dec_returns_invalid_params(self, executor):
        result = await executor.execute("goto_coordinates", {"ra": 10.5})
        assert result.status == ToolStatus.INVALID_PARAMS
        assert "dec" in result.error.lower()

    @pytest.mark.asyncio
    async def test_lookup_object_rejects_non_string(self, executor):
        with patch.object(executor, "_handle_lookup_object") as mock_handler:
            result = await executor.execute("lookup_object", {"object_name": 99})
        assert result.status == ToolStatus.INVALID_PARAMS
        mock_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_planet_position_rejects_non_string(self, executor):
        with patch.object(executor, "_handle_get_planet_position") as mock_handler:
            result = await executor.execute("get_planet_position", {"planet": 7})
        assert result.status == ToolStatus.INVALID_PARAMS
        mock_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_session_id_optional(self, executor):
        """session_id is optional — empty dict validates, orchestrator generates one."""
        # Need _running to test start_session end-to-end; we only need to assert
        # validation does NOT reject.
        executor.orchestrator._running = True
        result = await executor.execute("start_session", {})
        assert result.status != ToolStatus.INVALID_PARAMS

    @pytest.mark.asyncio
    async def test_zero_arg_tool_rejects_extra_param(self, executor):
        """park_telescope with bogus param -> INVALID_PARAMS."""
        with patch.object(executor, "_handle_park") as mock_handler:
            result = await executor.execute("park_telescope", {"force": True})
        assert result.status == ToolStatus.INVALID_PARAMS
        mock_handler.assert_not_called()
