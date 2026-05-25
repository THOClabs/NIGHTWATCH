"""
NIGHTWATCH Plate Solver Unit Tests

Step 119: Write unit tests for solver backends.
HWS-004: Adds coverage for the FITS-roundtrip / retry-with-larger-radius /
mount-sync / cancellation paths required by the modernization manual.
"""

import asyncio
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from astropy.io import fits

from services.astrometry.plate_solver import (
    PlateSolveHint,
    PlateSolver,
    SolveResult,
    SolverBackend,
    SolverConfig,
    SolveStatus,
)
from services.mount_control.lx200 import LX200Client


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
# HWS-004 — FITS-roundtrip / retry / mount-sync / cancellation
# ============================================================================


def _write_minimal_wcs_fits(
    path: Path,
    *,
    ra_deg: float,
    dec_deg: float,
    naxis1: int = 1000,
    naxis2: int = 1000,
    pixel_scale_arcsec: float = 1.0,
) -> None:
    """Write a minimal FITS file with a usable WCS centred at (ra, dec).

    Used by both the synthetic 'input image' and the synthetic '.wcs sidecar'
    that the mocked solve-field subprocess pretends to have produced.
    """
    cdelt_deg = pixel_scale_arcsec / 3600.0
    header = fits.Header()
    header["NAXIS"] = 2
    header["NAXIS1"] = naxis1
    header["NAXIS2"] = naxis2
    header["IMAGEW"] = naxis1
    header["IMAGEH"] = naxis2
    header["CTYPE1"] = "RA---TAN"
    header["CTYPE2"] = "DEC--TAN"
    header["CRPIX1"] = naxis1 / 2 + 0.5
    header["CRPIX2"] = naxis2 / 2 + 0.5
    header["CRVAL1"] = ra_deg
    header["CRVAL2"] = dec_deg
    # No rotation, square pixels — CD matrix is just diag(-cdelt, cdelt).
    # Negative CD1_1 mirrors the convention that RA increases right-to-left.
    header["CD1_1"] = -cdelt_deg
    header["CD1_2"] = 0.0
    header["CD2_1"] = 0.0
    header["CD2_2"] = cdelt_deg
    header["OBJCTRA"] = ra_deg
    header["OBJCTDEC"] = dec_deg

    # Need at least an empty data array for fits.writeto.
    hdu = fits.PrimaryHDU(header=header)
    hdu.writeto(path, overwrite=True)


class _FakeProcess:
    """Minimal stand-in for asyncio.subprocess.Process.

    Supports ``communicate`` (returning a configured (stdout, stderr) pair) and
    ``kill``. ``communicate`` may also be configured to invoke a side-effect
    callable BEFORE returning — this lets a test simulate solve-field writing
    its sidecar files mid-call.
    """

    def __init__(
        self,
        stdout: bytes = b"",
        stderr: bytes = b"",
        side_effect=None,
        delay: float = 0.0,
    ):
        self._stdout = stdout
        self._stderr = stderr
        self._side_effect = side_effect
        self._delay = delay
        self.kill_called = False
        self.returncode = 0

    async def communicate(self):
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._side_effect is not None:
            self._side_effect()
        return self._stdout, self._stderr

    def kill(self) -> None:
        self.kill_called = True
        self.returncode = -9


@pytest.fixture
def fits_image(tmp_path: Path) -> Path:
    """Synthetic input FITS frame with a known RA/Dec."""
    path = tmp_path / "frame.fits"
    _write_minimal_wcs_fits(path, ra_deg=12.345, dec_deg=45.678)
    return path


class TestFITSRoundtrip:
    """HWS-004 verify-bullet #1: solve-field WCS sidecar parses within 1 arcmin."""

    async def test_solve_field_success_matches_header_within_one_arcmin(
        self, fits_image: Path
    ):
        # Disable fallback so a single backend invocation is exercised.
        solver = PlateSolver(
            SolverConfig(fallback_solver=None, hint_timeout_sec=0.5)
        )

        wcs_path = fits_image.with_suffix(".wcs")
        solved_path = fits_image.with_suffix(".solved")

        def _write_sidecars():
            # Mock solve-field's side effect: produce .wcs + .solved
            _write_minimal_wcs_fits(wcs_path, ra_deg=12.345, dec_deg=45.678)
            solved_path.write_bytes(b"")

        proc = _FakeProcess(side_effect=_write_sidecars)
        with patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=proc),
        ):
            result = await solver.solve(
                str(fits_image),
                hint=PlateSolveHint(ra_deg=12.345, dec_deg=45.678, radius_deg=1.0),
            )

        assert result.status == SolveStatus.SUCCESS
        assert result.ra_deg is not None
        assert result.dec_deg is not None
        # 1 arcmin = 1/60 degree.
        assert abs(result.ra_deg - 12.345) < 1 / 60
        assert abs(result.dec_deg - 45.678) < 1 / 60
        assert result.backend_used == SolverBackend.ASTROMETRY_NET

    async def test_parse_wcs_rejects_garbage_header(self, tmp_path: Path):
        """Sanity check: a WCS file with no useful keywords must NOT report SUCCESS."""
        solver = PlateSolver(SolverConfig(fallback_solver=None))
        garbage = tmp_path / "garbage.wcs"
        # Valid empty FITS — no CRVAL/CD keywords.
        fits.PrimaryHDU().writeto(garbage, overwrite=True)

        result = await solver._parse_wcs(garbage, SolverBackend.ASTROMETRY_NET)

        assert result.status == SolveStatus.FAILED
        assert result.error_message is not None

    async def test_parse_wcs_rejects_out_of_range_crval(self, tmp_path: Path):
        """RA outside [0, 360] OR Dec outside [-90, 90] must be rejected."""
        solver = PlateSolver(SolverConfig(fallback_solver=None))
        bad = tmp_path / "bad.wcs"
        _write_minimal_wcs_fits(bad, ra_deg=99.0, dec_deg=200.0)  # bogus Dec
        result = await solver._parse_wcs(bad, SolverBackend.ASTROMETRY_NET)
        assert result.status == SolveStatus.FAILED


class TestRetryWithLargerRadius:
    """HWS-004 verify-bullet #2: FAILED on tight radius → retry with larger one."""

    async def test_retries_with_larger_radius_then_succeeds(
        self, fits_image: Path
    ):
        solver = PlateSolver(
            SolverConfig(
                fallback_solver=None,
                hint_timeout_sec=0.5,
                max_solve_attempts=3,
                radius_growth_factor=2.0,
                max_search_radius_deg=10.0,
            )
        )

        wcs_path = fits_image.with_suffix(".wcs")
        solved_path = fits_image.with_suffix(".solved")

        call_count = {"n": 0}
        observed_radii: list[float] = []

        async def _create_subprocess(*cmd, **_kwargs):
            call_count["n"] += 1
            # Extract --radius arg if present.
            cmd_list = list(cmd)
            if "--radius" in cmd_list:
                observed_radii.append(float(cmd_list[cmd_list.index("--radius") + 1]))

            if call_count["n"] == 1:
                # First attempt: solve-field "fails" (no .solved produced).
                return _FakeProcess()
            # Second attempt: succeed.
            return _FakeProcess(
                side_effect=lambda: (
                    _write_minimal_wcs_fits(wcs_path, ra_deg=12.345, dec_deg=45.678),
                    solved_path.write_bytes(b""),
                )
            )

        with patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=_create_subprocess),
        ):
            result = await solver.solve(
                str(fits_image),
                hint=PlateSolveHint(ra_deg=12.345, dec_deg=45.678, radius_deg=1.0),
            )

        assert result.status == SolveStatus.SUCCESS
        assert call_count["n"] == 2, "expected exactly one retry"
        assert len(observed_radii) == 2
        assert observed_radii[1] > observed_radii[0], (
            f"retry should grow radius: {observed_radii}"
        )
        assert observed_radii[1] == pytest.approx(2.0)

    async def test_terminal_failed_after_attempt_cap(
        self, fits_image: Path
    ):
        solver = PlateSolver(
            SolverConfig(
                fallback_solver=None,
                hint_timeout_sec=0.2,
                max_solve_attempts=2,
                radius_growth_factor=2.0,
                max_search_radius_deg=10.0,
            )
        )

        call_count = {"n": 0}

        async def _always_fail(*_cmd, **_kw):
            call_count["n"] += 1
            return _FakeProcess()

        with patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=_always_fail),
        ):
            result = await solver.solve(
                str(fits_image),
                hint=PlateSolveHint(ra_deg=12.345, dec_deg=45.678, radius_deg=1.0),
            )

        assert result.status == SolveStatus.FAILED
        assert call_count["n"] == 2, "exactly max_solve_attempts attempts"

    async def test_retry_radius_capped_at_max(self, fits_image: Path):
        """Growth factor must not push radius past max_search_radius_deg."""
        solver = PlateSolver(
            SolverConfig(
                fallback_solver=None,
                hint_timeout_sec=0.2,
                max_solve_attempts=3,
                radius_growth_factor=10.0,
                max_search_radius_deg=3.0,
            )
        )

        observed_radii: list[float] = []

        async def _fail(*cmd, **_kw):
            cmd_list = list(cmd)
            if "--radius" in cmd_list:
                observed_radii.append(
                    float(cmd_list[cmd_list.index("--radius") + 1])
                )
            return _FakeProcess()

        with patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=_fail),
        ):
            await solver.solve(
                str(fits_image),
                hint=PlateSolveHint(ra_deg=12.345, dec_deg=45.678, radius_deg=1.0),
            )

        assert all(r <= 3.0 + 1e-9 for r in observed_radii), observed_radii
        # And we should hit the cap on attempt 2 (1 * 10 = 10 -> capped 3.0).
        assert observed_radii[-1] == pytest.approx(3.0)


class TestMountSync:
    """HWS-004 verify-bullet #3: solve_and_sync must invoke mount sync."""

    async def test_solve_and_sync_invokes_sync_to_coordinates(
        self, fits_image: Path
    ):
        solver = PlateSolver(
            SolverConfig(fallback_solver=None, hint_timeout_sec=0.5)
        )

        wcs_path = fits_image.with_suffix(".wcs")
        solved_path = fits_image.with_suffix(".solved")

        proc = _FakeProcess(
            side_effect=lambda: (
                _write_minimal_wcs_fits(wcs_path, ra_deg=12.345, dec_deg=45.678),
                solved_path.write_bytes(b""),
            )
        )

        mount = MagicMock()
        mount.sync_to_coordinates = AsyncMock(return_value=True)

        with patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=proc),
        ):
            result = await solver.solve_and_sync(
                str(fits_image),
                mount,
                hint=PlateSolveHint(ra_deg=12.345, dec_deg=45.678, radius_deg=1.0),
            )

        assert result.status == SolveStatus.SUCCESS
        mount.sync_to_coordinates.assert_awaited_once()
        called_ra, called_dec = mount.sync_to_coordinates.call_args.args
        assert abs(called_ra - 12.345) < 1 / 60
        assert abs(called_dec - 45.678) < 1 / 60

    async def test_solve_and_sync_skips_mount_when_solve_fails(
        self, fits_image: Path
    ):
        solver = PlateSolver(SolverConfig(fallback_solver=None, hint_timeout_sec=0.2))
        mount = MagicMock()
        mount.sync_to_coordinates = AsyncMock()

        with patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=_FakeProcess()),
        ):
            result = await solver.solve_and_sync(
                str(fits_image),
                mount,
                hint=PlateSolveHint(ra_deg=12.345, dec_deg=45.678, radius_deg=1.0),
            )

        assert result.status == SolveStatus.FAILED
        mount.sync_to_coordinates.assert_not_awaited()

    async def test_solve_and_sync_warns_when_mount_rejects_sync(
        self, fits_image: Path, caplog: pytest.LogCaptureFixture
    ):
        """HWS-004 review Important #4: mount rejection must surface as a
        WARNING log, not be silently swallowed under the success message."""
        solver = PlateSolver(
            SolverConfig(fallback_solver=None, hint_timeout_sec=0.5)
        )

        wcs_path = fits_image.with_suffix(".wcs")
        solved_path = fits_image.with_suffix(".solved")

        proc = _FakeProcess(
            side_effect=lambda: (
                _write_minimal_wcs_fits(wcs_path, ra_deg=12.345, dec_deg=45.678),
                solved_path.write_bytes(b""),
            )
        )

        mount = MagicMock()
        # Mount silently rejects the sync — e.g. parked, busy, in error state.
        mount.sync_to_coordinates = AsyncMock(return_value=False)

        with caplog.at_level(logging.WARNING, logger="NIGHTWATCH.Astrometry"), patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=proc),
        ):
            result = await solver.solve_and_sync(
                str(fits_image),
                mount,
                hint=PlateSolveHint(ra_deg=12.345, dec_deg=45.678, radius_deg=1.0),
            )

        assert result.status == SolveStatus.SUCCESS
        mount.sync_to_coordinates.assert_awaited_once()
        rejected = [r for r in caplog.records if "REJECTED" in r.getMessage()]
        assert rejected, (
            f"expected WARNING containing 'REJECTED' but got: "
            f"{[r.getMessage() for r in caplog.records]}"
        )
        assert rejected[0].levelno == logging.WARNING


class TestLX200SyncToCoordinates:
    """The Protocol's deg→string conversion must reach LX200's :Sr/:Sd commands."""

    async def test_lx200_sync_to_coordinates_emits_Sr_Sd_CM(self):
        client = LX200Client.__new__(LX200Client)
        sent: list[str] = []

        def _record(cmd: str):
            sent.append(cmd)
            # CM (sync) returns "static name#" on success; Sr/Sd return "1".
            if cmd.startswith("Sr") or cmd.startswith("Sd"):
                return "1"
            if cmd == "CM":
                return "Coordinates matched."
            return ""

        client._send_command = _record  # type: ignore[assignment]

        ok = await client.sync_to_coordinates(12.345, 45.678)

        assert ok is True
        # Expect exactly one Sr*, one Sd*, then CM.
        sr = [s for s in sent if s.startswith("Sr")]
        sd = [s for s in sent if s.startswith("Sd")]
        assert len(sr) == 1
        assert len(sd) == 1
        assert "CM" in sent
        # RA value: 12.345 deg = 0.823 h ~ "00:49:22.80"
        assert sr[0].startswith("Sr00:")
        # Dec value: +45.67…° → starts with "+45*"
        assert sd[0].startswith("Sd+45*")


class TestLX200StringHelperRollover:
    """HWS-004 review Critical #1: rollover at the print-precision boundary.

    The naive ``ss >= 60.0 - 1e-6`` guard misses values like ``59.999976``
    that the ``f"{ss:05.2f}"`` formatter rounds up to ``"60.00"`` — producing
    wire strings like ``05:59:60.00`` that the mount rejects silently.
    The fix is to round to the printable precision BEFORE the rollover
    check so the guard sees the same value the formatter will emit.
    """

    @staticmethod
    def _parse_ra_lx200(s: str) -> float:
        """Parse ``HH:MM:SS.ss`` back to decimal degrees."""
        hh_s, mm_s, ss_s = s.split(":")
        hours = int(hh_s) + int(mm_s) / 60.0 + float(ss_s) / 3600.0
        return hours * 15.0

    @staticmethod
    def _parse_dec_lx200(s: str) -> float:
        """Parse ``sDD*MM:SS`` back to decimal degrees."""
        sign = -1.0 if s.startswith("-") else 1.0
        body = s[1:] if s[0] in "+-" else s
        dd_s, rest = body.split("*")
        mm_s, ss_s = rest.split(":")
        deg = int(dd_s) + int(mm_s) / 60.0 + int(ss_s) / 3600.0
        return sign * deg

    @pytest.mark.parametrize(
        "ra_deg",
        [
            89.9999999,
            14.999999722,
            0.0,
            359.999999,
            180.0,
            45.123456789,
        ],
    )
    def test_ra_helper_never_emits_seconds_or_minutes_at_60(self, ra_deg: float):
        s = LX200Client._ra_deg_to_lx200(ra_deg)
        hh_s, mm_s, ss_s = s.split(":")
        assert 0 <= int(hh_s) < 24, f"hours out of range in {s!r}"
        assert 0 <= int(mm_s) < 60, f"minutes hit 60 in {s!r}"
        assert float(ss_s) < 60.0, f"seconds hit 60 in {s!r}"

    @pytest.mark.parametrize(
        "ra_deg",
        [
            89.9999999,
            14.999999722,
            0.0,
            359.999999,
            180.0,
            45.123456789,
        ],
    )
    def test_ra_helper_round_trips_within_one_arcsec(self, ra_deg: float):
        s = LX200Client._ra_deg_to_lx200(ra_deg)
        recovered = self._parse_ra_lx200(s)
        # Normalize input the same way the helper does.
        expected = ra_deg % 360.0
        # RA wraps at 360 — treat 359.9999… ↔ 0.0000… as equivalent.
        raw = abs(recovered - expected)
        diff = min(raw, 360.0 - raw)
        assert diff < 1.0 / 3600.0, (
            f"round-trip failed: {ra_deg} → {s!r} → {recovered} (diff={diff})"
        )

    @pytest.mark.parametrize(
        "dec_deg",
        [
            89.9999999,
            -89.9999999,
            0.0,
            -0.5,
            45.0,
            -45.0,
        ],
    )
    def test_dec_helper_never_emits_seconds_or_minutes_at_60(self, dec_deg: float):
        s = LX200Client._dec_deg_to_lx200(dec_deg)
        # sDD*MM:SS — split off sign first.
        body = s[1:] if s[0] in "+-" else s
        dd_s, rest = body.split("*")
        mm_s, ss_s = rest.split(":")
        assert int(mm_s) < 60, f"minutes hit 60 in {s!r}"
        assert int(ss_s) < 60, f"seconds hit 60 in {s!r}"
        # Dec dd must stay in [0, 90] after the rollover ripple — anything
        # above 90 means a rollover walked past the pole.
        assert int(dd_s) <= 90, f"degrees walked past pole in {s!r}"

    @pytest.mark.parametrize(
        "dec_deg",
        [
            89.9999999,
            -89.9999999,
            0.0,
            -0.5,
            45.0,
            -45.0,
        ],
    )
    def test_dec_helper_round_trips_within_one_arcsec(self, dec_deg: float):
        s = LX200Client._dec_deg_to_lx200(dec_deg)
        recovered = self._parse_dec_lx200(s)
        assert abs(recovered - dec_deg) < 1.0 / 3600.0, (
            f"round-trip failed: {dec_deg} → {s!r} → {recovered}"
        )


class TestCancellation:
    """HWS-004: cancel() mid-solve must set status=CANCELLED, not TIMEOUT."""

    async def test_cancel_mid_solve_sets_cancelled_status(self, fits_image: Path):
        solver = PlateSolver(
            SolverConfig(fallback_solver=None, hint_timeout_sec=5.0)
        )

        # A long-running subprocess that we cancel before it finishes.
        proc = _FakeProcess(delay=0.5)

        with patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=proc),
        ):
            solve_task = asyncio.create_task(solver.solve(str(fits_image)))
            # Yield once so the subprocess is registered as the current process.
            await asyncio.sleep(0.05)
            await solver.cancel()
            result = await solve_task

        assert proc.kill_called is True
        assert result.status == SolveStatus.CANCELLED


# ============================================================================
# Run Configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
