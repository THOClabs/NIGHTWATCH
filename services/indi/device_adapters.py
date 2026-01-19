"""
NIGHTWATCH INDI Device Adapters
High-level adapters for common astronomy devices

This module provides convenient wrappers around raw INDI properties
for controlling common device types: filter wheels, focusers, cameras, etc.

These adapters mirror the functionality of the Alpaca adapters in
services/alpaca/alpaca_client.py for consistent cross-platform control.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Callable
from enum import Enum

from .indi_client import NightwatchINDIClient, INDIProperty, PropertyState

logger = logging.getLogger(__name__)


# =============================================================================
# Filter Wheel Adapter
# =============================================================================

@dataclass
class FilterInfo:
    """Information about a filter."""
    position: int
    name: str
    offset: float = 0.0  # Focus offset for this filter


class INDIFilterWheel:
    """
    INDI filter wheel adapter.

    Provides high-level control for filter wheel devices using standard
    INDI filter wheel properties.

    Common INDI filter wheel devices:
    - "Filter Simulator" (indi_simulator_wheel)
    - "Atik EFW2" (indi_atik_wheel)
    - "ZWO EFW" (indi_asi_wheel)

    Usage:
        client = NightwatchINDIClient()
        client.connect()

        wheel = INDIFilterWheel(client, "Filter Simulator")
        wheel.set_filter(3)  # Move to position 3
        wheel.set_filter_by_name("Ha")  # Move to Ha filter
    """

    # Standard INDI filter wheel properties
    PROP_FILTER_SLOT = "FILTER_SLOT"
    PROP_FILTER_NAME = "FILTER_NAME"

    def __init__(
        self,
        client: NightwatchINDIClient,
        device_name: str,
        filter_names: Optional[List[str]] = None
    ):
        """
        Initialize filter wheel adapter.

        Args:
            client: Connected INDI client
            device_name: INDI device name for the filter wheel
            filter_names: Optional list of filter names (if not provided by device)
        """
        self.client = client
        self.device = device_name
        self._filter_names = filter_names or []
        self._filter_offsets: Dict[str, float] = {}
        self._callbacks: List[Callable[[int], None]] = []

    def set_filter(self, position: int) -> bool:
        """
        Set filter position (1-indexed).

        Args:
            position: Filter position (1 = first filter)

        Returns:
            True if command sent successfully
        """
        result = self.client.set_number(
            self.device,
            self.PROP_FILTER_SLOT,
            {"FILTER_SLOT_VALUE": float(position)}
        )
        if result:
            logger.info(f"Filter wheel moving to position {position}")
        return result

    def set_filter_by_name(self, name: str) -> bool:
        """
        Set filter by name.

        Args:
            name: Filter name (e.g., "L", "R", "G", "B", "Ha", "OIII", "SII")

        Returns:
            True if filter found and command sent
        """
        names = self.get_filter_names()
        try:
            # Case-insensitive search
            for i, filter_name in enumerate(names):
                if filter_name.lower() == name.lower():
                    return self.set_filter(i + 1)

            logger.warning(f"Filter '{name}' not found. Available: {names}")
            return False
        except ValueError:
            logger.warning(f"Filter '{name}' not found in {names}")
            return False

    def get_filter(self) -> Optional[int]:
        """
        Get current filter position.

        Returns:
            Current filter position (1-indexed) or None if unavailable
        """
        prop = self.client.get_property(self.device, self.PROP_FILTER_SLOT)
        if prop and prop.values:
            return int(prop.values.get("FILTER_SLOT_VALUE", 0))
        return None

    def get_filter_name(self) -> Optional[str]:
        """
        Get name of current filter.

        Returns:
            Filter name or None if unavailable
        """
        position = self.get_filter()
        if position is None:
            return None

        names = self.get_filter_names()
        if 0 < position <= len(names):
            return names[position - 1]
        return f"Filter {position}"

    def get_filter_names(self) -> List[str]:
        """
        Get list of filter names.

        Returns:
            List of filter names
        """
        # Try to get names from device
        prop = self.client.get_property(self.device, self.PROP_FILTER_NAME)
        if prop and prop.values:
            # INDI returns filter names as FILTER_SLOT_NAME_1, FILTER_SLOT_NAME_2, etc.
            names = []
            for key in sorted(prop.values.keys()):
                names.append(prop.values[key])
            if names:
                return names

        # Fall back to configured names
        if self._filter_names:
            return self._filter_names

        # Default names
        return ["Filter 1", "Filter 2", "Filter 3", "Filter 4", "Filter 5"]

    def get_filter_count(self) -> int:
        """Get number of filter positions."""
        return len(self.get_filter_names())

    def is_moving(self) -> bool:
        """Check if filter wheel is moving."""
        prop = self.client.get_property(self.device, self.PROP_FILTER_SLOT)
        if prop:
            return prop.state == PropertyState.BUSY
        return False

    def set_filter_offset(self, name: str, offset: float):
        """
        Set focus offset for a filter.

        Args:
            name: Filter name
            offset: Focus offset in steps
        """
        self._filter_offsets[name] = offset

    def get_filter_offset(self, name: Optional[str] = None) -> float:
        """
        Get focus offset for a filter.

        Args:
            name: Filter name (uses current filter if None)

        Returns:
            Focus offset in steps
        """
        if name is None:
            name = self.get_filter_name()
        return self._filter_offsets.get(name, 0.0) if name else 0.0


# =============================================================================
# Focuser Adapter
# =============================================================================

@dataclass
class FocuserStatus:
    """Focuser status information."""
    position: int
    is_moving: bool
    temperature: Optional[float]
    temp_compensation: bool
    max_position: int
    step_size: float  # microns per step


class INDIFocuser:
    """
    INDI focuser adapter.

    Provides high-level control for focuser devices using standard
    INDI focuser properties.

    Common INDI focuser devices:
    - "Focuser Simulator" (indi_simulator_focus)
    - "MoonLite" (indi_moonlite_focus)
    - "ZWO EAF" (indi_asi_focuser)

    Usage:
        client = NightwatchINDIClient()
        client.connect()

        focuser = INDIFocuser(client, "Focuser Simulator")
        focuser.move_absolute(5000)
        focuser.move_relative(100)  # Move out 100 steps
    """

    # Standard INDI focuser properties
    PROP_ABS_POSITION = "ABS_FOCUS_POSITION"
    PROP_REL_POSITION = "REL_FOCUS_POSITION"
    PROP_FOCUS_MOTION = "FOCUS_MOTION"
    PROP_FOCUS_ABORT = "FOCUS_ABORT"
    PROP_FOCUS_MAX = "FOCUS_MAX"
    PROP_FOCUS_TEMPERATURE = "FOCUS_TEMPERATURE"
    PROP_FOCUS_TEMP_COMP = "FOCUS_TEMPERATURE_COMPENSATION"

    def __init__(self, client: NightwatchINDIClient, device_name: str):
        """
        Initialize focuser adapter.

        Args:
            client: Connected INDI client
            device_name: INDI device name for the focuser
        """
        self.client = client
        self.device = device_name
        self._callbacks: List[Callable[[int], None]] = []

    def move_absolute(self, position: int) -> bool:
        """
        Move to absolute position.

        Args:
            position: Target position in steps

        Returns:
            True if command sent successfully
        """
        result = self.client.set_number(
            self.device,
            self.PROP_ABS_POSITION,
            {"FOCUS_ABSOLUTE_POSITION": float(position)}
        )
        if result:
            logger.info(f"Focuser moving to absolute position {position}")
        return result

    def move_relative(self, steps: int) -> bool:
        """
        Move relative steps.

        Args:
            steps: Steps to move (positive=out, negative=in)

        Returns:
            True if command sent successfully
        """
        # Set direction first
        direction = "FOCUS_OUTWARD" if steps > 0 else "FOCUS_INWARD"
        if not self.client.set_switch(self.device, self.PROP_FOCUS_MOTION, direction):
            return False

        # Then set relative movement
        result = self.client.set_number(
            self.device,
            self.PROP_REL_POSITION,
            {"FOCUS_RELATIVE_POSITION": float(abs(steps))}
        )
        if result:
            logger.info(f"Focuser moving {steps} steps {'out' if steps > 0 else 'in'}")
        return result

    def abort(self) -> bool:
        """
        Abort focuser movement.

        Returns:
            True if command sent successfully
        """
        result = self.client.set_switch(self.device, self.PROP_FOCUS_ABORT, "ABORT")
        if result:
            logger.info("Focuser movement aborted")
        return result

    def get_position(self) -> Optional[int]:
        """
        Get current position.

        Returns:
            Current position in steps or None if unavailable
        """
        prop = self.client.get_property(self.device, self.PROP_ABS_POSITION)
        if prop and prop.values:
            return int(prop.values.get("FOCUS_ABSOLUTE_POSITION", 0))
        return None

    def is_moving(self) -> bool:
        """Check if focuser is moving."""
        prop = self.client.get_property(self.device, self.PROP_ABS_POSITION)
        if prop:
            return prop.state == PropertyState.BUSY
        return False

    def get_temperature(self) -> Optional[float]:
        """
        Get focuser temperature.

        Returns:
            Temperature in Celsius or None if not available
        """
        prop = self.client.get_property(self.device, self.PROP_FOCUS_TEMPERATURE)
        if prop and prop.values:
            return prop.values.get("TEMPERATURE", None)
        return None

    def get_max_position(self) -> int:
        """Get maximum focuser position."""
        prop = self.client.get_property(self.device, self.PROP_FOCUS_MAX)
        if prop and prop.values:
            return int(prop.values.get("FOCUS_MAX_VALUE", 100000))
        return 100000  # Default max

    def set_temp_compensation(self, enabled: bool) -> bool:
        """
        Enable/disable temperature compensation.

        Args:
            enabled: True to enable, False to disable

        Returns:
            True if command sent successfully
        """
        switch_name = "ENABLE" if enabled else "DISABLE"
        return self.client.set_switch(self.device, self.PROP_FOCUS_TEMP_COMP, switch_name)

    def get_status(self) -> FocuserStatus:
        """
        Get comprehensive focuser status.

        Returns:
            FocuserStatus with current state
        """
        # Check temp compensation
        temp_comp = False
        comp_prop = self.client.get_property(self.device, self.PROP_FOCUS_TEMP_COMP)
        if comp_prop and comp_prop.values:
            temp_comp = comp_prop.values.get("ENABLE", False)

        return FocuserStatus(
            position=self.get_position() or 0,
            is_moving=self.is_moving(),
            temperature=self.get_temperature(),
            temp_compensation=temp_comp,
            max_position=self.get_max_position(),
            step_size=1.0,  # Device-specific, default 1 micron
        )


# =============================================================================
# CCD Camera Adapter
# =============================================================================

class CCDFrameType(Enum):
    """CCD frame types."""
    LIGHT = "FRAME_LIGHT"
    BIAS = "FRAME_BIAS"
    DARK = "FRAME_DARK"
    FLAT = "FRAME_FLAT"


@dataclass
class CCDInfo:
    """CCD camera information."""
    width: int
    height: int
    pixel_size_x: float  # microns
    pixel_size_y: float  # microns
    bits_per_pixel: int
    max_bin_x: int
    max_bin_y: int


class INDICamera:
    """
    INDI CCD camera adapter.

    Provides high-level control for CCD/CMOS cameras using standard
    INDI CCD properties.

    Common INDI camera devices:
    - "CCD Simulator" (indi_simulator_ccd)
    - "ZWO CCD" (indi_asi_ccd)
    - "QHY CCD" (indi_qhy_ccd)

    Usage:
        client = NightwatchINDIClient()
        client.connect()

        camera = INDICamera(client, "CCD Simulator")
        camera.set_exposure(10.0)  # 10 second exposure
    """

    # Standard INDI CCD properties
    PROP_EXPOSURE = "CCD_EXPOSURE"
    PROP_ABORT = "CCD_ABORT_EXPOSURE"
    PROP_FRAME = "CCD_FRAME"
    PROP_BINNING = "CCD_BINNING"
    PROP_TEMPERATURE = "CCD_TEMPERATURE"
    PROP_COOLER = "CCD_COOLER"
    PROP_INFO = "CCD_INFO"
    PROP_FRAME_TYPE = "CCD_FRAME_TYPE"

    def __init__(self, client: NightwatchINDIClient, device_name: str):
        """
        Initialize camera adapter.

        Args:
            client: Connected INDI client
            device_name: INDI device name for the camera
        """
        self.client = client
        self.device = device_name
        self._exposure_callback: Optional[Callable[[bytes], None]] = None

    def set_exposure(self, duration: float) -> bool:
        """
        Start an exposure.

        Args:
            duration: Exposure duration in seconds

        Returns:
            True if exposure started
        """
        result = self.client.set_number(
            self.device,
            self.PROP_EXPOSURE,
            {"CCD_EXPOSURE_VALUE": duration}
        )
        if result:
            logger.info(f"Starting {duration}s exposure")
        return result

    def abort_exposure(self) -> bool:
        """
        Abort current exposure.

        Returns:
            True if command sent
        """
        result = self.client.set_switch(self.device, self.PROP_ABORT, "ABORT")
        if result:
            logger.info("Exposure aborted")
        return result

    def is_exposing(self) -> bool:
        """Check if camera is currently exposing."""
        prop = self.client.get_property(self.device, self.PROP_EXPOSURE)
        if prop:
            return prop.state == PropertyState.BUSY
        return False

    def get_exposure_remaining(self) -> float:
        """Get remaining exposure time in seconds."""
        prop = self.client.get_property(self.device, self.PROP_EXPOSURE)
        if prop and prop.values:
            return prop.values.get("CCD_EXPOSURE_VALUE", 0.0)
        return 0.0

    def set_binning(self, bin_x: int, bin_y: Optional[int] = None) -> bool:
        """
        Set camera binning.

        Args:
            bin_x: Horizontal binning factor
            bin_y: Vertical binning factor (defaults to bin_x)

        Returns:
            True if command sent
        """
        if bin_y is None:
            bin_y = bin_x

        return self.client.set_number(
            self.device,
            self.PROP_BINNING,
            {"HOR_BIN": float(bin_x), "VER_BIN": float(bin_y)}
        )

    def get_binning(self) -> tuple:
        """Get current binning (bin_x, bin_y)."""
        prop = self.client.get_property(self.device, self.PROP_BINNING)
        if prop and prop.values:
            return (
                int(prop.values.get("HOR_BIN", 1)),
                int(prop.values.get("VER_BIN", 1))
            )
        return (1, 1)

    def set_frame_type(self, frame_type: CCDFrameType) -> bool:
        """
        Set frame type for next exposure.

        Args:
            frame_type: Type of frame (LIGHT, DARK, FLAT, BIAS)

        Returns:
            True if command sent
        """
        return self.client.set_switch(self.device, self.PROP_FRAME_TYPE, frame_type.value)

    def set_temperature(self, temperature: float) -> bool:
        """
        Set target CCD temperature.

        Args:
            temperature: Target temperature in Celsius

        Returns:
            True if command sent
        """
        return self.client.set_number(
            self.device,
            self.PROP_TEMPERATURE,
            {"CCD_TEMPERATURE_VALUE": temperature}
        )

    def get_temperature(self) -> Optional[float]:
        """Get current CCD temperature in Celsius."""
        prop = self.client.get_property(self.device, self.PROP_TEMPERATURE)
        if prop and prop.values:
            return prop.values.get("CCD_TEMPERATURE_VALUE")
        return None

    def set_cooler(self, enabled: bool) -> bool:
        """
        Enable/disable camera cooler.

        Args:
            enabled: True to enable cooler

        Returns:
            True if command sent
        """
        switch_name = "COOLER_ON" if enabled else "COOLER_OFF"
        return self.client.set_switch(self.device, self.PROP_COOLER, switch_name)

    def get_info(self) -> Optional[CCDInfo]:
        """Get CCD information."""
        prop = self.client.get_property(self.device, self.PROP_INFO)
        if not prop or not prop.values:
            return None

        return CCDInfo(
            width=int(prop.values.get("CCD_MAX_X", 0)),
            height=int(prop.values.get("CCD_MAX_Y", 0)),
            pixel_size_x=prop.values.get("CCD_PIXEL_SIZE_X", 0.0),
            pixel_size_y=prop.values.get("CCD_PIXEL_SIZE_Y", 0.0),
            bits_per_pixel=int(prop.values.get("CCD_BITSPERPIXEL", 16)),
            max_bin_x=int(prop.values.get("CCD_MAX_BIN_X", 1)),
            max_bin_y=int(prop.values.get("CCD_MAX_BIN_Y", 1)),
        )


# =============================================================================
# Telescope/Mount Adapter
# =============================================================================

class TrackingMode(Enum):
    """Telescope tracking modes."""
    SIDEREAL = "TRACK_SIDEREAL"
    LUNAR = "TRACK_LUNAR"
    SOLAR = "TRACK_SOLAR"
    CUSTOM = "TRACK_CUSTOM"


class INDITelescope:
    """
    INDI telescope/mount adapter.

    Provides high-level control for telescope mounts using standard
    INDI telescope properties.

    Note: For OnStepX mounts, prefer the dedicated LX200Client in
    services/mount_control/ which supports extended commands.

    Common INDI telescope devices:
    - "Telescope Simulator" (indi_simulator_telescope)
    - "LX200 GPS" (indi_lx200gps)
    - "EQMod Mount" (indi_eqmod_telescope)
    """

    # Standard INDI telescope properties
    PROP_EQUATORIAL_COORD = "EQUATORIAL_EOD_COORD"
    PROP_TARGET_COORD = "TARGET_EOD_COORD"
    PROP_HORIZONTAL_COORD = "HORIZONTAL_COORD"
    PROP_ABORT = "TELESCOPE_ABORT_MOTION"
    PROP_TRACK_STATE = "TELESCOPE_TRACK_STATE"
    PROP_TRACK_MODE = "TELESCOPE_TRACK_MODE"
    PROP_PARK = "TELESCOPE_PARK"
    PROP_MOTION_NS = "TELESCOPE_MOTION_NS"
    PROP_MOTION_WE = "TELESCOPE_MOTION_WE"
    PROP_SLEW_RATE = "TELESCOPE_SLEW_RATE"

    def __init__(self, client: NightwatchINDIClient, device_name: str):
        """
        Initialize telescope adapter.

        Args:
            client: Connected INDI client
            device_name: INDI device name for the telescope
        """
        self.client = client
        self.device = device_name

    def goto(self, ra: float, dec: float) -> bool:
        """
        Slew to RA/Dec coordinates.

        Args:
            ra: Right Ascension in hours (0-24)
            dec: Declination in degrees (-90 to +90)

        Returns:
            True if slew command sent
        """
        result = self.client.set_number(
            self.device,
            self.PROP_EQUATORIAL_COORD,
            {"RA": ra, "DEC": dec}
        )
        if result:
            logger.info(f"Slewing to RA={ra:.4f}h Dec={dec:.4f}°")
        return result

    def sync(self, ra: float, dec: float) -> bool:
        """
        Sync mount to RA/Dec coordinates.

        Args:
            ra: Right Ascension in hours
            dec: Declination in degrees

        Returns:
            True if sync command sent
        """
        # Set ON_COORD_SET to SYNC first
        self.client.set_switch(self.device, "ON_COORD_SET", "SYNC")

        result = self.client.set_number(
            self.device,
            self.PROP_EQUATORIAL_COORD,
            {"RA": ra, "DEC": dec}
        )
        if result:
            logger.info(f"Synced to RA={ra:.4f}h Dec={dec:.4f}°")

        # Set back to SLEW mode
        self.client.set_switch(self.device, "ON_COORD_SET", "SLEW")
        return result

    def abort(self) -> bool:
        """Abort all motion."""
        result = self.client.set_switch(self.device, self.PROP_ABORT, "ABORT")
        if result:
            logger.info("Mount motion aborted")
        return result

    def get_coordinates(self) -> Optional[tuple]:
        """
        Get current RA/Dec coordinates.

        Returns:
            Tuple of (ra, dec) or None if unavailable
        """
        prop = self.client.get_property(self.device, self.PROP_EQUATORIAL_COORD)
        if prop and prop.values:
            return (
                prop.values.get("RA", 0.0),
                prop.values.get("DEC", 0.0)
            )
        return None

    def is_slewing(self) -> bool:
        """Check if telescope is slewing."""
        prop = self.client.get_property(self.device, self.PROP_EQUATORIAL_COORD)
        if prop:
            return prop.state == PropertyState.BUSY
        return False

    def set_tracking(self, enabled: bool) -> bool:
        """Enable/disable tracking."""
        switch_name = "TRACK_ON" if enabled else "TRACK_OFF"
        return self.client.set_switch(self.device, self.PROP_TRACK_STATE, switch_name)

    def is_tracking(self) -> bool:
        """Check if tracking is enabled."""
        prop = self.client.get_property(self.device, self.PROP_TRACK_STATE)
        if prop and prop.values:
            return prop.values.get("TRACK_ON", False)
        return False

    def set_tracking_mode(self, mode: TrackingMode) -> bool:
        """Set tracking mode."""
        return self.client.set_switch(self.device, self.PROP_TRACK_MODE, mode.value)

    def park(self) -> bool:
        """Park the telescope."""
        result = self.client.set_switch(self.device, self.PROP_PARK, "PARK")
        if result:
            logger.info("Parking telescope")
        return result

    def unpark(self) -> bool:
        """Unpark the telescope."""
        result = self.client.set_switch(self.device, self.PROP_PARK, "UNPARK")
        if result:
            logger.info("Unparking telescope")
        return result

    def is_parked(self) -> bool:
        """Check if telescope is parked."""
        prop = self.client.get_property(self.device, self.PROP_PARK)
        if prop and prop.values:
            return prop.values.get("PARK", False)
        return False


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    print("NIGHTWATCH INDI Device Adapters Test\n")

    from .indi_client import PYINDI_AVAILABLE

    if not PYINDI_AVAILABLE:
        print("PyIndi not available. Install with: pip install pyindi-client")
        exit(1)

    print("Connecting to INDI server...")
    client = NightwatchINDIClient("localhost", 7624)

    if not client.connect():
        print("Failed to connect. Is INDI server running?")
        print("Start with: indiserver indi_simulator_telescope indi_simulator_ccd indi_simulator_focus indi_simulator_wheel")
        exit(1)

    import time
    print("Waiting for devices...")
    time.sleep(3)

    devices = client.get_device_names()
    print(f"Found {len(devices)} devices: {devices}\n")

    # Test filter wheel
    if "Filter Simulator" in devices:
        print("=== Filter Wheel Test ===")
        wheel = INDIFilterWheel(client, "Filter Simulator")
        print(f"Current filter: {wheel.get_filter()} - {wheel.get_filter_name()}")
        print(f"Available filters: {wheel.get_filter_names()}")

    # Test focuser
    if "Focuser Simulator" in devices:
        print("\n=== Focuser Test ===")
        focuser = INDIFocuser(client, "Focuser Simulator")
        status = focuser.get_status()
        print(f"Position: {status.position}")
        print(f"Temperature: {status.temperature}")

    # Test telescope
    if "Telescope Simulator" in devices:
        print("\n=== Telescope Test ===")
        scope = INDITelescope(client, "Telescope Simulator")
        coords = scope.get_coordinates()
        if coords:
            print(f"Coordinates: RA={coords[0]:.4f}h Dec={coords[1]:.4f}°")
        print(f"Tracking: {scope.is_tracking()}")
        print(f"Parked: {scope.is_parked()}")

    client.disconnect()
    print("\nDone!")
