# BP-04 — Weld Map / Joint Schedule (Roll-off Roof)

> **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**

| Field | Value |
|---|---|
| Package | BP-04 — Roll-off roof ("disappearing turret") |
| Welding standard | **AWS D1.1** (structural steel; WPS/PQR + welder qualification WPQ) |
| Symbol standard | **AWS A2.4** (weld & NDE symbols) |
| Base metals | ASTM A500 Gr B HSS (frame/purlins); ASTM A36 (rail beams, brackets) |
| Finish | Hot-dip galvanize per ASTM A123 (**weld before galvanizing**) |
| Issue date / rev | 2026-08-06 / A |

This joint schedule enumerates the weld groups of BP-04, the **AWS A2.4 weld symbol** to apply, the
joint type, the **ASSUMED** weld size, the process, and the NDE. It is read with `SOW.md` and
`acceptance.md`, and it is marked up **as-built** by the fabricator for the CWI report.

> **⚠ ALL WELD SIZES AND JOINT TYPES BELOW ARE ASSUMED DESIGN-INTENT — PE/CWI TO CONFIRM.** No weld
> leg, throat, or CJP/PJP designation herein is a released value. The PE/CWI shall size each weld per
> the **AWS D1.1 minimum-fillet-weld tables** (governed by the **thinner part joined** — HSS walls are
> 3.2 mm [0.125 in]/4.0 mm [0.157 in]; brackets 9.5 mm [0.375 in]/12.7 mm [0.500 in]) and the PE's
> computed member forces for the **ASCE 7 snow (10.8 kN [2.42 klbf]) and survival-wind (9.2 kN
> [2.06 klbf] uplift)** cases. Prequalified WPS per AWS D1.1 are acceptable where applicable.

---

## 1. AWS A2.4 symbol legend (as used in this schedule)

| Symbol (text form) | AWS A2.4 meaning |
|---|---|
| `▷` fillet | Fillet weld; leg size to the left of the symbol (e.g. `6▷` = 6 mm leg). |
| `▷ (both sides)` | Fillet weld both sides of the joint (symbol on both sides of the reference line). |
| `V` / `CJP` | Complete-joint-penetration groove weld (bevel/V), full throat. |
| `PJP` | Partial-joint-penetration groove weld; effective throat specified. |
| `○` weld-all-around | Weld-all-around flag at the reference-line elbow (perimeter joint). |
| `▶` field weld | Field-weld flag (filled triangle at the elbow) — welds made at site, not in shop. |
| Tail `(VT)`, `(MT)`, `(PT)`, `(UT)` | NDE method called in the symbol tail (visual / mag-particle / dye-penetrant / ultrasonic). |

*(Rendered on the PDF control drawings and the STEP/weldment model as true AWS A2.4 graphic symbols;
the text forms above are the Markdown transcription.)*

---

## 2. Joint schedule

| Joint | Location / parts joined | Joint type | AWS A2.4 symbol (ASSUMED size) | Process (ASSUMED) | NDE (ASSUMED extent) | Criticality |
|---|---|---|---|---|---|---|
| **J1** | **Frame corners** — NW-RR-001 HSS-to-HSS mitred corners + corner gussets | Mitred T/corner, fully welded + gusset | `○ weld-all-around`, CJP or `5▷` fillet all-around `(VT)` | GMAW / FCAW | **VT 100%** + **MT 25%** | High (frame integrity) |
| **J2** | **Purlin-to-frame** — NW-RR-002 → NW-RR-001 (5 T-joints) | HSS-to-HSS T-joint | `5▷ (both sides)` fillet `(VT)` *(bolted clip alt. permitted)* | GMAW / FCAW | **VT 100%** | Medium (snow path) |
| **J3** | **Wheel-bracket-to-frame** — NW-RR-004 → NW-RR-001 (8×) | Plate-to-HSS, gusseted | `6▷ (both sides)` fillet `(VT)(MT)` | GMAW / FCAW | **VT 100%** + **MT 100%** | **CRITICAL** (carries roof + snow into wheels) |
| **J4** | **Drive-bracket-to-frame** — NW-RR-005 → NW-RR-001 (drive mount) | Plate-to-HSS, gusseted | `6▷ (both sides)` fillet `(VT)` | GMAW / FCAW | **VT 100%** + **MT 25%** | Medium (drive reaction) |
| **J5** | **Hold-down bracket welds** — NW-RR-006 → frame/roof structure (4×) | Plate-to-HSS/plate, gusseted | **CJP** or `8▷ (both sides)` fillet `(VT)(MT)` | GMAW / FCAW / SMAW | **VT 100%** + **MT 100%** (UT if CJP) | **CRITICAL — REMEDIATION** (survival-wind uplift) |
| **J6** | **Rail splices** — NW-RR-003 box-track length-to-length (if spliced) | Butt joint, running surface | **CJP** groove, backing, **ground flush** on wheel path `(VT)(PT)` | GMAW / SMAW | **VT 100%** + **PT 100%** (UT per PE) | **CRITICAL** (wheel running surface) |
| **J7** | **End stops** — stop blocks → NW-RR-003 rail ends / NW-RR-005 (4×) | Plate/block-to-rail | `6▷` fillet, weld-all-around `(VT)` | GMAW / FCAW | **VT 100%** | Medium (impact) |
| **J8** | **Rail-to-support / foundation connection** — NW-RR-003 → rail support | Plate-to-HSS **or bolted** | `6▷ (both sides)` fillet `(VT)` **or** ASTM A574 bolting | GMAW / FCAW / bolt | **VT 100%** (torque check if bolted) | High (rail reactions) |
| **J9** | **Corner gussets / stiffeners** — gusset plates at J1/J3/J5 | Plate-to-HSS | `5▷` fillet, weld-all-around `(VT)` | GMAW / FCAW | **VT 100%** | Supports J1/J3/J5 |

**Field vs shop.** J1–J7 and J9 are **shop welds** (weld → inspect → galvanize). J8 and any hold-down
attachment made at site are **field welds** (`▶` flag) — field-welded galvanized steel requires **galv
field-repair** per the bidder's approved procedure (ASTM A780, supplementary to the register).

---

## 3. Welding controls (AWS D1.1)

1. **WPS / PQR / WPQ.** Submit a **Welding Procedure Specification** for each joint/process/position,
   supported by a **Procedure Qualification Record** (or invoke a prequalified WPS where AWS D1.1
   allows), and **Welder Qualification records (WPQ)** for every welder before production welding.
2. **Filler / preheat.** Filler metal, preheat, and interpass temperatures per the qualified WPS
   (matching A500/A36 base metals) — **ASSUMED to the WPS; bidder to state.**
3. **Sequence & distortion.** Weld the frame (J1) and purlins (J2) with a sequence that holds the
   **frame-square 3 mm/m / diagonal 5 mm [0.197 in]** tolerance (`acceptance.md`); back-gouge CJP roots
   as required by the WPS.
4. **Galvanizing interaction.** Complete and inspect all shop welds **before** hot-dip galvanizing
   (ASTM A123). Provide **vent/drain holes** for the bath on all closed HSS (locations ASSUMED — bidder
   to detail, off stiffness-critical faces). Repair galvanize burned by field welds per §2 note.
5. **CWI.** An **AWS Certified Welding Inspector** performs/oversees the VT and the MT/PT/UT called
   above and signs the weld report (`acceptance.md`).

---

## 4. ASSUMED-value register (this weld map)

| # | ASSUMED value | Joints | Status |
|---|---|---|---|
| 1 | Every fillet leg / throat size (5–8 mm shown) | J1–J9 | ASSUMED — PE/CWI per AWS D1.1 min-fillet tables |
| 2 | CJP vs PJP vs fillet choice at J1, J5, J6 | J1, J5, J6 | ASSUMED — PE to set from computed demand |
| 3 | NDE method + extent (VT/MT/PT/UT %) | all | ASSUMED — PE/CWI to set (critical joints 100%) |
| 4 | Welding process (GMAW/FCAW/SMAW) & filler/preheat | all | ASSUMED — per qualified WPS |
| 5 | Bolted vs welded alternative at J2, J8 | J2, J8 | ASSUMED — bidder option, PE to approve |
| 6 | Galv vent/drain-hole locations | HSS | ASSUMED — bidder to detail |
| 7 | Field-weld extent + galv repair (A780) | J8 + site | ASSUMED — bidder procedure |
</content>
