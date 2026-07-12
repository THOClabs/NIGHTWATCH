# NIGHTWATCH Quality Audit (L4 Cross-Cutting)

**Auditor:** L4 Quality Auditor (the "column" cutting across every domain "row")
**Date:** 2026-07-12
**Repository:** `/home/user/NIGHTWATCH`
**Method:** Read `00-inventory.md`, `10-history.md`, and all five `20-domain-*.md` reports in full
before doing any independent work. Every "Quality observations" flag from all five domain reports was
either independently re-verified against source (grep/read/live execution) or explicitly marked as
trusted-from-domain-report where re-verification was out of budget. Built a real virtual environment
(`python3.11 -m venv`), installed dependencies via the project's own documented commands, ran the unit
test suite twice (parallel via `pytest-xdist` and serial, ~2618 tests, ~5-6 minutes each), ran
`ruff`, `mypy`, `bandit`, `ruff format --check`, `docker compose config`, and literally executed the
documented CLI entry point and install commands. Read-only toward source; the only file written is
this one.

---

## Executive summary

NIGHTWATCH's CI/CD pipeline is unable to fail on any test, lint, type, or security signal today —
every job either has `continue-on-error: true`, a `|| true` / `|| echo "..."` shell escape hatch after
the command that does the real work, or both. The single exception (a `docker compose config` syntax
check) currently passes trivially. This means the badge on the README ("CI: passing") certifies
nothing about test correctness, lint cleanliness, type safety, or coverage — it can only ever be green
or itself broken.

Underneath that pipeline, the actual numbers are: **2570 passed / 48 failed / 2 collection errors**
out of 2618 unit tests when run exactly as documented (`pytest tests/unit/ -v`) in a from-scratch
environment; **48.25% line coverage** against a configured-but-unenforced 60% threshold in
`pyproject.toml` (and a *different*, also-unenforced 80% threshold hand-rolled in the CI YAML);
**2585 ruff errors** even under CI's own ignore-list; **233 mypy errors** in the one package
(`nightwatch/`) that opts into stricter checking; and a documented install path
(`pip install -r services/requirements.txt`, the literal first command in the README Quickstart) that
**fails outright** on a clean machine because of an unsatisfiable version pin. None of this is
visible to a contributor trusting the green CI badge.

Of the 48 test failures, this audit traced root causes for a representative sample and found the
suite itself is not hygienic: two test files perform an unscoped, global `sys.modules['numpy'] =
MagicMock()` replacement at import time with no teardown, which silently poisons every subsequent
test in the same process/worker that needs a real `numpy` — this explains at least ~46 of the 48
failures (confirmed by reproducing several in isolation, where they pass). The remaining two are real:
a test that hangs because it doesn't override a 300-second production default
(`services/power/power_manager.py:792`), and a genuine double-invocation bug in the orchestrator's
shutdown path (`nightwatch/orchestrator.py:2059` and `:2391` both call `_save_session_log()`). Both
would have failed an honest CI run; neither does, because of the muting described above.

Every domain analyst's "Quality observations" flag was checked; **none were refuted**. Several were
independently reproduced (the `setup_logging()` crash, the `RoofController._gpio` AttributeError, the
`constants.py`/`config.py` safety-threshold drift, the missing tool-schema import, the orphaned
`requires_confirmation()` tool list). This report treats that as confirmation the domain layer's
"designed once, tested in isolation, never wired, never re-validated" pattern is real and pervasive,
and adds the CI/tooling/test-hygiene layer that makes it invisible to anyone not reading source.

---

## Severity counts

| Severity | Count |
|---|---|
| Critical | 4 |
| High | 6 |
| Medium | 7 |
| Low | 5 |
| Info | 4 |

---

## Confirmation/refutation of every domain analyst "Quality observations" flag

No flag from any domain report is refuted. Status key: **CONFIRMED** (independently reproduced/verified
by this audit), **CONFIRMED (trusted)** (internally consistent, consistent with other independent
evidence gathered, not independently re-executed given time budget).

### Core Orchestration & Safety (`20-domain-core-orchestration-safety.md` §6 Quality observations)

| # | Flag | Status |
|---|---|---|
| 1 | "Designed, tested-in-isolation, never wired" pattern (`SafetyInterlock`, `EmergencyResponse`, `SafeStateHandler`, `EventBus`, `CommandQueue`) | **CONFIRMED** — grep for constructor call sites of each class outside `tests/` returns nothing; independently re-confirmed for `LLMClient`/`VoicePipeline` (see LLM/Voice sections below) |
| 2 | `StartupSequence.run()` dependency-check `continue` only breaks the inner loop | **CONFIRMED** — read `nightwatch/health.py:679-690` directly; the `continue` at line 690 is inside `for dep in dependencies`, not `for service_name in self.STARTUP_ORDER` |
| 3 | `orchestrator.py` module docstring references nonexistent `process_command` | **CONFIRMED** — `grep -n process_command nightwatch/orchestrator.py` returns only the docstring line (46); no method definition anywhere |
| 4 | Two overlapping health/liveness loops; `watchdog.heartbeat()` never called for standard services | **CONFIRMED** — `grep -n "watchdog.heartbeat\|\.heartbeat(" nightwatch/orchestrator.py` returns zero matches |
| 5 | Test coverage gaps (`main.py`, `health.py` failing-dependency path, `execute_cancellable` family) | **CONFIRMED (trusted)**; corroborated in aggregate by this audit's own coverage run (48.25% overall, see Test Reality §) |
| 6 | Dangling `CLAUDE.md` reference in `config.py:81-82` | **CONFIRMED** — `find / -iname CLAUDE.md` (repo-scoped) returns nothing |
| 7 | `orchestrator.py` is a 3,446-line god-file | **CONFIRMED** — `wc -l nightwatch/orchestrator.py` = 3446 |
| 8 | `emergency_response.py`/`watchdog.SafeStateHandler` call sync mount methods without `await`, would silently no-op against an async mount | **CONFIRMED (trusted)** — consistent with the Astronomy domain's independently-confirmed finding that `LX200Client.park/unpark/stop` are plain synchronous methods while `mount_simulator`'s are `async def` |

### Voice & NLP (`20-domain-voice-nlp.md` §6 Quality observations)

| # | Flag | Status |
|---|---|---|
| 1 | Real NLP/voice engines disconnected from the running app; `nightwatch/__init__.py` NLP import commented out; `VoicePipeline.TTSInterface.synthesize()` returns mock silent audio, Piper never called | **CONFIRMED** — `nightwatch/__init__.py:51` (`# from services.nlp import (`), `nightwatch/voice_pipeline.py:1616-1622` (`return self._generate_mock_audio(text)` / `# Would use piper to synthesize`) |
| 2 | Whole domain (`voice/stt`, `voice/tts`, `voice/wyoming`, `services/nlp/*`) has exactly one commit each, all from 2026-01-20, none since | **CONFIRMED (trusted)** — consistent with `10-history.md`'s independently-derived churn table |
| 3 | Hardcoded `confidence=0.9` defeats the confidence-threshold feature | **CONFIRMED** — `voice/stt/whisper_service.py:592` |
| 4 | Stub warning generators in `SuggestionService` (`_check_meridian_flip_warning` etc.) always `return None` | **CONFIRMED (trusted)** |
| 5 | Process-wide singletons with no session key | **CONFIRMED (trusted)** — consistent with the module-level `get_*()` factory pattern visible throughout `services/` |
| 6 | Wyoming server code (`handle_client`, `_transcribe_buffer`, mDNS lifecycle) has zero test references | **CONFIRMED, and quantified** — this audit's coverage run measured `voice/wyoming/stt_server.py` at 14.89%, `tts_server.py` at 12.66%, `startup.py` at 18.90% line coverage, the three lowest-covered files in the entire tree |
| 7 | Inconsistent diagnostics: `print()` in `voice/stt`/`voice/tts` vs. `logging` elsewhere | **CONFIRMED (trusted)** |
| 8 | Untested resampling path (`np.interp`, no anti-aliasing) | **CONFIRMED (trusted)** |
| 9 | Unguarded parsing in `SessionNarrator.load_schedule` | **CONFIRMED (trusted)** |

### Command Execution & Tool Integration (`20-domain-command-execution-tool-integration.md` §6 Quality observations)

| # | Flag | Status |
|---|---|---|
| 1 | `ToolChain`/`BUILTIN_CHAINS` untested and references unregistered tool names | **CONFIRMED** — `nightwatch/tool_executor.py:1207` defines `BUILTIN_CHAINS`; none of `capture_image`/`autofocus`/`open_enclosure`/`close_enclosure` appear in `_register_default_handlers` (verified: only the 18 mount/catalog/ephemeris/weather/safety/session tools are registered) |
| 2 | Dead `step_id` variable masking a chain-result collision bug | **CONFIRMED (trusted)** |
| 3 | Large gap between ~87 defined tool schemas and 18 live handlers | **CONFIRMED (trusted)**, corroborated independently: `TOOL_PARAM_MODELS` (the schema registry consumed by both `tool_executor.py` and `llm_client.py`) contains exactly 18 keys (verified by direct read of `nightwatch/tool_params.py`) |
| 4 | `MeteorToolHandler` untested, no production caller, fragile string-parsing contract | **CONFIRMED (trusted)** |
| 5 | `ResponseFormatter.RESPONSE_TEMPLATES` — 12 of 15 entries dead | **CONFIRMED (trusted)** |
| 6 | Uneven test depth — `test_telescope_tools.py` is shape-assertion-heavy, not behavior-heavy | **CONFIRMED (trusted)** |
| 7 | `ToolRegistry.execute()`'s catch-all doesn't log | **CONFIRMED (trusted)** |
| 8 | `ToolExecutor.execute()` self-flagged complexity hotspot (`# noqa: PLR0912`) | **CONFIRMED** — `nightwatch/tool_executor.py:258` carries the noqa comment as described |

### Astronomy & Hardware Services (`20-domain-astronomy-hardware-services.md` §6 Quality observations)

| # | Flag | Status |
|---|---|---|
| 1 | Two safety-critical `AttributeError` bugs masked by test doubles (`roof_controller._gpio`, `SafetyMonitor._action_callback`) | **CONFIRMED BY LIVE REPRODUCTION** — this audit independently reproduced the `roof_controller.py` bug end-to-end (see Critical finding Q1 below); note a refinement: `close()`/`open()` only reach the buggy `_run_motor()` path when the roof is *not already* in the target state (a fresh `RoofController` defaults to `_position=0` → `RoofState.CLOSED`, so a naive `close()` on an untouched instance short-circuits at the "already closed" check before ever touching `_gpio`; the bug fires exactly in the scenario that matters — an *open* roof receiving an emergency close) |
| 2 | Dead `DATA_DIR` in `ephemeris/skyfield_service.py` | **CONFIRMED (trusted)** |
| 3 | INDI raw client (`indi_client.py`) untested directly | **CONFIRMED (trusted)** |
| 4 | `services/simulators/` has no standalone unit tests | **CONFIRMED (trusted)** |
| 5 | Stale-since-inception modules (`alpaca`, `enclosure`, `encoder`, `ephemeris`, `indi`, `simulators`) | **CONFIRMED (trusted)**, consistent with `10-history.md` §4.1 |
| 6 | Inconsistent async/sync API surface in `LX200Client`/`OnStepXExtended` | **CONFIRMED (trusted)** |
| 7 | Unusual naming in `meteor_tracking/hopi_circles.py`/`lexicon_prayers.py` | **CONFIRMED (trusted)** — out of this audit's scope to re-review, no functional impact found |
| 8 | Plaintext credential fields as dataclass attributes | **CONFIRMED (trusted)** |
| 9 | Broad-`except` counts per file | **CONFIRMED, and extended** — this audit's own repo-wide count: **437** `except Exception` occurrences across `nightwatch/` + `services/` + `voice/`, plus exactly **1** bare `except:` (confirmed at `services/power/power_manager.py:309`, matching the domain report's "1 bare except found, location not pinpointed" — location is now pinpointed) |
| 10 | Camera capture race-condition history (positive finding) | **CONFIRMED (trusted)**, not re-verified in depth (out of budget) |

### LLM Client & Tool Binding (`20-domain-llm-client-tool-binding.md` §6 Quality observations)

| # | Flag | Status |
|---|---|---|
| 1 | Stale module docstring referencing nonexistent `LLMConfig` import | **CONFIRMED (trusted)** |
| 2 | `chat_stream` bypasses VOX-003 validation and fallback chain entirely | **CONFIRMED (trusted)** |
| 3 | Unbounded conversation history growth | **CONFIRMED (trusted)** |
| 4 | Confidence heuristic is a hand-tuned English keyword list | **CONFIRMED (trusted)** |
| 5 | `health_check()` misleading for cloud backends (only checks client construction) | **CONFIRMED (trusted)** |
| 6 | Test coverage good for this domain specifically, but exercises unreachable code | **CONFIRMED** — independently confirmed `LLMClient`/`create_llm_client` have no construction site in `nightwatch/main.py` or `nightwatch/orchestrator.py` (grep), and that `nightwatch/voice_pipeline.py:2086`'s `from nightwatch.telescope_tools import get_tool_definitions` genuinely fails (`find` confirms no `nightwatch/telescope_tools.py` exists anywhere in the repo) |
| 7 | `LLMClient.chat` complexity hotspot (~108 lines) | **CONFIRMED (trusted)** |
| 8 | No use of `cancellation.py` primitives in `llm_client.py` | **CONFIRMED (trusted)** |

---

## Findings (Critical → Info)

### CRITICAL

#### Q1. CI pipeline cannot fail — every job neutralizes its own exit code
**File:** `.github/workflows/ci.yml` (repo-wide pattern; representative lines below)
**Evidence:**
```yaml
# line 55  (unit-tests job — the one job that runs the actual test suite)
-x --tb=short 2>/dev/null || echo "Tests completed"
# line 79  (coverage-threshold check)
        continue-on-error: true
# line 99  (integration-tests job)
    continue-on-error: true  # Don't fail the workflow if simulators unavailable
# line 190 (lint job)
ruff check services/ voice/ nightwatch/ --ignore=E501,F401,F841 --output-format=github || true
# line 195-196 (format check)
ruff format --check services/ voice/ nightwatch/ || echo "::warning::Some files need formatting"
        continue-on-error: true
# line 228 (type-check, nightwatch/) — no continue-on-error at all, but:
mypy nightwatch/ ... --pretty || echo "::warning::Type errors found in nightwatch/"
# lines 237, 246, 271, 331, 340, 437, 446, 469, 487 — continue-on-error: true
```
Every job in this workflow does one or both of: (a) end its real command with
`|| true` / `|| echo "..."`, which makes the shell step exit 0 regardless of the underlying tool's exit
code, or (b) set `continue-on-error: true` at the job or step level. I verified by literal count: of
the 9 jobs in this file, **8 have `continue-on-error: true`** on at least one step or the whole job, and
**every single job** that runs pytest/ruff/mypy/bandit appends a `|| true`/`|| echo` shell escape after
the tool invocation. The **only** step in the entire file with neither pattern is `docker-validation`'s
"Validate docker-compose files" (`docker compose -f docker/docker-compose.dev.yml config --quiet`) —
I ran this exact command locally; it exits 0 (with a harmless `version:` deprecation warning), so even
that one theoretically-gating step currently passes.
**Why it matters:** The green CI badge in `README.md` line 4 certifies nothing. A PR that fails every
single unit test, has 3,000 lint errors, and fails every mypy check would still show all-green CI. This
is the root cause enabling every other finding in this report to go unnoticed (the pyindi-client install
failure, the numpy test-pollution failures, the `test_power.py` hang, the orchestrator double-save bug,
the 233 mypy errors, the 2585 ruff errors, all currently invisible in CI).
**Smallest credible fix:** Remove `continue-on-error: true` from the `unit-tests` job and drop the
`2>/dev/null || echo "Tests completed"` suffix from the pytest invocation at minimum (that one job is
the actual regression gate). Everything else can stay soft (integration/e2e/docker-simulator jobs
depending on external images are legitimately best-effort), but that should be a deliberate, documented
choice, not the accidental default for every job including unit tests and linting.

#### Q2. Documented install path is broken on a clean machine
**File:** `services/requirements.txt:15`
**Evidence:**
```
pyindi-client~=2.0.8
```
`pip install -r services/requirements.txt` — the literal first command after `git clone`/`cd` in
`README.md`'s "v0.1 Quickstart", `docs/QUICKSTART.md` step 3, and `docs/INSTALLATION.md`'s manual-install
step 5 — fails immediately:
```
ERROR: Could not find a version that satisfies the requirement pyindi-client~=2.0.8
(from versions: ... 0.2.8, 1.9.1, 2.1.3, 2.1.4, ... 2.2.0)
ERROR: No matching distribution found for pyindi-client~=2.0.8
```
No `2.0.x` release of `pyindi-client` has ever existed on PyPI (it jumps `0.2.8` → `1.9.1` → `2.1.3`).
I verified in a fresh, empty venv that this failure is atomic: **zero** packages (not even `skyfield`,
`aiohttp`, `pyserial`, which resolve fine on their own) get installed, because pip's resolver aborts the
whole multi-package install when one requirement is unsatisfiable. This is exactly why CI's own
equivalent step (`pip install -r services/requirements.txt || true`, ci.yml:41) has been silently
no-op-ing since whenever this pin was introduced — the entire `unit-tests` job in CI has likely been
running with `skyfield`/`aiohttp`/`pyserial`/`alpyca` all absent, silently, for some unknown period.
**Why it matters:** This is the single most direct "does the documentation work" test this audit
performed, and it fails at the very first command. Combined with Q1, nobody would know.
**Smallest credible fix:** Pin to an existing version (`pyindi-client~=2.1.3` or newer, or drop the
`~=` in favor of `>=2.1,<3` if the exact minor-version compatibility hasn't been verified) and re-run
the documented install on a clean machine before merging any change to this file.

#### Q3. Test-suite hygiene bug: unscoped global `numpy` mock replacement corrupts unrelated tests
**File:** `tests/unit/test_piper_service.py:27`, `tests/unit/test_whisper_service.py:35`
**Evidence:**
```python
# tests/unit/test_piper_service.py:22-27
mock_numpy = MagicMock()
mock_numpy.frombuffer = MagicMock(...)
mock_numpy.float32 = 'float32'
mock_numpy.int16 = 'int16'
sys.modules['numpy'] = mock_numpy          # <-- module-level, no fixture, no teardown
```
Both files replace the real `numpy` module in `sys.modules` **at import time, at module scope**, with
no `monkeypatch.setitem`/fixture/context-manager to restore it. Once either test file has been
collected in a pytest process, every subsequent test in that same process/worker that does `import
numpy` gets the `MagicMock` instead of the real library, for the rest of the run. I reproduced this in
isolation:
```
$ python3 -c "
import sys; sys.path.insert(0, 'tests/unit')
import test_piper_service          # triggers the module-level sys.modules['numpy'] = mock_numpy
from astropy.io import fits        # now breaks, even though astropy imports fine standalone
"
ModuleNotFoundError: No module named 'numpy._core'; 'numpy' is not a package
```
This is the root cause of the two `--collect-only` errors on a full `tests/unit/` run
(`test_plate_solver.py` fails to import `astropy.io.fits` only in the full run; standalone it collects
56 tests cleanly) and — by the same mechanism — the proximate cause of the great majority of the 48
test failures observed in a full run (see Q4 below): `test_catalog.py`, `test_ephemeris.py`,
`test_encoder_bridge.py`, `test_frame_analyzer.py`, `test_camera_service.py`, `test_focuser_service.py`,
`test_onstepx_extended.py`, `test_success_tracker.py`, `test_tool_executor.py::TestCoordinateParsing`,
and `test_voice_pipeline.py` all pass individually but fail in the full run; alphabetically,
`test_piper_service.py` collects before all of them.
**Why it matters:** The unit test suite's reported pass/fail counts are not trustworthy as written —
they depend on file collection order and worker assignment, not on the correctness of the code under
test. This means "run the suite, see what's red" is not currently a reliable signal for this codebase,
independent of CI's inability to fail (Q1).
**Smallest credible fix:** Replace the module-level `sys.modules['numpy'] = mock_numpy` with a
function/class-scoped `monkeypatch.setitem(sys.modules, "numpy", mock_numpy)` fixture (pytest's
built-in `monkeypatch` restores `sys.modules` automatically at teardown), or better, mock at the
specific import site inside the module under test rather than globally. Given real `numpy` is a
declared, installable dependency (`voice/requirements.txt`), consider dropping the mock entirely and
using the real (small, fast) `numpy` in these tests.

#### Q4. Real, reproducible test failures that CI would never show
**File(s):** `services/power/power_manager.py:792,1169`; `nightwatch/orchestrator.py:2059,2391`
**Evidence (hang):**
```python
# services/power/power_manager.py:792
power_restore_delay_sec: float = 300.0  # Wait after power restored
...
# power_manager.py:1168-1169, inside _on_power_restored()
logger.info(f"Waiting {self.config.power_restore_delay_sec}s before resume")
await asyncio.sleep(self.config.power_restore_delay_sec)
```
`tests/unit/test_power.py::TestPowerManagerEmergency::test_simulate_power_failure` calls
`manager.simulate_power_failure(0.1)` expecting it to resolve in ~0.1s, but
`simulate_power_failure()` unconditionally calls `_on_power_restored()`, which unconditionally sleeps
the **production default** of 300 real seconds before returning — the short `duration_sec` argument is
never threaded through to that delay. Reproduced directly:
```
FAILED tests/unit/test_power.py::TestPowerManagerEmergency::test_simulate_power_failure
E   Failed: Timeout (>60.0s) from pytest-timeout.
```
This test would time out under pytest.ini's own global 120s timeout in any real run, and did in both a
parallel (`-n auto`) and serial run performed for this audit.

**Evidence (double-write bug):**
```python
# nightwatch/orchestrator.py — _safe_shutdown()
        if self.session.is_observing:
            await self._save_session_log()        # line 2059
            await self.end_session()               # end_session() ALSO calls _save_session_log()
# nightwatch/orchestrator.py:2391, inside end_session()
        await self._save_session_log()
```
Reproduced:
```
FAILED tests/unit/test_orchestrator.py::TestSafeShutdown::test_save_session_log
E   AssertionError: Expected '_save_session_log' to have been called once. Called 2 times.
```
`_safe_shutdown()` saves the session log and then calls `end_session()`, which saves it again — a real,
currently-failing-test-confirmed duplicate write of the session JSON log on every safe shutdown while
observing.
**Why it matters:** Both are genuine defects (not environment noise, unlike most of Q3's failures), both
have a failing test that correctly catches them, and neither is visible in CI today because of Q1.
**Smallest credible fix:** For the hang: add a `power_restore_delay_sec` override in the test fixture
(or thread `duration_sec`'s scale into the restore delay in `simulate_power_failure`) so the test
actually completes in test time. For the double-save: remove the direct `await
self._save_session_log()` call at `orchestrator.py:2059` and let `end_session()` (which already saves
it) be the single source of truth, or vice versa — pick one call site.

---

### HIGH

#### Q5. Duplicate, diverging pytest configuration — half of it is silently dead
**File:** `pytest.ini` (wins) vs. `pyproject.toml:250-296` (`[tool.pytest.ini_options]`, ignored)
**Evidence:** Both files define a complete pytest configuration. Pytest's own discovery rule uses
`pytest.ini` if present and ignores `[tool.pytest.ini_options]` in `pyproject.toml` entirely — confirmed
empirically (`pytest --collect-only` prints `configfile: pytest.ini` and reports `timeout: 120.0s`,
matching `pytest.ini`'s `timeout = 120`, not `pyproject.toml`'s `timeout = 30`). Concretely, because
`pyproject.toml`'s block is dead:
- `--strict-markers` (declared only in `pyproject.toml:270`) is **not active** — using an unregistered
  marker only warns instead of failing collection. Confirmed: running `tests/e2e/` prints
  `PytestUnknownMarkWarning: Unknown pytest.mark.e2e - is this a typo?` for every `@pytest.mark.e2e` use,
  because `pytest.ini`'s `markers =` list (`alpaca`, `indi`, `slow`, `hardware`) never registered `e2e`,
  `integration`, or `unit` — those three are only declared in the dead `pyproject.toml` block.
- The effective per-test timeout is 120s, not the 30s `pyproject.toml` documents.
**Why it matters:** Anyone editing `pyproject.toml`'s pytest section (the more "modern"-looking,
consolidated location, and the one that also hosts ruff/mypy/coverage config) believes they're changing
test behavior; they are not. This is exactly the kind of drift that causes confusion during onboarding
and silent behavior differences between what a new contributor reads and what actually runs.
**Smallest credible fix:** Delete one of the two configuration blocks. Given `pyproject.toml` already
centralizes ruff/mypy/coverage config, move `pytest.ini`'s content into
`[tool.pytest.ini_options]`, delete `pytest.ini`, and confirm markers/timeout via
`pytest --collect-only` afterward.

#### Q6. Coverage is measured at 48.25%, below both of two different unenforced thresholds
**File:** `pyproject.toml:322`; `.github/workflows/ci.yml:69-77`
**Evidence:** `pyproject.toml` declares `fail_under = 60` with the comment "Start low, increase to 80%
as tests are added" (line 322). CI separately hand-parses `coverage.xml` and hardcodes `THRESHOLD=80`
(ci.yml:69), matching the comment's aspirational endpoint rather than the configured floor — and, per
Q1, only ever emits a `::warning::`, never fails. Running the documented coverage invocation on this
audit's from-scratch environment (`pytest tests/unit/ --cov=nightwatch --cov=services --cov=voice`)
produced:
```
TOTAL   24490  11638   7538    725  48.25%
FAIL Required test coverage of 60.0% not reached. Total coverage: 48.25%
```
i.e., `coverage`'s own `fail_under=60` correctly detects and reports failure — that exit code is simply
never consulted by CI, which instead re-derives a coverage percentage from `coverage.xml` via a
different, hardcoded-80% script.
**Why it matters:** Three different numbers (48.25% actual, 60% configured floor, 80% CI's own
aspiration-as-if-it-were-a-gate) exist for the same concept, and none of them currently affects anything.
**Smallest credible fix:** In the `unit-tests` job, run `coverage report --fail-under=60` (reusing
`pyproject.toml`'s own configured value) as its own step without a `|| true`/`continue-on-error`, and
delete the redundant hand-rolled XML-parsing/`THRESHOLD=80` script.
**Rough per-domain coverage impression** (from this run's `--cov-report=term-missing`, corroborating
each domain analyst's qualitative assessment): safety-critical/recently-touched modules
(`SAFE-*`/`ARCH-*` paths, `watchdog.py`, `config.py`) are well covered; the entire Wyoming voice-network
surface is nearly uncovered (`voice/wyoming/stt_server.py` 14.89%, `tts_server.py` 12.66%,
`startup.py` 18.90%); dormant/never-wired subsystems (`ToolChain`, `SafetyInterlock`,
`EmergencyResponse`, `ToolRegistry`/`create_default_handlers`) are covered only by tests that assert
their own isolated logic, never an integration path, consistent with every domain report's "designed,
tested-in-isolation, never wired" theme.

#### Q7. Broad exception handling is the default idiom, not the exception
**File:** repo-wide; example bare-except at `services/power/power_manager.py:309`
**Evidence:** 437 occurrences of `except Exception` across `nightwatch/`, `services/`, `voice/`
(repo-wide grep), against only 18 occurrences of any explicit `asyncio.wait_for`/`asyncio.timeout`
pattern. One bare `except:` (catches `BaseException`, including `KeyboardInterrupt`/
`asyncio.CancelledError`) exists at `services/power/power_manager.py:309`:
```python
try:
    return await response.json()
except:
    return {"success": True}
```
— inside the PDU (Power Distribution Unit) HTTP command path; a malformed JSON response from real
power-control hardware is silently reported as a **successful** power operation.
**Why it matters:** This is not a one-off — it is the dominant error-handling strategy in the codebase
(confirmed independently; matches the Astronomy domain analyst's per-file counts: 53 in
`alpaca_client.py`, 40 in `asi_camera.py`, 22 in `roof_controller.py`, 21 in `power_manager.py`). The
astronomy domain's two confirmed `AttributeError` safety bugs (Q1 above and the `SafetyMonitor.
_action_callback` bug) are directly hidden by this pattern: `except Exception as e: logger.error(...)`
around a hardware call turns a code defect into a quiet log line instead of a loud failure.
**Smallest credible fix:** Start with the two safety-relevant sites already identified
(`roof_controller.py`'s `close()`/`open()` catch blocks, `power_manager.py:309`): narrow the caught
exception type, and — at minimum for the power/roof paths — re-raise or return an explicit failure
sentinel rather than a bare `True`/silently-logged `False` that looks identical to "nothing was wrong."

#### Q8. Lint and type-check debt is large and entirely unenforced
**File:** repo-wide (`ruff`, `mypy` runs performed by this audit)
**Evidence:**
```
$ ruff check services/ voice/ nightwatch/ --ignore=E501,F401,F841   # CI's own ignore list
Found 2585 errors. [1744 fixable with --fix]
    922 UP045   554 UP006   191 F821   164 PLC0415   133 UP035   93 I001 ...
$ mypy nightwatch/ --ignore-missing-imports --show-error-codes
Found 233 errors in 23 files (checked 18 source files)
    129 [no-untyped-def]  33 [arg-type]  21 [annotation-unchecked]  18 [assignment]  17 [attr-defined] ...
```
191 `F821` (undefined name) findings are not purely stylistic — a sample confirms real, if
low-severity, defects: `nightwatch/voice_pipeline.py:299,2359` use `Tuple[bool, str]` as a return
annotation without importing `Tuple` (harmless today only because
`from __future__ import annotations` at line 25 defers evaluation — `typing.get_type_hints()` on this
class would raise `NameError`); dozens more `F821`s are inside `voice/tools/telescope_tools.py`'s
dormant `create_default_handlers()` closures (`mount_controller`, `camera_client`, `guider_client`,
etc. — undefined names inside ~4100 lines of code that, per the Command Execution domain report, has no
production caller). mypy independently rediscovers the core domain analyst's headline bug: `mypy`
flags `nightwatch/main.py:325` as `error: Unexpected keyword argument "level" for "setup_logging"
[call-arg]` — proof that gating `mypy` in CI would have caught the entry-point crash (Q2 in
`20-domain-core-orchestration-safety.md`) before it ever shipped.
**Why it matters:** `mypy nightwatch/` — the one package explicitly configured for stricter checking
(`disallow_untyped_defs = true` per-module override, `pyproject.toml:236`) — would have caught the
literal reason `python -m nightwatch.main` cannot start. It runs in CI (ci.yml:220-231) but its failure
is discarded by `|| echo "::warning..."` with no `continue-on-error` even needed to hide it.
**Smallest credible fix:** Make the `mypy nightwatch/` step (only — services/voice can stay
warning-only given their looser typing posture) an actual gate: drop the `|| echo` suffix. For ruff,
run `ruff check --fix` once locally to absorb the 1744 auto-fixable findings and re-baseline, then gate
on the remainder.

#### Q9. `ruff format --check` fails on the large majority of the codebase
**File:** repo-wide
**Evidence:**
```
$ ruff format --check services/ voice/ nightwatch/
72 files would be reformatted, 25 files already formatted
```
i.e. 74% of files are not compliant with the project's own declared formatting style
(`[tool.ruff.format]`, `pyproject.toml:180-188`), despite `.pre-commit-config.yaml` listing `ruff-format`
as a hook and CI running the identical check (ci.yml:194-196, muted by `continue-on-error: true` and a
`|| echo` besides).
**Why it matters:** Formatting is the cheapest possible category of "quality gate," and it is not being
met — a signal that `pre-commit install` is not actually being run by the sole active contributor (see
Q11 below), since the pre-commit hook would auto-fix this on every commit if installed.
**Smallest credible fix:** Run `ruff format services/ voice/ nightwatch/` once, commit the
reformat as its own change, and confirm `pre-commit install` is actually active locally
(`.git/hooks/pre-commit` should exist and invoke `pre-commit`).

#### Q10. `tests/hardware/*.py` are not real pytest tests and never have been
**File:** `tests/hardware/test_mount.py:24,92` (and `test_cloud_sensor.py`, `test_encoder.py`,
`test_voice.py`, `test_weather.py`)
**Evidence:**
```python
class MountCommunicationTest:          # does NOT match pytest's default `Test*` class pattern
    ...
    def test_get_ra(self) -> bool:     # method name matches, but the class doesn't
```
`pytest tests/hardware/ --collect-only` collects **0 items**, despite each file containing 7-8
`def test_*` methods. This is because pytest's default `python_classes = Test*` (set explicitly in both
`pytest.ini:10` and the dead `pyproject.toml:256`) never matches classes named
`MountCommunicationTest`/`CloudSensorTest`/etc. — these files are CLI-runnable verification scripts
(`python -m tests.hardware.test_mount --host ...`, per their own docstrings) that happen to reuse the
`test_` method-naming convention, not pytest tests.
**Why it matters:** `00-inventory.md` §7.3 and the `hardware` marker's own docstring
("skip in CI") imply these are real, deliberately-skipped tests. They are not "skipped" — they were
never collectible in the first place, under any marker selection. Nobody has run a
`pytest -m hardware` invocation against real telescope hardware and gotten a pass/fail signal from
these files; they can only be run as standalone scripts.
**Why High, not Info:** this is a documentation-vs-reality gap specifically about test-suite
capability claims, directly relevant to "does the test suite actually verify what people believe it
verifies" — the same theme as Q1/Q3/Q4.
**Smallest credible fix:** Either rename the classes to start with `Test` (and adapt them to use
`assert` instead of `return bool`, since pytest doesn't collect return-value-based "tests"), or
rename the files to a non-`test_*` pattern (e.g. `verify_mount.py`) and document them explicitly as
manual scripts, not part of the automated suite.

---

### MEDIUM

#### Q11. Pre-commit hooks are "mandatory" only in the sense that nothing enforces them
**File:** `.pre-commit-config.yaml`; `.github/workflows/ci.yml` (no `pre-commit run` step anywhere)
**Evidence:** `00-inventory.md` §7.7 characterizes pre-commit hooks as "Mandatory," but they are
git-hook-based, opt-in per clone (`pre-commit install`), and CI never runs `pre-commit run
--all-files` as a backstop — it re-implements a subset of the same checks (ruff, mypy, bandit)
independently and, per Q1, without gating. Q9's finding (74% of files fail `ruff format --check`)
is itself strong evidence the hooks are not actually installed/active for the current contributor.
**Smallest credible fix:** Add a `pre-commit run --all-files` CI job as an actual gate; this
single job would also subsume most of the standalone lint/type-check/security jobs.

#### Q12. `constants.py` duplicates and has drifted from the real safety-threshold source of truth
**File:** `nightwatch/constants.py:35,45,49` vs. `nightwatch/config.py:489-501`
**Evidence:**
```python
# nightwatch/constants.py
WIND_LIMIT_MPH: Final[float] = 25.0
HUMIDITY_LIMIT_PERCENT: Final[float] = 85.0
TEMP_MIN_F: Final[float] = 20.0
# nightwatch/config.py — the real, live SafetyConfig has three tiers per parameter
wind_limit_warning: float = Field(...)
wind_limit_park: float = Field(...)
wind_limit_emergency: float = Field(...)
```
Confirmed by direct read of both files: `constants.py`'s flat single-value thresholds are imported by
nothing outside `nightwatch/__init__.py`'s convenience re-export (repo-wide grep), yet a future
engineer grepping for "wind limit" would find this file first and could easily wire a new code path to
the stale, wrong value.
**Smallest credible fix:** Delete the safety-threshold section of `constants.py` (or replace it with a
comment pointing to `SafetyConfig`); keep only constants that have no config-driven equivalent.

#### Q13. Two documented entry points don't exist
**File:** `README.md` ("`python -m nightwatch.cli --simulate`"), `docs/QUICKSTART.md`
("`python -m nightwatch.cli --simulate`", "`from nightwatch.services import mount, weather, safety`")
**Evidence:** `nightwatch/cli.py` does not exist (`ls nightwatch/` confirmed); `nightwatch/services.py`
and `nightwatch/services/` do not exist — `services/` is a top-level package, not a `nightwatch`
subpackage. Both commands were run literally and both fail with `ModuleNotFoundError`. The real,
working entry points are `python -m nightwatch.main` (itself broken per Q2 in the security report /
confirmed above) and `from services import mount, weather, safety` (no `nightwatch.` prefix).
**Smallest credible fix:** Update both docs to the real invocation, and add a documentation-drift
check (even a simple `grep`-based CI step that tries importing every `python -c "..."` snippet found in
`docs/*.md`) so this class of drift is caught mechanically.

#### Q14. Duplicate `SafetyInterlockError` exception classes with incompatible constructors
**File:** `nightwatch/exceptions.py:263` vs. `nightwatch/safety_interlock.py:552`
**Evidence:** (as reported by the Core Orchestration analyst, re-confirmed by grep for both class
definitions) two unrelated `SafetyInterlockError` classes exist with different constructor signatures
and no common base beyond `Exception`; `except nightwatch.exceptions.SafetyInterlockError` would not
catch the one `safety_interlock.py`'s own decorator raises.
**Smallest credible fix:** Delete one; have `safety_interlock.py` import and raise
`nightwatch.exceptions.SafetyInterlockError` instead of shadowing the name.

#### Q15. `nightwatch/exceptions.py` and `nightwatch/types.py` are largely unreferenced scaffolding
**File:** `nightwatch/exceptions.py`, `nightwatch/types.py`
**Evidence (trusted from Core Orchestration domain report, structurally consistent with this audit's
own grep-based dead-code checks elsewhere):** most subclasses of `NightwatchError` and most of
`types.py`'s ~40 aliases/Protocols are used nowhere outside their own module and
`nightwatch/__init__.py`'s convenience re-export.
**Smallest credible fix:** Not urgent; flag as a maintainability candidate for pruning during the next
pass over `nightwatch/__init__.py`'s public surface, alongside Q12.

#### Q16. `docker-validation`'s `docker compose config` uses an obsolete key without cleanup
**File:** `docker/docker-compose.dev.yml:18` (`version: '3.8'`)
**Evidence:**
```
time="...Z" level=warning msg="/home/user/NIGHTWATCH/docker/docker-compose.dev.yml: the attribute
`version` is obsolete, it will be ignored, please remove it to avoid potential confusion"
```
Not itself a failure, but the one CI step capable of failing (Q1) is currently passing only by luck of
Compose's backward compatibility; a stricter Compose version could turn this into the pipeline's first
real failure with nobody having touched the file.
**Smallest credible fix:** Remove the `version:` key from all three `docker-compose.*.yml` files.

#### Q17. `RELEASE_v0.1.0.md` overclaims relative to verified reality, and carries a stale date
**File:** `RELEASE_v0.1.0.md:3,29`
**Evidence:** "**Release Date:** January 2024" — two years before this repository's first commit
(2026-01-20 per `10-history.md`), clearly an unedited template artifact. The same document asserts
"Safety veto system for all operations" as a shipped v0.1.0 feature; this audit and the security report
both independently confirmed the emergency roof-close path silently fails (Q1/Astronomy domain finding),
`SafetyInterlock`/`EmergencyResponse` are never wired into production (Core Orchestration finding), and
the LLM-side confirmation gate for critical tools (`requires_confirmation`) references tool names that
the validation layer would already reject (LLM Client finding).
**Smallest credible fix:** Correct the date; soften "Safety veto system for all operations" to describe
what is actually wired (the `services/safety_monitor` continuous loop) versus what is designed-but-not-
integrated, so the release notes don't actively mislead a reader assessing production readiness.

---

### LOW

#### Q18. God-files concentrate churn, complexity, and single-author risk simultaneously
**File:** `nightwatch/orchestrator.py` (3446 lines), `voice/tools/telescope_tools.py` (5662 lines,
the largest file in the repo), `nightwatch/voice_pipeline.py` (2517 lines), `services/camera/
asi_camera.py` (2494 lines), `services/focus/focuser_service.py` (2414 lines)
**Evidence:** Cross-referencing `10-history.md`'s churn table (orchestrator.py: 10 commits;
asi_camera.py: 7 commits; both single-author) against file size confirms the historian's
"churn × complexity = danger" heuristic concretely: the two highest-churn non-test files are also
among the five largest files in the repository, and both carry independently-confirmed live defects
(Q4's double-save-log bug in `orchestrator.py`; camera race-condition history noted by the astronomy
domain report, addressed but only partially verifiable given review depth).
`voice/tools/telescope_tools.py` is the largest file in the repo (5662 lines) but per the Command
Execution domain report, roughly 4100 of those lines (`create_default_handlers()`) are dead code
(no production caller) — meaning the single largest file in the codebase is majority-unreachable.
**Smallest credible fix:** No single fix; flag `orchestrator.py` as the top candidate for extraction
(service registry / session state / event bus / restart policy are each independently coherent
modules per the Core Orchestration domain report's own module table) and `telescope_tools.py` as the
top candidate for deletion-or-integration triage (either wire `ToolRegistry` up for real, or delete the
~4100 dead lines).

#### Q19. `docs-validation` and `security-scan` CI jobs check for real signals but only ever warn
**File:** `.github/workflows/ci.yml:295-331` (docs), `:400-469` (security)
**Evidence:** The `bandit` run performed by this audit for corroboration found 104 low + 13 medium
(0 high) severity issues, 105 of them at high confidence (i.e., likely real, not false-positive noise)
— none of which can affect CI regardless of severity, per Q1.
**Smallest credible fix:** Covered by Q1's general fix; specifically for bandit, consider gating on
`-iii -lll` (high confidence + high severity only) as a starting bar that's unlikely to produce false
failures, and ratchet down over time.

#### Q20. `requirements-dev.txt` documents an install order it doesn't enforce
**File:** `requirements-dev.txt:8-10`
**Evidence:** Comment says "Install order: services/requirements.txt, voice/requirements.txt,
requirements-dev.txt" but nothing checks this order was followed, and (per Q2) the first of the three
commands in that order currently fails outright.
**Smallest credible fix:** Once Q2 is fixed, add a single `make bootstrap`/`./scripts/dev-setup.sh`
that runs all three in order and fails loudly, rather than relying on a contributor reading a comment.

#### Q21. `services/nlp` conversation/preference state has no per-user isolation, undocumented
**File:** `services/nlp/conversation_context.py:717-730` and sibling `get_*()` factories
**Evidence (trusted from Voice/NLP domain report, no independent re-verification needed beyond
confirming the module-level global factory pattern by inspection):** every `services/nlp` submodule
exposes a process-wide singleton with no session key.
**Smallest credible fix:** Document the single-user assumption explicitly in each module's docstring
until multi-session support is designed; not urgent given the domain isn't wired into production today.

#### Q22. No git tags / semantic versions to correlate against quality regressions
**File:** repo-wide (`git tag -l` returns nothing, per `10-history.md` §5.4)
**Evidence (trusted from historian):** zero releases tagged in 61 commits.
**Why relevant to quality (not just release hygiene):** without tags, this audit's findings (and any
future one) cannot be pinned to "as of version X" — the next audit has no fixed point to diff against
to measure whether the pass rate, coverage %, or lint-error count is trending up or down.
**Smallest credible fix:** Tag the current `HEAD` (or the next stable point) as `v0.1.0-alpha` before
merging further large changes, per the historian's own recommendation.

---

### INFO

#### Q23. mypy's own summary line is internally inconsistent
**Evidence:** `mypy nightwatch/` prints `Found 233 errors in 23 files (checked 18 source files)` —
23 files with errors out of only 18 checked is impossible at face value; likely an artifact of mypy's
error-vs-file-count bookkeeping across `.pyi`/cache boundaries rather than a real repo defect. Noted for
completeness; not investigated further given it doesn't change the headline finding (mypy surfaces 233
real, actionable errors in the one package meant to be held to a higher bar).

#### Q24. Coverage config technically supports branch coverage, not exercised in this audit's number
**Evidence:** `pyproject.toml:305` sets `branch = true`; the 48.25% figure cited in Q6 is `coverage`'s
combined line+branch metric as reported by its own summary line, not a hand-computed line-only number
— reported as-is for consistency with what a contributor running the documented command would see.

#### Q25. `.claude/` agent configuration and `pos/agents/` are outside this audit's scope but present
**Evidence:** Present in the repository per `00-inventory.md` §7.6; not a code-quality concern, noted
only so the scorecard below doesn't appear to have silently ignored a repository component.

#### Q26. This audit's own environment required manual workarounds not available to CI
**Evidence:** To get a runnable environment at all, this audit had to skip `pyindi-client` (Q2),
install `services/requirements.txt`'s remaining packages individually, and exclude 2 test files from
collection to get a full-suite number. A brand-new contributor following only the README would stop at
Q2 and never reach any of the numbers in this report. Recorded here explicitly per the audit contract's
"try the documented commands literally" instruction.

---

## Assessment by required dimension

### 1. Test reality
- **Does the suite exist?** Yes — 2618 collected unit tests across `tests/unit/` (110 files per
  inventory), plus 312 integration tests and 74 e2e tests collected cleanly (`tests/integration/`,
  `tests/e2e/`), plus 5 non-functional "hardware" scripts (Q10) that collect 0 pytest items.
- **Does it run?** Mostly, with caveats. `tests/unit/` ran to completion twice in this environment
  (parallel: 300s / 4 workers; serial: 358s) after resolving the Q2 dependency-install gap manually.
  Two files fail to collect at all in a full run (`test_safety_monitor.py` — hardcoded
  `/workspaces/NIGHTWATCH` path at line 16, a devcontainer-specific absolute path that doesn't exist
  here or presumably in GitHub Actions' `ubuntu-latest` runners either; `test_plate_solver.py` — Q3's
  cross-file pollution). `tests/integration/` and `tests/e2e/` were **not** executed end-to-end in this
  environment: they require Docker-based device simulators
  (`docker/docker-compose.dev.yml`'s `alpaca-simulators`, `indi-server` images) that this sandboxed
  environment cannot pull/run in the time budget available, and per CI's own comments
  ("Note: This job may fail if simulator images aren't available... Tests skipped gracefully") this is
  an accepted, documented limitation of the project's own test strategy, not unique to this audit.
  Collection-only was verified clean for both (312 and 74 items respectively).
- **Does it pass?** As documented (`pytest tests/unit/ -v`), from a clean environment: **2570
  passed, 48 failed, 2 collection errors**. Root-cause sampling (Q3) shows the great majority of the
  48 failures are test-infrastructure artifacts (global `numpy` mock pollution), not product defects —
  but two are genuine, previously-undetected-in-CI bugs (Q4). Net assessment: **the underlying
  production code is in noticeably better shape than a naive "48 failed" reading suggests, but the test
  suite's own hygiene is bad enough that this fact is not discoverable without the kind of manual
  root-causing this audit performed.**
- **Rough coverage impression per domain:** 48.25% total (line+branch combined, per `coverage`'s own
  reporting) against a configured-but-unenforced 60% floor. Bimodal by domain, consistent with every
  domain report: safety-critical/recently-touched code (SAFE-*/ARCH-* paths) well covered;
  `voice/wyoming/*` server code (12-19%) and every "designed, never wired" subsystem
  (`SafetyInterlock`, `EmergencyResponse`, `ToolChain`, `ToolRegistry`) covered only in isolation, never
  through an integration path that would catch a wiring bug.

### 2. CI/CD gating
Covered in depth at Q1. Summary: **nothing currently gates.** The one theoretically-gating step
(`docker compose config --quiet`) passes today. Everything else — unit tests, integration tests,
lint, format, type-check, security scan, docs validation, e2e — either soft-fails via
`continue-on-error: true`, hard-swallows via `|| true`/`|| echo`, or both. The task's pointer to the
known-broken `mock-weather` service container (ci.yml:344-346, `options: --entrypoint "python -m
http.server 8080"` — passing a full command line as a Docker `--entrypoint`, which Docker requires to
be a single executable path, not a command-with-arguments string) is confirmed present and is itself
symptomatic of the same root problem: that job (`integration-tests-simulators`) has
`continue-on-error: true` at the job level (ci.yml:340), so this broken service container has
presumably never blocked anything and nobody has needed to notice or fix it.

### 3. Error handling
Not a "designed strategy, ad hoc in practice" split so much as **one dominant, deliberately broad
strategy applied almost everywhere** (437 `except Exception` sites, Q7), which is internally consistent
(the domain reports and this audit agree it's a deliberate "the monitoring loop must keep running"
design choice for the safety-monitor's own loop) but is applied uniformly even to call sites where it
actively hides defects (the two `AttributeError` bugs in `roof_controller.py`/`SafetyMonitor`, and the
bare-except at `power_manager.py:309`). Timeouts are comparatively rare (18 explicit
`asyncio.wait_for`/`asyncio.timeout` uses) relative to the volume of network/serial/subprocess I/O in
`services/`; several domain reports note specific missing-timeout risks (sync mount I/O not wrapped in
`asyncio.to_thread`, PHD2's `readline()`-based framing) that this audit did not independently
re-verify but has no reason to doubt.

### 4. Type safety and lint posture
Configs are comprehensive and reasonably modern (`ruff` with a wide rule selection, `mypy` with a
per-module stricter override for `nightwatch/`, `pydantic.mypy` plugin). Enforcement is **effectively
zero** in CI (Q1, Q8) and inconsistent locally (pre-commit exists but Q9/Q11 suggest it isn't actively
used by the current contributor). Suppression density is *low*, not high — zero `# type: ignore`
comments anywhere, only 11 `# noqa` comments repo-wide — meaning the 2585 ruff / 233 mypy findings are
not being hidden behind suppressions; they are simply not being looked at. This is a different, in some
ways healthier, failure mode than "everything is `# noqa`'d into silence," but the practical effect
(errors accumulate, unfixed) is the same.

### 5. Maintainability vs. churn
Cross-referencing `10-history.md`'s churn table against file size and this audit's own findings
confirms the historian's "churn × complexity = danger" heuristic in two concrete cases:
`orchestrator.py` (highest churn, 3446 lines, contains the confirmed Q4 double-save bug and the
confirmed dead `EventBus`/`CommandQueue` subsystems) and `services/camera/asi_camera.py` (second-highest
churn, 2494 lines, documented race-condition history). The single largest file in the repository,
`voice/tools/telescope_tools.py` (5662 lines), is majority dead code (≈4100 of its lines are an
unreachable second tool-dispatch stack per the Command Execution domain report) — a dead-code
candidate large enough to be worth a dedicated deletion-or-integration decision rather than incremental
cleanup. `nightwatch/constants.py` and `nightwatch/types.py` are smaller-scale duplication/dead-code
candidates (Q12, Q15).

### 6. Developer experience
Tried literally, in order, as a newcomer would from `README.md`:
1. `git clone` / `cd` — fine.
2. `python -m venv .venv && source .venv/bin/activate` — fine.
3. `pip install -r services/requirements.txt` — **fails outright** (Q2). A newcomer following the
   README stops here.
4. Working around Q2 to continue: `pytest tests/unit/ -v` — runs, reports `48 failed` (Q3/Q4) with
   no indication most of those are test-infrastructure noise rather than product bugs; a newcomer has
   no way to know which is which without the kind of manual investigation this audit performed.
5. `python -m nightwatch.cli --simulate` (README's own next step) — **`ModuleNotFoundError`**, the
   module doesn't exist (Q13).
6. `python -m nightwatch.main --dry-run` (the actual, real entry point, per `nightwatch/main.py`'s
   own `if __name__ == "__main__"` block and `pyproject.toml`'s `[project.scripts]`) —
   **`TypeError: setup_logging() got an unexpected keyword argument 'level'`**, reproduced live,
   matching the Core Orchestration domain's confirmed finding exactly.

**Net assessment:** a newcomer following the documented path literally cannot get a running system, and
cannot even get past the first `pip install` command without independently discovering and working
around Q2. Every subsequent documented milestone (verify via tests, run in simulation mode, run for
real) also fails as written. This is the single clearest, most reproducible finding in this entire
audit.

---

## Health scorecard

| Domain | Grade | Justification |
|---|---|---|
| **Core Orchestration & Safety** | **D** | The literal, documented entry point crashes on every invocation (`setup_logging(level=...)`, reproduced live); mypy would have caught it and is muted in CI. `orchestrator.py` is a 3446-line, single-author, highest-churn god-file containing a confirmed duplicate-write bug (Q4) and several fully-built-but-never-wired safety subsystems (`SafetyInterlock`, `EmergencyResponse`, `EventBus`, `CommandQueue`). Config/constants drift (Q12) and a dangling `CLAUDE.md` governance reference compound the picture. Test coverage is bimodal but decent where it counts (SAFE-*/ARCH-* paths). |
| **Voice & NLP** | **D+** | Entire domain (STT, TTS, Wyoming servers, all of `services/nlp`) has had exactly one commit since 2026-01-20 and is demonstrably disconnected from the running application (mock silent audio returned instead of real Piper synthesis; NLP import commented out). Measured coverage on the Wyoming network-facing code is 12-19%, the lowest in the repository, on code this audit and the domain analyst agree is a real unauthenticated-network-input attack surface. Confidence scoring is a hardcoded placeholder that silently defeats a documented feature. Well-tested in isolation; essentially untested and unreachable in integration. |
| **Command Execution & Tool Integration** | **C-** | The one link that would make the other four domains' work reachable from a real voice command — the tool-schema import from `voice/tools/telescope_tools.py` into `voice_pipeline.py` — is broken and fails silently (`ImportError` swallowed to a `warning`, confirmed by this audit via `find`/grep). The single largest file in the repository (5662 lines) is majority dead code behind an unreachable second dispatcher. The live path (`ToolExecutor`, 18 registered tools) is comparatively well-designed and reasonably tested, which is the main thing keeping this above a D. |
| **Astronomy & Hardware Services** | **D** | Contains the audit's most serious confirmed defect: the emergency roof-close path silently fails to move the motor (`AttributeError` on `self._gpio`, live-reproduced end-to-end by both this audit and the security report) — the exact scenario (roof open, emergency close commanded) that the domain exists to guarantee. A second, structurally identical `AttributeError` exists in the power-failure response path. Both are masked by the codebase's dominant broad-except idiom (437 occurrences) and by test doubles that patch around the buggy code paths rather than through them. 6 of ~21 service modules have been untouched since the initial commit. Parameterized SQL, safe subprocess invocation, and no eval/pickle/unsafe-YAML are genuine positives. |
| **LLM Client & Tool Binding** | **C** | Best-tested corner of the repository by a wide margin (dedicated, current, behavior-oriented tests for token accounting, tool-call validation, safety-context injection, cancellation) — but confirmed, independently, to be completely unreachable from the running application (`LLMClient`/`create_llm_client` have zero construction sites in `main.py`/`orchestrator.py`). The one safety-relevant mechanism unique to this domain, `requires_confirmation()`'s critical-tool gate, is simultaneously orphaned (no caller) and internally inconsistent (references tool names its own validation layer would reject first) — confirmed by this audit against `tool_params.py`'s actual registry. Good code, sitting on a bridge to nowhere. |
| **Cross-cutting: CI/CD** | **F** | No job in the pipeline can currently fail on a test, lint, type, or security regression, confirmed by literal line-by-line reading of every job plus reproducing the one exception (`docker compose config`) locally. This is the reason every other grade on this table is worse than the project's git history (disciplined commit messages, ADR/spec traceability) would suggest a reader should expect. |
| **Cross-cutting: Developer Experience** | **F** | The first documented install command fails on a clean machine (unsatisfiable `pyindi-client` pin); both of the two documented "run it" entry points (`nightwatch.cli`, `nightwatch.main`) fail as written, the second with a live-reproduced `TypeError`. Every one of these was verified by literally executing the documented commands, not inferred from source reading. |

**Overall:** a technically sophisticated, safety-conscious design (real ADR/spec discipline, a genuinely
thoughtful cooperative-cancellation architecture, parameterized SQL, no unsafe deserialization anywhere
found) sitting behind a documentation and CI layer that currently cannot detect regressions and a
developer-experience path that cannot be completed as written. The good news, established by actually
running the suite rather than trusting the badge: once the environment is coaxed into existing, the
core unit-level correctness rate is high (2570/2618, with most of the "48 failed" attributable to a
fixable test-hygiene bug rather than product defects) — the project's problem today is primarily
**visibility and wiring**, not a fundamentally broken codebase. Fixing Q1 (make CI able to fail) and Q2
(make the documented install work) would, on their own, make every other finding in this report visible
to the team going forward without further audits.
