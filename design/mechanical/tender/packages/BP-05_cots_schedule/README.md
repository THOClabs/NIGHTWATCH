# BP-05 — COTS Procurement Schedule (Buy-to-Print / Off-the-Shelf) — Buyer README

> **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**

| Field | Value |
|---|---|
| Package | **BP-05 — COTS procurement schedule** |
| Trade | Purchasing / integration (no fabrication; no fab control drawings) |
| Parts | NW-CO-001 … NW-CO-014 (14 catalogue line items; 0 fabrication drawings) |
| Branch / project | `design/mechanical-tender` — NIGHTWATCH Observatory Mount & Roll-off Tender |
| Issue date | 2026-08-06 |
| Revision | A |
| Governing TDP standard | MIL-STD-31000A (Technical Data Package) |

This README is the entry point for the **purchasing agent / integrator** bidding BP-05. It defines the
**scope**, the **data package the buyer receives**, the **buyer deliverables**, the **PROCUREMENT
GATE (mandatory design-remediation items)**, and the items carried as **ASSUMED design-intent /
representative catalogue selections** the buyer must confirm. Read it with `SCHEDULE.md` (the purchase
table — item, part number, qty, key specs, supplier class + representative catalogue numbers) and
`fastener_schedule.md` (consolidated ASTM A574 SHCS + ASTM F1554 anchor buy) in this same folder.

BP-05 is a **buy list, not a fabrication package** — every line is COTS (`drawing=False` in the parts
registry; `stock=('cots',)`), so no NW-CO item carries a fabrication control drawing. Where a line
interfaces to a fabricated part (bearing seats, drive registers, wheel bores, anchor holes), the
**mating dimension is fixed by the fabrication package (BP-01…BP-04)** and repeated here for the
buyer's convenience — the buyer selects a catalogue item that **fits that fixed interface**.

---

## 0. PROCUREMENT GATE — READ FIRST (four items are MANDATORY design remediations)

> **⚠ FOUR of the fourteen BP-05 lines are the physical embodiment of the design proof-out
> remediations. They are NOT interchangeable with the cheaper baseline parts they replace. Buying the
> baseline part instead re-opens a proof the design study recorded as FAIL.**

The trade study and proof modules (`MECHANICAL_DESIGN.md` §9, `tradestudy/SECTION.md`) disqualified the
repository's baseline component choices on four counts. BP-05 carries the **remediated** parts. These
four are the gate:

| # | Line | Remediation (buy this) | Replaces / fixes | Proof result |
|---|---|---|---|---|
| 1 | **NW-CO-003 / -004** | Angular-contact **7008 / 7006** super-precision pairs, back-to-back (DB) | deep-groove **6008 / 6006** | Bearing compliance was **98 % of the 43.5″ stiffness FAIL**; angular-contact pairs restore moment stiffness. |
| 2 | **NW-CO-005** | **On-axis absolute encoder** (BiSS-C ring, sub-arcsec), 2 off | motor-side-only encoding | Baseline **5.02″ RMS FAIL** vs 1.0″ target; on-axis ring reaches **0.54″**. |
| 3 | **NW-CO-008** | **Temperature-compensated focuser** | passive (fixed) focus | 22 K night swing walks focus **~10× depth-of-focus**. |
| 4 | **NW-CO-013** | **48 V LiFePO4 battery pack** (+ solar) | 12 V pack | 12 V gives **3.3 h vs 10 h** night autonomy; 48 V gives **13.4 h**. |

> **Note on the 5th remediation.** The design study lists **five** proof-out remediations. The fifth —
> the **4× survival-wind hold-down anchors (survival uplift 9.2 kN → SF 3.9)** — is a **fabricated
> steel item, NW-RR-006, and lives in BP-04**, not here. Its anchor bolts are captured in
> `fastener_schedule.md` (ASTM F1554) for a consolidated buy, but the brackets themselves are BP-04
> scope. BP-05 therefore carries **4 of the 5 remediations**.

**Gate rule.** NW-CO-003, NW-CO-004, NW-CO-005 and NW-CO-008 are **MANDATORY for the buildable v1**.
NW-CO-013 (48 V pack) is **MANDATORY only for the off-grid v2**; **v1 may run grid + UPS** (see the
roadmap, `MECHANICAL_DESIGN.md` §9). A bid that substitutes a baseline part for any of the four v1
remediations shall be raised as an **RFI/deviation** and is not accepted without engineering sign-off.

**Optional line.** **NW-CO-009 counterweights are OPTIONAL** — the selected topology is the
**counterweight-FREE GEM** (torque proof SF 2.5/2.6; deletes 15.4 kg + 29 % RA inertia). Buy the
counterweight set **only** if the counterweighted variant is elected. See §6.

---

## 1. Scope

BP-05 covers **every purchased (off-the-shelf) component** in the NIGHTWATCH mount + roll-off
enclosure that is not fabricated under BP-01…BP-04. The buyer:

1. **Procures the drivetrain** — the two Harmonic Drive LLC strain-wave gears (NW-CO-001 RA,
   NW-CO-002 DEC), the two NEMA17 + 27:1 planetary stepper packages (NW-CO-006), and the two
   microstepping drivers / controller (NW-CO-007).
2. **Procures the four v1 remediation items** — the angular-contact bearing pairs (NW-CO-003 7008,
   NW-CO-004 7006), the on-axis absolute encoders (NW-CO-005), and the temperature-compensated
   focuser (NW-CO-008). See §0.
3. **Procures the enclosure motion + weather hardware** — V-groove track wheels (NW-CO-010), the
   roll-off roof drive / gate operator (NW-CO-011), and the metal roofing panel + flashing (NW-CO-012).
4. **Procures the power system** — the 48 V LiFePO4 battery pack + solar (NW-CO-013), mandatory for
   off-grid v2.
5. **Consolidates the fastener buy** — ASTM A574 socket-head cap screws and ASTM F1554 anchor bolts
   across all packages (NW-CO-014 → `fastener_schedule.md`).
6. **Optionally** procures the cast-iron counterweight set (NW-CO-009) if the counterweighted variant
   is bid.
7. Delivers **manufacturer certificates of conformance (CoC), datasheets, and interface confirmations**
   (bearing precision class, encoder protocol, drive bore/torque) so each buy is traceable against the
   fixed fabricated interfaces.

**Out of scope for BP-05** (the fabricated parts these items bolt into — separate packages):

| Interface | Fabricated under | BP-05 item that mates to it |
|---|---|---|
| RA / DEC axis housings, bearing seats, drive registers | BP-01 (machining) | NW-CO-001/-002 drives; NW-CO-003/-004 bearings; NW-CO-005 encoders |
| RA / DEC drive spindles (carry bearing inner races, couple the strain-wave gears) | BP-02 (turned parts) | NW-CO-001/-002 drives; NW-CO-003/-004 bearings |
| Pier / adapter plate | BP-03 (pier) | NW-CO-014 anchors (F1554) via `fastener_schedule.md` |
| Roll-off roof frame, rails, wheel brackets, drive bracket, **wind hold-downs** | BP-04 (roll-off) | NW-CO-010 wheels; NW-CO-011 drive; NW-CO-012 roofing; F1554 hold-down anchors |

---

## 2. Data package the buyer receives (per MIL-STD-31000A)

| Item | Format / standard | Role |
|---|---|---|
| `SCHEDULE.md` | Markdown | The **purchase table**: item, NW-CO-xx, qty, key specs (from `partspec`), supplier CLASS + representative catalogue part numbers, remediation flags, per-item procurement notes. |
| `fastener_schedule.md` | Markdown | Consolidated **ASTM A574 SHCS + ASTM F1554 anchor** buy across BP-01…BP-04 interfaces. |
| `cots_schedule.csv` (rows NW-CO-001…-014, + NW-PF-004) | CSV / XLSX (BOM per ASME Y14.34) | Machine-readable buy list generated from the parts registry. |
| `master_bom.csv` (BP-05 rows) | CSV / XLSX | Roll-up into the full-project BOM. |
| Interface dimensions | Repeated in `SCHEDULE.md` from BP-01…BP-04 control drawings (PDF) + STEP AP242 solids | Fixed mating dims the catalogue part must satisfy (bearing bores/OD, drive bores, wheel bores, anchor holes). |

**Order of precedence.** For a purchased part the **manufacturer's datasheet governs the part's own
dimensions and ratings**; the **fixed fabricated interface (BP-01…BP-04 control drawing / STEP AP242
solid) governs the mating dimension the part must fit.** Where a catalogue part cannot meet a fixed
interface, the buyer raises an **RFI before ordering** — the interface is not changed to suit stock.
General tolerances of any buyer-detailed adapter per **ISO 2768**; fits per **ISO 286** (bearing seats
H7 / journals j6 are set by BP-01/BP-02, not here). All representative catalogue numbers below are
**"representative — confirm"**: they establish the class, rating, and interface, **not** a sole source.

---

## 3. Line-item summary (source: `partspec.parts_for('BP-05')`)

All 14 lines are COTS — no fabrication drawing, no stock mass. Key specs are quoted from the parts
registry (`gen/partspec.py`, traced to `calc/params.py` where marked SOURCED). Full specs, suppliers,
and representative catalogue numbers are in `SCHEDULE.md`.

| Part no. | Name | Qty | Headline spec (from `partspec`) | Class | Status |
|---|---|---:|---|---|---|
| **NW-CO-001** | Harmonic drive, RA | 1 | CSF-32-100-2A-GR — ratio 100, rated 127 Nm [93.7 lbf·ft], peak 343 Nm [253 lbf·ft], hollow bore Ø80.0 mm [3.150 in] | Strain-wave (sole-class) | Core |
| **NW-CO-002** | Harmonic drive, DEC | 1 | CSF-25-80-2A-GR — ratio 80, rated 70 Nm [51.6 lbf·ft], peak 186 Nm [137 lbf·ft], hollow bore Ø64.0 mm [2.520 in] | Strain-wave (sole-class) | Core |
| **NW-CO-003** | Angular-contact bearing 7008 (RA pair) | 2 | Bore Ø40 mm [1.575 in], OD Ø68 mm [2.677 in], width 15 mm [0.591 in], DB back-to-back | Super-precision ABEC-7 | **REMEDIATION (v1 mandatory)** |
| **NW-CO-004** | Angular-contact bearing 7006 (DEC pair) | 2 | Bore Ø30 mm [1.181 in], OD Ø55 mm [2.165 in], width 13 mm [0.512 in], DB back-to-back | Super-precision ABEC-7 | **REMEDIATION (v1 mandatory)** |
| **NW-CO-005** | On-axis absolute encoder (RA + DEC) | 2 | Resolution < 1″; interface BiSS-C / SSI | Absolute ring + readhead | **REMEDIATION (v1 mandatory)** |
| **NW-CO-006** | Stepper NEMA17 + 27:1 planetary | 2 | 1.8° step, 27:1 planetary, Irun 1.5 A / Igoto 2.0 A, holding 0.45 Nm | Stepper + gearhead | Core |
| **NW-CO-007** | Motor driver (TMC5160) / OnStepX board | 2 | Irun 1.5 A, Igoto 2.0 A, 16 microsteps | Microstepping driver | Core |
| **NW-CO-008** | Temperature-compensated focuser | 1 | Temp coeff −2.5 steps/°C (ASSUMED) | Motorised absolute focuser | **REMEDIATION (v1 mandatory)** |
| **NW-CO-009** | Counterweights (5 kg ×2, 2.5 kg ×1) | 3 | 12.5 kg total available; shaft Ø31.75 mm [1.250 in] × 457.2 mm [18.000 in] (BP-02) | Cast iron | **OPTIONAL** |
| **NW-CO-010** | V-groove track wheels | 8 | Ø~4 in [~101.6 mm], ≥150 kg [≥331 lb] each | Steel V-groove | Core |
| **NW-CO-011** | Roof drive (gate operator) | 1 | Move force 235 N [52.8 lbf], SF 2.1 vs ~500 N [112 lbf] drive; fail-safe + wind interlock | Sliding-gate operator | Core |
| **NW-CO-012** | Metal roofing panel + flashing | 1 | Area ≈ 9.0 m² [≈96.9 ft²] (3.0 × 3.0 m) | Standing-seam / corrugated steel | Core |
| **NW-CO-013** | 48 V LiFePO4 battery pack + solar | 1 | 48 V bus, ~5 kWh, 13.4 h autonomy | LiFePO4 + PV | **REMEDIATION (v2 mandatory; v1 grid+UPS)** |
| **NW-CO-014** | Fastener schedule (SHCS, anchors) | 1 | ASTM A574 SHCS + ASTM F1554 Gr36 anchors — see `fastener_schedule.md` | Fastener buy | Core |

---

## 4. Cross-package interfaces the buyer must satisfy

Each purchased part fits a **fixed** fabricated feature. The buyer confirms the catalogue part meets
the mating dimension before ordering; **the mating dimension is not adjustable to suit stock.**

| BP-05 item | Fits (fixed by) | Fixed mating dimension |
|---|---|---|
| NW-CO-001 (CSF-32) | RA housing drive register (NW-MH-001) + RA spindle (NW-TP-002) | Drive bore Ø80.0 mm [3.150 in]; wave-gen register; 8 × M4 on Ø104 mm [4.094 in] PCD |
| NW-CO-002 (CSF-25) | DEC housing drive register (NW-MH-002) + DEC spindle (NW-TP-003) | Drive bore Ø64.0 mm [2.520 in]; 8 × M4 on Ø83 mm [3.268 in] PCD |
| NW-CO-003 (7008 pair) | RA housing seat H7 (NW-MH-001) + RA journal j6 (NW-TP-002) | Seat bore Ø68 mm [2.677 in] H7; journal Ø40 mm [1.575 in] j6 |
| NW-CO-004 (7006 pair) | DEC housing seat H7 (NW-MH-002) + DEC journal j6 (NW-TP-003) | Seat bore Ø55 mm [2.165 in] H7; journal Ø30 mm [1.181 in] j6 |
| NW-CO-005 (encoder ring) | RA / DEC axis (on-axis, one per axis) | Ring bore to clear the axis; readhead standoff — **ASSUMED, confirm to axis geometry** |
| NW-CO-010 (V-groove wheels) | Wheel axle brackets (NW-RR-004), M16 axle | Wheel bore for M16 [Ø16 mm] axle; V-groove to match rail (NW-RR-003) |
| NW-CO-011 (roof drive) | Drive bracket (NW-RR-005) | Rack/chain mount; 180 kg [397 lb] roof; end-stop + wind interlock |
| NW-CO-012 (roofing) | Roof frame + purlins (NW-RR-001/-002) | ≈9.0 m² [≈96.9 ft²] skin; edge/ridge flashing to frame |
| F1554 anchors (`fastener_schedule.md`) | Pier top plate (NW-PF-002) + wind hold-downs (NW-RR-006) | 4 × Ø0.75 in [Ø19.05 mm] each group; PE to size final |

---

## 5. Buyer deliverables

1. **Purchase orders** placed against `SCHEDULE.md` and `fastener_schedule.md`, with the **four v1
   remediation lines** (NW-CO-003/-004/-005/-008) confirmed as the remediated parts, not baseline.
2. **Certificates of conformance (CoC) / datasheets** for every line, and specifically:
   - Bearings (NW-CO-003/-004): **precision-class cert (≥ ABEC-7 / P4), DB-set matching cert, preload
     class** — confirming they fit the H7 seats / j6 journals set by BP-01/BP-02.
   - Encoders (NW-CO-005): **BiSS-C (or SSI) protocol confirmation and accuracy/resolution
     (sub-arcsec)** datasheet — confirming < 1″ on-axis.
   - Harmonic drives (NW-CO-001/-002): **rated/peak torque, ratio, and hollow-bore** datasheet —
     confirming Ø80.0 / Ø64.0 mm bores and the 8 × M4 PCDs.
   - Roof drive (NW-CO-011): **fail-safe behaviour + wind-interlock capability** confirmation.
   - 48 V pack (NW-CO-013): **capacity (kWh), 48 V bus, cell chemistry (LiFePO4), safety listing**.
3. **Interface-fit confirmation** — a short matrix confirming each catalogue part meets the fixed
   mating dimension in §4 (raise an RFI where it does not).
4. **Fastener CoC** — ASTM A574 SHCS mill cert / CoC and ASTM F1554 Gr36 anchor mill cert +
   galvanize (ASTM A123) cert, per `fastener_schedule.md`.
5. **Deviation / RFI log** — every representative catalogue number confirmed to an actual ordered part,
   and every ASSUMED value (§6) resolved before order.

---

## 6. ASSUMED design-intent / representative selection — buyer & PE to confirm (NOT final)

Carried as **ASSUMED design-intent** or **representative catalogue selection** in the parts registry;
**not** released procurement decisions. Confirm before ordering:

- **All representative catalogue part numbers** in `SCHEDULE.md` (SKF/NSK/FAG bearings, Renishaw/
  Heidenhain encoder, LiftMaster/US-Automatic gate operator, ZWO/Optec/Pegasus focuser, EG4/Battle-Born
  48 V pack, DuraGates/CasterHQ wheels) are **"representative — confirm"**. They fix the **class,
  rating, and interface**, not a sole source. Buyer confirms availability, lead time, and fit.
- **On-axis encoder ring geometry & interface** (NW-CO-005) — ring bore, readhead standoff, and
  BiSS-C vs SSI are **ASSUMED**; confirm against the actual RA/DEC axis geometry and the OnStepX /
  controller input.
- **Roof drive product & sizing** (NW-CO-011) — the **gate-operator class, fail-safe mode, and wind
  interlock** are **ASSUMED design-intent** (enclosure proof: 235 N [52.8 lbf] move force, SF 2.1);
  the specific operator, its duty rating for the 180 kg [397 lb] roof, and the interlock logic are
  **PE/controls to confirm**.
- **V-groove wheel product & rail match** (NW-CO-010) — Ø4 in [101.6 mm], ≥150 kg [≥331 lb]/wheel is
  **ASSUMED**; confirm the V-profile matches the BP-04 box-track section (NW-RR-003) and the ≥4× load
  factor on the 180 kg roof + snow.
- **Roofing panel type/gauge & flashing** (NW-CO-012) — standing-seam vs corrugated, gauge, and
  fastening are **ASSUMED**; confirm against the ASCE 7 snow/wind case and the purlin spacing (BP-04).
- **48 V pack sizing / v1 vs v2** (NW-CO-013) — ~5 kWh / 13.4 h autonomy is **ASSUMED**; the DGX duty
  cycle drives ~59 % of the load. **v1 may run grid + UPS**; the pack is **mandatory only for off-grid
  v2**.
- **Temp-comp focuser coefficient & coupling** (NW-CO-008) — the −2.5 steps/°C coefficient is
  **ASSUMED**; confirm the focuser couples to the OTA drawtube and the temperature-compensation curve
  against the 22 K night swing.
- **Motor + gearhead + driver products** (NW-CO-006/-007) — NEMA17 1.8° + 27:1 planetary + TMC5160 /
  OnStepX are **SOURCED for ratings** (`P.MOTOR`) but the **specific catalogue motor, gearhead, and
  controller board are representative** — confirm.
- **Counterweights are OPTIONAL** (NW-CO-009) — omitted in the counterweight-FREE build; buy only if
  the counterweighted variant is elected.
- **Fastener grades, lengths, and torque** (NW-CO-014) — ASTM A574 SHCS and ASTM F1554 Gr36 grades
  are **ASSUMED design-intent**; **lengths, quantities, and preload/torque are ASSUMED and are
  bidder/PE to confirm** (weld sizes and any structural anchor sizing are **PE** items). See
  `fastener_schedule.md`.

---

## 7. References

- Parts registry: `design/mechanical/tender/gen/partspec.py` → `parts_for('BP-05')` (single source of truth).
- BOM / COTS: `design/mechanical/tender/bom/{cots_schedule,master_bom}.csv`.
- Design basis: `design/mechanical/MECHANICAL_DESIGN.md` §9 (selected configuration, cost deltas, the
  5 remediations, v1/v2 roadmap); `design/mechanical/tradestudy/SECTION.md` (drive/encoder/bearing/
  enclosure/power selection rationale, disqualification gate).
- Interfaces: BP-01 (`../BP-01_mount_machining/`), BP-02 (`../BP-02_turned_parts/`),
  BP-03 (`../BP-03_pier_foundation/`), BP-04 (roll-off) — fixed mating dimensions.
- Standards register: MIL-STD-31000A (TDP); ASME Y14.34 (associated lists/BOM), Y14.100, Y14.24,
  Y14.1; ISO 286 (fits), ISO 2768 (general tolerances); ASTM A574 (SHCS), ASTM F1554 Gr36 (anchors),
  ASTM A123 (galvanize). Encoder interface BiSS-C / SSI. Formats: STEP ISO 10303 AP242 (interface
  solids), PDF (interface drawings), CSV/XLSX (BOM).
