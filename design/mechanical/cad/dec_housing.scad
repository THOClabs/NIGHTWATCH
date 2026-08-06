// ============================================================================
// NIGHTWATCH GEM — DEC axis housing + Losmandy-D saddle
// Parametric OpenSCAD model.  Units: MILLIMETRES.
//
// Render (OpenSCAD not installed here):
//     openscad -o dec_housing.stl                     dec_housing.scad
//     openscad -o dec_housing.png --imgsize=1200,900  dec_housing.scad
//
// Dimensions trace to design/mechanical/calc/params.py (SI metres -> mm).
// ============================================================================

$fn = 96;

// ---- parameters (traced to params.py) --------------------------------------
dec_outer_x  = 152.4;  // P.DEC_HOUSING.outer_x_m = u.inch(6)   -> 0.1524 m
dec_outer_y  = 152.4;  // P.DEC_HOUSING.outer_y_m = u.inch(6)
dec_depth    = 63.5;   // P.DEC_HOUSING.depth_m   = u.inch(2.5) -> bearing separation
dec_wall     = 8.0;    // P.DEC_HOUSING.wall_m    = u.mm(8)

brg_od       = 55.0;   // P.BRG_DEC_6006.od_m     = u.mm(55)  (6006 output bearing)
brg_bore     = 30.0;   // P.BRG_DEC_6006.bore_m   = u.mm(30)
brg_w        = 13.0;   // 6006 nominal width — ASSUMED (not in params.py)

drive_bore   = 64.0;   // P.DEC_DRIVE.bore_m      = u.mm(64)  (CSF-25-80 hollow bore)
flange_bc    = 83.0;   // ~ P.DEC_DRIVE.bore_m ; CSF-25 flange PCD (DERIVED ~1.3*bore)
flange_nbolt = 8;      // ASSUMED
flange_bolt_d = 4.5;   // M4 clearance — ASSUMED

// Losmandy-D dovetail (industry standard) — ASSUMED (repo does not dimension it).
losmandy_plate_w = 76.2;   // 3.00 in nominal Losmandy-D plate width — ASSUMED std
dovetail_angle   = 15.0;   // deg, standard dovetail flank — ASSUMED std
saddle_height    = 24.0;   // jaw block height — ASSUMED
saddle_slot_depth = 14.0;  // dovetail engagement depth — ASSUMED
clamp_bolt_d     = 8.0;    // side clamp knob thread — ASSUMED

// ---- dovetail channel (trapezoid: wide at base, narrow mouth) ---------------
module _dovetail_channel(chlen, plate_w, ang, depth) {
    mouth = plate_w - 2 * depth * tan(ang);      // narrower opening at the top
    translate([0, chlen / 2, 0])
        rotate([90, 0, 0])                        // extrude +Z -> run along -Y
            linear_extrude(height = chlen)
                polygon(points = [
                    [-plate_w / 2, 0],            // base (inside), wide
                    [ plate_w / 2, 0],
                    [ mouth / 2,  depth],         // mouth (top), narrow -> jaws grip
                    [-mouth / 2,  depth]
                ]);
}

// ---- DEC bearing/drive housing ---------------------------------------------
module dec_core() {
    difference() {
        translate([-dec_outer_x/2, -dec_outer_y/2, 0])
            cube([dec_outer_x, dec_outer_y, dec_depth]);

        // Stepped axial bore along +z (the DEC axis):
        translate([0, 0, -1])      cylinder(d = brg_od,     h = brg_w + 1);
        translate([0, 0, brg_w])   cylinder(d = drive_bore, h = dec_depth - brg_w + 1);
        translate([0, 0, -1])      cylinder(d = brg_bore - 6, h = dec_depth + 2);

        // CSF-25 flange bolt circle from the rear face.
        for (i = [0 : flange_nbolt - 1])
            rotate([0, 0, i * 360 / flange_nbolt])
                translate([flange_bc / 2, 0, dec_depth - 14])
                    cylinder(d = flange_bolt_d, h = 18);
    }
}

// ---- Losmandy-D saddle jaw block (sits on the +Y face of the DEC output) -----
module losmandy_saddle() {
    blk_w = losmandy_plate_w + 44;     // jaw width straddling the plate — ASSUMED
    blk_l = dec_outer_y;               // saddle length = DEC housing face
    difference() {
        translate([-blk_w/2, -blk_l/2, 0]) cube([blk_w, blk_l, saddle_height]);
        // dovetail channel, mouth flush with the top surface
        translate([0, 0, saddle_height - saddle_slot_depth])
            _dovetail_channel(blk_l + 2, losmandy_plate_w, dovetail_angle, saddle_slot_depth + 2);
        // side clamp knob cross-hole
        translate([blk_w/2 - 8, 0, saddle_height/2])
            rotate([0, 90, 0]) cylinder(d = clamp_bolt_d, h = 24, center = true);
    }
}

module dec_housing() {
    dec_core();
    // Mount the saddle on the DEC output face (+z), lifted clear of the bore boss.
    translate([0, 0, dec_depth]) losmandy_saddle();
}

dec_housing();   // executed standalone; ignored by `use <>` in assembly
