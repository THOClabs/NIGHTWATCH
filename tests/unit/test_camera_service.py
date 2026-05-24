"""
NIGHTWATCH Camera Service Unit Tests

Step 100: Write unit tests for camera control
"""

import logging
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
# TEC Cooling Tests (HWS-002)
# ============================================================================

class TestTECCooling:
    """Tests for closed-loop TEC cooling controller (cool_to method)."""

    @pytest.fixture
    def cooled_camera(self):
        """Create a camera wired with a mock SDK + camera handle and has_cooler=True."""
        cam = ASICamera(camera_index=0)
        # Wire up the mock SDK constants
        cam._asi = MagicMock()
        cam._asi.ASI_TEMPERATURE = 18
        cam._asi.ASI_TARGET_TEMP = 19
        cam._asi.ASI_COOLER_ON = 20
        cam._asi.ASI_COOLER_POWER_PERC = 21
        # Mock camera handle
        cam._camera = MagicMock()
        # Cooled-camera info
        cam._info = CameraInfo(
            name="ZWO ASI1600MM-Cool",
            camera_id=1,
            max_width=4656,
            max_height=3520,
            pixel_size_um=3.8,
            is_color=False,
            has_cooler=True,
            bit_depth=12,
            usb_host="USB3",
        )
        return cam

    @pytest.mark.asyncio
    async def test_cool_to_returns_false_when_no_cooler(self, camera):
        """No cooler available → return False immediately, no SDK calls."""
        # Default camera fixture has _info=None and _camera=None
        result = await camera.cool_to(-10.0, tolerance_c=0.5, timeout_s=1.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_cool_to_returns_false_when_info_says_no_cooler(self):
        """has_cooler=False on info → return False immediately."""
        cam = ASICamera(camera_index=0)
        cam._camera = MagicMock()
        cam._asi = MagicMock()
        cam._info = CameraInfo(
            name="ZWO ASI290MC",
            camera_id=1,
            max_width=1936,
            max_height=1096,
            pixel_size_um=2.9,
            is_color=True,
            has_cooler=False,
            bit_depth=12,
            usb_host="USB3",
        )
        result = await cam.cool_to(-10.0, tolerance_c=0.5, timeout_s=1.0)
        assert result is False
        # Ensure we did NOT touch the SDK
        cam._camera.set_control_value.assert_not_called()

    @pytest.mark.asyncio
    async def test_cool_to_returns_true_when_temp_stabilises(self, cooled_camera):
        """
        Spec verify case: ramping temp that stabilizes within tolerance for >= stable_secs
        → returns True. Uses sped-up timing for the unit test.
        """
        # SDK returns tenths-of-a-degree integers. Ramp: 25, 15, 5, then stable at -10.
        # After ramp reaches target, hold for enough polls to satisfy stable_secs.
        # stable_secs=0.05 + poll_interval_s=0.01 → ~5 stable polls needed (with margin).
        readings = [250, 150, 50, -50, -100, -100, -100, -100, -100, -100, -100, -100,
                    -100, -100, -100, -100]
        cooled_camera._camera.get_control_value.side_effect = [
            (r, 0) for r in readings
        ]

        result = await cooled_camera.cool_to(
            target_c=-10.0,
            tolerance_c=0.5,
            timeout_s=2.0,
            stable_secs=0.05,
            poll_interval_s=0.01,
        )
        assert result is True

        # Verify cooler was enabled with target temp.
        # Should have written ASI_TARGET_TEMP=-10 and ASI_COOLER_ON=1.
        set_calls = cooled_camera._camera.set_control_value.call_args_list
        ctrls_written = [c.args[0] for c in set_calls]
        assert 19 in ctrls_written  # ASI_TARGET_TEMP
        assert 20 in ctrls_written  # ASI_COOLER_ON
        # And cooler ON was set to 1
        cooler_on_calls = [c for c in set_calls if c.args[0] == 20]
        assert any(c.args[1] == 1 for c in cooler_on_calls)

    @pytest.mark.asyncio
    async def test_cool_to_resets_stability_timer_on_drift(self, cooled_camera):
        """
        Temp reaches target, drifts out of tolerance, then re-stabilizes.
        cool_to must wait for the SECOND continuous stable window, not the first.
        """
        # Ramp in → stable briefly → drift out → stable again long enough.
        # With stable_secs=0.05 and poll_interval_s=0.01, ~5 polls = ~0.05s stable.
        # First "stable" run is only 2 polls (insufficient), then drifts, then 8 polls (sufficient).
        readings = [
            250, 50,           # ramping
            -100, -100,        # in tolerance (2 polls, ~0.02s — not enough)
            -50,               # DRIFTS OUT (-5.0°C, diff=5°C > 0.5°C tolerance) → reset
            -100, -100, -100, -100, -100, -100, -100, -100, -100, -100,  # stable run #2
        ]
        cooled_camera._camera.get_control_value.side_effect = [
            (r, 0) for r in readings
        ]

        result = await cooled_camera.cool_to(
            target_c=-10.0,
            tolerance_c=0.5,
            timeout_s=2.0,
            stable_secs=0.05,
            poll_interval_s=0.01,
        )
        assert result is True

        # Verify that the loop polled past the drift sample (i.e., did NOT
        # short-circuit on the first stable run).
        # Count of get_control_value calls should be >= len(readings up to drift) + a few more.
        # The drift sample is index 4 (the 5th reading). To succeed we need at least
        # the drift sample + ~5 more stable polls = 10+ reads.
        assert cooled_camera._camera.get_control_value.call_count >= 10

    @pytest.mark.asyncio
    async def test_cool_to_returns_false_on_timeout(self, cooled_camera, caplog):
        """
        Temp never reaches target → timeout elapses → returns False with warning.
        """
        # Always read 25°C (250 tenths) — far from target.
        cooled_camera._camera.get_control_value.return_value = (250, 0)

        caplog.set_level(logging.WARNING, logger="NIGHTWATCH.Camera")

        result = await cooled_camera.cool_to(
            target_c=-10.0,
            tolerance_c=0.5,
            timeout_s=0.05,   # 50ms total budget
            stable_secs=0.02,
            poll_interval_s=0.01,
        )
        assert result is False

        # A warning about timing out should have been logged, naming current + target.
        timeout_warnings = [
            r for r in caplog.records
            if r.levelno == logging.WARNING and "timeout" in r.message.lower()
        ]
        assert len(timeout_warnings) >= 1
        # The warning should mention temps
        msg = timeout_warnings[-1].message
        assert "-10" in msg or "target" in msg.lower()

    @pytest.mark.asyncio
    async def test_cool_to_handles_temp_read_failure(self, cooled_camera):
        """
        get_control_value raises on some polls → cool_to does not crash;
        treats failed reads as 'not stable', eventually stabilizes when reads succeed.
        """
        # Sequence: bad read, bad read, then steady stream of stable readings.
        responses = [
            Exception("SDK transient error"),
            Exception("SDK transient error"),
        ] + [(-100, 0)] * 12  # stable at -10°C

        def side_effect(*args, **kwargs):
            resp = responses.pop(0)
            if isinstance(resp, Exception):
                raise resp
            return resp

        cooled_camera._camera.get_control_value.side_effect = side_effect

        result = await cooled_camera.cool_to(
            target_c=-10.0,
            tolerance_c=0.5,
            timeout_s=2.0,
            stable_secs=0.05,
            poll_interval_s=0.01,
        )
        assert result is True


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
