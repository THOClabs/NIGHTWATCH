#!/usr/bin/env python3
"""
NIGHTWATCH v0.5 AI Enhancement Demonstration

Launches the interactive Live Observatory Console by default —
a browser UI over scheduling, NLP, voice enhancement, and object ID.

    python examples/v05_ai_demo.py              # open web console
    python examples/v05_ai_demo.py --cli        # classic terminal walkthrough
    python examples/v05_ai_demo.py --host 0.0.0.0 --port 8765
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services import AIServices, AIServicesConfig


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def demo_scheduling(ai: AIServices) -> None:
    """Demonstrate intelligent scheduling capabilities."""
    print_section("Intelligent Scheduling (Steps 116-119)")

    candidates = [
        {
            "id": "M31",
            "name": "Andromeda Galaxy",
            "ra_hours": 0.712,
            "dec_degrees": 41.269,
            "magnitude": 3.4,
            "object_type": "galaxy",
        },
        {
            "id": "M42",
            "name": "Orion Nebula",
            "ra_hours": 5.588,
            "dec_degrees": -5.391,
            "magnitude": 4.0,
            "object_type": "nebula",
        },
        {
            "id": "M45",
            "name": "Pleiades",
            "ra_hours": 3.791,
            "dec_degrees": 24.117,
            "magnitude": 1.6,
            "object_type": "cluster",
        },
        {
            "id": "M13",
            "name": "Hercules Cluster",
            "ra_hours": 16.695,
            "dec_degrees": 36.467,
            "magnitude": 5.8,
            "object_type": "globular_cluster",
        },
    ]

    print("\n1. Creating tonight's schedule...")
    result = ai.schedule_tonight(candidates)

    print(f"   Scheduled {result['target_count']} targets")
    print(f"   Total observation time: {result['total_minutes']:.0f} minutes")
    print(f'\n   Narration: "{result["narration"]}"')

    print("\n2. Evaluating individual target (M31)...")
    info = ai.describe_target("M31", 0.712, 41.269, "galaxy")
    eval_data = info["evaluation"]
    print(f"   Quality: {eval_data.get('quality', 'N/A')}")
    print(f"   Score: {eval_data.get('total_score', 0):.2f}")
    print(f"   Recommendation: {info['recommendation']}")

    print("\n3. Condition scores for M31:")
    scores = info["condition_scores"]
    for score_name, score_value in scores.items():
        print(f"   - {score_name}: {score_value:.2f}")


def demo_nlp(ai: AIServices) -> None:
    """Demonstrate natural language capabilities."""
    print_section("Natural Language Processing (Steps 128-131, 137)")

    print("\n1. Multi-turn conversation context...")
    context = ai.context_manager
    context.add_user_message("Point the telescope at M31")
    context.add_assistant_message("Slewing to M31, the Andromeda Galaxy")
    context.add_user_message("Take a 60 second exposure")

    recent = context.get_context_messages(max_messages=3)
    print(f"   Tracking {len(recent)} messages in context")
    if recent:
        last_msg = recent[-1]
        content = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)
        print(f'   Last entry: "{content[:60]}..."')

    print("\n2. Clarification service...")
    clarification = ai.clarification
    result = clarification.check_command("Go to the nebula")
    print('   Input: "Go to the nebula"')
    print(f"   Needs clarification: {result.needs_clarification}")
    if result.needs_clarification:
        print(f"   Reason: {result.ambiguity_type.value if result.ambiguity_type else 'N/A'}")

    print("\n3. Proactive suggestions...")
    suggestions = ai.suggestions
    suggestion_list = suggestions.get_suggestions(max_suggestions=2)
    print(f"   Generated {len(suggestion_list)} suggestions")
    for s in suggestion_list[:2]:
        print(f"   - [{s.priority.value}] {s.text}")

    print("\n4. User preferences learning...")
    prefs = ai.user_preferences
    prefs.record_target_observation("M31", success=True, quality=0.9)
    prefs.record_target_observation("M31", success=True, quality=0.85)
    fav = prefs.get_favorite_targets(limit=3)
    print(f"   Recorded observations, tracking {len(fav)} favorites")

    print("\n5. Natural sky descriptions...")
    describer = ai.sky_describer
    from services.nlp import SkyCondition, SkyState, VisibleObject

    state = SkyState(
        condition=SkyCondition.GOOD,
        visible_objects=[
            VisibleObject(
                name="M31",
                object_type="galaxy",
                constellation="Andromeda",
                altitude_deg=55.0,
                azimuth_deg=45.0,
            )
        ],
    )
    desc = describer.describe_sky(state)
    print(f'   Sky description: "{desc.text}"')


def demo_voice(ai: AIServices) -> None:
    """Demonstrate voice enhancement capabilities."""
    print_section("Voice Enhancement (Steps 134-135)")

    print("\n1. Astronomy vocabulary trainer...")
    vocab = ai.vocabulary_trainer
    test_phrases = [
        "go to messier 31",
        "slew to ngc 7000",
        "point at the pleiades",
    ]
    print("   Normalizing astronomy terms:")
    for phrase in test_phrases:
        normalized = vocab.normalize_text(phrase)
        print(f'   - "{phrase}" -> "{normalized}"')

    vocab.record_usage("M31", success=True)
    vocab.record_usage("Andromeda", success=True)
    stats = vocab.get_statistics()
    print(
        f"\n   Vocabulary stats: "
        f"{stats.get('total_terms', stats.get('terms_count', 'N/A'))} terms tracked"
    )

    print("\n2. Wake word trainer...")
    wake = ai.wake_word_trainer
    print(f'   Wake word: "{wake.primary_phrase}"')
    print(f"   Training phase: {wake.get_status().phase.value}")

    wake.record_detection("nightwatch start session", detected=True, was_correct=True)
    wake.record_detection("hey nightwatch", detected=True, was_correct=True)
    status = wake.get_status()
    print(f"   Detection events: {status.total_detections}")
    print(f"   Accuracy: {status.accuracy:.0%}")


def demo_object_identification(ai: AIServices) -> None:
    """Demonstrate offline object identification."""
    print_section("Object Identification (Step 136)")

    identifier = ai.object_identifier

    print("\n1. Identifying object by coordinates...")
    print("   Position: RA=0.712h, Dec=41.27°")
    result = identifier.identify_at_coordinates(0.712, 41.269, search_radius_arcmin=60.0)
    if result.matches:
        best = result.matches[0]
        print(f"   Best match: {best.object_id} ({best.object_name})")
        print(f"   Confidence: {best.confidence_level.value}")
        print(f"   Method: {best.method.value}")
    else:
        print("   No matches found")

    print("\n2. Identifying object by catalog ID...")
    match = identifier.get_object_info("M42")
    if match:
        print(f"   Found: {match.object_id} ({match.object_name})")
        print(f"   Type: {match.object_type}, Constellation: {match.constellation}")
        print(f"   Magnitude: {match.magnitude}, Size: {match.size_arcmin} arcmin")
    else:
        print("   Not found")

    print("\n3. Asterism pattern matching...")
    test_stars = ["Vega", "Deneb", "Altair"]
    matches = identifier.match_pattern(test_stars)
    print(f"   Testing stars: {', '.join(test_stars)}")
    if matches:
        for m in matches[:2]:
            print(f"   - {m.pattern_name}: {m.description} ({m.confidence:.0%} match)")
    else:
        print("   No pattern matches found")


def demo_health_report(ai: AIServices) -> None:
    """Show service health summary."""
    print_section("Service Health Report")

    summary = ai.get_summary()
    print(f"\n   Initialized: {summary['initialized']}")
    print(f"   Services ready: {summary['services_ready']}")
    print(f"   Services error: {summary['services_error']}")
    print(f"   Overall status: {summary['overall_status']}")

    print("\n   Individual service status:")
    health = ai.get_health_report()
    for name, status in sorted(health.items()):
        symbol = "✓" if status.status.value == "ready" else "✗"
        print(f"   {symbol} {name}: {status.status.value}")


def run_cli_demo() -> None:
    """Run the classic terminal walkthrough."""
    print("\n" + "=" * 60)
    print("  NIGHTWATCH v0.5 AI Enhancement Demo (CLI)")
    print("=" * 60)
    print("\nThis demo showcases all v0.5 AI capabilities.")
    print("No hardware required - all services run in simulation mode.")

    config = AIServicesConfig(
        latitude_deg=38.9,
        longitude_deg=-117.6,
        lazy_init=True,
    )
    ai = AIServices(config)
    ai.initialize()

    demo_scheduling(ai)
    demo_nlp(ai)
    demo_voice(ai)
    demo_object_identification(ai)
    demo_health_report(ai)

    print_section("Demo Complete")
    print("\nv0.5 AI Enhancement milestone: 100% complete")
    print("Tip: run without --cli for the interactive web console.")
    print(f"Finished at {datetime.now().isoformat(timespec='seconds')}")


def run_web_demo(host: str, port: int) -> None:
    """Launch the interactive Live Observatory Console."""
    import importlib.util

    server_path = Path(__file__).parent / "demo_web" / "server.py"
    spec = importlib.util.spec_from_file_location("nightwatch_demo_server", server_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load demo server from {server_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Re-bind argv so the aiohttp server argparse sees host/port
    sys.argv = ["nightwatch-demo", "--host", host, "--port", str(port)]
    module.main()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NIGHTWATCH v0.5 AI demonstration",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run the classic terminal walkthrough instead of the web console",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Web demo bind host")
    parser.add_argument("--port", type=int, default=8765, help="Web demo port")
    args = parser.parse_args()

    if args.cli:
        run_cli_demo()
    else:
        run_web_demo(args.host, args.port)


if __name__ == "__main__":
    main()
