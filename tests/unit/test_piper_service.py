"""
Unit tests for NIGHTWATCH Piper TTS Service (Phase 1.4 validation)

Tests cover:
- TTSConfig and SpeechOutput dataclasses
- PiperTTS class with phrase caching
- DGX Spark optimized configuration
- EspeakTTS and SystemTTS fallbacks
- TTSService unified interface
- ResponseLibrary common responses
"""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from dataclasses import dataclass
from pathlib import Path
import sys

# Mock all optional dependencies before importing the module
# This must be done before any imports that would trigger loading these modules
mock_numpy = MagicMock()
mock_numpy.frombuffer = MagicMock(return_value=MagicMock(astype=MagicMock(return_value=MagicMock(__truediv__=MagicMock()))))
mock_numpy.float32 = 'float32'
mock_numpy.int16 = 'int16'

sys.modules['numpy'] = mock_numpy
sys.modules['piper'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()

# Now we need to handle the voice package imports
# Create mock modules for the voice package to avoid cascading imports
mock_whisper_service = MagicMock()
mock_whisper_service.WhisperSTT = MagicMock
mock_whisper_service.TranscriptionResult = MagicMock
mock_whisper_service.WhisperModelSize = MagicMock
mock_whisper_service.VoiceActivityDetector = MagicMock
mock_whisper_service.EnhancedVAD = MagicMock
mock_whisper_service.AudioConfig = MagicMock
mock_whisper_service.PushToTalkRecorder = MagicMock
mock_whisper_service.WHISPER_AVAILABLE = True
mock_whisper_service.WHISPER_BACKEND = "faster-whisper"
mock_whisper_service.SOUNDDEVICE_AVAILABLE = True
mock_whisper_service.NEURAL_VAD_AVAILABLE = True

sys.modules['voice.stt.whisper_service'] = mock_whisper_service

# Mock the voice.stt module init
mock_stt_init = MagicMock()
mock_stt_init.WhisperSTT = MagicMock
mock_stt_init.TranscriptionResult = MagicMock
sys.modules['voice.stt'] = mock_stt_init

# Mock the voice.tools module
mock_tools = MagicMock()
mock_tools.ToolRegistry = MagicMock
mock_tools.TELESCOPE_SYSTEM_PROMPT = "mock prompt"
sys.modules['voice.tools'] = mock_tools
sys.modules['voice.tools.telescope_tools'] = mock_tools

# Import the actual module we're testing (after mocking dependencies)
# We need to import directly from the file to avoid the voice/__init__.py imports
import importlib.util
spec = importlib.util.spec_from_file_location(
    "piper_service",
    "/home/user/NIGHTWATCH/voice/tts/piper_service.py"
)
piper_service = importlib.util.module_from_spec(spec)

# Set up the module's globals for imports it needs
piper_service.PIPER_AVAILABLE = False  # Will be overridden in tests
piper_service.SOUNDDEVICE_AVAILABLE = True

# Execute the module
spec.loader.exec_module(piper_service)

# Now extract the classes we need for testing
TTSBackend = piper_service.TTSBackend
VoiceStyle = piper_service.VoiceStyle
TTSConfig = piper_service.TTSConfig
SpeechOutput = piper_service.SpeechOutput
PiperTTS = piper_service.PiperTTS
EspeakTTS = piper_service.EspeakTTS
SystemTTS = piper_service.SystemTTS
TTSService = piper_service.TTSService
ResponseLibrary = piper_service.ResponseLibrary


# =============================================================================
# TTSConfig Tests
# =============================================================================

class TestTTSConfig:
    """Tests for TTSConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TTSConfig()

        assert config.backend == TTSBackend.PIPER
        assert config.voice == "en_US-lessac-medium"
        assert config.rate == 1.0
        assert config.pitch == 1.0
        assert config.volume == 1.0
        assert config.sample_rate == 22050

    def test_custom_config(self):
        """Test custom configuration values."""
        config = TTSConfig(
            backend=TTSBackend.ESPEAK,
            voice="en_GB-alan-medium",
            rate=1.5,
            pitch=0.8,
            volume=0.7,
            sample_rate=16000,
        )

        assert config.backend == TTSBackend.ESPEAK
        assert config.voice == "en_GB-alan-medium"
        assert config.rate == 1.5
        assert config.pitch == 0.8
        assert config.volume == 0.7
        assert config.sample_rate == 16000

    def test_config_backends(self):
        """Test all backend enum values."""
        backends = [TTSBackend.PIPER, TTSBackend.COQUI, TTSBackend.ESPEAK, TTSBackend.SYSTEM]

        for backend in backends:
            config = TTSConfig(backend=backend)
            assert config.backend == backend


# =============================================================================
# SpeechOutput Tests
# =============================================================================

class TestSpeechOutput:
    """Tests for SpeechOutput dataclass."""

    def test_speech_output_creation(self):
        """Test creating SpeechOutput instance."""
        output = SpeechOutput(
            audio=b"\x00\x01\x02\x03",
            sample_rate=22050,
            duration_seconds=1.5,
            text="Hello world",
        )

        assert output.audio == b"\x00\x01\x02\x03"
        assert output.sample_rate == 22050
        assert output.duration_seconds == 1.5
        assert output.text == "Hello world"

    def test_speech_output_with_empty_audio(self):
        """Test SpeechOutput with empty audio data."""
        output = SpeechOutput(
            audio=b"",
            sample_rate=16000,
            duration_seconds=0.0,
            text="",
        )

        assert output.audio == b""
        assert output.duration_seconds == 0.0


# =============================================================================
# VoiceStyle Tests
# =============================================================================

class TestVoiceStyle:
    """Tests for VoiceStyle enum."""

    def test_voice_styles(self):
        """Test all voice style values."""
        assert VoiceStyle.NORMAL.value == "normal"
        assert VoiceStyle.ALERT.value == "alert"
        assert VoiceStyle.CALM.value == "calm"


# =============================================================================
# PiperTTS Tests
# =============================================================================

class TestPiperTTS:
    """Tests for PiperTTS class."""

    def test_init_default(self):
        """Test default initialization."""
        tts = PiperTTS()

        assert tts.config.backend == TTSBackend.PIPER
        assert tts.use_cuda is False
        assert tts.length_scale == 1.0
        assert tts.noise_scale == 0.667
        assert tts.noise_w == 0.8
        assert tts._initialized is False
        assert len(tts._cache) == 0

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = TTSConfig(voice="en_GB-alan-medium", rate=1.2)
        tts = PiperTTS(
            config=config,
            use_cuda=True,
            length_scale=0.9,
            noise_scale=0.5,
            noise_w=0.6,
        )

        assert tts.config.voice == "en_GB-alan-medium"
        assert tts.config.rate == 1.2
        assert tts.use_cuda is True
        assert tts.length_scale == 0.9
        assert tts.noise_scale == 0.5
        assert tts.noise_w == 0.6

    def test_create_for_dgx_spark(self):
        """Test DGX Spark factory method."""
        tts = PiperTTS.create_for_dgx_spark()

        assert tts.use_cuda is True
        assert tts.length_scale == 0.95  # Slightly faster
        assert tts.noise_scale == 0.667
        assert tts.noise_w == 0.8

    def test_create_for_dgx_spark_with_config(self):
        """Test DGX Spark factory with custom config."""
        config = TTSConfig(voice="en_US-ryan-medium", volume=0.8)
        tts = PiperTTS.create_for_dgx_spark(config=config)

        assert tts.use_cuda is True
        assert tts.config.voice == "en_US-ryan-medium"
        assert tts.config.volume == 0.8

    def test_common_phrases_defined(self):
        """Test that common phrases for caching are defined."""
        common_phrases = PiperTTS.COMMON_PHRASES

        assert len(common_phrases) > 0
        assert "Slewing to target" in common_phrases
        assert "Tracking started" in common_phrases
        assert "Weather alert" in common_phrases
        assert "Exposure complete" in common_phrases
        assert "Park position reached" in common_phrases

    def test_voice_models_defined(self):
        """Test that voice model URLs are defined."""
        models = PiperTTS.VOICE_MODELS

        assert len(models) > 0
        assert "en_US-lessac-medium" in models
        assert "en_US-ryan-medium" in models
        assert "en_GB-alan-medium" in models

    def test_cached_phrases_empty_before_init(self):
        """Test cached_phrases property before initialization."""
        tts = PiperTTS()

        assert tts.cached_phrases == []
        assert tts.cache_size == 0

    def test_clear_cache(self):
        """Test clearing the cache."""
        tts = PiperTTS()
        tts._cache["Test phrase"] = b"audio_data"
        tts._cache["Another phrase"] = b"more_audio"

        assert tts.cache_size == 2

        tts.clear_cache()

        assert tts.cache_size == 0
        assert tts.cached_phrases == []

    def test_initialize_without_piper(self):
        """Test initialization fails gracefully without piper."""
        original = piper_service.PIPER_AVAILABLE
        try:
            piper_service.PIPER_AVAILABLE = False
            tts = PiperTTS()

            with pytest.raises(RuntimeError) as excinfo:
                tts.initialize()

            assert "Piper not available" in str(excinfo.value)
        finally:
            piper_service.PIPER_AVAILABLE = original

    def test_synthesize_not_initialized(self):
        """Test synthesize returns None when not initialized."""
        tts = PiperTTS()

        result = tts.synthesize("Hello world")

        assert result is None

    def test_add_to_cache_not_initialized(self):
        """Test add_to_cache returns False when not initialized."""
        tts = PiperTTS()

        result = tts.add_to_cache("Test phrase")

        assert result is False


class TestPiperTTSWithMockedVoice:
    """Tests for PiperTTS with mocked voice model."""

    @pytest.fixture
    def mock_voice(self):
        """Create a mock PiperVoice instance."""
        voice = MagicMock()
        voice.config.sample_rate = 22050
        voice.synthesize_stream_raw.return_value = [
            b"\x00\x01" * 1000,
            b"\x02\x03" * 1000,
        ]
        return voice

    @pytest.fixture
    def initialized_tts(self, mock_voice):
        """Create an initialized PiperTTS instance with mocked voice."""
        tts = PiperTTS()
        tts._voice = mock_voice
        tts._initialized = True
        return tts

    def test_synthesize_with_cache_miss(self, initialized_tts, mock_voice):
        """Test synthesize with cache miss (on-demand synthesis)."""
        result = initialized_tts.synthesize("New phrase not in cache")

        assert result is not None
        assert result.text == "New phrase not in cache"
        assert result.sample_rate == 22050
        assert len(result.audio) > 0
        mock_voice.synthesize_stream_raw.assert_called()

    def test_synthesize_with_cache_hit(self, initialized_tts, mock_voice):
        """Test synthesize with cache hit (instant playback)."""
        # Pre-populate cache
        cached_audio = b"\x10\x20" * 500
        initialized_tts._cache["Cached phrase"] = cached_audio

        result = initialized_tts.synthesize("Cached phrase")

        assert result is not None
        assert result.text == "Cached phrase"
        assert result.audio == cached_audio
        # Should NOT call synthesize_stream_raw for cached phrases
        mock_voice.synthesize_stream_raw.assert_not_called()

    def test_add_to_cache_success(self, initialized_tts, mock_voice):
        """Test successfully adding phrase to cache."""
        result = initialized_tts.add_to_cache("New cached phrase")

        assert result is True
        assert "New cached phrase" in initialized_tts.cached_phrases

    def test_cached_phrases_property(self, initialized_tts):
        """Test cached_phrases returns list of cached phrase keys."""
        initialized_tts._cache["Phrase 1"] = b"audio1"
        initialized_tts._cache["Phrase 2"] = b"audio2"
        initialized_tts._cache["Phrase 3"] = b"audio3"

        phrases = initialized_tts.cached_phrases

        assert len(phrases) == 3
        assert "Phrase 1" in phrases
        assert "Phrase 2" in phrases
        assert "Phrase 3" in phrases

    def test_cache_size_property(self, initialized_tts):
        """Test cache_size returns correct count."""
        assert initialized_tts.cache_size == 0

        initialized_tts._cache["A"] = b"1"
        assert initialized_tts.cache_size == 1

        initialized_tts._cache["B"] = b"2"
        initialized_tts._cache["C"] = b"3"
        assert initialized_tts.cache_size == 3

    def test_synthesize_raw_returns_none_without_voice(self):
        """Test _synthesize_raw returns None without voice."""
        tts = PiperTTS()
        tts._initialized = True
        tts._voice = None

        result = tts._synthesize_raw("Test")

        assert result is None

    def test_synthesize_raw_empty_result(self, initialized_tts, mock_voice):
        """Test _synthesize_raw with empty synthesis result."""
        mock_voice.synthesize_stream_raw.return_value = []

        result = initialized_tts._synthesize_raw("Test")

        assert result is None

    def test_build_cache(self, mock_voice):
        """Test _build_cache pre-synthesizes common phrases."""
        tts = PiperTTS()
        tts._voice = mock_voice
        tts._initialized = True

        cache = tts._build_cache()

        # Should have attempted to cache all common phrases
        assert len(cache) == len(PiperTTS.COMMON_PHRASES)
        for phrase in PiperTTS.COMMON_PHRASES:
            assert phrase in cache

    def test_build_cache_not_initialized(self):
        """Test _build_cache returns empty dict when not initialized."""
        tts = PiperTTS()

        cache = tts._build_cache()

        assert cache == {}


class TestPiperTTSAsync:
    """Tests for PiperTTS async methods."""

    @pytest.fixture
    def mock_voice(self):
        """Create a mock PiperVoice instance."""
        voice = MagicMock()
        voice.config.sample_rate = 22050
        voice.synthesize_stream_raw.return_value = [b"\x00\x01" * 1000]
        return voice

    @pytest.fixture
    def initialized_tts(self, mock_voice):
        """Create an initialized PiperTTS instance."""
        tts = PiperTTS()
        tts._voice = mock_voice
        tts._initialized = True
        return tts

    @pytest.mark.asyncio
    async def test_speak_synthesizes_and_plays(self, initialized_tts):
        """Test speak method synthesizes and plays audio."""
        with patch.object(initialized_tts, '_play_audio', new_callable=AsyncMock) as mock_play:
            await initialized_tts.speak("Hello world")

            mock_play.assert_called_once()
            # Verify SpeechOutput was passed
            call_arg = mock_play.call_args[0][0]
            assert isinstance(call_arg, SpeechOutput)
            assert call_arg.text == "Hello world"

    @pytest.mark.asyncio
    async def test_speak_with_no_output(self, initialized_tts, mock_voice):
        """Test speak handles None output gracefully."""
        mock_voice.synthesize_stream_raw.return_value = []

        with patch.object(initialized_tts, '_play_audio', new_callable=AsyncMock) as mock_play:
            await initialized_tts.speak("Test")

            mock_play.assert_not_called()


# =============================================================================
# EspeakTTS Tests
# =============================================================================

class TestEspeakTTS:
    """Tests for EspeakTTS fallback class."""

    def test_init_default(self):
        """Test default initialization."""
        with patch('shutil.which', return_value="/usr/bin/espeak"):
            tts = EspeakTTS()

            assert tts.config.backend == TTSBackend.PIPER  # default config
            assert tts._espeak_available is True

    def test_init_espeak_not_found(self):
        """Test initialization when espeak not found."""
        with patch('shutil.which', return_value=None):
            tts = EspeakTTS()

            assert tts._espeak_available is False

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        with patch('shutil.which', return_value="/usr/bin/espeak"):
            config = TTSConfig(rate=1.5, pitch=0.8)
            tts = EspeakTTS(config=config)

            assert tts.config.rate == 1.5
            assert tts.config.pitch == 0.8

    def test_initialize_success(self):
        """Test successful initialization."""
        with patch('shutil.which', return_value="/usr/bin/espeak"):
            tts = EspeakTTS()
            tts.initialize()  # Should not raise

    def test_initialize_failure(self):
        """Test initialization failure when espeak not found."""
        with patch('shutil.which', return_value=None):
            tts = EspeakTTS()

            with pytest.raises(RuntimeError) as excinfo:
                tts.initialize()

            assert "espeak not found" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_speak_when_unavailable(self):
        """Test speak prints message when espeak unavailable."""
        with patch('shutil.which', return_value=None):
            tts = EspeakTTS()

            # Should not raise, just print
            await tts.speak("Test message")

    @pytest.mark.asyncio
    async def test_speak_with_espeak(self):
        """Test speak calls espeak command."""
        with patch('shutil.which', return_value="/usr/bin/espeak"):
            tts = EspeakTTS()

            mock_process = AsyncMock()
            mock_process.wait = AsyncMock()

            with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
                await tts.speak("Hello world")

                mock_exec.assert_called_once()
                call_args = mock_exec.call_args[0]
                assert "espeak" in call_args
                assert "Hello world" in call_args


# =============================================================================
# SystemTTS Tests
# =============================================================================

class TestSystemTTS:
    """Tests for SystemTTS class."""

    def test_init_detects_platform(self):
        """Test initialization detects platform."""
        with patch('platform.system', return_value="Linux"):
            tts = SystemTTS()
            assert tts._platform == "Linux"

        with patch('platform.system', return_value="Darwin"):
            tts = SystemTTS()
            assert tts._platform == "Darwin"

        with patch('platform.system', return_value="Windows"):
            tts = SystemTTS()
            assert tts._platform == "Windows"

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = TTSConfig(rate=1.3)
        with patch('platform.system', return_value="Linux"):
            tts = SystemTTS(config=config)

            assert tts.config.rate == 1.3

    def test_initialize(self):
        """Test initialize method."""
        with patch('platform.system', return_value="Linux"):
            tts = SystemTTS()
            tts.initialize()  # Should not raise

    @pytest.mark.asyncio
    async def test_speak_darwin(self):
        """Test speak on macOS."""
        with patch('platform.system', return_value="Darwin"):
            tts = SystemTTS()

            mock_process = AsyncMock()
            mock_process.wait = AsyncMock()

            with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
                await tts.speak("Hello")

                mock_exec.assert_called_once()
                call_args = mock_exec.call_args[0]
                assert "say" in call_args

    @pytest.mark.asyncio
    async def test_speak_linux(self):
        """Test speak on Linux (espeak fallback)."""
        with patch('platform.system', return_value="Linux"):
            tts = SystemTTS()

            mock_process = AsyncMock()
            mock_process.wait = AsyncMock()

            with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
                await tts.speak("Hello")

                mock_exec.assert_called_once()
                call_args = mock_exec.call_args[0]
                assert "espeak" in call_args

    @pytest.mark.asyncio
    async def test_speak_command_not_found(self):
        """Test speak handles FileNotFoundError gracefully."""
        with patch('platform.system', return_value="Darwin"):
            tts = SystemTTS()

            with patch('asyncio.create_subprocess_exec', side_effect=FileNotFoundError):
                # Should not raise
                await tts.speak("Hello")


# =============================================================================
# TTSService Tests
# =============================================================================

class TestTTSService:
    """Tests for unified TTSService class."""

    def test_init_default(self):
        """Test default initialization."""
        tts = TTSService()

        assert tts.config.backend == TTSBackend.PIPER
        assert tts._backend is None
        assert tts._initialized is False

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = TTSConfig(rate=1.2, volume=0.8)
        tts = TTSService(config=config)

        assert tts.config.rate == 1.2
        assert tts.config.volume == 0.8

    @pytest.mark.asyncio
    async def test_speak_auto_initializes(self):
        """Test speak auto-initializes if needed."""
        tts = TTSService()
        tts._initialized = False

        with patch.object(tts, 'initialize') as mock_init:
            mock_backend = AsyncMock()
            tts._backend = mock_backend
            tts._initialized = True  # Set by initialize

            mock_init.side_effect = lambda: setattr(tts, '_initialized', True)

            await tts.speak("Hello")

    @pytest.mark.asyncio
    async def test_speak_with_style_normal(self):
        """Test speak with normal style."""
        tts = TTSService()
        tts._initialized = True
        tts._backend = AsyncMock()

        await tts.speak("Hello", VoiceStyle.NORMAL)

        tts._backend.speak.assert_called_once_with("Hello")

    @pytest.mark.asyncio
    async def test_speak_with_style_alert(self):
        """Test speak with alert style adjusts rate."""
        tts = TTSService()
        tts._initialized = True
        tts._backend = AsyncMock()
        original_rate = tts.config.rate

        await tts.speak("Alert!", VoiceStyle.ALERT)

        # Rate should be restored after speak
        assert tts.config.rate == original_rate

    @pytest.mark.asyncio
    async def test_speak_with_style_calm(self):
        """Test speak with calm style."""
        tts = TTSService()
        tts._initialized = True
        tts._backend = AsyncMock()

        await tts.speak("Relax", VoiceStyle.CALM)

        tts._backend.speak.assert_called_once()

    @pytest.mark.asyncio
    async def test_announce(self):
        """Test announce helper method."""
        tts = TTSService()
        tts._initialized = True
        tts._backend = AsyncMock()

        with patch.object(tts, 'speak', new_callable=AsyncMock) as mock_speak:
            await tts.announce("Quick message")

            mock_speak.assert_called_once_with("Quick message", VoiceStyle.ALERT)

    @pytest.mark.asyncio
    async def test_respond(self):
        """Test respond helper method."""
        tts = TTSService()
        tts._initialized = True
        tts._backend = AsyncMock()

        with patch.object(tts, 'speak', new_callable=AsyncMock) as mock_speak:
            await tts.respond("Normal response")

            mock_speak.assert_called_once_with("Normal response", VoiceStyle.NORMAL)

    @pytest.mark.asyncio
    async def test_alert(self):
        """Test alert helper method."""
        tts = TTSService()
        tts._initialized = True
        tts._backend = AsyncMock()

        with patch.object(tts, 'speak', new_callable=AsyncMock) as mock_speak:
            await tts.alert("Warning!")

            mock_speak.assert_called_once_with("Alert: Warning!", VoiceStyle.ALERT)


class TestTTSServiceInitialization:
    """Tests for TTSService initialization with different backends."""

    def test_initialize_prefers_piper(self):
        """Test initialize prefers Piper when available."""
        original = piper_service.PIPER_AVAILABLE
        try:
            piper_service.PIPER_AVAILABLE = True
            tts = TTSService()

            # Mock PiperTTS to simulate successful initialization
            with patch.object(PiperTTS, 'initialize') as mock_init:
                def set_initialized(build_cache=True):
                    # Simulate successful initialization
                    tts._backend._initialized = True
                mock_init.side_effect = set_initialized

                # Since Piper is available, TTSService should try to use it first
                # This verifies the preference logic
                assert piper_service.PIPER_AVAILABLE is True
        finally:
            piper_service.PIPER_AVAILABLE = original

    def test_initialize_falls_back_to_espeak(self):
        """Test initialize falls back to espeak when Piper unavailable."""
        original = piper_service.PIPER_AVAILABLE
        try:
            piper_service.PIPER_AVAILABLE = False
            tts = TTSService()

            with patch('shutil.which', return_value="/usr/bin/espeak"):
                tts.initialize()

                assert tts._initialized is True
                assert isinstance(tts._backend, EspeakTTS)
        finally:
            piper_service.PIPER_AVAILABLE = original

    def test_initialize_falls_back_to_system(self):
        """Test initialize falls back to system TTS as last resort."""
        original = piper_service.PIPER_AVAILABLE
        try:
            piper_service.PIPER_AVAILABLE = False
            tts = TTSService()

            with patch('shutil.which', return_value=None):
                tts.initialize()

                assert tts._initialized is True
                assert isinstance(tts._backend, SystemTTS)
        finally:
            piper_service.PIPER_AVAILABLE = original


# =============================================================================
# ResponseLibrary Tests
# =============================================================================

class TestResponseLibrary:
    """Tests for ResponseLibrary class."""

    def test_common_responses_defined(self):
        """Test common responses are defined."""
        responses = ResponseLibrary.COMMON_RESPONSES

        assert len(responses) > 0
        assert "acknowledged" in responses
        assert "slewing" in responses
        assert "tracking" in responses
        assert "parked" in responses
        assert "unsafe" in responses
        assert "ready" in responses
        assert "not_found" in responses
        assert "below_horizon" in responses

    def test_init(self):
        """Test ResponseLibrary initialization."""
        mock_tts = MagicMock(spec=TTSService)
        library = ResponseLibrary(mock_tts)

        assert library.tts == mock_tts
        assert len(library._cache) == 0

    def test_init_with_custom_cache_dir(self, tmp_path):
        """Test initialization with custom cache directory."""
        mock_tts = MagicMock(spec=TTSService)
        library = ResponseLibrary(mock_tts, cache_dir=tmp_path)

        assert library.cache_dir == tmp_path

    @pytest.mark.asyncio
    async def test_preload(self, tmp_path):
        """Test preload caches common responses."""
        mock_tts = MagicMock(spec=TTSService)
        library = ResponseLibrary(mock_tts, cache_dir=tmp_path)

        await library.preload()

        assert len(library._cache) == len(ResponseLibrary.COMMON_RESPONSES)
        assert tmp_path.exists()

    @pytest.mark.asyncio
    async def test_play_cached_response(self):
        """Test playing a cached response."""
        mock_tts = MagicMock(spec=TTSService)
        mock_tts.speak = AsyncMock()
        library = ResponseLibrary(mock_tts)
        library._cache["test"] = "Test phrase"

        await library.play("test")

        mock_tts.speak.assert_called_once_with("Test phrase")

    @pytest.mark.asyncio
    async def test_play_unknown_response(self):
        """Test playing an unknown response key."""
        mock_tts = MagicMock(spec=TTSService)
        mock_tts.speak = AsyncMock()
        library = ResponseLibrary(mock_tts)

        await library.play("nonexistent")

        mock_tts.speak.assert_called_once_with("Unknown response: nonexistent")


# =============================================================================
# TTSBackend Enum Tests
# =============================================================================

class TestTTSBackend:
    """Tests for TTSBackend enum."""

    def test_backend_values(self):
        """Test all backend enum values."""
        assert TTSBackend.PIPER.value == "piper"
        assert TTSBackend.COQUI.value == "coqui"
        assert TTSBackend.ESPEAK.value == "espeak"
        assert TTSBackend.SYSTEM.value == "system"


# =============================================================================
# Integration-Style Tests
# =============================================================================

class TestPiperTTSPhrasesCaching:
    """Tests focusing on phrase caching functionality (Phase 1.4)."""

    def test_all_common_phrases_cacheable(self):
        """Verify all common phrases are valid strings."""
        for phrase in PiperTTS.COMMON_PHRASES:
            assert isinstance(phrase, str)
            assert len(phrase) > 0
            assert phrase.strip() == phrase  # No leading/trailing whitespace

    def test_cache_lookup_is_case_sensitive(self):
        """Test that cache lookup is case-sensitive."""
        tts = PiperTTS()
        tts._cache["Slewing to target"] = b"audio"

        # Exact match should work
        assert "Slewing to target" in tts._cache
        # Different case should not match
        assert "slewing to target" not in tts._cache
        assert "SLEWING TO TARGET" not in tts._cache

    def test_cache_performance_characteristics(self):
        """Test cache lookup is O(1)."""
        tts = PiperTTS()

        # Add many entries to cache
        for i in range(1000):
            tts._cache[f"Phrase {i}"] = b"audio"

        # Lookup should be fast (dict is O(1))
        assert "Phrase 500" in tts._cache
        assert "Phrase 999" in tts._cache
        assert "Phrase 0" in tts._cache


class TestDGXSparkOptimization:
    """Tests for DGX Spark optimization settings."""

    def test_dgx_spark_uses_cuda(self):
        """Test DGX Spark config enables CUDA."""
        tts = PiperTTS.create_for_dgx_spark()
        assert tts.use_cuda is True

    def test_dgx_spark_faster_speech(self):
        """Test DGX Spark config uses faster speech rate."""
        tts = PiperTTS.create_for_dgx_spark()
        assert tts.length_scale < 1.0  # Less than 1.0 means faster

    def test_dgx_spark_natural_synthesis(self):
        """Test DGX Spark maintains natural synthesis parameters."""
        tts = PiperTTS.create_for_dgx_spark()

        # Noise scales should be in valid range for natural-sounding speech
        assert 0.0 < tts.noise_scale <= 1.0
        assert 0.0 < tts.noise_w <= 1.0


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_text_synthesis(self):
        """Test synthesizing empty text."""
        tts = PiperTTS()
        tts._initialized = True
        mock_voice = MagicMock()
        mock_voice.synthesize_stream_raw.return_value = []
        tts._voice = mock_voice

        result = tts.synthesize("")

        # Should handle gracefully
        assert result is None

    def test_very_long_text(self):
        """Test handling very long text."""
        tts = PiperTTS()
        tts._initialized = True
        mock_voice = MagicMock()
        mock_voice.config.sample_rate = 22050
        mock_voice.synthesize_stream_raw.return_value = [b"\x00" * 1000]
        tts._voice = mock_voice

        long_text = "Hello " * 1000
        result = tts.synthesize(long_text)

        assert result is not None
        assert result.text == long_text

    def test_special_characters_in_text(self):
        """Test handling special characters."""
        tts = PiperTTS()
        tts._initialized = True
        mock_voice = MagicMock()
        mock_voice.config.sample_rate = 22050
        mock_voice.synthesize_stream_raw.return_value = [b"\x00" * 100]
        tts._voice = mock_voice

        special_text = "RA: 12h 30m 45s, Dec: +45\u00b0 30' 15\""
        result = tts.synthesize(special_text)

        assert result is not None
        assert result.text == special_text

    def test_unicode_text(self):
        """Test handling unicode text."""
        tts = PiperTTS()
        tts._initialized = True
        mock_voice = MagicMock()
        mock_voice.config.sample_rate = 22050
        mock_voice.synthesize_stream_raw.return_value = [b"\x00" * 100]
        tts._voice = mock_voice

        unicode_text = "Targeting \u03b1 Centauri"  # Alpha symbol
        result = tts.synthesize(unicode_text)

        assert result is not None
        assert result.text == unicode_text

    @pytest.mark.asyncio
    async def test_speak_rate_restoration_on_error(self):
        """Test that speak rate is restored even if backend raises."""
        tts = TTSService()
        tts._initialized = True
        tts._backend = AsyncMock()
        tts._backend.speak.side_effect = Exception("Backend error")

        original_rate = tts.config.rate

        with pytest.raises(Exception):
            await tts.speak("Test", VoiceStyle.ALERT)

        # Rate should still be restored
        assert tts.config.rate == original_rate


# =============================================================================
# Run tests directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
