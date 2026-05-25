"""Unit tests for SAFE-004: hardware-level fail-safe path.

Spec verify line:
    Kill safety_monitor process; within 90s ``enclosure_controller.close()``
    is invoked by the watchdog and a SAFETY_VETO event fires.

These tests exercise ``WatchdogManager`` directly. Time is simulated by
backdating ``ServiceStatus.last_heartbeat`` rather than waiting wall-clock
seconds — the production loop runs ``_check_services`` every 5s, but the
loop's body is what we test, by invoking ``_check_services_once`` (added
in SAFE-004 to expose a single iteration for testing).

The fail-safe contract under test:

* ``safety_monitor`` is registered as a critical service with a 90s
  heartbeat-timeout.
* If the watchdog observes the timeout and an enclosure is registered via
  ``set_enclosure``, the watchdog directly calls ``enclosure.close(
  emergency=True)`` and fires the registered ``safety_veto_callback``.
* The veto callback fires *after* the close attempt regardless of whether
  the close itself raised.
* The failsafe is idempotent — it fires once per timeout episode and does
  not re-fire on every 5s check iteration until safety_monitor heartbeats
  again.
* If no enclosure is registered (dev/simulator opt-out), the watchdog
  does not crash; it logs a critical message and still fires the veto
  callback so observers can react.
* A healthy heartbeating safety_monitor never triggers the failsafe
  (regression guard for accidental firing during normal operation).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from nightwatch.watchdog import (
    DEFAULT_CONFIGS,
    ServiceState,
    ServiceType,
    WatchdogManager,
)
from services.safety_monitor.monitor import SafetyAction


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


def _make_fake_enclosure(close_result: bool = True, raises: Exception | None = None):
    """Build an AsyncMock that mimics ``EnclosureServiceProtocol.close``.

    The real ``RoofController.close`` accepts ``emergency: bool = False``.
    """
    enclosure = MagicMock()
    if raises is not None:
        enclosure.close = AsyncMock(side_effect=raises)
    else:
        enclosure.close = AsyncMock(return_value=close_result)
    return enclosure


def _backdate_heartbeat(manager: WatchdogManager, service: ServiceType, seconds_ago: float):
    """Force a watchdog's last_heartbeat to ``seconds_ago`` in the past."""
    wd = manager.get_watchdog(service)
    assert wd is not None, f"{service} watchdog not registered"
    wd.status.last_heartbeat = datetime.now() - timedelta(seconds=seconds_ago)
    wd.status.state = ServiceState.HEALTHY


# ---------------------------------------------------------------------------
# Enum + config
# ---------------------------------------------------------------------------


class TestSafetyMonitorWatchdogConfig:
    """The watchdog registers safety_monitor with the right knobs."""

    def test_safety_monitor_service_type_exists(self):
        """ServiceType has SAFETY_MONITOR (SAFE-004 adds it)."""
        assert hasattr(ServiceType, "SAFETY_MONITOR")
        assert ServiceType.SAFETY_MONITOR.value == "safety_monitor"

    def test_safety_monitor_default_config(self):
        """Default config: timeout >= 90s and critical=True."""
        assert ServiceType.SAFETY_MONITOR in DEFAULT_CONFIGS
        cfg = DEFAULT_CONFIGS[ServiceType.SAFETY_MONITOR]
        # Spec: ">90s" timeout — using 90.0 as the documented threshold.
        assert cfg.timeout_sec >= 90.0
        # Spec: failure of safety_monitor MUST be safety-critical.
        assert cfg.critical is True

    def test_safety_action_safety_veto_exists(self):
        """SafetyAction.SAFETY_VETO enum member exists (SAFE-004)."""
        assert hasattr(SafetyAction, "SAFETY_VETO")
        assert SafetyAction.SAFETY_VETO.value == "safety_veto"


# ---------------------------------------------------------------------------
# Manager wiring API
# ---------------------------------------------------------------------------


class TestWatchdogFailsafeAPI:
    """Surface of the new ``WatchdogManager`` API for SAFE-004."""

    def test_set_enclosure(self):
        m = WatchdogManager()
        encl = _make_fake_enclosure()
        m.set_enclosure(encl)
        assert m._enclosure is encl

    def test_set_safety_veto_callback(self):
        m = WatchdogManager()
        cb = AsyncMock()
        m.set_safety_veto_callback(cb)
        assert m._safety_veto_callback is cb


# ---------------------------------------------------------------------------
# Failsafe behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestFailsafeBehavior:
    """End-to-end behaviour of the SAFE-004 failsafe path."""

    async def test_spec_verify_safety_monitor_timeout_closes_enclosure(self):
        """Spec verify: safety_monitor silent >90s -> enclosure.close + veto.

        This is the test that demonstrates the verify-line scenario.
        """
        manager = WatchdogManager()
        enclosure = _make_fake_enclosure()
        veto_cb = AsyncMock()
        manager.set_enclosure(enclosure)
        manager.set_safety_veto_callback(veto_cb)

        # Simulate "kill safety_monitor": last heartbeat was 100s ago.
        _backdate_heartbeat(manager, ServiceType.SAFETY_MONITOR, seconds_ago=100.0)

        # Run one watchdog iteration (the body of _check_services).
        await manager._check_services_once()

        # Verify (1): enclosure.close was called with emergency=True.
        enclosure.close.assert_awaited_once_with(emergency=True)

        # Verify (2): SAFETY_VETO event fired with safety_monitor cause.
        veto_cb.assert_awaited_once()
        args, _ = veto_cb.call_args
        assert args[0] == ServiceType.SAFETY_MONITOR
        # Reason should be a non-empty string identifying the timeout cause.
        assert isinstance(args[1], str) and args[1]

    async def test_healthy_safety_monitor_does_not_trigger_failsafe(self):
        """Regression guard: heartbeating safety_monitor never fires veto."""
        manager = WatchdogManager()
        enclosure = _make_fake_enclosure()
        veto_cb = AsyncMock()
        manager.set_enclosure(enclosure)
        manager.set_safety_veto_callback(veto_cb)

        # Fresh heartbeat now.
        manager.heartbeat(ServiceType.SAFETY_MONITOR)

        # Run several iterations.
        for _ in range(5):
            await manager._check_services_once()

        enclosure.close.assert_not_called()
        veto_cb.assert_not_called()

    async def test_timeout_threshold_respected_below(self):
        """At t-80s (< 90s threshold), no failsafe yet."""
        manager = WatchdogManager()
        enclosure = _make_fake_enclosure()
        veto_cb = AsyncMock()
        manager.set_enclosure(enclosure)
        manager.set_safety_veto_callback(veto_cb)

        _backdate_heartbeat(manager, ServiceType.SAFETY_MONITOR, seconds_ago=80.0)
        await manager._check_services_once()

        enclosure.close.assert_not_called()
        veto_cb.assert_not_called()

    async def test_timeout_threshold_respected_above(self):
        """At t-100s (> 90s threshold), failsafe fires."""
        manager = WatchdogManager()
        enclosure = _make_fake_enclosure()
        veto_cb = AsyncMock()
        manager.set_enclosure(enclosure)
        manager.set_safety_veto_callback(veto_cb)

        _backdate_heartbeat(manager, ServiceType.SAFETY_MONITOR, seconds_ago=100.0)
        await manager._check_services_once()

        enclosure.close.assert_awaited_once_with(emergency=True)
        veto_cb.assert_awaited_once()

    async def test_veto_callback_fires_even_when_close_raises(self):
        """If enclosure.close raises, the veto callback STILL fires."""
        manager = WatchdogManager()
        enclosure = _make_fake_enclosure(raises=RuntimeError("motor jammed"))
        veto_cb = AsyncMock()
        manager.set_enclosure(enclosure)
        manager.set_safety_veto_callback(veto_cb)

        _backdate_heartbeat(manager, ServiceType.SAFETY_MONITOR, seconds_ago=100.0)
        # Must not bubble — watchdog absorbs hardware errors.
        await manager._check_services_once()

        enclosure.close.assert_awaited_once_with(emergency=True)
        veto_cb.assert_awaited_once()

    async def test_failsafe_idempotent_does_not_refire(self):
        """Repeated check loops in the same timeout episode fire once."""
        manager = WatchdogManager()
        enclosure = _make_fake_enclosure()
        veto_cb = AsyncMock()
        manager.set_enclosure(enclosure)
        manager.set_safety_veto_callback(veto_cb)

        _backdate_heartbeat(manager, ServiceType.SAFETY_MONITOR, seconds_ago=100.0)

        # Run 5 iterations back-to-back.
        for _ in range(5):
            await manager._check_services_once()

        # Should still be exactly one close + one veto.
        assert enclosure.close.await_count == 1
        assert veto_cb.await_count == 1

    async def test_failsafe_rearms_after_recovery(self):
        """After heartbeat resumes, a new timeout fires the failsafe again."""
        manager = WatchdogManager()
        enclosure = _make_fake_enclosure()
        veto_cb = AsyncMock()
        manager.set_enclosure(enclosure)
        manager.set_safety_veto_callback(veto_cb)

        # Episode 1: timeout -> failsafe fires once.
        _backdate_heartbeat(manager, ServiceType.SAFETY_MONITOR, seconds_ago=100.0)
        await manager._check_services_once()
        assert enclosure.close.await_count == 1

        # Recovery: heartbeat resumes.
        manager.heartbeat(ServiceType.SAFETY_MONITOR)
        await manager._check_services_once()
        # Still 1 (no re-fire on healthy state).
        assert enclosure.close.await_count == 1

        # Episode 2: new timeout -> failsafe fires again.
        _backdate_heartbeat(manager, ServiceType.SAFETY_MONITOR, seconds_ago=100.0)
        await manager._check_services_once()
        assert enclosure.close.await_count == 2
        assert veto_cb.await_count == 2

    async def test_orchestrator_wires_enclosure_into_watchdog(self):
        """Production wiring: ``register_enclosure`` calls watchdog.set_enclosure.

        Per LEARNINGS 2026-05-25 ARCH-003 ("infrastructure ship needs a
        production caller"), the watchdog's failsafe path must be
        reachable from a real production code path — registering an
        enclosure via ``Orchestrator.register_enclosure`` MUST make the
        watchdog able to drive that enclosure when safety_monitor
        times out, with no extra wiring required by the caller.
        """
        from nightwatch.config import NightwatchConfig
        from nightwatch.orchestrator import Orchestrator

        orch = Orchestrator(NightwatchConfig())
        # SAFE-004 contract: the orchestrator owns a watchdog by default.
        assert orch.watchdog is not None

        enclosure = _make_fake_enclosure()
        orch.register_enclosure(enclosure, required=False)

        # The watchdog now knows about the enclosure.
        assert orch.watchdog._enclosure is enclosure

        # And a SAFETY_VETO-emitting callback is wired.
        assert orch.watchdog._safety_veto_callback is not None

    async def test_orchestrator_safety_veto_emits_event(self):
        """The orchestrator's default veto callback emits EventType.SAFETY_VETO.

        Observability path: when the watchdog fires the failsafe, the
        orchestrator's event listeners (TTS alerts, telemetry sinks,
        UI dashboards) must learn about it via the standard event bus.
        """
        from nightwatch.config import NightwatchConfig
        from nightwatch.orchestrator import EventType, Orchestrator

        orch = Orchestrator(NightwatchConfig())
        enclosure = _make_fake_enclosure()
        orch.register_enclosure(enclosure, required=False)

        # Subscribe a listener to capture the event.
        captured: list = []

        async def _listener(event):
            captured.append(event)

        orch._event_listeners.setdefault(EventType.SAFETY_VETO, []).append(_listener)

        # Trigger failsafe via the watchdog's veto callback directly.
        await orch.watchdog._safety_veto_callback(
            ServiceType.SAFETY_MONITOR, "test reason"
        )

        assert len(captured) == 1
        evt = captured[0]
        assert evt.event_type == EventType.SAFETY_VETO
        assert "safety_monitor" in evt.message.lower()
        assert evt.data.get("service") == "safety_monitor"
        assert evt.data.get("reason") == "test reason"

    async def test_no_enclosure_registered_does_not_crash(self):
        """Without ``set_enclosure``, watchdog logs critical, fires veto, no crash.

        This is the dev/simulator opt-out: don't wire an enclosure, the
        failsafe close becomes a no-op. The veto callback STILL fires so
        observability still records the safety event.
        """
        manager = WatchdogManager()
        veto_cb = AsyncMock()
        # Intentionally NOT calling set_enclosure.
        manager.set_safety_veto_callback(veto_cb)

        _backdate_heartbeat(manager, ServiceType.SAFETY_MONITOR, seconds_ago=100.0)

        # Must not raise.
        await manager._check_services_once()

        # Veto callback still fires so observers learn about the event.
        veto_cb.assert_awaited_once()
        args, _ = veto_cb.call_args
        assert args[0] == ServiceType.SAFETY_MONITOR
        # Reason should hint at no enclosure registered.
        assert "enclosure" in args[1].lower()
