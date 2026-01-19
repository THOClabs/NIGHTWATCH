# POS Panel Member Resources

This document tracks GitHub profiles and key repositories for Panel of Specialists members, enabling future integration and contribution opportunities.

---

## Members with GitHub Profiles

### Howard Dutton (#1: OnStepX / Embedded Systems)

**GitHub:** [hjd1964](https://github.com/hjd1964)

| Repository | Description | NIGHTWATCH Relevance |
|------------|-------------|---------------------|
| [OnStepX](https://github.com/hjd1964/OnStepX) | Main telescope controller firmware | Core mount control - Teensy 4.1 configuration |
| [OnStep](https://github.com/hjd1964/OnStep) | Original OnStep firmware (legacy) | Reference for older implementations |
| [SmartWebServer](https://github.com/hjd1964/SmartWebServer) | Web interface for OnStep | Potential remote control integration |
| [OCS](https://github.com/hjd1964/OCS) | Observatory Control System | Enclosure/power management patterns |

**Notes:** Most active and directly relevant to NIGHTWATCH. Primary source for firmware configuration patterns, TMC5160 driver settings, and encoder integration strategies.

---

### Michael Hansen (#7: TTS / Voice Assistants)

**GitHub:** [synesthesiam](https://github.com/synesthesiam)

| Repository | Description | NIGHTWATCH Relevance |
|------------|-------------|---------------------|
| [rhasspy/piper](https://github.com/rhasspy/piper) | Fast local neural TTS | Voice synthesis on DGX Spark |
| [rhasspy](https://github.com/rhasspy/rhasspy) | Offline voice assistant toolkit | Voice pipeline architecture patterns |
| [wyoming](https://github.com/rhasspy/wyoming) | Voice assistant protocol | Service communication patterns |
| [piper-phonemize](https://github.com/rhasspy/piper-phonemize) | Phonemization for Piper | TTS preprocessing |

**Notes:** Piper TTS is explicitly used in the NIGHTWATCH voice pipeline. Key resource for ONNX model optimization, voice selection, and low-latency synthesis configuration.

---

### Craig Stark (#10: Autoguiding / Software)

**Primary Repository:** [OpenPHDGuiding/phd2](https://github.com/OpenPHDGuiding/phd2)

While Craig Stark (Stark Labs, original PHD Guiding author) does not maintain a personal public GitHub, PHD2—the open-source successor he founded—is community-maintained:

| Repository | Description | NIGHTWATCH Relevance |
|------------|-------------|---------------------|
| [phd2](https://github.com/OpenPHDGuiding/phd2) | Open-source autoguiding software | Phase 2 guiding integration |

**Notes:** Early source files (e.g., `graph.h`, `cam_SAC42.cpp`) credit Craig Stark's foundational work. PHD2 integration is planned for POS Phase 2 autoguiding with target RMS < 0.5" error.

---

### Alec Radford (#6: Speech Recognition / Whisper)

**GitHub:** [AlecRadford](https://github.com/AlecRadford) (limited public activity)

**Historical:** [newmu](https://github.com/newmu) (older personal account)

| Related Repository | Description | NIGHTWATCH Relevance |
|-------------------|-------------|---------------------|
| [openai/whisper](https://github.com/openai/whisper) | Automatic speech recognition | STT in voice pipeline |

**Notes:** While Alec Radford's personal GitHub has limited public repos, his work on Whisper (via OpenAI) directly informs the NIGHTWATCH STT pipeline. The agent profile channels his expertise in audio processing and model optimization for the DGX Spark deployment.

---

## Members Without Public GitHub Profiles

The following panel members contribute expertise but do not have publicly known GitHub accounts:

| # | Member | Expertise | Alternative Resources |
|---|--------|-----------|----------------------|
| 2 | Damian Peach | Planetary Astrophotography | [damianpeach.com](https://www.damianpeach.com) |
| 3 | Yuri Petrunin | Russian Optics / TEC | [telescopengineering.com](https://www.telescopengineering.com) |
| 4 | Michael Clive | AI Voice Control / NVIDIA | [LinkedIn: clivefx](https://www.linkedin.com/in/clivefx/) |
| 5 | C.W. Musser | Harmonic Drives (Legacy) | Historical patents, HD LLC documentation |
| 8 | Antonio García | Weather Sensing / Lunatico | [lunatico.es](https://www.lunatico.es) |
| 9 | Richard Hedrick | Precision Mounts / PlaneWave | [planewave.com](https://www.planewave.com) |
| 11 | Bob Denny | ASCOM / DC-3 Dreams | [dc3.com](https://www.dc3.com), [ASCOM Standards](https://ascom-standards.org) |
| 12 | SRO Team | Remote Observatory Ops | [Sierra Remote Observatories](https://www.sierraremote.com) |

---

## Integration Opportunities

### Immediate (Phase 1-2)
- **OnStepX** — Fork and customize Config.h for NIGHTWATCH mount specs
- **Piper** — Test voice models, optimize for outdoor clarity
- **PHD2** — Evaluate guiding algorithms for harmonic drive characteristics

### Future (Phase 3+)
- **Whisper** — Fine-tune for astronomy-specific vocabulary
- **OCS patterns** — Adapt enclosure control logic
- **Wyoming protocol** — Standardize voice service communication

---

## Contributing

If you discover additional GitHub profiles or repositories relevant to panel members, please open a PR or issue to update this document.
