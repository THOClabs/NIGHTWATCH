# BP-02 — Statement of Work: Precision Turned Parts (303 SS)

> **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**

| Field | Value |
|---|---|
| Package | BP-02 — Precision turned parts |
| Parts | NW-TP-001 (counterweight shaft, OPTIONAL), NW-TP-002 (RA drive spindle), NW-TP-003 (DEC drive spindle) |
| Process | CNC / manual turning (single-point) + light milling (bolt patterns, flats) |
| Material | 303 stainless steel per **ASTM A582** |
| Finish | **Passivate per ASTM A967** (nitric or citric) |
| Issue date / rev | 2026-08-06 / A |

**Purpose.** This SOW specifies the turning, tolerancing, finishing, and certification requirements for
the three turned parts. It is read with the STEP ISO 10303 AP242 solid master (CNC authority), the
NW-TP control drawings (PDF), and `acceptance.md`. All dimensions are dual-unit, **mm primary, inch in
brackets**, drawn from the parts registry (`partspec.parts_for('BP-02')`) and `cut_list.csv` — no
dimension herein is invented.

**Standards applied.** MIL-STD-31000A (TDP); **ASME Y14.5-2018** (GD&T); ASME Y14.100 (drawing
practices), Y14.24 (drawing types), Y14.1 (sheet/title block); **ASME Y14.36 & ASME B46.1** (surface
texture); **ISO 286** (j6 / h6 / H7 fits); **ISO 2768-mK** (general tolerances); **ASTM A582** (303
free-machining stainless bar); **ASTM A967** (passivation of stainless).

---

## 1. General requirements (all parts)

1. **Material & certification.** 303 stainless bar per **ASTM A582** (free-machining austenitic).
   Furnish mill certification and Certificate of Conformance with **heat/lot traceability** and full
   **chemistry** (the sulphur content governs passivation, §6). Mark each part with part number and
   revision per ASME Y14.100.
2. **General tolerance.** **ISO 2768-mK** (medium, fine machining class) on all dimensions not
   otherwise toleranced. Break sharp edges 0.3–0.5 mm [0.012–0.020 in]; deburr all threads and
   cross-holes; no burrs into bearing seats.
3. **Journal fits.** Bearing-race journals and drive registers to **ISO 286** — see per-part tables.
   The general note is **journal diameters h6**; the two **bearing-race journals are shown at j6** (a
   transition fit to retain the rotating inner ring). See §5 and the ASSUMED-value register (§8).
4. **Concentricity / run-out.** The turned features share one datum axis: **journal-to-register (and
   journal-to-journal) run-out shall not exceed 0.02 mm [0.0008 in] TIR** (registry `_TOL_TURN`
   SOURCED value). Turn the mating diameters **in one setup / between centres** wherever practical to
   hold it. The datum-axis assignment (which feature is Datum A) is **ASSUMED — bidder/PE to confirm**.
5. **GD&T.** Interpret all geometric callouts per **ASME Y14.5-2018**. Surface-texture symbols per
   **ASME Y14.36**, values per **ASME B46.1**.
6. **Stress / distortion.** 303 work-hardens and can move on the last cut; **finish the bearing
   journals last, in a light final pass**, to hold the j6/h6 band and the 0.02 TIR (**ASSUMED best
   practice — bidder to propose**).
7. **Surface finish.** Part-level **Ra 0.8 µm [32 µin]** per the control drawing. Bearing-race journals
   are typically held finer at **Ra ≤ 0.4 µm [16 µin]** (**ASSUMED design-intent — bidder/PE to
   confirm**; see `acceptance.md`).
8. **Finish sequence.** Turn/mill complete, deburr, then **passivate per ASTM A967** (§6). No plating.

---

## 2. NW-TP-002 — RA drive spindle / drawbar adapter

**Drawing:** NW-TP-002 (rev A). **Stock:** 303-SS round bar **Ø88.9 mm [3.500 in] × 101.6 mm
[4.000 in]**, cut allowance 3.0 mm, stock mass 5.05 kg (`cut_list.csv` row 6). Process: **CNC turn +
mill**.

**Function.** Couples the **CSF-32-100** harmonic-drive output to the RA axis and **carries the inner
race of the 7008 angular-contact pair**.

**Datum reference frame (ASME Y14.5-2018, ASSUMED — PE to confirm):**
- **Datum A** — bearing-journal axis (the axis of rotation, Ø40 j6).
- **Datum B** — CSF-32 register face (axial seat against the drive output).
- **Datum C** — a designated bolt hole, for clocking the 8 × M4 pattern.

**Critical features:**

| Feature | Nominal (mm [in]) | Fit / tolerance | ISO 286 limits (representative) | Ra |
|---|---|---|---|---|
| Bearing journal (7008 inner race) | Ø **40.0** [1.575] | **j6** (ASSUMED grade) per ISO 286 | Ø39.995 – 40.011 (j6) *(h6 alt: 39.984 – 40.000)* | ≤0.4 µm (ASSUMED) |
| Journal-to-register concentricity | — | **0.02 mm TIR** (SOURCED) | run-out to Datum A/B | — |
| Journal-shoulder squareness / preload land | — | ⟂ to Datum A *(value ASSUMED — PE)* | — | — |
| CSF-32 wave-gen / output register | Ø **80.0** [3.150] | locating fit (H7/h6 ASSUMED) | per CSF-32 datasheet | 0.8 µm |
| Body dia (flange OD) | Ø **88.9** [3.500] | ISO 2768-mK *(ASSUMED)* | — | 0.8 µm |
| Length | **101.6** [4.000] | ISO 2768-mK | — | 0.8 µm |
| Bolt pattern | **8 × M4 on Ø104 PCD** | position *(ASSUMED)* | matches NW-MH-001 flange | — |
| Drawbar / drawtube thread | *(not dimensioned)* | **ASSUMED design-intent** | — | — |

**Provenance / flags.** Journal Ø40 = **7008 bore (remediation)**; CSF-32 register Ø80 =
**P.RA_DRIVE.bore_m (SOURCED)**; **body dia Ø88.9 ASSUMED**; bolt pattern DERIVED to the NW-MH-001
flange PCD (itself ASSUMED). The **journal fit grade (j6 vs h6)** and the **drawbar thread** are
ASSUMED — bidder/PE to confirm.

**Interfaces:** journal → NW-CO-003 (7008 DB pair, bore 40) seating in NW-MH-001 bore Ø68 H7; register
→ NW-CO-001 (CSF-32, bore 80); bolt pattern → NW-MH-001 flange.

---

## 3. NW-TP-003 — DEC drive spindle / saddle stub

**Drawing:** NW-TP-003 (rev A). **Stock:** 303-SS round bar **Ø76.2 mm [3.000 in] × 88.9 mm
[3.500 in]**, cut allowance 3.0 mm, stock mass 3.24 kg (`cut_list.csv` row 7). Process: **CNC turn +
mill**.

**Function.** Couples the **CSF-25-80** harmonic-drive output to the DEC axis / saddle side and
**carries the inner race of the 7006 angular-contact pair**.

**Datum reference frame (ASME Y14.5-2018, ASSUMED — PE to confirm):**
- **Datum A** — bearing-journal axis (DEC axis of rotation, Ø30 j6).
- **Datum B** — CSF-25 register face.
- **Datum C** — a designated bolt hole for clocking the 8 × M4 pattern.

**Critical features:**

| Feature | Nominal (mm [in]) | Fit / tolerance | ISO 286 limits (representative) | Ra |
|---|---|---|---|---|
| Bearing journal (7006 inner race) | Ø **30.0** [1.181] | **j6** (ASSUMED grade) per ISO 286 | Ø29.996 – 30.009 (j6) *(h6 alt: 29.987 – 30.000)* | ≤0.4 µm (ASSUMED) |
| Journal-to-register concentricity | — | **0.02 mm TIR** (SOURCED) | run-out to Datum A/B | — |
| Journal-shoulder squareness / preload land | — | ⟂ to Datum A *(value ASSUMED — PE)* | — | — |
| CSF-25 wave-gen / output register | Ø **64.0** [2.520] | locating fit (H7/h6 ASSUMED) | per CSF-25 datasheet | 0.8 µm |
| Body dia (flange OD) | Ø **76.2** [3.000] | ISO 2768-mK *(ASSUMED)* | — | 0.8 µm |
| Length | **88.9** [3.500] | ISO 2768-mK | — | 0.8 µm |
| Bolt pattern | **8 × M4 on Ø83 PCD** | position *(ASSUMED)* | matches NW-MH-002 flange | — |

**Provenance / flags.** Journal Ø30 = **7006 bore (remediation)**; CSF-25 register Ø64 =
**P.DEC_DRIVE.bore_m (SOURCED)**; **body dia Ø76.2 ASSUMED**; bolt pattern DERIVED to the NW-MH-002
flange PCD (itself ASSUMED). The **journal fit grade (j6 vs h6)** is ASSUMED — bidder/PE to confirm.

**Interfaces:** journal → NW-CO-004 (7006 DB pair, bore 30) seating in NW-MH-002 bore Ø55 H7; register
→ NW-CO-002 (CSF-25, bore 64); bolt pattern → NW-MH-002 flange.

---

## 4. NW-TP-001 — Counterweight shaft (OPTIONAL)

**Drawing:** NW-TP-001 (rev A). **Stock:** 303-SS round bar **Ø31.75 mm [1.250 in] × 457.2 mm
[18.000 in]** (sheet displays Ø31.8 mm), cut allowance 3.0 mm, stock mass 2.90 kg (`cut_list.csv`
row 5). Process: **CNC turn**.

> **OPTIONAL PART.** The selected topology is the **counterweight-FREE GEM** (torque proof SF 2.5/2.6;
> deletes 15.4 kg + 29% RA inertia — MECHANICAL_DESIGN.md §9). NW-TP-001 (and its COTS counterweights
> NW-CO-009) are supplied **only if the counterweighted variant is bid**. Price it as a separately
> deletable line item.

**Datum reference frame:** Datum A = shaft OD axis.

| Feature | Nominal (mm [in]) | Tolerance | Ra |
|---|---|---|---|
| Shaft diameter | Ø **31.75** [1.250] | ISO 2768-mK | 0.8 µm |
| Length | **457.2** [18.000] | ISO 2768-mK | 0.8 µm |
| Stud end | **M12 × 40** | 6g thread (ISO 2768) | — |
| Safety-stop thread | **M12** | 6g thread | — |
| Root fillet | **R3.0** [0.118] | — | — |

**Provenance / flags.** Diameter/length = **P.COUNTERWEIGHTS (SOURCED)**; stud (M12 × 40), safety-stop
(M12), and root fillet (R3.0) are on the sheet. Thread class (6g) and the safety-stop feature detail
are **ASSUMED — bidder/PE to confirm**.

**Interfaces:** M12 stud → DEC-axis counterweight boss; carries NW-CO-009 counterweights (cast iron,
5 kg × 2 + 2.5 kg × 1). Safety-stop retains the weight stack against drop.

---

## 5. Bearing-journal callout block (stiffness remediation — grounding)

The two spindle journals (**Ø40 j6 on NW-TP-002, Ø30 j6 on NW-TP-003**) carry the inner races of the
**matched angular-contact pairs — 7008 (RA, bore 40 mm) and 7006 (DEC, bore 30 mm) in a back-to-back
(DB), preloaded arrangement** (NW-CO-003 / NW-CO-004, BP-05). This is the proven **remediation of the
deep-groove 6008/6006 baseline**: the stiffness/deflection proof attributed **14.21″ (RA 6008 pair,
76.2 mm span) + 28.43″ (DEC 6006 pair, 63.5 mm span) = 42.64″ of the 43.52″ static pointing deflection
(~98%) — the dominant term in the 5″-target FAIL** (MECHANICAL_DESIGN.md §9; trade study item 8).

Because **moment stiffness** — not load rating — governs, the turned controls that matter are:

- **Journal fit** to the inner race — a snug transition/interference (**j6 shown; grade ASSUMED, PE to
  set**) so the rotating inner ring does not creep or lose preload.
- **Journal-shoulder squareness** to the journal axis, and the **axial location** of the shoulder that
  sets the DB preload — **ASSUMED, PE to set**.
- **Journal-to-register / journal-to-journal concentricity ≤ 0.02 mm TIR** (SOURCED) and **Ra ≤ 0.4 µm**
  (ASSUMED) on the race seats — turn in one setup / between centres to hold it.
- **Preload method** (ground spacer/shim vs. clamped nut) — the housing (BP-01) and spindle shoulders
  together set it; **ASSUMED design-intent, bidder/PE to detail.**

---

## 6. Finishing — passivation

- **Passivate per ASTM A967** after all machining and deburring. Nitric or citric process acceptable;
  state the process on the certificate.
- **303 is a free-machining, high-sulphur grade**: the manganese-sulphide inclusions passivate less
  readily than 304/316 and can leave active sites. Use a process qualified for free-machining grades
  and **verify** by an ASTM A967 acceptance test (water-immersion / high-humidity / salt-spray /
  copper-sulphate) — the specific test is **ASSUMED, bidder/PE to confirm**.
- **Mask nothing that must stay dimensional** — passivation is not a coating and does not build
  thickness, so the j6/h6 journals are unaffected; still re-verify per `acceptance.md`.
- Furnish a **passivation certificate** stating process, solution, and the acceptance test used.

---

## 7. Submittals & deliverables

1. Finished, passivated parts: NW-TP-002, NW-TP-003 (qty 1 each); **NW-TP-001 only if bid**.
2. Material cert / CoC (ASTM A582) with heat/lot traceability and chemistry.
3. Passivation certificate (ASTM A967) with process + acceptance test.
4. First-Article Inspection report per `acceptance.md` (journal diameters, concentricity/TIR, threads).
5. RFI log resolving every ASSUMED value before production.

---

## 8. ASSUMED design-intent register (this SOW)

| Item | Part(s) | Status |
|---|---|---|
| Bearing-race journal fit grade (j6 shown vs h6 general note; k5/k6 alt for rotating inner ring) | NW-TP-002, -003 | ASSUMED — PE to set |
| Bearing-journal surface finish (Ra ≤ 0.4 µm) | NW-TP-002, -003 | ASSUMED — bidder/PE to confirm |
| Journal-shoulder squareness / axial preload land | NW-TP-002, -003 | ASSUMED — PE to set |
| Datum-axis assignment for the 0.02 TIR run-out | NW-TP-002, -003 | ASSUMED — bidder/PE to confirm |
| Spindle body diameters (Ø88.9 / Ø76.2) | NW-TP-002, -003 | ASSUMED design-intent |
| Bolt patterns (8 × M4 on Ø104 / Ø83 PCD) | NW-TP-002, -003 | DERIVED/ASSUMED — confirm vs CSF flange |
| CSF register form & fit class (OD pilot vs bore; H7/h6) | NW-TP-002, -003 | ASSUMED — confirm vs CSF datasheet |
| Drawbar / drawtube thread | NW-TP-002 | ASSUMED design-intent (not dimensioned) |
| Thread class (6g) & safety-stop detail | NW-TP-001 | ASSUMED — bidder/PE to confirm |
| Passivation method (nitric/citric) & acceptance test | all | ASSUMED — bidder/PE to confirm |
| NW-TP-001 inclusion (counterweight-free build omits it) | NW-TP-001 | OPTIONAL — bid separately deletable |
