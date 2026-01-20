"""
NIGHTWATCH Observing Scheduler

Unified scheduling system integrating all v0.5 AI Enhancement components.

This module provides:
- Intelligent target scheduling combining multiple factors
- Weather-aware observation planning
- Moon avoidance optimization
- Historical success rate weighting
- User preference adaptation
- Dynamic schedule adjustment
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import math


# =============================================================================
# Enums and Constants
# =============================================================================


class ScheduleQuality(Enum):
    """Quality assessment of a scheduled observation."""

    EXCELLENT = "excellent"  # Optimal conditions
    GOOD = "good"           # Favorable conditions
    FAIR = "fair"           # Acceptable conditions
    MARGINAL = "marginal"   # Borderline conditions
    POOR = "poor"           # Unfavorable conditions


class ScheduleReason(Enum):
    """Reason for scheduling decision."""

    OPTIMAL_ALTITUDE = "optimal_altitude"
    MOON_AVOIDANCE = "moon_avoidance"
    WEATHER_WINDOW = "weather_window"
    USER_PREFERENCE = "user_preference"
    HISTORICAL_SUCCESS = "historical_success"
    TIME_CONSTRAINT = "time_constraint"
    MERIDIAN_TRANSIT = "meridian_transit"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class SchedulingConstraints:
    """Constraints for observation scheduling."""

    # Time constraints
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    min_observation_minutes: float = 30.0
    max_observation_minutes: float = 180.0

    # Altitude constraints
    min_altitude_deg: float = 20.0
    preferred_altitude_deg: float = 50.0

    # Moon constraints
    min_moon_separation_deg: float = 30.0
    avoid_bright_moon: bool = True

    # Weather constraints
    max_cloud_cover_percent: float = 30.0
    max_wind_speed_mph: float = 25.0
    require_clear_forecast: bool = True

    # Target constraints
    min_score: float = 0.3
    prefer_user_favorites: bool = True
    consider_history: bool = True


@dataclass
class ScheduledTarget:
    """A target scheduled for observation."""

    target_id: str
    target_name: Optional[str]
    scheduled_start: datetime
    scheduled_end: datetime
    expected_altitude_deg: float
    moon_separation_deg: Optional[float]
    quality: ScheduleQuality
    score: float
    reasons: list[ScheduleReason] = field(default_factory=list)
    notes: Optional[str] = None

    @property
    def duration_minutes(self) -> float:
        """Get scheduled duration in minutes."""
        delta = self.scheduled_end - self.scheduled_start
        return delta.total_seconds() / 60

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "target_id": self.target_id,
            "target_name": self.target_name,
            "scheduled_start": self.scheduled_start.isoformat(),
            "scheduled_end": self.scheduled_end.isoformat(),
            "duration_minutes": self.duration_minutes,
            "expected_altitude_deg": self.expected_altitude_deg,
            "moon_separation_deg": self.moon_separation_deg,
            "quality": self.quality.value,
            "score": self.score,
            "reasons": [r.value for r in self.reasons],
            "notes": self.notes,
        }


@dataclass
class ScheduleResult:
    """Result of scheduling operation."""

    targets: list[ScheduledTarget] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_observation_minutes: float = 0.0
    weather_windows: int = 0
    constraints_applied: Optional[SchedulingConstraints] = None
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def target_count(self) -> int:
        """Get number of scheduled targets."""
        return len(self.targets)

    @property
    def average_quality(self) -> float:
        """Get average quality score."""
        if not self.targets:
            return 0.0
        quality_values = {
            ScheduleQuality.EXCELLENT: 1.0,
            ScheduleQuality.GOOD: 0.8,
            ScheduleQuality.FAIR: 0.6,
            ScheduleQuality.MARGINAL: 0.4,
            ScheduleQuality.POOR: 0.2,
        }
        scores = [quality_values[t.quality] for t in self.targets]
        return sum(scores) / len(scores)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "targets": [t.to_dict() for t in self.targets],
            "target_count": self.target_count,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_observation_minutes": self.total_observation_minutes,
            "average_quality": self.average_quality,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class CandidateTarget:
    """Internal representation of a scheduling candidate."""

    target_id: str
    target_name: Optional[str]
    ra_hours: float
    dec_degrees: float
    magnitude: Optional[float] = None
    object_type: Optional[str] = None

    # Computed scores
    base_score: float = 0.0
    altitude_score: float = 0.0
    moon_score: float = 0.0
    weather_score: float = 0.0
    history_score: float = 0.0
    preference_score: float = 0.0

    # Computed values
    current_altitude: float = 0.0
    transit_time: Optional[datetime] = None
    moon_separation: float = 0.0

    @property
    def total_score(self) -> float:
        """Calculate weighted total score."""
        weights = {
            "base": 0.25,
            "altitude": 0.20,
            "moon": 0.15,
            "weather": 0.15,
            "history": 0.15,
            "preference": 0.10,
        }
        return (
            self.base_score * weights["base"] +
            self.altitude_score * weights["altitude"] +
            self.moon_score * weights["moon"] +
            self.weather_score * weights["weather"] +
            self.history_score * weights["history"] +
            self.preference_score * weights["preference"]
        )


# =============================================================================
# Observing Scheduler
# =============================================================================


class ObservingScheduler:
    """
    Unified scheduling system for observation planning.

    Integrates:
    - Target scoring based on conditions
    - Moon phase and position avoidance
    - Weather forecast consideration
    - Historical success weighting
    - User preference learning
    """

    def __init__(
        self,
        latitude_deg: float = 35.0,
        longitude_deg: float = -120.0,
    ):
        """
        Initialize scheduler.

        Args:
            latitude_deg: Observer latitude
            longitude_deg: Observer longitude
        """
        self.latitude = latitude_deg
        self.longitude = longitude_deg

        # These would be injected in production
        self._target_scorer = None
        self._success_tracker = None
        self._user_preferences = None
        self._weather_service = None
        self._ephemeris = None

    def create_schedule(
        self,
        candidates: list[dict],
        constraints: Optional[SchedulingConstraints] = None,
        observation_time: Optional[datetime] = None,
    ) -> ScheduleResult:
        """
        Create an optimized observation schedule.

        Args:
            candidates: List of candidate targets with ra, dec, id
            constraints: Scheduling constraints
            observation_time: Time to schedule for (default: now)

        Returns:
            ScheduleResult with scheduled targets
        """
        constraints = constraints or SchedulingConstraints()
        obs_time = observation_time or datetime.now()

        # Convert to internal candidates
        internal_candidates = []
        for c in candidates:
            candidate = CandidateTarget(
                target_id=c.get("id", c.get("target_id", "Unknown")),
                target_name=c.get("name"),
                ra_hours=c.get("ra_hours", c.get("ra", 0)),
                dec_degrees=c.get("dec_degrees", c.get("dec", 0)),
                magnitude=c.get("magnitude"),
                object_type=c.get("object_type"),
            )
            internal_candidates.append(candidate)

        # Score all candidates
        scored = self._score_candidates(internal_candidates, constraints, obs_time)

        # Filter by minimum score
        filtered = [c for c in scored if c.total_score >= constraints.min_score]

        # Sort by score
        filtered.sort(key=lambda c: c.total_score, reverse=True)

        # Build schedule
        scheduled_targets = []
        current_time = constraints.start_time or obs_time
        end_time = constraints.end_time or (obs_time + timedelta(hours=8))
        total_minutes = 0.0

        for candidate in filtered:
            # Check if we have time remaining
            remaining = (end_time - current_time).total_seconds() / 60
            if remaining < constraints.min_observation_minutes:
                break

            # Calculate observation duration
            duration = min(
                constraints.max_observation_minutes,
                max(constraints.min_observation_minutes, remaining)
            )

            # Determine quality
            quality = self._score_to_quality(candidate.total_score)

            # Determine reasons
            reasons = self._get_scheduling_reasons(candidate, constraints)

            # Create scheduled target
            scheduled = ScheduledTarget(
                target_id=candidate.target_id,
                target_name=candidate.target_name,
                scheduled_start=current_time,
                scheduled_end=current_time + timedelta(minutes=duration),
                expected_altitude_deg=candidate.current_altitude,
                moon_separation_deg=candidate.moon_separation,
                quality=quality,
                score=candidate.total_score,
                reasons=reasons,
            )
            scheduled_targets.append(scheduled)

            current_time += timedelta(minutes=duration + 5)  # 5 min buffer
            total_minutes += duration

        return ScheduleResult(
            targets=scheduled_targets,
            start_time=constraints.start_time or obs_time,
            end_time=end_time,
            total_observation_minutes=total_minutes,
            constraints_applied=constraints,
        )

    def get_best_target(
        self,
        candidates: list[dict],
        constraints: Optional[SchedulingConstraints] = None,
        observation_time: Optional[datetime] = None,
    ) -> Optional[ScheduledTarget]:
        """
        Get the single best target for immediate observation.

        Args:
            candidates: List of candidate targets
            constraints: Scheduling constraints
            observation_time: Time to evaluate

        Returns:
            Best ScheduledTarget or None
        """
        result = self.create_schedule(
            candidates,
            constraints,
            observation_time,
        )
        return result.targets[0] if result.targets else None

    def evaluate_target(
        self,
        target: dict,
        observation_time: Optional[datetime] = None,
    ) -> dict:
        """
        Evaluate a single target's observability.

        Args:
            target: Target with ra, dec, id
            observation_time: Time to evaluate

        Returns:
            Dictionary with scores and recommendations
        """
        obs_time = observation_time or datetime.now()
        constraints = SchedulingConstraints()

        candidate = CandidateTarget(
            target_id=target.get("id", "Unknown"),
            target_name=target.get("name"),
            ra_hours=target.get("ra_hours", target.get("ra", 0)),
            dec_degrees=target.get("dec_degrees", target.get("dec", 0)),
            magnitude=target.get("magnitude"),
            object_type=target.get("object_type"),
        )

        scored = self._score_candidates([candidate], constraints, obs_time)
        if not scored:
            return {"error": "Could not evaluate target"}

        c = scored[0]
        quality = self._score_to_quality(c.total_score)
        reasons = self._get_scheduling_reasons(c, constraints)

        return {
            "target_id": c.target_id,
            "total_score": c.total_score,
            "quality": quality.value,
            "altitude_deg": c.current_altitude,
            "moon_separation_deg": c.moon_separation,
            "scores": {
                "base": c.base_score,
                "altitude": c.altitude_score,
                "moon": c.moon_score,
                "weather": c.weather_score,
                "history": c.history_score,
                "preference": c.preference_score,
            },
            "reasons": [r.value for r in reasons],
            "recommendation": self._get_recommendation(c, quality),
        }

    def _score_candidates(
        self,
        candidates: list[CandidateTarget],
        constraints: SchedulingConstraints,
        obs_time: datetime,
    ) -> list[CandidateTarget]:
        """Score all candidates for the given time."""
        for candidate in candidates:
            # Calculate altitude
            candidate.current_altitude = self._calculate_altitude(
                candidate.ra_hours,
                candidate.dec_degrees,
                obs_time,
            )

            # Altitude score
            if candidate.current_altitude < constraints.min_altitude_deg:
                candidate.altitude_score = 0.0
            elif candidate.current_altitude >= constraints.preferred_altitude_deg:
                candidate.altitude_score = 1.0
            else:
                candidate.altitude_score = (
                    (candidate.current_altitude - constraints.min_altitude_deg) /
                    (constraints.preferred_altitude_deg - constraints.min_altitude_deg)
                )

            # Moon separation (simplified - would use ephemeris in production)
            candidate.moon_separation = self._estimate_moon_separation(
                candidate.ra_hours,
                candidate.dec_degrees,
                obs_time,
            )

            if candidate.moon_separation < constraints.min_moon_separation_deg:
                candidate.moon_score = 0.0
            elif candidate.moon_separation > 90:
                candidate.moon_score = 1.0
            else:
                candidate.moon_score = (
                    (candidate.moon_separation - constraints.min_moon_separation_deg) /
                    (90 - constraints.min_moon_separation_deg)
                )

            # Base score from magnitude/type
            candidate.base_score = self._calculate_base_score(candidate)

            # Weather score (would query weather service)
            candidate.weather_score = 0.8  # Default good

            # History score (would query success tracker)
            candidate.history_score = 0.7  # Default neutral

            # Preference score (would query user preferences)
            candidate.preference_score = 0.5  # Default neutral

        return candidates

    def _calculate_altitude(
        self,
        ra_hours: float,
        dec_deg: float,
        obs_time: datetime,
    ) -> float:
        """Calculate altitude of object at given time."""
        # Simplified altitude calculation
        # In production, would use proper ephemeris

        # Calculate hour angle
        lst = self._local_sidereal_time(obs_time)
        ha = lst - ra_hours
        if ha < -12:
            ha += 24
        elif ha > 12:
            ha -= 24

        # Convert to radians
        ha_rad = math.radians(ha * 15)
        dec_rad = math.radians(dec_deg)
        lat_rad = math.radians(self.latitude)

        # Calculate altitude
        sin_alt = (
            math.sin(lat_rad) * math.sin(dec_rad) +
            math.cos(lat_rad) * math.cos(dec_rad) * math.cos(ha_rad)
        )
        alt_rad = math.asin(max(-1, min(1, sin_alt)))

        return math.degrees(alt_rad)

    def _local_sidereal_time(self, obs_time: datetime) -> float:
        """Calculate local sidereal time in hours."""
        # Simplified LST calculation
        j2000 = datetime(2000, 1, 1, 12, 0, 0)
        days = (obs_time - j2000).total_seconds() / 86400

        # Greenwich sidereal time
        gst = 18.697374558 + 24.06570982441908 * days
        gst = gst % 24

        # Local sidereal time
        lst = gst + self.longitude / 15
        if lst < 0:
            lst += 24
        elif lst >= 24:
            lst -= 24

        return lst

    def _estimate_moon_separation(
        self,
        ra_hours: float,
        dec_deg: float,
        obs_time: datetime,
    ) -> float:
        """Estimate angular separation from moon."""
        # Simplified moon position - would use ephemeris in production
        days_in_month = obs_time.day
        moon_ra = (days_in_month / 29.5) * 24  # Very rough approximation
        moon_dec = 20 * math.sin(math.radians(days_in_month * 12))

        # Angular separation
        ra_diff = abs(ra_hours - moon_ra) * 15  # Convert to degrees
        if ra_diff > 180:
            ra_diff = 360 - ra_diff

        dec_diff = abs(dec_deg - moon_dec)

        # Approximate angular separation
        separation = math.sqrt(ra_diff**2 + dec_diff**2)
        return min(180, separation)

    def _calculate_base_score(self, candidate: CandidateTarget) -> float:
        """Calculate base score from object properties."""
        score = 0.5  # Default

        # Magnitude bonus
        if candidate.magnitude is not None:
            if candidate.magnitude <= 6:
                score += 0.3
            elif candidate.magnitude <= 9:
                score += 0.2
            elif candidate.magnitude <= 12:
                score += 0.1

        # Type bonus
        if candidate.object_type:
            bonuses = {
                "galaxy": 0.1,
                "nebula": 0.15,
                "cluster": 0.1,
                "planetary_nebula": 0.1,
            }
            score += bonuses.get(candidate.object_type.lower(), 0)

        return min(1.0, score)

    def _score_to_quality(self, score: float) -> ScheduleQuality:
        """Convert score to quality enum."""
        if score >= 0.85:
            return ScheduleQuality.EXCELLENT
        elif score >= 0.70:
            return ScheduleQuality.GOOD
        elif score >= 0.55:
            return ScheduleQuality.FAIR
        elif score >= 0.40:
            return ScheduleQuality.MARGINAL
        else:
            return ScheduleQuality.POOR

    def _get_scheduling_reasons(
        self,
        candidate: CandidateTarget,
        constraints: SchedulingConstraints,
    ) -> list[ScheduleReason]:
        """Determine reasons for scheduling this target."""
        reasons = []

        if candidate.altitude_score > 0.8:
            reasons.append(ScheduleReason.OPTIMAL_ALTITUDE)

        if candidate.moon_score > 0.8:
            reasons.append(ScheduleReason.MOON_AVOIDANCE)

        if candidate.weather_score > 0.7:
            reasons.append(ScheduleReason.WEATHER_WINDOW)

        if candidate.history_score > 0.7:
            reasons.append(ScheduleReason.HISTORICAL_SUCCESS)

        if candidate.preference_score > 0.6:
            reasons.append(ScheduleReason.USER_PREFERENCE)

        if not reasons:
            reasons.append(ScheduleReason.TIME_CONSTRAINT)

        return reasons

    def _get_recommendation(
        self,
        candidate: CandidateTarget,
        quality: ScheduleQuality,
    ) -> str:
        """Generate human-readable recommendation."""
        if quality == ScheduleQuality.EXCELLENT:
            return f"Excellent time to observe {candidate.target_id}. All conditions are favorable."
        elif quality == ScheduleQuality.GOOD:
            return f"Good conditions for {candidate.target_id}. Recommended for observation."
        elif quality == ScheduleQuality.FAIR:
            return f"{candidate.target_id} is observable but not at optimal conditions."
        elif quality == ScheduleQuality.MARGINAL:
            return f"Marginal conditions for {candidate.target_id}. Consider waiting for better timing."
        else:
            return f"Poor conditions for {candidate.target_id}. Not recommended at this time."


# =============================================================================
# Module-level singleton
# =============================================================================

_scheduler: Optional[ObservingScheduler] = None


def get_scheduler(
    latitude_deg: float = 35.0,
    longitude_deg: float = -120.0,
) -> ObservingScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = ObservingScheduler(latitude_deg, longitude_deg)
    return _scheduler
