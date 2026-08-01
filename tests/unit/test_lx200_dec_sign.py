"""
Regression tests for LX200 declination sign handling (fix S2-1).

A Declination of "-00" degrees must keep its negative sign. The previous
implementation derived the sign from the float magnitude, and because
``-0.0 < 0`` evaluates to ``False`` a southern target within one degree of
the celestial equator was silently flipped to the northern hemisphere.
"""

import pytest
from unittest.mock import patch

from services.mount_control.lx200 import (
    LX200Client,
    ConnectionType,
    dec_to_degrees,
)


def test_dec_to_degrees_negative_zero_degrees():
    """A -00 deg 30' Dec must parse to approximately -0.5 degrees."""
    assert dec_to_degrees("-00*30:00") == pytest.approx(-0.5)


def test_dec_to_degrees_positive_zero_degrees():
    """A +00 deg 30' Dec must parse to approximately +0.5 degrees."""
    assert dec_to_degrees("+00*30:00") == pytest.approx(0.5)


def test_dec_to_degrees_ordinary_negative():
    """Signs on non-zero degrees still work."""
    assert dec_to_degrees("-12*30:00") == pytest.approx(-12.5)


def test_get_status_preserves_negative_zero_dec():
    """get_status() for a -00 deg 30' target converts to ~ -0.5 degrees.

    Only the serial/TCP transport is stubbed: ``_send_command`` maps each
    LX200 query to a canned reply, and the real parsing/conversion code runs.
    """
    client = LX200Client(connection_type=ConnectionType.TCP)

    responses = {
        "GR": "12:00:00",   # RA HH:MM:SS
        "GD": "-00*30:00",  # Dec sDD*MM:SS at -00 deg 30'
        "GW": "TN0",        # tracking, not slewing
        "GU": "n",          # not parked
        "Gm": "E",          # pier east
    }

    with patch.object(
        LX200Client,
        "_send_command",
        side_effect=lambda cmd: responses.get(cmd),
    ):
        status = client.get_status()

        assert status is not None
        # The parsed degrees component must carry the negative sign so that
        # the conversion to decimal degrees stays in the southern hemisphere.
        dec_deg = client._mount_dec_to_degrees(status)

    assert dec_deg == pytest.approx(-0.5)
