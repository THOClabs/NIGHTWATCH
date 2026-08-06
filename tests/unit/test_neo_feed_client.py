"""
NIGHTWATCH NEO Feed Client Tests
Tests for NASA NEO Feed API client (secondary data source).

presa-nightwatch. velmu-test.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from services.meteor_tracking.close_approach_client import CloseApproach, ThreatLevel
from services.meteor_tracking.neo_feed_client import NEOFeedClient


# =========================================================================
# Test Data Fixtures
# =========================================================================

SAMPLE_NEO_FEED_RESPONSE = {
    'element_count': 2,
    'near_earth_objects': {
        '2026-03-23': [
            {
                'neo_reference_id': '2026FU',
                'name': '(2026 FU)',
                'absolute_magnitude_h': 27.0,
                'estimated_diameter': {
                    'meters': {
                        'estimated_diameter_min': 10.0,
                        'estimated_diameter_max': 22.0,
                    }
                },
                'is_potentially_hazardous_asteroid': False,
                'close_approach_data': [
                    {
                        'close_approach_date': '2026-03-23',
                        'close_approach_date_full': '2026-Mar-23 12:00',
                        'miss_distance': {
                            'astronomical': '0.00246',
                            'kilometers': '367918',
                            'lunar': '0.957',
                        },
                        'relative_velocity': {
                            'kilometers_per_second': '8.5',
                            'kilometers_per_hour': '30600',
                        }
                    }
                ]
            },
            {
                'neo_reference_id': '3200',
                'name': '3200 Phaethon',
                'absolute_magnitude_h': 14.6,
                'estimated_diameter': {
                    'meters': {
                        'estimated_diameter_min': 4600.0,
                        'estimated_diameter_max': 5200.0,
                    }
                },
                'is_potentially_hazardous_asteroid': True,
                'close_approach_data': [
                    {
                        'close_approach_date': '2026-03-23',
                        'close_approach_date_full': '2026-Mar-23 18:00',
                        'miss_distance': {
                            'astronomical': '0.5',
                            'kilometers': '74798935',
                            'lunar': '194.6',
                        },
                        'relative_velocity': {
                            'kilometers_per_second': '25.0',
                            'kilometers_per_hour': '90000',
                        }
                    }
                ]
            }
        ]
    }
}


# =========================================================================
# NEO Feed Client Tests
# =========================================================================

class TestNEOFeedClient:
    """Test NASA NEO Feed API client."""

    def test_init_default(self):
        """Test default initialization with DEMO_KEY."""
        client = NEOFeedClient()
        assert client.api_key == "DEMO_KEY"

    def test_init_custom_key(self):
        """Test initialization with custom API key."""
        client = NEOFeedClient(api_key="my_key_123")
        assert client.api_key == "my_key_123"

    @pytest.mark.asyncio
    async def test_parse_neo_feed(self):
        """Test parsing NEO Feed API response."""
        client = NEOFeedClient()
        approaches = client._parse_neo_feed(SAMPLE_NEO_FEED_RESPONSE)

        assert len(approaches) == 2
        # Should be sorted by approach date
        assert approaches[0].close_approach_date <= approaches[1].close_approach_date

    @pytest.mark.asyncio
    async def test_parse_neo_feed_properties(self):
        """Test that parsed NEO objects have correct properties."""
        client = NEOFeedClient()
        approaches = client._parse_neo_feed(SAMPLE_NEO_FEED_RESPONSE)

        fu = next(a for a in approaches if a.designation == '2026FU')
        assert fu.fullname == '(2026 FU)'
        assert fu.distance_au == pytest.approx(0.00246)
        assert fu.distance_km == pytest.approx(367918.0)
        assert fu.relative_velocity_km_s == pytest.approx(8.5)
        assert fu.estimated_diameter_m_min == 10.0
        assert fu.estimated_diameter_m_max == 22.0
        assert fu.is_potentially_hazardous is False

    @pytest.mark.asyncio
    async def test_parse_neo_feed_pha(self):
        """Test PHA flag is correctly parsed from NEO Feed."""
        client = NEOFeedClient()
        approaches = client._parse_neo_feed(SAMPLE_NEO_FEED_RESPONSE)

        phaethon = next(a for a in approaches if a.designation == '3200')
        assert phaethon.is_potentially_hazardous is True
        # PHA at any distance should be ALERT
        assert phaethon.threat_level == ThreatLevel.ALERT

    @pytest.mark.asyncio
    async def test_parse_neo_feed_empty(self):
        """Test parsing empty feed response."""
        client = NEOFeedClient()
        approaches = client._parse_neo_feed({'near_earth_objects': {}})
        assert len(approaches) == 0

    @pytest.mark.asyncio
    async def test_parse_neo_feed_no_approach_data(self):
        """Test parsing NEO with no close approach data."""
        client = NEOFeedClient()
        response = {
            'near_earth_objects': {
                '2026-03-23': [{
                    'neo_reference_id': 'test',
                    'name': 'test',
                    'absolute_magnitude_h': 25.0,
                    'estimated_diameter': {
                        'meters': {
                            'estimated_diameter_min': 10,
                            'estimated_diameter_max': 20
                        }
                    },
                    'is_potentially_hazardous_asteroid': False,
                    'close_approach_data': []
                }]
            }
        }
        approaches = client._parse_neo_feed(response)
        assert len(approaches) == 0

    @pytest.mark.asyncio
    async def test_close_no_session(self):
        """Test closing with no active session."""
        client = NEOFeedClient()
        await client.close()
        assert client._session is None

    @pytest.mark.asyncio
    async def test_close_owned_session(self):
        """Test that owned session is properly closed."""
        client = NEOFeedClient()
        mock_session = AsyncMock()
        client._session = mock_session
        client._owns_session = True

        await client.close()
        mock_session.close.assert_called_once()
        assert client._session is None

    @pytest.mark.asyncio
    async def test_close_borrowed_session(self):
        """Test that borrowed session is not closed."""
        mock_session = AsyncMock()
        client = NEOFeedClient(session=mock_session)

        await client.close()
        mock_session.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_parse_datetime_formats(self):
        """Test various date format parsing."""
        client = NEOFeedClient()

        dt = client._parse_datetime('2026-Mar-23 12:00')
        assert dt.year == 2026
        assert dt.month == 3
        assert dt.day == 23
        assert dt.hour == 12

        dt = client._parse_datetime('2026-03-23')
        assert dt.day == 23


class TestNEOFeedIntegration:
    """Integration tests for NEO Feed with existing CloseApproach type."""

    def test_feed_produces_compatible_types(self):
        """NEO Feed results are the same CloseApproach type as CAD results."""
        client = NEOFeedClient()
        approaches = client._parse_neo_feed(SAMPLE_NEO_FEED_RESPONSE)

        for a in approaches:
            assert isinstance(a, CloseApproach)
            # All CloseApproach properties should work
            assert isinstance(a.threat_level, ThreatLevel)
            assert isinstance(a.estimated_diameter_str, str)
            assert isinstance(a.approach_id, str)
            assert isinstance(a.lexicon_str, str)

    def test_feed_pha_vs_cad_heuristic(self):
        """
        NEO Feed provides real PHA flag from NASA.
        CAD client uses heuristic (H<=22 and dist<0.05 AU).
        Feed data should be more authoritative.
        """
        client = NEOFeedClient()
        approaches = client._parse_neo_feed(SAMPLE_NEO_FEED_RESPONSE)

        # Phaethon is officially PHA but distant — feed correctly flags it
        phaethon = next(a for a in approaches if a.designation == '3200')
        assert phaethon.is_potentially_hazardous is True

        # 2026 FU is close but not PHA — feed correctly doesn't flag it
        fu = next(a for a in approaches if a.designation == '2026FU')
        assert fu.is_potentially_hazardous is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
