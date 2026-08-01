"""
SEC3-1: Security tests for the Wyoming STT server.

Covers:
- Wyoming bind defaults are loopback, not 0.0.0.0.
- Per-session audio buffer is bounded (no unbounded memory growth from a
  malicious/broken client that never sends AUDIO_STOP).

These drive the REAL message handler (no mocking of the buffer under test).
"""

import pytest

from voice.wyoming.stt_server import (
    WyomingSTTServer,
    ClientSession,
    MAX_AUDIO_BUFFER_BYTES,
)
from voice.wyoming.protocol import WyomingMessage, MessageType


def test_stt_server_default_host_is_loopback():
    """SEC3-1: STT server must bind loopback by default, not 0.0.0.0."""
    server = WyomingSTTServer()
    assert server.host == "127.0.0.1"


def test_session_starts_with_zero_buffered_bytes():
    session = ClientSession()
    assert session.buffered_bytes == 0
    session.audio_buffer.append(b"x")
    session.buffered_bytes = 123
    session.reset()
    assert session.buffered_bytes == 0
    assert session.audio_buffer == []


@pytest.mark.asyncio
async def test_audio_buffer_is_bounded():
    """SEC3-1: feeding chunks past the cap keeps the buffer bounded."""
    server = WyomingSTTServer()
    session = ClientSession()

    # Begin streaming
    await server._handle_message(WyomingMessage.audio_start(), session)
    assert session.is_streaming is True

    # Send well past the cap: MAX + several chunks worth.
    chunk = b"\x00" * 32000  # 1 second of 16kHz 16-bit mono
    num_chunks = (MAX_AUDIO_BUFFER_BYTES // len(chunk)) + 50

    for _ in range(num_chunks):
        await server._handle_message(
            WyomingMessage.audio_chunk(chunk), session
        )
        # Invariant: buffered bytes never exceed the cap.
        assert session.buffered_bytes <= MAX_AUDIO_BUFFER_BYTES
        # And the accumulated buffer size matches the tracked byte count.
        assert sum(len(c) for c in session.audio_buffer) == session.buffered_bytes

    # The stream must have been reset at least once (cap enforced), so the
    # final buffer is far smaller than the total bytes we attempted to send.
    total_attempted = num_chunks * len(chunk)
    assert total_attempted > MAX_AUDIO_BUFFER_BYTES
    assert session.buffered_bytes <= MAX_AUDIO_BUFFER_BYTES
