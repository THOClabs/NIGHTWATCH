# BP-01 — Mount Head Machining (CNC 6061-T6) — Bidder README

> **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**

| Field | Value |
|---|---|
| Package | **BP-01 — Mount head machining** |
| Trade | CNC machining (6061-T6 aluminium), 3-axis mill |
| Parts | NW-MH-001, NW-MH-002, NW-MH-003 (3 fabricated line items) |
| Branch / project | `design/mechanical-tender` — NIGHTWATCH Observatory Mount & Roll-off Tender |
| Issue date | 2026-08-06 |
| Revision | A |
| Governing TDP standard | MIL-STD-31000A (Technical Data Package) |

This README is the entry point for the machine shop bidding BP-01. It defines the **scope**, the
**data package the shop receives**, the **bidder deliverables**, and the items still carried as
**ASSUMED design-intent**. Read it with `SOW.md` (the per-part machining specification) and
`acceptance.md` (the CMM dimensional acceptance plan) in this same folder.

---

## 1. Scope

BP-01 covers the **mount head only** — the three fabricated 6061-T6 aluminium parts that form the
right-ascension (RA) and declination (DEC) axis housings and the dovetail saddle clamp. The shop:

1. Procures **6061-T6 plate** to spec, with material certification.
2. CNC-machines the three parts to the STEP master and the NW-MH control drawings.
3. Applies **Type III hardcoat anodize** per MIL-A-8625F Class 1 (clear).
4. Inspects per `acceptance.md` and delivers finished, certified, first-article-inspected parts.

**Out of scope for BP-01** (separate packages — the head *interfaces* to these but the shop does not
supply them):

| Interface | Supplied under | Notes |
|---|---|---|
| Counterweight shaft, RA drive spindle, DEC drive spindle | BP-02 (303 SS precision turned) | Spindles carry the bearing inner races that seat in the BP-01 housings. |
| Concrete pier, pier top plate, pier-to-mount adapter | BP-03 (pier & foundation) | The RA housing mounts to the adapter plate (NW-PF-003). |
| Roll-off roof steelwork | BP-04 | Not a mount-head interface. |
| Harmonic drives, angular-contact bearings, on-axis encoders, motors, fasteners | BP-05 (COTS) | See §4 interface list. |

---

## 2. Data package the shop receives (per MIL-STD-31000A)

| Item | Format / standard | Role |
|---|---|---|
| 3-D solid master | **STEP ISO 10303 AP242** | **CNC authority** — governs as-modelled geometry. |
| Control drawings NW-MH-001 / -002 / -003 | **PDF** (drawing practices per ASME Y14.100; drawing types Y14.24; sheet & title block Y14.1) | Envelope + title block + key dimensions & features; bid control drawing. |
| `SOW.md` | Markdown | Per-part machining spec: datums, H7 bores, registers, saddle, finish, GD&T, certs. |
| `acceptance.md` | Markdown | CMM dimensional acceptance of the H7 bores + flatness; FAI requirements. |
| `cut_list.csv` (rows for NW-MH-001/002/003) | CSV/XLSX | Stock size, cut allowance, stock mass. |

**Order of precedence.** The **STEP AP242 solid governs geometry**; the drawing + SOW govern
tolerances, notes, finish, and material; where geometry and the tolerance package disagree, the **SOW
controls** and the bidder shall raise an RFI before cutting metal. All GD&T is interpreted per
**ASME Y14.5-2018**; general tolerances per **ISO 2768-mK**; fits per **ISO 286**.

---

## 3. Line-item summary (source: `partspec.parts_for('BP-01')` + `cut_list.csv`)

| Part no. | Name | Stock (plate) | Qty | Stock mass | Finish | Drawing | cut_list row |
|---|---|---|---:|---:|---|---|---|
| **NW-MH-001** | RA (polar) axis housing | 203.2 mm [8.000 in] × 203.2 mm [8.000 in] × 76.2 mm [3.000 in] | 1 | 8.50 kg | Type III hardcoat anodize | NW-MH-001 | row 2 |
| **NW-MH-002** | DEC axis housing + Losmandy-D saddle | 152.4 mm [6.000 in] × 152.4 mm [6.000 in] × 63.5 mm [2.500 in] | 1 | 3.98 kg | Type III hardcoat anodize | NW-MH-002 | row 3 |
| **NW-MH-003** | DEC saddle clamp bar | 101.6 mm [4.000 in] × 76.2 mm [3.000 in] × 25.4 mm [1.000 in] | 1 | 0.53 kg | Type III hardcoat anodize | NW-MH-003 | row 4 |

Stock mass is the **quantity ordered** (stock volume × 6061-T6 density), not finished net mass. Cut
allowance is 3.0 mm on stock. Material for all three: **6061-T6 aluminium plate per ASTM B209 /
AMS-QQ-A-250/11**.

---

## 4. Cross-package interfaces the shop must preserve

The bearing seats and drive registers are mating features to other packages. The shop machines the
BP-01 side; the datums must be held so the mating COTS/turned parts assemble:

| BP-01 feature | Mates to | Part |
|---|---|---|
| NW-MH-001 bearing seat Ø68 H7 | Angular-contact **7008** DB pair (OD 68 mm) | NW-CO-003 (BP-05) |
| NW-MH-001 drive register Ø80 mm | **CSF-32-100** harmonic drive (bore 80 mm) via RA spindle | NW-CO-001 / NW-TP-002 |
| NW-MH-002 bearing seat Ø55 H7 | Angular-contact **7006** DB pair (OD 55 mm) | NW-CO-004 (BP-05) |
| NW-MH-002 drive register Ø64 mm | **CSF-25-80** harmonic drive (bore 64 mm) via DEC spindle | NW-CO-002 / NW-TP-003 |
| Axis (through-bore) | **On-axis absolute encoder ring** | NW-CO-005 (BP-05) |
| NW-MH-002 Losmandy-D saddle + NW-MH-003 clamp | OTA dovetail | (owner-supplied OTA) |

> **Remediation context.** The bearing seats are sized for **angular-contact 7008 (RA) / 7006 (DEC)**
> pairs in a **back-to-back (DB), preloaded** arrangement — the proven remediation of the deep-groove
> 6008/6006 baseline, which the stiffness proof showed to be ~98% of the pointing-deflection FAIL.
> This is a **moment-stiffness** decision: seat coaxiality and bore-to-face perpendicularity are the
> stiffness-critical callouts (see `SOW.md` §4 and MECHANICAL_DESIGN.md §9).

---

## 5. Bidder deliverables

1. Finished, anodized parts NW-MH-001 / -002 / -003 (qty 1 each).
2. **Material certification / CoC** for the 6061-T6 plate (ASTM B209 / AMS-QQ-A-250/11), with heat/lot
   traceability and T6 temper confirmation.
3. **Anodize certification** — MIL-A-8625F Type III Class 1, coating thickness record.
4. **First-Article Inspection (FAI) report** per `acceptance.md`, including the CMM results for every
   H7 bore and flatness callout.
5. RFI / nonconformance log for any ASSUMED value the shop needed resolved.

---

## 6. ASSUMED design-intent — bidder / PE to confirm (NOT final)

The following are carried as **ASSUMED design-intent** in the parts registry and must **not** be
treated as released dimensions. The bidder/PE shall confirm before production:

- **Flange bolt-circle diameters and patterns** — NW-MH-001 Ø104.0 mm [4.094 in] × 8 holes; NW-MH-002
  Ø83.0 mm [3.268 in] (DERIVED ~1.3× drive bore; not fixed in the design).
- **Losmandy-D saddle geometry** on NW-MH-002 (76.2 mm [3.000 in] width, 15° dovetail) — ASSUMED to a
  standard Losmandy-D profile; undercut/relief not dimensioned in the repo.
- **NW-MH-003 saddle clamp bar** — the entire part is ASSUMED design-intent; the Losmandy-D clamp is
  not dimensioned in the repo.
- **GD&T tolerance values** — coaxiality, perpendicularity, and position values are ASSUMED pending PE.
- **Bearing-seat surface finish and preload method** (shim vs. clamp) — ASSUMED, bidder/PE to detail.
- **Encoder-ring register location** on the axis — ASSUMED; preserve the through-bore.

---

## 7. References

- Parts registry: `design/mechanical/tender/gen/partspec.py` → `parts_for('BP-01')` (single source of truth).
- BOM / cut list: `design/mechanical/tender/bom/{master_bom,cut_list}.csv`.
- Control drawings: `design/mechanical/tender/drawings/NW-MH-00{1,2,3}.svg`.
- Design basis: `design/mechanical/MECHANICAL_DESIGN.md` §9 (selected config + remediations);
  `design/mechanical/tradestudy/SECTION.md` (selection rationale, item 8 bearing fix).
- Standards register: MIL-STD-31000A, ASME Y14.5-2018 / Y14.100 / Y14.24 / Y14.1 / Y14.36, ASME B46.1,
  ISO 286, ISO 2768, MIL-A-8625F, ASTM B209 / AMS-QQ-A-250/11.
