# BP-05 / NW-CO-014 — Consolidated Fastener Schedule (SHCS + Anchors)

> **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**

| Field | Value |
|---|---|
| Part | NW-CO-014 — Fastener schedule (consolidated buy across BP-01…BP-04) |
| Governing specs | **ASTM A574** (alloy-steel socket-head cap screws), **ASTM F1554 Gr36** (anchor bolts), **ASTM A123** (galvanize, anchors) |
| Fits | ISO 286 (threaded fits), ISO 2768 (general) |
| Issue date / Rev | 2026-08-06 / A |

This schedule consolidates the **threaded fasteners** implied by the mating interfaces in the parts
registry (`gen/partspec.py`, `key_dims_mm`) into a single buy. The **fastener grades are ASSUMED
design-intent**; **thread sizes are derived from the fixed interfaces** (SOURCED where a `key_dims`
entry names them); and **lengths, quantities, and torque are ASSUMED — bidder/PE to confirm** against
the as-built grip lengths and the governing structural loads. **Weld sizes and any structural anchor
sizing are PE items** and are NOT fixed here.

Dual units throughout: mm primary, inch in brackets.

---

## 1. Socket-head cap screws — ASTM A574 (alloy steel, high-strength)

| Thread | Ø | Where used (interface) | Fixed by | Qty* | Length* | Status |
|---|---|---|---:|---:|---:|---|
| **M4** | Ø4 mm [0.157 in] | RA spindle → CSF-32 output flange, **8 × M4 on Ø104 mm [4.094 in] PCD** | NW-TP-002 / NW-MH-001 (SOURCED pattern) | 8 | ASSUMED | Core |
| **M4** | Ø4 mm [0.157 in] | DEC spindle → CSF-25 output flange, **8 × M4 on Ø83 mm [3.268 in] PCD** | NW-TP-003 / NW-MH-002 (SOURCED pattern) | 8 | ASSUMED | Core |
| **M6** | Ø6 mm [0.236 in] | Pier adapter → RA housing, **4 × M6** (also RA housing corner holes ×4) | NW-PF-003 → NW-MH-001 (SOURCED pattern) | 4 | ASSUMED | Core |
| **M8** | Ø8 mm [0.315 in] | DEC saddle clamp bar, **2 × M8** clamp screws | NW-MH-003 / NW-MH-002 (SOURCED pattern) | 2 | ASSUMED | Core |
| **M12** | Ø12 mm [0.472 in] | Counterweight shaft **stud end M12 × 40** + **M12** safety-stop | NW-TP-001 (SOURCED) | 2 | 40 mm [1.575 in] stud | **OPTIONAL** (CW-free build omits) |
| **M16** | Ø16 mm [0.630 in] | V-groove wheel **axles**, wheel-bracket bores (8 wheels) | NW-RR-004 (ASSUMED) | 8 | ASSUMED | Core *(axle/shoulder bolt — confirm type)* |

\* **Quantities are the interface pattern counts; add make-up/spares. Lengths are ASSUMED** — set from
the as-built grip (housing wall + flange stack + thread engagement) and confirm.

**SHCS notes.**
- **Grade.** ASTM A574 (alloy steel, ~property class 12.9 equivalent) is the **ASSUMED** grade per the
  standards register. **Galvanic caution (ASSUMED, confirm):** several joints land in **Type III
  hardcoat-anodized 6061-T6** (BP-01) and **passivated 303 SS** (BP-02); at those aluminium/stainless
  interfaces the PE may elect **stainless SHCS to ISO 3506 A2-70 / A4-70** in lieu of A574 to avoid
  galvanic coupling, accepting the lower proof load. Confirm per joint.
- **Torque / preload.** ASSUMED — set per fastener grade and joint (lubricated vs dry), bidder/PE to
  specify. The M4 drive-flange screws are the precision-critical joints (they locate the strain-wave
  output to the axis) — torque to a controlled value with thread-locker as required.
- **Finish.** Plain/black-oxide A574 for interior joints; where exposed to weather use stainless or a
  suitably plated screw — confirm.

---

## 2. Anchor bolts — ASTM F1554 Gr36 (galvanized per ASTM A123)

| Group | Ø | Embedment / projection | Where used | Fixed by | Qty | Status |
|---|---|---|---|---|---:|---|
| **Pier anchor set** | Ø0.75 in [19.05 mm] | Embedment 304.8 mm [12.000 in]; projection 50.0 mm [1.969 in] | Cast into pier, carries the top plate | **NW-PF-004 (BP-03)** — cast via template | 4 | Core *(BP-03 buy line)* |
| **Wind hold-down anchors** | Ø0.75 in [19.05 mm] | ASSUMED (PE to size) | Clamp roof/enclosure against **9.2 kN survival uplift** | **NW-RR-006 (BP-04)** — 4× hold-down brackets | 4 | **REMEDIATION** *(SF 3.9; each ≥2 klbf [≈8.9 kN])* |

**Anchor notes.**
- **The pier anchor set (4×) is procured under BP-03 as line NW-PF-004** and cast into the pier via a
  setting template; it is repeated here so the F1554 buy can be consolidated. The **wind hold-down
  anchors (4×)** serve the **enclosure/building foundation** (the pier is structurally isolated) and
  belong to the BP-04 hold-down brackets NW-RR-006 (the **5th** proof-out remediation).
- **PE GATE.** Final anchor **diameter, grade, embedment, edge distance, and count are PE-sized per
  ACI 318 Ch.17** for the governing wind/seismic uplift (bounding roof uplift ≈9.2 kN; each hold-down
  ≥2 klbf gives SF 3.9). The Ø0.75 in F1554 Gr36 values here are **ASSUMED design-intent — PE to
  confirm and stamp** (see BP-03 README §0, the PE-STAMP gate).
- **Finish.** Hot-dip galvanize per **ASTM A123**; supply mill cert / CoC + galvanize coating record
  and the anchor proof/pull test per the BP-03 acceptance plan.

---

## 3. Not covered here (flagged)

- **Weld sizes / NDE** (BP-03 top plate, BP-04 roof frame, rails, brackets) — **ASSUMED design-intent;
  bidder/PE to confirm** per **AWS D1.1** (steel) / **AWS D1.2** (aluminium), symbols per **AWS A2.4**,
  with WPS/PQR welder qualification. Not a fastener buy.
- **Roofing panel fasteners / closures** (NW-CO-012) — supplied with the roofing system; type/spacing
  ASSUMED, confirm to the ASCE 7 snow/wind case.
- **Rail-to-pier / rail-to-building bolting** (NW-RR-003) — structural connection; PE to detail.
- **Leveling nuts, washers, grout, thread-locker** — ASSUMED consumables; bidder to include.

---

## 4. Consolidated buy summary

| Spec | Sizes | Total pieces (interface count)* |
|---|---|---:|
| ASTM A574 SHCS | M4, M6, M8, (M12 optional), M16 | 8 + 8 + 4 + 2 + (2) + 8 = **32** (+ M12 ×2 optional) |
| ASTM F1554 Gr36 anchors, galv. A123 | Ø0.75 in [19.05 mm] | **8** (4 pier via NW-PF-004 + 4 hold-down via NW-RR-006) |

\* **Interface counts only — add make-up, spares, and stack washers/nuts.** All lengths, torque, final
grade selection (A574 vs stainless at galvanic joints), and structural anchor sizing are **ASSUMED
design-intent — bidder/PE to confirm.**
