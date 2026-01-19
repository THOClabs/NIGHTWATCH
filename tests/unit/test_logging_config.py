"""
NIGHTWATCH Unit Tests - Logging Configuration

Unit tests for nightwatch/logging_config.py.
Tests setup_logging, get_logger, set_service_level, and helper functions.

Run:
    pytest tests/unit/test_logging_config.py -v
"""

import logging
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


# =============================================================================
# Test setup_logging Function
# =============================================================================

class TestSetupLogging:
    """Unit tests for setup_logging function."""

    def test_setup_logging_default(self):
        """Test setup_logging with default parameters."""
        from nightwatch.logging_config import setup_logging, get_logger

        setup_logging()

        logger = get_logger("test_default")
        assert logger is not None
        assert logger.name == "nightwatch.test_default"

    def test_setup_logging_custom_level(self):
        """Test setup_logging with custom log level."""
        from nightwatch.logging_config import setup_logging

        setup_logging(log_level="DEBUG")

        root_logger = logging.getLogger("nightwatch")
        assert root_logger.level == logging.DEBUG

    def test_setup_logging_warning_level(self):
        """Test setup_logging with WARNING level."""
        from nightwatch.logging_config import setup_logging

        setup_logging(log_level="WARNING")

        root_logger = logging.getLogger("nightwatch")
        assert root_logger.level == logging.WARNING

    def test_setup_logging_with_file(self):
        """Test setup_logging creates file handler when log_file specified."""
        from nightwatch.logging_config import setup_logging

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            setup_logging(log_file=log_path)

            # Get the nightwatch logger and verify handlers
            root_logger = logging.getLogger("nightwatch")

            # Should have at least 2 handlers (console + file)
            assert len(root_logger.handlers) >= 2

            # Find the file handler
            file_handlers = [
                h for h in root_logger.handlers
                if hasattr(h, 'baseFilename')
            ]
            assert len(file_handlers) == 1
            assert Path(file_handlers[0].baseFilename) == log_path

            # Close file handler before temp dir cleanup (Windows fix)
            for h in file_handlers:
                h.close()
                root_logger.removeHandler(h)

    def test_setup_logging_creates_parent_directory(self):
        """Test that setup_logging creates parent directories for log file."""
        from nightwatch.logging_config import setup_logging

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "subdir" / "nested" / "test.log"
            setup_logging(log_file=log_path)

            assert log_path.parent.exists()

            # Close file handler before temp dir cleanup (Windows fix)
            root_logger = logging.getLogger("nightwatch")
            for h in list(root_logger.handlers):
                if hasattr(h, 'baseFilename'):
                    h.close()
                    root_logger.removeHandler(h)

    def test_setup_logging_clears_existing_handlers(self):
        """Test that setup_logging clears existing handlers on re-initialization."""
        from nightwatch.logging_config import setup_logging

        # Setup twice
        setup_logging(log_level="INFO")
        setup_logging(log_level="DEBUG")

        root_logger = logging.getLogger("nightwatch")
        # Should not accumulate handlers
        assert len(root_logger.handlers) == 1  # Only console handler


# =============================================================================
# Test get_logger Function
# =============================================================================

class TestGetLogger:
    """Unit tests for get_logger function."""

    def test_get_logger_returns_logger(self):
        """Test get_logger returns a Logger instance."""
        from nightwatch.logging_config import get_logger

        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_adds_nightwatch_prefix(self):
        """Test get_logger adds nightwatch prefix to logger name."""
        from nightwatch.logging_config import get_logger

        logger = get_logger("services.mount")
        assert logger.name == "nightwatch.services.mount"

    def test_get_logger_preserves_existing_prefix(self):
        """Test get_logger preserves existing nightwatch prefix."""
        from nightwatch.logging_config import get_logger

        logger = get_logger("nightwatch.services.mount")
        assert logger.name == "nightwatch.services.mount"

    def test_get_logger_dunder_name(self):
        """Test get_logger with typical __name__ style input."""
        from nightwatch.logging_config import get_logger

        logger = get_logger("services.weather.ecowitt")
        assert logger.name == "nightwatch.services.weather.ecowitt"


# =============================================================================
# Test set_service_level Function
# =============================================================================

class TestSetServiceLevel:
    """Unit tests for set_service_level function."""

    def test_set_service_level_debug(self):
        """Test setting service level to DEBUG."""
        from nightwatch.logging_config import setup_logging, set_service_level

        setup_logging()
        set_service_level("mount", "DEBUG")

        service_logger = logging.getLogger("nightwatch.services.mount")
        assert service_logger.level == logging.DEBUG

    def test_set_service_level_warning(self):
        """Test setting service level to WARNING."""
        from nightwatch.logging_config import setup_logging, set_service_level

        setup_logging()
        set_service_level("weather", "WARNING")

        service_logger = logging.getLogger("nightwatch.services.weather")
        assert service_logger.level == logging.WARNING

    def test_set_service_level_case_insensitive(self):
        """Test that level names are case-insensitive."""
        from nightwatch.logging_config import setup_logging, set_service_level

        setup_logging()
        set_service_level("camera", "debug")

        service_logger = logging.getLogger("nightwatch.services.camera")
        assert service_logger.level == logging.DEBUG

    def test_set_service_level_invalid_defaults_to_info(self):
        """Test that invalid level defaults to INFO."""
        from nightwatch.logging_config import setup_logging, set_service_level

        setup_logging()
        set_service_level("guiding", "INVALID_LEVEL")

        service_logger = logging.getLogger("nightwatch.services.guiding")
        assert service_logger.level == logging.INFO


# =============================================================================
# Test log_exception Helper
# =============================================================================

class TestLogException:
    """Unit tests for log_exception helper function."""

    def test_log_exception_logs_at_error_level(self):
        """Test log_exception logs at ERROR level by default."""
        from nightwatch.logging_config import setup_logging, get_logger, log_exception

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_exception")

        with patch.object(logger, 'log') as mock_log:
            exc = ValueError("test error message")
            log_exception(logger, "Operation failed", exc)

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == logging.ERROR  # First arg is level

    def test_log_exception_includes_exception_type(self):
        """Test log_exception includes exception type in message."""
        from nightwatch.logging_config import setup_logging, get_logger, log_exception

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_exception_type")

        with patch.object(logger, 'log') as mock_log:
            exc = RuntimeError("runtime error")
            log_exception(logger, "Something broke", exc)

            call_args = mock_log.call_args
            message = call_args[0][1]
            assert "RuntimeError" in message
            assert "runtime error" in message

    def test_log_exception_custom_level(self):
        """Test log_exception with custom log level."""
        from nightwatch.logging_config import setup_logging, get_logger, log_exception

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_custom_level")

        with patch.object(logger, 'log') as mock_log:
            exc = ValueError("test")
            log_exception(logger, "Test", exc, level=logging.WARNING)

            call_args = mock_log.call_args
            assert call_args[0][0] == logging.WARNING

    def test_log_exception_without_traceback(self):
        """Test log_exception without traceback when include_traceback=False."""
        from nightwatch.logging_config import setup_logging, get_logger, log_exception

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_no_traceback")

        with patch.object(logger, 'log') as mock_log:
            exc = ValueError("no trace")
            log_exception(logger, "Error", exc, include_traceback=False)

            call_args = mock_log.call_args
            extra = call_args[1].get('extra', {})
            # traceback key should not be in extra
            assert 'traceback' not in extra

    def test_log_exception_with_traceback(self):
        """Test log_exception includes traceback by default."""
        from nightwatch.logging_config import setup_logging, get_logger, log_exception

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_with_traceback")

        with patch.object(logger, 'log') as mock_log:
            try:
                raise ValueError("with trace")
            except ValueError as exc:
                log_exception(logger, "Error", exc, include_traceback=True)

            call_args = mock_log.call_args
            extra = call_args[1].get('extra', {})
            assert 'traceback' in extra
            assert 'ValueError' in extra['traceback']


# =============================================================================
# Test log_timing Context Manager
# =============================================================================

class TestLogTiming:
    """Unit tests for log_timing context manager."""

    def test_log_timing_logs_start_and_end(self):
        """Test log_timing logs operation start and completion."""
        from nightwatch.logging_config import setup_logging, get_logger, log_timing

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_timing")

        with patch.object(logger, 'log') as mock_log:
            with log_timing(logger, "test_operation"):
                pass

            # Should be called at least twice (start + end)
            assert mock_log.call_count >= 2

    def test_log_timing_measures_duration(self):
        """Test log_timing accurately measures operation duration."""
        from nightwatch.logging_config import setup_logging, get_logger, log_timing

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_duration")

        with patch.object(logger, 'log') as mock_log:
            with log_timing(logger, "sleep_operation"):
                time.sleep(0.1)  # Sleep for 100ms

            # Check the completion message includes timing
            calls = mock_log.call_args_list
            completion_call = calls[-1]
            message = completion_call[0][1]
            # Should contain "completed in X.XXXs" format
            assert "completed in" in message

    def test_log_timing_warns_on_threshold_exceeded(self):
        """Test log_timing emits warning when threshold exceeded."""
        from nightwatch.logging_config import setup_logging, get_logger, log_timing

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_threshold")

        with patch.object(logger, 'warning') as mock_warning:
            with log_timing(logger, "slow_operation", warn_threshold_sec=0.01):
                time.sleep(0.05)  # Sleep longer than threshold

            mock_warning.assert_called_once()
            call_args = mock_warning.call_args
            message = call_args[0][0]
            assert "exceeded" in message
            assert "threshold" in message

    def test_log_timing_no_warning_under_threshold(self):
        """Test log_timing does not warn when under threshold."""
        from nightwatch.logging_config import setup_logging, get_logger, log_timing

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_under_threshold")

        with patch.object(logger, 'warning') as mock_warning:
            with log_timing(logger, "fast_operation", warn_threshold_sec=10.0):
                pass  # Instant operation

            mock_warning.assert_not_called()

    def test_log_timing_includes_extra_data(self):
        """Test log_timing includes operation name in extra data."""
        from nightwatch.logging_config import setup_logging, get_logger, log_timing

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_extra")

        with patch.object(logger, 'log') as mock_log:
            with log_timing(logger, "my_operation"):
                pass

            # Check completion log has extra data
            calls = mock_log.call_args_list
            completion_call = calls[-1]
            extra = completion_call[1].get('extra', {})
            assert 'operation' in extra
            assert extra['operation'] == "my_operation"
            assert 'elapsed_seconds' in extra

    def test_log_timing_works_with_exception(self):
        """Test log_timing still logs completion even if exception raised."""
        from nightwatch.logging_config import setup_logging, get_logger, log_timing

        setup_logging(log_level="DEBUG")
        logger = get_logger("test_exception_timing")

        with patch.object(logger, 'log') as mock_log:
            with pytest.raises(RuntimeError):
                with log_timing(logger, "failing_operation"):
                    raise RuntimeError("Intentional error")

            # Should still have logged start and completion
            assert mock_log.call_count >= 2


# =============================================================================
# Test Log Level Constants
# =============================================================================

class TestLogLevels:
    """Unit tests for log level constants."""

    def test_log_levels_mapping_contains_standard_levels(self):
        """Test LOG_LEVELS contains all standard Python log levels."""
        from nightwatch.logging_config import LOG_LEVELS

        assert "DEBUG" in LOG_LEVELS
        assert "INFO" in LOG_LEVELS
        assert "WARNING" in LOG_LEVELS
        assert "ERROR" in LOG_LEVELS
        assert "CRITICAL" in LOG_LEVELS

    def test_log_levels_map_to_correct_values(self):
        """Test LOG_LEVELS maps to correct logging module values."""
        from nightwatch.logging_config import LOG_LEVELS

        assert LOG_LEVELS["DEBUG"] == logging.DEBUG
        assert LOG_LEVELS["INFO"] == logging.INFO
        assert LOG_LEVELS["WARNING"] == logging.WARNING
        assert LOG_LEVELS["ERROR"] == logging.ERROR
        assert LOG_LEVELS["CRITICAL"] == logging.CRITICAL


# =============================================================================
# Test Default Constants
# =============================================================================

class TestDefaultConstants:
    """Unit tests for default logging constants."""

    def test_default_max_bytes(self):
        """Test DEFAULT_MAX_BYTES is 10MB."""
        from nightwatch.logging_config import DEFAULT_MAX_BYTES

        assert DEFAULT_MAX_BYTES == 10 * 1024 * 1024  # 10 MB

    def test_default_backup_count(self):
        """Test DEFAULT_BACKUP_COUNT is 5."""
        from nightwatch.logging_config import DEFAULT_BACKUP_COUNT

        assert DEFAULT_BACKUP_COUNT == 5

    def test_default_log_level(self):
        """Test DEFAULT_LOG_LEVEL is INFO."""
        from nightwatch.logging_config import DEFAULT_LOG_LEVEL

        assert DEFAULT_LOG_LEVEL == "INFO"
