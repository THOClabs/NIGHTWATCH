# NIGHTWATCH Hardware Integration Test Plan

**Document:** Step 639 - Hardware Integration Test Plan
**Version:** 0.1.0
**Date:** 2025-01-20

## Overview

This document describes the hardware integration testing procedures for NIGHTWATCH v0.1. These tests verify communication and functionality with real observatory equipment before deployment.

## Prerequisites

### Equipment Required
- OnStepX-based mount controller (Wemos D1 R32 + TMC2130)
- ZWO ASI camera or INDI-compatible camera
- Moonlite-compatible focuser
- Ecowitt GW1000/GW2000 weather station
- AAG CloudWatcher (optional)
- Roll-off roof controller with limit switches
- UPS with USB/serial monitoring (CyberPower recommended)

### Software Prerequisites
- NIGHTWATCH v0.1 installed
- Python 3.11+ with all dependencies
- Network access to all devices
- INDI server running (if using INDI devices)

## Test Execution Order

Execute tests in this order to build confidence progressively:

1. **Network Connectivity** - Verify all devices reachable
2. **Individual Device Tests** - Test each device in isolation
3. **Subsystem Tests** - Test related device groups
4. **Full System Tests** - Test complete workflows

## Test Categories

### 1. Mount Integration Tests

**Test File:** `tests/hardware/test_mount.py`

| Test ID | Description | Pass Criteria |
|---------|-------------|---------------|
| MT-001 | Connect to mount | Status response received |
| MT-002 | Read current position | Valid RA/Dec returned |
| MT-003 | Slew to coordinates | Slew completes, position matches |
| MT-004 | Stop slew | Mount stops within 2 seconds |
| MT-005 | Park mount | Mount reaches park position |
| MT-006 | Unpark mount | Tracking starts |
| MT-007 | Tracking rate change | Rate changes (sidereal/lunar/solar) |
| MT-008 | Sync to position | Position updates correctly |

**Execution:**
```bash
python -m tests.hardware.test_mount --host <mount_ip> --port 9999
```

### 2. Weather Station Tests

**Test File:** `tests/hardware/test_weather.py`

| Test ID | Description | Pass Criteria |
|---------|-------------|---------------|
| WS-001 | Connect to gateway | HTTP response received |
| WS-002 | Read temperature | -40°C to 60°C range |
| WS-003 | Read humidity | 0-100% range |
| WS-004 | Read wind speed | 0-100 mph range |
| WS-005 | Read pressure | 800-1100 hPa range |
| WS-006 | Data freshness | Update within 60 seconds |

**Execution:**
```bash
python -m tests.hardware.test_weather --host <gateway_ip> --port 8080
```

### 3. Cloud Sensor Tests

**Test File:** `tests/hardware/test_cloud_sensor.py`

| Test ID | Description | Pass Criteria |
|---------|-------------|---------------|
| CS-001 | Connect to sensor | TCP connection established |
| CS-002 | Read ambient temp | Valid temperature response |
| CS-003 | Read sky temp | Valid temperature response |
| CS-004 | Read rain sensor | Valid frequency value |
| CS-005 | Read brightness | Valid brightness value |
| CS-006 | Check safe/unsafe | Switch status returned |

**Execution:**
```bash
python -m tests.hardware.test_cloud_sensor --host <sensor_ip> --port 8081
```

### 4. Camera Tests

| Test ID | Description | Pass Criteria |
|---------|-------------|---------------|
| CM-001 | Connect to camera | Camera detected |
| CM-002 | Read camera info | Model, sensor size returned |
| CM-003 | Set gain | Gain changes, confirmed |
| CM-004 | Set exposure | Exposure time set |
| CM-005 | Capture frame | Image data received |
| CM-006 | Cooling control | Temperature changes toward target |
| CM-007 | Abort exposure | Exposure stops immediately |

### 5. Focuser Tests

| Test ID | Description | Pass Criteria |
|---------|-------------|---------------|
| FC-001 | Connect to focuser | Focuser detected |
| FC-002 | Read position | Valid position returned |
| FC-003 | Move relative | Position changes by step count |
| FC-004 | Move absolute | Position matches target |
| FC-005 | Stop movement | Movement stops |
| FC-006 | Temperature read | Valid temperature (if equipped) |

### 6. Enclosure Tests

| Test ID | Description | Pass Criteria |
|---------|-------------|---------------|
| EN-001 | Read status | Open/Closed/Moving status |
| EN-002 | Open roof | Roof opens, limit switch triggers |
| EN-003 | Close roof | Roof closes, limit switch triggers |
| EN-004 | Emergency stop | Motor stops immediately |
| EN-005 | Rain response | Close initiates on rain signal |

**CAUTION:** Ensure mount is parked before roof operations!

### 7. Voice Pipeline Tests

**Test File:** `tests/hardware/test_voice.py`

| Test ID | Description | Pass Criteria |
|---------|-------------|---------------|
| VP-001 | Microphone capture | Audio data received |
| VP-002 | Whisper transcription | Text output from speech |
| VP-003 | LLM response | Tool call generated |
| VP-004 | Piper TTS | Audio output generated |
| VP-005 | End-to-end | Voice command executes |

**Execution:**
```bash
python -m tests.hardware.test_voice --microphone default --speaker default
```

### 8. Encoder Tests

**Test File:** `tests/hardware/test_encoder.py`

| Test ID | Description | Pass Criteria |
|---------|-------------|---------------|
| EC-001 | Connect to encoder | SPI communication established |
| EC-002 | Read position | Valid counts returned |
| EC-003 | Position vs mount | Error within 1 arcminute |
| EC-004 | Multiple reads | Consistent values |

## Subsystem Integration Tests

### Safety System Tests

| Test ID | Description | Pass Criteria |
|---------|-------------|---------------|
| SS-001 | Weather unsafe triggers park | Mount parks when wind > 25 mph |
| SS-002 | Rain closes roof | Roof closes, mount parks |
| SS-003 | Power failure response | Graceful shutdown initiated |
| SS-004 | Sensor timeout failsafe | System enters safe mode |

### Imaging Workflow Tests

| Test ID | Description | Pass Criteria |
|---------|-------------|---------------|
| IW-001 | Slew and center | Object centered within 30" |
| IW-002 | Focus routine | HFD minimized |
| IW-003 | Guiding starts | RMS < 2" within 30 seconds |
| IW-004 | Capture sequence | Frames saved correctly |

## Full System Integration Test

**Test File:** `tests/integration/test_full_system.py`

Complete end-to-end test simulating a typical observing session:

1. System startup and initialization
2. Weather check (safe conditions)
3. Open enclosure
4. Unpark mount
5. Slew to target
6. Plate solve and center
7. Start autoguiding
8. Capture test image
9. Stop guiding
10. Park mount
11. Close enclosure
12. System shutdown

**Execution:**
```bash
python -m tests.integration.test_full_system --target M31 --exposure 60
```

## Test Results Template

```
NIGHTWATCH Hardware Integration Test Results
============================================
Date: YYYY-MM-DD
Tester: [Name]
Location: [Observatory Location]
Firmware Versions:
  - Mount: OnStepX [version]
  - Camera: [model] [driver version]

Test Results:
-------------
[ ] MT-001: Connect to mount        [PASS/FAIL] Notes:
[ ] MT-002: Read current position   [PASS/FAIL] Notes:
...

Overall Result: [PASS/FAIL]
Blocking Issues: [List any]
Notes: [Additional observations]
```

## Troubleshooting

### Mount Connection Issues
- Verify mount IP and port (default 9999)
- Check firewall settings
- Confirm mount WiFi is connected
- Try OnStep web interface first

### Weather Station Issues
- Verify gateway IP on local network
- Check Ecowitt app for connectivity
- Ensure gateway firmware is updated

### Camera Issues
- Check USB connection
- Verify INDI server running
- Check camera permissions (udev rules)

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| Tester | | | |
| Owner | | | |

---

*Document prepared for NIGHTWATCH v0.1 release*
