# Domain Report: Core Orchestration & Safety

**Domain:** `nightwatch/` core package (excluding `tool_executor.py`, `response_formatter.py`,
`llm_client.py`, `tool_params.py`, `cancellation.py`, which belong to other analysts' domains)
**Analyst:** L3 Domain Analyst
**Date:** 2026-07-12

Files reviewed in depth: `__init__.py`, `constants.py`, `types.py`, `exceptions.py`, `config.py`,
`logging_config.py`, `safety_interlock.py`, `emergency_response.py`, `watchdog.py`, `health.py`,
`main.py`, `orchestrator.py` (3,446 lines — the largest file, read in full via targeted sections).
`voice_pipeline.py` (2,517 lines) lives in this directory but is thematically STT/TTS/audio
plumbing for the Voice & NLP domain; it is covered only briefly here as a boundary note.
`cancellation.py` is owned by another analyst but is read here just enough to describe the
`CommandContext`/`CancelToken` contract that `orchestrator.py` consumes.

All findings below were verified by reading source and, where noted, by executing code directly
(`python3 -m nightwatch.main --dry-run`, targeted `grep` across the whole repo to confirm
call-site counts). No claim below is speculative extrapolation from a single read.

---

## 1. Responsibility

This domain is the system's central nervous system and safety brain: it loads and validates
configuration, starts/stops all hardware/software services in a defined order, tracks the
current observing session, and is supposed to guarantee that whenever conditions turn unsafe
(weather, a hung safety monitor, an operator Ctrl-C, an unhandled exception) the telescope mount
gets parked and the roof gets closed before anything else happens. A new engineer should think of
it as "the thing every other service reports to, and the last line of defense that closes the
roof no matter what else is going wrong."

## 2. Key modules

| File | Role |
|---|---|
| `nightwatch/main.py` | CLI entry point (`main()`, `async_main()`, `create_parser()`), signal handling (`GracefulShutdown`). |
| `nightwatch/orchestrator.py` | `Orchestrator` class — service registry, session state, event bus, command timeouts/cancellation, shutdown sequences. 3,446 lines, by far the largest and highest-churn file in the domain (10 commits per `10-history.md:46`). |
| `nightwatch/config.py` | Pydantic-based `NightwatchConfig` and sub-configs (`SafetyConfig`, `MountConfig`, etc.); `load_config()`; `SAFETY_ENV_OVERRIDE_ALLOWLIST` (config.py:90) — deny-by-default guard against disabling safety thresholds via env var. |
| `nightwatch/safety_interlock.py` | `SafetyInterlock` — pre-command gatekeeper (`check_command`) meant to veto unsafe commands before dispatch. **Not wired into production** (see §6). |
| `nightwatch/emergency_response.py` | `EmergencyResponse` — retrying emergency park/close sequences with alert escalation. **Not wired into production** (see §6). |
| `nightwatch/watchdog.py` | `WatchdogManager` — per-service heartbeat/timeout tracking with SAFE-004 hardware fail-safe (`_execute_safety_veto`, watchdog.py:505). `SafeStateHandler` (watchdog.py:733) is a second park/close implementation, also **not wired into production**. |
| `nightwatch/health.py` | `HealthChecker`, service-specific checks (mount/weather/voice/guider/power), `StartupSequence` for ordered startup. Contains a confirmed dependency-check bug (§6). |
| `nightwatch/logging_config.py` | `setup_logging()`, correlation-ID context vars, `log_exception`/`log_timing` helpers. |
| `nightwatch/exceptions.py` | `NightwatchError` hierarchy. Only `NightwatchError` and `ConfigurationError` are actually used elsewhere; the rest is unreferenced (§6). |
| `nightwatch/constants.py` | Centralized magic numbers, including a full parallel copy of safety thresholds that duplicates (and has drifted from) `SafetyConfig` — unused elsewhere (§6). |
| `nightwatch/types.py` | Shared type aliases/TypedDicts/Protocols; imported by nothing outside `__init__.py`'s convenience re-export (§6). |

## 3. Data flow — startup and safety-shutdown, traced end to end

**Startup:** `bin/nightwatch` → `python -m nightwatch.main` → `main()` (main.py:296) parses args,
calls `load_config()` (config.py:963, YAML via `yaml.safe_load` + `NIGHTWATCH_*` env overrides),
then `asyncio.run(async_main(...))` → `Orchestrator(config)` is constructed (orchestrator.py:1564)
→ `orchestrator.start()` (orchestrator.py:1912) iterates `ServiceRegistry` entries in registration
order, calling `service.start()` for each and marking `ServiceStatus.RUNNING`/`ERROR`; a required
service failing to start aborts startup. A background `_health_loop` task (orchestrator.py:2096)
is then spawned (30s poll of `service.is_running` + restart-policy dispatch), and
`async_main` blocks on `shutdown_event.wait()` until SIGINT/SIGTERM.

**Safety-critical path (the one that matters most):** the actual continuous environmental
monitoring lives in `services/safety_monitor/monitor.py` (cross-domain). When it detects an
unsafe condition it (a) drives the enclosure closed itself and (b) invokes the callback
registered via `register_safety()` (orchestrator.py:1703-1729), which is `_on_safety_change`
(orchestrator.py:1823). That callback cancels `self._active_context` — a single
`CommandContext` from `nightwatch/cancellation.py` set by the tool-dispatch layer
(`tool_executor.py:351,406`, confirmed by grep) around whichever long-running tool call
(slew/capture/focus) is currently in flight. Separately, `WatchdogManager` (owned by
`Orchestrator.watchdog`, orchestrator.py:1602) tracks heartbeats from `safety_monitor` itself; if
`safety_monitor` goes silent for >90s, `_execute_safety_veto` (watchdog.py:505) closes the
enclosure directly (bypassing the orchestrator) and fires `_on_safety_veto`
(orchestrator.py:1865), which also cancels `_active_context` and emits `EventType.SAFETY_VETO`.

**Shutdown (signal/exception path):** `main.py`'s `GracefulShutdown._handle_signal` sets an
`asyncio.Event`; `async_main` wakes up and calls `orchestrator.shutdown(safe=True)`
(orchestrator.py:1965) → `_safe_shutdown()` (orchestrator.py:2015) → parks mount / closes
enclosure via `registry.get_for_shutdown()` (a deliberate bypass of the RUNNING-only gate,
documented at orchestrator.py:1282-1311, so park/close still fire on an ERRORed mount) → saves a
JSON session log → stops all services in reverse registration order. On an unhandled exception in
`async_main`, `orchestrator.shutdown(safe=False)` is attempted as a last resort (main.py:289-292).

## 4. External dependencies

- **pydantic ≥2.0** — all configuration validation (`config.py`). **PyYAML** — `yaml.safe_load`
  only (config.py:991), no unsafe YAML loading.
- **Cross-domain, this domain calls into:** `services/safety_monitor` (safety callback contract,
  duck-typed `SafetyStatus` with `.is_safe`/`.action`/`.reasons`, documented at
  orchestrator.py:1833-1837), `services/enclosure.RoofController` (`close()`/`open()`/`stop()`,
  all `async def`), mount services (`park()`/`stop()`/`get_status()` — **contract is
  inconsistent across implementations**, see §6), `services/mount_control/lx200.py`
  (`LX200Client`, confirmed synchronous `stop()`/`park()`, lx200.py:530,580) vs.
  `services/simulators/mount_simulator.py` (confirmed `async def stop()/park()`,
  mount_simulator.py:131,143).
- **Cross-domain, calls in:** `nightwatch/tool_executor.py` (owned by another analyst) is the
  only real caller of `Orchestrator.set_active_context`/`clear_active_context`
  (tool_executor.py:351,406) — i.e. the actual command-dispatch entry point into this domain's
  cancellation machinery.
- **`nightwatch/cancellation.py`** (another analyst's domain) supplies `CommandContext`/
  `CancelToken` — a deliberately *cooperative* cancellation primitive, explicitly designed to
  replace hard `asyncio.Task.cancel()` (cancellation.py:11-22) because mid-write cancellation of
  FITS files / mount serial transactions can corrupt state. `Orchestrator` also has an
  **independent, older, hard-cancel command-tracking system** (`execute_cancellable`,
  `cancel_command`, `_active_commands: Dict[str, asyncio.Task]`) that predates ARCH-003 and is
  not the live path — see §6.

## 5. Invariants and conventions

- **Safety env-override allowlist is deny-by-default** (config.py:90,
  `SAFETY_ENV_OVERRIDE_ALLOWLIST: Final[frozenset[str]] = frozenset()`): any `NIGHTWATCH_SAFETY_*`
  env var not in the (currently empty) allowlist is rejected with a `logger.critical` and the
  YAML/default value is kept. Well tested (`tests/unit/test_config.py:395-505`).
- **`get_running` vs. `get_for_shutdown`** (orchestrator.py:1254 vs. 1282): the documented,
  deliberate rule is that the command-dispatch path only ever sees `RUNNING` services (ARCH-002),
  while the three safety-shutdown call sites (`_safe_shutdown`, `end_session`,
  `emergency_shutdown`) bypass that gate so park/close is attempted even on an `ERROR`ed service.
  This is a real, well-documented, well-reasoned invariant — but it is only as good as callers
  remembering to use the right accessor; a new safety-shutdown path that reaches for
  `self.mount`/`self.registry.get_running(...)` instead of `get_for_shutdown(...)` would silently
  skip parking an errored mount.
- **Cooperative cancellation, not task cancellation** (cancellation.py:1-38): long-running ops
  are expected to poll `CommandContext`/`CancelToken` at safe iteration boundaries rather than be
  killed via `Task.cancel()`. SAFE-001 depends on ordering: the safety monitor's
  `_notify_callbacks` (which reaches `_on_safety_change`) must run **before**
  `execute_action`/EMERGENCY_CLOSE (cancellation.py:29-38) so the cancel signal reaches in-flight
  ops before the enclosure physically starts moving.
- **Single active context** (orchestrator.py:1772-1811): `set_active_context` is explicitly
  documented as *not* supporting concurrent commands — a second call silently displaces the first
  (logged at ERROR, not raised) and the displaced (older, possibly still-running) operation is no
  longer reachable by a subsequent safety cancel. This is a known, TODO-tagged gap, not a bug I'm
  reporting as new, but it is a real invariant callers must respect.
- **Config loading precedence**: CLI `--config` > `./nightwatch.yaml` > `~/.nightwatch/config.yaml`
  > `/etc/nightwatch/config.yaml` > built-in pydantic defaults (config.py:963-996), env overrides
  applied last except for the safety allowlist gate.

## 6. MATRIX FLAGS

### Security observations

1. **CLI entry point cannot start (confirmed by execution).** `nightwatch/main.py:308` and `:325`
   call `setup_logging(level=log_level)` / `setup_logging(level=config.log_level)`, but
   `setup_logging()`'s only parameter is named `log_level` (`nightwatch/logging_config.py:185`).
   I verified this empirically:
   ```
   $ python3 -m nightwatch.main --dry-run
   TypeError: setup_logging() got an unexpected keyword argument 'level'
   ```
   Every invocation of the documented entry point (`nightwatch` CLI, `bin/nightwatch`,
   `python -m nightwatch.main`) crashes before configuration is even validated. This is a
   reliability finding first, but it is also security-relevant: **it means no deployment can
   currently be running the code in this branch as its production entry point**, so any security
   posture claims about "the system enforces X at startup" are unverifiable/moot until this is
   fixed. `tests/integration/test_startup.py` imports `async_main` directly and never calls
   `main()`, which is why this shipped undetected (`nightwatch/main.py:296-368` has zero test
   coverage; confirmed via repo-wide grep for `test_main`).

2. **Multiple safety subsystems are fully built, unit-tested in isolation, and never wired into
   the running orchestrator.** This is the domain's most important structural risk: a reviewer
   reading `safety_interlock.py`, `emergency_response.py`, or `watchdog.py`'s `SafeStateHandler`
   would reasonably conclude the system has defense-in-depth. Grep across the entire repository
   shows otherwise:
   - `SafetyInterlock` (safety_interlock.py:154, the documented "gatekeeper for all telescope
     commands") is only ever constructed in `tests/unit/test_safety_interlock.py` — zero
     production call sites in `orchestrator.py`, `tool_executor.py`, or `main.py`.
   - `EmergencyResponse` (emergency_response.py:100) is likewise only constructed in
     `tests/unit/test_emergency_response.py`. `orchestrator.py`'s actual `emergency_shutdown()`
     (orchestrator.py:2886) is an independent, simpler, single-attempt reimplementation with no
     retries and no confirmation polling (contrast with `EmergencyResponse.emergency_park`'s
     3-retry, poll-for-`is_parked` loop).
   - `SafeStateHandler` (watchdog.py:733) is likewise never constructed outside
     `tests/unit/test_watchdog.py`; `WatchdogManager.set_safe_state_callback` is never called
     anywhere in `orchestrator.py` (confirmed by grep), so `_check_services_once`'s
     `if failed_critical and self._safe_state_callback:` branch (watchdog.py:459) never fires.
     **Practical consequence: a critical-service failure for `mount`, `weather`, `power`, or
     `enclosure` (all marked `critical=True` in `DEFAULT_CONFIGS`, watchdog.py:116-190) that is
     NOT specifically a `safety_monitor` heartbeat timeout produces only a `logger.critical` log
     line — no automatic park or roof close is triggered.** Only the `SAFETY_MONITOR` service
     type has a wired hardware fail-safe (SAFE-004, via `set_safety_veto_callback`,
     orchestrator.py:1603).
   - Even if `SafeStateHandler` or `EmergencyResponse` were wired up, both call
     `self._roof.get_state()` (emergency_response.py:261, watchdog.py:834) to poll for enclosure
     closure — but the real `services/enclosure/roof_controller.py` exposes `state` as a
     **property**, not a `get_state()` method (roof_controller.py:539). This would raise
     `AttributeError` on first use against production hardware; it is currently masked only
     because both modules are tested exclusively against `MagicMock()` roof fixtures, which
     fabricate any attribute requested (`tests/unit/test_emergency_response.py:49-54`).
   - `EventBus` (orchestrator.py:507, a ~350-line pub/sub implementation with subscription
     history/stats) and `CommandQueue`/`CommandPriority` (orchestrator.py:109-374, a
     priority-ordered command queue meant to let `EMERGENCY` commands preempt in-flight `NORMAL`
     ones) are both fully implemented and exported in `__all__`, but `Orchestrator` never
     instantiates either — it uses its own smaller ad hoc `_event_listeners` dict instead. The
     elaborate emergency-preemption priority model described in `CommandPriority`'s docstring
     (orchestrator.py:109-123) does not actually preempt anything in the live system.
   - **Net effect for the security/safety auditors:** treat `SafetyInterlock`, `EmergencyResponse`,
     `SafeStateHandler`, `EventBus`, and the priority `CommandQueue` as **not part of the
     enforced safety boundary**. The actual enforced boundary today is: `services/safety_monitor`
     (cross-domain) driving the roof directly + `_on_safety_change`/`_on_safety_veto`
     cancellation + the manual park/close blocks inline in `_safe_shutdown`/`end_session`/
     `emergency_shutdown`.

3. **The "cancel all commands" step of both shutdown paths is a no-op.**
   `graceful_shutdown()` (orchestrator.py:2837-2843) and `emergency_shutdown()`
   (orchestrator.py:2898-2903) both cancel commands tracked in `self._active_commands` (populated
   only by `execute_cancellable`, orchestrator.py:2555). Repo-wide grep confirms
   `execute_cancellable` has exactly one call site — its own definition — and is never invoked by
   `tool_executor.py` or anything else. The real in-flight command is tracked via
   `self._active_context` (a single `CommandContext`, set by `tool_executor.py:351`), which
   neither shutdown path references or cancels directly (only the safety-monitor-driven
   `_on_safety_change`/`_on_safety_veto` callbacks do). Practically: if `emergency_shutdown()` is
   invoked outside of the safety-monitor path (e.g., a future direct operator/API trigger), the
   log message "Immediately cancel all commands" is misleading — the actual running voice-tool
   command is left untouched while mount and enclosure are being driven underneath it.
   `emergency_shutdown()` also unconditionally `return True`s (orchestrator.py:2945) even when
   both the mount-park and enclosure-close `except` blocks were hit — callers cannot detect
   partial failure from the return value; they must know to check logs.

4. **Duplicate, incompatible `SafetyInterlockError` classes.** `nightwatch/exceptions.py:263`
   defines `SafetyInterlockError(SafetyError)` (part of the `NightwatchError` hierarchy,
   constructor `(message, interlock_name, required_state, current_state)`).
   `nightwatch/safety_interlock.py:552` independently defines its **own**
   `SafetyInterlockError(Exception)` (constructor `(message, status)`) — unrelated to the first
   by inheritance. `safety_interlock.py`'s `require_safety_check` decorator (safety_interlock.py:
   514-549) raises the local one. Code that did `except nightwatch.exceptions.SafetyInterlockError`
   expecting to catch safety-interlock failures would not catch this. In practice this is currently
   low-impact because (a) `SafetyInterlock`/`require_safety_check` aren't wired into production
   (see finding 2) and (b) grep confirms nothing in `nightwatch/` or `services/` imports
   `SafetyInterlockError` from `exceptions.py` at all — but it is a real footgun for anyone who
   does complete the wiring later, and evidence that the exception hierarchy in `exceptions.py`
   is largely aspirational (see Quality §, dead-code item).
5. **Config parsing is safe.** `load_config()` uses `yaml.safe_load` (config.py:991), not
   `yaml.load`, so no arbitrary-object-deserialization risk from a malicious config file.
   Env-var override type coercion (config.py:947-956) only does bool/int/float parsing, no
   `eval`/`exec`; no injection vector found.
6. **Filesystem writes are narrow and non-attacker-controlled in the reviewed code.** Log file
   path (`logging_config.py:232-245`, `RotatingFileHandler`) and session-log path
   (`orchestrator.py:2062-2094`, writes to `Path(self.config.data_dir if hasattr(...) else "logs")`
   joined with `session_{self.session.session_id}.json`) both come from operator-controlled
   config/CLI, not from voice/LLM input reaching this domain directly — no path-traversal vector
   observed here. Note `hasattr(self.config, 'data_dir')` is always `False` in practice: pydantic's
   `NightwatchConfig` (config.py:824-866) has no `data_dir` field, so session logs always land in
   a `logs/` directory relative to the process's current working directory regardless of
   deployment config — a portability/operational gap more than a security one, but worth the
   deployment-focused auditor's attention (systemd units should set `WorkingDirectory=` or this
   silently writes into `/` or wherever the unit starts).

### Quality observations

1. **Recurring "designed, tested-in-isolation, never wired" pattern.** Across this domain alone,
   at least five substantial, individually well-documented subsystems have zero production call
   sites: `SafetyInterlock`, `EmergencyResponse`, `watchdog.SafeStateHandler`, `EventBus`, and the
   `CommandQueue`/`CommandPriority` preemption system (all cited with line numbers under Security
   §, finding 2, to avoid duplication). The same pattern shows up in supporting modules:
   `nightwatch/constants.py`'s entire safety-threshold section (`WIND_LIMIT_MPH`,
   `HUMIDITY_LIMIT_PERCENT`, `TEMP_MIN_F`, etc., constants.py:34-61) is imported by nothing outside
   `__init__.py`'s two unrelated convenience names — and it has already **drifted** from the
   real source of truth (`SafetyConfig` in config.py has 3-tier warning/park/emergency thresholds
   per parameter; `constants.py` has a single flat value per parameter, e.g.
   `WIND_LIMIT_MPH = 25.0` vs. `SafetyConfig.wind_limit_warning/park/emergency = 20/25/30`).
   Similarly `nightwatch/types.py`'s ~40 shared types/Protocols are used by nothing outside
   `nightwatch/__init__.py`'s 5-name convenience re-export — `services/` and `voice/` define their
   own local equivalents instead. `nightwatch/exceptions.py`'s device/command/catalog exception
   subclasses (`DeviceBusyError`, `CommandTimeoutError`, `ObjectNotFoundError`, etc.) are likewise
   unreferenced outside the module itself and docs. This suggests architecture/scaffolding work
   consistently outpacing integration — consistent with `10-history.md`'s finding of a 16:1
   feature-to-test commit ratio and single-author bus factor (`10-history.md:301-321`).
2. **Confirmed logic bug in `StartupSequence.run()`'s dependency check**
   (`nightwatch/health.py:686-692`):
   ```python
   for dep in dependencies:
       if dep not in self._started_services:
           logger.warning(f"Skipping {service_name}: dependency '{dep}' not started")
           continue          # <-- only continues the inner `for dep in dependencies` loop
   # falls through to check service_name's health regardless
   ```
   The `continue` only affects the inner dependency loop, not the outer per-service loop, so the
   logged "Skipping {service_name}" never actually happens — the service's health check runs
   anyway even when a declared dependency (e.g. `guider` depends on `mount`) never started. No
   test exercises the failing-dependency path (`tests/integration/test_startup.py`'s fixture
   always configures `mount` as a healthy simulator), so this has never been caught.
3. **`nightwatch/orchestrator.py` module docstring references a nonexistent method.** Line 46:
   `response = await orchestrator.process_command("slew to M31")` — there is no
   `process_command` method anywhere on `Orchestrator` (confirmed by grep); command dispatch
   actually happens via `tool_executor.py` calling `set_active_context`/`clear_active_context`
   directly. Minor, but a new-engineer-facing docstring should not describe an API that doesn't
   exist.
4. **Two overlapping health/liveness loops with different mechanisms and cadences.**
   `Orchestrator._health_loop` (orchestrator.py:2096) polls `service.is_running` every 30s and
   drives the restart-policy state machine (`ServiceRegistry.should_restart`/`get_restart_delay`,
   orchestrator.py:1397-1465, a well-designed exponential-backoff restart system). Separately,
   `WatchdogManager._check_services` (watchdog.py:420) runs every 5s on a heartbeat/timeout model
   that services must explicitly call (`watchdog.heartbeat(service_type)`). Nothing in
   `orchestrator.py` calls `self.watchdog.heartbeat(...)` for the standard services (mount,
   weather, camera, etc.) — grep shows the only production heartbeat caller pattern is the
   SAFE-004 safety_monitor path. So `WatchdogManager`'s per-service `DEFAULT_CONFIGS` entries for
   `MOUNT`, `WEATHER`, `CAMERA`, `GUIDER`, `FOCUSER`, `ENCLOSURE`, `POWER` (watchdog.py:116-172)
   likely never receive a heartbeat in production and would sit at `ServiceState.UNKNOWN`
   forever (their `check_timeout()` returns `False` when `last_heartbeat is None`,
   watchdog.py:252-253) — meaning the watchdog's restart/failure callbacks for those services are
   also effectively inert, and `_health_loop`'s simpler `is_running`-poll restart mechanism is
   the one actually doing the work. Worth confirming with whoever owns the individual `services/`
   modules whether `watchdog.heartbeat()` is called from inside those services (out of this
   domain's scope to verify further).
5. **Test coverage gaps.** `nightwatch/main.py` (372 lines, the literal CLI entry point) has zero
   dedicated unit tests; the only test file touching `nightwatch.main`
   (`tests/integration/test_startup.py`) imports `async_main`, `create_parser`, `GracefulShutdown`
   directly and never calls `main()` — which is exactly why the `setup_logging(level=...)` bug
   above shipped. `nightwatch/health.py`'s `StartupSequence` has 3 tests, none of which exercise a
   failing/unstarted dependency. `nightwatch/orchestrator.py`'s `execute_cancellable`/
   `cancel_command`/`cancel_all_commands`/`get_active_commands` have zero tests anywhere in the
   repo (confirmed by grep across `tests/`). By contrast, `config.py`'s safety-allowlist logic
   (§5) and `watchdog.py`'s SAFE-004 fail-safe path (`tests/unit/test_safe_004_watchdog_failsafe.py`,
   345 lines) are genuinely well tested — coverage quality in this domain is bimodal: the
   recently-touched safety-critical paths (SAFE-001/002/004, per `10-history.md`'s May 2026
   hardening push) are carefully tested, while older/peripheral modules (`main.py`, `health.py`,
   the pre-ARCH-003 cancellation system) are not.
6. **Dangling documentation reference.** `config.py:81-82` refers to "the CLAUDE.md
   prohibited-edits list" as the governance mechanism restricting edits to `safety_monitor`; no
   `CLAUDE.md` file exists anywhere in this repository (confirmed via repo-wide search). Either
   the file was removed/never committed, or the governance process it describes doesn't actually
   exist yet — worth flagging for the chief architect / process reviewer.
7. **`orchestrator.py` is a 3,446-line single file** covering service registry, session state,
   event bus, metrics, command timeout/cancellation, restart policy, and shutdown sequencing all
   in one class (`Orchestrator`) plus ~10 supporting classes. This is the domain's obvious
   complexity hotspot and highest-churn file (10 commits, single author, per `10-history.md:46,99`)
   — any future change here has no second reviewer's mental model to check against, and the file
   is large enough that (as demonstrated above) entire subsystems within it can go unused without
   anyone noticing.
8. **Minor:** `nightwatch/emergency_response.py`'s `emergency_park` and
   `watchdog.SafeStateHandler.enter_safe_state` call `self._mount.stop()` /
   `self._mount.park()` without `await`. This is correct for the real `LX200Client` (confirmed
   synchronous, `services/mount_control/lx200.py:530,580`) but would silently no-op (coroutine
   created, never awaited, and a coroutine object is truthy so `if success:` proceeds as if it
   succeeded) against an async mount implementation such as
   `services/simulators/mount_simulator.py` (confirmed `async def stop/park`,
   mount_simulator.py:131,143). Since both modules are unreachable from production today (finding
   2 above), this is latent rather than active, but it would need fixing before either module
   could be safely wired up, and it's the kind of duck-typed contract mismatch that unit tests
   using `MagicMock()` (not `AsyncMock()`) will never catch.

---

## Cross-domain touchpoints (for other analysts)

- **Voice & NLP / Command Execution domains:** `nightwatch/voice_pipeline.py` physically lives in
  this directory but is audio/STT/TTS/wake-word plumbing (`WakeWordDetector`, `AudioCapture`,
  `STTInterface`, `TTSInterface`, `VoicePipeline`) with no direct coupling to `orchestrator.py`
  or `cancellation.py` (confirmed by grep) — it is not covered in depth here and should be treated
  as that domain's territory despite the directory boundary.
- **`nightwatch/tool_executor.py`** (Command Execution domain) is the sole real caller of
  `Orchestrator.set_active_context`/`clear_active_context` — any change to the ARCH-003
  cancellation contract in `orchestrator.py` must be coordinated with that file.
- **`services/safety_monitor/monitor.py`** (Astronomy & Hardware Services domain) is the actual
  live safety brain this domain's callbacks (`_on_safety_change`, `register_safety`) depend on;
  its `SafetyStatus` duck-typed contract (`.is_safe`, `.action.name`, `.reasons`) is assumed but
  not enforced by a shared type in this domain.
- **`services/enclosure/roof_controller.py`** and **`services/mount_control/`** — the interface
  mismatches noted above (`get_state()` vs. `state` property; sync vs. async mount clients) are
  genuinely cross-domain contract bugs; whoever owns `services/` should be aware their real
  `RoofController`/mount APIs don't match what `nightwatch/emergency_response.py` and
  `nightwatch/watchdog.py` expect.
- **`nightwatch/llm_client.py`** (LLM Client domain) reads `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`
  directly from `os.environ` (llm_client.py:454,572) rather than through `NightwatchConfig`'s
  `LLMConfig` (which has no `api_key`/`endpoint` fields at all, contrary to what
  `00-inventory.md:291` describes) — API key handling bypasses this domain's config validation
  and env-override-allowlist machinery entirely. Worth the security auditor's attention even
  though the file itself is out of scope here.
