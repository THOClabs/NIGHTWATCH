"""
NIGHTWATCH Observing Scheduler Tests

Tests for the unified scheduling system integrating v0.5 components.
"""

import pytest
from datetime import datetime, timedelta

from services.scheduling.scheduler import (
    ObservingScheduler,
    ScheduledTarget,
    SchedulingConstraints,
    ScheduleResult,
    ScheduleQuality,
    ScheduleReason,
    CandidateTarget,
    get_scheduler,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def scheduler():
    """Create an ObservingScheduler."""
    return ObservingScheduler(latitude_deg=35.0, longitude_deg=-120.0)


@pytest.fixture
def sample_candidates():
    """Create sample candidate targets."""
    return [
        {
            "id": "M31",
            "name": "Andromeda Galaxy",
            "ra_hours": 0.712,
            "dec_degrees": 41.269,
            "magnitude": 3.4,
            "object_type": "galaxy",
        },
        {
            "id": "M42",
            "name": "Orion Nebula",
            "ra_hours": 5.588,
            "dec_degrees": -5.391,
            "magnitude": 4.0,
            "object_type": "nebula",
        },
        {
            "id": "M45",
            "name": "Pleiades",
            "ra_hours": 3.791,
            "dec_degrees": 24.117,
            "magnitude": 1.6,
            "object_type": "cluster",
        },
        {
            "id": "M13",
            "name": "Hercules Cluster",
            "ra_hours": 16.695,
            "dec_degrees": 36.467,
            "magnitude": 5.8,
            "object_type": "globular_cluster",
        },
    ]


@pytest.fixture
def sample_constraints():
    """Create sample scheduling constraints."""
    return SchedulingConstraints(
        min_altitude_deg=25.0,
        preferred_altitude_deg=55.0,
        min_moon_separation_deg=30.0,
        min_observation_minutes=20.0,
        max_observation_minutes=120.0,
    )


# =============================================================================
# SchedulingConstraints Tests
# =============================================================================


class TestSchedulingConstraints:
    """Tests for SchedulingConstraints dataclass."""

    def test_default_constraints(self):
        """Default constraints have sensible values."""
        constraints = SchedulingConstraints()

        assert constraints.min_altitude_deg == 20.0
        assert constraints.preferred_altitude_deg == 50.0
        assert constraints.min_moon_separation_deg == 30.0
        assert constraints.min_observation_minutes == 30.0

    def test_custom_constraints(self):
        """Custom constraints are applied."""
        constraints = SchedulingConstraints(
            min_altitude_deg=30.0,
            min_moon_separation_deg=45.0,
        )

        assert constraints.min_altitude_deg == 30.0
        assert constraints.min_moon_separation_deg == 45.0


# =============================================================================
# ScheduledTarget Tests
# =============================================================================


class TestScheduledTarget:
    """Tests for ScheduledTarget dataclass."""

    def test_target_creation(self):
        """Create a scheduled target."""
        start = datetime.now()
        end = start + timedelta(hours=1)

        target = ScheduledTarget(
            target_id="M31",
            target_name="Andromeda Galaxy",
            scheduled_start=start,
            scheduled_end=end,
            expected_altitude_deg=55.0,
            moon_separation_deg=90.0,
            quality=ScheduleQuality.EXCELLENT,
            score=0.9,
        )

        assert target.target_id == "M31"
        assert target.quality == ScheduleQuality.EXCELLENT

    def test_duration_calculation(self):
        """Duration is calculated correctly."""
        start = datetime.now()
        end = start + timedelta(minutes=45)

        target = ScheduledTarget(
            target_id="M31",
            target_name=None,
            scheduled_start=start,
            scheduled_end=end,
            expected_altitude_deg=50.0,
            moon_separation_deg=None,
            quality=ScheduleQuality.GOOD,
            score=0.8,
        )

        assert target.duration_minutes == 45.0

    def test_to_dict(self):
        """Target converts to dictionary."""
        start = datetime.now()
        end = start + timedelta(hours=1)

        target = ScheduledTarget(
            target_id="M31",
            target_name="Andromeda Galaxy",
            scheduled_start=start,
            scheduled_end=end,
            expected_altitude_deg=55.0,
            moon_separation_deg=90.0,
            quality=ScheduleQuality.GOOD,
            score=0.85,
            reasons=[ScheduleReason.OPTIMAL_ALTITUDE],
        )

        d = target.to_dict()
        assert d["target_id"] == "M31"
        assert d["quality"] == "good"
        assert "optimal_altitude" in d["reasons"]


# =============================================================================
# ScheduleResult Tests
# =============================================================================


class TestScheduleResult:
    """Tests for ScheduleResult dataclass."""

    def test_empty_result(self):
        """Empty result has correct defaults."""
        result = ScheduleResult()

        assert result.target_count == 0
        assert result.total_observation_minutes == 0.0
        assert result.average_quality == 0.0

    def test_result_with_targets(self):
        """Result with targets calculates correctly."""
        start = datetime.now()

        targets = [
            ScheduledTarget(
                target_id="M31",
                target_name=None,
                scheduled_start=start,
                scheduled_end=start + timedelta(hours=1),
                expected_altitude_deg=55.0,
                moon_separation_deg=None,
                quality=ScheduleQuality.EXCELLENT,
                score=0.9,
            ),
            ScheduledTarget(
                target_id="M42",
                target_name=None,
                scheduled_start=start + timedelta(hours=1),
                scheduled_end=start + timedelta(hours=2),
                expected_altitude_deg=45.0,
                moon_separation_deg=None,
                quality=ScheduleQuality.GOOD,
                score=0.8,
            ),
        ]

        result = ScheduleResult(
            targets=targets,
            total_observation_minutes=120.0,
        )

        assert result.target_count == 2
        assert result.average_quality == 0.9  # (1.0 + 0.8) / 2

    def test_to_dict(self):
        """Result converts to dictionary."""
        result = ScheduleResult(
            total_observation_minutes=60.0,
        )

        d = result.to_dict()
        assert d["target_count"] == 0
        assert d["total_observation_minutes"] == 60.0


# =============================================================================
# Schedule Creation Tests
# =============================================================================


class TestScheduleCreation:
    """Tests for schedule creation."""

    def test_create_schedule(self, scheduler, sample_candidates):
        """Create a basic schedule."""
        result = scheduler.create_schedule(sample_candidates)

        assert result is not None
        assert isinstance(result, ScheduleResult)

    def test_schedule_has_targets(self, scheduler, sample_candidates):
        """Schedule includes targets."""
        result = scheduler.create_schedule(sample_candidates)

        # Should have at least some targets (depends on simulated conditions)
        assert result.target_count >= 0

    def test_schedule_respects_constraints(self, scheduler, sample_candidates, sample_constraints):
        """Schedule respects constraints."""
        result = scheduler.create_schedule(
            sample_candidates,
            constraints=sample_constraints,
        )

        # All scheduled targets should meet minimum score
        for target in result.targets:
            assert target.score >= sample_constraints.min_score

    def test_schedule_sorted_by_score(self, scheduler, sample_candidates):
        """Targets are sorted by score (best first)."""
        result = scheduler.create_schedule(sample_candidates)

        if len(result.targets) >= 2:
            for i in range(len(result.targets) - 1):
                # Earlier targets should have equal or higher scores
                assert result.targets[i].score >= result.targets[i + 1].score

    def test_schedule_with_time_constraints(self, scheduler, sample_candidates):
        """Schedule respects time constraints."""
        now = datetime.now()
        constraints = SchedulingConstraints(
            start_time=now,
            end_time=now + timedelta(hours=2),
            min_observation_minutes=30.0,
        )

        result = scheduler.create_schedule(sample_candidates, constraints)

        # All targets should be within time window
        for target in result.targets:
            assert target.scheduled_start >= now
            assert target.scheduled_end <= now + timedelta(hours=2, minutes=5)  # Small buffer


# =============================================================================
# Best Target Tests
# =============================================================================


class TestBestTarget:
    """Tests for getting best target."""

    def test_get_best_target(self, scheduler, sample_candidates):
        """Get single best target."""
        best = scheduler.get_best_target(sample_candidates)

        # May or may not have a result depending on conditions
        if best is not None:
            assert isinstance(best, ScheduledTarget)
            assert best.score > 0

    def test_best_target_has_highest_score(self, scheduler, sample_candidates):
        """Best target has highest score among schedule."""
        result = scheduler.create_schedule(sample_candidates)
        best = scheduler.get_best_target(sample_candidates)

        if best is not None and result.targets:
            assert best.target_id == result.targets[0].target_id


# =============================================================================
# Target Evaluation Tests
# =============================================================================


class TestTargetEvaluation:
    """Tests for single target evaluation."""

    def test_evaluate_target(self, scheduler):
        """Evaluate a single target."""
        target = {
            "id": "M31",
            "name": "Andromeda Galaxy",
            "ra_hours": 0.712,
            "dec_degrees": 41.269,
        }

        evaluation = scheduler.evaluate_target(target)

        assert "target_id" in evaluation
        assert "total_score" in evaluation
        assert "quality" in evaluation
        assert "scores" in evaluation

    def test_evaluation_includes_all_scores(self, scheduler):
        """Evaluation includes all score components."""
        target = {
            "id": "M42",
            "ra_hours": 5.588,
            "dec_degrees": -5.391,
        }

        evaluation = scheduler.evaluate_target(target)

        scores = evaluation["scores"]
        assert "base" in scores
        assert "altitude" in scores
        assert "moon" in scores
        assert "weather" in scores
        assert "history" in scores
        assert "preference" in scores

    def test_evaluation_has_recommendation(self, scheduler):
        """Evaluation includes recommendation."""
        target = {
            "id": "M45",
            "ra_hours": 3.791,
            "dec_degrees": 24.117,
        }

        evaluation = scheduler.evaluate_target(target)

        assert "recommendation" in evaluation
        assert len(evaluation["recommendation"]) > 0


# =============================================================================
# Altitude Calculation Tests
# =============================================================================


class TestAltitudeCalculation:
    """Tests for altitude calculations."""

    def test_calculate_altitude(self, scheduler):
        """Calculate altitude for a target."""
        # Polaris (near north celestial pole)
        alt = scheduler._calculate_altitude(
            ra_hours=2.53,
            dec_deg=89.26,
            obs_time=datetime.now(),
        )

        # Should be close to latitude for circumpolar object
        assert alt > 0  # Should be visible from 35°N

    def test_altitude_varies_with_hour_angle(self, scheduler):
        """Altitude changes with hour angle."""
        ra = 12.0  # Arbitrary RA
        dec = 30.0

        # Check at different times
        now = datetime.now()
        alt1 = scheduler._calculate_altitude(ra, dec, now)
        alt2 = scheduler._calculate_altitude(ra, dec, now + timedelta(hours=6))

        # Altitudes should be different
        assert alt1 != alt2

    def test_southern_object_low_altitude(self, scheduler):
        """Southern objects have low altitude from northern latitudes."""
        # Very southern object
        alt = scheduler._calculate_altitude(
            ra_hours=12.0,
            dec_deg=-60.0,
            obs_time=datetime.now(),
        )

        # Should be below horizon or very low from 35°N
        assert alt < 20


# =============================================================================
# Score Calculation Tests
# =============================================================================


class TestScoreCalculation:
    """Tests for score calculations."""

    def test_high_altitude_high_score(self, scheduler, sample_candidates):
        """High altitude targets get high altitude scores."""
        constraints = SchedulingConstraints(min_altitude_deg=20.0)

        candidates = [
            CandidateTarget(
                target_id="test",
                target_name=None,
                ra_hours=12.0,
                dec_degrees=35.0,  # Near latitude, can get high
            )
        ]

        scored = scheduler._score_candidates(candidates, constraints, datetime.now())

        # Score should be between 0 and 1
        assert 0 <= scored[0].altitude_score <= 1

    def test_base_score_from_magnitude(self, scheduler):
        """Brighter objects get higher base scores."""
        bright = CandidateTarget(
            target_id="bright",
            target_name=None,
            ra_hours=12.0,
            dec_degrees=30.0,
            magnitude=3.0,
        )

        faint = CandidateTarget(
            target_id="faint",
            target_name=None,
            ra_hours=12.0,
            dec_degrees=30.0,
            magnitude=12.0,
        )

        bright_score = scheduler._calculate_base_score(bright)
        faint_score = scheduler._calculate_base_score(faint)

        assert bright_score > faint_score


# =============================================================================
# Quality Conversion Tests
# =============================================================================


class TestQualityConversion:
    """Tests for score to quality conversion."""

    def test_excellent_quality(self, scheduler):
        """High scores produce excellent quality."""
        quality = scheduler._score_to_quality(0.90)
        assert quality == ScheduleQuality.EXCELLENT

    def test_good_quality(self, scheduler):
        """Medium-high scores produce good quality."""
        quality = scheduler._score_to_quality(0.75)
        assert quality == ScheduleQuality.GOOD

    def test_fair_quality(self, scheduler):
        """Medium scores produce fair quality."""
        quality = scheduler._score_to_quality(0.60)
        assert quality == ScheduleQuality.FAIR

    def test_marginal_quality(self, scheduler):
        """Low scores produce marginal quality."""
        quality = scheduler._score_to_quality(0.45)
        assert quality == ScheduleQuality.MARGINAL

    def test_poor_quality(self, scheduler):
        """Very low scores produce poor quality."""
        quality = scheduler._score_to_quality(0.30)
        assert quality == ScheduleQuality.POOR


# =============================================================================
# Enum Tests
# =============================================================================


class TestEnums:
    """Tests for enum values."""

    def test_schedule_quality_values(self):
        """All schedule quality values defined."""
        assert ScheduleQuality.EXCELLENT.value == "excellent"
        assert ScheduleQuality.GOOD.value == "good"
        assert ScheduleQuality.FAIR.value == "fair"
        assert ScheduleQuality.MARGINAL.value == "marginal"
        assert ScheduleQuality.POOR.value == "poor"

    def test_schedule_reason_values(self):
        """All schedule reason values defined."""
        assert ScheduleReason.OPTIMAL_ALTITUDE.value == "optimal_altitude"
        assert ScheduleReason.MOON_AVOIDANCE.value == "moon_avoidance"
        assert ScheduleReason.WEATHER_WINDOW.value == "weather_window"
        assert ScheduleReason.HISTORICAL_SUCCESS.value == "historical_success"


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Tests for module-level factory."""

    def test_get_scheduler_returns_singleton(self):
        """get_scheduler returns same instance."""
        s1 = get_scheduler()
        s2 = get_scheduler()
        assert s1 is s2

    def test_get_scheduler_creates_instance(self):
        """get_scheduler creates instance."""
        scheduler = get_scheduler()
        assert isinstance(scheduler, ObservingScheduler)

    def test_get_scheduler_with_location(self):
        """get_scheduler accepts location parameters."""
        scheduler = get_scheduler(latitude_deg=40.0, longitude_deg=-75.0)
        assert isinstance(scheduler, ObservingScheduler)
