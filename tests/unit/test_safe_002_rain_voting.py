"""Unit tests for SAFE-002: dual-redundant rain sensor voting.

Covers the 1-of-2 / 2-of-2 voting policy in
``SafetyMonitor._evaluate_weather`` plus the safety-cascade
integration (callback fires when voting flips unsafe).

The spec verify case (kickoff):
    Ecowitt=dry + secondary=rain
    -> SafetyStatus.is_safe is False
    -> reason contains "rain detected (1 of 2 sensors)"

Fail-safe policy under test (chosen per implementation):
    * Either sensor reports rain -> unsafe ("N of 2 sensors")
    * Either sensor missing/stale -> unsafe (zero-of-two valid)
    * Both fresh + both dry      -> safe (re: rain; other checks may still
      fail, but the rain-voting branch passes)

These tests import the package path ``services.safety_monitor.monitor``
to avoid the legacy ``sys.path.insert(0, "/workspaces/...")`` shim
used in ``tests/unit/test_safety_monitor.py`` (which is broken on
non-Codespaces machines and tracked separately).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest

from services.safety_monitor.monitor import (
    SafetyAction,
    SafetyMonitor,
    SafetyStatus,
    SafetyThresholds,
)
from services.weather.secondary_rain import (
    SECONDARY_RAIN_SENSOR_IDS,
    SecondaryRainReading,
)


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


@dataclass
class _MockWeather:
    """Minimal Ecowitt-shape stand-in.

    Mirrors the attributes ``SafetyMonitor._evaluate_weather`` reads via
    ``hasattr``: rain flags, wind, humidity, temperature, dew point.
    """

    is_raining: bool = False
    rain_rate_in_hr: float = 0.0
    wind_speed_mph: float = 5.0
    wind_gust_mph: float = 8.0
    humidity_percent: float = 40.0
    temperature_f: float = 55.0
    dew_point_f: float = 30.0


def _fresh_secondary(*, is_raining: bool) -> SecondaryRainReading:
    """Build a secondary reading with the current timestamp."""
    return SecondaryRainReading(
        is_raining=is_raining,
        timestamp=datetime.now(),
        sensor_id="hydreon-rg15",
    )


# ---------------------------------------------------------------------------
# SecondaryRainReading dataclass
# ---------------------------------------------------------------------------


class TestSecondaryRainReading:
    """The new sensor-reading shape is frozen and minimally typed."""

    def test_default_sensor_id(self):
        reading = SecondaryRainReading(
            is_raining=False, timestamp=datetime.now()
        )
        assert reading.sensor_id == "secondary"

    def test_frozen(self):
        reading = SecondaryRainReading(
            is_raining=False, timestamp=datetime.now()
        )
        # Minor #7: tighten from bare Exception to the precise type the
        # frozen dataclass raises so future regressions (e.g. removing
        # frozen=True) fail loudly instead of being absorbed by a
        # different exception subclass.
        with pytest.raises(dataclasses.FrozenInstanceError):
            reading.is_raining = True  # type: ignore[misc]

    def test_rejects_unknown_sensor_id(self):
        """Minor #4: sensor_id must come from the curated allowlist."""
        with pytest.raises(ValueError, match="sensor_id"):
            SecondaryRainReading(
                is_raining=False,
                timestamp=datetime.now(),
                sensor_id="some-arbitrary-typo",
            )

    def test_accepts_each_allowlisted_sensor_id(self):
        """Smoke: every value in the allowlist constructs cleanly."""
        for sensor_id in SECONDARY_RAIN_SENSOR_IDS:
            reading = SecondaryRainReading(
                is_raining=False,
                timestamp=datetime.now(),
                sensor_id=sensor_id,
            )
            assert reading.sensor_id == sensor_id


# ---------------------------------------------------------------------------
# update_secondary_rain_sensor public API
# ---------------------------------------------------------------------------


class TestUpdateSecondaryRainSensor:
    """The setter mirrors ``update_weather``'s shape: async, no I/O."""

    @pytest.mark.asyncio
    async def test_stores_reading_in_sensor_slot(self):
        monitor = SafetyMonitor()
        reading = _fresh_secondary(is_raining=False)

        await monitor.update_secondary_rain_sensor(reading)

        assert monitor._secondary_rain_data is not None
        assert monitor._secondary_rain_data.value is reading
        assert monitor._secondary_rain_data.is_valid is True

    @pytest.mark.asyncio
    async def test_overwrites_previous_reading(self):
        monitor = SafetyMonitor()
        await monitor.update_secondary_rain_sensor(
            _fresh_secondary(is_raining=False)
        )
        new = _fresh_secondary(is_raining=True)

        await monitor.update_secondary_rain_sensor(new)

        assert monitor._secondary_rain_data is not None
        assert monitor._secondary_rain_data.value is new


# ---------------------------------------------------------------------------
# _evaluate_weather voting policy
# ---------------------------------------------------------------------------


class TestRainSensorVoting:
    """The voting matrix.

    Asymmetric by design: rain-positive from either sensor closes the
    enclosure; only mutual dry permits operation. Conservative on
    missing data.
    """

    @pytest.mark.asyncio
    async def test_spec_verify_ecowitt_dry_secondary_rain(self):
        """Kickoff verify case.

        Ecowitt=dry + secondary=rain -> is_safe False, reason cites
        "rain detected (1 of 2 sensors)".
        """
        monitor = SafetyMonitor()
        await monitor.update_weather(_MockWeather(is_raining=False))
        await monitor.update_secondary_rain_sensor(
            _fresh_secondary(is_raining=True)
        )
        # Daylight must be safe so the voting reason is the sole cause.
        await monitor.update_sun_altitude(-18.0)

        status = monitor.evaluate()

        assert status.is_safe is False
        assert any(
            "rain detected (1 of 2 sensors)" in r for r in status.reasons
        ), f"reasons={status.reasons!r}"

    @pytest.mark.asyncio
    async def test_symmetric_ecowitt_rain_secondary_dry(self):
        """Ecowitt=rain + secondary=dry -> unsafe, '1 of 2 sensors'."""
        monitor = SafetyMonitor()
        await monitor.update_weather(_MockWeather(is_raining=True))
        await monitor.update_secondary_rain_sensor(
            _fresh_secondary(is_raining=False)
        )
        await monitor.update_sun_altitude(-18.0)

        status = monitor.evaluate()

        assert status.is_safe is False
        assert any(
            "rain detected (1 of 2 sensors)" in r for r in status.reasons
        ), f"reasons={status.reasons!r}"

    @pytest.mark.asyncio
    async def test_both_raining_marks_2_of_2(self):
        monitor = SafetyMonitor()
        await monitor.update_weather(_MockWeather(is_raining=True))
        await monitor.update_secondary_rain_sensor(
            _fresh_secondary(is_raining=True)
        )
        await monitor.update_sun_altitude(-18.0)

        status = monitor.evaluate()

        assert status.is_safe is False
        assert any(
            "rain detected (2 of 2 sensors)" in r for r in status.reasons
        ), f"reasons={status.reasons!r}"

    @pytest.mark.asyncio
    async def test_both_dry_passes_rain_check(self):
        """Both sensors dry + safe wind/humidity/daylight -> safe."""
        monitor = SafetyMonitor()
        await monitor.update_weather(_MockWeather(is_raining=False))
        await monitor.update_secondary_rain_sensor(
            _fresh_secondary(is_raining=False)
        )
        await monitor.update_sun_altitude(-18.0)
        # Cloud sensor + enclosure default OK paths: there is no cloud
        # data so _evaluate_clouds returns unsafe-stale by default. Inject
        # a fresh, clear reading.
        await monitor.update_cloud_sensor(-30.0)

        status = monitor.evaluate()

        # Rain branch passed: no "rain detected" reason should appear.
        assert not any("rain detected" in r for r in status.reasons), (
            f"unexpected rain reason: {status.reasons!r}"
        )

    @pytest.mark.asyncio
    async def test_rain_rate_counts_as_rain_for_voting(self):
        """Ecowitt rain_rate>0 (without is_raining flag) still votes rain."""
        weather = _MockWeather(is_raining=False, rain_rate_in_hr=0.25)
        monitor = SafetyMonitor()
        await monitor.update_weather(weather)
        await monitor.update_secondary_rain_sensor(
            _fresh_secondary(is_raining=False)
        )
        await monitor.update_sun_altitude(-18.0)

        status = monitor.evaluate()

        assert status.is_safe is False
        assert any(
            "rain detected (1 of 2 sensors)" in r for r in status.reasons
        ), f"reasons={status.reasons!r}"


# ---------------------------------------------------------------------------
# Fail-safe behavior on missing / stale secondary
# ---------------------------------------------------------------------------


class TestFailSafeMissingOrStale:
    """When secondary data is absent or stale, default to unsafe."""

    @pytest.mark.asyncio
    async def test_secondary_never_updated_is_unsafe(self):
        """No Hydreon driver yet -> secondary slot is None -> unsafe."""
        monitor = SafetyMonitor()
        await monitor.update_weather(_MockWeather(is_raining=False))
        await monitor.update_sun_altitude(-18.0)

        status = monitor.evaluate()

        assert status.is_safe is False
        assert any(
            "secondary rain sensor" in r.lower() for r in status.reasons
        ), f"reasons={status.reasons!r}"

    @pytest.mark.asyncio
    async def test_secondary_stale_is_unsafe(self):
        """Reading older than threshold -> unsafe."""
        thresholds = SafetyThresholds(secondary_rain_sensor_timeout=10.0)
        monitor = SafetyMonitor(thresholds=thresholds)
        await monitor.update_weather(_MockWeather(is_raining=False))
        await monitor.update_sun_altitude(-18.0)

        stale = SecondaryRainReading(
            is_raining=False,
            timestamp=datetime.now() - timedelta(seconds=60),
            sensor_id="hydreon-rg15",
        )
        await monitor.update_secondary_rain_sensor(stale)

        status = monitor.evaluate()

        assert status.is_safe is False
        assert any(
            "secondary rain sensor" in r.lower() for r in status.reasons
        ), f"reasons={status.reasons!r}"

    @pytest.mark.asyncio
    async def test_ecowitt_stale_secondary_fresh_returns_weather_stale(self):
        """Pre-existing Ecowitt-stale path still wins.

        Audit assertion: voting must NOT mask the existing
        "Weather data stale" branch when the primary is the missing one.
        """
        monitor = SafetyMonitor()
        # Inject a stale Ecowitt reading by hand: update_weather stamps
        # datetime.now(); mutate the slot to backdate it.
        await monitor.update_weather(_MockWeather(is_raining=False))
        assert monitor._weather_data is not None
        monitor._weather_data.timestamp = datetime.now() - timedelta(
            seconds=monitor.thresholds.weather_sensor_timeout + 10
        )
        await monitor.update_secondary_rain_sensor(
            _fresh_secondary(is_raining=False)
        )
        await monitor.update_sun_altitude(-18.0)

        status = monitor.evaluate()

        assert status.is_safe is False
        assert any(
            "weather data stale" in r.lower() for r in status.reasons
        ), f"reasons={status.reasons!r}"


# ---------------------------------------------------------------------------
# Emergency-cascade audit (lines 980-985 in monitor.py)
# ---------------------------------------------------------------------------


class TestEmergencyCascade:
    """The ``is_emergency`` branch in ``evaluate()`` must vote too.

    Per the kickoff audit task: lines 980-985 set
    ``action = EMERGENCY_CLOSE`` on Ecowitt-only rain. Once voting
    exists, ANY sensor reporting rain should trigger emergency close.
    """

    @pytest.mark.asyncio
    async def test_secondary_only_rain_triggers_emergency_close(self):
        monitor = SafetyMonitor()
        await monitor.update_weather(_MockWeather(is_raining=False))
        await monitor.update_secondary_rain_sensor(
            _fresh_secondary(is_raining=True)
        )
        await monitor.update_sun_altitude(-18.0)

        status = monitor.evaluate()

        assert status.action == SafetyAction.EMERGENCY_CLOSE, (
            f"expected EMERGENCY_CLOSE, got {status.action}"
        )

    @pytest.mark.asyncio
    async def test_primary_only_rain_still_triggers_emergency_close(self):
        """Regression: pre-SAFE-002 behavior must not weaken."""
        monitor = SafetyMonitor()
        await monitor.update_weather(_MockWeather(is_raining=True))
        await monitor.update_secondary_rain_sensor(
            _fresh_secondary(is_raining=False)
        )
        await monitor.update_sun_altitude(-18.0)

        status = monitor.evaluate()

        assert status.action == SafetyAction.EMERGENCY_CLOSE


# ---------------------------------------------------------------------------
# Safety-cascade integration: callback fires on voting flip
# ---------------------------------------------------------------------------


class TestSafetyStatusSecondaryTelemetry:
    """Important #2: ``SafetyStatus`` exposes secondary rain state.

    Operators and post-incident log review need to distinguish
    "secondary sensor reports rain" (genuine 1-of-2 event) from
    "secondary missing -> conservatively unsafe" (deployment issue).
    Reason strings carry that info today but are fragile; structured
    telemetry fields are durable.

    Contract:
      * ``secondary_rain_is_raining: Optional[bool]``
            None when reading is unavailable OR stale; True/False
            when a fresh reading is present.
      * ``secondary_rain_sensor_stale: bool``
            False when reading is fresh OR was never provided; True
            ONLY when a reading was provided but has aged out.
    """

    @pytest.mark.asyncio
    async def test_safety_status_exposes_secondary_rain_state_when_fresh(
        self,
    ):
        monitor = SafetyMonitor()
        await monitor.update_weather(_MockWeather(is_raining=False))
        await monitor.update_secondary_rain_sensor(
            _fresh_secondary(is_raining=False)
        )
        await monitor.update_sun_altitude(-18.0)

        status = monitor.evaluate()

        assert status.secondary_rain_is_raining is False
        assert status.secondary_rain_sensor_stale is False

    @pytest.mark.asyncio
    async def test_safety_status_secondary_rain_state_true_when_raining(
        self,
    ):
        monitor = SafetyMonitor()
        await monitor.update_weather(_MockWeather(is_raining=False))
        await monitor.update_secondary_rain_sensor(
            _fresh_secondary(is_raining=True)
        )
        await monitor.update_sun_altitude(-18.0)

        status = monitor.evaluate()

        assert status.secondary_rain_is_raining is True
        assert status.secondary_rain_sensor_stale is False

    @pytest.mark.asyncio
    async def test_safety_status_secondary_stale_when_old_reading(self):
        thresholds = SafetyThresholds(secondary_rain_sensor_timeout=10.0)
        monitor = SafetyMonitor(thresholds=thresholds)
        await monitor.update_weather(_MockWeather(is_raining=False))
        await monitor.update_sun_altitude(-18.0)
        stale = SecondaryRainReading(
            is_raining=False,
            timestamp=datetime.now() - timedelta(seconds=60),
            sensor_id="hydreon-rg15",
        )
        await monitor.update_secondary_rain_sensor(stale)

        status = monitor.evaluate()

        assert status.secondary_rain_is_raining is None
        assert status.secondary_rain_sensor_stale is True

    @pytest.mark.asyncio
    async def test_safety_status_secondary_none_when_never_updated(self):
        """No reading ever provided -> None + not-stale.

        ``stale=False`` is correct because staleness implies a reading
        existed and aged out. A missing reading is a different
        condition (visible via ``secondary_rain_is_raining is None``
        with ``secondary_rain_sensor_stale is False``).
        """
        monitor = SafetyMonitor()
        await monitor.update_weather(_MockWeather(is_raining=False))
        await monitor.update_sun_altitude(-18.0)

        status = monitor.evaluate()

        assert status.secondary_rain_is_raining is None
        assert status.secondary_rain_sensor_stale is False


class TestRequireSecondaryRainSensorFlag:
    """Important #1: ``require_secondary_rain_sensor`` opt-out flag.

    Default (True) preserves the production fail-safe: missing secondary
    -> unsafe. Setting False lets the primary alone decide when no
    secondary reading has ever been pushed. This is for dev machines
    and initial deployments where the Hydreon driver hasn't landed
    yet. The flag must NOT silence sensor *staleness* — a stale
    secondary is sensor failure, distinct from "no secondary installed."
    """

    @pytest.mark.asyncio
    async def test_require_secondary_false_allows_primary_only_when_secondary_missing(
        self,
    ):
        """Flag off + primary fresh+dry + no secondary -> safe (re: rain)."""
        monitor = SafetyMonitor(
            thresholds=SafetyThresholds(require_secondary_rain_sensor=False)
        )
        await monitor.update_weather(_MockWeather(is_raining=False))
        await monitor.update_sun_altitude(-18.0)
        await monitor.update_cloud_sensor(-30.0)

        status = monitor.evaluate()

        # No "rain detected" reason, no "secondary unavailable" reason.
        assert not any(
            "rain detected" in r.lower() for r in status.reasons
        ), f"unexpected rain reason: {status.reasons!r}"
        assert not any(
            "secondary rain sensor" in r.lower() for r in status.reasons
        ), f"unexpected secondary reason: {status.reasons!r}"

    @pytest.mark.asyncio
    async def test_require_secondary_false_still_unsafe_when_primary_rain(
        self,
    ):
        """Flag off + primary fresh+rain + no secondary -> unsafe."""
        monitor = SafetyMonitor(
            thresholds=SafetyThresholds(require_secondary_rain_sensor=False)
        )
        await monitor.update_weather(_MockWeather(is_raining=True))
        await monitor.update_sun_altitude(-18.0)

        status = monitor.evaluate()

        assert status.is_safe is False
        assert any(
            "rain detected" in r.lower() for r in status.reasons
        ), f"reasons={status.reasons!r}"

    @pytest.mark.asyncio
    async def test_require_secondary_false_still_unsafe_when_primary_stale(
        self,
    ):
        """Flag off + primary stale + no secondary -> unsafe.

        With both sensors absent (one stale, one missing) there is no
        fresh sensor at all — the operator gets no signal.
        """
        monitor = SafetyMonitor(
            thresholds=SafetyThresholds(require_secondary_rain_sensor=False)
        )
        # Backdate the primary into staleness.
        await monitor.update_weather(_MockWeather(is_raining=False))
        assert monitor._weather_data is not None
        monitor._weather_data.timestamp = datetime.now() - timedelta(
            seconds=monitor.thresholds.weather_sensor_timeout + 10
        )
        await monitor.update_sun_altitude(-18.0)

        status = monitor.evaluate()

        assert status.is_safe is False
        # Some "unavailable" reason should be present — the exact wording
        # depends on the implementation's reason cascade.
        assert any(
            "unavailable" in r.lower() or "stale" in r.lower()
            for r in status.reasons
        ), f"reasons={status.reasons!r}"

    @pytest.mark.asyncio
    async def test_require_secondary_true_default_unsafe_when_secondary_missing(
        self,
    ):
        """Default flag (True) + secondary None -> unsafe.

        Regression guard: the opt-out flag must not change default
        behavior. This re-asserts the pre-Minor #1 contract: shipping
        without a secondary driver remains fail-safe.
        """
        monitor = SafetyMonitor()  # default thresholds
        await monitor.update_weather(_MockWeather(is_raining=False))
        await monitor.update_sun_altitude(-18.0)

        status = monitor.evaluate()

        assert status.is_safe is False
        assert any(
            "secondary rain sensor" in r.lower() for r in status.reasons
        ), f"reasons={status.reasons!r}"

    @pytest.mark.asyncio
    async def test_require_secondary_false_does_not_affect_stale_secondary(
        self,
    ):
        """Flag off but a stale (not missing) secondary -> still unsafe.

        Staleness means the sensor *was* installed and is *now broken*.
        The opt-out only covers the "never installed" case.
        """
        thresholds = SafetyThresholds(
            require_secondary_rain_sensor=False,
            secondary_rain_sensor_timeout=10.0,
        )
        monitor = SafetyMonitor(thresholds=thresholds)
        await monitor.update_weather(_MockWeather(is_raining=False))
        await monitor.update_sun_altitude(-18.0)
        stale = SecondaryRainReading(
            is_raining=False,
            timestamp=datetime.now() - timedelta(seconds=60),
            sensor_id="hydreon-rg15",
        )
        await monitor.update_secondary_rain_sensor(stale)

        status = monitor.evaluate()

        assert status.is_safe is False
        assert any(
            "secondary rain sensor" in r.lower() for r in status.reasons
        ), f"reasons={status.reasons!r}"


class TestVotingCallbackIntegration:
    """register_callback (ARCH-003) must fire when voting flips unsafe."""

    @pytest.mark.asyncio
    async def test_callback_invoked_when_secondary_rain_flips_unsafe(self):
        """Production wiring path.

        Orchestrator.cancel-on-unsafe (ARCH-003) registers a sync
        callback. _notify_callbacks is what fires it. We can call
        evaluate() and _notify_callbacks() directly: the run-loop is
        not under test here, only the cascade.
        """
        monitor = SafetyMonitor()
        received: list[SafetyStatus] = []

        def on_change(status: SafetyStatus) -> None:
            received.append(status)

        monitor.register_callback(on_change)

        # Set the world to safe (dry, dry).
        await monitor.update_weather(_MockWeather(is_raining=False))
        await monitor.update_secondary_rain_sensor(
            _fresh_secondary(is_raining=False)
        )
        await monitor.update_sun_altitude(-18.0)
        await monitor.update_cloud_sensor(-30.0)

        # First evaluation: presumed safe (or at least no rain reason).
        first = monitor.evaluate()
        await monitor._notify_callbacks(first)

        # Flip the secondary to "raining".
        await monitor.update_secondary_rain_sensor(
            _fresh_secondary(is_raining=True)
        )
        second = monitor.evaluate()
        await monitor._notify_callbacks(second)

        assert len(received) == 2
        # The second status must be unsafe and cite the voting reason.
        assert received[1].is_safe is False
        assert any(
            "rain detected (1 of 2 sensors)" in r
            for r in received[1].reasons
        )
