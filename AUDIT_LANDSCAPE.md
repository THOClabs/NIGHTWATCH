# NIGHTWATCH — Repository Landscape Audit

> **Audit commit:** `7fa94a2` · **Date:** 2026-07-02 · **Scope:** read-only landscape audit.
> All `path:line` citations are relative to this commit. This document reports; it does not fix.
>
> **Confidence legend:** `[confirmed]` = the exact cited lines were read and quoted · `[inferred]` = strong indirect evidence · `[suspected]` = plausible but unverified.
>
> **Method (summary):** three parallel exploration passes, then a 10-agent evidence wave (five security agents grouped by trust boundary, an adversarial refuter, an entry-point checker, a test-quality sampler, a dependency verifier) whose every citation was mechanically snippet-verified against the source (174 evidence items: 168 exact, 5 within ±8 lines, 1 corrected here). High-severity security findings received an independent second read. Load-bearing "X does not exist / is not wired" claims were checked with recorded grep scopes. See Appendix A.

---

## Executive summary

NIGHTWATCH is an ambitious, **~64,000-LOC** voice-controlled autonomous telescope observatory, written almost entirely by AI agents (Claude Opus 4.5/4.7/4.8) driven by an autonomous build loop, for a specific Nevada dark-sky installation. It is best understood as **a large kit of individually real, individually tested parts that has never been assembled into a running machine.**

The single most important finding, which an adversarial refuter tried and failed to overturn:

- **The system does not run — it crashes on startup. `[confirmed by execution]`** Running the entry point revealed it aborts *immediately*: `python -m nightwatch.main` (every mode but `--version`) dies with `TypeError: setup_logging() got an unexpected keyword argument 'level'` (`nightwatch/main.py:308` — the parameter is `log_level`), before it ever reaches the orchestrator. And even past that two-line bug, production `nightwatch/main.py:247` would start the orchestrator with an **empty service registry** — nothing constructs the real hardware services from config outside tests and docstrings. The voice pipeline imports a **module that does not exist** (`nightwatch/voice_pipeline.py:2086`, confirmed at runtime) and silently falls back to a 3-command stub; the 5,662-line real tool layer (`voice/tools/telescope_tools.py`) is wired only in tests. So the headline capability — *speak a command, telescope acts, safety vetoes* — has all its pieces present, none connected, behind a front door that won't open. (Full runtime evidence: §4.5.)

The rest follows from that:

- **The hardware/driver layer is the crown jewel — but it needs a debugging pass, not just wiring. `[confirmed]`** ~28k LOC across 20 subsystems (ASI camera, PHD2, Alpaca, INDI, LX200, GPIO roof, plate-solving, weather, PDU) is genuine device code with graceful mock fallbacks. The deepen pass, however, found a layer of **correctness bugs that produce plausible-but-wrong behavior** (§3.8): declinations within 1° of the equator lose their sign, all four Alpaca adapters call the client with the wrong constructor shape, position getters return RA=0h/Dec=0° on error, a catalog star carries the wrong coordinates, and observation history is written non-atomically. Still the highest-value asset — but "turn it on" is followed closely by "debug it."
- **The safety system has real latent bugs, but they are currently inert. `[confirmed]`** The watchdog is never started; emergency roof-close can't close a mid-opening roof; a safety-monitor close path awaits nothing; and a broader **async class** (§3.7) means many drivers block the single event loop (the safety monitor would freeze behind a stalled mount). All reachable only once someone assembles the system, which nobody has.
- **The tests are thinner than they look, and CI is decorative. `[confirmed]`** Correcting a pass-1 over-claim: the safety *unit* tests are genuinely behavioral, but the **entire `tests/e2e/` tier and two of three safety-integration suites import zero production code** (mock theater that would pass against an empty repo), and the one test of base-`SafetyMonitor` logic is dead on checkout (§4.1). Meanwhile every CI gate swallows its own failures (`|| true`, `continue-on-error`, `2>/dev/null || echo`) — a green badge proves the YAML parses, nothing more.
- **The repository documents a project that doesn't match the code. `[confirmed]`** The quickstart command references a non-existent module, release notes are dated 2024 in a 2026 project, and there are no git tags despite a "released v0.1.0."

**The single biggest opportunity** is therefore not new features — it is **assembly**: a service-factory that builds the existing, tested drivers from config, a repaired voice→LLM→tool path, and one honest end-to-end simulated integration test. Days-to-weeks of work would convert a large, dormant, well-built parts bin into a system that actually turns on. Everything in the expansion section (§7) is gated on that. Full three-tier expansion analysis is in §7.

**Finding counts** (**121 verified findings** across two passes — 69 in pass 1, 52 in a deepen pass covering the frozen subsystems, an async bug-class hunt, a broken-wiring sweep, and full test grading; every citation mechanically snippet-verified, security/high severities post independent cross-read):

| Severity | Where | Notes |
|---|---|---|
| High (live) | 2 config/deploy artifacts (`privileged: true` container; the misconfigured CI service container) | The most severe *runtime* safety and correctness bugs are gated behind the assembly gap |
| Medium | ~35 | Safety-close bugs, async event-loop blocking, driver correctness (wrong coords/sign/URL), network exposure, HTML-email injection, dependency/deploy breakage |
| Low / Info | remainder | Includes genuine defensive controls, credited in §3.6, and confirmed dead code |

> **Reachability is load-bearing throughout.** Because production `main.py` starts an empty service registry, the large majority of security and correctness findings are **only-if-assembled** — real bugs that arm the moment someone wires the drivers, not exploits against the code as it runs today. Each finding is tagged accordingly.

---

## 1. System map

### 1.1 What this repo is

An **autonomous observatory control system** for a DIY Maksutov-Newtonian telescope on a harmonic-drive German equatorial mount, controlled by voice through a local (on-device) AI pipeline, at a permanent Nevada dark-sky site. The design intent (`README.md`, `NIGHTWATCH_Build_Package.md`) is *local-first, no cloud*: speech-to-text (Whisper) → LLM intent+tool-calling → observatory tool execution → hardware, with environmental safety interlocks that can veto any action and close the roof. Target compute is an NVIDIA DGX Spark; mount firmware is OnStepX on a Teensy 4.1.

Scale `[confirmed]`: **64,068 LOC** of product Python (`nightwatch/` + `services/` + `voice/`) and **56,256 LOC** of tests across **86 `test_*.py` files**; 298 tracked files total.

### 1.2 Three layers

| Layer | Dir | LOC (approx) | Role |
|---|---|---|---|
| Orchestration / brain | `nightwatch/` | ~15,500 | Orchestrator, voice pipeline, LLM client, tool executor, safety interlock, watchdog, emergency response, config |
| Hardware / domain services | `services/` | ~28,000 | 20 subsystems: real device/API drivers + simulators |
| Voice I/O + tools | `voice/` | ~9,500 | Wyoming STT/TTS servers, whisper/piper wrappers, the 90-handler telescope tool registry |

Largest files `[confirmed]`: `voice/tools/telescope_tools.py` (5662), `nightwatch/orchestrator.py` (3446), `nightwatch/voice_pipeline.py` (2517), `services/camera/asi_camera.py` (2494), `services/focus/focuser_service.py` (2414), `services/power/power_manager.py` (1782), `services/safety_monitor/monitor.py` (1743), `services/enclosure/roof_controller.py` (1668).

The 20 `services/` subsystems and their reality:

| Subsystem | Reality `[confirmed]` unless noted | Evidence |
|---|---|---|
| camera (ASI) | Real ZWO ASI SDK w/ sim fallback; FITS writer | `services/camera/asi_camera.py` |
| focus | Real V-curve autofocus w/ cancellation | `services/focus/focuser_service.py` |
| guiding (PHD2) | Real TCP JSON-RPC to PHD2 :4400 | `services/guiding/phd2_client.py:153` |
| alpaca | Real ASCOM Alpaca REST + UDP discovery | `services/alpaca/alpaca_client.py:172` |
| indi | Real PyIndi, gated on `PYINDI_AVAILABLE` | `services/indi/indi_client.py` |
| mount_control | Real LX200 over serial/TCP + OnStepX ext. | `services/mount_control/lx200.py` |
| enclosure | Real GPIO roll-off roof controller | `services/enclosure/roof_controller.py:108` |
| weather | Real Ecowitt + AAG CloudWatcher (HTTP) | `services/weather/ecowitt.py:124` |
| astrometry | Real plate-solve subprocess (solve-field/ASTAP) | `services/astrometry/plate_solver.py` |
| power | Real PDU over HTTP/SNMP, sim default | `services/power/power_manager.py:147` |
| safety_monitor | Real 3-way safety logic, dual rain voting | `services/safety_monitor/monitor.py` |
| catalog | Real logic, thin embedded data | `services/catalog/` |
| meteor_tracking | Real NASA CNEOS fireball API + thematic extras | `services/meteor_tracking/` |
| ephemeris | Real Skyfield | `services/ephemeris/skyfield_service.py` |
| encoder | Real serial encoder bridge | `services/encoder/encoder_bridge.py` |
| alerts | Real HTTP alert dispatch | `services/alerts/alert_manager.py` |
| nlp | Real logic, **orphaned** (see §6) | `services/nlp/` |
| scheduling | Real logic, **orphaned** (see §6) | `services/scheduling/` |
| simulators | In-process hardware sims for `--simulator` | `services/simulators/` |
| voice (trainers) | Vocabulary / wake-word personalization | `services/voice/` |

### 1.3 Control & data flow — intended vs actual

**Intended:** `process_audio` → VAD capture → Whisper STT → `process_text` → `LLMClient.chat(message, tools)` → for each tool call, `ToolExecutor.execute()` → orchestrator → service → hardware → result folded back to LLM → Piper TTS. Safety is enforced in three layers: pre-command veto (`nightwatch/safety_interlock.py`), continuous monitor with dual rain-sensor voting (`services/safety_monitor/monitor.py`), and a hardware watchdog that closes the roof on heartbeat timeout (`nightwatch/watchdog.py`).

**Actual `[confirmed]`:** the chain is never assembled (§3.1). `nightwatch/main.py:247` builds an `Orchestrator(config)` and calls `start()` (`nightwatch/main.py:272`), but `Orchestrator.start()` only iterates an empty registry and logs *"No required services registered"* (`nightwatch/orchestrator.py:1928`). The voice pipeline and LLM client are never constructed by `main.py` or the orchestrator at all.

### 1.4 The two divergent tool layers `[confirmed]`

There are **two** tool systems and the confirmation logic lives in the one the pipeline does *not* use:

- `nightwatch/tool_executor.py` (~30 handlers, Pydantic-validated at `:316`) — what the voice pipeline would call. Has **no confirmation concept** and covers only mount/catalog/ephemeris/weather/safety/session (no roof/power/emergency).
- `voice/tools/telescope_tools.py` (~90 handlers via `create_default_handlers()` at `:1405`) — richer, has a confirmation-aware `ToolRegistry.execute(confirmed=...)` (`:1374`) that gates 4 tools (open/close/stop roof, emergency_shutdown). Called only in tests / `__main__`.

The pipeline references a **third**, non-existent module (`nightwatch.telescope_tools`) and thus loads no tools at all (§3.2).

### 1.5 External touchpoints

Serial (LX200 mount, encoder, roof `/dev/ttyUSB0`); TCP (PHD2 :4400, LX200-over-IP, Alpaca :11111, safety network probe); UDP (Alpaca discovery); INDI (:7624); GPIO (roof relays/limit switches, voice LED pin 18); subprocess (`solve-field`, ASTAP); HTTP(S) outbound (Ecowitt, NASA CNEOS `ssd-api.jpl.nasa.gov`, Anthropic/OpenAI, alert endpoints, PDU); Skyfield `.bsp` ephemeris; and ~16 filesystem write sites (FITS, session/observation logs, success/preference JSON, TTS audio, meteor state, focus data, trained models).

---

## 2. Dependencies & supply chain

The dependency story is told in **four disagreeing places** — `pyproject.toml` (open `>=` bounds), `services/requirements.txt` + `voice/requirements.txt` (`~=` caps), and `uv.lock` (resolved pins) — and they contradict each other. `[confirmed]`

### 2.1 Runtime imports declared in no manifest `[confirmed]`

| Package | Imported at | Declared in pyproject / requirements / uv.lock? |
|---|---|---|
| `llama-cpp-python` (**default LLM backend**, `LLMBackend.LOCAL`) | `nightwatch/llm_client.py:353`, `:667` | **No** — absent everywhere |
| `anthropic` (cloud fallback) | `nightwatch/llm_client.py:467` | **No** |
| `openai` (cloud fallback) | `nightwatch/llm_client.py:585` | **No** (only a commented-out, different `openai-whisper` at `voice/requirements.txt:6`) |
| `RPi.GPIO` (roof, LED) | `services/enclosure/roof_controller.py:108`, `nightwatch/voice_pipeline.py:1318` | **No** |

Consequence: a clean `uv sync` cannot run the *default* (local-LLM) path or the roof GPIO. **Correction to a common assumption:** `wyoming` is **not** an undeclared PyPI dependency — the repo *vendors* its own Wyoming protocol in `voice/wyoming/` (`voice/wyoming/protocol.py:11`). `[confirmed]`

### 2.2 Version conflicts and lock gaps `[confirmed]`

- The `~=` caps in `voice/requirements.txt` are **violated** by `uv.lock`'s resolved versions — most starkly `numpy` (pinned `~=1.26`, i.e. `<2.0`; resolved `2.x` — a full major jump), plus `faster-whisper`, `piper-tts`, `pymicro-vad` (`pyproject.toml:67`, `voice/requirements.txt:13`). **Observed consequence `[confirmed by execution, §4.5]`:** `uv sync` installs numpy 2.4.6, which breaks the astropy import chain and fails `tests/unit/test_plate_solver.py` at collection — the lock resolves an environment the pins were written to forbid.
- `pyindi-client`, `alpyca`, and `webrtcvad` are declared in the requirements files but present in **neither** `pyproject.toml` **nor** `uv.lock` (`services/requirements.txt:15`, `voice/requirements.txt:19`) — the documented `pip install -r` path installs packages the lockfile never pins.
- `webrtcvad~=2.0.10` is **abandoned upstream** (last release 2.0.10, 2017) and kept as the VAD fallback (`voice/requirements.txt:19`). `[inferred]` on the abandonment date.

### 2.3 License `[confirmed]`

The `LICENSE` file and `pyproject.toml:21` both declare **CC BY-NC-SA 4.0** — a *content* license with a NonCommercial clause, unusual and legally ambiguous for software — while `pyproject.toml:38` simultaneously classifies it `License :: Other/Proprietary License`. These contradict each other. No copyleft (GPL/LGPL) appears among locked deps; the spot-checked upstreams (faster-whisper, piper-tts, ctranslate2, skyfield MIT; astropy BSD) are permissive.

### 2.4 Python version disagreement `[confirmed]`

`pyproject.toml:22` and `bin/nightwatch` require `>=3.11`, but `README.md:6` (badge) and `deploy/scripts/install.sh` advertise/allow 3.10 — a 3.10 user passes the installer then fails the package metadata and the launcher's own check.

---

## 3. Security surface

Every finding below carries a **reachability** tag, because the assembly gap (§3.1) means much of the vulnerable code does not execute in the shipped system. This is not an excuse — it is the difference between "exploitable today" and "latent landmine that arms the moment someone wires the system." Severities reflect an independent second read of every high finding.

### 3.1 The assembly gap (architectural, load-bearing) `[confirmed]`

An adversarial agent was tasked to *disprove* "nothing assembles this system" and **could not**:

- **Startup crash (found by running it).** Before the registry even matters, `main()` crashes at `nightwatch/main.py:308` — `setup_logging(level=…)` against a function whose parameter is `log_level` (`nightwatch/logging_config.py:185`) → `TypeError` on every mode but `--version`. `[confirmed by execution, §4.5]`
- **Empty registry.** `nightwatch/main.py:247` `orchestrator = Orchestrator(config)`; `Orchestrator.start()` (`nightwatch/orchestrator.py:1912`) iterates `self.registry.list_services()` and warns "No required services registered" (`:1928`). The only `register_*` call sites repo-wide are the method definitions, `tool_executor.py`, and `tests/**`. No factory, DI, plugin loader, or entry-point group builds services from config. *(Search: `register_mount|register_camera|register_weather|register_safety|register_enclosure|register_*`, scope = repo excluding tests.)*
- **Phantom import.** `nightwatch/voice_pipeline.py:2086` `from nightwatch.telescope_tools import get_tool_definitions` — that module does not exist (`ls nightwatch/` has no `telescope_tools.py`; no such symbol anywhere). The `ImportError` is caught (`:2088`) and `_get_tools()` returns `None`, so the LLM is always called with `tools=None`.
- **Stub fallback.** `nightwatch/voice_pipeline.py:2015` — the `_execute_tool` fallback handles only `goto_object`, `park_telescope`, `get_weather`; everything else returns "Unknown tool."
- **Real tools unused.** `voice/tools/telescope_tools.py:1405` `create_default_handlers()` is invoked only in tests/`__main__`.
- **Orphaned AI cluster.** `services/scheduling` + `services/nlp` are imported only by `services/ai_services.py:320,339`, whose only instantiator is `examples/v05_ai_demo.py` — never by `nightwatch/*`. `[confirmed]`

**Reachability: reachable-in-running-system** (it *is* how the system runs — into a wall). Severity: this is the defining structural fact, not a "vulnerability," but it is why most findings below are only-if-assembled.

### 3.2 LLM / voice → tool-call path

| ID | Finding | Sev (post-review) | Reach | Evidence |
|---|---|---|---|---|
| VOX-NOWIRE | Entire voice→LLM→tool path never constructed in shipped system | info | test-only | `nightwatch/main.py:247`,`:272` |
| VOX-GETTOOLS-BROKEN | `_get_tools()` imports non-existent module → LLM always gets `tools=None` | medium | only-if-assembled | `nightwatch/voice_pipeline.py:2086` |
| VOX-NO-CONFIRM-GATE | Pipeline executes every LLM tool call with **no confirmation**; `requires_confirmation()`/`get_confirmation_prompt()` exist but are never called | low (was high) | only-if-assembled | `nightwatch/voice_pipeline.py:1961`, `nightwatch/llm_client.py:1089` |
| VOX-DIVERGENT-EXECUTORS | Confirmation logic lives in the tool layer the pipeline doesn't use; the one it does use has no confirmation and no roof/power/emergency handlers | medium | only-if-assembled | `voice/tools/telescope_tools.py:1374`, `nightwatch/tool_executor.py:353` |
| VOX-INJECTION-ADVISORY-SAFETY | System-prompt safety is advisory and injectable (via utterance or replayed tool-result text); **but** slew/goto/unpark have a deterministic `safety.is_safe` veto in the executor. Confirmation has no such backstop. | medium | only-if-assembled | `nightwatch/llm_client.py:997`, `nightwatch/tool_executor.py:447` |
| VOX-CLOUD-EXFIL | Local→cloud fallback ships the full context (voice transcripts + site telemetry: sun altitude, wind, Nevada location) to Anthropic/OpenAI, contradicting the "local-first, no cloud" claim | medium | config/deploy | `nightwatch/llm_client.py:700`,`:920` |

Models in use `[confirmed]`: local primary llama-cpp (Llama 3.2 3B, path-driven); cloud fallbacks default to **`claude-3-haiku-20240307`** and **`gpt-4o-mini`** (legacy pins) (`nightwatch/llm_client.py:726`). STT faster-whisper `base`; TTS Piper `en_US-lessac-medium`.

### 3.3 Actuation & safety chain (real bugs, mostly dormant)

These are genuine correctness defects in the safety system. All are **only-if-assembled** except the dormant-watchdog fact itself, because `EmergencyResponse`/`WatchdogManager`/`SafetyMonitor` are not wired into the empty-registry runtime. Independent re-read confirmed each snippet verbatim and downgraded severities accordingly (a bug in code that can't run is not a live high).

| ID | Finding | Sev | Evidence |
|---|---|---|---|
| WATCHDOG-DORMANT | `WatchdogManager()` is constructed but `.start()` is **never called** and nothing ever heartbeats it → the SAFE-004 hardware fail-safe is dead. *(Search: `watchdog.start`, `record_heartbeat` excl. tests → no call sites.)* | low (was high) | `nightwatch/orchestrator.py:1602`, `nightwatch/watchdog.py:569` |
| WATCHDOG-NULL-HEARTBEAT | `check_timeout()` returns `False` when `last_heartbeat is None` → a safety service that dies before its first heartbeat never trips the veto | low (was high) | `nightwatch/watchdog.py:252` |
| EMERGENCY-CLOSE-NOT-FORCED | `emergency_close()` calls `roof.close()` **without** `emergency=True` despite a "force mode - bypass checks" comment → cannot close a roof that is mid-opening (`RuntimeError("Motor already running")`) | medium (was high) | `nightwatch/emergency_response.py:253`, `services/enclosure/roof_controller.py:714` |
| ROOF-GET-STATE-MISSING | Emergency/safe-state loops poll `roof.get_state()`, which **does not exist** on `RoofController` (only a `state` property) → `AttributeError` → close reported failed. Tests hide this by monkeypatching `get_state`. *(Search: `def get_state` → zero matches.)* | medium (was high) | `nightwatch/emergency_response.py:261`, `services/enclosure/roof_controller.py:538` |
| SAFETY-CLOSE-NOT-AWAITED | `SafetyMonitor._close_enclosure_safely()` calls the **async** `enclosure.close()` **without `await`** → un-awaited coroutine, roof never closes on the monitor's own emergency path (defeats the SAFE-001 fix for async enclosures) | medium (was high) | `services/safety_monitor/monitor.py:1532`, `nightwatch/orchestrator.py:1127` |
| INTERLOCK-ALT-ZERO-FAILOPEN | Altitude check uses `target_altitude or self._target_altitude`; a requested altitude of exactly `0.0` (horizon, below the 10° min) is falsy → discarded → below-horizon slew not blocked | medium | `nightwatch/safety_interlock.py:254` |
| ROOF-STOP-MOTOR-RACE | `_stop_motor()` only flips a flag; the in-flight `_run_motor()` loop never checks it → emergency close can start a second concurrent motor run | medium | `services/enclosure/roof_controller.py:880`,`:709` |
| STOP-MOTOR-NO-RELAY-DEENERGIZE | Motor stop clears a flag but does **not** de-energize GPIO relays (unlike the power-loss handler) | medium | `services/enclosure/roof_controller.py:882`,`:1391` |
| DAYLIGHT-EPHEMERIS-FAILOPEN | Missing sun altitude → `daylight_ok=True`; stale ephemeris only logs → system can treat daylight as "astronomical night" and permit opening `[inferred]` | medium | `services/safety_monitor/monitor.py:814`,`:807` |

### 3.4 Network surface

| ID | Finding | Sev | Reach | Evidence |
|---|---|---|---|---|
| NET-001 | Wyoming STT/TTS default-bind `0.0.0.0` with **no auth** on audio/command ingress | medium (was high) | only-if-assembled / standalone-runner | `voice/wyoming/stt_server.py:117`, `voice/wyoming/tts_server.py:164` |
| NET-002 | mDNS/Zeroconf advertises the unauthenticated endpoints on the LAN | medium | only-if-assembled | `voice/wyoming/startup.py:274` |
| NET-003 | Inbound audio chunks buffered unbounded → memory-exhaustion DoS | medium | only-if-assembled | `voice/wyoming/stt_server.py:234` |
| NET-004 | PHD2 client reads with **no timeout** → a hung/malicious endpoint blocks indefinitely | medium | only-if-assembled | `services/guiding/phd2_client.py:214` |
| NET-005 | PDU client sends Basic Auth (default **admin/admin**) in cleartext over `http://` | medium | only-if-assembled | `services/power/power_manager.py:147`,`:150` |
| NET-006 | Alpaca UDP discovery trusts any LAN responder → spoofed device redirection | low | only-if-assembled | `services/alpaca/alpaca_client.py:172` |
| NET-007 | Handlers return raw exception strings to unauthenticated clients (info leak) | low | only-if-assembled | `voice/wyoming/stt_server.py:193` |
| NET-008 | Outbound weather/Alpaca use plaintext `http://` with no TLS option | low | only-if-assembled | `services/weather/ecowitt.py:124` |

### 3.5 Subprocess / filesystem / secrets / deployment privilege

| ID | Finding | Sev | Reach | Evidence |
|---|---|---|---|---|
| PRIV-001 | Prod compose runs the main container **`privileged: true`** + bind-mounts host `/dev`, nullifying the non-root UID 10001 user | **high** | config/deploy | `docker/docker-compose.prod.yml:29`,`:38` |
| PRIV-002 | systemd grants **`CAP_SYS_RAWIO`** (root-equivalent: `/dev/mem`, raw block/PCI, ioperm) though `dialout gpio audio` groups already cover the need | medium (was high) | config/deploy | `deploy/systemd/nightwatch.service:65`,`:68` |
| DEP-001 | Documented install is `curl -fsSL … \| bash`; installer/upgrader use `git reset --hard origin/main` (+ arbitrary `--branch`) with **no pinning/signature** → RCE-as-root on repo/MITM compromise | medium | config/deploy | `deploy/scripts/install.sh:9`,`:421` |
| SEC-SUBPROC-01 | Windows `SystemTTS.speak()` interpolates spoken text into a `powershell -Command` string → **command injection** via a `"` + `);` in the text | medium | only-if-assembled | `voice/tts/piper_service.py:444`,`:436` |
| SEC-FS-02 | `ASICamera.capture_single()` joins a caller-supplied `filename` onto `data_dir` with no sanitization → path traversal / absolute-path write | low | only-if-assembled | `services/camera/asi_camera.py:976` |
| CFG-001 | `install.sh` writes `safety:` keys (`wind_limit_mph`, `humidity_limit_pct`, …) that don't match the Pydantic schema; `extra="ignore"` → operator's tightened safety thresholds **silently dropped** | medium | config/deploy | `deploy/scripts/install.sh:366`, `nightwatch/config.py:495` |
| CFG-002 | `install.sh` writes `/etc/nightwatch/config.yaml` with no `chmod` → world-readable (0644); any secret later added is exposed | low `[inferred]` | config/deploy | `deploy/scripts/install.sh:404` |
| SEC-001 | PDU config carries default `admin/admin` + SNMP RW community `private` | low | only-if-assembled | `services/power/power_manager.py:50`,`:806` |

No committed live secrets were found in the tracked tree; `nightwatch.yaml.example` contains placeholders, and cloud API keys are read from env (`ANTHROPIC_API_KEY`/`OPENAI_API_KEY`) and not logged directly (`nightwatch/llm_client.py:452`). `[confirmed]`

### 3.6 Defensive practices observed (credit where due) `[confirmed]`

- **LLM tool-call arguments are Pydantic-validated before execution**, in two independent layers (`nightwatch/llm_client.py:944` `_validate_tool_calls`; `nightwatch/tool_executor.py:316` `model_validate`). Unknown tools and invalid args are dropped.
- **Deterministic safety veto** on slew/goto/unpark in the executor (`nightwatch/tool_executor.py:447`) — injection cannot force an unsafe slew even if it defeats the advisory prompt, *when safety is wired*.
- **Deny-by-default safety env-override allowlist**: `SAFETY_ENV_OVERRIDE_ALLOWLIST = frozenset()` rejects any `NIGHTWATCH_SAFETY_*` override with a `logger.critical` (`nightwatch/config.py`, SAFE-003).
- **Dual-redundant rain-sensor voting** and **cancel-before-close ordering** exist and are behaviorally tested (§4).
- **Non-root container user** (UID 10001) and a hardened systemd unit (`ProtectSystem=strict`) — undermined only by PRIV-001/002.

### 3.7 Async & event-loop correctness (deepen pass) `[confirmed]`

A dedicated bug-class hunt (seeded by the pass-1 `SAFETY-CLOSE-NOT-AWAITED` finding) shows the codebase **systematically mixes `async def` APIs with blocking I/O**: many drivers are declared async but call synchronous socket/serial/model calls directly on the event loop, and only *some* paths correctly use `asyncio.to_thread` (e.g. `services/mount_control/lx200.py:528` `sync_to_coordinates` does; its siblings don't). In a real assembled run, any one stalled device would freeze the single event loop — including the safety monitor, watchdog, and TTS. All are **only-if-assembled** unless noted (the drivers aren't wired into the empty-registry runtime).

| ID | Finding | Sev | Evidence |
|---|---|---|---|
| ASYNC-ONSTEPX-BLOCKING | Every `async def` in `onstepx_extended.py` (PEC, driver-status, tracking-offset) calls the inherited synchronous `_send_command` on the loop — up to 5 s (`COMMAND_TIMEOUT`) blocked per command | medium | `services/mount_control/onstepx_extended.py:121`, `services/mount_control/lx200.py:154` |
| ASYNC-ENCODER-SERIAL-BLOCKING | `EncoderBridge._send_command` does blocking `pyserial` `read_until(b"#")` on the loop; an `asyncio.Lock` serializes but does not offload it | medium | `services/encoder/encoder_bridge.py:231`,`:222` |
| ASYNC-CLOUDWATCHER-BLOCKING | CloudWatcher async sensor reads call `_send_command`, which does blocking `socket.recv(256)` on the loop | medium | `services/weather/cloudwatcher.py:223`,`:217` |
| ASYNC-MOUNT-STATUS-BLOCKING | `LX200Client.get_corrected_position`/`get_pointing_error` are async but call the blocking `get_status()` (6 sequential round-trips, ≤30 s worst case) on the loop. *Downgraded: no production caller — the prod handler re-implements; effectively test-only.* | low | `services/mount_control/lx200.py:244`,`:310` |
| ASYNC-WHISPER-INFERENCE-BLOCKING | `WhisperSTT` runs blocking Whisper inference on the loop (the sibling Wyoming STT server correctly uses `run_in_executor`) | medium | `voice/stt/whisper_service.py:534`,`:420` |
| ASYNC-PIPER-TTS-BLOCKING | `PiperTTS.speak` runs neural synthesis + `sd.wait()` (blocks until playback ends) on the loop; the subprocess Piper variants correctly `await` | medium | `voice/tts/piper_service.py:280`,`:320` |
| ASYNC-CAMERA-TASK-NOT-RETAINED | `ASICamera.start_capture` does `asyncio.create_task(self._capture_loop(...))` and **discards the Task** — GC can kill it mid-exposure, its exceptions are never retrieved, and `stop_capture` has no handle to cancel it (only flips a flag) | medium | `services/camera/asi_camera.py:664` |
| METEOR-FIREBALL-TIMEOUT-UNCAUGHT | Fireball clients catch only `aiohttp.ClientError`; the request total-timeout raises `asyncio.TimeoutError` (not a subclass) → propagates uncaught instead of returning `[]` | low | `services/meteor_tracking/fireball_client.py:148`,`:289` |

### 3.8 Driver correctness, data integrity & injection (deepen pass)

The deepen pass read the ~13 subsystems pass 1 only characterized. The drivers are real, but carry correctness bugs that would produce **plausible-but-wrong** hardware behavior — the most dangerous kind, because nothing signals the error. All **only-if-assembled** unless noted.

| ID | Finding | Sev | Cat | Evidence |
|---|---|---|---|---|
| ALPACA-CTOR-SIGNATURE | All four Alpaca adapters construct `alpyca` device objects with the wrong arg shape — bare host as `address` (no port) and the int `self.port` passed into alpyca's `protocol: str` parameter → every Alpaca connection targets the wrong URL | high→medium `[inferred]` | correctness | `services/alpaca/alpaca_client.py:293`,`:963` |
| ALPACA-FABRICATED-COORDS | `AlpacaTelescope` getters swallow all exceptions and return sentinels: `ra`/`dec` → `0.0` on any read error (a valid-looking RA=0h/Dec=0° "position"), `is_slewing`/`is_parked`/`is_tracking` → `False` | medium | data-integrity | `services/alpaca/alpaca_client.py:332`,`:391` |
| ALPACA-FOCUSER-RELMOVE | `move_relative` reads position (which returns `0` on error, not `None`), adds steps, and issues an **absolute** move → a failed read drives the focuser to step 0 / hard stop | medium | correctness | `services/alpaca/alpaca_client.py:1092`,`:997` |
| MSE-01 | `LX200Client` derives declination sign from the degrees field only; a Dec in `-00°xx` parses `-00` → `-0.0`, and `-0.0 < 0` is `False` → **any target within 1° south of the equator loses its sign** (wrong goto) | medium | correctness | `services/mount_control/lx200.py:344`,`:212` |
| MSE-06 | `get_driver_status` returns an **all-clear** `DriverStatus` (all fault bits `False`) on empty/non-hex response — a real short/overtemp/stall fault that returns garbage is reported healthy | medium | correctness | `services/mount_control/onstepx_extended.py:269`,`:277` |
| MSE-05 | PEC `ready` flag has an operator-precedence + lowercasing bug → PEC reported "trained and ready" even with no PEC data | medium | correctness | `services/mount_control/onstepx_extended.py:134` |
| MSE-07 | LX200 command strings built by raw f-string interpolation of coordinate/site values (`:Sr{ra}`, `:Sd{dec}`, `:St{lat}`, `:Sg{lon}`) with no escaping — an embedded `#` or `:…#` can break framing or inject a second LX200 command | low | security | `services/mount_control/lx200.py:386`,`:630` |
| PLATESOLVE-WCS-CDELT-ZERO | `_parse_wcs` accepts a CDELT-only WCS as a valid solve but computes scale/rotation/field from the (all-zero) CD matrix → reports SUCCESS with fabricated 0 arcsec/px, 0° rotation, 0×0° field | medium | correctness | `services/astrometry/plate_solver.py:609`,`:644` |
| PLATESOLVE-POINTING-RA-WRAP | Pointing-error RA is a raw subtraction with no 0/360° wrap → near RA=0 the error is off by ~360° | medium | correctness | `services/astrometry/plate_solver.py:887` |
| PLATESOLVE-ASTAP-INI-NOVALIDATE | ASTAP `.ini` parse returns SUCCESS on `PLTSOLVD=T` with missing keys defaulted to 0 (RA=0/Dec=0, scale=0), RA not normalized | low | correctness | `services/astrometry/plate_solver.py:675` |
| SKYFIELD-JNOW-J2000-APPROX | `jnow_to_j2000` builds a Skyfield `Star` from JNow coords but `Star()` treats them as ICRS → precession/nutation is never actually inverted | low `[inferred]` | correctness | `services/ephemeris/skyfield_service.py:532` |
| INDI-FILTERNAMES-LEXSORT | Filter names ordered by `sorted()` over `FILTER_SLOT_NAME_*` keys → for ≥10 slots, `_10`/`_11` sort before `_2`, mapping names to the wrong physical position | low | correctness | `services/indi/device_adapters.py:161` |
| CATALOG-CORCAROLI-WRONGCOORDS | The named-star entry for Cor Caroli is mislabeled "Alioth" **and** carries Alkaid's coordinates → resolving "Cor Caroli" returns a position ~11° off in Dec (bad slew) | medium | data-integrity | `services/catalog/catalog_data.py:281`,`:287` |
| CATALOG-DUP-CATALOGID-OVERWRITE | Four duplicate `catalog_id`s across star/double-star lists; the upsert on the UNIQUE id means later entries silently overwrite earlier ones (e.g. Caph → Eta Cas) | medium | data-integrity | `services/catalog/catalog_data.py:291`, `services/catalog/catalog.py:187` |
| SUCCESS-TRACKER-NONATOMIC-SAVE | `SuccessTracker._save` rewrites the whole history JSON non-atomically (`open('w')`+`json.dump`, no temp+rename/lock) and `_load` swallows errors → one interrupted write silently discards **all** observation history | medium | data-integrity | `services/catalog/success_tracker.py:666`,`:688` |
| TARGET-SCORER-LST-IGNORES-LONGITUDE | Hour angle computed from the UTC clock hour, ignoring observer longitude and the sidereal offset, and never using stored latitude → HA/time-remaining scores are effectively fabricated | low | correctness | `services/catalog/target_scorer.py:487`,`:187` |
| ALERTS-HTML-EMAIL-INJECTION | `_format_email_html` interpolates `alert.message` and every `alert.data` key/value into the HTML email body unescaped → untrusted content (CNEOS/AMS fireball fields, mount error strings, target names) is injected raw | medium | security | `services/alerts/alert_manager.py:715`,`:701` |
| ALERTS-EMAIL-SUBJECT-HEADER-INJECTION | Subject header built by f-string from `alert.source`/`alert.message` with no CRLF sanitization → possible SMTP header injection | low `[suspected]` | security | `services/alerts/alert_manager.py:641` |
| ALERTS-TEMPLATE-FORMAT-KEYERROR | `raise_from_template` does `template['message'].format(**kwargs)` — a missing placeholder raises an uncaught `KeyError` | low | correctness | `services/alerts/alert_manager.py:1122` |
| MSE-10 | `EncoderBridge.connect()` leaves the serial handle open (and `_serial` set) when the post-open status check fails → leaked serial device | low | correctness | `services/encoder/encoder_bridge.py:107`,`:108` |

**Defensive note:** these are correctness bugs in *individually real* code — the drivers do talk to hardware; they just mishandle edge cases and errors. None is reachable in the current runtime, but each becomes live the moment the corresponding service is assembled.

---

## 4. Test & verification coverage

### 4.1 Volume vs value

86 test files / ~56k LOC is large, but volume is not coverage. The suite is **bimodal by layer** — and the deepen pass sharpened this into an important correction of a pass-1 claim. `[confirmed]`

**Correction to pass 1:** the statement "safety-critical modules have strong behavioral tests" is **true only at the unit layer** (a full re-read confirmed CONFIRMED-unit / REFUTED-integration+e2e):

- **Genuinely behavioral** (would fail if the implementation were gutted): the safety-critical *unit* tests. Watchdog fail-safe, dual-rain voting (SAFE-002), safety cancellation ordering, and interlock tests import and exercise real implementations and assert computed reasons/state (`tests/unit/test_safe_004_watchdog_failsafe.py:150`, `tests/integration/test_safety_cancellation.py:563`).
- **The entire `tests/e2e/` tier is mock theater.** All six e2e files (`test_emergency_shutdown`, `test_safety_veto`, `test_goto_object`, `test_park_unpark`, `test_session_flow`, `test_weather_response`) import **zero production code** — each builds `unittest.mock.Mock()` objects, puts the control-flow logic *inside the test body*, and asserts on the mocks it just configured. **They would pass against an empty codebase** (`tests/e2e/test_emergency_shutdown.py:11`,`:84`, `tests/e2e/test_safety_veto.py:53`). The voice→tool→service path pass 1 flagged as unwired is not tested here at all.
- **Two of three safety *integration* suites are vacuous:** `tests/integration/test_safety_mount.py` and `tests/integration/test_safety_enclosure.py` mock **both** sides and embed the decision logic in the test body, importing no `nightwatch`/`services` module (`tests/integration/test_safety_mount.py:85`,`:206`, `tests/integration/test_safety_enclosure.py:103`). The "e2e" pipeline tests likewise patch `VoicePipeline.__init__` to a no-op and call a fake executor (`tests/integration/test_voice_pipeline_e2e.py:267`,`:276`); `tests/integration/test_orchestrator_services.py:499` hand-scripts the park/close instead of invoking the orchestrator's wiring.
- **The one test of base `SafetyMonitor` evaluation logic is dead.** `tests/unit/test_safety_monitor.py:15` (37 tests, 550 lines — thresholds, hysteresis, rain-holdoff, altitude, power) hardcodes `sys.path.insert(0, "/workspaces/NIGHTWATCH/…")` then `from monitor import …`; `/workspaces` doesn't exist off Codespaces, so it fails collection. **Consequence: the base safety-evaluation state machine is effectively unexercised** — only the SAFE-002 rain-voting slice uses the correct import.
- **Weak / vacuous elsewhere**: an estimated **30–40% of sampled test functions** assert only `is not None` / `isinstance` / `callable` / dict-key-present / `enum.value == "literal"`, concentrated in `tests/unit/test_ai_services.py` (~85% weak; `:185`,`:448`) and `tests/unit/test_telescope_tools.py` (~55–60% weak; `:364`,`:464`). `[inferred]` on percentages (sample-based).
- **Permissive safety contract codified in a test:** `tests/unit/test_emergency_response.py:512` asserts `emergency_park_and_close()` returns `True` with **no** mount and **no** roof wired ("Should return True since no mount/roof to fail") — success with nothing actually secured.
- **Device layer skips by default:** `tests/integration/test_device_layer.py:62` sets a module-level `skipif(not is_alpaca_available())`, so the real Alpaca device-layer suite provides zero coverage on a plain checkout / CI without the simulator.

### 4.2 CI is decorative `[confirmed]`

No CI job can turn the workflow red on a test/lint/type failure:

- Unit tests: `pytest … 2>/dev/null || echo "Tests completed"` (`.github/workflows/ci.yml:55`) — discards stderr *and* masks the exit code; with `-x`, one broken import aborts the run yet stays green.
- Coverage "80% threshold": warning-only, `continue-on-error` (`:79`).
- Lint: `ruff … || true` (`:190`); mypy: `… || echo "::warning::"` + `continue-on-error` (`:228`,`:237`).
- Integration/e2e/security jobs: all `continue-on-error: true` (`:99`,`:340`,`:487`).

A green badge means the YAML parsed and files exist (`docs-validation` is a file-existence check). `release.yml` has never run — there are **no git tags** (§6).

**Refinement (observed on PR #90's own run):** there is a *third* way an individual check goes red despite the `continue-on-error` armor — a **service-container startup failure**. The `Integration Tests (Full Simulators)` job defines `mock-weather` with `options: --entrypoint "python -m http.server 8080"` (`.github/workflows/ci.yml:346`); Docker treats the whole quoted string as one executable name → `executable file not found in $PATH`, failing the job in ~6 s during *setup*, before the `continue-on-error` step logic applies. So the workflow still can't be failed by test results, but this misconfigured service container shows a red check on every run (including runs that only add documentation). `[confirmed]`

### 4.3 Config divergence

Two pytest configs coexist and `pytest.ini` wins, so the entire `pyproject.toml [tool.pytest.ini_options]` block is dead — including its `--strict-markers` and `timeout=30` (`pytest.ini:22`, `pyproject.toml:262`). Because `--strict-markers` is inert and `pytest.ini`'s marker list registers only `alpaca/indi/slow/hardware`, the `@pytest.mark.e2e` used across `tests/e2e/` is silently accepted and marker typos would not be caught. `[confirmed]`

### 4.4 How much to trust a diff without a human reading it

**Low — and narrower than pass 1 first credited.** With CI unable to fail on test results, whole-file weak/mock-theater tiers (all of `tests/e2e/`, two of three safety-integration suites), and the *only* base-`SafetyMonitor` evaluation test dead on checkout, an agent could make a broad change, see green, and ship a regression. The genuine protection is narrower than "the safety subsystem": it is the safety-critical **unit** tests (watchdog fail-safe, rain-voting, cancellation ordering, interlock) *when run locally with a real, non-`-x`, non-swallowed invocation*. Distrust the integration/e2e tiers entirely (they assert on mocks), and distrust base safety-evaluation coverage until `tests/unit/test_safety_monitor.py`'s import is fixed. Everywhere else, distrust until §7's assembly + real integration test exists.

### 4.5 Runtime verification (observed behavior) `[confirmed by execution]`

Everything above §4.5 is static analysis. To test the load-bearing claims empirically, the repo was built in a throwaway `uv sync` virtualenv (Python 3.11.15) and run. This produced one finding static analysis had missed, and turned several "read" claims into "observed."

- **NEW — the application entry point crashes on startup, every time.** `[confirmed by execution]` `python -m nightwatch.main` (and the `nightwatch` console script) aborts with `TypeError: setup_logging() got an unexpected keyword argument 'level'` before doing anything. `main()` calls `setup_logging(level=…)` at `nightwatch/main.py:308` and `:325`, but the function's parameter is `log_level` (`nightwatch/logging_config.py:185`). **Every invocation except `--version` dies here** — `--dry-run`, `--check-health`, `--simulator`, and normal start all hit it, so the process never even reaches the (empty) service registry of §3.1. Severity **high**, `reachable-in-running-system`. mypy flags the same call (`nightwatch/main.py:325`) — but CI swallows it (below). *This means the system is more broken than pass 1 concluded: it isn't "starts empty," it's "doesn't start."*
- **The phantom import fails at runtime, as predicted.** `import nightwatch.telescope_tools` → `ModuleNotFoundError: No module named 'nightwatch.telescope_tools'` (§3.1, §3.2 confirmed by execution).
- **A default `uv sync --frozen` installs only 7 packages** (pydantic, pyyaml + the package). The service code can't import on it — `aiohttp`, `serial`, `skyfield` all `ModuleNotFound` (the deps are optional extras). Confirms the §2 install story.
- **The four undeclared deps are genuinely absent.** After `uv sync --extra services --extra dev`, `llama_cpp`, `anthropic`, `openai`, and `RPi` all still raise `ModuleNotFoundError` — they are declared in no manifest (§2.1 confirmed by execution).
- **The numpy conflict is real and breaks a dependency.** `uv.lock` resolves **numpy 2.4.6** (vs the `~=1.26`/`<2.0` pin at `voice/requirements.txt:13`); numpy 2.x breaks the astropy import chain, so `tests/unit/test_plate_solver.py` fails at collection (§2.2 confirmed by execution).
- **The dead safety test is dead, observed.** `tests/unit/test_safety_monitor.py` fails collection with `ModuleNotFoundError: No module named 'monitor'` (the `/workspaces` path) — the only base-`SafetyMonitor` coverage does not run (§4.1 confirmed by execution).
- **The safety *unit* tests really do pass.** `test_safe_004_watchdog_failsafe.py` + `test_safety_cancellation.py` → **23 passed**. The "behavioral safety unit tests" credit (§4.1) holds up under execution.
- **The e2e tier runs but is not even all-green:** **73 passed, 1 failed** (`test_session_flow.py::test_session_with_weather_interruption`) — self-contained mock logic that imports no production code (§4.1).
- **CI-decorative, proven by numbers.** `ruff check` reports **2,675 errors** under the CI's own `--ignore=E501,F401,F841` filter (3,866 raw); `mypy nightwatch/` reports **160 errors** (including the startup-crash call). CI runs both as `… || true` / `… || echo "::warning::"` with `continue-on-error`, so all 2,835+ real findings are swallowed and the badge stays green (§4.2 confirmed by execution).

**Net:** running the code strengthened the audit rather than contradicting it, and surfaced the single most consequential defect in the repository — the entry point does not start. It is a two-line fix (`level=` → `log_level=`), but nothing that depends on the process running (the whole system) can work until it lands.

---

## 5. Documentation & onboarding

There is a *lot* of documentation (25 files in `docs/`, plus a 53 KB `NIGHTWATCH_Build_Package.md` founding brief and a 107 KB machine-execution plan). The problem is not quantity — it is that **the docs describe a project that diverges from the code**, so a new engineer or agent following them hits walls. `[confirmed]`

- **The very first command fails.** `README.md:32` and `docs/QUICKSTART.md:61,87` instruct `python -m nightwatch.cli --simulate` — there is no `nightwatch/cli.py` and no `--simulate` flag (the real entry is `nightwatch.main --simulator`). Onboarding breaks at step one.
- **Release fiction.** `RELEASE_v0.1.0.md:3`, `CHANGELOG.md:45`, and `ROADMAP.md:7` date "v0.1.0" to **January 2024**, but the whole project is 2026 (ralph-loop `started_at: 2026-01-20`). There are no git tags, so the "released" v0.1.0 was never published (§6).
- **Counts disagree.** README says "14 observatory microservices" (`README.md:114`), the master plan says "13 core" (`docs/NIGHTWATCH_V0.1_PLAN.md:11`), the POS workflow says "21 domain services" (`pos/opus48-capability-review.workflow.mjs:43`); the actual count is **20**.
- **Config templates diverge — and the installer's is worse than pass 1 thought.** The Pydantic-accurate `nightwatch.yaml.example` disagrees with the `install.sh` heredoc, whose divergence is not limited to the safety block: the generated config uses key names that match no `NightwatchConfig` field across **weather, safety, voice, and LLM**, plus an entire `logging:` section with no model (`deploy/scripts/install.sh:338`,`:363`,`:367`). With `extra="ignore"`, all of it is silently discarded and defaults are used — an operator who edits the installed config to tighten safety or point at a different LLM gets no effect and no warning. `[confirmed]`
- **Silently ignored config.** `nightwatch.yaml.example:220` documents a full `meteor:` block, but `config.py` (`:865`) has no `MeteorConfig` and `extra="ignore"` drops it entirely; the service uses an unrelated in-module dataclass never populated from YAML. A systematic per-section check confirms `meteor:` is the **only** example section lacking a model. `[confirmed]`
- **The real backlog lives outside the repo.** The task IDs in commit messages (HWS-/SAFE-/ARCH-/VOX-/DEP-) and the "Risk #N" register reference `CLAUDE.md` — which is **not tracked** (`git ls-files` → none) — and `~/.claude/plans/*.md` on the author's machine (`pos/opus48-capability-review.workflow.mjs` hardcodes `/Users/timhennessey/…`). The design intent is not auditable from the repo alone.

**Verdict:** a new agent session with no prior context could learn the *shape* of the system from the (excellent, voluminous) prose, but could **not get it running** from the written instructions — only by reading the code and discovering the assembly gap firsthand. The one thing that would most help onboarding — an honest "it doesn't run end-to-end yet; here's the entry point and what's missing" — is exactly what the docs omit.

---

## 6. History & dead weight

### 6.1 Shape `[confirmed]`

- **59 commits**, first `2026-01-20` (`4ffc2d7`, labeled "Step 118" but actually a big-bang import of the entire scaffold), last `2026-06-15` (`7fa94a2`, pos docs).
- **Three eras, with a gap:** 2026-01 = 31 commits (autonomous "Step NNN" build-out), **2026-02→04 = 0**, 2026-05 = 26 (task-ID hardening via git worktrees), 2026-06 = 2 (pos capability-review docs only).
- **Solo, ~100% AI-authored.** One human (`timothyehennessey@gmail.com`) under two git identities (`THOClabs` 31, `Tim Hennessey` 28). Co-authored-by trailers: Claude Opus 4.5 ×31, Opus 4.7 (1M) ×25, Opus 4.8 (1M) ×2. Built by an autonomous loop (`.claude/ralph-loop.local.md`, `iteration: 5`, `max_iterations: 500`).
- **No git tags** despite a tag-triggered `release.yml` and a `RELEASE_v0.1.0.md`.

### 6.2 Actively maintained vs frozen vs orphaned `[confirmed]`

**249 of 298 files are single-commit** — untouched since the January import. Only **49** were ever revisited. Maintenance energy concentrated on ~15 files:

- Most-revisited: `orchestrator.py` (10 commits), `test_llm_client.py` (6), `services/nlp/__init__.py` (6), `test_camera_service.py` (5), `safety_monitor/monitor.py` (5), `camera/asi_camera.py` (5), `llm_client.py` (5).
- The **May hardening pass touched only 7 of 20 service subsystems** (astrometry, camera, focus, guiding, mount_control, safety_monitor, weather). The other 13 (alpaca, catalog, enclosure, encoder, ephemeris, indi, nlp, power, scheduling, simulators, services/voice, + alerts, meteor_tracking) are frozen at import.
- **Whole top-level trees frozen at 2026-01-20:** `firmware/`, `deploy/`, `bin/`, `examples/`, `.github/`, `.claude/`; `docs/` frozen at 2026-01-28.

### 6.3 Notable freezes and orphans

- **The roof actuator was never revisited.** `services/enclosure/roof_controller.py` (1668 LOC — the code that physically moves the roof) is **single-commit**. The SAFE-001 commit "EMERGENCY_CLOSE actually closes roof" (`b6565eb`) touched `cancellation.py`, `orchestrator.py`, `safety_monitor/monitor.py`, and a test — **not** the actuator. This is why the §3.3 close-path bugs (missing `get_state`, un-forced close) survive. `[confirmed]`
- **The v0.5 AI cluster is orphaned.** `services/scheduling` + `services/nlp` (~5.5k LOC, plus `AIServices`) have consumers only in `services/__init__.py`, `services/ai_services.py` (self), `examples/v05_ai_demo.py`, and `tests/unit/test_ai_services.py` — never in the production path. `nightwatch/__init__.py:51` even has a commented-out `# from services.nlp import (`. `[confirmed]`
- **Stalled experiments / vestigial:** the entire `deploy/` tree ships broken entry points (§3.5, §5) and was never revisited; `firmware/onstepx_config/Config.h` is a drop-in header with no build system; `pos/` is a design-methodology apparatus (12 simulated expert personas + a Claude Code Workflow `.mjs` with hardcoded author-machine paths) rather than product code.
- **Function-level dead code and a phantom symbol (deepen pass) `[confirmed]`:** the deepen pass confirmed `services/nlp` and `services/scheduling` are dead on the production path (firm verdict — nothing outside the never-instantiated `AIServices` facade, an example, and tests imports them: `nightwatch/main.py:247`, `nightwatch/__init__.py:51`). It also found the whole `voice` package is imported only by tests, and the symbol the pipeline actually wants — `get_tool_definitions` — is **defined nowhere in the repo** (`voice/tools/__init__.py:8`), so even correcting the phantom module path wouldn't resolve it. And a latent constant collision: `OnStepXExtended` defines `CMD_PEC_RECORD` and `CMD_PEC_READ_EEPROM` both as `"$QZR"` (`services/mount_control/onstepx_extended.py:73`,`:75`) — the read-EEPROM constant is currently unreferenced (dead), but the collision would make any future read trigger a PEC record.

---

## 7. Expansion opportunities

This is the part that matters most, and it has an unusual starting condition: **the biggest latent asset — ~28k LOC of real, individually-tested hardware drivers — has never been assembled into a running system.** So the highest-leverage move is not adding features; it is *turning on what already exists*. Confidence tags below are the panel's estimate of whether the opportunity is correctly scoped; the findings each rests on are `[confirmed]` (§1–§6).

**The keystone (do this first): a `config → registry` service-assembly factory.** Everything else depends on or is amplified by it. Add a `nightwatch/factory.py` that maps config to concrete service instances (the `Literal` type discriminators on `MountConfig`/`CameraConfig`/`WeatherConfig`/`EnclosureConfig` and the orchestrator's existing `register_*` methods already define the contract), replace the bare `Orchestrator(config)` at `nightwatch/main.py:247` with the populated build, repoint the phantom import (`nightwatch/voice_pipeline.py:2086`) at the real 90-handler tool layer, and lock it in with one golden simulator integration test. *Effort: ~1 week for a simulator-only vertical slice, 3–6 weeks for all 20 slots with real backends. Confidence: high.* This converts a dormant parts-bin into a system that runs (in simulation) end-to-end. **This is the single biggest opportunity in the repository.**

### 7.1 Quick wins (days, low risk, clear payoff)

Mostly "make the existing real code run, and make the repo honest." Note QW7's safety fixes have no *runtime* effect until the keystone assembles the system — but they should land first so the safety baseline is correct the instant it does.

| Quick win | What it takes | Unlocks | Motivating finding | Effort · Conf |
|---|---|---|---|---|
| Declare undeclared deps & reconcile manifests | Add `llama-cpp-python` (optional extra), `anthropic`, `openai`, platform-gated `RPi.GPIO`; fix numpy 1.x-pin-vs-2.x-resolved; drop-or-lock `pyindi-client`/`alpyca`; replace abandoned `webrtcvad`; verify clean-env install | A fresh checkout installs and imports without hidden `ModuleNotFoundError` — precondition for the keystone and demo to be reproducible off the author's box | §2.1, §2.2 | 1–2 d · high |
| Kill the CI escape hatches (staged) | Remove `2>/dev/null \|\| echo` and `\|\| true`/`continue-on-error`; start with hard-failing unit tests + an import smoke test, then ruff, then mypy | Green CI becomes a real signal; regressions actually turn it red | §4.2 | 1–2 d · high |
| Fix the broken quickstart & make README truthful | Correct `nightwatch.cli --simulate` → `nightwatch.main --simulator`; fix 2024 dates; converge the 3 config templates; correct service counts to 20; resolve the license/classifier contradiction; add an honest "components real, assembly in progress" status | First-run success instead of an immediate error; docs that match reality | §5, §2.3 | 1 d · high |
| Make the systemd units boot & stop | `Type=simple`, drop `WatchdogSec` (until the real watchdog lands), fix `ExecStop` off `--shutdown`; repoint the wyoming unit at the real `voice/wyoming` servers; drop the unneeded `CAP_SYS_RAWIO` | The documented deploy path starts/stops cleanly with a smaller privilege footprint | §3.5 (EP-02/03/04), PRIV-002 | 1–2 d · high |
| Fix the container health signal | Point Docker `HEALTHCHECK` at the already-working `nightwatch.main --check-health` (drives the existing `HealthChecker`) instead of curling an unserved `:8080`. Deliberately *not* standing up a web server (avoids new ingress) | Containers report healthy; existing health path gets a consumer; no new attack surface | §3.5 (EP-06) | <1 d · high |
| Release hygiene | Delete `pytest.ini` (stop shadowing pyproject); fix the `/workspaces/`-hardcoded safety test; pick one version string; create the `v0.1.0` tag `release.yml` assumes — *after* the dep+CI wins land | Consistent test collection; a release workflow that can fire; honest versioning | §4.3, §6.1 | 0.5–1 d · high |
| Batch the test-guarded safety one-liners | Fix the located defects behind existing behavioral tests: interlock `0.0` falsy; `emergency_close()` pass `emergency=True`; replace the non-existent `roof.get_state()` poll; add the missing `await` on `_close_enclosure_safely()` | Safety layer behaves as designed the instant assembly lands | §3.3 | 1–2 d · high |
| Restore base-safety-monitor coverage | Fix the `/workspaces/`-hardcoded import in `tests/unit/test_safety_monitor.py` so its 37 base-`SafetyMonitor` evaluation tests actually run again (they're the only coverage of thresholds/hysteresis/rain-holdoff/altitude) | The core safety state machine goes from *untested-on-checkout* to tested — the cheapest large coverage gain in the repo | §4.1 (TI-DEAD-MONITOR) | <1 d · high |
| Batch the cheap driver-correctness fixes | Fix the located, high-value bugs that produce plausible-but-wrong output: Alpaca constructor arg shape (all 4 adapters), declination-sign for targets within 1° south, `get_driver_status` fault-masking, the mislabeled/duplicate catalog entries, and non-atomic `SuccessTracker` writes (temp+rename) | The "crown jewel" drivers stop silently returning wrong coordinates / masking faults / losing history once assembled | §3.8 | 2–4 d · high |

### 7.2 Substantial builds (weeks, real design, high payoff)

1. **KEYSTONE — assembly factory + real tool layer + golden simulator integration test** (the item above, fully built out across all 20 service slots). *3–6 wks · high.* Turns ~28k LOC of orphaned drivers into a runnable system and gives the LLM ~90 tools instead of none. — *§3.1, §3.2*
2. **Safety-correctness + live-watchdog workstream behind a sim/HIL rig.** One workstream with a simulated-hardware harness that asserts the roof physically reaches "closed": fix the stop-motor race, make emergency stop de-energize relays, make daylight/ephemeris checks fail *closed*, call `WatchdogManager.start()` and drive heartbeats, add `sd_notify`. **Fold in the async-blocking class (§3.7)** — move blocking serial/socket/inference off the event loop (via `asyncio.to_thread`, as `sync_to_coordinates` already does) so a stalled device can't freeze the safety monitor, and retain the fire-and-forget capture task so it can't be GC'd or lose exceptions. *3–5 wks · high.* Makes the mature 3-layer safety design actually protect an unattended open-roof telescope. — *§3.3, §3.7, §4.1*
3. **Confirmation gate for destructive commands.** Build the state machine that finally calls the existing-but-unused `requires_confirmation()`/`get_confirmation_prompt()`; classify tool destructiveness, require an affirmative response, default to DENY on timeout, support `--yes` for unattended mode. *2–3 wks · high.* Without it, assembly becomes unconfirmed autonomous roof/mount actuation. — *§3.2 (VOX-NO-CONFIRM-GATE)*
4. **Security hardening: authenticate ingress + secrets + config-schema + least-privilege deploy.** Add token/mTLS auth to the vendored Wyoming protocol, default-bind loopback, bound the audio buffer, sanitize errors; replace PDU `admin/admin`-over-cleartext and SNMP `private`; validate Alpaca UDP responders; real secrets provider; make unknown safety-config keys *fail* instead of silently dropping; remove the privileged container. *4–6 wks · high.* Closes the "LAN foothold = full control of an open-roof telescope" path. — *§3.4, §3.5*
5. **Test-integrity workstream: mutation gates on safety modules + rebuild the mock-theater tiers.** Add coverage + mutation testing scoped to the safety-critical modules to *prove* the behavioral tests catch regressions; **replace the entire `tests/e2e/` tier and the two vacuous safety-integration suites** (which import zero production code) with tests that actually assemble services and exercise the real path; rewrite the ~85%-weak `test_ai_services` and ~55–60%-weak `test_telescope_tools`. *3–5 wks · high.* Turns the suite into a real safety net for a solo/agent-driven workflow. — *§4.1*
6. **Local-first egress governance.** A data-governance layer around `LLMClient`: opt-in egress gate (default offline), a redaction pass stripping location/telemetry before any cloud call, an allowlist, and a tamper-evident audit log. *2–3 wks · medium.* Makes the "local-first, no cloud" claim true or the exception explicit. (Subsumed by RI-2 if the cloud path is deleted outright.) — *§3.2 (VOX-CLOUD-EXFIL)*

### 7.3 Reimaginings (what this would be if started today)

Where the 2026 capability gap *is* the opportunity — tools, local models, and agent patterns that didn't exist when the bulk was scaffolded.

1. **MCP-native driver plane.** Instead of finishing hand-rolled DI glue, expose each `services/` subsystem as an MCP tool server behind the interfaces that already exist (14 typed `ServiceProtocol`s; `Connectable`/`Slewable`/`Parkable` in `types.py`). A thin agent loop consumes the driver catalog directly; assembly becomes a declarative manifest, and each driver is independently launchable, testable, and reusable by *any* MCP client. *Months · high.* Turns "assembly missing" from a build task into a config task and gives the driver asset value independent of the monolith. — *§3.1, §1.4*
2. **DGX-class local model as autonomous night planner, retiring the cloud fallback.** The `BaseLLMClient` ABC already abstracts backends (today a 3B model). Swap in a 2026 30B+ model that fits DGX Spark and wire it to the *orphaned* `services/scheduling` + `services/nlp` brain (weather-aware scheduler, success tracker, session narrator) so it plans and executes a night. *Months · medium.* Genuine on-box autonomous planning *and* deletes the egress problem by deleting the egress. — *§6.3, §3.2*
3. **Digital-twin shadow observatory + adversarial safety-verification agent.** Assemble the full stack against the existing ~2,900-LOC simulator suite as a digital twin, then run a testing agent that adversarially fuzzes failure scenarios (mid-open roof, rain during slew, sun-up, watchdog starvation) and *requires proof the roof closes* before any code touches real GPIO. *Months · high.* Every safety defect becomes a reproducible simulated gate — the agent-era evolution of SB-2's HIL rig. — *§3.3, §1.5*
4. **Adversarial guardian agent: a second local model gating every destructive action.** A dedicated safety-supervisor model between planner and executor that dry-runs proposed actions against the digital twin and checks policy-as-code before hardware sees them; cheap 2026 local inference makes a second model affordable. (Keep the hard real-time interlocks deterministic — the model is defense-in-depth, not the primary veto.) *Weeks–months · high.* — *§3.2, §3.6*
5. **Local vision-model frame QA + auto-narrated night logs.** `frame_analyzer.py` triages frames by fixed statistical thresholds today; add a 2026 local vision model for richer judgment (clouds, satellite trails, dew, gradients, focus drift) feeding the scheduler, plus a narrated night log — keeping the deterministic CV as a fast pre-filter. *Weeks · medium.* Exactly the judgment where a vision model beats hand-set thresholds. — *§1.2 (`services/camera/frame_analyzer.py`)*
6. **Multi-station federation for fireball triangulation.** A coordinator agent federates multiple NIGHTWATCH nodes for multi-station triangulation (inherently ≥2 sites), shared sky coverage, and transient follow-up; the `services/meteor_tracking` stack already assumes the multi-station framing. Hard prerequisite: the SB-4 ingress authentication. *Months · medium.* Scientific value a single site can't produce. — *§1.2, §3.4*

---

## 8. Open questions

Ranked; each notes what would resolve it.

1. **Is the assembly gap intentional (a parts-first strategy) or an incomplete build the loop never reached?** `[suspected]` The ralph-loop plan and `CLAUDE.md` are outside the repo, so intent is unknowable from code. *Resolves with:* the external plan files, or your direct answer.
2. **Has this system ever driven real hardware, or only simulators and tests?** `[suspected]` Every driver has a mock fallback and there's no runtime assembly, suggesting sim-only, but that's not provable from the tree. *Resolves with:* session logs / observation logs from a real run, or your answer.
3. **Is the CC BY-NC-SA 4.0 + "Proprietary" classifier combination deliberate, and is commercial/redistribution ever intended?** `[confirmed]` the contradiction; intent unknown. *Resolves with:* your licensing intent.
4. **Which deploy target is canonical — a single DGX Spark host, or a split DGX-plus-Pi topology?** `[suspected]` The artifacts assume both (CUDA + GPIO on one host). *Resolves with:* the intended hardware topology.
5. **Should the two tool layers converge, and on which one?** The 90-handler `voice/tools/telescope_tools.py` is richer and confirmation-aware; the 30-handler `nightwatch/tool_executor.py` is what the pipeline calls. *Resolves with:* your preference (drives a §7 quick win).
6. **Are the cloud LLM fallbacks acceptable given the "local-first, no cloud" principle,** or should they be removed/gated to satisfy the stated privacy goal (VOX-CLOUD-EXFIL)? *Resolves with:* your policy call.
7. **Is `pos/` (Panel of Specialists) meant to remain in the product repo** as living methodology, or is it archival? It's ~unmaintained relative to code. *Resolves with:* your answer.

---

## Appendix A — Methodology

Read-only audit at commit `7fa94a2`, in two passes.

**Pass 1** (69 findings): (1) three parallel exploration passes (architecture; infrastructure/tests/docs; git/deps). (2) A 10-agent evidence wave via deterministic multi-agent orchestration — five security agents grouped by trust boundary (actuation/safety, LLM/voice, subprocess/filesystem, network, secrets/deploy), an adversarial refuter tasked to *disprove* the assembly-gap thesis, an entry-point reality checker, a test-quality sampler, and a dependency verifier — each emitting findings under a schema that **required a verbatim source snippet per citation**. (3) A mechanical verifier re-read every citation (`sed` + normalized substring match): 174 evidence items → 168 exact, 5 within ±8 lines, 1 corrected (`ci.yml` swallow line is `:55`). (4) Independent second read of every high-severity security finding, which downgraded most safety findings to *only-if-assembled* and confirmed `privileged: true` and CI-decorative as genuine. (5) A three-stance expansion panel (ship-it / harden-it / reimagine-it) plus a scoring judge for §7.

**Pass 2 — deepen** (52 findings, §3.7/§3.8 and the §4 corrections): six agents covering the ~13 subsystems pass 1 only characterized (mount/serial/encoder, device-I/O + coordinate math, catalog/meteor/alerts/orphaned-AI), an **async-correctness bug-class hunt** seeded by the pass-1 un-awaited-close finding, a **broken-wiring / config-completeness sweep**, and a **full (not sampled) test-integrity grade** — same schema, same verbatim-snippet requirement. Mechanical verification: 126 evidence items → 111 exact, 7 within ±8 lines, 8 stitched multi-line snippets re-confirmed by hand. New critical/high findings got an independent cross-read (which downgraded the Alpaca-constructor and mount-status-blocking findings and confirmed the e2e/integration mock-theater as real). Pass 2 also **corrected a pass-1 over-claim**: "safety-critical modules have strong behavioral tests" holds only at the unit layer.

Confidence tags follow the legend at the top; reachability tags account for the empty-registry runtime throughout.

## Appendix B — Confidence & severity rubric

- **confirmed** = cited lines read and quoted verbatim; mechanically snippet-verified.
- **inferred** = strong indirect evidence (e.g. upstream-abandonment dates, sample-based percentages).
- **suspected** = plausible, not verifiable from the code alone (flagged as open questions).
- Security **severity** reflects real-world consequence **after** applying the reachability tag: a defect in code that cannot execute in the shipped system is not scored as a live high.
