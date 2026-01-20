"""
NIGHTWATCH Focus + Camera Integration Test (Step 192)

Tests end-to-end autofocus workflow using camera simulator
and focus service working together.
"""

import asyncio
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

# Import services
from services.focus.focuser_service import (
    FocuserConfig,
    FocuserState,
    AutoFocusMethod,
    FocusMetric,
    FocusRun,
    FocusPositionRecord,
    FocusRunDatabase,
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


class TestFocusCameraIntegration:
    """Integration tests for focus + camera workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_simulators()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_focuser_config_defaults(self):
        """Test focuser configuration defaults."""
        config = FocuserConfig()

        assert config.max_position == 50000
        assert config.step_size_um == 1.0
        assert config.backlash_steps == 100
        assert config.temp_coefficient == -2.5
        assert config.autofocus_method == AutoFocusMethod.HFD
        assert config.autofocus_samples == 9
        assert config.hfd_target == 3.0

    def test_focuser_states(self):
        """Test all focuser states exist."""
        states = [
            FocuserState.IDLE,
            FocuserState.MOVING,
            FocuserState.AUTOFOCUS,
            FocuserState.CALIBRATING,
            FocuserState.ERROR,
        ]
        assert len(states) == 5

    def test_autofocus_methods(self):
        """Test all autofocus methods exist."""
        methods = [
            AutoFocusMethod.VCURVE,
            AutoFocusMethod.BAHTINOV,
            AutoFocusMethod.CONTRAST,
            AutoFocusMethod.HFD,
        ]
        assert len(methods) == 4

    def test_focus_metric_creation(self):
        """Test creating focus metric measurements."""
        metric = FocusMetric(
            timestamp=datetime.now(),
            position=25000,
            hfd=3.5,
            fwhm=2.1,
            peak_value=45000,
            star_count=15,
            temperature_c=20.0,
        )

        assert metric.position == 25000
        assert metric.hfd == 3.5
        assert metric.fwhm == 2.1
        assert metric.star_count == 15
        assert metric.temperature_c == 20.0

    def test_focus_run_creation(self):
        """Test creating a focus run record."""
        run = FocusRun(
            run_id="focus_001",
            start_time=datetime.now(),
            method=AutoFocusMethod.HFD,
            initial_position=25000,
        )

        assert run.run_id == "focus_001"
        assert run.method == AutoFocusMethod.HFD
        assert run.initial_position == 25000
        assert run.final_position == 0
        assert run.success is False
        assert len(run.measurements) == 0

    def test_focus_run_with_measurements(self):
        """Test focus run with measurement data."""
        run = FocusRun(
            run_id="focus_002",
            start_time=datetime.now(),
            method=AutoFocusMethod.VCURVE,
            initial_position=24000,
        )

        # Add measurements at different positions
        positions = [24000, 24500, 25000, 25500, 26000]
        hfds = [4.5, 3.8, 3.2, 3.5, 4.2]  # V-curve shape

        for pos, hfd in zip(positions, hfds):
            metric = FocusMetric(
                timestamp=datetime.now(),
                position=pos,
                hfd=hfd,
                fwhm=hfd * 0.6,
                peak_value=50000,
                star_count=20,
                temperature_c=18.5,
            )
            run.measurements.append(metric)

        # Find best position
        best_idx = hfds.index(min(hfds))
        run.final_position = positions[best_idx]
        run.best_hfd = min(hfds)
        run.success = True
        run.end_time = datetime.now()

        assert len(run.measurements) == 5
        assert run.final_position == 25000
        assert run.best_hfd == 3.2
        assert run.success is True

    def test_focus_position_record(self):
        """Test focus position recording."""
        record = FocusPositionRecord(
            timestamp=datetime.now(),
            position=25000,
            temperature_c=18.5,
            reason="auto_focus",
            hfd=3.2,
        )

        assert record.position == 25000
        assert record.reason == "auto_focus"
        assert record.hfd == 3.2

    def test_camera_for_focus_imaging(self):
        """Test camera capture for focus measurements."""
        camera = CameraSimulator(model=SimulatedCameraModel.ASI294MC_PRO)
        camera.initialize()

        # Set up for focus imaging (small ROI, short exposure)
        camera.set_roi(0, 0, 512, 512, 2)  # 2x2 binning
        camera.set_control_value(1, 2000)  # 2ms exposure
        camera.set_control_value(0, 200)   # Moderate gain

        frame = camera.capture_frame()
        assert frame is not None

        # Verify binned image size (512/2 * 512/2 * 2 bytes)
        expected_size = 256 * 256 * 2
        assert len(frame) == expected_size

        camera.close()

    def test_star_field_for_hfd_measurement(self):
        """Test generating star field for HFD measurement testing."""
        # Generate star field with known FWHM
        config = StarFieldConfig(
            width=512,
            height=512,
            num_stars=25,
            min_magnitude=6.0,
            max_magnitude=10.0,
            fwhm_pixels=4.0,  # Simulated out-of-focus
            background_level=300,
        )

        generator = StarFieldGenerator(config)
        generator.set_seed(42)

        image = generator.generate()
        catalog = generator.get_star_catalog()

        assert len(catalog) == 25
        # All stars should have FWHM near 4.0 (with variation)
        for star in catalog:
            assert 3.0 < star["fwhm"] < 5.0

    def test_vcurve_data_simulation(self):
        """Test simulating V-curve focus data."""
        # Simulate V-curve: HFD decreases then increases around best focus
        best_position = 25000
        step_size = 500
        samples = 9

        positions = []
        hfds = []

        for i in range(samples):
            pos = best_position - (samples // 2) * step_size + i * step_size
            positions.append(pos)

            # Parabolic V-curve simulation
            distance = abs(pos - best_position) / 1000.0
            hfd = 3.0 + 0.5 * distance ** 2
            hfds.append(hfd)

        # Verify V-curve shape
        assert len(positions) == 9
        assert min(hfds) == hfds[4]  # Minimum at center
        assert hfds[0] > hfds[4]     # Left side higher
        assert hfds[8] > hfds[4]     # Right side higher


class TestFocusDatabase:
    """Test focus run database functionality."""

    def setup_method(self):
        """Set up test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_focus.db"

    def teardown_method(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_database_initialization(self):
        """Test initializing focus database."""
        db = FocusRunDatabase(str(self.db_path))

        result = db.initialize()
        assert result is True
        assert db._initialized is True
        assert self.db_path.exists()

    def test_database_path_stored(self):
        """Test database path is stored correctly."""
        db = FocusRunDatabase("/custom/path/focus.db")
        assert db.db_path == "/custom/path/focus.db"


class TestFocusCameraWorkflow:
    """Test complete focus workflow with camera."""

    def setup_method(self):
        """Set up test fixtures."""
        reset_simulators()

    def test_complete_autofocus_workflow_mock(self):
        """Test complete autofocus workflow (mocked)."""
        # Create camera
        camera = CameraSimulator(model=SimulatedCameraModel.ASI183MM_PRO)
        camera.initialize()

        # Create focus run
        run = FocusRun(
            run_id="test_af_001",
            start_time=datetime.now(),
            method=AutoFocusMethod.HFD,
            initial_position=24000,
        )

        # Simulate focus sequence
        positions = range(23000, 27000, 500)
        best_pos = 25000
        best_hfd = float('inf')

        for pos in positions:
            # In real workflow: move focuser, capture image, measure HFD
            camera.set_roi(0, 0, 512, 512, 2)
            frame = camera.capture_frame()
            assert frame is not None

            # Simulated HFD measurement (parabolic)
            distance = abs(pos - 25000) / 1000.0
            hfd = 3.0 + 0.4 * distance ** 2

            metric = FocusMetric(
                timestamp=datetime.now(),
                position=pos,
                hfd=hfd,
                fwhm=hfd * 0.6,
                peak_value=50000,
                star_count=20,
                temperature_c=20.0,
            )
            run.measurements.append(metric)

            if hfd < best_hfd:
                best_hfd = hfd
                best_pos = pos

        run.final_position = best_pos
        run.best_hfd = best_hfd
        run.success = True
        run.end_time = datetime.now()

        # Verify results
        assert run.success is True
        assert run.final_position == 25000
        assert run.best_hfd < 3.5
        assert len(run.measurements) == 8

        camera.close()

    def test_temperature_compensation_calculation(self):
        """Test temperature compensation calculation."""
        config = FocuserConfig(temp_coefficient=-2.5)

        # Temperature changed by 4 degrees
        temp_change = 4.0
        position_adjustment = config.temp_coefficient * temp_change

        assert position_adjustment == -10.0  # Move in by 10 steps

        # Verify threshold
        assert config.temp_interval_c == 2.0  # Re-focus every 2°C

    def test_backlash_compensation(self):
        """Test backlash compensation logic."""
        config = FocuserConfig(backlash_steps=100)

        # When moving inward, overshoot then return
        target_pos = 24000
        current_pos = 25000

        if target_pos < current_pos:
            # Moving inward - apply backlash
            overshoot_pos = target_pos - config.backlash_steps
            assert overshoot_pos == 23900
            # Then move to target: 23900 -> 24000


class TestFocusQualityMetrics:
    """Test focus quality metric calculations."""

    def test_hfd_target_configuration(self):
        """Test HFD target is configurable."""
        config = FocuserConfig(hfd_target=2.5)
        assert config.hfd_target == 2.5

    def test_focus_tolerance(self):
        """Test focus position tolerance."""
        config = FocuserConfig(focus_tolerance=15)
        assert config.focus_tolerance == 15

    def test_autofocus_parameters(self):
        """Test autofocus parameters are configurable."""
        config = FocuserConfig(
            autofocus_step_size=150,
            autofocus_samples=11,
            autofocus_exposure_sec=3.0,
        )

        assert config.autofocus_step_size == 150
        assert config.autofocus_samples == 11
        assert config.autofocus_exposure_sec == 3.0


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
