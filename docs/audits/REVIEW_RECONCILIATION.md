> **HISTORICAL SNAPSHOT — archived 2026-08-06 during the v0.1.1 main-only consolidation.**
> This document audits the repository as of commit `7fa94a2` (2026-07/08). Its headline
> findings (startup crash, broken roof-close, dormant watchdog, advisory-only CI, driver
> bugs) were subsequently fixed by PRs #94-#110, and its line citations refer to a tree
> that no longer exists. Preserved from PR #90 as an engineering-history record; do not
> action findings from this file without re-verifying against current main.

# NIGHTWATCH — Review Reconciliation & Resumption Backlog

> **Purpose.** Two independent full-repository reviews were produced within three days of each
> other (PR #90 and PR #93) and never reconciled. This document collapses them into a **single
> prioritized backlog** so the next active development session has one source of truth instead of
> two overlapping audits. It also inventories two months of repo activity so we resume by
> *joining the highest-value effort* rather than starting a third parallel one.
>
> **Status:** orientation document. It changes no product code. It records a recommendation; the
> merge/close decisions on PRs #90 and #93 are deliberately left to the active session.
>
> **Provenance.** Reconciles `AUDIT_LANDSCAPE.md` (PR #90, reviewed at `eebdbac`) and the
> `docs/review/` corpus on branch `claude/install-review-org-37y4ck` (PR #93, reviewed at
> `cc61aa2`). The two headline findings below (startup crash, broken roof-close) were
> spot-re-verified against live source at the current branch HEAD before publishing.

---

## 1. Two-month landscape (2026-06-01 → 2026-08-01)

- **Nothing product-facing shipped to `main`.** Only two commits landed in the whole window —
  both on 2026-06-15, the `pos/` "Panel of Specialists" review workflow (tooling/docs). `main`
  head is `7fa94a2`, stale since mid-June.
- **All five open PRs are docs/tooling:** #93 review organization, #92 frontend prompt pack, #90
  this audit (draft), #91 repo-URL metadata fix (from a fork), #89 Cursor dev-env (draft). None
  merged.
- **~55 unmerged feature branches** carry real product code (NEO close-approach, hourly scanner,
  event journal, meteor/AMS integration) — but none merged, none with an open PR, most stale
  since March. See the triage table in §6.
- **The signal:** this repo has been *reviewed and scaffolded* far more than it has been
  *integrated*. Both reviews reach the same conclusion about the code itself, below.

---

## 2. The two reviews, and which to join

| | **PR #90 — `AUDIT_LANDSCAPE.md`** | **PR #93 — review organization + run** |
|---|---|---|
| Shape | Single static document | A standing 7-agent review *organization* (`.claude/agents/*` + `/full-review`) **plus** its first run under `docs/review/` |
| Depth | 121 findings, ~300 verified evidence items; 3 passes incl. a runtime pass | Ran the **full unit suite** (2570 pass / 48 fail / 2 err, 48% cov), **live-reproduced** the critical bug, scored a **risk register R1–R10** + per-domain grades |
| Reusable? | No — one-time | **Yes** — re-runnable each time the repo changes; also writes a `CLAUDE.md` summary block |
| Distinct value | ~10 fine-grained correctness/data-integrity bugs (§4) | aiohttp CVEs, test-pollution root cause, weather fail-open detail, bus-factor analysis (§5) |

**Recommendation: adopt PR #93's review organization as the canonical, ongoing review mechanism;
harvest PR #90's unique findings into the backlog below; retire #90 as a standalone once
harvested.** #93 is deeper, better prioritized, and *reusable*. But the two reviews **cross-confirm**
the load-bearing findings (§3), which makes those ground truth — this is a merge, not a pick.

---

## 3. Cross-confirmed findings — ground truth, top priority

These were found **independently by both reviews**, so confidence is high. Ordered by stakes.

1. **Emergency roof-close is broken — the physical fail-safe does not close the roof.**
   - #90: `SafetyMonitor._close_enclosure_safely()` calls the `async` `close()` **without
     `await`** (`services/safety_monitor/monitor.py:1532`); emergency loops poll
     `roof.get_state()` which does not exist (only a `state` property,
     `nightwatch/emergency_response.py:261`); `emergency_close()` fails to pass `emergency=True`.
   - #93: additionally, `RoofController.__init__` never initializes `self._gpio`
     (`services/enclosure/roof_controller.py:484-531`), so `_run_motor()` raises
     `AttributeError` (dereferenced at `:848`) — swallowed by `close()`'s `except Exception`.
     Scored **R1 (Critical), live-reproduced.** *(Re-verified here: `__init__` indeed sets no
     `_gpio`; the only assignment at `:1061` has no callers.)*
   - **Net:** two independent break mechanisms in the same safety path, both masked by tests that
     mock out `_run_motor`. Highest-stakes item in the repo.

2. **The system cannot start.** `setup_logging(level=…)` raises `TypeError` on every launch but
   `--version`: `nightwatch/main.py:308` and `:325` pass `level=`, but the parameter is
   `log_level` (`nightwatch/logging_config.py:185`). *(Re-verified here — confirmed at all three
   line numbers.)* Two-line fix. (#90 F1 = #93 R3/H1, both live-reproduced.)

3. **CI cannot fail.** Every gate swallows its exit code (`continue-on-error`, `|| true`,
   `2>/dev/null || echo`). Thousands of ruff and hundreds of mypy errors — including the startup
   crash, which mypy already flags — stay invisible behind a green badge. (#90 §4.2 = #93 R2/Q1.)
   *This is the enabling defect: every other finding shipped because this one hides them.*

4. **Built but never wired (the assembly gap).** The orchestrator starts an empty service
   registry; `LLMClient`, `VoicePipeline`, the safety interlocks, `EventBus`, `CommandQueue`, and
   the ~87-tool registry have **zero production call sites**. The integrated product does not
   exist, yet the codebase and release notes imply it does. (#90 F2/§3.1 = #93 R4.)

5. **Watchdog dormant.** `WatchdogManager` is constructed but `.start()` is never called and
   nothing heartbeats it → the SAFE-004 hardware fail-safe is dead. (#90 F10 = #93.)

6. **Phantom tool-schema import.** The pipeline imports a module that does not exist, silently
   falling back to `tools=None` — the LLM never receives real tool schemas.
   `nightwatch/voice_pipeline.py:2086`. (#90 F3 = #93 M6.)

7. **Unauthenticated network surface.** Wyoming STT/TTS bind `0.0.0.0` with no auth/TLS and an
   unbounded per-session audio buffer (DoS + audio injection upstream of command interpretation).
   (#90 NET-* = #93 R8/H4.)

8. **PDU default credentials** `admin`/`admin` over plaintext HTTP + SNMP `private`, controlling
   mount/camera/computer outlets. `services/power/power_manager.py:50-55`. (#90 §3.5 = #93 H3.)

9. **PowerShell TTS command injection.** Spoken text is interpolated into a `powershell -Command`
   string. `voice/tts/piper_service.py:444`. (#90 SEC-SUBPROC-01 = #93 L3.)

10. **Broad-except swallowing as house idiom** — #93 counted 437 `except Exception` sites vs 18
    explicit timeouts; the root-cause pattern behind #1, weather fail-open, and the power bug.
    (#90 pattern = #93 R9.)

---

## 4. Distinct to PR #90 — harvest these (not in #93's register)

Fine-grained correctness / data-integrity / deployment findings unique to the single-file audit:

- **Declination sign loss near the equator** — sign taken from the degrees field only; a Dec of
  `-00°xx` parses to `-0.0` and `-0.0 < 0` is `False`, so any target within 1° south of the
  equator slews with the wrong sign. `services/mount_control/lx200.py:344`, `:212`.
- **Alpaca constructor arg-shape misuse** — all four adapters pass bare host as `address` (no
  port) and the int port into alpyca's `protocol: str`, so every Alpaca connection targets the
  wrong URL. `services/alpaca/alpaca_client.py:293`, `:963`.
- **Fabricated coordinates on error** — getters swallow all exceptions and return valid-looking
  RA=0h/Dec=0° with slewing/parked/tracking = `False`; a failed focuser read returns 0 → absolute
  move drives to the hard stop. `services/alpaca/alpaca_client.py:332`, `:391`, `:1092`.
- **Mislabeled catalog star** — Cor Caroli is labeled "Alioth" and carries Alkaid's coordinates
  (~11° off in Dec); plus four duplicate `catalog_id`s where upsert overwrites the earlier entry.
  `services/catalog/catalog_data.py:281`, `:287`, `:291`.
- **Non-atomic history writes** — `SuccessTracker._save` rewrites the whole JSON with no
  temp+rename/lock and `_load` swallows errors → one interrupted write silently discards all
  observation history. `services/catalog/success_tracker.py:666`, `:688`.
- **HTML-email + SMTP-subject injection** — unescaped untrusted alert content (CNEOS/AMS/mount
  strings) interpolated into the email body and subject. `services/alerts/alert_manager.py:715`,
  `:641`.
- **LX200 command-injection surface** — command strings built by raw f-string interpolation of
  coordinate/site values; an embedded `#` can break framing or inject a second command.
  `services/mount_control/lx200.py:386`, `:630`.
- **`privileged: true` production container** + host `/dev` bind-mount, which nullifies the
  non-root UID; and **`CAP_SYS_RAWIO`** in systemd. `docker/docker-compose.prod.yml:29`, `:38`;
  `deploy/systemd/nightwatch.service:65`, `:68`. *(#90's one live HIGH.)*
- **The `ci.yml:346` mock-weather service-container startup failure** — the specific reason the
  "Integration Tests (Full Simulators)" check is red on every run (its `--entrypoint` isn't on
  `$PATH`, so the container dies in ~6s during setup).
- License contradiction (CC BY-NC-SA 4.0 vs "Proprietary" classifier); Python-version
  disagreement (`>=3.11` vs 3.10).

---

## 5. Distinct to PR #93 — adopt these

- **aiohttp 3.13.5 → 11 known CVEs** (fixed in 3.14.1) — and aiohttp is the transport for every
  safety-relevant network feed. (R10/H2.)
- **Full unit-suite baseline + test-pollution root cause.** 2570 pass / 48 fail / 2 errors,
  48.25% coverage. **~46 of 48 failures are an artifact** of a global
  `sys.modules['numpy'] = MagicMock()` with no teardown (`tests/unit/test_piper_service.py:27`,
  `test_whisper_service.py:35`) — they pass in isolation. Only **2 are real bugs**: a 300s
  power-restore hang (`services/power/power_manager.py:792`) and a double `_save_session_log`
  (`nightwatch/orchestrator.py:2059` + `:2391`).
- **Weather ingestion fails open** — the Ecowitt parser substitutes benign defaults on
  missing/garbled fields (a truncated response parses as "70°F, dry", `is_valid=True`),
  suppressing the rain signal; the promised secondary rain sensor is data-shape-only.
  `services/weather/ecowitt.py:159-200`. (R7.)
- **Bus factor = 1** — one author (two git identities), 97% of commits, zero code review, two
  god-files (`orchestrator.py` ~3,446 lines; `voice/tools/telescope_tools.py` ~5,662). (R6.)
- **The review organization itself** — the re-runnable `/full-review` pipeline, its
  `.claude/agent-memory/` notes, and the "next-review checklist" of greps. This is the single most
  reusable artifact across both efforts.

**Known metric drift (not contradictions — different review commits/filters):** ruff 2,675 (#90)
vs 2,585 (#93); mypy 160 (#90) vs 233 (#93); LOC ~64k (#90) vs ~122k/25k-source (#93); live tool
handlers 30/90 (#90) vs 18/87 (#93). Both agree on the shape: thousands of ruff, hundreds of
mypy, all swallowed; dozens of live handlers against ~90 declared schemas.

---

## 6. Resumption backlog — the prioritized Stage 0–5 plan

Sequenced so the two *enabling* fixes come first: make failure visible (CI), then make the system
boot — after which every downstream fix becomes verifiable.

### Stage 0 — Boot + visibility *(days)*
- Fix `setup_logging(level=→log_level=)` at `main.py:308`, `:325` (2-line).
- Un-mute CI: let the pytest / `mypy nightwatch/` / ruff steps fail the build; fix the
  `ci.yml:346` mock-weather service container.
- Fix the numpy-mock test pollution with `monkeypatch.setitem` (removes ~46 phantom failures).
- Fix the `pyindi-client` version pin and the README / systemd entry points so documented
  install/run paths work.
- Add a `main(["--dry-run"])` boot smoke test.
- **Acceptance:** CI can go red, and `python -m nightwatch.main --dry-run` exits 0.

### Stage 1 — Physical-safety cluster *(days)*
- Initialize `RoofController._gpio`; `await` the async enclosure close; restore
  `roof.get_state()`/`state`; force `emergency_close(emergency=True)`; assign the power
  `_action_callback`; **start** the `WatchdogManager`; make the Ecowitt parser fail **closed**.
- Add one emergency-close test that does **not** mock `_run_motor`.

### Stage 2 — Data-integrity / driver correctness *(days — the #90 harvest, §4)*
- Declination sign; Alpaca constructor arg-shape; fabricated coordinates + focuser rel-move;
  catalog Cor Caroli mislabel + duplicate-id; atomic `SuccessTracker` writes.

### Stage 3 — Security hardening *(days)*
- Wyoming → `127.0.0.1` + capped audio buffer; empty PDU credential defaults; `aiohttp>=3.14.1`;
  drop `privileged: true` / `CAP_SYS_RAWIO`; escape HTML-email + SMTP subject; fix PowerShell TTS
  injection.

### Stage 4 — Assembly: the real project *(weeks)*
- A one-page **wire-or-delete** decision per dormant subsystem; collapse the two command-dispatch
  stacks into one validation regime; make `LX200Client` methods async (`asyncio.to_thread`); add a
  parametrized Protocol-conformance test per service.

### Stage 5 — Process *(standing)*
- PR-gated merges even solo; tag `v0.1.0-alpha`; keep the review org current (re-run
  `/full-review`); execute the branch triage in §6.

---

## 7. Stale feature-branch triage

~55 unmerged branches cluster around one feature set, attempted many times in parallel. None
reached `main`. Winner-selection requires diffing the top candidates against `main` (a Stage 5
task); the grouping below is the starting point.

| Group | Feature | Representative branches | First move |
|---|---|---|---|
| A | NEO close-approach + space-weather clients | `feat/neo-close-approach-client`, `feat/close-approach-client`, `feat/neo-space-weather-clients` | Diff the 2–3 newest vs `main`; keep the most complete, prune the rest |
| B | Hourly autonomous scan loop | `feat/hourly-neo-scanner`, `feat/hourly-scan-system`, `feat/hourly-event-polling` | Same; this is the "conductor/night-executor" the roadmap says is missing |
| C | Event journal | `feat/event-journal`, `add-event-journal-and-neo-client` | Often bundled with A/B — evaluate together |
| D | Meteor / AMS integration | `fix/ams-monitoring-integration`, `wire-meteor-to-orchestrator`, `integrate-meteor-config` | Evaluate after A–C land |
| — | **Prune-first (dated 2026-03, superseded duplicates)** | `hourly-scan/2026-03-*`, `hourly-meteor-integration-2026-03-22`, `nightwatch-hourly-scan-2026-03-23`, etc. | Delete unless a later branch lost unique work |

**Guidance:** because Stage 4 is fundamentally about *assembly*, this cluster is high-leverage —
but only after Stage 0–1 make integration verifiable. Salvage into a single clean PR per feature;
do not re-merge parallel duplicates.

---

## 8. How to resume

1. Land **Stage 0** first — it is a few hours of work and unlocks verification for everything else.
2. Then **Stage 1** (physical safety) — the one cluster where "it doesn't run" masks real danger.
3. Decide PR housekeeping: adopt #93's review org (merge when Stage 0 is green so its `CLAUDE.md`
   block lands on a working base), and close #90 once §4 is folded into tickets.
4. Keep this file (or its successor under `docs/review/`) as the single tracked backlog; re-run
   `/full-review` after each stage to catch regressions the muted CI used to hide.
