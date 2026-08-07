"""
NIGHTWATCH Scan Severity Classification Tests
presa-nightwatch. velmu-test-severity.

Tests event severity classification, zone mapping, and space weather models.
"""

import pytest
from datetime import datetime, timezone

from services.meteor_tracking.fireball_client import Fireball
from services.meteor_tracking.scan_severity import (
    EventSeverity,
    ScanCircleZone,
    SpaceWeatherConditions,
    classify_zone_by_distance,
    classify_fireball_severity,
    classify_neo_severity,
    distance_from_home,
    ZONE_BOUNDARIES,
)


# ============================================================================
# EventSeverity Tests
# ============================================================================


class TestEventSeverity:
    """Test severity enum ordering."""

    def test_severity_values(self):
        assert EventSeverity.INFO.value == "info"
        assert EventSeverity.NOTABLE.value == "notable"
        assert EventSeverity.SIGNIFICANT.value == "significant"
        assert EventSeverity.CRITICAL.value == "critical"

    def test_all_four_levels(self):
        assert len(EventSeverity) == 4


# ============================================================================
# Zone Classification Tests
# ============================================================================


class TestZoneClassification:
    """Test distance-to-zone mapping."""

    def test_home_base(self):
        assert classify_zone_by_distance(0) == ScanCircleZone.HOME_BASE

    def test_inner(self):
        assert classify_zone_by_distance(5) == ScanCircleZone.INNER
        assert classify_zone_by_distance(20) == ScanCircleZone.INNER

    def test_middle(self):
        assert classify_zone_by_distance(50) == ScanCircleZone.MIDDLE
        assert classify_zone_by_distance(80) == ScanCircleZone.MIDDLE

    def test_outer(self):
        assert classify_zone_by_distance(100) == ScanCircleZone.OUTER
        assert classify_zone_by_distance(200) == ScanCircleZone.OUTER

    def test_extended(self):
        assert classify_zone_by_distance(300) == ScanCircleZone.HOME_BASES_EXTENDED
        assert classify_zone_by_distance(500) == ScanCircleZone.HOME_BASES_EXTENDED

    def test_new_days(self):
        assert classify_zone_by_distance(501) == ScanCircleZone.NEW_DAYS
        assert classify_zone_by_distance(5000) == ScanCircleZone.NEW_DAYS

    def test_boundaries_are_monotonic(self):
        """Zone boundaries should be monotonically increasing."""
        boundaries = list(ZONE_BOUNDARIES.values())
        for i in range(1, len(boundaries) - 1):
            assert boundaries[i] > boundaries[i - 1]


# ============================================================================
# Fireball Severity Tests
# ============================================================================


class TestFireballSeverity:
    """Test fireball severity classification."""

    def _make_fireball(self, **kwargs) -> Fireball:
        defaults = dict(
            date=datetime(2026, 3, 23, 3, 19),
            latitude=39.0, longitude=-117.0,
            altitude_km=50.0, velocity_km_s=20.0,
            total_radiated_energy_j=None,
            calculated_total_impact_energy_kt=None,
        )
        defaults.update(kwargs)
        return Fireball(**defaults)

    def test_very_bright_is_critical(self):
        """Magnitude < -15 is CRITICAL."""
        fb = self._make_fireball(total_radiated_energy_j=1e14)
        severity = classify_fireball_severity(fb)
        assert severity == EventSeverity.CRITICAL

    def test_bright_is_significant(self):
        """Magnitude between -15 and -8 is SIGNIFICANT."""
        # Use 5e11 J which gives magnitude around -13.7
        fb = self._make_fireball(total_radiated_energy_j=5e11)
        mag = fb.magnitude_estimate
        assert mag is not None
        assert -15 < mag < -8
        severity = classify_fireball_severity(fb)
        assert severity == EventSeverity.SIGNIFICANT

    def test_nearby_no_energy_is_notable(self):
        """Fireball within 200mi with unknown energy is NOTABLE."""
        fb = self._make_fireball(
            latitude=38.95, longitude=-117.35,
            total_radiated_energy_j=None,
        )
        severity = classify_fireball_severity(fb)
        assert severity == EventSeverity.NOTABLE

    def test_distant_dim_is_info(self):
        """Distant, dim fireball is INFO."""
        fb = self._make_fireball(
            latitude=50.0, longitude=7.5,
            total_radiated_energy_j=None,
        )
        severity = classify_fireball_severity(fb)
        assert severity == EventSeverity.INFO

    def test_no_coordinates_no_energy_is_info(self):
        """Fireball with no data defaults to INFO."""
        fb = self._make_fireball(
            latitude=None, longitude=None,
            total_radiated_energy_j=None,
        )
        severity = classify_fireball_severity(fb)
        assert severity == EventSeverity.INFO


# ============================================================================
# NEO Severity Tests
# ============================================================================


class TestNEOSeverity:
    """Test near-Earth object severity classification."""

    def test_very_close_is_critical(self):
        assert classify_neo_severity(0.002) == EventSeverity.CRITICAL

    def test_close_large_is_significant(self):
        assert classify_neo_severity(0.005, diameter_m=100) == EventSeverity.SIGNIFICANT

    def test_close_small_is_notable(self):
        assert classify_neo_severity(0.005, diameter_m=10) == EventSeverity.NOTABLE

    def test_distant_is_info(self):
        assert classify_neo_severity(0.05, diameter_m=500) == EventSeverity.INFO

    def test_at_threshold(self):
        """Test behavior exactly at thresholds."""
        # At very_close boundary (uses strict <, so 0.003 is NOT critical)
        assert classify_neo_severity(0.003) == EventSeverity.NOTABLE
        # Just below very_close boundary IS critical
        assert classify_neo_severity(0.0029) == EventSeverity.CRITICAL
        # At close boundary (uses strict <, so 0.01 is INFO)
        assert classify_neo_severity(0.01) == EventSeverity.INFO
        # Just below close boundary, no diameter -> NOTABLE
        assert classify_neo_severity(0.009) == EventSeverity.NOTABLE


# ============================================================================
# Space Weather Tests
# ============================================================================


class TestSpaceWeatherConditions:
    """Test space weather data model and severity."""

    def test_quiet_conditions(self):
        sw = SpaceWeatherConditions()
        assert sw.severity == EventSeverity.INFO
        assert not sw.aurora_possible
        assert not sw.cme_watch

    def test_g1_storm(self):
        sw = SpaceWeatherConditions(storm_level="G1-Minor")
        assert sw.severity == EventSeverity.INFO

    def test_g2_storm(self):
        sw = SpaceWeatherConditions(
            storm_level="G2-Moderate", kp_index=6.0, aurora_possible=True,
        )
        assert sw.severity == EventSeverity.NOTABLE

    def test_g3_storm(self):
        sw = SpaceWeatherConditions(storm_level="G3-Strong")
        assert sw.severity == EventSeverity.SIGNIFICANT

    def test_g4_storm(self):
        sw = SpaceWeatherConditions(storm_level="G4-Severe")
        assert sw.severity == EventSeverity.SIGNIFICANT

    def test_g5_storm(self):
        sw = SpaceWeatherConditions(storm_level="G5-Extreme")
        assert sw.severity == EventSeverity.CRITICAL

    def test_lexicon_lines_empty(self):
        sw = SpaceWeatherConditions()
        lines = sw.to_lexicon_lines()
        assert lines[0] == "sky-conditions:"
        assert len(lines) == 1  # Only header, no data

    def test_lexicon_lines_full(self):
        sw = SpaceWeatherConditions(
            kp_index=6.0,
            storm_level="G2-Moderate",
            solar_flare_class="M2.7",
            solar_flare_region="4392",
            aurora_possible=True,
            cme_watch=True,
            radio_blackout_level="R1-Minor",
        )
        lines = sw.to_lexicon_lines()
        joined = "\n".join(lines)
        assert "G2-Moderate" in joined
        assert "M2.7" in joined
        assert "4392" in joined
        assert "aurora: possible-at-horizon" in joined
        assert "kp-index: 6.0" in joined
        assert "cme-watch: active" in joined
        assert "R1-Minor" in joined


# ============================================================================
# Distance Calculation Tests
# ============================================================================


class TestDistanceFromHome:
    """Test distance calculations from Nevada home base."""

    def test_home_is_zero(self):
        dist = distance_from_home(38.9, -117.4)
        assert dist < 0.1

    def test_chowchilla_ca(self):
        """Chowchilla, CA — ~210 mi from Nevada site."""
        dist = distance_from_home(37.1, -120.2)
        assert 150 < dist < 250

    def test_koblenz_germany(self):
        """Koblenz — trans-Atlantic distance."""
        dist = distance_from_home(50.3, 7.5)
        assert dist > 5000

    def test_pittsburgh_area(self):
        """Pittsburgh / Lake Erie — ~2000 mi."""
        dist = distance_from_home(41.5, -81.5)
        assert 1800 < dist < 2200

    def test_las_vegas(self):
        """Las Vegas — ~200 mi from Nevada site."""
        dist = distance_from_home(36.17, -115.14)
        assert 150 < dist < 250

    def test_custom_home(self):
        """Test with custom home base coordinates."""
        dist = distance_from_home(39.0, -117.0, home_lat=39.0, home_lon=-117.0)
        assert dist < 0.1


# ============================================================================
# Real-world Event Simulation
# ============================================================================


class TestMarch2026Events:
    """Simulate real March 2026 events through severity classification."""

    def test_koblenz_meteorite(self):
        """2026 Koblenz meteor — mag -15 to -20, confirmed meteorite."""
        fb = Fireball(
            date=datetime(2026, 3, 8, 17, 55),
            latitude=50.34, longitude=7.55,
            altitude_km=50.0, velocity_km_s=20.0,
            total_radiated_energy_j=1e14,
            calculated_total_impact_energy_kt=0.5,
        )
        severity = classify_fireball_severity(fb)
        assert severity == EventSeverity.CRITICAL

        zone = classify_zone_by_distance(distance_from_home(50.34, 7.55))
        assert zone == ScanCircleZone.NEW_DAYS

    def test_pittsburgh_fireball(self):
        """2026-03-17 Pittsburgh fireball — sonic boom, 222 AMS reports."""
        fb = Fireball(
            date=datetime(2026, 3, 17, 12, 57),
            latitude=41.5, longitude=-81.5,
            altitude_km=80.0, velocity_km_s=17.9,
            total_radiated_energy_j=1e12,
            calculated_total_impact_energy_kt=0.05,
        )
        severity = classify_fireball_severity(fb)
        assert severity in (EventSeverity.SIGNIFICANT, EventSeverity.CRITICAL)

        zone = classify_zone_by_distance(distance_from_home(41.5, -81.5))
        assert zone == ScanCircleZone.NEW_DAYS

    def test_california_fireball(self):
        """2026-03-23 California fireball — bright green, 239 AMS reports."""
        fb = Fireball(
            date=datetime(2026, 3, 23, 3, 19),
            latitude=37.1, longitude=-120.2,
            altitude_km=79.0, velocity_km_s=15.6,
            total_radiated_energy_j=5e11,
            calculated_total_impact_energy_kt=0.005,
        )
        severity = classify_fireball_severity(fb)
        # Energy of 5e11 gives magnitude ~-15
        assert severity in (EventSeverity.SIGNIFICANT, EventSeverity.CRITICAL)

        dist = distance_from_home(37.1, -120.2)
        zone = classify_zone_by_distance(dist)
        assert zone in (ScanCircleZone.OUTER, ScanCircleZone.HOME_BASES_EXTENDED)

    def test_g2_geomagnetic_storm(self):
        """G2 storm from March 19 CME arrival."""
        sw = SpaceWeatherConditions(
            kp_index=6.0,
            storm_level="G2-Moderate",
            solar_flare_class="M2.7",
            solar_flare_region="4392",
            aurora_possible=True,
            cme_watch=True,
        )
        assert sw.severity == EventSeverity.NOTABLE

    def test_asteroid_2026_eg1(self):
        """2026 EG1 — 40ft, 198K mi (closer than Moon)."""
        # 198K mi = ~318K km = ~0.00213 AU
        severity = classify_neo_severity(0.00213, diameter_m=12.0)
        assert severity == EventSeverity.CRITICAL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
