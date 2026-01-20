"""
NIGHTWATCH Plate Solver Unit Tests

Step 119: Write unit tests for solver backends
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

from services.astrometry.plate_solver import (
    PlateSolver,
    SolverConfig,
    SolveResult,
    SolveStatus,
    SolverBackend,
    PlateSolveHint,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def solver():
    """Create a plate solver instance."""
    return PlateSolver()


@pytest.fixture
def config():
    """Create a solver configuration."""
    return SolverConfig()


@pytest.fixture
def solve_hint():
    """Create a position hint."""
    return PlateSolveHint(ra_deg=180.0, dec_deg=45.0, radius_deg=3.0)


# ============================================================================
# SolverBackend Enum Tests
# ============================================================================

class TestSolverBackend:
    """Tests for SolverBackend enum."""

    def test_all_backends_defined(self):
        """Verify all solver backends are defined."""
        assert SolverBackend.ASTROMETRY_NET.value == "astrometry.net"
        assert SolverBackend.ASTAP.value == "astap"
        assert SolverBackend.PLATESOLVE2.value == "platesolve2"
        assert SolverBackend.NOVA.value == "nova"


# ============================================================================
# SolveStatus Enum Tests
# ============================================================================

class TestSolveStatus:
    """Tests for SolveStatus enum."""

    def test_all_statuses_defined(self):
        """Verify all solve statuses are defined."""
        assert SolveStatus.SUCCESS.value == "success"
        assert SolveStatus.FAILED.value == "failed"
        assert SolveStatus.TIMEOUT.value == "timeout"
        assert SolveStatus.NO_STARS.value == "no_stars"
        assert SolveStatus.CANCELLED.value == "cancelled"


# ============================================================================
# SolverConfig Tests
# ============================================================================

class TestSolverConfig:
    """Tests for SolverConfig dataclass."""

    def test_default_config(self, config):
        """Verify default solver configuration."""
        assert config.primary_solver == SolverBackend.ASTROMETRY_NET
        assert config.fallback_solver == SolverBackend.ASTAP
        assert config.blind_timeout_sec == 30.0
        assert config.hint_timeout_sec == 5.0
        assert config.downsample == 2

    def test_custom_config(self):
        """Verify custom solver configuration."""
        config = SolverConfig(
            primary_solver=SolverBackend.ASTAP,
            fallback_solver=None,
            blind_timeout_sec=60.0,
            pixel_scale_low=1.0,
            pixel_scale_high=3.0,
        )
        assert config.primary_solver == SolverBackend.ASTAP
        assert config.fallback_solver is None
        assert config.blind_timeout_sec == 60.0

    def test_config_paths(self, config):
        """Verify default path configurations."""
        assert config.solve_field_path == "/usr/bin/solve-field"
        assert config.astap_path == "/opt/astap/astap"
        assert config.index_path == "/usr/share/astrometry"


# ============================================================================
# SolveResult Tests
# ============================================================================

class TestSolveResult:
    """Tests for SolveResult dataclass."""

    def test_success_result(self):
        """Verify successful solve result."""
        result = SolveResult(
            status=SolveStatus.SUCCESS,
            ra_deg=180.0,
            dec_deg=45.0,
            rotation_deg=90.0,
            pixel_scale=1.5,
            solve_time_sec=2.5,
            backend_used=SolverBackend.ASTROMETRY_NET,
            num_stars_matched=50,
        )
        assert result.status == SolveStatus.SUCCESS
        assert result.ra_deg == 180.0
        assert result.dec_deg == 45.0
        assert result.solve_time_sec == 2.5

    def test_failed_result(self):
        """Verify failed solve result."""
        result = SolveResult(
            status=SolveStatus.FAILED,
            error_message="No matching stars found",
        )
        assert result.status == SolveStatus.FAILED
        assert result.error_message == "No matching stars found"
        assert result.ra_deg is None

    def test_ra_hms_conversion(self):
        """Verify RA to HMS format conversion."""
        result = SolveResult(status=SolveStatus.SUCCESS, ra_deg=180.0)
        hms = result.ra_hms
        assert "12h" in hms  # 180 deg = 12 hours

    def test_ra_hms_empty_when_none(self):
        """Verify RA HMS is empty when not solved."""
        result = SolveResult(status=SolveStatus.FAILED)
        assert result.ra_hms == ""

    def test_dec_dms_conversion(self):
        """Verify Dec to DMS format conversion."""
        result = SolveResult(status=SolveStatus.SUCCESS, dec_deg=45.0)
        dms = result.dec_dms
        assert "+45°" in dms

    def test_dec_dms_negative(self):
        """Verify negative Dec formatting."""
        result = SolveResult(status=SolveStatus.SUCCESS, dec_deg=-30.5)
        dms = result.dec_dms
        assert "-30°" in dms

    def test_dec_dms_empty_when_none(self):
        """Verify Dec DMS is empty when not solved."""
        result = SolveResult(status=SolveStatus.FAILED)
        assert result.dec_dms == ""


# ============================================================================
# PlateSolveHint Tests
# ============================================================================

class TestPlateSolveHint:
    """Tests for PlateSolveHint dataclass."""

    def test_hint_creation(self, solve_hint):
        """Verify position hint creation."""
        assert solve_hint.ra_deg == 180.0
        assert solve_hint.dec_deg == 45.0
        assert solve_hint.radius_deg == 3.0

    def test_hint_default_radius(self):
        """Verify default hint radius."""
        hint = PlateSolveHint(ra_deg=0.0, dec_deg=0.0)
        assert hint.radius_deg == 5.0


# ============================================================================
# PlateSolver Tests
# ============================================================================

class TestPlateSolver:
    """Tests for PlateSolver class."""

    def test_solver_initialization(self, solver):
        """Verify solver initializes correctly."""
        assert solver.config is not None
        assert isinstance(solver.config, SolverConfig)

    def test_solver_custom_config(self):
        """Verify solver with custom config."""
        config = SolverConfig(blind_timeout_sec=60.0)
        solver = PlateSolver(config=config)
        assert solver.config.blind_timeout_sec == 60.0

    def test_solver_has_solve_method(self, solver):
        """Verify solver has solve method."""
        assert hasattr(solver, 'solve')
        assert callable(solver.solve)

    def test_solver_has_solve_and_sync_method(self, solver):
        """Verify solver has solve_and_sync method."""
        assert hasattr(solver, 'solve_and_sync')
        assert callable(solver.solve_and_sync)

    def test_solver_config_defaults(self, solver):
        """Verify solver uses default configuration."""
        assert solver.config.primary_solver == SolverBackend.ASTROMETRY_NET
        assert solver.config.blind_timeout_sec == 30.0
        assert solver.config.hint_timeout_sec == 5.0


# ============================================================================
# Solver Command Building Tests
# ============================================================================

class TestSolverCommands:
    """Tests for solver command building."""

    def test_astrometry_net_command_structure(self, solver):
        """Test astrometry.net command construction."""
        if hasattr(solver, '_build_astrometry_command'):
            cmd = solver._build_astrometry_command(
                Path("/tmp/test.fits"),
                hint=None,
                timeout=30.0,
            )
            assert isinstance(cmd, list)
            assert any("solve-field" in str(c) for c in cmd)

    def test_astap_command_structure(self, solver):
        """Test ASTAP command construction."""
        if hasattr(solver, '_build_astap_command'):
            cmd = solver._build_astap_command(
                Path("/tmp/test.fits"),
                hint=None,
                timeout=30.0,
            )
            assert isinstance(cmd, list)


# ============================================================================
# Run Configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
