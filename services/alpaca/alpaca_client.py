"""
ASCOM Alpaca client for NIGHTWATCH device communication.

This module provides Python wrappers for ASCOM Alpaca devices, enabling
network-based control of telescopes, cameras, focusers, and filter wheels
through a standardized REST API.

Requirements:
    - alpyca>=2.0.0

Example:
    >>> from services.alpaca import AlpacaDiscovery, AlpacaTelescope
    >>> devices = AlpacaDiscovery.discover()
    >>> telescope = AlpacaTelescope("192.168.1.100", 11111, 0)
    >>> telescope.connect()
    >>> print(f"RA: {telescope.ra}, Dec: {telescope.dec}")
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
import logging
import time
import threading

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class AlpacaDevice:
    """Discovered Alpaca device information."""
    name: str
    device_type: str
    address: str
    port: int
    device_number: int
    unique_id: str = ""

    @property
    def endpoint(self) -> str:
        """Get the base endpoint URL for this device."""
        return f"http://{self.address}:{self.port}"


@dataclass
class CameraState:
    """Camera exposure and readout state."""

    class State(Enum):
        IDLE = 0
        WAITING = 1
        EXPOSING = 2
        READING = 3
        DOWNLOAD = 4
        ERROR = 5

    state: State
    percent_complete: float
    image_ready: bool


@dataclass
class ImageData:
    """Container for downloaded camera image data."""
    data: Any  # numpy array when available
    width: int
    height: int
    exposure_duration: float
    start_time: str
    filter_name: str = ""
    bin_x: int = 1
    bin_y: int = 1


# ============================================================================
# Device Discovery
# ============================================================================

class AlpacaDiscovery:
    """
    Discover Alpaca devices on the local network.

    Uses UDP broadcast on port 32227 to find ASCOM Alpaca servers
    and enumerate their available devices.
    """

    DISCOVERY_PORT = 32227
    DISCOVERY_MESSAGE = b"alpacadiscovery1"

    @staticmethod
    def discover(timeout: float = 2.0, num_queries: int = 2) -> List[AlpacaDevice]:
        """
        Search for Alpaca devices via UDP broadcast.

        Args:
            timeout: Time to wait for responses (seconds)
            num_queries: Number of discovery broadcasts to send

        Returns:
            List of discovered AlpacaDevice objects
        """
        devices = []

        try:
            # Try using alpyca's built-in discovery first
            from alpaca.discovery import search_ipv4
            results = search_ipv4(timeout=timeout, numquery=num_queries)

            for server in results:
                address = server.get("AlpacaServerName", "Unknown")
                ip = server.get("ServerAddress", "")
                port = server.get("ServerPort", 11111)

                # Query the management API for available devices
                device_list = AlpacaDiscovery._query_configured_devices(ip, port)
                for dev in device_list:
                    devices.append(AlpacaDevice(
                        name=dev.get("DeviceName", address),
                        device_type=dev.get("DeviceType", "Unknown"),
                        address=ip,
                        port=port,
                        device_number=dev.get("DeviceNumber", 0),
                        unique_id=dev.get("UniqueID", ""),
                    ))

        except ImportError:
            logger.warning("alpyca not installed, using fallback discovery")
            devices = AlpacaDiscovery._fallback_discover(timeout)
        except Exception as e:
            logger.error(f"Alpaca discovery failed: {e}")

        logger.info(f"Alpaca discovery found {len(devices)} device(s)")
        return devices

    @staticmethod
    def _query_configured_devices(address: str, port: int) -> List[Dict]:
        """Query Alpaca server for configured devices."""
        import urllib.request
        import json

        try:
            url = f"http://{address}:{port}/management/v1/configureddevices"
            with urllib.request.urlopen(url, timeout=2.0) as response:
                data = json.loads(response.read().decode())
                return data.get("Value", [])
        except Exception as e:
            logger.debug(f"Failed to query configured devices: {e}")
            return []

    @staticmethod
    def _fallback_discover(timeout: float) -> List[AlpacaDevice]:
        """Fallback UDP-based discovery when alpyca is not available."""
        import socket

        devices = []
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)

        try:
            sock.sendto(
                AlpacaDiscovery.DISCOVERY_MESSAGE,
                ("<broadcast>", AlpacaDiscovery.DISCOVERY_PORT)
            )

            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    # Parse response - minimal implementation
                    import json
                    response = json.loads(data.decode())
                    port = response.get("AlpacaPort", 11111)
                    devices.append(AlpacaDevice(
                        name=f"Alpaca Server at {addr[0]}",
                        device_type="Server",
                        address=addr[0],
                        port=port,
                        device_number=0,
                    ))
                except socket.timeout:
                    break
        finally:
            sock.close()

        return devices

    @staticmethod
    def discover_by_type(
        device_type: str,
        timeout: float = 2.0
    ) -> List[AlpacaDevice]:
        """
        Discover devices of a specific type.

        Args:
            device_type: ASCOM device type (telescope, camera, focuser, filterwheel)
            timeout: Discovery timeout in seconds

        Returns:
            List of matching devices
        """
        all_devices = AlpacaDiscovery.discover(timeout)
        return [d for d in all_devices if d.device_type.lower() == device_type.lower()]


# ============================================================================
# Base Adapter
# ============================================================================

class AlpacaDeviceBase:
    """
    Base class for Alpaca device adapters.

    Provides common functionality for connection management,
    error handling, and property access.
    """

    def __init__(
        self,
        address: str,
        port: int = 11111,
        device_number: int = 0,
        client_id: int = 1,
    ):
        """
        Initialize Alpaca device adapter.

        Args:
            address: IP address or hostname of Alpaca server
            port: Alpaca API port (default 11111)
            device_number: Device number on the server
            client_id: Client transaction ID
        """
        self.address = address
        self.port = port
        self.device_number = device_number
        self.client_id = client_id
        self._connected = False
        self._lock = threading.Lock()

    @property
    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self._connected

    def _get_endpoint(self) -> str:
        """Get base API endpoint."""
        return f"http://{self.address}:{self.port}"


# ============================================================================
# Telescope Adapter
# ============================================================================

class AlpacaTelescope(AlpacaDeviceBase):
    """
    ASCOM Alpaca telescope adapter for NIGHTWATCH.

    Provides mount control including slewing, tracking, parking,
    and position readout via the Alpaca REST API.

    Example:
        >>> telescope = AlpacaTelescope("localhost", 11111, 0)
        >>> telescope.connect()
        >>> telescope.slew_to_coordinates(12.5, 45.0)
        >>> while telescope.is_slewing:
        ...     time.sleep(0.5)
        >>> print(f"Arrived at RA={telescope.ra}, Dec={telescope.dec}")
    """

    def __init__(
        self,
        address: str,
        port: int = 11111,
        device_number: int = 0
    ):
        super().__init__(address, port, device_number)
        self._telescope = None

    def connect(self) -> bool:
        """
        Connect to the telescope.

        Returns:
            True if connection successful
        """
        try:
            from alpaca.telescope import Telescope
            self._telescope = Telescope(
                self.address,
                self.device_number,
                self.port
            )
            self._telescope.Connected = True
            self._connected = self._telescope.Connected

            if self._connected:
                logger.info(
                    f"Connected to Alpaca telescope at "
                    f"{self.address}:{self.port}/{self.device_number}"
                )
            return self._connected

        except Exception as e:
            logger.error(f"Alpaca telescope connection failed: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Disconnect from telescope."""
        if self._telescope:
            try:
                self._telescope.Connected = False
            except Exception as e:
                logger.warning(f"Error disconnecting telescope: {e}")
            self._connected = False

    @property
    def ra(self) -> float:
        """
        Get current Right Ascension in hours.

        Returns:
            RA in decimal hours (0-24)
        """
        if not self._telescope:
            return 0.0
        try:
            return self._telescope.RightAscension
        except Exception as e:
            logger.error(f"Failed to read RA: {e}")
            return 0.0

    @property
    def dec(self) -> float:
        """
        Get current Declination in degrees.

        Returns:
            Dec in decimal degrees (-90 to +90)
        """
        if not self._telescope:
            return 0.0
        try:
            return self._telescope.Declination
        except Exception as e:
            logger.error(f"Failed to read Dec: {e}")
            return 0.0

    @property
    def altitude(self) -> float:
        """Get current altitude in degrees."""
        if not self._telescope:
            return 0.0
        try:
            return self._telescope.Altitude
        except Exception as e:
            logger.error(f"Failed to read altitude: {e}")
            return 0.0

    @property
    def azimuth(self) -> float:
        """Get current azimuth in degrees."""
        if not self._telescope:
            return 0.0
        try:
            return self._telescope.Azimuth
        except Exception as e:
            logger.error(f"Failed to read azimuth: {e}")
            return 0.0

    @property
    def is_tracking(self) -> bool:
        """Check if telescope is tracking."""
        if not self._telescope:
            return False
        try:
            return self._telescope.Tracking
        except Exception:
            return False

    @property
    def is_slewing(self) -> bool:
        """Check if telescope is slewing."""
        if not self._telescope:
            return False
        try:
            return self._telescope.Slewing
        except Exception:
            return False

    @property
    def is_parked(self) -> bool:
        """Check if telescope is at park position."""
        if not self._telescope:
            return False
        try:
            return self._telescope.AtPark
        except Exception:
            return False

    @property
    def pier_side(self) -> str:
        """Get current pier side (East/West/Unknown)."""
        if not self._telescope:
            return "Unknown"
        try:
            side = self._telescope.SideOfPier
            return {0: "East", 1: "West"}.get(side, "Unknown")
        except Exception:
            return "Unknown"

    def set_tracking(self, enabled: bool) -> bool:
        """
        Enable or disable tracking.

        Args:
            enabled: True to enable tracking

        Returns:
            True if successful
        """
        if not self._telescope:
            return False
        try:
            self._telescope.Tracking = enabled
            logger.info(f"Tracking {'enabled' if enabled else 'disabled'}")
            return True
        except Exception as e:
            logger.error(f"Failed to set tracking: {e}")
            return False

    def slew_to_coordinates(self, ra: float, dec: float, async_slew: bool = True) -> bool:
        """
        Slew to RA/Dec coordinates.

        Args:
            ra: Right Ascension in decimal hours (0-24)
            dec: Declination in decimal degrees (-90 to +90)
            async_slew: If True, return immediately while slewing

        Returns:
            True if slew initiated successfully
        """
        if not self._telescope:
            return False
        try:
            if async_slew:
                self._telescope.SlewToCoordinatesAsync(ra, dec)
            else:
                self._telescope.SlewToCoordinates(ra, dec)
            logger.info(f"Slewing to RA={ra:.4f}h, Dec={dec:.4f}°")
            return True
        except Exception as e:
            logger.error(f"Slew to coordinates failed: {e}")
            return False

    def slew_to_altaz(self, alt: float, az: float, async_slew: bool = True) -> bool:
        """
        Slew to Alt/Az coordinates.

        Args:
            alt: Altitude in degrees (0-90)
            az: Azimuth in degrees (0-360)
            async_slew: If True, return immediately while slewing

        Returns:
            True if slew initiated successfully
        """
        if not self._telescope:
            return False
        try:
            if async_slew:
                self._telescope.SlewToAltAzAsync(az, alt)
            else:
                self._telescope.SlewToAltAz(az, alt)
            logger.info(f"Slewing to Alt={alt:.2f}°, Az={az:.2f}°")
            return True
        except Exception as e:
            logger.error(f"Slew to AltAz failed: {e}")
            return False

    def abort_slew(self) -> bool:
        """
        Abort any in-progress slew.

        Returns:
            True if successful
        """
        if not self._telescope:
            return False
        try:
            self._telescope.AbortSlew()
            logger.info("Slew aborted")
            return True
        except Exception as e:
            logger.error(f"Abort slew failed: {e}")
            return False

    def park(self) -> bool:
        """
        Park the telescope.

        Returns:
            True if park initiated successfully
        """
        if not self._telescope:
            return False
        try:
            self._telescope.Park()
            logger.info("Parking telescope")
            return True
        except Exception as e:
            logger.error(f"Park failed: {e}")
            return False

    def unpark(self) -> bool:
        """
        Unpark the telescope.

        Returns:
            True if successful
        """
        if not self._telescope:
            return False
        try:
            self._telescope.Unpark()
            logger.info("Telescope unparked")
            return True
        except Exception as e:
            logger.error(f"Unpark failed: {e}")
            return False

    def sync(self, ra: float, dec: float) -> bool:
        """
        Sync telescope to known coordinates.

        Args:
            ra: Actual RA in decimal hours
            dec: Actual Dec in decimal degrees

        Returns:
            True if sync successful
        """
        if not self._telescope:
            return False
        try:
            self._telescope.SyncToCoordinates(ra, dec)
            logger.info(f"Synced to RA={ra:.4f}h, Dec={dec:.4f}°")
            return True
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return False

    def move_axis(self, axis: int, rate: float) -> bool:
        """
        Move telescope axis at specified rate.

        Args:
            axis: 0=RA/Az, 1=Dec/Alt
            rate: Movement rate in degrees/second (0 to stop)

        Returns:
            True if successful
        """
        if not self._telescope:
            return False
        try:
            self._telescope.MoveAxis(axis, rate)
            return True
        except Exception as e:
            logger.error(f"Move axis failed: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive telescope status.

        Returns:
            Dictionary with position, state, and capabilities
        """
        return {
            "connected": self._connected,
            "ra": self.ra,
            "dec": self.dec,
            "altitude": self.altitude,
            "azimuth": self.azimuth,
            "is_tracking": self.is_tracking,
            "is_slewing": self.is_slewing,
            "is_parked": self.is_parked,
            "pier_side": self.pier_side,
        }


# ============================================================================
# Camera Adapter
# ============================================================================

class AlpacaCamera(AlpacaDeviceBase):
    """
    ASCOM Alpaca camera adapter for NIGHTWATCH.

    Provides camera control including exposure, binning,
    temperature regulation, and image download.

    Example:
        >>> camera = AlpacaCamera("localhost", 11111, 0)
        >>> camera.connect()
        >>> camera.set_binning(2, 2)
        >>> camera.start_exposure(30.0, light=True)
        >>> while not camera.image_ready:
        ...     time.sleep(1)
        >>> image = camera.download_image()
    """

    def __init__(
        self,
        address: str,
        port: int = 11111,
        device_number: int = 0
    ):
        super().__init__(address, port, device_number)
        self._camera = None

    def connect(self) -> bool:
        """Connect to the camera."""
        try:
            from alpaca.camera import Camera
            self._camera = Camera(
                self.address,
                self.device_number,
                self.port
            )
            self._camera.Connected = True
            self._connected = self._camera.Connected

            if self._connected:
                logger.info(
                    f"Connected to Alpaca camera at "
                    f"{self.address}:{self.port}/{self.device_number}"
                )
            return self._connected

        except Exception as e:
            logger.error(f"Alpaca camera connection failed: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Disconnect from camera."""
        if self._camera:
            try:
                self._camera.Connected = False
            except Exception as e:
                logger.warning(f"Error disconnecting camera: {e}")
            self._connected = False

    @property
    def camera_state(self) -> CameraState:
        """Get current camera state."""
        if not self._camera:
            return CameraState(
                state=CameraState.State.ERROR,
                percent_complete=0.0,
                image_ready=False
            )
        try:
            return CameraState(
                state=CameraState.State(self._camera.CameraState),
                percent_complete=self._camera.PercentCompleted,
                image_ready=self._camera.ImageReady
            )
        except Exception as e:
            logger.error(f"Failed to get camera state: {e}")
            return CameraState(
                state=CameraState.State.ERROR,
                percent_complete=0.0,
                image_ready=False
            )

    @property
    def image_ready(self) -> bool:
        """Check if image is ready for download."""
        if not self._camera:
            return False
        try:
            return self._camera.ImageReady
        except Exception:
            return False

    @property
    def sensor_width(self) -> int:
        """Get sensor width in pixels."""
        if not self._camera:
            return 0
        try:
            return self._camera.CameraXSize
        except Exception:
            return 0

    @property
    def sensor_height(self) -> int:
        """Get sensor height in pixels."""
        if not self._camera:
            return 0
        try:
            return self._camera.CameraYSize
        except Exception:
            return 0

    @property
    def temperature(self) -> float:
        """Get current CCD temperature in Celsius."""
        if not self._camera:
            return 0.0
        try:
            return self._camera.CCDTemperature
        except Exception:
            return 0.0

    @property
    def cooler_on(self) -> bool:
        """Check if cooler is enabled."""
        if not self._camera:
            return False
        try:
            return self._camera.CoolerOn
        except Exception:
            return False

    @property
    def cooler_power(self) -> float:
        """Get cooler power level (0-100%)."""
        if not self._camera:
            return 0.0
        try:
            return self._camera.CoolerPower
        except Exception:
            return 0.0

    @property
    def bin_x(self) -> int:
        """Get current X binning."""
        if not self._camera:
            return 1
        try:
            return self._camera.BinX
        except Exception:
            return 1

    @property
    def bin_y(self) -> int:
        """Get current Y binning."""
        if not self._camera:
            return 1
        try:
            return self._camera.BinY
        except Exception:
            return 1

    def set_binning(self, bin_x: int, bin_y: int) -> bool:
        """
        Set camera binning.

        Args:
            bin_x: Horizontal binning (1, 2, 3, 4)
            bin_y: Vertical binning (1, 2, 3, 4)

        Returns:
            True if successful
        """
        if not self._camera:
            return False
        try:
            self._camera.BinX = bin_x
            self._camera.BinY = bin_y
            logger.info(f"Binning set to {bin_x}x{bin_y}")
            return True
        except Exception as e:
            logger.error(f"Failed to set binning: {e}")
            return False

    def set_cooler(self, enabled: bool) -> bool:
        """
        Enable or disable camera cooler.

        Args:
            enabled: True to enable cooler

        Returns:
            True if successful
        """
        if not self._camera:
            return False
        try:
            self._camera.CoolerOn = enabled
            logger.info(f"Cooler {'enabled' if enabled else 'disabled'}")
            return True
        except Exception as e:
            logger.error(f"Failed to set cooler: {e}")
            return False

    def set_temperature(self, target: float) -> bool:
        """
        Set target CCD temperature.

        Args:
            target: Target temperature in Celsius

        Returns:
            True if successful
        """
        if not self._camera:
            return False
        try:
            self._camera.SetCCDTemperature = target
            logger.info(f"Target temperature set to {target}°C")
            return True
        except Exception as e:
            logger.error(f"Failed to set temperature: {e}")
            return False

    def start_exposure(
        self,
        duration: float,
        light: bool = True
    ) -> bool:
        """
        Start a camera exposure.

        Args:
            duration: Exposure time in seconds
            light: True for light frame, False for dark

        Returns:
            True if exposure started successfully
        """
        if not self._camera:
            return False
        try:
            self._camera.StartExposure(duration, light)
            frame_type = "light" if light else "dark"
            logger.info(f"Started {duration}s {frame_type} exposure")
            return True
        except Exception as e:
            logger.error(f"Failed to start exposure: {e}")
            return False

    def abort_exposure(self) -> bool:
        """
        Abort current exposure.

        Returns:
            True if successful
        """
        if not self._camera:
            return False
        try:
            self._camera.AbortExposure()
            logger.info("Exposure aborted")
            return True
        except Exception as e:
            logger.error(f"Failed to abort exposure: {e}")
            return False

    def stop_exposure(self) -> bool:
        """
        Stop current exposure and read out image.

        Returns:
            True if successful
        """
        if not self._camera:
            return False
        try:
            self._camera.StopExposure()
            logger.info("Exposure stopped, reading out")
            return True
        except Exception as e:
            logger.error(f"Failed to stop exposure: {e}")
            return False

    def download_image(self) -> Optional[ImageData]:
        """
        Download the current image.

        Returns:
            ImageData object with pixel data, or None if not ready
        """
        if not self._camera or not self.image_ready:
            return None
        try:
            image_array = self._camera.ImageArray

            return ImageData(
                data=image_array,
                width=self._camera.NumX,
                height=self._camera.NumY,
                exposure_duration=self._camera.LastExposureDuration,
                start_time=self._camera.LastExposureStartTime,
                bin_x=self.bin_x,
                bin_y=self.bin_y,
            )
        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive camera status."""
        state = self.camera_state
        return {
            "connected": self._connected,
            "state": state.state.name,
            "percent_complete": state.percent_complete,
            "image_ready": state.image_ready,
            "temperature": self.temperature,
            "cooler_on": self.cooler_on,
            "cooler_power": self.cooler_power,
            "bin_x": self.bin_x,
            "bin_y": self.bin_y,
            "sensor_width": self.sensor_width,
            "sensor_height": self.sensor_height,
        }


# ============================================================================
# Focuser Adapter
# ============================================================================

class AlpacaFocuser(AlpacaDeviceBase):
    """
    ASCOM Alpaca focuser adapter for NIGHTWATCH.

    Provides focuser control including absolute and relative
    movement, temperature compensation, and position readout.

    Example:
        >>> focuser = AlpacaFocuser("localhost", 11111, 0)
        >>> focuser.connect()
        >>> focuser.move_absolute(5000)
        >>> while focuser.is_moving:
        ...     time.sleep(0.1)
        >>> print(f"Position: {focuser.position}")
    """

    def __init__(
        self,
        address: str,
        port: int = 11111,
        device_number: int = 0
    ):
        super().__init__(address, port, device_number)
        self._focuser = None

    def connect(self) -> bool:
        """Connect to the focuser."""
        try:
            from alpaca.focuser import Focuser
            self._focuser = Focuser(
                self.address,
                self.device_number,
                self.port
            )
            self._focuser.Connected = True
            self._connected = self._focuser.Connected

            if self._connected:
                logger.info(
                    f"Connected to Alpaca focuser at "
                    f"{self.address}:{self.port}/{self.device_number}"
                )
            return self._connected

        except Exception as e:
            logger.error(f"Alpaca focuser connection failed: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Disconnect from focuser."""
        if self._focuser:
            try:
                self._focuser.Connected = False
            except Exception as e:
                logger.warning(f"Error disconnecting focuser: {e}")
            self._connected = False

    @property
    def position(self) -> int:
        """Get current focuser position in steps."""
        if not self._focuser:
            return 0
        try:
            return self._focuser.Position
        except Exception:
            return 0

    @property
    def max_position(self) -> int:
        """Get maximum focuser position."""
        if not self._focuser:
            return 0
        try:
            return self._focuser.MaxStep
        except Exception:
            return 0

    @property
    def is_moving(self) -> bool:
        """Check if focuser is moving."""
        if not self._focuser:
            return False
        try:
            return self._focuser.IsMoving
        except Exception:
            return False

    @property
    def temperature(self) -> float:
        """Get focuser temperature in Celsius."""
        if not self._focuser:
            return 0.0
        try:
            return self._focuser.Temperature
        except Exception:
            return 0.0

    @property
    def temp_comp(self) -> bool:
        """Check if temperature compensation is enabled."""
        if not self._focuser:
            return False
        try:
            return self._focuser.TempComp
        except Exception:
            return False

    def set_temp_comp(self, enabled: bool) -> bool:
        """
        Enable or disable temperature compensation.

        Args:
            enabled: True to enable temp compensation

        Returns:
            True if successful
        """
        if not self._focuser:
            return False
        try:
            self._focuser.TempComp = enabled
            logger.info(f"Temperature compensation {'enabled' if enabled else 'disabled'}")
            return True
        except Exception as e:
            logger.error(f"Failed to set temp comp: {e}")
            return False

    def move_absolute(self, position: int) -> bool:
        """
        Move focuser to absolute position.

        Args:
            position: Target position in steps

        Returns:
            True if move initiated successfully
        """
        if not self._focuser:
            return False
        try:
            self._focuser.Move(position)
            logger.info(f"Moving focuser to position {position}")
            return True
        except Exception as e:
            logger.error(f"Focuser move failed: {e}")
            return False

    def move_relative(self, steps: int) -> bool:
        """
        Move focuser by relative steps.

        Args:
            steps: Number of steps to move (positive=out, negative=in)

        Returns:
            True if move initiated successfully
        """
        current = self.position
        target = current + steps
        return self.move_absolute(target)

    def halt(self) -> bool:
        """
        Halt focuser movement.

        Returns:
            True if successful
        """
        if not self._focuser:
            return False
        try:
            self._focuser.Halt()
            logger.info("Focuser halted")
            return True
        except Exception as e:
            logger.error(f"Focuser halt failed: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive focuser status."""
        return {
            "connected": self._connected,
            "position": self.position,
            "max_position": self.max_position,
            "is_moving": self.is_moving,
            "temperature": self.temperature,
            "temp_comp": self.temp_comp,
        }


# ============================================================================
# Filter Wheel Adapter
# ============================================================================

class AlpacaFilterWheel(AlpacaDeviceBase):
    """
    ASCOM Alpaca filter wheel adapter for NIGHTWATCH.

    Provides filter wheel control including position setting
    and filter name management.

    Example:
        >>> wheel = AlpacaFilterWheel("localhost", 11111, 0)
        >>> wheel.connect()
        >>> print(wheel.filter_names)  # ['L', 'R', 'G', 'B', 'Ha', 'OIII']
        >>> wheel.set_position(4)  # Move to Ha filter
    """

    def __init__(
        self,
        address: str,
        port: int = 11111,
        device_number: int = 0
    ):
        super().__init__(address, port, device_number)
        self._wheel = None

    def connect(self) -> bool:
        """Connect to the filter wheel."""
        try:
            from alpaca.filterwheel import FilterWheel
            self._wheel = FilterWheel(
                self.address,
                self.device_number,
                self.port
            )
            self._wheel.Connected = True
            self._connected = self._wheel.Connected

            if self._connected:
                logger.info(
                    f"Connected to Alpaca filter wheel at "
                    f"{self.address}:{self.port}/{self.device_number}"
                )
            return self._connected

        except Exception as e:
            logger.error(f"Alpaca filter wheel connection failed: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Disconnect from filter wheel."""
        if self._wheel:
            try:
                self._wheel.Connected = False
            except Exception as e:
                logger.warning(f"Error disconnecting filter wheel: {e}")
            self._connected = False

    @property
    def position(self) -> int:
        """Get current filter position (0-indexed)."""
        if not self._wheel:
            return -1
        try:
            return self._wheel.Position
        except Exception:
            return -1

    @property
    def filter_names(self) -> List[str]:
        """Get list of filter names."""
        if not self._wheel:
            return []
        try:
            return list(self._wheel.Names)
        except Exception:
            return []

    @property
    def current_filter(self) -> str:
        """Get name of current filter."""
        names = self.filter_names
        pos = self.position
        if 0 <= pos < len(names):
            return names[pos]
        return "Unknown"

    def set_position(self, position: int) -> bool:
        """
        Set filter wheel position.

        Args:
            position: Filter position (0-indexed)

        Returns:
            True if move initiated successfully
        """
        if not self._wheel:
            return False
        try:
            self._wheel.Position = position
            logger.info(f"Moving to filter position {position}")
            return True
        except Exception as e:
            logger.error(f"Filter wheel move failed: {e}")
            return False

    def set_filter_by_name(self, name: str) -> bool:
        """
        Set filter by name.

        Args:
            name: Filter name (case-insensitive)

        Returns:
            True if move initiated successfully
        """
        names = self.filter_names
        name_lower = name.lower()

        for i, filter_name in enumerate(names):
            if filter_name.lower() == name_lower:
                return self.set_position(i)

        logger.error(f"Filter '{name}' not found. Available: {names}")
        return False

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive filter wheel status."""
        return {
            "connected": self._connected,
            "position": self.position,
            "current_filter": self.current_filter,
            "filter_names": self.filter_names,
        }


# ============================================================================
# Factory Functions
# ============================================================================

def create_for_dgx_spark(
    device_type: str = "telescope",
    address: str = "localhost",
    port: int = 11111,
    device_number: int = 0,
) -> AlpacaDeviceBase:
    """
    Create Alpaca device adapter optimized for DGX Spark deployment.

    Args:
        device_type: Device type (telescope, camera, focuser, filterwheel)
        address: Alpaca server address
        port: Alpaca server port
        device_number: Device number on server

    Returns:
        Configured device adapter
    """
    adapters = {
        "telescope": AlpacaTelescope,
        "camera": AlpacaCamera,
        "focuser": AlpacaFocuser,
        "filterwheel": AlpacaFilterWheel,
    }

    adapter_class = adapters.get(device_type.lower())
    if not adapter_class:
        raise ValueError(f"Unknown device type: {device_type}")

    return adapter_class(address, port, device_number)
