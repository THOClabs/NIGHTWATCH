# BP-04 — Statement of Work: Roll-off Roof "Disappearing Turret" (Structural Steel + Rail/Drive)

> **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**

| Field | Value |
|---|---|
| Package | BP-04 — Roll-off roof ("disappearing turret") |
| Parts | NW-RR-001 (frame), -002 (purlins), -003 (rail beams), -004 (wheel brackets), -005 (drive bracket + stops), -006 (wind hold-down brackets) |
| Process | Structural steel cut + weld (AWS D1.1); laser-cut plate brackets; rail/drive install |
| Material | ASTM A500 Gr B HSS (frame/purlins); ASTM A36 (rail beams, brackets) |
| Finish | **Hot-dip galvanize per ASTM A123** (after fabrication) |
| Issue date / rev | 2026-08-06 / A |

**Purpose.** This SOW specifies the fabrication, welding, tolerancing, finishing, rail/drive
installation, and commissioning requirements for the roll-off roof and its track/drive. It is read with
the STEP ISO 10303 AP242 solid master (weldment/bracket geometry authority), the DXF/DWG flat patterns
(plate brackets), the NW-RR control drawings (PDF), `weld_map.md` (joint schedule), and `acceptance.md`.
All dimensions are dual-unit, **mm primary, inch in brackets**, drawn from the parts registry
(`partspec.parts_for('BP-04')`) and `cut_list.csv` — **no dimension herein is invented.**

**Standards applied.** MIL-STD-31000A (TDP); **AWS D1.1** (structural steel welding, incl. WPS/PQR and
welder qualification WPQ); **AWS A2.4** (weld & NDE symbols); **ASTM A500 Gr B** (HSS), **ASTM A36**
(steel), **ASTM A123** (hot-dip galvanize), **ASTM F1554 Gr36** (anchor bolts), **ASTM A574** (SHCS);
**ACI 318 Ch.17** (anchorage into concrete/foundation); **ASCE 7** (wind/snow/seismic loads);
**ASME Y14.5-2018** (bracket GD&T), Y14.100/Y14.24/Y14.1 (drawing practices); **ISO 286** (fits);
**ISO 2768** (general tolerances).

> **PE-STAMP GATE (see README §0).** The roof and its supporting steel are a **structure**. Member
> sizes, weld sizes, and anchorage in this SOW are **ASSUMED design-intent** and are **not** releasable
> for construction until a licensed PE confirms them against the **ASCE 7 snow (10.8 kN [2.42 klbf]
> closed-roof) and survival-wind (9.2 kN [2.06 klbf] uplift)** cases and **stamps** the drawings.

---

## 1. General requirements (all parts)

1. **Material & certification.** HSS to **ASTM A500 Gr B**; plate and rail to **ASTM A36**. Furnish
   mill certification / CoC with **heat/lot traceability**; mark each member with part number and
   revision per ASME Y14.100.
2. **General tolerance.** **ISO 2768-mK** on plate features; frame/rail geometric tolerances per the
   per-part tables (§2–§7). Break sharp edges; no burrs on plate brackets.
3. **Welding.** All welds per **AWS D1.1**. The bidder shall submit **WPS** supported by **PQR**, and
   **welder qualification records (WPQ)** for each process/position, **before** production welding.
   Prequalified joints per AWS D1.1 are acceptable where applicable; all others require a qualified WPS.
   Weld & NDE symbols on the drawings and in `weld_map.md` are interpreted per **AWS A2.4**.
4. **Weld sizes are ASSUMED design-intent.** Every weld leg/throat and every CJP/PJP designation in
   `weld_map.md` is **ASSUMED — PE/CWI to size** per the AWS D1.1 minimum-fillet-weld tables (governed
   by the thinner part joined) and the PE's computed member forces. **Do not treat any weld size herein
   as released.**
5. **GD&T.** Bracket geometric callouts per **ASME Y14.5-2018**; hole-pattern position per the drawing
   (bracket hole patterns held to **0.25 mm [0.010 in]**, `cut_list`/drawing).
6. **Fabrication sequence.** Weld → dimensional/weld inspection → **hot-dip galvanize (ASTM A123, after
   all welding)** → install wheels/drive → align → commission. Provide **vent and drain holes** on all
   closed HSS sections for the galvanizing bath (locations **ASSUMED — bidder to detail**, must not
   fall on a stiffness-critical face).
7. **Finish.** **Hot-dip galvanize per ASTM A123** on all steel after fabrication. Field-repair of
   galvanize damaged by field welding/handling per the **bidder's approved procedure** (recognized
   repair standard **ASTM A780**, supplementary to the register). Coating mass/thickness recorded.
8. **Fasteners.** Structural bolting and bracket fasteners per **ASTM A574** (SHCS) where used; anchors
   per **ASTM F1554 Gr36** (see §7). Fastener schedule consolidated under BP-05 (NW-CO-014).

---

## 2. NW-RR-001 — Roof frame perimeter (HSS)

**Drawing:** NW-RR-001 (rev A). **Stock:** HSS **50.8 mm [2.000 in] sq × 3.2 mm [0.125 in] wall**,
total **12000.0 mm [472.441 in]** (four sides of the **3000.0 mm [118.110 in] × 3000.0 mm [118.110 in]**
square perimeter), cut allowance 3.0 mm, stock mass 56.98 kg (`cut_list.csv`). **Process:** cut + weld
(AWS D1.1). **Tolerance:** frame square **3 mm/m**, diagonal **5 mm [0.197 in]** across the frame.

| Feature | Value (mm [in]) | Spec |
|---|---|---|
| Perimeter span × length | 3000.0 [118.110] × 3000.0 [118.110] | ASSUMED footprint (`P.ENCLOSURE`) |
| Member | HSS 2×2×1/8 (50.8 sq × 3.2 wall) | **ASSUMED design-intent** — PE to size vs snow/wind |
| Corner joints | fully welded, **gusseted** | AWS D1.1; size in `weld_map.md` (ASSUMED) |
| Frame square / diagonal | 3 mm/m; diagonal 5 mm [0.197 in] | acceptance datum |

**Function.** The frame carries the purlins + roofing panel and transfers the **closed-roof snow load
(10.8 kN [2.42 klbf])** and **survival-wind uplift (9.2 kN [2.06 klbf])** into the wheels/hold-downs.
Corner joints are **fully welded and gusseted**. **Member size ASSUMED — PE to confirm vs ASCE 7.**

**Provenance / flags.** Roof span/length = P.ENCLOSURE (ASSUMED footprint); member size ASSUMED
design-intent; corner-weld size ASSUMED (`weld_map.md` J1).

---

## 3. NW-RR-002 — Roof rafters / purlins

**Drawing:** NW-RR-002 (rev A). **Stock:** HSS **38.1 mm [1.500 in] sq × 3.2 mm [0.125 in] wall**,
total **15000.0 mm [590.551 in]** (**5 purlins × 3000.0 mm [118.110 in]** span), cut allowance 3.0 mm,
stock mass 52.23 kg (`cut_list.csv`). **Qty 5**, spaced **600.0 mm [23.622 in] o.c.** **Process:**
cut + weld to the frame (AWS D1.1). **Finish:** galvanize ASTM A123.

| Feature | Value (mm [in]) | Spec |
|---|---|---|
| Span (each) | 3000.0 [118.110] | ASSUMED (`P.ENCLOSURE`) |
| Spacing | 600.0 [23.622] o.c. | ASSUMED design-intent |
| Count | 5 | ASSUMED design-intent |
| Member | HSS 2×1×1/8 **or** 38.1 sq × 3.2 wall | **ASSUMED — reconcile (see below)** |
| Purlin-to-frame joint | fillet both sides (or bolted clip) | AWS D1.1; `weld_map.md` J2 (ASSUMED) |

> **Member-callout reconciliation (ASSUMED design-intent).** The registry names the member **"HSS
> 2×1×1/8"** (rectangular) while the modelled/ordered stock is **38.1 mm [1.500 in] square × 3.2 mm
> wall**. Both are carried as ASSUMED; **the PE shall reconcile the purlin section** against the ASCE 7
> **snow case (10.8 kN [2.42 klbf] over the 9 m² [96.9 ft²] roof, ≈6.1× the roof dead weight)**, which
> is the **governing design driver** for the purlins and panel (`MECHANICAL_DESIGN.md` §10), and issue
> the released size.

**Function.** Purlins carry the **metal roofing panel (NW-CO-012, BP-05)** and the snow load. A
**sloped/pitched, slippery metal roof sheds most snow** (ASCE 7 slope factor Cs → ~0 for a steep metal
roof); a **flat** roll-off roof must carry the full load and needs the **snow interlock** (§6).

---

## 4. NW-RR-003 — Track rail beams (box track)

**Drawing:** NW-RR-003 (rev A). **Stock:** box track **63.5 mm [2.500 in] sq × 4.0 mm [0.157 in]
wall**, **6000.0 mm [236.220 in] each**, **2 rails**, cut allowance 3.0 mm, stock mass 89.68 kg
(`cut_list.csv`). **Process:** cut + weld / bolt to the rail supports. **Tolerance:** rail straightness
**3 mm [0.118 in] over the run**; gauge **2 mm [0.079 in]**.

| Feature | Value (mm [in]) | Spec |
|---|---|---|
| Rail length (each) | 6000.0 [236.220] = **2× roof length** | so the roof **fully clears** the aperture |
| Gauge (rail spacing) | 3000.0 [118.110] | = roof span; hold to ±2 mm [0.079 in] |
| Section | box track, 2.5 in [63.5 mm] class | **ASSUMED**; brand/section = COTS (BP-05) |
| Straightness | 3 mm [0.118 in] over run | acceptance datum |
| End stops | required, both ends, both rails | part of NW-RR-005 |

**Function.** The **"disappearing turret" travels its own full length off the building** — hence the
**rail run = 2× the roof length (6000 mm [236.220 in])**. Each rail carries the roof + snow reaction on
the V-groove wheels. **Splices** (if the rail is furnished in shorter lengths) shall be **CJP groove
butt welds with backing, ground flush on the running surface** (`weld_map.md` J6, size/NDE ASSUMED).
Rail brand/section is a **suggested COTS category** (steel V-groove box track, README §6); the shop may
furnish proprietary track in lieu of fabricated box track **subject to PE approval**. **End stops are
MANDATORY** at both ends of both rails.

---

## 5. NW-RR-004 — Wheel axle brackets

**Drawing:** NW-RR-004 (rev A). **Stock:** plate **101.6 mm [4.000 in] × 76.2 mm [3.000 in] × 9.5 mm
[0.375 in]**, **qty 8**, cut allowance 3.0 mm, stock mass 4.63 kg. **Process:** laser cut + weld.
**Tolerance:** hole pattern **0.25 mm [0.010 in]**.

| Feature | Value | Spec |
|---|---|---|
| Count | 8 (4 per side) | ASSUMED design-intent |
| Wheel bore | for **Ø101.6 mm [4.000 in] V-groove wheel** (COTS, NW-CO-010) | shop installs the wheel |
| Axle | **M16** | ASSUMED; bidder/PE to confirm shear/bending |
| Bracket-to-frame weld | fillet both sides, gusseted | AWS D1.1; `weld_map.md` J3 (ASSUMED, CRITICAL) |

**Function.** The brackets carry the COTS **V-groove wheels (NW-CO-010, BP-05)** and transmit the roof
weight into the rails. **Size the wheels for ≥4× the wheel share of the roof (180 kg [397 lb]) + snow.**
4 in [101.6 mm] steel V-groove wheels are commonly rated ~3,000 lb [~13 kN] each, so **alignment and
weld integrity — not wheel capacity — govern** (`acceptance.md`). Bracket-to-frame welds are
**load-critical** and receive VT 100% + MT/PT (extent ASSUMED, §`acceptance.md`).

---

## 6. NW-RR-005 — Drive bracket + end stops (and the drive/interlock scope)

**Drawing:** NW-RR-005 (rev A). **Stock:** plate/angle **150.0 mm [5.906 in] × 100.0 mm [3.937 in] ×
9.5 mm [0.375 in]**, **qty 4**, cut allowance 3.0 mm, stock mass 4.49 kg. **Process:** laser cut + weld.

| Feature | Value | Spec |
|---|---|---|
| Drive | **rack-and-pinion / gate operator** (COTS, NW-CO-011) | shop installs + commissions |
| End stops | **4** + rubber bump pads | hard limits, both ends both rails |
| Drive-bracket weld | fillet, gusseted | AWS D1.1; `weld_map.md` J4 (ASSUMED) |

**Drive sizing (from the proof — `MECHANICAL_DESIGN.md` §10).** The drive moves the **180 kg [397 lb]**
roof against rolling **88 N [19.8 lbf]** + **35 mph [15.6 m/s]** wind **147 N [33.1 lbf]** = **235 N
[52.8 lbf]** tractive force (**11.77 Nm [8.68 lbf·ft]** @ 50 mm [1.969 in] wheel) → **SF 2.1 vs a
~500 N [112 lbf] garage-door-class drive.** Because **wind is 62% of the tractive load, the drive is
WIND-sized** — specify a **positive, fail-safe close against the gust**. Suggested COTS category:
**light-commercial rack-and-pinion slide-gate operator** (README §6).

**Interlocks (MANDATORY — REMEDIATION/finding).**
- **Wind interlock:** park at **25 mph [11.2 m/s]** (roof stays open only below this), emergency close
  at **35 mph [15.6 m/s]** gust; open time 45 s < 60 s motor timeout.
- **Snow interlock (MANDATORY):** a fully snow-laden roof needs **627 N [141 lbf]** to roll — which
  **exceeds the ~500 N drive** — so the roof **must never be commanded open under snow load**. The
  safety monitor shall **hold the roof CLOSED while snow-loaded** (`MECHANICAL_DESIGN.md` §10). A
  **pitched shedding roof** is the design alternative.
- Provide **soft-start/soft-stop, manual release, photo-beam/limit safety,** and interlock with the
  building/telescope safety monitor. Interlock sensor/logic detail is **ASSUMED — bidder/PE to detail.**

**Control power.** The drive + interlocks draw from the site power system — **grid + UPS (v1)** or the
**48 V LiFePO4 pack (v2, NW-CO-013, REMEDIATION of the power/autonomy FAIL)**; power source is a BP-05
coordination item.

---

## 7. NW-RR-006 — Wind hold-down anchor brackets (REMEDIATION — MANDATORY)

**Drawing:** NW-RR-006 (rev A). **Stock:** plate **127.0 mm [5.000 in] × 101.6 mm [4.000 in] × 12.7 mm
[0.500 in]**, **qty 4**, cut allowance 3.0 mm, stock mass 5.15 kg. **Process:** laser cut + weld.
**Tolerance:** hole pattern **0.25 mm [0.010 in]**.

| Feature | Value | Spec |
|---|---|---|
| Count | **4** | REMEDIATION basis |
| Anchor | **Ø0.75 in [19.05 mm] F1554 Gr36** (to enclosure foundation) | ACI 318 Ch.17; PE to size |
| Capacity (each) | **≥2 klbf [8.9 kN]** | proof-test target |
| Bracket weld | CJP or heavy fillet, gusseted | AWS D1.1; `weld_map.md` J5 (ASSUMED, **CRITICAL**) |

> **REMEDIATION — MANDATORY (do not value-engineer out).** The survival-wind proof (`MECHANICAL_DESIGN.md`
> §7) found **gross roof uplift 9.2 kN [2.06 klbf]** vs **1.8 kN [397 lbf]** self-weight → **SF 0.19 —
> FAIL.** Net anchor demand is **7.4 kN [1.66 klbf]**. **Four hold-down brackets at ≥2 klbf [8.9 kN]
> each (35.6 kN [8 klbf] total) restore SF 3.9.** These brackets **clamp the roof/building against the
> 105 mph [46.9 m/s] survival uplift and are interlocked with the drive** (the roof cannot be driven
> while a hold-down is engaged, and must re-engage on close).

**Anchorage.** The brackets anchor into the **enclosure/building foundation** (the telescope pier is
isolated — README §4). **Final anchor diameter, grade, embedment, and edge distance are PE to set per
ACI 318 Ch.17**; each anchor is **proof-pull-tested** per `acceptance.md`.

---

## 8. Weatherproofing

- Install the COTS **metal roofing panel + flashing (NW-CO-012, BP-05)** over the purlins: lapped/sealed
  panel, **ridge and edge flashing, and perimeter gaskets** at the roof-to-wall closure when shut.
- Provide **drainage/weeps** so the closed roof sheds water; detail the **wall-top weather seal** that
  the roof lands on. Panel lap, flashing, gasket, and drainage details are **ASSUMED — bidder to detail**
  with the panel supplier; verify by the **roof-closed water test** (`acceptance.md`).
- A **pitched** panel is preferred (sheds snow per §3/§6); a flat panel triggers the snow interlock.

---

## 9. Submittals & deliverables

1. Finished, galvanized, weatherproofed, commissioned assembly (all six NW-RR parts).
2. Material / mill certs (A500 Gr B, A36) with heat/lot traceability.
3. **WPS + PQR + welder qualification (WPQ)** per AWS D1.1; as-built `weld_map.md`; **CWI** weld report.
4. **NDE reports** (VT 100% + MT/PT on critical welds; extent ASSUMED per `acceptance.md`).
5. **Galvanize cert** (ASTM A123 coating mass/thickness) + vent/drain detail + galv-repair procedure.
6. **Rail-alignment survey** (gauge, straightness, level, splice flushness).
7. **Drive-cycle + interlock commissioning report** (travel, tractive load/current, wind + snow interlocks).
8. **Hold-down pull-test record** (each anchor to the PE-set proof load).
9. **Weatherproofing (water) test** record.
10. **PE sign-off** — stamped structural drawings + field hold-point sign-offs.
11. RFI / nonconformance log resolving every ASSUMED value before it is built.

---

## 10. ASSUMED design-intent register (this SOW)

| # | ASSUMED value | Part(s) | Status |
|---|---|---|---|
| 1 | Frame HSS 2×2×1/8 member size | NW-RR-001 | ASSUMED — PE to size vs ASCE 7 snow/wind |
| 2 | Purlin section (HSS 2×1×1/8 vs 38.1 sq), spacing 600 mm, count 5 | NW-RR-002 | ASSUMED — PE to reconcile & size (snow-governed) |
| 3 | Box-track section (2.5 in class), rail supports/anchorage spacing | NW-RR-003 | ASSUMED — PE to detail; COTS track alt allowed |
| 4 | All weld sizes & joint types (CJP/PJP/fillet legs) | all | ASSUMED — PE/CWI to size per AWS D1.1 |
| 5 | Wheel axle M16; wheel bore/rating | NW-RR-004 | ASSUMED — size wheels ≥4× wheel share |
| 6 | Drive product + interlock sensor/logic | NW-RR-005 | ASSUMED — light-commercial rack-and-pinion (README §6) |
| 7 | Hold-down anchor Ø0.75 F1554, ≥2 klbf, embedment/edge | NW-RR-006 | ASSUMED REMEDIATION — PE per ACI 318 Ch.17 |
| 8 | Roof geometry 3.0×3.0 m / 180 kg | all | ASSUMED footprint (`P.ENCLOSURE`) |
| 9 | Galvanize vent/drain holes; galv field-repair (A780) | all | ASSUMED — bidder to detail |
| 10 | Weatherproofing detail (panel lap, flashing, gasket, drainage) | roof | ASSUMED — bidder to detail |
| 11 | Bracket GD&T / surface-finish values | NW-RR-004/-005/-006 | ASSUMED — PE to set |
</content>
