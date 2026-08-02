## Trade Study (Phase B) — Morphological Box + Weighted-Pugh Selection

This section does not compute physics; it **selects** among design permutations by
scoring them against the verdicts the Phase-C proof modules actually computed, so
the configuration that goes into CAD is grounded rather than asserted. The scoring
matrix, the three CSVs below, and their invariants are a pure function encoded in
`design/mechanical/tradestudy/build_tradestudy.py` and locked by
`design/mechanical/tests/test_tradestudy.py` (10 tests, green).

**Grounding — the Phase-C verdict ledger the scores are anchored to:**

| Proof | Verdict | Governing number |
|---|---|---|
| torque | PASS | counterweight-FREE MN78: RA SF 2.5, DEC SF 2.6 vs rated |
| stiffness | **FAIL** | 43.3" vs 5" target — bearing compliance at 63.5/76.2 mm spans governs |
| dynamics | PASS | first mode 65 Hz vs 10 Hz (SF 6.5) |
| encoder | **FAIL** | baseline 5.02" RMS vs 1.0"; on-axis RESA ring 0.54" |
| balance | PASS | 12.5 kg balances 18 kg (fit 1.59); CW-free deletes 15.4 kg + 29% RA inertia |
| bearings | PASS + finding | load never governs; 60xx are deep-groove — use angular-contact 7008/7006 pairs |
| wind | **FAIL** | roof uplift SF 0.19 — hold-down anchors mandatory (SF 3.9 with 4x 2 klbf) |
| pier | PASS | governing SF 6.8, f_n 152 Hz |
| thermal | **FAIL** (passive) | 22 K swing walks focus ~10x DoF — temp-compensated focuser required |
| enclosure | PASS + finding | drive SF 2.1; snow case governs the roof, snow interlock required |
| power | **FAIL** (off-grid) | 12 V pack 3.3 h vs 10 h night; 48 V -> 13.4 h; DGX = 59% of load |

**Scoring convention.** Every criterion is *higher-is-better* on a 1–5 scale (for
cost and sourcing, 5 = cheapest / lowest risk), so a weighted score stays in 1–5.
Default weights: **stiffness 0.22, precision 0.22, cost 0.15, buildability 0.15,
thermal 0.10, sourcing-risk 0.16**. Crucially, precision against the hard 1.0"
tracking target is a **pass/fail GATE**, not merely a weighted term: an option that
fails it is *disqualified* regardless of its weighted score.

### 1. Morphological (Zwicky) matrix — the option space

`morphological.csv`. Bold picks are marked **[BOLD]**.

| Subsystem | Baseline | Alternatives | Bold |
|---|---|---|---|
| OTA | MN78 f/8 (14 kg) | MN76 f/6 (9 kg), MN86 8", ES-MN152 | APM-LZOS apo triplet |
| Mount topology | Counterweighted GEM | Fork + derotator | **Counterweight-FREE GEM** |
| Axis drive | NEMA17 + 27:1 + harmonic | Direct-to-harmonic | **Torque-motor direct drive** |
| Encoder | AMT103 + AS5600 | Hybrid (motor + on-axis abs.) | **On-axis high-res absolute ring** |
| Pier | Concrete Sonotube | Steel-concrete hybrid | **Isolated pier-in-pier** |
| Enclosure | Roll-off roof | Clamshell dome | **Roll-off + active thermal** |
| Frame | 6061-T6 CNC plates | Steel weldment | **Cast housings** |

### 2. Weighted-Pugh scores (default weights)

`pugh_scores.csv`. Winner of each subsystem in **bold**; the encoder baseline is
`DISQUALIFIED` by the tracking gate.

| Subsystem | Option | stiff | prec | cost | build | therm | src | **Weighted** |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| OTA | MN78 f/8 (baseline) | 2 | 4 | 3 | 3 | 4 | 2 | 2.94 |
| OTA | MN76 f/6 | 4 | 3 | 3 | 4 | 3 | 2 | 3.21 |
| OTA | MN86 8" | 1 | 4 | 2 | 2 | 3 | 1 | 2.16 |
| OTA | APM-LZOS **[BOLD]** | 2 | 5 | 1 | 3 | 3 | 2 | 2.76 |
| OTA | **ES-MN152** | 4 | 3 | 5 | 4 | 3 | 5 | **3.99** |
| Topology | Counterweighted GEM (baseline) | 3 | 3 | 3 | 4 | 3 | 4 | 3.31 |
| Topology | **Counterweight-FREE GEM [BOLD]** | 3 | 4 | 4 | 4 | 3 | 4 | **3.68** |
| Topology | Fork + derotator | 3 | 2 | 2 | 2 | 3 | 2 | 2.32 |
| Drive | **NEMA17 + 27:1 + harmonic (baseline)** | 3 | 2 | 4 | 4 | 3 | 4 | **3.24** |
| Drive | Direct-to-harmonic | 3 | 3 | 3 | 3 | 3 | 4 | 3.16 |
| Drive | Torque-motor DD **[BOLD]** | 3 | 5 | 1 | 2 | 2 | 2 | 2.73 |
| Encoder | AMT103 + AS5600 (baseline) | 3 | 1 | 5 | 4 | 3 | 5 | 3.33 `DISQ` |
| Encoder | On-axis RESA ring **[BOLD]** | 3 | 5 | 1 | 2 | 3 | 2 | 2.83 |
| Encoder | **Hybrid (motor + on-axis abs.)** | 3 | 4 | 2 | 3 | 3 | 3 | **3.07** |
| Pier | **Concrete Sonotube (baseline)** | 4 | 3 | 5 | 4 | 4 | 5 | **4.09** |
| Pier | Isolated pier-in-pier **[BOLD]** | 4 | 4 | 3 | 3 | 4 | 4 | 3.70 |
| Pier | Steel-concrete hybrid | 3 | 3 | 3 | 3 | 2 | 3 | 2.90 |
| Enclosure | **Roll-off roof (baseline)** | 3 | 3 | 5 | 5 | 3 | 5 | **3.92** |
| Enclosure | Clamshell dome | 3 | 3 | 2 | 2 | 2 | 2 | 2.44 |
| Enclosure | Roll-off + active thermal **[BOLD]** | 3 | 4 | 4 | 4 | 5 | 4 | 3.88 |
| Frame | **6061-T6 CNC plates (baseline)** | 3 | 3 | 4 | 4 | 4 | 4 | **3.56** |
| Frame | Steel weldment | 4 | 3 | 3 | 2 | 3 | 3 | 3.07 |
| Frame | Cast housings **[BOLD]** | 4 | 4 | 2 | 1 | 3 | 2 | 2.83 |

Two results are worth pausing on. First, the **encoder baseline has the *highest*
raw weighted score in its subsystem (3.33) yet is not selectable** — it fails the
1.0" gate (encoder proof: 5.02" RMS). A naive weighted sum would have kept a design
that misses the headline requirement by 5x; the gate is what prevents that, and it
is the single most important structural feature of this study. Second, the **OTA
math prefers the light in-production ES-MN152 (3.99), and among the Intes pair MN76
(3.21) out-scores the doc-'selected' MN78 (2.94)** — MN78 is the *worst* realistic
tube on the six mechanical axes, precisely because its 14 kg / 1.4 m tube is the
lever the stiffness proof FAILs on.

### 3. Sensitivity — precision-heavy and cost-heavy re-weighting

`sensitivity.csv`. Precision-heavy = {prec 0.40, stiff 0.20, cost 0.10, build 0.10,
therm 0.08, src 0.12}; cost-heavy = {cost 0.35, src 0.20, build 0.15, stiff 0.12,
prec 0.10, therm 0.08}.

| Subsystem | Default winner | Precision-heavy | Cost-heavy | Robust? |
|---|---|---|---|---|
| OTA | ES-MN152 (3.99) | ES-MN152 (3.74) | ES-MN152 (4.37) | **stable** |
| Topology | CW-FREE GEM (3.68) | CW-FREE GEM (3.72) | CW-FREE GEM (3.80) | **stable** |
| Drive | NEMA17+harmonic (3.24) | **Torque-motor DD (3.30)** | NEMA17+harmonic (3.60) | flips (prec) |
| Encoder | Hybrid (3.07) | **RESA ring (3.38)** | Hybrid (2.75) | flips (prec) |
| Pier | Sonotube (4.09) | Sonotube (3.82) | Sonotube (4.45) | **stable** |
| Enclosure | Roll-off (3.92) | **Roll-off + thermal (3.88)** | Roll-off (4.40) | flips (prec) |
| Frame | 6061 CNC (3.56) | 6061 CNC (3.40) | 6061 CNC (3.56/3.78) | **stable** |

The winner changes in exactly three subsystems, and **all three flips are in the
same direction**: weighting the sub-arcsec mission more heavily pulls the drive to a
zero-gear-PE torque motor, the encoder to the full on-axis ring, and the enclosure
to active thermal control — i.e. the bold options are the *precision* options, and
they win the moment precision dominates. Four subsystems (OTA, topology, pier,
frame) never move.

### 4. Selected permutation + rationale

The delivered build takes the default-weight winners, with two deliberate,
disclosed departures. It comprises **4 baselines, 2 bold picks, and 1 mandatory
bold-adjacent upgrade**:

1. **OTA — MN78 f/8 (science override of the mechanical winner).** The mechanical
   Pugh winner is ES-MN152 under every weighting, and MN76 beats MN78 among the
   Intes pair. MN78 is retained for its f/8 imaging scale and 0.134 obstruction —
   an optical/science requirement that lives *outside* the six mechanical criteria.
   This retention is not free: it is exactly why the stiffness proof FAILs, and it
   is the reason item 8 below is mandatory. If the bearing remediation proves
   insufficient, **MN76 is the drop-in mechanical hedge** (shorter CG lever, lower
   RA torque).
2. **Mount topology — Counterweight-FREE GEM [BOLD].** Robust winner under all three
   weightings. Grounded: torque proof gives RA SF 2.5 / DEC SF 2.6 on the harmonic
   drives' back-drive resistance, and the balance proof shows deleting the shaft +
   weights removes **15.4 kg and 29% of the RA inertia** — a strict improvement in
   what the drives and pier must carry, the same principle the ZWO AM5 / RST-135
   exploit.
3. **Axis drive — NEMA17 + 27:1 planetary + harmonic (baseline).** Wins default and
   cost-heavy; torque proof PASS. The planetary's periodic error — the only reason
   to consider deleting it — is **mooted by the on-axis encoder (item 4), which
   corrects everything upstream of the axis**, so the cheap standard OnStepX
   drivetrain is retained. (Under a precision-only view it flips to the torque
   motor; that is a documented, deferred upgrade path.)
4. **Encoder — Hybrid: motor encoder (velocity) + on-axis absolute (position)
   [mandatory on-axis upgrade].** The as-specified baseline is **DISQUALIFIED** —
   encoder proof: 5.02" RMS, 5x over target, because the AS5600's ~91" quantisation
   makes it homing-grade only and the servo must close on the motor encoder, which
   cannot see harmonic PE or mount flexure. Some form of on-axis absolute feedback
   is *required*, not optional (proof: on-axis ring reaches 0.54" RMS). The hybrid
   wins among qualifying options at default/cost weights; the **full on-axis RESA
   ring [BOLD]** is the selected upgrade when precision is weighted heavily and is
   the only option that reaches sub-arcsec outright.
5. **Pier — Concrete Sonotube (baseline).** Wins under all weightings (4.09). The
   pier proof already passes with governing SF 6.8 and f_n 152 Hz, so the bold
   isolated pier-in-pier would be **gold-plating the one part that is not the
   constraint** — the head/bearings are. Retained as baseline.
6. **Enclosure — Roll-off + active thermal [BOLD].** A statistical tie with the
   plain roll-off at default weights (3.88 vs 3.92, within noise), broken toward the
   bold variant by two proof findings the plain roof ignores: the **thermal FAIL**
   (22 K diurnal swing walks focus ~10x depth-of-focus) and the **power finding**
   that the DGX dumps ~14 K into the enclosure at 2 ACH ("ventilate or locate
   outside"). Active ventilation + insulation + day pre-cooling is the direct remedy,
   and it becomes the outright winner the instant precision is weighted up.
7. **Frame — 6061-T6 CNC plates (baseline).** Wins under all weightings (3.56). The
   key insight from the stiffness proof: the **aluminium plates are *not* the
   governing compliance — the bearings are** — so switching to a steel weldment or
   cast housings spends stiffness budget in the wrong place. Retain the machinable,
   DIY-friendly 6061 frame and fix the bearings instead (item 8).

**Cross-cutting actions the trade study surfaces but cannot select away.** Three
Phase-C FAILs are not closable by any of the seven morphological axes and are
booked here as required detail-design actions:

- **Stiffness (governing FAIL, 43.3" vs 5"):** fix at the *component* level, not the
  configuration level — replace the deep-groove 6008/6006 with **matched
  angular-contact 7008/7006 pairs (back-to-back) on larger spans** (bearings +
  stiffness proofs). No frame or topology choice in the box moves this number.
- **Wind (FAIL, roof uplift SF 0.19):** hold-down anchors are **mandatory and
  currently unspecified** — 4x 2 klbf anchors restore SF 3.9 (wind proof). Pair with
  the snow interlock the enclosure proof requires.
- **Off-grid power (FAIL):** the selected build assumes grid + UPS (16x shutdown
  margin). True autonomy needs a **48 V pack (13.4 h) or a DGX duty-cycle**, not the
  specified 12 V / 100 Ah pack (3.3 h). Orthogonal to the enclosure/pier choices.

**Net:** the selected permutation banks the two clearly-won bold improvements
(counterweight-free GEM, active-thermal enclosure) plus the mandatory on-axis
encoder, keeps the baseline where the baseline already passes (drive, pier, frame),
and honestly flags that the OTA choice, the stiffness fix, the wind anchors, and the
power autonomy are decisions the science mission and detail design must own — the
trade study cannot make them disappear.
