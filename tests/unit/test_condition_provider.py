"""
NIGHTWATCH Condition Provider Tests

Tests for the scheduling condition provider service.
"""

import pytest
from datetime import datetime

from services.scheduling.condition_provider import (
    ConditionProvider,
    ConditionQuality,
    WeatherConditions,
    MoonConditions,
    HistoryConditions,
    PreferenceConditions,
    TargetConditions,
    SimulatedWeatherProvider,
    SimulatedEphemerisProvider,
    SimulatedHistoryProvider,
    SimulatedPreferenceProvider,
    get_condition_provider,
    create_condition_provider,
    WEATHER_THRESHOLDS,
    MOON_THRESHOLDS,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def weather_provider():
    """Create a simulated weather provider."""
    return SimulatedWeatherProvider(
        cloud_cover=15.0,
        humidity=60.0,
        wind_speed=5.0,
        temperature=15.0,
        is_safe=True,
    )


@pytest.fixture
def ephemeris_provider():
    """Create a simulated ephemeris provider."""
    return SimulatedEphemerisProvider(
        moon_phase=0.3,
        moon_altitude=45.0,
        moon_ra=6.0,
        moon_dec=20.0,
    )


@pytest.fixture
def history_provider():
    """Create a simulated history provider."""
    return SimulatedHistoryProvider(
        data={
            "M31": (0.85, 10),
            "M42": (0.6, 5),
            "M45": (0.3, 3),
        }
    )


@pytest.fixture
def preference_provider():
    """Create a simulated preference provider."""
    return SimulatedPreferenceProvider(
        favorites={"M31", "NGC7000"},
        type_preferences={"galaxy": 0.9, "nebula": 0.8, "cluster": 0.6},
    )


@pytest.fixture
def full_provider(weather_provider, ephemeris_provider, history_provider, preference_provider):
    """Create provider with all services."""
    return ConditionProvider(
        weather_provider=weather_provider,
        ephemeris_provider=ephemeris_provider,
        history_provider=history_provider,
        preference_provider=preference_provider,
    )


@pytest.fixture
def empty_provider():
    """Create provider without services."""
    return ConditionProvider()


# =============================================================================
# ConditionQuality Tests
# =============================================================================


class TestConditionQuality:
    """Tests for ConditionQuality enum."""

    def test_quality_values(self):
        """All quality values defined."""
        assert ConditionQuality.EXCELLENT.value == "excellent"
        assert ConditionQuality.GOOD.value == "good"
        assert ConditionQuality.FAIR.value == "fair"
        assert ConditionQuality.POOR.value == "poor"
        assert ConditionQuality.UNSAFE.value == "unsafe"


# =============================================================================
# WeatherConditions Tests
# =============================================================================


class TestWeatherConditions:
    """Tests for WeatherConditions dataclass."""

    def test_excellent_conditions(self):
        """Low cloud cover is excellent."""
        conditions = WeatherConditions(
            cloud_cover_pct=5.0,
            humidity_pct=50.0,
            wind_speed_mph=3.0,
            is_safe=True,
        )
        assert conditions.quality == ConditionQuality.EXCELLENT

    def test_good_conditions(self):
        """Moderate cloud cover is good."""
        conditions = WeatherConditions(
            cloud_cover_pct=20.0,
            humidity_pct=60.0,
            wind_speed_mph=8.0,
            is_safe=True,
        )
        assert conditions.quality == ConditionQuality.GOOD

    def test_fair_conditions_clouds(self):
        """Higher cloud cover is fair."""
        conditions = WeatherConditions(
            cloud_cover_pct=40.0,
            is_safe=True,
        )
        assert conditions.quality == ConditionQuality.FAIR

    def test_fair_conditions_wind(self):
        """Moderate wind is fair."""
        conditions = WeatherConditions(
            cloud_cover_pct=10.0,
            wind_speed_mph=20.0,
            is_safe=True,
        )
        assert conditions.quality == ConditionQuality.FAIR

    def test_poor_conditions_clouds(self):
        """High cloud cover is poor."""
        conditions = WeatherConditions(
            cloud_cover_pct=60.0,
            is_safe=True,
        )
        assert conditions.quality == ConditionQuality.POOR

    def test_poor_conditions_humidity(self):
        """High humidity is poor."""
        conditions = WeatherConditions(
            humidity_pct=90.0,
            is_safe=True,
        )
        assert conditions.quality == ConditionQuality.POOR

    def test_poor_conditions_wind(self):
        """High wind is poor."""
        conditions = WeatherConditions(
            wind_speed_mph=30.0,
            is_safe=True,
        )
        assert conditions.quality == ConditionQuality.POOR

    def test_unsafe_override(self):
        """Unsafe flag overrides everything."""
        conditions = WeatherConditions(
            cloud_cover_pct=5.0,  # Would be excellent
            is_safe=False,
        )
        assert conditions.quality == ConditionQuality.UNSAFE


# =============================================================================
# MoonConditions Tests
# =============================================================================


class TestMoonConditions:
    """Tests for MoonConditions dataclass."""

    def test_moon_below_horizon(self):
        """Moon below horizon is excellent."""
        conditions = MoonConditions(
            phase=0.9,  # Full moon
            altitude_deg=-10.0,
            separation_deg=30.0,
            is_above_horizon=False,
        )
        assert conditions.quality == ConditionQuality.EXCELLENT

    def test_dim_moon_any_position(self):
        """Dim moon is good regardless of position."""
        conditions = MoonConditions(
            phase=0.1,  # Thin crescent
            altitude_deg=60.0,
            separation_deg=20.0,  # Close
            is_above_horizon=True,
        )
        assert conditions.quality == ConditionQuality.GOOD

    def test_excellent_separation(self):
        """Far from moon is excellent."""
        conditions = MoonConditions(
            phase=0.5,
            altitude_deg=45.0,
            separation_deg=100.0,
            is_above_horizon=True,
        )
        assert conditions.quality == ConditionQuality.EXCELLENT

    def test_good_separation(self):
        """Moderate separation is good."""
        conditions = MoonConditions(
            phase=0.5,
            altitude_deg=45.0,
            separation_deg=70.0,
            is_above_horizon=True,
        )
        assert conditions.quality == ConditionQuality.GOOD

    def test_fair_separation(self):
        """Closer separation is fair."""
        conditions = MoonConditions(
            phase=0.5,
            altitude_deg=45.0,
            separation_deg=40.0,
            is_above_horizon=True,
        )
        assert conditions.quality == ConditionQuality.FAIR

    def test_poor_separation(self):
        """Very close to bright moon is poor."""
        conditions = MoonConditions(
            phase=0.8,
            altitude_deg=60.0,
            separation_deg=15.0,
            is_above_horizon=True,
        )
        assert conditions.quality == ConditionQuality.POOR


# =============================================================================
# HistoryConditions Tests
# =============================================================================


class TestHistoryConditions:
    """Tests for HistoryConditions dataclass."""

    def test_no_history(self):
        """No history is fair (neutral)."""
        conditions = HistoryConditions(
            target_id="M31",
            observation_count=0,
        )
        assert not conditions.has_history
        assert conditions.quality == ConditionQuality.FAIR

    def test_excellent_history(self):
        """High success rate is excellent."""
        conditions = HistoryConditions(
            target_id="M31",
            success_rate=0.9,
            observation_count=10,
        )
        assert conditions.has_history
        assert conditions.quality == ConditionQuality.EXCELLENT

    def test_good_history(self):
        """Moderate success rate is good."""
        conditions = HistoryConditions(
            target_id="M42",
            success_rate=0.7,
            observation_count=5,
        )
        assert conditions.quality == ConditionQuality.GOOD

    def test_poor_history(self):
        """Low success rate is poor."""
        conditions = HistoryConditions(
            target_id="M45",
            success_rate=0.2,
            observation_count=8,
        )
        assert conditions.quality == ConditionQuality.POOR


# =============================================================================
# PreferenceConditions Tests
# =============================================================================


class TestPreferenceConditions:
    """Tests for PreferenceConditions dataclass."""

    def test_favorite_target(self):
        """Favorite target is excellent."""
        conditions = PreferenceConditions(
            target_id="M31",
            is_favorite=True,
            overall_preference=0.5,
        )
        assert conditions.quality == ConditionQuality.EXCELLENT

    def test_high_preference(self):
        """High preference score is excellent."""
        conditions = PreferenceConditions(
            target_id="M42",
            is_favorite=False,
            overall_preference=0.9,
        )
        assert conditions.quality == ConditionQuality.EXCELLENT

    def test_neutral_preference(self):
        """Middle preference is fair."""
        conditions = PreferenceConditions(
            target_id="NGC1234",
            is_favorite=False,
            overall_preference=0.5,
        )
        assert conditions.quality == ConditionQuality.FAIR

    def test_low_preference(self):
        """Low preference is poor."""
        conditions = PreferenceConditions(
            target_id="NGC9999",
            is_favorite=False,
            overall_preference=0.2,
        )
        assert conditions.quality == ConditionQuality.POOR


# =============================================================================
# TargetConditions Tests
# =============================================================================


class TestTargetConditions:
    """Tests for TargetConditions dataclass."""

    def test_weather_score(self):
        """Weather score calculated correctly."""
        weather = WeatherConditions(cloud_cover_pct=5.0, is_safe=True)
        conditions = TargetConditions(target_id="M31", weather=weather)

        assert conditions.get_weather_score() == 1.0  # Excellent

    def test_moon_score_with_data(self):
        """Moon score calculated with data."""
        weather = WeatherConditions(is_safe=True)
        moon = MoonConditions(
            phase=0.5,
            altitude_deg=45.0,
            separation_deg=100.0,
            is_above_horizon=True,
        )
        conditions = TargetConditions(target_id="M31", weather=weather, moon=moon)

        assert conditions.get_moon_score() == 1.0  # Excellent

    def test_moon_score_default(self):
        """Moon score defaults to neutral."""
        weather = WeatherConditions(is_safe=True)
        conditions = TargetConditions(target_id="M31", weather=weather)

        assert conditions.get_moon_score() == 0.7  # Neutral default

    def test_history_score_with_data(self):
        """History score calculated with data."""
        weather = WeatherConditions(is_safe=True)
        history = HistoryConditions(target_id="M31", success_rate=0.9, observation_count=10)
        conditions = TargetConditions(target_id="M31", weather=weather, history=history)

        assert conditions.get_history_score() == 1.0  # Excellent

    def test_history_score_default(self):
        """History score defaults to neutral."""
        weather = WeatherConditions(is_safe=True)
        conditions = TargetConditions(target_id="M31", weather=weather)

        assert conditions.get_history_score() == 0.5  # Neutral default

    def test_preference_score_favorite(self):
        """Preference score for favorite."""
        weather = WeatherConditions(is_safe=True)
        preference = PreferenceConditions(target_id="M31", is_favorite=True)
        conditions = TargetConditions(target_id="M31", weather=weather, preference=preference)

        assert conditions.get_preference_score() == 1.0  # Excellent


# =============================================================================
# Simulated Provider Tests
# =============================================================================


class TestSimulatedWeatherProvider:
    """Tests for SimulatedWeatherProvider."""

    def test_returns_configured_values(self, weather_provider):
        """Returns configured values."""
        assert weather_provider.get_cloud_cover() == 15.0
        assert weather_provider.get_humidity() == 60.0
        assert weather_provider.get_wind_speed() == 5.0
        assert weather_provider.get_temperature() == 15.0
        assert weather_provider.is_safe() is True


class TestSimulatedEphemerisProvider:
    """Tests for SimulatedEphemerisProvider."""

    def test_returns_moon_data(self, ephemeris_provider):
        """Returns configured moon data."""
        assert ephemeris_provider.get_moon_phase() == 0.3
        assert ephemeris_provider.get_moon_altitude() == 45.0

    def test_calculates_separation(self, ephemeris_provider):
        """Calculates angular separation."""
        # Target at same position as moon
        sep = ephemeris_provider.get_moon_separation(6.0, 20.0)
        assert sep == 0.0

        # Target 90 degrees away in RA
        sep = ephemeris_provider.get_moon_separation(12.0, 20.0)
        assert sep == 90.0


class TestSimulatedHistoryProvider:
    """Tests for SimulatedHistoryProvider."""

    def test_returns_configured_data(self, history_provider):
        """Returns data for known targets."""
        assert history_provider.get_success_rate("M31") == 0.85
        assert history_provider.get_observation_count("M31") == 10

    def test_unknown_target(self, history_provider):
        """Returns None for unknown targets."""
        assert history_provider.get_success_rate("NGC9999") is None
        assert history_provider.get_observation_count("NGC9999") == 0


class TestSimulatedPreferenceProvider:
    """Tests for SimulatedPreferenceProvider."""

    def test_favorite_detection(self, preference_provider):
        """Detects favorites correctly."""
        assert preference_provider.is_favorite("M31") is True
        assert preference_provider.is_favorite("M42") is False

    def test_type_preferences(self, preference_provider):
        """Returns type preferences."""
        assert preference_provider.get_preference_score("any", "galaxy") == 0.9
        assert preference_provider.get_preference_score("any", "unknown") == 0.5

    def test_favorite_score(self, preference_provider):
        """Favorites get perfect score."""
        assert preference_provider.get_preference_score("M31", "galaxy") == 1.0


# =============================================================================
# ConditionProvider Tests
# =============================================================================


class TestConditionProvider:
    """Tests for ConditionProvider."""

    def test_weather_from_provider(self, full_provider):
        """Gets weather from provider."""
        weather = full_provider.get_weather_conditions()

        assert weather.cloud_cover_pct == 15.0
        assert weather.humidity_pct == 60.0
        assert weather.is_safe is True

    def test_weather_default(self, empty_provider):
        """Uses defaults without provider."""
        weather = empty_provider.get_weather_conditions()

        assert weather.cloud_cover_pct == 20.0
        assert weather.is_safe is True

    def test_weather_caching(self, full_provider):
        """Weather is cached."""
        w1 = full_provider.get_weather_conditions()
        w2 = full_provider.get_weather_conditions()

        assert w1 is w2  # Same object

    def test_cache_clear(self, full_provider):
        """Cache can be cleared."""
        w1 = full_provider.get_weather_conditions()
        full_provider.clear_cache()
        w2 = full_provider.get_weather_conditions()

        assert w1 is not w2  # Different objects

    def test_moon_from_provider(self, full_provider):
        """Gets moon conditions from provider."""
        moon = full_provider.get_moon_conditions(12.0, 30.0)

        assert moon is not None
        assert moon.phase == 0.3
        assert moon.altitude_deg == 45.0
        assert moon.separation_deg > 0

    def test_moon_without_provider(self, empty_provider):
        """Returns None without provider."""
        moon = empty_provider.get_moon_conditions(12.0, 30.0)
        assert moon is None

    def test_history_from_provider(self, full_provider):
        """Gets history from provider."""
        history = full_provider.get_history_conditions("M31")

        assert history is not None
        assert history.success_rate == 0.85
        assert history.observation_count == 10

    def test_history_without_provider(self, empty_provider):
        """Returns None without provider."""
        history = empty_provider.get_history_conditions("M31")
        assert history is None

    def test_preference_from_provider(self, full_provider):
        """Gets preferences from provider."""
        pref = full_provider.get_preference_conditions("M31", "galaxy")

        assert pref is not None
        assert pref.is_favorite is True

    def test_preference_without_provider(self, empty_provider):
        """Returns None without provider."""
        pref = empty_provider.get_preference_conditions("M31")
        assert pref is None

    def test_target_conditions(self, full_provider):
        """Gets all conditions for target."""
        conditions = full_provider.get_target_conditions(
            "M31", 0.712, 41.269, "galaxy"
        )

        assert conditions.target_id == "M31"
        assert conditions.weather is not None
        assert conditions.moon is not None
        assert conditions.history is not None
        assert conditions.preference is not None

    def test_get_scores(self, full_provider):
        """Gets all scores as dictionary."""
        scores = full_provider.get_scores("M31", 0.712, 41.269, "galaxy")

        assert "weather_score" in scores
        assert "moon_score" in scores
        assert "history_score" in scores
        assert "preference_score" in scores

        # All should be valid scores
        for score in scores.values():
            assert 0.0 <= score <= 1.0


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunctions:
    """Tests for module-level factories."""

    def test_get_condition_provider(self):
        """get_condition_provider returns instance."""
        provider = get_condition_provider()
        assert isinstance(provider, ConditionProvider)

    def test_get_condition_provider_singleton(self):
        """get_condition_provider returns same instance."""
        p1 = get_condition_provider()
        p2 = get_condition_provider()
        assert p1 is p2

    def test_create_condition_provider(self, weather_provider):
        """create_condition_provider creates new instance."""
        provider = create_condition_provider(weather_provider=weather_provider)
        assert isinstance(provider, ConditionProvider)

        weather = provider.get_weather_conditions()
        assert weather.cloud_cover_pct == 15.0


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests."""

    def test_score_calculation_flow(self, full_provider):
        """Test full scoring flow for a target."""
        # M31 is a favorite with good history
        scores = full_provider.get_scores("M31", 0.712, 41.269, "galaxy")

        # Should have high preference score (favorite)
        assert scores["preference_score"] == 1.0

        # Should have high history score (0.85 success rate)
        assert scores["history_score"] == 1.0

        # Weather should be good (15% clouds)
        assert scores["weather_score"] >= 0.8

    def test_poor_target_scores(self, full_provider):
        """Test scores for a target with poor history."""
        # M45 has low success rate (0.3)
        scores = full_provider.get_scores("M45", 3.791, 24.117, "cluster")

        # Should have poor history score
        assert scores["history_score"] == 0.3

        # Not a favorite
        assert scores["preference_score"] < 1.0

    def test_unknown_target_defaults(self, full_provider):
        """Test scores for unknown target."""
        # Use unknown type to avoid type preferences
        scores = full_provider.get_scores("NGC9999", 12.0, 45.0, "unknown_type")

        # History should be neutral (no data)
        assert scores["history_score"] == 0.5

        # Preference should be neutral (not favorite, no type preference)
        assert scores["preference_score"] == 0.5  # Neutral default
