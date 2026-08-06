# NIGHTWATCH — Mount & Roll-off "Turret" Fabrication Tender

**ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**

Vendor tender package that turns the proven mechanical design
(`design/mechanical/MECHANICAL_DESIGN.md`) into biddable fabrication documents.
Bid **in parts or whole** — each package below is self-contained.

## Start here
- **`packages/BP-00_master_dossier/`** — the umbrella: Instructions to Bidders,
  general SOW, standards register, drawing register, Inspection & Test Plan,
  **pricing/bid form**, T&Cs, and the roll-off/turret-variant appendix.

## Bid packages (one per trade)
| Pkg | Scope | Trade | Items |
|---|---|---|:-:|
| BP-01 | Mount head machining (housings, saddle) | CNC 6061-T6 | 3 |
| BP-02 | Precision turned parts (spindles, shaft) | Turning, 303 SS | 3 |
| BP-03 | Pier & foundation *(PE-stamp gate)* | RC + structural steel | 4 |
| BP-04 | Roll-off roof "disappearing turret" *(PE-stamp gate)* | Steel fab + rail/drive | 6 |
| BP-05 | COTS procurement schedule | Purchase | 14 |

## Deliverables (all generated from the proven `calc/params.py`)
- `bom/master_bom.csv`, `bom/cut_list.csv`, `bom/cots_schedule.csv` — dual-unit (mm [in]).
- `bom/NIGHTWATCH_tender_BOM.xlsx` — Excel workbook (Index + BOM + Cut List + COTS).
- `drawings/NW-*.svg` — 15 dimensioned control drawings; `drawings/DRAWING_SET.html`
  bundles them all (open in a browser → Print → Save as PDF).
- `docs/NIGHTWATCH_tender_RFQ.docx` — the whole tender as one Word RFQ.

## Regenerate (single source of truth)
```
python3 -m design.mechanical.tender.gen.bom        # BOM + cut list CSVs
python3 -m design.mechanical.tender.gen.drawing    # 15 control drawings
python3 -m design.mechanical.tender.gen.htmlset    # print-to-PDF drawing set
python3 -m design.mechanical.tender.gen.xlsx_export # Excel BOM  (needs: pip install openpyxl)
python3 -m design.mechanical.tender.gen.docx_export # Word RFQ   (needs: pip install python-docx)
```
`design/mechanical/tests/test_tender.py` gates consistency (dims trace to the
registry; BOM ↔ cut-list ↔ drawings agree; remediations present, baseline absent).

## Key notes for bidders
- **The five proof-out remediations are baked in:** angular-contact **7008/7006**
  bearings (replace deep-groove 6008/6006), **on-axis absolute encoder**, **4× wind
  hold-down anchors**, temperature-compensated focuser, 48 V power pack.
- **PE-stamp gate:** BP-03 pier and BP-04 roof are structural (ASCE 7 wind/snow/
  seismic) — a licensed Professional Engineer must stamp the analysis before any
  "Issued for Construction" release.
- Values the design does not yet fix (weld/member sizing, rail/drive product, GD&T
  values, surface-finish Ra) are marked **ASSUMED design-intent — bidder/PE to confirm**.
