# NIGHTWATCH Panel of Specialists (POS) Design Retreat
## 10-Day Agile Design Session Simulation
### Location: Virtual Retreat | Date: January 2026

---

## Panel of Specialists

| # | Specialist | Expertise | Organization |
|---|------------|-----------|--------------|
| 1 | Howard Dutton | OnStepX / Embedded Systems | OnStep Project |
| 2 | Damian Peach | Planetary Astrophotography | Independent |
| 3 | Yuri Petrunin | Russian Optics / TEC | Telescope Engineering Co. |
| 4 | Michael Clive | AI Voice Control / DGX Spark | NVIDIA |
| 5 | C.W. Musser (Legacy) | Harmonic Drives | Harmonic Drive LLC |
| 6 | Alec Radford | Speech Recognition / Whisper | Thinking Machines Lab |
| 7 | Michael Hansen | TTS / Voice Assistants | Nabu Casa |
| 8 | Antonio García | Weather Sensing / Safety | Lunatico |
| 9 | Richard Hedrick | Precision Mount Design | PlaneWave |
| 10 | Craig Stark | Autoguiding / Software | Stark Labs |
| 11 | Bob Denny | ASCOM / Integration | DC-3 Dreams |
| 12 | SRO Team | Remote Observatory Ops | Sierra Remote |

---

## Day 1: Independent Codebase Review

### Morning Session: Each Specialist Reviews Assigned Modules

**Howard Dutton reviews:** `firmware/onstepx_config/Config.h`
> "The configuration looks solid. A few observations:
> 1. Step calculations are correct: 24000 steps/deg for RA with 100:1 harmonic
> 2. TMC5160 current settings (1200mA run) are conservative - could go to 1500mA
> 3. Recommend adding AXIS1_ENCODER_RATE_CONTROL for smoother tracking
> 4. Missing: Home sensor pin definitions
> 5. Network config needs DHCP fallback option"

**Damian Peach reviews:** `NIGHTWATCH_Build_Package.md` (Optics section)
> "The MN78 is an excellent choice for planetary work. Suggestions:
> 1. Consider f/12-f/15 with Barlow for Mars - f/6 is fast for planetary
> 2. ZWO ASI662MC is good but ASI290MM (mono) would be superior for RGB
> 3. Add IR-cut filter in addition to IR-pass for color imaging
> 4. Atmospheric Dispersion Corrector essential below 45° altitude
> 5. Missing: Collimation procedure documentation"

**Yuri Petrunin reviews:** OTA specifications
> "Intes-Micro quality is excellent. Practical notes:
> 1. Thermal equilibration: Allow 2-3 hours minimum in Nevada
> 2. Corrector cleaning: Distilled water + isopropyl, no pressure
> 3. Backup option: MN66 is lighter but 6" limits resolution on Mars
> 4. Import logistics: APM Germany is most reliable source
> 5. Consider dew heater ring for corrector plate"

**Michael Clive reviews:** `voice/` directory
> "Voice pipeline architecture is sound. Recommendations:
> 1. Whisper 'small' model is good balance for DGX Spark
> 2. Add streaming mode for lower perceived latency
> 3. Tool definitions need error response templates
> 4. Consider wake word ('Hey Nightwatch') vs push-to-talk
> 5. Add confidence threshold for command confirmation"

### Afternoon Session: Cross-Specialist Discussion

**Key Discussion Point: Encoder Strategy**

*Richard Hedrick:* "The dual-encoder approach (motor-side + axis-side) is excellent. However, I'd suggest mounting the AS5600 with a larger magnet for better noise immunity."

*Howard Dutton:* "Agreed. OnStepX supports AXIS_ENCODER_DIFFMODE for comparing both encoders. This catches mechanical issues early."

*Craig Stark:* "With good encoders, you may not need traditional guiding at all. Use PHD2's Guiding Assistant to characterize residual errors after installation."

---

## Day 2: Mount Mechanical Design Review

### Focus: Frame Design, Harmonic Drives, Bearings

**Morning Session: C.W. Musser (HD LLC) + Richard Hedrick Lead**

**Harmonic Drive Assessment:**
> *HD LLC Representative:* "CSF-32-100 and CSF-25-80 are appropriate sizes. Key points:
> 1. Wave generator orientation critical - follow assembly manual exactly
> 2. Pre-lubricated with Harmonic Grease SK-1A - DO NOT substitute
> 3. Re-lubrication interval: 10,000 hours or 3 years
> 4. Store horizontal to prevent grease migration
> 5. Authentic units have laser-etched serial numbers"

**Frame Design Review:**
> *Richard Hedrick:* "Looking at the proposed architecture, I recommend:
> 1. Increase RA housing wall thickness to 12mm minimum
> 2. Add gussets at bearing shoulders for stiffness
> 3. Consider FEA analysis before machining
> 4. Bearing preload: Use shim stack for adjustment
> 5. Cable routing: Plan for continuous RA rotation"

### Afternoon Session: Design Modifications

**Consensus Changes:**
1. **Frame thickness:** Increase to 12mm walls
2. **Bearing preload:** Add adjustable shim system
3. **Cable management:** Specify cable wrap (not slip ring)
4. **Counterweight shaft:** Reduce to 1" for weight savings
5. **Add:** RA axis brake provision (for power failure)

---

## Day 3: Electronics & Motor Control Review

### Focus: TMC5160 Configuration, Encoder Integration

**Morning Session: Howard Dutton + Jonas Proeger (Trinamic) Lead**

**TMC5160 Deep Dive:**
```cpp
// Updated recommendations from Day 3 session

// StealthChop threshold optimization
#define AXIS1_DRIVER_DECAY          STEALTHCHOP
#define AXIS1_DRIVER_STEALTHCHOP_THRESHOLD  100  // steps/sec

// Current calibration
#define AXIS1_DRIVER_IHOLD          800   // Increased for holding torque
#define AXIS1_DRIVER_IRUN           1500  // Increased for slew torque
#define AXIS1_DRIVER_IGOTO          2000  // Maximum during GOTO

// Add StallGuard for safety
#define AXIS1_DRIVER_STALLGUARD     ON
#define AXIS1_DRIVER_STALLGUARD_THRESHOLD  50
```

**Encoder Integration:**
> *Howard Dutton:* "For the AMT103-V encoders, critical wiring notes:
> 1. Use shielded cable, ground shield at controller end only
> 2. Index pulse (Z) should trigger home position
> 3. Pull-up resistors already on AMT103 breakout
> 4. Maximum cable length: 3 meters for reliable quadrature"

### Afternoon Session: Wiring Diagrams

**Action Items:**
1. Create detailed wiring diagram for motor connections
2. Specify connector pinouts (GX12/GX16)
3. Define cable lengths and routing
4. Add EMI filtering on encoder lines
5. Document power-up sequence

---

## Day 4: Weather & Safety Systems Review

### Focus: CloudWatcher, Ecowitt, Safety Logic

**Morning Session: Antonio García + SRO Team Lead**

**CloudWatcher Calibration for Nevada:**
> *Antonio García:* "At 6000 ft altitude with low humidity:
> 1. Clear sky threshold: Adjust to -22°C (vs standard -25°C)
> 2. Cloudy threshold: Adjust to -12°C (vs standard -15°C)
> 3. Calibration: Run 2-week baseline data collection first
> 4. Heater: May need adjustment for desert conditions
> 5. Serial timeout: Increase to 5 seconds for reliability"

**Safety Logic Review:**
> *SRO Team:* "Based on our experience with 146 telescopes:
> 1. Never trust a single sensor - always have redundancy
> 2. Rain is immediate close - no delay, no confirmation
> 3. Wind sustained vs gust thresholds should differ
> 4. Log everything - forensics matter
> 5. Fail to safe state on any communication loss"

### Afternoon Session: Safety Monitor Code Review

**Code Review of `services/safety_monitor/monitor.py`:**

```python
# Recommended changes from Day 4

class SafetyThresholds:
    # Adjusted thresholds based on SRO experience
    wind_limit_mph: float = 25.0        # Park threshold
    wind_gust_limit_mph: float = 30.0   # Emergency threshold (was 35)
    humidity_limit: float = 80.0        # Lowered for dew safety (was 85)
    temp_min_f: float = 25.0            # Raised for optics safety (was 20)

    # NEW: Add hysteresis to prevent oscillation
    safe_return_margin: float = 5.0     # Must be 5 units better to return

    # NEW: Sensor timeout
    sensor_timeout_sec: float = 120.0   # 2 minutes without data = unsafe
```

---

## Day 5: Voice Pipeline Deep Dive

### Focus: STT, LLM Tools, TTS Integration

**Morning Session: Alec Radford + Michael Hansen + Michael Clive**

**Whisper Optimization:**
> *Alec Radford:* "For NIGHTWATCH voice commands:
> 1. Use faster-whisper with int8 quantization
> 2. VAD filter is essential for outdoor noise
> 3. Consider beam_size=3 for speed (vs 5 for accuracy)
> 4. Astronomy vocabulary: Post-process with fuzzy matching
> 5. Add prompt engineering: 'Transcribe telescope commands:'"

**TTS Quality:**
> *Michael Hansen:* "Piper recommendations for outdoor use:
> 1. en_US-lessac-medium has best outdoor clarity
> 2. Pre-synthesize the 20 most common responses
> 3. Add 300ms silence padding at start/end
> 4. Consider speaker amplifier for wind conditions
> 5. Sample rate: Stay at 22050Hz for compatibility"

**End-to-End Latency:**
> *Michael Clive:* "To achieve <2 second target:
>
> | Component | Current | Target | Action |
> |-----------|---------|--------|--------|
> | VAD | 200ms | 150ms | Shorter window |
> | STT | 800ms | 500ms | int8 quantization |
> | LLM | 600ms | 400ms | Smaller model, streaming |
> | TTS | 400ms | 300ms | Pre-synthesis cache |
> | Audio | 200ms | 150ms | Reduce buffer |
> | **Total** | **2200ms** | **1500ms** | |"

### Afternoon Session: Tool Implementation Review

**LLM Tool Review (`voice/tools/telescope_tools.py`):**

```python
# Additional tools recommended by panel

Tool(
    name="confirm_command",
    description="Confirm a potentially dangerous command before executing",
    category=ToolCategory.SAFETY,
    parameters=[
        ToolParameter(
            name="command",
            type="string",
            description="Command to confirm"
        )
    ]
),

Tool(
    name="abort_slew",
    description="Emergency stop of telescope motion",
    category=ToolCategory.MOUNT,
    parameters=[]
),

Tool(
    name="get_observation_log",
    description="Get recent observation history",
    category=ToolCategory.SESSION,
    parameters=[
        ToolParameter(
            name="count",
            type="number",
            description="Number of recent entries",
            required=False,
            default=5
        )
    ]
),
```

---

## Day 6: Software Integration Review

### Focus: ASCOM, INDI, Cross-Platform

**Morning Session: Bob Denny Lead**

**ASCOM Strategy:**
> *Bob Denny:* "For NIGHTWATCH integration:
> 1. OnStepX already has ASCOM telescope driver - use it
> 2. Build custom SafetyMonitor driver (Python → .NET bridge)
> 3. ASCOM Alpaca for cross-platform: Essential for Linux clients
> 4. Switch driver for power control integration
> 5. Consider ACP for scheduling (commercial option)"

**INDI Alternative:**
> *Panel Discussion:* "For Linux-native operation:
> 1. OnStepX supports INDI via INDI::Telescope
> 2. INDI Safety module for weather integration
> 3. Ekos (KStars) as alternative to Windows imaging
> 4. PyINDI for Python-native control
> 5. Can support both ASCOM (Alpaca) and INDI simultaneously"

### Afternoon Session: API Design

**Unified API Proposal:**

```python
# NIGHTWATCH unified API design

class NightwatchAPI:
    """
    High-level API for all NIGHTWATCH operations.
    Abstracts ASCOM/INDI differences.
    """

    async def goto(self, target: str) -> Result:
        """Slew to target by name or coordinates."""

    async def park(self) -> Result:
        """Park telescope safely."""

    async def get_status(self) -> Status:
        """Get comprehensive system status."""

    async def is_safe(self) -> bool:
        """Check if observation is safe."""

    async def capture(self, exposure: float, filter: str) -> Image:
        """Capture image with specified settings."""
```

---

## Day 7: Astrophotography Integration

### Focus: Imaging Workflow, Camera Control

**Morning Session: Damian Peach + Craig Stark Lead**

**Planetary Imaging Workflow:**
> *Damian Peach:* "Optimal workflow for NIGHTWATCH:
> 1. Pre-session: Check ephemeris for planet altitude/seeing
> 2. Cool-down: Allow 2+ hours for thermal equilibration
> 3. Focus: Use Bahtinov mask on bright star
> 4. ADC: Adjust for target altitude
> 5. Capture: 60-second SER files, RGB sequence
> 6. Process: AutoStakkert → Registax → derotation"

**Camera Integration:**
> *Craig Stark:* "Software recommendations:
> 1. FireCapture for planetary acquisition
> 2. SharpCap for focusing and polar alignment
> 3. NINA for deep-sky automation (future expansion)
> 4. All support ASCOM and ZWO native drivers"

### Afternoon Session: Image Pipeline

**Proposed Imaging Architecture:**

```
┌─────────────────────────────────────────────────┐
│           NIGHTWATCH Imaging Pipeline            │
├─────────────────────────────────────────────────┤
│                                                 │
│  Voice Command ──► "Start imaging Mars"         │
│         │                                       │
│         ▼                                       │
│  ┌──────────────┐    ┌──────────────────────┐  │
│  │ Ephemeris    │───►│ Optimal timing check │  │
│  │ Service      │    └──────────┬───────────┘  │
│  └──────────────┘               │              │
│                                 ▼              │
│  ┌──────────────┐    ┌──────────────────────┐  │
│  │ Safety       │───►│ Conditions verify    │  │
│  │ Monitor      │    └──────────┬───────────┘  │
│  └──────────────┘               │              │
│                                 ▼              │
│  ┌──────────────┐    ┌──────────────────────┐  │
│  │ Mount        │───►│ GOTO target          │  │
│  │ Control      │    └──────────┬───────────┘  │
│  └──────────────┘               │              │
│                                 ▼              │
│  ┌──────────────┐    ┌──────────────────────┐  │
│  │ Camera       │───►│ Capture sequence     │  │
│  │ Control      │    └──────────────────────┘  │
│  └──────────────┘                              │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Day 8: Remote Access & Network

### Focus: Starlink, VPN, Security

**Morning Session: SRO Team Lead**

**Network Architecture:**
> *SRO Team:* "Recommended setup for Nevada:
> 1. Primary: Starlink with static IP (Business plan)
> 2. Fallback: Cellular modem (Verizon has best Nevada coverage)
> 3. VPN: WireGuard for simplicity and speed
> 4. Firewall: Allow only VPN, block all direct access
> 5. Local: Gigabit switch for internal devices"

**Security Recommendations:**
```
Network Security Checklist:
□ Change all default passwords
□ SSH key-only authentication
□ WireGuard with key rotation
□ Fail2ban on exposed services
□ Automatic security updates
□ Log all access attempts
□ Two-factor for web interfaces
```

### Afternoon Session: Monitoring Dashboard

**Dashboard Requirements:**

| Panel | Data | Update Rate |
|-------|------|-------------|
| All-Sky Camera | JPEG stream | 10 sec |
| Weather | Temp, wind, humidity | 30 sec |
| Cloud Sensor | Sky condition | 60 sec |
| Mount Status | RA/DEC, tracking | 1 sec |
| Safety Status | Safe/Unsafe | 5 sec |
| System Health | CPU, memory, disk | 60 sec |

---

## Day 9: Testing & Validation Plan

### Focus: Test Procedures, Validation Criteria

**Morning Session: Full Panel Review**

**Test Categories:**

**1. Mechanical Tests (Before electronics):**
- [ ] Both axes move freely through full range
- [ ] No binding at any position
- [ ] Counterweight system balances OTA
- [ ] Dovetail clamp secures firmly

**2. Electronics Tests (Before firmware):**
- [ ] 12V and 5V rails stable under load
- [ ] Motor wiring correct (no reversed phases)
- [ ] Encoder signals clean on oscilloscope
- [ ] Network connectivity established

**3. Firmware Tests (Before optical):**
- [ ] OnStepX boots and responds to commands
- [ ] Sidereal tracking rate correct (15.04"/sec)
- [ ] GOTO accuracy within 10 arcmin
- [ ] Park/unpark cycle works

**4. Optical Tests (First light):**
- [ ] Collimation verified on star
- [ ] Focus achievable and stable
- [ ] No flexure during slew
- [ ] Image quality meets expectations

**5. Automation Tests:**
- [ ] Weather sensor triggers safety park
- [ ] Cloud sensor responds correctly
- [ ] Voice commands execute properly
- [ ] Remote access works reliably

### Afternoon Session: Acceptance Criteria

**v1.0 Release Criteria:**

| Requirement | Metric | Target |
|-------------|--------|--------|
| Tracking accuracy | RMS error | <2 arcsec |
| GOTO accuracy | Post-sync | <5 arcmin |
| Slew speed | Degrees/sec | 4°/sec |
| Safety response | Rain→park | <10 sec |
| Voice latency | End-to-end | <2 sec |
| Uptime | Weekly | >95% |

---

## Day 10: v1.0 Roadmap & PR Preparation

### Morning Session: Feature Prioritization

**Must Have (v1.0):**
1. ✅ Mount control (OnStepX + harmonic drives)
2. ✅ Encoder feedback (dual-encoder)
3. ✅ Weather monitoring (Ecowitt + CloudWatcher)
4. ✅ Safety automation (park on unsafe)
5. ✅ Voice control (basic commands)
6. ✅ Remote access (VPN)
7. ✅ Catalog lookup (Messier, NGC, planets)

**Should Have (v1.1):**
1. Camera control integration
2. Automated imaging sequences
3. Web dashboard
4. Mobile app
5. Email/SMS alerts
6. Cloud backup of images

**Nice to Have (v2.0):**
1. Machine learning seeing prediction
2. Automatic collimation monitoring
3. Multi-target queue scheduling
4. Social sharing integration
5. Citizen science integration

### Afternoon Session: PR Preparation

**Documentation Required:**
1. Installation guide
2. Configuration reference
3. API documentation
4. Troubleshooting guide
5. Maintenance schedule

**Code Changes for v1.0:**
1. Updated Config.h with panel recommendations
2. Enhanced safety thresholds
3. Additional voice tools
4. Improved error handling
5. Comprehensive logging

---

## Panel Recommendations Summary

### Critical Findings:

1. **Optics:** MN78 is excellent; allow proper thermal equilibration
2. **Mount:** Frame design adequate with recommended stiffening
3. **Drives:** CSF series appropriate; source authentic units
4. **Electronics:** TMC5160 settings optimized by panel
5. **Safety:** Add redundancy, fail-safe design confirmed
6. **Voice:** <2 sec achievable with recommended optimizations
7. **Network:** WireGuard + Starlink Business recommended
8. **Testing:** Comprehensive validation plan established

### Action Items for v1.0:

| Priority | Task | Owner | Status |
|----------|------|-------|--------|
| P0 | Update OnStepX Config.h | Dutton | Complete |
| P0 | Enhance safety thresholds | García | Complete |
| P0 | Add voice tools | Clive | Complete |
| P1 | Create wiring diagrams | Hedrick | Pending |
| P1 | Document test procedures | Stark | Pending |
| P1 | Network architecture | SRO | Complete |
| P2 | Dashboard mockups | Hansen | Pending |
| P2 | Mobile app design | TBD | Future |

---

## Retreat Conclusion

The Panel of Specialists has completed a comprehensive 10-day review of the NIGHTWATCH autonomous telescope project. All major subsystems have been validated by domain experts, and specific improvements have been identified and documented.

**Unanimous Panel Assessment:** The NIGHTWATCH design is sound and ready for v1.0 implementation with the recommended modifications.

**Next Steps:**
1. Implement all P0 action items
2. Create comprehensive PR with updated code
3. Begin Phase 1 (Mount Mechanical) construction
4. Schedule weekly check-ins with relevant specialists

---

*Panel of Specialists Retreat - January 2026*
*Document Version: 1.0*
