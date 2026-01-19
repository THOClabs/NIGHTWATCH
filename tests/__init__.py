"""
NIGHTWATCH Test Suite

This package contains all tests for the NIGHTWATCH observatory system.

Test Organization:
    tests/
    ├── __init__.py          # This file
    ├── integration/         # Integration tests (require simulators)
    │   ├── __init__.py
    │   └── test_device_layer.py
    └── unit/               # Unit tests (no external dependencies)
        └── __init__.py

Running Tests:
    # Run all tests
    pytest tests/

    # Run integration tests (requires docker-compose up)
    pytest tests/integration/

    # Run with coverage
    pytest tests/ --cov=services --cov-report=html

Requirements:
    pip install pytest pytest-asyncio pytest-timeout

Integration Test Setup:
    Before running integration tests, start the simulators:
        docker-compose -f docker/docker-compose.dev.yml up -d

    Verify simulators are running:
        curl http://localhost:11111/management/apiversions  # Alpaca
        echo ':' | nc -w 1 localhost 7624                   # INDI
"""
