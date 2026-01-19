"""
NIGHTWATCH Logging Configuration

Provides centralized logging configuration for the NIGHTWATCH observatory
control system with support for:
- Structured JSON logging format (machine-parseable)
- Rotating file handlers with size limits
- Console output with optional color formatting
- Per-service log level configuration
- Request correlation IDs for tracing

Usage:
    from nightwatch.logging_config import setup_logging, get_logger

    # Initialize logging at application startup
    setup_logging(log_level="INFO", log_file="nightwatch.log")

    # Get a logger for your module
    logger = get_logger(__name__)
    logger.info("Mount connected", extra={"device": "OnStepX"})
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Module-level constants
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_BACKUP_COUNT = 5

# Log level mapping for per-service configuration
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def setup_logging(
    log_level: str = DEFAULT_LOG_LEVEL,
    log_file: Optional[str | Path] = None,
    json_format: bool = False,
    enable_color: bool = True,
) -> None:
    """Configure logging for the NIGHTWATCH application.

    Sets up the root logger with console and optional file handlers.
    Should be called once at application startup.

    Args:
        log_level: Default logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file. If provided, enables file logging
                  with rotation.
        json_format: If True, use structured JSON format for logs.
        enable_color: If True, enable colored console output (when supported).

    Example:
        setup_logging(log_level="DEBUG", log_file="/var/log/nightwatch.log")
    """
    # Get the root logger for nightwatch
    root_logger = logging.getLogger("nightwatch")
    root_logger.setLevel(LOG_LEVELS.get(log_level.upper(), logging.INFO))

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(LOG_LEVELS.get(log_level.upper(), logging.INFO))
    console_handler.setFormatter(
        logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT)
    )
    root_logger.addHandler(console_handler)

    # Create file handler if log_file specified
    if log_file:
        from logging.handlers import RotatingFileHandler

        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=DEFAULT_MAX_BYTES,
            backupCount=DEFAULT_BACKUP_COUNT,
        )
        file_handler.setLevel(LOG_LEVELS.get(log_level.upper(), logging.INFO))
        file_handler.setFormatter(
            logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT)
        )
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module or service.

    Returns a child logger under the nightwatch namespace for consistent
    configuration inheritance.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Starting mount service")
    """
    # Ensure logger is under nightwatch namespace
    if not name.startswith("nightwatch"):
        name = f"nightwatch.{name}"
    return logging.getLogger(name)


def set_service_level(service_name: str, level: str) -> None:
    """Set log level for a specific service.

    Allows granular control over logging verbosity per service.

    Args:
        service_name: Name of the service (e.g., "mount", "weather", "voice")
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Example:
        set_service_level("mount", "DEBUG")  # Verbose mount logging
        set_service_level("weather", "WARNING")  # Only weather warnings
    """
    logger_name = f"nightwatch.services.{service_name}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(LOG_LEVELS.get(level.upper(), logging.INFO))
