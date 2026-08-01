"""Smoke tests for the NIGHTWATCH main entry point.

These tests exercise the real boot path (config loading, logging setup) in
dry-run mode. They intentionally do NOT mock setup_logging/load_config so a
regression in the boot sequence fails the suite.
"""

from nightwatch.main import main


def test_boot_dry_run_returns_zero(capsys):
    assert main(["--dry-run"]) == 0
    assert "Configuration is valid" in capsys.readouterr().out


def test_boot_dry_run_with_log_level():
    assert main(["--dry-run", "--log-level", "DEBUG"]) == 0


def test_boot_simulator_dry_run_returns_zero():
    assert main(["--simulator", "--dry-run"]) == 0
