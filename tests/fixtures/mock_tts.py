"""
Mock Text-to-Speech Service for Testing.

Simulates TTS (Piper) for unit and integration testing.
Provides configurable audio generation and playback simulation.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, List, Any

logger = logging.getLogger("NIGHTWATCH.fixtures.MockTTS")


class MockTTSState(Enum):
    """TTS service state."""
    DISCONNECTED = "disconnected"
    READY = "ready"
    SYNTHESIZING = "synthesizing"
    PLAYING = "playing"
    ERROR = "error"


@dataclass
class SynthesisResult:
    """Result of text-to-speech synthesis."""
    text: str
    audio_data: bytes = b""
    duration_sec: float = 0.0
    sample_rate: int = 22050
    synthesis_time_sec: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "duration_sec": self.duration_sec,
            "sample_rate": self.sample_rate,
            "synthesis_time_sec": self.synthesis_time_sec,
            "audio_size_bytes": len(self.audio_data),
        }


@dataclass
class TTSStats:
    """TTS usage statistics."""
    total_synthesized: int = 0
    total_characters: int = 0
    total_audio_seconds: float = 0.0
    average_synthesis_time: float = 0.0


class MockTTS:
    """
    Mock TTS service for testing.

    Simulates Piper text-to-speech with:
    - Text synthesis simulation
    - Audio playback simulation
    - Voice configuration
    - Speech rate control
    - Error injection

    Example:
        tts = MockTTS()
        await tts.connect()

        # Synthesize and play
        await tts.speak("Hello, welcome to NIGHTWATCH")

        # Or just synthesize
        result = await tts.synthesize("The telescope is now parked")
    """

    # Default voice configuration
    DEFAULT_VOICE = "en_US-lessac-medium"
    DEFAULT_SAMPLE_RATE = 22050

    # Estimated speech rate (characters per second)
    SPEECH_RATE_CPS = 15.0

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        simulate_delays: bool = True,
    ):
        """
        Initialize mock TTS.

        Args:
            voice: Voice model name
            sample_rate: Audio sample rate
            simulate_delays: Whether to simulate synthesis/playback time
        """
        self.voice = voice
        self.sample_rate = sample_rate
        self.simulate_delays = simulate_delays

        # State
        self._state = MockTTSState.DISCONNECTED
        self._stats = TTSStats()
        self._is_playing = False
        self._speech_rate = 1.0  # Multiplier

        # Queue for sequential playback
        self._speech_queue: List[str] = []
        self._playback_task: Optional[asyncio.Task] = None

        # Last synthesis result
        self._last_result: Optional[SynthesisResult] = None

        # Error injection
        self._inject_connect_error = False
        self._inject_synthesize_error = False
        self._inject_playback_error = False

        # Callbacks
        self._synthesis_callbacks: List[Callable] = []
        self._playback_callbacks: List[Callable] = []
        self._complete_callbacks: List[Callable] = []

    @property
    def state(self) -> MockTTSState:
        """Get current state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if TTS is connected."""
        return self._state != MockTTSState.DISCONNECTED

    @property
    def is_speaking(self) -> bool:
        """Check if currently playing audio."""
        return self._is_playing

    async def connect(self) -> bool:
        """
        Connect to TTS service.

        Returns:
            True if connected successfully
        """
        if self._inject_connect_error:
            raise ConnectionError("Mock: Simulated connection failure")

        if self.simulate_delays:
            await asyncio.sleep(0.1)

        self._state = MockTTSState.READY
        logger.info(f"MockTTS connected: voice={self.voice}")
        return True

    async def disconnect(self):
        """Disconnect from TTS service."""
        await self.stop()
        self._state = MockTTSState.DISCONNECTED
        logger.info("MockTTS disconnected")

    async def synthesize(self, text: str) -> SynthesisResult:
        """
        Synthesize text to audio.

        Args:
            text: Text to synthesize

        Returns:
            Synthesis result with audio data
        """
        if not self.is_connected:
            raise RuntimeError("TTS not connected")

        if self._inject_synthesize_error:
            raise RuntimeError("Mock: Simulated synthesis failure")

        self._state = MockTTSState.SYNTHESIZING
        start_time = datetime.now()

        # Calculate expected audio duration
        audio_duration = len(text) / self.SPEECH_RATE_CPS / self._speech_rate

        # Simulate synthesis time (roughly proportional to text length)
        synthesis_time = 0.0
        if self.simulate_delays:
            synthesis_time = len(text) * 0.005  # ~5ms per character
            await asyncio.sleep(synthesis_time)

        # Generate fake audio data (silence)
        # In real implementation this would be actual audio
        num_samples = int(audio_duration * self.sample_rate)
        audio_data = bytes(num_samples * 2)  # 16-bit audio

        synthesis_time = (datetime.now() - start_time).total_seconds()

        result = SynthesisResult(
            text=text,
            audio_data=audio_data,
            duration_sec=audio_duration,
            sample_rate=self.sample_rate,
            synthesis_time_sec=synthesis_time,
        )

        self._last_result = result
        self._update_stats(result)
        self._state = MockTTSState.READY

        # Notify callbacks
        for callback in self._synthesis_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Synthesis callback error: {e}")

        return result

    async def play(self, audio_data: bytes, duration_sec: float = 0.0) -> bool:
        """
        Play audio data.

        Args:
            audio_data: Audio bytes to play
            duration_sec: Expected duration (for simulation)

        Returns:
            True if playback completed
        """
        if not self.is_connected:
            raise RuntimeError("TTS not connected")

        if self._inject_playback_error:
            raise RuntimeError("Mock: Simulated playback failure")

        self._state = MockTTSState.PLAYING
        self._is_playing = True

        # Notify playback started
        for callback in self._playback_callbacks:
            try:
                callback("started")
            except Exception as e:
                logger.error(f"Playback callback error: {e}")

        # Simulate playback time
        if self.simulate_delays and duration_sec > 0:
            await asyncio.sleep(duration_sec)

        self._is_playing = False
        self._state = MockTTSState.READY

        # Notify playback complete
        for callback in self._complete_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Complete callback error: {e}")

        return True

    async def speak(self, text: str) -> bool:
        """
        Synthesize and play text (convenience method).

        Args:
            text: Text to speak

        Returns:
            True if completed successfully
        """
        logger.info(f"MockTTS speaking: '{text[:50]}{'...' if len(text) > 50 else ''}'")

        result = await self.synthesize(text)
        return await self.play(result.audio_data, result.duration_sec)

    async def speak_queued(self, text: str):
        """
        Add text to speech queue for sequential playback.

        Args:
            text: Text to queue
        """
        self._speech_queue.append(text)

        # Start queue processing if not already running
        if self._playback_task is None or self._playback_task.done():
            self._playback_task = asyncio.create_task(self._process_queue())

    async def _process_queue(self):
        """Process the speech queue."""
        while self._speech_queue:
            text = self._speech_queue.pop(0)
            try:
                await self.speak(text)
            except Exception as e:
                logger.error(f"Queue playback error: {e}")

    async def stop(self):
        """Stop current playback and clear queue."""
        self._speech_queue.clear()

        if self._playback_task and not self._playback_task.done():
            self._playback_task.cancel()
            try:
                await self._playback_task
            except asyncio.CancelledError:
                pass

        self._is_playing = False
        if self._state == MockTTSState.PLAYING:
            self._state = MockTTSState.READY

        logger.info("MockTTS playback stopped")

    def _update_stats(self, result: SynthesisResult):
        """Update usage statistics."""
        n = self._stats.total_synthesized + 1
        self._stats.total_synthesized = n
        self._stats.total_characters += len(result.text)
        self._stats.total_audio_seconds += result.duration_sec

        # Update average synthesis time
        old_avg = self._stats.average_synthesis_time
        self._stats.average_synthesis_time = (
            old_avg * (n - 1) + result.synthesis_time_sec
        ) / n

    def get_stats(self) -> TTSStats:
        """Get usage statistics."""
        return self._stats

    def get_last_result(self) -> Optional[SynthesisResult]:
        """Get the last synthesis result."""
        return self._last_result

    # Configuration
    def set_voice(self, voice: str):
        """Set the voice model."""
        self.voice = voice
        logger.info(f"MockTTS voice set to: {voice}")

    def set_speech_rate(self, rate: float):
        """
        Set speech rate multiplier.

        Args:
            rate: Rate multiplier (0.5 = half speed, 2.0 = double speed)
        """
        self._speech_rate = max(0.25, min(4.0, rate))
        logger.info(f"MockTTS speech rate set to: {self._speech_rate}")

    def get_available_voices(self) -> List[str]:
        """Get list of available voices."""
        return [
            "en_US-lessac-medium",
            "en_US-lessac-high",
            "en_US-amy-medium",
            "en_US-ryan-medium",
            "en_GB-alan-medium",
        ]

    # Callbacks
    def set_synthesis_callback(self, callback: Callable):
        """Register callback for synthesis completion."""
        self._synthesis_callbacks.append(callback)

    def set_playback_callback(self, callback: Callable):
        """Register callback for playback events."""
        self._playback_callbacks.append(callback)

    def set_complete_callback(self, callback: Callable):
        """Register callback for playback completion."""
        self._complete_callbacks.append(callback)

    # Error injection
    def inject_connect_error(self, enable: bool = True):
        """Enable/disable connection error injection."""
        self._inject_connect_error = enable

    def inject_synthesize_error(self, enable: bool = True):
        """Enable/disable synthesis error injection."""
        self._inject_synthesize_error = enable

    def inject_playback_error(self, enable: bool = True):
        """Enable/disable playback error injection."""
        self._inject_playback_error = enable

    def reset(self):
        """Reset mock to initial state."""
        self._state = MockTTSState.DISCONNECTED
        self._stats = TTSStats()
        self._is_playing = False
        self._speech_queue.clear()
        self._last_result = None
        self._inject_connect_error = False
        self._inject_synthesize_error = False
        self._inject_playback_error = False
