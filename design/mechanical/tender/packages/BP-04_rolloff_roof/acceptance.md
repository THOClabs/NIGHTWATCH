# BP-04 — Acceptance & Inspection Plan: Roll-off Roof (Structural Steel + Rail/Drive)

> **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**

| Field | Value |
|---|---|
| Package | BP-04 — Roll-off roof ("disappearing turret") |
| Parts | NW-RR-001, -002, -003, -004, -005, -006 |
| Method | Weld VT/NDE (AWS D1.1) · frame & rail dimensional survey · drive-cycle + interlock test · hold-down proof-pull · roof-closed water test |
| Issue date / rev | 2026-08-06 / A |

**Scope.** This plan defines the inspection methods and accept/reject criteria for BP-04. Welds are
inspected per **AWS D1.1** (symbols per **AWS A2.4**); the rail run and frame are dimensionally
surveyed; the drive and its **wind + snow interlocks** are cycle-tested; the **mandatory 4× hold-downs**
are proof-pull-tested; and the closed roof is water-tested. All limits are dual-unit and derived from
`partspec` / the NW-RR control drawings and the design proofs — **nothing invented**. Because this is a
**structure**, the plan is executed under the **PE-approved ITP** and the PE's field hold-points.

**Standards.** AWS D1.1 (weld acceptance, WPS/PQR/WPQ) & AWS A2.4 (symbols); ASTM A123 (galvanize);
ASTM A500 Gr B / A36 (materials); ASTM F1554 Gr36 (anchors) & ACI 318 Ch.17 (anchorage); ASCE 7
(load basis); ISO 2768 (general tolerance); ASME Y14.5-2018 (bracket GD&T).

---

## 1. Weld visual & NDE acceptance (AWS D1.1)

1. **Qualification gate.** Before any acceptance, verify the **WPS + PQR** and **welder qualification
   (WPQ)** are on file per AWS D1.1; production welding by unqualified procedure/welder is rejectable.
2. **Visual (VT) — 100% of all welds** by an **AWS Certified Welding Inspector (CWI)** to the AWS D1.1
   visual acceptance criteria (statically-loaded, unless the PE classifies a joint cyclic): no cracks;
   full fusion; undersize, undercut, porosity, and profile within the D1.1 limits; weld sizes match the
   **as-built `weld_map.md`**.
3. **Surface NDE — critical joints.** **MT (magnetic-particle)** or **PT (dye-penetrant)** per the
   `weld_map.md` extents: **J3 (wheel brackets) 100%**, **J5 (hold-downs) 100%**, **J6 (rail splices)
   100% PT**, sampling elsewhere. **UT** on CJP groove welds (J5/J6) **if required by the PE**.
   *(NDE method + extent are ASSUMED — PE/CWI to confirm; see §8.)*
4. **Reject/repair.** Reweld and re-inspect per AWS D1.1; log every disposition.

| Weld group | Method | Extent | Accept criterion |
|---|---|---:|---|
| J1 frame corners | VT (+MT) | 100% VT / 25% MT | AWS D1.1 visual; no cracks; size per as-built |
| J2 purlin-to-frame | VT | 100% | AWS D1.1 visual |
| **J3 wheel brackets** | VT + **MT** | **100% / 100%** | AWS D1.1; no surface indications |
| J4 drive bracket | VT (+MT) | 100% / 25% | AWS D1.1 visual |
| **J5 hold-downs** | VT + **MT** (UT if CJP) | **100% / 100%** | AWS D1.1; **CRITICAL** — no indications |
| **J6 rail splices** | VT + **PT** (UT per PE) | **100% / 100%** | flush-ground running surface; no indications |
| J7 end stops / J8 rail supports / J9 gussets | VT | 100% | AWS D1.1 visual (J8 torque-check if bolted) |

---

## 2. Material & galvanize acceptance

| Characteristic | Requirement | Method | Class |
|---|---|---|---|
| HSS material | **ASTM A500 Gr B** mill cert, heat/lot traceable | certificate review | Critical |
| Plate / rail material | **ASTM A36** mill cert, heat/lot traceable | certificate review | Critical |
| Galvanize | **ASTM A123** coating mass/thickness | magnetic thickness gauge + cert | Major |
| Vent/drain holes | present on all closed HSS (ASSUMED locations) | visual | Major |
| Galv field-repair | bidder procedure (ASTM A780, supplementary) | visual + thickness | Major |

---

## 3. Frame & bracket dimensional acceptance

| Characteristic | Nominal (mm [in]) | Accept limit | Method | Class |
|---|---|---|---|---|
| Frame perimeter | 3000.0 [118.110] × 3000.0 [118.110] | ISO 2768 + frame-square | tape/total station | Major |
| Frame square | — | **≤ 3 mm/m** | diagonal check | **Critical** |
| Frame diagonal difference | — | **≤ 5 mm [0.197 in]** | cross-diagonal tape | **Critical** |
| Purlin spacing | 600.0 [23.622] o.c., ×5 | ISO 2768 | tape | Minor |
| Bracket plate envelope (NW-RR-004/-005/-006) | per §3 SOW | ISO 2768-mK | calipers | Minor |
| Bracket hole pattern | — | **≤ 0.25 mm [0.010 in]** | CMM / gauge | Major |

---

## 4. Rail alignment survey (NW-RR-003)

The rail run is the wheel path — **alignment and straightness govern**, not wheel capacity.

| Characteristic | Nominal (mm [in]) | Accept limit | Method | Class |
|---|---|---|---|---|
| Rail length (each) | 6000.0 [236.220] = **2× roof length** | ISO 2768 | tape/total station | Major |
| Gauge (rail spacing) | 3000.0 [118.110] | **± 2 mm [0.079 in]** over the run | total station / trammel | **Critical** |
| Straightness | — | **≤ 3 mm [0.118 in] over the run** | string-line / laser | **Critical** |
| Level / co-planarity of the two rails | — | per PE *(ASSUMED — e.g. ≤ 3 mm)* | level / total station | Critical |
| Splice flushness (J6) on running surface | — | **flush, ground** — no step at the wheel path | straightedge / feeler | **Critical** |
| End stops present + engaged | 4, both ends both rails | hard stop + rubber pad | function check | Major |

---

## 5. Drive-cycle & interlock test (NW-RR-005 + NW-CO-011)

| Test | Requirement | Method | Class |
|---|---|---|---|
| Full open travel | Roof clears the aperture (travels its **full length, 3000 mm [118.110 in]**) | run to open end stop | **Critical** |
| Open/close time | **≤ 45 s** each (**< 60 s** motor timeout) | stopwatch | Major |
| Roof speed | ≈ 0.067 m/s (**< 0.30 m/s** ceiling) | travel/time | Minor |
| Tractive load / drive margin | Move force ≈ **235 N [52.8 lbf]**; drive **SF ≥ 2.0** vs the drive rating | inline load / motor current | **Critical** |
| Soft-start / soft-stop | smooth ramp; end-stop engagement without slam | observe | Major |
| Manual release | disengages drive; roof movable by hand; re-engages | function | **Critical (safety)** |
| Photo-beam / limit safety | reverses/stops on obstruction; limits stop travel | function | **Critical (safety)** |
| **Wind interlock** | **park ≤ 25 mph [11.2 m/s]; emergency close ≤ 35 mph [15.6 m/s] gust**; positive close against gust | simulate signal | **Critical (safety)** |
| **Snow interlock (MANDATORY)** | roof **held CLOSED while snow-loaded** — cannot be commanded open (snow-laden roll force **627 N [141 lbf] > drive**) | simulate snow signal | **Critical (safety)** |
| Drive ↔ hold-down interlock | drive inhibited while a hold-down is engaged; hold-downs re-engage on close | function | **Critical (safety)** |

> **Why the interlocks are mandatory (grounding).** The drive is **WIND-sized** — at 35 mph the wind is
> **62%** of the 235 N tractive load, so a positive close against the gust is the governing requirement
> (`MECHANICAL_DESIGN.md` §10). A **fully snow-laden** roof needs **627 N [141 lbf]** to roll, which
> **exceeds the ~500 N [112 lbf] drive**, so opening under snow is prohibited by interlock.

---

## 6. Hold-down proof-pull test (NW-RR-006 — MANDATORY / REMEDIATION)

| Characteristic | Requirement | Method | Class |
|---|---|---|---|
| Anchor count | **4** hold-downs installed & interlocked | visual | **Critical** |
| Proof load per anchor | **≥ 2 klbf [8.9 kN]** (PE to set the proof value) | calibrated hydraulic pull / load cell | **Critical** |
| Group capacity vs demand | 4× ≥ 2 klbf = **35.6 kN [8 klbf]** vs net uplift **7.4 kN [1.66 klbf]** → **SF 3.9** | calc + test | **Critical** |
| Anchorage (into enclosure foundation) | per **ACI 318 Ch.17**; embedment/edge PE-set | PE field inspection | **Critical** |
| No slip / no concrete cone / no bracket yield at proof | pass | observe + measure | **Critical** |

> **Grounding.** Survival-wind proof (`MECHANICAL_DESIGN.md` §7): **gross roof uplift 9.2 kN
> [2.06 klbf]** vs **1.8 kN [397 lbf]** self-weight → **SF 0.19 FAIL**; the **4× hold-downs restore
> SF 3.9**. This is the **REMEDIATION** and is **not** value-engineerable out. Anchors land in the
> **enclosure/building foundation** (the pier is isolated — README §4).

---

## 7. Weatherproofing (roof-closed water test)

| Characteristic | Requirement | Method | Class |
|---|---|---|---|
| Roof-closed rain test | no ingress at panel laps, ridge/edge flashing, perimeter gasket | spray/hose test | Major |
| Drainage / weeps | closed roof sheds water; no ponding | visual under test | Major |
| Wall-top weather seal | roof lands on and seals to the wall-top | visual + water test | Major |

---

## 8. Sampling, documentation & sign-off

- **Critical characteristics** (frame square/diagonal, rail gauge/straightness/splice, drive travel +
  all safety interlocks, hold-down proof, critical welds J3/J5/J6) receive **100%** inspection.
- **Major / Minor** verified to ISO 2768 / drawing on the acceptance record.

The bidder shall deliver:

1. **CWI weld report** — VT + MT/PT/UT results keyed to the as-built `weld_map.md`, with dispositions.
2. **WPS / PQR / WPQ** records (AWS D1.1).
3. **Material & galvanize certs** (A500 Gr B, A36, A123 coating record).
4. **Frame + rail dimensional survey** (square, diagonal, gauge, straightness, splice flushness).
5. **Drive-cycle + interlock commissioning report** (travel, time, tractive load, wind + snow + hold-down interlocks, safeties).
6. **Hold-down proof-pull record** (each anchor, proof load, SF).
7. **Weatherproofing (water) test** record.
8. **PE field hold-point sign-offs** (fit-up, weld, galvanize, anchor set, commissioning) + stamped drawings.
9. **RFI / nonconformance** dispositions for every ASSUMED value.

| Role | Name | Signature | Date |
|---|---|---|---|
| Bidder QA | | | |
| CWI (weld) | | | |
| Owner / PE review | | | |

---

## 9. ASSUMED-value register (do NOT treat as final)

| # | ASSUMED acceptance value | Part(s) / joint(s) |
|---|---|---|
| 1 | All weld sizes & the NDE method/extent (VT/MT/PT/UT %) | all welds (`weld_map.md`) |
| 2 | Member sizes the dimensional checks verify against | NW-RR-001/-002/-003 |
| 3 | Rail level / co-planarity limit | NW-RR-003 |
| 4 | Drive rating (→ the SF ≥ 2.0 gate) & interlock thresholds/logic | NW-RR-005 / NW-CO-011 |
| 5 | Hold-down proof load & anchorage (embedment/edge, ACI 318 Ch.17) | NW-RR-006 |
| 6 | Wheel axle / wheel rating (≥4× wheel share) | NW-RR-004 / NW-CO-010 |
| 7 | Weatherproofing detail & water-test method | roof / NW-CO-012 |
| 8 | Galvanize vent/drain + field-repair (A780) acceptance | all steel |
| 9 | Bracket GD&T / surface-finish acceptance values | NW-RR-004/-005/-006 |
</content>
