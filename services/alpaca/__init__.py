"""
ASCOM Alpaca device integration for NIGHTWATCH.

This module provides network-based device control via the ASCOM Alpaca
protocol, enabling cross-platform device communication with Windows,
Linux, and macOS systems.
"""

from .alpaca_client import (
    AlpacaDevice,
    AlpacaDiscovery,
    AlpacaTelescope,
    AlpacaCamera,
    AlpacaFocuser,
    AlpacaFilterWheel,
)

__all__ = [
    "AlpacaDevice",
    "AlpacaDiscovery",
    "AlpacaTelescope",
    "AlpacaCamera",
    "AlpacaFocuser",
    "AlpacaFilterWheel",
]
