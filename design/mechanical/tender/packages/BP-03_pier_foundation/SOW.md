# BP-03 — Statement of Work: Pier & Foundation (Reinforced Concrete + Structural Steel)

> **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**

| Field | Value |
|---|---|
| Package | BP-03 — Pier & foundation |
| Parts | NW-PF-001 (RC pier), NW-PF-002 (top plate), NW-PF-003 (adapter plate), NW-PF-004 (anchor set + template) |
| Process | Cast-in-place reinforced concrete; laser/waterjet + drill (steel plate); CNC mill (aluminium plate); buy + template (anchors) |
| Site datum | 38.9 °N / −117.4 °W, elevation ~1800 m [~5900 ft], remote high-desert Nevada, seismically active |
| Issue date / rev | 2026-08-06 / A |

> ## PE-STAMP GATE
> **The reinforced-concrete pier (NW-PF-001), its reinforcement, its embedment, and the anchor-bolt set
> (NW-PF-004) are ISSUED FOR PE REVIEW.** A **licensed Professional Engineer**, registered in the
> build-site jurisdiction, **must review, size, complete, and STAMP** these items under the governing
> building code and **ASCE 7** (wind/snow/seismic) **before any permit is issued or any concrete is
> placed.** All structural quantities below are **SOURCED envelope/material values** or **ASSUMED
> design-intent** presented for the PE — none is a released structural design.

**Purpose.** This SOW specifies the concrete, reinforcement, anchorage, isolation, embedment,
finishing, and certification requirements for the four BP-03 parts. It is read with the PE-stamped
structural drawings (which **govern for construction**), the STEP ISO 10303 AP242 solids (plate
geometry), the NW-PF control drawings (PDF), and `acceptance.md`. All dimensions are dual-unit,
**mm primary, inch in brackets**, drawn from the parts registry (`partspec.parts_for('BP-03')`) and
the BOM/cut list — **no dimension herein is invented.**

**Standards applied.** MIL-STD-31000A (TDP); **ACI 318** (structural concrete, incl. **Ch.17**
anchoring-to-concrete); **ACI 301** (specifications for structural concrete); **ASCE 7**
(wind/snow/seismic loads); **ASTM A615 Gr60** (deformed reinforcing bar); **ASTM F1554 Gr36** (anchor
bolts); **ASTM A36** (structural steel); **ASTM A123** (hot-dip galvanize); **ASTM B209** (6061-T6
plate); **MIL-A-8625F** (Type III hardcoat anodize); **ASME Y14.5-2018 / Y14.100 / Y14.24 / Y14.1**
(plate drawings); **ISO 286** (fits); **ISO 2768** (general tolerances). Concrete field/lab test
methods are those **invoked by ACI 301** — see `acceptance.md`.

---

## 1. General requirements (all parts)

1. **PE authority.** The PE-stamped structural drawings supersede every rebar, anchor, embedment, and
   reinforcement value in this SOW. Where this SOW and the stamped set disagree, **the stamped set
   controls**; the bidder shall RFI before placing concrete.
2. **Materials & certification.** Furnish mill certs / CoC with heat/lot traceability for: the concrete
   mix (ACI 301 approved mix design, f'c = 4000 psi), the reinforcing bar (ASTM A615 Gr60), the anchor
   bolts (ASTM F1554 Gr36), the A36 plate, and the 6061-T6 plate (ASTM B209). Mark fabricated plates
   with part number and revision per ASME Y14.100.
3. **General tolerance.** Plate dimensions to **ISO 2768-mK**; concrete workmanship tolerances per
   **ACI 117** as invoked by ACI 301 (**ASSUMED — PE/bidder to confirm the tolerance class**).
4. **Isolation (MANDATORY).** The pier is **structurally isolated** from any building slab, footing, or
   floor — no bearing, no bond, no shared reinforcement. Maintain an isolation gap/joint (compressible
   filler) around the pier where it passes any slab (detail bidder/PE to confirm). This keeps floor
   footfall and enclosure vibration off the optical train.
5. **Embedment vs frost.** Pier embedment 914.4 mm [36.000 in] (SOURCED) shall be verified by the PE
   to exceed the **site frost depth** (ASSUMED 0.3–0.6 m [12–24 in] for central-NV high desert;
   SF ≈ 1.52) and to satisfy seismic/overturning fixity.
6. **Cold-joint / lift control, curing, and hot/cold-weather placement** per ACI 301.

---

## 2. NW-PF-001 — Reinforced-concrete telescope pier

**Drawing:** NW-PF-001 (rev A). **Envelope:** round pier **Ø304.8 mm [12.000 in] × 1828.8 mm
[72.000 in]** overall (height above grade 914.4 mm [36.000 in] + embedment 914.4 mm [36.000 in]).
**Stock/pour mass:** 320.26 kg (≈0.13 m³ [≈4.7 ft³ / ≈0.18 yd³] concrete — pour-planning estimate
from the envelope; `cut_list.csv` row NW-PF-001). **Material:** cast-in-place concrete **f'c = 4000 psi
(27.6 MPa)** per **ACI 318 / ACI 301**.

**Controlling dimensions (SOURCED = P.PIER):**

| Feature | Nominal (mm [in]) | Source |
|---|---|---|
| Diameter | Ø **304.8** [12.000] | SOURCED |
| Height above grade | **914.4** [36.000] | SOURCED |
| Embedment | **914.4** [36.000] | SOURCED |
| Overall length | **1828.8** [72.000] | SOURCED |
| f'c | **4000 psi (27.6 MPa)** | SOURCED |

**Reinforcement schedule (ASSUMED design-intent — PE to confirm/complete/stamp):**

| Item | Baseline callout | Bar dia (mm [in]) | Standard | Status |
|---|---|---|---|---|
| Vertical bars | **6 × #4** | Ø12.7 [0.500] | ASTM A615 Gr60 | ASSUMED — PE to set count/size |
| Ties / hoops | **#3 @ 12 in [304.8 mm] oc** | Ø9.5 [0.375] | ASTM A615 Gr60 | ASSUMED — PE to set spacing + seismic hoop detail |
| Clear cover | **~76 mm [3.00 in]** cast against earth | — | ACI 318 §20.5 | ASSUMED — PE to confirm |
| Splices / development / hooks | per ACI 318 Ch.25 | — | ACI 318 | PE to detail |

> **ASSUMED design-intent — bidder/PE to confirm.** The rebar cage (6 × #4 vertical, #3 ties), cover,
> tie spacing, seismic hoop confinement, and lap splices are **ASSUMED**. In a Walker-Lane-vicinity
> seismic zone (S_DS ≈ 0.5 g, ASSUMED) the transverse reinforcement/confinement detailing is a
> **PE-stamped** decision. The design study models the pier as an unreinforced circular cantilever for
> tilt/frequency (concrete SF 111 compression / 13.8 tension) — reinforcement is required by code for
> ductility/anchorage regardless of the low computed stress.

**Structural basis (from `MECHANICAL_DESIGN.md` §8 — pier PASS, governing SF 6.8):**

| Quantity | Value | Note |
|---|---|---|
| Pier pointing tilt @ 35 mph gust | 0.70″ | vs 5″ budget → SF 7.2 |
| Pier first mode | 151.9 Hz | vs 10 Hz target → SF 15.2 |
| Seismic overturning SF (embed + weight) | 7.0 | dead-weight-only 0.81 → **embedment governs** |
| Sliding SF (passive / base shear) | 6.8 | governing SF |
| Concrete net compression / f'c | SF 111 | — |
| Concrete net tension / modulus of rupture | SF 13.8 | f_r = 0.62√f'c = 3.26 MPa (ASSUMED code value) |
| Embedment / frost depth | SF 1.52 | 0.914 m vs ASSUMED 0.6 m frost |

**Workmanship tolerances (drawing):** **plumb ≤ 1:200**; **top-of-pier level ≤ 0.5°**. Anchor cage +
setting template (NW-PF-004) cast integrally — see §5.

**Provenance / flags.** Ø/height/embed/f'c = P.PIER (**SOURCED**); rebar schedule **ASSUMED
design-intent (PE to confirm)**. **REQUIRES PE STAMP.**

---

## 3. NW-PF-002 — Pier top plate

**Drawing:** NW-PF-002 (rev A). **Stock:** A36 plate **304.8 mm [12.000 in] × 304.8 mm [12.000 in] ×
9.5 mm [0.375 in]**, cut allowance 3.0 mm, stock mass 6.94 kg (`cut_list.csv` row NW-PF-002).
**Process:** laser/waterjet cut + drill. **Finish:** **hot-dip galvanize per ASTM A123** (after all
cutting/drilling).

| Feature | Nominal (mm [in]) | Tolerance | Note |
|---|---|---|---|
| Side (square) | **304.8** [12.000] | ISO 2768-mK | matches pier diameter |
| Thickness | **9.5** [0.375] | ISO 2768-mK | A36 plate |
| Anchor holes | **4 × Ø20.6 [Ø0.81]** | ± 0.25 mm pattern | clearance for Ø0.75 F1554 (NW-PF-004) |
| Centre pattern | **4 × Ø11.2 [Ø0.44]** | ± 0.25 mm pattern | matches NW-PF-003 adapter |
| Surface finish | Ra 3.2 µm [125 µin] | — | cut faces |

**Notes.** Grouted onto the pier over the cast-in anchor bolts, then leveled and torqued with
leveling/plate nuts (bidder to detail; leveling-nut vs full-grout method **ASSUMED — PE to confirm**).
Galvanize per ASTM A123 with coating-thickness record; ream/retap holes after galvanize as needed to
clear the anchors and the Ø0.44 pattern.

**Provenance / flags.** Side/thickness = P.PIER (**SOURCED**); hole patterns **DERIVED** to match
NW-PF-004 (Ø0.81) and NW-PF-003 (Ø0.44) → hole positions **ASSUMED design-intent, bidder/PE to
confirm** against the stamped anchor layout.

---

## 4. NW-PF-003 — Pier-to-mount adapter plate

**Drawing:** NW-PF-003 (rev A). **Stock:** 6061-T6 plate **254.0 mm [10.000 in] × 254.0 mm [10.000 in]
× 19.1 mm [0.750 in]**, cut allowance 3.0 mm, stock mass 3.32 kg (`cut_list.csv` row NW-PF-003).
**Process:** CNC mill. **Finish:** **Type III hardcoat anodize, 0.002 in, Class 1 (clear) per
MIL-A-8625F** (after machining; mask bores/threads).

| Feature | Nominal (mm [in]) | Tolerance | Note |
|---|---|---|---|
| Side (square) | **254.0** [10.000] | ISO 2768-mK | — |
| Thickness | **19.1** [0.750] | ISO 2768-mK | — |
| RA-housing pattern | **4 × M6** | position *(ASSUMED)* | matches **NW-MH-001 (BP-01)** |
| Pier-plate pattern | **4 × Ø11.2 [Ø0.44]** | position *(ASSUMED)* | matches **NW-PF-002** |
| Centre bore | Ø **90.0** [3.543] | H8 pilot *(ASSUMED)* | cable/drawbar clearance |
| Face flatness | ▱ 0.05 mm to mounting face | per Y14.5 | mount seating |
| Surface finish | Ra 3.2 µm [125 µin] | — | — |

> **ASSUMED design-intent — bidder/PE to confirm.** The adapter **bridges the 12×12 in pier plate to
> the 8×8 in RA housing and provides the latitude wedge to orient the polar (RA) axis to the site
> latitude 38.9°** (wedge plate or shim set). **Adapter geometry (patterns, centre bore, wedge angle)
> is not fixed in the repository** — it is ASSUMED design-intent; the bidder details the wedge/shim and
> the PE confirms. Preserve the 4 × M6 RA-housing pattern and the 4 × Ø0.44 pier-plate pattern so the
> stack assembles.

**Provenance / flags.** ASSUMED design-intent — adapter geometry not in repo (bridges 12×12 plate to
8×8 housing). Levels/orients the RA axis to site latitude 38.9° (wedge or shim set, bidder to detail).

---

## 5. NW-PF-004 — Anchor-bolt set + setting template

**Buy + fabricate** (no fabrication control drawing SVG). **Anchors:** **4 × Ø19.05 mm [0.750 in] ×
304.8 mm [12.000 in]**, **ASTM F1554 Gr36**, **hot-dip galvanized per ASTM A123**, cast into the wet
pier per **ACI 318 Ch.17** (anchoring to concrete). **Projection** 50.0 mm [1.969 in] above the pier
top. **Template:** rigid setting template (ASSUMED 0.25 in [6.35 mm] plywood/ply-steel), hole position
tolerance **0.02** (drawing callout), matching the NW-PF-002 anchor pattern.

| Feature | Nominal (mm [in]) | Standard | Status |
|---|---|---|---|
| Bolt diameter | Ø **19.05** [0.750] | ASTM F1554 Gr36 | ASSUMED — PE to size |
| Embedment (into pier) | **304.8** [12.000] | ACI 318 Ch.17 | ASSUMED — PE to size |
| Projection | **50.0** [1.969] | — | for plate + nut stack |
| Count | **4** | — | ASSUMED — PE to set |
| Template hole tolerance | **± 0.02 mm** pattern | — | so bolts drop through NW-PF-002 |

> **Anchor sizing tied to the wind-uplift number — PE to confirm (per task + registry provenance).**
> The registry sizes NW-PF-004 against the governing **survival-wind roof-uplift** case from
> `MECHANICAL_DESIGN.md` §7: **roof gross uplift 9.2 kN (9163 N)** minus roof self-weight 1765 N →
> **net anchor demand 7.4 kN (7398 N)**; **4× 2 klbf [≈8.9 kN] anchors → capacity 35.6 kN → SF 3.9**
> (the wind remediation). **However:** the design study assumes the **telescope pier is isolated from
> the enclosure**, so the **9.2 kN roof uplift is actually carried by the enclosure/building hold-downs
> (NW-RR-006, BP-04), not the pier.** The pier anchors NW-PF-004 resist the **mount overturning +
> seismic** demand (base shear 1008 N, overturning 673.8 Nm; embedment governs). The 9.2 kN figure is
> retained as the **bounding tension case** for anchor selection. **Final anchor diameter, grade,
> embedment, edge distance, count, and the pier-vs-enclosure anchor split are ASSUMED design-intent —
> the PE shall size and stamp them per ACI 318 Ch.17 and ASCE 7.**

**Setting procedure.** Position the template on the form; hang the 4 anchors plumb at the specified
projection; verify pattern against NW-PF-002 before the pour; place concrete; do not disturb until
initial set; strip template after cure. Cast integrally with the pier — **no post-installed anchors**
unless the PE approves and re-specifies to ACI 318 Ch.17 post-installed provisions.

**Provenance / flags.** ASSUMED design-intent per ACI 318 Ch.17 (PE to size for wind/seismic uplift
~9.2 kN). Cast into pier via template; sizing tied to the wind proof roof/pier uplift — **PE to
confirm.**

---

## 6. Finishing

| Part | Finish | Standard | Notes |
|---|---|---|---|
| NW-PF-001 pier | formed concrete, cured | ACI 301 | rub/patch form-tie holes; no coating unless PE specifies |
| NW-PF-002 top plate | **hot-dip galvanize** | **ASTM A123** | after cut/drill; coating-thickness record; clear holes post-dip |
| NW-PF-003 adapter | **Type III hardcoat anodize 0.002 in, Class 1 (clear)** | **MIL-A-8625F** | after machining; mask centre bore + threads |
| NW-PF-004 anchors | **hot-dip galvanize** | **ASTM A123** | full-length; protect threads/projection during pour |

---

## 7. Submittals & deliverables

1. Installed pier + plate stack + cast anchor set (NW-PF-001..004), leveled and plumbed.
2. **Concrete:** ACI 301 approved mix design, batch tickets, **7-day + 28-day cylinder break reports**
   (`acceptance.md`), slump/air records.
3. **Reinforcement:** ASTM A615 Gr60 mill certs + rebar-placement/cover inspection record vs the
   stamped cage.
4. **Anchors:** ASTM F1554 Gr36 mill cert/CoC, ASTM A123 galvanize cert, **anchor proof/pull test
   record**.
5. **Plates:** A36 cert + ASTM A123 coating-thickness (NW-PF-002); 6061-T6 cert (ASTM B209) + Type III
   anodize cert (NW-PF-003).
6. **Plumb/level survey** (≤ 1:200 plumb; ≤ 0.5° top level).
7. **PE-stamped structural drawings + PE field hold-point sign-offs** (rebar, embedment, anchor set,
   pour).
8. RFI/NCR log resolving every ASSUMED value before construction.

---

## 8. ASSUMED design-intent register (this SOW)

| # | Item | Part(s) | Status |
|---|---|---|---|
| 1 | Rebar schedule (6 × #4 vert + #3 ties), cover, seismic hoop detailing, splices | NW-PF-001 | ASSUMED — PE to set & stamp |
| 2 | Anchor sizing (Ø0.75 F1554 Gr36, embed, projection, count) vs ~9.2 kN uplift | NW-PF-004 | ASSUMED — PE to size (ACI 318 Ch.17) |
| 3 | Pier-vs-enclosure anchor split (9.2 kN roof uplift lands on BP-04 hold-downs) | NW-PF-004 / NW-RR-006 | ASSUMED — PE coordination |
| 4 | Site frost depth vs embedment; bearing/bell detail | NW-PF-001 | ASSUMED — PE to confirm |
| 5 | Wind speed (105 mph) / seismic S_DS (0.5 g) | all | ASSUMED (ASCE 7) — PE to set |
| 6 | Latitude wedge angle + adapter geometry (patterns, centre bore) | NW-PF-003 | ASSUMED — bidder to detail, PE to confirm |
| 7 | Grout/leveling-nut method + pier-slab isolation gap detail | NW-PF-001/002 | ASSUMED — bidder/PE to detail |
| 8 | Top-plate hole positions (Ø0.81 anchor, Ø0.44 adapter) | NW-PF-002 | ASSUMED — confirm vs stamped anchor layout |
| 9 | Concrete workmanship tolerance class (ACI 117) | NW-PF-001 | ASSUMED — PE/bidder to confirm |
