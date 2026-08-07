# NIGHTWATCH — Unveiling Keynote

`NIGHTWATCH_UNVEILING.html` is a self-contained, cinematic ~3-hour keynote (107 slides,
six acts + intermission) unveiling the NIGHTWATCH optics program. One file, zero network
dependencies: fonts, styles, and every figure are embedded, and **all engineering figures
are computed live** from the real design constants (exact meridional ray trace through the
seed prescriptions, annular-pupil MTF, Airy/Strehl physics, CTE ladder, budget, phases).
The design system is the repo's own "High Desert Brass" (`docs/design/CLAUDE_DESIGN_PROMPT.md`).

## Presenting

Open the file in any modern browser (Chrome/Edge/Firefox/Safari). No server needed.

| Key | Action |
|---|---|
| `→` / `space` | next (reveals in-slide fragments first) |
| `←` | previous |
| `O` | overview grid (jump anywhere) |
| `N` | speaker notes + next-slide preview (every slide carries its beat + cumulative ⏱ cue) |
| `T` | presenter clock |
| `F` | fullscreen |
| `R` | Rubylith night-vision mode (the design system's alternate theme) |
| `?` | key help |

Click zones: right two-thirds = next, left third = back. Deep-linkable: `#/54` jumps to slide 54.

## Run of show

| Segment | Slides | Clock |
|---|---|---|
| Prologue | 1–4 | 0:00 |
| Act I — The Watch | 5–18 | 0:05 |
| Act II — The Sky Is the Enemy | 19–36 | 0:25 |
| Act III — The Glass That Time Forgot | 37–52 | 0:50 |
| Intermission (leave slide 53 on screen) | 53 | 1:15 |
| Act IV — Designing the Eye | 54–77 | 1:27 |
| Act V — Metal, Money, and Mirrors | 78–97 | 2:02 |
| Act VI — First Light | 98–107 | 2:32 → 2:47 |

AV notes: dark room strongly preferred (the deck is indigo-black by design); 16:9
projection; the interactive moments are slide 54-55 (ray-trace f/6↔f/8 toggle) and
63-64 (obstruction ε slider) — rehearse those two. `prefers-reduced-motion` is honored.
Print (`⌘P`) produces a one-slide-per-page handout with the speaker notes appended.

## Regenerating

The deck was assembled from the design sources at v0.1.1. If the prescription changes,
the figures change with it — the physics is in the file's own JavaScript
(`NW_FIG.__test()` in the console returns the key computed values for verification:
MTF loss at ν=0.3/ε=0.25 ≈ 14.5%, clear-aperture MTF(0.5) ≈ 0.391, Rayleigh 0.77″).
