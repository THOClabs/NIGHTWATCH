"""
Data-integrity regression tests for the Alpaca adapters (fixes S2-2, S2-3).

S2-2: the alpyca device objects must be constructed as
``Device("host:port", device_number)`` rather than with a mis-placed third
positional (port-as-protocol) argument.

S2-3: getters must not fabricate valid-looking values (0.0/False/0) when a
device read fails; the underlying read error must propagate so callers cannot
mistake a comms failure for a real pointing/state.
"""

import pytest
from unittest.mock import Mock, patch


# =============================================================================
# S2-2 - constructor argument shape
# =============================================================================

def test_telescope_constructor_uses_host_port_string():
    from services.alpaca.alpaca_client import AlpacaTelescope

    tele = AlpacaTelescope(address="localhost", port=11111, device_number=2)
    mock_cls = Mock()
    with patch.dict("sys.modules", {"alpaca.telescope": Mock(Telescope=mock_cls)}):
        tele.connect()
    mock_cls.assert_called_once_with("localhost:11111", 2)


def test_camera_constructor_uses_host_port_string():
    from services.alpaca.alpaca_client import AlpacaCamera

    cam = AlpacaCamera(address="localhost", port=11111, device_number=1)
    mock_cls = Mock()
    with patch.dict("sys.modules", {"alpaca.camera": Mock(Camera=mock_cls)}):
        cam.connect()
    mock_cls.assert_called_once_with("localhost:11111", 1)


def test_focuser_constructor_uses_host_port_string():
    from services.alpaca.alpaca_client import AlpacaFocuser

    foc = AlpacaFocuser(address="localhost", port=11111, device_number=0)
    mock_cls = Mock()
    with patch.dict("sys.modules", {"alpaca.focuser": Mock(Focuser=mock_cls)}):
        foc.connect()
    mock_cls.assert_called_once_with("localhost:11111", 0)


def test_filterwheel_constructor_uses_host_port_string():
    from services.alpaca.alpaca_client import AlpacaFilterWheel

    fw = AlpacaFilterWheel(address="localhost", port=11111, device_number=3)
    mock_cls = Mock()
    with patch.dict("sys.modules", {"alpaca.filterwheel": Mock(FilterWheel=mock_cls)}):
        fw.connect()
    mock_cls.assert_called_once_with("localhost:11111", 3)


# =============================================================================
# S2-3 - read failures must propagate, not fabricate values
# =============================================================================

class _FailingReadTelescope:
    """Alpyca telescope stub whose every position/state read raises."""

    @property
    def RightAscension(self):
        raise ConnectionError("device read failed")

    @property
    def Declination(self):
        raise ConnectionError("device read failed")

    @property
    def Tracking(self):
        raise ConnectionError("device read failed")

    @property
    def Slewing(self):
        raise ConnectionError("device read failed")

    @property
    def AtPark(self):
        raise ConnectionError("device read failed")


def _connected_telescope():
    from services.alpaca.alpaca_client import AlpacaTelescope

    tele = AlpacaTelescope(address="localhost", port=11111, device_number=0)
    tele._telescope = _FailingReadTelescope()
    tele._connected = True
    return tele


def test_ra_read_error_propagates():
    tele = _connected_telescope()
    with pytest.raises(ConnectionError):
        _ = tele.ra


def test_dec_read_error_propagates():
    tele = _connected_telescope()
    with pytest.raises(ConnectionError):
        _ = tele.dec


def test_is_tracking_read_error_propagates():
    tele = _connected_telescope()
    with pytest.raises(ConnectionError):
        _ = tele.is_tracking


def test_is_slewing_read_error_propagates():
    tele = _connected_telescope()
    with pytest.raises(ConnectionError):
        _ = tele.is_slewing


def test_is_parked_read_error_propagates():
    tele = _connected_telescope()
    with pytest.raises(ConnectionError):
        _ = tele.is_parked


class _FailingReadFocuser:
    """Alpyca focuser stub whose Position read raises; records Move calls."""

    def __init__(self):
        self.move_calls = []

    @property
    def Position(self):
        raise ConnectionError("device read failed")

    def Move(self, position):
        self.move_calls.append(position)


def test_focuser_position_read_error_propagates():
    from services.alpaca.alpaca_client import AlpacaFocuser

    foc = AlpacaFocuser(address="localhost", port=11111, device_number=0)
    foc._focuser = _FailingReadFocuser()
    foc._connected = True
    with pytest.raises(ConnectionError):
        _ = foc.position


def test_move_relative_does_not_move_when_position_read_fails():
    from services.alpaca.alpaca_client import AlpacaFocuser

    foc = AlpacaFocuser(address="localhost", port=11111, device_number=0)
    stub = _FailingReadFocuser()
    foc._focuser = stub
    foc._connected = True

    # Reading current position fails, so no (bogus, step-0-ish) absolute
    # move must ever be issued to the hardware.
    with pytest.raises(ConnectionError):
        foc.move_relative(500)

    assert stub.move_calls == []
