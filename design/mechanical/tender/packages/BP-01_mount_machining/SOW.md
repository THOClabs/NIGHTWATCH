# BP-01 — Statement of Work: Mount Head Machining (CNC 6061-T6)

> **ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION**

| Field | Value |
|---|---|
| Package | BP-01 — Mount head machining |
| Parts | NW-MH-001 (RA housing), NW-MH-002 (DEC housing + saddle), NW-MH-003 (saddle clamp bar) |
| Process | CNC mill, 3-axis |
| Material | 6061-T6 aluminium plate per **ASTM B209 / AMS-QQ-A-250/11** |
| Finish | **MIL-A-8625F** Type III hardcoat anodize, 0.002 in, Class 1 (clear) |
| Issue date / rev | 2026-08-06 / A |

**Purpose.** This SOW specifies the machining, tolerancing, finishing, and certification requirements
for the three fabricated mount-head parts. It is read with the STEP ISO 10303 AP242 solid master (CNC
authority), the NW-MH control drawings (PDF), and `acceptance.md`. All dimensions are dual-unit,
**mm primary, inch in brackets**, drawn from the parts registry (`partspec.parts_for('BP-01')`) and
`cut_list.csv` — no dimension herein is invented.

**Standards applied.** MIL-STD-31000A (TDP); **ASME Y14.5-2018** (GD&T); ASME Y14.100 (drawing
practices), Y14.24 (drawing types), Y14.1 (sheet/title block); **ASME Y14.36 & ASME B46.1** (surface
texture); **ISO 286** (H7/js6 fits); **ISO 2768-mK** (general tolerances); **MIL-A-8625F** (hardcoat
anodize); **ASTM B209 / AMS-QQ-A-250/11** (6061-T6 plate).

---

## 1. General requirements (all three parts)

1. **Material & certification.** 6061-T6 plate per **ASTM B209 / AMS-QQ-A-250/11**, T6 temper.
   Furnish mill certification and Certificate of Conformance with **heat/lot traceability**; mark each
   part with part number and revision per ASME Y14.100.
2. **General tolerance.** **ISO 2768-mK** (medium, fine machining class) on all dimensions not
   otherwise toleranced. Break all sharp edges 0.3–0.5 mm [0.012–0.020 in] unless a sealing/mating
   face is noted; no burrs.
3. **GD&T.** Interpret all geometric callouts per **ASME Y14.5-2018**. Datum reference frames are
   defined per part below. Surface-texture symbols per **ASME Y14.36**, values per **ASME B46.1**.
4. **Fits.** Bearing seats and registers per **ISO 286**: bores at **H7** (see per-part tables);
   pilot/register bores at H8 unless the mating part dictates otherwise (**ASSUMED — bidder/PE to
   confirm**).
5. **Stress relief.** Rough-machine, then stress-relieve before finish-machining the bearing seats to
   hold the H7 tolerance through anodize (**ASSUMED best practice — bidder to propose**).
6. **Finish sequence.** Apply **Type III hardcoat anodize per MIL-A-8625F Class 1 (clear), 0.002 in
   [~0.051 mm]** *after* final machining. **Mask** the bearing seats, drive registers, and threaded
   holes. The hardcoat builds ~0.001 in [~0.025 mm] **per side**, which consumes the H7 band — so the
   **H7 bores shall be dimensioned and verified in the as-delivered (post-mask/post-anodize) state**
   (**ASSUMED masking approach — bidder/PE to confirm**; see `acceptance.md`).
7. **Surface finish.** Part-level surface finish per the control drawing: **Ra 1.6 µm [63 µin]** on
   NW-MH-001 / NW-MH-002, **Ra 3.2 µm [125 µin]** on NW-MH-003. Bearing-seat bores are typically held
   finer at **Ra ≤ 0.8 µm [32 µin]** (**ASSUMED design-intent — bidder/PE to confirm**).

---

## 2. NW-MH-001 — RA (polar) axis housing

**Drawing:** NW-MH-001 (rev A). **Stock:** plate **203.2 mm [8.000 in] × 203.2 mm [8.000 in] ×
76.2 mm [3.000 in]**, cut allowance 3.0 mm, stock mass 8.50 kg (`cut_list.csv` row 2). **Wall:**
8.0 mm [0.315 in]. Pocket-lightening is permitted at the bidder's option **provided the bore and
flange datums are retained**.

**Datum reference frame (ASME Y14.5-2018):**
- **Datum A** — primary flange / mounting face (planar; controls the housing to the pier-adapter and
  DEC-head interface).
- **Datum B** — bearing-seat bore axis, Ø68 H7 (the axis of rotation).
- **Datum C** — drive-register bore or a designated flange hole, for clocking the bolt pattern.

**Critical features:**

| Feature | Nominal (mm [in]) | Tolerance / fit | GD&T (per Y14.5) | Ra |
|---|---|---|---|---|
| Bearing seat bore (7008) | Ø **68.000 – 68.030** [Ø2.677] | **H7** per ISO 286 (+0.030 / 0) | Ⓐ datum B; cylindricity *(value ASSUMED)* | ≤0.8 µm (ASSUMED) |
| Bore-to-flange perpendicularity | — | — | ⟂ bore axis to Datum A *(value ASSUMED — PE)* | — |
| Two-seat coaxiality (bearing span 76.2 mm [3.000 in]) | — | — | ◎ seats coaxial *(value ASSUMED — PE)* | — |
| Drive register bore (CSF-32) | Ø **80.0** [3.150] | H8 pilot (ASSUMED) | positional to B | 1.6 µm |
| Flange face flatness | — | — | ▱ **0.05 mm** to Datum A | 1.6 µm |
| Flange bolt circle | Ø **104.0** [4.094], **8 holes** | position *(ASSUMED)* | ⊕ to B/C *(ASSUMED)* | — |
| Corner mounting holes | **4 × M6** | ISO 2768-mK | — | — |

**Provenance / flags.** Outer/wall/depth = P.RA_HOUSING (SOURCED); bearing seat = **7008 remediation**;
**flange PCD Ø104 mm and 8-hole pattern are DERIVED (~1.3× bore) → ASSUMED design-intent, bidder/PE
to confirm.** Perpendicularity + coaxiality are the stiffness-critical callouts (§4).

**Interfaces:** bearing seat ← NW-CO-003 (7008 DB pair, OD 68); drive register ← NW-CO-001 (CSF-32,
bore 80) via NW-TP-002; through-bore ← NW-CO-005 encoder ring.

---

## 3. NW-MH-002 — DEC axis housing + Losmandy-D saddle

**Drawing:** NW-MH-002 (rev A). **Stock:** plate **152.4 mm [6.000 in] × 152.4 mm [6.000 in] ×
63.5 mm [2.500 in]**, cut allowance 3.0 mm, stock mass 3.98 kg (`cut_list.csv` row 3). **Wall:**
8.0 mm [0.315 in]. Integral Losmandy-D dovetail saddle.

**Datum reference frame (ASME Y14.5-2018):**
- **Datum A** — flange / mounting face (interfaces to the RA head).
- **Datum B** — bearing-seat bore axis, Ø55 H7 (DEC axis of rotation).
- **Datum C** — Losmandy-D saddle dovetail centre-plane.

**Critical features:**

| Feature | Nominal (mm [in]) | Tolerance / fit | GD&T (per Y14.5) | Ra |
|---|---|---|---|---|
| Bearing seat bore (7006) | Ø **55.000 – 55.030** [Ø2.165] | **H7** per ISO 286 (+0.030 / 0) | Ⓐ datum B; cylindricity *(ASSUMED)* | ≤0.8 µm (ASSUMED) |
| Bore-to-flange perpendicularity | — | — | ⟂ bore axis to Datum A *(ASSUMED — PE)* | — |
| Two-seat coaxiality (bearing span 63.5 mm [2.500 in]) | — | — | ◎ seats coaxial *(ASSUMED — PE)* | — |
| Drive register bore (CSF-25) | Ø **64.0** [2.520] | H8 pilot (ASSUMED) | positional to B | 1.6 µm |
| Flange face flatness | — | — | ▱ **0.05 mm** to Datum A | 1.6 µm |
| Flange bolt circle | Ø **83.0** [3.268] | position *(ASSUMED)* | ⊕ to B/C *(ASSUMED)* | — |
| Losmandy-D saddle width | **76.2** [3.000] | ISO 2768-mK *(profile ASSUMED)* | profile to Datum C *(ASSUMED)* | 1.6 µm |
| Dovetail angle | **15°** | ± *(ASSUMED)* | — | 1.6 µm |

**Provenance / flags.** Outer/wall/depth = P.DEC_HOUSING (SOURCED); bearing seat = **7006 remediation**;
**Losmandy-D saddle geometry (76.2 mm width, 15° dovetail, undercut/relief) is ASSUMED to a standard
Losmandy-D profile — bidder/PE to confirm against a reference dovetail.** Flange PCD Ø83 mm is
ASSUMED design-intent.

**Interfaces:** bearing seat ← NW-CO-004 (7006 DB pair, OD 55); drive register ← NW-CO-002 (CSF-25,
bore 64) via NW-TP-003; saddle + NW-MH-003 clamp ← OTA dovetail.

---

## 4. NW-MH-003 — DEC saddle clamp bar

**Drawing:** NW-MH-003 (rev A). **Stock:** plate **101.6 mm [4.000 in] × 76.2 mm [3.000 in] ×
25.4 mm [1.000 in]**, cut allowance 3.0 mm, stock mass 0.53 kg (`cut_list.csv` row 4).

**Datum reference frame:** Datum A = clamp mating face; Datum B = dovetail bevel face.

| Feature | Nominal (mm [in]) | Tolerance | Ra |
|---|---|---|---|
| Length | **101.6** [4.000] | ISO 2768-mK | 3.2 µm |
| Width | **76.2** [3.000] | ISO 2768-mK | 3.2 µm |
| Thickness | **25.4** [1.000] | ISO 2768-mK | 3.2 µm |
| Clamp screws | **2 × M8** | ISO 2768-mK | — |
| Dovetail bevel | **15°** (matching NW-MH-002) | ± *(ASSUMED)* | 3.2 µm |

> **ASSUMED design-intent — bidder/PE to confirm.** The **entire NW-MH-003 clamp bar** is carried as
> ASSUMED design-intent: the Losmandy-D clamp is not dimensioned in the repository. It pairs with the
> NW-MH-002 saddle to clamp the OTA dovetail; the shop shall confirm the mating profile and clamp
> travel before production.

---

## 5. Bearing-seat callout block (stiffness remediation — grounding)

The two housing bearing seats (**Ø68 H7 on NW-MH-001, Ø55 H7 on NW-MH-002**) are sized for
**matched angular-contact bearing pairs — 7008 (RA, OD 68 mm) and 7006 (DEC, OD 55 mm) — in a
back-to-back (DB), preloaded arrangement** (NW-CO-003 / NW-CO-004, BP-05). This is the proven
**remediation of the deep-groove 6008/6006 baseline**, which the stiffness/deflection proof identified
as ~98% of the 43.5″ pointing-deflection FAIL against the 5″ target (MECHANICAL_DESIGN.md §9; trade
study item 8).

Because moment stiffness — not load rating — governs, the machining controls that matter are:

- **Coaxiality** of the two end seats over the bearing span (76.2 mm RA / 63.5 mm DEC) — GD&T value
  **ASSUMED, PE to set**.
- **Perpendicularity** of each seat axis to the flange mounting face (Datum A) — **ASSUMED, PE to set**.
- **H7 bore roundness/cylindricity and Ra ≤ 0.8 µm** for correct outer-ring seating.
- **Preload method** (ground spacer/shim set vs. clamped ring) — **ASSUMED design-intent; bidder/PE to
  detail.** The housing shall provide an axial shoulder or clamp land per the released design.

---

## 6. Finishing

- **Type III hardcoat anodize per MIL-A-8625F Class 1 (clear), 0.002 in [~0.051 mm]** on all external
  surfaces after final machining.
- **Mask:** bearing seats (Ø68 H7, Ø55 H7), drive registers (Ø80, Ø64), and all threaded holes.
- Post-anodize, re-verify the masked H7 bores are within tolerance (see `acceptance.md`).
- Furnish an anodize certificate with coating-thickness record.

---

## 7. Submittals & deliverables

1. Finished, anodized parts (qty 1 each): NW-MH-001, NW-MH-002, NW-MH-003.
2. Material cert / CoC (ASTM B209 / AMS-QQ-A-250/11) with heat/lot traceability.
3. Anodize certificate (MIL-A-8625F Type III).
4. First-Article Inspection report per `acceptance.md` (CMM for every H7 bore + flatness).
5. RFI log resolving every ASSUMED value before production.

---

## 8. ASSUMED design-intent register (this SOW)

| Item | Part(s) | Status |
|---|---|---|
| Flange PCD & bolt pattern (Ø104/8-hole, Ø83) | NW-MH-001, -002 | ASSUMED — bidder/PE to confirm |
| GD&T coaxiality / perpendicularity / position values | NW-MH-001, -002 | ASSUMED — PE to set |
| Bearing-seat surface finish (Ra ≤ 0.8 µm) & preload method | NW-MH-001, -002 | ASSUMED — bidder/PE to detail |
| Drive-register fit class (H8 pilot) | NW-MH-001, -002 | ASSUMED — bidder/PE to confirm |
| Losmandy-D saddle profile / undercut / 15° dovetail | NW-MH-002 | ASSUMED — confirm vs reference dovetail |
| Entire saddle clamp bar geometry | NW-MH-003 | ASSUMED design-intent |
| Encoder-ring register location | NW-MH-001, -002 | ASSUMED — preserve through-bore |
| Post-anodize masking approach on H7 bores | all | ASSUMED — bidder/PE to confirm |
