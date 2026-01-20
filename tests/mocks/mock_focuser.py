"""
NIGHTWATCH Mock Focuser for Testing

Step 190: Create mock focuser for testing

Provides a simulated focuser for unit testing without actual hardware.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Callable
from enum import Enum


class MockFocuserState(Enum):
    """Mock focuser states."""
    IDLE = "idle"
    MOVING = "moving"
    AUTOFOCUS = "autofocus"
    ERROR = "error"


@dataclass
class MockFocusMetric:
    """Mock focus quality measurement."""
    position: int
    hfd: float
    temperature_c: float


class MockFocuser:
    """
    Mock focuser for testing NIGHTWATCH focus functionality.

    Simulates a ZWO EAF or similar electronic focuser with:
    - Position tracking with backlash simulation
    - Temperature simulation with drift
    - HFD simulation based on position (V-curve)
    - Move timing simulation
    - Error injection for testing error handling

    Usage:
        focuser = MockFocuser()
        await focuser.connect()

        # Move to position
        await focuser.move_to(25000)

        # Simulate auto-focus
        await focuser.auto_focus()

        # Inject errors for testing
        focuser.inject_error("move_timeout")
    """

    def __init__(
        self,
        optimal_position: int = 25000,
        initial_position: int = 25000,
        max_position: int = 50000,
        step_time_ms: float = 10.0,
        initial_temperature: float = 20.0,
    ):
        """
        Initialize mock focuser.

        Args:
            optimal_position: Focus position with best HFD
            initial_position: Starting position
            max_position: Maximum focuser position
            step_time_ms: Milliseconds per step movement
            initial_temperature: Initial temperature in Celsius
        """
        self._optimal_position = optimal_position
        self._position = initial_position
        self._max_position = max_position
        self._step_time_ms = step_time_ms
        self._temperature = initial_temperature

        self._connected = False
        self._state = MockFocuserState.IDLE
        self._move_count = 0
        self._autofocus_count = 0

        # For history tracking
        self._position_history: List[tuple] = []  # (timestamp, position, reason)

        # Error injection
        self._inject_errors: dict = {}

        # Callbacks for monitoring
        self._callbacks: List[Callable] = []

        # Backlash simulation
        self._backlash_steps = 50
        self._last_direction = 0  # 1 = outward, -1 = inward

    @property
    def connected(self) -> bool:
        """Check if focuser is connected."""
        return self._connected

    @property
    def position(self) -> int:
        """Current focuser position."""
        return self._position

    @property
    def state(self) -> MockFocuserState:
        """Current focuser state."""
        return self._state

    @property
    def temperature(self) -> float:
        """Current temperature in Celsius."""
        return self._temperature

    @property
    def move_count(self) -> int:
        """Number of move operations performed."""
        return self._move_count

    @property
    def autofocus_count(self) -> int:
        """Number of auto-focus operations performed."""
        return self._autofocus_count

    async def connect(self) -> bool:
        """
        Connect to mock focuser.

        Returns:
            True if connected successfully
        """
        if self._inject_errors.get("connect_fail"):
            return False

        await asyncio.sleep(0.1)  # Simulate connection delay
        self._connected = True
        self._state = MockFocuserState.IDLE
        return True

    async def disconnect(self) -> None:
        """Disconnect from mock focuser."""
        self._connected = False
        self._state = MockFocuserState.IDLE

    async def move_to(self, position: int, reason: str = "manual") -> bool:
        """
        Move to absolute position.

        Args:
            position: Target position
            reason: Reason for move (for logging)

        Returns:
            True if move successful
        """
        if not self._connected:
            raise RuntimeError("Focuser not connected")

        if self._state == MockFocuserState.MOVING:
            raise RuntimeError("Focuser already moving")

        # Check for injected errors
        if self._inject_errors.get("move_timeout"):
            await asyncio.sleep(10.0)  # Simulate timeout
            return False

        if self._inject_errors.get("move_fail"):
            return False

        # Clamp position
        position = max(0, min(position, self._max_position))

        # Calculate move
        start_position = self._position
        direction = 1 if position > start_position else -1

        # Simulate backlash if changing direction
        backlash_error = 0
        if direction != self._last_direction and self._last_direction != 0:
            backlash_error = self._backlash_steps if direction > 0 else -self._backlash_steps

        self._state = MockFocuserState.MOVING
        self._last_direction = direction

        # Simulate movement time
        steps = abs(position - start_position)
        move_time = (steps * self._step_time_ms) / 1000.0
        await asyncio.sleep(min(move_time, 2.0))  # Cap at 2 seconds for testing

        # Apply position (with optional backlash for realism)
        self._position = position
        self._state = MockFocuserState.IDLE
        self._move_count += 1

        # Record in history
        self._position_history.append((datetime.now(), position, reason))

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback("move_complete", position)
            except Exception:
                pass

        return True

    async def move_relative(self, steps: int, reason: str = "manual") -> bool:
        """
        Move relative to current position.

        Args:
            steps: Steps to move (positive = outward)
            reason: Reason for move

        Returns:
            True if successful
        """
        return await self.move_to(self._position + steps, reason)

    async def halt(self) -> None:
        """Halt focuser movement."""
        self._state = MockFocuserState.IDLE

    def get_hfd(self) -> float:
        """
        Get simulated HFD at current position.

        Returns a V-curve based on distance from optimal position.

        Returns:
            Simulated HFD value
        """
        # V-curve simulation: HFD = base + k * distance^2
        distance = abs(self._position - self._optimal_position)
        base_hfd = 2.0
        k = 1e-7

        hfd = base_hfd + k * (distance ** 2)

        # Add small random noise
        import random
        hfd += random.gauss(0, 0.05)

        return max(1.5, hfd)  # Minimum HFD of 1.5

    async def auto_focus(self) -> dict:
        """
        Run simulated auto-focus routine.

        Returns:
            Dict with focus results
        """
        if not self._connected:
            raise RuntimeError("Focuser not connected")

        if self._inject_errors.get("autofocus_fail"):
            return {"success": False, "error": "Auto-focus failed"}

        self._state = MockFocuserState.AUTOFOCUS

        # Simulate auto-focus by moving to optimal position
        initial_position = self._position

        # Simulate V-curve sampling
        samples = []
        step_size = 200
        start_pos = self._optimal_position - (4 * step_size)

        for i in range(9):
            pos = start_pos + (i * step_size)
            await self.move_to(pos, reason="auto_focus_sample")
            hfd = self.get_hfd()
            samples.append(MockFocusMetric(position=pos, hfd=hfd, temperature_c=self._temperature))
            await asyncio.sleep(0.05)  # Simulate exposure time

        # Find best position (minimum HFD)
        best_sample = min(samples, key=lambda s: s.hfd)
        await self.move_to(best_sample.position, reason="auto_focus_result")

        self._state = MockFocuserState.IDLE
        self._autofocus_count += 1

        return {
            "success": True,
            "initial_position": initial_position,
            "final_position": best_sample.position,
            "best_hfd": best_sample.hfd,
            "samples": len(samples),
        }

    def set_temperature(self, temperature: float) -> None:
        """
        Set simulated temperature.

        Args:
            temperature: Temperature in Celsius
        """
        self._temperature = temperature

    def simulate_temperature_drift(self, delta: float) -> None:
        """
        Simulate temperature change.

        Args:
            delta: Temperature change in Celsius
        """
        self._temperature += delta

    def set_optimal_position(self, position: int) -> None:
        """
        Set optimal focus position (for testing).

        Args:
            position: New optimal position
        """
        self._optimal_position = position

    # =========================================================================
    # ERROR INJECTION
    # =========================================================================

    def inject_error(self, error_type: str) -> None:
        """
        Inject error for testing error handling.

        Args:
            error_type: Type of error to inject
                - "connect_fail": Connection fails
                - "move_timeout": Move times out
                - "move_fail": Move fails immediately
                - "autofocus_fail": Auto-focus fails
        """
        self._inject_errors[error_type] = True

    def clear_errors(self) -> None:
        """Clear all injected errors."""
        self._inject_errors.clear()

    def clear_error(self, error_type: str) -> None:
        """
        Clear specific injected error.

        Args:
            error_type: Type of error to clear
        """
        self._inject_errors.pop(error_type, None)

    # =========================================================================
    # HISTORY AND STATS
    # =========================================================================

    def get_position_history(self) -> List[tuple]:
        """
        Get position history.

        Returns:
            List of (timestamp, position, reason) tuples
        """
        return self._position_history.copy()

    def clear_history(self) -> None:
        """Clear position history."""
        self._position_history.clear()

    def get_stats(self) -> dict:
        """
        Get mock focuser statistics.

        Returns:
            Dict with usage statistics
        """
        return {
            "move_count": self._move_count,
            "autofocus_count": self._autofocus_count,
            "position_history_count": len(self._position_history),
            "current_position": self._position,
            "current_temperature": self._temperature,
            "optimal_position": self._optimal_position,
            "connected": self._connected,
        }

    def reset(self) -> None:
        """Reset mock focuser to initial state."""
        self._position = 25000
        self._temperature = 20.0
        self._connected = False
        self._state = MockFocuserState.IDLE
        self._move_count = 0
        self._autofocus_count = 0
        self._position_history.clear()
        self._inject_errors.clear()
        self._last_direction = 0

    # =========================================================================
    # CALLBACKS
    # =========================================================================

    def register_callback(self, callback: Callable) -> None:
        """
        Register callback for focuser events.

        Args:
            callback: Function called with (event_type, data)
        """
        self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable) -> None:
        """
        Unregister callback.

        Args:
            callback: Callback to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)


# =============================================================================
# Factory function for convenience
# =============================================================================

def create_mock_focuser(
    preset: str = "default",
    **kwargs,
) -> MockFocuser:
    """
    Create mock focuser with preset configuration.

    Args:
        preset: Configuration preset name
            - "default": Standard settings
            - "out_of_focus": Starts far from optimal
            - "slow": Slow movement for timeout testing
            - "noisy": Higher HFD noise
        **kwargs: Override specific parameters

    Returns:
        Configured MockFocuser instance
    """
    presets = {
        "default": {
            "optimal_position": 25000,
            "initial_position": 25000,
            "max_position": 50000,
            "step_time_ms": 10.0,
            "initial_temperature": 20.0,
        },
        "out_of_focus": {
            "optimal_position": 25000,
            "initial_position": 30000,
            "max_position": 50000,
            "step_time_ms": 10.0,
            "initial_temperature": 20.0,
        },
        "slow": {
            "optimal_position": 25000,
            "initial_position": 25000,
            "max_position": 50000,
            "step_time_ms": 100.0,
            "initial_temperature": 20.0,
        },
    }

    config = presets.get(preset, presets["default"]).copy()
    config.update(kwargs)

    return MockFocuser(**config)
