# NIGHTWATCH Frontend v0.1 — Claude Design Prompt Pack

This directory contains the complete prompt pack for generating the NIGHTWATCH demo frontend with **Claude Design** (claude.ai/design) running **Claude Fable 5** at **High** effort.

| File | What it is |
|---|---|
| `CLAUDE_DESIGN_PROMPT.md` | The master generation-1 prompt. Paste the **entire file** into Claude Design in one shot. Builds the design system, global shell, simulation engine, digital twin, voice console, and ten flagship screens, with honest placeholders for the rest. |
| `ITERATION_PROMPTS.md` | Six staged follow-up prompts that flesh out the remaining modules (Facility, Operations, System, Sky/Imaging depth, Voice/Meteor depth, polish pass) one generation at a time. |
| `README.md` | This file — usage, iteration discipline, and provenance. |

## How to run it

1. Open **claude.ai/design**, start a **new project**, set the model to **Claude Fable 5** and effort to **High**.
2. Paste the full contents of `CLAUDE_DESIGN_PROMPT.md` as the first message. Do not summarize or trim it — the length is spec density, and Fable 5 rewards a complete spec in a single turn.
3. If Claude Design asks clarifying questions before generating, answer them deliberately (desktop-first, dark-only + Rubylith, animation yes, single self-contained app). Thoughtful answers measurably improve the output.
4. Expect a long single generation (minutes) at High effort — that is normal.
5. Review against the prompt's `<success_criteria>` checklist and play the demo script chapter by chapter from the Demo Director bar.

## Iteration discipline (matters as much as the prompt)

- **Chat** is for structural changes only — new sections, new screens, behavior changes. One or two changes per message, never "regenerate everything but tweak X".
- **Inline comments** on the canvas are for targeted component-level fixes ("this gauge needle should be brass, not white").
- **Direct canvas edits / adjustment sliders** are for visual nudges (spacing, sizes, alignment).
- Follow-up modules: run the prompts in `ITERATION_PROMPTS.md` **in order, one per generation, in the same project** so the design system and simulation carry over.
- **Budget note:** Claude Design usage is metered on a weekly allowance and big generations are expensive. The master prompt is engineered to make generation 1 count; avoid speculative full regenerations — iterate with comments and canvas edits instead.
- When the design is ready to become code, use Claude Design's **Claude Code handoff** (exports the HTML/CSS/JS bundle, per-state screenshots, and design notes) and target a `frontend/` app in this repo wrapping the real orchestrator (FastAPI + WebSocket bridge over the `EventBus` is the intended v0.2 architecture; see `ROADMAP.md`).

## Provenance — where every fact in the prompt comes from

The prompt is transcribed from the repository, not invented. If the backend changes, update the prompt from these sources:

| Prompt section | Source of truth |
|---|---|
| Mission, site, hardware identity | `README.md`, `NIGHTWATCH_Build_Package.md`, `docs/INTES_MICRO_HISTORY.md` |
| Mount states, pier side, tracking rates | `services/simulators/mount_simulator.py`, `services/mount_control/lx200.py` |
| Drive physics (steps/°, slew, meridian limits) | `firmware/onstepx_config/Config.h` |
| Event vocabulary (`EventType`) | `nightwatch/orchestrator.py` (line ~375) |
| Safety levels, actions, thresholds, hysteresis, cancel-before-close | `services/safety_monitor/monitor.py`, `nightwatch.yaml.example` (`safety:` section) |
| Roof states, interlocks, motor limits, rain holdoff | `services/enclosure/roof_controller.py` |
| Weather fields, dual rain redundancy | `services/weather/unified.py`, `services/weather/secondary_rain.py` |
| Frame grades and rejection reasons | `services/camera/frame_analyzer.py` |
| Guiding stats | `services/guiding/phd2_client.py` |
| Focus V-curve contract | `services/focus/focuser_service.py` |
| Power states, battery staging, PDU outlets | `services/power/power_manager.py`, `services/safety_monitor/monitor.py` |
| Voice pipeline states and per-turn result | `nightwatch/voice_pipeline.py` (`PipelineState`, `PipelineResult`) |
| Tool names and confirmation flow | `voice/tools/telescope_tools.py`, `docs/VOICE_COMMANDS.md` |
| Suggestions, narration styles, session phases | `services/nlp/suggestions.py`, `services/nlp/session_narrator.py` |
| Scheduling quality/reasons | `services/scheduling/scheduler.py` |
| Alert schema and acknowledge flow | `services/alerts/alert_manager.py` |
| Meteor showers, Lexicon vocabulary, Hopi circles | `services/meteor_tracking/shower_calendar.py`, `lexicon_prayers.py`, `hopi_circles.py` |
| Config sections for Settings screens | `nightwatch.yaml.example` |

## Why the prompt is shaped this way

The structure follows Anthropic's published guidance for prompting Claude Fable 5 and Claude Design: a complete specification in a single turn; XML section tags for a prompt that mixes context, data, and instructions; longform reference data early and instructions/success criteria at the end; exact hex/typography tokens (explicit values are honored, adjectives are not); real content everywhere instead of placeholders; an explicit golden-path demo script; delegated creative freedom where we have no opinion; and a scope built around one deeply-specified flagship set plus stubs, because one-shotting every screen degrades coherence. The staged iteration prompts carry the remaining ~20 screens without risking the foundation.
