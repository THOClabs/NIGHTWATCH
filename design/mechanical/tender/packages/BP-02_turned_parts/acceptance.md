# BP-02 — Dimensional Acceptance Plan: Precision Turned Parts

> **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**

| Field | Value |
|---|---|
| Package | BP-02 — Precision turned parts |
| Parts | NW-TP-001 (OPTIONAL), NW-TP-002, NW-TP-003 |
| Method | Dimensional acceptance of the **bearing-race journals** + **journal-to-register concentricity/run-out**; thread gauging; passivation verification |
| Issue date / rev | 2026-08-06 / A |

**Scope.** This plan defines the inspection method and accept/reject criteria for BP-02. Because each
part has quantity 1, the **First-Article Inspection (FAI) *is* the production acceptance**. The
**bearing-race journals** (Ø40 j6 / Ø30 j6), the **journal-to-register concentricity (0.02 mm TIR)**,
and the **harmonic-drive registers** (Ø80 / Ø64) are the **critical characteristics** and receive
**100% verification**; general dimensions are verified to **ISO 2768-mK** on the FAI. All limits are
dual-unit and derived from `partspec` / the NW-TP control drawings — nothing invented.

**Standards.** ASME Y14.5-2018 (datum alignment / GD&T interpretation); ISO 286 (j6 / h6 / H7 limits);
ISO 2768 (general tolerance & threads); ASME B46.1 (surface texture measurement); ASTM A967
(passivation verification); ISO 1 (20 °C reference temperature).

---

## 1. Inspection method

1. **Diameters.** Bearing journals and registers measured with **CMM or bench-centre + calibrated bore
   micrometer / air gauge**, ≥ 3 axial stations × ≥ 4 angular positions; report least-squares diameter,
   roundness, and taper.
2. **Concentricity / run-out.** Part supported **between centres (or in matched V-blocks)**; journal
   and register **total indicated run-out (TIR)** read with a dial/probe against the datum axis
   (`SOW.md` §4). Datum-axis assignment per the FAI datum frame (ASSUMED — see §7).
3. **Threads (NW-TP-001).** M12 stud and safety-stop verified with **go/no-go ring/plug gauges**
   (class 6g ASSUMED); root fillet R3.0 by radius gauge / optical comparator.
4. **Surface finish.** Profilometer per ASME B46.1 on journals, registers, and general OD.
5. **Metrology environment:** temperature-controlled at **20 °C** per ISO 1; parts thermally soaked
   before measurement (**ASSUMED soak time — bidder to state**).
6. **Measurement uncertainty:** CMM/gauge + fixturing uncertainty **≤ 10% of the tolerance band** for
   the j6 journals (gauge R&R / MSA evidence on request) — **ASSUMED acceptance gate, bidder/PE to
   confirm**.
7. **State of measurement:** passivation is not a coating and does not build thickness; journals are
   measured **as delivered (post-passivation)**.

---

## 2. Acceptance criteria — NW-TP-002 (RA drive spindle)

| Characteristic | Nominal (mm [in]) | Accept limits | Method | Class |
|---|---|---|---|---|
| Bearing journal Ø40 **j6** (7008 race) | Ø40.0 [1.575] | **Ø39.995 – 40.011 mm** (j6, ASSUMED grade) | CMM / air gauge | **Critical — 100%** |
| Journal-to-register concentricity | — | **≤ 0.02 mm [0.0008 in] TIR** | between centres, dial/probe | **Critical — 100%** |
| Journal roundness / taper | — | within the j6 band | CMM | Critical |
| Journal-shoulder squareness / preload land | — | per PE GD&T *(value ASSUMED)* | CMM | Critical |
| CSF-32 register Ø80 | Ø80.0 [3.150] | locating fit *(H7/h6 ASSUMED)* | CMM / micrometer | Major |
| Bolt pattern 8 × M4 on Ø104 PCD | Ø104.0 [4.094] | position *(ASSUMED)* | CMM | Major |
| Body dia Ø88.9 | Ø88.9 [3.500] | ISO 2768-mK *(ASSUMED)* | micrometer | Minor |
| Length | 101.6 [4.000] | ISO 2768-mK | calipers/CMM | Minor |
| Journal surface finish | — | **Ra ≤ 0.4 µm [16 µin]** *(ASSUMED)* | profilometer | Major |
| General surface finish | — | **Ra 0.8 µm [32 µin]** | profilometer | Minor |

## 3. Acceptance criteria — NW-TP-003 (DEC drive spindle)

| Characteristic | Nominal (mm [in]) | Accept limits | Method | Class |
|---|---|---|---|---|
| Bearing journal Ø30 **j6** (7006 race) | Ø30.0 [1.181] | **Ø29.996 – 30.009 mm** (j6, ASSUMED grade) | CMM / air gauge | **Critical — 100%** |
| Journal-to-register concentricity | — | **≤ 0.02 mm [0.0008 in] TIR** | between centres, dial/probe | **Critical — 100%** |
| Journal roundness / taper | — | within the j6 band | CMM | Critical |
| Journal-shoulder squareness / preload land | — | per PE GD&T *(value ASSUMED)* | CMM | Critical |
| CSF-25 register Ø64 | Ø64.0 [2.520] | locating fit *(H7/h6 ASSUMED)* | CMM / micrometer | Major |
| Bolt pattern 8 × M4 on Ø83 PCD | Ø83.0 [3.268] | position *(ASSUMED)* | CMM | Major |
| Body dia Ø76.2 | Ø76.2 [3.000] | ISO 2768-mK *(ASSUMED)* | micrometer | Minor |
| Length | 88.9 [3.500] | ISO 2768-mK | calipers/CMM | Minor |
| Journal surface finish | — | **Ra ≤ 0.4 µm [16 µin]** *(ASSUMED)* | profilometer | Major |
| General surface finish | — | **Ra 0.8 µm [32 µin]** | profilometer | Minor |

## 4. Acceptance criteria — NW-TP-001 (counterweight shaft, OPTIONAL)

> Inspect **only if the counterweighted variant is bid** (§ `SOW.md` §4). The selected build is
> counterweight-free.

| Characteristic | Nominal (mm [in]) | Accept limits | Method | Class |
|---|---|---|---|---|
| Shaft diameter | Ø31.75 [1.250] | ISO 2768-mK | micrometer | Minor |
| Length | 457.2 [18.000] | ISO 2768-mK | tape/CMM | Minor |
| Stud end thread | M12 × 40 | 6g go/no-go *(ASSUMED)* | ring gauge | Major |
| Safety-stop thread | M12 | 6g go/no-go *(ASSUMED)* | ring gauge | Major |
| Root fillet | R3.0 [0.118] | radius gauge | comparator | Minor |
| Surface finish | — | **Ra 0.8 µm [32 µin]** | profilometer | Minor |

---

## 5. Passivation verification (all parts)

| Characteristic | Requirement | Method | Class |
|---|---|---|---|
| Passivation | Per **ASTM A967** (nitric or citric) | certificate + acceptance test | **Critical — 100%** |
| Free-iron / passivity check | Pass the stated ASTM A967 test | water-immersion / high-humidity / salt-spray / copper-sulphate *(specific test ASSUMED — bidder/PE to confirm)* | Critical |

> **303 note.** Because 303 is a **free-machining, high-sulphur** grade, verify passivity with a test
> qualified for free-machining stainless; report the process (solution, concentration, time,
> temperature) and the acceptance-test result on the certificate (`SOW.md` §6).

---

## 6. Sampling & documentation

- **Critical characteristics** (j6 journals, journal-to-register concentricity, registers, passivation):
  **100%** — each part is qty 1, so FAI = production acceptance.
- **Major / Minor characteristics:** verified on the FAI to ISO 2768-mK.

The bidder shall deliver, per part:

1. **FAI report** — every characteristic in §2–§5 with measured value vs. limit and pass/fail.
2. **CMM / gauge raw output** — probe data + datum alignment record (Y14.5 frame) + run-out traces.
3. **Material certificate** (ASTM A582) with heat/lot traceability and chemistry.
4. **Passivation certificate** (ASTM A967) with process + acceptance-test result.
5. **Nonconformance / RFI dispositions** for any ASSUMED value or out-of-tolerance condition.

| Role | Name | Signature | Date |
|---|---|---|---|
| Bidder QA | | | |
| Owner / PE review | | | |

---

## 7. ASSUMED-value register (do NOT treat as final)

The following acceptance values are **ASSUMED design-intent — bidder/PE to confirm** before they can be
applied as pass/fail gates:

| # | ASSUMED value | Part(s) |
|---|---|---|
| 1 | Journal fit grade (j6 shown vs h6 general note; k5/k6 alt for rotating inner ring) | NW-TP-002, -003 |
| 2 | Bearing-journal surface finish Ra ≤ 0.4 µm | NW-TP-002, -003 |
| 3 | Journal-shoulder squareness / axial preload land | NW-TP-002, -003 |
| 4 | Datum-axis assignment for the 0.02 mm TIR run-out | NW-TP-002, -003 |
| 5 | CSF register fit class (H7/h6) and form (OD pilot vs bore) | NW-TP-002, -003 |
| 6 | Bolt-pattern position (8 × M4 on Ø104 / Ø83 PCD) | NW-TP-002, -003 |
| 7 | Spindle body diameters (Ø88.9 / Ø76.2) | NW-TP-002, -003 |
| 8 | Drawbar / drawtube thread | NW-TP-002 |
| 9 | Thread class (6g) & safety-stop detail | NW-TP-001 |
| 10 | Passivation method (nitric/citric) & specific acceptance test | all |
| 11 | CMM/gauge uncertainty gate (≤ 10% of tol band), soak time | all |
