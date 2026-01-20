"""
NIGHTWATCH Mock Plate Solver for Testing

Step 118: Create mock solver for testing

Provides a simulated plate solver for unit testing without actual solver binaries.
"""

import asyncio
import random
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List


class MockSolverBackend(Enum):
    """Mock solver backends."""
    ASTROMETRY_NET = "astrometry.net"
    ASTAP = "astap"


class MockSolveStatus(Enum):
    """Solve result status."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    NO_STARS = "no_stars"
    CANCELLED = "cancelled"


@dataclass
class MockSolveResult:
    """Result of a mock plate solve."""
    status: MockSolveStatus
    ra_deg: Optional[float] = None
    dec_deg: Optional[float] = None
    rotation_deg: Optional[float] = None
    pixel_scale: Optional[float] = None
    solve_time_sec: Optional[float] = None
    backend_used: Optional[MockSolverBackend] = None
    num_stars_matched: Optional[int] = None
    error_message: Optional[str] = None
    field_width_deg: Optional[float] = None
    field_height_deg: Optional[float] = None

    @property
    def ra_hms(self) -> str:
        """RA in HMS format."""
        if self.ra_deg is None:
            return ""
        hours = self.ra_deg / 15.0
        h = int(hours)
        m = int((hours - h) * 60)
        s = ((hours - h) * 60 - m) * 60
        return f"{h:02d}h {m:02d}m {s:05.2f}s"

    @property
    def dec_dms(self) -> str:
        """Dec in DMS format."""
        if self.dec_deg is None:
            return ""
        sign = "+" if self.dec_deg >= 0 else "-"
        dec = abs(self.dec_deg)
        d = int(dec)
        m = int((dec - d) * 60)
        s = ((dec - d) * 60 - m) * 60
        return f"{sign}{d:02d}° {m:02d}' {s:05.2f}\""


@dataclass
class MockSolveHint:
    """Position hint for faster solving."""
    ra_deg: float
    dec_deg: float
    radius_deg: float = 5.0


class MockPlateSolver:
    """
    Mock plate solver for testing NIGHTWATCH astrometry functionality.

    Simulates plate solving behavior including:
    - Configurable solve success/failure
    - Simulated solve times
    - Position hint support
    - Error injection for testing error handling

    Usage:
        solver = MockPlateSolver()

        # Solve with hint (faster)
        result = await solver.solve("/tmp/image.fits", hint=MockSolveHint(ra_deg=180, dec_deg=45))

        # Blind solve (slower)
        result = await solver.solve("/tmp/image.fits")

        # Inject errors for testing
        solver.inject_error("timeout")
    """

    def __init__(
        self,
        primary_backend: MockSolverBackend = MockSolverBackend.ASTROMETRY_NET,
        fallback_backend: Optional[MockSolverBackend] = MockSolverBackend.ASTAP,
        default_pixel_scale: float = 1.5,
        blind_timeout_sec: float = 30.0,
        hint_timeout_sec: float = 5.0,
    ):
        """
        Initialize mock solver.

        Args:
            primary_backend: Primary solver to simulate
            fallback_backend: Fallback solver to simulate
            default_pixel_scale: Default pixel scale in arcsec/pixel
            blind_timeout_sec: Timeout for blind solves
            hint_timeout_sec: Timeout for hint solves
        """
        self.primary_backend = primary_backend
        self.fallback_backend = fallback_backend
        self.default_pixel_scale = default_pixel_scale
        self.blind_timeout_sec = blind_timeout_sec
        self.hint_timeout_sec = hint_timeout_sec

        # Tracking
        self._solve_count = 0
        self._successful_solves = 0
        self._failed_solves = 0
        self._solve_history: List[MockSolveResult] = []

        # Error injection
        self._inject_errors: Dict[str, bool] = {}

        # Success probability (can be adjusted for testing)
        self._success_probability = 0.95
        self._blind_solve_time_range = (2.0, 8.0)
        self._hint_solve_time_range = (0.5, 2.0)

        # Configurable result (for deterministic testing)
        self._fixed_result: Optional[MockSolveResult] = None

    async def solve(
        self,
        image_path: str,
        hint: Optional[MockSolveHint] = None,
        timeout: Optional[float] = None,
    ) -> MockSolveResult:
        """
        Solve an image.

        Args:
            image_path: Path to image file
            hint: Optional position hint for faster solving
            timeout: Optional custom timeout

        Returns:
            MockSolveResult with solve results
        """
        self._solve_count += 1

        # Check for injected errors
        if self._inject_errors.get("timeout"):
            timeout_sec = timeout or (self.hint_timeout_sec if hint else self.blind_timeout_sec)
            await asyncio.sleep(timeout_sec + 1)
            result = MockSolveResult(
                status=MockSolveStatus.TIMEOUT,
                error_message="Solve timed out",
            )
            self._failed_solves += 1
            self._solve_history.append(result)
            return result

        if self._inject_errors.get("no_stars"):
            result = MockSolveResult(
                status=MockSolveStatus.NO_STARS,
                error_message="No stars detected in image",
            )
            self._failed_solves += 1
            self._solve_history.append(result)
            return result

        if self._inject_errors.get("failed"):
            result = MockSolveResult(
                status=MockSolveStatus.FAILED,
                error_message="Solve failed - no solution found",
            )
            self._failed_solves += 1
            self._solve_history.append(result)
            return result

        # Return fixed result if set
        if self._fixed_result is not None:
            self._solve_history.append(self._fixed_result)
            if self._fixed_result.status == MockSolveStatus.SUCCESS:
                self._successful_solves += 1
            else:
                self._failed_solves += 1
            return self._fixed_result

        # Simulate solve time
        if hint:
            solve_time = random.uniform(*self._hint_solve_time_range)
        else:
            solve_time = random.uniform(*self._blind_solve_time_range)

        await asyncio.sleep(min(solve_time, 1.0))  # Cap for testing

        # Determine success based on probability
        if random.random() > self._success_probability:
            result = MockSolveResult(
                status=MockSolveStatus.FAILED,
                solve_time_sec=solve_time,
                backend_used=self.primary_backend,
                error_message="Solve failed - insufficient matches",
            )
            self._failed_solves += 1
            self._solve_history.append(result)
            return result

        # Generate solution
        if hint:
            # Solution near hint with small offset
            ra = hint.ra_deg + random.gauss(0, 0.01)
            dec = hint.dec_deg + random.gauss(0, 0.01)
        else:
            # Random position for blind solve
            ra = random.uniform(0, 360)
            dec = random.uniform(-90, 90)

        rotation = random.uniform(0, 360)
        pixel_scale = self.default_pixel_scale + random.gauss(0, 0.02)
        stars_matched = random.randint(30, 150)

        result = MockSolveResult(
            status=MockSolveStatus.SUCCESS,
            ra_deg=ra,
            dec_deg=dec,
            rotation_deg=rotation,
            pixel_scale=pixel_scale,
            solve_time_sec=solve_time,
            backend_used=self.primary_backend,
            num_stars_matched=stars_matched,
            field_width_deg=pixel_scale * 1936 / 3600,  # Assume 1936 pixels
            field_height_deg=pixel_scale * 1096 / 3600,  # Assume 1096 pixels
        )

        self._successful_solves += 1
        self._solve_history.append(result)
        return result

    async def solve_and_sync(
        self,
        image_path: str,
        mount_client=None,
        hint: Optional[MockSolveHint] = None,
    ) -> MockSolveResult:
        """
        Solve and sync mount to solution.

        Args:
            image_path: Path to image file
            mount_client: Mount client for sync (optional in mock)
            hint: Optional position hint

        Returns:
            MockSolveResult with solve results
        """
        result = await self.solve(image_path, hint)

        if result.status == MockSolveStatus.SUCCESS and mount_client:
            # In real implementation, would sync mount
            # mount_client.sync(result.ra_deg, result.dec_deg)
            pass

        return result

    def calculate_pointing_error(
        self,
        expected_ra: float,
        expected_dec: float,
        actual_ra: float,
        actual_dec: float,
    ) -> Dict[str, float]:
        """
        Calculate pointing error between expected and actual position.

        Args:
            expected_ra: Expected RA in degrees
            expected_dec: Expected Dec in degrees
            actual_ra: Actual solved RA in degrees
            actual_dec: Actual solved Dec in degrees

        Returns:
            Dict with error values in arcseconds
        """
        import math

        # Calculate great circle distance
        ra1 = math.radians(expected_ra)
        dec1 = math.radians(expected_dec)
        ra2 = math.radians(actual_ra)
        dec2 = math.radians(actual_dec)

        # Haversine formula
        dra = ra2 - ra1
        ddec = dec2 - dec1

        a = math.sin(ddec/2)**2 + math.cos(dec1) * math.cos(dec2) * math.sin(dra/2)**2
        c = 2 * math.asin(math.sqrt(a))

        # Convert to arcseconds
        error_arcsec = math.degrees(c) * 3600

        # Component errors
        ra_error_arcsec = (actual_ra - expected_ra) * 3600 * math.cos(dec1)
        dec_error_arcsec = (actual_dec - expected_dec) * 3600

        return {
            "total_error_arcsec": error_arcsec,
            "ra_error_arcsec": ra_error_arcsec,
            "dec_error_arcsec": dec_error_arcsec,
        }

    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    def set_success_probability(self, probability: float) -> None:
        """Set probability of successful solve (0.0 to 1.0)."""
        self._success_probability = max(0.0, min(1.0, probability))

    def set_fixed_result(self, result: Optional[MockSolveResult]) -> None:
        """
        Set a fixed result to return for all solves.

        Args:
            result: Fixed result, or None to use random results
        """
        self._fixed_result = result

    def set_solve_time_range(
        self,
        blind_range: tuple = (2.0, 8.0),
        hint_range: tuple = (0.5, 2.0),
    ) -> None:
        """Set solve time ranges for blind and hinted solves."""
        self._blind_solve_time_range = blind_range
        self._hint_solve_time_range = hint_range

    # =========================================================================
    # ERROR INJECTION
    # =========================================================================

    def inject_error(self, error_type: str) -> None:
        """
        Inject error for testing.

        Args:
            error_type: Type of error
                - "timeout": Solve times out
                - "no_stars": No stars detected
                - "failed": Generic failure
                - "cancelled": Solve was cancelled
        """
        self._inject_errors[error_type] = True

    def clear_errors(self) -> None:
        """Clear all injected errors."""
        self._inject_errors.clear()

    def clear_error(self, error_type: str) -> None:
        """Clear specific error."""
        self._inject_errors.pop(error_type, None)

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get solver statistics."""
        return {
            "total_solves": self._solve_count,
            "successful_solves": self._successful_solves,
            "failed_solves": self._failed_solves,
            "success_rate": self._successful_solves / self._solve_count
                if self._solve_count > 0 else 0.0,
            "primary_backend": self.primary_backend.value,
            "fallback_backend": self.fallback_backend.value if self.fallback_backend else None,
        }

    def get_solve_history(self, limit: int = 10) -> List[MockSolveResult]:
        """Get recent solve history."""
        return self._solve_history[-limit:]

    def reset(self) -> None:
        """Reset solver to initial state."""
        self._solve_count = 0
        self._successful_solves = 0
        self._failed_solves = 0
        self._solve_history.clear()
        self._inject_errors.clear()
        self._fixed_result = None


# =============================================================================
# Factory function
# =============================================================================

def create_mock_solver(
    preset: str = "default",
    **kwargs,
) -> MockPlateSolver:
    """
    Create mock solver with preset configuration.

    Args:
        preset: Configuration preset
            - "default": Standard configuration
            - "fast": Always succeeds quickly
            - "slow": Longer solve times
            - "unreliable": Lower success rate
        **kwargs: Override specific parameters

    Returns:
        Configured MockPlateSolver instance
    """
    presets = {
        "default": {
            "blind_timeout_sec": 30.0,
            "hint_timeout_sec": 5.0,
        },
        "fast": {
            "blind_timeout_sec": 5.0,
            "hint_timeout_sec": 1.0,
        },
        "slow": {
            "blind_timeout_sec": 60.0,
            "hint_timeout_sec": 15.0,
        },
        "unreliable": {
            "blind_timeout_sec": 30.0,
            "hint_timeout_sec": 5.0,
        },
    }

    config = presets.get(preset, presets["default"]).copy()
    config.update(kwargs)

    solver = MockPlateSolver(**config)

    # Apply preset-specific settings
    if preset == "unreliable":
        solver.set_success_probability(0.5)

    return solver
