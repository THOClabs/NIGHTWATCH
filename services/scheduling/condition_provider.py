"""
NIGHTWATCH Scheduling Condition Provider

Connects the ObservingScheduler to real v0.5 services for live condition data.

This module bridges:
- WeatherService: Real-time weather and cloud conditions
- EphemerisService: Moon position and phase calculations
- SuccessTracker: Historical observation success rates
- UserPreferences: Observer preferences and favorites

The provider can be injected into the scheduler to replace placeholder
scores with actual data from the integrated v0.5 components.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Protocol
from enum import Enum


# =============================================================================
# Protocols for Service Interfaces
# =============================================================================


class WeatherProvider(Protocol):
    """Protocol for weather data providers."""

    def get_cloud_cover(self) -> Optional[float]:
        """Get cloud cover percentage (0-100)."""
        ...

    def get_humidity(self) -> Optional[float]:
        """Get humidity percentage (0-100)."""
        ...

    def get_wind_speed(self) -> Optional[float]:
        """Get wind speed in mph."""
        ...

    def get_temperature(self) -> Optional[float]:
        """Get temperature in Celsius."""
        ...

    def is_safe(self) -> bool:
        """Check if conditions are safe for observing."""
        ...


class EphemerisProvider(Protocol):
    """Protocol for ephemeris data providers."""

    def get_moon_phase(self) -> float:
        """Get moon phase (0.0 new to 1.0 full)."""
        ...

    def get_moon_altitude(self) -> float:
        """Get moon altitude in degrees."""
        ...

    def get_moon_separation(self, ra_hours: float, dec_deg: float) -> float:
        """Get angular separation from moon in degrees."""
        ...


class HistoryProvider(Protocol):
    """Protocol for observation history providers."""

    def get_success_rate(self, target_id: str) -> Optional[float]:
        """Get historical success rate for target (0.0-1.0)."""
        ...

    def get_observation_count(self, target_id: str) -> int:
        """Get number of previous observations."""
        ...


class PreferenceProvider(Protocol):
    """Protocol for user preference providers."""

    def is_favorite(self, target_id: str) -> bool:
        """Check if target is in favorites."""
        ...

    def get_preference_score(self, target_id: str, object_type: Optional[str]) -> float:
        """Get preference score for target/type (0.0-1.0)."""
        ...


# =============================================================================
# Enums and Constants
# =============================================================================


class ConditionQuality(Enum):
    """Quality assessment of observing conditions."""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNSAFE = "unsafe"


# Score thresholds
WEATHER_THRESHOLDS = {
    "cloud_excellent": 10.0,    # % cloud cover for excellent
    "cloud_good": 25.0,
    "cloud_fair": 50.0,
    "humidity_poor": 85.0,      # % humidity threshold
    "wind_marginal": 15.0,      # mph wind threshold
    "wind_poor": 25.0,
}

MOON_THRESHOLDS = {
    "separation_excellent": 90.0,  # degrees for excellent
    "separation_good": 60.0,
    "separation_fair": 30.0,
    "phase_dim": 0.25,            # phase fraction for dim moon
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class WeatherConditions:
    """Current weather conditions for scoring."""

    cloud_cover_pct: Optional[float] = None
    humidity_pct: Optional[float] = None
    wind_speed_mph: Optional[float] = None
    temperature_c: Optional[float] = None
    is_safe: bool = True
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def quality(self) -> ConditionQuality:
        """Assess overall weather quality."""
        if not self.is_safe:
            return ConditionQuality.UNSAFE

        if self.cloud_cover_pct is not None:
            if self.cloud_cover_pct > WEATHER_THRESHOLDS["cloud_fair"]:
                return ConditionQuality.POOR
            if self.cloud_cover_pct > WEATHER_THRESHOLDS["cloud_good"]:
                return ConditionQuality.FAIR

        if self.humidity_pct is not None:
            if self.humidity_pct > WEATHER_THRESHOLDS["humidity_poor"]:
                return ConditionQuality.POOR

        if self.wind_speed_mph is not None:
            if self.wind_speed_mph > WEATHER_THRESHOLDS["wind_poor"]:
                return ConditionQuality.POOR
            if self.wind_speed_mph > WEATHER_THRESHOLDS["wind_marginal"]:
                return ConditionQuality.FAIR

        # Check for excellent conditions
        if (self.cloud_cover_pct is not None and
            self.cloud_cover_pct <= WEATHER_THRESHOLDS["cloud_excellent"]):
            return ConditionQuality.EXCELLENT

        return ConditionQuality.GOOD


@dataclass
class MoonConditions:
    """Moon conditions for a specific target."""

    phase: float  # 0.0-1.0
    altitude_deg: float
    separation_deg: float
    is_above_horizon: bool

    @property
    def quality(self) -> ConditionQuality:
        """Assess moon impact quality."""
        # Moon below horizon is excellent
        if not self.is_above_horizon:
            return ConditionQuality.EXCELLENT

        # Dim moon is good regardless of position
        if self.phase < MOON_THRESHOLDS["phase_dim"]:
            return ConditionQuality.GOOD

        # Check separation
        if self.separation_deg >= MOON_THRESHOLDS["separation_excellent"]:
            return ConditionQuality.EXCELLENT
        elif self.separation_deg >= MOON_THRESHOLDS["separation_good"]:
            return ConditionQuality.GOOD
        elif self.separation_deg >= MOON_THRESHOLDS["separation_fair"]:
            return ConditionQuality.FAIR
        else:
            return ConditionQuality.POOR


@dataclass
class HistoryConditions:
    """Historical observation data for a target."""

    target_id: str
    success_rate: Optional[float] = None
    observation_count: int = 0
    last_observed: Optional[datetime] = None

    @property
    def has_history(self) -> bool:
        """Check if target has observation history."""
        return self.observation_count > 0

    @property
    def quality(self) -> ConditionQuality:
        """Assess based on historical success."""
        if not self.has_history:
            return ConditionQuality.FAIR  # Neutral for unknowns

        if self.success_rate is None:
            return ConditionQuality.FAIR

        if self.success_rate >= 0.8:
            return ConditionQuality.EXCELLENT
        elif self.success_rate >= 0.6:
            return ConditionQuality.GOOD
        elif self.success_rate >= 0.4:
            return ConditionQuality.FAIR
        else:
            return ConditionQuality.POOR


@dataclass
class PreferenceConditions:
    """User preference data for a target."""

    target_id: str
    is_favorite: bool = False
    type_preference: float = 0.5  # 0.0-1.0
    overall_preference: float = 0.5

    @property
    def quality(self) -> ConditionQuality:
        """Assess based on user preferences."""
        if self.is_favorite:
            return ConditionQuality.EXCELLENT

        if self.overall_preference >= 0.8:
            return ConditionQuality.EXCELLENT
        elif self.overall_preference >= 0.6:
            return ConditionQuality.GOOD
        elif self.overall_preference >= 0.4:
            return ConditionQuality.FAIR
        else:
            return ConditionQuality.POOR


@dataclass
class TargetConditions:
    """Combined conditions for a scheduling candidate."""

    target_id: str
    weather: WeatherConditions
    moon: Optional[MoonConditions] = None
    history: Optional[HistoryConditions] = None
    preference: Optional[PreferenceConditions] = None

    def get_weather_score(self) -> float:
        """Calculate weather score (0.0-1.0)."""
        quality_scores = {
            ConditionQuality.EXCELLENT: 1.0,
            ConditionQuality.GOOD: 0.8,
            ConditionQuality.FAIR: 0.6,
            ConditionQuality.POOR: 0.3,
            ConditionQuality.UNSAFE: 0.0,
        }
        return quality_scores[self.weather.quality]

    def get_moon_score(self) -> float:
        """Calculate moon avoidance score (0.0-1.0)."""
        if self.moon is None:
            return 0.7  # Neutral default

        quality_scores = {
            ConditionQuality.EXCELLENT: 1.0,
            ConditionQuality.GOOD: 0.8,
            ConditionQuality.FAIR: 0.5,
            ConditionQuality.POOR: 0.2,
            ConditionQuality.UNSAFE: 0.0,
        }
        return quality_scores[self.moon.quality]

    def get_history_score(self) -> float:
        """Calculate history-based score (0.0-1.0)."""
        if self.history is None:
            return 0.5  # Neutral default

        quality_scores = {
            ConditionQuality.EXCELLENT: 1.0,
            ConditionQuality.GOOD: 0.8,
            ConditionQuality.FAIR: 0.5,
            ConditionQuality.POOR: 0.3,
            ConditionQuality.UNSAFE: 0.1,
        }
        return quality_scores[self.history.quality]

    def get_preference_score(self) -> float:
        """Calculate preference-based score (0.0-1.0)."""
        if self.preference is None:
            return 0.5  # Neutral default

        quality_scores = {
            ConditionQuality.EXCELLENT: 1.0,
            ConditionQuality.GOOD: 0.75,
            ConditionQuality.FAIR: 0.5,
            ConditionQuality.POOR: 0.25,
            ConditionQuality.UNSAFE: 0.1,
        }
        return quality_scores[self.preference.quality]


# =============================================================================
# Condition Provider
# =============================================================================


class ConditionProvider:
    """
    Provides real condition data for scheduling decisions.

    Connects to v0.5 services to gather weather, moon, history,
    and preference data for target scoring.
    """

    def __init__(
        self,
        weather_provider: Optional[WeatherProvider] = None,
        ephemeris_provider: Optional[EphemerisProvider] = None,
        history_provider: Optional[HistoryProvider] = None,
        preference_provider: Optional[PreferenceProvider] = None,
    ):
        """
        Initialize provider with optional service connections.

        Args:
            weather_provider: Weather data source
            ephemeris_provider: Ephemeris calculations source
            history_provider: Historical observation data source
            preference_provider: User preference data source
        """
        self._weather = weather_provider
        self._ephemeris = ephemeris_provider
        self._history = history_provider
        self._preference = preference_provider

        # Cache for current weather (shared across targets)
        self._weather_cache: Optional[WeatherConditions] = None
        self._weather_cache_time: Optional[datetime] = None
        self._cache_ttl_seconds = 60.0

    def get_weather_conditions(self) -> WeatherConditions:
        """
        Get current weather conditions.

        Returns cached data if recent, otherwise queries provider.
        """
        now = datetime.now()

        # Check cache
        if (self._weather_cache is not None and
            self._weather_cache_time is not None):
            age = (now - self._weather_cache_time).total_seconds()
            if age < self._cache_ttl_seconds:
                return self._weather_cache

        # Query provider or use defaults
        if self._weather is not None:
            conditions = WeatherConditions(
                cloud_cover_pct=self._weather.get_cloud_cover(),
                humidity_pct=self._weather.get_humidity(),
                wind_speed_mph=self._weather.get_wind_speed(),
                temperature_c=self._weather.get_temperature(),
                is_safe=self._weather.is_safe(),
                timestamp=now,
            )
        else:
            # Default good conditions when no provider
            conditions = WeatherConditions(
                cloud_cover_pct=20.0,
                is_safe=True,
                timestamp=now,
            )

        self._weather_cache = conditions
        self._weather_cache_time = now
        return conditions

    def get_moon_conditions(
        self,
        ra_hours: float,
        dec_degrees: float,
    ) -> Optional[MoonConditions]:
        """
        Get moon conditions for a target position.

        Args:
            ra_hours: Target right ascension in hours
            dec_degrees: Target declination in degrees

        Returns:
            MoonConditions or None if no ephemeris available
        """
        if self._ephemeris is None:
            return None

        phase = self._ephemeris.get_moon_phase()
        altitude = self._ephemeris.get_moon_altitude()
        separation = self._ephemeris.get_moon_separation(ra_hours, dec_degrees)

        return MoonConditions(
            phase=phase,
            altitude_deg=altitude,
            separation_deg=separation,
            is_above_horizon=altitude > 0,
        )

    def get_history_conditions(
        self,
        target_id: str,
    ) -> Optional[HistoryConditions]:
        """
        Get historical observation data for a target.

        Args:
            target_id: Target identifier

        Returns:
            HistoryConditions or None if no history available
        """
        if self._history is None:
            return None

        success_rate = self._history.get_success_rate(target_id)
        obs_count = self._history.get_observation_count(target_id)

        return HistoryConditions(
            target_id=target_id,
            success_rate=success_rate,
            observation_count=obs_count,
        )

    def get_preference_conditions(
        self,
        target_id: str,
        object_type: Optional[str] = None,
    ) -> Optional[PreferenceConditions]:
        """
        Get user preference data for a target.

        Args:
            target_id: Target identifier
            object_type: Optional object type for type-based preferences

        Returns:
            PreferenceConditions or None if no preferences available
        """
        if self._preference is None:
            return None

        is_fav = self._preference.is_favorite(target_id)
        pref_score = self._preference.get_preference_score(target_id, object_type)

        return PreferenceConditions(
            target_id=target_id,
            is_favorite=is_fav,
            overall_preference=pref_score,
        )

    def get_target_conditions(
        self,
        target_id: str,
        ra_hours: float,
        dec_degrees: float,
        object_type: Optional[str] = None,
    ) -> TargetConditions:
        """
        Get all conditions for a scheduling candidate.

        Args:
            target_id: Target identifier
            ra_hours: Target right ascension
            dec_degrees: Target declination
            object_type: Optional object type

        Returns:
            TargetConditions with all available data
        """
        weather = self.get_weather_conditions()
        moon = self.get_moon_conditions(ra_hours, dec_degrees)
        history = self.get_history_conditions(target_id)
        preference = self.get_preference_conditions(target_id, object_type)

        return TargetConditions(
            target_id=target_id,
            weather=weather,
            moon=moon,
            history=history,
            preference=preference,
        )

    def get_scores(
        self,
        target_id: str,
        ra_hours: float,
        dec_degrees: float,
        object_type: Optional[str] = None,
    ) -> dict[str, float]:
        """
        Get all scores for a scheduling candidate.

        Convenience method that returns scores ready for injection
        into the scheduler.

        Args:
            target_id: Target identifier
            ra_hours: Target right ascension
            dec_degrees: Target declination
            object_type: Optional object type

        Returns:
            Dictionary with weather_score, moon_score, history_score,
            preference_score keys
        """
        conditions = self.get_target_conditions(
            target_id, ra_hours, dec_degrees, object_type
        )

        return {
            "weather_score": conditions.get_weather_score(),
            "moon_score": conditions.get_moon_score(),
            "history_score": conditions.get_history_score(),
            "preference_score": conditions.get_preference_score(),
        }

    def clear_cache(self) -> None:
        """Clear weather cache to force refresh."""
        self._weather_cache = None
        self._weather_cache_time = None


# =============================================================================
# Simulated Providers for Testing
# =============================================================================


class SimulatedWeatherProvider:
    """Simulated weather provider for testing."""

    def __init__(
        self,
        cloud_cover: float = 15.0,
        humidity: float = 60.0,
        wind_speed: float = 5.0,
        temperature: float = 15.0,
        is_safe: bool = True,
    ):
        self._cloud_cover = cloud_cover
        self._humidity = humidity
        self._wind_speed = wind_speed
        self._temperature = temperature
        self._is_safe = is_safe

    def get_cloud_cover(self) -> Optional[float]:
        return self._cloud_cover

    def get_humidity(self) -> Optional[float]:
        return self._humidity

    def get_wind_speed(self) -> Optional[float]:
        return self._wind_speed

    def get_temperature(self) -> Optional[float]:
        return self._temperature

    def is_safe(self) -> bool:
        return self._is_safe


class SimulatedEphemerisProvider:
    """Simulated ephemeris provider for testing."""

    def __init__(
        self,
        moon_phase: float = 0.3,
        moon_altitude: float = 45.0,
        moon_ra: float = 6.0,
        moon_dec: float = 20.0,
    ):
        self._phase = moon_phase
        self._altitude = moon_altitude
        self._moon_ra = moon_ra
        self._moon_dec = moon_dec

    def get_moon_phase(self) -> float:
        return self._phase

    def get_moon_altitude(self) -> float:
        return self._altitude

    def get_moon_separation(self, ra_hours: float, dec_deg: float) -> float:
        """Simple angular separation calculation."""
        import math
        ra_diff = abs(ra_hours - self._moon_ra) * 15  # to degrees
        if ra_diff > 180:
            ra_diff = 360 - ra_diff
        dec_diff = abs(dec_deg - self._moon_dec)
        return math.sqrt(ra_diff**2 + dec_diff**2)


class SimulatedHistoryProvider:
    """Simulated history provider for testing."""

    def __init__(self, data: Optional[dict[str, tuple[float, int]]] = None):
        """
        Args:
            data: Dict mapping target_id to (success_rate, count)
        """
        self._data = data or {}

    def get_success_rate(self, target_id: str) -> Optional[float]:
        if target_id in self._data:
            return self._data[target_id][0]
        return None

    def get_observation_count(self, target_id: str) -> int:
        if target_id in self._data:
            return self._data[target_id][1]
        return 0


class SimulatedPreferenceProvider:
    """Simulated preference provider for testing."""

    def __init__(
        self,
        favorites: Optional[set[str]] = None,
        type_preferences: Optional[dict[str, float]] = None,
    ):
        self._favorites = favorites or set()
        self._type_prefs = type_preferences or {}

    def is_favorite(self, target_id: str) -> bool:
        return target_id in self._favorites

    def get_preference_score(
        self,
        target_id: str,
        object_type: Optional[str],
    ) -> float:
        if target_id in self._favorites:
            return 1.0
        if object_type and object_type in self._type_prefs:
            return self._type_prefs[object_type]
        return 0.5


# =============================================================================
# Module-level factory
# =============================================================================

_provider: Optional[ConditionProvider] = None


def get_condition_provider() -> ConditionProvider:
    """Get the global condition provider instance."""
    global _provider
    if _provider is None:
        _provider = ConditionProvider()
    return _provider


def create_condition_provider(
    weather_provider: Optional[WeatherProvider] = None,
    ephemeris_provider: Optional[EphemerisProvider] = None,
    history_provider: Optional[HistoryProvider] = None,
    preference_provider: Optional[PreferenceProvider] = None,
) -> ConditionProvider:
    """Create a new condition provider with specified services."""
    return ConditionProvider(
        weather_provider=weather_provider,
        ephemeris_provider=ephemeris_provider,
        history_provider=history_provider,
        preference_provider=preference_provider,
    )
