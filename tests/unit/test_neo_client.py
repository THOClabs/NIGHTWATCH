"""
NIGHTWATCH Close Approach Data Client Tests
presa-nightwatch. velmu-sky. watching-what-approaches.

Tests for the NASA JPL CAD API client that tracks asteroid/comet
close approaches to Earth.
"""

import pytest
import math
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from services.meteor_tracking.close_approach_client import (
    CloseApproach,
    CADClient,
    ThreatLevel,
    estimate_diameter_from_h,
    generate_approach_prayer,
    fetch_upcoming_approaches,
)


# =========================================================================
# Test data fixtures
# =========================================================================

def make_approach(**overrides) -> CloseApproach:
    """Factory for CloseApproach test objects."""
    defaults = dict(
        designation="2026 EG1",
        close_approach_date=datetime(2026, 3, 12, 9, 15),
        distance_au=0.00133,
        distance_ld=0.518,
        distance_km=198_925.0,
        relative_velocity_km_s=9.62,
        absolute_magnitude_h=27.5,
        estimated_diameter_m_min=5.3,
        estimated_diameter_m_max=11.8,
        is_potentially_hazardous=False,
        orbit_id="23",
        fullname="(2026 EG1)",
    )
    defaults.update(overrides)
    return CloseApproach(**defaults)


# Sample API response matching JPL CAD format
SAMPLE_API_RESPONSE = {
    "signature": {"version": "1.5", "source": "NASA/JPL SBDB Close Approach Data API"},
    "count": "3",
    "fields": ["des", "orbit_id", "jd", "cd", "dist", "dist_min", "dist_max",
               "v_rel", "v_inf", "t_sigma_f", "h", "diameter", "diameter_sigma",
               "fullname"],
    "data": [
        ["2026 EG1", "23", "2460747.885", "2026-Mar-12 09:15", "0.00133",
         "0.00125", "0.00140", "9.62", "9.50", "00:03", "27.5", None, None,
         "   (2026 EG1)"],
        ["2026 FU", "15", "2460758.321", "2026-Mar-22 19:42", "0.00987",
         "0.00950", "0.01020", "12.44", "12.30", "00:08", "24.1", None, None,
         "   (2026 FU)"],
        ["2026 FK", "8", "2460758.654", "2026-Mar-22 03:41", "0.01234",
         "0.01200", "0.01280", "8.75", "8.60", "00:12", "25.8", None, None,
         "   (2026 FK)"],
    ],
}

EMPTY_API_RESPONSE = {
    "signature": {"version": "1.5", "source": "NASA/JPL"},
    "count": "0",
    "fields": ["des", "orbit_id", "jd", "cd", "dist", "dist_min", "dist_max",
               "v_rel", "v_inf", "t_sigma_f", "h", "diameter", "diameter_sigma",
               "fullname"],
    "data": [],
}


# =========================================================================
# CloseApproach dataclass tests
# =========================================================================

class TestCloseApproach:
    """Test CloseApproach dataclass properties."""

    def test_threat_level_alert_close_distance(self):
        """< 1 LD = ALERT."""
        ca = make_approach(distance_ld=0.5, is_potentially_hazardous=False)
        assert ca.threat_level == ThreatLevel.ALERT

    def test_threat_level_alert_pha(self):
        """PHA flag = ALERT regardless of distance."""
        ca = make_approach(distance_ld=5.0, is_potentially_hazardous=True)
        assert ca.threat_level == ThreatLevel.ALERT

    def test_threat_level_watch(self):
        """< 2 LD = WATCH."""
        ca = make_approach(distance_ld=1.5, is_potentially_hazardous=False)
        assert ca.threat_level == ThreatLevel.WATCH

    def test_threat_level_significant(self):
        """< 5 LD + detectable size = SIGNIFICANT."""
        ca = make_approach(
            distance_ld=3.0,
            is_potentially_hazardous=False,
            estimated_diameter_m_max=20.0,
        )
        assert ca.threat_level == ThreatLevel.SIGNIFICANT

    def test_threat_level_notable_distance(self):
        """< 10 LD = NOTABLE."""
        ca = make_approach(
            distance_ld=7.0,
            is_potentially_hazardous=False,
            estimated_diameter_m_max=5.0,
        )
        assert ca.threat_level == ThreatLevel.NOTABLE

    def test_threat_level_notable_large(self):
        """Large object (> 50m) = NOTABLE even at distance."""
        ca = make_approach(
            distance_ld=15.0,
            is_potentially_hazardous=False,
            estimated_diameter_m_max=60.0,
        )
        assert ca.threat_level == ThreatLevel.NOTABLE

    def test_threat_level_routine(self):
        """> 10 LD + small = ROUTINE."""
        ca = make_approach(
            distance_ld=25.0,
            is_potentially_hazardous=False,
            estimated_diameter_m_max=5.0,
        )
        assert ca.threat_level == ThreatLevel.ROUTINE

    def test_estimated_diameter_str_meters(self):
        ca = make_approach(estimated_diameter_m_min=5.3, estimated_diameter_m_max=11.8)
        assert "5-12 m" in ca.estimated_diameter_str or "5" in ca.estimated_diameter_str

    def test_estimated_diameter_str_cm(self):
        ca = make_approach(estimated_diameter_m_min=0.01, estimated_diameter_m_max=0.05)
        assert "cm" in ca.estimated_diameter_str

    def test_estimated_diameter_str_km(self):
        ca = make_approach(estimated_diameter_m_min=1200, estimated_diameter_m_max=2500)
        assert "km" in ca.estimated_diameter_str

    def test_estimated_diameter_str_unknown(self):
        ca = make_approach(estimated_diameter_m_min=None, estimated_diameter_m_max=None)
        assert ca.estimated_diameter_str == "unknown"

    def test_approach_id_format(self):
        ca = make_approach(
            designation="2026 EG1",
            close_approach_date=datetime(2026, 3, 12),
        )
        assert ca.approach_id == "cad_2026_EG1_20260312"

    def test_approach_id_uniqueness(self):
        ca1 = make_approach(designation="2026 EG1")
        ca2 = make_approach(designation="2026 FU")
        assert ca1.approach_id != ca2.approach_id

    def test_lexicon_str(self):
        ca = make_approach()
        s = ca.lexicon_str
        assert "2026 EG1" in s
        assert "LD" in s
        assert "km/s" in s

    def test_hours_until_approach_future(self):
        future = datetime.utcnow() + timedelta(hours=5)
        ca = make_approach(close_approach_date=future)
        hours = ca.hours_until_approach()
        assert 4.9 < hours < 5.1

    def test_hours_until_approach_past(self):
        past = datetime.utcnow() - timedelta(hours=3)
        ca = make_approach(close_approach_date=past)
        hours = ca.hours_until_approach()
        assert -3.1 < hours < -2.9


# =========================================================================
# Diameter estimation tests
# =========================================================================

class TestDiameterEstimation:
    """Test the H magnitude to diameter conversion."""

    def test_estimate_large_asteroid(self):
        """H=17 should give ~1-3 km diameter."""
        d_min, d_max = estimate_diameter_from_h(17.0)
        assert d_min > 500   # > 500m
        assert d_max < 5000  # < 5km

    def test_estimate_medium_asteroid(self):
        """H=22 should give ~100-200m range."""
        d_min, d_max = estimate_diameter_from_h(22.0)
        assert d_min > 50
        assert d_max < 500

    def test_estimate_small_asteroid(self):
        """H=27 should give ~5-15m range."""
        d_min, d_max = estimate_diameter_from_h(27.0)
        assert d_min > 1
        assert d_max < 50

    def test_estimate_tiny_asteroid(self):
        """H=30 should give very small (< 5m)."""
        d_min, d_max = estimate_diameter_from_h(30.0)
        assert d_max < 10

    def test_dark_gives_larger_diameter(self):
        """Lower albedo (dark) should estimate larger diameter."""
        d_min, d_max = estimate_diameter_from_h(25.0)
        assert d_max > d_min  # d_max uses dark albedo

    def test_consistent_with_apophis(self):
        """
        Cross-check: Apophis (H=19.7) is ~370m.
        Our estimate range should bracket that.
        """
        d_min, d_max = estimate_diameter_from_h(19.7)
        assert d_min < 370
        assert d_max > 370


# =========================================================================
# CADClient parsing tests
# =========================================================================

class TestCADClientParsing:
    """Test API response parsing (no network calls)."""

    def test_parse_sample_response(self):
        client = CADClient()
        approaches = client._parse_approaches(SAMPLE_API_RESPONSE)
        assert len(approaches) == 3
        assert approaches[0].designation == "2026 EG1"
        assert approaches[1].designation == "2026 FU"
        assert approaches[2].designation == "2026 FK"

    def test_parse_distances(self):
        client = CADClient()
        approaches = client._parse_approaches(SAMPLE_API_RESPONSE)
        eg1 = approaches[0]
        assert eg1.distance_au == 0.00133
        # distance_ld should be derived from AU
        assert eg1.distance_ld > 0
        # distance_km should be derived from AU
        expected_km = 0.00133 * CADClient.AU_TO_KM
        assert abs(eg1.distance_km - expected_km) < 1.0

    def test_parse_velocity(self):
        client = CADClient()
        approaches = client._parse_approaches(SAMPLE_API_RESPONSE)
        assert approaches[0].relative_velocity_km_s == 9.62

    def test_parse_h_magnitude(self):
        client = CADClient()
        approaches = client._parse_approaches(SAMPLE_API_RESPONSE)
        assert approaches[0].absolute_magnitude_h == 27.5
        assert approaches[1].absolute_magnitude_h == 24.1

    def test_parse_fullname_stripped(self):
        client = CADClient()
        approaches = client._parse_approaches(SAMPLE_API_RESPONSE)
        assert approaches[0].fullname == "(2026 EG1)"

    def test_parse_diameter_estimation(self):
        client = CADClient()
        approaches = client._parse_approaches(SAMPLE_API_RESPONSE)
        eg1 = approaches[0]
        assert eg1.estimated_diameter_m_min is not None
        assert eg1.estimated_diameter_m_max is not None
        assert eg1.estimated_diameter_m_min < eg1.estimated_diameter_m_max

    def test_parse_date_format(self):
        client = CADClient()
        approaches = client._parse_approaches(SAMPLE_API_RESPONSE)
        eg1 = approaches[0]
        assert eg1.close_approach_date.year == 2026
        assert eg1.close_approach_date.month == 3
        assert eg1.close_approach_date.day == 12

    def test_parse_empty_response(self):
        client = CADClient()
        assert client._parse_approaches(EMPTY_API_RESPONSE) == []

    def test_parse_malformed_response(self):
        client = CADClient()
        assert client._parse_approaches({}) == []
        assert client._parse_approaches({"fields": []}) == []
        assert client._parse_approaches({"data": []}) == []

    def test_parse_row_missing_designation(self):
        """Row missing designation is skipped."""
        client = CADClient()
        bad_response = {
            "fields": ["des", "orbit_id", "cd", "dist", "v_rel", "h", "fullname"],
            "data": [
                ["", "1", "2026-Mar-12 09:15", "0.001", "10.0", "25", "Test"],
                ["2026 YY", "1", "2026-Mar-12 09:15", "0.001", "10.0", "25", "Good"],
            ],
        }
        approaches = client._parse_approaches(bad_response)
        assert len(approaches) == 1
        assert approaches[0].designation == "2026 YY"

    def test_parse_row_missing_distance(self):
        """Row missing distance is skipped."""
        client = CADClient()
        bad_response = {
            "fields": ["des", "orbit_id", "cd", "dist", "v_rel", "h", "fullname"],
            "data": [
                ["2026 XX", "1", "2026-Mar-12 09:15", None, "10.0", "25", "Test"],
                ["2026 YY", "1", "2026-Mar-12 09:15", "0.001", "10.0", "25", "Good"],
            ],
        }
        approaches = client._parse_approaches(bad_response)
        assert len(approaches) == 1
        assert approaches[0].designation == "2026 YY"


# =========================================================================
# Date parsing tests
# =========================================================================

class TestCADDateParsing:
    """Test JPL CAD date format variations."""

    def test_parse_standard_jpl_format(self):
        client = CADClient()
        dt = client._parse_cad_datetime("2026-Mar-23 09:15")
        assert dt.year == 2026
        assert dt.month == 3
        assert dt.day == 23
        assert dt.hour == 9
        assert dt.minute == 15

    def test_parse_numeric_date_format(self):
        client = CADClient()
        dt = client._parse_cad_datetime("2026-03-23 09:15")
        assert dt.month == 3
        assert dt.day == 23

    def test_parse_date_only_jpl(self):
        client = CADClient()
        dt = client._parse_cad_datetime("2026-Mar-23")
        assert dt.month == 3
        assert dt.day == 23

    def test_parse_date_only_numeric(self):
        client = CADClient()
        dt = client._parse_cad_datetime("2026-03-23")
        assert dt.month == 3

    def test_parse_unparseable_date(self):
        """Unparseable date should return current time, not crash."""
        client = CADClient()
        dt = client._parse_cad_datetime("not-a-date")
        assert isinstance(dt, datetime)


# =========================================================================
# Approach prayer formatting tests
# =========================================================================

class TestApproachPrayer:
    """Test Lexicon-style approach prayer formatting."""

    def test_prayer_structure_with_approaches(self):
        approaches = [make_approach(distance_ld=0.5)]  # ALERT level
        prayer = generate_approach_prayer(approaches)
        assert "nightwatch-approach-scan." in prayer
        assert "varek:" in prayer
        assert "ALERT" in prayer
        assert "2026 EG1" in prayer
        assert "presa-sky-aware." in prayer
        assert "do-good-us." in prayer

    def test_prayer_empty_approaches(self):
        prayer = generate_approach_prayer([])
        assert "nightwatch-approach-scan." in prayer
        assert "neo-clear" in prayer
        assert "velmu-sky-quiet." in prayer

    def test_prayer_groups_by_threat(self):
        approaches = [
            make_approach(designation="Close1", distance_ld=0.5),
            make_approach(designation="Watch1", distance_ld=1.5, is_potentially_hazardous=False),
            make_approach(
                designation="Sig1", distance_ld=3.0,
                is_potentially_hazardous=False, estimated_diameter_m_max=20.0,
            ),
        ]
        prayer = generate_approach_prayer(approaches)
        assert "ALERT" in prayer
        assert "WATCH" in prayer
        assert "SIGNIFICANT" in prayer

    def test_prayer_routine_count(self):
        approaches = [
            make_approach(
                designation=f"Routine{i}",
                distance_ld=25.0,
                is_potentially_hazardous=False,
                estimated_diameter_m_max=5.0,
            )
            for i in range(3)
        ]
        prayer = generate_approach_prayer(approaches)
        assert "routine-passes: 3" in prayer


# =========================================================================
# Async client method tests (mocked network)
# =========================================================================

class TestCADClientAsync:
    """Test async client methods with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_fetch_close_approaches(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=SAMPLE_API_RESPONSE)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)

        client = CADClient(session=mock_session)
        approaches = await client.fetch_close_approaches()

        assert len(approaches) == 3
        assert approaches[0].designation == "2026 EG1"
        mock_session.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_today(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=EMPTY_API_RESPONSE)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)

        client = CADClient(session=mock_session)
        approaches = await client.fetch_today()
        assert approaches == []

    @pytest.mark.asyncio
    async def test_fetch_handles_network_error(self):
        import aiohttp

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            side_effect=aiohttp.ClientError("Connection failed")
        )

        client = CADClient(session=mock_session)
        approaches = await client.fetch_close_approaches()
        assert approaches == []

    @pytest.mark.asyncio
    async def test_close_owned_session(self):
        client = CADClient()
        mock_session = AsyncMock()
        client._session = mock_session
        client._owns_session = True

        await client.close()
        mock_session.close.assert_called_once()
        assert client._session is None

    @pytest.mark.asyncio
    async def test_close_borrowed_session(self):
        mock_session = AsyncMock()
        client = CADClient(session=mock_session)

        await client.close()
        mock_session.close.assert_not_called()


# =========================================================================
# Integration-style tests (pure logic, no network)
# =========================================================================

class TestCADIntegration:
    """Test CAD client in context of NIGHTWATCH workflow."""

    def test_approach_to_prayer_flow(self):
        """Full flow: CloseApproach -> generate_approach_prayer."""
        approach = make_approach(
            distance_ld=0.518,
            is_potentially_hazardous=False,
        )

        assert approach.threat_level == ThreatLevel.ALERT  # < 1 LD
        prayer = generate_approach_prayer([approach])
        assert "ALERT" in prayer
        assert "2026 EG1" in prayer

    def test_multiple_approaches_sorted_by_threat(self):
        approaches = [
            make_approach(
                designation="Far",
                distance_ld=25.0,
                is_potentially_hazardous=False,
                estimated_diameter_m_max=5.0,
            ),
            make_approach(designation="Close", distance_ld=0.3),
            make_approach(
                designation="Mid",
                distance_ld=8.0,
                is_potentially_hazardous=False,
                estimated_diameter_m_max=5.0,
            ),
        ]

        threat_order = {
            ThreatLevel.ALERT: 0,
            ThreatLevel.WATCH: 1,
            ThreatLevel.SIGNIFICANT: 2,
            ThreatLevel.NOTABLE: 3,
            ThreatLevel.ROUTINE: 4,
        }
        sorted_approaches = sorted(
            approaches,
            key=lambda a: threat_order.get(a.threat_level, 99),
        )

        assert sorted_approaches[0].designation == "Close"
        assert sorted_approaches[-1].designation == "Far"

    def test_approach_ids_unique_across_batch(self):
        approaches = [
            make_approach(
                designation=f"2026 {chr(65+i)}{chr(65+i)}",
                close_approach_date=datetime(2026, 3, 12 + i),
            )
            for i in range(10)
        ]

        ids = [a.approach_id for a in approaches]
        assert len(ids) == len(set(ids))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
