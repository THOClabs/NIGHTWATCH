<!-- BEGIN REPO-REVIEW (generated) -->
# Repository Review Summary (generated 2026-07-12)

Full review corpus: `docs/review/` (00-inventory through 60-executive-summary). Do not trust
the green CI badge or the README quickstart — see "Verified commands" below.

## What this is
NIGHTWATCH: voice-controlled autonomous observatory controller (Python 3.11, v0.1.0-dev).
Intended loop: voice -> Whisper STT -> LLM tool call -> validated dispatch -> mount/camera/roof,
with a continuous safety monitor that parks the mount and closes the roof on unsafe weather.
Key fact: components are well built and unit-tested but NOT wired into a running system.

## System map
- **Core orchestration & safety** (`nightwatch/`): `orchestrator.py` (3,446-line hub), `config.py`
  (pydantic + safety env allowlist), `watchdog.py` (SAFE-004). `safety_interlock.py`,
  `emergency_response.py`, `EventBus`, `CommandQueue` are DORMANT (zero production call sites).
- **Command execution** (`nightwatch/tool_executor.py` + `voice/tools/`): 18 live
  Pydantic-validated handlers; ~87 tool schemas defined, most with no live handler;
  `ToolRegistry` (~4,100 lines of `telescope_tools.py`) is dead code with NO validation.
- **LLM client** (`nightwatch/llm_client.py`, `tool_params.py`, `cancellation.py`): local llama +
  Anthropic/OpenAI fallback, VOX-003 tool-call validation — never constructed in production.
- **Voice & NLP** (`voice/`, `services/nlp/`): real Whisper/Piper/Wyoming engines, all unwired;
  `nightwatch/voice_pipeline.py` duplicates STT and returns mock silent TTS audio.
- **Astronomy & hardware** (`services/`, ~21 modules): mount, camera, roof, weather, power,
  ephemeris, catalog, guiding, etc. `services/safety_monitor/monitor.py` is the LIVE safety brain.

## Verified commands (state as of 2026-07-12, per docs/review/31-quality.md)
- Install: `pip install -r services/requirements.txt` FAILS on a clean machine —
  `pyindi-client~=2.0.8` never existed on PyPI. README/QUICKSTART cannot be completed as written.
- Run: `python -m nightwatch.main --dry-run` CRASHES — `setup_logging(level=...)` vs. parameter
  `log_level` (`main.py:308,325`). `python -m nightwatch.cli` (README) does not exist.
- Test: `pytest tests/unit/` — ~2618 tests; expect ~48 failures, most caused by unscoped
  `sys.modules['numpy'] = MagicMock()` in `tests/unit/test_piper_service.py:27` and
  `test_whisper_service.py:35` (collection-order pollution; they pass in isolation).
  `pytest.ini` is the live config; `pyproject.toml`'s `[tool.pytest.ini_options]` block is DEAD.
  `tests/hardware/` collects 0 pytest items (manual CLI scripts, not tests).
- Lint/type: `ruff check services/ voice/ nightwatch/ --ignore=E501,F401,F841` (2585 errors);
  `mypy nightwatch/ --ignore-missing-imports` (233 errors — it flags the main.py crash).
- CI (`.github/workflows/ci.yml`) CANNOT FAIL: every real check is muted via
  `continue-on-error: true` and/or `|| true`/`|| echo`. A green badge certifies nothing.
- Coverage: 48.25% measured vs. unenforced 60% (pyproject) and 80% (CI script) thresholds.

## Conventions and invariants to respect
- Commits: conventional `type(area): SPEC-### subject` referencing ARCH-/SAFE-/HWS-/VOX-/DEP-
  specs and `Risk #N`; pre-commit blocks direct commits to main.
- `SAFETY_ENV_OVERRIDE_ALLOWLIST` (`nightwatch/config.py:90`) is deny-by-default and EMPTY:
  `NIGHTWATCH_SAFETY_*` env overrides are rejected. Never widen it casually; it is well tested.
- `TOOL_PARAM_MODELS` (`nightwatch/tool_params.py`) is the single tool-schema source of truth,
  `extra="forbid"`, validated in both `llm_client.py` (VOX-003) and `tool_executor.py`
  (ARCH-001). A tool offered to the LLM without a registry entry is silently dropped.
- Cancellation is cooperative (`CancelToken`/`CommandContext`, ARCH-003) — never
  `Task.cancel()`. SAFE-001 requires safety callbacks (cancel) to run BEFORE the roof moves.
  Only one active context is supported; a second `set_active_context` displaces the first.
- Shutdown/safety code must use `registry.get_for_shutdown()` (not `get_running()`) so an
  ERRORed mount still gets parked (ARCH-002 bypass invariant).
- Every new mutating tool handler must add its own `orchestrator.safety.is_safe` check —
  there is no centralized safety middleware.
- NLP "dangerous action" clarification and the LLM `SAFETY STATUS:` prompt are advisory UX
  only; the authoritative veto is `services/safety_monitor`. Never treat them as enforcement.
- Do NOT add `except Exception`-and-continue on safety/hardware paths without a structured
  alert plus one test through the real (unmocked) call path — this idiom (437 sites) has
  already hidden three safety-critical defects.

## Danger zones (extra care required)
- `services/enclosure/roof_controller.py` — `self._gpio` never initialized in `__init__`;
  emergency close raises AttributeError, swallowed → roof never moves (Risk R1, security C1).
- `services/safety_monitor/monitor.py` — `_close_enclosure_safely()` calls async `close()`
  without `await` (M2); `handle_power_failure_response` references never-assigned
  `_action_callback` (M1). Live safety brain; `config.py:81` intends edits here restricted.
- `nightwatch/orchestrator.py` — 3,446 lines, highest churn, single author; contains dormant
  subsystems and a confirmed double `_save_session_log()` (lines 2059 + 2391).
- `nightwatch/main.py` — crashes on every invocation; `main()` has zero test coverage.
- `voice/tools/telescope_tools.py` — 5,662 lines, ~4,100 dead (`ToolRegistry` does raw
  `handler(**arguments)` with no validation; its emergency `close_roof` audit log is a stub).
  Do not revive without routing through `TOOL_PARAM_MODELS`.
- `nightwatch/constants.py` — safety thresholds duplicated from `SafetyConfig` and already
  drifted; always use `config.py`'s `SafetyConfig`, never `constants.py`.
- Protocol mismatch: orchestrator does `await mount.park()` but `LX200Client.park()` is
  synchronous — TypeError against real hardware; MagicMock tests hide all such contract breaks.
- Network defaults: Wyoming STT/TTS bind `0.0.0.0`, no auth, unbounded audio buffer
  (`config.py:346-420`); PDU defaults `admin`/`admin` + SNMP `private`
  (`services/power/power_manager.py:50-55`).
- Dormant-but-plausible code (`SafetyInterlock`, `EmergencyResponse`, `SafeStateHandler`,
  `EventBus`, `CommandQueue`, `ToolChain`, `LLMClient`, `VoicePipeline`, Wyoming servers,
  `services/nlp`): zero production call sites — never assume they enforce anything at runtime.

Review date: 2026-07-12. Regenerate this section when the review corpus is refreshed.
<!-- END REPO-REVIEW (generated) -->
