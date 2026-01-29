"""
NIGHTWATCH Meteor Tracking Service
Main service that integrates with NIGHTWATCH observatory.

Provides async monitoring, fireball detection, and Lexicon prayer alerts.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Callable, Any

from .fireball_client import CNEOSClient, AMSClient, Fireball, AMSFireball
from .shower_calendar import ShowerCalendar, MeteorShower, get_next_major_shower
from .trajectory import calculate_trajectory, is_visible_from, TrajectoryResult
from .hopi_circles import generate_hopi_circles, SearchPattern
from .watch_manager import WatchManager, WatchWindow, WatchIntensity
from .lexicon_prayers import (
    generate_prayer_of_finding,
    generate_prayer_of_watching,
    generate_status_prayer,
)

logger = logging.getLogger("NIGHTWATCH.MeteorTracking")


@dataclass
class MeteorConfig:
    """Configuration for meteor tracking service."""
    # Default location (Nevada property)
    default_latitude: float = 39.5
    default_longitude: float = -117.0
    default_location_name: str = "Nevada"

    # Monitoring settings
    poll_interval_seconds: float = 1800  # 30 minutes
    min_magnitude: float = -4  # Only alert on bright fireballs
    visibility_check: bool = True

    # Data source settings
    cneos_enabled: bool = True
    ams_enabled: bool = True

    # State persistence
    state_file: Optional[str] = None


@dataclass
class MeteorAlert:
    """A meteor alert with all data and prayer."""
    timestamp: datetime
    fireball: Fireball
    window: WatchWindow
    trajectory: Optional[TrajectoryResult]
    search_pattern: Optional[SearchPattern]
    prayer: str
    sky_conditions: str


class MeteorTrackingService:
    """
    Main meteor tracking service for NIGHTWATCH.

    Integrates with:
    - NIGHTWATCH alert system for notifications
    - Voice pipeline for natural language commands
    - Observatory safety system for status awareness

    Features:
    - Natural language watch window creation
    - Real-time fireball monitoring during watch windows
    - Trajectory calculation and debris prediction
    - Lexicon prayer generation for findings
    """

    def __init__(
        self,
        config: Optional[MeteorConfig] = None,
        alert_callback: Optional[Callable[[MeteorAlert], Any]] = None
    ):
        self.config = config or MeteorConfig()
        self._alert_callback = alert_callback

        # Initialize clients
        self._cneos = CNEOSClient() if self.config.cneos_enabled else None
        self._ams = AMSClient() if self.config.ams_enabled else None

        # Initialize managers
        self._watch_manager = WatchManager(
            state_file=self.config.state_file,
            default_lat=self.config.default_latitude,
            default_lon=self.config.default_longitude,
            default_location=self.config.default_location_name
        )
        self._shower_calendar = ShowerCalendar()

        # Monitoring state
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._known_fireballs: set = set()

        logger.info("Meteor tracking service initialized")

    async def start(self):
        """Start the meteor monitoring service."""
        if self._running:
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Meteor tracking service started")

    async def stop(self):
        """Stop the meteor monitoring service."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

        # Close clients
        if self._cneos:
            await self._cneos.close()
        if self._ams:
            await self._ams.close()

        logger.info("Meteor tracking service stopped")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                await self._check_for_fireballs()
                await asyncio.sleep(self.config.poll_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(60)  # Back off on error

    async def _check_for_fireballs(self):
        """Check for new fireballs in active watch windows."""
        active_windows = self._watch_manager.get_active_windows()
        if not active_windows:
            return

        # Fetch recent fireballs
        fireballs = []
        if self._cneos:
            cneos_fireballs = await self._cneos.fetch_fireballs(
                start_date=datetime.utcnow() - timedelta(days=1),
                end_date=datetime.utcnow()
            )
            fireballs.extend(cneos_fireballs)

        self._watch_manager.last_check = datetime.now()
        self._watch_manager.save_state()

        # Check each fireball against windows
        for window in active_windows:
            for fb in fireballs:
                await self._process_fireball(window, fb)

    async def _process_fireball(self, window: WatchWindow, fireball: Fireball):
        """Process a single fireball for a watch window."""
        # Skip if already seen
        fb_id = fireball.fireball_id
        if fb_id in self._known_fireballs:
            return

        # Check coordinates
        if fireball.latitude is None or fireball.longitude is None:
            return

        # Check visibility
        if self.config.visibility_check:
            visible = is_visible_from(
                window.latitude, window.longitude,
                fireball.latitude, fireball.longitude,
                event_alt_km=80.0
            )
            if not visible:
                return

        # Check magnitude threshold
        if fireball.magnitude_estimate and fireball.magnitude_estimate > self.config.min_magnitude:
            return

        # New fireball found!
        self._known_fireballs.add(fb_id)
        logger.info(f"Fireball detected: {fb_id} at {fireball.coordinates_str}")

        # Generate alert
        alert = await self._create_alert(window, fireball)

        # Notify callback
        if self._alert_callback:
            try:
                if asyncio.iscoroutinefunction(self._alert_callback):
                    await self._alert_callback(alert)
                else:
                    self._alert_callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

    async def _create_alert(self, window: WatchWindow, fireball: Fireball) -> MeteorAlert:
        """Create a full meteor alert with prayer."""
        # Calculate trajectory if we have enough data
        trajectory = None
        if fireball.velocity_km_s:
            trajectory = calculate_trajectory(
                start_lat=fireball.latitude,
                start_lon=fireball.longitude,
                end_lat=fireball.latitude,
                end_lon=fireball.longitude,
                velocity_km_s=fireball.velocity_km_s
            )

        # Generate search pattern if debris possible
        search_pattern = None
        if fireball.magnitude_estimate and fireball.magnitude_estimate < -8:
            if trajectory and trajectory.debris_field_center:
                debris_lat, debris_lon = trajectory.debris_field_center
                search_pattern = generate_hopi_circles(
                    debris_lat, debris_lon,
                    initial_radius_miles=10,
                    max_radius_miles=50
                )

        # Build sky conditions string
        sky_conditions = f"{window.location_name.lower()}-sky"

        # Generate prayer
        prayer = generate_prayer_of_finding(
            timestamp=fireball.date,
            lat=fireball.latitude,
            lon=fireball.longitude,
            magnitude=fireball.magnitude_estimate,
            trajectory=trajectory,
            search_pattern=search_pattern,
            sky_conditions=sky_conditions
        )

        return MeteorAlert(
            timestamp=fireball.date,
            fireball=fireball,
            window=window,
            trajectory=trajectory,
            search_pattern=search_pattern,
            prayer=prayer,
            sky_conditions=sky_conditions
        )

    # =========================================================================
    # PUBLIC API (for voice tools)
    # =========================================================================

    async def add_watch(self, text: str) -> str:
        """
        Add a watch window from natural language.

        Args:
            text: Natural language request (e.g., "Watch for Perseids next week")

        Returns:
            Confirmation message with Prayer of Watching
        """
        window = self._watch_manager.add_watch(text)

        # Get shower ZHR if applicable
        zhr = None
        if window.shower_name:
            shower = self._shower_calendar.get_shower_by_name(window.shower_name)
            if shower:
                zhr = shower.zhr

        # Generate watching prayer
        prayer = generate_prayer_of_watching(
            start_time=window.start_time,
            end_time=window.end_time,
            location_name=window.location_name,
            lat=window.latitude,
            lon=window.longitude,
            shower_name=window.shower_name,
            zhr=zhr
        )

        return f"Watch window created: {window.id}\n\n{prayer}"

    async def get_status(self) -> str:
        """
        Get current nightwatch status.

        Returns:
            Status report in Lexicon style
        """
        active = self._watch_manager.get_active_windows()
        next_shower = get_next_major_shower()

        return generate_status_prayer(
            active_windows=len(active),
            last_check=self._watch_manager.last_check,
            known_fireballs=len(self._known_fireballs),
            next_shower_name=next_shower.name if next_shower else None,
            next_shower_date=str(next_shower.peak_start) if next_shower else None
        )

    async def get_shower_info(self, shower_name: Optional[str] = None) -> str:
        """
        Get meteor shower information.

        Args:
            shower_name: Specific shower to query, or None for upcoming

        Returns:
            Shower information
        """
        if shower_name:
            shower = self._shower_calendar.get_shower_by_name(shower_name)
            if shower:
                return self._format_shower_info(shower)
            return f"Shower not found: {shower_name}"

        # Return upcoming showers
        upcoming = self._shower_calendar.get_upcoming_showers(days=90)
        if not upcoming:
            return "No major showers in the next 90 days."

        lines = ["Upcoming meteor showers:"]
        for s in upcoming[:5]:
            lines.append(f"  {s.name}: {s.peak_start} to {s.peak_end}")
            lines.append(f"    ZHR: {s.zhr}/hour, Parent: {s.parent_body}")
            lines.append("")

        return "\n".join(lines)

    def _format_shower_info(self, shower: MeteorShower) -> str:
        """Format detailed shower information."""
        lines = [
            f"Meteor Shower: {shower.name}",
            f"Peak: {shower.peak_start} to {shower.peak_end}",
            f"ZHR: {shower.zhr} meteors/hour (ideal conditions)",
            f"Velocity: {shower.velocity_km_s} km/s",
            f"Radiant: {shower.radiant_constellation} ({shower.radiant_ra}°, {shower.radiant_dec}°)",
            f"Parent body: {shower.parent_body}",
        ]
        if shower.notes:
            lines.append(f"Notes: {shower.notes}")

        return "\n".join(lines)

    async def check_now(self) -> str:
        """
        Manually trigger a fireball check.

        Returns:
            Results of check
        """
        active = self._watch_manager.get_active_windows()
        if not active:
            return "No active watch windows. Add one with 'watch for meteors tonight'."

        await self._check_for_fireballs()

        return f"Check complete. {len(self._known_fireballs)} fireballs tracked."

    def get_active_windows(self) -> List[WatchWindow]:
        """Get currently active watch windows."""
        return self._watch_manager.get_active_windows()

    def cleanup_expired(self):
        """Remove expired watch windows."""
        self._watch_manager.cleanup_expired()
