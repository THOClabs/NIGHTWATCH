"""
Pytest Fixtures for NIGHTWATCH Testing.

Provides shared fixtures for unit and integration tests.
Import these fixtures by placing conftest.py in the tests directory
or by importing directly from tests.fixtures.

Usage:
    # In test files, fixtures are automatically available:
    async def test_mount_slew(mock_mount):
        await mock_mount.connect()
        await mock_mount.slew_to_coordinates(12.5, 45.0)
        assert mock_mount.is_slewing
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator

from tests.fixtures.mock_mount import MockMount
from tests.fixtures.mock_weather import MockWeather
from tests.fixtures.mock_camera import MockCamera
from tests.fixtures.mock_guider import MockGuider
from tests.fixtures.mock_focuser import MockFocuser
from tests.fixtures.mock_enclosure import MockEnclosure
from tests.fixtures.mock_power import MockPower
from tests.fixtures.mock_llm import MockLLM
from tests.fixtures.mock_stt import MockSTT
from tests.fixtures.mock_tts import MockTTS


# =============================================================================
# Hardware Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_mount() -> MockMount:
    """
    Provide a MockMount instance.

    Returns disconnected mount that can be configured before connecting.
    """
    mount = MockMount(simulate_delays=False)
    yield mount
    mount.reset()


@pytest_asyncio.fixture
async def connected_mount() -> AsyncGenerator[MockMount, None]:
    """
    Provide a connected MockMount instance.

    Automatically connects and disconnects.
    """
    mount = MockMount(simulate_delays=False)
    await mount.connect()
    yield mount
    await mount.disconnect()


@pytest.fixture
def mock_weather() -> MockWeather:
    """
    Provide a MockWeather instance with clear conditions.

    Returns disconnected weather service.
    """
    weather = MockWeather(initial_scenario="clear", simulate_delays=False)
    yield weather
    weather.reset()


@pytest_asyncio.fixture
async def connected_weather() -> AsyncGenerator[MockWeather, None]:
    """
    Provide a connected MockWeather instance.

    Automatically connects and disconnects.
    """
    weather = MockWeather(initial_scenario="clear", simulate_delays=False)
    await weather.connect()
    yield weather
    await weather.disconnect()


@pytest.fixture
def mock_camera() -> MockCamera:
    """
    Provide a MockCamera instance.

    Returns disconnected camera.
    """
    camera = MockCamera(simulate_delays=False, generate_images=False)
    yield camera
    camera.reset()


@pytest_asyncio.fixture
async def connected_camera() -> AsyncGenerator[MockCamera, None]:
    """
    Provide a connected MockCamera instance.

    Automatically connects and disconnects.
    """
    camera = MockCamera(simulate_delays=False, generate_images=False)
    await camera.connect()
    yield camera
    await camera.disconnect()


@pytest.fixture
def mock_guider() -> MockGuider:
    """
    Provide a MockGuider instance.

    Returns disconnected guider.
    """
    guider = MockGuider(simulate_delays=False)
    yield guider
    guider.reset()


@pytest_asyncio.fixture
async def connected_guider() -> AsyncGenerator[MockGuider, None]:
    """
    Provide a connected and calibrated MockGuider instance.

    Automatically connects, calibrates, and disconnects.
    """
    guider = MockGuider(simulate_delays=False)
    await guider.connect()
    await guider.start_looping()
    await guider.auto_select_star()
    await guider.calibrate()
    yield guider
    await guider.disconnect()


@pytest.fixture
def mock_focuser() -> MockFocuser:
    """
    Provide a MockFocuser instance.

    Returns disconnected focuser.
    """
    focuser = MockFocuser(simulate_delays=False)
    yield focuser
    focuser.reset()


@pytest_asyncio.fixture
async def connected_focuser() -> AsyncGenerator[MockFocuser, None]:
    """
    Provide a connected MockFocuser instance.

    Automatically connects and disconnects.
    """
    focuser = MockFocuser(simulate_delays=False)
    await focuser.connect()
    yield focuser
    await focuser.disconnect()


@pytest.fixture
def mock_enclosure() -> MockEnclosure:
    """
    Provide a MockEnclosure instance.

    Returns disconnected enclosure in closed state.
    """
    enclosure = MockEnclosure(simulate_delays=False)
    yield enclosure
    enclosure.reset()


@pytest_asyncio.fixture
async def connected_enclosure() -> AsyncGenerator[MockEnclosure, None]:
    """
    Provide a connected MockEnclosure instance.

    Automatically connects and disconnects.
    """
    enclosure = MockEnclosure(simulate_delays=False)
    await enclosure.connect()
    yield enclosure
    await enclosure.disconnect()


@pytest.fixture
def mock_power() -> MockPower:
    """
    Provide a MockPower instance.

    Returns disconnected power monitor on mains power.
    """
    power = MockPower(has_pdu=False, simulate_delays=False)
    yield power
    power.reset()


@pytest.fixture
def mock_power_with_pdu() -> MockPower:
    """
    Provide a MockPower instance with PDU control.

    Returns disconnected power monitor with PDU outlets.
    """
    power = MockPower(has_pdu=True, simulate_delays=False)
    yield power
    power.reset()


@pytest_asyncio.fixture
async def connected_power() -> AsyncGenerator[MockPower, None]:
    """
    Provide a connected MockPower instance.

    Automatically connects and disconnects.
    """
    power = MockPower(has_pdu=False, simulate_delays=False)
    await power.connect()
    yield power
    await power.disconnect()


# =============================================================================
# Voice Pipeline Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_llm() -> MockLLM:
    """
    Provide a MockLLM instance.

    Returns disconnected LLM with auto-response enabled.
    """
    llm = MockLLM(simulate_delays=False)
    yield llm
    llm.reset()


@pytest_asyncio.fixture
async def connected_llm() -> AsyncGenerator[MockLLM, None]:
    """
    Provide a connected MockLLM instance.

    Automatically connects and disconnects.
    """
    llm = MockLLM(simulate_delays=False)
    await llm.connect()
    yield llm
    await llm.disconnect()


@pytest.fixture
def mock_stt() -> MockSTT:
    """
    Provide a MockSTT instance.

    Returns disconnected STT service.
    """
    stt = MockSTT(simulate_delays=False)
    yield stt
    stt.reset()


@pytest_asyncio.fixture
async def connected_stt() -> AsyncGenerator[MockSTT, None]:
    """
    Provide a connected MockSTT instance.

    Automatically connects and disconnects.
    """
    stt = MockSTT(simulate_delays=False)
    await stt.connect()
    yield stt
    await stt.disconnect()


@pytest.fixture
def mock_tts() -> MockTTS:
    """
    Provide a MockTTS instance.

    Returns disconnected TTS service.
    """
    tts = MockTTS(simulate_delays=False)
    yield tts
    tts.reset()


@pytest_asyncio.fixture
async def connected_tts() -> AsyncGenerator[MockTTS, None]:
    """
    Provide a connected MockTTS instance.

    Automatically connects and disconnects.
    """
    tts = MockTTS(simulate_delays=False)
    await tts.connect()
    yield tts
    await tts.disconnect()


# =============================================================================
# Composite Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def observatory_mocks() -> AsyncGenerator[dict, None]:
    """
    Provide all connected observatory mock services.

    Returns a dictionary with all connected mocks for integration testing.
    """
    mocks = {
        "mount": MockMount(simulate_delays=False),
        "weather": MockWeather(initial_scenario="clear", simulate_delays=False),
        "camera": MockCamera(simulate_delays=False, generate_images=False),
        "guider": MockGuider(simulate_delays=False),
        "focuser": MockFocuser(simulate_delays=False),
        "enclosure": MockEnclosure(simulate_delays=False),
        "power": MockPower(has_pdu=False, simulate_delays=False),
    }

    # Connect all
    for mock in mocks.values():
        await mock.connect()

    yield mocks

    # Disconnect all
    for mock in mocks.values():
        await mock.disconnect()


@pytest_asyncio.fixture
async def voice_pipeline_mocks() -> AsyncGenerator[dict, None]:
    """
    Provide all connected voice pipeline mock services.

    Returns a dictionary with LLM, STT, and TTS mocks.
    """
    mocks = {
        "llm": MockLLM(simulate_delays=False),
        "stt": MockSTT(simulate_delays=False),
        "tts": MockTTS(simulate_delays=False),
    }

    # Connect all
    for mock in mocks.values():
        await mock.connect()

    yield mocks

    # Disconnect all
    for mock in mocks.values():
        await mock.disconnect()


@pytest_asyncio.fixture
async def full_system_mocks() -> AsyncGenerator[dict, None]:
    """
    Provide all connected mock services for full system testing.

    Returns a dictionary with all observatory and voice pipeline mocks.
    """
    mocks = {
        # Observatory
        "mount": MockMount(simulate_delays=False),
        "weather": MockWeather(initial_scenario="clear", simulate_delays=False),
        "camera": MockCamera(simulate_delays=False, generate_images=False),
        "guider": MockGuider(simulate_delays=False),
        "focuser": MockFocuser(simulate_delays=False),
        "enclosure": MockEnclosure(simulate_delays=False),
        "power": MockPower(has_pdu=False, simulate_delays=False),
        # Voice pipeline
        "llm": MockLLM(simulate_delays=False),
        "stt": MockSTT(simulate_delays=False),
        "tts": MockTTS(simulate_delays=False),
    }

    # Connect all
    for mock in mocks.values():
        await mock.connect()

    yield mocks

    # Disconnect all
    for mock in mocks.values():
        await mock.disconnect()


# =============================================================================
# Scenario Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def unsafe_weather() -> AsyncGenerator[MockWeather, None]:
    """
    Provide connected MockWeather with unsafe conditions.

    Sets weather to rainy scenario.
    """
    weather = MockWeather(initial_scenario="rain", simulate_delays=False)
    await weather.connect()
    yield weather
    await weather.disconnect()


@pytest_asyncio.fixture
async def low_battery_power() -> AsyncGenerator[MockPower, None]:
    """
    Provide connected MockPower with low battery.

    Sets battery to 20% (below safety threshold).
    """
    power = MockPower(has_pdu=False, simulate_delays=False)
    await power.connect()
    power.set_battery_percent(20.0)
    power.set_mains_present(False)
    yield power
    await power.disconnect()


@pytest_asyncio.fixture
async def parked_mount() -> AsyncGenerator[MockMount, None]:
    """
    Provide connected MockMount in parked state.
    """
    mount = MockMount(simulate_delays=False)
    await mount.connect()
    # Mount starts parked by default after connect
    yield mount
    await mount.disconnect()


@pytest_asyncio.fixture
async def tracking_mount() -> AsyncGenerator[MockMount, None]:
    """
    Provide connected MockMount that is tracking.
    """
    mount = MockMount(simulate_delays=False)
    await mount.connect()
    await mount.unpark()
    await mount.start_tracking()
    yield mount
    await mount.disconnect()
