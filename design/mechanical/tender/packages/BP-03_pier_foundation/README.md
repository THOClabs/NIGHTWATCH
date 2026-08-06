# BP-03 — Pier & Foundation (Reinforced Concrete + Structural Steel) — Bidder README

> **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**

| Field | Value |
|---|---|
| Package | **BP-03 — Pier & foundation** |
| Trade | Reinforced concrete (cast-in-place) + structural steel + light CNC |
| Parts | NW-PF-001, NW-PF-002, NW-PF-003, NW-PF-004 (4 line items; 3 fabrication control drawings) |
| Branch / project | `design/mechanical-tender` — NIGHTWATCH Observatory Mount & Roll-off Tender |
| Issue date | 2026-08-06 |
| Revision | A |
| Governing TDP standard | MIL-STD-31000A (Technical Data Package) |

This README is the entry point for the concrete/foundation contractor bidding BP-03. It defines the
**scope**, the **data package the contractor receives**, the **bidder deliverables**, the **PE-STAMP
GATE**, and the items carried as **ASSUMED design-intent**. Read it with `SOW.md` (per-part
specification) and `acceptance.md` (cylinder breaks, anchor pull, plumb/level) in this same folder.

---

## 0. PE-STAMP GATE — READ FIRST (this package is NOT releasable for construction)

> **⚠ THE PIER AND FOUNDATION ARE ISSUED FOR PE REVIEW ONLY.**
> **A licensed Professional Engineer, registered in the jurisdiction of the build site, MUST review,
> size, and STAMP the reinforced-concrete pier, its reinforcement, its embedment, and the anchor
> bolts BEFORE any permit is drawn or any concrete is placed.** Nothing in this package — dimensions,
> rebar schedule, anchor sizing, embedment — is a released structural design. Every structural
> quantity herein is either **SOURCED from the proven parametric model** (envelope geometry, f'c,
> embedment) or **ASSUMED design-intent** (rebar schedule, anchor grade/count, cover, seismic
> detailing) and is presented **for the PE to confirm, complete, and stamp** under the governing
> building code and the referenced load standard.

**Why a stamp is mandatory.** The build site is a remote, seismically-active, high-desert Nevada
location (**site datum 38.9 °N / −117.4 °W, elevation ~1800 m [~5900 ft]**). Three structural loads
govern and are **owner/PE responsibilities under ASCE 7**:

| Load | Basis (design study) | What it drives |
|---|---|---|
| **Wind** | ASCE 7 basic wind ~105 mph 3-sec gust, Risk Category I (survival, roof closed) | roof/enclosure hold-down, pier overturning |
| **Snow** | ~25 psf ground snow, high-desert @ ~1800 m | enclosure (BP-04), not the pier directly |
| **Seismic** | S_DS ≈ 0.5 g (Walker Lane vicinity) | pier base shear, anchorage, embedment |

The wind basic speed (105 mph) and seismic S_DS (0.5 g) are **ASSUMED** in the design study because
the repository was silent on them — they are **exactly the values the PE must set from the site's
ASCE 7 hazard data and stamp.** See `MECHANICAL_DESIGN.md` §7 (wind — FAIL/remediated) and §8
(pier — PASS) for the computed basis.

**No concrete is placed, and no anchor is cast, until the stamped drawings and the PE-approved
Inspection & Test Plan (`acceptance.md`) are in hand.**

---

## 1. Scope

BP-03 covers the **telescope pier and its foundation interface** — the cast-in-place reinforced-concrete
pier, the steel top plate grouted to it, the aluminium adapter plate that orients the mount to site
latitude, and the cast-in anchor-bolt set with its setting template. The contractor:

1. Places a **cast-in-place reinforced-concrete pier** (NW-PF-001) to f'c = 4000 psi (27.6 MPa) per
   **ACI 318 / ACI 301**, with a rebar cage per the PE-stamped schedule (baseline 6 × #4 vertical +
   #3 ties per **ASTM A615 Gr60**), **structurally isolated from any building slab or footing.**
2. Casts the **anchor-bolt set** (NW-PF-004, **ASTM F1554 Gr36**, per **ACI 318 Ch.17**) into the wet
   pier via a fabricated setting template so the projecting bolts match the top-plate pattern.
3. Supplies the **galvanized steel top plate** (NW-PF-002, **ASTM A36**, hot-dip galv per **ASTM A123**)
   and the **anodized aluminium adapter plate** (NW-PF-003, **6061-T6** per ASTM B209, Type III
   hardcoat per **MIL-A-8625F**), or subcontracts their cut/machine scope.
4. Grouts, levels, and plumbs the plate stack, then inspects per `acceptance.md` (concrete cylinder
   breaks, anchor proof/pull, plumb/level) and delivers a certified, PE-signed foundation.

**Out of scope for BP-03** (separate packages — the pier *interfaces* to these but the contractor does
not supply them):

| Interface | Supplied under | Notes |
|---|---|---|
| RA (polar) axis housing NW-MH-001 | BP-01 (mount head) | Bolts to the adapter plate NW-PF-003 (4 × M6). |
| Roll-off roof steelwork + **wind hold-down anchor brackets NW-RR-006** | BP-04 | The **4× survival-wind roof hold-downs** anchor the enclosure/building foundation, **not** the telescope pier (the pier is isolated). See §4. |
| Harmonic drives, bearings, encoders, fasteners | BP-05 (COTS) | Not a pier interface. |
| Enclosure/building foundation | Owner / site civil (not in this tender scope) | The pier passes **through** but is **isolated from** the building slab. |

---

## 2. Data package the contractor receives (per MIL-STD-31000A)

| Item | Format / standard | Role |
|---|---|---|
| 3-D solid master (pier + plates) | **STEP ISO 10303 AP242** | As-modelled geometry master. |
| Control drawings NW-PF-001 / -002 / -003 | **PDF** (drawing practices ASME Y14.100; drawing types Y14.24; sheet & title block Y14.1) | Envelope + title block + key dimensions; bid control drawing. |
| **PE-stamped structural drawings** | PDF (issued by owner's PE) | **Governs for construction** — supersedes the ASSUMED rebar/anchor/embedment values herein. |
| `SOW.md` | Markdown | Per-part spec: concrete, rebar, anchors, isolation, embedment, finishes. |
| `acceptance.md` | Markdown | Concrete cylinder breaks, anchor pull/proof, plumb/level, placement inspection. |
| `cut_list.csv` (rows NW-PF-001/002/003) | CSV/XLSX | Stock size, cut allowance, stock mass. |
| `cots_schedule.csv` (row NW-PF-004) | CSV/XLSX | Anchor-bolt buy item + template. |

**Order of precedence.** For the **fabricated plates** (NW-PF-002/-003) the **STEP AP242 solid
governs geometry**; the drawing + SOW govern tolerances, finish, and material. **For the
reinforced-concrete pier, the reinforcement, the embedment, and the anchor bolts, the PE-STAMPED
STRUCTURAL DRAWINGS GOVERN and supersede every number in this package.** Where any document disagrees,
the **PE-stamped set controls** and the bidder shall raise an RFI before placing concrete. General
tolerances per **ISO 2768**; plate GD&T per **ASME Y14.5-2018**; fits per **ISO 286**.

---

## 3. Line-item summary (source: `partspec.parts_for('BP-03')` + BOM/cut list)

| Part no. | Name | Material | Stock / size | Qty | Stock mass | Finish | Fab drawing |
|---|---|---|---|---:|---:|---|---|
| **NW-PF-001** | Reinforced-concrete telescope pier | Cast-in-place concrete **f'c = 4000 psi (27.6 MPa)** per ACI 318 / ACI 301 | Round pier **Ø304.8 mm [12.000 in] × 1828.8 mm [72.000 in]** overall | 1 | 320.26 kg (≈0.13 m³ [≈4.7 ft³ / ≈0.18 yd³] concrete) | none (formed) | NW-PF-001 |
| **NW-PF-002** | Pier top plate | ASTM A36 structural steel | Plate **304.8 mm [12.000 in] × 304.8 mm [12.000 in] × 9.5 mm [0.375 in]** | 1 | 6.94 kg | Hot-dip galvanize per ASTM A123 | NW-PF-002 |
| **NW-PF-003** | Pier-to-mount adapter plate | 6061-T6 aluminium per ASTM B209 | Plate **254.0 mm [10.000 in] × 254.0 mm [10.000 in] × 19.1 mm [0.750 in]** | 1 | 3.32 kg | Type III hardcoat anodize per MIL-A-8625F | NW-PF-003 |
| **NW-PF-004** | Anchor-bolt set + template | ASTM F1554 Gr36 galvanized | **4 × Ø19.05 mm [0.750 in] × 304.8 mm [12.000 in]** anchor bolts + setting template | 1 | — (buy + fabricate) | Hot-dip galvanize per ASTM A123 | none (buy item; template bidder-detailed) |

Pier stock mass is the **quantity ordered** (stock envelope volume × concrete density 2400 kg/m³),
not a formed-net figure; the ≈0.13 m³ concrete volume is a **pour-planning estimate derived from the
Ø304.8 × 1828.8 mm envelope** — confirm against the stamped forming detail. Plate cut allowance is
3.0 mm on stock. NW-PF-004 carries **no fabrication control drawing** — the bolts are purchased to
ASTM F1554 and the setting template is fabricated by the bidder to the stamped top-plate/adapter hole
pattern (see `SOW.md` §5).

---

## 4. Cross-package interfaces the contractor must preserve

The plate stack chains the pier up to the mount head. Bottom-to-top:

| Level | Feature | Mates to | Part |
|---|---|---|---|
| Pier top | 4 × cast-in anchor bolts, projection 50.0 mm [1.969 in] | Top-plate anchor holes | NW-PF-004 → NW-PF-002 |
| Top plate | 4 × Ø20.6 mm [Ø0.81 in] anchor holes (clearance for Ø0.75 F1554) | Cast-in anchors NW-PF-004 | NW-PF-002 |
| Top plate → adapter | Centre hole pattern 4 × Ø11.2 mm [Ø0.44 in] | Adapter pier-plate pattern | NW-PF-002 ↔ NW-PF-003 |
| Adapter → RA housing | 4 × M6 pattern + centre bore Ø90.0 mm [3.543 in] | RA (polar) axis housing | NW-PF-003 → **NW-MH-001 (BP-01)** |
| Adapter wedge | Latitude tilt to **38.9°** (wedge/shim, bidder to detail) | Sets polar axis to site latitude | NW-PF-003 |

> **Wind hold-down clarification (important).** The **9.2 kN survival-wind roof uplift** is resisted by
> the **4× wind hold-down anchor brackets NW-RR-006 (BP-04)**, which anchor the **enclosure/building
> foundation** — because the design study assumes the **telescope pier is structurally isolated from
> the enclosure** (standard observatory practice, to keep vibration off the optics). The BP-03
> anchor-bolt set NW-PF-004 casts into the **pier** and resists the **mount overturning + seismic**
> demand (pier proof §8). The registry nonetheless **sizes NW-PF-004 against the ~9.2 kN uplift number
> as a bounding case** — see §6 and `SOW.md` §5. **Where each anchor group lands, and the final anchor
> capacity, are PE coordination items — PE to confirm.**

---

## 5. Bidder deliverables

1. Finished pier (NW-PF-001), top plate (NW-PF-002), adapter plate (NW-PF-003), and cast anchor set +
   template (NW-PF-004), installed, grouted, leveled, and plumbed.
2. **Concrete submittals** — approved mix design (f'c = 4000 psi per ACI 301), batch tickets, and
   **cylinder break reports** (7-day and 28-day) per `acceptance.md`.
3. **Reinforcement certs** — mill certs for the #4 / #3 bar (ASTM A615 Gr60) and a rebar-placement /
   cover inspection record against the stamped cage.
4. **Anchor-bolt certs** — mill cert / CoC for the ASTM F1554 Gr36 bolts, galvanize cert (ASTM A123),
   and the **anchor proof/pull test record** per `acceptance.md`.
5. **Steel & aluminium plate certs** — A36 material cert + galvanize (ASTM A123) coating-thickness
   record for NW-PF-002; 6061-T6 cert (ASTM B209) + Type III anodize cert (MIL-A-8625F) for NW-PF-003.
6. **Plumb / level survey** — pier plumb ≤ 1:200 and top-of-plate level ≤ 0.5° per `acceptance.md`.
7. **PE sign-off** — the PE-stamped structural drawings and the PE's field-inspection/hold-point
   sign-offs (rebar, embedment, pour, anchor set).
8. RFI / nonconformance log resolving every ASSUMED value before it is built.

---

## 6. ASSUMED design-intent — bidder / PE to confirm (NOT final)

Carried as **ASSUMED design-intent** in the parts registry; **not** released dimensions. The PE shall
confirm/complete and stamp before construction:

- **Rebar schedule** — baseline **6 × #4 vertical + #3 ties @ 12 in [304.8 mm] oc** (ASTM A615 Gr60)
  is **ASSUMED design-intent**; bar size/count, tie spacing, seismic hoop detailing, splices, and
  **concrete cover** (ASSUMED ~76 mm [3 in] cast against earth per ACI 318) are **PE to set.**
- **Anchor-bolt sizing** — **4 × Ø0.75 in [19.05 mm] F1554 Gr36**, embedment 304.8 mm [12.000 in],
  projection 50.0 mm [1.969 in], is **ASSUMED per ACI 318 Ch.17**; final diameter, grade, embedment,
  edge distance, and count are **PE to size for the governing wind/seismic uplift (~9.2 kN roof-uplift
  bounding case; net anchor demand 7.4 kN → 4× 2 klbf gives SF 3.9).**
- **Embedment vs frost** — 914.4 mm [36.000 in] embedment is **SOURCED**; it exceeds the **ASSUMED**
  central-NV frost line of 0.3–0.6 m [12–24 in] (SF ≈ 1.52). PE to confirm the site frost depth and
  any bearing/bell-footing detail.
- **Latitude wedge on NW-PF-003** — the 38.9° polar-axis tilt (wedge or shim set) is **ASSUMED
  design-intent; adapter geometry is not fixed in the repo** — bidder to detail, PE to confirm.
- **Wind speed / seismic parameters** — basic wind 105 mph and S_DS 0.5 g are **ASSUMED (ASCE 7);
  PE to set from site hazard data.**
- **Grout, leveling nuts, and isolation gap detail** between pier and any building slab — ASSUMED;
  bidder/PE to detail (the pier **must not** bear on or bond to the slab).

---

## 7. References

- Parts registry: `design/mechanical/tender/gen/partspec.py` → `parts_for('BP-03')` (single source of truth).
- BOM / cut list / COTS: `design/mechanical/tender/bom/{master_bom,cut_list,cots_schedule}.csv`.
- Control drawings: `design/mechanical/tender/drawings/NW-PF-00{1,2,3}.svg`.
- Design basis: `design/mechanical/MECHANICAL_DESIGN.md` §7 (wind loads — FAIL/remediated),
  §8 (pier/foundation — PASS, governing SF 6.8); `design/mechanical/tradestudy/SECTION.md` item 5
  (pier — Concrete Sonotube baseline retained).
- Standards register: MIL-STD-31000A; ACI 318 (Ch.17 anchoring), ACI 301 (concrete spec); ASCE 7
  (wind/snow/seismic); ASTM A615 Gr60 (rebar), ASTM F1554 Gr36 (anchor bolts), ASTM A36 (steel),
  ASTM A123 (hot-dip galvanize), ASTM B209 (6061-T6), MIL-A-8625F (Type III anodize);
  ASME Y14.5-2018 / Y14.100 / Y14.24 / Y14.1; ISO 286; ISO 2768.
