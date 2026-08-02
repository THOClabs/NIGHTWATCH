## Mechanical CAD (Phase D) — parametric geometry

The repository shipped **zero usable CAD**: every `.step` reference in the build package is marked *Pending*. Phase D replaces that void with **text-based, parametric geometry driven entirely by the computed design** in `design/mechanical/calc/params.py`. Nothing is hand-dimensioned that already exists as a parameter — change a number in `params.py` and the models (and the preview) move with it.

### The immediate visual

![NIGHTWATCH GEM meridian elevation](cad/preview_assembly.svg)

`cad/preview_assembly.svg` is a to-scale meridian-plane side elevation of the mount in its park pose — pier, RA housing on the polar axis inclined at the **38.9° site latitude**, DEC head, MN78 OTA pointing at the pole, and the counterweight shaft hanging on the down side. It is produced by a **pure-stdlib** Python script (no OpenSCAD, no third-party libraries) that imports `params.py` and writes the SVG with the real numbers annotated. This is the deliverable you can look at right now; the OpenSCAD files below are the manufacturable source.

### The parts

| File | Part | Headline dimensions (all traced to `params.py`) |
|---|---|---|
| `cad/ra_housing.scad` | RA (polar) axis housing | 203.2 × 203.2 × 76.2 mm block (`RA_HOUSING` 8″×8″×3″), 8 mm wall; stepped axial bore — 6008 seat (Ø68/Ø40, `BRG_RA_6008`) opening to the CSF‑32 Ø80 hollow‑drive register (`RA_DRIVE.bore_m`); flange bolt circle ≈ Ø104 |
| `cad/dec_housing.scad` | DEC axis housing + **Losmandy‑D saddle** | 152.4 × 152.4 × 63.5 mm (`DEC_HOUSING` 6″×6″×2.5″); 6006 seat (Ø55/Ø30, `BRG_DEC_6006`) → CSF‑25 Ø64 register (`DEC_DRIVE.bore_m`); dovetail saddle 76.2 mm / 15° with side clamp |
| `cad/pier_adapter.scad` | Pier adapter plate | 254 × 254 × 19.05 mm (10″×10″×0.75″) bridging the SOURCED 304.8 × 9.525 mm (12″×0.375″) `PIER` top plate to the RA housing corner pattern |
| `cad/counterweight_shaft.scad` | Counterweight shaft + weights | Ø31.75 mm × 457.2 mm 303‑SS (`COUNTERWEIGHTS` 1.25″×18″), stud + safety knob, 5+5+2.5 kg discs (12.5 kg available) |
| `cad/assembly.scad` | Full GEM assembly | Composes all four parts + the MN78 OTA tube (Ø210 × 1400 mm) on the pier, posed at latitude `SITE.latitude_deg` |
| `cad/svg_preview.py` | Zero‑dep previewer | Imports `params`/`units`, emits `preview_assembly.svg` |

### Parametric approach

Each `.scad` opens with a **params block** whose every entry carries a `// = P.<...>` comment tracing it to `params.py` (SI metres in the calculator → millimetres in OpenSCAD, the CAD convention). Parts are pure `module`s; `assembly.scad` pulls them in with `use <...>` and places them with explicit transforms (`rotate([0, 90-lat, 0])` puts local *+z* on the celestial pole; a nested `rotate([90,0,0])` sets the DEC axis perpendicular to RA). The SVG previewer is the strictest link in the chain — it reads `params.py` **at runtime**, so it can never disagree with the proofs, and a test pins the committed SVG byte‑for‑byte to the renderer output.

### How to render

OpenSCAD is **not installed** in the design sandbox, so each part header documents the command to run locally:

```
openscad -o ra_housing.stl                      design/mechanical/cad/ra_housing.scad
openscad -o assembly.stl                        design/mechanical/cad/assembly.scad
openscad -o assembly.png --imgsize=1600,1200    design/mechanical/cad/assembly.scad
```

The SVG needs nothing but Python: `python3 design/mechanical/cad/svg_preview.py` regenerates `preview_assembly.svg` (re‑run it whenever `params.py` changes).

### Honest assumptions (tagged ASSUMED/DERIVED in‑file and in `svg_preview`)

- **Pier adapter (10×10×0.75″)** is an *added* part — the repo's `PIER` only specifies a 12×12×0.375″ top plate, so the adapter geometry is **ASSUMED**.
- **Losmandy‑D dovetail** 76.2 mm / 15° is the **ASSUMED** industry standard; the repo never dimensions the saddle.
- **Bearing widths** (6008 = 15 mm, 6006 = 13 mm) and **counterweight disc OD/thickness** are **ASSUMED** — `params` gives bore/OD and weight mass only.
- **CSF flange bolt circle** is taken as **DERIVED** ≈ 1.3 × drive bore (`RA_DRIVE.bore_m` / `DEC_DRIVE.bore_m`), since datasheet PCDs are not in the repo.

### Verification

`design/mechanical/tests/test_cad.py` — **13 tests, all green** (and the full mechanical suite stays at 118 passed): the polar‑axis vector is a unit vector at the site latitude with the perpendiculars orthogonal to it; drawn dimensions equal `params.py` exactly; swapping MN76↔MN78 changes the geometry (proof it is parametric); the head sits above the pier top, the OTA clears the DEC head toward the pole, and the counterweight hangs on the opposite side of the inclined axis; the SVG is valid, dimensioned with the real numbers, and actually writes; and every `.scad` carries its render command and `params.py` traceability.