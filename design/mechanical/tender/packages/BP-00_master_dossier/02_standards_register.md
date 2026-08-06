# 02 — Standards Register

**Document:** BP-00 / 02 — Standards Register, Rev A
**Status:** **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**
**Units:** mm primary, [inch] in brackets.

Every standard is cited **by number**. Bidders shall comply with the latest issue in
force at bid date unless a specific edition is named. Where a standard is marked
*ASSUMED / PE-to-confirm*, the design does not yet fix the governed value and the
bidder/PE shall confirm it before construction.

---

## 1. Technical Data Package

| Standard | Governs | Applies to |
|---|---|---|
| **MIL-STD-31000A** | Technical Data Package: product-definition data set, associated lists, data-management "issued for" states (this package is issued at the *bid* state) | Whole dossier (BP-00 … BP-05) |

## 2. Drawing practice, GD&T, and surface texture

| Standard | Governs | Applies to |
|---|---|---|
| **ASME Y14.5-2018** | Geometric dimensioning & tolerancing (datums, feature control frames, position/flatness/concentricity) | BP-01, BP-02, BP-03, BP-04 machined/fabricated features |
| **ASME Y14.100** | Engineering drawing practices (general) | All control drawings `NW-xx` |
| **ASME Y14.24** | Drawing types (detail, assembly, control) — these sheets are *bid control drawings* | All control drawings |
| **ASME Y14.34** | Associated lists / bill of material (parts list, data list) | Master BOM, cut list, COTS schedule (XLSX) |
| **ASME Y14.1** | Sheet size and title-block format | All control drawings (ANSI B-class sheet, ASME-style title block) |
| **ASME Y14.36** | Surface texture symbols on drawings | BP-01, BP-02 (Ra callouts), BP-03 adapter |
| **ASME B46.1** | Surface texture (measurement of roughness Ra) | Verification of BP-01/BP-02 finish (see ITP) |

**ASSUMED / PE-to-confirm — GD&T tolerance values.** The registry states general
tolerances (ISO 2768-mK) and critical callouts (H7 bores, h6/j6 journals,
concentricity 0.02 TIR, flange flatness 0.05); specific **feature-control-frame
values per Y14.5** (true position of bolt patterns, datum references) are ASSUMED
design-intent and shall be confirmed by the PE on the released drawings.

## 3. Fits and general tolerances

| Standard | Governs | Applies to |
|---|---|---|
| **ISO 286** | Limits & fits — **H7** bearing bores, **js6/j6/h6** journals | BP-01 seats (Ø68.0 mm [2.677 in] H7 RA; Ø55.0 mm [2.165 in] H7 DEC), BP-02 journals |
| **ISO 2768** (class **mK**) | General linear and angular tolerances for un-toleranced dimensions | BP-01, BP-02, BP-03, BP-04 |

## 4. Materials

| Standard | Governs | Applies to |
|---|---|---|
| **ASTM B209 / AMS-QQ-A-250/11** | 6061-T6 aluminium plate | BP-01 (NW-MH-001/002/003), BP-03 adapter (NW-PF-003) |
| **ASTM A582** | 303 free-machining stainless bar | BP-02 (NW-TP-001/002/003) |
| **ASTM A36** | Structural carbon-steel plate | BP-03 top plate (NW-PF-002); BP-04 rails/brackets (NW-RR-003/004/005/006) |
| **ASTM A500 Gr B** | Cold-formed welded HSS | BP-04 roof frame & purlins (NW-RR-001/002) |
| **ASTM A615 Gr60** | Deformed rebar | BP-03 pier cage (NW-PF-001) — *schedule ASSUMED, PE-to-confirm* |
| **ASTM F1554 Gr36** | Anchor bolts (headed/threaded) | BP-03 anchor set (NW-PF-004); BP-04 hold-down anchors — *sizing ASSUMED, PE-to-confirm* |
| **ASTM A574** | Alloy-steel socket-head cap screws | Fastener schedule (NW-CO-014), all bolted joints |

## 5. Finishes

| Standard | Governs | Applies to |
|---|---|---|
| **MIL-A-8625F Type III** | Hardcoat anodize (Class 1 clear, 0.002 in [0.051 mm]) | BP-01 aluminium (NW-MH-001/002/003), BP-03 adapter (NW-PF-003) |
| **ASTM A123** | Hot-dip galvanizing of steel | BP-03 top plate, anchor set; BP-04 all steel (NW-RR-001…006) |
| **ASTM A967** | Passivation of stainless (nitric) | BP-02 (NW-TP-001/002/003) |

## 6. Welding and NDE

| Standard | Governs | Applies to |
|---|---|---|
| **AWS A2.4** | Weld and NDE symbols on drawings | BP-04 weld callouts; BP-03 (if any steel welding) |
| **AWS D1.1** | Structural steel welding code, incl. **WPS / PQR and welder qualification** | BP-04 (NW-RR-001…006) |
| **AWS D1.2** | Structural aluminium welding | *Conditional* — only if any aluminium is welded (BP-01 items are machined, not welded, at baseline) |

**ASSUMED / PE-to-confirm — weld sizes.** Fillet/groove sizes, joint details, and NDE
extent for BP-04 are ASSUMED design-intent (registry: "fully welded, gusseted"
corners). The bidder's **WPS/PQR** and the PE shall fix weld sizes and NDE scope
against the confirmed ASCE 7 loads.

## 7. Foundation and loads

| Standard | Governs | Applies to |
|---|---|---|
| **ACI 318** (incl. **Ch. 17** anchoring-to-concrete) | Reinforced-concrete design; cast-in / post-installed anchor capacity | BP-03 pier (NW-PF-001), anchor set (NW-PF-004), roof hold-down anchors |
| **ACI 301** | Specification for structural concrete (materials, placement, cylinder testing) | BP-03 concrete work |
| **ASCE 7** | Minimum design loads — **wind, snow, seismic** | BP-03 pier; BP-04 roof (survival-wind uplift & snow cases govern) |

**PE-stamp gate.** BP-03 (pier + anchors) and the BP-04 roof structure are
**construction-gated on a PE-stamped analysis** against ASCE 7 loads confirmed for
the permitted site. Rebar schedule, anchor sizing, member sizing, and weld sizing are
ASSUMED design-intent until stamped.

## 8. Deliverable data formats

| Standard / format | Governs | Applies to |
|---|---|---|
| **STEP ISO 10303 AP242** | 3-D product model exchange for CNC | BP-01, BP-02, BP-03 machined items (`cad/*.scad` → STEP master) |
| **DXF / DWG** | 2-D flat-pattern cutting geometry | BP-03/BP-04 laser/waterjet-cut plates |
| **PDF** | Released drawing sheets | All `NW-xx` control drawings |
| **XLSX** | Bill of material / associated lists / COTS schedule | Master BOM, cut list, COTS schedule |

---

*Standards are cited to establish acceptance criteria only; they do not change any
dimension in the frozen technical baseline. Where a standard and a control drawing
conflict on a value, the **drawing/partspec governs** and the conflict is an RFI item.*
