# NIGHTWATCH Test Fixtures

Mock implementations of observatory services for testing without hardware.

## Overview

This package provides comprehensive mock implementations for all NIGHTWATCH services, enabling:

- **Unit Testing**: Test individual components in isolation
- **Integration Testing**: Test service interactions without hardware
- **Error Simulation**: Test failure handling with error injection
- **Scenario Testing**: Test specific conditions (weather, power, etc.)

## Available Fixtures

### Hardware Mocks

| Fixture | Description | Key Features |
|---------|-------------|--------------|
| `MockMount` | Telescope mount controller | Slew, track, park/unpark, position queries |
| `MockWeather` | Weather station | Preset scenarios, condition updates, safety evaluation |
| `MockCamera` | CCD/CMOS camera | Exposure simulation, settings, synthetic images |
| `MockGuider` | PHD2 guiding service | Calibration, guiding, dithering, RMS simulation |
| `MockFocuser` | Motor focuser | Position control, temperature compensation |
| `MockEnclosure` | Roll-off roof/dome | Open/close, safety interlocks, position tracking |
| `MockPower` | UPS/PDU monitor | Battery state, outlet control, power scenarios |

### Voice Pipeline Mocks

| Fixture | Description | Key Features |
|---------|-------------|--------------|
| `MockLLM` | Local LLM inference | Response generation, tool calls, intent recognition |
| `MockSTT` | Speech-to-text | Transcription, wake word detection, continuous listening |
| `MockTTS` | Text-to-speech | Synthesis, playback, voice configuration |

## Quick Start

### Using Pytest Fixtures

The easiest way to use mocks is through pytest fixtures. Copy `conftest.py` to your test directory or import fixtures directly:

```python
import pytest

# Fixtures are automatically available when conftest.py is present
async def test_mount_slew(connected_mount):
    """Test slewing to coordinates."""
    await connected_mount.slew_to_coordinates(12.5, 45.0)
    assert connected_mount.is_slewing

async def test_weather_check(connected_weather):
    """Test weather safety check."""
    is_safe = await connected_weather.is_safe_for_observing()
    assert is_safe  # Default is clear weather
```

### Direct Import

```python
from tests.fixtures import MockMount, MockWeather

async def test_custom_scenario():
    mount = MockMount(simulate_delays=False)
    weather = MockWeather(initial_scenario="rain")

    await mount.connect()
    await weather.connect()

    # Test your logic
    assert not await weather.is_safe_for_observing()
```

## Fixture Categories

### Basic Fixtures (disconnected)

These return fresh mock instances that need explicit connection:

- `mock_mount`, `mock_weather`, `mock_camera`, etc.
- Use when you need to configure the mock before connecting

### Connected Fixtures

These automatically connect and disconnect:

- `connected_mount`, `connected_weather`, `connected_camera`, etc.
- Use for most tests where you just need a working service

### Composite Fixtures

These provide multiple connected services:

- `observatory_mocks`: All hardware mocks (mount, weather, camera, etc.)
- `voice_pipeline_mocks`: LLM, STT, TTS mocks
- `full_system_mocks`: All mocks for end-to-end testing

### Scenario Fixtures

Pre-configured for specific test scenarios:

- `unsafe_weather`: Weather set to rainy conditions
- `low_battery_power`: Power with 20% battery, on battery
- `parked_mount`: Mount in parked state
- `tracking_mount`: Mount tracking at sidereal rate

## Error Injection

All mocks support error injection for testing failure scenarios:

```python
async def test_connection_failure(mock_mount):
    """Test handling of connection failure."""
    mock_mount.inject_connect_error(True)

    with pytest.raises(ConnectionError):
        await mock_mount.connect()

async def test_timeout_handling(connected_camera):
    """Test camera timeout handling."""
    connected_camera.inject_timeout(True)

    with pytest.raises(TimeoutError):
        await connected_camera.capture()
```

### Available Error Injections

| Mock | Error Methods |
|------|---------------|
| All | `inject_connect_error()` |
| MockMount | `inject_slew_error()`, `inject_timeout()` |
| MockCamera | `inject_capture_error()`, `inject_timeout()` |
| MockWeather | `inject_timeout()` |
| MockGuider | `inject_calibrate_error()`, `inject_guide_error()`, `inject_star_lost()` |
| MockFocuser | `inject_move_error()`, `inject_stall()` |
| MockEnclosure | `inject_open_error()`, `inject_close_error()`, `inject_motor_stall()` |
| MockPower | `inject_read_error()` |
| MockLLM | `inject_generate_error()`, `inject_timeout()` |
| MockSTT | `inject_transcribe_error()`, `inject_timeout()`, `inject_noise()` |
| MockTTS | `inject_synthesize_error()`, `inject_playback_error()` |

## Weather Scenarios

MockWeather includes preset scenarios:

```python
# Available scenarios
weather.set_scenario("clear")        # Safe conditions
weather.set_scenario("partly_cloudy")  # Still safe
weather.set_scenario("cloudy")       # Unsafe - clouds
weather.set_scenario("high_wind")    # Unsafe - wind
weather.set_scenario("humid")        # Unsafe - humidity
weather.set_scenario("rain")         # Unsafe - rain
weather.set_scenario("storm")        # Unsafe - severe
```

## Callbacks

Most mocks support callbacks for event notification:

```python
async def test_with_callbacks(mock_mount):
    positions = []

    def on_position(pos):
        positions.append(pos)

    mock_mount.set_position_callback(on_position)
    await mock_mount.connect()
    await mock_mount.slew_to_coordinates(10.0, 45.0)

    # positions list now contains updates from slew
```

## Configuration

### Disabling Delays

All mocks accept `simulate_delays=False` for faster testing:

```python
# Fast tests without simulated timing
mount = MockMount(simulate_delays=False)
camera = MockCamera(simulate_delays=False)
```

### Custom Timing

Configure timing for integration tests:

```python
mount = MockMount(
    slew_rate=10.0,  # Degrees per second
    simulate_delays=True
)

llm = MockLLM(
    generation_time_sec=0.5,  # Response generation time
    simulate_delays=True
)
```

## Best Practices

1. **Use `simulate_delays=False`** for unit tests to keep them fast
2. **Use connected fixtures** when possible for cleaner test code
3. **Reset mocks** after tests that modify state: `mock.reset()`
4. **Use error injection** to test all failure paths
5. **Use composite fixtures** for integration tests
6. **Check properties** like `is_connected`, `is_slewing` for state verification

## Example Test File

```python
"""Example test file using NIGHTWATCH fixtures."""

import pytest
from tests.fixtures import MockMount, MockWeather

class TestMountOperations:
    """Tests for mount operations."""

    async def test_slew_to_target(self, connected_mount):
        """Test slewing to coordinates."""
        await connected_mount.slew_to_coordinates(12.5, 45.0)
        ra, dec = connected_mount.get_ra_dec()
        assert abs(ra - 12.5) < 0.01
        assert abs(dec - 45.0) < 0.01

    async def test_park_mount(self, connected_mount):
        """Test parking the mount."""
        await connected_mount.unpark()
        await connected_mount.park()
        assert connected_mount.is_parked

    async def test_weather_safety_check(self, connected_mount, unsafe_weather):
        """Test that slew is blocked in unsafe weather."""
        # Your safety logic would check weather before slew
        is_safe = await unsafe_weather.is_safe_for_observing()
        assert not is_safe

class TestVoicePipeline:
    """Tests for voice pipeline."""

    async def test_transcription(self, connected_stt):
        """Test speech transcription."""
        connected_stt.set_transcription("Go to Andromeda")
        result = await connected_stt.transcribe(b"audio_data")
        assert result.text == "Go to Andromeda"

    async def test_llm_tool_call(self, connected_llm):
        """Test LLM generates tool call."""
        response = await connected_llm.generate("Go to M31")
        assert response.has_tool_calls
```
