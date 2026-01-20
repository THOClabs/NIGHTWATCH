"""
NIGHTWATCH PHD2 Client Unit Tests

Step 199: Write unit tests for PHD2 client
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from services.guiding.phd2_client import (
    PHD2Client,
    GuideState,
    GuideStats,
    CalibrationData,
    GuideStar,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Create a PHD2 client instance."""
    return PHD2Client()


@pytest.fixture
def custom_client():
    """Create a PHD2 client with custom settings."""
    return PHD2Client(host="192.168.1.100", port=4401)


@pytest.fixture
def guide_stats():
    """Create sample guide statistics."""
    return GuideStats(
        timestamp=datetime.now(),
        state=GuideState.GUIDING,
        rms_total=0.8,
        rms_ra=0.5,
        rms_dec=0.6,
        peak_ra=1.2,
        peak_dec=1.0,
        snr=25.0,
        star_mass=5000.0,
        frame_number=100,
    )


@pytest.fixture
def calibration_data():
    """Create sample calibration data."""
    return CalibrationData(
        timestamp=datetime.now(),
        ra_rate=10.5,
        dec_rate=10.2,
        ra_angle=0.0,
        dec_angle=90.0,
        orthogonality=0.5,
        valid=True,
    )


# ============================================================================
# GuideState Enum Tests
# ============================================================================

class TestGuideState:
    """Tests for GuideState enum."""

    def test_all_states_defined(self):
        """Verify all guide states are defined."""
        assert GuideState.STOPPED.value == "Stopped"
        assert GuideState.SELECTED.value == "Selected"
        assert GuideState.CALIBRATING.value == "Calibrating"
        assert GuideState.GUIDING.value == "Guiding"
        assert GuideState.LOST_LOCK.value == "LostLock"
        assert GuideState.PAUSED.value == "Paused"
        assert GuideState.LOOPING.value == "Looping"


# ============================================================================
# GuideStats Tests
# ============================================================================

class TestGuideStats:
    """Tests for GuideStats dataclass."""

    def test_guide_stats_creation(self, guide_stats):
        """Verify GuideStats can be created."""
        assert guide_stats.state == GuideState.GUIDING
        assert guide_stats.rms_total == 0.8
        assert guide_stats.rms_ra == 0.5
        assert guide_stats.rms_dec == 0.6
        assert guide_stats.snr == 25.0

    def test_guide_stats_all_fields(self):
        """Verify all GuideStats fields."""
        stats = GuideStats(
            timestamp=datetime.now(),
            state=GuideState.STOPPED,
            rms_total=0.0,
            rms_ra=0.0,
            rms_dec=0.0,
            peak_ra=0.0,
            peak_dec=0.0,
            snr=0.0,
            star_mass=0.0,
            frame_number=0,
        )
        assert stats.frame_number == 0
        assert stats.peak_ra == 0.0


# ============================================================================
# CalibrationData Tests
# ============================================================================

class TestCalibrationData:
    """Tests for CalibrationData dataclass."""

    def test_calibration_data_creation(self, calibration_data):
        """Verify CalibrationData can be created."""
        assert calibration_data.ra_rate == 10.5
        assert calibration_data.dec_rate == 10.2
        assert calibration_data.orthogonality == 0.5
        assert calibration_data.valid is True

    def test_calibration_default_valid(self):
        """Verify default valid is True."""
        cal = CalibrationData(
            timestamp=datetime.now(),
            ra_rate=10.0,
            dec_rate=10.0,
            ra_angle=0.0,
            dec_angle=90.0,
            orthogonality=0.0,
        )
        assert cal.valid is True


# ============================================================================
# GuideStar Tests
# ============================================================================

class TestGuideStar:
    """Tests for GuideStar dataclass."""

    def test_guide_star_creation(self):
        """Verify GuideStar can be created."""
        star = GuideStar(x=512.5, y=384.2, snr=30.0)
        assert star.x == 512.5
        assert star.y == 384.2
        assert star.snr == 30.0


# ============================================================================
# PHD2Client Initialization Tests
# ============================================================================

class TestPHD2ClientInit:
    """Tests for PHD2Client initialization."""

    def test_default_initialization(self, client):
        """Verify client initializes with defaults."""
        assert client.host == "localhost"
        assert client.port == 4400
        assert client.connected is False
        assert client.state == GuideState.STOPPED
        assert client.last_stats is None

    def test_custom_initialization(self, custom_client):
        """Verify client initializes with custom settings."""
        assert custom_client.host == "192.168.1.100"
        assert custom_client.port == 4401

    def test_default_constants(self):
        """Verify default constants."""
        assert PHD2Client.DEFAULT_HOST == "localhost"
        assert PHD2Client.DEFAULT_PORT == 4400


# ============================================================================
# PHD2Client Properties Tests
# ============================================================================

class TestPHD2ClientProperties:
    """Tests for PHD2Client properties."""

    def test_connected_property(self, client):
        """Verify connected property."""
        assert client.connected is False
        client._connected = True
        assert client.connected is True

    def test_state_property(self, client):
        """Verify state property."""
        assert client.state == GuideState.STOPPED
        client._state = GuideState.GUIDING
        assert client.state == GuideState.GUIDING

    def test_last_stats_property(self, client, guide_stats):
        """Verify last_stats property."""
        assert client.last_stats is None
        client._last_stats = guide_stats
        assert client.last_stats is not None
        assert client.last_stats.rms_total == 0.8


# ============================================================================
# PHD2Client Method Tests
# ============================================================================

class TestPHD2ClientMethods:
    """Tests for PHD2Client methods."""

    def test_has_connect_method(self, client):
        """Verify client has connect method."""
        assert hasattr(client, 'connect')
        assert callable(client.connect)

    def test_has_disconnect_method(self, client):
        """Verify client has disconnect method."""
        assert hasattr(client, 'disconnect')
        assert callable(client.disconnect)

    def test_has_start_guiding_method(self, client):
        """Verify client has start_guiding method."""
        assert hasattr(client, 'start_guiding')
        assert callable(client.start_guiding)

    def test_has_stop_guiding_method(self, client):
        """Verify client has stop_guiding method."""
        assert hasattr(client, 'stop_guiding')
        assert callable(client.stop_guiding)

    def test_has_get_guide_stats_method(self, client):
        """Verify client has get_guide_stats method."""
        assert hasattr(client, 'get_guide_stats')
        assert callable(client.get_guide_stats)

    def test_has_dither_method(self, client):
        """Verify client has dither method."""
        assert hasattr(client, 'dither')
        assert callable(client.dither)


# ============================================================================
# Run Configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
