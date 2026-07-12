# Agent Memory: Domain Analyst — Voice & NLP (voice/, services/nlp/)

Durable notes for future reviews of NIGHTWATCH. Written 2026-07-12 after first full
domain review. Update this file (don't replace wholesale) as new reviews confirm,
refute, or extend these findings.

## Architecture facts (high confidence, file:line verified)

- **The voice/NLP subsystem is built but not wired into the running app.**
  `nightwatch/__init__.py:50-57` has the `from services.nlp import (...)` line
  literally commented out ("to avoid circular deps"). `nightwatch/voice_pipeline.py`
  reimplements its own `STTInterface`/`TTSInterface` (lines ~1458-1659) instead of
  reusing `voice/stt/whisper_service.py:WhisperSTT` or
  `voice/tts/piper_service.py:PiperTTS`, and its `TTSInterface.synthesize()` is a
  hardcoded mock (`_generate_mock_audio`, silent WAV) — Piper is never actually
  called from the main pipeline. `voice/wyoming/startup.py:start_wyoming_servers()`
  and `services/ai_services.py:AIServices` (the only code that assembles
  `ConversationContext`/`ClarificationService`/`SuggestionService`/etc.) are each
  only called from their own module, `examples/v05_ai_demo.py`, or `tests/` — never
  from `nightwatch/main.py` or `nightwatch/orchestrator.py`.
  **Before trusting any "data flow" narrative about voice control in this repo,
  grep for actual call sites — the docstrings/comments describe an architecture
  that isn't fully assembled yet.**

- **`services/ai_services.py`** (top-level file directly under `services/`, not in
  any subdirectory) is the de facto integration facade for `services/nlp/*` but was
  not explicitly assigned to any domain in the 00-inventory decomposition. Whoever
  reviews "Astronomy & Hardware Services" or does synthesis should know it exists
  and is currently a dead end (only used by `examples/v05_ai_demo.py` + tests).

- **Every file in `voice/stt`, `voice/tts`, `voice/wyoming`, and all six
  `services/nlp/*.py` files has exactly ONE commit**, all dated 2026-01-20 between
  05:29-06:29 UTC. Zero commits since (as of 2026-07-12, ~171 days). The L2
  git-historian's "abandoned zones" list (`docs/review/10-history.md` §4.1) did
  NOT include voice/ or services/nlp — but by the same "no commits in 165+ days"
  criterion it uses for alpaca/enclosure/encoder/ephemeris/indi/simulators, this
  entire domain qualifies too. Worth checking if future historian passes catch this.

- **Wyoming protocol servers (`voice/wyoming/stt_server.py`,
  `voice/wyoming/tts_server.py`) have zero authentication anywhere**, bind
  `0.0.0.0` by default (`nightwatch/config.py:346-349,411-414`), and are enabled by
  default (`wyoming_enabled: bool = True`). No TLS, no token, no allowlist in
  `voice/wyoming/protocol.py` at all. This is consistent with the general
  Wyoming/Home-Assistant LAN-trust ecosystem model but there's no code-level
  mitigation or documented caveat in this repo.

- **`WhisperSTT.transcribe()` hardcodes `confidence=0.9`** in all code paths
  (`voice/stt/whisper_service.py:454,465,592`), regardless of backend. This makes
  the Wyoming STT server's "Step 317" confidence-threshold filtering
  (`voice/wyoming/stt_server.py`, default threshold 0.6) permanently inert. Tests
  (`tests/unit/test_whisper_service.py:800`) assert `confidence == 0.9`, so this
  is an accepted stub, not an oversight anyone will "just fix" without prompting.

- **`services/nlp/clarification.py`'s "SAFETY_CONFIRMATION" ambiguity type is a
  conversational nicety, not a safety interlock.** It matches literal substrings
  ("emergency", "abort", "park", "close roof", etc.) in `DANGEROUS_ACTIONS` and
  asks a yes/no question. The real safety enforcement lives in
  `nightwatch/safety_interlock.py` (Core Orchestration & Safety domain). Any
  synthesis-level report should NOT conflate these two — they are unconnected.

- **Naming convention across `services/nlp/*.py`:** every submodule follows the
  same shape — dataclasses + Enum types, a `logging.getLogger("NIGHTWATCH.<Name>")`
  logger, a service class with public methods, and a `get_<name>()` factory backed
  by a module-level singleton (`_default_*: Optional[...] = None`). All six
  singletons are process-wide with no session/user key — a real risk if NIGHTWATCH
  ever needs concurrent sessions.

- **Two different code-style zones inside this domain:** `voice/stt/*.py` and
  `voice/tts/*.py` use bare `print()` for all diagnostics (no `logging` at all).
  `voice/wyoming/*.py` and `services/nlp/*.py` use `logging.getLogger(...)`
  consistently. If reviewing again, check whether this has been unified.

## Test coverage facts

- Strong, well-mocked unit tests exist for: `test_whisper_service.py` (1162 lines),
  `test_piper_service.py` (1017 lines), `test_wyoming_protocol.py` (867 lines —
  protocol/dataclass serialization ONLY), and all six `services/nlp` submodules
  (`test_clarification.py`, `test_conversation_context.py`,
  `test_session_narrator.py`, `test_sky_describer.py`, `test_suggestions.py`,
  `test_user_preferences.py`, ~500-700 lines each). This contradicts a naive
  "young repo = low test coverage" assumption for this specific domain — the NLP
  side is actually well tested for pure logic.
- **Zero test coverage found for the actual network server classes**
  (`WyomingSTTServer`, `WyomingTTSServer`, `WyomingManager`,
  `start_wyoming_servers`) — confirmed via repo-wide grep, no hits under `tests/`.
  This is exactly where the unbounded-buffer-growth and silent-exception-swallowing
  issues live. High-value gap to flag again if it persists in future reviews.

## Gotchas for future analysts of this repo

- Don't assume `voice/requirements.txt` dependencies are only used inside `voice/`
  — `webrtcvad` is declared there but actually imported by
  `nightwatch/voice_pipeline.py` (Core Orchestration domain), not by anything
  under `voice/`.
- `services/ai_services.py` sits at `services/` top level, outside any
  subdirectory-based domain in the 00-inventory decomposition — easy to miss when
  scoping a domain review strictly by directory list.
- When checking "is X wired up," grep for the actual constructor call
  (`ClassName(`) or function call site across the whole repo excluding `tests/`
  and `examples/` — docstrings and `__init__.py` comments in this repo are
  sometimes aspirational (see `nightwatch/__init__.py:50-57`).
- Git blame/log per-file is fast and decisive for "is this maintained" questions;
  `git log --all -- <path> | wc -l` plus `git log -1 --format=%ai --all -- <path>`
  gave crisp, citable evidence for the "built in one hour, day one" finding.
