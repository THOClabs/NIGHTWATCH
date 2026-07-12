# NIGHTWATCH Security Audit (L4 Cross-Cutting)

**Auditor:** L4 Security Auditor (the "column" cutting across every domain "row")
**Date:** 2026-07-12
**Repository:** /home/user/NIGHTWATCH
**Method:** Every analyst "Security observations" flag was re-verified against source before entering
this report. Independent sweeps run per contract: secrets, injection surfaces, authN/authZ, trust
boundaries, dependency audit (`pip-audit` against the exact pins in `uv.lock`), filesystem/network
hygiene. Read-only toward source; the only file written is this one.

## Scope and posture note (read this first)

Four of the five domain analysts independently concluded that NIGHTWATCH's *production entry point
is currently non-functional or unwired*: `python -m nightwatch.main` crashes before config validation
(a `setup_logging()` kwarg bug), and the `Orchestrator` never constructs `LLMClient`, `VoicePipeline`,
the Wyoming servers, or any concrete hardware service. I confirmed each of these independently.

This creates a two-tier severity problem that I have handled explicitly rather than hand-waving:

- **Tier A — exploitable/impactful *as written or as soon as the entry point is fixed*.** These are
  ranked on their real severity. The entry-point bug is a one-line fix (see H1); once it lands, the
  latent items become live. Treating "it's not wired yet" as a mitigating control would be a mistake —
  the code is one trivial fix away from running, and the systemd/docker units are written to run it.
- **Tier B — genuinely dormant** (code with no production path AND non-trivial to reach). Down-ranked
  and flagged as dormant, but reported because the repo intends to wire them up (per commit history
  and the deployment artifacts).

The single most alarming property of this codebase from a safety-security standpoint: **the physical
fail-safes that protect a telescope and its enclosure from weather do not work**, and the failures are
masked by broad `except Exception` swallowing plus test doubles that patch out the broken code path.
For an autonomous observatory, "fail to close the roof in rain" is the security-equivalent of a
disabled emergency brake. See C1.

---

## Severity counts

| Severity | Count |
|---|---|
| Critical | 1 |
| High | 4 |
| Medium | 6 |
| Low | 5 |
| Info | 4 |

---

## CRITICAL

### C1. Emergency roof-close fails to move the roof (AttributeError swallowed) — physical fail-safe defeated
**File:** `services/enclosure/roof_controller.py:848` (evaluated during `close(emergency=True)` →
`_run_motor`), `__init__` at `:484-531`, setter-only-source at `:1051-1061`
**Evidence:**
```python
# __init__ (484-531): self._gpio is NEVER assigned. Every other attribute is.
# _run_motor (848):
    if self._gpio:                       # AttributeError: no attribute '_gpio'
        current = self._gpio.read_motor_current()
# close() (737-740) swallows it:
    except Exception as e:
        self._state = RoofState.ERROR
        logger.error(f"Roof close failed: {e}")
        return False
```
`self._gpio` is only ever created as a side effect of `setup_rain_sensor_interrupt()`
(`roof_controller.py:1051`, assigns at `:1061`), and grep confirms that method has **zero call sites**
anywhere in the repo. So on any `RoofController` that has not had that method manually invoked,
`_run_motor` raises `AttributeError` on first reference, `close()`/`open()` catch it, set state to
`ERROR`, and return `False` — the motor is never commanded.
**Why it matters:** This is the terminal step of the entire weather-safety chain. Data flow (verified):
`SafetyMonitor.evaluate()` correctly detects rain/emergency → `execute_action(EMERGENCY_CLOSE)`
(`monitor.py:1445`) → `_close_enclosure_safely()` (`monitor.py:1515`) → `self.enclosure.close()`. The
close call returns `False` and `_close_enclosure_safely` swallows/logs it (`monitor.py:1534-1537`). The
observatory correctly decides "close the roof now" and then silently does not. This directly nullifies
the SAFE-001 commit ("EMERGENCY_CLOSE actually closes roof, Risk #2"). Confirmed reproducible by the
Astronomy/Hardware analyst live; I confirmed the code paths statically end-to-end.
**Why not merely dormant:** the roof controller is safety infrastructure that the deployment artifacts
(`deploy/systemd/nightwatch.service`, `docker-compose.prod.yml`) are built to run. The bug is masked
from tests because `tests/unit/test_roof_controller.py`'s fixture monkey-patches `_run_motor` with a
fake that never touches `self._gpio`. That masking is why it shipped.
**Smallest credible fix:** initialize the backend in the constructor —
`self._gpio: Optional[GPIOInterface] = None` at minimum (removes the `AttributeError`; `if self._gpio:`
then cleanly skips current-monitoring), and for real hardware construct the `GPIOInterface` in
`__init__`/`connect()` rather than only inside `setup_rain_sensor_interrupt()`. Add a test that drives
`close(emergency=True)` **without** patching `_run_motor`.

---

## HIGH

### H1. CLI entry point crashes before config validation (`setup_logging(level=...)`)
**File:** `nightwatch/main.py:308` and `:325`; signature at `nightwatch/logging_config.py:185-191`
**Evidence:** `main.py` calls `setup_logging(level=log_level)` and `setup_logging(level=config.log_level)`,
but the parameter is named `log_level`, not `level`. Confirmed:
```
$ python3 -m nightwatch.main --dry-run
TypeError: setup_logging() got an unexpected keyword argument 'level'
```
**Why it matters (security-relevant):** every documented launch path (`nightwatch` CLI, `bin/nightwatch`,
`python -m nightwatch.main`, and the `ExecStart=` in `deploy/systemd/nightwatch.service:34`) crashes
before configuration is validated. Any claim that "the system enforces safety/allowlist X at startup" is
currently unverifiable — nothing starts. It also means the entire startup security posture (config
allowlist gate, service wiring) is untested against the real entry point (`main()` has zero unit
coverage; `tests/integration/test_startup.py` imports `async_main` directly, bypassing `main()`).
**Confirming the analyst flag:** Core Orchestration analyst flagged this as Security #1 — **confirmed**.
**Smallest credible fix:** rename the two call-site kwargs to `log_level=...` (or add a `level` alias in
`setup_logging`). Add a smoke test that invokes `main(["--dry-run"])`.

### H2. Known-vulnerable `aiohttp` 3.13.5 pinned in lockfile (11 CVEs)
**File:** `uv.lock` (`aiohttp` pinned `3.13.5`); declared loosely as `aiohttp~=3.9` in
`services/requirements.txt:2` and `pyproject.toml`
**Evidence:** `pip-audit` against the exact `uv.lock` pins reported 11 known vulns in aiohttp 3.13.5:
```
aiohttp 3.13.5  CVE-2026-34993, CVE-2026-47265, CVE-2026-50269, CVE-2026-54273..54280,
                PYSEC-2026-237     Fix in 3.14.0 / 3.14.1
```
**Why it matters:** aiohttp is the outbound HTTP client for every network-sourced safety-relevant feed
in the system — Ecowitt weather gateway (`services/weather/ecowitt.py:144`), PDU power control
(`services/power/power_manager.py:149`), ntfy push, AMS fireball API. These CVEs (request smuggling /
parsing / resource classes in this cluster) sit on the ingress path of data that drives roof/park
decisions. No other package in the 97-package lock tree flagged.
**Smallest credible fix:** bump the constraint to `aiohttp>=3.14.1` and regenerate `uv.lock`; wire
`pip-audit` into CI as a failing gate (it is currently run informational-only per
`00-inventory.md:209`).

### H3. Hardcoded default credentials for real power-control hardware
**File:** `services/power/power_manager.py:50-55` (`PDUConfig`) and `:806-808` (second config class)
**Evidence:**
```python
http_username: str = "admin"
http_password: str = "admin"          # controls mount/camera/computer outlets
snmp_community: str = "private"       # SNMP write community
# ... duplicated at 806-808: pdu_password = "admin", pdu_snmp_community = "private"
```
Used at `_connect_http` (`:150`, `aiohttp.BasicAuth(username, password)` over plaintext `http://`) and
the SNMP path. `port_names` (`:59-64`) maps outlets to `mount`, `camera`, `focuser`, `computer`.
**Why it matters:** if a deployment leaves defaults (plausible — no config surface forces a change, and
the PDU section is off by default so it is easy to forget when enabled), any host on the LAN can cut
power to the mount mid-slew or to the control computer via unauthenticated/weakly-authenticated
plaintext. This is a real integrity/availability risk against safety-critical hardware. These are
*default* values, not committed live secrets, so it is High rather than Critical — but the defaults are
guessable industry defaults, which is the worst kind.
**Confirming the analyst flag:** Astronomy/Hardware analyst Security #4 — **confirmed**.
**Smallest credible fix:** default the credential fields to empty and hard-fail PDU connect if
`pdu_enabled` and no credentials supplied; require them from config/secret, never a working default.
Prefer SNMPv3 or HTTPS where the PDU supports it. Never log the values (currently they are not logged —
good).

### H4. Wyoming STT/TTS servers: unauthenticated, unencrypted, bind `0.0.0.0` by default, unbounded audio buffer
**File:** config defaults `nightwatch/config.py:346-355` (`wyoming_host="0.0.0.0"`,
`wyoming_enabled=True`, port 10300) and `:411-420` (TTS, port 10301); server binds
`stt_server.py:116`; unbounded buffer `stt_server.py:234-238`; protocol has no auth field anywhere in
`voice/wyoming/protocol.py`
**Evidence:**
```python
# config.py: wyoming_enabled default True, wyoming_host default "0.0.0.0"
# stt_server.py:234-238 — every AUDIO_CHUNK appended, no size/duration cap:
    elif message.type == MessageType.AUDIO_CHUNK:
        if session.is_streaming and isinstance(message.data, AudioChunk):
            session.audio_buffer.append(message.data.audio)
```
`deploy/systemd/nightwatch-wyoming.service:40` launches a `voice.wyoming_server` module to expose these
(note: that module does not exist in-tree — see M6 — but the intent to run these on the network is
explicit, and `docker-compose.prod.yml` exposes `10300`).
**Why it matters:** any host that can reach the port can (a) submit audio for GPU/CPU-costly
transcription, (b) request arbitrary speech synthesis, (c) passively read all traffic (no TLS), and
(d) exhaust server memory by opening a stream and never sending `AUDIO_STOP` — trivial DoS, no auth to
gate it. Whisper transcripts are the front of the command pipeline, so an attacker on the LAN who can
inject audio is upstream of tool selection. The Wyoming LAN-trust model is conventional, but nothing
here adds an allowlist/token/mTLS and no caveat sits near the `0.0.0.0`/`enabled=True` defaults.
**Why not merely dormant:** the servers are network-exposed by design and shipped with
`wyoming_enabled=True`; the systemd/compose units are written to run them. The only reason they are not
live today is the unrelated launcher gap (M6).
**Confirming the analyst flags:** Voice/NLP Security #1 (auth/TLS) and #2 (unbounded buffer) —
**both confirmed.**
**Smallest credible fix:** default `wyoming_host` to `127.0.0.1`; add a per-session cap on
`audio_buffer` bytes/duration (reuse `AudioConfig.max_duration` already enforced on the local path,
`whisper_service.py:517-523`) and drop/close the session on exceed; document the LAN-trust assumption
and offer an optional shared-token check.

---

## MEDIUM

### M1. Power-failure safety action is dead-on-arrival (`_action_callback` never assigned)
**File:** `services/safety_monitor/monitor.py:1141-1142`; `execute_action` dispatch at `:1506-1510`
**Evidence:** `handle_power_failure_response()` references `self._action_callback` which is never set in
`__init__` (verified — `__init__` at `:296-339` has no such field, and grep shows no setter). Calling
`execute_action(SafetyAction.POWER_FAILURE)` therefore raises `AttributeError`, which is re-raised at
`:1161` and then swallowed by the outer `except Exception` in `execute_action` (`:1512-1513`). The
detected power-failure never parks the mount or closes the roof through this path.
**Why it matters:** second independent hole in the safety-veto engine, same masking pattern as C1
(broad-except + no end-to-end test). Lower than C1 only because the power-failure branch is one of
several action types and its detection preconditions are narrower than the rain/emergency path.
**Confirming the analyst flag:** Astronomy/Hardware Security #2 — **confirmed.**
**Smallest credible fix:** either add `self._action_callback = None` + a setter and wire it from the
orchestrator, or make `handle_power_failure_response()` perform the park/close directly via
`self.mount`/`self.enclosure` like the other branches do. Add a test exercising
`execute_action(POWER_FAILURE)` with a mock mount+enclosure.

### M2. `SafetyMonitor` invokes async enclosure `close()` without awaiting it
**File:** `services/safety_monitor/monitor.py:1535` (`_close_enclosure_safely`)
**Evidence:**
```python
def _close_enclosure_safely(self, calling_action: str) -> None:   # sync method
    if self.enclosure is None:
        return
    try:
        self.enclosure.close()          # RoofController.close is `async def` (roof_controller.py:690)
    except Exception as e:
        logger.error(...)
```
`RoofController.close()` is a coroutine. Calling it without `await` creates a coroutine object that is
never scheduled (and never awaited), so **even after C1 is fixed**, the emergency close from the
`EMERGENCY_CLOSE` / `LOW_BATTERY_SHUTDOWN` branches would not actually run. A coroutine object is truthy
and raises no exception here, so the swallow-and-log guard does not catch it; you get a
"coroutine was never awaited" runtime warning at best. Note the SAFE-004 watchdog path does this
correctly (`watchdog.py:546`, `result = await self._enclosure.close(emergency=True)`), which highlights
the inconsistency.
**Why it matters:** this is the *second* independent reason the emergency roof close does not fire from
the primary safety loop. C1 and M2 must both be fixed for EMERGENCY_CLOSE to work. Ranked Medium (not
stacked into C1) because it is a distinct defect with a distinct fix, but treat it as part of the same
"roof does not close" remediation.
**Smallest credible fix:** make `_close_enclosure_safely` async and `await self.enclosure.close(...)`,
propagating up through `execute_action` (already async). Pass `emergency=True` to match intent.

### M3. Systemic Protocol/implementation mismatch — `await mount.park()` against a sync `LX200Client`
**File:** `services/mount_control/lx200.py:530,580,585` (sync `stop`/`park`/`unpark`); awaited at
`nightwatch/orchestrator.py:2035, 2366, 2920`; Protocols at `orchestrator.py:871-1135`
**Evidence:** `MountServiceProtocol` requires `async def park()/unpark()`; `LX200Client.park()` etc. are
plain synchronous methods. `await mount.park()` against a real `LX200Client` raises
`TypeError: object bool can't be used in 'await' expression`. Similarly `SafetyMonitor` exposes no
`is_safe` property / `get_unsafe_reasons()` (only a `SafetyStatus` data field), `ASICamera` exposes
`capturing`/`capture_single` not `is_exposing`/`capture()`, `PowerManager` lacks
`on_battery`/`battery_percent`. Grep confirms concrete service constructors (`RoofController(`,
`LX200Client(`, `EcowittClient(`, `PDUClient(`) are invoked only from tests, never from `nightwatch/`.
**Why it matters:** the hardware layer cannot currently be driven from the orchestrator without raising.
This is quality-shaped but has a security consequence: the shutdown/park paths (`orchestrator.py:2035`
in `_safe_shutdown`) would throw against real hardware, so a signal-driven safe shutdown could fail to
park the mount. Medium because production wiring is absent today (Tier B), but it lands on the safety
path the moment wiring is added.
**Confirming the analyst flag:** Astronomy/Hardware Security #3 — **confirmed** (re-verified the
sync/async signatures and the awaited call sites).
**Smallest credible fix:** reconcile the contract — either make `LX200Client` methods `async` (wrapping
blocking socket I/O in `asyncio.to_thread`, as `sync_to_coordinates` already does at `lx200.py:515`), or
adapt them behind an async shim; add a conformance test that checks each concrete service against its
Protocol.

### M4. Ecowitt weather parser fails *open* (reports "dry/comfortable" on malformed safety input)
**File:** `services/weather/ecowitt.py:159-200`
**Evidence:** `_parse_response` defaults missing/garbled fields to benign values —
`temp_f = get_common("0x02", 70.0)`, and `is_raining = rain_rate > 0` where `rain_rate` defaults to `0`.
A partial/garbled JSON payload (comment at `:161` admits "structure varies by firmware version")
produces a fully-valid-looking `WeatherData` marked safe, and `SafetyMonitor.update_weather` wraps it as
`SensorInput(is_valid=True)` with no signal that the parse degraded.
**Why it matters:** this is network-sourced input on the safety boundary (plaintext HTTP, no auth — see
M5) that drives the roof/park decision, and it fails toward "safe to observe" instead of failing closed.
An attacker who can shape or truncate the gateway response (or a firmware quirk) can suppress a rain
signal. The SAFE-002 dual-sensor redundancy that was meant to hedge this is itself unimplemented (no
secondary-rain driver exists; `secondary_rain.py` is data-shape-only), so the primary sensor is the only
line.
**Confirming the analyst flag:** Astronomy/Hardware Security #6 — **confirmed.**
**Smallest credible fix:** treat missing required keys as an invalid reading — return `None`/set
`is_valid=False` so the monitor's staleness/fail-safe logic (which already treats missing as unsafe)
engages, rather than substituting benign defaults for safety-relevant fields (rain, wind, humidity).

### M5. Plaintext HTTP with no integrity/auth on safety-relevant sensor and control feeds
**File:** `services/weather/ecowitt.py:124,146` (`http://{gateway}`); `services/power/power_manager.py:147`
(`http://{host}/api/status`); `services/alpaca/alpaca_client.py:146` (`http://{addr}:{port}/management/...`)
**Evidence:** all device I/O to weather gateway, PDU, and Alpaca management is plaintext `http://` with
no transport auth or response integrity check. Ecowitt/CloudWatcher have no credential at all.
**Why it matters:** on a compromised or shared LAN segment, these feeds (which drive safety decisions and
power control) can be observed or tampered with. Combined with M4 (fail-open parsing) and H3 (default
PDU creds) this is defense-in-depth debt on the exact data that governs the physical hardware. LAN-local
risk profile keeps it Medium.
**Smallest credible fix:** where the hardware supports it, use HTTPS/authenticated endpoints; otherwise
document the LAN-trust boundary explicitly and network-segment these devices. At minimum, sanity-bound
parsed values and reject implausible readings (ties into M4).

### M6. Broken tool-schema wiring silently disables LLM tool-calling (fail-silent to degraded capability)
**File:** `nightwatch/voice_pipeline.py:2086` imports `from nightwatch.telescope_tools import
get_tool_definitions`; `_get_tools()` at `:2083-2090`
**Evidence:** there is no `nightwatch/telescope_tools.py` module (confirmed via Glob) and no
`get_tool_definitions` anywhere in the repo. The import raises `ImportError`, which is caught and logged
only as a `warning`, so `_get_tools()` returns `None`. With `tools=None`, `llm_client.py`'s `if tools:`
gates (`:390`, `:496`) hand the model no function schema — tool-calling cannot occur through this path,
and the VOX-003 validation layer never runs on real traffic. Separately, `deploy/systemd/
nightwatch-wyoming.service:40` references a `voice.wyoming_server` module that also does not exist
in-tree (only `voice/wyoming/{startup,stt_server,tts_server}.py`), so the shipped unit would fail to
launch.
**Why it matters:** security-relevant because it is a fail-silent degradation on the command path: an
operator sees only a warning, not an error, and the validated-tool-call safety machinery (VOX-003) is
inert in practice. Also, the missing `voice.wyoming_server` means the deployment artifact is untested
against reality.
**Confirming the analyst flags:** Command-Execution Security #1 and LLM-Client cross-domain touchpoint —
**both confirmed.**
**Smallest credible fix:** export a `get_tool_definitions()` (or correct the import to
`voice.tools.telescope_tools`) that returns `TELESCOPE_TOOLS` in OpenAI/Anthropic format; make the
`except ImportError` log at `error` and surface a health-check failure rather than silently returning
`None`. Fix the systemd `ExecStart` to a real module. Ensure every tool offered to the LLM has a
`TOOL_PARAM_MODELS` entry (see M-adjacent LL-registry gap in L2 below).

---

## LOW

### L1. Orphaned, internally-inconsistent critical-tool confirmation gate in `LLMClient`
**File:** `nightwatch/llm_client.py:1090` (`requires_confirmation`); registry at `tool_params.py:160-185`
**Evidence:** `critical_tools = {"emergency_shutdown","open_roof","close_roof","stop_roof"}` — none of
these appear in `TOOL_PARAM_MODELS`, so VOX-003 (`llm_client.py:774`, run inside `chat()` before the
caller sees the response) would already drop any such tool call as "Unknown tool" before
`requires_confirmation` could ever inspect it. Grep confirms `requires_confirmation`/
`get_confirmation_prompt` have zero callers outside `llm_client.py` and its unit tests. There is a
second, separate confirmation mechanism on `voice/tools/telescope_tools.py`'s `ToolRegistry`
(`:1374`) that is itself unreachable (see L2).
**Why it matters:** an engineer wiring enclosure/emergency control through the LLM would reasonably
assume this is the safety gate; it is not — it is dead and self-contradictory. Low because nothing
reaches it today.
**Confirming the analyst flag:** LLM-Client Security #1 — **confirmed.**
**Fix:** either register the four tool names in `TOOL_PARAM_MODELS` and call `requires_confirmation`
from the pipeline before acting, or delete the dead gate to avoid false assurance. Pick one confirmation
mechanism and make it the single source of truth.

### L2. Second, unvalidated command-dispatch stack (`ToolRegistry`) with a raw `handler(**arguments)` splat
**File:** `voice/tools/telescope_tools.py:1389` (`handler(**arguments)`); class at `:1298`
**Evidence:** `ToolRegistry.execute()` does `handler(**arguments)` with no Pydantic/`extra="forbid"`
validation, catching only `TypeError`/generic `Exception` after the fact and (`:1397-1398`) not logging.
This is the exact unvalidated-args class that ARCH-001/VOX-003 were written to close. Grep confirms
`ToolRegistry()`/`create_default_handlers()` are constructed only in `__main__` and tests — no production
path. Its `close_roof(emergency=True)` bypass has a stubbed audit log (`:3008`,
`# Logger would log here in production`).
**Why it matters:** dormant today (Tier B), but it is a validation-bypassing dispatcher sitting in the
same package as the validated one; if revived it reintroduces the injection-of-hallucinated-args risk
and an unlogged emergency bypass.
**Confirming the analyst flags:** Command-Execution Security #4 and #6 — **confirmed as dormant.**
**Fix:** if `ToolRegistry` is retired, delete it; if it is the future path, route it through
`TOOL_PARAM_MODELS` validation and implement the emergency-bypass audit log before any revival.

### L3. PowerShell command construction via string interpolation in Windows TTS fallback
**File:** `voice/tts/piper_service.py:444`
**Evidence:**
```python
ps_script = f'Add-Type ...; $speak.Speak("{text}")'
cmd = ["powershell", "-Command", ps_script]
```
`create_subprocess_exec` avoids the OS shell, but PowerShell itself parses the whole `-Command` string;
`text` containing `"` plus a statement separator/backtick can break out of the string literal and
execute attacker-influenced PowerShell.
**Why it matters:** requires Windows AND both Piper and espeak unavailable AND attacker-influenced text
reaching `speak()` — a narrow chain, hence Low. But it is a genuine injection primitive and `text` on
this path can originate from LLM/voice output.
**Confirming the analyst flag:** Voice/NLP Security #3 — **confirmed.**
**Fix:** pass text via `-EncodedCommand` (base64 UTF-16LE) or via stdin to a script that reads
`[Console]::In`, rather than interpolating into the script literal.

### L4. Training-data loaders crash on hand-edited/corrupt state files (`ValueError` not caught)
**File:** `services/voice/vocabulary_trainer.py:181,184,185` and `_load` at `:316-335`;
`services/voice/wake_word_trainer.py:108,141,142,176` and `_load` at `:301-329`
**Evidence:** `_load()` catches only `(json.JSONDecodeError, KeyError)`, but the loaded paths call
`TermCategory(data["category"])` / `DetectionOutcome(data["outcome"])` (raise `ValueError` on an
unknown enum string) and `datetime.fromisoformat(...)` (raises `ValueError` on a bad timestamp). A
corrupted `~/.nightwatch/vocabulary.json` or `wake_word_training.json` (user-writable, not
specially-protected) raises an uncaught `ValueError` out of the constructor. `services/ai_services.py`
eagerly touches both trainers (`:164-165`), so a bad state file is plausibly a startup-crash vector.
**Why it matters:** availability/robustness at a local trust boundary (files a user or another local
process can edit). Low because it requires local write access and current wiring is thin.
**Confirming the analyst flag:** Command-Execution Security #2 — **confirmed.**
**Fix:** broaden the except to include `ValueError` (and log-and-default), or validate enum/timestamp
fields before constructing.

### L5. Cloud-SDK exception strings logged verbatim (potential partial-credential echo)
**File:** `nightwatch/llm_client.py:544` and `:640` (`logger.error(f"...API call failed: {e}")`)
**Evidence:** the raw third-party SDK exception is logged unscrubbed. Some provider SDK auth errors echo
a masked/partial key or request payload in the message. API keys themselves are read from env and never
logged directly (good), and no confirmed leak was found — this is a hardening item.
**Why it matters:** low-probability information disclosure into logs; logs may be shipped off-host.
**Confirming the analyst flag:** LLM-Client Security #5 — **confirmed as a hardening item, not a
confirmed leak.**
**Fix:** log `type(e).__name__` plus a scrubbed message, or catch specific auth-error types and emit a
fixed string.

---

## INFO / positive findings

### I1. No hardcoded live secrets, keys, or tokens found (independent sweep)
Grep for private-key headers, AWS keys, `sk-` tokens across the working tree and the last 20 commits of
history found nothing. No `.env`/`.pem`/`.key`/credential files in history. The only credential-shaped
values are *default placeholders* (`http_password="admin"` — see H3; `sms_twilio_token=""`,
`email_smtp_password=""` — empty defaults in `services/alerts/alert_manager.py:58,69`). API keys are
sourced from env (`ANTHROPIC_API_KEY`/`OPENAI_API_KEY`, `llm_client.py:454,572`) and AMS `api_key` is
passed as a param (`fireball_client.py:222`), never committed. Pre-commit runs `detect-private-key`
(`.pre-commit-config.yaml:67`) and `bandit` (`:114-119`).

### I2. No dangerous deserialization or eval-family constructs anywhere
Repo-wide grep for `eval(`, `exec(`, `pickle`, `marshal`, `yaml.load(` (unsafe), `shell=True`,
`os.system(` returned **zero** matches in application code. Config loading uses `yaml.safe_load`
(`config.py:991`). All persistence uses `json` only. Subprocess use is safe: plate solver
(`astrometry/plate_solver.py:368,520`) and TTS fallbacks (`piper_service.py:410,451`) use
`create_subprocess_exec(*argv)` with list args, not a shell (the L3 PowerShell caveat is about
PowerShell's own parsing, not the OS shell).

### I3. SQL is fully parameterized; env-override safety allowlist is a genuine, well-tested control
`services/catalog/catalog.py:403-507` builds `sql`/`params` separately and passes both to
`cursor.execute(sql, params)` — no string-interpolated SQL. The `SAFETY_ENV_OVERRIDE_ALLOWLIST`
deny-by-default gate (`config.py:90`, enforced at `:920-941`) correctly rejects `NIGHTWATCH_SAFETY_*`
env overrides not on the (empty) allowlist with a `logger.critical`, and is well covered
(`tests/unit/test_config.py:395-505`). This is a real, correctly-implemented control.

### I4. CI/CD and systemd hardening are reasonable
GitHub Actions pin major-version tags (`actions/checkout@v4`, `setup-python@v5`); `release.yml` scopes
`permissions:` on the publish job; no `pull_request_target` misuse; no `secrets.` interpolated into shell
in a risky way. Systemd units apply `NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`,
`PrivateTmp`, capability bounding (`CAP_SYS_RAWIO` only), memory/CPU limits, and a dedicated
`nightwatch` user (`deploy/systemd/nightwatch.service:53-69`). Two notes for the deployment reviewer,
not security findings here: `docker-compose.prod.yml` runs the main container `privileged: true` with
`/dev:/dev` (broad, but a common GPIO/serial pattern — recommend `devices:`/specific `--device` instead),
and session logs land in a CWD-relative `logs/` dir because `NightwatchConfig` has no `data_dir` field
(`orchestrator.py:2072`, `hasattr` is always False) — set `WorkingDirectory=` (the units do:
`/opt/nightwatch`).

---

## Cleared — analyst flags investigated and dismissed / re-characterized

Each item below was raised by a domain analyst and, on re-verification, is **not** an independent
security vulnerability (or was down-ranked with reasons). Listed so nothing is silently dropped.

- **"Config parsing is safe" (Core Orch Security #5), "No secrets/deserialization in Voice domain"
  (Voice #6), "No eval/exec/pickle/yaml.load" (Astronomy #9), "Subprocess use is safe" (Astronomy #8):**
  **Confirmed cleared** — independently re-verified via repo-wide grep (see I2/I3). These were correct
  negative findings; nothing to escalate.

- **`SafetyInterlock` / `EmergencyResponse` / `SafeStateHandler` / `EventBus` / priority `CommandQueue`
  "built, tested, never wired" (Core Orch Security #2):** **Confirmed as dormant, cleared as a *security
  vuln*, retained as architecture risk.** These are not an attack surface (no production path, no
  network/input exposure). The *real* enforced safety boundary the analyst identified
  (`services/safety_monitor` driving the roof + orchestrator cancel callbacks) is exactly where C1/M1/M2
  live, so the substantive risk is captured there. The "defense-in-depth that isn't wired" observation is
  a real architecture/quality concern for the L5 architect, not a distinct security finding.

- **Duplicate/incompatible `SafetyInterlockError` classes (Core Orch Security #4):** **Cleared as a
  security finding.** Verified both definitions exist (`exceptions.py:263` vs
  `safety_interlock.py:552`), but nothing imports the `exceptions.py` variant and `SafetyInterlock` is
  unwired. This is a latent footgun / quality issue, not an exploitable condition.

- **"Dangerous action" clarification is UX not enforcement (Voice #5, LLM safety-grounding advisory
  prose):** **Confirmed and cleared as *correctly characterized by the analyst*.** The
  `clarification.py` substring match and the `SAFETY STATUS:` prompt block are advisory. I confirmed no
  component treats "clarification resolved" or "model complied" as the authoritative veto — the intended
  authoritative veto is `services/safety_monitor` (which has its own defects, C1/M1/M2). No new finding;
  the analyst's warning ("do not let downstream assume otherwise") stands as guidance.

- **Silent exception swallowing at Wyoming `read_message` (Voice #4):** **Confirmed behavior, folded into
  H4 rather than ranked separately.** `protocol.py:433` catches all exceptions and returns `None`
  (indistinguishable from disconnect). Real, but its security impact (weak forensic trail for probing) is
  only meaningful in combination with the no-auth exposure already captured in H4. Fix: log at debug/info
  in `read_message` before returning `None`.

- **Unauthenticated Alpaca UDP discovery accepts attacker-shaped input (Astronomy #5):** **Confirmed,
  down-ranked to dormant/Info-adjacent.** `alpaca_client.py:154-188` does `json.loads` on any UDP reply
  and stores an advertised port with no validation. This mirrors the real ASCOM Alpaca protocol (not a
  novel flaw), the parsed values feed only device-endpoint construction, and the whole Alpaca module is
  stale/unwired (no production caller). Worth an allowlist/bounds-check *if* Alpaca is activated; not an
  active vulnerability today. Rolled into the M5 plaintext-device-IO theme.

- **`chat_stream` bypasses VOX-003 (LLM Quality #2), unbounded conversation history (LLM Quality #3),
  `add_normalization` ReDoS primitive (Command-Exec Security #3):** **Cleared as latent, no live path.**
  `chat_stream` has no production caller; conversation-history growth is a memory/quality issue not a
  security boundary; `add_normalization` has no production caller and the one wired rule-adding path
  (`learn_from_correction`) uses `re.escape()` first (verified `vocabulary_trainer.py:564-570`). All three
  are correct as "flag for when this gets wired" — no action required now beyond awareness.

- **`LLMClient`/`LocalLlamaClient` blocks the event loop; `model_path` unvalidated (LLM Security #3, #4):**
  **Confirmed, cleared as *not a security vuln today*.** Real concerns, but `LLMClient` is unconstructed
  in production (verified) and `model_path` comes from operator config, not attacker input. The
  event-loop-blocking point is a reliability risk for the safety loop *if* the client is ever wired onto
  the orchestrator's loop — carried forward as a note for whoever does the wiring, not ranked here.

- **`meteor_tracking/hopi_circles.py` / `lexicon_prayers.py` naming (Astronomy #7):** **Not a security
  matter.** Editorial/cultural-sensitivity review item; code read contains ordinary geometry/string
  formatting, no defect. Explicitly out of security scope.

---

## Top remediation order (for the architect)

1. **C1 + M2 together** — make the emergency roof close actually move the roof (init `_gpio`; `await` the
   async `close`). This is the highest-consequence defect in the repo.
2. **H1** — fix `setup_logging(level=...)` so the system can start and its startup security posture
   becomes testable.
3. **H2** — bump aiohttp to ≥3.14.1 and make `pip-audit` a failing CI gate.
4. **M1** — repair the power-failure safety action.
5. **H3 / H4** — remove default PDU credentials and bind Wyoming to loopback + cap the audio buffer
   before any network deployment.
6. **M3** — reconcile the async/sync Protocol contract before wiring real hardware (the park path is on
   the safe-shutdown route).

The recurring root cause across C1, M1, M2, M4 is **broad `except Exception` swallowing on the safety
path combined with tests that mock out the failing code** — a monitoring loop legitimately must not die,
but swallowing must be paired with (a) a loud, structured alert and (b) at least one test that exercises
the real (unmocked) hardware call path. That pattern, not any single line, is what let three separate
safety-critical defects ship undetected.
