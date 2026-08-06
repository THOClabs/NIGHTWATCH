"""
NIGHTWATCH tender — the parts registry (single source of truth for the BOM,
cut lists, and fabrication drawings).

Every fabricated part's controlling dimensions are pulled from the proven
``design/mechanical/calc/params.py`` so the tender cannot drift from the
validated design. Where the design does not yet fix a value a fabricator needs
(roof member sizes, weld sizes, GD&T tolerance values, surface finish), it is
stated here as **ASSUMED design-intent** for the bidder to confirm — never as a
final number.

Units: dimensions are held in MILLIMETRES (the CAD/shop convention); the drawing
and BOM engines render dual inch + mm. Masses in kg, computed from stock volume x
material density (the quantity you *order*, not the finished-part net mass).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from design.mechanical.calc import params as P
from design.mechanical.calc import units as u

MM3_PER_M3 = 1.0e9

# Trades / bid packages -----------------------------------------------------
PACKAGES = {
    "BP-01": ("Mount head machining", "CNC machining (6061-T6 aluminium)"),
    "BP-02": ("Precision turned parts", "CNC / manual turning (303 stainless)"),
    "BP-03": ("Pier & foundation", "Reinforced concrete + structural steel"),
    "BP-04": ("Roll-off roof ('disappearing turret')", "Structural steel fab + rail/drive install"),
    "BP-05": ("COTS procurement schedule", "Purchase (buy-to-print / off-the-shelf)"),
}


@dataclass(frozen=True)
class Part:
    part_no: str
    name: str
    package: str                       # BP-01..05
    material: str                      # spec string incl. ASTM/AMS callout
    stock_form: str                    # human stock description
    stock: tuple                       # ('plate', L, W, T) | ('round', dia, len) | ('hss', o, wall, len) | ('cots',)
    process: str                       # CNC mill / turn / weld / cast-in-place / purchase
    finish: str                        # anodize / galv / passivate / none / n-a
    tolerance: str                     # general + critical (H7 bores etc.)
    ra_um: float | None                # surface finish, micrometres (None = n/a)
    qty: int
    key_dims_mm: dict = field(default_factory=dict)
    provenance: str = ""               # sourced/derived/assumed trace
    notes: str = ""
    drawing: bool = True               # False => COTS, no fab drawing

    @property
    def density(self) -> float | None:
        for key in ("6061-T6", "303-SS", "A36-steel", "concrete-4ksi"):
            if key.split("-")[0].lower() in self.material.lower() or key in self.material:
                return P.MATERIALS[key].rho
        if "6061" in self.material:
            return P.MATERIALS["6061-T6"].rho
        if "303" in self.material or "304" in self.material or "stainless" in self.material.lower():
            return P.MATERIALS["303-SS"].rho
        if "a36" in self.material.lower() or "a500" in self.material.lower() or "steel" in self.material.lower():
            return P.MATERIALS["A36-steel"].rho
        if "concrete" in self.material.lower():
            return P.MATERIALS["concrete-4ksi"].rho
        return None

    def stock_volume_m3(self) -> float | None:
        kind = self.stock[0]
        if kind == "plate":
            _, L, W, T = self.stock
            return (L * W * T) / MM3_PER_M3
        if kind == "round":
            _, dia, length = self.stock
            import math
            return (math.pi / 4.0 * dia * dia * length) / MM3_PER_M3
        if kind == "hss":  # square/rect hollow section, approx wall*perimeter*len
            _, outer, wall, length = self.stock
            inner = outer - 2 * wall
            area_mm2 = outer * outer - inner * inner
            return (area_mm2 * length) / MM3_PER_M3
        return None

    def stock_mass_kg(self) -> float | None:
        v = self.stock_volume_m3()
        d = self.density
        if v is None or d is None:
            return None
        return v * d * self.qty


# Controlling dimensions pulled from params (mm) ----------------------------
def _mm(m: float) -> float:
    return round(m * 1000.0, 2)


RA = P.RA_HOUSING
DEC = P.DEC_HOUSING
CW = P.COUNTERWEIGHTS
PIER = P.PIER

# ==========================================================================
# BP-01 — Mount head machining (6061-T6, Type III hardcoat anodize)
# ==========================================================================
_ANOD = "Type III hardcoat anodize, 0.002 in, per MIL-A-8625F Class 1 (clear)"
_AL = "6061-T6 aluminium plate per ASTM B209 / AMS-QQ-A-250/11"
_TOL_MACH = "General ISO 2768-mK; bearing bores H7 (+0.030/0); flange faces flat 0.05"

BP01 = [
    Part(
        "NW-MH-001", "RA (polar) axis housing", "BP-01", _AL,
        "6061-T6 plate 8.0 x 8.0 x 3.0 in", ("plate", _mm(RA.outer_x_m), _mm(RA.outer_y_m), _mm(RA.depth_m)),
        "CNC mill, 3-axis", _ANOD, _TOL_MACH, 1.6, 1,
        key_dims_mm={
            "Outer X": _mm(RA.outer_x_m), "Outer Y": _mm(RA.outer_y_m), "Depth (bearing span)": _mm(RA.depth_m),
            "Wall": _mm(RA.wall_m), "Bearing seat bore (7008) H7": 68.0, "Drive register bore (CSF-32)": _mm(P.RA_DRIVE.bore_m),
            "Flange bolt circle": 104.0, "Flange holes": 8, "Corner holes (M6)": 4,
        },
        provenance="Outer/wall/depth = P.RA_HOUSING (SOURCED); bearing seat=7008 remediation; flange PCD DERIVED ~1.3x bore.",
        notes="Bearing seat sized for angular-contact 7008 (remediation of 6008). Pocket-lighten at bidder's option; keep bore/flange datums.",
    ),
    Part(
        "NW-MH-002", "DEC axis housing + Losmandy-D saddle", "BP-01", _AL,
        "6061-T6 plate 6.0 x 6.0 x 2.5 in", ("plate", _mm(DEC.outer_x_m), _mm(DEC.outer_y_m), _mm(DEC.depth_m)),
        "CNC mill, 3-axis", _ANOD, _TOL_MACH, 1.6, 1,
        key_dims_mm={
            "Outer X": _mm(DEC.outer_x_m), "Outer Y": _mm(DEC.outer_y_m), "Depth (bearing span)": _mm(DEC.depth_m),
            "Wall": _mm(DEC.wall_m), "Bearing seat bore (7006) H7": 55.0, "Drive register bore (CSF-25)": _mm(P.DEC_DRIVE.bore_m),
            "Flange bolt circle": 83.0, "Losmandy-D saddle width": 76.2, "Dovetail angle (deg)": 15,
        },
        provenance="Outer/wall/depth = P.DEC_HOUSING (SOURCED); saddle = Losmandy-D ASSUMED std; bearing seat=7006 remediation.",
        notes="Integral Losmandy-D dovetail saddle. Bearing seat sized for angular-contact 7006.",
    ),
    Part(
        "NW-MH-003", "DEC saddle clamp bar", "BP-01", _AL,
        "6061-T6 bar 3.0 x 1.0 x 4.0 in", ("plate", 101.6, 76.2, 25.4),
        "CNC mill, 3-axis", _ANOD, _TOL_MACH, 3.2, 1,
        key_dims_mm={"Length": 101.6, "Width": 76.2, "Thickness": 25.4, "Clamp screws (M8)": 2, "Dovetail angle (deg)": 15},
        provenance="ASSUMED design-intent — Losmandy-D clamp not dimensioned in repo.",
        notes="Pairs with NW-MH-002 saddle to clamp the OTA dovetail.",
    ),
]

# ==========================================================================
# BP-02 — Precision turned parts (303 SS, passivated)
# ==========================================================================
_SS = "303 stainless per ASTM A582"
_PASS = "Passivate per ASTM A967 (nitric)"
_TOL_TURN = "General ISO 2768-mK; journal diameters h6; concentricity 0.02 TIR"

BP02 = [
    Part(
        "NW-TP-001", "Counterweight shaft", "BP-02", _SS,
        "303-SS round bar 1.25 in dia x 18 in", ("round", _mm(CW.shaft_dia_m), _mm(CW.shaft_len_m)),
        "CNC turn", _PASS, _TOL_TURN, 0.8, 1,
        key_dims_mm={"Diameter": _mm(CW.shaft_dia_m), "Length": _mm(CW.shaft_len_m), "Stud end": "M12 x 40",
                     "Safety-stop thread": "M12", "Root fillet R": 3.0},
        provenance="Dia/length = P.COUNTERWEIGHTS (SOURCED).",
        notes="Counterweight-FREE build makes this OPTIONAL (see BP-00 / trade study). Include only if counterweighted variant is bid.",
    ),
    Part(
        "NW-TP-002", "RA drive spindle / drawbar adapter", "BP-02", _SS,
        "303-SS round bar 3.5 in dia x 4 in", ("round", 88.9, 101.6),
        "CNC turn + mill", _PASS, _TOL_TURN, 0.8, 1,
        key_dims_mm={"Body dia": 88.9, "Length": 101.6, "Bearing journal (7008) j6": 40.0,
                     "CSF-32 wave-gen register": _mm(P.RA_DRIVE.bore_m), "Bolt pattern": "8 x M4 on 104 PCD"},
        provenance="Journal = 7008 bore (remediation); CSF-32 register = P.RA_DRIVE.bore_m (SOURCED). Body dia ASSUMED.",
        notes="Couples the CSF-32 output to the RA axis; carries the inner race of the 7008 pair.",
    ),
    Part(
        "NW-TP-003", "DEC drive spindle / saddle stub", "BP-02", _SS,
        "303-SS round bar 3.0 in dia x 3.5 in", ("round", 76.2, 88.9),
        "CNC turn + mill", _PASS, _TOL_TURN, 0.8, 1,
        key_dims_mm={"Body dia": 76.2, "Length": 88.9, "Bearing journal (7006) j6": 30.0,
                     "CSF-25 wave-gen register": _mm(P.DEC_DRIVE.bore_m), "Bolt pattern": "8 x M4 on 83 PCD"},
        provenance="Journal = 7006 bore (remediation); CSF-25 register = P.DEC_DRIVE.bore_m (SOURCED). Body dia ASSUMED.",
        notes="Couples the CSF-25 output to the DEC axis / saddle side.",
    ),
]

# ==========================================================================
# BP-03 — Pier & foundation (RC + structural steel).  PE-STAMP GATE.
# ==========================================================================
_STEEL = "ASTM A36 structural steel"
_GALV = "Hot-dip galvanize per ASTM A123"
_CONC = "Cast-in-place concrete f'c = 4000 psi (27.6 MPa) per ACI 318 / ACI 301"

BP03 = [
    Part(
        "NW-PF-001", "Reinforced-concrete telescope pier", "BP-03", _CONC,
        "Drilled/formed pier Ø12 in", ("round", _mm(PIER.diameter_m), _mm(PIER.height_above_m + PIER.embed_depth_m)),
        "Cast-in-place", "none", "Plumb 1:200; top level 0.5 deg", None, 1,
        key_dims_mm={"Diameter": _mm(PIER.diameter_m), "Height above grade": _mm(PIER.height_above_m),
                     "Embedment": _mm(PIER.embed_depth_m), "f'c (psi)": 4000,
                     "Vertical rebar": "6 x #4 (A615 Gr60)", "Ties": "#3 @ 12 in oc"},
        provenance="Ø/height/embed/f'c = P.PIER (SOURCED); rebar schedule ASSUMED design-intent (PE to confirm).",
        notes="ISOLATED from any building slab (vibration). Embedment>frost line. Rebar cage + anchor template cast integrally. REQUIRES PE STAMP.",
    ),
    Part(
        "NW-PF-002", "Pier top plate", "BP-03", _STEEL,
        "A36 plate 12 x 12 x 0.375 in", ("plate", _mm(PIER.top_plate_side_m), _mm(PIER.top_plate_side_m), _mm(PIER.top_plate_thk_m)),
        "Laser/waterjet cut + drill", _GALV, "General ISO 2768-mK; hole pattern 0.25", 3.2, 1,
        key_dims_mm={"Side": _mm(PIER.top_plate_side_m), "Thickness": _mm(PIER.top_plate_thk_m),
                     "Anchor holes": "4 x Ø0.81 (for Ø0.75 F1554)", "Centre pattern": "matches NW-PF-003"},
        provenance="Side/thickness = P.PIER (SOURCED); hole pattern DERIVED.",
        notes="Grouted onto the pier over the cast-in anchor bolts.",
    ),
    Part(
        "NW-PF-003", "Pier-to-mount adapter plate", "BP-03", "6061-T6 aluminium per ASTM B209",
        "6061-T6 plate 10 x 10 x 0.75 in", ("plate", 254.0, 254.0, 19.05),
        "CNC mill", _ANOD, _TOL_MACH, 3.2, 1,
        key_dims_mm={"Side": 254.0, "Thickness": 19.05, "RA housing pattern": "4 x M6 (matches NW-MH-001)",
                     "Pier plate pattern": "4 x Ø0.44 (matches NW-PF-002)", "Centre bore": 90.0},
        provenance="ASSUMED design-intent — adapter geometry not in repo (bridges 12x12 plate to 8x8 housing).",
        notes="Levels/orients the RA axis to site latitude 38.9 deg (wedge or shim set, bidder to detail).",
    ),
    Part(
        "NW-PF-004", "Anchor-bolt set + template", "BP-03", "ASTM F1554 Gr36 galvanized",
        "4 x Ø0.75 in x 12 in anchor bolts + template", ("cots",),
        "Purchase + fabricate template", _GALV, "Template hole 0.02", None, 1,
        key_dims_mm={"Bolt dia": 19.05, "Embedment": 304.8, "Projection": 50.0, "Count": 4, "Template": "0.25 in plywood/ply-steel"},
        provenance="ASSUMED design-intent per ACI 318 Ch.17 (PE to size for wind/seismic uplift ~9.2 kN).",
        notes="Cast into pier via template. Sizing tied to the wind proof roof/pier uplift — PE to confirm.",
        drawing=True,
    ),
]

# ==========================================================================
# BP-04 — Roll-off roof "disappearing turret" (A36 steel; AWS D1.1).
# Member sizes are ASSUMED design-intent (bidder/PE to confirm vs ASCE 7 loads).
# ==========================================================================
_A500 = "ASTM A500 Gr B HSS (steel)"
_WELD = "Welded per AWS D1.1; weld symbols per AWS A2.4"

def _roof_len_mm() -> float:
    return _mm(P.ENCLOSURE.roof_length_m)

def _roof_span_mm() -> float:
    return _mm(P.ENCLOSURE.roof_span_m)

BP04 = [
    Part(
        "NW-RR-001", "Roof frame perimeter (HSS)", "BP-04", _A500,
        "HSS 2 x 2 x 1/8 in", ("hss", 50.8, 3.175, 4 * _roof_span_mm()),
        "Cut + weld (AWS D1.1)", _GALV, "Frame square 3 mm/m; diagonal 5 mm", None, 1,
        key_dims_mm={"Span": _roof_span_mm(), "Length": _roof_len_mm(), "Member": "HSS 2x2x1/8",
                     "Corner joints": "fully welded, gusseted"},
        provenance="Roof span/length = P.ENCLOSURE (ASSUMED footprint); member size ASSUMED design-intent.",
        notes="Rectangular roll-off roof frame. Member sizing to be confirmed vs ASCE 7 snow/wind by PE.",
    ),
    Part(
        "NW-RR-002", "Roof rafters / purlins", "BP-04", _A500,
        "HSS 2 x 1 x 1/8 in", ("hss", 38.1, 3.175, 5 * _roof_span_mm()),
        "Cut + weld (AWS D1.1)", _GALV, "n/a", None, 5,
        key_dims_mm={"Span": _roof_span_mm(), "Spacing": 600, "Member": "HSS 2x1x1/8", "Count": 5},
        provenance="ASSUMED design-intent (5 purlins @ ~600 mm).",
        notes="Carries the metal roofing panel + snow load (10.8 kN closed-roof snow case, see enclosure proof).",
    ),
    Part(
        "NW-RR-003", "Track rail beams (box track)", "BP-04", _STEEL,
        "Box track / channel, ~2x roof length", ("hss", 63.5, 4.0, 2 * 2 * _roof_len_mm()),
        "Cut + weld / bolt to piers", _GALV, "Rail straightness 3 mm over run; gauge 2 mm", None, 2,
        key_dims_mm={"Rail length (each)": 2 * _roof_len_mm(), "Gauge (rail spacing)": _roof_span_mm(),
                     "Section": "box track 2.5 in class"},
        provenance="ASSUMED design-intent — rail run = 2x roof length so the roof fully clears the aperture.",
        notes="Roof travels its own length off the building. Rail brand/section = COTS (BP-05). End stops required.",
    ),
    Part(
        "NW-RR-004", "Wheel axle brackets", "BP-04", _STEEL,
        "A36 plate 4 x 3 x 3/8 in", ("plate", 101.6, 76.2, 9.525),
        "Laser cut + weld", _GALV, "Hole pattern 0.25", None, 8,
        key_dims_mm={"Count": 8, "Wheel bore": "for Ø4 in V-groove wheel (COTS)", "Axle": "M16"},
        provenance="ASSUMED design-intent — 8 wheels (4 per side).",
        notes="Carry the COTS V-groove wheels (BP-05). Roof 180 kg + snow -> size wheels for >=4x.",
    ),
    Part(
        "NW-RR-005", "Drive bracket + end stops", "BP-04", _STEEL,
        "A36 plate + angle assembly", ("plate", 150.0, 100.0, 9.525),
        "Laser cut + weld", _GALV, "n/a", None, 4,
        key_dims_mm={"Drive": "gate-operator / rack (COTS)", "End stops": 4, "Bump pads": "rubber"},
        provenance="ASSUMED design-intent — drive = gate operator sized for 180 kg (enclosure proof: 235 N move force).",
        notes="Mounts the COTS drive (BP-05) and hard end stops. Wind-during-motion limit per enclosure proof.",
    ),
    Part(
        "NW-RR-006", "Wind hold-down anchor brackets", "BP-04", _STEEL,
        "A36 plate 5 x 4 x 1/2 in", ("plate", 127.0, 101.6, 12.7),
        "Laser cut + weld", _GALV, "Hole pattern 0.25", None, 4,
        key_dims_mm={"Count": 4, "Anchor": "Ø0.75 F1554 (to building/pier)", "Capacity (each)": ">=2 klbf"},
        provenance="REMEDIATION — wind proof: survival uplift 9.2 kN, 4 x 2 klbf anchors -> SF 3.9.",
        notes="MANDATORY. Clamp the roof/building against 105 mph survival uplift. Interlocked with the drive.",
    ),
]

# ==========================================================================
# BP-05 — COTS procurement schedule (purchase; no fab drawing).
# ==========================================================================
def _cots(part_no, name, material, qty, dims, prov, notes):
    return Part(part_no, name, "BP-05", material, "COTS", ("cots",), "purchase", "n-a", "per datasheet",
                None, qty, key_dims_mm=dims, provenance=prov, notes=notes, drawing=False)

BP05 = [
    _cots("NW-CO-001", "Harmonic drive, RA (CSF-32-100-2A-GR)", "Harmonic Drive LLC", 1,
          {"Ratio": 100, "Rated torque (Nm)": 127, "Peak (Nm)": 343, "Bore (mm)": _mm(P.RA_DRIVE.bore_m)},
          "P.RA_DRIVE (SOURCED).", "Strain-wave gear, RA axis."),
    _cots("NW-CO-002", "Harmonic drive, DEC (CSF-25-80-2A-GR)", "Harmonic Drive LLC", 1,
          {"Ratio": 80, "Rated torque (Nm)": 70, "Peak (Nm)": 186, "Bore (mm)": _mm(P.DEC_DRIVE.bore_m)},
          "P.DEC_DRIVE (SOURCED).", "Strain-wave gear, DEC axis."),
    _cots("NW-CO-003", "Angular-contact bearing 7008 (RA pair)", "ABEC-7, back-to-back (DB)", 2,
          {"Bore (mm)": 40, "OD (mm)": 68, "Arrangement": "DB back-to-back"},
          "REMEDIATION of deep-groove 6008 (stiffness proof: bearings were 98% of the 43.5 arcsec FAIL).",
          "Preloaded pair for MOMENT stiffness. Replaces 6008."),
    _cots("NW-CO-004", "Angular-contact bearing 7006 (DEC pair)", "ABEC-7, back-to-back (DB)", 2,
          {"Bore (mm)": 30, "OD (mm)": 55, "Arrangement": "DB back-to-back"},
          "REMEDIATION of deep-groove 6006.", "Preloaded pair, DEC axis. Replaces 6006."),
    _cots("NW-CO-005", "On-axis absolute encoder (RA + DEC)", "Absolute ring/BiSS-C, sub-arcsec", 2,
          {"Resolution (arcsec)": "<1", "Interface": "BiSS-C / SSI"},
          "REMEDIATION — encoder proof: baseline 5.02 arcsec RMS FAIL; on-axis ring reaches 0.54 arcsec.",
          "MANDATORY for sub-arcsecond. Closes the loop on the axis (corrects harmonic PE)."),
    _cots("NW-CO-006", "Stepper motor NEMA17 + 27:1 planetary", "NEMA17 1.8deg + gearhead", 2,
          {"Step (deg)": 1.8, "Planetary ratio": 27}, "P.MOTOR (SOURCED).", "One per axis."),
    _cots("NW-CO-007", "Motor driver (TMC5160) / OnStepX board", "Trinamic TMC5160", 2,
          {"Irun (A)": 1.5, "Igoto (A)": 2.0}, "P.MOTOR (SOURCED).", "Microstepping driver."),
    _cots("NW-CO-008", "Temperature-compensated focuser", "e.g. motorised absolute focuser", 1,
          {"Temp coeff": "-2.5 steps/degC"},
          "REMEDIATION — thermal proof: passive focus walks ~10x depth-of-focus over 22 K swing.",
          "Compensates the aluminium-tube focus drift."),
    _cots("NW-CO-009", "Counterweights (5 kg x2, 2.5 kg x1)", "Cast iron", 3,
          {"Total (kg)": 12.5}, "P.COUNTERWEIGHTS (SOURCED).",
          "OPTIONAL — counterweight-FREE build omits these (torque proof)."),
    _cots("NW-CO-010", "V-groove track wheels", "Steel V-groove, ~4 in", 8,
          {"Dia (in)": 4, "Rated (kg each)": ">=150"}, "ASSUMED design-intent (BP-04 rail).",
          "8 wheels for the roll-off roof (4 per side)."),
    _cots("NW-CO-011", "Roof drive (gate operator)", "Sliding-gate operator / rack", 1,
          {"Move force (N)": 235, "Drive": "rack-and-pinion / chain"},
          "ASSUMED design-intent — enclosure proof: 235 N move force, SF 2.1 vs ~500 N drive.",
          "Sized for 180 kg roof + 35 mph gust. Fail-safe + wind interlock."),
    _cots("NW-CO-012", "Metal roofing panel + flashing", "Standing-seam / corrugated steel", 1,
          {"Area (m2)": round(P.ENCLOSURE.roof_span_m * P.ENCLOSURE.roof_length_m, 1)},
          "ASSUMED design-intent (roof cladding).", "Weatherproof skin + ridge/edge flashing + gaskets."),
    _cots("NW-CO-013", "48 V LiFePO4 battery pack + solar", "48 V pack, ~5 kWh", 1,
          {"Bus (V)": 48, "Autonomy (h)": 13.4},
          "REMEDIATION — power proof: 12 V pack gives 3.3 h vs 10 h night; 48 V gives 13.4 h.",
          "For off-grid autonomy (v2). v1 may run grid + UPS."),
    _cots("NW-CO-014", "Fastener schedule (SHCS, anchors)", "ASTM A574 SHCS / ASTM F1554 anchors", 1,
          {"Grades": "A574 (SHCS), F1554 Gr36 (anchors)"}, "ASSUMED design-intent.",
          "Consolidated fastener BOM — see cut list / fastener schedule."),
]

ALL_PARTS: list[Part] = BP01 + BP02 + BP03 + BP04 + BP05


def parts_for(package: str) -> list[Part]:
    return [p for p in ALL_PARTS if p.package == package]


def fabricated_parts() -> list[Part]:
    return [p for p in ALL_PARTS if p.drawing and p.stock[0] != "cots"]


if __name__ == "__main__":
    for pkg, (title, trade) in PACKAGES.items():
        parts = parts_for(pkg)
        print(f"{pkg} {title} ({trade}) — {len(parts)} line items")
        for p in parts:
            m = p.stock_mass_kg()
            mm = f"{m:.1f} kg stock" if m else "COTS"
            print(f"   {p.part_no}  {p.name:42} x{p.qty}  {mm}")
