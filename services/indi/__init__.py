"""
NIGHTWATCH INDI Service
Interface to INDI (Instrument Neutral Distributed Interface) devices

This module provides a Python interface to INDI servers for controlling
astronomy equipment on Linux systems. INDI is the standard device protocol
for astronomy software on Linux, complementing ASCOM Alpaca for Windows.

Components:
- NightwatchINDIClient: Core INDI client for server communication
- AsyncINDIClient: Async wrapper for use in asyncio applications
- Device adapters: High-level interfaces for common device types

Supported Device Types:
- Filter wheels (INDIFilterWheel)
- Focusers (INDIFocuser)
- CCD/CMOS cameras (INDICamera)
- Telescope mounts (INDITelescope)

Requirements:
- pyindi-client: pip install pyindi-client
- INDI libraries: apt install libindi-dev (Ubuntu/Debian)

Usage:
    from services.indi import NightwatchINDIClient, INDIFocuser

    # Connect to INDI server
    client = NightwatchINDIClient("localhost", 7624)
    client.connect()

    # Control a focuser
    focuser = INDIFocuser(client, "Focuser Simulator")
    focuser.move_absolute(5000)

Running INDI Server:
    # Start INDI server with simulators for testing
    indiserver indi_simulator_telescope indi_simulator_ccd \\
               indi_simulator_focus indi_simulator_wheel

    # Or use Docker (see docker/docker-compose.dev.yml)
    docker-compose -f docker/docker-compose.dev.yml up indi-server

See Also:
- services/alpaca/ - ASCOM Alpaca client for Windows/network devices
- docker/docker-compose.dev.yml - Development simulators
- tests/integration/test_device_layer.py - Integration tests
"""

from .indi_client import (
    NightwatchINDIClient,
    AsyncINDIClient,
    INDIProperty,
    INDIDevice,
    PropertyState,
    PropertyType,
    PYINDI_AVAILABLE,
)

from .device_adapters import (
    # Filter wheel
    INDIFilterWheel,
    FilterInfo,
    # Focuser
    INDIFocuser,
    FocuserStatus,
    # Camera
    INDICamera,
    CCDInfo,
    CCDFrameType,
    # Telescope
    INDITelescope,
    TrackingMode,
)

__all__ = [
    # Client
    "NightwatchINDIClient",
    "AsyncINDIClient",
    "PYINDI_AVAILABLE",
    # Properties
    "INDIProperty",
    "INDIDevice",
    "PropertyState",
    "PropertyType",
    # Filter wheel
    "INDIFilterWheel",
    "FilterInfo",
    # Focuser
    "INDIFocuser",
    "FocuserStatus",
    # Camera
    "INDICamera",
    "CCDInfo",
    "CCDFrameType",
    # Telescope
    "INDITelescope",
    "TrackingMode",
]

__version__ = "0.1.0"
