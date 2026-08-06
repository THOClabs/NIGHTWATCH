# 01 — Statement of Work (General)

**Project:** NIGHTWATCH Observatory — telescope mount + roll-off roof enclosure
**Document:** BP-00 / 01 — General Statement of Work, Rev A
**Status:** **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**
**Units:** mm primary, [inch] in brackets.

---

## 1. Scope summary

NIGHTWATCH is a small robotic astronomical observatory: a **counterweight-free German
equatorial mount (GEM)** carrying an Intes-Micro MN78 f/8 optical tube, mounted on an
**isolated reinforced-concrete pier**, inside a **roll-off roof enclosure**. This
tender procures the fabricated mechanical hardware and the commercial (COTS) hardware
for that build, organized into five packages:

- **The mount** — a machined 6061-T6 aluminium head (RA + DEC housings and saddle,
  BP-01), 303 stainless turned spindles and shaft (BP-02), driven by COTS harmonic
  drives, angular-contact bearings, on-axis absolute encoders, and stepper
  drivetrains (BP-05).
- **The foundation** — an isolated cast-in-place concrete pier with a galvanized steel
  top plate, an anodized aluminium pier-to-mount adapter, and a cast-in anchor-bolt
  set (BP-03).
- **The roll-off roof** ("disappearing turret") — a welded structural-steel roof frame
  with rafters/purlins, box-track rails, wheel/drive/hold-down brackets, hot-dip
  galvanized, with a COTS gate-operator drive, V-groove wheels, and metal roofing
  (BP-04 fabrication + BP-05 purchase).

The mechanical design is **frozen and proven** (`design/mechanical/MECHANICAL_DESIGN.md`,
6 PASS / 5 remediated-FAIL across eleven proofs). This SOW procures the build to that
baseline; it does not re-open design decisions.

### 1.1 Proof-out remediations embedded in this scope

The tender carries the five computed remediations from the proof-out; bidders shall
treat each as a **mandatory** feature of the parts they touch:

| Remediation | Where it appears | Registry basis |
|---|---|---|
| **Angular-contact 7008 (RA) / 7006 (DEC) bearings**, back-to-back — replace deep-groove 6008/6006 | Housing seats NW-MH-001 (7008 seat) / NW-MH-002 (7006 seat); spindle journals NW-TP-002 / NW-TP-003; bearings NW-CO-003 / NW-CO-004 | Stiffness proof: 6008/6006 were ~98% of the 43.5″ deflection FAIL |
| **On-axis absolute encoder** (RA + DEC) — replaces homing-grade baseline | NW-CO-005 | Encoder proof: baseline 5.02″ RMS FAIL → on-axis ring 0.54″ |
| **4× wind hold-down anchors** | Brackets NW-RR-006 + anchor set NW-PF-004 | Wind proof: survival uplift 9.2 kN, 4× 2 klbf anchors → SF 3.9 |
| **Temperature-compensated focuser** | NW-CO-008 | Thermal proof: 22 K diurnal swing walks focus ~10× depth-of-focus |
| **48 V power pack** (v2 autonomy) | NW-CO-013 | Power proof: 12 V pack 3.3 h vs 10 h night; 48 V → 13.4 h |

## 2. Site

| Parameter | Value | Basis |
|---|---|---|
| Location | Central Nevada (high-desert site) | Config baseline (SOURCED) |
| Elevation | **1800 m [5906 ft]** | `params.SITE.elevation_m` |
| Latitude | **38.9° N** | `params.SITE.latitude_deg` |
| Air density | ISA at 1800 m (derived) — reduced density lowers wind drag but is used for the survival case | `params.SITE.air_density` (DERIVED) |
| Design wind | Operational gust and **105 mph survival** governs roof uplift | Wind proof (ASCE 7 framing) |
| Snow | Closed-roof snow case governs roof structure (10.8 kN, ~6.1× dead weight) | Enclosure proof |
| Seismic / foundation | Pier passes with governing SF 6.8, f_n 152 Hz; embedment > frost line, isolated from any building slab | Pier proof |

**Site loads (wind/snow/seismic) are ASSUMED design-intent at the ASCE 7 level and
shall be confirmed by the responsible PE against the actual permitted site
(ground-snow load, wind exposure category, seismic design category).** Bidders on
BP-03 and BP-04 shall price to the loads the PE confirms.

## 3. General responsibilities

### 3.1 Owner (or Owner's engineer) provides
- The released Technical Data Package for each awarded package: STEP AP242 masters,
  DXF/DWG flat patterns, PDF control drawings (`NW-xx`), and the XLSX BOM.
- The responsible **Professional Engineer** who reviews and stamps the pier (BP-03)
  and the roof structure (BP-04) before construction.
- Confirmed site loads and the survey/benchmark for pier location and orientation to
  latitude 38.9°.
- Coordination of cross-package interfaces where packages are awarded separately.

### 3.2 Bidder / Contractor provides (for each package bid)
- All labour, materials to the specified stock (see cut list), consumables, finishes,
  fixturing, and shipping to the delivery point.
- Fabrication to the frozen dimensions, materials, finishes, and tolerances of the
  control drawings and partspec — **dual-unit** dimensions govern as drawn.
- The **Inspection & Test Plan** deliverables of `04_inspection_test_plan.md`
  (CMM reports, weld NDE, concrete cylinder breaks, material certs, finish checks) as
  a condition of acceptance.
- Resolution — via RFI — of any "ASSUMED design-intent" value needed to fabricate,
  submitted for PE confirmation; the contractor shall not silently finalize an
  assumed value.
- For BP-03/BP-04: the PE-stampable structural submittals (rebar/anchor design; weld
  procedures and member-size confirmation) required before construction.

## 4. Standards applicability matrix

Which standards govern which package. Full text and scope in `02_standards_register.md`.

| Standard(s) | BP-01 | BP-02 | BP-03 | BP-04 | BP-05 | Governs |
|---|:-:|:-:|:-:|:-:|:-:|---|
| MIL-STD-31000A | ● | ● | ● | ● | ● | Technical Data Package structure |
| ASME Y14.5-2018 (GD&T) | ● | ● | ● | ● | | Geometric dimensioning & tolerancing |
| ASME Y14.100 / .24 / .34 / .1 | ● | ● | ● | ● | ● | Drawing practice, types, associated lists/BOM, sheet/title block |
| ASME Y14.36 / ASME B46.1 | ● | ● | ○ | | | Surface texture symbols & measurement |
| ISO 286 (H7/js6) | ● | ● | ○ | | | Bearing-bore / journal fits |
| ISO 2768 (mK) | ● | ● | ● | ● | | General tolerances |
| ASTM B209 / AMS-QQ-A-250/11 | ● | | ● | | | 6061-T6 plate material |
| ASTM A582 | | ● | | | | 303 stainless bar |
| ASTM A36 | | | ● | ● | | Structural steel plate |
| ASTM A500 Gr B | | | | ● | | HSS members |
| ASTM A615 Gr60 | | | ● | | | Rebar |
| ASTM F1554 Gr36 | | | ● | ● | ● | Anchor bolts |
| ASTM A574 | ● | ● | ● | ● | ● | Socket-head cap screws |
| MIL-A-8625F Type III | ● | | ● | | | Hardcoat anodize (aluminium) |
| ASTM A123 | | | ● | ● | | Hot-dip galvanize (steel) |
| ASTM A967 | | ● | | | | Passivation (stainless) |
| AWS A2.4 / D1.1 (+ WPS/PQR) | | | ○ | ● | | Weld & NDE symbols; structural steel welding |
| AWS D1.2 | | | | ○ | | Aluminium welding (if any welded Al) |
| ACI 318 (Ch. 17) / ACI 301 | | | ● | ○ | | Concrete design/spec & anchoring |
| ASCE 7 | | | ● | ● | | Wind / snow / seismic loads |
| STEP ISO 10303 AP242 | ● | ● | ● | ○ | | 3-D / CNC exchange |
| DXF / DWG | | | ● | ● | | Flat-pattern cutting |
| PDF / XLSX | ● | ● | ● | ● | ● | Drawings / BOM formats |

● = primary/applicable · ○ = conditionally applicable (as-noted / if that process is used).

## 5. Interfaces (owner-coordinated on split awards)

Key mating features held by shared datums across packages — a partial bidder builds
to their own published dimensions; the Owner coordinates fit:

- **RA housing NW-MH-001** flange (104 mm [4.094 in] bolt circle, 8 holes) ↔ **RA
  spindle NW-TP-002** (8× M4 on 104 PCD) ↔ **CSF-32 harmonic drive NW-CO-001** (bore
  80.0 mm [3.150 in]).
- **DEC housing NW-MH-002** (83 mm [3.268 in] bolt circle) ↔ **DEC spindle NW-TP-003**
  ↔ **CSF-25 NW-CO-002** (bore 64.0 mm [2.520 in]).
- **Bearing seats** NW-MH-001 (Ø68.0 mm [2.677 in] H7, 7008) / NW-MH-002 (Ø55.0 mm
  [2.165 in] H7, 7006) ↔ spindle journals ↔ COTS bearings NW-CO-003/004.
- **Pier top plate NW-PF-002** (12 in sq) ↔ **adapter plate NW-PF-003** (10 in sq) ↔
  **RA housing NW-MH-001** ↔ **anchor set NW-PF-004** (4× Ø19.05 mm [0.750 in] F1554).
- **Roof wheel brackets NW-RR-004** ↔ **V-groove wheels NW-CO-010** ↔ **rails
  NW-RR-003**; **drive bracket NW-RR-005** ↔ **gate-operator NW-CO-011**; **hold-down
  brackets NW-RR-006** ↔ **anchors** (mandatory wind remediation).

---

*Package-specific SOWs (per-part fabrication notes, sequencing, and acceptance)
accompany each child package BP-01 … BP-05 and incorporate this general SOW by
reference.*
