# BP-01 — Dimensional Acceptance Plan: Mount Head Machining

> **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**

| Field | Value |
|---|---|
| Package | BP-01 — Mount head machining |
| Parts | NW-MH-001, NW-MH-002, NW-MH-003 |
| Method | CMM dimensional acceptance of the **H7 bearing-seat bores** + **flange flatness**; profilometer for Ra |
| Issue date / rev | 2026-08-06 / A |

**Scope.** This plan defines the inspection method and accept/reject criteria for BP-01. Because each
part has quantity 1, the **First-Article Inspection (FAI) *is* the production acceptance**. The H7
bearing seats and the flange flatness are the **critical characteristics** and receive **100% CMM
verification**; general dimensions are verified to **ISO 2768-mK** on the FAI. All limits are dual-unit
and derived from `partspec` / the NW-MH control drawings — nothing invented.

**Standards.** ASME Y14.5-2018 (datum alignment / GD&T interpretation); ISO 286 (H7 limits); ISO 2768
(general tolerance); ASME B46.1 (surface texture measurement); ISO 1 (20 °C reference temperature).

---

## 1. Inspection method

1. **CMM** for all bores, flatness, and located hole patterns. Datum alignment shall follow the part's
   datum reference frame in `SOW.md` (Datum A flange face, Datum B bore axis, Datum C register/saddle).
2. **Metrology environment:** temperature-controlled at **20 °C** per ISO 1; parts thermally soaked
   before measurement (**ASSUMED soak time — bidder to state**).
3. **Measurement uncertainty:** CMM + fixturing uncertainty shall be **≤ 10% of the tolerance band**
   for the H7 bores (gauge R&R / MSA evidence on request) — **ASSUMED acceptance gate, bidder/PE to
   confirm**.
4. **Bore evaluation:** each H7 seat probed with **≥ 8 points per circle at 3 axial depths**; report
   least-squares diameter, roundness, and cylindricity.
5. **Surface finish:** profilometer per ASME B46.1 on bore walls and flange faces.
6. **State of measurement:** the H7 bores are measured **as delivered (post-mask / post-anodize)** —
   see `SOW.md` §1.6/§6.

---

## 2. Acceptance criteria — NW-MH-001 (RA housing)

| Characteristic | Nominal (mm [in]) | Accept limits | Method | Class |
|---|---|---|---|---|
| Bearing seat bore Ø68 **H7** | Ø68.000 [2.677] | **Ø68.000 – 68.030 mm** (+0.030/0) | CMM, ≥8 pts × 3 depths | **Critical — 100%** |
| Bearing seat roundness / cylindricity | — | per PE GD&T *(value ASSUMED)* | CMM | Critical |
| Bore-to-flange perpendicularity | — | per PE GD&T *(ASSUMED)* | CMM (B to A) | Critical |
| Two-seat coaxiality over 76.2 mm [3.000 in] span | — | per PE GD&T *(ASSUMED)* | CMM | Critical |
| Flange face flatness | — | **≤ 0.05 mm [0.0020 in]** | CMM plane fit | Critical — 100% |
| Drive register bore Ø80 (CSF-32) | Ø80.0 [3.150] | H8 pilot *(ASSUMED)* | CMM | Major |
| Flange bolt circle Ø104, 8 holes | Ø104.0 [4.094] | position *(ASSUMED)* | CMM | Major |
| Corner holes 4 × M6 | — | ISO 2768-mK | thread gauge | Minor |
| Bore surface finish | — | **Ra ≤ 0.8 µm [32 µin]** *(ASSUMED)* | profilometer | Major |
| General surface finish | — | **Ra 1.6 µm [63 µin]** | profilometer | Minor |
| Envelope 203.2 × 203.2 × 76.2 | [8.000×8.000×3.000] | ISO 2768-mK | calipers/CMM | Minor |

## 3. Acceptance criteria — NW-MH-002 (DEC housing + saddle)

| Characteristic | Nominal (mm [in]) | Accept limits | Method | Class |
|---|---|---|---|---|
| Bearing seat bore Ø55 **H7** | Ø55.000 [2.165] | **Ø55.000 – 55.030 mm** (+0.030/0) | CMM, ≥8 pts × 3 depths | **Critical — 100%** |
| Bearing seat roundness / cylindricity | — | per PE GD&T *(ASSUMED)* | CMM | Critical |
| Bore-to-flange perpendicularity | — | per PE GD&T *(ASSUMED)* | CMM (B to A) | Critical |
| Two-seat coaxiality over 63.5 mm [2.500 in] span | — | per PE GD&T *(ASSUMED)* | CMM | Critical |
| Flange face flatness | — | **≤ 0.05 mm [0.0020 in]** | CMM plane fit | Critical — 100% |
| Drive register bore Ø64 (CSF-25) | Ø64.0 [2.520] | H8 pilot *(ASSUMED)* | CMM | Major |
| Flange bolt circle Ø83 | Ø83.0 [3.268] | position *(ASSUMED)* | CMM | Major |
| Losmandy-D saddle width | 76.2 [3.000] | ISO 2768-mK *(profile ASSUMED)* | CMM / profile gauge | Major |
| Dovetail angle | 15° | ± *(ASSUMED)* | angle gauge / CMM | Major |
| Bore surface finish | — | **Ra ≤ 0.8 µm** *(ASSUMED)* | profilometer | Major |
| General surface finish | — | **Ra 1.6 µm [63 µin]** | profilometer | Minor |
| Envelope 152.4 × 152.4 × 63.5 | [6.000×6.000×2.500] | ISO 2768-mK | calipers/CMM | Minor |

## 4. Acceptance criteria — NW-MH-003 (saddle clamp bar)

| Characteristic | Nominal (mm [in]) | Accept limits | Method | Class |
|---|---|---|---|---|
| Length | 101.6 [4.000] | ISO 2768-mK | calipers/CMM | Minor |
| Width | 76.2 [3.000] | ISO 2768-mK | calipers/CMM | Minor |
| Thickness | 25.4 [1.000] | ISO 2768-mK | calipers/CMM | Minor |
| Clamp screws | 2 × M8 | ISO 2768-mK | thread gauge | Minor |
| Dovetail bevel | 15° (match NW-MH-002) | ± *(ASSUMED)* | angle gauge | Major |
| Surface finish | — | **Ra 3.2 µm [125 µin]** | profilometer | Minor |

> The whole part is **ASSUMED design-intent** (Losmandy-D clamp not dimensioned in the repo); acceptance
> limits above are provisional pending PE release.

---

## 5. Sampling

- **Critical characteristics** (H7 bores, flange flatness, and the stiffness-critical coaxiality /
  perpendicularity callouts): **100%** — each part is qty 1, so FAI = production acceptance.
- **Major / Minor characteristics:** verified on the FAI to ISO 2768-mK.
- **Post-anodize re-check:** the H7 bores are re-verified after masking/anodize (per `SOW.md` §6).

## 6. Documentation & sign-off

The bidder shall deliver, per part:

1. **FAI report** — every characteristic in §2–§4 with measured value vs. limit and pass/fail.
2. **CMM raw output** — probe data + datum alignment record (Y14.5 frame).
3. **Material certificate** (ASTM B209 / AMS-QQ-A-250/11) with heat/lot traceability.
4. **Anodize certificate** (MIL-A-8625F Type III) with coating-thickness record.
5. **Nonconformance / RFI dispositions** for any ASSUMED value or out-of-tolerance condition.

| Role | Name | Signature | Date |
|---|---|---|---|
| Bidder QA | | | |
| Owner / PE review | | | |

---

## 7. ASSUMED-value register (do NOT treat as final)

The following acceptance values are **ASSUMED design-intent — bidder/PE to confirm** before they can
be applied as pass/fail gates:

| # | ASSUMED value | Part(s) |
|---|---|---|
| 1 | All GD&T coaxiality / perpendicularity / position tolerances | NW-MH-001, -002 |
| 2 | Bearing-seat surface finish Ra ≤ 0.8 µm | NW-MH-001, -002 |
| 3 | Drive-register fit class (H8 pilot) | NW-MH-001, -002 |
| 4 | Flange PCD & pattern (Ø104/8-hole, Ø83) | NW-MH-001, -002 |
| 5 | Losmandy-D saddle profile & 15° dovetail | NW-MH-002 |
| 6 | Entire saddle clamp bar geometry | NW-MH-003 |
| 7 | CMM uncertainty gate (≤10% of tol band), soak time | all |
| 8 | Post-anodize masking / re-check approach | all |
