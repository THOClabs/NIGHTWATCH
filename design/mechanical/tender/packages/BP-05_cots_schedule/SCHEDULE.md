# BP-05 — COTS Procurement Schedule (Purchase Table)

> **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**

| Field | Value |
|---|---|
| Package | BP-05 — COTS procurement schedule |
| Source of truth | `partspec.parts_for('BP-05')` (14 lines) + `bom/cots_schedule.csv` |
| Issue date / Rev | 2026-08-06 / A |
| TDP / BOM standards | MIL-STD-31000A; ASME Y14.34 (associated lists / BOM) |

**How to read this schedule.** Every line is COTS (buy, no fabrication drawing). *Key specs* are quoted
from the parts registry (SOURCED = traced to `calc/params.py`; ASSUMED = design-intent, confirm).
*Supplier class* is the component class the design requires. *Representative catalogue part no.* is a
**real part that meets the class/rating/interface — "representative, confirm"**, established via a short
supplier search; it is **not a sole source** and the buyer confirms availability, lead time, and fit.
Dual units throughout: mm primary, inch in brackets. **Bold "REMEDIATION"** = a mandatory design
proof-out fix (see §0 of `README.md`). Fasteners (NW-CO-014) are broken out in `fastener_schedule.md`.

---

## A. Purchase table

| # | NW-CO | Item | Qty | Key specs (from `partspec`) | Supplier CLASS | Representative catalogue part no. — *confirm* | Status |
|---|---|---|---:|---|---|---|---|
| 1 | **NW-CO-001** | Harmonic drive, RA | 1 | Ratio 100; rated 127 Nm [93.7 lbf·ft]; peak 343 Nm [253 lbf·ft]; hollow bore Ø80.0 mm [3.150 in] *(SOURCED `P.RA_DRIVE`)*; backlash ≤1.0 arcmin | Strain-wave gear | **Harmonic Drive LLC CSF-32-100-2A-GR** *(registry designation = mfr part; sole-class)* | Core |
| 2 | **NW-CO-002** | Harmonic drive, DEC | 1 | Ratio 80; rated 70 Nm [51.6 lbf·ft]; peak 186 Nm [137 lbf·ft]; hollow bore Ø64.0 mm [2.520 in] *(SOURCED `P.DEC_DRIVE`)*; backlash ≤1.0 arcmin | Strain-wave gear | **Harmonic Drive LLC CSF-25-80-2A-GR** *(registry designation = mfr part; sole-class)* | Core |
| 3 | **NW-CO-003** | Angular-contact bearing 7008 (RA pair) | 2 | Bore Ø40 mm [1.575 in]; OD Ø68 mm [2.677 in]; width 15 mm [0.591 in]; DB back-to-back; 15° contact; ABEC-7/P4 | Super-precision angular-contact ball bearing | **SKF 7008 CD/P4A** (universal-match: **7008 CDGA/P4A** for factory DB set); equiv **NSK 7008A5TYNSULP4 / FAG HCB7008-E-T-P4S** | **REMEDIATION — v1 mandatory** |
| 4 | **NW-CO-004** | Angular-contact bearing 7006 (DEC pair) | 2 | Bore Ø30 mm [1.181 in]; OD Ø55 mm [2.165 in]; width 13 mm [0.512 in]; DB back-to-back; 15° contact; ABEC-7/P4 | Super-precision angular-contact ball bearing | **SKF 7006 CD/P4A** (universal-match: **7006 CDGA/P4A**); equiv **NSK 7006A5 / FAG HCB7006** | **REMEDIATION — v1 mandatory** |
| 5 | **NW-CO-005** | On-axis absolute encoder (RA + DEC) | 2 | Resolution < 1″ (on-axis); interface BiSS-C / SSI; **corrects harmonic PE** | Absolute angle ring + readhead | **Renishaw RESOLUTE™ (BiSS-C) readhead + RESA30 rotary angle ring**, 26-bit (0.02″ resolution); equiv **Heidenhain RCN/ECA absolute ring** | **REMEDIATION — v1 mandatory** |
| 6 | **NW-CO-006** | Stepper motor NEMA17 + 27:1 planetary | 2 | Step 1.8°; planetary 27:1; Irun 1.5 A; Igoto 2.0 A; holding 0.45 Nm; 16 microsteps *(SOURCED `P.MOTOR`)* | Hybrid stepper + planetary gearhead | **StepperOnline 17HS19-2004S1 + PG27 gearhead** (equiv Oriental Motor PKP + gearhead) *— representative* | Core |
| 7 | **NW-CO-007** | Motor driver (TMC5160) / OnStepX board | 2 | Irun 1.5 A; Igoto 2.0 A; 16 microsteps *(SOURCED `P.MOTOR`)* | Microstepping stepper driver + controller | **Analog Devices/Trinamic TMC5160** on an **OnStepX** controller (e.g. MaxPCB / FYSETC) *— representative* | Core |
| 8 | **NW-CO-008** | Temperature-compensated focuser | 1 | Temp coeff −2.5 steps/°C *(ASSUMED)*; motorised absolute; compensates Al-tube focus drift over 22 K swing | Motorised absolute focuser w/ temp probe | **Optec TCF-S** (true temp-comp); equiv **ZWO EAF + temperature sensor** or **Pegasus Astro FocusCube v2** *— representative* | **REMEDIATION — v1 mandatory** |
| 9 | **NW-CO-009** | Counterweights (5 kg ×2, 2.5 kg ×1) | 3 | 12.5 kg total available *(SOURCED `P.COUNTERWEIGHTS`)*; fits shaft Ø31.75 mm [1.250 in] (NW-TP-001, BP-02) | Cast-iron mount counterweight | Generic 1.25 in-bore cast-iron CW discs (e.g. ADM / ZWO CW set) *— representative* | **OPTIONAL** (CW-free build omits) |
| 10 | **NW-CO-010** | V-groove track wheels | 8 | Ø~4 in [~101.6 mm]; ≥150 kg [≥331 lb] each; 4 per side; ≥4× on 180 kg roof + snow | Steel V-groove gate/track wheel | **DuraGates 4″ galvanized V-groove wheel** (≤~425 kg [~937 lb]/wheel) or **CasterHQ V-track wheel** *— representative* | Core |
| 11 | **NW-CO-011** | Roof drive (gate operator) | 1 | Move force 235 N [52.8 lbf]; SF 2.1 vs ~500 N [112 lbf] drive; rack-and-pinion/chain; **fail-safe + wind interlock** | Commercial sliding-gate operator | **LiftMaster SL3000UL** (1/2 HP, ≤~454 kg [1000 lb], 15 m travel); equiv **US Automatic Patriot RSL / Nice-Apollo** *— representative* | Core |
| 12 | **NW-CO-012** | Metal roofing panel + flashing | 1 | Area ≈ 9.0 m² [≈96.9 ft²] (3.0 × 3.0 m) *(SOURCED `P.ENCLOSURE`)*; weather skin + ridge/edge flashing + closures | Standing-seam / corrugated steel roofing | 24 ga standing-seam or corrugated galvanized/Galvalume panel + matching flashing/closures *(commodity — representative)* | Core |
| 13 | **NW-CO-013** | 48 V LiFePO4 battery pack + solar | 1 | 48 V bus; ~5 kWh; **13.4 h autonomy** (vs 12 V 3.3 h; night 10 h); DGX ≈59 % of load | 48 V LiFePO4 pack + PV/MPPT + hybrid inverter | **EG4 LifePower4 V2 48 V 100 Ah (5.12 kWh)** rack battery + 48 V hybrid inverter + PV array/MPPT; equiv **Battle Born / SOK** *— representative* | **REMEDIATION — v2 mandatory (v1 grid+UPS)** |
| 14 | **NW-CO-014** | Fastener schedule (SHCS, anchors) | 1 | ASTM A574 SHCS + ASTM F1554 Gr36 anchors *(grades ASSUMED)* | Fastener buy (consolidated) | See **`fastener_schedule.md`** | Core |

---

## B. Per-item procurement notes

**NW-CO-001 / -002 — Harmonic Drive LLC strain-wave gears (drivetrain core).**
The registry designations `CSF-32-100-2A-GR` and `CSF-25-80-2A-GR` are the **manufacturer part numbers**
(SOURCED from `P.RA_DRIVE.name` / `P.DEC_DRIVE.name`), so the class is effectively **sole-source** to
Harmonic Drive LLC's CSF-2A series (second-source only if a proven equivalent hollow-bore strain-wave
unit of identical ratio/torque/bore is qualified). Confirm the **hollow-bore** variant (Ø80.0 /
Ø64.0 mm) and the output-flange bolt pattern against the RA/DEC spindles (8 × M4 on Ø104 / Ø83 mm PCD,
BP-02). Rated torque governs continuous tracking; peak governs slew/wind gust.

**NW-CO-003 / -004 — angular-contact bearing pairs (REMEDIATION, v1 mandatory).**
These **replace the baseline deep-groove 6008 / 6006** whose compliance was 98 % of the 43.5″ stiffness
FAIL. Buy **matched pairs mounted back-to-back (DB)** for moment stiffness — either universal-match
(CDGA/P4A, arrange DB in assembly) or a factory-matched DB set. Precision class **≥ ABEC-7 / ISO P4**.
Confirm bore/OD/width against the H7 housing seats (BP-01) and j6 spindle journals (BP-02): 7008 =
Ø40/Ø68/15 mm, 7006 = Ø30/Ø55/13 mm. Specify preload class and DB matching on the CoC. **Do not
substitute deep-groove** — it re-opens the stiffness FAIL.

**NW-CO-005 — on-axis absolute encoder (REMEDIATION, v1 mandatory).**
Closes the tracking loop **on the axis** so it corrects the harmonic gear's periodic error. Baseline
motor-side-only encoding was DISQUALIFIED at **5.02″ RMS** (5× the 1.0″ gate); the on-axis ring reaches
**0.54″**. Buy an absolute angle ring + readhead with a **BiSS-C (or SSI) serial interface** and
**sub-arcsecond** accuracy/resolution (representative: Renishaw RESOLUTE + RESA30, 26-bit = 0.02″
resolution). Confirm the **ring bore, readhead standoff, and interface** against the actual RA/DEC axis
geometry and the OnStepX / controller input — these are **ASSUMED, confirm**. One per axis (×2).

**NW-CO-006 / -007 — steppers + drivers (drivetrain core).**
Ratings are SOURCED (`P.MOTOR`: 1.8° step, 27:1 planetary, Irun 1.5 A, Igoto 2.0 A, holding 0.45 Nm,
16 microsteps); the specific catalogue motor, gearhead, and controller board are **representative,
confirm**. The planetary periodic error is **mooted by the on-axis encoder** (NW-CO-005) — the servo
closes on the absolute ring for position and the motor encoder for velocity. TMC5160 on an OnStepX board
is the reference control stack.

**NW-CO-008 — temperature-compensated focuser (REMEDIATION, v1 mandatory).**
Passive (fixed) focus walks **~10× depth-of-focus** over the 22 K night swing (thermal proof). Buy a
**motorised absolute focuser with a temperature probe and a compensation curve** (representative: Optec
TCF-S true temp-comp, or ZWO EAF + temp sensor, or Pegasus FocusCube v2). The **−2.5 steps/°C**
coefficient is **ASSUMED** — confirm against the as-built OTA and calibrate. Confirm mechanical coupling
to the OTA drawtube.

**NW-CO-009 — counterweights (OPTIONAL).**
The selected topology is the **counterweight-FREE GEM** (torque proof SF 2.5/2.6; deletes 15.4 kg +
29 % RA inertia; cost delta −$110). **Buy only if the counterweighted variant is elected.** If bought,
the 12.5 kg set (5 + 5 + 2.5 kg) rides the Ø31.75 mm [1.250 in] shaft NW-TP-001 (BP-02, itself optional).

**NW-CO-010 — V-groove track wheels (enclosure motion core).**
Eight wheels (4 per side) carry the 180 kg [397 lb] roof + snow on the BP-04 box track (NW-RR-003).
Ø~4 in [~101.6 mm], **≥150 kg [≥331 lb]/wheel** rated (target ≥4× on the loaded roof — representative
DuraGates 4″ carries ~425 kg [~937 lb]/wheel, ample). Confirm the **V-profile matches the rail section**
and the axle bore fits the M16 axle of the wheel brackets (NW-RR-004, BP-04). **ASSUMED, confirm.**

**NW-CO-011 — roof drive / gate operator (enclosure motion core).**
Enclosure proof: **235 N [52.8 lbf] move force, SF 2.1** vs a ~500 N [112 lbf]-class drive. Buy a
**commercial sliding-gate operator** (rack-and-pinion or chain) rated for the 180 kg [397 lb] roof.
**Must be fail-safe and interlocked with the wind system** (no open above the gust limit; hold closed on
survival wind, coordinated with the NW-RR-006 hold-downs). Representative: LiftMaster SL3000UL. The
operator product, duty rating, and interlock logic are **ASSUMED design-intent — PE/controls confirm.**

**NW-CO-012 — metal roofing panel + flashing (weather skin core).**
Weatherproof skin over the roll-off frame, ≈9.0 m² [≈96.9 ft²] (SOURCED roof 3.0 × 3.0 m). Panel type
(standing-seam vs corrugated), gauge, and fastening are **ASSUMED** — confirm against the ASCE 7
snow/wind case and the purlin spacing (NW-RR-002, BP-04). Include **ridge/edge flashing, closures, and
gaskets** for a sealed roll-off joint.

**NW-CO-013 — 48 V LiFePO4 battery pack + solar (REMEDIATION, v2 mandatory).**
Power proof: a 12 V pack gives only **3.3 h vs the 10 h** night; **48 V gives 13.4 h** (DGX ≈59 % of the
load). Buy a **48 V LiFePO4 pack (~5 kWh) + solar array/MPPT + 48 V hybrid inverter** for off-grid
autonomy. **Mandatory only for the off-grid v2**; **v1 may run grid + UPS** (`MECHANICAL_DESIGN.md` §9
roadmap). Representative: EG4 LifePower4 V2 48 V 100 Ah (5.12 kWh). Sizing **ASSUMED — confirm** against
the final load schedule and DGX duty cycle.

**NW-CO-014 — fastener schedule.**
Consolidated ASTM A574 SHCS + ASTM F1554 Gr36 anchor buy across BP-01…BP-04 → see
`fastener_schedule.md`. Grades are **ASSUMED design-intent**; lengths/quantities/torque are **ASSUMED,
bidder/PE to confirm**; structural anchor sizing is a **PE** item.

---

## C. Remediation & option roll-up (buyer checklist)

| Category | Lines | Rule |
|---|---|---|
| **v1 MANDATORY remediations** | NW-CO-003, NW-CO-004, NW-CO-005, NW-CO-008 | Must be the remediated parts — no baseline substitution without engineering sign-off. |
| **v2 MANDATORY remediation** | NW-CO-013 | Off-grid autonomy only; v1 may run grid + UPS. |
| **Core buy (build-critical)** | NW-CO-001, -002, -006, -007, -010, -011, -012, -014 | Required for the v1 build; representative catalogue numbers to confirm. |
| **OPTIONAL** | NW-CO-009 | Counterweight-FREE build omits; buy only for the counterweighted variant. |
| **5th remediation (elsewhere)** | NW-RR-006 (BP-04) | 4× wind hold-downs — fabricated steel, not BP-05; anchors captured in `fastener_schedule.md`. |

> All representative catalogue part numbers are **"representative — confirm"**: they fix the class,
> rating, and interface, not a sole source. Confirm availability, lead time, and fit against the fixed
> BP-01…BP-04 interfaces (`README.md` §4) before placing any order; resolve every ASSUMED value via
> RFI first.
