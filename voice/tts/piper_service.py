"""
NIGHTWATCH Voice TTS Service
Text-to-Speech Output

This module provides text-to-speech capabilities for voice responses,
using Piper TTS for fast local inference on DGX Spark.

Supports:
- Piper TTS (recommended for low latency)
- Coqui TTS (alternative)
- System espeak (fallback)
"""

import asyncio
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Callable
import shutil

# Try to import audio playback
try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

# Try to import piper
try:
    from piper import PiperVoice
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False


class TTSBackend(Enum):
    """Available TTS backends."""
    PIPER = "piper"
    COQUI = "coqui"
    ESPEAK = "espeak"
    SYSTEM = "system"  # macOS say, Windows SAPI


class VoiceStyle(Enum):
    """Voice styles for different contexts."""
    NORMAL = "normal"
    ALERT = "alert"      # Faster, more urgent
    CALM = "calm"        # Slower, relaxed


@dataclass
class TTSConfig:
    """TTS configuration."""
    backend: TTSBackend = TTSBackend.PIPER
    voice: str = "en_US-lessac-medium"
    rate: float = 1.0      # Speech rate multiplier
    pitch: float = 1.0     # Pitch multiplier
    volume: float = 1.0    # Volume 0.0-1.0
    sample_rate: int = 22050


@dataclass
class SpeechOutput:
    """Generated speech output."""
    audio: bytes
    sample_rate: int
    duration_seconds: float
    text: str


class PiperTTS:
    """
    Piper TTS engine for fast local speech synthesis.

    Piper is optimized for low-latency on-device inference,
    making it ideal for interactive telescope control.

    Features:
    - GPU acceleration via CUDA for faster synthesis
    - Phrase caching for instant playback of common responses
    - Configurable synthesis parameters (length, noise scales)
    """

    # Default voice models (download from Piper releases)
    VOICE_MODELS = {
        "en_US-lessac-medium": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/",
        "en_US-ryan-medium": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/",
        "en_GB-alan-medium": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/",
    }

    # Common phrases for telescope control - pre-synthesized for instant playback
    COMMON_PHRASES = [
        "Slewing to target",
        "Tracking started",
        "Tracking stopped",
        "Weather alert",
        "Guiding active",
        "Guiding stopped",
        "Exposure complete",
        "Exposure started",
        "Park position reached",
        "Telescope parked",
        "Unparking telescope",
        "Ready for commands",
        "Command acknowledged",
        "Target acquired",
        "Below horizon",
        "Conditions unsafe",
        "Focusing started",
        "Focus complete",
    ]

    def __init__(
        self,
        config: Optional[TTSConfig] = None,
        use_cuda: bool = False,
        length_scale: float = 1.0,
        noise_scale: float = 0.667,
        noise_w: float = 0.8,
    ):
        """
        Initialize Piper TTS.

        Args:
            config: TTS configuration
            use_cuda: Enable GPU acceleration (requires CUDA-enabled piper)
            length_scale: Speech speed (1.0 = normal, <1.0 = faster, >1.0 = slower)
            noise_scale: Variation in speech (0.0-1.0, higher = more expressive)
            noise_w: Phoneme duration variation (0.0-1.0)
        """
        self.config = config or TTSConfig()
        self.use_cuda = use_cuda
        self.length_scale = length_scale
        self.noise_scale = noise_scale
        self.noise_w = noise_w

        self._voice = None
        self._model_path: Optional[Path] = None
        self._initialized = False
        self._cache: dict[str, bytes] = {}  # Phrase -> audio bytes cache

    def initialize(self, model_path: Optional[str] = None, build_cache: bool = True):
        """
        Initialize TTS engine with voice model.

        Args:
            model_path: Path to Piper voice model (.onnx file)
            build_cache: Pre-synthesize common phrases for instant playback
        """
        if not PIPER_AVAILABLE:
            raise RuntimeError(
                "Piper not available. Install with: pip install piper-tts"
            )

        if model_path:
            self._model_path = Path(model_path)
        else:
            # Use default model location
            self._model_path = Path(__file__).parent / "models" / f"{self.config.voice}.onnx"

        if not self._model_path.exists():
            print(f"Warning: Voice model not found at {self._model_path}")
            print("Download voices from: https://github.com/rhasspy/piper/releases")
            return

        # Load voice model with optional CUDA acceleration
        try:
            self._voice = PiperVoice.load(
                str(self._model_path),
                use_cuda=self.use_cuda,
            )
        except TypeError:
            # Older piper versions may not support use_cuda parameter
            self._voice = PiperVoice.load(str(self._model_path))
            if self.use_cuda:
                print("Warning: CUDA not supported by this piper version")

        self._initialized = True
        cuda_status = " (CUDA)" if self.use_cuda else ""
        print(f"Piper TTS initialized with voice: {self.config.voice}{cuda_status}")

        # Pre-synthesize common phrases for instant playback
        if build_cache:
            self._build_cache()

    def _build_cache(self) -> dict[str, bytes]:
        """
        Pre-synthesize frequently used responses for instant playback.

        This reduces latency for common telescope responses by caching
        the audio data. First response of each phrase will be instant.

        Returns:
            Dictionary mapping phrases to audio bytes
        """
        if not self._initialized or not self._voice:
            return {}

        print(f"Pre-synthesizing {len(self.COMMON_PHRASES)} common phrases...")
        cached_count = 0

        for phrase in self.COMMON_PHRASES:
            try:
                audio_data = self._synthesize_raw(phrase)
                if audio_data:
                    self._cache[phrase] = audio_data
                    cached_count += 1
            except Exception as e:
                print(f"Warning: Failed to cache phrase '{phrase}': {e}")

        print(f"Cached {cached_count} phrases for instant playback")
        return self._cache

    def _synthesize_raw(self, text: str) -> Optional[bytes]:
        """
        Synthesize text to raw audio bytes (internal method).

        Args:
            text: Text to synthesize

        Returns:
            Raw audio bytes or None on failure
        """
        if not self._voice:
            return None

        audio_data = []
        try:
            for audio_bytes in self._voice.synthesize_stream_raw(
                text,
                length_scale=self.length_scale,
                noise_scale=self.noise_scale,
                noise_w=self.noise_w,
            ):
                audio_data.append(audio_bytes)
        except TypeError:
            # Older piper versions may not support synthesis parameters
            for audio_bytes in self._voice.synthesize_stream_raw(text):
                audio_data.append(audio_bytes)

        if not audio_data:
            return None

        return b"".join(audio_data)

    @property
    def cached_phrases(self) -> list[str]:
        """Return list of cached phrases available for instant playback."""
        return list(self._cache.keys())

    @property
    def cache_size(self) -> int:
        """Return number of cached phrases."""
        return len(self._cache)

    def synthesize(self, text: str) -> Optional[SpeechOutput]:
        """
        Synthesize speech from text.

        Uses cached audio for common phrases (instant playback),
        otherwise synthesizes on-demand.

        Args:
            text: Text to speak

        Returns:
            SpeechOutput with audio data
        """
        if not self._initialized or not self._voice:
            return None

        # Check cache first for instant playback
        if text in self._cache:
            audio = self._cache[text]
        else:
            # Synthesize on-demand
            audio = self._synthesize_raw(text)
            if not audio:
                return None

        # Calculate duration
        sample_rate = self._voice.config.sample_rate
        num_samples = len(audio) // 2  # 16-bit audio
        duration = num_samples / sample_rate

        return SpeechOutput(
            audio=audio,
            sample_rate=sample_rate,
            duration_seconds=duration,
            text=text
        )

    async def speak(self, text: str):
        """
        Synthesize and play speech.

        Args:
            text: Text to speak
        """
        output = self.synthesize(text)
        if output:
            await self._play_audio(output)

    async def _play_audio(self, output: SpeechOutput):
        """Play audio output."""
        if not SOUNDDEVICE_AVAILABLE:
            print("Audio playback not available (sounddevice not installed)")
            return

        # Convert bytes to numpy array
        audio = np.frombuffer(output.audio, dtype=np.int16).astype(np.float32)
        audio = audio / 32768.0  # Normalize to -1.0 to 1.0

        # Apply volume
        audio = audio * self.config.volume

        # Play audio
        sd.play(audio, output.sample_rate)
        sd.wait()

    @classmethod
    def create_for_dgx_spark(
        cls,
        config: Optional[TTSConfig] = None,
    ) -> "PiperTTS":
        """
        Create PiperTTS optimized for DGX Spark.

        Uses CUDA acceleration and phrase caching for minimum latency
        on NVIDIA DGX Spark hardware.

        Args:
            config: Optional TTS configuration

        Returns:
            Configured PiperTTS instance (call initialize() to load model)
        """
        return cls(
            config=config,
            use_cuda=True,           # GPU acceleration
            length_scale=0.95,       # Slightly faster speech
            noise_scale=0.667,       # Natural variation
            noise_w=0.8,             # Natural phoneme duration
        )

    def add_to_cache(self, phrase: str) -> bool:
        """
        Add a custom phrase to the cache.

        Args:
            phrase: Text to pre-synthesize and cache

        Returns:
            True if successfully cached, False otherwise
        """
        if not self._initialized:
            return False

        try:
            audio = self._synthesize_raw(phrase)
            if audio:
                self._cache[phrase] = audio
                return True
        except Exception as e:
            print(f"Failed to cache phrase: {e}")
        return False

    def clear_cache(self):
        """Clear all cached phrases."""
        self._cache.clear()


class EspeakTTS:
    """
    Espeak TTS fallback using system espeak command.

    Works on Linux systems with espeak installed.
    """

    def __init__(self, config: Optional[TTSConfig] = None):
        self.config = config or TTSConfig()
        self._espeak_available = shutil.which("espeak") is not None

    def initialize(self):
        """Check espeak availability."""
        if not self._espeak_available:
            raise RuntimeError("espeak not found. Install with: apt install espeak")
        print("Espeak TTS initialized")

    async def speak(self, text: str):
        """Speak text using espeak."""
        if not self._espeak_available:
            print(f"Would speak: {text}")
            return

        # Build espeak command
        rate = int(175 * self.config.rate)  # Default espeak rate is 175
        pitch = int(50 * self.config.pitch)  # Default pitch is 50

        cmd = [
            "espeak",
            "-s", str(rate),
            "-p", str(pitch),
            text
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await process.wait()


class SystemTTS:
    """
    System TTS using platform-specific commands.

    - macOS: say command
    - Windows: PowerShell SAPI
    - Linux: espeak fallback
    """

    def __init__(self, config: Optional[TTSConfig] = None):
        self.config = config or TTSConfig()
        import platform
        self._platform = platform.system()

    def initialize(self):
        """Initialize system TTS."""
        print(f"System TTS initialized for {self._platform}")

    async def speak(self, text: str):
        """Speak using system TTS."""
        if self._platform == "Darwin":
            # macOS
            rate = int(200 * self.config.rate)
            cmd = ["say", "-r", str(rate), text]
        elif self._platform == "Windows":
            # Windows PowerShell SAPI
            ps_script = f'Add-Type -AssemblyName System.Speech; $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; $speak.Speak("{text}")'
            cmd = ["powershell", "-Command", ps_script]
        else:
            # Linux - fall back to espeak
            cmd = ["espeak", text]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await process.wait()
        except FileNotFoundError:
            print(f"TTS command not found. Would speak: {text}")


# =============================================================================
# UNIFIED TTS SERVICE
# =============================================================================

class TTSService:
    """
    Unified TTS service with automatic backend selection.

    Tries backends in order: Piper -> Coqui -> espeak -> system
    """

    def __init__(self, config: Optional[TTSConfig] = None):
        self.config = config or TTSConfig()
        self._backend = None
        self._initialized = False

    def initialize(self):
        """Initialize best available TTS backend."""
        # Try Piper first (best quality/speed)
        if PIPER_AVAILABLE:
            try:
                self._backend = PiperTTS(self.config)
                self._backend.initialize()
                if self._backend._initialized:
                    self._initialized = True
                    print(f"Using Piper TTS")
                    return
            except Exception as e:
                print(f"Piper init failed: {e}")

        # Try espeak
        if shutil.which("espeak"):
            try:
                self._backend = EspeakTTS(self.config)
                self._backend.initialize()
                self._initialized = True
                print("Using espeak TTS")
                return
            except Exception as e:
                print(f"Espeak init failed: {e}")

        # Fall back to system TTS
        self._backend = SystemTTS(self.config)
        self._backend.initialize()
        self._initialized = True
        print("Using system TTS")

    async def speak(self, text: str, style: VoiceStyle = VoiceStyle.NORMAL):
        """
        Speak text with optional style.

        Args:
            text: Text to speak
            style: Voice style (affects rate/pitch)
        """
        if not self._initialized:
            self.initialize()

        # Adjust config for style
        original_rate = self.config.rate
        if style == VoiceStyle.ALERT:
            self.config.rate = 1.2
        elif style == VoiceStyle.CALM:
            self.config.rate = 0.9

        try:
            await self._backend.speak(text)
        finally:
            self.config.rate = original_rate

    async def announce(self, text: str):
        """Quick announcement (slightly faster speech)."""
        await self.speak(text, VoiceStyle.ALERT)

    async def respond(self, text: str):
        """Normal conversational response."""
        await self.speak(text, VoiceStyle.NORMAL)

    async def alert(self, text: str):
        """Alert message (fastest, most urgent)."""
        # Prepend attention sound if available
        await self.speak(f"Alert: {text}", VoiceStyle.ALERT)


# =============================================================================
# PRE-RECORDED RESPONSES
# =============================================================================

class ResponseLibrary:
    """
    Library of pre-recorded or pre-synthesized responses
    for faster playback of common phrases.
    """

    COMMON_RESPONSES = {
        "acknowledged": "Acknowledged.",
        "slewing": "Slewing to target.",
        "tracking": "Now tracking.",
        "parked": "Telescope parked.",
        "unsafe": "Conditions are not safe for observation.",
        "ready": "Ready for commands.",
        "not_found": "Object not found in catalog.",
        "below_horizon": "Target is below the horizon.",
    }

    def __init__(self, tts: TTSService, cache_dir: Optional[Path] = None):
        self.tts = tts
        self.cache_dir = cache_dir or Path(__file__).parent / "cache"
        self._cache: dict = {}

    async def preload(self):
        """Pre-synthesize common responses."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        for key, text in self.COMMON_RESPONSES.items():
            # Would cache synthesized audio here
            self._cache[key] = text

    async def play(self, key: str):
        """Play cached response or synthesize on demand."""
        if key in self._cache:
            await self.tts.speak(self._cache[key])
        else:
            await self.tts.speak(f"Unknown response: {key}")


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    print("NIGHTWATCH Voice TTS Service Test\n")

    print(f"Piper available: {PIPER_AVAILABLE}")
    print(f"Sounddevice available: {SOUNDDEVICE_AVAILABLE}")
    print(f"Espeak available: {shutil.which('espeak') is not None}")
    print()

    async def test():
        tts = TTSService()
        tts.initialize()
        print()

        # Test basic phrases
        test_phrases = [
            "NIGHTWATCH telescope system ready.",
            "Slewing to Mars at 45 degrees altitude.",
            "Warning: Wind speed exceeds safe limits.",
        ]

        for phrase in test_phrases:
            print(f"Speaking: {phrase}")
            await tts.speak(phrase)
            await asyncio.sleep(0.5)

        # Test cached phrase (should be instant if using PiperTTS)
        if isinstance(tts._backend, PiperTTS):
            print(f"\nCached phrases: {tts._backend.cache_size}")
            cached_phrase = "Slewing to target"
            if cached_phrase in tts._backend.cached_phrases:
                print(f"Playing cached: {cached_phrase}")
                await tts.speak(cached_phrase)

    async def test_dgx_spark():
        """Test DGX Spark optimized configuration."""
        print("\n--- DGX Spark Configuration ---")
        piper = PiperTTS.create_for_dgx_spark()
        print(f"CUDA enabled: {piper.use_cuda}")
        print(f"Length scale: {piper.length_scale}")
        print(f"Noise scale: {piper.noise_scale}")
        # Note: initialize() not called without model file

    asyncio.run(test())
    asyncio.run(test_dgx_spark())
