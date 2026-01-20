"""
Audio fixture files for voice tests (Step 580).

Provides synthetic audio data for testing STT/TTS pipelines without
requiring actual audio hardware or recordings.

Usage:
    from tests.fixtures.audio import (
        generate_silence,
        generate_tone,
        generate_speech_envelope,
        get_test_audio_16k,
        SAMPLE_COMMANDS,
    )

    # Get 1 second of silence at 16kHz
    silence = generate_silence(duration_sec=1.0, sample_rate=16000)

    # Get test audio for STT testing
    audio = get_test_audio_16k("park the telescope")
"""

import struct
import math
from typing import Optional, List, Tuple
from dataclasses import dataclass


# Standard sample rates
RATE_16K = 16000  # Whisper input
RATE_22K = 22050  # Piper output
RATE_44K = 44100  # CD quality


@dataclass
class AudioConfig:
    """Audio configuration for test fixtures."""
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2  # 16-bit
    dtype: str = "int16"


# Common voice commands for testing
SAMPLE_COMMANDS = [
    "park the telescope",
    "slew to Andromeda",
    "what is the current position",
    "take a five second exposure",
    "set tracking rate to sidereal",
    "close the roof",
    "emergency stop",
    "check weather conditions",
    "focus inward fifty steps",
    "start autoguiding",
]

# Expected responses for TTS testing
SAMPLE_RESPONSES = [
    "Parking telescope now.",
    "Slewing to Andromeda Galaxy at RA 0h 42m, Dec +41 degrees.",
    "Current position is RA 12 hours 30 minutes, Declination plus 45 degrees.",
    "Starting 5 second exposure.",
    "Tracking rate set to sidereal.",
    "Closing observatory roof.",
    "Emergency stop activated. All motion halted.",
    "Weather is clear, humidity 45 percent, wind 5 miles per hour.",
    "Moving focuser inward 50 steps.",
    "Autoguiding started, guide star acquired.",
]


def generate_silence(
    duration_sec: float,
    sample_rate: int = RATE_16K,
    channels: int = 1,
) -> bytes:
    """
    Generate silent audio data.

    Args:
        duration_sec: Duration in seconds
        sample_rate: Sample rate in Hz
        channels: Number of audio channels

    Returns:
        Raw PCM audio bytes (16-bit signed)
    """
    num_samples = int(duration_sec * sample_rate * channels)
    return bytes(num_samples * 2)  # 2 bytes per sample


def generate_tone(
    frequency_hz: float,
    duration_sec: float,
    amplitude: float = 0.5,
    sample_rate: int = RATE_16K,
) -> bytes:
    """
    Generate a pure sine wave tone.

    Args:
        frequency_hz: Tone frequency in Hz
        duration_sec: Duration in seconds
        amplitude: Amplitude (0.0 to 1.0)
        sample_rate: Sample rate in Hz

    Returns:
        Raw PCM audio bytes (16-bit signed)
    """
    num_samples = int(duration_sec * sample_rate)
    max_val = 32767  # Max for 16-bit signed

    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = int(amplitude * max_val * math.sin(2 * math.pi * frequency_hz * t))
        samples.append(struct.pack("<h", value))

    return b"".join(samples)


def generate_speech_envelope(
    duration_sec: float,
    sample_rate: int = RATE_16K,
    base_frequency: float = 150.0,
    variation: float = 50.0,
) -> bytes:
    """
    Generate audio with speech-like amplitude envelope.

    Creates audio that mimics the amplitude patterns of speech
    without actual speech content. Useful for VAD testing.

    Args:
        duration_sec: Duration in seconds
        sample_rate: Sample rate in Hz
        base_frequency: Base frequency for the carrier
        variation: Frequency variation range

    Returns:
        Raw PCM audio bytes (16-bit signed)
    """
    num_samples = int(duration_sec * sample_rate)
    max_val = 32767

    samples = []
    for i in range(num_samples):
        t = i / sample_rate

        # Amplitude envelope (speech-like bursts)
        envelope = 0.3 + 0.7 * abs(math.sin(2 * math.pi * 3 * t))  # ~3Hz syllable rate

        # Frequency variation
        freq = base_frequency + variation * math.sin(2 * math.pi * 0.5 * t)

        # Generate sample
        value = int(envelope * 0.5 * max_val * math.sin(2 * math.pi * freq * t))
        samples.append(struct.pack("<h", value))

    return b"".join(samples)


def generate_noise(
    duration_sec: float,
    amplitude: float = 0.1,
    sample_rate: int = RATE_16K,
) -> bytes:
    """
    Generate white noise.

    Args:
        duration_sec: Duration in seconds
        amplitude: Amplitude (0.0 to 1.0)
        sample_rate: Sample rate in Hz

    Returns:
        Raw PCM audio bytes (16-bit signed)
    """
    import random
    num_samples = int(duration_sec * sample_rate)
    max_val = 32767

    samples = []
    for _ in range(num_samples):
        value = int(amplitude * max_val * (random.random() * 2 - 1))
        samples.append(struct.pack("<h", value))

    return b"".join(samples)


def get_test_audio_16k(command: str, duration_sec: float = 2.0) -> bytes:
    """
    Get test audio for a given command.

    Returns synthetic audio with speech-like characteristics.
    The audio doesn't contain actual speech but has properties
    suitable for testing audio processing pipelines.

    Args:
        command: The command text (used to vary the audio)
        duration_sec: Audio duration in seconds

    Returns:
        Raw PCM audio bytes at 16kHz mono 16-bit
    """
    # Use command hash to vary the audio deterministically
    cmd_hash = hash(command) % 1000

    # Vary frequency based on command
    base_freq = 120 + (cmd_hash % 100)

    return generate_speech_envelope(
        duration_sec=duration_sec,
        sample_rate=RATE_16K,
        base_frequency=base_freq,
    )


def create_wav_header(
    data_size: int,
    sample_rate: int = RATE_16K,
    channels: int = 1,
    bits_per_sample: int = 16,
) -> bytes:
    """
    Create a WAV file header.

    Args:
        data_size: Size of audio data in bytes
        sample_rate: Sample rate in Hz
        channels: Number of channels
        bits_per_sample: Bits per sample

    Returns:
        44-byte WAV header
    """
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        data_size + 36,  # File size - 8
        b"WAVE",
        b"fmt ",
        16,  # Subchunk1Size (PCM)
        1,   # AudioFormat (PCM)
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header


def audio_to_wav(audio_data: bytes, sample_rate: int = RATE_16K) -> bytes:
    """
    Convert raw PCM audio to WAV format.

    Args:
        audio_data: Raw PCM audio bytes
        sample_rate: Sample rate in Hz

    Returns:
        Complete WAV file as bytes
    """
    header = create_wav_header(len(audio_data), sample_rate)
    return header + audio_data


class AudioFixture:
    """
    Audio fixture generator for voice tests.

    Provides consistent audio data for testing voice pipelines.
    """

    def __init__(self, sample_rate: int = RATE_16K):
        self.sample_rate = sample_rate

    def silence(self, duration_sec: float) -> bytes:
        """Generate silence."""
        return generate_silence(duration_sec, self.sample_rate)

    def tone(self, frequency: float, duration_sec: float) -> bytes:
        """Generate a tone."""
        return generate_tone(frequency, duration_sec, sample_rate=self.sample_rate)

    def speech_like(self, duration_sec: float) -> bytes:
        """Generate speech-like audio."""
        return generate_speech_envelope(duration_sec, self.sample_rate)

    def noise(self, duration_sec: float, amplitude: float = 0.1) -> bytes:
        """Generate noise."""
        return generate_noise(duration_sec, amplitude, self.sample_rate)

    def command_audio(self, command: str) -> bytes:
        """Get audio for a specific command."""
        return get_test_audio_16k(command)

    def as_wav(self, audio_data: bytes) -> bytes:
        """Convert audio to WAV format."""
        return audio_to_wav(audio_data, self.sample_rate)


# Pre-built fixtures for common test cases
SILENCE_1S = generate_silence(1.0)
SILENCE_100MS = generate_silence(0.1)
TONE_440HZ_1S = generate_tone(440.0, 1.0)
SPEECH_ENVELOPE_2S = generate_speech_envelope(2.0)
NOISE_1S = generate_noise(1.0, 0.05)


def get_command_audio_pairs() -> List[Tuple[str, bytes]]:
    """
    Get list of (command, audio) pairs for testing.

    Returns:
        List of tuples containing command text and corresponding audio
    """
    return [(cmd, get_test_audio_16k(cmd)) for cmd in SAMPLE_COMMANDS]
