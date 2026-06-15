# NIGHTWATCH — Opus-4.8 Capability Review

*A Panel-of-Specialists convergence on what a 1M-context builder changes for this codebase.*

## The pivot

This review exists because the builder changed. NIGHTWATCH was planned around a 290-task atomized roadmap (`good-catch-on-the-glistening-deer.md`) and a `CLAUDE.md` "Context budget — CRITICAL for Opus 4.7 1M sessions" discipline that treats `orchestrator.py`, `voice_pipeline.py`, and `tool_executor.py` as files to read by Grep, never whole, and to keep in separate subsystem-tagged sessions so a context-limited builder wouldn't cross-contaminate domains. That scaffolding was correct for the builder it was written for. It is now the constraint, not the safeguard.

An Opus-4.8 / 1M builder holds the whole command path at once — orchestrator, scheduler, the four imaging services, and the deterministic safety stack — and writes cross-service changes as single reviewable diffs. Work the old cadence had to shatter into 17 or 21 single-file tasks is now the *cheap* path; the expensive, error-prone path is doing it as separate edits.

### Builder vs. runtime — the line that must not blur

The pivot is in **how we build**, not in **what the observatory becomes at runtime**. Two authorities must stay distinct:

- **Builder capability** = Opus 4.8 / 1M writing the code. This is what just got more powerful.
- **Runtime authority** = what actually decides and actuates on a real night. This stays exactly where it is: a **local Llama** model (never cloud) that may *propose* targets and parse voice, and a **deterministic safety stack** that is the sole authority that can halt / park / close.

"LLM proposes the plan; the deterministic executor + interlock dispose" is a categorically different design from "LLM in the loop," and the old plan wrongly bundled them. Reopening the *capability* of a whole-night planner does **not** reopen putting a model in the hard-safety path.

### The immovable guardrails

These do not move under any roadmap re-baseline:

1. **No LLM — and no cloud model of any kind — in the hard-safety loop, ever.** The deterministic stack (`services/safety_monitor/monitor.py`, `nightwatch/safety_interlock.py`, `nightwatch/emergency_response.py`, `nightwatch/watchdog.py`) remains the only thing that can stop the observatory.
2. **Runtime stays no-cloud / local-AI / deterministic-safety.** Builder power changes nothing here.
3. **Everything is simulator-only.** No service has touched real ASI / OnStepX / PHD2 hardware. The hardware program (OTA/OFAC, harmonic drives at 10–12wk lead, mount fab, pier, site, power, remote tunnel) is the real gate — software cannot create the illusion the observatory is near-operational.
4. **`do-good-us`** governs every call here: we ship this because it is genuinely good for Tim to operate, not because it demos well.

---

## Headline verdict

**NIGHTWATCH can become a genuinely autonomous, simulator-validated observatory in one coherent Opus-4.8 build cycle — because the primitives are all written and green. What is missing is the conductor (a night executor) and a system-wide abort path. Both are exactly the cross-service, single-diff work the old 290-task cadence had to defer, and both are now tractable for a builder that holds the whole stack at once.**

The single biggest gap is **integration, not capability**. Verified against the tree:

- `ObservingScheduler.create_schedule` (`services/scheduling/scheduler.py:250`) and `get_best_target` (`:341`) already produce a scored, time-sliced `ScheduleResult` — but it is consumed **only** by `services/ai_services.py` and `services/nlp/session_narrator.py`, i.e. for *narration*. Nothing actuates it.
- The orchestrator's *only* run loop is `_health_loop` (`nightwatch/orchestrator.py:2096`, started at `:1958`) — service supervision, not a night executor. `start_session` (`:2296`) flips state; it does not drive a night.
- Every acquisition primitive exists and is simulator-testable: `slew_to_coordinates` (`orchestrator.py:874`), `capture` (`:981`), `start_guiding` (`:1005`), `auto_focus` (`:1053`); and in the services, `plate_solver.solve_and_sync` (`:708`), `phd2_client.calibrate_and_guide` (`:489`), `phd2_client.dither_and_wait` (`:447`), `focuser_service.auto_focus` (`:863`), `asi_camera.start_capture` (`:610`).

Nothing chains slew → focus → solve → sync → guide → dithered-capture → repeat. That chain is the verdict's "conductor."

---

## Per-lens highlights

### 1. Autonomy lens

- **The night executor is now a single coherent build, not a 21-task crawl.** The atoms are individually green; what's absent is `run_target()` (per-target sequence with abort points) and `run_night(ScheduleResult)` (iterate the scored schedule). A 1M builder writes that with correct cross-service ordering in one pass.
- **The scheduler→actuator gap is the highest-value unlock.** Wiring `ScheduleResult → run_night` *and* adding the missing feedback edge (replan on target-failure / clouds / a higher-scorer rising) requires reasoning over scheduler internals and orchestrator state simultaneously — now feasible.
- **System-wide cancellation is one rollout.** `CancelToken` reaches only `services/camera/asi_camera.py` and `services/safety_monitor/monitor.py` today (verified). The contract in `cancellation.py` is built; extending it to mount / enclosure / guiding / weather is one diff, not 17 SAFE-* tasks.
- **Per-resource concurrency (ARCH-005).** The orchestrator serializes on one `asyncio.Lock` (`:220`) and `set_active_context` (`:1772`) *rejects* a second context (the ARCH-003 raise at `:1803`) rather than coordinating; `is_slewing` (`:1540`) is a bare flag. A whole-night loop plus a voice barge-in will contend for the mount — this needs per-resource locks first.

### 2. Imaging lens

- **The whole-night acquisition executor is the headline build** and is now one reviewed pass: a builder can hold `plate_solver` (960L) + `phd2_client` (1332L) + `focuser_service` (2414L) + `asi_camera` (2494L) + scheduler at once and write the `slew → auto_focus → solve_and_sync → calibrate_and_guide → start_capture → dither → repeat` orchestration.
- **Type the high-blast-radius imaging verbs.** `tool_params.py` has 7 Pydantic models + `NoParams` + the `TOOL_PARAM_MODELS` registry, but **no** models for `start_capture`, `auto_focus`, `start_guiding`, `dither`, or `solve` — while `voice/tools/telescope_tools.py` registers ~147 flat tools. A bad `exposure-ms` or `dither-pixels` from Llama drives real hardware; type the acquisition verbs the executor calls first.
- **CancelToken through the rest of the acquisition chain in one sweep.** Camera consumes it; focus uses its own cancel flag; PHD2 and mount don't observe it. Making `auto_focus` and `calibrate_and_guide` token-aware closes the mid-operation-abort guarantee for the whole chain.
- **Fireball response is buildable — but as a second actuation path.** `meteor_service.py` fires a `MeteorAlert` (with a Lexicon prayer; `min_magnitude=-4`) but **no** callback reaches mount or camera (verified: zero slew/goto/capture in the file). A bounded, deterministic responder is attractive new science — and is the panel's chief sequencing tension (below).

### 3. Safety / interlock lens

- The four safety files all exist and are substantial (`monitor.py` 72KB, `watchdog.py` 33KB, `emergency_response.py` 26KB, `safety_interlock.py` 19KB). They remain the **sole** stop authority.
- The hazard is concrete: a self-driving loop on **partial** cancellation is *strictly more dangerous* than today's command-at-a-time system. Rain mid-exposure → roof closes before the capture aborts → water damage. This is the original Risk #2, and it gets worse, not better, the moment a loop exists on top of 2-of-many cancellation coverage.
- Therefore: the abort path must be made system-wide **before or with** the executor — never after.

### 4. Process / cadence lens

- The 290-task atomized plan, the per-task worktrees, append-only `LEARNINGS.md` / `PATTERNS.md`, and the "Context budget — CRITICAL for Opus 4.7 1M" rules (read-by-Grep, compact at 60%, subsystem session tags) are **weak-builder scaffolding**. Note `CLAUDE.md:51` literally names "Opus 4.7" and lists `orchestrator.py` as 3059 lines — the file is now 3446L, so even the inventory is stale.
- Re-bucket semantically-single changes (cancellation rollout, typed-tool-boundary completion, correlation-ID propagation) into coherent PRs. Keep `LEARNINGS`/`PATTERNS` as durable human docs; stop quarantining cross-domain work — that is now normal mode.
- **Exception, preserved:** keep atomic granularity + per-change human review for the prohibited safety / firmware set. There, the small-diff discipline *is* the point.

### 5. Honesty / status lens

- **`ROADMAP.md` is stale and self-contradictory** (verified): it dates v0.1.0 to "January 2024," targets v0.2 imaging at "Q2 2024" (in the past), and sits out of step with the live work. The modernization plan's DONE markers + git log are the only reliable status. Rewrite or delete it.
- **AID-013 is trivially closeable and still live** (verified): `llm_client.py:452` and `:726` both default to the retired `claude-3-haiku-20240307`. It lingers only because the cadence queues it as one more task. It is a *builder-convenience* cloud fallback and must never sit in the runtime inference or safety path.
- **Four tests don't collect** — `/home/user`-hardcoded paths in `tests/unit/test_whisper_service.py` and `test_piper_service.py`, plus optional-dep gaps for the plate-solver / safety-monitor tests (zwoasi + numpy). You cannot trust verification against a suite that won't collect.

---

## Agreements

1. **The biggest gap is integration, not capability.** Imaging primitives + a scoring scheduler all exist and are simulator-testable; nothing chains them, and `ScheduleResult` feeds only narration. (Verified: the orchestrator's only loop is `_health_loop` supervision.)
2. **The night executor is a one-pass build** for a builder holding orchestrator + scheduler + the four imaging services + the safety stack together — the exact coherence the weak-builder era forbade.
3. **The atomized plan and the context-budget rules are weak-builder scaffolding** to be re-bucketed into coherent PRs — *except* the prohibited safety/firmware files, where atomicity and human review stay.
4. **The immovable line is `do-good-us`:** local Llama may propose; the deterministic stack disposes. "Propose/dispose" ≠ "LLM in the loop."
5. **AID-013 is sweepable now** (still live at `:452` and `:726`); it is builder-convenience only and must never enter runtime/safety inference.
6. **`ROADMAP.md` must be rewritten or deleted;** git log + plan DONE markers are the real status source.
7. **The abort path must go system-wide before or with the executor.** Cancellation is verified *narrower* than the brief feared — only camera + safety_monitor — so a loop on top is more dangerous than today.

---

## Honest tensions

1. **Sequencing — the one real disagreement.** The autonomy lens insists per-resource locking (ARCH-005) and full `CancelToken` propagation land **before/with** the executor, citing mount-contention hardware damage when a voice barge-in races an automated slew. The imaging lens treats cancellation/typing as parallel "one coherent pass" work without the same hard ordering. **Chair's ruling (Pragmatist): the autonomy lens wins.** A night executor that can drive the mount must not ship before the abort path and per-resource locks exist. This is a safety gate, not a preference — the executor build and the cancellation/locking build are the **same release**.
2. **Scope of the typed boundary.** Autonomy wants schema-complete param models across all ~147 registered tools as the precondition for trusting any multi-step plan; imaging wants the high-blast-radius acquisition verbs first. Compatible if staged: type the acquisition verbs the executor calls **first** (small, blocks nothing), finish the long tail opportunistically. Not a real conflict once sequenced.
3. **Fireball responder ambition.** Genuinely attractive new science — but it opens a **second** autonomous mount-driving path contending for the same resource. **Chair: defer** until per-resource locking + system-wide cancellation are proven. Do not open two actuation paths in one cycle.
4. **Megafile refactor timing.** The imaging lens wants to extract acquisition orchestration out of the 3446L `orchestrator.py` *while* writing the executor. Tempting, but mixing a large mechanical refactor into the highest-stakes new safety-adjacent diff muddies the review that most needs to be clean. **Chair: write the executor as a new cohesive module** (so it doesn't bloat `orchestrator.py` further), but do **not** refactor the existing 3446L file in the same PR.

---

## Leverage-ranked roadmap

| # | Move | Effort | Why now |
|---|------|--------|---------|
| 1 | **Hygiene sweep (single PR):** fix AID-013 (`llm_client.py:452` + `:726` → local-first default; if a cloud fallback is kept, migrate to `claude-haiku-4-5`, builder-convenience only, never runtime); fix the 4 non-collecting tests (hardcoded `/home/user` paths in `test_piper`/`test_whisper`; optional-dep guards for plate-solver/safety-monitor zwoasi+numpy); rewrite or delete the stale `ROADMAP.md`. | **S** | Clean room before the big build — you cannot trust verification against a suite that won't collect, and a 1M builder sweeps all of this in one short pass. |
| 2 | **System-wide abort + concurrency (one coherent diff):** propagate `CancelToken` through mount_control, enclosure, guiding, weather (and every step boundary the executor will use); replace the single global `Lock` + context-rejecting `set_active_context` (ARCH-005) with per-resource `asyncio.Lock`s on mount / camera / focus. | **M** | **The safety gate.** Verified only camera + safety_monitor consume `CancelToken` today; the executor cannot ship safely on top of that. Upgrades Risk #2 from partial to whole-night-safe and removes the mount-contention hardware-damage path before any loop can trigger it. |
| 3 | **The night executor — as a NEW cohesive module (not bloating `orchestrator.py`):** `run_target()` (slew → plate_solve → sync → autofocus → guide → dithered-capture) with a `CancelToken` checkpoint **and** a deterministic safety-state check between every step; `run_night(ScheduleResult)` pulling scored targets from `ObservingScheduler.get_best_target()` and replanning on target-failure / clouds / higher-scorer-rises. LLM proposes/orders; the deterministic executor + interlock gate every step. | **L** | **THE headline unlock.** The scheduler scores targets nothing actuates (verified: consumed only by narration). Ships in the **same release** as item 2 — they are one safety-coupled unit. |
| 4 | **Type the acquisition verbs:** add Pydantic param models for `start_capture`, `auto_focus`, `start_guiding`, `dither`, `solve`, extending the existing 7-model + `NoParams` + `TOOL_PARAM_MODELS` registry. Defer the ~147-tool long tail to opportunistic follow-up. | **S** | The executor calls these verbs directly; an unvalidated `exposure-ms` or `dither-pixels` from Llama drives real hardware — type them before the loop relies on them. |
| 5 | **Minimal remote observe + kill surface:** a read-only status view + a hard ABORT/PARK/CLOSE button (can lean on the existing safety stack as the actuator). Not a full web dashboard, not an Alpaca server. | **M** | A solo dev cannot trust unattended whole-night autonomy on a remote Nevada site with no off-site observe/abort surface. This is a precondition for *running* the executor for real, not a v0.3 nicety. |
| 6 | **Process re-baseline:** update `CLAUDE.md`'s "Context budget — CRITICAL" section (drop read-by-Grep / compact-at-60% / subsystem-tagging as the default; a 1M builder holds the megafiles whole and the inventory is stale at 3059 vs 3446L); re-estimate the ~270 open tasks against the new cost frontier; re-bucket semantically-single changes into coherent PRs — keeping atomic granularity + per-change human review **only** for the prohibited safety/firmware set. | **M** | Re-aligns the development process with the new builder so future work doesn't crawl. Cheap relative to its compounding payoff. |
| 7 | **Deterministic fireball responder:** a bounded `meteor_service → orchestrator` bridge (CNEOS/AMS fireball above magnitude threshold, inside FOV/altitude gate, within slew-time budget, hard weather/safety precondition) that slews + burst-captures. Strictly deterministic trigger logic — **never** "ask the model whether to slew." | **L** | Real new science, but it opens a **second** autonomous mount-driving path — only safe once items 2 + 3 are field-exercised in simulation. |
| 8 | **Alpaca server (HWS-006):** expose the observatory to standard remote clients. | **L** | Genuinely useful but not on the critical path; item 5 already covers the safety-critical remote need. Lowest priority — explicitly after autonomy + safety + the minimal remote surface are solid. |

---

## Do not do

- **Do NOT put the LLM — or any cloud model — in the hard-safety loop, ever.** `monitor.py` / `safety_interlock.py` / `emergency_response.py` / `watchdog.py` remain the sole halt/park/close authority. The executor and replanner *propose*; the interlock *disposes*. Builder capability (Opus 4.8 writing code) is never runtime authority (local Llama, deterministic, no-cloud).
- **Do NOT ship the night executor before system-wide `CancelToken` + per-resource locks land.** A self-driving loop on partial cancellation is strictly more dangerous than today's command-at-a-time system. These are **one** release, not two.
- **Do NOT edit the prohibited safety/firmware files without an explicit `[approved]` marker**, and do NOT collapse SAFE-* / FW-* tasks into big coherent PRs. Per-change human review *is* the point there. Re-bucketing applies to everything *except* that set.
- **Do NOT let an impressive simulator-validated loop create the illusion the observatory is near-operational.** Everything is simulator-only; no service has touched real ASI/OnStepX/PHD2. The hardware program is the real gate. Run only with `--simulator` unless Tim approves real hardware in-session.
- **Do NOT move the runtime off no-cloud / local-AI / deterministic-safety.** The pivot is in how we *build*, not what the observatory *becomes*.
- **Do NOT scope-creep** into a full web dashboard, an all-sky / cloud-from-imagery rebuild, or a runtime background-agent fleet. The existing WS90 + CloudWatcher + dual rain-sensor suite is the safety input the executor uses. Propose only what one person can run and reason about on a single DGX Spark.
- **Do NOT open two autonomous mount-driving paths** (night executor + fireball responder) in the same cycle. One actuation path, proven, before the second.
- **Do NOT bundle a refactor of the 3446L `orchestrator.py` into the executor PR.** Write the executor as a new module so the highest-stakes diff stays clean to review.

---

## Start these three

1. **Land the hygiene sweep PR (item 1):** the AID-013 two-line fix at `llm_client.py:452` + `:726`, the 4 non-collecting tests, and the `ROADMAP.md` rewrite/delete — so the suite is green out-of-the-box and status is honest before the big build. Minutes-to-hours for a 1M builder.
2. **Land system-wide abort + per-resource locks (item 2)** as one coherent diff — propagate `CancelToken` through mount / enclosure / guiding / weather and replace the global `Lock` + context-rejecting `set_active_context` with per-resource `asyncio.Lock`s. This is the safety gate; nothing that drives the mount autonomously ships until it is in.
3. **Begin the night executor (item 3)** as a new cohesive module — `run_target()` with a `CancelToken` + safety-state checkpoint between every step, and `run_night(ScheduleResult)` pulling scored targets from `ObservingScheduler` and replanning on failure/weather — released together with item 2 and exercised end-to-end against `services/` simulators only (`--simulator`). Type the acquisition verbs (item 4) alongside, since the executor calls them directly.
