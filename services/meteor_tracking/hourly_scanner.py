"""
NIGHTWATCH Hourly Event Scanner
Independent, continuous monitoring of near-Earth events.

Runs as a background task in the Orchestrator, scanning for:
- Fireball events (CNEOS, AMS)
- NEO close approaches (CAD API)
- Active meteor showers
- Space weather events

Unlike the MeteorTrackingService monitor loop (which requires active
watch windows), the HourlyEventScanner runs ALWAYS and independently.

Architecture:
    HourlyEventScanner
      ├── CNEOSClient (fireballs)
      ├── CADClient (NEO close approaches)
      ├── ShowerCalendar (active showers)
      └── EventLog (persistent scan results)

Scan Pattern:
    starting coords → hopi circles → home bases → new days
    Each scan radiates outward from Nevada home base through
    concentric awareness circles, checking all home bases,
    then advancing to the next time window.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

from .fireball_client import CNEOSClient, Fireball
from .close_approach_client import CADClient, CloseApproach, ThreatLevel
from .shower_calendar import ShowerCalendar, MeteorShower
from .hopi_circles import generate_hopi_circles, SearchPattern, haversine_miles
from .lexicon_prayers import LexiconFormatter

logger = logging.getLogger("NIGHTWATCH.HourlyScanner")

# Rank-preserving map from close_approach_client.ThreatLevel to the scanner's
# string levels. Scanner alerts (ScanResult.has_alerts) fire on CLOSE/ALERT,
# i.e. JPL WATCH (<2 LD or potentially hazardous) and ALERT (<1 LD).
THREAT_LEVEL_MAP: Dict[ThreatLevel, str] = {
    ThreatLevel.ROUTINE: "INFO",
    ThreatLevel.NOTABLE: "WATCH",
    ThreatLevel.SIGNIFICANT: "NEAR",
    ThreatLevel.WATCH: "CLOSE",
    ThreatLevel.ALERT: "ALERT",
}


# Home bases for multi-site awareness
HOME_BASES: Dict[str, tuple] = {
    "Nevada": (39.5, -117.0),
    "Astoria": (46.1879, -123.8313),
    "Aliso Viejo": (33.5676, -117.7256),
    "Phoenix": (33.4484, -112.0740),
    "Las Vegas": (36.1699, -115.1398),
}

# Starting coords (primary observatory)
STARTING_COORDS = HOME_BASES["Nevada"]


@dataclass
class ScanEvent:
    """A single event discovered during a scan."""
    event_type: str  # "fireball", "neo_approach", "shower_active", "space_weather"
    event_id: str
    timestamp: datetime
    summary: str
    data: Dict[str, Any]
    threat_level: str = "INFO"  # INFO, WATCH, NEAR, CLOSE, ALERT
    home_base: Optional[str] = None  # Which home base it's nearest to
    hopi_circle: Optional[int] = None  # Which concentric circle it falls in
    distance_from_home_mi: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "summary": self.summary,
            "data": self.data,
            "threat_level": self.threat_level,
            "home_base": self.home_base,
            "hopi_circle": self.hopi_circle,
            "distance_from_home_mi": self.distance_from_home_mi,
        }


@dataclass
class ScanResult:
    """Result of a complete hourly scan cycle."""
    scan_id: str
    scan_time: datetime
    duration_seconds: float
    events_found: int
    fireballs: List[ScanEvent]
    neo_approaches: List[ScanEvent]
    active_showers: List[ScanEvent]
    errors: List[str]
    scan_pattern: str = "starting_coords → hopi_circles → home_bases → new_days"

    @property
    def has_alerts(self) -> bool:
        """Check if any events warrant alerting."""
        all_events = self.fireballs + self.neo_approaches
        return any(e.threat_level in ("CLOSE", "ALERT") for e in all_events)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scan_id": self.scan_id,
            "scan_time": self.scan_time.isoformat(),
            "duration_seconds": self.duration_seconds,
            "events_found": self.events_found,
            "scan_pattern": self.scan_pattern,
            "fireballs": [e.to_dict() for e in self.fireballs],
            "neo_approaches": [e.to_dict() for e in self.neo_approaches],
            "active_showers": [e.to_dict() for e in self.active_showers],
            "errors": self.errors,
        }

    def to_prayer(self) -> str:
        """Format scan result as Lexicon prayer."""
        fmt = LexiconFormatter()
        lines = []

        lines.append("nightwatch-scan.")
        lines.append(f"varek: {self.scan_time.strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"scan-pattern: {self.scan_pattern}")
        lines.append("")

        if not self.fireballs and not self.neo_approaches:
            lines.append("sky-quiet: ne-events-found")
        else:
            if self.fireballs:
                lines.append(f"luminara-count: {len(self.fireballs)}")
                for fb in self.fireballs[:3]:
                    lines.append(f"  luminara: {fb.summary}")

            if self.neo_approaches:
                lines.append(f"neo-approach-count: {len(self.neo_approaches)}")
                for neo in self.neo_approaches[:5]:
                    lines.append(f"  approach: {neo.summary}")

        if self.active_showers:
            lines.append("")
            for shower in self.active_showers:
                lines.append(f"shower-active: {shower.summary}")

        if self.errors:
            lines.append("")
            lines.append(f"scan-errors: {len(self.errors)}")

        lines.append("")
        lines.append("presa-nightwatch.")
        lines.append(fmt.ALCHEMICAL_SYMBOL)

        return "\n".join(lines)


@dataclass
class ScannerConfig:
    """Configuration for the hourly event scanner."""
    # Scan interval
    scan_interval_seconds: float = 3600.0  # 1 hour default
    initial_delay_seconds: float = 10.0  # Wait before first scan

    # Data sources
    cneos_enabled: bool = True
    cad_enabled: bool = True
    neo_feed_enabled: bool = False  # Optional, rate-limited

    # NEO approach thresholds
    max_approach_distance_au: float = 0.05  # PHA distance
    lookahead_days: int = 7
    lookback_days: int = 1  # Check recent fireballs

    # Size filter - only alert on objects this bright or brighter
    max_h_magnitude: float = 26.0  # Filter very small objects

    # State persistence
    state_file: Optional[str] = None
    log_file: Optional[str] = None

    # NASA API key for NEO Feed
    nasa_api_key: str = "DEMO_KEY"


class HourlyEventScanner:
    """
    Independent hourly scanner for near-Earth events.

    Runs as a background asyncio task, continuously scanning
    NASA data sources for events of interest to NIGHTWATCH.

    Scan Pattern (each cycle):
    1. Starting coords: Check from primary observatory (Nevada)
    2. Hopi circles: Classify events by distance in concentric rings
    3. Home bases: Check visibility from all known locations
    4. New days: Advance scan window for next cycle

    Does NOT require active watch windows - always scanning.
    """

    def __init__(
        self,
        config: Optional[ScannerConfig] = None,
        alert_callback: Optional[Callable[[ScanResult], Any]] = None,
    ):
        self.config = config or ScannerConfig()
        self._alert_callback = alert_callback

        # API clients
        self._cneos: Optional[CNEOSClient] = None
        self._cad: Optional[CADClient] = None

        # Shower calendar
        self._shower_calendar = ShowerCalendar()

        # State
        self._running = False
        self._scan_task: Optional[asyncio.Task] = None
        self._scan_count = 0
        self._known_event_ids: set = set()
        self._last_scan: Optional[datetime] = None
        self._scan_history: List[ScanResult] = []

        # Hopi circles for spatial classification
        self._hopi_pattern = generate_hopi_circles(
            center_lat=STARTING_COORDS[0],
            center_lon=STARTING_COORDS[1],
            initial_radius_miles=50,
            expansion_factor=2.0,
            max_radius_miles=1000,
            num_circles=5,
        )

        logger.info("HourlyEventScanner initialized")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def scan_count(self) -> int:
        return self._scan_count

    @property
    def last_scan_time(self) -> Optional[datetime]:
        return self._last_scan

    async def start(self):
        """Start the hourly scanner."""
        if self._running:
            return

        # Initialize API clients
        if self.config.cneos_enabled:
            self._cneos = CNEOSClient()
        if self.config.cad_enabled:
            self._cad = CADClient()

        self._running = True
        self._scan_task = asyncio.create_task(self._scan_loop())
        logger.info(
            f"HourlyEventScanner started (interval={self.config.scan_interval_seconds}s)"
        )

    async def stop(self):
        """Stop the hourly scanner."""
        self._running = False
        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
            self._scan_task = None

        # Close clients
        if self._cneos:
            await self._cneos.close()
        if self._cad:
            await self._cad.close()

        # Save final state
        self._save_state()
        logger.info("HourlyEventScanner stopped")

    async def _scan_loop(self):
        """Main scan loop - runs every hour."""
        # Initial delay to let other services start
        await asyncio.sleep(self.config.initial_delay_seconds)

        while self._running:
            try:
                result = await self.run_scan()

                # Notify callback if alerts found
                if self._alert_callback and result.has_alerts:
                    try:
                        if asyncio.iscoroutinefunction(self._alert_callback):
                            await self._alert_callback(result)
                        else:
                            self._alert_callback(result)
                    except Exception as e:
                        logger.error(f"Alert callback error: {e}")

                await asyncio.sleep(self.config.scan_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scan loop error: {e}", exc_info=True)
                await asyncio.sleep(60)  # Back off on error

    async def run_scan(self) -> ScanResult:
        """
        Execute a single scan cycle.

        Pattern: starting coords → hopi circles → home bases → new days

        Returns:
            ScanResult with all events found
        """
        scan_start = datetime.now(timezone.utc)
        scan_id = scan_start.strftime("%Y%m%d%H%M%S")
        self._scan_count += 1

        logger.info(f"Starting scan #{self._scan_count} ({scan_id})")

        errors: List[str] = []
        fireball_events: List[ScanEvent] = []
        neo_events: List[ScanEvent] = []
        shower_events: List[ScanEvent] = []

        # =====================================================================
        # Step 1: STARTING COORDS - Fetch data centered on primary observatory
        # =====================================================================
        logger.debug("Step 1: Starting coords scan")

        # Fetch fireballs
        if self._cneos:
            try:
                fireballs = await self._cneos.fetch_fireballs(
                    start_date=datetime.now(timezone.utc)
                    - timedelta(days=self.config.lookback_days),
                    end_date=datetime.now(timezone.utc),
                )
                for fb in fireballs:
                    event = self._process_fireball(fb)
                    if event and event.event_id not in self._known_event_ids:
                        fireball_events.append(event)
                        self._known_event_ids.add(event.event_id)
            except Exception as e:
                errors.append(f"CNEOS fetch error: {e}")
                logger.error(f"CNEOS fetch error: {e}")

        # Fetch NEO close approaches
        if self._cad:
            try:
                approaches = await self._cad.fetch_close_approaches(
                    date_min=datetime.now(timezone.utc),
                    date_max=datetime.now(timezone.utc)
                    + timedelta(days=self.config.lookahead_days),
                    dist_max_au=self.config.max_approach_distance_au,
                )
                for approach in approaches:
                    event = self._process_approach(approach)
                    if event and event.event_id not in self._known_event_ids:
                        neo_events.append(event)
                        self._known_event_ids.add(event.event_id)
            except Exception as e:
                errors.append(f"CAD fetch error: {e}")
                logger.error(f"CAD fetch error: {e}")

        # =====================================================================
        # Step 2: HOPI CIRCLES - Classify by distance from starting coords
        # =====================================================================
        logger.debug("Step 2: Hopi circles classification")

        for event in fireball_events:
            lat = event.data.get("latitude")
            lon = event.data.get("longitude")
            if lat is not None and lon is not None:
                circle = self._classify_hopi_circle(lat, lon)
                event.hopi_circle = circle
                event.distance_from_home_mi = haversine_miles(
                    STARTING_COORDS[0], STARTING_COORDS[1], lat, lon
                )

        # =====================================================================
        # Step 3: HOME BASES - Check visibility from all locations
        # =====================================================================
        logger.debug("Step 3: Home bases check")

        for event in fireball_events:
            lat = event.data.get("latitude")
            lon = event.data.get("longitude")
            if lat is not None and lon is not None:
                nearest = self._find_nearest_home_base(lat, lon)
                event.home_base = nearest

        # =====================================================================
        # Step 4: NEW DAYS - Check active/upcoming showers
        # =====================================================================
        logger.debug("Step 4: New days - shower calendar check")

        active_showers = self._shower_calendar.get_active_showers()
        for shower in active_showers:
            shower_event = ScanEvent(
                event_type="shower_active",
                event_id=f"shower_{shower.name}_{shower.peak_start.isoformat()}",
                timestamp=datetime.now(timezone.utc),
                summary=f"{shower.name} active (ZHR {shower.zhr}/hr, "
                f"radiant in {shower.radiant_constellation})",
                data={
                    "name": shower.name,
                    "zhr": shower.zhr,
                    "peak_start": shower.peak_start.isoformat(),
                    "peak_end": shower.peak_end.isoformat(),
                    "velocity_km_s": shower.velocity_km_s,
                    "parent_body": shower.parent_body,
                },
                threat_level="INFO",
            )
            shower_events.append(shower_event)

        # Also check upcoming showers (next 7 days)
        upcoming = self._shower_calendar.get_upcoming_showers(days=7)
        for shower in upcoming:
            if shower not in active_showers:
                days_until = shower.days_until_peak()
                shower_event = ScanEvent(
                    event_type="shower_upcoming",
                    event_id=f"shower_upcoming_{shower.name}",
                    timestamp=datetime.now(timezone.utc),
                    summary=f"{shower.name} in {days_until} days "
                    f"(ZHR {shower.zhr}/hr)",
                    data={
                        "name": shower.name,
                        "zhr": shower.zhr,
                        "days_until": days_until,
                    },
                    threat_level="INFO",
                )
                shower_events.append(shower_event)

        # =====================================================================
        # Build result
        # =====================================================================
        scan_end = datetime.now(timezone.utc)
        duration = (scan_end - scan_start).total_seconds()

        result = ScanResult(
            scan_id=scan_id,
            scan_time=scan_start,
            duration_seconds=duration,
            events_found=len(fireball_events) + len(neo_events) + len(shower_events),
            fireballs=fireball_events,
            neo_approaches=neo_events,
            active_showers=shower_events,
            errors=errors,
        )

        self._last_scan = scan_start
        self._scan_history.append(result)

        # Keep last 24 scans in memory
        if len(self._scan_history) > 24:
            self._scan_history = self._scan_history[-24:]

        # Save state
        self._save_state()

        # Log summary
        logger.info(
            f"Scan #{self._scan_count} complete: "
            f"{len(fireball_events)} fireballs, "
            f"{len(neo_events)} NEO approaches, "
            f"{len(shower_events)} shower events, "
            f"{len(errors)} errors "
            f"({duration:.1f}s)"
        )

        return result

    def _process_fireball(self, fb: Fireball) -> Optional[ScanEvent]:
        """Convert a Fireball to a ScanEvent."""
        if fb.latitude is None or fb.longitude is None:
            return None

        mag = fb.magnitude_estimate
        threat = "INFO"
        if mag is not None:
            if mag < -15:
                threat = "ALERT"
            elif mag < -10:
                threat = "CLOSE"
            elif mag < -6:
                threat = "NEAR"
            elif mag < -4:
                threat = "WATCH"

        mag_str = f"mag {mag:.0f}" if mag else "mag unknown"
        return ScanEvent(
            event_type="fireball",
            event_id=fb.fireball_id,
            timestamp=fb.date,
            summary=f"Fireball at {fb.coordinates_str}, {mag_str}, "
            f"v={fb.velocity_km_s or 0:.0f}km/s",
            data={
                "latitude": fb.latitude,
                "longitude": fb.longitude,
                "altitude_km": fb.altitude_km,
                "velocity_km_s": fb.velocity_km_s,
                "energy_j": fb.total_radiated_energy_j,
                "impact_energy_kt": fb.calculated_total_impact_energy_kt,
                "magnitude": mag,
            },
            threat_level=threat,
        )

    def _process_approach(self, approach: CloseApproach) -> Optional[ScanEvent]:
        """Convert a CloseApproach to a ScanEvent."""
        # Filter very small objects
        if (
            approach.absolute_magnitude_h is not None
            and approach.absolute_magnitude_h > self.config.max_h_magnitude
        ):
            return None

        threat = THREAT_LEVEL_MAP[approach.threat_level]
        size = approach.estimated_diameter_str

        return ScanEvent(
            event_type="neo_approach",
            event_id=approach.approach_id,
            timestamp=approach.close_approach_date,
            summary=f"{approach.designation} ({size}) at "
            f"{approach.distance_ld:.1f} LD, "
            f"{approach.relative_velocity_km_s:.1f} km/s on "
            f"{approach.close_approach_date.strftime('%Y-%m-%d')}",
            data={
                "designation": approach.designation,
                "fullname": approach.fullname,
                "distance_au": approach.distance_au,
                "distance_ld": approach.distance_ld,
                "distance_km": approach.distance_km,
                "velocity_km_s": approach.relative_velocity_km_s,
                "h_magnitude": approach.absolute_magnitude_h,
                "diameter_min_m": approach.estimated_diameter_m_min,
                "diameter_max_m": approach.estimated_diameter_m_max,
                "size_category": size,
                "is_pha": approach.is_potentially_hazardous,
            },
            threat_level=threat,
        )

    def _classify_hopi_circle(self, lat: float, lon: float) -> int:
        """Classify a point by which hopi circle it falls in."""
        for circle in self._hopi_pattern.circles:
            if circle.contains_point(lat, lon):
                return circle.priority
        # Beyond all circles
        return len(self._hopi_pattern.circles) + 1

    def _find_nearest_home_base(self, lat: float, lon: float) -> str:
        """Find the nearest home base to a point."""
        nearest = "Nevada"
        min_dist = float("inf")

        for name, (base_lat, base_lon) in HOME_BASES.items():
            dist = haversine_miles(base_lat, base_lon, lat, lon)
            if dist < min_dist:
                min_dist = dist
                nearest = name

        return nearest

    def _save_state(self):
        """Save scanner state to file."""
        if not self.config.state_file:
            return

        try:
            state = {
                "scan_count": self._scan_count,
                "last_scan": self._last_scan.isoformat() if self._last_scan else None,
                "known_event_ids": list(self._known_event_ids)[-500:],
                "last_result": (
                    self._scan_history[-1].to_dict() if self._scan_history else None
                ),
            }

            path = Path(self.config.state_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save scanner state: {e}")

    def _load_state(self):
        """Load scanner state from file."""
        if not self.config.state_file:
            return

        path = Path(self.config.state_file)
        if not path.exists():
            return

        try:
            with open(path) as f:
                state = json.load(f)

            self._scan_count = state.get("scan_count", 0)
            if state.get("last_scan"):
                self._last_scan = datetime.fromisoformat(state["last_scan"])
            self._known_event_ids = set(state.get("known_event_ids", []))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Could not load scanner state: {e}")

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    async def get_status(self) -> str:
        """Get scanner status in Lexicon style."""
        fmt = LexiconFormatter()
        lines = []

        lines.append("nightwatch-scanner-status.")
        lines.append("")
        lines.append(f"scans-completed: {self._scan_count}")

        if self._last_scan:
            lines.append(
                f"last-scan: {self._last_scan.strftime('%Y-%m-%d %H:%M')}"
            )
        else:
            lines.append("last-scan: ne-yet")

        lines.append(f"events-tracked: {len(self._known_event_ids)}")
        lines.append(f"scanner-running: {'es' if self._running else 'ne'}")

        if self._scan_history:
            latest = self._scan_history[-1]
            lines.append("")
            lines.append(f"latest-fireballs: {len(latest.fireballs)}")
            lines.append(f"latest-neo: {len(latest.neo_approaches)}")
            if latest.errors:
                lines.append(f"latest-errors: {len(latest.errors)}")

        lines.append("")
        lines.append("presa-when-called.")
        lines.append(fmt.ALCHEMICAL_SYMBOL)

        return "\n".join(lines)

    def get_latest_result(self) -> Optional[ScanResult]:
        """Get the most recent scan result."""
        return self._scan_history[-1] if self._scan_history else None

    def get_scan_history(self, limit: int = 10) -> List[ScanResult]:
        """Get recent scan history."""
        return self._scan_history[-limit:]
