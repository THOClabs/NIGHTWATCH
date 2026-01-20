"""
NIGHTWATCH Astrometry + Camera Integration Test (Step 120)

Tests end-to-end plate solving workflow using camera simulator
and astrometry service working together.
"""

import asyncio
import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

# Import services
from services.astrometry.plate_solver import (
    PlateSolver,
    SolverConfig,
    SolverBackend,
    SolveStatus,
    SolveResult,
    PlateSolveHint,
)
from services.simulators.camera_simulator import (
    CameraSimulator,
    SimulatedCameraModel,
    reset_simulators,
)
from services.simulators.star_field import (
    StarFieldGenerator,
    StarFieldConfig,
)


class TestAstrometryCameraIntegration:
    """Integration tests for astrometry + camera workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_simulators()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_camera_capture_for_solving(self):
        """Test capturing an image suitable for plate solving."""
        # Create camera simulator
        camera = CameraSimulator(model=SimulatedCameraModel.ASI294MC_PRO)
        camera.initialize()

        # Set ROI for faster capture
        camera.set_roi(0, 0, 1024, 1024, 1)
        camera.set_control_value(1, 5000)  # 5ms exposure

        # Capture frame
        frame = camera.capture_frame()
        assert frame is not None
        assert len(frame) > 0

        # Verify image dimensions (1024 x 1024 x 2 bytes)
        expected_size = 1024 * 1024 * 2
        assert len(frame) == expected_size

        camera.close()

    def test_star_field_generation_for_solving(self):
        """Test generating synthetic star field for solver testing."""
        config = StarFieldConfig(
            width=1024,
            height=1024,
            num_stars=100,
            min_magnitude=6.0,
            max_magnitude=12.0,
            fwhm_pixels=3.0,
            background_level=500,
        )

        generator = StarFieldGenerator(config)
        generator.set_seed(42)  # Reproducible

        image = generator.generate()
        assert image is not None
        assert len(image) == 1024 * 1024 * 2  # 16-bit

        # Check star catalog
        catalog = generator.get_star_catalog()
        assert len(catalog) == 100
        assert all("x" in star and "y" in star for star in catalog)

    def test_solver_config_defaults(self):
        """Test plate solver configuration defaults."""
        config = SolverConfig()

        assert config.primary_solver == SolverBackend.ASTROMETRY_NET
        assert config.fallback_solver == SolverBackend.ASTAP
        assert config.blind_timeout_sec == 30.0
        assert config.hint_timeout_sec == 5.0
        assert config.pixel_scale_low == 0.5
        assert config.pixel_scale_high == 2.0

    def test_solver_initialization(self):
        """Test plate solver initialization."""
        solver = PlateSolver()

        assert solver.config is not None
        assert solver._solve_history == []

    def test_solve_result_formatting(self):
        """Test solve result RA/Dec formatting."""
        result = SolveResult(
            status=SolveStatus.SUCCESS,
            ra_deg=83.633,    # Orion Nebula
            dec_deg=-5.375,
            rotation_deg=45.0,
            pixel_scale=1.2,
        )

        # Test RA HMS format
        ra_hms = result.ra_hms
        assert "05h" in ra_hms
        assert "34m" in ra_hms

        # Test Dec DMS format
        dec_dms = result.dec_dms
        assert "-05°" in dec_dms
        assert "22'" in dec_dms

    def test_position_hint_creation(self):
        """Test creating position hints for faster solving."""
        hint = PlateSolveHint(
            ra_deg=180.0,
            dec_deg=45.0,
            radius_deg=2.0,
        )

        assert hint.ra_deg == 180.0
        assert hint.dec_deg == 45.0
        assert hint.radius_deg == 2.0

    @pytest.mark.asyncio
    async def test_solve_missing_image(self):
        """Test solving with non-existent image file."""
        solver = PlateSolver()

        result = await solver.solve("/nonexistent/image.fits")

        assert result.status == SolveStatus.FAILED
        assert "not found" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_solve_workflow_mock(self):
        """Test complete solve workflow with mocked solver backend."""
        solver = PlateSolver()

        # Create a test FITS file
        test_image = Path(self.temp_dir) / "test.fits"
        test_image.write_bytes(b"SIMPLE  =                    T")

        # Mock the solver backend
        with patch.object(solver, '_solve_astrometry_net') as mock_solve:
            mock_solve.return_value = SolveResult(
                status=SolveStatus.SUCCESS,
                ra_deg=180.0,
                dec_deg=45.0,
                rotation_deg=0.0,
                pixel_scale=1.0,
                backend_used=SolverBackend.ASTROMETRY_NET,
                num_stars_matched=25,
            )

            result = await solver.solve(str(test_image))

            assert result.status == SolveStatus.SUCCESS
            assert result.ra_deg == 180.0
            assert result.dec_deg == 45.0

    @pytest.mark.asyncio
    async def test_solve_with_hint(self):
        """Test solving with position hint."""
        solver = PlateSolver()
        test_image = Path(self.temp_dir) / "test.fits"
        test_image.write_bytes(b"SIMPLE  =                    T")

        hint = PlateSolveHint(ra_deg=180.0, dec_deg=45.0, radius_deg=2.0)

        with patch.object(solver, '_solve_astrometry_net') as mock_solve:
            mock_solve.return_value = SolveResult(
                status=SolveStatus.SUCCESS,
                ra_deg=180.1,
                dec_deg=45.05,
            )

            result = await solver.solve(str(test_image), hint=hint)
            assert result.status == SolveStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_solve_fallback_to_astap(self):
        """Test fallback to ASTAP when primary solver fails."""
        solver = PlateSolver()
        test_image = Path(self.temp_dir) / "test.fits"
        test_image.write_bytes(b"SIMPLE  =                    T")

        # Mock primary failure, fallback success
        with patch.object(solver, '_solve_astrometry_net') as mock_anet, \
             patch.object(solver, '_solve_astap') as mock_astap:

            mock_anet.return_value = SolveResult(
                status=SolveStatus.FAILED,
                error_message="No solution found",
            )
            mock_astap.return_value = SolveResult(
                status=SolveStatus.SUCCESS,
                ra_deg=180.0,
                dec_deg=45.0,
                backend_used=SolverBackend.ASTAP,
            )

            result = await solver.solve(str(test_image))

            assert result.status == SolveStatus.SUCCESS
            assert result.backend_used == SolverBackend.ASTAP

    def test_solve_history_tracking(self):
        """Test that solve results are tracked in history."""
        solver = PlateSolver()

        # Manually add to history
        result1 = SolveResult(status=SolveStatus.SUCCESS, ra_deg=180.0, dec_deg=45.0)
        result2 = SolveResult(status=SolveStatus.FAILED, error_message="Test failure")

        solver._solve_history.append(result1)
        solver._solve_history.append(result2)

        assert len(solver._solve_history) == 2
        assert solver._solve_history[0].status == SolveStatus.SUCCESS
        assert solver._solve_history[1].status == SolveStatus.FAILED


class TestCameraSolverWorkflow:
    """Test complete camera-to-solver workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_simulators()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_capture_and_prepare_for_solve(self):
        """Test capturing image and preparing for solve."""
        # Set up camera
        camera = CameraSimulator(model=SimulatedCameraModel.ASI183MM_PRO)
        camera.initialize()
        camera.set_roi(0, 0, 512, 512, 1)

        # Generate star field for the camera
        star_config = StarFieldConfig(
            width=512,
            height=512,
            num_stars=50,
            fwhm_pixels=2.5,
        )
        generator = StarFieldGenerator(star_config)
        generator.set_seed(123)

        # In real use, the camera would capture actual sky
        # For testing, we verify the workflow components work
        frame = camera.capture_frame()
        assert frame is not None

        # Verify star field can be generated
        stars = generator.generate_stars()
        assert len(stars) == 50

        camera.close()

    @pytest.mark.asyncio
    async def test_full_capture_solve_cycle(self):
        """Test complete capture -> solve cycle (mocked)."""
        # Create camera
        camera = CameraSimulator(model=SimulatedCameraModel.ASI294MC_PRO)
        camera.initialize()

        # Create solver
        solver = PlateSolver()

        # Capture frame
        camera.set_roi(0, 0, 1024, 1024, 1)
        frame = camera.capture_frame()
        assert frame is not None

        # Save frame (in real use, would save as FITS)
        frame_path = Path(self.temp_dir) / "capture.fits"
        frame_path.write_bytes(frame[:1000])  # Just header for test

        # Mock the solve
        with patch.object(solver, '_solve_astrometry_net') as mock_solve:
            mock_solve.return_value = SolveResult(
                status=SolveStatus.SUCCESS,
                ra_deg=280.0,  # Somewhere in the sky
                dec_deg=38.0,
                pixel_scale=1.1,
                num_stars_matched=30,
            )

            result = await solver.solve(str(frame_path))

            assert result.status == SolveStatus.SUCCESS
            assert 275 < result.ra_deg < 285
            assert 35 < result.dec_deg < 42

        camera.close()


class TestSolverStatusCodes:
    """Test solver status handling."""

    def test_all_status_codes_exist(self):
        """Verify all status codes are defined."""
        statuses = [
            SolveStatus.SUCCESS,
            SolveStatus.FAILED,
            SolveStatus.TIMEOUT,
            SolveStatus.NO_STARS,
            SolveStatus.CANCELLED,
        ]
        assert len(statuses) == 5

    def test_status_values(self):
        """Test status value strings."""
        assert SolveStatus.SUCCESS.value == "success"
        assert SolveStatus.FAILED.value == "failed"
        assert SolveStatus.TIMEOUT.value == "timeout"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
