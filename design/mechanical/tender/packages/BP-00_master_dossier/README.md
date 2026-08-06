# NIGHTWATCH Observatory — Master Tender Dossier (BP-00)

**ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**

Document set: `BP-00` (umbrella). Rev A. Units: **mm primary, [inch] in brackets**.
Technical Data Package structured per **MIL-STD-31000A**.

---

This dossier is the umbrella over five bid packages (BP-01 … BP-05) that together
build the NIGHTWATCH telescope mount and its roll-off roof enclosure. The mechanical
engineering is proven out and frozen (see `design/mechanical/MECHANICAL_DESIGN.md`);
this dossier and its child packages are the **procurement documents** that let a shop
price and fabricate the work. Every controlling dimension quoted anywhere in the
dossier is pulled from the parts registry `design/mechanical/tender/gen/partspec.py`
and the generated Bill of Materials — no dimension is invented here.

## 1. Package index

| Pkg | Title | Trade | Line items | Fab drawings | Key vendor deliverables |
|---|---|---|:-:|:-:|---|
| **BP-01** | Mount head machining | CNC machining, 6061-T6 aluminium | 3 | 3 | 3× machined housings/bar, Type III hardcoat anodize, CMM report on H7 bores, material certs |
| **BP-02** | Precision turned parts | CNC / manual turning, 303 stainless | 3 | 3 | 3× turned spindles/shaft, passivation cert, concentricity report, material certs |
| **BP-03** | Pier & foundation | Reinforced concrete + structural steel | 4 | 3 | Cast-in-place RC pier, galvanized top plate, anodized adapter plate, cast-in anchor set + template. **PE stamp + concrete cylinder breaks required** |
| **BP-04** | Roll-off roof ("disappearing turret") | Structural steel fab + rail/drive install | 6 | 6 | Welded HSS roof frame, rafters/purlins, box-track rails, wheel/drive/hold-down brackets, hot-dip galvanized. **AWS D1.1 WPS/PQR + welder quals required** |
| **BP-05** | COTS procurement schedule | Purchase (buy-to-print / off-the-shelf) | 14 | 0 | Harmonic drives, angular-contact bearings, on-axis encoders, motors/drivers, focuser, wheels, roof drive, roofing, 48 V power pack, fasteners, anchor set |

Line-item and fabricated-drawing counts above are the current registry output
(`python3 -m design.mechanical.tender.gen.partspec`). Total across the job:
**30 registry line items**, **15 fabricated control drawings** (BP-05 and the
anchor set NW-PF-004 are buy items and carry no fabrication drawing).

## 2. BID IN PARTS OR WHOLE

A vendor may bid **any single package, any combination of packages, or the whole
job.** There is no requirement to bid the complete scope.

- **Single-trade shops** — a machine shop may bid BP-01 and/or BP-02 alone; a steel
  fabricator may bid BP-04 alone; a concrete/foundation contractor may bid BP-03
  alone; a distributor may quote BP-05 alone.
- **Line-item bidding** — within a package a bidder may price individual NW-xx line
  items. The pricing schedule (`05_bid_form.md`) has one row per line item plus a
  per-package subtotal and a whole-job total, so partial bids are first-class.
- **Whole-job bidding** — a general/turnkey bidder prices every package plus the
  integration/install scope and submits the whole-job total.
- **Interfaces stay the owner's risk to coordinate.** Mating features are held on the
  drawings by shared bolt patterns and registers (e.g. NW-MH-001 flange ↔ NW-TP-002
  register; NW-PF-002 ↔ NW-PF-003 hole pattern; NW-RR-004 bracket ↔ NW-CO-010
  wheel). A partial bidder is responsible only for their own package's conformance to
  the published dimensions and datums; the owner coordinates cross-package fit.

Award may be made by package, so price each package to stand alone.

## 3. Part-numbering scheme (NW-xx)

Every fabricated or purchased item carries a stable part number of the form
**`NW-<TT>-<NNN>`**:

| Field | Meaning |
|---|---|
| `NW` | Project prefix — NIGHTWATCH |
| `TT` | Trade/type code: **MH** = mount-head machined, **TP** = turned part, **PF** = pier/foundation, **RR** = roll-off roof, **CO** = commercial off-the-shelf |
| `NNN` | Sequential item within the trade (001, 002, …) |

The trade code maps one-to-one onto the bid package: MH→BP-01, TP→BP-02, PF→BP-03,
RR→BP-04, CO→BP-05. A part number never changes across revisions; the sheet revision
(Rev A at issue) tracks changes. Control drawings are named `NW-<TT>-<NNN>.svg`
(PDF at issue) and match the part number exactly.

## 4. File-format map (which trade gets what)

The 3-D machining master for every fabricated part is the parametric
`design/mechanical/cad/*.scad` and the **STEP (ISO 10303 AP242)** exported from it.
The dimensioned bid control drawing is the per-part sheet. Deliverable formats a
bidder receives / returns by trade:

| Package | Trade | Native/CNC geometry | Cutting / flat pattern | Drawing | BOM / schedule |
|---|---|---|---|---|---|
| BP-01 Mount head machining | 3-axis CNC mill | **STEP AP242** (3-D master) | — | **PDF** (`NW-MH-00x`) | **XLSX** |
| BP-02 Precision turned parts | CNC / manual turn | **STEP AP242** | — | **PDF** (`NW-TP-00x`) | **XLSX** |
| BP-03 Pier & foundation | RC + steel + anodized adapter | **STEP AP242** (adapter/top plate) | **DXF/DWG** (plate profiles) | **PDF** (`NW-PF-00x`) | **XLSX** |
| BP-04 Roll-off roof | Steel fab (cut + weld) | STEP AP242 (assembly ref) | **DXF/DWG** (flat-pattern laser/waterjet cut) | **PDF** (`NW-RR-00x`) | **XLSX** |
| BP-05 COTS procurement | Purchase | — | — | Vendor datasheets (PDF) | **XLSX** (COTS schedule) |

Rule of thumb: **STEP AP242 for anything CNC-machined in 3-D; DXF/DWG for anything
cut flat and welded; PDF for every dimensioned drawing; XLSX for every BOM and the
COTS schedule.** Drawings and BOM are also carried in this repo as generator source
(SVG sheets, CSV BOM) so the package regenerates deterministically.

## 5. DISAPPEARING TURRET — VARIANT APPENDIX

The observatory's popular name is the "disappearing turret." **The primary,
tendered, and proven scope is the roll-off roof of BP-04** — a rectangular steel
roof frame that rolls its own length off the aperture on box-track rails, selected
in the trade study (Weighted-Pugh 3.92, the winner at default and cost-heavy
weights) and proven in the enclosure and wind proofs (drive move-force 235 N at
SF 2.1; snow case governs; survival-wind hold-down anchors mandatory). Bidders
should price BP-04 as the delivered enclosure.

**A retractable / telescoping vertical turret is documented here as a future
ALTERNATE only.** A turret that lowers or telescopes the whole enclosure below a
parapet has architectural appeal but is **not engineered in this data package** and
must not be priced as the base scope. Any bidder proposing it must treat it as a
separate, later procurement subject to these gates:

- **It needs its own structural proof first.** None of the eleven Phase-C proofs
  covers a telescoping turret: its lifting structure, guide columns, seals, snow and
  survival-wind load paths, and drive are all unproven. The roll-off roof's wind
  proof (survival uplift 9.2 kN, hold-downs → SF 3.9) and snow proof (10.8 kN closed
  roof) do not transfer.
- **It is an ASSUMED design-intent concept — bidder/PE to confirm.** Member sizing,
  drive selection, seal detail, and foundation reactions are all open.
- **Bid it as a priced alternate**, in the "Alternates" block of `05_bid_form.md`,
  clearly separated from the base roll-off scope, and flagged as requiring an
  independent PE-stamped structural analysis before it can be built.

Until that analysis exists, the roll-off roof (BP-04) is the only enclosure
authorized for construction pricing.

## 6. Dossier contents

| File | Purpose |
|---|---|
| `README.md` | This index — packages, bid-in-parts rules, numbering, formats, turret appendix |
| `00_instructions_to_bidders.md` | ITB — eligibility, RFI, validity, evaluation, submission, schedule |
| `01_statement_of_work_general.md` | General SOW — scope, site, responsibilities, standards applicability |
| `02_standards_register.md` | Full standards table and what each governs |
| `03_drawing_register.md` | Every control drawing (part_no, name, pkg, material, rev, sheet) |
| `04_inspection_test_plan.md` | ITP — acceptance criteria per trade, hold/witness points |
| `05_bid_form.md` | Pricing schedule the vendor fills (per package, per line item, whole-job, alternates) |
| `06_terms_and_conditions.md` | Commercial T&Cs placeholders |

Child bid packages BP-01 … BP-05 (their SOWs, per-part fabrication notes, and
package-specific ITPs) live under their own `packages/BP-0x_*/` directories and
inherit every general document in this dossier.

---

*Every "ASSUMED design-intent" item in this dossier and its children is a value the
proven design does not yet fix (weld sizes, roof member sizing, rail/drive product
selection, GD&T tolerance values, surface finish, rebar/anchor sizing). Each is
explicitly flagged for the **bidder/PE to confirm** and is never presented as final.*
