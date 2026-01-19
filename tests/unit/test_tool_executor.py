"""
Unit tests for NIGHTWATCH Tool Executor.

Tests tool execution, parameter validation, and service integration.
"""

import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock

import pytest

from nightwatch.tool_executor import (
    ToolExecutor,
    ToolResult,
    ToolStatus,
    ToolExecutionError,
)
from nightwatch.config import NightwatchConfig
from nightwatch.orchestrator import Orchestrator


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
        executor.register_handler("custom_tool", handler)
        assert "custom_tool" in executor._handlers

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

        executor.register_handler("slow_tool", slow_handler)
        result = await executor.execute("slow_tool", {}, timeout=0.1)
        assert result.status == ToolStatus.TIMEOUT

    @pytest.mark.asyncio
    async def test_execute_with_exception(self, executor):
        """Test tool execution with exception."""
        async def failing_handler(params):
            raise ValueError("Test error")

        executor.register_handler("failing_tool", failing_handler)
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
        """Create orchestrator with mock mount."""
        orch = Orchestrator(config)
        mock_mount = AsyncMock()
        mock_mount.is_parked = False
        mock_mount.is_tracking = True
        mock_mount.slew_to_coordinates = AsyncMock(return_value=True)
        mock_mount.park = AsyncMock(return_value=True)
        mock_mount.unpark = AsyncMock(return_value=True)
        orch.register_mount(mock_mount)
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
        """Create orchestrator with mock services."""
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
        """Create orchestrator with mock weather."""
        orch = Orchestrator(config)
        mock_weather = Mock()
        mock_weather.is_safe = True
        mock_weather.current_conditions = {
            "temperature": 15.0,
            "humidity": 45,
            "wind_speed": 10,
        }
        orch.register_weather(mock_weather)
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
