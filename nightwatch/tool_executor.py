"""
NIGHTWATCH Tool Executor
Bridges voice tools to actual service calls.

The ToolExecutor takes LLM tool calls (from telescope_tools.py definitions)
and executes them against the actual services via the Orchestrator.

Architecture:
    Voice Input -> STT -> LLM -> Tool Selection
                                      |
                              +-------v--------+
                              | ToolExecutor   |
                              +-------+--------+
                                      |
                              +-------v--------+
                              | Orchestrator   |
                              +-------+--------+
                                      |
                              +-------v--------+
                              | Services       |
                              +----------------+

Usage:
    from nightwatch.tool_executor import ToolExecutor
    from nightwatch.orchestrator import Orchestrator

    orchestrator = Orchestrator(config)
    executor = ToolExecutor(orchestrator)

    # Execute a tool call from LLM
    result = await executor.execute("goto_object", {"object_name": "M31"})
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from nightwatch.exceptions import NightwatchError, CommandError

logger = logging.getLogger("NIGHTWATCH.ToolExecutor")


__all__ = [
    "ToolExecutor",
    "ToolResult",
    "ToolStatus",
    "ToolExecutionError",
    "ToolChain",
    "ChainStep",
    "ChainResult",
]


# =============================================================================
# Result Types
# =============================================================================


class ToolStatus(Enum):
    """Tool execution status."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    VETOED = "vetoed"  # Safety system blocked the action
    NOT_FOUND = "not_found"
    INVALID_PARAMS = "invalid_params"


@dataclass
class ToolResult:
    """Result of a tool execution."""
    tool_name: str
    status: ToolStatus
    data: Optional[Dict[str, Any]] = None
    message: str = ""
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.status == ToolStatus.SUCCESS

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tool_name": self.tool_name,
            "status": self.status.value,
            "data": self.data,
            "message": self.message,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class ToolExecutionError(NightwatchError):
    """Error during tool execution."""
    pass


# =============================================================================
# Tool Executor
# =============================================================================


class ToolExecutor:
    """
    Executes LLM tool calls against actual services.

    Maps tool names to service methods and handles:
    - Parameter validation
    - Service availability checking
    - Safety veto integration
    - Timeout handling
    - Result formatting
    - Execution logging
    """

    def __init__(self, orchestrator, default_timeout: float = 30.0):
        """
        Initialize tool executor.

        Args:
            orchestrator: NIGHTWATCH orchestrator instance
            default_timeout: Default timeout for tool execution in seconds
        """
        self.orchestrator = orchestrator
        self.default_timeout = default_timeout
        self._handlers: Dict[str, Callable] = {}
        self._execution_log: List[ToolResult] = []

        # Register built-in handlers
        self._register_default_handlers()

        logger.info("ToolExecutor initialized")

    # =========================================================================
    # Handler Registration
    # =========================================================================

    def register_handler(self, tool_name: str, handler: Callable):
        """
        Register a handler for a tool.

        Args:
            tool_name: Name of the tool
            handler: Async function to handle the tool call
        """
        self._handlers[tool_name] = handler
        logger.debug(f"Registered handler for tool: {tool_name}")

    def _register_default_handlers(self):
        """Register default handlers for built-in tools."""
        # Mount control
        self.register_handler("goto_object", self._handle_goto_object)
        self.register_handler("goto_coordinates", self._handle_goto_coordinates)
        self.register_handler("park_telescope", self._handle_park)
        self.register_handler("unpark_telescope", self._handle_unpark)
        self.register_handler("stop_mount", self._handle_stop_mount)
        self.register_handler("get_mount_status", self._handle_get_mount_status)

        # Catalog
        self.register_handler("lookup_object", self._handle_lookup_object)
        self.register_handler("what_is", self._handle_what_is)

        # Ephemeris
        self.register_handler("get_planet_position", self._handle_get_planet_position)
        self.register_handler("get_sun_status", self._handle_get_sun_status)
        self.register_handler("get_twilight_times", self._handle_get_twilight_times)

        # Weather
        self.register_handler("get_weather", self._handle_get_weather)
        self.register_handler("is_weather_safe", self._handle_is_weather_safe)

        # Safety
        self.register_handler("get_safety_status", self._handle_get_safety_status)
        self.register_handler("check_can_observe", self._handle_check_can_observe)

        # Session
        self.register_handler("start_session", self._handle_start_session)
        self.register_handler("end_session", self._handle_end_session)
        self.register_handler("get_session_status", self._handle_get_session_status)

    # =========================================================================
    # Execution
    # =========================================================================

    async def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> ToolResult:
        """
        Execute a tool with the given parameters.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            timeout: Optional timeout override

        Returns:
            ToolResult with execution status and data
        """
        start_time = time.time()
        timeout = timeout or self.default_timeout

        logger.info(f"Executing tool: {tool_name} with params: {parameters}")

        # Check if handler exists
        handler = self._handlers.get(tool_name)
        if not handler:
            result = ToolResult(
                tool_name=tool_name,
                status=ToolStatus.NOT_FOUND,
                error=f"Unknown tool: {tool_name}",
                message=f"I don't know how to do '{tool_name}'",
            )
            self._log_execution(result)
            return result

        # Execute with timeout
        try:
            async with asyncio.timeout(timeout):
                result = await handler(parameters)

        except asyncio.TimeoutError:
            result = ToolResult(
                tool_name=tool_name,
                status=ToolStatus.TIMEOUT,
                error=f"Tool execution timed out after {timeout}s",
                message="The operation took too long and was cancelled",
            )

        except ToolExecutionError as e:
            result = ToolResult(
                tool_name=tool_name,
                status=ToolStatus.ERROR,
                error=str(e),
                message=str(e),
            )

        except Exception as e:
            logger.exception(f"Tool execution error: {tool_name}")
            result = ToolResult(
                tool_name=tool_name,
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"An error occurred: {e}",
            )

        # Record execution time
        result.execution_time_ms = (time.time() - start_time) * 1000
        self._log_execution(result)

        return result

    def _log_execution(self, result: ToolResult):
        """Log tool execution for audit trail."""
        self._execution_log.append(result)

        # Keep last 1000 executions
        if len(self._execution_log) > 1000:
            self._execution_log = self._execution_log[-1000:]

        level = logging.INFO if result.success else logging.WARNING
        logger.log(
            level,
            f"Tool {result.tool_name}: {result.status.value} "
            f"({result.execution_time_ms:.1f}ms)"
        )

    def get_execution_log(self, limit: int = 100) -> List[ToolResult]:
        """Get recent execution log."""
        return self._execution_log[-limit:]

    # =========================================================================
    # Mount Handlers
    # =========================================================================

    async def _handle_goto_object(self, params: Dict[str, Any]) -> ToolResult:
        """Handle goto_object tool."""
        object_name = params.get("object_name")
        if not object_name:
            return ToolResult(
                tool_name="goto_object",
                status=ToolStatus.INVALID_PARAMS,
                error="Missing object_name parameter",
                message="Please specify an object name",
            )

        # Check safety first
        if self.orchestrator.safety:
            if not self.orchestrator.safety.is_safe:
                reasons = self.orchestrator.safety.get_unsafe_reasons()
                return ToolResult(
                    tool_name="goto_object",
                    status=ToolStatus.VETOED,
                    error="Safety conditions not met",
                    message=f"Cannot slew: {', '.join(reasons)}",
                    data={"reasons": reasons},
                )

        # Resolve object coordinates
        coords = None
        if self.orchestrator.catalog:
            coords = self.orchestrator.catalog.resolve_object(object_name)

        if not coords:
            # Try ephemeris for planets
            if self.orchestrator.ephemeris:
                coords = self.orchestrator.ephemeris.get_planet_position(object_name)

        if not coords:
            return ToolResult(
                tool_name="goto_object",
                status=ToolStatus.ERROR,
                error=f"Object not found: {object_name}",
                message=f"I couldn't find an object named '{object_name}'",
            )

        ra, dec = coords

        # Execute slew
        if not self.orchestrator.mount:
            return ToolResult(
                tool_name="goto_object",
                status=ToolStatus.ERROR,
                error="Mount service not available",
                message="The telescope mount is not connected",
            )

        try:
            success = await self.orchestrator.mount.slew_to_coordinates(ra, dec)
            if success:
                return ToolResult(
                    tool_name="goto_object",
                    status=ToolStatus.SUCCESS,
                    message=f"Now pointing at {object_name}",
                    data={"object": object_name, "ra": ra, "dec": dec},
                )
            else:
                return ToolResult(
                    tool_name="goto_object",
                    status=ToolStatus.ERROR,
                    error="Slew failed",
                    message=f"Failed to slew to {object_name}",
                )
        except Exception as e:
            return ToolResult(
                tool_name="goto_object",
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"Error slewing to {object_name}: {e}",
            )

    async def _handle_goto_coordinates(self, params: Dict[str, Any]) -> ToolResult:
        """Handle goto_coordinates tool."""
        ra = params.get("ra")
        dec = params.get("dec")

        if not ra or not dec:
            return ToolResult(
                tool_name="goto_coordinates",
                status=ToolStatus.INVALID_PARAMS,
                error="Missing ra or dec parameter",
                message="Please specify both RA and Dec coordinates",
            )

        # Check safety
        if self.orchestrator.safety and not self.orchestrator.safety.is_safe:
            return ToolResult(
                tool_name="goto_coordinates",
                status=ToolStatus.VETOED,
                error="Safety conditions not met",
                message="Cannot slew due to safety conditions",
            )

        if not self.orchestrator.mount:
            return ToolResult(
                tool_name="goto_coordinates",
                status=ToolStatus.ERROR,
                error="Mount service not available",
                message="The telescope mount is not connected",
            )

        # Parse coordinates (assuming they might be strings)
        try:
            ra_val = float(ra) if isinstance(ra, (int, float)) else self._parse_ra(ra)
            dec_val = float(dec) if isinstance(dec, (int, float)) else self._parse_dec(dec)
        except ValueError as e:
            return ToolResult(
                tool_name="goto_coordinates",
                status=ToolStatus.INVALID_PARAMS,
                error=str(e),
                message="Invalid coordinate format",
            )

        try:
            success = await self.orchestrator.mount.slew_to_coordinates(ra_val, dec_val)
            if success:
                return ToolResult(
                    tool_name="goto_coordinates",
                    status=ToolStatus.SUCCESS,
                    message=f"Now pointing at RA {ra}, Dec {dec}",
                    data={"ra": ra_val, "dec": dec_val},
                )
            else:
                return ToolResult(
                    tool_name="goto_coordinates",
                    status=ToolStatus.ERROR,
                    error="Slew failed",
                    message="Failed to slew to coordinates",
                )
        except Exception as e:
            return ToolResult(
                tool_name="goto_coordinates",
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"Error slewing: {e}",
            )

    async def _handle_park(self, params: Dict[str, Any]) -> ToolResult:
        """Handle park_telescope tool."""
        if not self.orchestrator.mount:
            return ToolResult(
                tool_name="park_telescope",
                status=ToolStatus.ERROR,
                error="Mount service not available",
                message="The telescope mount is not connected",
            )

        try:
            success = await self.orchestrator.mount.park()
            if success:
                return ToolResult(
                    tool_name="park_telescope",
                    status=ToolStatus.SUCCESS,
                    message="Telescope is now parked",
                )
            else:
                return ToolResult(
                    tool_name="park_telescope",
                    status=ToolStatus.ERROR,
                    error="Park failed",
                    message="Failed to park telescope",
                )
        except Exception as e:
            return ToolResult(
                tool_name="park_telescope",
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"Error parking: {e}",
            )

    async def _handle_unpark(self, params: Dict[str, Any]) -> ToolResult:
        """Handle unpark_telescope tool."""
        if not self.orchestrator.mount:
            return ToolResult(
                tool_name="unpark_telescope",
                status=ToolStatus.ERROR,
                error="Mount service not available",
                message="The telescope mount is not connected",
            )

        # Check safety before unparking
        if self.orchestrator.safety and not self.orchestrator.safety.is_safe:
            return ToolResult(
                tool_name="unpark_telescope",
                status=ToolStatus.VETOED,
                error="Safety conditions not met",
                message="Cannot unpark due to safety conditions",
            )

        try:
            success = await self.orchestrator.mount.unpark()
            if success:
                return ToolResult(
                    tool_name="unpark_telescope",
                    status=ToolStatus.SUCCESS,
                    message="Telescope is now unparked and ready",
                )
            else:
                return ToolResult(
                    tool_name="unpark_telescope",
                    status=ToolStatus.ERROR,
                    error="Unpark failed",
                    message="Failed to unpark telescope",
                )
        except Exception as e:
            return ToolResult(
                tool_name="unpark_telescope",
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"Error unparking: {e}",
            )

    async def _handle_stop_mount(self, params: Dict[str, Any]) -> ToolResult:
        """Handle stop_mount tool."""
        if not self.orchestrator.mount:
            return ToolResult(
                tool_name="stop_mount",
                status=ToolStatus.ERROR,
                error="Mount service not available",
                message="The telescope mount is not connected",
            )

        try:
            if hasattr(self.orchestrator.mount, 'stop'):
                await self.orchestrator.mount.stop()
            return ToolResult(
                tool_name="stop_mount",
                status=ToolStatus.SUCCESS,
                message="Mount motion stopped",
            )
        except Exception as e:
            return ToolResult(
                tool_name="stop_mount",
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"Error stopping mount: {e}",
            )

    async def _handle_get_mount_status(self, params: Dict[str, Any]) -> ToolResult:
        """Handle get_mount_status tool."""
        if not self.orchestrator.mount:
            return ToolResult(
                tool_name="get_mount_status",
                status=ToolStatus.ERROR,
                error="Mount service not available",
                message="The telescope mount is not connected",
            )

        try:
            is_parked = self.orchestrator.mount.is_parked
            is_tracking = self.orchestrator.mount.is_tracking

            return ToolResult(
                tool_name="get_mount_status",
                status=ToolStatus.SUCCESS,
                message=f"Mount is {'parked' if is_parked else 'unparked'}, "
                        f"{'tracking' if is_tracking else 'not tracking'}",
                data={"is_parked": is_parked, "is_tracking": is_tracking},
            )
        except Exception as e:
            return ToolResult(
                tool_name="get_mount_status",
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"Error getting mount status: {e}",
            )

    # =========================================================================
    # Catalog Handlers
    # =========================================================================

    async def _handle_lookup_object(self, params: Dict[str, Any]) -> ToolResult:
        """Handle lookup_object tool."""
        object_name = params.get("object_name")
        if not object_name:
            return ToolResult(
                tool_name="lookup_object",
                status=ToolStatus.INVALID_PARAMS,
                error="Missing object_name parameter",
                message="Please specify an object name",
            )

        if not self.orchestrator.catalog:
            return ToolResult(
                tool_name="lookup_object",
                status=ToolStatus.ERROR,
                error="Catalog service not available",
                message="The catalog database is not available",
            )

        try:
            obj = self.orchestrator.catalog.lookup(object_name)
            if obj:
                return ToolResult(
                    tool_name="lookup_object",
                    status=ToolStatus.SUCCESS,
                    message=f"Found {object_name}",
                    data={"object": obj} if isinstance(obj, dict) else {"name": object_name},
                )
            else:
                return ToolResult(
                    tool_name="lookup_object",
                    status=ToolStatus.ERROR,
                    error=f"Object not found: {object_name}",
                    message=f"I couldn't find '{object_name}' in the catalog",
                )
        except Exception as e:
            return ToolResult(
                tool_name="lookup_object",
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"Error looking up object: {e}",
            )

    async def _handle_what_is(self, params: Dict[str, Any]) -> ToolResult:
        """Handle what_is tool - conversational object info."""
        object_name = params.get("object_name")
        if not object_name:
            return ToolResult(
                tool_name="what_is",
                status=ToolStatus.INVALID_PARAMS,
                error="Missing object_name parameter",
                message="What object would you like to know about?",
            )

        if not self.orchestrator.catalog:
            return ToolResult(
                tool_name="what_is",
                status=ToolStatus.ERROR,
                error="Catalog service not available",
                message="The catalog database is not available",
            )

        try:
            if hasattr(self.orchestrator.catalog, 'what_is'):
                description = self.orchestrator.catalog.what_is(object_name)
                return ToolResult(
                    tool_name="what_is",
                    status=ToolStatus.SUCCESS,
                    message=description,
                    data={"object": object_name},
                )
            else:
                obj = self.orchestrator.catalog.lookup(object_name)
                if obj:
                    return ToolResult(
                        tool_name="what_is",
                        status=ToolStatus.SUCCESS,
                        message=f"{object_name} is a celestial object in the catalog",
                        data={"object": object_name},
                    )
                else:
                    return ToolResult(
                        tool_name="what_is",
                        status=ToolStatus.ERROR,
                        error=f"Object not found: {object_name}",
                        message=f"I don't have information about '{object_name}'",
                    )
        except Exception as e:
            return ToolResult(
                tool_name="what_is",
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"Error: {e}",
            )

    # =========================================================================
    # Ephemeris Handlers
    # =========================================================================

    async def _handle_get_planet_position(self, params: Dict[str, Any]) -> ToolResult:
        """Handle get_planet_position tool."""
        planet = params.get("planet")
        if not planet:
            return ToolResult(
                tool_name="get_planet_position",
                status=ToolStatus.INVALID_PARAMS,
                error="Missing planet parameter",
                message="Which planet would you like to find?",
            )

        if not self.orchestrator.ephemeris:
            return ToolResult(
                tool_name="get_planet_position",
                status=ToolStatus.ERROR,
                error="Ephemeris service not available",
                message="The ephemeris service is not available",
            )

        try:
            coords = self.orchestrator.ephemeris.get_planet_position(planet)
            if coords:
                ra, dec = coords
                return ToolResult(
                    tool_name="get_planet_position",
                    status=ToolStatus.SUCCESS,
                    message=f"{planet} is currently at RA {ra:.2f}h, Dec {dec:.1f}°",
                    data={"planet": planet, "ra": ra, "dec": dec},
                )
            else:
                return ToolResult(
                    tool_name="get_planet_position",
                    status=ToolStatus.ERROR,
                    error=f"Planet not found: {planet}",
                    message=f"I couldn't find position data for '{planet}'",
                )
        except Exception as e:
            return ToolResult(
                tool_name="get_planet_position",
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"Error getting planet position: {e}",
            )

    async def _handle_get_sun_status(self, params: Dict[str, Any]) -> ToolResult:
        """Handle get_sun_status tool."""
        if not self.orchestrator.ephemeris:
            return ToolResult(
                tool_name="get_sun_status",
                status=ToolStatus.ERROR,
                error="Ephemeris service not available",
                message="The ephemeris service is not available",
            )

        try:
            altitude = self.orchestrator.ephemeris.get_sun_altitude()
            if altitude > 0:
                status = "up"
                message = f"The sun is up at {altitude:.1f}° altitude"
            elif altitude > -6:
                status = "civil_twilight"
                message = f"Civil twilight, sun at {altitude:.1f}°"
            elif altitude > -12:
                status = "nautical_twilight"
                message = f"Nautical twilight, sun at {altitude:.1f}°"
            elif altitude > -18:
                status = "astronomical_twilight"
                message = f"Astronomical twilight, sun at {altitude:.1f}°"
            else:
                status = "night"
                message = f"It's nighttime, sun at {altitude:.1f}°"

            return ToolResult(
                tool_name="get_sun_status",
                status=ToolStatus.SUCCESS,
                message=message,
                data={"sun_altitude": altitude, "status": status},
            )
        except Exception as e:
            return ToolResult(
                tool_name="get_sun_status",
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"Error getting sun status: {e}",
            )

    async def _handle_get_twilight_times(self, params: Dict[str, Any]) -> ToolResult:
        """Handle get_twilight_times tool."""
        if not self.orchestrator.ephemeris:
            return ToolResult(
                tool_name="get_twilight_times",
                status=ToolStatus.ERROR,
                error="Ephemeris service not available",
                message="The ephemeris service is not available",
            )

        try:
            times = self.orchestrator.ephemeris.get_twilight_times()
            return ToolResult(
                tool_name="get_twilight_times",
                status=ToolStatus.SUCCESS,
                message="Here are today's twilight times",
                data=times,
            )
        except Exception as e:
            return ToolResult(
                tool_name="get_twilight_times",
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"Error getting twilight times: {e}",
            )

    # =========================================================================
    # Weather Handlers
    # =========================================================================

    async def _handle_get_weather(self, params: Dict[str, Any]) -> ToolResult:
        """Handle get_weather tool."""
        if not self.orchestrator.weather:
            return ToolResult(
                tool_name="get_weather",
                status=ToolStatus.ERROR,
                error="Weather service not available",
                message="The weather station is not connected",
            )

        try:
            conditions = self.orchestrator.weather.current_conditions
            return ToolResult(
                tool_name="get_weather",
                status=ToolStatus.SUCCESS,
                message="Current weather conditions retrieved",
                data=conditions,
            )
        except Exception as e:
            return ToolResult(
                tool_name="get_weather",
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"Error getting weather: {e}",
            )

    async def _handle_is_weather_safe(self, params: Dict[str, Any]) -> ToolResult:
        """Handle is_weather_safe tool."""
        if not self.orchestrator.weather:
            return ToolResult(
                tool_name="is_weather_safe",
                status=ToolStatus.ERROR,
                error="Weather service not available",
                message="The weather station is not connected",
            )

        try:
            is_safe = self.orchestrator.weather.is_safe
            return ToolResult(
                tool_name="is_weather_safe",
                status=ToolStatus.SUCCESS,
                message="Weather is safe for observing" if is_safe else "Weather is NOT safe for observing",
                data={"is_safe": is_safe},
            )
        except Exception as e:
            return ToolResult(
                tool_name="is_weather_safe",
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"Error checking weather safety: {e}",
            )

    # =========================================================================
    # Safety Handlers
    # =========================================================================

    async def _handle_get_safety_status(self, params: Dict[str, Any]) -> ToolResult:
        """Handle get_safety_status tool."""
        if not self.orchestrator.safety:
            return ToolResult(
                tool_name="get_safety_status",
                status=ToolStatus.ERROR,
                error="Safety monitor not available",
                message="The safety monitor is not connected",
            )

        try:
            is_safe = self.orchestrator.safety.is_safe
            reasons = self.orchestrator.safety.get_unsafe_reasons() if not is_safe else []
            return ToolResult(
                tool_name="get_safety_status",
                status=ToolStatus.SUCCESS,
                message="All systems safe" if is_safe else f"UNSAFE: {', '.join(reasons)}",
                data={"is_safe": is_safe, "unsafe_reasons": reasons},
            )
        except Exception as e:
            return ToolResult(
                tool_name="get_safety_status",
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"Error getting safety status: {e}",
            )

    async def _handle_check_can_observe(self, params: Dict[str, Any]) -> ToolResult:
        """Handle check_can_observe tool."""
        can_observe = True
        reasons = []

        # Check safety
        if self.orchestrator.safety:
            if not self.orchestrator.safety.is_safe:
                can_observe = False
                reasons.extend(self.orchestrator.safety.get_unsafe_reasons())

        # Check weather
        if self.orchestrator.weather:
            if not self.orchestrator.weather.is_safe:
                can_observe = False
                reasons.append("Weather unsafe")

        # Check mount
        if not self.orchestrator.mount:
            can_observe = False
            reasons.append("Mount not connected")

        return ToolResult(
            tool_name="check_can_observe",
            status=ToolStatus.SUCCESS,
            message="Ready to observe!" if can_observe else f"Cannot observe: {', '.join(reasons)}",
            data={"can_observe": can_observe, "reasons": reasons},
        )

    # =========================================================================
    # Session Handlers
    # =========================================================================

    async def _handle_start_session(self, params: Dict[str, Any]) -> ToolResult:
        """Handle start_session tool."""
        session_id = params.get("session_id")

        try:
            success = await self.orchestrator.start_session(session_id)
            if success:
                return ToolResult(
                    tool_name="start_session",
                    status=ToolStatus.SUCCESS,
                    message=f"Observing session started: {self.orchestrator.session.session_id}",
                    data={"session_id": self.orchestrator.session.session_id},
                )
            else:
                return ToolResult(
                    tool_name="start_session",
                    status=ToolStatus.ERROR,
                    error="Failed to start session",
                    message="Could not start observing session",
                )
        except Exception as e:
            return ToolResult(
                tool_name="start_session",
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"Error starting session: {e}",
            )

    async def _handle_end_session(self, params: Dict[str, Any]) -> ToolResult:
        """Handle end_session tool."""
        try:
            await self.orchestrator.end_session()
            return ToolResult(
                tool_name="end_session",
                status=ToolStatus.SUCCESS,
                message="Observing session ended",
            )
        except Exception as e:
            return ToolResult(
                tool_name="end_session",
                status=ToolStatus.ERROR,
                error=str(e),
                message=f"Error ending session: {e}",
            )

    async def _handle_get_session_status(self, params: Dict[str, Any]) -> ToolResult:
        """Handle get_session_status tool."""
        session = self.orchestrator.session
        return ToolResult(
            tool_name="get_session_status",
            status=ToolStatus.SUCCESS,
            message=f"Session {'active' if session.is_observing else 'inactive'}",
            data={
                "session_id": session.session_id,
                "is_observing": session.is_observing,
                "images_captured": session.images_captured,
                "current_target": session.current_target.name if session.current_target else None,
            },
        )

    # =========================================================================
    # Coordinate Parsing Helpers
    # =========================================================================

    def _parse_ra(self, ra_str: str) -> float:
        """Parse RA string (HH:MM:SS) to decimal hours."""
        parts = ra_str.replace("h", ":").replace("m", ":").replace("s", "").split(":")
        if len(parts) == 3:
            h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
            return h + m/60 + s/3600
        elif len(parts) == 2:
            h, m = float(parts[0]), float(parts[1])
            return h + m/60
        else:
            return float(ra_str)

    def _parse_dec(self, dec_str: str) -> float:
        """Parse Dec string (sDD:MM:SS) to decimal degrees."""
        dec_str = dec_str.strip()
        sign = -1 if dec_str.startswith("-") else 1
        dec_str = dec_str.lstrip("+-")

        parts = dec_str.replace("°", ":").replace("'", ":").replace('"', "").split(":")
        if len(parts) == 3:
            d, m, s = float(parts[0]), float(parts[1]), float(parts[2])
            return sign * (d + m/60 + s/3600)
        elif len(parts) == 2:
            d, m = float(parts[0]), float(parts[1])
            return sign * (d + m/60)
        else:
            return float(dec_str) * sign


# =============================================================================
# Tool Chaining (Step 267)
# =============================================================================


@dataclass
class ChainStep:
    """
    A single step in a tool chain.

    Attributes:
        tool_name: Name of the tool to execute
        parameters: Static parameters for the tool
        param_mappings: Dynamic parameter mappings from previous step results
        condition: Optional condition function to check before executing
        on_failure: Action on failure: "stop", "skip", or "continue"
        description: Human-readable description of this step
    """
    tool_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    param_mappings: Dict[str, str] = field(default_factory=dict)
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    on_failure: str = "stop"  # "stop", "skip", "continue"
    description: str = ""

    def __post_init__(self):
        if self.on_failure not in ("stop", "skip", "continue"):
            raise ValueError(f"Invalid on_failure: {self.on_failure}")


@dataclass
class ChainResult:
    """
    Result of executing a tool chain.

    Attributes:
        success: Whether all required steps completed successfully
        steps_executed: Number of steps that were executed
        steps_total: Total number of steps in the chain
        results: List of ToolResults for each executed step
        final_data: Aggregated data from all successful steps
        message: Summary message
        execution_time_ms: Total execution time
    """
    success: bool
    steps_executed: int
    steps_total: int
    results: List[ToolResult] = field(default_factory=list)
    final_data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "steps_executed": self.steps_executed,
            "steps_total": self.steps_total,
            "results": [r.to_dict() for r in self.results],
            "final_data": self.final_data,
            "message": self.message,
            "execution_time_ms": self.execution_time_ms,
        }


class ToolChain:
    """
    Tool chain for executing complex multi-step commands (Step 267).

    Allows chaining multiple tools together, with parameter passing
    between steps and conditional execution.

    Example usage:
        chain = ToolChain("slew_and_capture", executor)

        # Add steps
        chain.add_step("goto_object", {"object_name": "M31"})
        chain.add_step("capture_image", {"exposure_sec": 30})

        # Execute the chain
        result = await chain.execute()

    Example with parameter passing:
        chain = ToolChain("lookup_and_goto", executor)
        chain.add_step("lookup_object", {"object_name": "M42"})
        chain.add_step(
            "goto_coordinates",
            param_mappings={"ra": "lookup_object.ra", "dec": "lookup_object.dec"}
        )

    Built-in chains:
        - "slew_and_capture": Slew to object, then capture image
        - "focus_and_capture": Autofocus, then capture image
        - "full_imaging": Slew, focus, guide, capture sequence
    """

    # Built-in chain definitions
    BUILTIN_CHAINS: Dict[str, List[Dict[str, Any]]] = {
        "slew_and_capture": [
            {"tool": "goto_object", "params": {}, "param_keys": ["object_name"]},
            {"tool": "capture_image", "params": {"exposure_sec": 30}, "param_keys": ["exposure_sec"]},
        ],
        "focus_and_capture": [
            {"tool": "autofocus", "params": {}},
            {"tool": "capture_image", "params": {"exposure_sec": 30}, "param_keys": ["exposure_sec"]},
        ],
        "safe_shutdown": [
            {"tool": "stop_guiding", "params": {}, "on_failure": "continue"},
            {"tool": "park_telescope", "params": {}},
            {"tool": "close_enclosure", "params": {}, "on_failure": "continue"},
        ],
        "startup_sequence": [
            {"tool": "check_can_observe", "params": {}},
            {"tool": "open_enclosure", "params": {}, "on_failure": "stop"},
            {"tool": "unpark_telescope", "params": {}},
        ],
    }

    def __init__(
        self,
        name: str,
        executor: ToolExecutor,
        description: str = "",
        stop_on_veto: bool = True
    ):
        """
        Initialize a tool chain.

        Args:
            name: Name of the chain (for logging)
            executor: ToolExecutor instance to execute tools
            description: Human-readable description
            stop_on_veto: Whether to stop the chain if a step is vetoed
        """
        self.name = name
        self.executor = executor
        self.description = description
        self.stop_on_veto = stop_on_veto
        self._steps: List[ChainStep] = []
        self._context: Dict[str, Any] = {}

        logger.debug(f"ToolChain '{name}' created")

    def add_step(
        self,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        param_mappings: Optional[Dict[str, str]] = None,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
        on_failure: str = "stop",
        description: str = ""
    ) -> "ToolChain":
        """
        Add a step to the chain.

        Args:
            tool_name: Name of the tool to execute
            parameters: Static parameters for the tool
            param_mappings: Dynamic mappings like {"ra": "step1.data.ra"}
            condition: Function that returns True if step should execute
            on_failure: "stop", "skip", or "continue"
            description: Human-readable description

        Returns:
            Self for method chaining
        """
        step = ChainStep(
            tool_name=tool_name,
            parameters=parameters or {},
            param_mappings=param_mappings or {},
            condition=condition,
            on_failure=on_failure,
            description=description or f"Execute {tool_name}",
        )
        self._steps.append(step)
        return self

    def clear(self) -> "ToolChain":
        """Clear all steps from the chain."""
        self._steps.clear()
        self._context.clear()
        return self

    def set_context(self, key: str, value: Any) -> "ToolChain":
        """Set a context value for parameter resolution."""
        self._context[key] = value
        return self

    @classmethod
    def from_builtin(
        cls,
        chain_name: str,
        executor: ToolExecutor,
        params: Optional[Dict[str, Any]] = None
    ) -> "ToolChain":
        """
        Create a chain from a built-in definition.

        Args:
            chain_name: Name of the built-in chain
            executor: ToolExecutor instance
            params: Override parameters for the chain

        Returns:
            Configured ToolChain instance
        """
        if chain_name not in cls.BUILTIN_CHAINS:
            raise ValueError(f"Unknown built-in chain: {chain_name}")

        params = params or {}
        chain = cls(chain_name, executor, description=f"Built-in: {chain_name}")

        for step_def in cls.BUILTIN_CHAINS[chain_name]:
            step_params = dict(step_def.get("params", {}))

            # Override with provided params if matching param_keys
            for key in step_def.get("param_keys", []):
                if key in params:
                    step_params[key] = params[key]

            chain.add_step(
                tool_name=step_def["tool"],
                parameters=step_params,
                on_failure=step_def.get("on_failure", "stop"),
            )

        return chain

    def _resolve_param(self, mapping: str, results: Dict[str, ToolResult]) -> Any:
        """
        Resolve a parameter mapping to its value.

        Mapping format: "step_name.field" or "step_name.data.subfield"
        """
        parts = mapping.split(".")
        if len(parts) < 2:
            # Check context
            return self._context.get(mapping)

        step_name = parts[0]
        if step_name not in results:
            raise ValueError(f"Step '{step_name}' not found in results")

        result = results[step_name]

        # Navigate to the value
        if parts[1] == "data" and len(parts) > 2:
            value = result.data
            for part in parts[2:]:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = getattr(value, part, None)
            return value
        elif parts[1] == "message":
            return result.message
        elif parts[1] == "status":
            return result.status.value
        else:
            # Assume it's a data field
            return result.data.get(parts[1]) if result.data else None

    async def execute(
        self,
        timeout_per_step: Optional[float] = None
    ) -> ChainResult:
        """
        Execute the chain.

        Args:
            timeout_per_step: Optional timeout override per step

        Returns:
            ChainResult with execution details
        """
        start_time = time.time()
        results_by_name: Dict[str, ToolResult] = {}
        all_results: List[ToolResult] = []
        final_data: Dict[str, Any] = {}
        steps_executed = 0

        logger.info(f"Executing chain '{self.name}' with {len(self._steps)} steps")

        for i, step in enumerate(self._steps):
            step_id = f"{step.tool_name}_{i}"

            # Check condition
            if step.condition:
                try:
                    should_run = step.condition(final_data)
                    if not should_run:
                        logger.debug(f"Step {i+1} '{step.tool_name}' skipped (condition false)")
                        continue
                except Exception as e:
                    logger.warning(f"Condition check failed for step {i+1}: {e}")
                    continue

            # Build parameters
            params = dict(step.parameters)
            for param_name, mapping in step.param_mappings.items():
                try:
                    params[param_name] = self._resolve_param(mapping, results_by_name)
                except Exception as e:
                    logger.error(f"Failed to resolve param '{param_name}': {e}")
                    if step.on_failure == "stop":
                        return ChainResult(
                            success=False,
                            steps_executed=steps_executed,
                            steps_total=len(self._steps),
                            results=all_results,
                            final_data=final_data,
                            message=f"Parameter resolution failed at step {i+1}: {e}",
                            execution_time_ms=(time.time() - start_time) * 1000,
                        )
                    elif step.on_failure == "skip":
                        continue

            # Execute the step
            logger.debug(f"Executing step {i+1}: {step.tool_name}")
            result = await self.executor.execute(
                step.tool_name,
                params,
                timeout=timeout_per_step
            )

            all_results.append(result)
            results_by_name[step.tool_name] = result
            steps_executed += 1

            # Aggregate successful data
            if result.success and result.data:
                final_data[step.tool_name] = result.data

            # Handle failure
            if not result.success:
                is_veto = result.status == ToolStatus.VETOED

                if is_veto and self.stop_on_veto:
                    logger.warning(f"Chain stopped at step {i+1}: vetoed")
                    return ChainResult(
                        success=False,
                        steps_executed=steps_executed,
                        steps_total=len(self._steps),
                        results=all_results,
                        final_data=final_data,
                        message=f"Chain vetoed at step {i+1}: {result.message}",
                        execution_time_ms=(time.time() - start_time) * 1000,
                    )

                if step.on_failure == "stop":
                    logger.warning(f"Chain stopped at step {i+1}: {result.error}")
                    return ChainResult(
                        success=False,
                        steps_executed=steps_executed,
                        steps_total=len(self._steps),
                        results=all_results,
                        final_data=final_data,
                        message=f"Chain failed at step {i+1}: {result.message}",
                        execution_time_ms=(time.time() - start_time) * 1000,
                    )
                elif step.on_failure == "skip":
                    logger.info(f"Step {i+1} failed but skipping: {result.error}")
                # "continue" just proceeds to next step

        # Success
        execution_time = (time.time() - start_time) * 1000
        logger.info(
            f"Chain '{self.name}' completed: {steps_executed}/{len(self._steps)} steps "
            f"in {execution_time:.1f}ms"
        )

        return ChainResult(
            success=True,
            steps_executed=steps_executed,
            steps_total=len(self._steps),
            results=all_results,
            final_data=final_data,
            message=f"Chain completed successfully ({steps_executed} steps)",
            execution_time_ms=execution_time,
        )

    def __repr__(self) -> str:
        return f"ToolChain(name='{self.name}', steps={len(self._steps)})"
