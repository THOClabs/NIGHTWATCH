"""
NIGHTWATCH INDI Client
Interface to INDI (Instrument Neutral Distributed Interface) Server

This module provides a Python interface to INDI servers for controlling
astronomy devices including cameras, filter wheels, focusers, and mounts.

INDI is the standard device communication protocol on Linux for astronomy
equipment, complementing ASCOM Alpaca which is used on Windows/network.

Requires: pyindi-client (pip install pyindi-client)
"""

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import PyIndi
try:
    import PyIndi
    PYINDI_AVAILABLE = True
except ImportError:
    PYINDI_AVAILABLE = False
    logger.warning("PyIndi not available. Install with: pip install pyindi-client")


class PropertyState(Enum):
    """INDI property states."""
    IDLE = "Idle"
    OK = "Ok"
    BUSY = "Busy"
    ALERT = "Alert"
    UNKNOWN = "Unknown"


class PropertyType(Enum):
    """INDI property types."""
    NUMBER = "number"
    SWITCH = "switch"
    TEXT = "text"
    LIGHT = "light"
    BLOB = "blob"
    UNKNOWN = "unknown"


@dataclass
class INDIProperty:
    """Wrapper for INDI property values."""
    name: str
    device: str
    type: PropertyType
    values: Dict[str, Any]
    state: PropertyState
    label: str = ""
    group: str = ""
    timestamp: str = ""

    def __repr__(self) -> str:
        return f"INDIProperty({self.device}.{self.name}: {self.values})"


@dataclass
class INDIDevice:
    """Representation of an INDI device."""
    name: str
    driver: str = ""
    connected: bool = False
    properties: Dict[str, INDIProperty] = field(default_factory=dict)

    def __repr__(self) -> str:
        status = "connected" if self.connected else "disconnected"
        return f"INDIDevice({self.name}, {status}, {len(self.properties)} properties)"


if PYINDI_AVAILABLE:
    class NightwatchINDIClient(PyIndi.BaseClient):
        """
        INDI client for NIGHTWATCH device communication.

        Provides async-friendly interface to INDI server for controlling
        cameras, filter wheels, focusers, and other astronomy devices.

        Usage:
            client = NightwatchINDIClient("localhost", 7624)
            if client.connect():
                # Wait for device discovery
                await asyncio.sleep(2)

                # List devices
                for name in client.get_device_names():
                    print(f"Found: {name}")

                # Control a focuser
                client.set_number("Focuser Simulator", "ABS_FOCUS_POSITION",
                                  {"FOCUS_ABSOLUTE_POSITION": 5000})
        """

        def __init__(self, host: str = "localhost", port: int = 7624):
            """
            Initialize INDI client.

            Args:
                host: INDI server hostname
                port: INDI server port (default 7624)
            """
            super().__init__()
            self.host = host
            self.port = port
            self._devices: Dict[str, PyIndi.BaseDevice] = {}
            self._device_info: Dict[str, INDIDevice] = {}
            self._property_callbacks: Dict[str, List[Callable]] = {}
            self._device_callbacks: List[Callable] = []
            self._connected = False
            self._lock = threading.Lock()

        def connect(self) -> bool:
            """
            Connect to INDI server.

            Returns:
                True if connection successful, False otherwise
            """
            self.setServer(self.host, self.port)
            if not self.connectServer():
                logger.error(f"Failed to connect to INDI server at {self.host}:{self.port}")
                return False
            self._connected = True
            logger.info(f"Connected to INDI server at {self.host}:{self.port}")
            return True

        def disconnect(self):
            """Disconnect from INDI server."""
            if self._connected:
                self.disconnectServer()
                self._connected = False
                logger.info("Disconnected from INDI server")

        @property
        def is_connected(self) -> bool:
            """Check if connected to server."""
            return self._connected

        # =====================================================================
        # PyIndi.BaseClient Callbacks
        # =====================================================================

        def newDevice(self, d):
            """Callback: New device connected."""
            name = d.getDeviceName()
            with self._lock:
                self._devices[name] = d
                self._device_info[name] = INDIDevice(name=name)
            logger.info(f"INDI device discovered: {name}")

            # Notify callbacks
            for callback in self._device_callbacks:
                try:
                    callback(name, "added")
                except Exception as e:
                    logger.error(f"Device callback error: {e}")

        def removeDevice(self, d):
            """Callback: Device disconnected."""
            name = d.getDeviceName()
            with self._lock:
                self._devices.pop(name, None)
                self._device_info.pop(name, None)
            logger.info(f"INDI device removed: {name}")

            # Notify callbacks
            for callback in self._device_callbacks:
                try:
                    callback(name, "removed")
                except Exception as e:
                    logger.error(f"Device callback error: {e}")

        def newProperty(self, p):
            """Callback: New property available."""
            prop = self._wrap_property(p)
            if prop:
                prop_key = f"{prop.device}.{prop.name}"

                # Store property info
                with self._lock:
                    if prop.device in self._device_info:
                        self._device_info[prop.device].properties[prop.name] = prop

                # Notify callbacks
                if prop_key in self._property_callbacks:
                    for callback in self._property_callbacks[prop_key]:
                        try:
                            callback(prop)
                        except Exception as e:
                            logger.error(f"Property callback error: {e}")

        def updateProperty(self, p):
            """Callback: Property value updated."""
            # Same handling as newProperty
            self.newProperty(p)

        def removeProperty(self, p):
            """Callback: Property removed."""
            device_name = p.getDeviceName()
            prop_name = p.getName()
            with self._lock:
                if device_name in self._device_info:
                    self._device_info[device_name].properties.pop(prop_name, None)

        def newMessage(self, d, m):
            """Callback: New message from device."""
            logger.debug(f"INDI message from {d.getDeviceName()}: {d.messageQueue(m)}")

        def serverConnected(self):
            """Callback: Server connection established."""
            logger.info("INDI server connection established")

        def serverDisconnected(self, code):
            """Callback: Server disconnected."""
            self._connected = False
            logger.warning(f"INDI server disconnected (code: {code})")

        # =====================================================================
        # Property Helpers
        # =====================================================================

        def _wrap_property(self, p) -> Optional[INDIProperty]:
            """Convert INDI property to dataclass."""
            try:
                values = {}
                prop_type = PropertyType.UNKNOWN

                if p.getType() == PyIndi.INDI_NUMBER:
                    prop_type = PropertyType.NUMBER
                    num_prop = p.getNumber()
                    for i in range(num_prop.count):
                        elem = num_prop[i]
                        values[elem.name] = elem.value
                elif p.getType() == PyIndi.INDI_SWITCH:
                    prop_type = PropertyType.SWITCH
                    switch_prop = p.getSwitch()
                    for i in range(switch_prop.count):
                        elem = switch_prop[i]
                        values[elem.name] = elem.s == PyIndi.ISS_ON
                elif p.getType() == PyIndi.INDI_TEXT:
                    prop_type = PropertyType.TEXT
                    text_prop = p.getText()
                    for i in range(text_prop.count):
                        elem = text_prop[i]
                        values[elem.name] = elem.text
                elif p.getType() == PyIndi.INDI_LIGHT:
                    prop_type = PropertyType.LIGHT
                    light_prop = p.getLight()
                    for i in range(light_prop.count):
                        elem = light_prop[i]
                        values[elem.name] = elem.s
                elif p.getType() == PyIndi.INDI_BLOB:
                    prop_type = PropertyType.BLOB
                    # BLOBs handled separately

                state_map = {
                    PyIndi.IPS_IDLE: PropertyState.IDLE,
                    PyIndi.IPS_OK: PropertyState.OK,
                    PyIndi.IPS_BUSY: PropertyState.BUSY,
                    PyIndi.IPS_ALERT: PropertyState.ALERT,
                }

                return INDIProperty(
                    name=p.getName(),
                    device=p.getDeviceName(),
                    type=prop_type,
                    values=values,
                    state=state_map.get(p.getState(), PropertyState.UNKNOWN),
                    label=p.getLabel(),
                    group=p.getGroupName(),
                    timestamp=p.getTimestamp(),
                )
            except Exception as e:
                logger.error(f"Failed to wrap property: {e}")
                return None

        # =====================================================================
        # Device Access
        # =====================================================================

        def get_device(self, name: str) -> Optional[PyIndi.BaseDevice]:
            """
            Get device by name.

            Args:
                name: Device name

            Returns:
                INDI device or None if not found
            """
            with self._lock:
                return self._devices.get(name)

        def get_device_names(self) -> List[str]:
            """
            Get list of connected device names.

            Returns:
                List of device names
            """
            with self._lock:
                return list(self._devices.keys())

        def get_device_info(self, name: str) -> Optional[INDIDevice]:
            """
            Get device info including properties.

            Args:
                name: Device name

            Returns:
                INDIDevice or None if not found
            """
            with self._lock:
                return self._device_info.get(name)

        def wait_for_device(self, name: str, timeout: float = 10.0) -> bool:
            """
            Wait for a device to be discovered.

            Args:
                name: Device name to wait for
                timeout: Maximum wait time in seconds

            Returns:
                True if device found, False if timeout
            """
            import time
            start = time.time()
            while time.time() - start < timeout:
                if name in self._devices:
                    return True
                time.sleep(0.1)
            return False

        # =====================================================================
        # Property Access
        # =====================================================================

        def get_property(self, device: str, property_name: str) -> Optional[INDIProperty]:
            """
            Get current property value.

            Args:
                device: Device name
                property_name: Property name

            Returns:
                INDIProperty or None if not found
            """
            dev = self.get_device(device)
            if not dev:
                logger.warning(f"Device not found: {device}")
                return None

            prop = dev.getProperty(property_name)
            if not prop:
                logger.warning(f"Property not found: {device}.{property_name}")
                return None

            return self._wrap_property(prop)

        def set_number(self, device: str, property_name: str, values: Dict[str, float]) -> bool:
            """
            Set number property values.

            Args:
                device: Device name
                property_name: Property name
                values: Dictionary of element names to values

            Returns:
                True if successful, False otherwise
            """
            dev = self.get_device(device)
            if not dev:
                logger.error(f"Device not found: {device}")
                return False

            prop = dev.getNumber(property_name)
            if not prop:
                logger.error(f"Number property not found: {device}.{property_name}")
                return False

            # Set values
            for i in range(prop.count):
                elem = prop[i]
                if elem.name in values:
                    elem.value = values[elem.name]

            self.sendNewNumber(prop)
            logger.debug(f"Set {device}.{property_name} = {values}")
            return True

        def set_switch(self, device: str, property_name: str, switch_name: str) -> bool:
            """
            Set switch property (turns on specified switch, others off).

            Args:
                device: Device name
                property_name: Property name
                switch_name: Switch element to turn on

            Returns:
                True if successful, False otherwise
            """
            dev = self.get_device(device)
            if not dev:
                logger.error(f"Device not found: {device}")
                return False

            prop = dev.getSwitch(property_name)
            if not prop:
                logger.error(f"Switch property not found: {device}.{property_name}")
                return False

            # Turn all off, then set requested one
            for i in range(prop.count):
                elem = prop[i]
                elem.s = PyIndi.ISS_ON if elem.name == switch_name else PyIndi.ISS_OFF

            self.sendNewSwitch(prop)
            logger.debug(f"Set {device}.{property_name}.{switch_name} = ON")
            return True

        def set_text(self, device: str, property_name: str, values: Dict[str, str]) -> bool:
            """
            Set text property values.

            Args:
                device: Device name
                property_name: Property name
                values: Dictionary of element names to text values

            Returns:
                True if successful, False otherwise
            """
            dev = self.get_device(device)
            if not dev:
                logger.error(f"Device not found: {device}")
                return False

            prop = dev.getText(property_name)
            if not prop:
                logger.error(f"Text property not found: {device}.{property_name}")
                return False

            # Set values
            for i in range(prop.count):
                elem = prop[i]
                if elem.name in values:
                    elem.text = values[elem.name]

            self.sendNewText(prop)
            logger.debug(f"Set {device}.{property_name} = {values}")
            return True

        # =====================================================================
        # Callbacks
        # =====================================================================

        def register_property_callback(
            self,
            device: str,
            property_name: str,
            callback: Callable[[INDIProperty], None]
        ):
            """
            Register callback for property changes.

            Args:
                device: Device name
                property_name: Property name
                callback: Function to call on property change
            """
            key = f"{device}.{property_name}"
            if key not in self._property_callbacks:
                self._property_callbacks[key] = []
            self._property_callbacks[key].append(callback)

        def register_device_callback(self, callback: Callable[[str, str], None]):
            """
            Register callback for device add/remove events.

            Args:
                callback: Function(device_name, event_type) where event_type is "added" or "removed"
            """
            self._device_callbacks.append(callback)

        # =====================================================================
        # Connection Control
        # =====================================================================

        def connect_device(self, device: str) -> bool:
            """
            Connect to a specific device.

            Args:
                device: Device name

            Returns:
                True if connection initiated
            """
            return self.set_switch(device, "CONNECTION", "CONNECT")

        def disconnect_device(self, device: str) -> bool:
            """
            Disconnect from a specific device.

            Args:
                device: Device name

            Returns:
                True if disconnection initiated
            """
            return self.set_switch(device, "CONNECTION", "DISCONNECT")

        def is_device_connected(self, device: str) -> bool:
            """
            Check if device is connected.

            Args:
                device: Device name

            Returns:
                True if device is connected
            """
            prop = self.get_property(device, "CONNECTION")
            if prop and prop.values:
                return prop.values.get("CONNECT", False)
            return False

else:
    # Stub class when PyIndi is not available
    class NightwatchINDIClient:
        """Stub INDI client when PyIndi is not available."""

        def __init__(self, host: str = "localhost", port: int = 7624):
            self.host = host
            self.port = port
            self._connected = False
            self._devices: Dict[str, Any] = {}
            raise RuntimeError(
                "PyIndi not available. Install with: pip install pyindi-client\n"
                "Note: pyindi-client requires INDI libraries to be installed:\n"
                "  Ubuntu/Debian: apt install libindi-dev\n"
                "  macOS: brew install indilib"
            )


# =============================================================================
# Async Wrapper
# =============================================================================

class AsyncINDIClient:
    """
    Async wrapper for NightwatchINDIClient.

    Provides asyncio-friendly interface for use in async applications.
    """

    def __init__(self, host: str = "localhost", port: int = 7624):
        self.host = host
        self.port = port
        self._client: Optional[NightwatchINDIClient] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def connect(self) -> bool:
        """Connect to INDI server asynchronously."""
        self._loop = asyncio.get_event_loop()
        self._client = NightwatchINDIClient(self.host, self.port)
        return await self._loop.run_in_executor(None, self._client.connect)

    async def disconnect(self):
        """Disconnect from INDI server."""
        if self._client:
            await self._loop.run_in_executor(None, self._client.disconnect)

    async def wait_for_device(self, name: str, timeout: float = 10.0) -> bool:
        """Wait for device discovery."""
        if not self._client:
            return False
        return await self._loop.run_in_executor(
            None, self._client.wait_for_device, name, timeout
        )

    def get_device_names(self) -> List[str]:
        """Get list of device names."""
        if not self._client:
            return []
        return self._client.get_device_names()

    def get_property(self, device: str, property_name: str) -> Optional[INDIProperty]:
        """Get property value."""
        if not self._client:
            return None
        return self._client.get_property(device, property_name)

    async def set_number(self, device: str, property_name: str, values: Dict[str, float]) -> bool:
        """Set number property."""
        if not self._client:
            return False
        return await self._loop.run_in_executor(
            None, self._client.set_number, device, property_name, values
        )

    async def set_switch(self, device: str, property_name: str, switch_name: str) -> bool:
        """Set switch property."""
        if not self._client:
            return False
        return await self._loop.run_in_executor(
            None, self._client.set_switch, device, property_name, switch_name
        )


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    print("NIGHTWATCH INDI Client Test\n")
    print(f"PyIndi available: {PYINDI_AVAILABLE}")

    if not PYINDI_AVAILABLE:
        print("\nInstall PyIndi with: pip install pyindi-client")
        print("Requires INDI libraries: apt install libindi-dev (Ubuntu)")
        exit(1)

    # Test connection to local INDI server
    print("\nConnecting to INDI server at localhost:7624...")
    client = NightwatchINDIClient("localhost", 7624)

    if client.connect():
        print("Connected! Waiting for devices...")
        import time
        time.sleep(3)

        devices = client.get_device_names()
        print(f"\nDiscovered {len(devices)} devices:")
        for name in devices:
            info = client.get_device_info(name)
            print(f"  - {name}: {len(info.properties)} properties")

        client.disconnect()
    else:
        print("Failed to connect. Is INDI server running?")
        print("Start with: indiserver indi_simulator_telescope indi_simulator_ccd")
