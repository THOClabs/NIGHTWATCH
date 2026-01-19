"""
Mock GPIO module for NIGHTWATCH testing.

Simulates Raspberry Pi GPIO pins for testing roof controller
and other hardware-interfacing components without actual hardware.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Callable, Optional
import logging

logger = logging.getLogger("NIGHTWATCH.MockGPIO")


class GPIOState(Enum):
    """GPIO pin states."""
    LOW = 0
    HIGH = 1


class GPIODirection(Enum):
    """GPIO pin direction."""
    INPUT = "in"
    OUTPUT = "out"


class GPIOPull(Enum):
    """GPIO pull resistor configuration."""
    NONE = "none"
    UP = "up"
    DOWN = "down"


@dataclass
class GPIOPin:
    """Represents a single GPIO pin."""
    number: int
    direction: GPIODirection = GPIODirection.INPUT
    state: GPIOState = GPIOState.LOW
    pull: GPIOPull = GPIOPull.NONE
    callbacks: List[Callable] = field(default_factory=list)

    def read(self) -> int:
        """Read pin state."""
        return self.state.value

    def write(self, value: int):
        """Write pin state (for output pins)."""
        if self.direction != GPIODirection.OUTPUT:
            raise RuntimeError(f"Pin {self.number} is not configured as output")
        old_state = self.state
        self.state = GPIOState(value)
        if old_state != self.state:
            self._trigger_callbacks()

    def set_high(self):
        """Set pin high."""
        self.write(1)

    def set_low(self):
        """Set pin low."""
        self.write(0)

    def toggle(self):
        """Toggle pin state."""
        self.write(1 - self.state.value)

    def add_callback(self, callback: Callable):
        """Add state change callback."""
        self.callbacks.append(callback)

    def _trigger_callbacks(self):
        """Trigger all registered callbacks."""
        for callback in self.callbacks:
            try:
                callback(self.number, self.state)
            except Exception as e:
                logger.error(f"GPIO callback error: {e}")


class MockGPIO:
    """
    Mock GPIO controller for testing.

    Simulates a GPIO interface compatible with RPi.GPIO style usage.

    Usage:
        gpio = MockGPIO()

        # Setup pins
        gpio.setup(17, gpio.OUT)
        gpio.setup(27, gpio.IN, pull_up_down=gpio.PUD_UP)

        # Write output
        gpio.output(17, gpio.HIGH)

        # Read input
        value = gpio.input(27)

        # Add event detection
        gpio.add_event_detect(27, gpio.FALLING, callback=my_callback)

        # Simulate external input (for testing)
        gpio.simulate_input(27, gpio.LOW)
    """

    # Direction constants
    IN = GPIODirection.INPUT
    OUT = GPIODirection.OUTPUT

    # State constants
    LOW = 0
    HIGH = 1

    # Pull constants
    PUD_OFF = GPIOPull.NONE
    PUD_UP = GPIOPull.UP
    PUD_DOWN = GPIOPull.DOWN

    # Edge constants
    RISING = "rising"
    FALLING = "falling"
    BOTH = "both"

    # Mode constants
    BCM = "bcm"
    BOARD = "board"

    def __init__(self):
        """Initialize mock GPIO."""
        self._pins: Dict[int, GPIOPin] = {}
        self._mode: Optional[str] = None
        self._warnings = True
        self._event_callbacks: Dict[int, List[tuple]] = {}  # pin -> [(edge, callback), ...]

    def setmode(self, mode: str):
        """Set pin numbering mode."""
        self._mode = mode
        logger.debug(f"GPIO mode set to {mode}")

    def setwarnings(self, enabled: bool):
        """Enable/disable warnings."""
        self._warnings = enabled

    def setup(self, pin: int, direction: GPIODirection,
              pull_up_down: GPIOPull = GPIOPull.NONE,
              initial: Optional[int] = None):
        """
        Setup a GPIO pin.

        Args:
            pin: Pin number
            direction: Input or output
            pull_up_down: Pull resistor configuration
            initial: Initial state for outputs
        """
        if pin in self._pins and self._warnings:
            logger.warning(f"Pin {pin} already setup, reconfiguring")

        state = GPIOState.LOW
        if initial is not None:
            state = GPIOState(initial)
        elif pull_up_down == GPIOPull.UP:
            state = GPIOState.HIGH

        self._pins[pin] = GPIOPin(
            number=pin,
            direction=direction,
            state=state,
            pull=pull_up_down
        )
        logger.debug(f"Pin {pin} setup as {direction.value}")

    def output(self, pin: int, value: int):
        """
        Set output pin state.

        Args:
            pin: Pin number
            value: HIGH or LOW
        """
        if pin not in self._pins:
            raise RuntimeError(f"Pin {pin} not setup")
        self._pins[pin].write(value)
        logger.debug(f"Pin {pin} output: {value}")

    def input(self, pin: int) -> int:
        """
        Read input pin state.

        Args:
            pin: Pin number

        Returns:
            Pin state (0 or 1)
        """
        if pin not in self._pins:
            raise RuntimeError(f"Pin {pin} not setup")
        return self._pins[pin].read()

    def add_event_detect(self, pin: int, edge: str,
                        callback: Optional[Callable] = None,
                        bouncetime: int = 0):
        """
        Add edge detection callback.

        Args:
            pin: Pin number
            edge: RISING, FALLING, or BOTH
            callback: Function to call on edge
            bouncetime: Debounce time in ms (ignored in mock)
        """
        if pin not in self._pins:
            raise RuntimeError(f"Pin {pin} not setup")

        if pin not in self._event_callbacks:
            self._event_callbacks[pin] = []

        if callback:
            self._event_callbacks[pin].append((edge, callback))

        logger.debug(f"Event detect added: pin {pin}, edge {edge}")

    def remove_event_detect(self, pin: int):
        """Remove edge detection from pin."""
        if pin in self._event_callbacks:
            del self._event_callbacks[pin]

    def event_detected(self, pin: int) -> bool:
        """Check if event was detected on pin."""
        # In mock, always return False unless explicitly triggered
        return False

    def cleanup(self, pin: Optional[int] = None):
        """
        Cleanup GPIO.

        Args:
            pin: Specific pin to cleanup, or None for all
        """
        if pin is not None:
            if pin in self._pins:
                del self._pins[pin]
            if pin in self._event_callbacks:
                del self._event_callbacks[pin]
        else:
            self._pins.clear()
            self._event_callbacks.clear()
            self._mode = None
        logger.debug(f"GPIO cleanup: {pin if pin else 'all'}")

    # =========================================================================
    # Test simulation methods
    # =========================================================================

    def simulate_input(self, pin: int, value: int):
        """
        Simulate an external input change (for testing).

        This triggers any registered event callbacks.

        Args:
            pin: Pin number
            value: New state value
        """
        if pin not in self._pins:
            raise RuntimeError(f"Pin {pin} not setup")

        old_state = self._pins[pin].state
        new_state = GPIOState(value)
        self._pins[pin].state = new_state

        # Trigger edge callbacks
        if pin in self._event_callbacks:
            edge_type = None
            if old_state == GPIOState.LOW and new_state == GPIOState.HIGH:
                edge_type = self.RISING
            elif old_state == GPIOState.HIGH and new_state == GPIOState.LOW:
                edge_type = self.FALLING

            if edge_type:
                for edge, callback in self._event_callbacks[pin]:
                    if edge == self.BOTH or edge == edge_type:
                        try:
                            callback(pin)
                        except Exception as e:
                            logger.error(f"Event callback error: {e}")

        logger.debug(f"Simulated input: pin {pin} = {value}")

    def get_pin_state(self, pin: int) -> Optional[GPIOState]:
        """Get pin state for inspection."""
        if pin in self._pins:
            return self._pins[pin].state
        return None

    def get_all_pin_states(self) -> Dict[int, int]:
        """Get all pin states for inspection."""
        return {pin: p.state.value for pin, p in self._pins.items()}

    def reset(self):
        """Reset all pins to initial state."""
        for pin in self._pins.values():
            if pin.pull == GPIOPull.UP:
                pin.state = GPIOState.HIGH
            else:
                pin.state = GPIOState.LOW


# Singleton for tests that need a shared GPIO instance
_mock_gpio_instance: Optional[MockGPIO] = None


def get_mock_gpio() -> MockGPIO:
    """Get or create singleton MockGPIO instance."""
    global _mock_gpio_instance
    if _mock_gpio_instance is None:
        _mock_gpio_instance = MockGPIO()
    return _mock_gpio_instance


def reset_mock_gpio():
    """Reset the singleton MockGPIO instance."""
    global _mock_gpio_instance
    if _mock_gpio_instance is not None:
        _mock_gpio_instance.cleanup()
    _mock_gpio_instance = MockGPIO()
