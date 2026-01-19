# POS Panel Member Resources

*Last Updated: January 2026*

This document tracks GitHub profiles and key repositories for Panel of Specialists members, enabling future integration and contribution opportunities.

---

## Members with GitHub Profiles

### Howard Dutton (#1: OnStepX / Embedded Systems)

**GitHub:** [hjd1964](https://github.com/hjd1964)

| Repository | Description | NIGHTWATCH Relevance |
|------------|-------------|---------------------|
| [OnStepX](https://github.com/hjd1964/OnStepX) | Main telescope controller firmware (170★) | Core mount control - Teensy 4.1 configuration |
| [OnStep](https://github.com/hjd1964/OnStep) | Original OnStep firmware (558★, legacy) | Reference for older implementations |
| [SmartWebServer](https://github.com/hjd1964/SmartWebServer) | Web interface for OnStep (45★) | Potential remote control integration |
| [OCS](https://github.com/hjd1964/OCS) | Observatory Control System (8★) | Enclosure/power management patterns |
| [SmartHandController](https://github.com/hjd1964/SmartHandController) | Physical hand controller for OnStepX (19★) | Tactile control for dark-sky operation |
| [EncoderBridge](https://github.com/hjd1964/EncoderBridge) | Serial encoder bridge for OnStepX | High-precision encoder integration |
| [OnStepX-Plugins](https://github.com/hjd1964/OnStepX-Plugins) | Plugin extensions for OnStepX (11★) | Extended functionality patterns |

**Notes:** Most active and directly relevant to NIGHTWATCH. Primary source for firmware configuration patterns, TMC5160 driver settings, and encoder integration strategies. The EncoderBridge is particularly relevant for achieving sub-arcsecond positioning accuracy with the harmonic drive mount.

---

### Michael Hansen (#7: TTS / Voice Assistants)

**GitHub:** [synesthesiam](https://github.com/synesthesiam)

| Repository | Description | NIGHTWATCH Relevance |
|------------|-------------|---------------------|
| [rhasspy/piper](https://github.com/rhasspy/piper) | Fast local neural TTS (10.5k★) | Voice synthesis on DGX Spark |
| [rhasspy](https://github.com/rhasspy/rhasspy) | Offline voice assistant toolkit (2.7k★) | Voice pipeline architecture patterns |
| [wyoming](https://github.com/rhasspy/wyoming) | Voice assistant protocol | Service communication patterns |
| [wyoming-faster-whisper](https://github.com/rhasspy/wyoming-faster-whisper) | Wyoming server for faster-whisper STT (283★) | STT service deployment pattern |
| [wyoming-satellite](https://github.com/rhasspy/wyoming-satellite) | Remote voice satellite (1.2k★, deprecated) | Distributed audio capture patterns |
| [piper-phonemize](https://github.com/rhasspy/piper-phonemize) | Phonemization for Piper (137★) | TTS preprocessing |
| [piper-recording-studio](https://github.com/rhasspy/piper-recording-studio) | Voice dataset recording tool (201★) | Custom voice model training |
| [pymicro-vad](https://github.com/rhasspy/pymicro-vad) | Voice activity detection (36★) | Audio preprocessing for STT |

**Notes:** Piper TTS is explicitly used in the NIGHTWATCH voice pipeline. Key resource for ONNX model optimization, voice selection, and low-latency synthesis configuration. The wyoming-faster-whisper project provides the deployment pattern for Whisper STT on the DGX Spark.

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
| [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 4x faster Whisper via CTranslate2 | Optimized STT for DGX Spark |

**Notes:** While Alec Radford's personal GitHub has limited public repos, his work on Whisper (via OpenAI) directly informs the NIGHTWATCH STT pipeline. The **faster-whisper** implementation from SYSTRAN is particularly relevant — it provides 4x speedup with lower memory usage, supporting int8/int16 quantization and CUDA acceleration essential for DGX Spark deployment.

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

## Related Organizations & Ecosystem Projects

The following organizations maintain projects highly relevant to NIGHTWATCH, even if not directly affiliated with panel members.

### INDI Library (Linux Telescope Control)

**Organization:** [indilib](https://github.com/indilib)

| Repository | Description | NIGHTWATCH Relevance |
|------------|-------------|---------------------|
| [indi](https://github.com/indilib/indi) | Core INDI library (424★) | Linux device communication standard |
| [indi-3rdparty](https://github.com/indilib/indi-3rdparty) | Third-party drivers (148★) | Camera/mount driver support |
| [pyindi-client](https://github.com/indilib/pyindi-client) | Python INDI client (28★) | Python service integration |

**Notes:** INDI is the Linux counterpart to ASCOM. The NIGHTWATCH services layer will likely communicate with OnStepX through INDI on the DGX Spark. The pyindi-client enables direct Python integration for our microservices.

---

### ASCOM Initiative (Windows Standards)

**Organization:** [ASCOMInitiative](https://github.com/ASCOMInitiative)

| Repository | Description | NIGHTWATCH Relevance |
|------------|-------------|---------------------|
| [ASCOMPlatform](https://github.com/ASCOMInitiative/ASCOMPlatform) | ASCOM runtime/SDK (117★) | Interface standard reference |
| [alpyca](https://github.com/ASCOMInitiative/alpyca) | Python Alpaca client (28★) | Cross-platform ASCOM via REST |
| [ASCOM.Alpaca.Simulators](https://github.com/ASCOMInitiative/ASCOM.Alpaca.Simulators) | Alpaca device simulators (29★) | Development/testing without hardware |
| [ASCOMRemote](https://github.com/ASCOMInitiative/ASCOMRemote) | REST-based remote access (58★) | Network device communication |

**Notes:** While NIGHTWATCH primarily targets Linux (DGX Spark), the **alpyca** library enables Python access to ASCOM Alpaca devices over HTTP. This provides compatibility with Windows-based astronomy software when needed. Bob Denny (#11) is a key contributor to ASCOM standards.

---

### SYSTRAN (Speech Processing)

**Organization:** [SYSTRAN](https://github.com/SYSTRAN)

| Repository | Description | NIGHTWATCH Relevance |
|------------|-------------|---------------------|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Optimized Whisper implementation | Primary STT engine candidate |

**Notes:** Faster-whisper achieves 4x speed improvement over OpenAI's reference implementation with lower memory usage. Supports int8/int16 quantization, batched inference, and CUDA acceleration — ideal for DGX Spark deployment.

---

## Integration Opportunities

### Immediate (Phase 1-2)
- **OnStepX** — Fork and customize Config.h for NIGHTWATCH mount specs
- **EncoderBridge** — Integrate high-resolution encoders for harmonic drive feedback
- **faster-whisper** — Deploy optimized STT on DGX Spark with CUDA acceleration
- **Piper** — Test voice models, optimize for outdoor clarity
- **pyindi-client** — Establish Python-based device communication layer

### Medium-term (Phase 2-3)
- **PHD2** — Evaluate guiding algorithms for harmonic drive characteristics
- **wyoming-faster-whisper** — Adopt Wyoming protocol for STT service architecture
- **alpyca** — Add ASCOM Alpaca compatibility for cross-platform support
- **ASCOM.Alpaca.Simulators** — Development testing without physical hardware

### Future (Phase 3+)
- **Whisper fine-tuning** — Customize for astronomy-specific vocabulary
- **OCS patterns** — Adapt enclosure control logic for roll-off roof
- **Wyoming protocol** — Standardize voice service communication
- **piper-recording-studio** — Train custom voice model for NIGHTWATCH persona
- **OnStepX-Plugins** — Develop NIGHTWATCH-specific extensions

---

## Contributing

If you discover additional GitHub profiles or repositories relevant to panel members, please open a PR or issue to update this document.
