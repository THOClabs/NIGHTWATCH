# NIGHTWATCH UI — Iteration Prompts (Generation 2+)

The master prompt (`CLAUDE_DESIGN_PROMPT.md`) builds the shell, the design system, the simulation, and the ten flagship screens, leaving ~20 routes as honest placeholders. These follow-up prompts flesh those out **one module at a time** — the pattern that keeps Claude Design output coherent (one-shotting dozens of screens degrades quality and burns the weekly allowance).

Rules of engagement for every iteration:

- Run these **in the same Claude Design project** as the master generation so the design system, tokens, simulation, and shell carry over.
- One prompt per generation. Don't combine.
- Each prompt already follows the four-part iteration form: *what exists → scope → outcome → what must not change.* Paste as-is, or trim scope if the generation budget is tight.
- For small fixes after a generation, use **inline comments** on the canvas (component-level) or **direct canvas edits** (visual nudges) — reserve chat for structural changes, and ask for at most 1–2 changes per chat turn.

---

## Iteration 1 — Facility module (roof, power, drives)

> The NIGHTWATCH app already has its design system (High Desert Brass tokens), global shell, simulation store, and flagship screens. Do not change any of those, the routes, or the data model.
>
> Build out the three Facility screens, replacing their placeholders:
>
> **`/facility/roof`** — A large cross-section roof diagram (reuse the twin's enclosure/roof SVG group at high detail) with the roof panel at its live `positionPercent`. Big brass OPEN and CLOSE buttons that respect interlocks: when `canOpen`/`canClose` is false, the button disables and an interlock explainer lists `interlockReasons` in plain language ("Telescope is not parked — the roof never moves over an unparked mount"). Show motor telemetry (running, current in amps against the 5.0 A cutoff drawn on a small bar), the 60 s travel timeout as a progress ring while moving, and the rain-holdoff countdown card when active. Opening/closing here animates the twin everywhere.
>
> **`/facility/power`** — The battery staging ladder is the hero: a vertical ladder from 100% down, with rungs at 50 (warn), 30 (park), 15 (close roof), 10 (emergency shutdown), the current battery level as a brass float, and each rung labeled with its automatic action. Beside it: UPS card (state online/on_battery/low_battery/charging, runtime minutes, load %, input voltage) and the PDU outlet strip — four labeled outlets (1 mount, 2 camera, 3 focuser, 4 computer) with toggles that visibly cut power (twin's power-chain flow dots stop for that branch). Include the sequenced power-on affordance: computer → mount → camera → focuser, 5 s apart, animated down the chain.
>
> **`/facility/drives`** — Engineering diagnostics for the two axes. Per-axis cards (RA: Harmonic Drive CSF-32 100:1, 24,000 steps/°; DEC: CSF-25 80:1, 19,200 steps/°) showing TMC5160 driver status as labeled indicator lamps: standstill, open-load A/B, short-to-ground, overtemperature pre-warn/fault, StallGuard, current mA (against IRUN 1500 / IGOTO 2000). An encoder card shows motor-side counts vs axis-side absolute position and the derived pointing error in arcsec. A PEC panel shows record/play state with a worm-period phase curve.
>
> Outcome: Facility feels like the electrical room of the observatory — dense, labeled, honest. Keep every existing screen, token, and the sim physics untouched. You may extend the simulation store with small `DriverStatus`, `EncoderStatus`, and `PECStatus` slices for the drives screen, provided their values stay consistent with the physics constants (IHOLD 800 mA, IRUN 1500 mA, IGOTO 2000 mA).

---

## Iteration 2 — Operations module (queue, session timeline, log, report)

> Same project; design system, shell, sim, and existing screens are fixed. Build out four Operations screens:
>
> **`/ops/queue`** — The command queue: rows of pending/executing commands (name, source: voice/schedule/ui, priority chip with emergency jumping to top, enqueued time, state). Executing rows show a progress affordance; completed ones collapse into a recent-history section. A cancel control per row demonstrates cooperative cancellation.
>
> **`/ops/session`** — The event-bus timeline: every `ObservatoryEvent` of the night on a vertical scrubber synced to the Demo Director clock, grouped by hour, icon per event type, safety events tinted by level. Clicking an event jumps the sim clock to that moment (deterministic replay). A filter bar by event family (mount / weather / safety / guiding / session / system).
>
> **`/ops/log`** — The observation log: one entry per target visit (target, start/end, frames kept/rejected, integration minutes, average FWHM and guiding RMS, notes line from the narrator e.g. "Interrupted by rain at 02:25"). Filterable by session/date; a summary footer totals the night.
>
> **`/ops/report`** — The morning report, styled like a typed observatory report sheet (Fraunces heading, mono body): session span, weather summary with the interruption window, per-target results table, equipment notes (max motor temp, battery low-water mark), and the schedule's planned-vs-actual strip. A "copy as text" button.
>
> Outcome: Operations tells the story of the night after the fact as clearly as Mission Control tells it live. No changes to tokens, routes, sim physics, or other modules.

---

## Iteration 3 — System module (health, settings, simulator)

> Same project; everything existing is fixed. Build out three System screens:
>
> **`/system/health`** — The service supervisor: a grid of the 21 backend services (mount_control, camera, weather, safety_monitor, ephemeris, catalog, guiding, focus, astrometry, meteor_tracking, scheduling, alerts, power, enclosure, encoder, nlp, indi, alpaca, simulators, voice, stt/tts) each as a card with status (healthy / degraded / unhealthy / disabled), uptime, restart count, and last heartbeat age. The safety_monitor card carries a special watchdog strip: heartbeat pulse animation and the fail-safe explainer ("if this service goes silent, the hardware watchdog closes the roof directly"). A restart action per card fires a service_stopped → service_started event pair.
>
> **`/system/settings`** — Schema-generated settings forms, one nav section per real config group: site, mount, weather, voice, tts, llm, safety, camera, guider, encoder, alerts, meteor, power, enclosure. Render each as a clean form from a small schema (label, type, unit, current value, help line) — read-only inputs with an "editing arrives in v0.2" note is fine, but the safety section must visually mirror the threshold tiers used across the app (same numbers: wind 20/25/30, humidity 75/80/85, rain holdoff 30 min). One pattern, fourteen instances — do not hand-craft fourteen bespoke layouts.
>
> **`/system/simulator`** — A full-page mirror of the Demo Director: sim speed, scrub, chapter jumps, free-run toggle, plus fault-injection buttons for demos (trip primary rain sensor, stall roof motor at 40%, drop guide star, kill weather sensor feed → watch staleness flip to unsafe). Each fault fires the correct existing events and safety responses — no new physics.
>
> Outcome: System proves the platform is operable and self-aware. Reuse existing enums and events only.

---

## Iteration 4 — Sky & Targets + Imaging depth

> Same project; everything existing is fixed. Deepen five screens:
>
> **`/sky/target/:id`** — Object detail: designation and common name, type, constellation, magnitude, size; tonight's altitude curve with the observing window shaded and meridian rule; observation history from the log (times observed, best FWHM); score breakdown showing each `ScheduleReason` as a scored row; a brass "Go to" honoring safety interlocks.
>
> **`/sky/almanac`** — Tonight's almanac: twilight ladder (civil/nautical/astronomical times both dusk and dawn), moon card (phase disc drawn as SVG, illumination %, rise/set), planet visibility strip (which planets are up and when), LST clock ticking in mono.
>
> **`/imaging/focus`** — Full V-curve screen: the sampled HFD-vs-position curve with fitted parabola, best-position marker, R² and confidence readouts, low-confidence warning state, temperature-compensation card (−2.5 steps/°C with tonight's drift plotted), and a run-history list.
>
> **`/imaging/platesolve`** — Solve viewer: star-field frame with solved WCS crosshair vs target crosshair, offset in arcsec, iterative centering progress (solve → nudge → solve), and a sync-to-mount action that visibly zeros the pointing error.
>
> **`/imaging/gallery`** — Session frame grid, filterable by grade; each cell shows its grade edge and hover metrics; selecting frames shows a stack-preview card (kept count, total integration).
>
> Outcome: the astronomy depth of the app matches the engineering depth. No new tokens, no new routes.

---

## Iteration 5 — Voice & Meteor depth

> Same project; everything existing is fixed. Deepen four screens:
>
> **`/voice/history`** — A searchable archive of all `VoiceTurn`s: date-grouped list, each row a compact turn (transcript → outcome), expanding to the full turn rendering used on the console. Aggregate stats header: turns tonight, average total latency, tool success rate.
>
> **`/voice/settings`** — Wake word card ("Nightwatch", sensitivity slider), voice-style picker with a sample line rendered per style (normal / alert / calm / technical — the alert style is the one used during emergencies), narration verbosity (brief / standard / verbose), and earcon toggles.
>
> **`/meteor/showers`** — The full shower calendar: all nine showers (Quadrantids, Lyrids, Eta Aquariids, Delta Aquariids, Perseids, Orionids, Leonids, Geminids, Ursids) as an annual ring or table with activity windows, peak dates, ZHR, radiant constellation, and moon interference for the current year; the active shower carries the violet glow.
>
> **`/meteor/search`** — The Hopi-circle search planner: given the scripted fireball's ground track, render the expanding concentric search rings on a coordinate grid (ring number, radius, cumulative area in mi², walk-time estimate), violet on indigo, with an export-as-text action producing a search briefing that opens with "presa-nightwatch. velmu-sky. do-good-us." and closes with 🜏.
>
> Outcome: the two most distinctive modules — the voice and the chapel — feel complete. Lexicon styling stays inside Meteor.

---

## Iteration 6 — States, polish, and the empty observatory

> Same project; no new screens. A finishing pass:
>
> 1. **Empty/idle states:** the app at 14:00 with the sim paused — parked, roof closed, daylight. Every flagship screen needs a dignified daytime idle state ("Telescope parked · roof closed · 5 h 42 m to astronomical darkness") rather than empty charts.
> 2. **Loading discipline:** the one orchestrated page-load reveal per screen; skeletons in surface color for any panel that waits on the store.
> 3. **Keyboard:** `g` then `d/t/v/s…` to jump modules; `space` play/pause sim; `[`/`]` sim speed; `a` acknowledge newest alert. A `?` overlay lists them, styled like an engraved legend plate.
> 4. **Rubylith audit:** flip every flagship screen to Rubylith and fix any element that kept a non-red hue or lost AA contrast.
> 5. **Reduced motion:** honor `prefers-reduced-motion` — twin snaps between attitudes, pulses become static outlines.
>
> Change nothing structural; do not touch the data model or routes.
