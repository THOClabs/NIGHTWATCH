// ============================================================================
// NIGHTWATCH GEM — counterweight shaft + weights
// Parametric OpenSCAD model.  Units: MILLIMETRES.
//
// Render (OpenSCAD not installed here):
//     openscad -o counterweight_shaft.stl                     counterweight_shaft.scad
//     openscad -o counterweight_shaft.png --imgsize=1200,900  counterweight_shaft.scad
//
// Dimensions trace to design/mechanical/calc/params.py (SI metres -> mm).
// NOTE: the counterweight-FREE study (balance.py) recommends DELETING this shaft;
// it is modelled so the classical GEM option remains fully drawable.
// ============================================================================

$fn = 96;

// ---- parameters (traced to params.py) --------------------------------------
shaft_d = 31.75;   // P.COUNTERWEIGHTS.shaft_dia_m = u.inch(1.25) -> 0.03175 m (303-SS)
shaft_l = 457.2;   // P.COUNTERWEIGHTS.shaft_len_m = u.inch(18.0) -> 0.4572 m

// Weights available = 12.5 kg (2 x 5 kg + 1 x 2.5 kg) = P.COUNTERWEIGHTS.weights_available_kg
// Cast-iron disc geometry is ASSUMED (params gives mass only, not OD/thickness).
disc_bore  = 33.0;   // slip fit over the shaft — ASSUMED
disc5_od   = 127.0;  // 5.0 kg disc OD — ASSUMED
disc5_t    = 40.0;   // 5.0 kg disc thickness — ASSUMED
disc25_od  = 102.0;  // 2.5 kg disc OD — ASSUMED
disc25_t   = 33.0;   // 2.5 kg disc thickness — ASSUMED

// End fittings — ASSUMED.
stud_d = 20.0; stud_l = 26.0;   // threaded stud into the DEC block
knob_d = 46.0; knob_h = 16.0;   // safety stop knob at the far end

module _disc(od, t) {
    difference() {
        cylinder(d = od, h = t);
        translate([0, 0, -1]) cylinder(d = disc_bore, h = t + 2);
        // knurl-substitute relief so the disc reads as a weight, not a plain ring
        translate([0, 0, t/2]) rotate_extrude() translate([od/2 - 3, 0, 0]) square([3, t], center=true);
    }
}

module counterweight_shaft() {
    // threaded stud (mount end) at z<0
    translate([0, 0, -stud_l]) cylinder(d = stud_d, h = stud_l);
    // main 303-SS shaft
    cylinder(d = shaft_d, h = shaft_l);
    // safety stop knob at the far (top) end
    translate([0, 0, shaft_l]) cylinder(d = knob_d, h = knob_h);

    // Stacked weights near the far end (parked position): 5 + 5 + 2.5 kg.
    z0 = shaft_l - 40;
    translate([0, 0, z0 - disc5_t])                       _disc(disc5_od,  disc5_t);
    translate([0, 0, z0 - disc5_t - disc5_t])             _disc(disc5_od,  disc5_t);
    translate([0, 0, z0 - disc5_t - disc5_t - disc25_t])  _disc(disc25_od, disc25_t);
}

counterweight_shaft();   // standalone; ignored by `use <>` in assembly
