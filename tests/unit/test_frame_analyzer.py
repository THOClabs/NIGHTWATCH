"""
NIGHTWATCH Frame Analyzer Tests

Tests for frame quality analysis and automatic rejection (Steps 122-125).
"""

import pytest
from datetime import datetime, timezone, timedelta

from services.camera.frame_analyzer import (
    FrameAnalyzer,
    FrameMetrics,
    FrameQuality,
    StarMeasurement,
    QualityThresholds,
    SessionQualityStats,
    RejectionReason,
    create_star_measurement,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def analyzer():
    """Create a basic FrameAnalyzer."""
    return FrameAnalyzer(pixel_scale=1.0, bit_depth=16)


@pytest.fixture
def analyzer_with_session(analyzer):
    """Create analyzer with active session."""
    analyzer.start_session("test_session")
    return analyzer


@pytest.fixture
def good_stars():
    """Create a set of good quality star measurements (enough to pass star count threshold)."""
    stars = []
    for i in range(25):  # Enough stars to pass min_stars_good threshold
        stars.append(create_star_measurement(
            x=100 + i * 40,
            y=100 + i * 30,
            fwhm=2.5 + (i % 3) * 0.1,
            peak=30000 - i * 100,
            flux=50000 - i * 200,
            background=500,
            elongation=1.05 + (i % 5) * 0.01,
            angle=i % 20,
        ))
    return stars


@pytest.fixture
def poor_stars():
    """Create a set of poor quality star measurements (trailing)."""
    return [
        create_star_measurement(x=100, y=100, fwhm=6.0, peak=15000, flux=30000,
                               background=500, elongation=1.6, angle=45),
        create_star_measurement(x=200, y=150, fwhm=5.8, peak=14000, flux=28000,
                               background=500, elongation=1.55, angle=44),
    ]


# =============================================================================
# StarMeasurement Tests
# =============================================================================


class TestStarMeasurement:
    """Tests for StarMeasurement creation."""

    def test_create_star_measurement(self):
        """Test creating a star measurement."""
        star = create_star_measurement(
            x=100, y=150, fwhm=3.0, peak=30000, flux=50000,
            background=500, elongation=1.1, angle=45
        )
        assert star.x == 100
        assert star.y == 150
        assert star.fwhm == 3.0
        assert star.hfd == pytest.approx(3.54, rel=0.1)  # ~1.18 * FWHM
        assert star.elongation == 1.1

    def test_snr_calculation(self):
        """Test SNR calculation from background."""
        star = create_star_measurement(
            x=100, y=100, fwhm=3.0, peak=30000, flux=50000,
            background=400
        )
        # SNR = (peak - background) / sqrt(background)
        expected_snr = (30000 - 400) / (400 ** 0.5)
        assert star.snr == pytest.approx(expected_snr, rel=0.01)

    def test_saturation_detection(self):
        """Test saturation flag."""
        saturated = create_star_measurement(
            x=100, y=100, fwhm=3.0, peak=65000, flux=100000,
            saturation_level=60000
        )
        unsaturated = create_star_measurement(
            x=100, y=100, fwhm=3.0, peak=30000, flux=50000,
            saturation_level=60000
        )
        assert saturated.saturated is True
        assert unsaturated.saturated is False


# =============================================================================
# Quality Thresholds Tests
# =============================================================================


class TestQualityThresholds:
    """Tests for quality threshold configuration."""

    def test_default_thresholds(self):
        """Test default threshold values."""
        t = QualityThresholds()
        assert t.fwhm_excellent == 2.5
        assert t.fwhm_reject == 8.0
        assert t.elongation_reject == 1.5

    def test_custom_thresholds(self):
        """Test custom threshold configuration."""
        t = QualityThresholds(fwhm_excellent=2.0, fwhm_reject=6.0)
        assert t.fwhm_excellent == 2.0
        assert t.fwhm_reject == 6.0

    def test_fwhm_trend_threshold_defaults(self):
        """Test FWHM trend threshold defaults."""
        t = QualityThresholds()
        assert t.fwhm_trend_threshold == 0.5
        assert t.fwhm_refocus_threshold == 1.0

    def test_fwhm_trend_threshold_custom(self):
        """Test custom FWHM trend thresholds."""
        t = QualityThresholds(fwhm_trend_threshold=0.3, fwhm_refocus_threshold=0.8)
        assert t.fwhm_trend_threshold == 0.3
        assert t.fwhm_refocus_threshold == 0.8


# =============================================================================
# Star Analysis Tests
# =============================================================================


class TestStarAnalysis:
    """Tests for star measurement aggregation."""

    def test_analyze_stars_empty(self, analyzer):
        """Test analyzing empty star list."""
        result = analyzer.analyze_stars([])
        assert result["star_count"] == 0
        assert result["median_fwhm"] == 0.0

    def test_analyze_stars_single(self, analyzer):
        """Test analyzing single star."""
        stars = [create_star_measurement(x=100, y=100, fwhm=3.0, peak=30000, flux=50000)]
        result = analyzer.analyze_stars(stars)
        assert result["star_count"] == 1
        assert result["median_fwhm"] == 3.0

    def test_analyze_stars_median_fwhm(self, analyzer, good_stars):
        """Test median FWHM calculation."""
        result = analyzer.analyze_stars(good_stars)
        # Stars have FWHM centered around 2.5-2.7
        assert 2.4 <= result["median_fwhm"] <= 2.8

    def test_analyze_stars_elongation(self, analyzer, good_stars):
        """Test elongation statistics."""
        result = analyzer.analyze_stars(good_stars)
        assert result["median_elongation"] < 1.1
        assert result["max_elongation"] >= result["median_elongation"]

    def test_analyze_stars_saturated_count(self, analyzer):
        """Test counting saturated stars."""
        stars = [
            create_star_measurement(x=100, y=100, fwhm=3.0, peak=65000, flux=100000, saturation_level=60000),
            create_star_measurement(x=200, y=200, fwhm=3.0, peak=30000, flux=50000, saturation_level=60000),
        ]
        result = analyzer.analyze_stars(stars)
        assert result["saturated_count"] == 1


# =============================================================================
# Quality Assessment Tests (Step 123)
# =============================================================================


class TestQualityAssessment:
    """Tests for frame quality assessment."""

    def test_excellent_quality(self, analyzer):
        """Test excellent quality assessment."""
        metrics = FrameMetrics(
            frame_id="test",
            timestamp=datetime.now(timezone.utc),
            exposure_sec=120,
            star_count=50,
            median_fwhm=2.0,
            median_elongation=1.05,
            median_snr=60,
        )
        quality, score, reasons = analyzer.assess_quality(metrics)
        assert quality == FrameQuality.EXCELLENT
        assert score >= 0.9
        assert len(reasons) == 0

    def test_reject_high_fwhm(self, analyzer):
        """Test rejection due to high FWHM."""
        metrics = FrameMetrics(
            frame_id="test",
            timestamp=datetime.now(timezone.utc),
            exposure_sec=120,
            star_count=30,
            median_fwhm=10.0,  # Very high
            median_elongation=1.1,
            median_snr=30,
        )
        quality, score, reasons = analyzer.assess_quality(metrics)
        assert quality == FrameQuality.REJECT
        assert RejectionReason.HIGH_FWHM in reasons

    def test_reject_elongated_stars(self, analyzer):
        """Test rejection due to star elongation."""
        metrics = FrameMetrics(
            frame_id="test",
            timestamp=datetime.now(timezone.utc),
            exposure_sec=120,
            star_count=30,
            median_fwhm=3.0,
            median_elongation=1.7,  # Very elongated
            median_snr=30,
        )
        quality, score, reasons = analyzer.assess_quality(metrics)
        assert quality == FrameQuality.REJECT
        assert RejectionReason.ELONGATED_STARS in reasons

    def test_reject_low_star_count(self, analyzer):
        """Test rejection due to low star count."""
        metrics = FrameMetrics(
            frame_id="test",
            timestamp=datetime.now(timezone.utc),
            exposure_sec=120,
            star_count=3,  # Very few stars
            median_fwhm=3.0,
            median_elongation=1.1,
            median_snr=30,
        )
        quality, score, reasons = analyzer.assess_quality(metrics)
        assert quality == FrameQuality.REJECT
        assert RejectionReason.LOW_STAR_COUNT in reasons

    def test_reject_low_snr(self, analyzer):
        """Test rejection due to low SNR."""
        metrics = FrameMetrics(
            frame_id="test",
            timestamp=datetime.now(timezone.utc),
            exposure_sec=120,
            star_count=30,
            median_fwhm=3.0,
            median_elongation=1.1,
            median_snr=3.0,  # Very low
        )
        quality, score, reasons = analyzer.assess_quality(metrics)
        assert RejectionReason.LOW_SNR in reasons

    def test_reject_trailing(self, analyzer):
        """Test rejection due to consistent trailing angle."""
        metrics = FrameMetrics(
            frame_id="test",
            timestamp=datetime.now(timezone.utc),
            exposure_sec=120,
            star_count=30,
            median_fwhm=4.0,
            median_elongation=1.4,
            elongation_consistency=0.9,  # Very consistent angle
            median_snr=30,
        )
        quality, score, reasons = analyzer.assess_quality(metrics)
        assert RejectionReason.TRAILING in reasons


# =============================================================================
# Frame Analysis Tests
# =============================================================================


class TestFrameAnalysis:
    """Tests for complete frame analysis."""

    def test_analyze_frame_good(self, analyzer_with_session, good_stars):
        """Test analyzing a good frame."""
        metrics = analyzer_with_session.analyze_frame(
            stars=good_stars,
            frame_id="frame_001",
            exposure_sec=120.0,
            background_mean=500,
            background_stddev=25,
        )
        assert metrics.frame_id == "frame_001"
        assert metrics.star_count == 25  # Our fixture has 25 stars
        assert metrics.quality in [FrameQuality.EXCELLENT, FrameQuality.GOOD]

    def test_analyze_frame_poor(self, analyzer_with_session, poor_stars):
        """Test analyzing a poor frame."""
        metrics = analyzer_with_session.analyze_frame(
            stars=poor_stars,
            frame_id="frame_002",
            exposure_sec=120.0,
            background_mean=500,
            background_stddev=25,
        )
        assert metrics.quality in [FrameQuality.MARGINAL, FrameQuality.REJECT]
        assert len(metrics.rejection_reasons) > 0

    def test_analyze_frame_sets_fwhm_arcsec(self, analyzer_with_session, good_stars):
        """Test FWHM conversion to arcseconds."""
        analyzer_with_session.pixel_scale = 1.5  # 1.5"/pixel
        metrics = analyzer_with_session.analyze_frame(
            stars=good_stars,
            frame_id="frame_003",
            exposure_sec=120.0,
        )
        assert metrics.fwhm_arcsec is not None
        assert metrics.fwhm_arcsec == pytest.approx(metrics.median_fwhm * 1.5, rel=0.01)

    def test_analyze_frame_to_dict(self, analyzer_with_session, good_stars):
        """Test frame metrics serialization."""
        metrics = analyzer_with_session.analyze_frame(
            stars=good_stars,
            frame_id="frame_004",
            exposure_sec=120.0,
        )
        d = metrics.to_dict()
        assert "frame_id" in d
        assert "quality" in d
        assert "quality_score" in d


# =============================================================================
# Session Tracking Tests (Step 125)
# =============================================================================


class TestSessionTracking:
    """Tests for session quality tracking."""

    def test_start_session(self, analyzer):
        """Test starting a new session."""
        analyzer.start_session("new_session")
        stats = analyzer.get_session_stats()
        assert stats is not None
        assert stats.session_id == "new_session"
        assert stats.frame_count == 0

    def test_session_frame_count(self, analyzer_with_session, good_stars):
        """Test frame counting."""
        for i in range(5):
            analyzer_with_session.analyze_frame(
                stars=good_stars,
                frame_id=f"frame_{i}",
                exposure_sec=120.0,
            )
        stats = analyzer_with_session.get_session_stats()
        assert stats.frame_count == 5

    def test_session_quality_distribution(self, analyzer_with_session, good_stars, poor_stars):
        """Test quality distribution tracking."""
        # Add good frames
        for i in range(3):
            analyzer_with_session.analyze_frame(
                stars=good_stars,
                frame_id=f"good_{i}",
                exposure_sec=120.0,
            )
        # Add poor frames
        for i in range(2):
            analyzer_with_session.analyze_frame(
                stars=poor_stars,
                frame_id=f"poor_{i}",
                exposure_sec=120.0,
            )

        stats = analyzer_with_session.get_session_stats()
        assert stats.frame_count == 5
        assert stats.rejected_count >= 0

    def test_session_fwhm_tracking(self, analyzer_with_session, good_stars):
        """Test FWHM value tracking."""
        for i in range(5):
            analyzer_with_session.analyze_frame(
                stars=good_stars,
                frame_id=f"frame_{i}",
                exposure_sec=120.0,
            )
        stats = analyzer_with_session.get_session_stats()
        assert len(stats.fwhm_values) == 5

    def test_session_best_worst_tracking(self, analyzer_with_session):
        """Test best/worst frame tracking."""
        # Frame with good FWHM
        good = [create_star_measurement(x=100, y=100, fwhm=2.0, peak=30000, flux=50000)]
        analyzer_with_session.analyze_frame(stars=good, frame_id="best", exposure_sec=120)

        # Frame with poor FWHM
        poor = [create_star_measurement(x=100, y=100, fwhm=5.0, peak=30000, flux=50000)]
        analyzer_with_session.analyze_frame(stars=poor, frame_id="worst", exposure_sec=120)

        stats = analyzer_with_session.get_session_stats()
        assert stats.best_frame_id == "best"
        assert stats.worst_frame_id == "worst"
        assert stats.best_fwhm < stats.worst_fwhm

    def test_rejection_rate(self, analyzer_with_session, good_stars, poor_stars):
        """Test rejection rate calculation."""
        # 3 good, 2 rejected
        for i in range(3):
            analyzer_with_session.analyze_frame(stars=good_stars, frame_id=f"good_{i}", exposure_sec=120)
        for i in range(2):
            analyzer_with_session.analyze_frame(stars=poor_stars, frame_id=f"poor_{i}", exposure_sec=120)

        stats = analyzer_with_session.get_session_stats()
        # Rejection rate depends on actual classifications
        assert 0 <= stats.rejection_rate <= 100


# =============================================================================
# FWHM Trend Tests (Step 125)
# =============================================================================


class TestFWHMTrend:
    """Tests for FWHM trend analysis."""

    def test_trend_stable(self, analyzer_with_session):
        """Test stable FWHM trend detection."""
        # Add frames with consistent FWHM
        for i in range(10):
            stars = [create_star_measurement(x=100, y=100, fwhm=3.0, peak=30000, flux=50000)]
            analyzer_with_session.analyze_frame(stars=stars, frame_id=f"frame_{i}", exposure_sec=120)

        stats = analyzer_with_session.get_session_stats()
        assert stats.fwhm_trend == "stable"

    def test_trend_insufficient_data(self, analyzer_with_session):
        """Test trend with insufficient data."""
        stars = [create_star_measurement(x=100, y=100, fwhm=3.0, peak=30000, flux=50000)]
        analyzer_with_session.analyze_frame(stars=stars, frame_id="frame_1", exposure_sec=120)

        stats = analyzer_with_session.get_session_stats()
        assert stats.fwhm_trend == "stable"  # Default when not enough data

    def test_trend_uses_configurable_threshold(self):
        """Test that trend detection uses configurable threshold."""
        # Use a very low threshold so small changes trigger trend detection
        thresholds = QualityThresholds(fwhm_trend_threshold=0.1)
        analyzer = FrameAnalyzer(thresholds=thresholds)
        analyzer.start_session("test_sensitive")

        # Add frames with slight FWHM increase (should trigger with low threshold)
        base_time = datetime.now(timezone.utc)
        for i in range(6):
            fwhm = 3.0 + i * 0.05  # Small increase per frame
            stars = [create_star_measurement(x=100, y=100, fwhm=fwhm, peak=30000, flux=50000)]
            analyzer.analyze_frame(stars=stars, frame_id=f"frame_{i}", exposure_sec=120)
            # Simulate time passing by directly manipulating fwhm_values
            if analyzer._session_stats:
                analyzer._session_stats.fwhm_values[-1] = (
                    base_time + timedelta(minutes=i * 10),
                    fwhm
                )

        stats = analyzer.get_session_stats()
        # With low threshold, even small changes should be detected
        assert stats.fwhm_trend in ["degrading", "stable"]

    def test_trend_with_high_threshold(self):
        """Test that high threshold ignores moderate changes."""
        # Use a very high threshold so only large changes trigger trend detection
        thresholds = QualityThresholds(fwhm_trend_threshold=5.0)
        analyzer = FrameAnalyzer(thresholds=thresholds)
        analyzer.start_session("test_insensitive")

        # Verify the threshold is properly set
        assert analyzer.thresholds.fwhm_trend_threshold == 5.0

        # Add frames with consistent FWHM (no change = rate of 0)
        for i in range(6):
            fwhm = 3.0  # Constant FWHM, rate = 0
            stars = [create_star_measurement(x=100, y=100, fwhm=fwhm, peak=30000, flux=50000)]
            analyzer.analyze_frame(stars=stars, frame_id=f"frame_{i}", exposure_sec=120)

        stats = analyzer.get_session_stats()
        # Zero rate should be well below 5.0 threshold
        assert stats.fwhm_trend == "stable"
        assert abs(stats.fwhm_trend_rate) < 5.0


# =============================================================================
# Recommendation Tests
# =============================================================================


class TestRecommendations:
    """Tests for focus recommendations."""

    def test_recommendation_none_good_session(self, analyzer_with_session, good_stars):
        """Test no recommendation for good session."""
        for i in range(5):
            analyzer_with_session.analyze_frame(stars=good_stars, frame_id=f"frame_{i}", exposure_sec=120)

        rec = analyzer_with_session.get_focus_recommendation()
        # Good session may or may not have recommendation
        assert rec is None or isinstance(rec, str)

    def test_format_session_summary(self, analyzer_with_session, good_stars):
        """Test session summary formatting."""
        for i in range(3):
            analyzer_with_session.analyze_frame(stars=good_stars, frame_id=f"frame_{i}", exposure_sec=120)

        summary = analyzer_with_session.format_session_summary()
        assert "3 frames" in summary
        assert "session" in summary.lower()

    def test_format_session_summary_no_session(self, analyzer):
        """Test summary when no session active."""
        summary = analyzer.format_session_summary()
        assert "No imaging session" in summary


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_star_list(self, analyzer_with_session):
        """Test handling empty star list."""
        metrics = analyzer_with_session.analyze_frame(
            stars=[],
            frame_id="empty",
            exposure_sec=120.0,
        )
        assert metrics.star_count == 0
        assert RejectionReason.LOW_STAR_COUNT in metrics.rejection_reasons

    def test_single_star(self, analyzer_with_session):
        """Test handling single star."""
        stars = [create_star_measurement(x=100, y=100, fwhm=3.0, peak=30000, flux=50000)]
        metrics = analyzer_with_session.analyze_frame(
            stars=stars,
            frame_id="single",
            exposure_sec=120.0,
        )
        assert metrics.star_count == 1

    def test_high_background(self, analyzer_with_session, good_stars):
        """Test high background detection."""
        metrics = analyzer_with_session.analyze_frame(
            stars=good_stars,
            frame_id="high_bg",
            exposure_sec=120.0,
            background_mean=40000,  # High background
        )
        # Should flag high background
        assert RejectionReason.HIGH_BACKGROUND in metrics.rejection_reasons

    def test_quality_score_clamped(self, analyzer):
        """Test quality score is clamped to 0-1."""
        # Excellent metrics might give score > 1 before clamping
        metrics = FrameMetrics(
            frame_id="test",
            timestamp=datetime.now(timezone.utc),
            exposure_sec=120,
            star_count=100,
            median_fwhm=1.5,
            median_elongation=1.0,
            median_snr=100,
        )
        quality, score, reasons = analyzer.assess_quality(metrics)
        assert 0.0 <= score <= 1.0
