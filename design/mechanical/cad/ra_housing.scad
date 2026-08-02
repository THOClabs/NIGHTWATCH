// ============================================================================
// NIGHTWATCH GEM — RA (polar) axis housing
// Parametric OpenSCAD model.  Units: MILLIMETRES (OpenSCAD convention).
//
// Render (OpenSCAD is NOT installed in this design sandbox; this is text CAD):
//     openscad -o ra_housing.stl                      ra_housing.scad
//     openscad -o ra_housing.png --imgsize=1200,900   ra_housing.scad
//
// Every dimension traces to design/mechanical/calc/params.py so the geometry
// cannot silently drift from the computed design.  Edit params.py, then mirror
// the value here (and in the sibling parts).  SI metres in params -> mm here.
// ============================================================================

$fn = 96;

// ---- parameters (traced to params.py) --------------------------------------
ra_outer_x   = 203.2;  // P.RA_HOUSING.outer_x_m = u.inch(8)   -> 0.2032 m
ra_outer_y   = 203.2;  // P.RA_HOUSING.outer_y_m = u.inch(8)   -> 0.2032 m
ra_depth     = 76.2;   // P.RA_HOUSING.depth_m   = u.inch(3)   -> bearing separation
ra_wall      = 8.0;    // P.RA_HOUSING.wall_m    = u.mm(8)  (Hedrick min; 12 mm bold)

brg_od       = 68.0;   // P.BRG_RA_6008.od_m     = u.mm(68)  (6008 output bearing)
brg_bore     = 40.0;   // P.BRG_RA_6008.bore_m   = u.mm(40)
brg_w        = 15.0;   // 6008 nominal width — ASSUMED (not dimensioned in params.py)

drive_bore   = 80.0;   // P.RA_DRIVE.bore_m      = u.mm(80)  (CSF-32-100 hollow bore)
// CSF-32 output flange mounting bolt circle scales with the hollow bore.
// DERIVED: ~1.3 x bore keeps the ring clear of the bore wall.  Traced ~ P.RA_DRIVE.bore_m.
flange_bc    = 104.0;  // ~ P.RA_DRIVE.bore_m ; CSF-32 flange PCD (DERIVED)
flange_nbolt = 8;      // ASSUMED (CSF-32 flange hole count)
flange_bolt_d = 4.5;   // M4 clearance — ASSUMED

corner_bolt_d = 6.6;   // M6 clearance: housing -> RA stage / pier adapter — ASSUMED
corner_inset  = 18.0;  // ASSUMED

// ---- part ------------------------------------------------------------------
module ra_housing() {
    difference() {
        // Solid 6061-T6 block; production part would be pocket-lightened, kept
        // solid here so the parametric proof stays unambiguous.
        translate([-ra_outer_x/2, -ra_outer_y/2, 0])
            cube([ra_outer_x, ra_outer_y, ra_depth]);

        // Stepped axial bore along +z (the polar / RA axis):
        //   front  (z=0)      : 6008 bearing seat (OD 68)
        //   rear   (z=brg_w+) : opens to the CSF-32 hollow-drive register (80)
        translate([0, 0, -1])      cylinder(d = brg_od,     h = brg_w + 1);
        translate([0, 0, brg_w])   cylinder(d = drive_bore, h = ra_depth - brg_w + 1);
        // clear through-hole for drawbar / cable routing
        translate([0, 0, -1])      cylinder(d = brg_bore - 6, h = ra_depth + 2);

        // CSF-32 drive flange bolt circle, counter-drilled from the rear face.
        for (i = [0 : flange_nbolt - 1])
            rotate([0, 0, i * 360 / flange_nbolt])
                translate([flange_bc / 2, 0, ra_depth - 16])
                    cylinder(d = flange_bolt_d, h = 20);

        // Four corner through-holes (housing -> adapter / RA stage).
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx * (ra_outer_x/2 - corner_inset),
                       sy * (ra_outer_y/2 - corner_inset), -1])
                cylinder(d = corner_bolt_d, h = ra_depth + 2);
    }
}

ra_housing();   // executed when opened directly; ignored by `use <>` in assembly
