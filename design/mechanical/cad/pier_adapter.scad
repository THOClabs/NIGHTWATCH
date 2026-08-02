// ============================================================================
// NIGHTWATCH GEM — pier adapter plate
// Bridges the concrete pier's steel top plate (12" x 0.375") to the RA housing.
// Parametric OpenSCAD model.  Units: MILLIMETRES.
//
// Render (OpenSCAD not installed here):
//     openscad -o pier_adapter.stl                     pier_adapter.scad
//     openscad -o pier_adapter.png --imgsize=1200,900  pier_adapter.scad
//
// Dimensions trace to design/mechanical/calc/params.py (SI metres -> mm).
// ============================================================================

$fn = 96;

// ---- parameters ------------------------------------------------------------
// The adapter plate itself is 10" x 10" x 0.75" — an ADDED part (repo is silent
// on an adapter; tagged ASSUMED).  It seats on the SOURCED pier top plate below.
adapter_side = 254.0;   // 10 in  = u.inch(10)  -> ASSUMED (adapter geometry added)
adapter_thk  = 19.05;   // 0.75 in = u.inch(0.75) -> ASSUMED

// Below: the pier's steel top plate (SOURCED, params.py P.PIER).
pier_plate_side = 304.8;   // P.PIER.top_plate_side_m = u.inch(12)
pier_plate_thk  = 9.525;   // P.PIER.top_plate_thk_m  = u.inch(0.375)  (reference)
pier_dia        = 304.8;   // P.PIER.diameter_m       = u.inch(12)     (cable-hole guide)

// Above: the RA housing corner bolt pattern it must accept.
ra_outer     = 203.2;   // P.RA_HOUSING.outer_x_m = u.inch(8)
ra_corner_inset = 18.0; // must match ra_housing.scad corner_inset — DERIVED

// Fastener geometry — ASSUMED.
down_bolt_d  = 13.5;    // M12 anchor pattern into the pier top plate
down_bc      = 228.6;   // bolt circle to the pier plate (9.0 in square) — ASSUMED
up_bolt_d    = 7.0;     // M6 tapped-clearance for the RA housing corners
cable_bore   = 60.0;    // central cable / drawbar pass-through — ASSUMED

module pier_adapter() {
    ra_bc = ra_outer - 2 * ra_corner_inset;   // RA housing corner square (mm)
    difference() {
        // 10" square plate with lightly chamfered footprint (via minkowski-free
        // bevel: a plain square keeps the model unambiguous).
        translate([-adapter_side/2, -adapter_side/2, 0])
            cube([adapter_side, adapter_side, adapter_thk]);

        // central cable / drawbar bore
        translate([0, 0, -1]) cylinder(d = cable_bore, h = adapter_thk + 2);

        // DOWN pattern: 4 bolts on a square to the pier top plate
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx * down_bc/2, sy * down_bc/2, -1])
                cylinder(d = down_bolt_d, h = adapter_thk + 2);

        // UP pattern: 4 tapped holes matching the RA housing corner bolts
        for (sx = [-1, 1], sy = [-1, 1])
            translate([sx * ra_bc/2, sy * ra_bc/2, -1])
                cylinder(d = up_bolt_d, h = adapter_thk + 2);
    }
}

pier_adapter();   // standalone; ignored by `use <>` in assembly
