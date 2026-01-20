"""
NIGHTWATCH Camera Service Unit Tests

Step 100: Write unit tests for camera control
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

from services.camera.asi_camera import (
    ASICamera,
    CameraSettings,
    CameraInfo,
    CaptureSession,
    ImageFormat,
    CaptureMode,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def camera():
    """Create a camera instance without hardware initialization."""
    return ASICamera(camera_index=0)


@pytest.fixture
def camera_settings():
    """Create default camera settings."""
    return CameraSettings()


# ============================================================================
# Camera Settings Tests
# ============================================================================

class TestCameraSettings:
    """Tests for CameraSettings dataclass."""

    def test_default_settings(self, camera_settings):
        """Verify default camera settings."""
        assert camera_settings.gain == 250
        assert camera_settings.exposure_ms == 10.0
        assert camera_settings.binning == 1
        assert camera_settings.format == ImageFormat.SER
        assert camera_settings.usb_bandwidth == 80
        assert camera_settings.high_speed_mode is True
        assert camera_settings.cooler_on is False

    def test_custom_settings(self):
        """Verify custom camera settings."""
        settings = CameraSettings(
            gain=300,
            exposure_ms=50.0,
            binning=2,
            format=ImageFormat.FITS,
        )
        assert settings.gain == 300
        assert settings.exposure_ms == 50.0
        assert settings.binning == 2
        assert settings.format == ImageFormat.FITS


# ============================================================================
# Camera Info Tests
# ============================================================================

class TestCameraInfo:
    """Tests for CameraInfo dataclass."""

    def test_camera_info_creation(self):
        """Verify CameraInfo can be created."""
        info = CameraInfo(
            name="ZWO ASI290MC",
            camera_id=1,
            max_width=1936,
            max_height=1096,
            pixel_size_um=2.9,
            is_color=True,
            has_cooler=False,
            bit_depth=12,
            usb_host="USB3"
        )
        assert info.name == "ZWO ASI290MC"
        assert info.max_width == 1936
        assert info.pixel_size_um == 2.9
        assert info.is_color is True
        assert info.has_cooler is False


# ============================================================================
# ASICamera Tests (without hardware)
# ============================================================================

class TestASICamera:
    """Tests for ASICamera class."""

    def test_camera_initialization_state(self, camera):
        """Verify camera starts in uninitialized state."""
        assert camera.initialized is False
        assert camera.capturing is False
        assert camera.info is None

    def test_presets_exist(self, camera):
        """Verify planetary presets are defined."""
        assert "mars" in camera.PRESETS
        assert "jupiter" in camera.PRESETS
        assert "saturn" in camera.PRESETS
        assert "moon" in camera.PRESETS
        assert "deep_sky" in camera.PRESETS

    def test_get_preset(self, camera):
        """Verify preset retrieval."""
        mars = camera.get_preset("mars")
        assert mars.gain == 280
        assert mars.exposure_ms == 8.0

        jupiter = camera.get_preset("Jupiter")  # Case insensitive
        assert jupiter.gain == 250

    def test_get_preset_unknown(self, camera):
        """Verify unknown preset returns default."""
        settings = camera.get_preset("unknown_target")
        assert isinstance(settings, CameraSettings)

    def test_get_current_settings(self, camera):
        """Verify current settings retrieval."""
        settings = camera.get_current_settings()
        assert isinstance(settings, CameraSettings)


# ============================================================================
# Gain Control Tests (Step 86)
# ============================================================================

class TestGainControl:
    """Tests for gain control functionality."""

    def test_get_gain_without_camera(self, camera):
        """Verify get_gain returns settings when not initialized."""
        gain = camera.get_gain()
        assert gain == camera._settings.gain

    def test_set_gain_without_camera(self, camera):
        """Verify set_gain fails gracefully without camera."""
        result = camera.set_gain(300)
        assert result is False

    def test_get_gain_range_default(self, camera):
        """Verify default gain range."""
        min_gain, max_gain = camera.get_gain_range()
        assert min_gain == 0
        assert max_gain == 500


# ============================================================================
# Exposure Control Tests (Step 87)
# ============================================================================

class TestExposureControl:
    """Tests for exposure control functionality."""

    def test_get_exposure_without_camera(self, camera):
        """Verify get_exposure returns settings when not initialized."""
        exposure = camera.get_exposure()
        assert exposure == camera._settings.exposure_ms

    def test_set_exposure_without_camera(self, camera):
        """Verify set_exposure fails gracefully without camera."""
        result = camera.set_exposure(100.0)
        assert result is False

    def test_get_exposure_range_default(self, camera):
        """Verify default exposure range."""
        min_exp, max_exp = camera.get_exposure_range()
        assert min_exp == 0.001  # 1 microsecond
        assert max_exp == 3600000.0  # 1 hour


# ============================================================================
# Binning Control Tests (Step 88)
# ============================================================================

class TestBinningControl:
    """Tests for binning control functionality."""

    def test_get_binning_without_camera(self, camera):
        """Verify get_binning returns settings when not initialized."""
        binning = camera.get_binning()
        assert binning == 1

    def test_set_binning_without_camera(self, camera):
        """Verify set_binning fails gracefully without camera."""
        result = camera.set_binning(2)
        assert result is False

    def test_get_supported_binning_default(self, camera):
        """Verify default supported binning modes."""
        bins = camera.get_supported_binning()
        assert 1 in bins
        assert 2 in bins
        assert 4 in bins


# ============================================================================
# Temperature Monitoring Tests (Step 95)
# ============================================================================

class TestTemperatureMonitoring:
    """Tests for temperature monitoring functionality."""

    def test_get_temperature_status_uninitialized(self, camera):
        """Verify temperature status when not initialized."""
        status = camera.get_temperature_status()
        assert status["sensor_temp_c"] is None
        assert status["has_cooler"] is False
        assert status["cooler_on"] is False

    def test_get_temperature_without_camera(self, camera):
        """Verify get_temperature returns None when not initialized."""
        temp = camera.get_temperature()
        assert temp is None

    def test_get_cooler_power_without_camera(self, camera):
        """Verify get_cooler_power returns None when not initialized."""
        power = camera.get_cooler_power()
        assert power is None


# ============================================================================
# Capture Abort Tests (Step 96)
# ============================================================================

class TestCaptureAbort:
    """Tests for capture abort functionality."""

    def test_is_capture_in_progress_default(self, camera):
        """Verify capture is not in progress by default."""
        assert camera.is_capture_in_progress() is False

    def test_get_capture_progress_none(self, camera):
        """Verify capture progress is None when no capture."""
        progress = camera.get_capture_progress()
        assert progress is None

    @pytest.mark.asyncio
    async def test_abort_capture_no_capture(self, camera):
        """Verify abort returns False when no capture in progress."""
        result = await camera.abort_capture()
        assert result is False


# ============================================================================
# Capture Session Tests
# ============================================================================

class TestCaptureSession:
    """Tests for CaptureSession dataclass."""

    def test_capture_session_creation(self):
        """Verify CaptureSession can be created."""
        session = CaptureSession(
            session_id="mars_20240101_120000",
            target="mars",
            start_time=datetime.now(),
            settings=CameraSettings(),
            output_path=Path("/data/captures/mars.ser"),
        )
        assert session.session_id == "mars_20240101_120000"
        assert session.frame_count == 0
        assert session.complete is False
        assert session.error is None


# ============================================================================
# Image Format Tests
# ============================================================================

class TestImageFormat:
    """Tests for ImageFormat enum."""

    def test_all_formats_defined(self):
        """Verify all image formats are defined."""
        assert ImageFormat.RAW8.value == "RAW8"
        assert ImageFormat.RAW16.value == "RAW16"
        assert ImageFormat.SER.value == "SER"
        assert ImageFormat.FITS.value == "FITS"
        assert ImageFormat.PNG.value == "PNG"


# ============================================================================
# Capture Mode Tests
# ============================================================================

class TestCaptureMode:
    """Tests for CaptureMode enum."""

    def test_all_modes_defined(self):
        """Verify all capture modes are defined."""
        assert CaptureMode.PLANETARY.value == "planetary"
        assert CaptureMode.LUNAR.value == "lunar"
        assert CaptureMode.DEEP_SKY.value == "deep_sky"
        assert CaptureMode.PREVIEW.value == "preview"


# ============================================================================
# Run Configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
