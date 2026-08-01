"""Integration tests for 1-06: orchestrator <-> watchdog wiring.

The orchestrator owns a ``WatchdogManager`` but previously never
started it, stopped it, or fed it heartbeats — so the SAFE-004
hardware-level fail-safe (a silent safety_monitor closing the enclosure
directly) could never actually fire in production. These tests exercise
the production wiring end-to-end:

* after ``orch.start()`` the watchdog is running;
* backdating the SAFETY_MONITOR heartbeat past its timeout and running
  one watchdog check iteration drives ``enclosure.close(emergency=True)``;
* ``orch.shutdown()`` stops the watchdog.

Time is simulated by backdating ``ServiceStatus.last_heartbeat`` rather
than sleeping wall-clock seconds (same technique as the SAFE-004 unit
tests). The watchdog's periodic loop body is invoked directly via
``_check_services_once`` for determinism.

Known residual (noted in the PR): the orchestrator heartbeats the
watchdog off each service's ``is_running`` flag in the health loop, not
off actual ``SafetyMonitor.evaluate()``-loop progress. A safety monitor
whose object is alive but whose evaluation loop has wedged would still
be heartbeated. The fuller fix injects a heartbeat inside
``SafetyMonitor.run()``; this change wires the plumbing that makes that
heartbeat reach a running watchdog.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from nightwatch.config import NightwatchConfig
from nightwatch.orchestrator import Orchestrator
from nightwatch.watchdog import ServiceState, ServiceType


def _make_fake_enclosure():
    """AsyncMock enclosure whose close/start/stop are awaitable."""
    enclosure = MagicMock()
    enclosure.close = AsyncMock(return_value=True)
    enclosure.start = AsyncMock()
    enclosure.stop = AsyncMock()
    return enclosure


def _backdate_heartbeat(orch: Orchestrator, service: ServiceType, seconds_ago: float):
    wd = orch.watchdog.get_watchdog(service)
    assert wd is not None, f"{service} watchdog not registered"
    wd.status.last_heartbeat = datetime.now() - timedelta(seconds=seconds_ago)
    wd.status.state = ServiceState.HEALTHY


@pytest.mark.asyncio
async def test_start_runs_watchdog():
    """After orch.start(), the watchdog background loop is running."""
    orch = Orchestrator(NightwatchConfig())
    assert orch.watchdog._running is False

    started = await orch.start()
    try:
        assert started is True
        assert orch.watchdog._running is True
    finally:
        await orch.shutdown(safe=False)


@pytest.mark.asyncio
async def test_shutdown_stops_watchdog():
    """orch.shutdown() stops the watchdog it started."""
    orch = Orchestrator(NightwatchConfig())
    await orch.start()

    assert orch.watchdog._running is True

    await orch.shutdown(safe=False)
    assert orch.watchdog._running is False


@pytest.mark.asyncio
async def test_safety_monitor_timeout_closes_enclosure_after_start():
    """A stale SAFETY_MONITOR heartbeat drives the emergency enclosure close.

    This is the whole point of wiring the watchdog into the orchestrator:
    once running, a silent safety monitor must reach the hardware
    fail-safe and close the roof.
    """
    orch = Orchestrator(NightwatchConfig())
    enclosure = _make_fake_enclosure()
    orch.register_enclosure(enclosure, required=False)

    await orch.start()
    try:
        assert orch.watchdog._running is True

        # Simulate "safety monitor went silent 100s ago" (> 90s timeout).
        _backdate_heartbeat(orch, ServiceType.SAFETY_MONITOR, seconds_ago=100.0)

        # Drive one deterministic watchdog iteration.
        await orch.watchdog._check_services_once()

        enclosure.close.assert_awaited_once_with(emergency=True)
    finally:
        await orch.shutdown(safe=False)
