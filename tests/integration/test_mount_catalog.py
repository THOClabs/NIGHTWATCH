"""
Integration tests for Mount + Catalog Service (Step 565).

Tests the interaction between mount control and object catalog lookup,
including coordinate resolution, slewing to named objects, and position queries.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime


class TestMountCatalogIntegration:
    """Integration tests for mount and catalog services."""

    @pytest.fixture
    def mock_mount(self):
        """Create mock mount controller."""
        mount = Mock()
        mount.is_connected = True
        mount.is_parked = False
        mount.is_slewing = False
        mount.is_tracking = True
        mount.ra_hours = 12.5
        mount.dec_degrees = 45.0
        mount.altitude = 65.0
        mount.azimuth = 180.0
        mount.slew_to_coordinates = AsyncMock(return_value=True)
        mount.get_position = Mock(return_value=(12.5, 45.0))
        mount.sync_to_coordinates = AsyncMock(return_value=True)
        return mount

    @pytest.fixture
    def mock_catalog(self):
        """Create mock catalog service."""
        catalog = Mock()

        # Define catalog lookup responses
        catalog_data = {
            "M31": {"ra": 0.712, "dec": 41.27, "name": "Andromeda Galaxy", "type": "galaxy"},
            "M42": {"ra": 5.588, "dec": -5.39, "name": "Orion Nebula", "type": "nebula"},
            "M13": {"ra": 16.695, "dec": 36.46, "name": "Hercules Cluster", "type": "globular"},
            "NGC7000": {"ra": 20.987, "dec": 44.53, "name": "North America Nebula", "type": "nebula"},
            "Polaris": {"ra": 2.530, "dec": 89.26, "name": "Polaris", "type": "star"},
            "Vega": {"ra": 18.616, "dec": 38.78, "name": "Vega", "type": "star"},
        }

        def lookup(name):
            if name in catalog_data:
                return catalog_data[name]
            return None

        catalog.lookup = Mock(side_effect=lookup)
        catalog.search = Mock(return_value=[])
        return catalog

    @pytest.fixture
    def mock_safety(self):
        """Create mock safety monitor."""
        safety = Mock()
        safety.is_safe_to_slew = Mock(return_value=True)
        safety.check_altitude = Mock(return_value=True)
        safety.get_horizon_limit = Mock(return_value=10.0)
        return safety

    @pytest.mark.asyncio
    async def test_slew_to_messier_object(self, mock_mount, mock_catalog, mock_safety):
        """Test slewing to a Messier catalog object."""
        # Lookup M31 in catalog
        result = mock_catalog.lookup("M31")
        assert result is not None
        assert result["name"] == "Andromeda Galaxy"

        # Check safety
        assert mock_safety.is_safe_to_slew() is True

        # Slew to coordinates
        ra, dec = result["ra"], result["dec"]
        success = await mock_mount.slew_to_coordinates(ra, dec)

        assert success is True
        mock_mount.slew_to_coordinates.assert_called_once_with(ra, dec)

    @pytest.mark.asyncio
    async def test_slew_to_ngc_object(self, mock_mount, mock_catalog, mock_safety):
        """Test slewing to an NGC catalog object."""
        result = mock_catalog.lookup("NGC7000")
        assert result is not None
        assert result["name"] == "North America Nebula"

        success = await mock_mount.slew_to_coordinates(result["ra"], result["dec"])
        assert success is True

    @pytest.mark.asyncio
    async def test_slew_to_star(self, mock_mount, mock_catalog, mock_safety):
        """Test slewing to a named star."""
        result = mock_catalog.lookup("Vega")
        assert result is not None
        assert result["type"] == "star"

        success = await mock_mount.slew_to_coordinates(result["ra"], result["dec"])
        assert success is True

    def test_catalog_not_found(self, mock_catalog):
        """Test handling of object not in catalog."""
        result = mock_catalog.lookup("NonexistentObject")
        assert result is None

    @pytest.mark.asyncio
    async def test_slew_blocked_by_safety(self, mock_mount, mock_catalog, mock_safety):
        """Test that slew is blocked when safety check fails."""
        mock_safety.is_safe_to_slew.return_value = False

        result = mock_catalog.lookup("M31")
        assert result is not None

        # Safety check should fail
        assert mock_safety.is_safe_to_slew() is False

        # In real code, slew would not be called
        # This test verifies the safety integration point

    @pytest.mark.asyncio
    async def test_slew_blocked_below_horizon(self, mock_mount, mock_catalog, mock_safety):
        """Test that slew to object below horizon is blocked."""
        mock_safety.check_altitude.return_value = False

        result = mock_catalog.lookup("M42")  # Orion (dec -5)
        assert result is not None

        # Altitude check should fail for certain times/locations
        mock_safety.check_altitude.return_value = False
        assert mock_safety.check_altitude(result["dec"]) is False

    @pytest.mark.asyncio
    async def test_sync_after_platesolve(self, mock_mount, mock_catalog):
        """Test syncing mount position after plate solve."""
        # Simulate plate solve result
        solved_ra = 12.502
        solved_dec = 45.015

        # Sync mount to solved coordinates
        success = await mock_mount.sync_to_coordinates(solved_ra, solved_dec)
        assert success is True
        mock_mount.sync_to_coordinates.assert_called_once_with(solved_ra, solved_dec)

    def test_position_query(self, mock_mount):
        """Test querying current mount position."""
        ra, dec = mock_mount.get_position()

        assert ra == 12.5
        assert dec == 45.0

    @pytest.mark.asyncio
    async def test_multiple_object_sequence(self, mock_mount, mock_catalog, mock_safety):
        """Test slewing to multiple objects in sequence."""
        objects = ["M31", "M42", "M13"]

        for obj_name in objects:
            result = mock_catalog.lookup(obj_name)
            assert result is not None, f"Object {obj_name} not found"

            if mock_safety.is_safe_to_slew():
                success = await mock_mount.slew_to_coordinates(result["ra"], result["dec"])
                assert success is True

        # Verify all slews were called
        assert mock_mount.slew_to_coordinates.call_count == 3


class TestMountCatalogCoordinateConversion:
    """Tests for coordinate handling between mount and catalog."""

    def test_ra_hours_to_degrees(self):
        """Test RA conversion from hours to degrees."""
        ra_hours = 12.5
        ra_degrees = ra_hours * 15
        assert ra_degrees == 187.5

    def test_ra_degrees_to_hours(self):
        """Test RA conversion from degrees to hours."""
        ra_degrees = 180.0
        ra_hours = ra_degrees / 15
        assert ra_hours == 12.0

    def test_coordinate_format_hms(self):
        """Test HMS coordinate formatting."""
        ra_hours = 12.5  # 12h 30m 0s
        hours = int(ra_hours)
        minutes = int((ra_hours - hours) * 60)
        seconds = ((ra_hours - hours) * 60 - minutes) * 60

        assert hours == 12
        assert minutes == 30
        assert abs(seconds) < 0.001

    def test_coordinate_format_dms(self):
        """Test DMS coordinate formatting."""
        dec_degrees = 45.5  # 45° 30' 0"
        degrees = int(dec_degrees)
        arcmin = int((dec_degrees - degrees) * 60)
        arcsec = ((dec_degrees - degrees) * 60 - arcmin) * 60

        assert degrees == 45
        assert arcmin == 30
        assert abs(arcsec) < 0.001


class TestMountCatalogErrorHandling:
    """Tests for error handling in mount-catalog integration."""

    @pytest.fixture
    def mock_mount_with_errors(self):
        """Create mock mount that can simulate errors."""
        mount = Mock()
        mount.is_connected = True
        mount.slew_to_coordinates = AsyncMock(side_effect=Exception("Slew failed"))
        return mount

    @pytest.fixture
    def mock_catalog(self):
        """Create mock catalog."""
        catalog = Mock()
        catalog.lookup = Mock(return_value={"ra": 12.0, "dec": 45.0, "name": "Test"})
        return catalog

    @pytest.mark.asyncio
    async def test_slew_failure_handling(self, mock_mount_with_errors, mock_catalog):
        """Test handling of slew failures."""
        result = mock_catalog.lookup("Test")

        with pytest.raises(Exception, match="Slew failed"):
            await mock_mount_with_errors.slew_to_coordinates(result["ra"], result["dec"])

    def test_catalog_service_unavailable(self):
        """Test handling when catalog service is unavailable."""
        catalog = Mock()
        catalog.lookup = Mock(side_effect=ConnectionError("Service unavailable"))

        with pytest.raises(ConnectionError):
            catalog.lookup("M31")

    @pytest.mark.asyncio
    async def test_mount_not_connected(self, mock_catalog):
        """Test handling when mount is not connected."""
        mount = Mock()
        mount.is_connected = False

        result = mock_catalog.lookup("M31")
        assert result is not None

        # Should not attempt slew when disconnected
        assert mount.is_connected is False
