"""
NIGHTWATCH Application Entry Point

Main entry point for the NIGHTWATCH autonomous observatory system.
Handles command-line arguments, configuration loading, signal handling,
and orchestrates the startup sequence.

Usage:
    nightwatch                          # Run with default config
    nightwatch --config /path/to/config.yaml
    nightwatch --log-level DEBUG
    nightwatch --dry-run                # Validate config without starting

Entry Points:
    - CLI: `nightwatch` command (via pyproject.toml)
    - Direct: `python -m nightwatch.main`
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from typing import TYPE_CHECKING

from nightwatch import __version__
from nightwatch.config import NightwatchConfig, load_config
from nightwatch.exceptions import ConfigurationError, NightwatchError
from nightwatch.health import HealthChecker
from nightwatch.logging_config import get_logger, setup_logging
from nightwatch.orchestrator import Orchestrator

if TYPE_CHECKING:
    from types import FrameType

__all__ = ["main", "async_main", "create_parser"]

# Module logger
logger = get_logger(__name__)


# =============================================================================
# Argument Parser (Step 44)
# =============================================================================


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="nightwatch",
        description="NIGHTWATCH Autonomous Observatory System",
        epilog="For more information, visit: https://github.com/THOClabs/NIGHTWATCH",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Version
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    # Configuration
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        metavar="PATH",
        help="Path to configuration file (default: auto-discover)",
    )

    # Logging
    parser.add_argument(
        "-l",
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help="Set logging level (overrides config file)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        metavar="PATH",
        help="Path to log file (default: stderr only)",
    )

    # Operation modes
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and exit without starting services",
    )
    parser.add_argument(
        "--check-health",
        action="store_true",
        help="Run health checks on configured services and exit",
    )

    # Service control
    parser.add_argument(
        "--no-voice",
        action="store_true",
        help="Disable voice pipeline (run in headless mode)",
    )
    parser.add_argument(
        "--simulator",
        action="store_true",
        help="Use simulator backends for all hardware",
    )

    return parser


# =============================================================================
# Signal Handlers (Step 45)
# =============================================================================


class GracefulShutdown:
    """Manages graceful shutdown on signals.

    Handles SIGINT (Ctrl+C) and SIGTERM for clean shutdown of observatory
    services including parking the mount and closing the enclosure.
    """

    def __init__(self) -> None:
        self._shutdown_requested = False
        self._shutdown_event: asyncio.Event | None = None
        self._original_handlers: dict[int, signal.Handlers] = {}

    @property
    def shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self._shutdown_requested

    def install_handlers(self) -> None:
        """Install signal handlers for graceful shutdown."""
        # Store original handlers
        self._original_handlers[signal.SIGINT] = signal.signal(
            signal.SIGINT, self._handle_signal
        )
        self._original_handlers[signal.SIGTERM] = signal.signal(
            signal.SIGTERM, self._handle_signal
        )
        logger.debug("Signal handlers installed for graceful shutdown")

    def restore_handlers(self) -> None:
        """Restore original signal handlers."""
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)
        self._original_handlers.clear()
        logger.debug("Original signal handlers restored")

    def _handle_signal(self, signum: int, frame: FrameType | None) -> None:
        """Handle shutdown signal.

        Args:
            signum: Signal number received
            frame: Current stack frame (unused)
        """
        signal_name = signal.Signals(signum).name
        if self._shutdown_requested:
            logger.warning(
                f"Received {signal_name} again - forcing immediate exit"
            )
            sys.exit(1)

        logger.info(f"Received {signal_name} - initiating graceful shutdown...")
        self._shutdown_requested = True

        # Set event if we're in async context
        if self._shutdown_event is not None:
            self._shutdown_event.set()

    def get_shutdown_event(self) -> asyncio.Event:
        """Get or create async shutdown event.

        Returns:
            Event that is set when shutdown is requested
        """
        if self._shutdown_event is None:
            self._shutdown_event = asyncio.Event()
        return self._shutdown_event


# Global shutdown handler
_shutdown_handler = GracefulShutdown()


def get_shutdown_handler() -> GracefulShutdown:
    """Get the global shutdown handler instance."""
    return _shutdown_handler


# =============================================================================
# Startup Banner
# =============================================================================


def print_banner(config: NightwatchConfig) -> None:
    """Print startup banner with configuration summary.

    Args:
        config: Loaded configuration
    """
    banner = f"""
╔══════════════════════════════════════════════════════════════════════╗
║                         NIGHTWATCH v{__version__:<24}           ║
║              Autonomous Observatory Control System                   ║
╠══════════════════════════════════════════════════════════════════════╣
║  Site: {config.site.name:<60} ║
║  Location: {config.site.latitude:+.4f}°, {config.site.longitude:+.4f}° @ {config.site.elevation:.0f}m{' ' * 26}║
║  Mount: {config.mount.type} @ {config.mount.host}:{config.mount.port:<30} ║
║  Voice: {'Enabled' if config.voice.enabled else 'Disabled':<60} ║
╚══════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


# =============================================================================
# Main Entry Points
# =============================================================================


async def async_main(args: argparse.Namespace, config: NightwatchConfig) -> int:
    """Async main function for running the observatory.

    Args:
        args: Parsed command-line arguments
        config: Validated configuration

    Returns:
        Exit code (0 for success)
    """
    shutdown = get_shutdown_handler()
    shutdown_event = shutdown.get_shutdown_event()

    logger.info("Starting NIGHTWATCH observatory system...")

    # Initialize orchestrator
    orchestrator = Orchestrator(config)

    try:
        # Health check mode - run checks and exit
        if args.check_health:
            logger.info("Running health checks...")
            health_checker = HealthChecker(config)
            results = await health_checker.check_all()

            # Display results
            print("\nHealth Check Results:")
            print("=" * 50)
            for name, status in results:
                symbol = "✓" if status.healthy else "✗"
                print(f"  {symbol} {name}: {status.status.value}")
                if status.message:
                    print(f"      {status.message}")
                if status.latency_ms > 0:
                    print(f"      Latency: {status.latency_ms:.1f}ms")
            print("=" * 50)
            print(f"Summary: {results.summary}")

            return 0 if results.all_required_healthy else 1

        # Start orchestrator and all services
        if not await orchestrator.start():
            logger.error("Failed to start orchestrator")
            return 1

        # Main event loop - wait for shutdown signal
        logger.info("Observatory system running. Press Ctrl+C to stop.")
        await shutdown_event.wait()

        logger.info("Shutdown signal received, stopping services...")
        # Graceful shutdown: parks mount, closes enclosure, saves session log
        await orchestrator.shutdown(safe=True)

        return 0

    except Exception as e:
        logger.exception(f"Fatal error in main loop: {e}")
        # Attempt emergency shutdown
        try:
            await orchestrator.shutdown(safe=False)
        except Exception:
            pass
        return 1


def main() -> int:
    """Main entry point for the NIGHTWATCH application.

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    # Parse arguments
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging (basic setup before config is loaded)
    log_level = args.log_level or "INFO"
    setup_logging(level=log_level)

    logger.info(f"NIGHTWATCH v{__version__} starting...")

    # Load configuration
    try:
        logger.debug(
            f"Loading configuration from: {args.config or 'auto-discover'}"
        )
        config = load_config(args.config)
        logger.info("Configuration loaded successfully")
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    # Apply log level from config if not overridden
    if args.log_level is None:
        setup_logging(level=config.log_level)

    # Apply simulator mode
    if args.simulator:
        config.mount.type = "simulator"
        config.weather.type = "simulator"
        config.camera.type = "simulator"
        logger.info("Simulator mode enabled for all hardware")

    # Disable voice if requested
    if args.no_voice:
        config.voice.enabled = False
        config.tts.enabled = False
        logger.info("Voice pipeline disabled")

    # Print banner
    print_banner(config)

    # Dry run mode - just validate and exit
    if args.dry_run:
        logger.info("Dry run mode - configuration valid, exiting")
        print("\n✓ Configuration is valid")
        return 0

    # Install signal handlers
    shutdown = get_shutdown_handler()
    shutdown.install_handlers()

    try:
        # Run async main
        return asyncio.run(async_main(args, config))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130  # Standard exit code for SIGINT
    except NightwatchError as e:
        logger.error(f"NIGHTWATCH error: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1
    finally:
        shutdown.restore_handlers()
        logger.info("NIGHTWATCH shutdown complete")


if __name__ == "__main__":
    sys.exit(main())
