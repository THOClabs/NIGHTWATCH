# 00 — Instructions to Bidders (ITB)

**Project:** NIGHTWATCH Observatory — telescope mount + roll-off roof enclosure
**Document:** BP-00 / 00 — Instructions to Bidders, Rev A
**Status:** **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**
**Units:** mm primary, [inch] in brackets throughout the package.

This tender is packaged as a **Technical Data Package structured per
MIL-STD-31000A** (product definition data, associated lists, and the "issued for
bid" data management state). The technical baseline is the parts registry
`design/mechanical/tender/gen/partspec.py` and the generated BOM/cut-list/COTS
schedule; the commercial baseline is this ITB together with `06_terms_and_conditions.md`.

---

## 1. Eligibility

A bidder is eligible to bid one or more packages if it can demonstrate, for each
package bid:

| Package | Minimum qualification |
|---|---|
| BP-01 Mount head machining | 3-axis CNC milling of 6061-T6 aluminium; ability to hold **ISO 286 H7** bearing bores and produce a CMM inspection report; anodizing per **MIL-A-8625F Type III** (in-house or qualified sub) |
| BP-02 Precision turned parts | CNC/manual turning of 303 stainless per **ASTM A582**; concentricity ≤ 0.02 TIR; passivation per **ASTM A967** (in-house or qualified sub) |
| BP-03 Pier & foundation | Cast-in-place reinforced concrete per **ACI 301 / ACI 318**; ability to deliver a **PE-stamped** foundation design and **ACI concrete cylinder break** reports; hot-dip galvanizing per **ASTM A123** (sub OK) |
| BP-04 Roll-off roof | Structural steel welding per **AWS D1.1** with current **WPS/PQR and welder qualifications**; hot-dip galvanizing per **ASTM A123**; rail/drive installation |
| BP-05 COTS procurement | Authorized distribution / procurement of the specified commercial items; ability to provide manufacturer datasheets and certificates of conformance |

Bidders shall submit evidence of the above (certifications, welder qual records, PE
registration in the project jurisdiction, sample inspection reports) with their
quote. A whole-job bidder shall evidence every package it self-performs and name its
subcontractors for the rest.

## 2. Request-for-Information (RFI) process

- All questions shall be submitted in writing to the Owner's technical
  representative by the **RFI cut-off date (SCHEDULE PLACEHOLDER — TBD)**, no later
  than **[N] business days** before the bid due date.
- Reference each question to a **NW-xx part number**, a drawing sheet, or a numbered
  clause of this dossier.
- Answers are issued to **all** bidders as numbered addenda; only written addenda
  amend the tender. Verbal guidance is not binding.
- **Every item flagged "ASSUMED design-intent — bidder/PE to confirm" is a valid RFI
  subject.** Where a bidder's fabrication method needs a value the frozen design does
  not fix (weld size, roof member size, rail/drive product, GD&T value, surface
  finish, rebar/anchor sizing), raise it as an RFI rather than assuming silently.

## 3. Quote validity

Quotes shall remain **firm and open for acceptance for 90 calendar days** from the
bid due date unless a longer period is stated on the bid form. Prices shall be fixed
(not indexed) for that period. Any assumptions, exclusions, or clarifications a
bidder relies on shall be listed explicitly on the bid form; unstated assumptions
are not binding on the Owner.

## 4. Basis of evaluation

Bids are evaluated on **best overall value to the Owner**, not lowest price alone.
The evaluation considers:

1. **Compliance** with the technical baseline (partspec dimensions, materials,
   finishes, tolerances, and the applicable standards register) and completeness of
   the required certs/reports.
2. **Total evaluated price** for the package(s) bid — labour + material + finish,
   inclusive of the Inspection & Test Plan deliverables of `04_inspection_test_plan.md`.
3. **Lead time** and schedule fit (see §7).
4. **Qualification and past performance** on comparable precision-mechanical /
   structural-steel / concrete work.
5. **Handling of ASSUMED design-intent items** — a bidder who prices these
   transparently and flags confirmations needed is preferred over one who buries them.

Award may be made **by individual package, by combination, or whole-job**, whichever
gives the Owner best overall value. The Owner may award different packages to
different bidders. The Owner is not bound to accept the lowest or any bid.

## 5. Submission format

Each bid shall contain, as separate clearly-labelled files:

1. **Completed pricing schedule** (`05_bid_form.md` filled in) — per line item, per
   package subtotal, whole-job total, and any alternates priced.
2. **Eligibility evidence** per §1.
3. **Compliance statement** — a line-by-line confirmation of conformance to each
   applicable standard in `02_standards_register.md`, with any deviations listed.
4. **Assumptions & exclusions** — including every "ASSUMED design-intent" value the
   bidder has resolved in order to price, stated for PE confirmation.
5. **Proposed lead time and schedule** against the placeholders in §7.
6. For BP-04: draft **WPS/PQR** references. For BP-03: the **PE** who will stamp the
   foundation. For BP-01/02: sample **inspection report** formats.

Preferred transmittal formats mirror the file-format map (README §4): **PDF** for
narrative and signed documents, **XLSX** for the priced schedule.

## 6. Award and documentation

The successful bidder shall, before fabrication, receive the released Technical Data
Package for the awarded package(s): the **STEP AP242** 3-D masters (BP-01/02/03
machined items), **DXF/DWG** flat patterns (BP-03/04 cut parts), **PDF** control
drawings (`NW-xx` sheets), and the **XLSX** BOM / COTS schedule. All released data
remains marked "ISSUED FOR BID / FOR PE REVIEW" until the responsible PE stamps the
package for construction; **no fabrication for permanent installation shall proceed
on unstamped data** (see BP-03 pier and BP-04 roof, both PE gates).

## 7. Schedule (PLACEHOLDERS — TBD)

| Milestone | Date |
|---|---|
| Tender issued | **[TBD]** |
| RFI cut-off | **[TBD]** |
| Final addenda issued | **[TBD]** |
| Bids due | **[TBD]** |
| Evaluation / clarifications | **[TBD]** |
| Award / letter of intent | **[TBD]** |
| Released-for-construction data (post PE stamp) | **[TBD]** |
| Delivery / installation window | **[TBD]** |

All dates are placeholders to be fixed in the issued tender. Bidders shall quote lead
times as **calendar weeks from award** on the bid form so schedules can be normalized
across partial and whole-job bids.

---

*This ITB is a commercial framing document. It does not alter any dimension, material,
finish, or tolerance in the frozen technical baseline; where it and a control drawing
appear to conflict on a technical value, the **partspec/drawing governs** and the
conflict shall be raised as an RFI.*
