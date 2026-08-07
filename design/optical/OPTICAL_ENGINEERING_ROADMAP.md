# NIGHTWATCH Optical Engineering Roadmap

**Designing the telescope itself: a 180 mm Maksutov-Newtonian with a zero-expansion-class primary.**

Status: ROADMAP — Issued with release v0.1.1 (2026-08-06)
Companion to: `design/mechanical/MECHANICAL_DESIGN.md` (the pattern this effort mirrors)
Method: assertion → proof → tender, with S/D/A provenance and PASS/FAIL gates

---

## 0. Why this exists

The mechanical effort engineered everything *around* the telescope — mount, pier, roof,
bearings, encoders, power — and proved it with computed budgets. The optical tube itself
appears in those documents only as a payload mass and a line on the COTS schedule that
says, in effect, "buy a used Russian tube."

That line no longer survives contact with reality, and this document exists because we
checked:

- **Intes Micro ceased production in 2018.** Adjudicated with dated sources and DNS/
  Wayback evidence (see `docs/research/SOURCING_RESEARCH.md`, corrected 2026-08-06).
  The repo's earlier "still producing March 2025" claim was traced to a frozen 2005-era
  website and recycled forum lore.
- **The used market is thin and cannot be specified.** Used MN76/78 units surface
  intermittently at ~$1,500–2,500, with unverifiable optical figure and almost never the
  Astrositall (Alter-grade) substrate that motivated the selection.
- **No current product meets the requirements** (§1.3). The only in-production
  Maksutov-Newtonian above 152 mm — Sky-Watcher Starlux 190MN, $2,375 — is an f/5.3
  astrograph with 27–34% obstruction and a borosilicate primary.

Therefore NIGHTWATCH designs its own optics. This roadmap defines the requirements, the
engineering phases, the CI-proof structure, the procurement strategy, and the budget —
with every load-bearing number carrying its provenance, exactly as the mechanical effort
demanded of itself.

**Scope discipline:** telescope components only — optical prescription, glass, cell and
collimation interfaces, baffling, thermal behavior of the optics, acceptance testing.
No observatory automation, no enclosure, no mount (those interfaces are referenced, not
re-opened).

---

## 1. Mission and requirements flowdown

### 1.1 Mission ranking (SOURCED — NIGHTWATCH_Build_Package.md:32-40)

1. Mars surface features (5/5)
2. Lucky imaging / high-speed planetary capture (5/5)
3. Autonomous overnight operation (5/5)
4. Remote monitoring (5/5)
5. Deep-sky visual (bonus, 4/5)

NEO follow-up astrometry is a standing secondary interest (services/meteor_tracking is
already flying); it influences field-of-view as a tiebreaker, not a driver (§4).

### 1.2 De-facto optical requirements (SOURCED — docs/SCIENTIFIC_FOUNDATIONS.md App. A)

| Requirement | Value | Source |
|---|---|---|
| Aperture class | 180 mm (7") | Build Package + params.py (both fork branches agree) |
| System Strehl (design + fab) | ≥ 0.95 at 546–550 nm (λ/8 P-V class) | SCIENTIFIC_FOUNDATIONS.md:158-166, A.2 |
| Diffraction floor | Strehl ≥ 0.80 (Maréchal) after all budgets | SCIENTIFIC_FOUNDATIONS.md:144-154 |
| Angular resolution | Rayleigh 0.78″, Dawes 0.65″ at 180 mm | App. A.1 |
| Site seeing to exploit | r₀ = 10–15 cm, τ₀ = 3–8 ms (lucky imaging) | App. A.3 (ASSUMED — unmeasured, see risk R6) |
| Thermal environment | ~22 K diurnal swing, alkaline desert dust | params.py Site/Environment; MECHANICAL_DESIGN.md |
| Sampling | Nyquist at diffraction cutoff per chosen sensor | App. A.4 (re-derived per f-ratio in §4) |
| Back focus | ≥ 55 mm usable (imaging-train convention) | Industry standard; MN190 practice |

### 1.3 The make-vs-buy gate: requirements no COTS instrument satisfies

The four requirements below justify custom fabrication. If any future finding relaxes
all four, the buy-side (§2) reopens.

- **(a) Zero-expansion-class primary.** Preferred CTE ≤ 0.1 ppm/K (Zerodur,
  Clearceram-Z HS, ULE, or an opportunistic Sitall CO-115M find); fused silica at
  0.52 ppm/K is the acceptable baseline. *Proven substrate-tolerant:* re-running the
  repo's own thermal-focus proof with fused-silica CTE leaves the verdict unchanged —
  the aluminum tube term dominates the mirror term 44–153×, and the
  temperature-compensated focuser remains mandatory at any f-ratio (§5, P1-T4).
- **(b) Central obstruction ≤ 18–20%, custom-sized** to the illuminated field actually
  needed (§4.2) rather than inherited from a catalog.
- **(c) Certified wavefront:** λ/8 P-V class with raw interferograms deliverable — not a
  25-year-old marketing claim on a used tube.
- **(d) Sealed tube** (full-aperture corrector) for Nevada's alkaline dust and
  unattended operation.

Starlux 190MN fails (a), (b), (c). Used Intes fails (c) always and (a) almost always
(Alter-grade Astrositall units are unicorns). Newtonian + coma corrector fails (d) and
gives up the no-spider contrast advantage (§3.4).

### 1.4 Decision packets required before design freeze (P0)

1. **Planetary camera baseline** — IMX678 (2.0 µm) vs IMX585 (2.9 µm). This single
   choice moves the required Barlow at f/6 from 1.76× to 1.21× (550 nm) and reorders
   the sampling row of the fork matrix (§4.1). Deliverable: price/QE/availability
   one-pager + decision.
2. **Sub-arcsecond tracking status for v1** — mechanical v1 concedes ~5″ with
   plate-solve recentering; confirm the optics budget should not carry sub-arcsec
   assumptions for v1.
3. **Focuser steps→µm coefficient** — still absent from `params.py`; blocks closure of
   the thermal-focus compensation proof (MECHANICAL_DESIGN.md:383).

---

## 2. Make-vs-buy evidence and the contingency line

| Path | Cost | Availability | Meets §1.3? | Verdict |
|---|---|---|---|---|
| New Intes MN76/78 | — | **Closed** (production ended 2018; sanctions ended reseller channels 2022) | — | Impossible |
| Used MN76/78 | $1,500–2,500 + months of watching | Intermittent, thin | (c) no; (a) rarely | Watch-list only |
| Intes raw optical set via APM | — | **Gone** (APM carries no Intes stock as of 2026-08) | — | Closed |
| Sky-Watcher Starlux 190MN | $2,375 new | In production, 2–4 weeks | (a),(b),(c) no | **Named contingency/interim OTA** |
| **Custom design + fabrication** | **$6.5k–12k (committed envelope, §6)** | 6–12 months | **Yes, by construction** | **Plan of record** |

The Starlux 190MN line stays in this document deliberately: it is the only way to get
*any* large Mak-Newt on the pier within a month if the program needs an interim
instrument, and its 13.2 kg mass is inside the mount envelope already proven for the
14 kg MN78 case.

A standing **used-market watch** (Astromart + Cloudy Nights classifieds, weekly) also
stays open: a genuine Alter-grade MN78 at a sane price would satisfy §1.3(a),(b),(d)
and could be upgraded to (c) by independent testing — it would then compete honestly
with the custom path at the P3 gate.

---

## 3. The glass story

### 3.1 Astrositall (Sitall CO-115M) — the signature, honestly stated

Astrositall is the Soviet/Russian zero-expansion glass-ceramic (CTE 0 ± 1.5×10⁻⁷/°C
over −60…+60 °C) used in premium "Alter" Intes instruments — the original inspiration
for NIGHTWATCH's glass identity. The 2026 reality:

- **LZOS (Lytkarino) is sanctioned** (Shvabe/Rostec; US Consolidated Screening List).
  Western resellers stopped purchasing in March 2022. New CO-115M import is effectively
  impossible.
- **Secondary market is opportunistic only:** observed lots are ~120 mm blanks and one
  8″ × 1.25″ blank on Astromart — not a plannable procurement at ~200 mm.

**Resolution:** the primary is specified by **CTE class, not brand**:

> *Primary substrate: zero-expansion class, CTE ≤ 0.1 ppm/K (Zerodur / Clearceram-Z HS /
> ULE 7972 / Sitall CO-115M), or fused silica (Corning 7980 class, 0.52 ppm/K) as the
> cost baseline. Substrate choice shall not require redesign (proven: thermal proof is
> substrate-independent, §1.3a).*

A standing **Sitall watch** (eBay/Astromart alerts for ≥190 mm CO-115M blanks) keeps the
signature alive as a drop-in swap. If a blank surfaces, it replaces the baseline at the
next procurement gate with zero prescription change.

### 3.2 Primary blank sourcing (P3 Lot A input)

| Substrate | CTE (ppm/K) | ~200 mm blank path | Indicative cost | Confidence |
|---|---|---|---|---|
| Fused silica (Corning 7980) | 0.52 | Advanced Glass Industries, United Lens (stock/custom) | $400–900 | Medium (RFQ needed; 200×5 mm window seen at $647 retail) |
| Zerodur (Schott) | 0.00±0.007 (class 0) | Schott quote; secondary market (7″ blank seen at $359) | $1,500–3,000 new | Low (no published price) |
| Clearceram-Z HS (Ohara) | 0.0±0.02 | Ohara quote (material in volume production for TMT) | quote-only | Low |
| Sitall CO-115M | 0.0±0.15 | Opportunistic secondary market only | n/a | — |

### 3.3 Corrector blank and secondary flat

- **Corrector blank (the critical-path item):** N-BK7 (Schott) or H-K9L (CDGM),
  ~230 mm dia × 35 mm, fine annealed, homogeneity **H2** (±5×10⁻⁶), bubble class ≤ B1,
  striae grade A. Schott TIE-41 confirms H2 producibility above 300 mm — availability
  is real; cost is the question ($400–900 est., RFQ). **Borofloat/Supremax are
  excluded** for the transmissive corrector (float/rolled glass carries no homogeneity
  or striae grade).
- **Secondary flat: a solved COTS problem — zero engineering effort allocated.**
  Antares 1.83″ minor-axis 1/30-wave elliptical at $181.49 (quoted); Ostahowski
  fused-quartz 1/10-wave-plus diagonals with interferograms as alternate. Final minor
  axis follows the P1-T5 secondary-sizing proof.

### 3.4 Why a meniscus at all (the honest trade memo, to be proven in P2)

The Mak-Newt buys, over a Newtonian + Paracorr-class corrector: no spider (no spikes,
higher planetary contrast), smaller achievable obstruction (17–20% vs 25–32% typical),
all-spherical surfaces (cheap to figure *accurately*), and a sealed tube. It costs:
a thick (~D/10) meniscus with slow thermal equilibration (fan + heater already in the
system budgets), ~2 kg extra glass, corrector tilt sensitivity (1° tilt = 0.27λ P-V
coma — drives the cell spec, §5 P1-T7), and the corrector fabrication bill (§6).
P2's trade study scores this with the same Zwicky/Pugh + hard-gate method the
mechanical effort used; if the meniscus loses on evidence, this roadmap pivots before
any glass is bought.

---

## 4. Resolving the fork: f/6 vs f/8 is a false binary

The repo has carried "MN76 f/6 vs MN78 f/8" as an unresolved fork
(`design/mechanical/calc/params.py:85-109`; trade study selected MN78 only as a
"science override"). **Because NIGHTWATCH now designs its own optics, the fork
dissolves:** focal ratio is a continuous variable, and central obstruction is
semi-independent of it (set by focuser height + illuminated-field diameter, not by
f-ratio alone).

**Provisional target (70% confidence): 180 mm f/6.5–f/7, obstruction ≤ 18%.**

### 4.1 Decision inputs (computed, this research pass)

- **Sampling** (Nyquist at diffraction cutoff, F = 2·pixel/λ):
  | Sensor | λ 550 nm | λ 656 nm | Barlow at f/6 | at f/7 | at f/8 |
  |---|---|---|---|---|---|
  | IMX585/462 (2.9 µm) | f/10.5 | f/8.8 | 1.76× | 1.51× | 1.32× |
  | IMX678 (2.0 µm) | f/7.3 | f/6.1 | 1.21× | 1.04× | 0.91× |
  A 2.0 µm sensor nearly closes the f/6 sampling gap natively at 656 nm; every path
  needs at most one high-quality amplifying element, and the ADC sits in the amplified
  beam in all cases.
- **Obstruction MTF** (computed annular-pupil autocorrelation): mid-band contrast loss
  vs unobstructed ≈ 10–18% at ε=0.25, but only 3–5% at ε=0.134. A custom ε=0.16–0.18
  recovers most of the f/8 advantage at any f-ratio — pending the P1-T5 illumination
  proof (MN76's measured **3 mm** fully-illuminated field is the cautionary tale).
- **Corrector cost:** f/6 vs f/8 delta is **<10%** (ray-trace-verified: only the
  R1−R2 match tolerance tightens, ±0.13 mm vs ±0.30 mm — both routine test-plate
  practice). The corrector does not decide the fork.
- **Mechanics:** tube length is a *weak* lever on the pointing-deflection FAIL (1.42×
  across 0.9–1.4 m; bearing **span** is the real lever — DEC ≥ 105 mm / RA ≥ 125 mm
  needed for the 5″ target, a BP-01 housing-geometry item, cross-cutting action §5
  P2-X1). Mount and roof budgets are already proven for the worst case (14 kg, 1.4 m).
- **Depth of focus:** ±39.6 µm (f/6) / ±53.9 µm (f/7) / ±70.4 µm (f/8) — second-order,
  since the 22 K swing walks focus ~10–18× DoF regardless and temp-compensated focusing
  is mandatory at any f-ratio.
- **FOV (NEO tiebreaker):** shorter FL buys 1.82× sky area per pointing; all
  sensor/FL combinations plate-solve routinely.

### 4.2 What settles it (P1/P2 gate tasks)

1. Sensor decision packet (P0-1).
2. Ray-trace the custom meniscus at f/6, f/6.5, f/7, f/8 — poly-Strehl + tolerance
   Monte Carlo → manufacturability-vs-f-ratio curve (P1-T1/T8).
3. Secondary-sizing/illumination ray trace at each f-ratio with a low-profile focuser
   stack → minimum honest obstruction (P1-T5).
4. Two real corrector quotes at f/6 and f/8 seed radii (P3 RFQ round 1) to replace the
   <10% estimated delta with vendor numbers.

The trade study (P2) then scores the continuous options and **retires the MN76/MN78
fork permanently**, updating `params.py` and the mechanical trade-study row.

---

## 5. Phase plan

Phases gate forward progress; each has entry/exit criteria. The structure deliberately
mirrors `design/mechanical/`: a generated design doc, `calc/` proof modules paired 1:1
with pytest gates, a locked trade study, then tender packages.

### P0 — Decision packets (no hardware cost)
**Exit gate:** the three §1.4 decisions written into `design/optical/calc/params.py`
with S/D/A provenance.

### P1 — Design skeleton and proofs (no hardware cost)
Create `design/optical/` mirroring the mechanical layout:

```
design/optical/
├── OPTICAL_DESIGN.md          # GENERATED by calc/report.py (drift-gated)
├── calc/
│   ├── params.py              # frozen dataclasses + PROVENANCE (S/D/A) — supersedes
│   │                          #   the 2-field Optical dataclass in mechanical params
│   ├── prescription.py        # radii/thickness/spacing/glass, both seed cases
│   ├── strehl_budget.py       # T1: poly-Strehl ≥ 0.95 gate (optiland + prysm)
│   ├── obstruction_mtf.py     # T2: annular MTF, integral contrast
│   ├── sampling.py            # T3: Nyquist/Barlow per sensor per band
│   ├── thermal_focus.py       # T4: substrate CTE sweep; focuser compensation
│   ├── secondary_sizing.py    # T5: illuminated field vs obstruction vs focuser height
│   ├── baffles.py             # T6: stray-light geometry, knife-edge positions
│   ├── collimation_tol.py     # T7: tilt/decenter/despace sensitivities (1° = 0.27λ)
│   ├── tolerancing.py         # T8: Monte Carlo yield at fab tolerance grades
│   └── report.py              # regenerates OPTICAL_DESIGN.md
└── tests/                     # test_*.py paired 1:1 + test_report.py drift gate
```

**Seed prescriptions (ray-trace-verified this research pass; DERIVED):**
N-BK7 meniscus, OD 215 mm, CA ≥ 204 mm, CT 22 mm, achromat condition
R1−R2 = −0.565·t with spherochromatism factor /0.97:

| Case | Mirror R | Corrector R1 | Corrector R2 |
|---|---|---|---|
| f/6 (FL 1224) | −2448 mm | −413.1 mm | −425.6 mm |
| f/8 (FL 1632) | −3264 mm | −513.4 mm | −525.8 mm |

(Seeds only — final prescription co-optimizes with the actual primary and the
coma-zero corrector spacing; intermediate f-ratios interpolate.)

**Tolerance table to encode as test fixtures (SOURCED — CFHT Baril 7.5″ f/8 precedent
+ standard precision-optics grades):** R1, R2 individually ±1%; **(R2−R1) to 0.1%**
(the governing fabrication tolerance); thickness and mirror radius ±2%; wedge ≤ 1′
(≤10 µm ETR); index homogeneity ≤ 2×10⁻⁴; corrector tilt spec: arcminutes (cell
design driver).

**Tooling (all pip-installable, CI-compatible; no commercial license):**
- **optiland** (MIT) — primary ray-trace engine: spots, wavefront, PSF/MTF, glass
  catalogs, sensitivity + Monte Carlo tolerancing
- **ray-optics** — independent cross-check engine (.zmx import for interchange)
- **prysm** (MIT) — physical-optics layer for the polychromatic Strehl/MTF budget gates
- **OSLO EDU** (free, 10-surface limit; this system is 5–6 surfaces) — offline human
  sanity check

**Exit gate:** all T1–T8 proofs green in CI for at least two f-ratio cases;
OPTICAL_DESIGN.md generated with a PASS/FAIL results table (FAILs are findings, not
embarrassments — the mechanical effort's five FAILs were its most valuable output).

### P2 — Trade study (no hardware cost)
Zwicky morphological box × weighted Pugh with **hard disqualification gates** (the
encoder-DISQ pattern): axes = f-ratio (continuous) × obstruction (T5-derived) ×
substrate (§3.2). Grounded exclusively in P1 proof outputs, never opinion.
**Cross-cutting action P2-X1:** feed the bearing-span requirement (DEC ≥ 105 mm /
RA ≥ 125 mm) back to BP-01 housing geometry — an optics-driven mechanical change the
study cannot select away.
**Exit gate:** selected prescription frozen in `params.py`; MN76/MN78 fork formally
retired; mechanical trade-study row updated.

### P3 — Tender package BP-06 (RFQ round; no fabrication commitment yet)
Three separately-awardable lots, mirroring the BP-01..05 anatomy (README + SOW +
acceptance + ASSUMED-design-intent registers):

- **Lot A — Primary mirror** (spherical, 180–200 mm, substrate per §3.2).
  Candidates: **Ostahowski Optics** (primary candidate — quotes one-offs, works quartz
  and ceramics, interferograms with every surface, in-house coating), Lockwood Custom
  Optics, Optical Mechanics Inc, Orion Optics UK. *(Zambuto closed to new orders
  2025-08-15; ISTAR not accepting orders — both verified 2026-08.)*
- **Lot B — Meniscus corrector** (60–75% of optics cost; melt-data design-assist
  clause REQUIRED: final radii co-optimized to the delivered blank's melt sheet).
  Candidates: Optimax (RFQ funnel go.optimaxsi.com / sales@optimaxsi.com /
  585-265-1020; prototype-singles capability; coats to 500 mm), Knight Optical UK
  (+44 1622 859444, custom menisci explicitly offered), United Lens (508-765-5421,
  blank + machining + annealing under one roof), Advanced Glass Industries
  (585-458-8040, blanks). RFQ-ready spec sheet: Appendix C.
- **Lot C — Secondary flat** → moves to the BP-05 COTS schedule (Antares 1.83″
  1/30-wave, $181.49 quoted; Ostahowski quartz alternate).

**Acceptance criteria (written now, argued never):** system transmitted wavefront
≤ λ/4 P-V and ≤ λ/14 RMS, **Strehl ≥ 0.95 at 546–550 nm**, double-pass autocollimation
interferometry at 20 ± 2 °C after thermal soak, optic unstressed in test mount, Zernike
table + **raw interferogram data** deliverable. Component-level interferograms from the
fabricator, plus **one independent verification** (Orion Optics UK test service, or
AstroReflect/AiryLab) as the payment gate — the optics analog of the mechanical
PE-stamp gate.

**Exit gate (budget checkpoint):** ≥ 2 real quotes per lot; fabrication go/no-go
against the §6 envelope; the used-market watch (§2) gets its last look here.

### P4 — Fabrication and coating (hardware money at risk)
- Corrector is the critical path: 3–6 months typical.
- Mirror coatings (quoted price list, Spectrum Coatings 2026-08): 8″-class primary
  $90/$130/$150 (protected/enhanced/MaxR aluminum), secondary $25–50, center-mark $10.
  Corrector BBAR (R < 0.5% avg 400–700 nm both sides) quoted separately — often
  cheapest bundled with the lens fabricator.
- Progress payments tied to component interferograms.

### P5 — Acceptance and integration
- Component + assembled-system interferometry per P3 criteria; independent test gate.
- Optical-mechanical design: mirror cell (zero-expansion substrate → athermal cell),
  corrector cell with arcminute-class tilt retention, collimation mechanism usable on
  a sealed tube, knife-edge baffles per T6.
- Interfaces: tube structure to BP-01/BP-02 machining packages; corrector dew heater
  < 2 W and temperature-compensated focuser tie-in (hard requirement, any f-ratio).

### P6 — First light and verification
- Star test + lucky-imaging pipeline measured against the T1 Strehl budget;
  double-pass autocollimation repeat after transport; thermal-equilibration
  characterization (2–3 h pre-cool policy per the Petrunin review criteria).
- **Site-seeing measurement task** (risk R6): DIMM or star-trail seeing monitor to
  replace the ASSUMED r₀ = 10–15 cm with data.

---

## 6. Budget (plan of record)

**Decision (Tim, 2026-08-06): the expanded optics envelope is committed now** — not
gated on RFQs. RFQ checkpoints (P3) refine numbers but do not reopen the commitment.

| Item | Range | Basis |
|---|---|---|
| Meniscus corrector (fab + AR, one-off US shop) | $3,500–6,500 (central $5,000) | Triangulated from 3 public anchors; ±40% until RFQ |
| — Chinese-fab option (H-K9L) | $1,500–3,000 | Unverified; higher QA risk |
| Primary mirror (blank + figure + cert) | $1,200–3,000 | Ostahowski $2,800/10″ quartz comp; sphere is easier |
| Secondary flat (finished, certified) | $150–250 | Antares quoted $181.49 |
| Mirror coatings (primary + flat) | $150–250 | Spectrum quoted table |
| Corrector BBAR (if not bundled) | $400–1,500 | Estimate |
| Independent acceptance test | $300–1,500 | Estimate (AiryLab/Orion Optics class) |
| Design-assist / melt re-optimization | $1,000–5,000 contingent | Estimate; may be absorbed by Lot B vendor |
| **Optics envelope** | **$6,500–12,000** | **Committed** |

Project context, stated honestly: the prior all-in target was $8,500–9,500 and the
mechanical selected configuration already consumed its contingency (+$2,290–5,790 in
mandatory remediations). With this envelope the **project total is acknowledged at
~$15,000–20,000.** The $900 eyepiece line and other visual accessories remain the
obvious donors if trimming is ever required.

Schedule: corrector RFQ turnarounds 3–10 business days; fabrication 3–6 months;
custom set end-to-end **6–12 months**. P0–P2 cost nothing but engineering time and
should complete before any RFQ goes out.

---

## 7. Risk register

| # | Risk | Exposure | Mitigation |
|---|---|---|---|
| R1 | Corrector single-vendor concentration (Lot B is 60–75% of cost) | Schedule + cost | ≥ 2 quotes incl. one non-US channel; melt-assist clause; Starlux contingency line |
| R2 | Sitall unobtainium erodes the "unique glass" identity | Identity/scope | CTE-class spec (§3.1) makes substrate a drop-in; standing Sitall watch |
| R3 | Corrector cost band is estimator-grade (no signed quote yet) | Budget | P3 RFQ round anchors it; envelope carries the high end |
| R4 | Custom obstruction ≤ 18% unproven until T5 illumination trace | Performance | T5 is a P1 exit-gate proof, before any procurement |
| R5 | BK7 poly-Strehl ≥ 0.95 at f/6 is derived, not yet traced | Performance | T1 gate at multiple f-ratios; f-ratio floats until P2 |
| R6 | Site r₀ = 10–15 cm is ASSUMED, never measured | Mission | P6 seeing-monitor task; lucky-imaging yield model re-run with data |
| R7 | Bearing-span remediation (P2-X1) touches BP-01 machining | Interface | Cross-cutting action tracked in both documents |
| R8 | Budget expansion (~$15–20k total) outruns appetite | Program | Committed knowingly (Tim, 2026-08-06); P3 checkpoint is the natural re-look |

---

## Appendix A — Seed prescription table (DERIVED, ray-trace-verified 2026-08-06)

Glass N-BK7 (n_e = 1.51872, n_F = 1.52238, n_C = 1.51432); OD 215.0 +0/−0.2 mm;
CA ≥ 204 mm; CT 22.0 ± 0.2 mm; achromat condition R1−R2 = −0.565·t (with /0.97
spherochromatism factor); corrector-mirror gap seed 0.85·f; residual F–C focus shift
~10–11 µm at the 0.7 zone (inside depth of focus); element mass ≈ 2.0 kg.

| Case | Mirror R (mm) | R1 (mm) | R2 (mm) | Sag₁ (mm) | Edge thickness (mm) |
|---|---|---|---|---|---|
| f/6, FL 1224 | −2448 | −413.1 | −425.6 | 14.2 | 21.6 |
| f/8, FL 1632 | −3264 | −513.4 | −525.8 | 11.4 | 21.7 |

Radius-match tolerance for diffraction-limited focus: ±0.13 mm (f/6) / ±0.30 mm (f/8);
common (pair) radius error: ±3.7 mm (f/6) / ±11 mm (f/8). R/D ≈ 2.0–2.5 both cases —
gentle spheres, routine test-plate work.

## Appendix B — Verified vendor contacts (2026-08-06)

| Vendor | Role | Contact |
|---|---|---|
| Ostahowski Optics | Primary (Lot A lead) | ostahowskioptics.com — quotes by email/phone |
| Lockwood Custom Optics | Primary alternate | loptics.com — 50% deposit model |
| Orion Optics UK | Primary alternate + **independent Zygo test service** | orionoptics.co.uk |
| Optimax | Corrector (Lot B lead) | go.optimaxsi.com/rfq · sales@optimaxsi.com · (585) 265-1020 |
| Knight Optical UK | Corrector | +44 (0)1622 859444 — custom menisci page |
| United Lens | Corrector/blank | (508) 765-5421 · info.unitedlens.com/request-a-quote |
| Advanced Glass Industries | Blanks | sales@advancedglass.net · (585) 458-8040 |
| Antares Optics | Secondary flat (COTS) | antaresoptics.com — live prices |
| Spectrum Coatings | Mirror coating | paul@spectrum-coatings.com · (386) 848-3924 |
| AstroReflect / AiryLab | Independent testing | astroreflect.com (free offer) / airylab.com |

Removed from candidate lists (verified 2026-08): Zambuto (closed to new orders
2025-08-15), ISTAR Optical (not accepting orders), the Optimax online Estimator
(offline; DNS dead + 404).

## Appendix C — RFQ-ready corrector specification

> Full-aperture Maksutov meniscus corrector, qty 1 (option qty 2). Material SCHOTT
> N-BK7 or CDGM H-K9L, fine annealed, homogeneity H2, bubble ≤ B1, striae grade A.
> OD 215.0 +0/−0.2 mm; CA ≥ 204 mm; CT 22.0 ± 0.2 mm. Baseline (f/8): R1 = −513.4 mm,
> R2 = −525.8 mm; alternate (f/6): R1 = −413.1 mm, R2 = −425.6 mm. Radii to test plate
> ±0.1%; R1−R2 difference held to ±0.25 mm (f/8) / ±0.10 mm (f/6), coupled to CT per
> R1−R2 = −0.565·t. Irregularity ≤ λ/8 P-V per surface at 633 nm over CA; surface
> quality 60-40; wedge ≤ 1 arcmin ETD. BBAR both sides, R_avg < 0.5%, 400–700 nm.
> Note: seed radii are optimization starting points — final prescription to be
> co-optimized with the specific primary and delivered melt data (design-assist clause).

## Appendix D — Documentation corrections executed with this roadmap

1. `docs/INTES_MICRO_HISTORY.md` — "environmental regulations" blank-scarcity claim
   softened to the evidenced cost/lead statement (Schott TIE-41; in-production 190MN).
2. `docs/research/SOURCING_RESEARCH.md` — MN76≠MN78 nomenclature corrected (f/6 vs
   f/8, different models); the false "still producing March 2025" claim replaced with
   the adjudicated 2018 cessation and its evidence trail; APM raw-optics channel marked
   historical; direct-Russia action item closed (sanctions).

---

*Method note: every number above is tagged by origin — SOURCED (repo or cited page),
DERIVED (computed this pass; ray traces and MTF autocorrelations re-runnable in P1 CI),
or estimate pending RFQ. The research dossier with per-claim URLs was produced by the
2026-08-06 multi-agent research workflow and is summarized in the PR that introduced
this file.*
