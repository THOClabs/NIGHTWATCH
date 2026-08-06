# BP-02 — Precision Turned Parts (303 SS) — Bidder README

> **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**

| Field | Value |
|---|---|
| Package | **BP-02 — Precision turned parts** |
| Trade | CNC / manual turning (303 stainless steel), single-point turning + light milling |
| Parts | NW-TP-001, NW-TP-002, NW-TP-003 (3 fabricated line items) |
| Branch / project | `design/mechanical-tender` — NIGHTWATCH Observatory Mount & Roll-off Tender |
| Issue date | 2026-08-06 |
| Revision | A |
| Governing TDP standard | MIL-STD-31000A (Technical Data Package) |

This README is the entry point for the turning shop bidding BP-02. It defines the **scope**, the
**data package the shop receives**, the **bidder deliverables**, and the items still carried as
**ASSUMED design-intent**. Read it with `SOW.md` (the per-part turning specification) and
`acceptance.md` (the dimensional / concentricity acceptance plan) in this same folder.

---

## 1. Scope

BP-02 covers the **three turned 303 stainless-steel parts** that couple the harmonic drives to the
right-ascension (RA) and declination (DEC) axes and carry the angular-contact bearing inner races —
plus the optional counterweight shaft. The shop:

1. Procures **303 stainless round bar** to spec (ASTM A582), with material certification.
2. **Turns** (and lightly mills the bolt patterns / wrench flats on) the three parts to the STEP
   master and the NW-TP control drawings, holding the **bearing-race journals** and the
   **harmonic-drive registers** to their ISO 286 fit classes.
3. Applies **passivation per ASTM A967** (nitric or citric).
4. Inspects per `acceptance.md` and delivers finished, passivated, first-article-inspected parts.

**Out of scope for BP-02** (separate packages — the turned parts *interface* to these but the shop
does not supply them):

| Interface | Supplied under | Notes |
|---|---|---|
| RA / DEC axis housings, dovetail saddle | BP-01 (6061-T6 machining) | The bearing **outer** races seat in the BP-01 housing bores (Ø68 H7 / Ø55 H7); the BP-02 journals carry the **inner** races. |
| Concrete pier, top plate, mount adapter | BP-03 (pier & foundation) | Not a turned-part interface. |
| Roll-off roof steelwork | BP-04 | Not a turned-part interface. |
| Harmonic drives, angular-contact bearings, on-axis encoders, counterweights, fasteners | BP-05 (COTS) | See §4 interface list. |

---

## 2. Data package the shop receives (per MIL-STD-31000A)

| Item | Format / standard | Role |
|---|---|---|
| 3-D solid master | **STEP ISO 10303 AP242** | **CNC authority** — governs as-modelled geometry. |
| Control drawings NW-TP-001 / -002 / -003 | **PDF** (drawing practices per ASME Y14.100; drawing types Y14.24; sheet & title block Y14.1) | Envelope + title block + key dimensions & features; bid control drawing. |
| `SOW.md` | Markdown | Per-part turning spec: journals to ISO 286 fits, CSF registers, concentricity/TIR, passivation, certs. |
| `acceptance.md` | Markdown | Dimensional acceptance of the journal fits + concentricity/run-out + passivation verification; FAI. |
| `cut_list.csv` (rows for NW-TP-001/002/003) | CSV/XLSX | Stock size, cut allowance, stock mass. |

**Order of precedence.** The **STEP AP242 solid governs geometry**; the drawing + SOW govern
tolerances, notes, finish, and material; where geometry and the tolerance package disagree, the **SOW
controls** and the bidder shall raise an RFI before cutting metal. All GD&T is interpreted per
**ASME Y14.5-2018**; general tolerances per **ISO 2768-mK**; fits per **ISO 286**; surface texture per
**ASME Y14.36 / ASME B46.1**.

---

## 3. Line-item summary (source: `partspec.parts_for('BP-02')` + `cut_list.csv`)

| Part no. | Name | Stock (round bar) | Qty | Stock mass | Finish | Drawing | cut_list row |
|---|---|---|---:|---:|---|---|---|
| **NW-TP-001** | Counterweight shaft **(OPTIONAL — see §6)** | Ø31.75 mm [1.250 in] × 457.2 mm [18.000 in] | 1 | 2.90 kg | Passivate ASTM A967 | NW-TP-001 | row 5 |
| **NW-TP-002** | RA drive spindle / drawbar adapter | Ø88.9 mm [3.500 in] × 101.6 mm [4.000 in] | 1 | 5.05 kg | Passivate ASTM A967 | NW-TP-002 | row 6 |
| **NW-TP-003** | DEC drive spindle / saddle stub | Ø76.2 mm [3.000 in] × 88.9 mm [3.500 in] | 1 | 3.24 kg | Passivate ASTM A967 | NW-TP-003 | row 7 |

Stock mass is the **quantity ordered** (stock volume × 303-SS density 8000 kg/m³), not finished net
mass. Cut allowance is 3.0 mm on stock. Material for all three: **303 stainless per ASTM A582**.

> The NW-TP-001 stock diameter is Ø31.75 mm (= 1.250 in exactly); the generated control sheet and
> `cut_list.csv` display the mm value rounded to **Ø31.8 mm** — the same diameter.

---

## 4. Cross-package interfaces the shop must preserve

The bearing-race **journals** and the harmonic-drive **registers** are mating features to other
packages. The shop turns the BP-02 side; the fits and concentricity must be held so the mating
COTS/housing parts assemble and preload correctly:

| BP-02 feature | Nominal | Fit / carries | Mates to |
|---|---|---|---|
| NW-TP-002 bearing journal | Ø **40.0 mm [1.575 in]** | **j6** (ISO 286) — inner race of 7008 DB pair | NW-CO-003 (bore 40) → seats in NW-MH-001 bore Ø68 H7 |
| NW-TP-002 CSF-32 register | Ø **80.0 mm [3.150 in]** | locating fit to CSF-32 output | NW-CO-001 (bore 80) → drive register in NW-MH-001 |
| NW-TP-002 bolt pattern | **8 × M4 on Ø104 PCD** | bolts spindle to CSF-32 output flange | matches NW-MH-001 flange PCD (BP-01) |
| NW-TP-003 bearing journal | Ø **30.0 mm [1.181 in]** | **j6** (ISO 286) — inner race of 7006 DB pair | NW-CO-004 (bore 30) → seats in NW-MH-002 bore Ø55 H7 |
| NW-TP-003 CSF-25 register | Ø **64.0 mm [2.520 in]** | locating fit to CSF-25 output | NW-CO-002 (bore 64) → drive register in NW-MH-002 |
| NW-TP-003 bolt pattern | **8 × M4 on Ø83 PCD** | bolts spindle to CSF-25 output flange | matches NW-MH-002 flange PCD (BP-01) |
| NW-TP-001 stud / safety-stop | **M12** stud (× 40) + M12 safety-stop | carries the counterweight stack | NW-CO-009 counterweights (OPTIONAL) |

> **Remediation context.** The journals carry the inner races of **angular-contact 7008 (RA) / 7006
> (DEC)** pairs in a **back-to-back (DB), preloaded** arrangement — the proven remediation of the
> deep-groove 6008/6006 baseline. The stiffness/deflection proof showed the two deep-groove pairs
> contributing **14.21″ (RA, 6008 @ 76.2 mm span) + 28.43″ (DEC, 6006 @ 63.5 mm span) = 42.64″ of the
> 43.52″ static pointing deflection — ~98% of the 5″-target FAIL**. Because **moment stiffness** (not
> load rating) governs, the **journal fit, journal-shoulder squareness, and journal-to-register
> concentricity** are the stiffness-critical turned features (see `SOW.md` §5 and MECHANICAL_DESIGN.md
> §9; trade study item 8).

---

## 5. Bidder deliverables

1. Finished, passivated parts NW-TP-002 / -003 (qty 1 each), and NW-TP-001 **only if the
   counterweighted variant is bid** (see §6).
2. **Material certification / CoC** for the 303 SS bar (ASTM A582), with heat/lot traceability and
   chemistry (incl. sulphur — relevant to passivation, §6 / `SOW.md` §6).
3. **Passivation certification** — ASTM A967, method and acceptance test used.
4. **First-Article Inspection (FAI) report** per `acceptance.md`, including the journal-diameter
   measurements, journal-to-register concentricity / TIR, and thread verification.
5. RFI / nonconformance log for any ASSUMED value the shop needed resolved.

---

## 6. ASSUMED design-intent — bidder / PE to confirm (NOT final)

The following are carried as **ASSUMED design-intent** in the parts registry and must **not** be
treated as released dimensions. The bidder/PE shall confirm before production:

- **Bearing-race journal fit class.** The race journals are shown at **j6** (Ø40 on NW-TP-002, Ø30 on
  NW-TP-003) while the drawing's general note reads **"journal diameters h6."** Because the shaft
  (inner ring) **rotates relative to the gravity load**, bearing-maker practice would call for a light
  transition/interference fit (j6/k5/k6) rather than a clearance h6. The **exact grade (j6 vs h6 vs
  k6) and the resulting preload are a PE call** — bidder/PE to confirm.
- **Spindle body diameters** — NW-TP-002 Ø88.9 mm [3.500 in] and NW-TP-003 Ø76.2 mm [3.000 in] are
  **ASSUMED** (registry provenance: "Body dia ASSUMED"); they set only the stock size and the flange
  OD, not a mating fit.
- **Bolt patterns (8 × M4 on Ø104 / Ø83 PCD)** — DERIVED to match the BP-01 housing flange PCDs, which
  are themselves ASSUMED design-intent; confirm against the released CSF output-flange pattern.
- **CSF register fit & form** — whether the Ø80 / Ø64 register is an OD pilot or a bore, and its fit
  class to the harmonic-drive output (H7/h6 locating assumed) — ASSUMED, bidder/PE to confirm against
  the CSF-32 / CSF-25 datasheet.
- **"Drawbar adapter" thread on NW-TP-002** — the drawtube/drawbar thread implied by the part name is
  not dimensioned in the repo — ASSUMED design-intent.
- **Journal-shoulder axial location & squareness / preload land** — the shoulder that sets DB preload
  and its perpendicularity to the journal axis — ASSUMED, PE to set.
- **Passivation method & acceptance test** — ASTM A967 nitric vs citric, and the verification test
  (water-immersion / high-humidity / salt-spray / copper-sulphate) — ASSUMED; note 303 is a
  **free-machining, high-sulphur** grade that passivates less readily than 304 (`SOW.md` §6).
- **Bearing-journal surface finish** — part-level Ra 0.8 µm is on the sheet; bearing-race seats may
  need **Ra ≤ 0.4 µm** — ASSUMED, bidder/PE to confirm.
- **NW-TP-001 inclusion** — the selected **counterweight-FREE GEM** (torque proof, SF 2.5/2.6) omits
  the counterweight shaft entirely; NW-TP-001 is **OPTIONAL** and bid only for the counterweighted
  variant.

---

## 7. References

- Parts registry: `design/mechanical/tender/gen/partspec.py` → `parts_for('BP-02')` (single source of truth).
- BOM / cut list: `design/mechanical/tender/bom/{master_bom,cut_list}.csv`.
- Control drawings: `design/mechanical/tender/drawings/NW-TP-00{1,2,3}.svg`.
- Design basis: `design/mechanical/MECHANICAL_DESIGN.md` §9 (selected config + remediations; bearings
  7008/7006 fix); `design/mechanical/tradestudy/SECTION.md` (selection rationale, item 8 bearing fix).
- Master dossier: `packages/BP-00_master_dossier/` (ITB, general SOW, standards & drawing registers).
- Standards register: MIL-STD-31000A, ASME Y14.5-2018 / Y14.100 / Y14.24 / Y14.1 / Y14.36, ASME B46.1,
  ISO 286, ISO 2768, ASTM A582 (303 SS), ASTM A967 (passivation).
