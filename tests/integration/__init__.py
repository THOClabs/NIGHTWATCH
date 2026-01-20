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
import subprocess
import time
import os
from typing import Optional, List
from pathlib import Path


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "alpaca: requires Alpaca simulator")
    config.addinivalue_line("markers", "indi: requires INDI simulator")
    config.addinivalue_line("markers", "slow: slow running tests")


# =============================================================================
# Simulator Helpers (Steps 571-572)
# =============================================================================

class SimulatorManager:
    """
    Helper class for managing Docker-based simulators (Steps 571-572).

    Provides methods to start, stop, and check simulator status.
    """

    def __init__(self, compose_file: Optional[str] = None):
        """
        Initialize simulator manager.

        Args:
            compose_file: Path to docker-compose file (default: docker/docker-compose.dev.yml)
        """
        self.project_root = Path(__file__).parent.parent.parent
        self.compose_file = compose_file or str(self.project_root / "docker" / "docker-compose.dev.yml")
        self._running = False

    def start(
        self,
        services: Optional[List[str]] = None,
        timeout: int = 60,
        wait_healthy: bool = True
    ) -> bool:
        """
        Start simulators (Step 571).

        Args:
            services: Specific services to start (default: all)
            timeout: Timeout in seconds for startup
            wait_healthy: Wait for health checks to pass

        Returns:
            True if simulators started successfully
        """
        if not os.path.exists(self.compose_file):
            print(f"Warning: Compose file not found: {self.compose_file}")
            return False

        cmd = ["docker-compose", "-f", self.compose_file, "up", "-d"]
        if services:
            cmd.extend(services)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                print(f"Failed to start simulators: {result.stderr}")
                return False

            self._running = True

            if wait_healthy:
                return self._wait_for_healthy(timeout)

            return True

        except subprocess.TimeoutExpired:
            print(f"Simulator startup timed out after {timeout}s")
            return False
        except FileNotFoundError:
            print("docker-compose not found - Docker may not be installed")
            return False
        except Exception as e:
            print(f"Error starting simulators: {e}")
            return False

    def stop(self, timeout: int = 30) -> bool:
        """
        Stop simulators (Step 572).

        Args:
            timeout: Timeout in seconds for shutdown

        Returns:
            True if simulators stopped successfully
        """
        if not os.path.exists(self.compose_file):
            return True  # Nothing to stop

        cmd = ["docker-compose", "-f", self.compose_file, "down"]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            self._running = False
            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print(f"Simulator shutdown timed out after {timeout}s")
            return False
        except Exception as e:
            print(f"Error stopping simulators: {e}")
            return False

    def is_running(self) -> bool:
        """Check if simulators are running."""
        if not os.path.exists(self.compose_file):
            return False

        try:
            result = subprocess.run(
                ["docker-compose", "-f", self.compose_file, "ps", "-q"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    def _wait_for_healthy(self, timeout: int) -> bool:
        """Wait for all services to be healthy."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    ["docker-compose", "-f", self.compose_file, "ps"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                # Check if all services are up
                if "Up" in result.stdout and "(unhealthy)" not in result.stdout:
                    return True

            except Exception:
                pass

            time.sleep(2)

        return False

    def check_alpaca(self, host: str = "localhost", port: int = 11111) -> bool:
        """Check if Alpaca simulator is responding."""
        import urllib.request
        try:
            url = f"http://{host}:{port}/management/apiversions"
            with urllib.request.urlopen(url, timeout=5) as response:
                return response.status == 200
        except Exception:
            return False

    def check_indi(self, host: str = "localhost", port: int = 7624) -> bool:
        """Check if INDI server is responding."""
        import socket
        try:
            with socket.create_connection((host, port), timeout=5):
                return True
        except Exception:
            return False


# Global simulator manager instance
_simulator_manager: Optional[SimulatorManager] = None


def get_simulator_manager() -> SimulatorManager:
    """Get or create the global simulator manager."""
    global _simulator_manager
    if _simulator_manager is None:
        _simulator_manager = SimulatorManager()
    return _simulator_manager


def start_simulators(services: Optional[List[str]] = None, timeout: int = 60) -> bool:
    """
    Convenience function to start simulators (Step 571).

    Args:
        services: Specific services to start (default: all)
        timeout: Timeout in seconds

    Returns:
        True if started successfully
    """
    return get_simulator_manager().start(services, timeout)


def stop_simulators(timeout: int = 30) -> bool:
    """
    Convenience function to stop simulators (Step 572).

    Args:
        timeout: Timeout in seconds

    Returns:
        True if stopped successfully
    """
    return get_simulator_manager().stop(timeout)


def simulators_running() -> bool:
    """Check if simulators are running."""
    return get_simulator_manager().is_running()


# Pytest fixtures for simulator management
@pytest.fixture(scope="session")
def simulator_manager():
    """Provide a simulator manager for the test session."""
    return get_simulator_manager()


@pytest.fixture(scope="session")
def simulators(simulator_manager):
    """
    Start simulators for the test session and stop after.

    This fixture starts all simulators before tests run and
    stops them after all tests complete.
    """
    started = simulator_manager.start()
    yield simulator_manager
    if started:
        simulator_manager.stop()


@pytest.fixture
def alpaca_available(simulator_manager):
    """Skip test if Alpaca simulator is not available."""
    if not simulator_manager.check_alpaca():
        pytest.skip("Alpaca simulator not available")


@pytest.fixture
def indi_available(simulator_manager):
    """Skip test if INDI server is not available."""
    if not simulator_manager.check_indi():
        pytest.skip("INDI server not available")
