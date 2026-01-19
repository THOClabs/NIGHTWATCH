"""
EncoderBridge interface for high-resolution position feedback.

This module interfaces with the EncoderBridge hardware (hjd1964/EncoderBridge)
to provide absolute encoder readings for harmonic drive correction.

The EncoderBridge provides high-resolution absolute encoder feedback that can
be used to correct for harmonic drive periodic error and backlash, achieving
sub-arcsecond positioning accuracy.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EncoderPosition:
    """High-resolution encoder position data."""

    axis1_counts: int  # RA/Az encoder counts
    axis2_counts: int  # Dec/Alt encoder counts
    axis1_degrees: float  # Computed position in degrees
    axis2_degrees: float  # Computed position in degrees
    timestamp: float  # Unix timestamp


class EncoderBridge:
    """
    Interface to EncoderBridge for high-resolution position feedback.

    The EncoderBridge provides absolute encoder readings that can be
    used to correct for harmonic drive periodic error and backlash.

    Attributes:
        port: Serial port path (e.g., "/dev/ttyUSB1")
        baudrate: Serial communication speed (default 115200)
        counts_per_rev: Tuple of counts per revolution for each axis

    Example:
        >>> bridge = EncoderBridge("/dev/ttyUSB1")
        >>> await bridge.connect()
        >>> position = await bridge.get_position()
        >>> print(f"RA: {position.axis1_degrees:.4f}°")
    """

    # EncoderBridge serial protocol commands
    CMD_GET_POSITION = "Q"
    CMD_SET_ZERO = "Z"
    CMD_GET_STATUS = "S"
    CMD_GET_VERSION = "V"
    CMD_SYNC = "Y"

    def __init__(
        self,
        port: str = "/dev/ttyUSB1",
        baudrate: int = 115200,
        counts_per_rev_axis1: int = 16384,  # 14-bit encoder
        counts_per_rev_axis2: int = 16384,
        timeout: float = 1.0,
    ):
        """
        Initialize EncoderBridge interface.

        Args:
            port: Serial port path
            baudrate: Serial communication speed
            counts_per_rev_axis1: Encoder counts per revolution for axis 1 (RA/Az)
            counts_per_rev_axis2: Encoder counts per revolution for axis 2 (Dec/Alt)
            timeout: Serial read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.counts_per_rev = (counts_per_rev_axis1, counts_per_rev_axis2)
        self.timeout = timeout
        self._serial = None
        self._callbacks: List[Callable[[EncoderPosition], None]] = []
        self._running = False
        self._connected = False
        self._lock = asyncio.Lock()

    async def connect(self) -> bool:
        """
        Connect to EncoderBridge.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            import serial

            self._serial = serial.Serial(
                self.port,
                self.baudrate,
                timeout=self.timeout,
            )
            # Verify connection with status check
            status = await self._send_command(self.CMD_GET_STATUS)
            if status and status.startswith("OK"):
                self._connected = True
                logger.info(f"EncoderBridge connected on {self.port}")
                return True
            logger.warning(f"EncoderBridge status check failed: {status}")
            return False
        except ImportError:
            logger.error("pyserial not installed. Install with: pip install pyserial")
            return False
        except Exception as e:
            logger.error(f"EncoderBridge connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from EncoderBridge."""
        self._running = False
        self._connected = False
        if self._serial:
            try:
                self._serial.close()
            except Exception as e:
                logger.error(f"Error closing serial port: {e}")
            self._serial = None
        logger.info("EncoderBridge disconnected")

    @property
    def is_connected(self) -> bool:
        """Check if connected to EncoderBridge."""
        return self._connected and self._serial is not None

    async def get_position(self) -> Optional[EncoderPosition]:
        """
        Read current encoder positions.

        Returns:
            EncoderPosition with counts and degrees for both axes,
            or None if read failed
        """
        response = await self._send_command(self.CMD_GET_POSITION)
        if not response:
            return None

        # Parse response: "axis1_counts,axis2_counts"
        try:
            parts = response.strip().split(",")
            if len(parts) < 2:
                logger.error(f"Invalid encoder response format: {response}")
                return None

            counts1 = int(parts[0])
            counts2 = int(parts[1])

            return EncoderPosition(
                axis1_counts=counts1,
                axis2_counts=counts2,
                axis1_degrees=(counts1 / self.counts_per_rev[0]) * 360.0,
                axis2_degrees=(counts2 / self.counts_per_rev[1]) * 360.0,
                timestamp=time.time(),
            )
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to parse encoder response '{response}': {e}")
            return None

    async def get_version(self) -> Optional[str]:
        """
        Get EncoderBridge firmware version.

        Returns:
            Version string or None if read failed
        """
        return await self._send_command(self.CMD_GET_VERSION)

    async def set_zero(self, axis: int = 0) -> bool:
        """
        Set current position as zero reference.

        Args:
            axis: 0 for both axes, 1 for axis1 only, 2 for axis2 only

        Returns:
            True if successful
        """
        cmd = f"{self.CMD_SET_ZERO}{axis}" if axis > 0 else self.CMD_SET_ZERO
        response = await self._send_command(cmd)
        return response == "1" or response == "OK"

    async def sync_to_position(
        self, axis1_degrees: float, axis2_degrees: float
    ) -> bool:
        """
        Sync encoder to known position (e.g., from plate solve).

        Args:
            axis1_degrees: Known position for axis 1 in degrees
            axis2_degrees: Known position for axis 2 in degrees

        Returns:
            True if sync successful
        """
        # Convert degrees to counts
        counts1 = int((axis1_degrees / 360.0) * self.counts_per_rev[0])
        counts2 = int((axis2_degrees / 360.0) * self.counts_per_rev[1])
        response = await self._send_command(f"{self.CMD_SYNC}{counts1},{counts2}")
        return response == "1" or response == "OK"

    async def _send_command(self, cmd: str) -> Optional[str]:
        """
        Send command and read response.

        Args:
            cmd: Command string to send

        Returns:
            Response string or None if failed
        """
        if not self._serial:
            logger.error("EncoderBridge not connected")
            return None

        async with self._lock:
            try:
                # Clear any pending data
                self._serial.reset_input_buffer()

                # Send command in LX200-style format
                self._serial.write(f":{cmd}#".encode())

                # Read response until terminator
                response = self._serial.read_until(b"#")
                return response.decode().rstrip("#")
            except Exception as e:
                logger.error(f"EncoderBridge command '{cmd}' failed: {e}")
                return None

    def register_callback(self, callback: Callable[[EncoderPosition], None]):
        """
        Register callback for position updates.

        Args:
            callback: Function called with EncoderPosition on each update
        """
        self._callbacks.append(callback)
        logger.debug(f"Registered encoder callback, total: {len(self._callbacks)}")

    def unregister_callback(self, callback: Callable[[EncoderPosition], None]):
        """
        Unregister a previously registered callback.

        Args:
            callback: The callback function to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            logger.debug(f"Unregistered encoder callback, remaining: {len(self._callbacks)}")

    async def start_continuous_read(self, interval: float = 0.1):
        """
        Start continuous position monitoring.

        This method runs in a loop, reading encoder positions at the
        specified interval and calling all registered callbacks.

        Args:
            interval: Time between reads in seconds (default 100ms)
        """
        self._running = True
        logger.info(f"Starting continuous encoder read at {interval}s interval")

        while self._running:
            position = await self.get_position()
            if position:
                for callback in self._callbacks:
                    try:
                        callback(position)
                    except Exception as e:
                        logger.error(f"Encoder callback error: {e}")
            await asyncio.sleep(interval)

        logger.info("Continuous encoder read stopped")

    def stop(self):
        """Stop continuous reading."""
        self._running = False

    async def get_position_error(
        self, mount_axis1_deg: float, mount_axis2_deg: float
    ) -> Optional[tuple]:
        """
        Calculate pointing error between mount and encoder positions.

        This is useful for detecting and correcting harmonic drive
        periodic error and backlash.

        Args:
            mount_axis1_deg: Mount-reported position for axis 1 (degrees)
            mount_axis2_deg: Mount-reported position for axis 2 (degrees)

        Returns:
            Tuple of (error_axis1, error_axis2) in degrees, or None if read failed
        """
        position = await self.get_position()
        if not position:
            return None

        error_axis1 = position.axis1_degrees - mount_axis1_deg
        error_axis2 = position.axis2_degrees - mount_axis2_deg

        # Normalize to ±180 degrees
        while error_axis1 > 180:
            error_axis1 -= 360
        while error_axis1 < -180:
            error_axis1 += 360
        while error_axis2 > 180:
            error_axis2 -= 360
        while error_axis2 < -180:
            error_axis2 += 360

        logger.debug(f"Position error: axis1={error_axis1:.4f}° axis2={error_axis2:.4f}°")
        return (error_axis1, error_axis2)


# Factory function for DGX Spark optimization
def create_for_dgx_spark(
    port: str = "/dev/ttyUSB1",
    high_resolution: bool = True,
) -> EncoderBridge:
    """
    Create EncoderBridge configured for DGX Spark observatory.

    Args:
        port: Serial port path
        high_resolution: Use 16-bit encoders if True, 14-bit if False

    Returns:
        Configured EncoderBridge instance
    """
    counts_per_rev = 65536 if high_resolution else 16384

    return EncoderBridge(
        port=port,
        baudrate=115200,
        counts_per_rev_axis1=counts_per_rev,
        counts_per_rev_axis2=counts_per_rev,
        timeout=0.5,  # Faster timeout for responsive operation
    )
