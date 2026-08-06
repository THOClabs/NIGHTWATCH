# BP-03 — Inspection & Test / Acceptance Plan: Pier & Foundation

> **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**

| Field | Value |
|---|---|
| Package | BP-03 — Pier & foundation |
| Parts | NW-PF-001 (RC pier), NW-PF-002 (top plate), NW-PF-003 (adapter plate), NW-PF-004 (anchor set) |
| Method | Concrete **cylinder breaks** + slump/air; **anchor proof/pull** test; **plumb/level** survey; rebar-placement & cover inspection; galvanize/anodize coating verification; plate dimensional check |
| Issue date / rev | 2026-08-06 / A |

> ## PE-STAMP GATE — this plan is not executable until the PE approves it
> **The reinforced-concrete pier and anchor set are ISSUED FOR PE REVIEW.** This Inspection & Test Plan
> (ITP) and its accept/reject limits are **provisional pending the PE-stamped structural drawings.**
> The PE sets the final f'c acceptance basis, the reinforcement/cover inspection criteria, the anchor
> proof load, and owns the **field hold points** below. **No concrete is placed and no anchor is cast
> until the stamped drawings and the PE-approved ITP are in hand.**

**Scope.** This plan defines the inspection methods and accept/reject criteria for BP-03. The concrete
strength (cylinder breaks), the anchor proof/pull, and the pier plumb/level are the **critical
characteristics**. All limits are dual-unit and derived from `partspec` / the NW-PF control drawings —
nothing invented. Concrete field/lab test methods are those **invoked by ACI 301**; where a specific
ASTM C-series method is named it is the method ACI 301 calls up (flagged **PE to confirm** if outside
the tender's standards register).

**Standards.** ACI 318 (structural concrete; Ch.17 anchoring); ACI 301 (concrete spec, invokes the
field/lab test methods and ACI 117 tolerances); ASCE 7 (loads — PE); ASTM A615 Gr60 (rebar);
ASTM F1554 Gr36 (anchors); ASTM A123 (galvanize coating thickness); ASTM B209 (6061-T6);
MIL-A-8625F (anodize); ASME Y14.5-2018 (plate GD&T); ISO 286 / ISO 2768 (fits / general tolerance);
ISO 1 (20 °C metrology reference for the plates).

---

## 1. Field hold points (PE / owner sign-off required to proceed)

| # | Hold point | Verify before proceeding | Sign-off |
|---|---|---|---|
| H1 | **Excavation / embedment** | Depth ≥ 914.4 mm [36.000 in] and ≥ site frost depth; bearing soil per PE | PE |
| H2 | **Rebar cage set** | Bar size/count/spacing, cover, splices, seismic hoops vs stamped cage | PE |
| H3 | **Anchor template set** | 4 × F1554 plumb, projection 50.0 mm [1.969 in], pattern vs NW-PF-002 | PE |
| H4 | **Pre-pour** | Forms, isolation gap from any slab, cleanliness, mix delivered = approved mix | PE / owner |
| H5 | **Pour + cylinders cast** | Placement, consolidation, cylinders fabricated & cured | Inspector |
| H6 | **Strip / cure complete** | Form strip, cure duration, surface finish | Bidder QA |
| H7 | **28-day strength + anchor proof** | f'c met; anchor proof/pull passed; plumb/level survey | PE |

---

## 2. Concrete — cylinder breaks & fresh-concrete tests (NW-PF-001)

**Specified strength:** **f'c = 4000 psi (27.6 MPa)** at 28 days, per ACI 318 / ACI 301.

| Test | Method (invoked by ACI 301) | Frequency | Accept criterion |
|---|---|---|---|
| **Compressive strength** | cast + cure standard cylinders; lab break (ACI 301 → ASTM C31 fabrication, ASTM C39 test) *(method PE to confirm)* | min. 1 set (pier is a single small pour); set = 2× 28-day + 1× 7-day + 1 spare | ACI 318 §26.12: avg of any 3 consecutive tests ≥ f'c **and** no single test < f'c − 500 psi [3.4 MPa] *(PE to confirm basis for a single-pour element)* |
| **7-day break (info)** | as above, 7-day | 1 cylinder | typically ≥ 65–70% f'c *(ASSUMED — trend indicator, not accept gate)* |
| **Slump** | ACI 301 → ASTM C143 | each load | per approved mix design ± tolerance *(PE to set)* |
| **Air content** | ACI 301 → ASTM C231 | each load (if air-entrained) | per approved mix *(PE to set — may be N/A)* |
| **Temperature** | ACI 301 (fresh-concrete temp) | each load | within hot/cold-weather limits (ACI 301) |

**Notes.** Cylinders cured and broken by an approved testing lab. Because the pier is a **single small
pour (≈0.13 m³ [≈4.7 ft³])**, the sampling frequency and the single-element acceptance basis are
**PE to confirm** (a small element may use a reduced set with the PE accepting the risk). **Concrete
below f'c → PE disposition** (core testing per ASTM C42, load evaluation, or reject) — no
self-disposition by the bidder.

---

## 3. Reinforcement placement & cover (NW-PF-001)

| Characteristic | Criterion | Method | Class |
|---|---|---|---|
| Bar size / grade | #4 vertical, #3 ties, **ASTM A615 Gr60** (or PE-stamped substitute) | mill cert + tape/gauge | Critical |
| Bar count | 6 × vertical (or PE-stamped) | count at H2 | Critical |
| Tie spacing | #3 @ 12 in [304.8 mm] oc (or PE-stamped) | tape at H2 | Major |
| **Clear cover** | ~76 mm [3.00 in] cast against earth *(ASSUMED — PE to set)* | cover meter / spacers | Critical |
| Splices / hooks / development | per ACI 318 Ch.25 (PE-stamped) | visual at H2 | Critical |
| Seismic hoop/confinement detail | per PE (S_DS ≈ 0.5 g ASSUMED) | visual at H2 | Critical |

> The full reinforcement schedule is **ASSUMED design-intent**; the accept criteria above become
> gates **only when the PE stamps the cage.**

---

## 4. Anchor-bolt set — proof / pull test (NW-PF-004)

**Anchors:** 4 × Ø19.05 mm [0.750 in] × 304.8 mm [12.000 in] ASTM F1554 Gr36, galvanized, cast per
ACI 318 Ch.17.

| Characteristic | Criterion | Method | Class |
|---|---|---|---|
| Material / grade | ASTM F1554 Gr36 | mill cert / CoC | Critical |
| Galvanize | ASTM A123 coating-thickness record | magnetic gauge | Major |
| Projection | 50.0 mm [1.969 in] ± *(PE)* | scale | Major |
| Pattern (as-cast) | matches NW-PF-002 4 × Ø0.81 holes; template tol ± 0.02 mm | template / bolts drop through plate | Critical |
| Plumb | vertical within *(PE tol)* | level | Major |
| **Proof / pull test** | apply PE-specified proof load and hold; **no slip, no concrete cracking/breakout** | calibrated hydraulic ram + reaction frame *(protocol PE to confirm)* | **Critical** |

**Proof-load basis (PE to set).** Tie the proof load to the governing tension demand. Bounding wind
case (`MECHANICAL_DESIGN.md` §7): roof gross uplift **9.2 kN**, net anchor demand **7.4 kN** across the
4-anchor group → **~1.85 kN/anchor service demand**; 4× 2 klbf [≈8.9 kN] capacity → **SF 3.9**. The
**field proof load per anchor is PE-specified** (commonly a factor of the service/design tension) and
**ASSUMED here pending PE**. Cast-in anchors are primarily accepted by **material cert + placement
inspection (H3)**; the proof/pull test is the **PE/owner-specified confirmation** requested for this
package. **Do not exceed a load that would damage the anchor or the young concrete — schedule after the
28-day strength is confirmed (H7).**

> **PE coordination.** Per the isolation assumption, the **9.2 kN roof uplift is carried by the
> enclosure hold-downs (NW-RR-006, BP-04)**, not the pier; the pier anchors resist mount overturning +
> seismic. The proof-load target and the anchor split are **PE to confirm.**

---

## 5. Plumb / level & dimensional (NW-PF-001, NW-PF-002)

| Characteristic | Nominal | Accept limit | Method | Class |
|---|---|---|---|---|
| Pier plumb (verticality) | vertical | **≤ 1:200** (5 mm/m) | plumb bob / total station | Critical |
| Top-of-pier / plate level | level | **≤ 0.5°** | precision level / total station | Critical |
| Pier height above grade | 914.4 mm [36.000 in] | per ACI 117 *(PE tol)* | tape / survey | Major |
| Pier diameter | Ø304.8 mm [12.000 in] | per ACI 117 *(PE tol)* | tape | Minor |
| Top-plate flatness after grout | flat | plate bears fully on grout, no rock | feeler / straightedge | Major |

---

## 6. Fabricated-plate acceptance (NW-PF-002, NW-PF-003)

**Environment:** 20 °C per ISO 1 for the machined-plate checks. Datum/GD&T per ASME Y14.5-2018.

### 6.1 NW-PF-002 — top plate (A36, galvanized)

| Characteristic | Nominal (mm [in]) | Accept limit | Method | Class |
|---|---|---|---|---|
| Side (square) | 304.8 [12.000] | ISO 2768-mK | tape/CMM | Minor |
| Thickness | 9.5 [0.375] | ISO 2768-mK | caliper | Minor |
| Anchor holes | 4 × Ø20.6 [Ø0.81] | ± 0.25 mm pattern | CMM/gauge | Major |
| Adapter pattern | 4 × Ø11.2 [Ø0.44] | ± 0.25 mm pattern | CMM/gauge | Major |
| Galvanize coating | ASTM A123 | thickness per A123 table *(grade PE/spec)* | magnetic gauge | Major |
| Surface finish | Ra 3.2 µm [125 µin] | — | comparator | Minor |

### 6.2 NW-PF-003 — adapter plate (6061-T6, anodized)

| Characteristic | Nominal (mm [in]) | Accept limit | Method | Class |
|---|---|---|---|---|
| Side (square) | 254.0 [10.000] | ISO 2768-mK | caliper/CMM | Minor |
| Thickness | 19.1 [0.750] | ISO 2768-mK | caliper | Minor |
| RA-housing pattern | 4 × M6 | position *(ASSUMED — PE)* | CMM / thread gauge | Major |
| Pier-plate pattern | 4 × Ø11.2 [Ø0.44] | position *(ASSUMED)* | CMM/gauge | Major |
| Centre bore | Ø90.0 [3.543] | H8 pilot *(ASSUMED)* | CMM/plug | Major |
| Mounting-face flatness | ≤ 0.05 mm [0.0020 in] | CMM plane fit | CMM | Major |
| Latitude wedge angle | to 38.9° *(ASSUMED — bidder detail)* | angle gauge / CMM | Major |
| Anodize | MIL-A-8625F Type III, 0.002 in | thickness record | eddy-current gauge | Major |
| Surface finish | Ra 3.2 µm [125 µin] | — | profilometer | Minor |

> The adapter geometry (patterns, centre bore, wedge angle) is **ASSUMED design-intent** — accept
> limits above are provisional pending PE release.

---

## 7. Sampling & documentation

- **Critical characteristics** (concrete strength, anchor proof/pull, plumb/level, reinforcement,
  wedge/pattern): **100%** — the pier and each plate are qty 1, so first-article inspection = production
  acceptance.
- **Major / Minor:** verified on the acceptance record to ISO 2768-mK (plates) / ACI 117 (concrete).

The bidder shall deliver:

1. **Concrete test reports** — mix design (ACI 301), batch tickets, 7-/28-day cylinder breaks, slump/air.
2. **Reinforcement** — ASTM A615 Gr60 mill certs + rebar-placement/cover record (H2).
3. **Anchors** — ASTM F1554 Gr36 cert/CoC, ASTM A123 galvanize cert, **anchor proof/pull record**.
4. **Plates** — A36 cert + A123 coating record (NW-PF-002); 6061-T6 cert + MIL-A-8625F anodize record
   (NW-PF-003); dimensional/FAI.
5. **Plumb/level survey** (≤ 1:200; ≤ 0.5°).
6. **PE-stamped drawings + PE hold-point sign-offs** (H1–H7).
7. **NCR / RFI dispositions** for any ASSUMED value or out-of-tolerance condition.

| Role | Name | Signature | Date |
|---|---|---|---|
| Bidder QA | | | |
| Testing lab (concrete) | | | |
| **Owner / PE (stamp + hold points)** | | | |

---

## 8. ASSUMED-value register (do NOT treat as final)

| # | ASSUMED value | Part(s) |
|---|---|---|
| 1 | Rebar schedule, cover (~76 mm), tie spacing, seismic hoops, splices | NW-PF-001 |
| 2 | Single-pour cylinder sampling frequency & single-element f'c acceptance basis | NW-PF-001 |
| 3 | Slump/air targets (per approved mix) | NW-PF-001 |
| 4 | Anchor sizing + **field proof/pull load** (tied to ~9.2 kN uplift bounding case) | NW-PF-004 |
| 5 | Pier-vs-enclosure anchor split (9.2 kN roof uplift → BP-04 hold-downs) | NW-PF-004 / NW-RR-006 |
| 6 | Site frost depth vs 914.4 mm embedment | NW-PF-001 |
| 7 | Wind 105 mph / seismic S_DS 0.5 g | all |
| 8 | Latitude wedge angle (38.9°) + adapter patterns/centre bore | NW-PF-003 |
| 9 | Grout/leveling-nut method + pier-slab isolation gap detail | NW-PF-001/002 |
| 10 | Concrete workmanship tolerance class (ACI 117) | NW-PF-001 |
