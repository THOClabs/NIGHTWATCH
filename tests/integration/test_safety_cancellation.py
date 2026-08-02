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
    SafetyThresholds,
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


# =============================================================================
# SAFE-001: cancel-BEFORE-close ordering through the production run() loop
# =============================================================================
#
# ARCH-003 proved the cancel signal flows end-to-end when callbacks fire.
# SAFE-001 closes the ordering loophole that ARCH-003 explicitly deferred:
# in ``SafetyMonitor.run()`` the action (``execute_action``) was previously
# dispatched BEFORE the callbacks (``_notify_callbacks``) fired, which on
# the EMERGENCY_CLOSE path meant the enclosure started closing while the
# in-flight exposure was still draining frames — the Risk #2 water-damage
# scenario.
#
# These tests exercise the PRODUCTION code path (the ``run()`` loop body)
# rather than calling ``_notify_callbacks`` directly. Per LEARNINGS
# 2026-05-25 ARCH-003, "infrastructure ship needs a production caller";
# the ordering fix only matters if the production caller honors it.


class _RecordingMount:
    """Mount stub that timestamps its stop/park calls for ordering checks."""

    def __init__(self, events: list[tuple[str, float]]):
        self._events = events
        self.parked = False

    async def stop(self) -> None:
        self._events.append(("mount_stop", time.monotonic()))

    async def park(self) -> None:
        self._events.append(("mount_park", time.monotonic()))
        self.parked = True


class _RecordingEnclosure:
    """Enclosure stub that timestamps its close calls.

    The signature is sync because ``execute_action`` calls
    ``self.enclosure.close()`` without awaiting — matches the existing
    LOW_BATTERY_SHUTDOWN call site at monitor.py:1470.
    """

    def __init__(self, events: list[tuple[str, float]]):
        self._events = events
        self.closed = False

    def close(self) -> None:
        self._events.append(("enclosure_close", time.monotonic()))
        self.closed = True


class TestSafe001OrderingThroughRunLoop:
    """SAFE-001 verify-line: cancel fires BEFORE close in production run() loop.

    The ordering bug ARCH-003's docstring deferred to SAFE-001:
    ``SafetyMonitor.run()`` used to invoke ``execute_action(status.action)``
    (which drives the enclosure) BEFORE ``_notify_callbacks(status)``
    (which fires the orchestrator's cancel-on-unsafe hook). This class
    exercises the ``run()`` loop body via a short-poll-interval task and
    asserts the inverted ordering: cancel event MUST be recorded before
    any enclosure-close event.

    Why not call ``_notify_callbacks`` directly? Because that's the test
    shape that LET the ordering bug ship under ARCH-003. The whole point
    of SAFE-001 is to verify the fix is in the production caller.
    """

    @pytest.mark.asyncio
    async def test_run_loop_fires_cancel_before_enclosure_close(self):
        """In ``run()``, EMERGENCY_CLOSE delivers cancel BEFORE enclosure.close.

        Setup:
          * SafetyMonitor with fake mount + fake enclosure that timestamp
            their write calls into a shared event list.
          * Orchestrator with an active CommandContext; the callback
            registered by ``register_safety`` will cancel that context
            on an unsafe transition. The cancel itself is timestamped
            via a thin wrapper around the orchestrator's hook.
          * ``evaluate()`` is monkeypatched to return EMERGENCY_CLOSE so
            we don't have to build a full sensor environment.
          * ``_unsafe_since`` is pre-set past ``unsafe_duration_to_park``
            so the run-loop fires the action on the first iteration.

        Assert:
          * ``cancel`` event timestamp < ``enclosure_close`` event timestamp.
          * Context is cancelled.
          * Enclosure was eventually closed (the irreversible safety
            action still runs — cancel-before-close, not cancel-INSTEAD-OF-close).
        """
        events: list[tuple[str, float]] = []
        mount = _RecordingMount(events)
        enclosure = _RecordingEnclosure(events)

        # Tight thresholds: the run loop should act on the first
        # iteration. cancel_settle_timeout_s small so the test stays fast.
        thresholds = SafetyThresholds(
            unsafe_duration_to_park=0.0,
            cancel_settle_timeout_s=0.05,
        )
        monitor = SafetyMonitor(
            thresholds=thresholds,
            mount_controller=mount,
            enclosure_controller=enclosure,
        )

        config = NightwatchConfig()
        orchestrator = Orchestrator(config)
        orchestrator.register_safety(monitor, required=False)

        ctx = CommandContext.new()
        orchestrator.set_active_context(ctx)

        # Timestamp the cancel by wrapping the token's cancel method.
        original_cancel = ctx.token.cancel

        def timestamped_cancel(reason: str) -> None:
            events.append(("cancel", time.monotonic()))
            original_cancel(reason)

        ctx.token.cancel = timestamped_cancel  # type: ignore[method-assign]

        # Pin evaluate() to EMERGENCY_CLOSE so the loop fires the
        # action+callbacks deterministically.
        unsafe_status = SafetyStatus(
            timestamp=datetime.now(),
            action=SafetyAction.EMERGENCY_CLOSE,
            is_safe=False,
            reasons=["rain detected by Hydreon"],
            alert_level=AlertLevel.EMERGENCY,
        )
        monitor.evaluate = lambda: unsafe_status  # type: ignore[method-assign]

        # Pre-set the unsafe-since so the duration check fires the
        # action on iteration #1 (otherwise the loop would wait until
        # unsafe_duration_to_park has elapsed).
        from datetime import timedelta
        monitor._unsafe_since = datetime.now() - timedelta(seconds=10)

        # Drive the production run() loop briefly. poll_interval tiny so
        # the first iteration runs immediately; we cancel after enough
        # wall-time for the cancel_settle wait + enclosure call to land.
        run_task = asyncio.create_task(monitor.run(poll_interval=0.01))
        # Wait long enough for one full iteration including the settle wait.
        await asyncio.sleep(0.5)
        monitor.stop()
        try:
            await asyncio.wait_for(run_task, timeout=2.0)
        except TimeoutError:
            run_task.cancel()
            raise

        # ORDERING ASSERTION (the whole point of this test):
        event_names = [name for name, _ts in events]
        assert "cancel" in event_names, (
            f"cancel callback was never fired; events={event_names}"
        )
        assert "enclosure_close" in event_names, (
            "SAFE-001 makes EMERGENCY_CLOSE actually close the enclosure; "
            f"events={event_names}"
        )

        cancel_ts = next(ts for name, ts in events if name == "cancel")
        close_ts = next(
            ts for name, ts in events if name == "enclosure_close"
        )
        assert cancel_ts < close_ts, (
            f"SAFE-001 ordering violation: cancel@{cancel_ts:.4f} must "
            f"fire BEFORE enclosure_close@{close_ts:.4f}. "
            f"events={events}"
        )

        # Context cancellation must have actually landed.
        assert ctx.is_cancelled() is True
        assert ctx.token.reason is not None
        assert "EMERGENCY_CLOSE" in ctx.token.reason
        assert "rain detected by Hydreon" in ctx.token.reason

        # And the irreversible safety action still ran (cancel-BEFORE-close,
        # not cancel-INSTEAD-OF-close).
        assert enclosure.closed is True

    @pytest.mark.asyncio
    async def test_cancel_settle_wait_only_fires_for_emergency_close(self):
        """The settle wait is gated on EMERGENCY_CLOSE — not every transition.

        Lower-severity actions (SAFE_TO_OBSERVE re-enable, DEW_WARNING,
        etc.) don't drive the enclosure and don't need the settle wait.
        Adding it unconditionally would penalize every state transition
        with the timeout. This test confirms the gate: a non-EMERGENCY
        action transition runs the loop without invoking the helper.
        """
        events: list[tuple[str, float]] = []
        mount = _RecordingMount(events)
        enclosure = _RecordingEnclosure(events)

        thresholds = SafetyThresholds(
            unsafe_duration_to_park=0.0,
            cancel_settle_timeout_s=5.0,  # Big enough we'd notice if it fired.
        )
        monitor = SafetyMonitor(
            thresholds=thresholds,
            mount_controller=mount,
            enclosure_controller=enclosure,
        )

        # A non-EMERGENCY warning action — no enclosure close, no settle wait.
        warning_status = SafetyStatus(
            timestamp=datetime.now(),
            action=SafetyAction.DEW_WARNING,
            is_safe=False,
            reasons=["dew point margin low"],
            alert_level=AlertLevel.WARNING,
        )
        monitor.evaluate = lambda: warning_status  # type: ignore[method-assign]

        from datetime import timedelta
        monitor._unsafe_since = datetime.now() - timedelta(seconds=10)

        # Wrap the settle helper so we can detect if it was called.
        settle_called: dict = {"count": 0}
        original_settle = monitor._wait_for_cancellations_to_drain

        async def counting_settle(timeout_s: float = 2.0) -> None:
            settle_called["count"] += 1
            await original_settle(timeout_s)

        monitor._wait_for_cancellations_to_drain = counting_settle  # type: ignore[method-assign]

        start = time.monotonic()
        run_task = asyncio.create_task(monitor.run(poll_interval=0.01))
        await asyncio.sleep(0.2)
        monitor.stop()
        try:
            await asyncio.wait_for(run_task, timeout=2.0)
        except TimeoutError:
            run_task.cancel()
            raise
        elapsed = time.monotonic() - start

        assert settle_called["count"] == 0, (
            f"settle helper must NOT fire for non-EMERGENCY actions "
            f"(action=DEW_WARNING), got {settle_called['count']} calls"
        )
        # And the loop didn't block on the 5s settle wait.
        assert elapsed < 1.5, (
            f"non-EMERGENCY transition shouldn't trigger settle wait; "
            f"loop took {elapsed:.2f}s"
        )
