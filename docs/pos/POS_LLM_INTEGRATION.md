# Panel of Specialists: LLM Integration for Voice Control

**Document Type:** POS (Panel of Specialists) Deliberation
**Topic:** Local LLM Integration for Observatory Voice Control
**Date:** 2025-01-20
**Status:** Design Recommendation

---

## Executive Summary

This document presents a panel of expert perspectives on integrating a local Large Language Model (LLM) into the NIGHTWATCH autonomous observatory for voice command processing. The panel considers hardware constraints (NVIDIA DGX Spark), speech-to-text requirements (Whisper), text-to-speech needs (Piper), and overall system architecture.

**Consensus Recommendation:** Deploy a quantized local LLM (Llama 3.2 8B or similar) with specialized astronomy tool bindings, running on the DGX Spark GPU alongside Whisper STT. Use streaming inference for low-latency responses and implement a structured tool-calling protocol for safe telescope operations.

---

## Panel Members

1. **Michael Clive** - AI Infrastructure Specialist (NVIDIA DGX Systems)
2. **Alec Radford** - Speech Recognition Expert (Whisper Architecture)
3. **Michael Hansen** - Neural TTS Specialist (Piper/VITS)
4. **Observatory Integration Lead** - System Architecture (NIGHTWATCH)

---

## Question for Deliberation

> How should NIGHTWATCH integrate a local LLM for processing voice commands to control telescope operations, given the constraints of edge deployment, real-time responsiveness, and safety-critical operations?

---

## Expert Perspectives

### Michael Clive - AI Infrastructure (DGX Spark)

**Background:** The NVIDIA DGX Spark provides substantial GPU compute (up to 1 PFLOP FP4) with 128GB unified memory, making it well-suited for running multiple AI models concurrently.

**Recommendations:**

1. **Model Selection:**
   - Primary: Llama 3.2 8B (4-bit quantized) - excellent reasoning with ~4GB VRAM
   - Fallback: Phi-3 Mini (3.8B) for faster inference if latency is critical
   - Both models fit comfortably alongside Whisper medium (~1.5GB)

2. **Memory Architecture:**
   - Leverage unified memory for zero-copy tensor sharing between models
   - Pre-load all models at startup to avoid cold-start latency
   - Reserve ~20GB for model inference, leaving headroom for camera processing

3. **Inference Optimization:**
   - Use TensorRT-LLM for optimized inference on Grace Hopper architecture
   - Enable KV-cache optimization for multi-turn conversations
   - Target <500ms time-to-first-token for responsive voice interaction

4. **Concurrency Model:**
   ```
   GPU Memory Layout:
   ├── Whisper Medium (1.5GB) - Always loaded
   ├── LLM 8B Quantized (4GB) - Always loaded
   ├── Piper TTS (200MB) - Always loaded
   ├── Camera Processing (2GB) - On-demand
   └── Buffer/KV Cache (12GB)
   ```

5. **Power Considerations:**
   - DGX Spark runs on standard power, suitable for remote observatory
   - Enable dynamic power scaling during idle periods
   - Monitor GPU temperature for thermal management in enclosure

**Key Insight:** The unified memory architecture eliminates the typical CPU-GPU transfer bottleneck, enabling seamless pipeline from audio input through LLM reasoning to speech output.

---

### Alec Radford - Speech Recognition (Whisper)

**Background:** Whisper's encoder-decoder architecture provides robust speech recognition even in challenging acoustic environments, critical for observatory operation.

**Recommendations:**

1. **Model Selection:**
   - Use Whisper Medium (769M params) for best accuracy/speed tradeoff
   - faster-whisper implementation with CTranslate2 for 4x speedup
   - Enable VAD (Voice Activity Detection) to reduce processing of silence

2. **Astronomy-Specific Tuning:**
   ```python
   # Boost astronomy vocabulary in decoding
   astronomy_vocab = [
       "Andromeda", "Messier", "NGC", "slew", "declination",
       "right ascension", "meridian", "zenith", "azimuth",
       "tracking", "sidereal", "guiding", "dither"
   ]
   ```
   - Use initial_prompt with astronomy context to bias recognition
   - Consider fine-tuning on astronomy command dataset if accuracy issues persist

3. **Pipeline Architecture:**
   ```
   Microphone → VAD → Whisper → LLM → Tool Execution → Piper → Speaker
              ↓
         (silence filtered)
   ```

4. **Latency Optimization:**
   - Stream audio in 1-second chunks for progressive transcription
   - Use Whisper's `no_speech_threshold` to skip silent segments
   - Target total STT latency: <1 second for typical commands

5. **Error Handling:**
   - Implement confidence thresholds - reject low-confidence transcriptions
   - Use LLM to disambiguate unclear commands ("Did you mean M31 or M13?")
   - Log all transcriptions for offline analysis and improvement

**Key Insight:** Whisper's robustness to background noise (wind, equipment) makes it ideal for observatory environments. The initial_prompt mechanism provides a zero-cost way to improve astronomy term recognition.

---

### Michael Hansen - Text-to-Speech (Piper)

**Background:** Piper provides high-quality neural TTS with minimal latency, essential for natural voice interaction in hands-free observatory operation.

**Recommendations:**

1. **Voice Selection:**
   - en_US-lessac-medium: Natural voice, good clarity, ~200MB
   - Pre-generate common responses for zero-latency playback
   - Consider en_GB-alan-medium for variety (optional second voice)

2. **Response Design:**
   ```python
   # Response templates for common operations
   TEMPLATES = {
       "slew_start": "Slewing to {object}. Estimated time: {seconds} seconds.",
       "slew_complete": "{object} acquired. Tracking engaged.",
       "safety_block": "Operation blocked. {reason}. Say 'override' to continue.",
       "weather_alert": "Weather warning: {condition}. Recommend parking telescope.",
   }
   ```

3. **Audio Pipeline:**
   ```
   LLM Response → Piper TTS → Audio Buffer → Speaker
                      ↓
              (streaming synthesis)
   ```

4. **Latency Optimization:**
   - Use streaming synthesis - start playback before full generation
   - Cache phoneme sequences for repeated phrases
   - Target time-to-first-audio: <200ms

5. **Observatory-Specific Considerations:**
   - Use moderate speech rate (not too fast for clarity in dark)
   - Implement interruptible playback for urgent safety alerts
   - Consider haptic/visual feedback alongside audio for confirmation

6. **Pronunciation Handling:**
   ```python
   # Custom pronunciations for astronomy terms
   PHONEME_OVERRIDES = {
       "NGC": "N G C",
       "RA": "R A",
       "Dec": "deck",
       "arcsec": "arc second",
   }
   ```

**Key Insight:** Pre-generating common responses (especially safety alerts) ensures instant feedback when timing is critical. Streaming synthesis provides responsive feel for longer explanations.

---

### Observatory Integration Lead - System Architecture

**Background:** Integrating LLM into NIGHTWATCH requires careful consideration of safety, reliability, and the unique requirements of telescope automation.

**Recommendations:**

1. **Tool-Calling Architecture:**
   ```python
   # Structured tool definitions for LLM
   TELESCOPE_TOOLS = [
       {
           "name": "goto_object",
           "description": "Slew telescope to named object",
           "parameters": {"object_name": "string"},
           "requires_confirmation": False,  # Common operation
           "safety_check": "altitude_limit"
       },
       {
           "name": "park_telescope",
           "description": "Park telescope in safe position",
           "parameters": {"confirmed": "boolean"},
           "requires_confirmation": True,  # Destructive action
           "safety_check": None  # Always allowed
       }
   ]
   ```

2. **Safety Integration:**
   - LLM cannot bypass safety system - all commands pass through SafetyMonitor
   - Implement "confirmation required" for destructive operations
   - Hard-code emergency stop - voice command directly triggers, no LLM processing

3. **Conversation Context:**
   ```python
   # Maintain session context for natural interaction
   context = {
       "current_target": "M31",
       "last_slew_time": "10 minutes ago",
       "weather_status": "clear",
       "tracking_status": "sidereal"
   }
   # LLM receives context for informed responses
   ```

4. **Failure Modes:**
   - LLM timeout → fall back to simple keyword matching
   - Whisper failure → request repeat ("I didn't catch that")
   - Tool execution failure → LLM explains error in natural language

5. **System Prompt Design:**
   ```
   You are NIGHTWATCH, an AI assistant for controlling an autonomous
   telescope observatory. You have access to tools for:
   - Telescope movement (slew, park, track)
   - Object lookup (catalog search, coordinates)
   - Weather monitoring
   - Safety status checks

   Always verify safety before movement commands.
   For ambiguous object names, ask for clarification.
   Acknowledge all commands before execution.
   ```

**Key Insight:** The LLM serves as a natural language interface to the structured tool system, not as a decision-maker for safety-critical operations. Safety logic remains in deterministic code.

---

## Consensus Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        NIGHTWATCH Voice Pipeline                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────┐    ┌──────────┐    ┌─────────┐    ┌─────────┐   │
│   │   Mic   │───►│ Whisper  │───►│   LLM   │───►│  Piper  │───►│Speaker
│   │  Input  │    │   STT    │    │ (8B-Q4) │    │   TTS   │   │
│   └─────────┘    └──────────┘    └────┬────┘    └─────────┘   │
│                                       │                         │
│                              ┌────────▼────────┐                │
│                              │  Tool Executor  │                │
│                              └────────┬────────┘                │
│                                       │                         │
│   ┌──────────┬──────────┬────────────┼────────────┐            │
│   │          │          │            │            │            │
│   ▼          ▼          ▼            ▼            ▼            │
│ Mount    Catalog    Weather      Safety      Ephemeris         │
│ Control  Service    Service      Monitor     Service           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Recommendations

### Phase 1: Basic Integration
1. Deploy Whisper medium with faster-whisper
2. Integrate Llama 3.2 8B with basic tool calling
3. Implement Piper TTS with lessac voice
4. Create initial tool handlers for mount control

### Phase 2: Optimization
1. Add astronomy vocabulary boosting to Whisper
2. Implement response caching for common phrases
3. Enable streaming synthesis in Piper
4. Optimize KV-cache for multi-turn conversations

### Phase 3: Refinement
1. Collect voice command dataset for analysis
2. Fine-tune Whisper on astronomy terminology (if needed)
3. Add multi-language support (optional)
4. Implement voice authentication (optional)

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| LLM hallucination | Tool-based architecture limits scope of actions |
| Misrecognition of commands | Confirmation required for destructive ops |
| Model loading time | Pre-load all models at system startup |
| Power failure during inference | Safety system operates independently |
| Acoustic interference | VAD filtering, noise-robust Whisper |

---

## Conclusion

The panel recommends a local-first architecture with:
- **Whisper Medium** for robust speech recognition with astronomy vocabulary boosting
- **Llama 3.2 8B (Q4)** for natural language understanding and tool selection
- **Piper TTS** for responsive, natural voice feedback
- **Structured tool-calling** to maintain safety boundaries

This architecture leverages the DGX Spark's unified memory and substantial GPU compute while maintaining the safety-critical requirement that all telescope operations pass through deterministic safety checks.

---

*Document prepared by the NIGHTWATCH Panel of Specialists*
