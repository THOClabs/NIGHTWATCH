# NIGHTWATCH Risk Register (L5)

**Author:** Chief Architect (L5/L6 synthesis)
**Date:** 2026-07-12
**Scoring:** Impact × Likelihood, each 1-5. Impact rates worst credible outcome (5 = destroyed
hardware / water damage / total project loss). Likelihood rates probability of the harm
materializing on the project's stated trajectory (deployment artifacts exist; the entry-point fix
is one line, so "not currently running" is not treated as a mitigation — per 30-security.md's
Tier A/B rule, which this register adopts). Owner-level: quick fix (< 1 day) / project (a planned
workstream) / strategic (changes how the project operates).

| # | Risk | Score |
|---|---|---|
| R1 | Emergency roof close silently fails — hardware/water loss | 20 |
| R2 | No feedback loop: CI cannot fail, test suite untrustworthy | 20 |
| R3 | System cannot start; every documented path broken | 16 |
| R4 | "Built but never wired" core — the product doesn't exist as a system, and looks like it does | 16 |
| R5 | Orchestrator/hardware contract mismatch breaks the park-and-close path at first real wiring | 16 |
| R6 | Bus factor = 1 across every subsystem | 15 |
| R7 | Weather ingestion fails open; promised rain-sensor redundancy doesn't exist | 12 |
| R8 | Unauthenticated network surface: Wyoming on 0.0.0.0 + default PDU credentials | 12 |
| R9 | Broad exception swallowing as house idiom keeps converting defects into silence | 12 |
| R10 | Dependency hygiene: 11 known aiohttp CVEs pinned; manifests unmonitored and partly unsatisfiable | 9 |

---

### R1. Emergency roof close silently fails (Impact 5 × Likelihood 4 = 20)

**Risk:** In a real rain/wind emergency the system correctly decides "close the roof now" and the
roof does not move, with no alarm. Two independent, code-confirmed breaks: (a) `RoofController`
never initializes `self._gpio` (only `setup_rain_sensor_interrupt()` would, and it has zero call
sites), so `_run_motor()` raises `AttributeError`, swallowed by `close()`'s `except Exception` —
live-reproduced by two independent reviewers; (b) `SafetyMonitor._close_enclosure_safely()` calls
the `async` `close()` without `await` from a sync method, so even with (a) fixed the coroutine
never runs. Both are masked by tests that patch `_run_motor` out. This directly nullifies the
SAFE-001 commit's stated guarantee.
**Evidence:** `services/enclosure/roof_controller.py:484-531` (no `_gpio` in `__init__`; verified),
`:848`, `:1051-1061`; `services/safety_monitor/monitor.py:1535` (verified un-awaited);
30-security.md C1+M2; 20-domain-astronomy §6; 31-quality.md Q-table (live reproduction, with the
refinement that the bug fires exactly when the roof is open — the scenario that matters).
**Blast radius:** telescope, camera, mount electronics, enclosure interior — total-loss scale for
a hobby-to-prosumer observatory; also every downstream claim of "autonomous safe operation."
**Smallest credible mitigation:** initialize `self._gpio: Optional[GPIOInterface] = None` in
`__init__` (construct real backend in `connect()`); make `_close_enclosure_safely` async and
`await self.enclosure.close(emergency=True)`; add one test that drives
`close(emergency=True)` on an open roof **without** patching `_run_motor`. Fix M1
(`_action_callback` never assigned — the power-failure twin of this bug) in the same pass.
**Owner-level:** quick fix (the code changes) + project (the unmocked-safety-path test policy).

### R2. No feedback loop: CI cannot fail and the test suite is not trustworthy (Impact 4 × Likelihood 5 = 20)

**Risk:** Every regression signal is muted: all 9 CI jobs neutralize their exit codes
(`continue-on-error: true` ×12 — verified — plus `|| true`/`|| echo` on every pytest/ruff/mypy/
bandit call); the unit suite itself is polluted by an unscoped module-level
`sys.modules['numpy'] = MagicMock()` in two test files, making pass/fail depend on collection
order (48 "failures," ~46 of them artifacts, 2 real bugs including a confirmed double
session-log write); coverage is 48.25% against two different unenforced thresholds. Every other
risk in this register shipped *because* of this one — mypy already flags the R3 crash verbatim.
**Evidence:** `.github/workflows/ci.yml:55,79,190,195-196,228` et al.;
`tests/unit/test_piper_service.py:27`, `test_whisper_service.py:35`;
`nightwatch/orchestrator.py:2059,2391`; 31-quality.md Q1/Q3/Q4/Q6/Q8.
**Blast radius:** entire codebase — quality regressions, security regressions, and safety
regressions are all currently undetectable; the green badge is actively misleading contributors
and any future collaborator/customer.
**Smallest credible mitigation:** un-mute exactly two steps — the `unit-tests` pytest invocation
and `mypy nightwatch/` — and fix the two `sys.modules['numpy']` mocks with `monkeypatch.setitem`.
Everything else can stay advisory for now, as a documented choice.
**Owner-level:** quick fix.

### R3. System cannot start; every documented path is broken (Impact 4 × Likelihood 4 = 16)

**Risk:** `python -m nightwatch.main` crashes on every invocation (`setup_logging(level=...)` vs
parameter `log_level` — verified at `main.py:308,325`); the README's first install command fails
atomically on a clean machine (`pyindi-client~=2.0.8` — a version that has never existed on PyPI);
the README's run command targets a nonexistent `nightwatch.cli`; the systemd Wyoming unit launches
a nonexistent `voice.wyoming_server` module (verified). No deployment can be running this branch;
no newcomer can complete onboarding; the startup safety posture (config allowlist, service wiring)
is untestable against the real entry point.
**Evidence:** 30-security.md H1, 31-quality.md Q2/Q13/Q26 (all live-executed);
`deploy/systemd/nightwatch-wyoming.service:40` (verified).
**Blast radius:** availability of the entire product; credibility of all documentation; masks the
true state of R4 (nobody can observe what does/doesn't run).
**Smallest credible mitigation:** rename the two kwargs; pin `pyindi-client>=2.1,<3`; correct the
README/QUICKSTART invocations and the systemd ExecStart; add one smoke test that calls
`main(["--dry-run"])`.
**Owner-level:** quick fix.

### R4. "Built but never wired": the integrated product doesn't exist, and the codebase actively suggests it does (Impact 4 × Likelihood 4 = 16)

**Risk:** The LLM client (with its VOX-003 validation and safety grounding), the voice pipeline,
the Wyoming servers, all of `services/nlp`, `SafetyInterlock`, `EmergencyResponse`,
`SafeStateHandler`, `EventBus`, the priority `CommandQueue`, `ToolChain`, and the 87-tool
`ToolRegistry` all have zero production call sites (verified for the load-bearing cases). The
tool-schema bridge imports a nonexistent module and fails silently to `tools=None`. Consequences:
(a) **false assurance** — a reviewer, insurer, or buyer reading the code sees layered safety and
capability that is not enforced (RELEASE_v0.1.0.md already overclaims "safety veto system for all
operations"); (b) **rot** — dormant code drifts from live conventions (already: `get_state()` vs
`state`, sync/async mismatches, constants drift) and its eventual wiring will surface a defect
cluster at the worst time; (c) wasted maintenance on ~4,100 dead lines in the repo's largest file.
**Evidence:** 20-domain-core §6.2; 20-domain-llm Security #1/#2; 20-domain-voice Quality #1;
20-domain-command Quality #1/#3; 31-quality.md Q17/Q18; `voice_pipeline.py:2086` and
`TOOL_PARAM_MODELS` = 18 keys (both verified by this author).
**Blast radius:** product delivery timeline; safety-review validity; every future integration
effort inherits the defect cluster.
**Smallest credible mitigation:** a one-page wire-or-delete triage listing each dormant subsystem
with a decision and a spec reference; immediately fix the `_get_tools()` import (export
`get_tool_definitions()` from `voice/tools/telescope_tools.py`) and make its failure loud; delete
(or move to an `attic/`) whichever of `ToolRegistry`/`EventBus`/`CommandQueue`/`EmergencyResponse`
loses the triage. Correct RELEASE_v0.1.0.md's claims meanwhile.
**Owner-level:** project.

### R5. Orchestrator/hardware Protocol mismatch breaks park-and-close at first real wiring (Impact 4 × Likelihood 4 = 16)

**Risk:** The orchestrator's shutdown and emergency paths `await mount.park()` etc., but the real
`LX200Client.park()/stop()/unpark()` are synchronous — `TypeError` at the exact moment a
signal-driven safe shutdown tries to park real hardware. Parallel mismatches: `SafetyMonitor`
lacks the `is_safe` property its Protocol requires; camera and power classes don't match theirs;
`emergency_response.py`/`watchdog.py` expect `roof.get_state()` where the real API is a property.
None of this is caught because every test uses `MagicMock`, which fabricates any attribute, and no
bootstrap constructs concrete services today.
**Evidence:** `services/mount_control/lx200.py:530,580,585` vs `orchestrator.py:2035,2366,2920`;
`orchestrator.py:871-1135`; 30-security.md M3 (confirmed); 20-domain-astronomy Security #3.
**Blast radius:** the safe-shutdown and emergency paths — the same physical assets as R1 — plus
weeks of integration schedule when wiring finally happens.
**Smallest credible mitigation:** one parametrized Protocol-conformance test (assert each concrete
service satisfies its `Protocol` via `isinstance` on a `runtime_checkable` version, plus
sync/async signature checks); make `LX200Client`'s mutating methods async via `asyncio.to_thread`
following the pattern `sync_to_coordinates` already established.
**Owner-level:** project.

### R6. Bus factor = 1 (Impact 5 × Likelihood 3 = 15)

**Risk:** One person (two git identities, 97% of commits) owns every subsystem; the sole active
developer for the last 60 days; zero code review (1 merge commit in 61); knowledge concentrated in
two single-author god-files (`orchestrator.py` 3,446 lines, `telescope_tools.py` 5,662 lines).
Illness, burnout, or departure stalls the project entirely; equally important, the wiring gaps of
R4 persist precisely because no second person has ever had to make the system run.
**Evidence:** 10-history.md §3/§7.1 (CRITICAL); 31-quality.md Q18; branch anomaly (main 27 days
stale, all work on a review branch).
**Blast radius:** project continuity and every unreviewed design decision.
**Smallest credible mitigation:** cannot be quick-fixed. Nearest credible steps: tag a release
(rollback point), enforce PR-based merges to main even solo (forces self-review + CI gate from
R2), and write down the run-it-for-real bootstrap procedure so a second person could take over.
The review corpus in `docs/review/` is itself a partial mitigation — keep it current.
**Owner-level:** strategic.

### R7. Weather ingestion fails open; promised rain redundancy doesn't exist (Impact 4 × Likelihood 3 = 12)

**Risk:** The primary safety sensor feed (Ecowitt, plaintext HTTP, no auth) substitutes benign
defaults on missing/garbled fields — a truncated or attacker-shaped response parses as "70°F, dry"
with `is_valid=True`, suppressing the rain signal that drives roof closure. The SAFE-002
dual-sensor voting that was designed to hedge exactly this has no secondary driver anywhere in the
codebase (`secondary_rain.py` is data-shape-only), while `require_secondary_rain_sensor=True` by
default would deadlock safety if the module were wired as-is — the flag has no config surface.
**Evidence:** `services/weather/ecowitt.py:159-200`; `services/weather/secondary_rain.py:13-23`;
`monitor.py:244,553-639`; 30-security.md M4/M5 (confirmed); 20-domain-astronomy §5/§6.
**Blast radius:** same physical assets as R1 (this is the decision input; R1 is the actuation),
plus false "SAFE_TO_OBSERVE" states during marginal weather.
**Smallest credible mitigation:** treat missing required keys as an invalid reading
(`is_valid=False`) so the monitor's existing staleness fail-safe engages; decide the SAFE-002
secondary-sensor question explicitly (implement the driver, or set the default to `False` with a
documented rationale) instead of leaving a default that can't be satisfied.
**Owner-level:** quick fix (parser) + project (SAFE-002 decision).

### R8. Unauthenticated network surface: Wyoming on 0.0.0.0 + default power credentials (Impact 4 × Likelihood 3 = 12)

**Risk:** Wyoming STT/TTS servers ship `wyoming_enabled=True`, bind `0.0.0.0`, no auth/TLS, mDNS
advertisement, and an unbounded per-session audio buffer (trivial memory-exhaustion DoS; audio
injection sits upstream of command interpretation). The PDU controller defaults to
`admin`/`admin` over plaintext HTTP and SNMP community `private` — any LAN host can cut power to
mount/camera/computer. `docker-compose.prod.yml` exposes 10300 (verified); the deploy intent is
explicit even though the launcher module is currently missing.
**Evidence:** `nightwatch/config.py:346-420`; `voice/wyoming/stt_server.py:116,234-238`;
`services/power/power_manager.py:50-55,147,806-808`; 30-security.md H3/H4 (both confirmed);
Wyoming server code is 12-19% covered — lowest in the tree (31-quality Q6).
**Blast radius:** LAN-adjacent attacker gets voice-command injection, resource exhaustion, and
power control over safety-relevant hardware.
**Smallest credible mitigation:** default `wyoming_host="127.0.0.1"`; cap `audio_buffer` using the
`AudioConfig.max_duration` logic that already exists on the local path; empty the PDU credential
defaults and hard-fail connect when enabled without configured credentials.
**Owner-level:** quick fix.

### R9. Broad exception swallowing as house idiom (Impact 3 × Likelihood 4 = 12)

**Risk:** 437 `except Exception` sites (vs 18 explicit timeout usages) plus one bare `except:`
that reports a malformed PDU response as a **successful** power operation
(`power_manager.py:309`). This idiom already converted three safety-critical defects (R1's two
breaks, plus the never-assigned `_action_callback` in the power-failure path) into log lines, and
the test suite's `MagicMock` habits mean swallowed defects are structurally undetectable. Until the
idiom changes, new defects of the same class will keep shipping silently — this is the root-cause
risk behind R1/R5/R7.
**Evidence:** 31-quality.md Q7 (repo-wide count, bare-except pinpointed); 30-security.md closing
root-cause note; 20-domain-astronomy Quality #1.
**Blast radius:** defect detectability across all hardware/safety paths.
**Smallest credible mitigation:** narrow the two known safety-relevant sites now (roof
`open()`/`close()` catches; `power_manager.py:309`); adopt a written rule — a swallow on a
safety/hardware path requires a structured alert plus one unmocked-path test — and enforce it in
review (which requires R2's CI gate to mean anything).
**Owner-level:** project.

### R10. Dependency hygiene: known-vulnerable pin + unmonitored, partly unsatisfiable manifests (Impact 3 × Likelihood 3 = 9)

**Risk:** `uv.lock` pins `aiohttp 3.13.5` with 11 known CVEs (fix in 3.14.1) — and aiohttp is the
transport for every safety-relevant network feed (weather, PDU, alerts). Simultaneously,
`services/requirements.txt` pins a `pyindi-client` version that never existed, proving nobody (and
no CI, per R2) exercises these manifests: `pip-audit` runs advisory-only, and CI's own install
step has been silently no-op-ing (`|| true`). No git tags exist, so no version can be patched or
rolled back independently.
**Evidence:** 30-security.md H2; 31-quality.md Q2/Q22; `.github/workflows/ci.yml:41`;
10-history.md §5.4/§7.4.
**Blast radius:** ingress path of safety-relevant data; reproducibility of any deployment;
inability to bisect or roll back.
**Smallest credible mitigation:** bump `aiohttp>=3.14.1` and regenerate the lock; fix the
`pyindi-client` pin (subsumes part of R3); make `pip-audit` a failing CI gate for
known-fix-available vulns; tag `v0.1.0-alpha` at the next stable point.
**Owner-level:** quick fix (pins) + project (audit gate, release cadence).

---

## Reading order for remediation

The register intentionally front-loads the two enabling risks: **R2 makes every other fix
verifiable, and R3 makes the system observable.** Recommended sequence: R3 + R2 (days), then R1 +
R7-parser (the physical-safety cluster, days), then R8 + R10 pins (hardening, days), then R4/R5/R9
as the first real project workstreams, with R6 as the standing strategic constraint that shapes
how all of the above are executed (PR-gated, documented, releasable).
