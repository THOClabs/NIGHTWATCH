"""
Mock Camera Controller for Testing.

Simulates camera behavior for unit and integration testing.
Provides configurable exposure simulation and image generation.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, List, Any

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None  # type: ignore

logger = logging.getLogger("NIGHTWATCH.fixtures.MockCamera")


class MockCameraState(Enum):
    """Camera operational states."""
    DISCONNECTED = "disconnected"
    IDLE = "idle"
    EXPOSING = "exposing"
    DOWNLOADING = "downloading"
    ERROR = "error"


class BinningMode(Enum):
    """Camera binning modes."""
    BIN_1X1 = "1x1"
    BIN_2X2 = "2x2"
    BIN_3X3 = "3x3"
    BIN_4X4 = "4x4"


@dataclass
class NoiseConfig:
    """
    Camera noise simulation configuration (Step 531).

    Models realistic CCD/CMOS noise sources:
    - Read noise: Gaussian noise from readout electronics
    - Dark current: Thermal noise increasing with temperature/exposure
    - Shot noise: Poisson noise from photon statistics
    - Hot pixels: Random bright defect pixels
    - Bias level: Constant offset added to all pixels
    """
    enable_read_noise: bool = True
    read_noise_e: float = 2.5  # electrons RMS (typical for cooled CMOS)

    enable_dark_current: bool = True
    dark_current_e_per_sec: float = 0.002  # electrons/pixel/sec at -10°C
    dark_current_doubling_temp_c: float = 6.0  # doubles every 6°C

    enable_shot_noise: bool = True  # Poisson noise on signal

    enable_hot_pixels: bool = True
    hot_pixel_fraction: float = 0.0001  # 0.01% of pixels are hot
    hot_pixel_rate_e_per_sec: float = 50.0  # electrons/sec for hot pixels

    enable_bias: bool = True
    bias_level_adu: int = 100  # constant bias offset

    gain_e_per_adu: float = 0.25  # electrons per ADU (conversion gain)


@dataclass
class CameraInfo:
    """Camera hardware information."""
    name: str = "MockCamera ASI294MC Pro"
    sensor_width_px: int = 4144
    sensor_height_px: int = 2822
    pixel_size_um: float = 4.63
    bit_depth: int = 14
    has_cooler: bool = True
    has_shutter: bool = False
    max_gain: int = 570
    min_exposure_ms: float = 0.032
    max_exposure_sec: float = 3600.0


@dataclass
class CameraSettings:
    """Current camera settings."""
    gain: int = 100
    offset: int = 10
    exposure_sec: float = 1.0
    binning: BinningMode = BinningMode.BIN_1X1
    roi_x: int = 0
    roi_y: int = 0
    roi_width: int = 4144
    roi_height: int = 2822
    cooler_on: bool = False
    cooler_setpoint_c: float = -10.0


@dataclass
class CameraStatus:
    """Current camera status."""
    state: MockCameraState = MockCameraState.DISCONNECTED
    temperature_c: float = 20.0
    cooler_power_percent: float = 0.0
    exposure_progress: float = 0.0
    last_exposure_time: Optional[datetime] = None


class MockCamera:
    """
    Mock camera controller for testing.

    Simulates a ZWO ASI camera with:
    - Connection/disconnection
    - Exposure control
    - Gain and offset settings
    - Binning modes
    - Cooling simulation
    - Synthetic image generation

    Example:
        camera = MockCamera()
        await camera.connect()
        camera.set_exposure(5.0)
        camera.set_gain(200)
        image = await camera.capture()
    """

    def __init__(
        self,
        simulate_delays: bool = True,
        generate_images: bool = True,
        noise_config: Optional[NoiseConfig] = None,
    ):
        """
        Initialize mock camera.

        Args:
            simulate_delays: Whether to simulate realistic delays
            generate_images: Whether to generate synthetic images
            noise_config: Configuration for realistic noise simulation (Step 531)
        """
        self.simulate_delays = simulate_delays
        self.generate_images = generate_images
        self.noise_config = noise_config or NoiseConfig()

        # Hardware info
        self.info = CameraInfo()

        # Settings
        self.settings = CameraSettings()
        self.settings.roi_width = self.info.sensor_width_px
        self.settings.roi_height = self.info.sensor_height_px

        # Status
        self.status = CameraStatus()

        # Internal state
        self._exposure_task: Optional[asyncio.Task] = None
        self._last_image: Optional[np.ndarray] = None

        # Hot pixel map (generated once per camera instance)
        self._hot_pixel_map: Optional[np.ndarray] = None

        # Error injection
        self._inject_connect_error = False
        self._inject_capture_error = False
        self._inject_timeout = False

        # Callbacks
        self._exposure_callbacks: List[Callable] = []
        self._complete_callbacks: List[Callable] = []

    @property
    def is_connected(self) -> bool:
        """Check if camera is connected."""
        return self.status.state != MockCameraState.DISCONNECTED

    @property
    def is_exposing(self) -> bool:
        """Check if camera is currently exposing."""
        return self.status.state == MockCameraState.EXPOSING

    async def connect(self, camera_id: int = 0) -> bool:
        """
        Connect to camera.

        Args:
            camera_id: Camera index (ignored in mock)

        Returns:
            True if connected successfully
        """
        if self._inject_connect_error:
            raise ConnectionError("Mock: Simulated connection failure")

        if self.simulate_delays:
            await asyncio.sleep(0.2)

        self.status.state = MockCameraState.IDLE
        self.status.temperature_c = 20.0

        logger.info(f"MockCamera connected: {self.info.name}")
        return True

    async def disconnect(self):
        """Disconnect from camera."""
        await self.abort_exposure()
        self.status.state = MockCameraState.DISCONNECTED
        logger.info("MockCamera disconnected")

    def get_info(self) -> CameraInfo:
        """Get camera hardware information."""
        return self.info

    def get_settings(self) -> CameraSettings:
        """Get current camera settings."""
        return self.settings

    def get_status(self) -> CameraStatus:
        """Get current camera status."""
        return self.status

    def set_exposure(self, exposure_sec: float):
        """
        Set exposure time.

        Args:
            exposure_sec: Exposure time in seconds
        """
        if exposure_sec < self.info.min_exposure_ms / 1000:
            raise ValueError(f"Exposure too short: min {self.info.min_exposure_ms}ms")
        if exposure_sec > self.info.max_exposure_sec:
            raise ValueError(f"Exposure too long: max {self.info.max_exposure_sec}s")

        self.settings.exposure_sec = exposure_sec
        logger.debug(f"MockCamera exposure set to {exposure_sec}s")

    def set_gain(self, gain: int):
        """
        Set camera gain.

        Args:
            gain: Gain value (0 to max_gain)
        """
        if not (0 <= gain <= self.info.max_gain):
            raise ValueError(f"Gain must be 0-{self.info.max_gain}")

        self.settings.gain = gain
        logger.debug(f"MockCamera gain set to {gain}")

    def set_offset(self, offset: int):
        """
        Set camera offset/black level.

        Args:
            offset: Offset value
        """
        self.settings.offset = offset
        logger.debug(f"MockCamera offset set to {offset}")

    def set_binning(self, mode: BinningMode):
        """
        Set camera binning mode.

        Args:
            mode: Binning mode
        """
        self.settings.binning = mode

        # Adjust ROI for binning
        bin_factor = int(mode.value[0])
        self.settings.roi_width = self.info.sensor_width_px // bin_factor
        self.settings.roi_height = self.info.sensor_height_px // bin_factor

        logger.debug(f"MockCamera binning set to {mode.value}")

    def set_roi(self, x: int, y: int, width: int, height: int):
        """
        Set region of interest.

        Args:
            x: ROI x offset
            y: ROI y offset
            width: ROI width
            height: ROI height
        """
        bin_factor = int(self.settings.binning.value[0])
        max_width = self.info.sensor_width_px // bin_factor
        max_height = self.info.sensor_height_px // bin_factor

        if x + width > max_width or y + height > max_height:
            raise ValueError("ROI exceeds sensor bounds")

        self.settings.roi_x = x
        self.settings.roi_y = y
        self.settings.roi_width = width
        self.settings.roi_height = height

        logger.debug(f"MockCamera ROI set to ({x}, {y}, {width}, {height})")

    async def capture(self) -> Any:
        """
        Capture a single frame.

        Returns:
            Image data as numpy array

        Raises:
            RuntimeError: If camera not connected or already exposing
        """
        if not self.is_connected:
            raise RuntimeError("Camera not connected")

        if self.is_exposing:
            raise RuntimeError("Exposure already in progress")

        if self._inject_capture_error:
            raise RuntimeError("Mock: Simulated capture failure")

        if self._inject_timeout:
            raise TimeoutError("Mock: Simulated capture timeout")

        self.status.state = MockCameraState.EXPOSING
        self.status.exposure_progress = 0.0

        logger.info(f"MockCamera starting {self.settings.exposure_sec}s exposure")

        # Simulate exposure time
        if self.simulate_delays:
            exposure_time = self.settings.exposure_sec
            update_interval = min(0.5, exposure_time / 10)
            elapsed = 0.0

            while elapsed < exposure_time:
                if self.status.state != MockCameraState.EXPOSING:
                    raise RuntimeError("Exposure aborted")

                await asyncio.sleep(update_interval)
                elapsed += update_interval
                self.status.exposure_progress = min(100.0, (elapsed / exposure_time) * 100)

                # Notify progress callbacks
                for callback in self._exposure_callbacks:
                    try:
                        callback(self.status.exposure_progress)
                    except Exception as e:
                        logger.error(f"Progress callback error: {e}")

        # Download phase
        self.status.state = MockCameraState.DOWNLOADING
        if self.simulate_delays:
            await asyncio.sleep(0.2)

        # Generate image
        if self.generate_images and HAS_NUMPY:
            image = self._generate_synthetic_image()
        elif HAS_NUMPY:
            image = np.zeros(
                (self.settings.roi_height, self.settings.roi_width),
                dtype=np.uint16
            )
        else:
            # Return placeholder when numpy not available
            image = None

        self._last_image = image
        self.status.state = MockCameraState.IDLE
        self.status.last_exposure_time = datetime.now()
        self.status.exposure_progress = 100.0

        logger.info("MockCamera exposure complete")

        # Notify complete callbacks
        for callback in self._complete_callbacks:
            try:
                callback(image)
            except Exception as e:
                logger.error(f"Complete callback error: {e}")

        return image

    async def start_exposure(self) -> bool:
        """
        Start an exposure asynchronously.

        Returns:
            True if exposure started
        """
        if self.is_exposing:
            return False

        self._exposure_task = asyncio.create_task(self.capture())
        return True

    async def abort_exposure(self):
        """Abort current exposure."""
        if self._exposure_task and not self._exposure_task.done():
            self.status.state = MockCameraState.IDLE
            self._exposure_task.cancel()
            try:
                await self._exposure_task
            except asyncio.CancelledError:
                pass

        logger.info("MockCamera exposure aborted")

    def get_last_image(self) -> Optional[Any]:
        """Get the last captured image."""
        return self._last_image

    def _generate_synthetic_image(self) -> Any:
        """
        Generate a synthetic star field image with realistic noise (Step 531).

        Implements proper CCD/CMOS noise model:
        1. Bias level (constant offset)
        2. Dark current (thermal, temperature/time dependent)
        3. Sky background signal
        4. Star signals
        5. Shot noise (Poisson on all signals)
        6. Read noise (Gaussian from electronics)
        7. Hot pixels (defects)
        """
        if not HAS_NUMPY:
            return None

        height = self.settings.roi_height
        width = self.settings.roi_width
        nc = self.noise_config
        exposure_sec = self.settings.exposure_sec
        temp_c = self.status.temperature_c

        # Effective gain (electrons per ADU) scales with camera gain setting
        # Higher gain = fewer electrons per ADU = more sensitive but more noise
        effective_gain_e_per_adu = nc.gain_e_per_adu * (1 + self.settings.gain / 100)

        # Start with signal in electrons
        signal_e = np.zeros((height, width), dtype=np.float64)

        # 1. Dark current (electrons) - doubles every ~6°C
        if nc.enable_dark_current:
            # Scale dark current by temperature relative to reference (-10°C)
            temp_factor = 2 ** ((temp_c - (-10.0)) / nc.dark_current_doubling_temp_c)
            dark_e = nc.dark_current_e_per_sec * temp_factor * exposure_sec
            signal_e += dark_e

        # 2. Add hot pixels (persistent defects with high dark current)
        if nc.enable_hot_pixels:
            if self._hot_pixel_map is None:
                # Generate hot pixel map once per camera
                n_hot = int(self.info.sensor_width_px * self.info.sensor_height_px
                           * nc.hot_pixel_fraction)
                self._hot_pixel_map = np.zeros(
                    (self.info.sensor_height_px, self.info.sensor_width_px),
                    dtype=np.float32
                )
                hot_y = np.random.randint(0, self.info.sensor_height_px, n_hot)
                hot_x = np.random.randint(0, self.info.sensor_width_px, n_hot)
                self._hot_pixel_map[hot_y, hot_x] = nc.hot_pixel_rate_e_per_sec

            # Apply hot pixel contribution (cropped to ROI)
            roi_hot = self._hot_pixel_map[
                self.settings.roi_y:self.settings.roi_y + height,
                self.settings.roi_x:self.settings.roi_x + width
            ]
            signal_e += roi_hot * exposure_sec

        # 3. Sky background signal (electrons) - scales with exposure and gain
        sky_background_e = 50 * exposure_sec * (1 + self.settings.gain / 200)
        signal_e += sky_background_e

        # 4. Add synthetic stars
        num_stars = np.random.randint(20, 100)
        for _ in range(num_stars):
            x = np.random.randint(0, width)
            y = np.random.randint(0, height)
            # Star flux in electrons
            brightness_e = np.random.uniform(1000, 50000) * exposure_sec
            sigma = np.random.uniform(1.5, 4.0)

            # Create Gaussian star PSF
            y_min, y_max = max(0, y - 20), min(height, y + 20)
            x_min, x_max = max(0, x - 20), min(width, x + 20)

            if y_max > y_min and x_max > x_min:
                y_grid, x_grid = np.ogrid[y_min:y_max, x_min:x_max]
                star = brightness_e * np.exp(
                    -((x_grid - x)**2 + (y_grid - y)**2) / (2 * sigma**2)
                )
                signal_e[y_min:y_max, x_min:x_max] += star

        # 5. Shot noise (Poisson noise on signal)
        if nc.enable_shot_noise:
            # Poisson noise - variance equals mean
            signal_e = np.maximum(signal_e, 0)  # Ensure non-negative
            signal_e = np.random.poisson(signal_e.astype(np.float64)).astype(np.float64)

        # 6. Read noise (Gaussian, in electrons)
        if nc.enable_read_noise:
            read_noise = np.random.normal(0, nc.read_noise_e, (height, width))
            signal_e += read_noise

        # Convert electrons to ADU
        signal_adu = signal_e / effective_gain_e_per_adu

        # 7. Add bias level
        if nc.enable_bias:
            signal_adu += nc.bias_level_adu

        # Clip to valid range and convert to uint16
        max_value = (2 ** self.info.bit_depth) - 1
        image = np.clip(signal_adu, 0, max_value).astype(np.uint16)

        return image

    # Cooling control
    async def set_cooler(self, enabled: bool, setpoint_c: float = -10.0):
        """
        Control camera cooling.

        Args:
            enabled: Whether to enable cooler
            setpoint_c: Target temperature in Celsius
        """
        if not self.info.has_cooler:
            raise RuntimeError("Camera does not have cooler")

        self.settings.cooler_on = enabled
        self.settings.cooler_setpoint_c = setpoint_c

        logger.info(f"MockCamera cooler {'enabled' if enabled else 'disabled'}, setpoint={setpoint_c}°C")

        # Simulate cooling (gradual temperature change)
        if enabled and self.simulate_delays:
            asyncio.create_task(self._simulate_cooling())

    async def _simulate_cooling(self):
        """Simulate gradual cooling to setpoint."""
        while (self.settings.cooler_on and
               abs(self.status.temperature_c - self.settings.cooler_setpoint_c) > 0.5):

            diff = self.settings.cooler_setpoint_c - self.status.temperature_c
            # Cool at ~1°C per second
            self.status.temperature_c += np.clip(diff, -1.0, 1.0)

            # Adjust cooler power based on temperature differential
            self.status.cooler_power_percent = min(100, abs(diff) * 10)

            await asyncio.sleep(1.0)

        self.status.cooler_power_percent = 20.0  # Maintenance power

    def get_temperature(self) -> float:
        """Get current sensor temperature."""
        return self.status.temperature_c

    # Callbacks
    def set_exposure_callback(self, callback: Callable):
        """Register callback for exposure progress updates."""
        self._exposure_callbacks.append(callback)

    def set_complete_callback(self, callback: Callable):
        """Register callback for exposure completion."""
        self._complete_callbacks.append(callback)

    # Error injection
    def inject_connect_error(self, enable: bool = True):
        """Enable/disable connection error injection."""
        self._inject_connect_error = enable

    def inject_capture_error(self, enable: bool = True):
        """Enable/disable capture error injection."""
        self._inject_capture_error = enable

    def inject_timeout(self, enable: bool = True):
        """Enable/disable timeout injection."""
        self._inject_timeout = enable

    def reset(self):
        """Reset mock to initial state."""
        self.status = CameraStatus()
        self.settings = CameraSettings()
        self.settings.roi_width = self.info.sensor_width_px
        self.settings.roi_height = self.info.sensor_height_px
        self._last_image = None
        self._hot_pixel_map = None  # Regenerate hot pixels on reset
        self._inject_connect_error = False
        self._inject_capture_error = False
        self._inject_timeout = False

    def set_noise_config(self, config: NoiseConfig):
        """
        Update noise simulation configuration (Step 531).

        Args:
            config: New noise configuration
        """
        self.noise_config = config
        self._hot_pixel_map = None  # Regenerate hot pixels with new config
        logger.debug(f"MockCamera noise config updated")
