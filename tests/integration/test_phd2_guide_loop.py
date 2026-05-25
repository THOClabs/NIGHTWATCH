"""Integration test: PHD2 full calibrate-and-guide orchestration (HWS-003).

HWS-003's spec verify line is:

    "integration test against PHD2 simulator:
     `guider.calibrate_and_guide(target=...)` returns settled state
     with `Settling.Done` event observed."

The existing ``PHD2Client`` has all the primitives (calibrate, auto_select_star,
start_guiding, wait_for_settle, event-driven SettleDone) but no single
orchestration entrypoint that composes them. HWS-003 adds that entrypoint and
this test exercises it end-to-end against a mocked PHD2 transport.

Test approach: Approach B from the HWS-003 prompt — mock ``_send_request`` to
return canned JSON-RPC results and inject events via ``_handle_event``
directly. This matches the existing ``tests/unit/test_phd2_client.py`` style
(MagicMock + AsyncMock) and keeps the test deterministic without standing up
a real TCP server. The wire path (JSON serialization, TCP framing) is already
covered by the existing 18 phd2 client tests.

Coverage:
  1. Spec verify: SettleDone observed → method returns True.
  2. Skip-calibration: existing calibration → no calibrate RPC issued.
  3. No-star-found: auto_select_star returns None → method returns False.
  4. Calibration timeout: settle never fires after calibrate → False.
  5. Settle timeout: SettleDone never emitted after start_guiding → False.
  6. Manual star selection: (x, y) tuple → set_guide_star issued, no auto_select.
  7. Failure is reported as bool, not raised (operator-facing surface).
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.guiding.phd2_client import (
    CalibrationData,
    GuideStar,
    GuideState,
    PHD2Client,
)


# ============================================================================
# Helpers
# ============================================================================

def _make_connected_client() -> PHD2Client:
    """Build a PHD2Client that looks 'connected' but has no real socket.

    The orchestration method only needs ``_connected=True`` so its
    connection check passes; ``_send_request`` is replaced with an
    AsyncMock per-test, so no actual I/O happens.
    """
    client = PHD2Client()
    client._connected = True
    return client


async def _fire_settle_done(client: PHD2Client, delay_s: float = 0.05) -> None:
    """Fire a SettleDone event after a short delay, as PHD2 would.

    Mirrors the JSON shape PHD2's socket server emits and lets the
    real ``_handle_event`` path set ``_dither_settle_event``. We bracket
    with a Settling event so ``wait_for_settle`` sees ``self._settling=True``
    and actually awaits the event (rather than the already-settled fast path).
    """
    # Mark settling so wait_for_settle takes the await branch.
    await client._handle_event({"Event": "Settling"})
    await asyncio.sleep(delay_s)
    await client._handle_event({"Event": "SettleDone", "Status": 0})


# ============================================================================
# 1. Spec verify case — the HWS-003 verify line
# ============================================================================

class TestCalibrateAndGuideSpecVerify:
    """HWS-003 spec verify: SettleDone observed → returns True."""

    async def test_calibrate_and_guide_returns_true_after_settle_done(self):
        """Spec verify: calibrate_and_guide returns True once SettleDone fires.

        This is the line item the HWS-003 task description names explicitly.
        """
        client = _make_connected_client()

        # Stub the JSON-RPC surface. ``find_star`` returns a star; ``guide``
        # accepts the start_guiding/calibrate calls; ``get_calibration_data``
        # returns None on the first call (forcing calibration) and then
        # SettleDone fires asynchronously to release wait_for_settle.
        client._send_request = AsyncMock(side_effect=_make_rpc_responder(
            calibration_data=None,  # no prior calibration → calibrate runs
            star=GuideStar(x=512.0, y=384.0, snr=30.0),
        ))

        # Fire SettleDone twice — once for calibration (which itself settles),
        # once for guiding. The orchestration awaits both settle gates.
        async def fire_two_settles():
            await _fire_settle_done(client, delay_s=0.05)
            await _fire_settle_done(client, delay_s=0.05)

        fire_task = asyncio.create_task(fire_two_settles())

        result = await client.calibrate_and_guide(
            settle_pixels=1.5,
            settle_time_s=0.1,
            settle_timeout_s=2.0,
            calibration_timeout_s=2.0,
        )

        await fire_task
        assert result is True, "expected True after SettleDone observed"


# ============================================================================
# 2. Skip-calibration when already calibrated
# ============================================================================

class TestSkipCalibration:
    """If skip_calibration_if_calibrated=True and a calibration exists, skip."""

    async def test_skip_calibration_no_calibrate_rpc_issued(self):
        """No 'guide' RPC with recalibrate=True should fire when skipping."""
        client = _make_connected_client()

        existing_cal = CalibrationData(
            timestamp=datetime.now(),
            ra_rate=10.5, dec_rate=10.2,
            ra_angle=0.0, dec_angle=90.0,
            orthogonality=0.5,
        )

        client._send_request = AsyncMock(side_effect=_make_rpc_responder(
            calibration_data=existing_cal,
            star=GuideStar(x=512.0, y=384.0, snr=30.0),
        ))

        # Only the guide-loop settle has to fire (no calibration settle).
        fire_task = asyncio.create_task(_fire_settle_done(client, delay_s=0.05))

        result = await client.calibrate_and_guide(
            settle_time_s=0.1,
            settle_timeout_s=2.0,
            skip_calibration_if_calibrated=True,
        )

        await fire_task
        assert result is True

        # Verify no recalibrate=True 'guide' call was made.
        recalibrate_calls = [
            call for call in client._send_request.call_args_list
            if call.args and call.args[0] == "guide"
            and len(call.args) > 1 and call.args[1].get("recalibrate") is True
        ]
        assert recalibrate_calls == [], (
            f"expected no recalibrate=True calls, got {recalibrate_calls}"
        )


# ============================================================================
# 3. No-star-found case
# ============================================================================

class TestNoStarFound:
    """auto_select_star returns None → return False, log warning."""

    async def test_no_star_returns_false(self):
        client = _make_connected_client()

        # Use an existing calibration so the cal step is skipped and the
        # method actually reaches auto_select_star (otherwise we'd be testing
        # cal-timeout, not no-star).
        existing_cal = CalibrationData(
            timestamp=datetime.now(),
            ra_rate=10.5, dec_rate=10.2,
            ra_angle=0.0, dec_angle=90.0,
            orthogonality=0.5,
        )

        client._send_request = AsyncMock(side_effect=_make_rpc_responder(
            calibration_data=existing_cal,
            star=None,  # find_star returns nothing
        ))

        result = await client.calibrate_and_guide(
            settle_timeout_s=1.0,
            calibration_timeout_s=1.0,
            skip_calibration_if_calibrated=True,
        )
        assert result is False

        # Confirm we DID reach find_star (proving this tests no-star, not
        # cal-timeout).
        find_star_calls = [
            call for call in client._send_request.call_args_list
            if call.args and call.args[0] == "find_star"
        ]
        assert len(find_star_calls) == 1


# ============================================================================
# 4. Calibration timeout
# ============================================================================

class TestCalibrationTimeout:
    """If calibration never reports SettleDone, return False after budget."""

    async def test_calibration_timeout_returns_false(self):
        client = _make_connected_client()

        client._send_request = AsyncMock(side_effect=_make_rpc_responder(
            calibration_data=None,
            star=GuideStar(x=512.0, y=384.0, snr=30.0),
        ))

        # No SettleDone fires for calibration — wait_for_settle times out.
        # Mark settling so wait_for_settle takes the await branch (otherwise
        # the not-settling early-return would short-circuit to True).
        await client._handle_event({"Event": "Settling"})

        result = await client.calibrate_and_guide(
            settle_timeout_s=0.2,
            calibration_timeout_s=0.2,  # tiny budget for fast test
        )
        assert result is False


# ============================================================================
# 5. Settle timeout (after start_guiding)
# ============================================================================

class TestSettleTimeout:
    """If SettleDone never fires after start_guiding, return False."""

    async def test_settle_timeout_returns_false(self):
        client = _make_connected_client()

        existing_cal = CalibrationData(
            timestamp=datetime.now(),
            ra_rate=10.5, dec_rate=10.2,
            ra_angle=0.0, dec_angle=90.0,
            orthogonality=0.5,
        )

        client._send_request = AsyncMock(side_effect=_make_rpc_responder(
            calibration_data=existing_cal,  # skip calibration
            star=GuideStar(x=512.0, y=384.0, snr=30.0),
        ))

        # Mark settling so wait_for_settle takes the await branch.
        await client._handle_event({"Event": "Settling"})

        result = await client.calibrate_and_guide(
            settle_timeout_s=0.2,  # tiny budget
            skip_calibration_if_calibrated=True,
        )
        assert result is False


# ============================================================================
# 6. Manual star selection
# ============================================================================

class TestManualStarSelection:
    """star_selection=(x, y) → set_guide_star issued, auto_select_star NOT."""

    async def test_manual_star_selection_issues_set_lock_position(self):
        client = _make_connected_client()

        client._send_request = AsyncMock(side_effect=_make_rpc_responder(
            calibration_data=None,
            star=GuideStar(x=999.0, y=999.0, snr=99.0),
        ))

        fire_task = asyncio.create_task(_fire_settle_two(client))

        result = await client.calibrate_and_guide(
            settle_time_s=0.1,
            settle_timeout_s=2.0,
            calibration_timeout_s=2.0,
            star_selection=(100.0, 200.0),
        )

        await fire_task
        assert result is True

        # Verify set_lock_position was called with the manual coords.
        set_lock_calls = [
            call for call in client._send_request.call_args_list
            if call.args and call.args[0] == "set_lock_position"
        ]
        assert len(set_lock_calls) == 1
        params = set_lock_calls[0].args[1]
        assert params["x"] == 100.0
        assert params["y"] == 200.0

        # Verify find_star (auto_select_star) was NOT called.
        find_star_calls = [
            call for call in client._send_request.call_args_list
            if call.args and call.args[0] == "find_star"
        ]
        assert find_star_calls == []


# ============================================================================
# 7. Operator surface: never raises, always returns bool
# ============================================================================

class TestOperatorSurfaceNeverRaises:
    """All failure paths return False, never raise (operator-facing)."""

    async def test_disconnected_returns_false_no_raise(self):
        """If not connected, return False rather than raising ConnectionError."""
        client = PHD2Client()  # _connected stays False
        # No _send_request stubbing needed — the method should bail at the
        # connection check before any RPC is attempted.
        result = await client.calibrate_and_guide(
            settle_timeout_s=0.1,
            calibration_timeout_s=0.1,
        )
        assert result is False

    async def test_rpc_error_returns_false_no_raise(self):
        """If an RPC errors mid-flow, return False (don't propagate)."""
        client = _make_connected_client()

        # get_calibration_data raises RuntimeError ("PHD2 error: ...").
        # The orchestrator should swallow and treat as no-prior-calibration
        # or as overall failure — either way, no exception escapes.
        async def boom(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("PHD2 error: simulated")

        client._send_request = AsyncMock(side_effect=boom)

        result = await client.calibrate_and_guide(
            settle_timeout_s=0.1,
            calibration_timeout_s=0.1,
        )
        assert result is False


# ============================================================================
# Cancellation propagation (ARCH-003)
# ============================================================================

class TestCancellationPropagates:
    """asyncio.CancelledError should propagate cleanly, not be swallowed."""

    async def test_cancellederror_propagates(self):
        """SafetyMonitor cancel → CancelledError must NOT be eaten by the bool surface."""
        client = _make_connected_client()

        # Block forever on the first RPC; we'll cancel the task externally.
        async def blocker(*args: Any, **kwargs: Any) -> Any:
            await asyncio.sleep(10.0)
            return None

        client._send_request = AsyncMock(side_effect=blocker)

        task = asyncio.create_task(client.calibrate_and_guide(
            settle_timeout_s=10.0,
            calibration_timeout_s=10.0,
        ))
        # Let it start, then cancel.
        await asyncio.sleep(0.05)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task


# ============================================================================
# Protocol conformance (HWS-002 cross-task LEARNING)
# ============================================================================

class TestGuidingServiceProtocolHasCalibrateAndGuide:
    """Per HWS-002 LEARNING: new client methods must be on the Protocol."""

    def test_protocol_declares_calibrate_and_guide(self):
        """GuidingServiceProtocol must declare calibrate_and_guide."""
        from nightwatch.orchestrator import GuidingServiceProtocol  # noqa: PLC0415
        # Protocol method lookup is by attribute presence.
        assert hasattr(GuidingServiceProtocol, "calibrate_and_guide"), (
            "GuidingServiceProtocol must declare calibrate_and_guide "
            "(HWS-002 cross-task LEARNING: new client methods need a "
            "Protocol declaration so they're callable through the "
            "orchestrator's typed surface)."
        )


# ============================================================================
# RPC responder factory
# ============================================================================

def _make_rpc_responder(
    *,
    calibration_data: Optional[CalibrationData],
    star: Optional[GuideStar],
):
    """Build an AsyncMock side_effect that returns canned PHD2 RPC results.

    Mirrors the wire shapes the real ``PHD2Client`` methods expect:
      - ``get_calibration_data`` → dict with xRate/yRate/xAngle/yAngle or None
      - ``find_star`` → dict with x/y or None
      - ``guide`` (calibrate or start_guiding) → 0
      - ``set_lock_position`` → 0
      - ``get_app_state`` → "Stopped"
    """
    cal_dict = None
    if calibration_data is not None:
        cal_dict = {
            "xRate": calibration_data.ra_rate,
            "yRate": calibration_data.dec_rate,
            "xAngle": calibration_data.ra_angle,
            "yAngle": calibration_data.dec_angle,
        }

    star_dict = None
    if star is not None:
        star_dict = {"x": star.x, "y": star.y}

    async def responder(method: str, params: Optional[dict] = None) -> Any:
        if method == "get_calibration_data":
            return cal_dict
        if method == "find_star":
            return star_dict
        if method == "guide":
            return 0
        if method == "set_lock_position":
            return 0
        if method == "get_app_state":
            return "Stopped"
        if method == "stop_capture":
            return 0
        return None

    return responder


async def _fire_settle_two(client: PHD2Client) -> None:
    """Fire two SettleDone events (one for calibration, one for guiding)."""
    await _fire_settle_done(client, delay_s=0.05)
    await _fire_settle_done(client, delay_s=0.05)
