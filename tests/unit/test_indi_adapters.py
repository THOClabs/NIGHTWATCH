"""
NIGHTWATCH Unit Tests - INDI Device Adapters

Unit tests for services/indi/device_adapters.py.
Uses mocking to test adapter logic without requiring pyindi-client or INDI server.

Run:
    pytest tests/unit/test_indi_adapters.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from enum import Enum


# =============================================================================
# Mock INDI types for testing without pyindi-client
# =============================================================================

class PropertyState(Enum):
    """Mock INDI property states."""
    IDLE = "Idle"
    OK = "Ok"
    BUSY = "Busy"
    ALERT = "Alert"


@dataclass
class MockINDIProperty:
    """Mock INDI property for testing."""
    name: str
    device: str
    type: str
    values: dict
    state: PropertyState = PropertyState.OK


# =============================================================================
# Mock Client Setup
# =============================================================================

@pytest.fixture
def mock_indi_client():
    """Create a mock INDI client for testing adapters."""
    client = Mock()
    client._devices = {
        "Filter Simulator": Mock(),
        "Focuser Simulator": Mock(),
        "CCD Simulator": Mock(),
        "Telescope Simulator": Mock(),
    }
    return client


# =============================================================================
# Filter Wheel Adapter Tests
# =============================================================================

class TestINDIFilterWheel:
    """Unit tests for INDIFilterWheel adapter."""

    @pytest.fixture
    def filter_wheel(self, mock_indi_client):
        """Create INDIFilterWheel with mock client."""
        # Patch the module import to avoid pyindi dependency
        with patch.dict('sys.modules', {'PyIndi': Mock()}):
            # Import with mocked dependencies
            import sys

            # Create mock indi_client module
            mock_indi_module = Mock()
            mock_indi_module.NightwatchINDIClient = Mock
            mock_indi_module.INDIProperty = MockINDIProperty
            mock_indi_module.PropertyState = PropertyState

            sys.modules['services.indi.indi_client'] = mock_indi_module

            # Now import the device adapters
            from services.indi.device_adapters import INDIFilterWheel

            wheel = INDIFilterWheel(
                mock_indi_client,
                "Filter Simulator",
                filter_names=["L", "R", "G", "B", "Ha", "OIII", "SII"]
            )
            return wheel

    def test_initialization(self, filter_wheel, mock_indi_client):
        """Test filter wheel adapter initialization."""
        assert filter_wheel.device == "Filter Simulator"
        assert filter_wheel.client == mock_indi_client
        assert len(filter_wheel._filter_names) == 7

    def test_set_filter_by_position(self, filter_wheel, mock_indi_client):
        """Test setting filter by position number."""
        mock_indi_client.set_number.return_value = True

        result = filter_wheel.set_filter(3)

        assert result is True
        mock_indi_client.set_number.assert_called_once_with(
            "Filter Simulator",
            "FILTER_SLOT",
            {"FILTER_SLOT_VALUE": 3.0}
        )

    def test_set_filter_by_name(self, filter_wheel, mock_indi_client):
        """Test setting filter by name."""
        mock_indi_client.set_number.return_value = True
        # Mock get_property to return empty so it uses configured names
        mock_indi_client.get_property.return_value = None

        result = filter_wheel.set_filter_by_name("Ha")

        assert result is True
        # Ha is at position 5 (index 4 + 1)
        mock_indi_client.set_number.assert_called_once_with(
            "Filter Simulator",
            "FILTER_SLOT",
            {"FILTER_SLOT_VALUE": 5.0}
        )

    def test_set_filter_by_name_case_insensitive(self, filter_wheel, mock_indi_client):
        """Test filter name lookup is case-insensitive."""
        mock_indi_client.set_number.return_value = True
        mock_indi_client.get_property.return_value = None

        result = filter_wheel.set_filter_by_name("ha")  # lowercase

        assert result is True

    def test_set_filter_by_name_not_found(self, filter_wheel, mock_indi_client):
        """Test setting filter with unknown name."""
        mock_indi_client.get_property.return_value = None

        result = filter_wheel.set_filter_by_name("Unknown")

        assert result is False

    def test_get_filter_position(self, filter_wheel, mock_indi_client):
        """Test getting current filter position."""
        mock_prop = MockINDIProperty(
            name="FILTER_SLOT",
            device="Filter Simulator",
            type="number",
            values={"FILTER_SLOT_VALUE": 3}
        )
        mock_indi_client.get_property.return_value = mock_prop

        position = filter_wheel.get_filter()

        assert position == 3

    def test_get_filter_position_unavailable(self, filter_wheel, mock_indi_client):
        """Test getting filter position when unavailable."""
        mock_indi_client.get_property.return_value = None

        position = filter_wheel.get_filter()

        assert position is None

    def test_get_filter_name(self, filter_wheel, mock_indi_client):
        """Test getting current filter name."""
        # Need to mock different return values for different property requests
        def mock_get_property(device, prop_name):
            if prop_name == "FILTER_SLOT":
                return MockINDIProperty(
                    name="FILTER_SLOT",
                    device="Filter Simulator",
                    type="number",
                    values={"FILTER_SLOT_VALUE": 5}
                )
            elif prop_name == "FILTER_NAME":
                # Return None so it falls back to configured names
                return None
            return None

        mock_indi_client.get_property.side_effect = mock_get_property

        name = filter_wheel.get_filter_name()

        assert name == "Ha"

    def test_get_filter_names_from_config(self, filter_wheel, mock_indi_client):
        """Test getting filter names from configuration."""
        mock_indi_client.get_property.return_value = None

        names = filter_wheel.get_filter_names()

        assert names == ["L", "R", "G", "B", "Ha", "OIII", "SII"]

    def test_get_filter_count(self, filter_wheel, mock_indi_client):
        """Test getting filter count."""
        mock_indi_client.get_property.return_value = None

        count = filter_wheel.get_filter_count()

        assert count == 7

    def test_is_moving(self, filter_wheel, mock_indi_client):
        """Test checking if filter wheel is moving."""
        mock_prop = MockINDIProperty(
            name="FILTER_SLOT",
            device="Filter Simulator",
            type="number",
            values={"FILTER_SLOT_VALUE": 3},
            state=PropertyState.BUSY
        )
        mock_indi_client.get_property.return_value = mock_prop

        assert filter_wheel.is_moving() is True

    def test_is_not_moving(self, filter_wheel, mock_indi_client):
        """Test checking when filter wheel is idle."""
        mock_prop = MockINDIProperty(
            name="FILTER_SLOT",
            device="Filter Simulator",
            type="number",
            values={"FILTER_SLOT_VALUE": 3},
            state=PropertyState.OK
        )
        mock_indi_client.get_property.return_value = mock_prop

        assert filter_wheel.is_moving() is False

    def test_filter_offset_management(self, filter_wheel):
        """Test focus offset management for filters."""
        filter_wheel.set_filter_offset("Ha", 150.0)
        filter_wheel.set_filter_offset("OIII", 120.0)

        assert filter_wheel.get_filter_offset("Ha") == 150.0
        assert filter_wheel.get_filter_offset("OIII") == 120.0
        assert filter_wheel.get_filter_offset("Unknown") == 0.0


# =============================================================================
# Focuser Adapter Tests
# =============================================================================

class TestINDIFocuser:
    """Unit tests for INDIFocuser adapter."""

    @pytest.fixture
    def focuser(self, mock_indi_client):
        """Create INDIFocuser with mock client."""
        with patch.dict('sys.modules', {'PyIndi': Mock()}):
            import sys

            mock_indi_module = Mock()
            mock_indi_module.NightwatchINDIClient = Mock
            mock_indi_module.INDIProperty = MockINDIProperty
            mock_indi_module.PropertyState = PropertyState

            sys.modules['services.indi.indi_client'] = mock_indi_module

            from services.indi.device_adapters import INDIFocuser

            return INDIFocuser(mock_indi_client, "Focuser Simulator")

    def test_initialization(self, focuser, mock_indi_client):
        """Test focuser adapter initialization."""
        assert focuser.device == "Focuser Simulator"
        assert focuser.client == mock_indi_client

    def test_move_absolute(self, focuser, mock_indi_client):
        """Test moving to absolute position."""
        mock_indi_client.set_number.return_value = True

        result = focuser.move_absolute(5000)

        assert result is True
        mock_indi_client.set_number.assert_called_once_with(
            "Focuser Simulator",
            "ABS_FOCUS_POSITION",
            {"FOCUS_ABSOLUTE_POSITION": 5000.0}
        )

    def test_move_relative_outward(self, focuser, mock_indi_client):
        """Test moving relative steps outward."""
        mock_indi_client.set_switch.return_value = True
        mock_indi_client.set_number.return_value = True

        result = focuser.move_relative(100)

        assert result is True
        mock_indi_client.set_switch.assert_called_with(
            "Focuser Simulator",
            "FOCUS_MOTION",
            "FOCUS_OUTWARD"
        )
        mock_indi_client.set_number.assert_called_with(
            "Focuser Simulator",
            "REL_FOCUS_POSITION",
            {"FOCUS_RELATIVE_POSITION": 100.0}
        )

    def test_move_relative_inward(self, focuser, mock_indi_client):
        """Test moving relative steps inward."""
        mock_indi_client.set_switch.return_value = True
        mock_indi_client.set_number.return_value = True

        result = focuser.move_relative(-100)

        assert result is True
        mock_indi_client.set_switch.assert_called_with(
            "Focuser Simulator",
            "FOCUS_MOTION",
            "FOCUS_INWARD"
        )

    def test_abort(self, focuser, mock_indi_client):
        """Test aborting focuser movement."""
        mock_indi_client.set_switch.return_value = True

        result = focuser.abort()

        assert result is True
        mock_indi_client.set_switch.assert_called_once_with(
            "Focuser Simulator",
            "FOCUS_ABORT",
            "ABORT"
        )

    def test_get_position(self, focuser, mock_indi_client):
        """Test getting current position."""
        mock_prop = MockINDIProperty(
            name="ABS_FOCUS_POSITION",
            device="Focuser Simulator",
            type="number",
            values={"FOCUS_ABSOLUTE_POSITION": 5000}
        )
        mock_indi_client.get_property.return_value = mock_prop

        position = focuser.get_position()

        assert position == 5000

    def test_get_position_unavailable(self, focuser, mock_indi_client):
        """Test getting position when unavailable."""
        mock_indi_client.get_property.return_value = None

        position = focuser.get_position()

        assert position is None

    def test_is_moving(self, focuser, mock_indi_client):
        """Test checking if focuser is moving."""
        mock_prop = MockINDIProperty(
            name="ABS_FOCUS_POSITION",
            device="Focuser Simulator",
            type="number",
            values={"FOCUS_ABSOLUTE_POSITION": 5000},
            state=PropertyState.BUSY
        )
        mock_indi_client.get_property.return_value = mock_prop

        assert focuser.is_moving() is True

    def test_get_temperature(self, focuser, mock_indi_client):
        """Test getting focuser temperature."""
        mock_prop = MockINDIProperty(
            name="FOCUS_TEMPERATURE",
            device="Focuser Simulator",
            type="number",
            values={"TEMPERATURE": -5.5}
        )
        mock_indi_client.get_property.return_value = mock_prop

        temp = focuser.get_temperature()

        assert temp == -5.5

    def test_get_max_position(self, focuser, mock_indi_client):
        """Test getting maximum position."""
        mock_prop = MockINDIProperty(
            name="FOCUS_MAX",
            device="Focuser Simulator",
            type="number",
            values={"FOCUS_MAX_VALUE": 50000}
        )
        mock_indi_client.get_property.return_value = mock_prop

        max_pos = focuser.get_max_position()

        assert max_pos == 50000

    def test_get_max_position_default(self, focuser, mock_indi_client):
        """Test getting default maximum position."""
        mock_indi_client.get_property.return_value = None

        max_pos = focuser.get_max_position()

        assert max_pos == 100000

    def test_set_temp_compensation_enable(self, focuser, mock_indi_client):
        """Test enabling temperature compensation."""
        mock_indi_client.set_switch.return_value = True

        result = focuser.set_temp_compensation(True)

        assert result is True
        mock_indi_client.set_switch.assert_called_once_with(
            "Focuser Simulator",
            "FOCUS_TEMPERATURE_COMPENSATION",
            "ENABLE"
        )

    def test_set_temp_compensation_disable(self, focuser, mock_indi_client):
        """Test disabling temperature compensation."""
        mock_indi_client.set_switch.return_value = True

        result = focuser.set_temp_compensation(False)

        assert result is True
        mock_indi_client.set_switch.assert_called_once_with(
            "Focuser Simulator",
            "FOCUS_TEMPERATURE_COMPENSATION",
            "DISABLE"
        )

    def test_get_status(self, focuser, mock_indi_client):
        """Test getting comprehensive focuser status."""
        def mock_get_property(device, prop_name):
            props = {
                "ABS_FOCUS_POSITION": MockINDIProperty(
                    name=prop_name, device=device, type="number",
                    values={"FOCUS_ABSOLUTE_POSITION": 5000},
                    state=PropertyState.OK
                ),
                "FOCUS_MAX": MockINDIProperty(
                    name=prop_name, device=device, type="number",
                    values={"FOCUS_MAX_VALUE": 50000}
                ),
                "FOCUS_TEMPERATURE": MockINDIProperty(
                    name=prop_name, device=device, type="number",
                    values={"TEMPERATURE": -5.5}
                ),
                "FOCUS_TEMPERATURE_COMPENSATION": MockINDIProperty(
                    name=prop_name, device=device, type="switch",
                    values={"ENABLE": True}
                ),
            }
            return props.get(prop_name)

        mock_indi_client.get_property.side_effect = mock_get_property

        status = focuser.get_status()

        assert status.position == 5000
        assert status.is_moving is False
        assert status.temperature == -5.5
        assert status.temp_compensation is True
        assert status.max_position == 50000


# =============================================================================
# Camera Adapter Tests
# =============================================================================

class TestINDICamera:
    """Unit tests for INDICamera adapter."""

    @pytest.fixture
    def camera(self, mock_indi_client):
        """Create INDICamera with mock client."""
        with patch.dict('sys.modules', {'PyIndi': Mock()}):
            import sys

            mock_indi_module = Mock()
            mock_indi_module.NightwatchINDIClient = Mock
            mock_indi_module.INDIProperty = MockINDIProperty
            mock_indi_module.PropertyState = PropertyState

            sys.modules['services.indi.indi_client'] = mock_indi_module

            from services.indi.device_adapters import INDICamera

            return INDICamera(mock_indi_client, "CCD Simulator")

    def test_initialization(self, camera, mock_indi_client):
        """Test camera adapter initialization."""
        assert camera.device == "CCD Simulator"
        assert camera.client == mock_indi_client

    def test_set_exposure(self, camera, mock_indi_client):
        """Test starting an exposure."""
        mock_indi_client.set_number.return_value = True

        result = camera.set_exposure(10.0)

        assert result is True
        mock_indi_client.set_number.assert_called_once_with(
            "CCD Simulator",
            "CCD_EXPOSURE",
            {"CCD_EXPOSURE_VALUE": 10.0}
        )

    def test_abort_exposure(self, camera, mock_indi_client):
        """Test aborting an exposure."""
        mock_indi_client.set_switch.return_value = True

        result = camera.abort_exposure()

        assert result is True
        mock_indi_client.set_switch.assert_called_once_with(
            "CCD Simulator",
            "CCD_ABORT_EXPOSURE",
            "ABORT"
        )

    def test_is_exposing(self, camera, mock_indi_client):
        """Test checking if camera is exposing."""
        mock_prop = MockINDIProperty(
            name="CCD_EXPOSURE",
            device="CCD Simulator",
            type="number",
            values={"CCD_EXPOSURE_VALUE": 5.0},
            state=PropertyState.BUSY
        )
        mock_indi_client.get_property.return_value = mock_prop

        assert camera.is_exposing() is True

    def test_get_exposure_remaining(self, camera, mock_indi_client):
        """Test getting remaining exposure time."""
        mock_prop = MockINDIProperty(
            name="CCD_EXPOSURE",
            device="CCD Simulator",
            type="number",
            values={"CCD_EXPOSURE_VALUE": 5.0}
        )
        mock_indi_client.get_property.return_value = mock_prop

        remaining = camera.get_exposure_remaining()

        assert remaining == 5.0

    def test_set_binning(self, camera, mock_indi_client):
        """Test setting camera binning."""
        mock_indi_client.set_number.return_value = True

        result = camera.set_binning(2, 2)

        assert result is True
        mock_indi_client.set_number.assert_called_once_with(
            "CCD Simulator",
            "CCD_BINNING",
            {"HOR_BIN": 2.0, "VER_BIN": 2.0}
        )

    def test_set_binning_single_value(self, camera, mock_indi_client):
        """Test setting binning with single value."""
        mock_indi_client.set_number.return_value = True

        result = camera.set_binning(2)

        assert result is True
        mock_indi_client.set_number.assert_called_once_with(
            "CCD Simulator",
            "CCD_BINNING",
            {"HOR_BIN": 2.0, "VER_BIN": 2.0}
        )

    def test_get_binning(self, camera, mock_indi_client):
        """Test getting current binning."""
        mock_prop = MockINDIProperty(
            name="CCD_BINNING",
            device="CCD Simulator",
            type="number",
            values={"HOR_BIN": 2, "VER_BIN": 2}
        )
        mock_indi_client.get_property.return_value = mock_prop

        bin_x, bin_y = camera.get_binning()

        assert bin_x == 2
        assert bin_y == 2

    def test_get_binning_default(self, camera, mock_indi_client):
        """Test getting default binning."""
        mock_indi_client.get_property.return_value = None

        bin_x, bin_y = camera.get_binning()

        assert bin_x == 1
        assert bin_y == 1

    def test_set_temperature(self, camera, mock_indi_client):
        """Test setting target temperature."""
        mock_indi_client.set_number.return_value = True

        result = camera.set_temperature(-20.0)

        assert result is True
        mock_indi_client.set_number.assert_called_once_with(
            "CCD Simulator",
            "CCD_TEMPERATURE",
            {"CCD_TEMPERATURE_VALUE": -20.0}
        )

    def test_get_temperature(self, camera, mock_indi_client):
        """Test getting current temperature."""
        mock_prop = MockINDIProperty(
            name="CCD_TEMPERATURE",
            device="CCD Simulator",
            type="number",
            values={"CCD_TEMPERATURE_VALUE": -15.5}
        )
        mock_indi_client.get_property.return_value = mock_prop

        temp = camera.get_temperature()

        assert temp == -15.5

    def test_set_cooler(self, camera, mock_indi_client):
        """Test enabling cooler."""
        mock_indi_client.set_switch.return_value = True

        result = camera.set_cooler(True)

        assert result is True
        mock_indi_client.set_switch.assert_called_once_with(
            "CCD Simulator",
            "CCD_COOLER",
            "COOLER_ON"
        )

    def test_get_info(self, camera, mock_indi_client):
        """Test getting CCD information."""
        mock_prop = MockINDIProperty(
            name="CCD_INFO",
            device="CCD Simulator",
            type="number",
            values={
                "CCD_MAX_X": 4656,
                "CCD_MAX_Y": 3520,
                "CCD_PIXEL_SIZE_X": 3.8,
                "CCD_PIXEL_SIZE_Y": 3.8,
                "CCD_BITSPERPIXEL": 16,
                "CCD_MAX_BIN_X": 4,
                "CCD_MAX_BIN_Y": 4,
            }
        )
        mock_indi_client.get_property.return_value = mock_prop

        info = camera.get_info()

        assert info.width == 4656
        assert info.height == 3520
        assert info.pixel_size_x == 3.8
        assert info.pixel_size_y == 3.8
        assert info.bits_per_pixel == 16
        assert info.max_bin_x == 4
        assert info.max_bin_y == 4


# =============================================================================
# Telescope Adapter Tests
# =============================================================================

class TestINDITelescope:
    """Unit tests for INDITelescope adapter."""

    @pytest.fixture
    def telescope(self, mock_indi_client):
        """Create INDITelescope with mock client."""
        with patch.dict('sys.modules', {'PyIndi': Mock()}):
            import sys

            mock_indi_module = Mock()
            mock_indi_module.NightwatchINDIClient = Mock
            mock_indi_module.INDIProperty = MockINDIProperty
            mock_indi_module.PropertyState = PropertyState

            sys.modules['services.indi.indi_client'] = mock_indi_module

            from services.indi.device_adapters import INDITelescope

            return INDITelescope(mock_indi_client, "Telescope Simulator")

    def test_initialization(self, telescope, mock_indi_client):
        """Test telescope adapter initialization."""
        assert telescope.device == "Telescope Simulator"
        assert telescope.client == mock_indi_client

    def test_goto(self, telescope, mock_indi_client):
        """Test slewing to coordinates."""
        mock_indi_client.set_number.return_value = True

        result = telescope.goto(12.5, 45.0)

        assert result is True
        mock_indi_client.set_number.assert_called_once_with(
            "Telescope Simulator",
            "EQUATORIAL_EOD_COORD",
            {"RA": 12.5, "DEC": 45.0}
        )

    def test_sync(self, telescope, mock_indi_client):
        """Test syncing to coordinates."""
        mock_indi_client.set_switch.return_value = True
        mock_indi_client.set_number.return_value = True

        result = telescope.sync(12.5, 45.0)

        assert result is True
        # Should set to SYNC mode, sync, then back to SLEW
        calls = mock_indi_client.set_switch.call_args_list
        assert calls[0] == (("Telescope Simulator", "ON_COORD_SET", "SYNC"),)
        assert calls[1] == (("Telescope Simulator", "ON_COORD_SET", "SLEW"),)

    def test_abort(self, telescope, mock_indi_client):
        """Test aborting motion."""
        mock_indi_client.set_switch.return_value = True

        result = telescope.abort()

        assert result is True
        mock_indi_client.set_switch.assert_called_once_with(
            "Telescope Simulator",
            "TELESCOPE_ABORT_MOTION",
            "ABORT"
        )

    def test_get_coordinates(self, telescope, mock_indi_client):
        """Test getting current coordinates."""
        mock_prop = MockINDIProperty(
            name="EQUATORIAL_EOD_COORD",
            device="Telescope Simulator",
            type="number",
            values={"RA": 12.5, "DEC": 45.0}
        )
        mock_indi_client.get_property.return_value = mock_prop

        coords = telescope.get_coordinates()

        assert coords == (12.5, 45.0)

    def test_get_coordinates_unavailable(self, telescope, mock_indi_client):
        """Test getting coordinates when unavailable."""
        mock_indi_client.get_property.return_value = None

        coords = telescope.get_coordinates()

        assert coords is None

    def test_is_slewing(self, telescope, mock_indi_client):
        """Test checking if telescope is slewing."""
        mock_prop = MockINDIProperty(
            name="EQUATORIAL_EOD_COORD",
            device="Telescope Simulator",
            type="number",
            values={"RA": 12.5, "DEC": 45.0},
            state=PropertyState.BUSY
        )
        mock_indi_client.get_property.return_value = mock_prop

        assert telescope.is_slewing() is True

    def test_is_not_slewing(self, telescope, mock_indi_client):
        """Test checking when telescope is not slewing."""
        mock_prop = MockINDIProperty(
            name="EQUATORIAL_EOD_COORD",
            device="Telescope Simulator",
            type="number",
            values={"RA": 12.5, "DEC": 45.0},
            state=PropertyState.OK
        )
        mock_indi_client.get_property.return_value = mock_prop

        assert telescope.is_slewing() is False

    def test_set_tracking_enable(self, telescope, mock_indi_client):
        """Test enabling tracking."""
        mock_indi_client.set_switch.return_value = True

        result = telescope.set_tracking(True)

        assert result is True
        mock_indi_client.set_switch.assert_called_once_with(
            "Telescope Simulator",
            "TELESCOPE_TRACK_STATE",
            "TRACK_ON"
        )

    def test_set_tracking_disable(self, telescope, mock_indi_client):
        """Test disabling tracking."""
        mock_indi_client.set_switch.return_value = True

        result = telescope.set_tracking(False)

        assert result is True
        mock_indi_client.set_switch.assert_called_once_with(
            "Telescope Simulator",
            "TELESCOPE_TRACK_STATE",
            "TRACK_OFF"
        )

    def test_is_tracking(self, telescope, mock_indi_client):
        """Test checking if tracking is enabled."""
        mock_prop = MockINDIProperty(
            name="TELESCOPE_TRACK_STATE",
            device="Telescope Simulator",
            type="switch",
            values={"TRACK_ON": True}
        )
        mock_indi_client.get_property.return_value = mock_prop

        assert telescope.is_tracking() is True

    def test_park(self, telescope, mock_indi_client):
        """Test parking telescope."""
        mock_indi_client.set_switch.return_value = True

        result = telescope.park()

        assert result is True
        mock_indi_client.set_switch.assert_called_once_with(
            "Telescope Simulator",
            "TELESCOPE_PARK",
            "PARK"
        )

    def test_unpark(self, telescope, mock_indi_client):
        """Test unparking telescope."""
        mock_indi_client.set_switch.return_value = True

        result = telescope.unpark()

        assert result is True
        mock_indi_client.set_switch.assert_called_once_with(
            "Telescope Simulator",
            "TELESCOPE_PARK",
            "UNPARK"
        )

    def test_is_parked(self, telescope, mock_indi_client):
        """Test checking if telescope is parked."""
        mock_prop = MockINDIProperty(
            name="TELESCOPE_PARK",
            device="Telescope Simulator",
            type="switch",
            values={"PARK": True}
        )
        mock_indi_client.get_property.return_value = mock_prop

        assert telescope.is_parked() is True


# =============================================================================
# Data Class Tests
# =============================================================================

class TestDataClasses:
    """Tests for adapter data classes."""

    def test_filter_info(self):
        """Test FilterInfo dataclass."""
        with patch.dict('sys.modules', {'PyIndi': Mock()}):
            import sys
            mock_indi_module = Mock()
            mock_indi_module.PropertyState = PropertyState
            sys.modules['services.indi.indi_client'] = mock_indi_module

            from services.indi.device_adapters import FilterInfo

            info = FilterInfo(position=3, name="Ha", offset=150.0)

            assert info.position == 3
            assert info.name == "Ha"
            assert info.offset == 150.0

    def test_filter_info_default_offset(self):
        """Test FilterInfo default offset."""
        with patch.dict('sys.modules', {'PyIndi': Mock()}):
            import sys
            mock_indi_module = Mock()
            mock_indi_module.PropertyState = PropertyState
            sys.modules['services.indi.indi_client'] = mock_indi_module

            from services.indi.device_adapters import FilterInfo

            info = FilterInfo(position=1, name="L")

            assert info.offset == 0.0

    def test_focuser_status(self):
        """Test FocuserStatus dataclass."""
        with patch.dict('sys.modules', {'PyIndi': Mock()}):
            import sys
            mock_indi_module = Mock()
            mock_indi_module.PropertyState = PropertyState
            sys.modules['services.indi.indi_client'] = mock_indi_module

            from services.indi.device_adapters import FocuserStatus

            status = FocuserStatus(
                position=5000,
                is_moving=False,
                temperature=-5.5,
                temp_compensation=True,
                max_position=50000,
                step_size=1.0
            )

            assert status.position == 5000
            assert status.is_moving is False
            assert status.temperature == -5.5
            assert status.temp_compensation is True
            assert status.max_position == 50000

    def test_ccd_info(self):
        """Test CCDInfo dataclass."""
        with patch.dict('sys.modules', {'PyIndi': Mock()}):
            import sys
            mock_indi_module = Mock()
            mock_indi_module.PropertyState = PropertyState
            sys.modules['services.indi.indi_client'] = mock_indi_module

            from services.indi.device_adapters import CCDInfo

            info = CCDInfo(
                width=4656,
                height=3520,
                pixel_size_x=3.8,
                pixel_size_y=3.8,
                bits_per_pixel=16,
                max_bin_x=4,
                max_bin_y=4
            )

            assert info.width == 4656
            assert info.height == 3520
            assert info.pixel_size_x == 3.8


# =============================================================================
# Enum Tests
# =============================================================================

class TestEnums:
    """Tests for adapter enums."""

    def test_ccd_frame_type_values(self):
        """Test CCDFrameType enum values."""
        with patch.dict('sys.modules', {'PyIndi': Mock()}):
            import sys
            mock_indi_module = Mock()
            mock_indi_module.PropertyState = PropertyState
            sys.modules['services.indi.indi_client'] = mock_indi_module

            from services.indi.device_adapters import CCDFrameType

            assert CCDFrameType.LIGHT.value == "FRAME_LIGHT"
            assert CCDFrameType.DARK.value == "FRAME_DARK"
            assert CCDFrameType.FLAT.value == "FRAME_FLAT"
            assert CCDFrameType.BIAS.value == "FRAME_BIAS"

    def test_tracking_mode_values(self):
        """Test TrackingMode enum values."""
        with patch.dict('sys.modules', {'PyIndi': Mock()}):
            import sys
            mock_indi_module = Mock()
            mock_indi_module.PropertyState = PropertyState
            sys.modules['services.indi.indi_client'] = mock_indi_module

            from services.indi.device_adapters import TrackingMode

            assert TrackingMode.SIDEREAL.value == "TRACK_SIDEREAL"
            assert TrackingMode.LUNAR.value == "TRACK_LUNAR"
            assert TrackingMode.SOLAR.value == "TRACK_SOLAR"
            assert TrackingMode.CUSTOM.value == "TRACK_CUSTOM"


# =============================================================================
# Run Configuration
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
