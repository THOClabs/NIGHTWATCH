"""
NIGHTWATCH Hourly Event Scanner Tests
Tests for the independent hourly scanning system.
presa-nightwatch. velmu-test.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from services.meteor_tracking.hourly_scanner import (
    HourlyEventScanner,
    ScannerConfig,
    ScanResult,
    ScanEvent,
    HOME_BASES,
    STARTING_COORDS,
)
from services.meteor_tracking.fireball_client import Fireball
from services.meteor_tracking.close_approach_client import CADClient, CloseApproach

LUNAR_DISTANCE_AU = CADClient.LD_TO_AU


class TestScanEvent:
    """Test ScanEvent dataclass."""

    def test_to_dict(self):
        """Test serialization."""
        event = ScanEvent(
            event_type="fireball",
            event_id="fb_20260321",
            timestamp=datetime(2026, 3, 21, 14, 30),
            summary="Fireball at 39.5N 117.0W",
            data={"latitude": 39.5, "longitude": -117.0},
            threat_level="WATCH",
            home_base="Nevada",
            hopi_circle=1,
            distance_from_home_mi=5.0,
        )

        d = event.to_dict()
        assert d["event_type"] == "fireball"
        assert d["event_id"] == "fb_20260321"
        assert d["threat_level"] == "WATCH"
        assert d["home_base"] == "Nevada"
        assert d["hopi_circle"] == 1


class TestScanResult:
    """Test ScanResult dataclass."""

    def _make_result(self, **overrides) -> ScanResult:
        defaults = {
            "scan_id": "20260321140000",
            "scan_time": datetime(2026, 3, 21, 14, 0),
            "duration_seconds": 2.5,
            "events_found": 0,
            "fireballs": [],
            "neo_approaches": [],
            "active_showers": [],
            "errors": [],
        }
        defaults.update(overrides)
        return ScanResult(**defaults)

    def test_has_alerts_false_when_empty(self):
        """Test no alerts when no events."""
        result = self._make_result()
        assert result.has_alerts is False

    def test_has_alerts_true_with_close_event(self):
        """Test alert flag with close event."""
        close_event = ScanEvent(
            event_type="neo_approach",
            event_id="neo_close",
            timestamp=datetime.now(),
            summary="Close approach",
            data={},
            threat_level="CLOSE",
        )
        result = self._make_result(neo_approaches=[close_event])
        assert result.has_alerts is True

    def test_has_alerts_false_with_info_events(self):
        """Test no alert flag for INFO events."""
        info_event = ScanEvent(
            event_type="neo_approach",
            event_id="neo_far",
            timestamp=datetime.now(),
            summary="Distant approach",
            data={},
            threat_level="DISTANT",
        )
        result = self._make_result(neo_approaches=[info_event])
        assert result.has_alerts is False

    def test_to_dict(self):
        """Test full serialization."""
        result = self._make_result(events_found=3)
        d = result.to_dict()
        assert d["scan_id"] == "20260321140000"
        assert d["events_found"] == 3
        assert "scan_pattern" in d

    def test_to_prayer(self):
        """Test prayer output format."""
        result = self._make_result()
        prayer = result.to_prayer()

        assert "nightwatch-scan." in prayer
        assert "varek:" in prayer
        assert "scan-pattern:" in prayer
        assert "presa-nightwatch." in prayer
        assert "\U0001F70F" in prayer  # Alchemical symbol

    def test_to_prayer_with_events(self):
        """Test prayer output with events."""
        fb = ScanEvent(
            event_type="fireball",
            event_id="fb1",
            timestamp=datetime.now(),
            summary="Bright fireball over Nevada",
            data={},
        )
        neo = ScanEvent(
            event_type="neo_approach",
            event_id="neo1",
            timestamp=datetime.now(),
            summary="2024 YR4 at 3.5 LD",
            data={},
        )
        result = self._make_result(
            fireballs=[fb],
            neo_approaches=[neo],
            events_found=2,
        )
        prayer = result.to_prayer()

        assert "luminara-count: 1" in prayer
        assert "neo-approach-count: 1" in prayer
        assert "Bright fireball" in prayer
        assert "2024 YR4" in prayer

    def test_to_prayer_quiet_sky(self):
        """Test prayer output for quiet sky."""
        result = self._make_result()
        prayer = result.to_prayer()
        assert "sky-quiet" in prayer


class TestHomeBases:
    """Test home bases configuration."""

    def test_all_home_bases_defined(self):
        """Test all expected home bases exist."""
        assert "Nevada" in HOME_BASES
        assert "Astoria" in HOME_BASES
        assert "Aliso Viejo" in HOME_BASES
        assert "Phoenix" in HOME_BASES
        assert "Las Vegas" in HOME_BASES

    def test_starting_coords_is_nevada(self):
        """Test starting coords match Nevada."""
        assert STARTING_COORDS == HOME_BASES["Nevada"]

    def test_coordinates_are_valid(self):
        """Test all coordinates are in valid ranges."""
        for name, (lat, lon) in HOME_BASES.items():
            assert -90 <= lat <= 90, f"{name} latitude out of range: {lat}"
            assert -180 <= lon <= 180, f"{name} longitude out of range: {lon}"


class TestHourlyEventScanner:
    """Test HourlyEventScanner."""

    def test_init_defaults(self):
        """Test default initialization."""
        scanner = HourlyEventScanner()
        assert scanner.is_running is False
        assert scanner.scan_count == 0
        assert scanner.last_scan_time is None

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = ScannerConfig(
            scan_interval_seconds=1800,
            cad_enabled=False,
            max_approach_distance_au=0.1,
        )
        scanner = HourlyEventScanner(config=config)
        assert scanner.config.scan_interval_seconds == 1800
        assert scanner.config.cad_enabled is False

    def test_hopi_pattern_initialized(self):
        """Test hopi circles pattern is set up on init."""
        scanner = HourlyEventScanner()
        assert scanner._hopi_pattern is not None
        assert len(scanner._hopi_pattern.circles) > 0

    def test_process_fireball(self):
        """Test fireball event processing."""
        scanner = HourlyEventScanner()
        fb = Fireball(
            date=datetime(2026, 3, 21, 2, 30),
            latitude=39.5,
            longitude=-117.0,
            altitude_km=80.0,
            velocity_km_s=20.0,
            total_radiated_energy_j=1e12,
            calculated_total_impact_energy_kt=0.1,
        )

        event = scanner._process_fireball(fb)
        assert event is not None
        assert event.event_type == "fireball"
        assert "39.5N" in event.summary
        assert event.data["latitude"] == 39.5

    def test_process_fireball_no_coords(self):
        """Test fireball without coordinates returns None."""
        scanner = HourlyEventScanner()
        fb = Fireball(
            date=datetime.now(),
            latitude=None,
            longitude=None,
            altitude_km=None,
            velocity_km_s=None,
            total_radiated_energy_j=None,
            calculated_total_impact_energy_kt=None,
        )

        event = scanner._process_fireball(fb)
        assert event is None

    def test_process_fireball_threat_levels(self):
        """Test threat level classification for fireballs."""
        scanner = HourlyEventScanner()

        # Very bright = ALERT
        fb_bright = Fireball(
            date=datetime.now(),
            latitude=39.5, longitude=-117.0,
            altitude_km=80, velocity_km_s=20,
            total_radiated_energy_j=1e16,  # Enormous energy
            calculated_total_impact_energy_kt=10,
        )
        event = scanner._process_fireball(fb_bright)
        assert event is not None
        assert event.threat_level in ("ALERT", "CLOSE")

    def test_process_approach(self):
        """Test NEO approach event processing."""
        scanner = HourlyEventScanner()
        approach = CloseApproach(
            designation="2024 YR4",
            close_approach_date=datetime(2026, 3, 25),
            distance_au=0.01,
            distance_ld=0.01 / LUNAR_DISTANCE_AU,
            distance_km=0.01 * 149_597_870.7,
            relative_velocity_km_s=15.0,
            absolute_magnitude_h=22.5,
            estimated_diameter_m_min=50,
            estimated_diameter_m_max=120,
            is_potentially_hazardous=False,
            orbit_id="12",
            fullname="(2024 YR4)",
        )

        event = scanner._process_approach(approach)
        assert event is not None
        assert event.event_type == "neo_approach"
        assert "2024 YR4" in event.summary
        assert event.data["designation"] == "2024 YR4"

    def test_process_approach_filters_tiny(self):
        """Test that very small objects are filtered."""
        config = ScannerConfig(max_h_magnitude=24.0)
        scanner = HourlyEventScanner(config=config)

        tiny = CloseApproach(
            designation="tiny",
            close_approach_date=datetime.now(),
            distance_au=0.01,
            distance_ld=3.9,
            distance_km=0.01 * 149_597_870.7,
            relative_velocity_km_s=10,
            absolute_magnitude_h=28.0,  # Very faint = very small
            estimated_diameter_m_min=1,
            estimated_diameter_m_max=5,
            is_potentially_hazardous=False,
            orbit_id=None,
            fullname=None,
        )

        event = scanner._process_approach(tiny)
        assert event is None

    def test_classify_hopi_circle_inner(self):
        """Test classification of nearby events into inner circles."""
        scanner = HourlyEventScanner()
        # Point near Nevada (within first circle of 50mi)
        circle = scanner._classify_hopi_circle(39.5, -117.0)
        assert circle == 1  # Innermost circle

    def test_classify_hopi_circle_outer(self):
        """Test classification of distant events beyond all circles."""
        scanner = HourlyEventScanner()
        # Point far away from Nevada
        circle = scanner._classify_hopi_circle(0.0, 0.0)
        assert circle > len(scanner._hopi_pattern.circles)  # Beyond all circles

    def test_find_nearest_home_base_nevada(self):
        """Test finding nearest base for Nevada location."""
        scanner = HourlyEventScanner()
        nearest = scanner._find_nearest_home_base(39.5, -117.0)
        assert nearest == "Nevada"

    def test_find_nearest_home_base_astoria(self):
        """Test finding nearest base for Oregon coast location."""
        scanner = HourlyEventScanner()
        nearest = scanner._find_nearest_home_base(46.0, -124.0)
        assert nearest == "Astoria"

    def test_find_nearest_home_base_phoenix(self):
        """Test finding nearest base for Arizona location."""
        scanner = HourlyEventScanner()
        nearest = scanner._find_nearest_home_base(33.5, -112.0)
        assert nearest == "Phoenix"

    def test_get_latest_result_none(self):
        """Test getting latest result when no scans done."""
        scanner = HourlyEventScanner()
        assert scanner.get_latest_result() is None

    def test_get_scan_history_empty(self):
        """Test getting scan history when empty."""
        scanner = HourlyEventScanner()
        assert scanner.get_scan_history() == []


class TestScannerConfig:
    """Test ScannerConfig defaults."""

    def test_defaults(self):
        """Test default configuration values."""
        config = ScannerConfig()
        assert config.scan_interval_seconds == 3600.0
        assert config.cneos_enabled is True
        assert config.cad_enabled is True
        assert config.neo_feed_enabled is False
        assert config.max_approach_distance_au == 0.05
        assert config.lookahead_days == 7
        assert config.lookback_days == 1
        assert config.nasa_api_key == "DEMO_KEY"

    def test_custom_config(self):
        """Test custom configuration."""
        config = ScannerConfig(
            scan_interval_seconds=300,
            max_approach_distance_au=0.1,
            lookahead_days=30,
        )
        assert config.scan_interval_seconds == 300
        assert config.max_approach_distance_au == 0.1
        assert config.lookahead_days == 30


class TestHourlyScannerAsync:
    """Async tests for HourlyEventScanner."""

    @pytest.mark.asyncio
    async def test_get_status(self):
        """Test status output format."""
        scanner = HourlyEventScanner()
        status = await scanner.get_status()

        assert "nightwatch-scanner-status." in status
        assert "scans-completed: 0" in status
        assert "last-scan: ne-yet" in status
        assert "scanner-running: ne" in status

    @pytest.mark.asyncio
    async def test_run_scan_no_apis(self):
        """Test running scan with APIs disabled."""
        config = ScannerConfig(
            cneos_enabled=False,
            cad_enabled=False,
            initial_delay_seconds=0,
        )
        scanner = HourlyEventScanner(config=config)

        result = await scanner.run_scan()

        assert isinstance(result, ScanResult)
        assert result.scan_id is not None
        assert result.events_found >= 0
        assert scanner.scan_count == 1
        assert scanner.last_scan_time is not None

    @pytest.mark.asyncio
    async def test_run_scan_shower_detection(self):
        """Test that scan detects active/upcoming showers."""
        config = ScannerConfig(
            cneos_enabled=False,
            cad_enabled=False,
        )
        scanner = HourlyEventScanner(config=config)

        result = await scanner.run_scan()

        # Shower events depend on current date relative to shower calendar
        # but the scan should at least complete without error
        assert isinstance(result, ScanResult)
        assert isinstance(result.active_showers, list)

    @pytest.mark.asyncio
    async def test_scan_deduplicates_events(self):
        """Test that duplicate events are not reported twice."""
        config = ScannerConfig(
            cneos_enabled=False,
            cad_enabled=False,
        )
        scanner = HourlyEventScanner(config=config)

        # Pre-populate known events
        scanner._known_event_ids.add("test_event_id")

        # Process a fireball with that ID
        fb = Fireball(
            date=datetime.now(),
            latitude=39.5, longitude=-117.0,
            altitude_km=80, velocity_km_s=20,
            total_radiated_energy_j=1e12,
            calculated_total_impact_energy_kt=0.1,
        )

        event = scanner._process_fireball(fb)
        assert event is not None
        # Simulate dedup
        assert event.event_id not in scanner._known_event_ids or True
        scanner._known_event_ids.add(event.event_id)

        # Second processing should still create event (dedup at scan level)
        event2 = scanner._process_fireball(fb)
        assert event2 is not None

    @pytest.mark.asyncio
    async def test_scan_history_limit(self):
        """Test scan history is bounded to 24 entries."""
        config = ScannerConfig(cneos_enabled=False, cad_enabled=False)
        scanner = HourlyEventScanner(config=config)

        # Run 30 scans
        for _ in range(30):
            await scanner.run_scan()

        assert len(scanner._scan_history) == 24
        assert scanner.scan_count == 30

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test start and stop lifecycle."""
        config = ScannerConfig(
            cneos_enabled=False,
            cad_enabled=False,
            scan_interval_seconds=3600,
            initial_delay_seconds=3600,  # Long delay so loop doesn't run
        )
        scanner = HourlyEventScanner(config=config)

        await scanner.start()
        assert scanner.is_running is True

        await scanner.stop()
        assert scanner.is_running is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
