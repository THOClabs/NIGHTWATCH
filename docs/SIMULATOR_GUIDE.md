# NIGHTWATCH Simulator Guide

This guide explains how to use simulators for testing and development without physical hardware.

## Overview

NIGHTWATCH supports several simulator backends:
- **ASCOM Alpaca Simulators** - Network-based device simulation
- **INDI Simulators** - Linux telescope simulation
- **Mock Fixtures** - Python test fixtures for unit testing

## Quick Start

### Using Docker Compose (Recommended)

Start all simulators with one command:

```bash
cd /opt/nightwatch
docker compose -f docker/docker-compose.dev.yml up -d
```

This starts:
- Alpaca Telescope Simulator (port 11111)
- Alpaca Focuser Simulator
- Alpaca Camera Simulator

### Verify Simulators Running

```bash
# Check Alpaca API
curl http://localhost:11111/management/apiversions

# List connected devices
curl http://localhost:11111/management/v1/configureddevices
```

## ASCOM Alpaca Simulators

### Starting Alpaca Simulators

```bash
# Pull and run the official ASCOM simulator image
docker run -d \
  --name alpaca-simulators \
  -p 11111:11111 \
  ghcr.io/ascominitiative/alpaca-simulators:latest
```

### Available Simulated Devices

| Device Type | Device Number | Description |
|-------------|---------------|-------------|
| Telescope | 0 | German Equatorial Mount |
| Focuser | 0 | Motorized Focuser |
| Camera | 0 | CCD Camera |
| FilterWheel | 0 | 8-Position Filter Wheel |
| Dome | 0 | Observatory Dome |
| SafetyMonitor | 0 | Safety Monitor |

### Configuring NIGHTWATCH for Alpaca

Edit `/etc/nightwatch/config.yaml`:

```yaml
mount:
  type: "alpaca"
  host: "localhost"
  port: 11111
  device_number: 0

focuser:
  type: "alpaca"
  host: "localhost"
  port: 11111
  device_number: 0
```

### Alpaca Web Interface

Access the simulator control panel at:
```
http://localhost:11111/setup
```

From here you can:
- Configure device properties
- Simulate error conditions
- View device state

## INDI Simulators

### Starting INDI Server with Simulators

```bash
# Run INDI server with telescope simulator
docker run -d \
  --name indi-server \
  -p 7624:7624 \
  indilib/indi-full:latest \
  indiserver indi_simulator_telescope indi_simulator_ccd indi_simulator_focus
```

### Available INDI Simulators

| Driver | Description |
|--------|-------------|
| `indi_simulator_telescope` | Telescope mount simulator |
| `indi_simulator_ccd` | CCD camera simulator |
| `indi_simulator_focus` | Focuser simulator |
| `indi_simulator_wheel` | Filter wheel simulator |
| `indi_simulator_dome` | Dome/roof simulator |
| `indi_simulator_gps` | GPS receiver simulator |

### Configuring NIGHTWATCH for INDI

```yaml
mount:
  type: "indi"
  host: "localhost"
  port: 7624
  device_name: "Telescope Simulator"
```

### Using KStars/Ekos with Simulators

For visual testing with a GUI:

```bash
# Install KStars (Ubuntu)
sudo apt install kstars

# Launch KStars
kstars &
```

Connect to INDI simulators through Ekos.

## Mock Fixtures for Testing

### Using pytest Fixtures

The test fixtures provide Python mock objects:

```python
import pytest
from tests.fixtures import MockMount, MockWeather

async def test_slew_operation(connected_mount):
    """Test slewing with mock mount."""
    await connected_mount.slew_to_coordinates(12.5, 45.0)
    assert connected_mount.is_slewing

async def test_weather_safety(connected_weather):
    """Test weather safety check."""
    is_safe = await connected_weather.is_safe_for_observing()
    assert is_safe
```

### Available Mock Fixtures

| Fixture | Description |
|---------|-------------|
| `mock_mount` | Disconnected mount mock |
| `connected_mount` | Connected mount mock |
| `mock_weather` | Weather service mock |
| `connected_weather` | Connected weather mock |
| `mock_camera` | Camera mock |
| `mock_guider` | PHD2 guider mock |
| `mock_focuser` | Focuser mock |
| `mock_enclosure` | Roof/dome mock |
| `mock_power` | UPS/power mock |
| `mock_llm` | LLM inference mock |
| `mock_stt` | Speech-to-text mock |
| `mock_tts` | Text-to-speech mock |

### Scenario Fixtures

Pre-configured scenarios for testing edge cases:

```python
async def test_unsafe_weather(unsafe_weather):
    """Test behavior in unsafe conditions."""
    is_safe = await unsafe_weather.is_safe_for_observing()
    assert not is_safe

async def test_low_battery(low_battery_power):
    """Test low battery response."""
    battery = low_battery_power.get_battery_percent()
    assert battery < 25
```

### Error Injection

Test failure handling:

```python
async def test_connection_failure(mock_mount):
    """Test handling of connection failure."""
    mock_mount.inject_connect_error(True)

    with pytest.raises(ConnectionError):
        await mock_mount.connect()
```

## Running Integration Tests

### With Alpaca Simulators

```bash
# Start simulators
docker compose -f docker/docker-compose.dev.yml up -d alpaca-simulators

# Wait for startup
sleep 10

# Run integration tests
pytest tests/integration/ -v -m alpaca

# Stop simulators
docker compose -f docker/docker-compose.dev.yml down
```

### With Mock Fixtures Only

```bash
# No Docker needed - uses Python mocks
pytest tests/unit/ -v
```

## Simulating Conditions

### Weather Scenarios

Using mock fixtures:

```python
# Set weather to rainy (unsafe)
mock_weather.set_scenario("rain")

# Set weather to high wind
mock_weather.set_scenario("high_wind")

# Available scenarios:
# - "clear" (default, safe)
# - "partly_cloudy" (safe)
# - "cloudy" (unsafe)
# - "high_wind" (unsafe)
# - "humid" (unsafe)
# - "rain" (unsafe)
# - "storm" (unsafe)
```

### Mount States

```python
# Simulate parked mount
mock_mount.set_parked(True)

# Simulate tracking
await mock_mount.start_tracking()

# Simulate slewing
await mock_mount.slew_to_coordinates(10.0, 45.0)
```

### Error Conditions

```python
# Simulate timeout
mock_mount.inject_timeout(True)

# Simulate slew error
mock_mount.inject_slew_error(True)

# Simulate calibration failure
mock_guider.inject_calibrate_error(True)
```

## Development Workflow

### 1. Unit Testing (Fast)

```bash
# Uses mock fixtures, no external dependencies
pytest tests/unit/ -v --tb=short
```

### 2. Integration Testing (Moderate)

```bash
# Start Docker simulators
docker compose -f docker/docker-compose.dev.yml up -d

# Run integration tests
pytest tests/integration/ -v

# Clean up
docker compose -f docker/docker-compose.dev.yml down
```

### 3. End-to-End Testing (Full)

```bash
# Start all services
docker compose -f docker/docker-compose.dev.yml up -d

# Run E2E tests
pytest tests/e2e/ -v

# Or manual testing with voice
python -m nightwatch.main --config config/dev.yaml
```

## Troubleshooting

### Simulators Won't Start

```bash
# Check Docker is running
docker info

# Check for port conflicts
netstat -tulpn | grep 11111

# View simulator logs
docker logs alpaca-simulators
```

### Connection Refused

```bash
# Verify simulator is listening
curl -v http://localhost:11111/management/apiversions

# Check firewall
sudo ufw status
```

### Tests Timing Out

```bash
# Increase test timeout
pytest tests/integration/ -v --timeout=120

# Check simulator responsiveness
curl -w "@curl-format.txt" http://localhost:11111/api/v1/telescope/0/connected
```

## Performance Notes

- **Mock Fixtures**: Fastest, ~0ms per operation
- **Alpaca Simulators**: Fast, ~10-50ms per operation
- **INDI Simulators**: Moderate, ~50-200ms per operation

Use `simulate_delays=False` in mock fixtures for fastest tests:

```python
mount = MockMount(simulate_delays=False)
```
