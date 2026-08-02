"""
NIGHTWATCH Safety Monitor Service
Observatory Automation and Safety Controller

This module implements the safety logic for autonomous observatory operation.
It integrates data from weather sensors, cloud sensor, and mount status to
make automated decisions about telescope operation.

Safety Priority Order:
1. Rain detection -> Immediate park
2. High wind -> Park and wait
3. Cloud cover -> Park and wait
4. Daylight -> Park for day
5. All clear -> Safe to observe
"""

import asyncio
import inspect
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Optional, List, Callable, Any
import logging

# SAFE-002 review Minor #5: SecondaryRainReading imported under
# ``TYPE_CHECKING`` for the typed parameter of
# ``update_secondary_rain_sensor``. Behind the guard so the runtime
# import graph stays minimal — at runtime the rain branches use
# duck-typed attribute access. (Mypy still follows the TYPE_CHECKING
# import to check the annotation; this surfaces +14 pre-existing
# errors in sibling weather adapters loaded eagerly by
# ``services/weather/__init__.py``. Those errors are unrelated to
# SAFE-002 and tracked separately.)
if TYPE_CHECKING:
    from services.weather.secondary_rain import SecondaryRainReading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NIGHTWATCH.Safety")


class SafetyAction(Enum):
    """Actions the safety monitor can command."""
    SAFE_TO_OBSERVE = "safe_to_observe"
    PARK_AND_WAIT = "park_and_wait"
    PARK_FOR_DAYLIGHT = "park_for_daylight"
    EMERGENCY_CLOSE = "emergency_close"
    DEW_WARNING = "dew_warning"
    COLD_WARNING = "cold_warning"
    # Step 486: Staged shutdown actions
    LOW_BATTERY_WARNING = "low_battery_warning"
    LOW_BATTERY_PARK = "low_battery_park"
    LOW_BATTERY_SHUTDOWN = "low_battery_shutdown"
    # Step 489: Network failure action
    NETWORK_FAILURE = "network_failure"
    # Step 485: Power failure response
    POWER_FAILURE = "power_failure"
    # SAFE-004: Watchdog-driven hardware fail-safe. Fired when the
    # safety_monitor service itself has gone silent past its heartbeat
    # timeout and the watchdog has bypassed the (possibly hung)
    # orchestrator to close the enclosure directly. This is NOT a
    # normal safety evaluation — it is the last-resort signal that the
    # safety pipeline itself has been declared unhealthy and the
    # hardware has been driven to its protected state.
    SAFETY_VETO = "safety_veto"


class ObservatoryState(Enum):
    """Current observatory operational state."""
    UNKNOWN = "unknown"
    CLOSED = "closed"
    OPENING = "opening"
    OPEN_IDLE = "open_idle"
    OBSERVING = "observing"
    PARKING = "parking"
    PARKED = "parked"
    EMERGENCY = "emergency"


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class SafetyStatus:
    """Current safety assessment."""
    timestamp: datetime
    action: SafetyAction
    is_safe: bool
    reasons: List[str]
    alert_level: AlertLevel

    # Individual sensor status
    weather_ok: bool = True
    clouds_ok: bool = True
    daylight_ok: bool = True
    mount_ok: bool = True
    power_ok: bool = True          # Step 469
    enclosure_ok: bool = True      # Step 470
    altitude_ok: bool = True       # Step 467
    meridian_ok: bool = True       # Step 468
    network_ok: bool = True        # Step 489

    # Environmental readings
    temperature_f: Optional[float] = None
    humidity_percent: Optional[float] = None
    wind_speed_mph: Optional[float] = None
    cloud_cover_percent: Optional[float] = None
    sun_altitude_deg: Optional[float] = None

    # Step 465: Rain holdoff tracking
    rain_holdoff_active: bool = False
    rain_holdoff_remaining_min: Optional[float] = None

    # Step 469: Power status
    ups_battery_percent: Optional[float] = None
    ups_on_battery: bool = False

    # Step 486: Staged battery shutdown status
    battery_shutdown_stage: Optional[str] = None  # warning/park/shutdown

    # Step 470: Enclosure status
    enclosure_open: Optional[bool] = None

    # Step 467: Target altitude
    target_altitude_deg: Optional[float] = None

    # Step 489: Network status
    network_connected: bool = True
    network_latency_ms: Optional[float] = None

    # SAFE-002 review Important #2: structured secondary-rain telemetry.
    # Lets operators distinguish "1 of 2 sensors reports rain" (genuine
    # weather event) from "secondary unavailable -> conservatively
    # unsafe" (deployment / sensor failure). Reason-string scraping is
    # fragile; these fields are durable.
    #
    #   secondary_rain_is_raining
    #     None  = reading unavailable OR stale (no usable signal).
    #     True  = fresh reading, sensor is detecting rain.
    #     False = fresh reading, sensor is dry.
    #
    #   secondary_rain_sensor_stale
    #     True  ONLY when a reading was provided and has aged past
    #           ``SafetyThresholds.secondary_rain_sensor_timeout``.
    #     False otherwise — including the "never provided" case, where
    #           ``secondary_rain_is_raining`` will be None and
    #           ``stale`` will be False, signaling "no sensor yet"
    #           rather than "sensor failed".
    # Note: ``bool | None`` (PEP 604) rather than the file-prevailing
    # ``Optional[bool]`` solely to keep ruff's UP045 count at the
    # post-implementer baseline (78). File-wide migration is deferred
    # (review Minor #6).
    secondary_rain_is_raining: bool | None = None
    secondary_rain_sensor_stale: bool = False


@dataclass
class SafetyThresholds:
    """
    Configurable safety thresholds.

    POS Panel Recommendations (v1.0):
    - Antonio García: Calibrated cloud thresholds for Nevada altitude
    - Bob Denny: Added sensor timeout and hysteresis for ASCOM compatibility
    - Sierra Remote: Adjusted timing for autonomous operation
    """
    # Wind limits (POS: calibrated for 6000ft elevation)
    wind_limit_mph: float = 25.0
    wind_gust_limit_mph: float = 35.0
    wind_hysteresis_mph: float = 5.0      # POS: Must drop 5mph below limit to clear

    # Humidity/temperature (POS: adjusted for Nevada desert)
    humidity_limit: float = 85.0
    humidity_hysteresis: float = 5.0      # POS: Must drop to 80% to clear
    temp_min_f: float = 20.0
    dew_point_margin_f: float = 5.0       # POS: Park if within 5°F of dew point

    # Cloud sensor (sky-ambient differential in Celsius)
    # POS Antonio García: Calibrated for Nevada altitude (thinner atmosphere)
    clear_sky_threshold: float = -25.0    # < -25°C = clear
    cloudy_threshold: float = -15.0       # > -15°C = cloudy
    cloud_hysteresis: float = 3.0         # POS: 3°C hysteresis band

    # Sun altitude for astronomical twilight
    twilight_altitude: float = -12.0      # degrees
    twilight_hysteresis: float = 2.0      # POS: 2° hysteresis

    # Timing (POS Bob Denny: ASCOM-compatible timeouts)
    unsafe_duration_to_park: float = 60.0  # seconds before parking
    safe_duration_to_resume: float = 300.0 # seconds (5 min) to confirm safe

    # SAFE-001 (Risk #2): bounded window the run() loop spends between
    # firing the cancel callbacks (which signal in-flight captures/slews
    # to abort) and dispatching execute_action() for EMERGENCY_CLOSE
    # (which is irreversible — drives the roof closed).
    #
    # The cancel token is cooperative (nightwatch.cancellation.CancelToken):
    # in-flight loops check it at known cadences — camera at frame
    # boundaries, mount at poll-tick boundaries, focus per-step. This
    # timeout is the worst-case "give cooperative cancellation a window
    # to land" budget. 2s is generous for typical configs.
    #
    # NOT a hard guarantee: if a handler ignores its token, we still
    # close the roof on schedule. Safety-first: a missed observing
    # window is recoverable; water on the primary is not.
    cancel_settle_timeout_s: float = 2.0

    # POS: Sensor health timeouts (treat stale data as unsafe)
    weather_sensor_timeout: float = 120.0  # seconds - Ecowitt update interval ~60s
    cloud_sensor_timeout: float = 180.0    # seconds - CloudWatcher slower updates
    ephemeris_timeout: float = 600.0       # seconds - ephemeris changes slowly

    # SAFE-002 (Risk #9): Secondary rain sensor staleness window.
    # Mirrors weather_sensor_timeout but tighter — a redundant rain
    # sensor that stops reporting is the failure mode we're guarding
    # against, so we want to flip to "unavailable" quickly.
    secondary_rain_sensor_timeout: float = 60.0  # seconds

    # SAFE-002 review Important #1: Production-vs-development opt-out
    # for the secondary rain sensor requirement.
    #
    #   True  (default, production): a missing secondary rain reading
    #         -> unsafe. This is the fail-safe shipped behavior; with
    #         no Hydreon driver installed, the observatory refuses to
    #         operate. Correct for any production deployment.
    #
    #   False (development / initial-deploy escape hatch): if the
    #         secondary reading slot is None, the primary alone
    #         decides. Primary rain -> unsafe; primary fresh+dry ->
    #         safe; primary stale -> unsafe (we still need at least
    #         one fresh sensor). This lets dev machines run before
    #         the redundant sensor lands AND lets initial deployments
    #         iterate the rest of the system without blocking on
    #         hardware.
    #
    # The flag deliberately does NOT cover the *stale* case: a stale
    # secondary means the sensor was installed and is now failing,
    # which is exactly the SAFE-002 failure mode we want to be loud
    # about.
    require_secondary_rain_sensor: bool = True

    # Step 465: Rain holdoff (POS recommendation)
    rain_holdoff_minutes: float = 30.0    # Minutes to wait after rain stops

    # Step 467: Horizon altitude limit
    min_altitude_deg: float = 10.0        # Minimum allowed altitude
    horizon_altitude_buffer: float = 2.0  # Buffer zone for warning

    # Step 469: Power level safety
    ups_warning_percent: float = 50.0     # UPS battery warning level
    ups_critical_percent: float = 25.0    # UPS battery critical level (park)
    ups_emergency_percent: float = 15.0   # UPS battery emergency level (immediate shutdown)

    # Step 470: Enclosure safety
    require_enclosure_open: bool = True   # Require enclosure open to observe

    # Step 468: Meridian safety zone (prevent collision during flip)
    meridian_safety_zone_deg: float = 5.0  # Degrees from meridian to warn
    meridian_flip_zone_deg: float = 2.0    # Degrees from meridian (must flip)

    # Step 486: Staged battery shutdown thresholds
    battery_stage1_percent: float = 50.0   # Stage 1: Warning
    battery_stage2_percent: float = 30.0   # Stage 2: Park telescope
    battery_stage3_percent: float = 15.0   # Stage 3: Close roof, prepare shutdown
    battery_stage4_percent: float = 10.0   # Stage 4: Emergency system shutdown

    # Step 489: Network monitoring thresholds
    network_check_hosts: List[str] = field(default_factory=lambda: ["8.8.8.8", "1.1.1.1"])
    network_timeout_sec: float = 5.0       # Timeout for network check
    network_fail_count_park: int = 3       # Consecutive failures before parking
    network_latency_warning_ms: float = 500.0  # High latency warning


@dataclass
class SensorInput:
    """Input from a single sensor."""
    name: str
    value: Any
    timestamp: datetime
    is_valid: bool = True
    error: Optional[str] = None


class SafetyMonitor:
    """
    Main safety monitor for NIGHTWATCH observatory.

    Integrates multiple sensor inputs and makes automated decisions
    about telescope operation to protect equipment.
    """

    def __init__(
        self,
        thresholds: Optional[SafetyThresholds] = None,
        mount_controller=None,
        weather_client=None,
        cloud_sensor=None,
        power_monitor=None,      # Step 469
        enclosure_controller=None  # Step 470
    ):
        self.thresholds = thresholds or SafetyThresholds()
        self.mount = mount_controller
        self.weather = weather_client
        self.cloud_sensor = cloud_sensor
        self.power_monitor = power_monitor        # Step 469
        self.enclosure = enclosure_controller     # Step 470

        self._state = ObservatoryState.UNKNOWN
        self._last_status: Optional[SafetyStatus] = None
        self._unsafe_since: Optional[datetime] = None
        self._safe_since: Optional[datetime] = None
        self._callbacks: List[Callable] = []
        self._running = False
        # Optional async action callback invoked on power-failure response;
        # stays None until set_action_callback wires one in.
        self._action_callback = None

        # Sensor data cache
        self._weather_data: Optional[SensorInput] = None
        self._cloud_data: Optional[SensorInput] = None
        # SAFE-002 (Risk #9): Secondary (non-Ecowitt) rain sensor slot.
        # Filled by ``update_secondary_rain_sensor``. Stays None until a
        # secondary-rain driver (typical: Hydreon RG-15) is wired in;
        # the voting policy in ``_evaluate_weather`` treats None as
        # "unavailable -> unsafe", which is the intended fail-safe.
        self._secondary_rain_data: Optional[SensorInput] = None
        self._sun_altitude: Optional[float] = None
        self._sun_altitude_time: Optional[datetime] = None

        # Step 465: Rain holdoff tracking
        self._last_rain_time: Optional[datetime] = None

        # Step 467: Target altitude tracking
        self._target_altitude: Optional[float] = None

        # Step 469: Power status cache
        self._ups_battery_percent: Optional[float] = None
        self._ups_on_battery: bool = False
        self._ups_update_time: Optional[datetime] = None

        # Step 470: Enclosure status cache
        self._enclosure_open: Optional[bool] = None
        self._enclosure_update_time: Optional[datetime] = None

        # POS: Hysteresis state tracking
        # Tracks whether each condition is currently in "triggered" state
        self._wind_triggered: bool = False
        self._humidity_triggered: bool = False
        self._cloud_triggered: bool = False
        self._daylight_triggered: bool = False

        # Step 486: Staged battery shutdown tracking
        self._battery_shutdown_stage: int = 0  # 0=normal, 1-4=stages
        self._battery_stage_time: Optional[datetime] = None

        # Step 489: Network failure tracking
        self._network_fail_count: int = 0
        self._network_connected: bool = True
        self._network_latency_ms: Optional[float] = None
        self._last_network_check: Optional[datetime] = None

    @property
    def state(self) -> ObservatoryState:
        """Current observatory state."""
        return self._state

    @property
    def last_status(self) -> Optional[SafetyStatus]:
        """Most recent safety assessment."""
        return self._last_status

    def register_callback(self, callback: Callable[["SafetyStatus"], None]):
        """
        Register callback for safety status changes.

        Callbacks are invoked whenever the safety status is updated,
        allowing other services to respond to safety state transitions.

        Args:
            callback: Function with signature (status: SafetyStatus) -> None
                     Called with current SafetyStatus containing is_safe,
                     conditions, and any active alerts.

        Example:
            def on_safety_change(status: SafetyStatus):
                if not status.is_safe:
                    initiate_emergency_close()

            monitor.register_callback(on_safety_change)
        """
        self._callbacks.append(callback)

    def set_action_callback(self, callback):
        """Register the action callback invoked during power-failure response."""
        self._action_callback = callback

    async def update_weather(self, data):
        """Update weather sensor data."""
        self._weather_data = SensorInput(
            name="Ecowitt WS90",
            value=data,
            timestamp=datetime.now()
        )

    async def update_secondary_rain_sensor(
        self, reading: "SecondaryRainReading"
    ) -> None:
        """Update secondary rain sensor reading (SAFE-002, Risk #9).

        Accepts a ``services.weather.secondary_rain.SecondaryRainReading``
        and stores it in the secondary slot for the dual-redundant
        voting policy in ``_evaluate_weather``.

        The method is ``async`` solely for symmetry with the sibling
        sensor setters (``update_weather``, ``update_cloud_sensor``,
        etc.). It performs no I/O — the actual sensor I/O is the
        responsibility of the (future) Hydreon driver that calls this.
        See ``services.weather.secondary_rain`` for the data contract.

        Args:
            reading: A ``SecondaryRainReading`` value with
                ``is_raining``, ``timestamp``, and ``sensor_id``.

        Note (ARCH-003 cross-reference):
            The orchestrator's ``SafetyServiceProtocol`` does NOT
            expose sensor-input methods — it is a read-only consumer
            interface (is_safe, get_unsafe_reasons, register_callback).
            So this method does NOT need a Protocol mirror. Future
            drivers wire to ``SafetyMonitor`` directly via this method.
        """
        # SAFE-002 review Minor #5: parameter is now typed as
        # SecondaryRainReading (TYPE_CHECKING-only import) so mypy sees
        # the contract. Runtime read uses direct attribute access — the
        # frozen dataclass + __post_init__ allowlist on the sender
        # side guarantees both ``sensor_id`` and ``timestamp`` are set.
        self._secondary_rain_data = SensorInput(
            name=f"SecondaryRain({reading.sensor_id})",
            value=reading,
            timestamp=reading.timestamp,
        )

    async def update_cloud_sensor(self, sky_temp_diff: float):
        """Update cloud sensor data (sky-ambient temperature difference)."""
        self._cloud_data = SensorInput(
            name="CloudWatcher",
            value=sky_temp_diff,
            timestamp=datetime.now()
        )

    async def update_sun_altitude(self, altitude: float):
        """Update sun altitude (from ephemeris service)."""
        self._sun_altitude = altitude
        self._sun_altitude_time = datetime.now()

    async def update_target_altitude(self, altitude: float):
        """
        Update target altitude for horizon limit check (Step 467).

        Args:
            altitude: Target altitude in degrees
        """
        self._target_altitude = altitude

    async def update_power_status(self, battery_percent: float, on_battery: bool = False):
        """
        Update UPS power status (Step 469).

        Args:
            battery_percent: Battery charge level (0-100)
            on_battery: True if running on battery power
        """
        self._ups_battery_percent = battery_percent
        self._ups_on_battery = on_battery
        self._ups_update_time = datetime.now()

    async def update_enclosure_status(self, is_open: bool):
        """
        Update enclosure status (Step 470).

        Args:
            is_open: True if enclosure/roof is open
        """
        self._enclosure_open = is_open
        self._enclosure_update_time = datetime.now()

    def _is_sensor_stale(self, sensor: Optional[SensorInput], timeout: float) -> bool:
        """
        Check if sensor data is stale (POS recommendation).

        Args:
            sensor: Sensor input to check
            timeout: Maximum age in seconds

        Returns:
            True if sensor is stale or missing
        """
        if not sensor:
            return True
        age = (datetime.now() - sensor.timestamp).total_seconds()
        return age > timeout

    def _primary_rain_vote(self) -> Optional[bool]:
        """Return the Ecowitt rain vote.

        Returns:
            True  if the primary sensor reports rain.
            False if the primary sensor is fresh and reports dry.
            None  if the primary sensor is stale, missing, invalid, or
                  its payload lacks both rain fields. The caller
                  (``_evaluate_weather``) treats None as "unavailable
                  -> unsafe" under the SAFE-002 voting policy.
        """
        if self._is_sensor_stale(
            self._weather_data, self.thresholds.weather_sensor_timeout
        ):
            return None
        if not self._weather_data or not self._weather_data.is_valid:
            return None
        data = self._weather_data.value
        if not data:
            return None
        if getattr(data, "is_raining", False):
            return True
        if getattr(data, "rain_rate_in_hr", 0.0) > 0:
            return True
        # Payload exists but neither rain field signals rain. We treat
        # this as a valid "dry" reading rather than "unavailable" —
        # the field-presence check already happened via getattr defaults.
        return False

    def _secondary_rain_vote(self) -> Optional[bool]:
        """Return the secondary rain sensor vote (SAFE-002).

        Same tri-state semantics as ``_primary_rain_vote``: True/False
        for fresh readings, None for stale/missing.
        """
        if self._is_sensor_stale(
            self._secondary_rain_data,
            self.thresholds.secondary_rain_sensor_timeout,
        ):
            return None
        if (
            not self._secondary_rain_data
            or not self._secondary_rain_data.is_valid
        ):
            return None
        reading = self._secondary_rain_data.value
        if reading is None:
            return None
        # Duck-typed getattr (instead of isinstance) so monitor.py does
        # not have to import SecondaryRainReading at runtime — see the
        # TYPE_CHECKING note at module top. Input validity is guaranteed
        # by SecondaryRainReading's frozen dataclass + __post_init__.
        return bool(getattr(reading, "is_raining", False))

    def _vote_rain_status(self) -> tuple[bool, List[str]]:
        """Apply dual-redundant rain voting (SAFE-002, Risk #9).

        Returns:
            (is_safe_re_rain, reasons)

            * is_safe_re_rain is True only when BOTH sensors are fresh
              AND both report dry — UNLESS
              ``SafetyThresholds.require_secondary_rain_sensor`` is
              False and the secondary slot has *never been populated*,
              in which case the primary alone decides (Important #1
              opt-out for dev / pre-Hydreon deployments).
            * Any sensor reporting rain -> unsafe with a
              "rain detected (N of 2 sensors): <names>" reason. N is the
              count of sensors voting rain (1 or 2); the names list lets
              the operator distinguish single-sensor disagreement
              (possible sensor fault) from agreement (genuine storm).
            * Any sensor missing/stale -> unsafe with an "unavailable"
              reason. Conservative fail-safe default: we never permit
              operation when redundancy is degraded, because the cost of
              rain damage (water on OTA + camera) is asymmetric with the
              cost of a missed observing window.

        Important #1 opt-out semantics (require_secondary_rain_sensor):
            The flag covers exactly one case: the secondary slot was
            never written to (driver not installed). It does NOT cover
            *stale* secondary readings — staleness means the sensor
            was there and is now broken, which is exactly the failure
            mode SAFE-002 exists to catch.
        """
        primary = self._primary_rain_vote()
        secondary = self._secondary_rain_vote()
        reasons: List[str] = []

        # Important #1: detect the "secondary never installed" case
        # before we tally the standard unavailable-reasons branch.
        secondary_never_installed = self._secondary_rain_data is None
        opt_out_active = (
            secondary is None
            and secondary_never_installed
            and not self.thresholds.require_secondary_rain_sensor
        )

        if primary is None:
            reasons.append(
                "Primary rain sensor (Ecowitt) unavailable - "
                "treating as unsafe"
            )
        # Suppress the "secondary unavailable" reason only under the
        # explicit opt-out. A stale (not-missing) secondary still hits
        # the standard reason path because secondary_never_installed
        # is False for stale readings.
        if secondary is None and not opt_out_active:
            reasons.append(
                "Secondary rain sensor unavailable - "
                "treating as unsafe"
            )

        rainers: List[str] = []
        if primary is True:
            rainers.append("Ecowitt")
        if secondary is True:
            # Duck-typed (see TYPE_CHECKING note at module top).
            sensor_name = "secondary"
            if self._secondary_rain_data is not None:
                value = self._secondary_rain_data.value
                sensor_name = getattr(value, "sensor_id", "secondary")
            rainers.append(sensor_name)

        if rainers:
            count = len(rainers)
            self._last_rain_time = datetime.now()
            reasons.append(
                f"rain detected ({count} of 2 sensors): "
                + ", ".join(rainers)
            )

        # Under the opt-out: secondary absent + primary fresh+dry ->
        # safe. We still require the primary to be a fresh False vote
        # (primary None would have raised an unavailable reason).
        if opt_out_active:
            is_safe_re_rain = primary is False and not reasons
        else:
            is_safe_re_rain = (
                primary is False and secondary is False and not reasons
            )
        return is_safe_re_rain, reasons

    def _any_rain_sensor_reports_rain(self) -> bool:
        """SAFE-002 audit helper for the ``evaluate()`` emergency cascade.

        The ``is_emergency`` block at the bottom of ``evaluate()``
        historically read ``_weather_data`` directly. With dual
        redundancy, ANY sensor reporting rain must trigger
        ``EMERGENCY_CLOSE`` — not just the primary.
        """
        return (
            self._primary_rain_vote() is True
            or self._secondary_rain_vote() is True
        )

    def _evaluate_weather(self) -> tuple[bool, List[str]]:
        """
        Evaluate weather conditions with hysteresis (POS recommendation).

        Hysteresis prevents rapid oscillation between safe/unsafe states
        when conditions are near threshold values.

        SAFE-002 (Risk #9): Rain detection is now dual-redundant. We
        consult both the Ecowitt WS90 (primary) and a secondary rain
        sensor (typically Hydreon RG-15) and apply asymmetric voting:
        either sensor reporting rain closes the enclosure; both must
        agree on "dry" (and both must be fresh) to permit operations.
        The remaining checks (wind / humidity / dew point) still rely
        on the Ecowitt payload because the secondary sensor only
        measures rain.
        """
        reasons: List[str] = []

        # SAFE-002: Rain voting comes first — its fail-safe default
        # (unsafe on missing/stale) subsumes the old single-sensor
        # "Weather data stale" early return for the rain branch. We
        # still need to gate the Ecowitt-only checks (wind, humidity,
        # dew point) on Ecowitt freshness below.
        rain_ok, rain_reasons = self._vote_rain_status()
        if not rain_ok:
            # Rain branch is the highest-priority safety signal — any
            # detected rain or any missing redundancy short-circuits
            # the rest of the weather evaluation (mirrors the previous
            # early-return on rain). Pre-SAFE-002 the Ecowitt-stale
            # branch returned this same reason string; tests rely on
            # the "Weather data stale" wording so we surface it when
            # the primary specifically is the missing one.
            if self._is_sensor_stale(
                self._weather_data,
                self.thresholds.weather_sensor_timeout,
            ):
                # Preserve the original wording for callers/tests that
                # match on it. The redundancy reason is still useful
                # context, so we append rather than replace.
                return False, [
                    "Weather data stale or unavailable - treating as unsafe",
                    *rain_reasons,
                ]
            return False, rain_reasons

        # Past the rain gate -> both sensors fresh and dry. We still
        # need the Ecowitt payload for wind / humidity / temperature
        # checks; the rain vote already guarantees it is fresh-ish, but
        # be defensive in case of partial-payload corner cases.
        if not self._weather_data or not self._weather_data.is_valid:
            return False, ["Weather data unavailable"]

        data = self._weather_data.value
        if not data:
            return False, ["Weather data unavailable"]

        # Check wind with hysteresis (POS recommendation)
        if hasattr(data, 'wind_gust_mph'):
            if data.wind_gust_mph > self.thresholds.wind_gust_limit_mph:
                self._wind_triggered = True
                return False, [f"Wind gust {data.wind_gust_mph:.1f} mph exceeds limit"]

        if hasattr(data, 'wind_speed_mph'):
            wind = data.wind_speed_mph
            if self._wind_triggered:
                # POS: Must drop below limit minus hysteresis to clear
                clear_threshold = self.thresholds.wind_limit_mph - self.thresholds.wind_hysteresis_mph
                if wind < clear_threshold:
                    self._wind_triggered = False
                else:
                    reasons.append(f"Wind {wind:.1f} mph - waiting for drop below {clear_threshold:.0f} mph")
            else:
                if wind > self.thresholds.wind_limit_mph:
                    self._wind_triggered = True
                    reasons.append(f"Wind {wind:.1f} mph exceeds limit")

        # Check humidity with hysteresis (POS recommendation)
        if hasattr(data, 'humidity_percent'):
            humidity = data.humidity_percent
            if self._humidity_triggered:
                clear_threshold = self.thresholds.humidity_limit - self.thresholds.humidity_hysteresis
                if humidity < clear_threshold:
                    self._humidity_triggered = False
                else:
                    reasons.append(f"Humidity {humidity:.1f}% - waiting for drop below {clear_threshold:.0f}%")
            else:
                if humidity > self.thresholds.humidity_limit:
                    self._humidity_triggered = True
                    reasons.append(f"Humidity {humidity:.1f}% exceeds limit")

        # Check temperature
        if hasattr(data, 'temperature_f'):
            if data.temperature_f < self.thresholds.temp_min_f:
                reasons.append(f"Temperature {data.temperature_f:.1f}°F below minimum")

        # POS: Check dew point proximity
        if hasattr(data, 'temperature_f') and hasattr(data, 'dew_point_f'):
            margin = data.temperature_f - data.dew_point_f
            if margin < self.thresholds.dew_point_margin_f:
                reasons.append(f"Temperature within {margin:.1f}°F of dew point - condensation risk")

        is_ok = len(reasons) == 0
        return is_ok, reasons

    def _evaluate_clouds(self) -> tuple[bool, List[str]]:
        """
        Evaluate cloud cover from IR sensor with hysteresis (POS recommendation).

        Antonio García's CloudWatcher calibration notes:
        - Sky-ambient differential indicates cloud cover
        - Nevada's thinner atmosphere at 6000ft affects readings
        - Hysteresis prevents oscillation during partly cloudy conditions
        """
        # POS: Check for stale sensor data
        if self._is_sensor_stale(self._cloud_data, self.thresholds.cloud_sensor_timeout):
            # Cloud sensor timeout - log warning but don't block
            # (weather sensor is primary safety)
            logger.warning("Cloud sensor data stale")
            return True, ["Cloud sensor data stale - relying on weather sensor"]

        if not self._cloud_data or not self._cloud_data.is_valid:
            # If no cloud sensor, assume OK (but log warning)
            return True, []

        sky_diff = self._cloud_data.value

        # POS: Apply hysteresis to prevent oscillation
        if self._cloud_triggered:
            # Currently cloudy - need clear reading plus hysteresis to clear
            clear_threshold = self.thresholds.clear_sky_threshold - self.thresholds.cloud_hysteresis
            if sky_diff < clear_threshold:
                self._cloud_triggered = False
                return True, [f"Clouds clearing: sky-ambient diff {sky_diff:.1f}°C"]
            else:
                return False, [f"Cloudy: sky-ambient diff {sky_diff:.1f}°C (waiting for < {clear_threshold:.0f}°C)"]
        else:
            # Currently clear - trigger if above cloudy threshold
            if sky_diff > self.thresholds.cloudy_threshold:
                self._cloud_triggered = True
                return False, [f"Cloudy: sky-ambient diff {sky_diff:.1f}°C"]

            if sky_diff > self.thresholds.clear_sky_threshold:
                return True, [f"Partly cloudy: sky-ambient diff {sky_diff:.1f}°C"]

        return True, []

    def _evaluate_daylight(self) -> tuple[bool, List[str]]:
        """
        Evaluate if it's astronomical night with hysteresis (POS recommendation).

        Hysteresis prevents rapid state changes during twilight transitions.
        """
        # POS: Check ephemeris staleness
        if self._sun_altitude_time:
            age = (datetime.now() - self._sun_altitude_time).total_seconds()
            if age > self.thresholds.ephemeris_timeout:
                logger.warning("Ephemeris data stale")
                # Don't fail on stale ephemeris - it changes slowly
                # But log for monitoring

        if self._sun_altitude is None:
            # If no ephemeris data, assume OK
            return True, []

        # POS: Apply hysteresis for twilight transitions
        if self._daylight_triggered:
            # Currently in daylight mode - need sun well below horizon to clear
            clear_threshold = self.thresholds.twilight_altitude - self.thresholds.twilight_hysteresis
            if self._sun_altitude < clear_threshold:
                self._daylight_triggered = False
                return True, [f"Astronomical night beginning (sun at {self._sun_altitude:.1f}°)"]
            else:
                return False, [f"Sun altitude {self._sun_altitude:.1f}° - waiting for < {clear_threshold:.0f}°"]
        else:
            # Currently night - trigger if sun rises above threshold
            if self._sun_altitude > self.thresholds.twilight_altitude:
                self._daylight_triggered = True
                return False, [f"Sun altitude {self._sun_altitude:.1f}° - not astronomical night"]

        return True, []

    def _evaluate_rain_holdoff(self) -> tuple[bool, List[str], Optional[float]]:
        """
        Check rain holdoff period (Step 465).

        After rain stops, wait for holdoff period before resuming operations.
        This allows equipment to dry and conditions to stabilize.

        Returns:
            (is_ok, reasons, remaining_minutes)
        """
        if self._last_rain_time is None:
            return True, [], None

        elapsed = datetime.now() - self._last_rain_time
        elapsed_minutes = elapsed.total_seconds() / 60.0
        holdoff_minutes = self.thresholds.rain_holdoff_minutes

        if elapsed_minutes < holdoff_minutes:
            remaining = holdoff_minutes - elapsed_minutes
            return False, [f"Rain holdoff: {remaining:.0f} minutes remaining"], remaining

        return True, [], None

    def _evaluate_altitude_limit(self) -> tuple[bool, List[str]]:
        """
        Check target altitude against horizon limit (Step 467).

        Prevents slewing to objects below the minimum safe altitude.

        Returns:
            (is_ok, reasons)
        """
        if self._target_altitude is None:
            # No target set - OK
            return True, []

        min_alt = self.thresholds.min_altitude_deg
        buffer = self.thresholds.horizon_altitude_buffer

        if self._target_altitude < min_alt:
            return False, [f"Target altitude {self._target_altitude:.1f}° below minimum {min_alt}°"]

        if self._target_altitude < (min_alt + buffer):
            # Warning zone but still OK
            return True, [f"Target altitude {self._target_altitude:.1f}° near horizon limit"]

        return True, []

    def _evaluate_power(self) -> tuple[bool, List[str], bool]:
        """
        Evaluate UPS power status (Step 469).

        Checks battery level and triggers safety actions:
        - Warning at 50%
        - Park at 25%
        - Emergency at 15%

        Returns:
            (is_ok, reasons, is_emergency)
        """
        reasons = []
        is_emergency = False

        if self._ups_battery_percent is None:
            # No UPS data - assume OK but log
            return True, [], False

        battery = self._ups_battery_percent
        thresholds = self.thresholds

        # Check for emergency level
        if battery < thresholds.ups_emergency_percent:
            is_emergency = True
            return False, [f"UPS battery CRITICAL: {battery:.0f}% - EMERGENCY SHUTDOWN"], is_emergency

        # Check for critical level
        if battery < thresholds.ups_critical_percent:
            return False, [f"UPS battery low: {battery:.0f}% - parking telescope"], is_emergency

        # Check for warning level
        if battery < thresholds.ups_warning_percent:
            reasons.append(f"UPS battery warning: {battery:.0f}%")

        # Additional warning if on battery power
        if self._ups_on_battery:
            reasons.append("Running on battery power")

        return True, reasons, is_emergency

    def _evaluate_enclosure(self) -> tuple[bool, List[str]]:
        """
        Evaluate enclosure/roof status (Step 470).

        Ensures roof is open before allowing observations.

        Returns:
            (is_ok, reasons)
        """
        if not self.thresholds.require_enclosure_open:
            # Enclosure check disabled
            return True, []

        if self._enclosure_open is None:
            # No enclosure data - warn but allow
            return True, ["Enclosure status unknown"]

        if not self._enclosure_open:
            return False, ["Enclosure closed - cannot observe"]

        return True, []

    def _evaluate_meridian(self) -> tuple[bool, List[str]]:
        """
        Evaluate meridian safety zone (Step 468).

        Checks if telescope is approaching meridian (hour angle near 0)
        where a meridian flip may be required to avoid collision.

        Returns:
            (is_ok, reasons)
        """
        reasons = []

        # Need mount data to check hour angle
        if not self.mount:
            return True, []

        try:
            status = self.mount.get_status()
            if not status:
                return True, []

            # Calculate hour angle if available
            # Hour angle = Local Sidereal Time - Right Ascension
            hour_angle = None

            if hasattr(status, 'hour_angle'):
                hour_angle = status.hour_angle
            elif hasattr(status, 'ha_degrees'):
                hour_angle = status.ha_degrees

            if hour_angle is None:
                # Cannot determine hour angle
                return True, []

            # Normalize hour angle to -180 to +180 range
            while hour_angle > 180:
                hour_angle -= 360
            while hour_angle < -180:
                hour_angle += 360

            abs_ha = abs(hour_angle)

            # Check if in meridian flip zone (critical)
            if abs_ha < self.thresholds.meridian_flip_zone_deg:
                reasons.append(
                    f"CRITICAL: At meridian (HA={hour_angle:.1f}°) - flip required"
                )
                return False, reasons

            # Check if approaching meridian (warning zone)
            if abs_ha < self.thresholds.meridian_safety_zone_deg:
                reasons.append(
                    f"Approaching meridian (HA={hour_angle:.1f}°) - flip soon"
                )
                # Warning but still safe
                return True, reasons

        except Exception as e:
            logger.error(f"Meridian check error: {e}")

        return True, reasons

    def _evaluate_staged_battery_shutdown(self) -> tuple[bool, List[str], Optional[str], SafetyAction]:
        """
        Evaluate staged battery shutdown (Step 486).

        Implements graceful degradation as battery depletes:
        - Stage 1 (50%): Warning, reduce non-essential operations
        - Stage 2 (30%): Park telescope safely
        - Stage 3 (15%): Close roof, prepare for shutdown
        - Stage 4 (10%): Emergency system shutdown

        Returns:
            (is_ok, reasons, stage_name, recommended_action)
        """
        reasons = []
        stage_name = None
        action = SafetyAction.SAFE_TO_OBSERVE

        if self._ups_battery_percent is None:
            return True, [], None, action

        battery = self._ups_battery_percent
        thresholds = self.thresholds

        # Determine current stage
        if battery < thresholds.battery_stage4_percent:
            new_stage = 4
            stage_name = "shutdown"
            action = SafetyAction.LOW_BATTERY_SHUTDOWN
            reasons.append(f"CRITICAL: Battery {battery:.0f}% - EMERGENCY SHUTDOWN REQUIRED")

        elif battery < thresholds.battery_stage3_percent:
            new_stage = 3
            stage_name = "close"
            action = SafetyAction.LOW_BATTERY_SHUTDOWN
            reasons.append(f"Battery {battery:.0f}% - Closing roof and preparing shutdown")

        elif battery < thresholds.battery_stage2_percent:
            new_stage = 2
            stage_name = "park"
            action = SafetyAction.LOW_BATTERY_PARK
            reasons.append(f"Battery {battery:.0f}% - Parking telescope")

        elif battery < thresholds.battery_stage1_percent:
            new_stage = 1
            stage_name = "warning"
            action = SafetyAction.LOW_BATTERY_WARNING
            reasons.append(f"Battery {battery:.0f}% - Low battery warning")

        else:
            new_stage = 0

        # Track stage transitions
        if new_stage != self._battery_shutdown_stage:
            if new_stage > self._battery_shutdown_stage:
                logger.warning(f"Battery shutdown stage increased: {self._battery_shutdown_stage} -> {new_stage}")
            else:
                logger.info(f"Battery shutdown stage decreased: {self._battery_shutdown_stage} -> {new_stage}")
            self._battery_shutdown_stage = new_stage
            self._battery_stage_time = datetime.now()

        # Only unsafe if in stage 2+ (need to take action)
        is_ok = new_stage < 2
        return is_ok, reasons, stage_name, action

    def _evaluate_power_failure(self) -> tuple[bool, List[str], SafetyAction]:
        """
        Evaluate and respond to power failure conditions (Step 485).

        Detects UPS power failure (mains loss) and triggers appropriate response:
        - Immediate alert when switching to battery
        - Park telescope to safe position
        - Close roof/enclosure
        - Prepare for potential shutdown

        Returns:
            (is_ok, reasons, recommended_action)
        """
        reasons = []
        action = SafetyAction.SAFE_TO_OBSERVE

        # Check if we have UPS data
        if self._ups_battery_percent is None:
            return True, [], action

        # Power failure detected when running on battery
        if self._ups_on_battery:
            battery = self._ups_battery_percent
            reasons.append(f"POWER FAILURE: Running on UPS battery ({battery:.0f}%)")
            action = SafetyAction.POWER_FAILURE

            # Log power failure event
            logger.warning(f"Power failure detected - UPS battery at {battery:.0f}%")

            # Add time estimate if available (rough estimate)
            if battery > 80:
                reasons.append("Estimated runtime: >30 minutes")
            elif battery > 50:
                reasons.append("Estimated runtime: 15-30 minutes")
            elif battery > 25:
                reasons.append("Estimated runtime: 5-15 minutes")
            else:
                reasons.append("Estimated runtime: <5 minutes - URGENT")

            # Power failure is always a safety concern requiring action
            return False, reasons, action

        return True, reasons, action

    async def handle_power_failure_response(self):
        """
        Execute power failure response sequence (Step 485).

        This method coordinates the observatory response to a power failure:
        1. Send alert to operator
        2. Stop any ongoing exposures
        3. Park telescope safely
        4. Close enclosure/roof
        5. Reduce power consumption
        6. Monitor battery and prepare for shutdown if needed

        Should be called when power failure is detected.
        """
        logger.warning("Executing power failure response sequence")

        # Track response
        response_steps = []

        try:
            # Step 1: Log and alert
            logger.critical("POWER FAILURE - Initiating emergency response")
            response_steps.append("Alert sent")

            # Step 2: If we have orchestrator callback, notify it
            if self._action_callback is not None:
                await self._action_callback(
                    SafetyAction.POWER_FAILURE,
                    {"reason": "UPS power failure detected"}
                )
                response_steps.append("Orchestrator notified")

            # Step 3: The orchestrator should handle parking and closing
            # This method serves as the coordination point
            logger.info("Power failure response: Requesting telescope park")
            response_steps.append("Park requested")

            logger.info("Power failure response: Requesting enclosure close")
            response_steps.append("Enclosure close requested")

            # Step 4: Log response completion
            logger.info(f"Power failure response completed: {response_steps}")

        except Exception as e:
            logger.error(f"Error during power failure response: {e}")
            raise

    async def check_network_connectivity(self) -> tuple[bool, Optional[float]]:
        """
        Check network connectivity (Step 489).

        Pings multiple hosts to verify network is operational.

        Returns:
            (is_connected, latency_ms)
        """
        import socket
        import time

        hosts = self.thresholds.network_check_hosts
        timeout = self.thresholds.network_timeout_sec

        for host in hosts:
            try:
                start = time.time()
                # Try TCP connection to port 53 (DNS) as a connectivity check
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect((host, 53))
                sock.close()
                latency = (time.time() - start) * 1000  # Convert to ms
                self._network_latency_ms = latency
                self._network_connected = True
                self._network_fail_count = 0
                self._last_network_check = datetime.now()
                return True, latency
            except (socket.timeout, socket.error, OSError):
                continue

        # All hosts failed
        self._network_fail_count += 1
        self._last_network_check = datetime.now()

        if self._network_fail_count >= self.thresholds.network_fail_count_park:
            self._network_connected = False

        return False, None

    def _evaluate_network(self) -> tuple[bool, List[str]]:
        """
        Evaluate network connectivity status (Step 489).

        Returns:
            (is_ok, reasons)
        """
        reasons = []

        # Check if we have recent network status
        if self._last_network_check is None:
            # No network check performed yet - assume OK but note it
            return True, ["Network status not yet checked"]

        # Check if network check is stale (older than 2x check interval)
        age = (datetime.now() - self._last_network_check).total_seconds()
        if age > 120:  # 2 minutes stale
            reasons.append("Network status stale - check may be failing")

        if not self._network_connected:
            reasons.append(f"Network disconnected ({self._network_fail_count} consecutive failures)")
            return False, reasons

        # Check for high latency
        if self._network_latency_ms is not None:
            if self._network_latency_ms > self.thresholds.network_latency_warning_ms:
                reasons.append(f"High network latency: {self._network_latency_ms:.0f}ms")

        return True, reasons

    def evaluate(self) -> SafetyStatus:
        """
        Perform comprehensive safety evaluation.

        Returns:
            SafetyStatus with current assessment
        """
        reasons = []

        # Evaluate each subsystem
        weather_ok, weather_reasons = self._evaluate_weather()
        clouds_ok, cloud_reasons = self._evaluate_clouds()
        daylight_ok, daylight_reasons = self._evaluate_daylight()

        # Step 465: Rain holdoff
        rain_holdoff_ok, rain_holdoff_reasons, rain_holdoff_remaining = self._evaluate_rain_holdoff()

        # Step 467: Altitude limit
        altitude_ok, altitude_reasons = self._evaluate_altitude_limit()

        # Step 469: Power status
        power_ok, power_reasons, power_emergency = self._evaluate_power()

        # Step 470: Enclosure status
        enclosure_ok, enclosure_reasons = self._evaluate_enclosure()

        # Step 468: Meridian safety
        meridian_ok, meridian_reasons = self._evaluate_meridian()

        # Step 486: Staged battery shutdown
        battery_shutdown_ok, battery_reasons, battery_stage, battery_action = self._evaluate_staged_battery_shutdown()

        # Step 489: Network status
        network_ok, network_reasons = self._evaluate_network()

        # Step 485: Power failure detection
        power_failure_ok, power_failure_reasons, power_failure_action = self._evaluate_power_failure()

        reasons.extend(weather_reasons)
        reasons.extend(cloud_reasons)
        reasons.extend(daylight_reasons)
        reasons.extend(rain_holdoff_reasons)
        reasons.extend(altitude_reasons)
        reasons.extend(power_reasons)
        reasons.extend(enclosure_reasons)
        reasons.extend(meridian_reasons)
        reasons.extend(battery_reasons)
        reasons.extend(network_reasons)
        reasons.extend(power_failure_reasons)

        # Determine overall safety and action
        is_safe = (weather_ok and clouds_ok and daylight_ok and
                   rain_holdoff_ok and altitude_ok and power_ok and enclosure_ok and
                   meridian_ok and battery_shutdown_ok and network_ok and power_failure_ok)

        # Check for emergency conditions (rain or power)
        is_emergency = power_emergency  # Step 469: Include power emergency
        # SAFE-002 (Risk #9): emergency-close on ANY rain sensor reporting
        # rain, not just Ecowitt. Voting policy is asymmetric: 1-of-2
        # detecting rain is enough to slam the roof.
        if self._any_rain_sensor_reports_rain():
            is_emergency = True

        # Step 486: Battery shutdown is also an emergency at stage 3+
        if self._battery_shutdown_stage >= 3:
            is_emergency = True

        # Determine action
        if is_emergency:
            action = SafetyAction.EMERGENCY_CLOSE
            alert_level = AlertLevel.EMERGENCY
        elif battery_action in [SafetyAction.LOW_BATTERY_SHUTDOWN, SafetyAction.LOW_BATTERY_PARK]:
            # Step 486: Use battery-specific action
            action = battery_action
            alert_level = AlertLevel.CRITICAL
        elif power_failure_action == SafetyAction.POWER_FAILURE:
            # Step 485: Power failure detected - immediate response
            action = SafetyAction.POWER_FAILURE
            alert_level = AlertLevel.CRITICAL
        elif not network_ok:
            # Step 489: Network failure - park safely
            action = SafetyAction.NETWORK_FAILURE
            alert_level = AlertLevel.WARNING
        elif not daylight_ok:
            action = SafetyAction.PARK_FOR_DAYLIGHT
            alert_level = AlertLevel.INFO
        elif not weather_ok or not clouds_ok or not rain_holdoff_ok:
            action = SafetyAction.PARK_AND_WAIT
            alert_level = AlertLevel.WARNING
        elif not power_ok:
            action = SafetyAction.PARK_AND_WAIT
            alert_level = AlertLevel.CRITICAL
        elif not altitude_ok:
            action = SafetyAction.PARK_AND_WAIT
            alert_level = AlertLevel.WARNING
        elif not enclosure_ok:
            action = SafetyAction.PARK_AND_WAIT
            alert_level = AlertLevel.WARNING
        elif battery_action == SafetyAction.LOW_BATTERY_WARNING:
            # Step 486: Low battery warning (still safe but warn)
            action = SafetyAction.SAFE_TO_OBSERVE
            alert_level = AlertLevel.WARNING
        else:
            action = SafetyAction.SAFE_TO_OBSERVE
            alert_level = AlertLevel.INFO

        # Extract readings for status (telemetry-only fields).
        # SAFE-002 audit: this block reads temp/humidity/wind from
        # _weather_data. Those are physical readings only the Ecowitt
        # WS90 produces — the secondary rain sensor measures rain only.
        # So no voting is needed here; the safety-decision voting lives
        # in _evaluate_weather / _any_rain_sensor_reports_rain above.
        temp = None
        humidity = None
        wind = None
        if self._weather_data and self._weather_data.is_valid:
            data = self._weather_data.value
            temp = getattr(data, 'temperature_f', None)
            humidity = getattr(data, 'humidity_percent', None)
            wind = getattr(data, 'wind_speed_mph', None)

        cloud_cover = None
        if self._cloud_data and self._cloud_data.is_valid:
            # Convert sky diff to approximate cloud percentage
            sky_diff = self._cloud_data.value
            if sky_diff < -25:
                cloud_cover = 0
            elif sky_diff > -5:
                cloud_cover = 100
            else:
                cloud_cover = ((sky_diff + 25) / 20) * 100

        # SAFE-002 review Important #2: derive secondary-rain telemetry
        # from the cached reading. Order matters here:
        #   1. Never provided    -> is_raining=None, stale=False
        #   2. Stale (provided)  -> is_raining=None, stale=True
        #   3. Fresh             -> is_raining=<reading>, stale=False
        # _is_sensor_stale returns True for "missing OR aged out", so
        # we explicitly check the "never provided" case first via
        # ``_secondary_rain_data is None`` to keep ``stale`` honest.
        # bool | None (PEP 604) — see SafetyStatus field note.
        secondary_rain_is_raining: bool | None = None
        secondary_rain_sensor_stale = False
        if self._secondary_rain_data is None:
            # Case 1: never provided. Both defaults are correct.
            pass
        elif self._is_sensor_stale(
            self._secondary_rain_data,
            self.thresholds.secondary_rain_sensor_timeout,
        ):
            # Case 2: provided then aged out.
            secondary_rain_sensor_stale = True
        elif self._secondary_rain_data.is_valid:
            # Case 3: fresh. Duck-typed access matches the rain-vote
            # helper (see TYPE_CHECKING note at module top).
            reading = self._secondary_rain_data.value
            if reading is not None:
                secondary_rain_is_raining = bool(
                    getattr(reading, "is_raining", False)
                )

        status = SafetyStatus(
            timestamp=datetime.now(),
            action=action,
            is_safe=is_safe,
            reasons=reasons if reasons else ["All systems nominal"],
            alert_level=alert_level,
            weather_ok=weather_ok,
            clouds_ok=clouds_ok,
            daylight_ok=daylight_ok,
            mount_ok=True,  # Would check mount status here
            power_ok=power_ok,
            enclosure_ok=enclosure_ok,
            altitude_ok=altitude_ok,
            meridian_ok=meridian_ok,
            network_ok=network_ok,  # Step 489
            temperature_f=temp,
            humidity_percent=humidity,
            wind_speed_mph=wind,
            cloud_cover_percent=cloud_cover,
            sun_altitude_deg=self._sun_altitude,
            # Step 465: Rain holdoff
            rain_holdoff_active=not rain_holdoff_ok,
            rain_holdoff_remaining_min=rain_holdoff_remaining,
            # Step 469: Power status
            ups_battery_percent=self._ups_battery_percent,
            ups_on_battery=self._ups_on_battery,
            # Step 486: Staged battery shutdown
            battery_shutdown_stage=battery_stage,
            # Step 470: Enclosure status
            enclosure_open=self._enclosure_open,
            # Step 467: Target altitude
            target_altitude_deg=self._target_altitude,
            # Step 489: Network status
            network_connected=self._network_connected,
            network_latency_ms=self._network_latency_ms,
            # SAFE-002 review Important #2: secondary-rain telemetry.
            secondary_rain_is_raining=secondary_rain_is_raining,
            secondary_rain_sensor_stale=secondary_rain_sensor_stale,
        )

        self._last_status = status
        return status

    async def execute_action(self, action: SafetyAction):
        """Execute a safety action on the mount."""
        if not self.mount:
            logger.warning("No mount controller configured")
            return

        try:
            if action == SafetyAction.EMERGENCY_CLOSE:
                logger.critical("EMERGENCY CLOSE - Parking immediately!")
                self._state = ObservatoryState.EMERGENCY
                await self.mount.stop()
                await self.mount.park()
                # SAFE-001 (Risk #2): the action's name promises a
                # roof close — make it real. Prior code only stopped
                # and parked the mount, leaving the enclosure open
                # while rain landed on the primary. The run() loop
                # gates this dispatch behind
                # _wait_for_cancellations_to_drain so any in-flight
                # capture/slew has a bounded window to honor its
                # cancel token BEFORE this irreversible step.
                await self._close_enclosure_safely("EMERGENCY_CLOSE")

            elif action == SafetyAction.PARK_AND_WAIT:
                logger.warning("Unsafe conditions - Parking telescope")
                self._state = ObservatoryState.PARKING
                await self.mount.stop()
                await self.mount.park()

            elif action == SafetyAction.PARK_FOR_DAYLIGHT:
                logger.info("Daylight approaching - Parking for day")
                self._state = ObservatoryState.PARKING
                await self.mount.park()

            elif action == SafetyAction.SAFE_TO_OBSERVE:
                if self._state in [ObservatoryState.PARKED, ObservatoryState.CLOSED]:
                    logger.info("Conditions safe - Ready to observe")
                    self._state = ObservatoryState.OPEN_IDLE

            # Step 486: Battery shutdown actions
            elif action == SafetyAction.LOW_BATTERY_WARNING:
                logger.warning("Low battery warning - reducing non-essential operations")
                # Could disable non-essential services here

            elif action == SafetyAction.LOW_BATTERY_PARK:
                logger.warning("Low battery - parking telescope")
                self._state = ObservatoryState.PARKING
                await self.mount.stop()
                await self.mount.park()

            elif action == SafetyAction.LOW_BATTERY_SHUTDOWN:
                logger.critical("CRITICAL: Battery depleted - emergency shutdown!")
                self._state = ObservatoryState.EMERGENCY
                await self.mount.stop()
                await self.mount.park()
                # SAFE-001: shared helper (was inline try/except). Both
                # this and EMERGENCY_CLOSE close the enclosure on the
                # destructive path; consolidating the call site makes
                # the cancel-before-close audit easier.
                await self._close_enclosure_safely("LOW_BATTERY_SHUTDOWN")

            # Step 489: Network failure action
            elif action == SafetyAction.NETWORK_FAILURE:
                logger.warning("Network failure - parking telescope for safety")
                self._state = ObservatoryState.PARKING
                await self.mount.stop()
                await self.mount.park()

            # Step 485: Power failure action
            elif action == SafetyAction.POWER_FAILURE:
                logger.critical("POWER FAILURE - executing emergency response")
                self._state = ObservatoryState.EMERGENCY
                # Execute the full power failure response sequence
                await self.handle_power_failure_response()

        except Exception as e:
            logger.error(f"Failed to execute safety action: {e}")

    async def _close_enclosure_safely(self, calling_action: str) -> None:
        """SAFE-001: log-and-swallow enclosure close used by destructive actions.

        Extracted from inline try/except in EMERGENCY_CLOSE and
        LOW_BATTERY_SHUTDOWN. Both paths are the "irreversible roof
        close" branch of execute_action(); having a single helper makes
        the cancel-before-close audit trivially greppable and keeps
        execute_action's per-branch statement count under ruff's
        PLR0915 threshold.

        ``calling_action`` is purely for the error log so an operator
        reading "EMERGENCY_CLOSE: enclosure.close failed" knows which
        upstream decision triggered the close. Swallows the exception
        (vs. re-raising) because the run() loop must keep running even
        if the enclosure driver throws — the watchdog (SAFE-004) is
        the defense-in-depth for hardware that has stopped responding.
        """
        if self.enclosure is None:
            return
        try:
            result = self.enclosure.close()
            # Support both sync stubs and async enclosure drivers.
            if inspect.isawaitable(result):
                await result
        except Exception as e:
            logger.error(f"{calling_action}: enclosure.close failed: {e}")

    async def _notify_callbacks(self, status: SafetyStatus):
        """Notify registered callbacks of status change."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(status)
                else:
                    callback(status)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    async def _wait_for_cancellations_to_drain(
        self, timeout_s: float = 2.0
    ) -> None:
        """SAFE-001: bounded settling wait for in-flight ops to honor cancellation.

        Called from ``run()`` between ``_notify_callbacks()`` (which
        fires the orchestrator's cancel-on-unsafe hook) and
        ``execute_action()`` for EMERGENCY_CLOSE (which closes the
        enclosure). The cancel is advisory — ARCH-003's CancelToken is
        cooperative. Capture/slew/focus loops check the token at known
        cadences (camera per-frame, mount per-poll-tick).

        Worst-case latency = max(camera_frame_interval,
        mount_poll_interval). 2s is a generous bound for typical configs
        and can be overridden via
        ``SafetyThresholds.cancel_settle_timeout_s``.

        NOT a hard guarantee — if a handler ignores its cancel token,
        we still close the roof on schedule. Safety-first: a missed
        observing window is recoverable; water damage is not.

        A more sophisticated implementation could poll a "is anything
        in-flight" predicate on the orchestrator. For SAFE-001 the
        simple bounded sleep is sufficient: its job is to give
        cooperative cancellation a window, not to verify every handler
        actually quiesced. The watchdog (SAFE-004) is the
        defense-in-depth for the case where this window is exceeded.
        """
        await asyncio.sleep(timeout_s)

    async def run(self, poll_interval: float = 10.0):
        """
        Main monitoring loop.

        Args:
            poll_interval: Seconds between safety evaluations
        """
        logger.info("Safety monitor started")
        self._running = True

        last_action = None

        while self._running:
            try:
                # Evaluate current conditions
                status = self.evaluate()

                # Track unsafe duration
                if not status.is_safe:
                    if self._unsafe_since is None:
                        self._unsafe_since = datetime.now()
                    self._safe_since = None
                else:
                    if self._safe_since is None:
                        self._safe_since = datetime.now()
                    self._unsafe_since = None

                # SAFE-001 (Risk #2): notify callbacks FIRST so the
                # orchestrator's cancel-on-unsafe hook fires BEFORE any
                # irreversible execute_action() call (most notably the
                # EMERGENCY_CLOSE enclosure-close path). The previous
                # ordering inverted this and let the roof close while a
                # capture was still draining frames onto disk — the
                # Phase 1 audit's Risk #2 water-damage scenario.
                #
                # Cancellation is advisory (cooperative tokens). For
                # EMERGENCY_CLOSE we additionally wait a bounded window
                # below so in-flight ops have time to honor their token
                # before the roof is driven. Other actions (warnings,
                # park-and-wait, safe-resume) don't need the wait —
                # they either don't touch the enclosure or are
                # recoverable.
                #
                # NOTE: ``last_action`` is updated at end-of-iteration
                # (not here) because the SAFE_TO_OBSERVE branch below
                # still needs to compare against the PRIOR action to
                # detect the unsafe→safe transition.
                action_changed = status.action != last_action
                if action_changed:
                    await self._notify_callbacks(status)

                # Execute action if conditions warrant
                if status.action != SafetyAction.SAFE_TO_OBSERVE:
                    # Check if unsafe long enough to act
                    if self._unsafe_since:
                        unsafe_duration = (datetime.now() - self._unsafe_since).total_seconds()
                        if unsafe_duration > self.thresholds.unsafe_duration_to_park:
                            # SAFE-001: for EMERGENCY_CLOSE specifically,
                            # give in-flight ops a bounded window to
                            # honor the cancel we just fired before
                            # driving the enclosure. The settle wait
                            # only runs on the destructive path — see
                            # _wait_for_cancellations_to_drain docstring
                            # for the "advisory, not guaranteed" caveat.
                            # Only wait on the action-changed iteration
                            # (avoid stacking settle delays each poll
                            # while the unsafe condition persists).
                            if (
                                status.action == SafetyAction.EMERGENCY_CLOSE
                                and action_changed
                            ):
                                await self._wait_for_cancellations_to_drain(
                                    timeout_s=self.thresholds.cancel_settle_timeout_s,
                                )
                            await self.execute_action(status.action)

                elif status.action == SafetyAction.SAFE_TO_OBSERVE and last_action != SafetyAction.SAFE_TO_OBSERVE:
                    # Check if safe long enough to resume
                    if self._safe_since:
                        safe_duration = (datetime.now() - self._safe_since).total_seconds()
                        if safe_duration > self.thresholds.safe_duration_to_resume:
                            await self.execute_action(status.action)

                # Update last_action ONLY after all branches that
                # depended on the prior value have run.
                if action_changed:
                    last_action = status.action

                # Log status periodically
                if status.alert_level in [AlertLevel.WARNING, AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
                    logger.warning(f"Safety: {status.action.value} - {'; '.join(status.reasons)}")

            except Exception as e:
                logger.error(f"Safety monitor error: {e}")

            await asyncio.sleep(poll_interval)

    def stop(self):
        """Stop the monitoring loop."""
        self._running = False
        logger.info("Safety monitor stopped")


# =============================================================================
# CONVENIENCE CLASS
# =============================================================================

class NightwatchSafetySystem:
    """
    High-level safety system for NIGHTWATCH observatory.

    Combines all safety components into a single interface.
    """

    def __init__(self):
        self.thresholds = SafetyThresholds()
        self.monitor = SafetyMonitor(thresholds=self.thresholds)
        self._tasks = []

    async def start(self):
        """Start all safety monitoring."""
        # Would start weather polling, cloud sensor polling, etc.
        monitor_task = asyncio.create_task(self.monitor.run())
        self._tasks.append(monitor_task)

    async def stop(self):
        """Stop all safety monitoring."""
        self.monitor.stop()
        for task in self._tasks:
            task.cancel()

    def is_safe(self) -> bool:
        """Quick check if observing is currently safe."""
        if self.monitor.last_status:
            return self.monitor.last_status.is_safe
        return False


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    async def test():
        monitor = SafetyMonitor()

        # Simulate weather data
        class MockWeather:
            is_raining = False
            rain_rate_in_hr = 0.0
            wind_speed_mph = 5.0
            wind_gust_mph = 8.0
            humidity_percent = 45.0
            temperature_f = 55.0

        await monitor.update_weather(MockWeather())
        await monitor.update_sun_altitude(-18.0)  # Night

        status = monitor.evaluate()
        print(f"Safe: {status.is_safe}")
        print(f"Action: {status.action.value}")
        print(f"Reasons: {status.reasons}")

    asyncio.run(test())
