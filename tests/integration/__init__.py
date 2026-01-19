"""
NIGHTWATCH Integration Tests

Integration tests for the device layer, requiring simulator backends.

These tests verify communication with:
    - ASCOM Alpaca simulators (telescope, camera, focuser, filter wheel)
    - INDI simulators (when implemented)

Setup:
    Start simulators before running tests:
        docker-compose -f docker/docker-compose.dev.yml up -d

    Verify Alpaca is running:
        curl http://localhost:11111/management/apiversions

Running:
    pytest tests/integration/ -v

Markers:
    @pytest.mark.alpaca  - Tests requiring Alpaca simulator
    @pytest.mark.indi    - Tests requiring INDI simulator
    @pytest.mark.slow    - Tests that take > 5 seconds
"""

import pytest


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "alpaca: requires Alpaca simulator")
    config.addinivalue_line("markers", "indi: requires INDI simulator")
    config.addinivalue_line("markers", "slow: slow running tests")
