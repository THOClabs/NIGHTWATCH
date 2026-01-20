"""
NIGHTWATCH ZWO ASI Camera Service
Planetary and Deep-Sky Imaging

POS Panel v2.0 - Day 12 Recommendations (Damian Peach):
- Gain: 250-300 for Mars (balance noise/speed)
- Exposure: 5-15ms depending on seeing
- ROI: Crop to 640x480 for faster capture
- Binning: 1x1 only (already undersampled at f/6)
- Format: SER files for stacking, 60-90 seconds each
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Tuple

logger = logging.getLogger("NIGHTWATCH.Camera")


class ImageFormat(Enum):
    """Supported image formats."""
    RAW8 = "RAW8"
    RAW16 = "RAW16"
    SER = "SER"
    FITS = "FITS"
    PNG = "PNG"


class CaptureMode(Enum):
    """Capture modes."""
    PLANETARY = "planetary"    # High-speed video
    LUNAR = "lunar"            # Medium-speed, larger ROI
    DEEP_SKY = "deep_sky"      # Long exposure FITS
    PREVIEW = "preview"        # Quick look


@dataclass
class CameraSettings:
    """Camera configuration for capture."""
    gain: int = 250               # 0-500 typically
    exposure_ms: float = 10.0     # Exposure time
    roi: Optional[Tuple[int, int, int, int]] = None  # (x, y, width, height)
    binning: int = 1              # 1x1, 2x2, etc.
    format: ImageFormat = ImageFormat.SER
    usb_bandwidth: int = 80       # Percentage (40-100)
    high_speed_mode: bool = True  # For planetary
    flip_horizontal: bool = False
    flip_vertical: bool = False

    # Cooling (for cooled cameras)
    target_temp_c: Optional[float] = None
    cooler_on: bool = False


@dataclass
class CameraInfo:
    """Camera hardware information."""
    name: str
    camera_id: int
    max_width: int
    max_height: int
    pixel_size_um: float
    is_color: bool
    has_cooler: bool
    bit_depth: int
    usb_host: str


@dataclass
class CaptureSession:
    """Active capture session metadata."""
    session_id: str
    target: str
    start_time: datetime
    settings: CameraSettings
    output_path: Path
    frame_count: int = 0
    duration_sec: float = 0.0
    complete: bool = False
    error: Optional[str] = None


class ASICamera:
    """
    ZWO ASI Camera Control for NIGHTWATCH.

    Supports:
    - Planetary high-speed video capture (SER format)
    - Deep-sky long exposure imaging (FITS format)
    - Live preview for focusing
    - Automated capture sequences

    Note: Requires zwoasi library (pip install zwoasi)
    """

    # Recommended settings by target type (Damian Peach recommendations)
    PRESETS = {
        "mars": CameraSettings(gain=280, exposure_ms=8.0, roi=(0, 0, 640, 480)),
        "jupiter": CameraSettings(gain=250, exposure_ms=12.0, roi=(0, 0, 800, 600)),
        "saturn": CameraSettings(gain=300, exposure_ms=15.0, roi=(0, 0, 800, 600)),
        "moon": CameraSettings(gain=100, exposure_ms=3.0),
        "sun": CameraSettings(gain=50, exposure_ms=1.0),  # REQUIRES FILTER!
        "deep_sky": CameraSettings(gain=200, exposure_ms=30000.0, format=ImageFormat.FITS),
    }

    def __init__(self, camera_index: int = 0, data_dir: Optional[Path] = None):
        """
        Initialize ASI camera.

        Args:
            camera_index: Camera index (0 for first camera)
            data_dir: Directory for saving captures
        """
        self.camera_index = camera_index
        self.data_dir = data_dir or Path("/data/captures")
        self._camera = None
        self._info: Optional[CameraInfo] = None
        self._initialized = False
        self._capturing = False
        self._current_session: Optional[CaptureSession] = None
        self._settings = CameraSettings()

    @property
    def initialized(self) -> bool:
        """Check if camera is initialized."""
        return self._initialized

    @property
    def capturing(self) -> bool:
        """Check if capture is in progress."""
        return self._capturing

    @property
    def info(self) -> Optional[CameraInfo]:
        """Camera information."""
        return self._info

    def initialize(self) -> bool:
        """
        Initialize camera connection.

        Returns:
            True if initialized successfully
        """
        try:
            # Import zwoasi (optional dependency)
            try:
                import zwoasi as asi
                self._asi = asi
            except ImportError:
                logger.error("zwoasi not installed. Install with: pip install zwoasi")
                return False

            # Initialize library
            asi.init()

            num_cameras = asi.get_num_cameras()
            if num_cameras == 0:
                logger.error("No ZWO cameras found")
                return False

            if self.camera_index >= num_cameras:
                logger.error(f"Camera index {self.camera_index} invalid (found {num_cameras})")
                return False

            # Connect to camera
            self._camera = asi.Camera(self.camera_index)
            props = self._camera.get_camera_property()

            self._info = CameraInfo(
                name=props["Name"],
                camera_id=props["CameraID"],
                max_width=props["MaxWidth"],
                max_height=props["MaxHeight"],
                pixel_size_um=props["PixelSize"],
                is_color=props["IsColorCam"],
                has_cooler=props["IsCoolerCam"],
                bit_depth=props["BitDepth"],
                usb_host=props.get("USB3Host", "Unknown")
            )

            # Set default controls
            self._apply_settings(self._settings)

            self._initialized = True
            logger.info(f"Initialized camera: {self._info.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            return False

    def close(self):
        """Close camera connection."""
        if self._camera:
            try:
                self._camera.close()
            except Exception:
                pass
        self._initialized = False
        self._camera = None
        logger.info("Camera closed")

    def _apply_settings(self, settings: CameraSettings):
        """Apply camera settings."""
        if not self._camera:
            return

        try:
            asi = self._asi

            # Gain
            self._camera.set_control_value(asi.ASI_GAIN, settings.gain)

            # Exposure (in microseconds)
            exposure_us = int(settings.exposure_ms * 1000)
            self._camera.set_control_value(asi.ASI_EXPOSURE, exposure_us)

            # USB bandwidth
            self._camera.set_control_value(
                asi.ASI_BANDWIDTHOVERLOAD,
                settings.usb_bandwidth
            )

            # High speed mode
            self._camera.set_control_value(
                asi.ASI_HIGH_SPEED_MODE,
                1 if settings.high_speed_mode else 0
            )

            # ROI
            if settings.roi:
                x, y, width, height = settings.roi
                self._camera.set_roi(x, y, width, height, settings.binning)
            else:
                # Full frame
                self._camera.set_roi(
                    0, 0,
                    self._info.max_width,
                    self._info.max_height,
                    settings.binning
                )

            # Flip
            self._camera.set_control_value(
                asi.ASI_FLIP,
                (2 if settings.flip_horizontal else 0) +
                (1 if settings.flip_vertical else 0)
            )

            # Cooling
            if self._info.has_cooler and settings.cooler_on:
                if settings.target_temp_c is not None:
                    self._camera.set_control_value(
                        asi.ASI_TARGET_TEMP,
                        int(settings.target_temp_c)
                    )
                    self._camera.set_control_value(asi.ASI_COOLER_ON, 1)

            self._settings = settings
            logger.debug(f"Applied camera settings: gain={settings.gain}, exp={settings.exposure_ms}ms")

        except Exception as e:
            logger.error(f"Failed to apply settings: {e}")

    def get_preset(self, target: str) -> CameraSettings:
        """
        Get recommended settings for a target.

        Args:
            target: Target name (mars, jupiter, saturn, moon, sun, deep_sky)

        Returns:
            Recommended settings
        """
        return self.PRESETS.get(target.lower(), CameraSettings())

    # =========================================================================
    # CAPTURE METHODS
    # =========================================================================

    async def start_capture(self,
                           target: str,
                           duration_sec: float = 60.0,
                           settings: Optional[CameraSettings] = None) -> CaptureSession:
        """
        Start planetary video capture.

        Args:
            target: Target name (for filename and metadata)
            duration_sec: Capture duration in seconds
            settings: Camera settings (uses preset if None)

        Returns:
            CaptureSession with capture details
        """
        if not self._initialized:
            raise RuntimeError("Camera not initialized")

        if self._capturing:
            raise RuntimeError("Capture already in progress")

        # Use preset if no settings provided
        if settings is None:
            settings = self.get_preset(target)

        self._apply_settings(settings)

        # Create session
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = f"{target.lower()}_{timestamp}"
        output_path = self.data_dir / datetime.now().strftime("%Y-%m-%d") / f"{session_id}.ser"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        session = CaptureSession(
            session_id=session_id,
            target=target,
            start_time=datetime.now(),
            settings=settings,
            output_path=output_path,
            duration_sec=duration_sec
        )

        self._current_session = session
        self._capturing = True

        # Start capture in background
        asyncio.create_task(self._capture_loop(session, duration_sec))

        logger.info(f"Started capture: {session_id} ({duration_sec}s)")
        return session

    async def _capture_loop(self, session: CaptureSession, duration_sec: float):
        """Background capture loop."""
        try:
            # In real implementation, would use ASI video capture
            # For now, simulate capture
            start_time = datetime.now()
            frame_count = 0

            while self._capturing:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed >= duration_sec:
                    break

                # Simulate frame capture
                await asyncio.sleep(session.settings.exposure_ms / 1000.0)
                frame_count += 1
                session.frame_count = frame_count

            session.complete = True
            session.frame_count = frame_count
            logger.info(f"Capture complete: {session.session_id} ({frame_count} frames)")

        except Exception as e:
            session.error = str(e)
            logger.error(f"Capture error: {e}")

        finally:
            self._capturing = False
            self._current_session = None

    async def stop_capture(self) -> Optional[CaptureSession]:
        """
        Stop current capture.

        Returns:
            Completed session info
        """
        if not self._capturing:
            return None

        session = self._current_session
        self._capturing = False

        # Wait for capture loop to finish
        await asyncio.sleep(0.1)

        logger.info("Capture stopped")
        return session

    async def capture_single(self,
                            exposure_sec: float = 1.0,
                            format: ImageFormat = ImageFormat.FITS,
                            filename: Optional[str] = None) -> Path:
        """
        Capture single frame.

        Args:
            exposure_sec: Exposure time in seconds
            format: Output format
            filename: Custom filename (optional)

        Returns:
            Path to saved image
        """
        if not self._initialized:
            raise RuntimeError("Camera not initialized")

        if self._capturing:
            raise RuntimeError("Capture in progress")

        # Set exposure
        settings = CameraSettings(
            gain=self._settings.gain,
            exposure_ms=exposure_sec * 1000,
            format=format
        )
        self._apply_settings(settings)

        # Generate filename
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = "fits" if format == ImageFormat.FITS else "png"
            filename = f"single_{timestamp}.{ext}"

        output_path = self.data_dir / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Capture frame
        try:
            # In real implementation: self._camera.capture()
            logger.info(f"Captured single frame: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Single capture failed: {e}")
            raise

    # =========================================================================
    # STATUS METHODS
    # =========================================================================

    def get_temperature(self) -> Optional[float]:
        """Get sensor temperature in Celsius."""
        if not self._camera or not self._info:
            return None

        try:
            if self._info.has_cooler:
                temp = self._camera.get_control_value(self._asi.ASI_TEMPERATURE)[0]
                return temp / 10.0  # Reported in 0.1°C units
            return None
        except Exception:
            return None

    def get_cooler_power(self) -> Optional[float]:
        """Get cooler power percentage."""
        if not self._camera or not self._info or not self._info.has_cooler:
            return None

        try:
            power = self._camera.get_control_value(self._asi.ASI_COOLER_POWER_PERC)[0]
            return float(power)
        except Exception:
            return None

    def get_current_settings(self) -> CameraSettings:
        """Get current camera settings."""
        return self._settings

    # =========================================================================
    # GAIN CONTROL (Step 86)
    # =========================================================================

    def set_gain(self, gain: int) -> bool:
        """
        Set camera gain.

        Args:
            gain: Gain value (typically 0-500 for ZWO cameras)

        Returns:
            True if successful
        """
        if not self._camera:
            logger.warning("Cannot set gain: camera not initialized")
            return False

        try:
            # Validate gain range
            min_gain, max_gain = self.get_gain_range()
            if not min_gain <= gain <= max_gain:
                logger.warning(f"Gain {gain} out of range ({min_gain}-{max_gain})")
                return False

            self._camera.set_control_value(self._asi.ASI_GAIN, gain)
            self._settings.gain = gain
            logger.debug(f"Set gain to {gain}")
            return True
        except Exception as e:
            logger.error(f"Failed to set gain: {e}")
            return False

    def get_gain(self) -> int:
        """
        Get current camera gain.

        Returns:
            Current gain value
        """
        if not self._camera:
            return self._settings.gain

        try:
            gain = self._camera.get_control_value(self._asi.ASI_GAIN)[0]
            return int(gain)
        except Exception:
            return self._settings.gain

    def get_gain_range(self) -> Tuple[int, int]:
        """
        Get supported gain range.

        Returns:
            Tuple of (min_gain, max_gain)
        """
        if not self._camera:
            return (0, 500)  # Default ZWO range

        try:
            info = self._camera.get_controls()[self._asi.ASI_GAIN]
            return (info["MinValue"], info["MaxValue"])
        except Exception:
            return (0, 500)

    # =========================================================================
    # EXPOSURE CONTROL (Step 87)
    # =========================================================================

    def set_exposure(self, exposure_ms: float) -> bool:
        """
        Set camera exposure time.

        Args:
            exposure_ms: Exposure time in milliseconds

        Returns:
            True if successful
        """
        if not self._camera:
            logger.warning("Cannot set exposure: camera not initialized")
            return False

        try:
            # Validate exposure range
            min_exp, max_exp = self.get_exposure_range()
            if not min_exp <= exposure_ms <= max_exp:
                logger.warning(f"Exposure {exposure_ms}ms out of range ({min_exp}-{max_exp}ms)")
                return False

            # Convert to microseconds for ASI API
            exposure_us = int(exposure_ms * 1000)
            self._camera.set_control_value(self._asi.ASI_EXPOSURE, exposure_us)
            self._settings.exposure_ms = exposure_ms
            logger.debug(f"Set exposure to {exposure_ms}ms")
            return True
        except Exception as e:
            logger.error(f"Failed to set exposure: {e}")
            return False

    def get_exposure(self) -> float:
        """
        Get current exposure time in milliseconds.

        Returns:
            Current exposure in ms
        """
        if not self._camera:
            return self._settings.exposure_ms

        try:
            exposure_us = self._camera.get_control_value(self._asi.ASI_EXPOSURE)[0]
            return exposure_us / 1000.0  # Convert to ms
        except Exception:
            return self._settings.exposure_ms

    def get_exposure_range(self) -> Tuple[float, float]:
        """
        Get supported exposure range in milliseconds.

        Returns:
            Tuple of (min_ms, max_ms)
        """
        if not self._camera:
            return (0.001, 3600000.0)  # 1us to 1hr default

        try:
            info = self._camera.get_controls()[self._asi.ASI_EXPOSURE]
            # Convert from microseconds to milliseconds
            return (info["MinValue"] / 1000.0, info["MaxValue"] / 1000.0)
        except Exception:
            return (0.001, 3600000.0)

    # =========================================================================
    # BINNING CONTROL (Step 88)
    # =========================================================================

    def set_binning(self, binning: int) -> bool:
        """
        Set camera binning mode.

        Args:
            binning: Binning factor (1, 2, 3, or 4)

        Returns:
            True if successful
        """
        if not self._camera:
            logger.warning("Cannot set binning: camera not initialized")
            return False

        supported = self.get_supported_binning()
        if binning not in supported:
            logger.warning(f"Binning {binning}x{binning} not supported. Supported: {supported}")
            return False

        try:
            # Get current ROI
            roi_info = self._camera.get_roi()
            # Set new ROI with updated binning
            self._camera.set_roi(
                roi_info[0], roi_info[1],  # x, y
                roi_info[2], roi_info[3],  # width, height
                binning
            )
            self._settings.binning = binning
            logger.debug(f"Set binning to {binning}x{binning}")
            return True
        except Exception as e:
            logger.error(f"Failed to set binning: {e}")
            return False

    def get_binning(self) -> int:
        """
        Get current binning mode.

        Returns:
            Current binning factor
        """
        if not self._camera:
            return self._settings.binning

        try:
            roi_info = self._camera.get_roi()
            return roi_info[4]  # binning is 5th element
        except Exception:
            return self._settings.binning

    def get_supported_binning(self) -> List[int]:
        """
        Get supported binning modes.

        Returns:
            List of supported binning factors
        """
        if not self._camera or not self._info:
            return [1, 2, 4]  # Default ZWO support

        try:
            props = self._camera.get_camera_property()
            bins = props.get("SupportedBins", [1, 2, 4])
            return list(bins)
        except Exception:
            return [1, 2, 4]

    # =========================================================================
    # TEMPERATURE MONITORING (Step 95)
    # =========================================================================

    def get_temperature_status(self) -> dict:
        """
        Get detailed temperature status.

        Returns:
            Dict with temperature information
        """
        result = {
            "sensor_temp_c": None,
            "target_temp_c": self._settings.target_temp_c,
            "cooler_on": self._settings.cooler_on,
            "cooler_power_percent": None,
            "has_cooler": False,
        }

        if not self._camera or not self._info:
            return result

        result["has_cooler"] = self._info.has_cooler

        if not self._info.has_cooler:
            return result

        try:
            # Get current sensor temperature
            temp = self._camera.get_control_value(self._asi.ASI_TEMPERATURE)[0]
            result["sensor_temp_c"] = temp / 10.0  # Reported in 0.1°C

            # Get cooler power
            power = self._camera.get_control_value(self._asi.ASI_COOLER_POWER_PERC)[0]
            result["cooler_power_percent"] = float(power)

            # Get cooler state
            cooler_on = self._camera.get_control_value(self._asi.ASI_COOLER_ON)[0]
            result["cooler_on"] = cooler_on == 1

        except Exception as e:
            logger.debug(f"Error reading temperature status: {e}")

        return result

    def set_cooler(self, enabled: bool, target_temp_c: Optional[float] = None) -> bool:
        """
        Control camera cooler.

        Args:
            enabled: Turn cooler on/off
            target_temp_c: Target temperature (required if enabling)

        Returns:
            True if successful
        """
        if not self._camera or not self._info or not self._info.has_cooler:
            logger.warning("Camera does not have a cooler")
            return False

        try:
            if enabled:
                if target_temp_c is None:
                    target_temp_c = self._settings.target_temp_c or -10.0

                self._camera.set_control_value(
                    self._asi.ASI_TARGET_TEMP,
                    int(target_temp_c)
                )
                self._camera.set_control_value(self._asi.ASI_COOLER_ON, 1)
                self._settings.target_temp_c = target_temp_c
                self._settings.cooler_on = True
                logger.info(f"Cooler enabled, target: {target_temp_c}°C")
            else:
                self._camera.set_control_value(self._asi.ASI_COOLER_ON, 0)
                self._settings.cooler_on = False
                logger.info("Cooler disabled")

            return True
        except Exception as e:
            logger.error(f"Failed to control cooler: {e}")
            return False

    # =========================================================================
    # CAPTURE ABORT (Step 96)
    # =========================================================================

    async def abort_capture(self) -> bool:
        """
        Immediately abort any capture in progress.

        Returns:
            True if capture was aborted
        """
        if not self._capturing:
            logger.debug("No capture to abort")
            return False

        logger.warning("Aborting capture!")
        self._capturing = False

        # Mark session as incomplete
        if self._current_session:
            self._current_session.complete = False
            self._current_session.error = "Capture aborted by user"

        # Stop video capture if running
        if self._camera:
            try:
                self._camera.stop_video_capture()
            except Exception:
                pass  # May not be in video mode

        # Brief delay to let capture loop exit
        await asyncio.sleep(0.1)

        logger.info("Capture aborted")
        return True

    def is_capture_in_progress(self) -> bool:
        """Check if a capture is currently in progress."""
        return self._capturing

    def get_capture_progress(self) -> Optional[dict]:
        """
        Get progress of current capture.

        Returns:
            Dict with capture progress or None if no capture
        """
        if not self._current_session:
            return None

        session = self._current_session
        elapsed = (datetime.now() - session.start_time).total_seconds()

        return {
            "session_id": session.session_id,
            "target": session.target,
            "frame_count": session.frame_count,
            "elapsed_sec": elapsed,
            "duration_sec": session.duration_sec,
            "progress_percent": min(100.0, (elapsed / session.duration_sec) * 100) if session.duration_sec > 0 else 0,
            "output_path": str(session.output_path),
        }


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    async def test():
        print("NIGHTWATCH Camera Service Test\n")

        camera = ASICamera()

        print("Attempting to initialize camera...")
        if camera.initialize():
            print(f"Camera: {camera.info.name}")
            print(f"Resolution: {camera.info.max_width}x{camera.info.max_height}")
            print(f"Pixel size: {camera.info.pixel_size_um}μm")
            print(f"Color: {camera.info.is_color}")
            print(f"Cooler: {camera.info.has_cooler}")

            # Show presets
            print("\nPlanetary presets:")
            for name, preset in ASICamera.PRESETS.items():
                print(f"  {name}: gain={preset.gain}, exp={preset.exposure_ms}ms")

            camera.close()
        else:
            print("No camera found or initialization failed")
            print("(This is expected if no ZWO camera is connected)")

    asyncio.run(test())
