"""
SEC3-3: Dependency pin tests.

Asserts that the aiohttp requirement (and its resolved lock entry, if present)
is pinned to a version that includes the security fixes shipped in 3.14.1+.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MIN_AIOHTTP = (3, 14, 1)


def _parse_version(text):
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    if not m:
        m = re.search(r"(\d+)\.(\d+)", text)
        if not m:
            return None
        return (int(m.group(1)), int(m.group(2)), 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def test_pyproject_aiohttp_pin():
    """pyproject.toml must require aiohttp >= 3.14.1."""
    text = (REPO_ROOT / "pyproject.toml").read_text()
    m = re.search(r'aiohttp\s*>=\s*([0-9][0-9.]*)', text)
    assert m, "aiohttp pin not found in pyproject.toml"
    version = _parse_version(m.group(1))
    assert version is not None
    assert version >= MIN_AIOHTTP, f"aiohttp pin {version} < {MIN_AIOHTTP}"


def test_services_requirements_aiohttp_pin():
    """services/requirements.txt must require aiohttp >= 3.14.1."""
    req = REPO_ROOT / "services" / "requirements.txt"
    if not req.exists():
        return
    line = next(
        (ln for ln in req.read_text().splitlines() if ln.strip().startswith("aiohttp")),
        None,
    )
    assert line is not None, "aiohttp not found in services/requirements.txt"
    m = re.search(r'>=\s*([0-9][0-9.]*)', line)
    assert m, f"aiohttp lower bound not found in: {line!r}"
    version = _parse_version(m.group(1))
    assert version is not None
    assert version >= MIN_AIOHTTP, f"aiohttp pin {version} < {MIN_AIOHTTP}"


def test_uv_lock_aiohttp_version():
    """If uv.lock is present, its resolved aiohttp version must be >= 3.14.1."""
    lock = REPO_ROOT / "uv.lock"
    if not lock.exists():
        return
    text = lock.read_text()
    # Find the aiohttp package block: name = "aiohttp" followed by version = "x.y.z"
    m = re.search(
        r'name\s*=\s*"aiohttp"\s*\n\s*version\s*=\s*"([0-9][0-9.]*)"',
        text,
    )
    if not m:
        # aiohttp may not be locked (e.g. optional extra not resolved); skip.
        return
    version = _parse_version(m.group(1))
    assert version is not None
    assert version >= MIN_AIOHTTP, f"locked aiohttp {version} < {MIN_AIOHTTP}"
