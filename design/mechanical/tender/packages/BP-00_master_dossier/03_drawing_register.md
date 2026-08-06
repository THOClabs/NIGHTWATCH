# 03 — Drawing Register

**Document:** BP-00 / 03 — Drawing Register, Rev A
**Status:** **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**
**Units:** mm primary, [inch] in brackets.

Every fabricated part in the parts registry carries one **control drawing** — a
to-scale stock envelope with the controlling dual-unit dimensions, a keyed
feature/dimension table, and an ASME-Y14-style title block (material, finish,
tolerance, GD&T status, and the "ISSUED FOR BID / FOR PE REVIEW" state). The sheet is
the dimensioned, quotable summary a shop reviews to price the job; the **3-D
machining master** for every machined feature is the parametric
`design/mechanical/cad/*.scad` and the **STEP (ISO 10303 AP242)** exported from it.

This register lists `partspec.fabricated_parts()` — parts with a fabrication drawing
and non-COTS stock. **15 control drawings** across four fabrication packages.
Drawing practice per **ASME Y14.100 / Y14.24 / Y14.1**; associated list per
**ASME Y14.34**.

---

## 1. Register

| # | Part No. | Name | Pkg | Material | Finish | Process | Rev | Sheet |
|:-:|---|---|:-:|---|---|---|:-:|---|
| 1 | **NW-MH-001** | RA (polar) axis housing | BP-01 | 6061-T6 aluminium plate per ASTM B209 / AMS-QQ-A-250/11 | Type III hardcoat anodize per MIL-A-8625F | CNC mill, 3-axis | A | `NW-MH-001.svg` → PDF |
| 2 | **NW-MH-002** | DEC axis housing + Losmandy-D saddle | BP-01 | 6061-T6 aluminium plate per ASTM B209 / AMS-QQ-A-250/11 | Type III hardcoat anodize per MIL-A-8625F | CNC mill, 3-axis | A | `NW-MH-002.svg` → PDF |
| 3 | **NW-MH-003** | DEC saddle clamp bar | BP-01 | 6061-T6 aluminium plate per ASTM B209 / AMS-QQ-A-250/11 | Type III hardcoat anodize per MIL-A-8625F | CNC mill, 3-axis | A | `NW-MH-003.svg` → PDF |
| 4 | **NW-TP-001** | Counterweight shaft | BP-02 | 303 stainless per ASTM A582 | Passivate per ASTM A967 (nitric) | CNC turn | A | `NW-TP-001.svg` → PDF |
| 5 | **NW-TP-002** | RA drive spindle / drawbar adapter | BP-02 | 303 stainless per ASTM A582 | Passivate per ASTM A967 (nitric) | CNC turn + mill | A | `NW-TP-002.svg` → PDF |
| 6 | **NW-TP-003** | DEC drive spindle / saddle stub | BP-02 | 303 stainless per ASTM A582 | Passivate per ASTM A967 (nitric) | CNC turn + mill | A | `NW-TP-003.svg` → PDF |
| 7 | **NW-PF-001** | Reinforced-concrete telescope pier | BP-03 | Cast-in-place concrete f′c = 4000 psi (27.6 MPa) per ACI 318 / ACI 301 | none (concrete) | Cast-in-place | A | `NW-PF-001.svg` → PDF |
| 8 | **NW-PF-002** | Pier top plate | BP-03 | ASTM A36 structural steel | Hot-dip galvanize per ASTM A123 | Laser/waterjet cut + drill | A | `NW-PF-002.svg` → PDF |
| 9 | **NW-PF-003** | Pier-to-mount adapter plate | BP-03 | 6061-T6 aluminium per ASTM B209 | Type III hardcoat anodize per MIL-A-8625F | CNC mill | A | `NW-PF-003.svg` → PDF |
| 10 | **NW-RR-001** | Roof frame perimeter (HSS) | BP-04 | ASTM A500 Gr B HSS (steel) | Hot-dip galvanize per ASTM A123 | Cut + weld (AWS D1.1) | A | `NW-RR-001.svg` → PDF |
| 11 | **NW-RR-002** | Roof rafters / purlins | BP-04 | ASTM A500 Gr B HSS (steel) | Hot-dip galvanize per ASTM A123 | Cut + weld (AWS D1.1) | A | `NW-RR-002.svg` → PDF |
| 12 | **NW-RR-003** | Track rail beams (box track) | BP-04 | ASTM A36 structural steel | Hot-dip galvanize per ASTM A123 | Cut + weld / bolt to piers | A | `NW-RR-003.svg` → PDF |
| 13 | **NW-RR-004** | Wheel axle brackets | BP-04 | ASTM A36 structural steel | Hot-dip galvanize per ASTM A123 | Laser cut + weld | A | `NW-RR-004.svg` → PDF |
| 14 | **NW-RR-005** | Drive bracket + end stops | BP-04 | ASTM A36 structural steel | Hot-dip galvanize per ASTM A123 | Laser cut + weld | A | `NW-RR-005.svg` → PDF |
| 15 | **NW-RR-006** | Wind hold-down anchor brackets | BP-04 | ASTM A36 structural steel | Hot-dip galvanize per ASTM A123 | Laser cut + weld | A | `NW-RR-006.svg` → PDF |

Sheets are held in the repo as SVG (`design/mechanical/tender/drawings/NW-xx.svg`) and
issued to bidders as **PDF**. All at **Rev A** at this issue.

## 2. 3-D / cutting masters and format map

| Package | 3-D machining master | Cutting geometry | Sheet |
|---|---|---|---|
| BP-01 (NW-MH-00x) | `cad/ra_housing.scad`, `cad/dec_housing.scad` → **STEP AP242** | — | PDF |
| BP-02 (NW-TP-00x) | `cad/counterweight_shaft.scad` (+ turned masters) → **STEP AP242** | — | PDF |
| BP-03 (NW-PF-00x) | `cad/pier_adapter.scad` → **STEP AP242** (adapter/top plate) | **DXF/DWG** plate profiles | PDF |
| BP-04 (NW-RR-00x) | `cad/assembly.scad` (assembly reference) | **DXF/DWG** flat patterns for laser/waterjet cut | PDF |

The `.scad` source and its STEP export are the geometry of record for machined 3-D
features; the control sheet governs the **dimensioned, toleranced** callouts. Where
the STEP model and the sheet disagree, the **sheet governs** and it is an RFI item.

## 3. Registry exceptions (no fabrication drawing)

The following are in the parts registry but carry **no fabrication control drawing**
(they are purchased / buy-to-print):

- **NW-PF-004** — Anchor-bolt set + template (BP-03): COTS ASTM F1554 Gr36 bolts plus
  a fabricated template; listed on the **COTS schedule** and the BP-03 SOW, sizing
  ASSUMED per ACI 318 Ch. 17 (PE to confirm for ~9.2 kN uplift). No `NW-PF-004.svg`.
- **NW-CO-001 … NW-CO-014** (BP-05): all commercial off-the-shelf; specified by
  manufacturer datasheet on the COTS schedule, not by a NIGHTWATCH drawing.

## 4. Notes on the register

- **Revisions.** Part numbers are stable; changes advance the sheet revision. Rev A is
  the issue-for-bid revision. A released-for-construction revision follows the PE stamp
  (see BP-03/BP-04 gates).
- **ASSUMED design-intent on the sheets.** Several sheets carry values the frozen
  design does not fix — Losmandy-D saddle/clamp geometry (NW-MH-002/003), spindle body
  diameters (NW-TP-002/003), adapter geometry (NW-PF-003), rebar schedule (NW-PF-001),
  roof member sizes and weld sizes (NW-RR-001…006). Each is tagged **ASSUMED
  design-intent — bidder/PE to confirm** in the sheet's PROVENANCE/NOTE line and shall
  be confirmed before construction.
- **Title-block status.** Every sheet's title block reads **"ISSUED FOR BID / FOR PE
  REVIEW — NOT FOR CONSTRUCTION"** and shall not be used for construction until
  re-issued post-stamp.

---

*This register is generated from `partspec.fabricated_parts()`; if the parts registry
changes, regenerate the sheets (`python3 -m design.mechanical.tender.gen.drawing`) and
reconcile this table.*
