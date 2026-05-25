"""Secondary rain sensor data shape for SAFE-002 dual-redundant voting.

The NIGHTWATCH safety monitor reads its primary rain signal from the
Ecowitt WS90 (``services.weather.ecowitt.WeatherData``). The WS90 has
known false-negative modes — sensor frozen in winter, RF link lost,
sensor partially shielded by an overhang — so SAFE-002 (Risk #9) adds a
second, independent rain sensor and a voting policy:

  * Either sensor reports rain -> unsafe ("close the enclosure")
  * BOTH sensors must report dry -> permitted to operate
  * Either sensor missing or stale -> conservatively unsafe

This module exposes only the *data shape* the SafetyMonitor consumes
via ``SafetyMonitor.update_secondary_rain_sensor(...)``. The actual
sensor driver (typical hardware: Hydreon RG-15 optical rain sensor,
reachable via UART or GPIO) is a separate hardware task and lives in
its own module when implemented.

Until that driver lands the SafetyMonitor's ``_secondary_rain_data``
slot stays ``None``, which the voting policy treats as
"sensor unavailable" -> unsafe. This is the intended fail-safe default;
operating without the redundant sensor is exactly the single-point-of-
failure mode SAFE-002 was created to remove.

Design notes:
  * ``frozen=True`` — readings are values, not records. Mutating an
    in-flight reading would invalidate the timestamp's meaning.
  * Standalone dataclass (not a reuse of ``SafetyMonitor.SensorInput``)
    because the SensorInput wrapper is the monitor's internal cache
    shape; this dataclass is the *public* contract a future Hydreon
    driver will produce.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

# Allowlist of accepted ``sensor_id`` values. SAFE-002 review (Minor #4)
# called for constraining this namespace so dashboards / log-greppers
# don't have to deal with arbitrary strings (typos, ad-hoc test names
# leaking into production). The ``Final[frozenset[str]]`` shape mirrors
# the existing NIGHTWATCH pattern (see ``nightwatch.config``
# ``SAFETY_ENV_OVERRIDE_ALLOWLIST``) — ``Final`` blocks rebinding the
# module-level name, ``frozenset`` blocks in-place mutation, so callers
# cannot widen the namespace at runtime.
#
# Membership rationale:
#   * ``"hydreon-rg15"`` — the planned secondary sensor (optical, UART).
#   * ``"secondary"``    — generic fallback used by the dataclass default
#                          and by tests that don't care about the model.
#
# Add more variants here as new sensor drivers land; do not allow
# arbitrary IDs.
SECONDARY_RAIN_SENSOR_IDS: Final[frozenset[str]] = frozenset(
    {"hydreon-rg15", "secondary"}
)


@dataclass(frozen=True)
class SecondaryRainReading:
    """One reading from the secondary (non-Ecowitt) rain sensor.

    Attributes:
        is_raining: True if the sensor currently detects precipitation.
        timestamp: When the reading was produced. Used by
            ``SafetyMonitor._is_sensor_stale`` against
            ``SafetyThresholds.secondary_rain_sensor_timeout``.
        sensor_id: Human-readable identifier surfaced in log lines and
            voice prompts so the operator can distinguish "Ecowitt vs
            Hydreon disagreement" from a genuine 2-of-2 storm. Must be
            a member of :data:`SECONDARY_RAIN_SENSOR_IDS`; ``__post_init__``
            raises ``ValueError`` otherwise.
    """

    is_raining: bool
    timestamp: datetime
    sensor_id: str = "secondary"

    def __post_init__(self) -> None:
        # Runtime validation: constrain ``sensor_id`` to the known
        # allowlist. ``Final[frozenset]`` chosen over ``Literal[...]``
        # for extensibility (new sensors require a one-line edit, no
        # type-checker complaints at call sites that build IDs from
        # config) — see module-level allowlist for rationale.
        if self.sensor_id not in SECONDARY_RAIN_SENSOR_IDS:
            raise ValueError(
                f"sensor_id {self.sensor_id!r} is not in "
                f"SECONDARY_RAIN_SENSOR_IDS={sorted(SECONDARY_RAIN_SENSOR_IDS)!r}"
            )
