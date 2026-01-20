"""
NIGHTWATCH Frame Quality Analyzer
Automatic Frame Rejection and Quality Metrics (Steps 122-125)

This module provides real-time image quality analysis for:
- Star FWHM measurement (Step 122)
- Automatic frame rejection based on quality thresholds (Step 123)
- Tracking error detection via star elongation (Step 124)
- Focus quality trend analysis (Step 125)

The analyzer evaluates frames and produces quality metrics that can
be used to automatically discard poor frames during imaging sessions.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Tuple, Any
import statistics


class FrameQuality(Enum):
    """Frame quality classification."""
    EXCELLENT = "excellent"    # Keep, high priority for stacking
    GOOD = "good"              # Keep, normal stacking weight
    ACCEPTABLE = "acceptable"  # Keep, reduced stacking weight
    MARGINAL = "marginal"      # Consider rejecting
    REJECT = "reject"          # Auto-reject


class RejectionReason(Enum):
    """Reasons for frame rejection."""
    NONE = "none"
    HIGH_FWHM = "high_fwhm"              # Poor focus or seeing
    ELONGATED_STARS = "elongated_stars"   # Tracking error
    LOW_STAR_COUNT = "low_star_count"     # Clouds or misfocus
    HIGH_BACKGROUND = "high_background"   # Light pollution, moon, dawn
    SATURATED = "saturated"               # Overexposed
    LOW_SNR = "low_snr"                   # Underexposed
    TRAILING = "trailing"                 # Mount tracking failure
    GRADIENT = "gradient"                 # Amp glow, light leak


@dataclass
class StarMeasurement:
    """Measurement of a single star in a frame."""
    x: float                    # Centroid X position (pixels)
    y: float                    # Centroid Y position (pixels)
    fwhm: float                 # Full-width half-max (pixels)
    hfd: float                  # Half-flux diameter (pixels)
    peak: float                 # Peak pixel value (ADU)
    flux: float                 # Total flux (ADU)
    snr: float                  # Signal-to-noise ratio
    elongation: float           # Ratio of major/minor axis (1.0 = circular)
    angle: float                # Elongation angle (degrees)
    saturated: bool = False     # Star is saturated


@dataclass
class FrameMetrics:
    """
    Complete quality metrics for a single frame (Steps 122-125).

    These metrics enable automatic frame rejection decisions and
    tracking of focus/seeing trends over an imaging session.
    """
    frame_id: str                           # Unique frame identifier
    timestamp: datetime                     # When frame was captured
    exposure_sec: float                     # Exposure duration

    # Star measurements (Step 122)
    star_count: int = 0                     # Number of detected stars
    median_fwhm: float = 0.0                # Median FWHM (pixels)
    median_hfd: float = 0.0                 # Median HFD (pixels)
    fwhm_stddev: float = 0.0                # FWHM variation
    fwhm_arcsec: Optional[float] = None     # FWHM in arcseconds

    # Tracking quality (Step 124)
    median_elongation: float = 1.0          # Star elongation (1.0 = round)
    max_elongation: float = 1.0             # Worst star elongation
    elongation_angle: float = 0.0           # Consistent angle = tracking issue
    elongation_consistency: float = 0.0     # How uniform elongation angles are

    # Background and noise
    background_mean: float = 0.0            # Mean background level (ADU)
    background_stddev: float = 0.0          # Background noise (ADU)
    median_snr: float = 0.0                 # Median star SNR
    gradient_magnitude: float = 0.0         # Background gradient strength

    # Saturation
    saturated_stars: int = 0                # Count of saturated stars
    saturated_pixels_pct: float = 0.0       # Percentage of saturated pixels

    # Quality assessment (Step 123)
    quality: FrameQuality = FrameQuality.GOOD
    quality_score: float = 1.0              # 0.0 to 1.0
    rejection_reasons: List[RejectionReason] = field(default_factory=list)
    recommendation: str = ""

    # Reference to star measurements (optional, can be large)
    stars: List[StarMeasurement] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp.isoformat(),
            "exposure_sec": self.exposure_sec,
            "star_count": self.star_count,
            "median_fwhm": self.median_fwhm,
            "median_hfd": self.median_hfd,
            "fwhm_arcsec": self.fwhm_arcsec,
            "median_elongation": self.median_elongation,
            "background_mean": self.background_mean,
            "median_snr": self.median_snr,
            "quality": self.quality.value,
            "quality_score": self.quality_score,
            "rejection_reasons": [r.value for r in self.rejection_reasons],
        }


@dataclass
class QualityThresholds:
    """
    Configurable thresholds for frame quality assessment.

    These can be adjusted based on equipment, seeing conditions,
    and imaging goals.
    """
    # FWHM thresholds (in pixels, typical for 1"/pixel scale)
    fwhm_excellent: float = 2.5        # < this = excellent
    fwhm_good: float = 3.5             # < this = good
    fwhm_acceptable: float = 5.0       # < this = acceptable
    fwhm_reject: float = 8.0           # > this = reject

    # Elongation thresholds (1.0 = perfectly round)
    elongation_good: float = 1.15      # < this = round enough
    elongation_acceptable: float = 1.3  # < this = acceptable
    elongation_reject: float = 1.5      # > this = reject (trailing)

    # Star count thresholds
    min_stars_reject: int = 5          # < this = reject (clouds?)
    min_stars_good: int = 20           # > this = good star count

    # SNR thresholds
    snr_excellent: float = 50.0        # > this = excellent
    snr_good: float = 20.0             # > this = good
    snr_reject: float = 5.0            # < this = reject

    # Background thresholds (as fraction of dynamic range)
    background_high: float = 0.3       # > this = high background warning
    background_reject: float = 0.5     # > this = reject (washed out)

    # Saturation
    max_saturated_pct: float = 0.1     # > this = oversaturated

    # Gradient (normalized 0-1)
    gradient_reject: float = 0.2       # > this = significant gradient


@dataclass
class SessionQualityStats:
    """
    Aggregated quality statistics for an imaging session (Step 125).

    Tracks trends in focus quality over time.
    """
    session_id: str
    start_time: datetime
    frame_count: int = 0
    rejected_count: int = 0

    # FWHM trend (Step 125)
    fwhm_values: List[Tuple[datetime, float]] = field(default_factory=list)
    fwhm_trend: str = "stable"         # "improving", "degrading", "stable"
    fwhm_trend_rate: float = 0.0       # Change per hour

    # Quality distribution
    excellent_count: int = 0
    good_count: int = 0
    acceptable_count: int = 0
    marginal_count: int = 0
    reject_count: int = 0

    # Best/worst frames
    best_fwhm: float = float('inf')
    worst_fwhm: float = 0.0
    best_frame_id: str = ""
    worst_frame_id: str = ""

    # Rejection reasons summary
    rejection_summary: Dict[str, int] = field(default_factory=dict)

    @property
    def rejection_rate(self) -> float:
        """Percentage of frames rejected."""
        if self.frame_count == 0:
            return 0.0
        return (self.rejected_count / self.frame_count) * 100

    @property
    def average_fwhm(self) -> float:
        """Average FWHM across session."""
        if not self.fwhm_values:
            return 0.0
        return statistics.mean(v for _, v in self.fwhm_values)


class FrameAnalyzer:
    """
    Frame quality analyzer for automatic rejection (Steps 122-125).

    Analyzes captured frames to measure star quality metrics and
    determine whether frames should be kept or rejected.

    Usage:
        analyzer = FrameAnalyzer()
        metrics = analyzer.analyze_frame(image_data, frame_id)
        if metrics.quality == FrameQuality.REJECT:
            print(f"Rejecting: {metrics.rejection_reasons}")
    """

    def __init__(
        self,
        thresholds: Optional[QualityThresholds] = None,
        pixel_scale: float = 1.0,       # arcsec/pixel
        bit_depth: int = 16,            # Camera bit depth
    ):
        """
        Initialize frame analyzer.

        Args:
            thresholds: Quality thresholds (defaults to standard values)
            pixel_scale: Image scale in arcsec/pixel
            bit_depth: Camera bit depth (for saturation detection)
        """
        self.thresholds = thresholds or QualityThresholds()
        self.pixel_scale = pixel_scale
        self.bit_depth = bit_depth
        self.max_adu = (2 ** bit_depth) - 1

        # Session tracking
        self._session_stats: Optional[SessionQualityStats] = None
        self._frame_history: List[FrameMetrics] = []

    def start_session(self, session_id: str) -> None:
        """Start a new imaging session for quality tracking."""
        self._session_stats = SessionQualityStats(
            session_id=session_id,
            start_time=datetime.now(timezone.utc),
        )
        self._frame_history = []

    def get_session_stats(self) -> Optional[SessionQualityStats]:
        """Get current session statistics."""
        return self._session_stats

    def analyze_stars(self, stars: List[StarMeasurement]) -> Dict[str, float]:
        """
        Calculate aggregate statistics from star measurements.

        Args:
            stars: List of measured stars

        Returns:
            Dictionary of aggregate metrics
        """
        if not stars:
            return {
                "star_count": 0,
                "median_fwhm": 0.0,
                "median_hfd": 0.0,
                "fwhm_stddev": 0.0,
                "median_elongation": 1.0,
                "max_elongation": 1.0,
                "elongation_angle": 0.0,
                "elongation_consistency": 0.0,
                "median_snr": 0.0,
                "saturated_count": 0,
            }

        fwhm_values = [s.fwhm for s in stars if s.fwhm > 0]
        hfd_values = [s.hfd for s in stars if s.hfd > 0]
        elongation_values = [s.elongation for s in stars]
        snr_values = [s.snr for s in stars if s.snr > 0]
        angles = [s.angle for s in stars if s.elongation > 1.1]

        # Calculate elongation angle consistency
        angle_consistency = 0.0
        if len(angles) >= 3:
            # Circular standard deviation for angles
            sin_sum = sum(math.sin(math.radians(a * 2)) for a in angles)
            cos_sum = sum(math.cos(math.radians(a * 2)) for a in angles)
            r = math.sqrt(sin_sum**2 + cos_sum**2) / len(angles)
            angle_consistency = r  # 1.0 = all same direction (tracking issue)

        return {
            "star_count": len(stars),
            "median_fwhm": statistics.median(fwhm_values) if fwhm_values else 0.0,
            "median_hfd": statistics.median(hfd_values) if hfd_values else 0.0,
            "fwhm_stddev": statistics.stdev(fwhm_values) if len(fwhm_values) > 1 else 0.0,
            "median_elongation": statistics.median(elongation_values) if elongation_values else 1.0,
            "max_elongation": max(elongation_values) if elongation_values else 1.0,
            "elongation_angle": statistics.median(angles) if angles else 0.0,
            "elongation_consistency": angle_consistency,
            "median_snr": statistics.median(snr_values) if snr_values else 0.0,
            "saturated_count": sum(1 for s in stars if s.saturated),
        }

    def assess_quality(self, metrics: FrameMetrics) -> Tuple[FrameQuality, float, List[RejectionReason]]:
        """
        Assess frame quality based on metrics (Step 123).

        Returns:
            Tuple of (quality_classification, score, rejection_reasons)
        """
        t = self.thresholds
        reasons = []
        score = 1.0

        # Check FWHM (Step 122)
        if metrics.median_fwhm > 0:
            if metrics.median_fwhm > t.fwhm_reject:
                reasons.append(RejectionReason.HIGH_FWHM)
                score *= 0.3
            elif metrics.median_fwhm > t.fwhm_acceptable:
                score *= 0.6
            elif metrics.median_fwhm > t.fwhm_good:
                score *= 0.8
            elif metrics.median_fwhm > t.fwhm_excellent:
                score *= 0.9

        # Check elongation (Step 124 - tracking error)
        if metrics.median_elongation > t.elongation_reject:
            reasons.append(RejectionReason.ELONGATED_STARS)
            score *= 0.3
        elif metrics.median_elongation > t.elongation_acceptable:
            score *= 0.6
        elif metrics.median_elongation > t.elongation_good:
            score *= 0.85

        # Check if elongation is consistent (= tracking, not seeing)
        if metrics.elongation_consistency > 0.7 and metrics.median_elongation > 1.2:
            reasons.append(RejectionReason.TRAILING)
            score *= 0.5

        # Check star count
        if metrics.star_count < t.min_stars_reject:
            reasons.append(RejectionReason.LOW_STAR_COUNT)
            score *= 0.2
        elif metrics.star_count < t.min_stars_good:
            score *= 0.8

        # Check SNR
        if metrics.median_snr > 0:
            if metrics.median_snr < t.snr_reject:
                reasons.append(RejectionReason.LOW_SNR)
                score *= 0.3
            elif metrics.median_snr < t.snr_good:
                score *= 0.7
            elif metrics.median_snr > t.snr_excellent:
                score *= 1.05  # Slight bonus

        # Check background
        bg_fraction = metrics.background_mean / self.max_adu
        if bg_fraction > t.background_reject:
            reasons.append(RejectionReason.HIGH_BACKGROUND)
            score *= 0.2
        elif bg_fraction > t.background_high:
            score *= 0.7

        # Check saturation
        if metrics.saturated_pixels_pct > t.max_saturated_pct:
            reasons.append(RejectionReason.SATURATED)
            score *= 0.5

        # Check gradient
        if metrics.gradient_magnitude > t.gradient_reject:
            reasons.append(RejectionReason.GRADIENT)
            score *= 0.7

        # Clamp score
        score = max(0.0, min(1.0, score))

        # Determine quality class
        if reasons:
            quality = FrameQuality.REJECT
        elif score >= 0.9:
            quality = FrameQuality.EXCELLENT
        elif score >= 0.75:
            quality = FrameQuality.GOOD
        elif score >= 0.5:
            quality = FrameQuality.ACCEPTABLE
        elif score >= 0.3:
            quality = FrameQuality.MARGINAL
        else:
            quality = FrameQuality.REJECT

        return quality, score, reasons

    def _generate_recommendation(self, metrics: FrameMetrics) -> str:
        """Generate human-readable recommendation."""
        if metrics.quality == FrameQuality.EXCELLENT:
            return "Excellent frame - high priority for stacking"
        elif metrics.quality == FrameQuality.GOOD:
            return "Good frame - suitable for stacking"
        elif metrics.quality == FrameQuality.ACCEPTABLE:
            return "Acceptable frame - include with lower weight"
        elif metrics.quality == FrameQuality.MARGINAL:
            return f"Marginal quality - consider excluding"
        else:
            reasons_str = ", ".join(r.value.replace("_", " ") for r in metrics.rejection_reasons)
            return f"Reject: {reasons_str}"

    def analyze_frame(
        self,
        stars: List[StarMeasurement],
        frame_id: str,
        exposure_sec: float,
        background_mean: float = 0.0,
        background_stddev: float = 0.0,
        saturated_pixels_pct: float = 0.0,
        gradient_magnitude: float = 0.0,
        timestamp: Optional[datetime] = None,
    ) -> FrameMetrics:
        """
        Analyze a frame and produce quality metrics (Steps 122-125).

        Args:
            stars: List of detected and measured stars
            frame_id: Unique identifier for this frame
            exposure_sec: Exposure duration in seconds
            background_mean: Mean background level (ADU)
            background_stddev: Background noise (ADU)
            saturated_pixels_pct: Percentage of saturated pixels
            gradient_magnitude: Background gradient strength (0-1)
            timestamp: Frame capture time (defaults to now)

        Returns:
            FrameMetrics with quality assessment
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # Analyze stars
        star_stats = self.analyze_stars(stars)

        # Build metrics
        metrics = FrameMetrics(
            frame_id=frame_id,
            timestamp=timestamp,
            exposure_sec=exposure_sec,
            star_count=star_stats["star_count"],
            median_fwhm=star_stats["median_fwhm"],
            median_hfd=star_stats["median_hfd"],
            fwhm_stddev=star_stats["fwhm_stddev"],
            fwhm_arcsec=star_stats["median_fwhm"] * self.pixel_scale if star_stats["median_fwhm"] > 0 else None,
            median_elongation=star_stats["median_elongation"],
            max_elongation=star_stats["max_elongation"],
            elongation_angle=star_stats["elongation_angle"],
            elongation_consistency=star_stats["elongation_consistency"],
            background_mean=background_mean,
            background_stddev=background_stddev,
            median_snr=star_stats["median_snr"],
            saturated_stars=star_stats["saturated_count"],
            saturated_pixels_pct=saturated_pixels_pct,
            gradient_magnitude=gradient_magnitude,
            stars=stars,
        )

        # Assess quality
        quality, score, reasons = self.assess_quality(metrics)
        metrics.quality = quality
        metrics.quality_score = score
        metrics.rejection_reasons = reasons
        metrics.recommendation = self._generate_recommendation(metrics)

        # Update session stats
        self._update_session_stats(metrics)

        # Keep in history
        self._frame_history.append(metrics)

        return metrics

    def _update_session_stats(self, metrics: FrameMetrics) -> None:
        """Update session statistics with new frame."""
        if self._session_stats is None:
            return

        stats = self._session_stats
        stats.frame_count += 1

        # Track FWHM (Step 125)
        if metrics.median_fwhm > 0:
            stats.fwhm_values.append((metrics.timestamp, metrics.median_fwhm))

            if metrics.median_fwhm < stats.best_fwhm:
                stats.best_fwhm = metrics.median_fwhm
                stats.best_frame_id = metrics.frame_id

            if metrics.median_fwhm > stats.worst_fwhm:
                stats.worst_fwhm = metrics.median_fwhm
                stats.worst_frame_id = metrics.frame_id

        # Quality distribution
        if metrics.quality == FrameQuality.EXCELLENT:
            stats.excellent_count += 1
        elif metrics.quality == FrameQuality.GOOD:
            stats.good_count += 1
        elif metrics.quality == FrameQuality.ACCEPTABLE:
            stats.acceptable_count += 1
        elif metrics.quality == FrameQuality.MARGINAL:
            stats.marginal_count += 1
        elif metrics.quality == FrameQuality.REJECT:
            stats.reject_count += 1
            stats.rejected_count += 1

            # Track rejection reasons
            for reason in metrics.rejection_reasons:
                reason_name = reason.value
                stats.rejection_summary[reason_name] = stats.rejection_summary.get(reason_name, 0) + 1

        # Update FWHM trend
        self._update_fwhm_trend()

    def _update_fwhm_trend(self) -> None:
        """Analyze FWHM trend over session (Step 125)."""
        if self._session_stats is None:
            return

        values = self._session_stats.fwhm_values
        if len(values) < 5:
            self._session_stats.fwhm_trend = "stable"
            return

        # Compare recent vs earlier values
        mid = len(values) // 2
        early_avg = statistics.mean(v for _, v in values[:mid])
        late_avg = statistics.mean(v for _, v in values[mid:])

        # Calculate time span
        time_span_hours = (values[-1][0] - values[0][0]).total_seconds() / 3600
        if time_span_hours < 0.01:
            time_span_hours = 0.01

        change = late_avg - early_avg
        rate_per_hour = change / time_span_hours

        self._session_stats.fwhm_trend_rate = rate_per_hour

        # Threshold for "significant" change: 0.5 pixels/hour
        if rate_per_hour > 0.5:
            self._session_stats.fwhm_trend = "degrading"
        elif rate_per_hour < -0.5:
            self._session_stats.fwhm_trend = "improving"
        else:
            self._session_stats.fwhm_trend = "stable"

    def get_focus_recommendation(self) -> Optional[str]:
        """
        Get focus recommendation based on quality trend (Step 125).

        Returns:
            Recommendation string or None if no action needed
        """
        if self._session_stats is None:
            return None

        stats = self._session_stats

        # Check if FWHM is degrading
        if stats.fwhm_trend == "degrading" and stats.fwhm_trend_rate > 1.0:
            return f"Focus degrading at {stats.fwhm_trend_rate:.1f} pixels/hour - refocus recommended"

        # Check if rejection rate is high
        if stats.rejection_rate > 20:
            top_reason = max(stats.rejection_summary.items(), key=lambda x: x[1])[0] if stats.rejection_summary else "unknown"
            return f"High rejection rate ({stats.rejection_rate:.0f}%) - primary cause: {top_reason}"

        # Check if current FWHM is much worse than best
        if len(stats.fwhm_values) > 3:
            current_fwhm = stats.fwhm_values[-1][1]
            if current_fwhm > stats.best_fwhm * 1.5:
                return f"Current FWHM ({current_fwhm:.1f}) significantly worse than best ({stats.best_fwhm:.1f}) - check focus"

        return None

    def format_session_summary(self) -> str:
        """Format session statistics for voice output."""
        if self._session_stats is None:
            return "No imaging session active."

        stats = self._session_stats
        parts = [f"Session summary: {stats.frame_count} frames analyzed."]

        # Quality breakdown
        kept = stats.excellent_count + stats.good_count + stats.acceptable_count
        parts.append(f"{kept} frames kept, {stats.rejected_count} rejected.")

        if stats.frame_count > 0:
            parts.append(f"Rejection rate: {stats.rejection_rate:.1f}%.")

        # FWHM stats
        if stats.fwhm_values:
            parts.append(f"Average FWHM: {stats.average_fwhm:.1f} pixels.")
            parts.append(f"Best: {stats.best_fwhm:.1f}, worst: {stats.worst_fwhm:.1f}.")
            parts.append(f"Focus trend: {stats.fwhm_trend}.")

        # Recommendation
        rec = self.get_focus_recommendation()
        if rec:
            parts.append(rec)

        return " ".join(parts)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def create_star_measurement(
    x: float,
    y: float,
    fwhm: float,
    peak: float,
    flux: float,
    background: float = 0.0,
    elongation: float = 1.0,
    angle: float = 0.0,
    saturation_level: float = 65000.0,
) -> StarMeasurement:
    """
    Create a StarMeasurement with calculated values.

    Args:
        x, y: Centroid position
        fwhm: Measured FWHM in pixels
        peak: Peak pixel value
        flux: Total flux
        background: Background level for SNR calculation
        elongation: Star elongation ratio
        angle: Elongation angle in degrees
        saturation_level: ADU level considered saturated

    Returns:
        StarMeasurement object
    """
    # Calculate HFD (approximately 1.18 * FWHM for Gaussian)
    hfd = fwhm * 1.18

    # Calculate SNR
    noise = math.sqrt(background) if background > 0 else 1.0
    snr = (peak - background) / noise if noise > 0 else 0.0

    return StarMeasurement(
        x=x,
        y=y,
        fwhm=fwhm,
        hfd=hfd,
        peak=peak,
        flux=flux,
        snr=snr,
        elongation=elongation,
        angle=angle,
        saturated=peak >= saturation_level,
    )


# =============================================================================
# MAIN (for testing)
# =============================================================================


if __name__ == "__main__":
    print("NIGHTWATCH Frame Analyzer Test\n")

    # Create analyzer
    analyzer = FrameAnalyzer(pixel_scale=1.5)  # 1.5"/pixel
    analyzer.start_session("test_session")

    # Simulate analyzing several frames
    print("Simulating frame analysis:\n")

    test_frames = [
        # (fwhm, elongation, star_count, snr, description)
        (2.5, 1.05, 50, 40, "Excellent frame"),
        (3.2, 1.10, 45, 35, "Good frame"),
        (4.5, 1.25, 30, 25, "Acceptable frame"),
        (6.0, 1.40, 15, 15, "Marginal frame"),
        (9.0, 1.60, 5, 8, "Bad frame - trailing"),
    ]

    for i, (fwhm, elong, count, snr, desc) in enumerate(test_frames):
        # Create simulated stars
        stars = []
        for j in range(count):
            stars.append(create_star_measurement(
                x=100 + j * 50,
                y=100 + j * 30,
                fwhm=fwhm + (j % 3) * 0.2,  # Slight variation
                peak=30000 - j * 100,
                flux=50000 - j * 200,
                background=500,
                elongation=elong,
                angle=45 if elong > 1.1 else 0,
            ))

        metrics = analyzer.analyze_frame(
            stars=stars,
            frame_id=f"frame_{i+1:04d}",
            exposure_sec=120.0,
            background_mean=500,
            background_stddev=25,
        )

        print(f"Frame {i+1}: {desc}")
        print(f"  FWHM: {metrics.median_fwhm:.1f} px ({metrics.fwhm_arcsec:.1f}\")")
        print(f"  Stars: {metrics.star_count}, Elongation: {metrics.median_elongation:.2f}")
        print(f"  Quality: {metrics.quality.value} (score: {metrics.quality_score:.2f})")
        print(f"  {metrics.recommendation}")
        print()

    # Session summary
    print("\n" + "=" * 50)
    print(analyzer.format_session_summary())

    # Focus recommendation
    rec = analyzer.get_focus_recommendation()
    if rec:
        print(f"\nRecommendation: {rec}")
