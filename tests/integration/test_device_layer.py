"""
NIGHTWATCH Integration Tests - Device Layer

Tests for the cross-platform device layer (Phase 3 & 4 of INTEGRATION_PLAN).
Requires simulators to be running via docker-compose.

Setup:
    docker-compose -f docker/docker-compose.dev.yml up -d

Run:
    pytest tests/integration/test_device_layer.py -v

Coverage:
    pytest tests/integration/test_device_layer.py --cov=services.alpaca -v
"""

import asyncio
import pytest
import socket
import time
from typing import Generator

# Import Alpaca clients
from services.alpaca.alpaca_client import (
    AlpacaDiscovery,
    AlpacaTelescope,
    AlpacaCamera,
    AlpacaFocuser,
    AlpacaFilterWheel,
)


# ============================================================================
# Configuration
# ============================================================================

ALPACA_HOST = "localhost"
ALPACA_PORT = 11111
TELESCOPE_DEVICE_NUM = 0
CAMERA_DEVICE_NUM = 0
FOCUSER_DEVICE_NUM = 0
FILTERWHEEL_DEVICE_NUM = 0


# ============================================================================
# Test Utilities
# ============================================================================

def is_alpaca_available() -> bool:
    """Check if Alpaca simulator is reachable."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        result = sock.connect_ex((ALPACA_HOST, ALPACA_PORT))
        sock.close()
        return result == 0
    except Exception:
        return False


# Skip all tests if Alpaca not available
pytestmark = pytest.mark.skipif(
    not is_alpaca_available(),
    reason="Alpaca simulator not available. Run: docker-compose -f docker/docker-compose.dev.yml up -d"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def alpaca_telescope() -> Generator[AlpacaTelescope, None, None]:
    """Fixture providing connected Alpaca telescope."""
    telescope = AlpacaTelescope(ALPACA_HOST, ALPACA_PORT, TELESCOPE_DEVICE_NUM)
    connected = telescope.connect()
    if not connected:
        pytest.skip("Could not connect to Alpaca telescope simulator")
    yield telescope
    telescope.disconnect()


@pytest.fixture
def alpaca_camera() -> Generator[AlpacaCamera, None, None]:
    """Fixture providing connected Alpaca camera."""
    camera = AlpacaCamera(ALPACA_HOST, ALPACA_PORT, CAMERA_DEVICE_NUM)
    connected = camera.connect()
    if not connected:
        pytest.skip("Could not connect to Alpaca camera simulator")
    yield camera
    camera.disconnect()


@pytest.fixture
def alpaca_focuser() -> Generator[AlpacaFocuser, None, None]:
    """Fixture providing connected Alpaca focuser."""
    focuser = AlpacaFocuser(ALPACA_HOST, ALPACA_PORT, FOCUSER_DEVICE_NUM)
    connected = focuser.connect()
    if not connected:
        pytest.skip("Could not connect to Alpaca focuser simulator")
    yield focuser
    focuser.disconnect()


@pytest.fixture
def alpaca_filterwheel() -> Generator[AlpacaFilterWheel, None, None]:
    """Fixture providing connected Alpaca filter wheel."""
    filterwheel = AlpacaFilterWheel(ALPACA_HOST, ALPACA_PORT, FILTERWHEEL_DEVICE_NUM)
    connected = filterwheel.connect()
    if not connected:
        pytest.skip("Could not connect to Alpaca filter wheel simulator")
    yield filterwheel
    filterwheel.disconnect()


# ============================================================================
# Discovery Tests
# ============================================================================

@pytest.mark.alpaca
class TestAlpacaDiscovery:
    """Tests for Alpaca device discovery."""

    def test_discover_devices(self):
        """Test that discovery finds simulator devices."""
        # Note: Discovery uses UDP broadcast which may not work in all environments
        # This test verifies the discovery mechanism itself
        devices = AlpacaDiscovery.discover(timeout=2.0)
        # Discovery may or may not find devices depending on network config
        # The important thing is it doesn't crash
        assert isinstance(devices, list)

    def test_discover_by_type(self):
        """Test discovering devices by type."""
        telescopes = AlpacaDiscovery.discover_by_type("telescope", timeout=2.0)
        assert isinstance(telescopes, list)


# ============================================================================
# Telescope Integration Tests
# ============================================================================

@pytest.mark.alpaca
class TestAlpacaTelescope:
    """Integration tests for Alpaca telescope control."""

    def test_connection(self, alpaca_telescope: AlpacaTelescope):
        """Test telescope connection."""
        assert alpaca_telescope.is_connected

    def test_read_position(self, alpaca_telescope: AlpacaTelescope):
        """Test reading telescope position."""
        ra = alpaca_telescope.ra
        dec = alpaca_telescope.dec

        assert isinstance(ra, float)
        assert isinstance(dec, float)
        assert 0 <= ra <= 24, f"RA {ra} out of range 0-24"
        assert -90 <= dec <= 90, f"Dec {dec} out of range -90 to +90"

    def test_read_altaz(self, alpaca_telescope: AlpacaTelescope):
        """Test reading altitude/azimuth."""
        alt = alpaca_telescope.altitude
        az = alpaca_telescope.azimuth

        assert isinstance(alt, float)
        assert isinstance(az, float)

    def test_tracking_control(self, alpaca_telescope: AlpacaTelescope):
        """Test tracking enable/disable."""
        # Enable tracking
        result = alpaca_telescope.set_tracking(True)
        assert result is True
        assert alpaca_telescope.is_tracking is True

        # Disable tracking
        result = alpaca_telescope.set_tracking(False)
        assert result is True
        assert alpaca_telescope.is_tracking is False

    def test_get_status(self, alpaca_telescope: AlpacaTelescope):
        """Test getting comprehensive status."""
        status = alpaca_telescope.get_status()

        assert "connected" in status
        assert "ra" in status
        assert "dec" in status
        assert "is_tracking" in status
        assert "is_slewing" in status
        assert status["connected"] is True

    @pytest.mark.slow
    def test_slew_to_coordinates(self, alpaca_telescope: AlpacaTelescope):
        """Test slewing to coordinates."""
        target_ra = 12.0   # 12 hours
        target_dec = 45.0  # +45 degrees

        # Unpark if needed
        if alpaca_telescope.is_parked:
            alpaca_telescope.unpark()
            time.sleep(0.5)

        # Initiate slew
        result = alpaca_telescope.slew_to_coordinates(target_ra, target_dec)
        assert result is True

        # Wait for slew to complete (with timeout)
        timeout = 30
        start = time.time()
        while alpaca_telescope.is_slewing and (time.time() - start) < timeout:
            time.sleep(0.5)

        # Verify arrived near target (within 0.1 degrees for simulator)
        assert abs(alpaca_telescope.ra - target_ra) < 0.1
        assert abs(alpaca_telescope.dec - target_dec) < 0.1

    def test_abort_slew(self, alpaca_telescope: AlpacaTelescope):
        """Test aborting a slew."""
        result = alpaca_telescope.abort_slew()
        assert result is True

    def test_sync_coordinates(self, alpaca_telescope: AlpacaTelescope):
        """Test syncing to coordinates."""
        current_ra = alpaca_telescope.ra
        current_dec = alpaca_telescope.dec

        # Sync to same position (should work)
        result = alpaca_telescope.sync(current_ra, current_dec)
        assert result is True


# ============================================================================
# Camera Integration Tests
# ============================================================================

@pytest.mark.alpaca
class TestAlpacaCamera:
    """Integration tests for Alpaca camera control."""

    def test_connection(self, alpaca_camera: AlpacaCamera):
        """Test camera connection."""
        assert alpaca_camera.is_connected

    def test_read_camera_info(self, alpaca_camera: AlpacaCamera):
        """Test reading camera information."""
        info = alpaca_camera.get_camera_info()

        assert "sensor_width" in info
        assert "sensor_height" in info
        assert info["sensor_width"] > 0
        assert info["sensor_height"] > 0

    def test_binning_control(self, alpaca_camera: AlpacaCamera):
        """Test setting binning mode."""
        # Set 2x2 binning
        result = alpaca_camera.set_binning(2, 2)
        assert result is True

        # Verify binning was set
        bin_x, bin_y = alpaca_camera.get_binning()
        assert bin_x == 2
        assert bin_y == 2

        # Reset to 1x1
        alpaca_camera.set_binning(1, 1)

    def test_cooler_info(self, alpaca_camera: AlpacaCamera):
        """Test reading cooler information."""
        temp = alpaca_camera.sensor_temperature
        assert isinstance(temp, float)

    @pytest.mark.slow
    def test_short_exposure(self, alpaca_camera: AlpacaCamera):
        """Test taking a short exposure."""
        # Start 1 second exposure
        result = alpaca_camera.start_exposure(1.0, light=True)
        assert result is True

        # Wait for exposure to complete
        timeout = 10
        start = time.time()
        while not alpaca_camera.is_image_ready and (time.time() - start) < timeout:
            time.sleep(0.2)

        # Check image is ready
        assert alpaca_camera.is_image_ready


# ============================================================================
# Focuser Integration Tests
# ============================================================================

@pytest.mark.alpaca
class TestAlpacaFocuser:
    """Integration tests for Alpaca focuser control."""

    def test_connection(self, alpaca_focuser: AlpacaFocuser):
        """Test focuser connection."""
        assert alpaca_focuser.is_connected

    def test_read_position(self, alpaca_focuser: AlpacaFocuser):
        """Test reading focuser position."""
        position = alpaca_focuser.position
        assert isinstance(position, int)
        assert position >= 0

    def test_read_max_step(self, alpaca_focuser: AlpacaFocuser):
        """Test reading maximum step value."""
        max_step = alpaca_focuser.max_step
        assert isinstance(max_step, int)
        assert max_step > 0

    @pytest.mark.slow
    def test_move_absolute(self, alpaca_focuser: AlpacaFocuser):
        """Test moving to absolute position."""
        max_step = alpaca_focuser.max_step
        target = max_step // 2  # Move to middle position

        result = alpaca_focuser.move_absolute(target)
        assert result is True

        # Wait for movement to complete
        timeout = 30
        start = time.time()
        while alpaca_focuser.is_moving and (time.time() - start) < timeout:
            time.sleep(0.2)

        # Verify arrived at target
        assert abs(alpaca_focuser.position - target) < 10

    def test_halt(self, alpaca_focuser: AlpacaFocuser):
        """Test halting focuser movement."""
        result = alpaca_focuser.halt()
        assert result is True


# ============================================================================
# Filter Wheel Integration Tests
# ============================================================================

@pytest.mark.alpaca
class TestAlpacaFilterWheel:
    """Integration tests for Alpaca filter wheel control."""

    def test_connection(self, alpaca_filterwheel: AlpacaFilterWheel):
        """Test filter wheel connection."""
        assert alpaca_filterwheel.is_connected

    def test_read_filter_names(self, alpaca_filterwheel: AlpacaFilterWheel):
        """Test reading filter names."""
        names = alpaca_filterwheel.filter_names
        assert isinstance(names, list)
        assert len(names) > 0

    def test_read_current_position(self, alpaca_filterwheel: AlpacaFilterWheel):
        """Test reading current filter position."""
        position = alpaca_filterwheel.position
        assert isinstance(position, int)
        assert position >= 0

    @pytest.mark.slow
    def test_set_filter_by_position(self, alpaca_filterwheel: AlpacaFilterWheel):
        """Test changing filter by position."""
        # Move to filter position 1
        result = alpaca_filterwheel.set_position(1)
        assert result is True

        # Wait for movement
        timeout = 10
        start = time.time()
        while alpaca_filterwheel.position == -1 and (time.time() - start) < timeout:
            time.sleep(0.2)

        # Verify position changed
        assert alpaca_filterwheel.position == 1

    def test_set_filter_by_name(self, alpaca_filterwheel: AlpacaFilterWheel):
        """Test changing filter by name."""
        names = alpaca_filterwheel.filter_names
        if len(names) > 0:
            result = alpaca_filterwheel.set_filter_by_name(names[0])
            assert result is True


# ============================================================================
# End-to-End Workflow Tests
# ============================================================================

@pytest.mark.alpaca
@pytest.mark.slow
class TestImagingWorkflow:
    """End-to-end tests simulating imaging workflows."""

    def test_basic_imaging_sequence(
        self,
        alpaca_telescope: AlpacaTelescope,
        alpaca_camera: AlpacaCamera,
        alpaca_focuser: AlpacaFocuser,
    ):
        """Test basic imaging sequence: slew, focus, capture."""
        # 1. Slew to target
        if alpaca_telescope.is_parked:
            alpaca_telescope.unpark()
            time.sleep(0.5)

        alpaca_telescope.set_tracking(True)
        alpaca_telescope.slew_to_coordinates(6.0, 22.0)  # Orion region

        # Wait for slew
        timeout = 30
        start = time.time()
        while alpaca_telescope.is_slewing and (time.time() - start) < timeout:
            time.sleep(0.5)

        assert not alpaca_telescope.is_slewing

        # 2. Move focuser to known position
        target_focus = alpaca_focuser.max_step // 2
        alpaca_focuser.move_absolute(target_focus)

        # Wait for focus movement
        start = time.time()
        while alpaca_focuser.is_moving and (time.time() - start) < 30:
            time.sleep(0.2)

        # 3. Take short exposure
        alpaca_camera.set_binning(1, 1)
        alpaca_camera.start_exposure(0.5, light=True)

        # Wait for exposure
        start = time.time()
        while not alpaca_camera.is_image_ready and (time.time() - start) < 10:
            time.sleep(0.2)

        assert alpaca_camera.is_image_ready

        # 4. Stop tracking and verify
        alpaca_telescope.set_tracking(False)
        assert not alpaca_telescope.is_tracking


# ============================================================================
# Run Configuration
# ============================================================================

if __name__ == "__main__":
    # Run with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
