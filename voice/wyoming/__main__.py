"""
NIGHTWATCH Wyoming Servers - Module Entry Point

Launches the Wyoming protocol STT and TTS servers as a long-running process,
suitable for use as a systemd service (see deploy/systemd/nightwatch-wyoming.service).

Usage:
    python -m voice.wyoming [--stt-port PORT] [--tts-port PORT]
                            [--whisper-model NAME] [--piper-voice NAME]
                            [--device {auto,cuda,cpu}]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

logger = logging.getLogger("voice.wyoming")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m voice.wyoming",
        description="Run the NIGHTWATCH Wyoming STT/TTS protocol servers.",
    )
    parser.add_argument(
        "--stt-port",
        type=int,
        default=10300,
        help="Bind port for the Wyoming STT server (default: 10300).",
    )
    parser.add_argument(
        "--tts-port",
        type=int,
        default=10301,
        help="Bind port for the Wyoming TTS server (default: 10301).",
    )
    parser.add_argument(
        "--whisper-model",
        default="large-v3",
        help="Whisper model name for STT (default: large-v3).",
    )
    parser.add_argument(
        "--piper-voice",
        default="en_US-lessac-medium",
        help="Piper voice model name for TTS (default: en_US-lessac-medium).",
    )
    parser.add_argument(
        "--device",
        choices=("auto", "cuda", "cpu"),
        default="auto",
        help="Compute device for inference (default: auto).",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind address for both servers (default: 0.0.0.0).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (default: INFO).",
    )
    return parser


async def _serve(args: argparse.Namespace) -> int:
    # Imported lazily so that --help does not require the heavy runtime deps.
    from nightwatch.config import TTSConfig, VoiceConfig
    from voice.wyoming.startup import start_wyoming_servers

    voice_config = VoiceConfig(
        enabled=True,
        model=args.whisper_model,
        device=args.device,
        wyoming_enabled=True,
        wyoming_host=args.host,
        wyoming_port=args.stt_port,
    )
    tts_config = TTSConfig(
        enabled=True,
        model=args.piper_voice,
        use_cuda=(args.device == "cuda"),
        wyoming_enabled=True,
        wyoming_host=args.host,
        wyoming_port=args.tts_port,
    )

    manager = await start_wyoming_servers(voice_config, tts_config)
    status = manager.get_status()
    logger.info(
        "Wyoming servers running (STT %s:%s, TTS %s:%s)",
        status.stt_host or args.host,
        status.stt_port or args.stt_port,
        status.tts_host or args.host,
        status.tts_port or args.tts_port,
    )

    try:
        # Block forever, keeping the background servers alive.
        await asyncio.Event().wait()
    finally:
        await manager.stop_all()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        return asyncio.run(_serve(args))
    except KeyboardInterrupt:
        logger.info("Interrupted, shutting down Wyoming servers")
        return 130


if __name__ == "__main__":
    sys.exit(main())
