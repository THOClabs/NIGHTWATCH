# Agent Memory: Chief Architect (L5/L6) — NIGHTWATCH

Distilled system model after the first full review cycle (2026-07-12, branch
claude/install-review-org-37y4ck, 61 commits, repo age 5.5 months). Update — don't replace —
on future passes. Deliverables written: docs/review/40-architecture.md, 50-risk-register.md.

## System model (one paragraph)

Voice-controlled autonomous observatory. Hub-and-spoke around `nightwatch/orchestrator.py`
(3,446-line god-file). Three layers: `nightwatch/` core, `services/` (22 capability modules),
`voice/` (STT/TTS/Wyoming + 87-tool LLM schema catalog). Dependency direction is clean
(services never import nightwatch). The defining property as of 2026-07: **breadth-first
scaffolding, near-zero integration** — components are individually well unit-tested but the
running system does not exist. Single author (Tim Hennessey = THOClabs, 97% of commits).

## Verified load-bearing facts (re-check these first on any future review)

- **Entry point crashes:** `main.py:308,325` `setup_logging(level=)` vs param `log_level`.
  One-line fix; if fixed, most "dormant" findings go live (adopt security report's Tier A/B rule).
- **Emergency roof close broken twice:** (1) `RoofController.__init__` (roof_controller.py:484-531)
  never sets `self._gpio` (only unreferenced `setup_rain_sensor_interrupt()` does, :1061);
  `_run_motor:848` AttributeErrors, swallowed. (2) `monitor.py:1535` calls async `close()` without
  await from sync `_close_enclosure_safely`. Both masked by tests that patch `_run_motor`.
- **Unwired in production (zero construction sites in main.py/orchestrator.py, all verified):**
  LLMClient, VoicePipeline, Wyoming servers, AIServices/services-nlp, SafetyInterlock,
  EmergencyResponse, SafeStateHandler, EventBus, CommandQueue, ToolChain, ToolRegistry
  (~4,100 dead lines in telescope_tools.py, repo's largest file), execute_cancellable/_active_commands.
- **Live safety boundary is exactly:** services/safety_monitor loop → orchestrator
  `_on_safety_change`/`_on_safety_veto` cancel of the single `_active_context` (set only by
  tool_executor.py:351,406) + inline park/close in `_safe_shutdown`/`end_session`/
  `emergency_shutdown` + SAFE-004 watchdog heartbeat path (safety_monitor only; other services'
  watchdog heartbeats never called → UNKNOWN forever).
- **Tool surface:** TOOL_PARAM_MODELS has exactly 18 keys (mount/catalog/ephemeris/weather/
  safety/session). 87 schemas defined in voice/tools. voice_pipeline.py:2086 imports nonexistent
  `nightwatch.telescope_tools` → tools=None → LLM never gets schemas → VOX-003 inert on real traffic.
  LLMClient.requires_confirmation's 4 critical tool names aren't in the registry (double-dead).
- **Protocol mismatches (M3):** LX200Client park/stop/unpark are sync; orchestrator awaits them.
  SafetyMonitor lacks `is_safe` property; emergency_response/watchdog expect roof.get_state()
  (real API: `state` property). MagicMock tests hide all of it.
- **CI cannot fail:** 12× continue-on-error + `|| true`/`|| echo` on every real check in ci.yml.
  Test suite polluted by module-level `sys.modules['numpy']=MagicMock()` in test_piper_service.py:27
  and test_whisper_service.py:35 (order-dependent failures). Coverage 48.25% vs unenforced 60/80.
  pytest.ini wins; pyproject.toml pytest block dead. Real bugs found by suite: power_restore 300s
  hang; double `_save_session_log` (orchestrator.py:2059+2391).
- **Config truths:** LLMConfig (config.py:436-479) has NO api_key/endpoint/backend fields —
  00-inventory.md:291 was wrong. Keys read from env in llm_client.py:454,572. SafetyConfig is the
  threshold source of truth; constants.py has drifted flat copies (unreferenced). SAFETY env
  allowlist (config.py:90) is real, empty, well-tested — the repo's best control.
- **Ecowitt parser fails open** (defaults 70°F/dry on garbled JSON); SAFE-002 secondary rain
  sensor unimplemented but `require_secondary_rain_sensor=True` default with no config surface.
- **Network defaults:** Wyoming 0.0.0.0:10300/10301, enabled=True, no auth, unbounded audio buffer;
  PDU admin/admin + SNMP "private". docker prod exposes 10300; systemd wyoming unit ExecStart's
  `voice.wyoming_server` module does not exist. README's `nightwatch.cli` does not exist.
  `pyindi-client~=2.0.8` has never existed on PyPI (install fails atomically).
- **aiohttp 3.13.5 in uv.lock: 11 CVEs, fix 3.14.1** (as of 2026-07).

## Git/history facts

- Two identities, one person; Claude has 2 docs commits. Main branch stale vs review branch.
- Stale-since-2026-01-20 (verified): alpaca, enclosure, encoder, ephemeris, indi, simulators,
  voice/stt, voice/tts, voice/wyoming, services/nlp (historian's §4.1 missed the voice/nlp set;
  voice/ recent activity is only voice/tools/telescope_tools.py). alerts/meteor stale since 01-28.
- No tags/releases. 1 merge commit. Commit discipline high (ARCH-/SAFE-/HWS-/VOX- refs) but specs
  are marked "Complete" at code-exists, not wired (ToolChain Step 267; SAFE-001 claim vs C1).

## Judgment calls I made (keep consistent next time)

- Adopted security auditor's rule: "unwired" is NOT a mitigation for anything the deploy artifacts
  intend to run (entry fix is one line).
- Ranked R1 (roof) and R2 (CI/no-feedback-loop) co-equal at 20; R2 is the enabling risk.
- Treated the review corpus itself as partial bus-factor mitigation.
- 437 broad-except sites framed as the root-cause pattern (with power_manager.py:309 bare except
  returning success) rather than as individual findings.
- meteor_tracking hopi_circles/lexicon_prayers: editorial/cultural-review item only, no code defect.

## Where reports were wrong (recorded in 40-architecture.md §6)

- 00-inventory: LLMConfig fields (wrong); SAFE-002/004 attributed to safety_interlock.py (wrong —
  they live in monitor.py:553 / watchdog.py:505); tests/hardware "skipped in CI" (wrong — collect
  0 items, they're manual scripts).
- 10-history: abandoned-zones list under-counted (missed voice/* subdirs + services/nlp).
- No domain analyst's concrete code claim was found wrong; 31-quality confirmed all flags.

## Next-review checklist

1. Is main.py fixed and does `--dry-run` run? If yes, re-tier all Tier-B findings.
2. `grep -n "_gpio" services/enclosure/roof_controller.py` — still uninitialized in __init__?
3. Does monitor.py `_close_enclosure_safely` await? Is `_action_callback` assigned?
4. ci.yml: count continue-on-error; is unit-tests job gated? Is mypy nightwatch/ gated?
5. Does voice_pipeline._get_tools resolve? TOOL_PARAM_MODELS key count vs live handlers?
6. Any wire-or-delete triage done on ToolRegistry/EventBus/CommandQueue/EmergencyResponse?
7. Tags created? Second contributor? PRs to main?
8. aiohttp bumped? pyindi-client pin fixed? pip-audit gating?
