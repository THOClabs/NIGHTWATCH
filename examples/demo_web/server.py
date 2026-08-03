#!/usr/bin/env python3
"""
NIGHTWATCH Live Observatory Demo Server

Interactive web console wrapping v0.5 AI services.
No hardware required — runs entirely in simulation mode.

    python examples/demo_web/server.py
    # then open http://127.0.0.1:8765
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aiohttp import web

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services import AIServices, AIServicesConfig
from services.nlp import SkyCondition, SkyState, VisibleObject

STATIC_DIR = Path(__file__).resolve().parent / "static"

CANDIDATE_TARGETS = [
    {
        "id": "M31",
        "name": "Andromeda Galaxy",
        "ra_hours": 0.712,
        "dec_degrees": 41.269,
        "magnitude": 3.4,
        "object_type": "galaxy",
        "constellation": "Andromeda",
    },
    {
        "id": "M42",
        "name": "Orion Nebula",
        "ra_hours": 5.588,
        "dec_degrees": -5.391,
        "magnitude": 4.0,
        "object_type": "nebula",
        "constellation": "Orion",
    },
    {
        "id": "M45",
        "name": "Pleiades",
        "ra_hours": 3.791,
        "dec_degrees": 24.117,
        "magnitude": 1.6,
        "object_type": "cluster",
        "constellation": "Taurus",
    },
    {
        "id": "M13",
        "name": "Hercules Cluster",
        "ra_hours": 16.695,
        "dec_degrees": 36.467,
        "magnitude": 5.8,
        "object_type": "globular_cluster",
        "constellation": "Hercules",
    },
    {
        "id": "M51",
        "name": "Whirlpool Galaxy",
        "ra_hours": 13.498,
        "dec_degrees": 47.195,
        "magnitude": 8.4,
        "object_type": "galaxy",
        "constellation": "Canes Venatici",
    },
    {
        "id": "M57",
        "name": "Ring Nebula",
        "ra_hours": 18.893,
        "dec_degrees": 33.029,
        "magnitude": 8.8,
        "object_type": "nebula",
        "constellation": "Lyra",
    },
    {
        "id": "M81",
        "name": "Bode's Galaxy",
        "ra_hours": 9.926,
        "dec_degrees": 69.065,
        "magnitude": 6.9,
        "object_type": "galaxy",
        "constellation": "Ursa Major",
    },
    {
        "id": "M104",
        "name": "Sombrero Galaxy",
        "ra_hours": 12.667,
        "dec_degrees": -11.623,
        "magnitude": 8.0,
        "object_type": "galaxy",
        "constellation": "Virgo",
    },
]

logger = logging.getLogger("nightwatch.demo")


def _json_safe(value: Any) -> Any:
    """Recursively convert enums / dataclasses / paths into JSON-safe values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "to_dict"):
        return _json_safe(value.to_dict())
    if hasattr(value, "__dict__"):
        return {
            k: _json_safe(v)
            for k, v in vars(value).items()
            if not k.startswith("_")
        }
    return str(value)


class DemoState:
    """Holds the live AIServices instance for the demo session."""

    def __init__(self) -> None:
        self.ai: AIServices | None = None
        self.started_at = datetime.now(timezone.utc)
        self.command_log: list[dict[str, Any]] = []

    def ensure(self) -> AIServices:
        if self.ai is None:
            config = AIServicesConfig(
                latitude_deg=38.9,
                longitude_deg=-117.6,  # central Nevada dark-sky site
                lazy_init=True,
            )
            self.ai = AIServices(config)
            self.ai.initialize()
            logger.info("AI services initialized for demo")
        return self.ai


STATE = DemoState()


def _find_target(target_id: str) -> dict[str, Any] | None:
    tid = target_id.strip().upper()
    for t in CANDIDATE_TARGETS:
        if t["id"].upper() == tid or t["name"].upper() == tid:
            return t
    return None


async def api_bootstrap(_: web.Request) -> web.Response:
    ai = STATE.ensure()
    summary = ai.get_summary()
    health = {
        name: {
            "status": status.status.value,
            "message": status.message,
        }
        for name, status in ai.get_health_report().items()
    }
    return web.json_response(
        {
            "brand": "NIGHTWATCH",
            "version": "0.5",
            "mode": "simulator",
            "site": {
                "name": "Central Nevada Dark Sky",
                "latitude_deg": ai.config.latitude_deg,
                "longitude_deg": ai.config.longitude_deg,
            },
            "started_at": STATE.started_at.isoformat(),
            "summary": summary,
            "health": health,
            "targets": CANDIDATE_TARGETS,
            "wake_word": ai.wake_word_trainer.primary_phrase,
        }
    )


async def api_schedule(_: web.Request) -> web.Response:
    ai = STATE.ensure()
    result = ai.schedule_tonight(CANDIDATE_TARGETS)

    evaluations = []
    for target in CANDIDATE_TARGETS:
        info = ai.describe_target(
            target["id"],
            target["ra_hours"],
            target["dec_degrees"],
            target["object_type"],
        )
        evaluations.append(
            {
                "target": target,
                "evaluation": _json_safe(info["evaluation"]),
                "condition_scores": _json_safe(info["condition_scores"]),
                "recommendation": info.get("recommendation", ""),
            }
        )

    return web.json_response(
        {
            "narration": result["narration"],
            "target_count": result["target_count"],
            "total_minutes": result["total_minutes"],
            "schedule": _json_safe(result["schedule"]),
            "evaluations": evaluations,
        }
    )


async def api_command(request: web.Request) -> web.Response:
    ai = STATE.ensure()
    body = await request.json()
    text = str(body.get("text", "")).strip()
    if not text:
        raise web.HTTPBadRequest(text="Missing command text")

    normalized = ai.vocabulary_trainer.normalize_text(text)
    clarification = ai.clarification.check_command(text)
    ai.context_manager.add_user_message(text)

    # Lightweight intent simulation for the demo console
    intent = "unknown"
    response_text = f"Heard: {normalized}"
    actions: list[dict[str, Any]] = []
    lower = text.lower()

    if clarification.needs_clarification:
        intent = "clarify"
        response_text = clarification.question or "I need a bit more detail."
        actions = [
            {
                "id": getattr(opt, "id", str(i)),
                "label": getattr(opt, "label", str(opt)),
            }
            for i, opt in enumerate(clarification.options or [])
        ]
    elif any(k in lower for k in ("park", "home")):
        intent = "park"
        response_text = "Parking the mount and securing the observatory."
        ai.context_manager.add_assistant_message(response_text)
    elif any(k in lower for k in ("weather", "sky", "conditions")):
        intent = "sky"
        state = SkyState(
            condition=SkyCondition.GOOD,
            visible_objects=[
                VisibleObject(
                    name=t["id"],
                    object_type=t["object_type"],
                    constellation=t.get("constellation", ""),
                    altitude_deg=45.0 + (i * 4),
                    azimuth_deg=30.0 + (i * 20),
                )
                for i, t in enumerate(CANDIDATE_TARGETS[:4])
            ],
        )
        desc = ai.sky_describer.describe_sky(state)
        response_text = desc.text
        ai.context_manager.add_assistant_message(response_text)
    elif any(k in lower for k in ("schedule", "tonight", "plan")):
        intent = "schedule"
        result = ai.schedule_tonight(CANDIDATE_TARGETS)
        response_text = result["narration"]
        ai.context_manager.add_assistant_message(response_text)
    elif any(k in lower for k in ("slew", "goto", "go to", "point", "track")):
        intent = "slew"
        matched = None
        for t in CANDIDATE_TARGETS:
            if t["id"].lower() in lower or t["name"].lower() in lower:
                matched = t
                break
        # Also catch common aliases after vocab normalization
        if matched is None:
            for t in CANDIDATE_TARGETS:
                if t["id"].lower() in normalized.lower():
                    matched = t
                    break
        if matched:
            info = ai.describe_target(
                matched["id"],
                matched["ra_hours"],
                matched["dec_degrees"],
                matched["object_type"],
            )
            response_text = (
                f"Slewing to {matched['id']} — {matched['name']}. "
                f"{info.get('recommendation', '')}"
            )
            ai.user_preferences.record_target_observation(
                matched["id"], success=True, quality=0.88
            )
            ai.vocabulary_trainer.record_usage(matched["id"], success=True)
        else:
            response_text = (
                "I can slew to a catalog target — try Andromeda, Orion Nebula, "
                "or M13."
            )
        ai.context_manager.add_assistant_message(response_text)
    elif "meteor" in lower or "fireball" in lower:
        intent = "meteor"
        response_text = (
            "Meteor watch armed. I'll keep an eye on the all-sky feed and "
            "wake you if something bright cuts the Nevada sky."
        )
        ai.context_manager.add_assistant_message(response_text)
    else:
        intent = "chat"
        response_text = (
            f"Normalized command: “{normalized}”. "
            "Try: slew to Andromeda, what's the weather, schedule tonight, "
            "or park the telescope."
        )
        ai.context_manager.add_assistant_message(response_text)

    # Wake-word trainer gets a synthetic positive sample when phrase present
    if "nightwatch" in lower:
        ai.wake_word_trainer.record_detection(text, detected=True, was_correct=True)

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "input": text,
        "normalized": normalized,
        "intent": intent,
        "response": response_text,
        "needs_clarification": clarification.needs_clarification,
        "actions": actions,
    }
    STATE.command_log.append(entry)
    STATE.command_log = STATE.command_log[-40:]

    context_msgs = ai.context_manager.get_context_messages(max_messages=6)
    return web.json_response(
        {
            **entry,
            "context": _json_safe(context_msgs),
            "wake_status": _json_safe(ai.wake_word_trainer.get_status()),
            "vocab_stats": _json_safe(ai.vocabulary_trainer.get_statistics()),
        }
    )


async def api_identify(request: web.Request) -> web.Response:
    ai = STATE.ensure()
    body = await request.json()

    if "object_id" in body and body["object_id"]:
        match = ai.object_identifier.get_object_info(str(body["object_id"]))
        return web.json_response(
            {
                "mode": "catalog",
                "query": body["object_id"],
                "match": _json_safe(match),
            }
        )

    if "stars" in body:
        stars = [str(s) for s in body["stars"]]
        matches = ai.object_identifier.match_pattern(stars)
        return web.json_response(
            {
                "mode": "pattern",
                "query": stars,
                "matches": _json_safe(matches),
            }
        )

    ra = float(body.get("ra_hours", 0.712))
    dec = float(body.get("dec_degrees", 41.269))
    radius = float(body.get("radius_arcmin", 60.0))
    result = ai.object_identifier.identify_at_coordinates(
        ra, dec, search_radius_arcmin=radius
    )
    return web.json_response(
        {
            "mode": "coordinates",
            "query": {"ra_hours": ra, "dec_degrees": dec, "radius_arcmin": radius},
            "matches": _json_safe(result.matches),
        }
    )


async def api_sky(_: web.Request) -> web.Response:
    ai = STATE.ensure()
    state = SkyState(
        condition=SkyCondition.EXCELLENT,
        visible_objects=[
            VisibleObject(
                name=t["name"],
                object_type=t["object_type"],
                constellation=t.get("constellation", ""),
                altitude_deg=52.0 - (i * 5),
                azimuth_deg=40.0 + (i * 28),
            )
            for i, t in enumerate(CANDIDATE_TARGETS[:5])
        ],
    )
    desc = ai.sky_describer.describe_sky(state)
    text = desc.text

    suggestions = ai.suggestions.get_suggestions(max_suggestions=4)
    favorites = ai.user_preferences.get_favorite_targets(limit=5)

    return web.json_response(
        {
            "description": text,
            "condition": _json_safe(state.condition),
            "visible": _json_safe(state.visible_objects),
            "suggestions": _json_safe(suggestions),
            "favorites": _json_safe(favorites),
            "site": {
                "name": "Central Nevada Dark Sky",
                "latitude_deg": ai.config.latitude_deg,
                "longitude_deg": ai.config.longitude_deg,
            },
        }
    )


async def api_health(_: web.Request) -> web.Response:
    ai = STATE.ensure()
    return web.json_response(
        {
            "summary": ai.get_summary(),
            "health": {
                name: {
                    "status": status.status.value,
                    "message": status.message,
                }
                for name, status in sorted(ai.get_health_report().items())
            },
            "commands_processed": len(STATE.command_log),
            "uptime_seconds": (
                datetime.now(timezone.utc) - STATE.started_at
            ).total_seconds(),
        }
    )


async def api_target(request: web.Request) -> web.Response:
    ai = STATE.ensure()
    target_id = request.match_info["target_id"]
    target = _find_target(target_id)
    if target is None:
        # Try catalog identifier
        match = ai.object_identifier.get_object_info(target_id)
        if match is None:
            raise web.HTTPNotFound(text=f"Unknown target: {target_id}")
        info = ai.describe_target(
            match.object_id,
            getattr(match, "ra_hours", 0.0) or 0.0,
            getattr(match, "dec_degrees", 0.0) or 0.0,
            getattr(match, "object_type", None),
        )
        return web.json_response(
            {
                "target": _json_safe(match),
                "evaluation": _json_safe(info["evaluation"]),
                "condition_scores": _json_safe(info["condition_scores"]),
                "recommendation": info.get("recommendation", ""),
            }
        )

    info = ai.describe_target(
        target["id"],
        target["ra_hours"],
        target["dec_degrees"],
        target["object_type"],
    )
    return web.json_response(
        {
            "target": target,
            "evaluation": _json_safe(info["evaluation"]),
            "condition_scores": _json_safe(info["condition_scores"]),
            "recommendation": info.get("recommendation", ""),
        }
    )


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        response = web.Response()
    else:
        response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


async def index(_: web.Request) -> web.FileResponse:
    return web.FileResponse(STATIC_DIR / "index.html")


def create_app() -> web.Application:
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/api/bootstrap", api_bootstrap)
    app.router.add_get("/api/schedule", api_schedule)
    app.router.add_get("/api/sky", api_sky)
    app.router.add_get("/api/health", api_health)
    app.router.add_get("/api/target/{target_id}", api_target)
    app.router.add_post("/api/command", api_command)
    app.router.add_post("/api/identify", api_identify)
    app.router.add_get("/", index)
    app.router.add_static("/", STATIC_DIR, show_index=True)
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="NIGHTWATCH live demo server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Warm services before accepting traffic
    STATE.ensure()

    app = create_app()
    url = f"http://{args.host}:{args.port}/"
    print("\n" + "=" * 60)
    print("  NIGHTWATCH Live Observatory Demo")
    print("=" * 60)
    print(f"\n  Open →  {url}")
    print("  Mode →  simulator (no hardware required)\n")
    web.run_app(app, host=args.host, port=args.port, print=None)


if __name__ == "__main__":
    main()
