"""
NIGHTWATCH Space Weather Client Tests
Tests for geomagnetic storm awareness and aurora detection.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from services.meteor_tracking.space_weather import (
    GeomagneticLevel,
    KpReading,
    SolarWindReading,
    SpaceWeatherSummary,
    SpaceWeatherClient,
)


class TestGeomagneticLevel:
    """Test NOAA geomagnetic storm scale."""

    def test_from_kp_quiet(self):
        """Test quiet conditions (Kp 0-3)."""
        assert GeomagneticLevel.from_kp(0) == GeomagneticLevel.QUIET
        assert GeomagneticLevel.from_kp(2) == GeomagneticLevel.QUIET
        assert GeomagneticLevel.from_kp(3) == GeomagneticLevel.QUIET

    def test_from_kp_unsettled(self):
        """Test unsettled conditions (Kp 4)."""
        assert GeomagneticLevel.from_kp(4) == GeomagneticLevel.UNSETTLED
        assert GeomagneticLevel.from_kp(4.5) == GeomagneticLevel.UNSETTLED

    def test_from_kp_g1(self):
        """Test G1 Minor storm (Kp 5)."""
        assert GeomagneticLevel.from_kp(5) == GeomagneticLevel.G1_MINOR
        assert GeomagneticLevel.from_kp(5.5) == GeomagneticLevel.G1_MINOR

    def test_from_kp_g2(self):
        """Test G2 Moderate storm (Kp 6)."""
        assert GeomagneticLevel.from_kp(6) == GeomagneticLevel.G2_MODERATE

    def test_from_kp_g3(self):
        """Test G3 Strong storm (Kp 7)."""
        assert GeomagneticLevel.from_kp(7) == GeomagneticLevel.G3_STRONG

    def test_from_kp_g4(self):
        """Test G4 Severe storm (Kp 8)."""
        assert GeomagneticLevel.from_kp(8) == GeomagneticLevel.G4_SEVERE

    def test_from_kp_g5(self):
        """Test G5 Extreme storm (Kp 9)."""
        assert GeomagneticLevel.from_kp(9) == GeomagneticLevel.G5_EXTREME

    def test_label(self):
        """Test human-readable labels."""
        assert "Quiet" in GeomagneticLevel.QUIET.label
        assert "Minor" in GeomagneticLevel.G1_MINOR.label
        assert "Strong" in GeomagneticLevel.G3_STRONG.label
        assert "Extreme" in GeomagneticLevel.G5_EXTREME.label

    def test_affects_tracking(self):
        """Test tracking impact thresholds."""
        assert not GeomagneticLevel.QUIET.affects_tracking
        assert not GeomagneticLevel.G1_MINOR.affects_tracking
        assert GeomagneticLevel.G2_MODERATE.affects_tracking
        assert GeomagneticLevel.G3_STRONG.affects_tracking
        assert GeomagneticLevel.G5_EXTREME.affects_tracking

    def test_aurora_latitude(self):
        """Test aurora visibility latitude thresholds."""
        # Higher storms -> lower latitude aurora
        quiet_lat = GeomagneticLevel.QUIET.aurora_visible_at_latitude
        g3_lat = GeomagneticLevel.G3_STRONG.aurora_visible_at_latitude
        g5_lat = GeomagneticLevel.G5_EXTREME.aurora_visible_at_latitude

        assert quiet_lat > g3_lat  # Quiet needs higher latitude
        assert g3_lat > g5_lat  # Extreme visible at lower latitude
        assert g5_lat <= 40.0  # G5 visible from mid-latitudes


class TestKpReading:
    """Test Kp index reading."""

    def test_level_property(self):
        """Test that level is derived from Kp value."""
        reading = KpReading(
            timestamp=datetime.utcnow(),
            kp=7.0,
            observed=True,
        )
        assert reading.level == GeomagneticLevel.G3_STRONG

    def test_observed_flag(self):
        """Test observed vs predicted distinction."""
        observed = KpReading(datetime.utcnow(), 3.0, True)
        predicted = KpReading(datetime.utcnow(), 3.0, False)
        assert observed.observed
        assert not predicted.observed


class TestSolarWindReading:
    """Test solar wind data."""

    def test_geoeffective_conditions(self):
        """Test geoeffective solar wind detection."""
        # Strong southward Bz + fast wind = geoeffective
        reading = SolarWindReading(
            timestamp=datetime.utcnow(),
            speed_km_s=600,
            density_p_cm3=10,
            bz_nt=-15,
            bt_nt=20,
        )
        assert reading.is_geoeffective

    def test_not_geoeffective_northward_bz(self):
        """Test non-geoeffective with northward Bz."""
        reading = SolarWindReading(
            timestamp=datetime.utcnow(),
            speed_km_s=600,
            density_p_cm3=10,
            bz_nt=5,  # Northward = not geoeffective
            bt_nt=10,
        )
        assert not reading.is_geoeffective

    def test_not_geoeffective_slow_wind(self):
        """Test non-geoeffective with slow solar wind."""
        reading = SolarWindReading(
            timestamp=datetime.utcnow(),
            speed_km_s=300,  # Slow wind
            density_p_cm3=5,
            bz_nt=-10,
            bt_nt=15,
        )
        assert not reading.is_geoeffective

    def test_coupling_strength_extreme(self):
        """Test extreme coupling conditions."""
        reading = SolarWindReading(
            timestamp=datetime.utcnow(),
            speed_km_s=700,
            density_p_cm3=20,
            bz_nt=-25,
            bt_nt=30,
        )
        assert reading.coupling_strength == "extreme"

    def test_coupling_strength_strong(self):
        """Test strong coupling conditions."""
        reading = SolarWindReading(
            timestamp=datetime.utcnow(),
            speed_km_s=550,
            density_p_cm3=10,
            bz_nt=-12,
            bt_nt=18,
        )
        assert reading.coupling_strength == "strong"

    def test_coupling_strength_none(self):
        """Test no coupling (northward Bz)."""
        reading = SolarWindReading(
            timestamp=datetime.utcnow(),
            speed_km_s=400,
            density_p_cm3=5,
            bz_nt=5,
            bt_nt=8,
        )
        assert reading.coupling_strength == "none"


class TestSpaceWeatherSummary:
    """Test space weather summary."""

    def _make_summary(self, kp=3.0, **kwargs):
        """Helper to create summary with defaults."""
        summary = SpaceWeatherSummary(
            timestamp=datetime.utcnow(),
            current_kp=KpReading(datetime.utcnow(), kp, True),
            geomagnetic_level=GeomagneticLevel.from_kp(kp),
            **kwargs,
        )
        return summary

    def test_observation_impact_none(self):
        """Test no impact during quiet conditions."""
        summary = self._make_summary(kp=2.0)
        assert "NONE" in summary.observation_impact

    def test_observation_impact_minor(self):
        """Test minor impact during G1."""
        summary = self._make_summary(kp=5.0)
        assert "MINOR" in summary.observation_impact

    def test_observation_impact_significant(self):
        """Test significant impact during G3."""
        summary = self._make_summary(kp=7.0)
        assert "SIGNIFICANT" in summary.observation_impact

    def test_observation_impact_severe(self):
        """Test severe impact during G4+."""
        summary = self._make_summary(kp=8.0)
        assert "SEVERE" in summary.observation_impact

    def test_to_lexicon_quiet(self):
        """Test Lexicon output for quiet conditions."""
        summary = self._make_summary(kp=2.0)
        lexicon = summary.to_lexicon()

        assert "nightwatch-space-weather." in lexicon
        assert "varek:" in lexicon
        assert "kp-index:" in lexicon
        assert "sky-quiet." in lexicon

    def test_to_lexicon_storm(self):
        """Test Lexicon output for storm conditions."""
        summary = self._make_summary(
            kp=7.0,
            aurora_possible_at_site=True,
            tracking_affected=True,
            alerts=["G3 Strong Storm Watch"],
        )
        lexicon = summary.to_lexicon()

        assert "nightwatch-space-weather." in lexicon
        assert "aurora-possible: yes-at-site" in lexicon
        assert "tracking-warning:" in lexicon
        assert "presa-storm." in lexicon

    def test_to_lexicon_with_solar_wind(self):
        """Test Lexicon output includes solar wind data."""
        summary = self._make_summary(kp=5.0)
        summary.solar_wind = SolarWindReading(
            timestamp=datetime.utcnow(),
            speed_km_s=550,
            density_p_cm3=10,
            bz_nt=-8,
            bt_nt=12,
        )
        lexicon = summary.to_lexicon()

        assert "solar-wind:" in lexicon
        assert "imf-bz:" in lexicon


class TestSpaceWeatherClientParsing:
    """Test SWPC data parsing methods."""

    def test_parse_kp_data_valid(self):
        """Test parsing Kp index JSON data."""
        client = SpaceWeatherClient()
        data = [
            ["time_tag", "Kp", "a_running", "station_count"],
            ["2026-03-21 00:00:00.000", "3.33", "15", "8"],
            ["2026-03-21 03:00:00.000", "7.00", "132", "8"],
        ]

        readings = client._parse_kp_data(data)
        assert len(readings) == 2
        assert readings[0].kp == 3.33
        assert readings[0].observed
        assert readings[1].kp == 7.0

    def test_parse_kp_data_empty(self):
        """Test parsing empty Kp data."""
        client = SpaceWeatherClient()
        assert client._parse_kp_data([]) == []
        assert client._parse_kp_data(None) == []

    def test_parse_kp_data_header_only(self):
        """Test parsing Kp data with only header."""
        client = SpaceWeatherClient()
        data = [["time_tag", "Kp"]]
        assert client._parse_kp_data(data) == []

    def test_parse_solar_wind_valid(self):
        """Test parsing solar wind plasma and mag data."""
        client = SpaceWeatherClient()

        plasma_data = [
            ["time_tag", "density", "speed", "temperature"],
            ["2026-03-21 00:00:00.000", "5.2", "450", "120000"],
        ]

        mag_data = [
            ["time_tag", "bx_gsm", "by_gsm", "bz_gsm", "lon_gsm",
             "lat_gsm", "bt"],
            ["2026-03-21 00:00:00.000", "2.1", "-3.5", "-8.2",
             "135", "12", "9.5"],
        ]

        result = client._parse_solar_wind(plasma_data, mag_data)
        assert result is not None
        assert result.speed_km_s == 450
        assert result.density_p_cm3 == 5.2
        assert result.bz_nt == -8.2
        assert result.bt_nt == 9.5

    def test_parse_solar_wind_missing_data(self):
        """Test parsing solar wind with missing values."""
        client = SpaceWeatherClient()
        result = client._parse_solar_wind(None, None)
        assert result is not None  # Should return defaults
        assert result.speed_km_s == 400.0  # Default

    def test_parse_alerts_valid(self):
        """Test parsing SWPC alert messages (real SWPC format uses uppercase keywords)."""
        client = SpaceWeatherClient()
        data = [
            {
                "product_id": "alert-1",
                "issue_datetime": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),
                "message": "Space Weather WARNING\nGeomagnetic Storm Warning issued\nKp expected 7",
            }
        ]

        alerts = client._parse_alerts(data)
        assert len(alerts) >= 1

    def test_parse_alerts_empty(self):
        """Test parsing empty alerts."""
        client = SpaceWeatherClient()
        assert client._parse_alerts([]) == []
        assert client._parse_alerts({}) == []


class TestSpaceWeatherIntegration:
    """Integration tests for space weather flow."""

    def test_g3_storm_march_2026_scenario(self):
        """
        Test the actual March 21, 2026 G3 storm scenario.
        Validates that the system correctly identifies impacts.
        """
        # Simulate G3 storm conditions from actual event
        summary = SpaceWeatherSummary(
            timestamp=datetime(2026, 3, 21, 2, 0),
            current_kp=KpReading(
                timestamp=datetime(2026, 3, 21, 1, 54),
                kp=7.0,
                observed=True,
            ),
            solar_wind=SolarWindReading(
                timestamp=datetime(2026, 3, 21, 1, 54),
                speed_km_s=550,
                density_p_cm3=12,
                bz_nt=-15,
                bt_nt=20,
            ),
            geomagnetic_level=GeomagneticLevel.G3_STRONG,
            aurora_possible_at_site=True,  # Nevada at 38.9N, G3 aurora to ~50N
            tracking_affected=True,
            alerts=["G3 Strong Geomagnetic Storm Alert"],
        )

        # Verify impacts
        assert summary.tracking_affected
        assert summary.aurora_possible_at_site
        assert "SIGNIFICANT" in summary.observation_impact
        assert summary.solar_wind.is_geoeffective
        assert summary.solar_wind.coupling_strength == "strong"

        # Verify Lexicon output
        lexicon = summary.to_lexicon()
        assert "presa-storm." in lexicon
        assert "aurora-possible" in lexicon
        assert "tracking-warning" in lexicon

    def test_equinox_coupling_awareness(self):
        """
        Test that system handles equinox-enhanced coupling.
        The Russell-McPherron effect makes equinoxes more susceptible
        to geomagnetic activity.
        """
        # During equinox, southward Bz with fast solar wind = strong coupling
        wind = SolarWindReading(
            timestamp=datetime(2026, 3, 20, 14, 46),  # Equinox
            speed_km_s=550,
            density_p_cm3=8,
            bz_nt=-12,
            bt_nt=15,
        )

        assert wind.is_geoeffective
        assert wind.coupling_strength == "strong"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
