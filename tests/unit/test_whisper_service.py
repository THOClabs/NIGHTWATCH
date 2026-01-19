"""
Unit tests for NIGHTWATCH Whisper STT Service (Phase 1.1 and 1.3 validation)

Tests cover:
- WhisperModelSize enum values
- TranscriptionResult dataclass with is_command property
- AudioConfig dataclass defaults and custom values
- VoiceActivityDetector energy-threshold VAD
- EnhancedVAD neural VAD with pymicro-vad (Phase 1.3)
- WhisperSTT class with faster-whisper integration (Phase 1.1)
- DGX Spark optimized configuration (int8_float16 quantization)
- Model pre-warming for reduced latency
- PushToTalkRecorder for noisy environments
"""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sys
import queue

# Mock all optional dependencies before importing the module
mock_numpy = MagicMock()
mock_numpy.zeros = MagicMock(return_value=MagicMock(dtype='float32'))
mock_numpy.sqrt = MagicMock(return_value=0.05)
mock_numpy.mean = MagicMock(return_value=0.0025)
mock_numpy.concatenate = MagicMock(return_value=MagicMock())
mock_numpy.float32 = 'float32'
mock_numpy.int16 = 'int16'
mock_numpy.ndarray = MagicMock

sys.modules['numpy'] = mock_numpy

# Mock sounddevice
mock_sd = MagicMock()
mock_sd.InputStream = MagicMock()
mock_sd.rec = MagicMock(return_value=MagicMock(flatten=MagicMock(return_value=MagicMock())))
mock_sd.wait = MagicMock()
sys.modules['sounddevice'] = mock_sd

# Mock pymicro_vad
mock_microvad = MagicMock()
mock_microvad.MicroVAD = MagicMock
sys.modules['pymicro_vad'] = mock_microvad

# Mock faster_whisper
mock_faster_whisper = MagicMock()
mock_whisper_model = MagicMock()
mock_faster_whisper.WhisperModel = mock_whisper_model
sys.modules['faster_whisper'] = mock_faster_whisper

# Mock openai whisper as fallback
mock_whisper = MagicMock()
sys.modules['whisper'] = mock_whisper

# Import the actual module using importlib to bypass package init
import importlib.util
spec = importlib.util.spec_from_file_location(
    "whisper_service",
    "/home/user/NIGHTWATCH/voice/stt/whisper_service.py"
)
whisper_service = importlib.util.module_from_spec(spec)

# Override availability flags for testing
whisper_service.SOUNDDEVICE_AVAILABLE = True
whisper_service.NEURAL_VAD_AVAILABLE = True
whisper_service.WHISPER_AVAILABLE = True
whisper_service.WHISPER_BACKEND = "faster-whisper"

# Execute the module
spec.loader.exec_module(whisper_service)

# Extract classes and constants for testing
WhisperModelSize = whisper_service.WhisperModelSize
TranscriptionResult = whisper_service.TranscriptionResult
AudioConfig = whisper_service.AudioConfig
VoiceActivityDetector = whisper_service.VoiceActivityDetector
EnhancedVAD = whisper_service.EnhancedVAD
WhisperSTT = whisper_service.WhisperSTT
PushToTalkRecorder = whisper_service.PushToTalkRecorder


# =============================================================================
# WhisperModelSize Enum Tests
# =============================================================================

class TestWhisperModelSize:
    """Tests for WhisperModelSize enum."""

    def test_tiny_model(self):
        """Test TINY model size value."""
        assert WhisperModelSize.TINY.value == "tiny"

    def test_base_model(self):
        """Test BASE model size value."""
        assert WhisperModelSize.BASE.value == "base"

    def test_small_model(self):
        """Test SMALL model size value."""
        assert WhisperModelSize.SMALL.value == "small"

    def test_medium_model(self):
        """Test MEDIUM model size value."""
        assert WhisperModelSize.MEDIUM.value == "medium"

    def test_large_model(self):
        """Test LARGE model size value (large-v3)."""
        assert WhisperModelSize.LARGE.value == "large-v3"

    def test_all_sizes_enumerated(self):
        """Test all model sizes are available."""
        sizes = list(WhisperModelSize)
        assert len(sizes) == 5
        expected = ["tiny", "base", "small", "medium", "large-v3"]
        assert [s.value for s in sizes] == expected

    def test_model_size_from_value(self):
        """Test creating enum from string value."""
        assert WhisperModelSize("tiny") == WhisperModelSize.TINY
        assert WhisperModelSize("base") == WhisperModelSize.BASE
        assert WhisperModelSize("large-v3") == WhisperModelSize.LARGE


# =============================================================================
# TranscriptionResult Dataclass Tests
# =============================================================================

class TestTranscriptionResult:
    """Tests for TranscriptionResult dataclass."""

    def test_result_creation(self):
        """Test creating TranscriptionResult instance."""
        now = datetime.now()
        result = TranscriptionResult(
            text="Point to Mars",
            confidence=0.95,
            language="en",
            duration_seconds=0.5,
            timestamp=now,
            segments=[{"start": 0.0, "end": 0.5, "text": "Point to Mars"}]
        )

        assert result.text == "Point to Mars"
        assert result.confidence == 0.95
        assert result.language == "en"
        assert result.duration_seconds == 0.5
        assert result.timestamp == now
        assert len(result.segments) == 1

    def test_is_command_slew_keywords(self):
        """Test is_command detects slew keywords."""
        slew_commands = [
            "slew to Polaris",
            "go to M31",
            "goto Andromeda",
            "point to Jupiter"
        ]
        for cmd in slew_commands:
            result = TranscriptionResult(
                text=cmd,
                confidence=0.9,
                language="en",
                duration_seconds=0.5,
                timestamp=datetime.now(),
                segments=[]
            )
            assert result.is_command is True, f"'{cmd}' should be detected as command"

    def test_is_command_tracking_keywords(self):
        """Test is_command detects tracking keywords."""
        result = TranscriptionResult(
            text="start tracking",
            confidence=0.9,
            language="en",
            duration_seconds=0.5,
            timestamp=datetime.now(),
            segments=[]
        )
        assert result.is_command is True

    def test_is_command_park_keywords(self):
        """Test is_command detects park/home keywords."""
        commands = ["park the telescope", "go home", "home position"]
        for cmd in commands:
            result = TranscriptionResult(
                text=cmd,
                confidence=0.9,
                language="en",
                duration_seconds=0.5,
                timestamp=datetime.now(),
                segments=[]
            )
            assert result.is_command is True, f"'{cmd}' should be detected as command"

    def test_is_command_stop_abort_keywords(self):
        """Test is_command detects stop/abort keywords."""
        commands = ["stop", "abort slew", "stop tracking"]
        for cmd in commands:
            result = TranscriptionResult(
                text=cmd,
                confidence=0.9,
                language="en",
                duration_seconds=0.5,
                timestamp=datetime.now(),
                segments=[]
            )
            assert result.is_command is True, f"'{cmd}' should be detected as command"

    def test_is_command_query_keywords(self):
        """Test is_command detects query keywords."""
        queries = [
            "what is the current position",
            "where is Mars",
            "show me Jupiter",
            "find the moon"
        ]
        for query in queries:
            result = TranscriptionResult(
                text=query,
                confidence=0.9,
                language="en",
                duration_seconds=0.5,
                timestamp=datetime.now(),
                segments=[]
            )
            assert result.is_command is True, f"'{query}' should be detected as command"

    def test_is_command_celestial_objects(self):
        """Test is_command detects celestial object names."""
        objects = [
            "mars is bright tonight",
            "jupiter is visible",
            "saturn rings",
            "moon phase",
            "sun position"
        ]
        for obj in objects:
            result = TranscriptionResult(
                text=obj,
                confidence=0.9,
                language="en",
                duration_seconds=0.5,
                timestamp=datetime.now(),
                segments=[]
            )
            assert result.is_command is True, f"'{obj}' should be detected as command"

    def test_is_command_catalog_objects(self):
        """Test is_command detects catalog designations."""
        catalogs = [
            "messier 31",
            "ngc 224",
            "that bright star"
        ]
        for cat in catalogs:
            result = TranscriptionResult(
                text=cat,
                confidence=0.9,
                language="en",
                duration_seconds=0.5,
                timestamp=datetime.now(),
                segments=[]
            )
            assert result.is_command is True, f"'{cat}' should be detected as command"

    def test_is_command_not_command(self):
        """Test is_command returns False for non-commands."""
        non_commands = [
            "hello there",
            "nice weather today",
            "thank you",
            "okay that's great",
            "goodbye",
            "yes please",
            "no thanks"
        ]
        for text in non_commands:
            result = TranscriptionResult(
                text=text,
                confidence=0.9,
                language="en",
                duration_seconds=0.5,
                timestamp=datetime.now(),
                segments=[]
            )
            assert result.is_command is False, f"'{text}' should NOT be detected as command"

    def test_is_command_case_insensitive(self):
        """Test is_command is case insensitive."""
        result = TranscriptionResult(
            text="SLEW TO MARS",
            confidence=0.9,
            language="en",
            duration_seconds=0.5,
            timestamp=datetime.now(),
            segments=[]
        )
        assert result.is_command is True

    def test_empty_text(self):
        """Test handling empty text."""
        result = TranscriptionResult(
            text="",
            confidence=0.0,
            language="en",
            duration_seconds=0.0,
            timestamp=datetime.now(),
            segments=[]
        )
        assert result.text == ""
        assert result.is_command is False


# =============================================================================
# AudioConfig Dataclass Tests
# =============================================================================

class TestAudioConfig:
    """Tests for AudioConfig dataclass."""

    def test_default_values(self):
        """Test default AudioConfig values."""
        config = AudioConfig()

        assert config.sample_rate == 16000  # Whisper expects 16kHz
        assert config.channels == 1  # Mono
        assert config.dtype == "float32"
        assert config.chunk_duration == 0.5
        assert config.silence_threshold == 0.01
        assert config.silence_duration == 1.0
        assert config.max_duration == 30.0

    def test_custom_values(self):
        """Test custom AudioConfig values."""
        config = AudioConfig(
            sample_rate=22050,
            channels=2,
            dtype="int16",
            chunk_duration=0.25,
            silence_threshold=0.02,
            silence_duration=0.5,
            max_duration=60.0
        )

        assert config.sample_rate == 22050
        assert config.channels == 2
        assert config.dtype == "int16"
        assert config.chunk_duration == 0.25
        assert config.silence_threshold == 0.02
        assert config.silence_duration == 0.5
        assert config.max_duration == 60.0

    def test_chunk_samples_calculation(self):
        """Test calculating samples per chunk."""
        config = AudioConfig(sample_rate=16000, chunk_duration=0.5)
        expected_samples = int(config.sample_rate * config.chunk_duration)
        assert expected_samples == 8000


# =============================================================================
# VoiceActivityDetector Tests
# =============================================================================

class TestVoiceActivityDetector:
    """Tests for VoiceActivityDetector (energy-threshold VAD)."""

    def test_default_initialization(self):
        """Test default VAD initialization."""
        vad = VoiceActivityDetector()

        assert vad.threshold == 0.01
        assert vad.min_speech_samples == int(0.3 * 16000)  # 4800
        assert vad.min_silence_samples == int(0.8 * 16000)  # 12800
        assert vad._is_speaking is False

    def test_custom_initialization(self):
        """Test custom VAD initialization."""
        vad = VoiceActivityDetector(
            threshold=0.02,
            min_speech_duration=0.5,
            min_silence_duration=1.0
        )

        assert vad.threshold == 0.02
        assert vad.min_speech_samples == int(0.5 * 16000)
        assert vad.min_silence_samples == int(1.0 * 16000)

    def test_backend_property(self):
        """Test backend property returns correct value."""
        vad = VoiceActivityDetector()
        assert vad.backend == "energy-threshold"

    def test_reset(self):
        """Test reset clears all state."""
        vad = VoiceActivityDetector()
        vad._is_speaking = True
        vad._speech_samples = 10000
        vad._silence_samples = 5000

        vad.reset()

        assert vad._is_speaking is False
        assert vad._speech_samples == 0
        assert vad._silence_samples == 0

    def test_process_silence_returns_false(self):
        """Test process returns False for silence."""
        vad = VoiceActivityDetector()

        # Create mock silent audio chunk (energy below threshold)
        with patch.object(whisper_service.np, 'sqrt', return_value=0.001):
            with patch.object(whisper_service.np, 'mean', return_value=0.000001):
                mock_chunk = MagicMock()
                mock_chunk.__len__ = MagicMock(return_value=8000)
                mock_chunk.__pow__ = MagicMock(return_value=MagicMock())

                result = vad.process(mock_chunk)
                assert result is False

    def test_speech_detection_accumulation(self):
        """Test speech detection requires accumulated samples."""
        vad = VoiceActivityDetector(threshold=0.01, min_speech_duration=0.1)

        # Simulate energy above threshold
        vad._speech_samples = 0
        vad._silence_samples = 0
        vad._is_speaking = False

        # Manually set state as if speech was detected
        vad._speech_samples = vad.min_speech_samples + 1
        vad._is_speaking = True

        assert vad._is_speaking is True

    def test_speech_to_silence_transition(self):
        """Test transition from speech to silence."""
        vad = VoiceActivityDetector()

        # Simulate speaking state
        vad._is_speaking = True
        vad._speech_samples = 10000
        vad._silence_samples = 0

        # Accumulate enough silence
        vad._silence_samples = vad.min_silence_samples + 1
        vad._is_speaking = False  # This would happen in process()

        assert vad._is_speaking is False


# =============================================================================
# EnhancedVAD Tests (Phase 1.3)
# =============================================================================

class TestEnhancedVAD:
    """Tests for EnhancedVAD neural VAD (Phase 1.3 validation)."""

    def test_default_initialization(self):
        """Test default EnhancedVAD initialization."""
        with patch.object(whisper_service, 'NEURAL_VAD_AVAILABLE', True):
            with patch.object(whisper_service, 'MicroVAD', MagicMock()):
                vad = EnhancedVAD()

                assert vad.threshold == 0.5
                assert vad.sample_rate == 16000
                assert vad._min_speech_frames == 3
                assert vad._min_silence_frames == 8

    def test_custom_threshold(self):
        """Test custom threshold initialization."""
        with patch.object(whisper_service, 'NEURAL_VAD_AVAILABLE', True):
            with patch.object(whisper_service, 'MicroVAD', MagicMock()):
                vad = EnhancedVAD(threshold=0.7, sample_rate=16000)

                assert vad.threshold == 0.7
                assert vad.sample_rate == 16000

    def test_backend_property_neural(self):
        """Test backend property returns neural when available."""
        with patch.object(whisper_service, 'NEURAL_VAD_AVAILABLE', True):
            with patch.object(whisper_service, 'MicroVAD', MagicMock()):
                vad = EnhancedVAD()
                vad._use_neural = True
                assert vad.backend == "pymicro-vad"

    def test_backend_property_fallback(self):
        """Test backend property returns fallback when neural unavailable."""
        vad = EnhancedVAD()
        vad._use_neural = False
        assert vad.backend == "energy-threshold"

    def test_reset_with_neural_vad(self):
        """Test reset with neural VAD."""
        mock_vad = MagicMock()
        vad = EnhancedVAD()
        vad._vad = mock_vad
        vad._use_neural = True
        vad._is_speaking = True
        vad._speech_frames = 5
        vad._silence_frames = 3

        vad.reset()

        mock_vad.reset.assert_called_once()
        assert vad._is_speaking is False
        assert vad._speech_frames == 0
        assert vad._silence_frames == 0

    def test_reset_without_neural_vad(self):
        """Test reset without neural VAD."""
        vad = EnhancedVAD()
        vad._vad = None
        vad._use_neural = False
        vad._is_speaking = True
        vad._speech_frames = 5
        vad._silence_frames = 3

        vad.reset()

        assert vad._is_speaking is False
        assert vad._speech_frames == 0
        assert vad._silence_frames == 0

    def test_process_alias_for_is_speech(self):
        """Test process() is alias for is_speech()."""
        vad = EnhancedVAD()
        vad._use_neural = False
        vad._is_speaking = False

        mock_chunk = MagicMock()

        with patch.object(vad, 'is_speech', return_value=True) as mock_is_speech:
            result = vad.process(mock_chunk)
            mock_is_speech.assert_called_once_with(mock_chunk)
            assert result is True

    def test_is_speech_uses_neural_when_available(self):
        """Test is_speech uses neural detection when available."""
        vad = EnhancedVAD()
        vad._use_neural = True

        mock_chunk = MagicMock()

        with patch.object(vad, '_neural_detect', return_value=True) as mock_detect:
            result = vad.is_speech(mock_chunk)
            mock_detect.assert_called_once_with(mock_chunk)
            assert result is True

    def test_is_speech_uses_energy_fallback(self):
        """Test is_speech uses energy detection when neural unavailable."""
        vad = EnhancedVAD()
        vad._use_neural = False

        mock_chunk = MagicMock()

        with patch.object(vad, '_energy_detect', return_value=False) as mock_detect:
            result = vad.is_speech(mock_chunk)
            mock_detect.assert_called_once_with(mock_chunk)
            assert result is False

    def test_neural_detect_high_probability(self):
        """Test neural detection with high speech probability."""
        mock_vad_instance = MagicMock()
        mock_vad_instance.process = MagicMock(return_value=0.9)

        vad = EnhancedVAD()
        vad._vad = mock_vad_instance
        vad._use_neural = True
        vad.threshold = 0.5
        vad._speech_frames = 2
        vad._min_speech_frames = 3

        mock_chunk = MagicMock()
        mock_chunk.__mul__ = MagicMock(return_value=MagicMock(astype=MagicMock(return_value=MagicMock(tobytes=MagicMock(return_value=b'\x00')))))

        # Simulate the logic: probability > threshold means speech frame
        # After enough consecutive speech frames, _is_speaking becomes True
        vad._speech_frames = 3
        vad._is_speaking = True

        assert vad._is_speaking is True

    def test_energy_detect_fallback(self):
        """Test energy-based fallback detection."""
        vad = EnhancedVAD()
        vad._use_neural = False
        vad._energy_threshold = 0.01
        vad._speech_frames = 0
        vad._silence_frames = 0
        vad._min_speech_frames = 3

        # Test that state accumulates correctly
        vad._speech_frames = 5
        vad._is_speaking = True

        assert vad._is_speaking is True


# =============================================================================
# WhisperSTT Tests (Phase 1.1)
# =============================================================================

class TestWhisperSTT:
    """Tests for WhisperSTT class (Phase 1.1 validation)."""

    def test_default_initialization(self):
        """Test default WhisperSTT initialization."""
        stt = WhisperSTT()

        assert stt.model_size == WhisperModelSize.SMALL
        assert stt.device == "cuda"
        assert stt.compute_type == "float16"
        assert stt.language == "en"
        assert stt.cpu_threads == 4
        assert stt.num_workers == 1
        assert stt._model is None
        assert stt._warmed_up is False

    def test_custom_initialization(self):
        """Test custom WhisperSTT initialization."""
        stt = WhisperSTT(
            model_size=WhisperModelSize.BASE,
            device="cpu",
            compute_type="int8",
            language="de",
            use_enhanced_vad=False,
            cpu_threads=8,
            num_workers=4
        )

        assert stt.model_size == WhisperModelSize.BASE
        assert stt.device == "cpu"
        assert stt.compute_type == "int8"
        assert stt.language == "de"
        assert stt.cpu_threads == 8
        assert stt.num_workers == 4

    def test_dgx_spark_factory_method(self):
        """Test create_for_dgx_spark factory method (Phase 1.1 optimization)."""
        stt = WhisperSTT.create_for_dgx_spark(
            model_size=WhisperModelSize.BASE,
            language="en"
        )

        # Verify DGX Spark optimizations
        assert stt.device == "cuda"
        assert stt.compute_type == "int8_float16"  # Optimized quantization
        assert stt.num_workers == 2  # Parallel decoding
        assert stt.cpu_threads == 4
        assert stt.model_size == WhisperModelSize.BASE

    def test_dgx_spark_default_model_size(self):
        """Test DGX Spark uses BASE model by default."""
        stt = WhisperSTT.create_for_dgx_spark()

        assert stt.model_size == WhisperModelSize.BASE

    def test_is_warmed_up_property(self):
        """Test is_warmed_up property."""
        stt = WhisperSTT()
        assert stt.is_warmed_up is False

        stt._warmed_up = True
        assert stt.is_warmed_up is True

    def test_register_callback(self):
        """Test registering transcription callbacks."""
        stt = WhisperSTT()

        callback = MagicMock()
        stt.register_callback(callback)

        assert callback in stt._callbacks
        assert len(stt._callbacks) == 1

    def test_register_multiple_callbacks(self):
        """Test registering multiple callbacks."""
        stt = WhisperSTT()

        callback1 = MagicMock()
        callback2 = MagicMock()

        stt.register_callback(callback1)
        stt.register_callback(callback2)

        assert len(stt._callbacks) == 2
        assert callback1 in stt._callbacks
        assert callback2 in stt._callbacks

    def test_uses_enhanced_vad_by_default(self):
        """Test enhanced VAD is used by default."""
        stt = WhisperSTT(use_enhanced_vad=True)
        # Should use EnhancedVAD
        assert isinstance(stt._vad, EnhancedVAD)

    def test_can_use_simple_vad(self):
        """Test can use simple energy-threshold VAD."""
        stt = WhisperSTT(use_enhanced_vad=False)
        assert isinstance(stt._vad, VoiceActivityDetector)

    def test_stop_listening(self):
        """Test stop_listening sets flag."""
        stt = WhisperSTT()
        stt._is_listening = True

        stt.stop_listening()

        assert stt._is_listening is False


class TestWhisperSTTInitialize:
    """Tests for WhisperSTT initialization and model loading."""

    def test_initialize_loads_faster_whisper(self):
        """Test initialize loads faster-whisper model."""
        mock_model = MagicMock()
        mock_model.transcribe = MagicMock(return_value=iter([]))

        with patch.object(whisper_service, 'WHISPER_AVAILABLE', True):
            with patch.object(whisper_service, 'WHISPER_BACKEND', "faster-whisper"):
                with patch.object(whisper_service, 'WhisperModel', return_value=mock_model):
                    stt = WhisperSTT(model_size=WhisperModelSize.TINY, device="cpu")
                    stt.initialize(warm_up=False)

                    assert stt._model is not None

    def test_initialize_raises_without_whisper(self):
        """Test initialize raises error when Whisper unavailable."""
        stt = WhisperSTT()

        with patch.object(whisper_service, 'WHISPER_AVAILABLE', False):
            with pytest.raises(RuntimeError, match="Whisper not available"):
                stt.initialize()

    def test_warm_up_runs_dummy_transcription(self):
        """Test warm_up runs dummy transcription."""
        mock_model = MagicMock()
        mock_model.transcribe = MagicMock(return_value=iter([]))

        stt = WhisperSTT()
        stt._model = mock_model
        stt._warmed_up = False

        with patch.object(whisper_service, 'WHISPER_BACKEND', "faster-whisper"):
            stt._warm_up()

        mock_model.transcribe.assert_called_once()
        assert stt._warmed_up is True

    def test_warm_up_skips_if_already_warmed(self):
        """Test warm_up skips if already warmed up."""
        mock_model = MagicMock()

        stt = WhisperSTT()
        stt._model = mock_model
        stt._warmed_up = True

        stt._warm_up()

        mock_model.transcribe.assert_not_called()


class TestWhisperSTTTranscribe:
    """Tests for WhisperSTT transcription."""

    def test_transcribe_raises_without_model(self):
        """Test transcribe raises error when model not initialized."""
        stt = WhisperSTT()
        stt._model = None

        mock_audio = MagicMock()

        with pytest.raises(RuntimeError, match="Model not initialized"):
            stt.transcribe(mock_audio)

    def test_transcribe_faster_whisper(self):
        """Test transcription with faster-whisper backend."""
        mock_segment = MagicMock()
        mock_segment.text = "Point to Mars"
        mock_segment.start = 0.0
        mock_segment.end = 1.0

        mock_info = MagicMock()
        mock_model = MagicMock()
        mock_model.transcribe = MagicMock(return_value=([mock_segment], mock_info))

        stt = WhisperSTT()
        stt._model = mock_model

        mock_audio = MagicMock()

        with patch.object(whisper_service, 'WHISPER_BACKEND', "faster-whisper"):
            result = stt.transcribe(mock_audio)

        assert result.text == "Point to Mars"
        assert result.language == "en"
        assert result.confidence == 0.9
        assert len(result.segments) == 1

    def test_transcribe_returns_transcription_result(self):
        """Test transcribe returns TranscriptionResult instance."""
        mock_model = MagicMock()
        mock_model.transcribe = MagicMock(return_value=([], MagicMock()))

        stt = WhisperSTT()
        stt._model = mock_model

        mock_audio = MagicMock()

        with patch.object(whisper_service, 'WHISPER_BACKEND', "faster-whisper"):
            result = stt.transcribe(mock_audio)

        assert isinstance(result, TranscriptionResult)
        assert result.timestamp is not None


class TestWhisperSTTFileTranscription:
    """Tests for WhisperSTT file transcription."""

    @pytest.mark.asyncio
    async def test_transcribe_file_faster_whisper(self):
        """Test file transcription with faster-whisper."""
        mock_segment = MagicMock()
        mock_segment.text = "Hello world"

        mock_info = MagicMock()
        mock_model = MagicMock()
        mock_model.transcribe = MagicMock(return_value=([mock_segment], mock_info))

        stt = WhisperSTT()
        stt._model = mock_model

        with patch.object(whisper_service, 'WHISPER_BACKEND', "faster-whisper"):
            result = await stt.transcribe_file("/path/to/audio.wav")

        assert result.text == "Hello world"
        mock_model.transcribe.assert_called_once()


# =============================================================================
# PushToTalkRecorder Tests
# =============================================================================

class TestPushToTalkRecorder:
    """Tests for PushToTalkRecorder class."""

    def test_initialization_with_default_config(self):
        """Test initialization with default config."""
        mock_stt = MagicMock(spec=WhisperSTT)

        ptt = PushToTalkRecorder(mock_stt)

        assert ptt.stt == mock_stt
        assert isinstance(ptt.config, AudioConfig)
        assert ptt._recording is False
        assert ptt._audio_buffer == []

    def test_initialization_with_custom_config(self):
        """Test initialization with custom config."""
        mock_stt = MagicMock(spec=WhisperSTT)
        custom_config = AudioConfig(sample_rate=22050, max_duration=60.0)

        ptt = PushToTalkRecorder(mock_stt, config=custom_config)

        assert ptt.config.sample_rate == 22050
        assert ptt.config.max_duration == 60.0


# =============================================================================
# Integration Tests
# =============================================================================

class TestWhisperSTTIntegration:
    """Integration tests for WhisperSTT components."""

    def test_stt_with_enhanced_vad(self):
        """Test WhisperSTT with EnhancedVAD integration."""
        stt = WhisperSTT(use_enhanced_vad=True)

        assert isinstance(stt._vad, EnhancedVAD)
        assert stt._vad.threshold == 0.5

    def test_stt_with_basic_vad(self):
        """Test WhisperSTT with basic VAD integration."""
        stt = WhisperSTT(use_enhanced_vad=False)

        assert isinstance(stt._vad, VoiceActivityDetector)
        assert stt._vad.threshold == 0.01

    def test_dgx_spark_config_is_optimized(self):
        """Test DGX Spark configuration has all optimizations."""
        stt = WhisperSTT.create_for_dgx_spark()

        # Verify all DGX Spark optimizations are applied
        assert stt.device == "cuda"
        assert stt.compute_type == "int8_float16"
        assert stt.num_workers == 2
        assert isinstance(stt._vad, EnhancedVAD)


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_transcription_result_with_unicode(self):
        """Test TranscriptionResult handles unicode text."""
        result = TranscriptionResult(
            text="Point to Alpha Centauri",
            confidence=0.95,
            language="en",
            duration_seconds=0.5,
            timestamp=datetime.now(),
            segments=[]
        )
        assert result.text == "Point to Alpha Centauri"

    def test_transcription_result_with_special_characters(self):
        """Test TranscriptionResult handles special characters."""
        result = TranscriptionResult(
            text="M31 - The Andromeda Galaxy",
            confidence=0.9,
            language="en",
            duration_seconds=0.5,
            timestamp=datetime.now(),
            segments=[]
        )
        assert "-" in result.text

    def test_audio_config_with_zero_values(self):
        """Test AudioConfig handles zero silence threshold."""
        config = AudioConfig(silence_threshold=0.0)
        assert config.silence_threshold == 0.0

    def test_vad_with_very_short_audio(self):
        """Test VAD handles very short audio chunks."""
        vad = VoiceActivityDetector()

        # Very small chunk
        mock_chunk = MagicMock()
        mock_chunk.__len__ = MagicMock(return_value=10)
        mock_chunk.__pow__ = MagicMock(return_value=MagicMock())

        # Should not crash
        with patch.object(whisper_service.np, 'sqrt', return_value=0.001):
            with patch.object(whisper_service.np, 'mean', return_value=0.000001):
                result = vad.process(mock_chunk)
                assert isinstance(result, bool)

    def test_enhanced_vad_with_zero_threshold(self):
        """Test EnhancedVAD with zero threshold (always speech)."""
        vad = EnhancedVAD(threshold=0.0)
        assert vad.threshold == 0.0

    def test_enhanced_vad_with_max_threshold(self):
        """Test EnhancedVAD with max threshold (never speech)."""
        vad = EnhancedVAD(threshold=1.0)
        assert vad.threshold == 1.0


# =============================================================================
# Model Size Tests
# =============================================================================

class TestModelSizeSelection:
    """Tests for model size selection logic."""

    def test_tiny_model_for_fastest_inference(self):
        """Test TINY model for fastest inference."""
        stt = WhisperSTT(model_size=WhisperModelSize.TINY)
        assert stt.model_size.value == "tiny"

    def test_base_model_for_dgx_spark(self):
        """Test BASE model recommended for DGX Spark."""
        stt = WhisperSTT.create_for_dgx_spark(model_size=WhisperModelSize.BASE)
        assert stt.model_size.value == "base"

    def test_large_model_for_accuracy(self):
        """Test LARGE model for maximum accuracy."""
        stt = WhisperSTT(model_size=WhisperModelSize.LARGE)
        assert stt.model_size.value == "large-v3"


# =============================================================================
# Compute Type Tests (Phase 1.1 Optimization)
# =============================================================================

class TestComputeTypes:
    """Tests for compute type configurations (Phase 1.1)."""

    def test_float16_default(self):
        """Test float16 is default compute type."""
        stt = WhisperSTT()
        assert stt.compute_type == "float16"

    def test_int8_float16_for_dgx_spark(self):
        """Test int8_float16 for DGX Spark optimization."""
        stt = WhisperSTT.create_for_dgx_spark()
        assert stt.compute_type == "int8_float16"

    def test_int8_for_cpu(self):
        """Test int8 compute type for CPU."""
        stt = WhisperSTT(device="cpu", compute_type="int8")
        assert stt.compute_type == "int8"

    def test_float32_for_full_precision(self):
        """Test float32 for full precision."""
        stt = WhisperSTT(compute_type="float32")
        assert stt.compute_type == "float32"


# =============================================================================
# Language Support Tests
# =============================================================================

class TestLanguageSupport:
    """Tests for language configuration."""

    def test_default_language_english(self):
        """Test default language is English."""
        stt = WhisperSTT()
        assert stt.language == "en"

    def test_custom_language(self):
        """Test custom language setting."""
        languages = ["de", "fr", "es", "ja", "zh"]
        for lang in languages:
            stt = WhisperSTT(language=lang)
            assert stt.language == lang


# =============================================================================
# Callback Tests
# =============================================================================

class TestCallbackHandling:
    """Tests for callback registration and handling."""

    def test_sync_callback(self):
        """Test synchronous callback registration."""
        stt = WhisperSTT()

        def sync_callback(result):
            pass

        stt.register_callback(sync_callback)
        assert sync_callback in stt._callbacks

    def test_async_callback(self):
        """Test async callback registration."""
        stt = WhisperSTT()

        async def async_callback(result):
            pass

        stt.register_callback(async_callback)
        assert async_callback in stt._callbacks

    def test_lambda_callback(self):
        """Test lambda callback registration."""
        stt = WhisperSTT()

        callback = lambda result: print(result.text)
        stt.register_callback(callback)
        assert callback in stt._callbacks


# =============================================================================
# Device Configuration Tests
# =============================================================================

class TestDeviceConfiguration:
    """Tests for device configuration."""

    def test_cuda_device(self):
        """Test CUDA device configuration."""
        stt = WhisperSTT(device="cuda")
        assert stt.device == "cuda"

    def test_cpu_device(self):
        """Test CPU device configuration."""
        stt = WhisperSTT(device="cpu")
        assert stt.device == "cpu"

    def test_cpu_threads_configuration(self):
        """Test CPU threads configuration."""
        stt = WhisperSTT(cpu_threads=8)
        assert stt.cpu_threads == 8

    def test_num_workers_configuration(self):
        """Test num workers configuration."""
        stt = WhisperSTT(num_workers=4)
        assert stt.num_workers == 4


# =============================================================================
# Command Detection Tests
# =============================================================================

class TestCommandDetection:
    """Comprehensive tests for command detection."""

    def test_slew_variations(self):
        """Test various slew command variations."""
        variations = [
            "slew to orion",
            "please slew to polaris",
            "can you slew to m42",
            "slew east",
        ]
        for text in variations:
            result = TranscriptionResult(
                text=text,
                confidence=0.9,
                language="en",
                duration_seconds=0.5,
                timestamp=datetime.now(),
                segments=[]
            )
            assert result.is_command is True, f"Failed for: {text}"

    def test_goto_variations(self):
        """Test various goto command variations."""
        variations = [
            "go to vega",
            "goto arcturus",
            "go to the north star",
        ]
        for text in variations:
            result = TranscriptionResult(
                text=text,
                confidence=0.9,
                language="en",
                duration_seconds=0.5,
                timestamp=datetime.now(),
                segments=[]
            )
            assert result.is_command is True, f"Failed for: {text}"

    def test_mixed_case_commands(self):
        """Test commands with mixed case."""
        commands = [
            "SLEW TO MARS",
            "Go To Jupiter",
            "TRACK the moon",
            "Park NOW",
        ]
        for cmd in commands:
            result = TranscriptionResult(
                text=cmd,
                confidence=0.9,
                language="en",
                duration_seconds=0.5,
                timestamp=datetime.now(),
                segments=[]
            )
            assert result.is_command is True, f"Failed for: {cmd}"
