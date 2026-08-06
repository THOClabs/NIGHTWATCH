# BP-04 — Roll-off Roof "Disappearing Turret" (Structural Steel + Rail/Drive) — Bidder README

> **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**

| Field | Value |
|---|---|
| Package | **BP-04 — Roll-off roof ("disappearing turret")** |
| Trade | Structural steel fabrication (welded, AWS D1.1) + rail/drive install |
| Parts | NW-RR-001, -002, -003, -004, -005, -006 (6 fabricated line items; 6 control drawings) |
| Branch / project | `design/mechanical-tender` — NIGHTWATCH Observatory Mount & Roll-off Tender |
| Issue date | 2026-08-06 |
| Revision | A |
| Governing TDP standard | MIL-STD-31000A (Technical Data Package) |

This README is the entry point for the steel fabricator / gate-and-rail installer bidding BP-04. It
defines the **scope**, the **data package the shop receives**, the **bidder deliverables**, the
**PE-STAMP GATE**, and the items carried as **ASSUMED design-intent**. Read it with `SOW.md` (per-part
specification), `weld_map.md` (the joint schedule with AWS symbols), and `acceptance.md` (weld
visual/NDE, rail alignment, drive-cycle test, hold-down pull) in this same folder.

---

## 0. PE-STAMP GATE — READ FIRST (this package is NOT releasable for construction)

> **⚠ THE ROLL-OFF ROOF AND ITS SUPPORTING STEEL ARE A STRUCTURE. THEY ARE ISSUED FOR PE REVIEW ONLY.**
> **A licensed Professional Engineer, registered in the jurisdiction of the build site, MUST review,
> size, and STAMP every structural member (frame, purlins, rail beams, brackets), every weld size, and
> every hold-down/rail anchor BEFORE any steel is cut or any anchor is set.** Nothing in this package —
> member sizes, weld sizes, anchor sizing — is a released structural design. The controlling **section
> sizes are ASSUMED design-intent**; they are presented **for the PE to confirm, complete, and stamp**
> against the governing building code and ASCE 7 load cases.

**Why a stamp is mandatory.** The building shell and its moving roof carry code-level loads. Two load
cases govern this package and are **owner/PE responsibilities under ASCE 7**:

| Load case | Basis (design proof) | What it drives | Proof status |
|---|---|---|---|
| **Snow (structural)** | ~25 psf [1197 Pa] ground snow, high-desert @ ~1800 m; **closed flat roof carries 10.8 kN [2.42 klbf]** (≈6.1× the roof's own 1.8 kN [397 lbf] dead weight; ≈1.1 t of snow) | roof frame + purlin sizing, panel; **snow interlock** | §10 PASS + FINDING — **snow is the roof's design driver** |
| **Survival wind (105 mph [46.9 m/s])** | q = 1131 Pa; gross roof uplift **9.2 kN [2.06 klbf]** vs 1.8 kN self-weight → **SF 0.19 FAIL**; net anchor demand 7.4 kN [1.66 klbf] | **4× wind hold-down anchors** (NW-RR-006) | §7 FAIL → remediated: **4× ≥2 klbf → SF 3.9** |

The wind basic speed (105 mph) and ground snow load (25 psf) are **ASSUMED** in the design study
because the repository was silent on roof structure — they are **exactly the values the PE must set
from the site's ASCE 7 hazard data and stamp.** See `MECHANICAL_DESIGN.md` §7 (wind — FAIL/remediated)
and §10 (roll-off drive + snow — PASS + finding).

**No steel is cut, and no anchor is set, until the stamped structural drawings, the PE-approved
weld/NDE plan, and the PE-approved Inspection & Test Plan (`acceptance.md`) are in hand.**

---

## 1. Scope

BP-04 covers the **roll-off "disappearing turret" roof and its track/drive** — a rectangular welded
steel roof frame that rolls its **own full length clear of the aperture** on a **box-track rail run
twice the roof length**, driven by a COTS gate operator, held closed against survival wind by
**mandatory hold-down anchors**, and interlocked against wind and snow. The shop:

1. Fabricates the **welded steel roof frame + purlins** (NW-RR-001, -002) per **AWS D1.1** (weld
   symbols per **AWS A2.4**), sized to carry the closed-roof snow case.
2. Fabricates/installs the **box-track rail beams** (NW-RR-003), each **2× the roof length** so the
   roof fully clears the aperture, with **end stops**.
3. Fabricates the **wheel axle brackets** (NW-RR-004) that carry the COTS V-groove wheels, the
   **drive bracket + end stops** (NW-RR-005) that mount the COTS gate operator, and the **MANDATORY
   4× wind hold-down anchor brackets** (NW-RR-006).
4. **Hot-dip galvanizes** all steel per **ASTM A123** (after welding), weatherproofs the closed roof,
   and commissions the drive with its **wind + snow interlocks**.
5. Inspects per `acceptance.md` (weld VT/NDE, rail alignment, drive-cycle test, hold-down pull) and
   delivers a certified, PE-signed assembly.

**Out of scope for BP-04** (separate packages — the roof *interfaces* to these but the shop does not
supply them, except where noted "install"):

| Interface | Supplied under | Notes |
|---|---|---|
| **V-groove track wheels** (NW-CO-010, ×8) | BP-05 (COTS) | Shop **installs** them on the NW-RR-004 brackets. |
| **Roof drive — gate operator / rack** (NW-CO-011) | BP-05 (COTS) | Shop **installs + commissions** it on NW-RR-005; see §6 for the suggested product category. |
| **Metal roofing panel + flashing** (NW-CO-012) | BP-05 (COTS) | Weatherproof skin; shop installs + seals over the purlins. |
| Telescope pier NW-PF-001, anchor set NW-PF-004 | BP-03 | The pier is **structurally isolated** from the enclosure; roof uplift lands on the **building/enclosure foundation**, not the pier. See §4. |
| Mount head, optics, electronics | BP-01 / BP-02 / BP-05 | Not a roof interface. |
| Enclosure walls / building shell / enclosure foundation | Owner / site civil (coordinated, PE-stamped) | The roof rides on this shell; the hold-down anchors land in it. |

---

## 2. Data package the shop receives (per MIL-STD-31000A)

| Item | Format / standard | Role |
|---|---|---|
| 3-D solid master (frame + brackets) | **STEP ISO 10303 AP242** | As-modelled geometry master (weldment + brackets). |
| Flat-pattern cut files (plate brackets NW-RR-004/-005/-006) | **DXF / DWG** | Laser/waterjet flat patterns. |
| Control drawings NW-RR-001…-006 | **PDF** (drawing practices ASME Y14.100; drawing types Y14.24; sheet & title block Y14.1) | Envelope + title block + key dims; bid control drawing. |
| **PE-stamped structural drawings** | PDF (issued by owner's PE) | **Governs for construction** — supersedes the ASSUMED member/weld/anchor values herein. |
| `SOW.md` | Markdown | Per-part spec: members, welds (AWS D1.1/A2.4), rail run, drive, hold-downs, galvanize, weatherproofing. |
| `weld_map.md` | Markdown | Joint schedule: joint type, AWS A2.4 weld symbol, ASSUMED size, process, NDE. |
| `acceptance.md` | Markdown | Weld VT/NDE, rail alignment, drive-cycle test, hold-down pull, weatherproofing. |
| `cut_list.csv` (rows NW-RR-001…-006) | CSV/XLSX | Stock size, cut allowance, stock mass. |

**Order of precedence.** For the **fabricated brackets** (NW-RR-004/-005/-006) the **STEP AP242 solid
governs geometry**; the DXF/DWG governs flat patterns; the drawing + SOW govern tolerances, finish, and
material. **For the structural steel (frame, purlins, rail beams), the member sizing, the weld sizing,
and the anchorage, the PE-STAMPED STRUCTURAL DRAWINGS GOVERN and supersede every number in this
package.** Where any document disagrees, the **PE-stamped set controls** and the bidder shall raise an
RFI before cutting steel. Welding, weld procedures (WPS/PQR) and welder qualification (WPQ) per
**AWS D1.1**; weld & NDE symbols per **AWS A2.4**; general tolerances per **ISO 2768**; bracket GD&T per
**ASME Y14.5-2018**; fits per **ISO 286**.

---

## 3. Line-item summary (source: `partspec.parts_for('BP-04')` + `cut_list.csv`)

| Part no. | Name | Material | Stock / size | Qty | Stock mass | Finish | Drawing |
|---|---|---|---|---:|---:|---|---|
| **NW-RR-001** | Roof frame perimeter (HSS) | ASTM A500 Gr B HSS | HSS **50.8 mm [2.000 in] sq × 3.2 mm [0.125 in] wall × 12000.0 mm [472.441 in]** total (4 sides of the 3.0 m [9.843 ft] square perimeter) | 1 | 56.98 kg | Galvanize ASTM A123 | NW-RR-001 |
| **NW-RR-002** | Roof rafters / purlins | ASTM A500 Gr B HSS | HSS **38.1 mm [1.500 in] sq × 3.2 mm [0.125 in] wall × 15000.0 mm [590.551 in]** total (5 purlins × 3000 mm [118.110 in] span @ 600 mm [23.622 in] o.c.) | 5 | 261.14 kg | Galvanize ASTM A123 | NW-RR-002 |
| **NW-RR-003** | Track rail beams (box track) | ASTM A36 structural steel | Box track **63.5 mm [2.500 in] sq × 4.0 mm [0.157 in] wall × 6000.0 mm [236.220 in] each** (2 rails; run = **2× roof length**) | 2 | 179.36 kg | Galvanize ASTM A123 | NW-RR-003 |
| **NW-RR-004** | Wheel axle brackets | ASTM A36 structural steel | Plate **101.6 mm [4.000 in] × 76.2 mm [3.000 in] × 9.5 mm [0.375 in]** | 8 | 4.63 kg | Galvanize ASTM A123 | NW-RR-004 |
| **NW-RR-005** | Drive bracket + end stops | ASTM A36 structural steel | Plate/angle assembly **150.0 mm [5.906 in] × 100.0 mm [3.937 in] × 9.5 mm [0.375 in]** | 4 | 4.49 kg | Galvanize ASTM A123 | NW-RR-005 |
| **NW-RR-006** | **Wind hold-down anchor brackets (REMEDIATION — MANDATORY)** | ASTM A36 structural steel | Plate **127.0 mm [5.000 in] × 101.6 mm [4.000 in] × 12.7 mm [0.500 in]** | 4 | 5.15 kg | Galvanize ASTM A123 | NW-RR-006 |

Stock mass is the **quantity ordered** (stock envelope volume × steel density), not finished net mass;
cut allowance is 3.0 mm on stock. Rail run per rail is **6000.0 mm [236.220 in] = 2 × the 3000.0 mm
[118.110 in] roof length**, so the roof travels its full length off the aperture. Total roof assembly
mass basis for the drive/wheel sizing is **180 kg [397 lb]** (`P.ENCLOSURE.roof_mass_kg`, ASSUMED).

> **Member-callout reconciliation (ASSUMED).** On NW-RR-002 the nominal member designation in the
> registry key-dims (**"HSS 2×1×1/8"**, a rectangular section) differs from the modelled/ordered stock
> envelope (**38.1 mm [1.500 in] square × 3.2 mm wall**). Both are **ASSUMED design-intent**; the PE
> shall reconcile the purlin section against the ASCE 7 snow demand and issue the released size.

---

## 4. Cross-package interfaces the shop must preserve

| Interface | Feature | Mates to | Part |
|---|---|---|---|
| Roof → rail | 8 × V-groove wheels on NW-RR-004 brackets | Box-track rail running surface | NW-CO-010 (BP-05) → NW-RR-003 |
| Roof → drive | Drive bracket + rack/pinion pickup | Gate operator + gear rack | NW-CO-011 (BP-05) → NW-RR-005 |
| Roof → weather | Purlin top flanges | Metal roofing panel + flashing | NW-CO-012 (BP-05) → NW-RR-002 |
| Rail → structure | Rail-beam anchorage | Enclosure/building foundation (PE-designed) | NW-RR-003 → owner civil |
| Roof/rail → structure | **4× hold-down anchor brackets** | Ø0.75 in [19.05 mm] F1554 anchors into the enclosure foundation | NW-RR-006 → owner civil |
| End of travel | 4× end stops + rubber bump pads | Rail ends + drive limit | NW-RR-005 / NW-RR-003 |

> **Wind hold-down clarification (important).** The **9.2 kN [2.06 klbf] survival-wind roof uplift** is
> resisted by the **4× wind hold-down anchor brackets NW-RR-006 (this package)**, which anchor the
> **enclosure/building foundation** — because the telescope pier (BP-03) is **structurally isolated**
> from the enclosure (standard observatory practice, to keep vibration off the optics). The BP-03
> anchor set NW-PF-004 casts into the **pier** and resists the mount overturning + seismic demand, a
> **separate** load path. **Where each hold-down lands, the anchor edge distance/embedment into the
> building foundation, and the final anchor capacity are PE coordination items — anchorage into
> concrete per ACI 318 Ch.17; PE to confirm.**

---

## 5. Bidder deliverables

1. Finished, galvanized, weatherproofed assembly: frame (NW-RR-001), purlins (NW-RR-002 ×5), rail
   beams (NW-RR-003 ×2), wheel brackets (NW-RR-004 ×8), drive bracket + stops (NW-RR-005 ×4), and the
   **4× wind hold-down brackets (NW-RR-006)** — installed, aligned, and commissioned.
2. **Material / mill certs** — ASTM A500 Gr B (HSS) and ASTM A36 (plate/rail), heat/lot traceable.
3. **Welding submittals** — WPS + supporting PQR and welder qualification records (WPQ) per **AWS D1.1**;
   weld map (`weld_map.md`) marked up with as-built weld sizes; **CWI** weld inspection report.
4. **NDE reports** — visual (VT) 100% + magnetic-particle (MT)/dye-penetrant (PT) on the critical
   hold-down, wheel-bracket, and rail-splice welds per `acceptance.md` (extent **ASSUMED — PE/CWI to set**).
5. **Galvanize cert** — ASTM A123 coating mass/thickness record; vent/drain-hole detail for the HSS;
   field-repair procedure for damaged galvanize (bidder-proposed; the recognized repair standard is
   **ASTM A780**, supplementary to the register).
6. **Rail-alignment survey** — gauge, straightness, level/co-planarity, splice flushness (`acceptance.md`).
7. **Drive-cycle + interlock commissioning report** — full open/close travel within timeout, tractive
   load/current, soft-start/stop, end-stop engagement, manual release, and the **wind + snow interlocks**.
8. **Hold-down pull-test record** — each anchor proofed to the PE-set load (≥2 klbf [8.9 kN] baseline).
9. **Weatherproofing test** — roof-closed water/rain test, flashing/gasket, drainage.
10. **PE sign-off** — stamped structural drawings + field hold-point sign-offs (fit-up, weld, anchor set).
11. RFI / nonconformance log resolving every ASSUMED value before it is built.

---

## 6. Suggested COTS product categories (procured under BP-05 — named, not specified)

The task's two long-lead COTS items map to well-established commercial product categories. These are
**suggested categories to guide the BP-05 buy**, not a released product spec — final selection and
sizing are the bidder's/PE's, confirmed against the loads below.

- **Track rail + wheels → sliding-gate "V-groove box track" hardware (steel).** The **box-track rail
  NW-RR-003** (2.5 in [63.5 mm] class) and the **8× V-groove wheels NW-CO-010** correspond to the
  **steel V-groove gate-track + V-groove wheel-with-preattached-steel-box** category used on slide
  gates and DIY roll-off observatories. Steel 4 in [101.6 mm] V-groove wheels are commonly rated to
  ~3,000 lb [~13 kN] each; with **8 wheels for the 180 kg [397 lb] roof + snow**, capacity is not the
  constraint — **alignment and straightness are** (see `acceptance.md`). Size wheels for **≥4×** the
  wheel share of roof + snow (per NW-RR-004 note).
- **Roof drive → rack-and-pinion "slide-gate operator" (light-commercial class).** The **roof drive
  NW-CO-011** corresponds to a **rack-and-pinion sliding-gate operator**. The proof requires only
  **235 N [52.8 lbf]** tractive force (rolling 88 N [19.8 lbf] + 35 mph [15.6 m/s] wind 147 N
  [33.1 lbf]) → **SF 2.1 vs a ~500 N [112 lbf] garage-door-class drive**; light-commercial slide-gate
  operators rated for gate weights of ~270–500 kg [~600–1,100 lb] give ample margin **and** provide the
  needed **soft-start/soft-stop, manual release, and photo-beam/limit interlocks**. Because **wind is
  62% of the tractive load, the drive is WIND-sized** — spec a **positive, fail-safe close against the
  35 mph gust**.

> **Sizing anchors (from the proofs, for the BP-05 buyer).** Move force 235 N [52.8 lbf]; drive torque
> 11.77 Nm [8.68 lbf·ft] @ 50 mm [1.969 in] wheel; roof speed 0.067 m/s (3 m in 45 s) < 0.30 m/s
> ceiling; open time 45 s < 60 s motor timeout. **Snow interlock is MANDATORY:** a fully snow-laden
> roof needs **627 N [141 lbf]** to roll — it **exceeds** the ~500 N drive, so the roof must **never**
> be commanded open under snow load (`MECHANICAL_DESIGN.md` §10).

Sources for the named categories (BP-05 to confirm): [Steel Supply LP — V-groove track & wheels](https://www.steelsupplylp.com/ornamental-iron/store/gate-door-hardware/v-groove-tracks-wheels-boxes),
[Hoover Fence — V-groove wheel w/ preattached steel box](https://www.hooverfence.com/v-groove-wheel-with-preattached-steel-box),
[Cloudy Nights — roll-off roof roller/rail systems](https://www.cloudynights.com/topic/812178-recommend-a-low-friction-rollerrail-system-for-8x10/),
[FAAC 844 ER rack-and-pinion slide-gate operator](https://www.affordableopeners.com/faac-usa-844-er-rack-and-pinion-slide-gate-operator.html),
[LiftMaster rack-and-pinion slide-gate operator](https://www.asapgaragedoorandgaterepair.com/portfolio/liftmaster-residential-rack-pinion-drive-slide-gate-operator/).

---

## 7. ASSUMED design-intent — bidder / PE to confirm (NOT final)

Carried as **ASSUMED design-intent** in the parts registry; **not** released dimensions. The PE shall
confirm/complete and stamp before construction:

- **All structural member sizes** — frame HSS 2×2×1/8 (NW-RR-001), purlin HSS (NW-RR-002, incl. the
  2×1 vs 1.5-sq reconciliation of §3), box-track section 2.5 in class (NW-RR-003), and bracket
  thicknesses — are **ASSUMED design-intent; PE to confirm vs the ASCE 7 snow (10.8 kN [2.42 klbf]
  closed-roof) + survival-wind cases.**
- **All weld sizes and joint types** — every weld leg/throat and CJP/PJP call in `weld_map.md` is
  **ASSUMED; PE/CWI to size per AWS D1.1 minimum-fillet tables and the computed demand.**
- **Hold-down anchor sizing** — 4× Ø0.75 in [19.05 mm] F1554, capacity ≥2 klbf [8.9 kN] each, is the
  **REMEDIATION** basis (survival uplift 9.2 kN → SF 3.9). Final diameter, grade, embedment, and edge
  distance into the enclosure foundation are **PE to set per ACI 318 Ch.17.**
- **Rail support / anchorage spacing** and the rail-to-foundation connection (weld vs bolt) — ASSUMED;
  PE to detail for the roof + snow + wind reactions.
- **Roof geometry (3.0 × 3.0 m [9.843 × 9.843 ft], 180 kg [397 lb])** — ASSUMED footprint/mass
  (`P.ENCLOSURE`, flagged); confirm against the released enclosure.
- **Snow interlock and wind interlock logic** — MANDATORY per §10/§7; interlock thresholds
  (25 mph [11.2 m/s] park, 35 mph [15.6 m/s] close, snow hold-closed) SOURCED, but the sensor/logic
  implementation is ASSUMED — bidder/PE to detail.
- **Surface finish / GD&T values** on the brackets — ASSUMED; PE to set.
- **Weatherproofing detail** (panel lap, flashing, gasket, drainage) — ASSUMED; bidder to detail with
  the NW-CO-012 panel.

---

## 8. References

- Parts registry: `design/mechanical/tender/gen/partspec.py` → `parts_for('BP-04')` (single source of truth).
- BOM / cut list / COTS: `design/mechanical/tender/bom/{master_bom,cut_list,cots_schedule}.csv`.
- Control drawings: `design/mechanical/tender/drawings/NW-RR-00{1..6}.svg`.
- Design basis: `design/mechanical/MECHANICAL_DESIGN.md` §7 (wind — FAIL/remediated, hold-downs),
  §10 (roll-off drive + snow — PASS + snow-interlock finding), §9 (selected config + the 5 remediations);
  `design/mechanical/tradestudy/SECTION.md` (enclosure = roll-off + active thermal; anchors = 4× 2 klbf).
- Standards register: MIL-STD-31000A; **AWS D1.1** (structural steel welding, WPS/PQR/WPQ), **AWS A2.4**
  (weld & NDE symbols); ASTM A500 Gr B (HSS), ASTM A36 (steel), ASTM A123 (hot-dip galvanize),
  ASTM F1554 Gr36 (anchor bolts), ASTM A574 (SHCS); ACI 318 Ch.17 (anchoring), ASCE 7 (wind/snow/seismic);
  ASME Y14.5-2018 / Y14.100 / Y14.24 / Y14.1; ISO 286; ISO 2768; STEP ISO 10303 AP242; DXF/DWG.
</content>
</invoke>
