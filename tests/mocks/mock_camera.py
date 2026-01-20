"""
NIGHTWATCH Mock Camera for Testing

Step 99: Create mock camera for testing

Provides a simulated ZWO ASI camera for unit testing without actual hardware.
"""

import asyncio
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Callable, Tuple, Dict, Any


class MockCameraState(Enum):
    """Mock camera states."""
    DISCONNECTED = "disconnected"
    IDLE = "idle"
    CAPTURING = "capturing"
    STREAMING = "streaming"
    ERROR = "error"


@dataclass
class MockCameraInfo:
    """Mock camera hardware information."""
    name: str = "ZWO ASI290MC (Mock)"
    camera_id: int = 0
    max_width: int = 1936
    max_height: int = 1096
    pixel_size_um: float = 2.9
    is_color: bool = True
    has_cooler: bool = False
    bit_depth: int = 12
    usb_host: str = "USB3 (Mock)"


@dataclass
class MockCaptureResult:
    """Result of a mock capture operation."""
    success: bool
    frame_count: int = 0
    duration_sec: float = 0.0
    output_path: Optional[Path] = None
    error: Optional[str] = None


class MockCamera:
    """
    Mock ZWO ASI camera for testing NIGHTWATCH imaging functionality.

    Simulates camera behavior including:
    - Connection/disconnection
    - Setting gain, exposure, binning
    - Temperature monitoring (simulated)
    - Frame capture with synthetic data
    - Error injection for testing error handling

    Usage:
        camera = MockCamera()
        await camera.connect()

        # Configure
        camera.set_gain(250)
        camera.set_exposure(10.0)

        # Capture
        result = await camera.capture_frames(100)

        # Inject errors for testing
        camera.inject_error("capture_fail")
    """

    # Presets matching real ASICamera presets
    PRESETS = {
        "mars": {"gain": 280, "exposure_ms": 8.0, "usb_bandwidth": 90},
        "jupiter": {"gain": 250, "exposure_ms": 12.0, "usb_bandwidth": 85},
        "saturn": {"gain": 300, "exposure_ms": 15.0, "usb_bandwidth": 80},
        "moon": {"gain": 100, "exposure_ms": 5.0, "usb_bandwidth": 90},
        "deep_sky": {"gain": 350, "exposure_ms": 30000.0, "usb_bandwidth": 40},
    }

    def __init__(
        self,
        camera_info: Optional[MockCameraInfo] = None,
        initial_temperature: float = 20.0,
    ):
        """
        Initialize mock camera.

        Args:
            camera_info: Camera hardware info (uses defaults if None)
            initial_temperature: Initial sensor temperature in Celsius
        """
        self._info = camera_info or MockCameraInfo()
        self._state = MockCameraState.DISCONNECTED
        self._connected = False

        # Settings
        self._gain = 250
        self._exposure_ms = 10.0
        self._binning = 1
        self._roi: Optional[Tuple[int, int, int, int]] = None
        self._usb_bandwidth = 80
        self._high_speed_mode = True

        # Cooling simulation
        self._temperature = initial_temperature
        self._target_temp: Optional[float] = None
        self._cooler_on = False
        self._cooler_power = 0

        # Capture tracking
        self._capturing = False
        self._capture_abort_requested = False
        self._frame_count = 0
        self._capture_start_time: Optional[datetime] = None
        self._current_capture_total = 0

        # Statistics
        self._total_captures = 0
        self._total_frames = 0

        # Error injection
        self._inject_errors: Dict[str, bool] = {}

        # Callbacks
        self._frame_callbacks: List[Callable] = []
        self._status_callbacks: List[Callable] = []

    @property
    def initialized(self) -> bool:
        """Check if camera is initialized."""
        return self._connected

    @property
    def connected(self) -> bool:
        """Check if camera is connected."""
        return self._connected

    @property
    def capturing(self) -> bool:
        """Check if capture is in progress."""
        return self._capturing

    @property
    def info(self) -> Optional[MockCameraInfo]:
        """Get camera info."""
        return self._info if self._connected else None

    @property
    def state(self) -> MockCameraState:
        """Get current camera state."""
        return self._state

    # =========================================================================
    # CONNECTION
    # =========================================================================

    async def connect(self, camera_index: int = 0) -> bool:
        """
        Connect to mock camera.

        Args:
            camera_index: Camera index (ignored in mock)

        Returns:
            True if connected successfully
        """
        if self._inject_errors.get("connect_fail"):
            return False

        await asyncio.sleep(0.1)  # Simulate connection delay
        self._connected = True
        self._state = MockCameraState.IDLE
        return True

    async def disconnect(self) -> None:
        """Disconnect from mock camera."""
        if self._capturing:
            await self.abort_capture()

        self._connected = False
        self._state = MockCameraState.DISCONNECTED

    # =========================================================================
    # SETTINGS
    # =========================================================================

    def set_gain(self, gain: int) -> bool:
        """
        Set camera gain.

        Args:
            gain: Gain value (0-500 typical)

        Returns:
            True if set successfully
        """
        if not self._connected:
            return False

        self._gain = max(0, min(500, gain))
        return True

    def get_gain(self) -> int:
        """Get current gain."""
        return self._gain

    def get_gain_range(self) -> Tuple[int, int]:
        """Get gain range (min, max)."""
        return (0, 500)

    def set_exposure(self, exposure_ms: float) -> bool:
        """
        Set exposure time.

        Args:
            exposure_ms: Exposure in milliseconds

        Returns:
            True if set successfully
        """
        if not self._connected:
            return False

        self._exposure_ms = max(0.001, min(3600000.0, exposure_ms))
        return True

    def get_exposure(self) -> float:
        """Get current exposure in milliseconds."""
        return self._exposure_ms

    def get_exposure_range(self) -> Tuple[float, float]:
        """Get exposure range in ms (min, max)."""
        return (0.001, 3600000.0)

    def set_binning(self, binning: int) -> bool:
        """
        Set binning mode.

        Args:
            binning: Binning factor (1, 2, or 4)

        Returns:
            True if set successfully
        """
        if not self._connected:
            return False

        if binning in [1, 2, 4]:
            self._binning = binning
            return True
        return False

    def get_binning(self) -> int:
        """Get current binning."""
        return self._binning

    def get_supported_binning(self) -> List[int]:
        """Get supported binning modes."""
        return [1, 2, 4]

    def set_roi(self, x: int, y: int, width: int, height: int) -> bool:
        """
        Set region of interest.

        Args:
            x: Left offset
            y: Top offset
            width: ROI width
            height: ROI height

        Returns:
            True if set successfully
        """
        if not self._connected:
            return False

        # Validate against camera dimensions
        if x + width > self._info.max_width or y + height > self._info.max_height:
            return False

        self._roi = (x, y, width, height)
        return True

    def get_roi(self) -> Optional[Tuple[int, int, int, int]]:
        """Get current ROI (x, y, width, height) or None for full frame."""
        return self._roi

    def clear_roi(self) -> None:
        """Clear ROI (use full frame)."""
        self._roi = None

    def get_current_settings(self) -> Dict[str, Any]:
        """Get all current settings."""
        return {
            "gain": self._gain,
            "exposure_ms": self._exposure_ms,
            "binning": self._binning,
            "roi": self._roi,
            "usb_bandwidth": self._usb_bandwidth,
            "high_speed_mode": self._high_speed_mode,
        }

    def get_preset(self, target: str) -> Dict[str, Any]:
        """
        Get preset settings for a target.

        Args:
            target: Target name (mars, jupiter, saturn, moon, deep_sky)

        Returns:
            Dict with preset settings
        """
        return self.PRESETS.get(target.lower(), self.PRESETS["jupiter"])

    def apply_preset(self, target: str) -> bool:
        """
        Apply preset settings for a target.

        Args:
            target: Target name

        Returns:
            True if applied successfully
        """
        preset = self.get_preset(target)
        self._gain = preset["gain"]
        self._exposure_ms = preset["exposure_ms"]
        self._usb_bandwidth = preset["usb_bandwidth"]
        return True

    # =========================================================================
    # TEMPERATURE
    # =========================================================================

    def get_temperature(self) -> Optional[float]:
        """Get sensor temperature in Celsius."""
        if not self._connected:
            return None
        return self._temperature

    def get_temperature_status(self) -> Dict[str, Any]:
        """Get full temperature status."""
        if not self._connected:
            return {
                "sensor_temp_c": None,
                "has_cooler": False,
                "cooler_on": False,
                "cooler_power": 0,
                "target_temp_c": None,
            }

        return {
            "sensor_temp_c": self._temperature,
            "has_cooler": self._info.has_cooler,
            "cooler_on": self._cooler_on,
            "cooler_power": self._cooler_power,
            "target_temp_c": self._target_temp,
        }

    def set_cooler(self, on: bool, target_temp_c: Optional[float] = None) -> bool:
        """
        Control cooler.

        Args:
            on: Enable/disable cooler
            target_temp_c: Target temperature

        Returns:
            True if set successfully
        """
        if not self._connected or not self._info.has_cooler:
            return False

        self._cooler_on = on
        if target_temp_c is not None:
            self._target_temp = target_temp_c

        return True

    def get_cooler_power(self) -> Optional[int]:
        """Get cooler power percentage."""
        if not self._connected:
            return None
        return self._cooler_power

    def simulate_temperature_change(self, delta: float) -> None:
        """Simulate temperature change for testing."""
        self._temperature += delta

    # =========================================================================
    # CAPTURE
    # =========================================================================

    async def capture_single_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame.

        Returns:
            Numpy array with image data, or None on failure
        """
        if not self._connected:
            return None

        if self._inject_errors.get("capture_fail"):
            return None

        await asyncio.sleep(self._exposure_ms / 1000.0)

        # Generate synthetic frame
        width = self._roi[2] if self._roi else self._info.max_width // self._binning
        height = self._roi[3] if self._roi else self._info.max_height // self._binning

        # Create random frame with some structure (simulated stars)
        frame = np.random.randint(0, 50, (height, width), dtype=np.uint16)

        # Add some "stars"
        num_stars = 20
        for _ in range(num_stars):
            x = np.random.randint(10, width - 10)
            y = np.random.randint(10, height - 10)
            brightness = np.random.randint(1000, 4000)
            frame[y-2:y+3, x-2:x+3] += brightness

        self._total_frames += 1
        return frame

    async def capture_frames(
        self,
        count: int,
        output_path: Optional[Path] = None,
    ) -> MockCaptureResult:
        """
        Capture multiple frames.

        Args:
            count: Number of frames to capture
            output_path: Optional path to save frames

        Returns:
            MockCaptureResult with capture statistics
        """
        if not self._connected:
            return MockCaptureResult(success=False, error="Camera not connected")

        if self._capturing:
            return MockCaptureResult(success=False, error="Capture already in progress")

        if self._inject_errors.get("capture_timeout"):
            await asyncio.sleep(60)  # Simulate timeout
            return MockCaptureResult(success=False, error="Capture timeout")

        self._capturing = True
        self._state = MockCameraState.CAPTURING
        self._capture_abort_requested = False
        self._capture_start_time = datetime.now()
        self._current_capture_total = count
        self._frame_count = 0

        try:
            for i in range(count):
                if self._capture_abort_requested:
                    return MockCaptureResult(
                        success=False,
                        frame_count=self._frame_count,
                        error="Capture aborted",
                    )

                frame = await self.capture_single_frame()
                if frame is None:
                    return MockCaptureResult(
                        success=False,
                        frame_count=self._frame_count,
                        error="Frame capture failed",
                    )

                self._frame_count += 1

                # Notify callbacks
                for callback in self._frame_callbacks:
                    try:
                        callback(i + 1, count, frame)
                    except Exception:
                        pass

            duration = (datetime.now() - self._capture_start_time).total_seconds()
            self._total_captures += 1

            return MockCaptureResult(
                success=True,
                frame_count=self._frame_count,
                duration_sec=duration,
                output_path=output_path,
            )

        finally:
            self._capturing = False
            self._state = MockCameraState.IDLE

    async def abort_capture(self) -> bool:
        """
        Abort capture in progress.

        Returns:
            True if abort requested successfully
        """
        if not self._capturing:
            return False

        self._capture_abort_requested = True
        return True

    def is_capture_in_progress(self) -> bool:
        """Check if capture is in progress."""
        return self._capturing

    def get_capture_progress(self) -> Optional[Dict[str, Any]]:
        """Get capture progress information."""
        if not self._capturing:
            return None

        return {
            "frames_captured": self._frame_count,
            "total_frames": self._current_capture_total,
            "percent_complete": (self._frame_count / self._current_capture_total * 100)
                if self._current_capture_total > 0 else 0,
            "elapsed_sec": (datetime.now() - self._capture_start_time).total_seconds()
                if self._capture_start_time else 0,
        }

    # =========================================================================
    # CALLBACKS
    # =========================================================================

    def register_frame_callback(self, callback: Callable) -> None:
        """Register callback for frame events."""
        self._frame_callbacks.append(callback)

    def register_status_callback(self, callback: Callable) -> None:
        """Register callback for status events."""
        self._status_callbacks.append(callback)

    # =========================================================================
    # ERROR INJECTION
    # =========================================================================

    def inject_error(self, error_type: str) -> None:
        """
        Inject error for testing.

        Args:
            error_type: Type of error
                - "connect_fail": Connection fails
                - "capture_fail": Single frame capture fails
                - "capture_timeout": Capture times out
        """
        self._inject_errors[error_type] = True

    def clear_errors(self) -> None:
        """Clear all injected errors."""
        self._inject_errors.clear()

    def clear_error(self, error_type: str) -> None:
        """Clear specific error."""
        self._inject_errors.pop(error_type, None)

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get mock camera statistics."""
        return {
            "total_captures": self._total_captures,
            "total_frames": self._total_frames,
            "connected": self._connected,
            "state": self._state.value,
            "current_settings": self.get_current_settings(),
        }

    def reset(self) -> None:
        """Reset mock camera to initial state."""
        self._connected = False
        self._state = MockCameraState.DISCONNECTED
        self._capturing = False
        self._frame_count = 0
        self._total_captures = 0
        self._total_frames = 0
        self._inject_errors.clear()
        self._gain = 250
        self._exposure_ms = 10.0
        self._binning = 1
        self._roi = None
        self._temperature = 20.0


# =============================================================================
# Factory function
# =============================================================================

def create_mock_camera(
    preset: str = "default",
    **kwargs,
) -> MockCamera:
    """
    Create mock camera with preset configuration.

    Args:
        preset: Configuration preset
            - "default": Standard ASI290MC
            - "cooled": Camera with cooler (ASI294MC)
            - "mono": Monochrome camera (ASI290MM)
        **kwargs: Override specific parameters

    Returns:
        Configured MockCamera instance
    """
    presets = {
        "default": MockCameraInfo(
            name="ZWO ASI290MC (Mock)",
            camera_id=0,
            max_width=1936,
            max_height=1096,
            pixel_size_um=2.9,
            is_color=True,
            has_cooler=False,
            bit_depth=12,
            usb_host="USB3 (Mock)",
        ),
        "cooled": MockCameraInfo(
            name="ZWO ASI294MC Pro (Mock)",
            camera_id=1,
            max_width=4144,
            max_height=2822,
            pixel_size_um=4.63,
            is_color=True,
            has_cooler=True,
            bit_depth=14,
            usb_host="USB3 (Mock)",
        ),
        "mono": MockCameraInfo(
            name="ZWO ASI290MM (Mock)",
            camera_id=2,
            max_width=1936,
            max_height=1096,
            pixel_size_um=2.9,
            is_color=False,
            has_cooler=False,
            bit_depth=12,
            usb_host="USB3 (Mock)",
        ),
    }

    camera_info = presets.get(preset, presets["default"])
    return MockCamera(camera_info=camera_info, **kwargs)
