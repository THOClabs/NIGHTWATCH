"""Integration test: safety transitions cancel in-flight ops (ARCH-003).

The Phase 1 audit's Risk #2 — "rain detected → roof closes BEFORE the
in-flight exposure aborts → water damage." ARCH-003 lays the
cancellation infrastructure (CancelToken + CommandContext) and wires
the Orchestrator to register a SafetyMonitor callback that cancels
the active CommandContext when a transition makes the observatory
unsafe.

The verify-line target is the spec's:

    "start a 60s mock exposure, flip safety to unsafe; the capture
     aborts within 2s and the camera service reports cancelled-not-failed."

We exercise that here against a real ASICamera (mocked-SDK), a real
Orchestrator (so the callback-registration path is the production
code path), and a real SafetyMonitor (so the _notify_callbacks pipe
is the production pipe). The only test doubles are:

  - the camera SDK (already mocked by HWS-001's
    _build_mocked_real_sdk_camera helper),
  - the ASICamera._do_exposure / _save_fits stubs (so the test runs
    without astropy + zwoasi installed in this environment),
  - the camera's start/stop lifecycle methods (a thin adapter so the
    bare ASICamera fits the registry's `start()` contract).

SAFE-001 (next vertical task) will add the safety-shutdown-sequence
test that confirms the cancel callback fires BEFORE enclosure.close()
— that's an ordering question; ARCH-003 only proves the cancel signal
flows end-to-end.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime

import pytest

from nightwatch.cancellation import CancellationError, CommandContext
from nightwatch.config import NightwatchConfig
from nightwatch.orchestrator import Orchestrator
from nightwatch.tool_executor import ToolExecutor, ToolResult, ToolStatus
from nightwatch.tool_params import NoParams
from services.camera.asi_camera import (
    ASICamera,
    ASISDKWrapper,
    CameraSettings,
    ImageFormat,
)
from services.safety_monitor.monitor import (
    AlertLevel,
    SafetyAction,
    SafetyMonitor,
    SafetyStatus,
)

# The HWS-001 mocked-SDK camera builder is exposed as the
# ``mocked_real_sdk_camera`` factory fixture in tests/conftest.py —
# inject it into each test that needs to construct a camera. Promoted
# 2026-05-25 (ARCH-003 fix-pass) out of tests/unit/test_camera_service.py
# so this file no longer needs a sys.path.insert cross-dir import hack.


def _make_unsafe_status(reason: str = "rain detected") -> SafetyStatus:
    """Construct a SafetyStatus that ``_notify_callbacks`` would deliver."""
    return SafetyStatus(
        timestamp=datetime.now(),
        action=SafetyAction.EMERGENCY_CLOSE,
        is_safe=False,
        reasons=[reason],
        alert_level=AlertLevel.EMERGENCY,
    )


def _make_safe_status() -> SafetyStatus:
    return SafetyStatus(
        timestamp=datetime.now(),
        action=SafetyAction.SAFE_TO_OBSERVE,
        is_safe=True,
        reasons=[],
        alert_level=AlertLevel.INFO,
    )


class _CameraAdapter:
    """Adapt the bare ASICamera to the orchestrator's service-registry
    `start()` lifecycle contract. The unit-test camera is already
    initialized via _build_mocked_real_sdk_camera; this adapter is a
    no-op shim that registers under name='camera'.
    """

    def __init__(self, camera: ASICamera):
        self.camera = camera

    async def start(self) -> None:
        # _build_mocked_real_sdk_camera flipped _initialized = True already
        return None

    async def stop(self) -> None:
        if self.camera._capturing:
            await self.camera.stop_capture()


@pytest.fixture
def fast_camera(tmp_path, monkeypatch, mocked_real_sdk_camera):
    """An ASICamera with _do_exposure/_save_fits stubbed for fast tests."""
    monkeypatch.setattr(ASISDKWrapper, "SDK_AVAILABLE", True)
    camera = mocked_real_sdk_camera(tmp_path, width=16, height=16)

    async def slow_do_exposure(exposure_sec=None, gain=None, callback=None):
        # 50ms per frame — slow enough that a cancel mid-burst lands
        # while one is in flight, fast enough that the test stays sub-second
        # in the steady-state path.
        await asyncio.sleep(0.05)
        return bytes([1] * (16 * 16 * 2))

    def stub_save_fits(*_args, **_kwargs):
        return True

    monkeypatch.setattr(camera, "_do_exposure", slow_do_exposure)
    monkeypatch.setattr(camera, "_save_fits", stub_save_fits)
    return camera


class TestSafetyTriggeredCancellation:
    """The ARCH-003 verify-line, plus targeted regressions."""

    @pytest.mark.asyncio
    async def test_safety_unsafe_callback_cancels_active_context(self):
        """SAFETY_UNSAFE → Orchestrator's active context is cancelled.

        Direct callback exercise: we don't need the SafetyMonitor's
        evaluate() loop here — we just verify that when the orchestrator
        registers its callback and the callback receives an unsafe
        status, the active context's token reports cancelled with the
        right reason.
        """
        config = NightwatchConfig()
        orchestrator = Orchestrator(config)

        ctx = CommandContext.new()
        orchestrator.set_active_context(ctx)

        # Fire the callback the way SafetyMonitor._notify_callbacks would.
        orchestrator._on_safety_change(_make_unsafe_status("wind gust 42 mph"))

        assert ctx.is_cancelled() is True
        assert ctx.token.reason is not None
        # Reason must surface BOTH the safety-action enum and the
        # human-readable cause so the voice formatter has something
        # useful to say.
        assert "EMERGENCY_CLOSE" in ctx.token.reason
        assert "wind gust 42 mph" in ctx.token.reason

    @pytest.mark.asyncio
    async def test_safety_safe_callback_does_not_cancel(self):
        """A SAFE_TO_OBSERVE status must never cancel an active context."""
        config = NightwatchConfig()
        orchestrator = Orchestrator(config)
        ctx = CommandContext.new()
        orchestrator.set_active_context(ctx)

        orchestrator._on_safety_change(_make_safe_status())

        assert ctx.is_cancelled() is False

    @pytest.mark.asyncio
    async def test_callback_with_no_active_context_is_noop(self):
        """Unsafe transition with no active command must not crash."""
        config = NightwatchConfig()
        orchestrator = Orchestrator(config)
        # No set_active_context call.
        orchestrator._on_safety_change(_make_unsafe_status())
        # Should reach here without raising — no active context to cancel.

    @pytest.mark.asyncio
    async def test_orchestrator_registers_callback_on_register_safety(
        self,
    ):
        """register_safety wires the cancel-on-unsafe callback onto the monitor.

        The orchestrator must register its callback when a SafetyMonitor
        is registered, not lazily at first command — otherwise the very
        first command after startup is uncovered. We exercise this
        directly via SafetyMonitor.register_callback (the public surface
        confirmed to exist + accept sync callbacks at line 277 of
        services/safety_monitor/monitor.py).
        """
        config = NightwatchConfig()
        orchestrator = Orchestrator(config)
        monitor = SafetyMonitor()

        callbacks_before = list(monitor._callbacks)
        orchestrator.register_safety(monitor, required=False)
        callbacks_after = list(monitor._callbacks)

        assert len(callbacks_after) == len(callbacks_before) + 1, (
            "register_safety should append exactly one orchestrator callback"
        )

    @pytest.mark.asyncio
    async def test_verify_line_capture_cancels_within_two_seconds(
        self, fast_camera
    ):
        """The spec's verify-line: 60s mock exposure, flip unsafe, abort < 2s.

        End-to-end exercise:
          1. Orchestrator with a real SafetyMonitor registered (which
             auto-wires the cancel callback).
          2. CommandContext set active on the orchestrator.
          3. start_capture(duration_sec=60, cancel_token=ctx.token).
          4. Background task waits 500ms, then delivers an unsafe status
             via the monitor's notify pipe.
          5. Within 2s of the unsafe delivery, camera._capturing must
             be False AND session.cancelled must be True.
        """
        config = NightwatchConfig()
        orchestrator = Orchestrator(config)
        monitor = SafetyMonitor()
        orchestrator.register_safety(monitor, required=False)

        ctx = CommandContext.new()
        orchestrator.set_active_context(ctx)

        # Start the 60-second mock exposure with the context's token.
        session = await fast_camera.start_capture(
            target="moon",
            duration_sec=60.0,
            settings=CameraSettings(exposure_ms=50.0, format=ImageFormat.FITS),
            cancel_token=ctx.token,
        )

        # Let ~10 frames go by, then flip safety.
        await asyncio.sleep(0.5)
        unsafe = _make_unsafe_status("rain detected by Hydreon")
        flip_at = time.monotonic()
        # Use the real monitor's notify pipe — proves the callback
        # registered by register_safety actually fires.
        await monitor._notify_callbacks(unsafe)

        # Wait for the capture loop to unwind. 2s budget per the spec.
        deadline = flip_at + 2.0
        while time.monotonic() < deadline and fast_camera._capturing:
            await asyncio.sleep(0.01)

        elapsed = time.monotonic() - flip_at
        assert elapsed < 2.0, (
            f"Capture did not abort within 2s of safety flip "
            f"(took {elapsed:.2f}s)"
        )
        assert fast_camera._capturing is False
        assert session.cancelled is True, (
            "Spec requires CANCELLED status, not FAILED"
        )
        assert session.complete is False
        # Reason should carry both the action enum and the human cause
        # so a voice formatter can say "Stopping capture: rain detected".
        assert "rain detected by Hydreon" in (session.error or "")


class TestProductionWiringThroughToolExecutor:
    """Production-path coverage: ToolExecutor.execute must auto-wire the active context.

    The other test class in this file pre-loads the orchestrator's
    active context by hand (``orchestrator.set_active_context(ctx)``)
    before kicking off the capture. That proves the cancel *callback*
    works but NOT that any production caller actually registers the
    context — Orchestrator.set_active_context / clear_active_context
    are only useful if something calls them during the live dispatch
    path. The only production caller that owns the CommandContext for
    the lifetime of a long-running tool is ToolExecutor.execute(), so
    the wire-up belongs there.

    Without that wiring, a rain event during a real voice-driven
    ``capture`` would hit ``_on_safety_change`` with
    ``self._active_context is None`` and silently no-op — the exposure
    would run to completion AFTER the enclosure had already started
    closing. Test exercises the wire-up via the real ToolExecutor
    dispatch path with NO manual set_active_context call.
    """

    @pytest.mark.asyncio
    async def test_production_wiring_through_tool_executor(self):
        """ToolExecutor.execute auto-registers the context as active.

        Failure mode this guards against: a long-running handler is
        dispatched through ToolExecutor.execute(...,  context=ctx), a
        safety transition fires mid-flight, the orchestrator's
        ``_on_safety_change`` reads ``self._active_context`` and finds
        ``None`` because nothing told it about this command. The
        handler never sees a cancel, the exposure runs to completion,
        and the enclosure-close race wins. This test pins down the
        opposite: execute() must set the active context before
        dispatch and clear it after (compare-and-clear) so the
        callback hits the right token even when the test does NOT
        manually pre-load the context.
        """
        config = NightwatchConfig()
        orchestrator = Orchestrator(config)
        monitor = SafetyMonitor()
        # register_safety wires the cancel-on-unsafe callback. This is
        # the production path — voice startup does this once per boot.
        orchestrator.register_safety(monitor, required=False)

        tool_executor = ToolExecutor(orchestrator)

        # A mocked long-running handler that mimics a 30s exposure.
        # It races its own work against the cancel token so we can
        # observe the abort the same way the real ASICamera does.
        handler_started = asyncio.Event()
        handler_observed_cancel: dict = {"reason": None}

        async def fake_capture_handler(
            params: NoParams, context: CommandContext | None = None
        ) -> ToolResult:
            assert context is not None, (
                "wiring fix should ensure execute() forwards a non-None context"
            )
            handler_started.set()
            try:
                # Race a 30s "exposure" against the cancel token's wait.
                await asyncio.wait_for(
                    context.token.wait_cancelled(), timeout=30.0
                )
                # If wait_cancelled returns the token was cancelled.
                handler_observed_cancel["reason"] = context.token.reason
                raise CancellationError(context.token.reason or "")
            except TimeoutError:
                return ToolResult(
                    tool_name="capture", status=ToolStatus.SUCCESS
                )

        tool_executor.register_handler(
            "capture", fake_capture_handler, param_model=NoParams
        )

        ctx = CommandContext.new()

        # NOTE: deliberately NO `orchestrator.set_active_context(ctx)`
        # call here. This is the whole point — production callers
        # supply the context via execute(); the wire-up must happen
        # inside execute(), not at the call site.
        execute_task = asyncio.create_task(
            tool_executor.execute("capture", {}, context=ctx)
        )

        # Wait for the handler to actually start, so we know the
        # context is live and execute() has had a chance to register it.
        await asyncio.wait_for(handler_started.wait(), timeout=1.0)

        # Confirm the production wiring did its job: the orchestrator
        # should now consider this context active.
        assert orchestrator._active_context is ctx, (
            "ToolExecutor.execute must call orchestrator.set_active_context "
            "for safety transitions to find the right token"
        )

        # Now fire the safety callback through the real monitor pipe.
        # If the wiring is missing, _active_context will be None and
        # the cancel is silently dropped → the handler runs forever.
        flip_at = time.monotonic()
        await monitor._notify_callbacks(
            _make_unsafe_status("rain detected by Hydreon")
        )

        # The cancel should propagate to the in-flight handler within
        # the 2s spec budget. We await the task itself to confirm the
        # full execute() unwind path also clears the active context.
        result = await asyncio.wait_for(execute_task, timeout=2.5)
        elapsed = time.monotonic() - flip_at
        assert elapsed < 2.0, (
            f"ToolExecutor did not unwind within 2s of safety flip "
            f"(took {elapsed:.2f}s)"
        )
        assert handler_observed_cancel["reason"] is not None, (
            "Handler must have observed the cancel — proves the wire-up "
            "delivered the cancel signal to the right token"
        )
        assert "rain detected by Hydreon" in (
            handler_observed_cancel["reason"] or ""
        )

        # execute() must map the CancellationError to CANCELLED status.
        assert result.status == ToolStatus.CANCELLED, (
            f"expected CANCELLED, got {result.status}"
        )

        # After execute() returns, the active context must be cleared
        # (compare-and-clear semantics so a stale clear can't drop a
        # newer command's marker).
        assert orchestrator._active_context is None, (
            "ToolExecutor.execute must call clear_active_context in finally"
        )
