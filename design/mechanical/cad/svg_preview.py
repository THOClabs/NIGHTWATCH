"""
Zero-dependency SVG side-elevation of the NIGHTWATCH German Equatorial Mount.

This is the *immediate* visual for the CAD package: OpenSCAD is not installed in
the design sandbox, so rather than ship un-renderable ``.step`` stubs (the repo's
current state — every CAD file is "Pending"), this module draws a correctly-
proportioned meridian-plane elevation straight from the computed design.

Every dimension is read live from ``design.mechanical.calc.params`` — nothing is
hardcoded that already lives in params.py — so the drawing cannot drift from the
proofs.  The pose is the classic GEM park: polar (RA) axis inclined at the site
latitude, OTA pointing at the celestial pole, counterweight shaft hanging on the
"down" side.

Pure standard-library string templating; run it to (re)write ``preview_assembly.svg``:

    python3 design/mechanical/cad/svg_preview.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# Allow ``python3 design/mechanical/cad/svg_preview.py`` from anywhere: put the
# repo root (…/NIGHTWATCH) on sys.path so the calc package imports cleanly.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from design.mechanical.calc import params as P  # noqa: E402
from design.mechanical.calc import units as u  # noqa: E402

DEFAULT_OUT = Path(__file__).resolve().parent / "preview_assembly.svg"

# --------------------------------------------------------------------------
# 2-D vector helpers (metres, maths frame: +x = north/right, +y = up).
# --------------------------------------------------------------------------
Vec = tuple[float, float]


def _add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1])


def _mul(a: Vec, s: float) -> Vec:
    return (a[0] * s, a[1] * s)


def polar_axis_unit(lat_deg: float) -> Vec:
    """Unit vector of the polar (RA) axis: altitude = latitude, toward +x."""
    r = math.radians(lat_deg)
    return (math.cos(r), math.sin(r))


def _perp_up(lat_deg: float) -> Vec:
    """Unit vector _|_ to the polar axis, on the OTA (up) side."""
    r = math.radians(lat_deg)
    return (-math.sin(r), math.cos(r))


def _perp_down(lat_deg: float) -> Vec:
    """Unit vector _|_ to the polar axis, on the counterweight (down) side."""
    r = math.radians(lat_deg)
    return (math.sin(r), -math.cos(r))


def _oriented_rect(center: Vec, along: Vec, cross: Vec, length: float, width: float) -> list[Vec]:
    """Four corners of a rectangle centred at ``center`` with the given axes."""
    a = _mul(along, length / 2.0)
    c = _mul(cross, width / 2.0)
    return [
        _add(_add(center, a), c),
        _add(_add(center, a), _mul(c, -1)),
        _add(_add(center, _mul(a, -1)), _mul(c, -1)),
        _add(_add(center, _mul(a, -1)), c),
    ]


# --------------------------------------------------------------------------
# Geometry model — all lengths in metres, straight from params.py.
# --------------------------------------------------------------------------
def build_geometry(ota: P.OTA | None = None) -> dict:
    """Assemble the meridian-plane geometry of the GEM from params.py.

    Returns a dict of named parts (each a list of corner Vecs) plus the scalar
    dimensions used for annotation.  DERIVED placement constants are flagged.
    """
    if ota is None:
        ota = P.MN78  # params default across the proofs

    lat = P.SITE.latitude_deg
    u_ax = polar_axis_unit(lat)
    up = _perp_up(lat)
    down = _perp_down(lat)

    # --- pier + plates (stacked on +y) ---
    pier_h = P.PIER.height_above_m
    pier_d = P.PIER.diameter_m
    tp_thk = P.PIER.top_plate_thk_m
    tp_side = P.PIER.top_plate_side_m
    adapter_thk = u.inch(0.75)   # pier_adapter.scad, ASSUMED added part
    adapter_side = u.inch(10.0)  # pier_adapter.scad, ASSUMED added part

    pier = [(-pier_d / 2, 0.0), (pier_d / 2, 0.0), (pier_d / 2, pier_h), (-pier_d / 2, pier_h)]
    y0 = pier_h
    top_plate = [(-tp_side / 2, y0), (tp_side / 2, y0),
                 (tp_side / 2, y0 + tp_thk), (-tp_side / 2, y0 + tp_thk)]
    y0 += tp_thk
    adapter = [(-adapter_side / 2, y0), (adapter_side / 2, y0),
               (adapter_side / 2, y0 + adapter_thk), (-adapter_side / 2, y0 + adapter_thk)]
    adapter_top = y0 + adapter_thk

    # --- RA housing on the polar axis ---
    ra_depth = P.RA_HOUSING.depth_m
    ra_face = P.RA_HOUSING.outer_x_m
    dec_face = P.DEC_HOUSING.outer_x_m
    dec_depth = P.DEC_HOUSING.depth_m

    # RA housing centre: lifted off the adapter so the tilted block clears it. DERIVED.
    p_ra = (0.0, adapter_top + ra_face / 2.0 * math.sin(math.radians(lat)) + 0.02)
    ra_housing = _oriented_rect(p_ra, u_ax, up, ra_depth, ra_face)

    # DEC head at the far end of the RA axis. DERIVED seat distance.
    L_ra = ra_depth + dec_face / 2.0 + 0.04
    c_dec = _add(p_ra, _mul(u_ax, L_ra))
    dec_housing = _oriented_rect(c_dec, u_ax, up, dec_depth, dec_face)

    # --- OTA tube, parallel to the polar axis, on the saddle (up) side ---
    saddle = 0.05  # stiffness.SADDLE_LEVER_M, ASSUMED
    ota_offset = dec_face / 2.0 + saddle + ota.tube_od_m / 2.0
    tube_center = _add(c_dec, _mul(up, ota_offset))
    # saddle ~1/3 up the tube: shift the tube so more of it rises toward the pole
    tube_center = _add(tube_center, _mul(u_ax, ota.tube_length_m / 6.0))
    ota_tube = _oriented_rect(tube_center, u_ax, up, ota.tube_length_m, ota.tube_od_m)

    # --- counterweight shaft on the down side ---
    cw_len = P.COUNTERWEIGHTS.shaft_len_m
    cw_dia = P.COUNTERWEIGHTS.shaft_dia_m
    cw_start = _add(c_dec, _mul(down, dec_face / 2.0))
    cw_center = _add(cw_start, _mul(down, cw_len / 2.0))
    cw_shaft = _oriented_rect(cw_center, down, up, cw_len, cw_dia)

    # counterweight discs near the far end of the shaft (12.5 kg available)
    disc_od = 0.127
    discs = []
    for k, frac in enumerate((0.72, 0.82, 0.92)):
        dc = _add(cw_start, _mul(down, cw_len * frac))
        discs.append(_oriented_rect(dc, down, up, 0.04, disc_od))

    return {
        "ota": ota,
        "lat": lat,
        "u_axis": u_ax,
        "parts": {
            "pier": pier,
            "top_plate": top_plate,
            "adapter": adapter,
            "ra_housing": ra_housing,
            "dec_housing": dec_housing,
            "ota_tube": ota_tube,
            "cw_shaft": cw_shaft,
        },
        "discs": discs,
        "dims": {
            "pier_h": pier_h,
            "pier_d": pier_d,
            "tube_len": ota.tube_length_m,
            "tube_od": ota.tube_od_m,
            "cw_len": cw_len,
            "cw_dia": cw_dia,
            "adapter_side": adapter_side,
            "adapter_thk": adapter_thk,
        },
        "anchors": {
            "p_ra": p_ra,
            "c_dec": c_dec,
            "tube_center": tube_center,
            "cw_start": cw_start,
            "adapter_top": adapter_top,
        },
    }


# --------------------------------------------------------------------------
# SVG rendering.
# --------------------------------------------------------------------------
_STYLE = {
    "pier": ("#8a8577", "#4a463d"),
    "top_plate": ("#4c4c52", "#2a2a2e"),
    "adapter": ("#c9a83d", "#7a6417"),
    "ra_housing": ("#b9c2c8", "#5d666c"),
    "dec_housing": ("#a9b4bb", "#525b61"),
    "ota_tube": ("#20232a", "#000000"),
    "cw_shaft": ("#3a3a40", "#101014"),
}


def _fmt_m(x: float) -> str:
    return f"{x:.3f} m"


def _fmt_mm(x: float) -> str:
    return f"{x * 1000:.0f} mm"


def render_svg(ota: P.OTA | None = None, scale_px_per_m: float = 300.0) -> str:
    """Render the GEM meridian elevation to an SVG string (pure stdlib)."""
    geo = build_geometry(ota)
    ota = geo["ota"]

    # Collect all points to compute bounds (maths frame, +y up).
    all_pts: list[Vec] = []
    for poly in geo["parts"].values():
        all_pts.extend(poly)
    for d in geo["discs"]:
        all_pts.extend(d)

    xs = [p[0] for p in all_pts]
    ys = [p[1] for p in all_pts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(0.0, max(ys))  # include grade (y=0)

    pad_m = 0.55
    label_pad_m = 1.15  # extra room on the right for the dimension column
    min_x -= pad_m
    max_x += pad_m + label_pad_m
    min_y -= pad_m
    max_y += pad_m

    S = scale_px_per_m
    width_px = (max_x - min_x) * S
    height_px = (max_y - min_y) * S

    def tx(x: float) -> float:
        return (x - min_x) * S

    def ty(y: float) -> float:
        return (max_y - y) * S  # flip: SVG +y is down

    def poly_svg(poly: list[Vec]) -> str:
        return " ".join(f"{tx(px):.1f},{ty(py):.1f}" for px, py in poly)

    parts: list[str] = []

    # --- header + defs ---
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width_px:.0f}" height="{height_px:.0f}" '
        f'viewBox="0 0 {width_px:.1f} {height_px:.1f}" '
        f'font-family="Helvetica, Arial, sans-serif">'
    )
    parts.append(
        '<rect x="0" y="0" width="100%" height="100%" fill="#f6f7f9"/>'
    )

    # --- ground line + hatch ---
    gy = ty(0.0)
    parts.append(
        f'<line x1="0" y1="{gy:.1f}" x2="{width_px:.1f}" y2="{gy:.1f}" '
        f'stroke="#7a6417" stroke-width="2"/>'
    )
    hx = 0.0
    while hx < width_px:
        parts.append(
            f'<line x1="{hx:.1f}" y1="{gy:.1f}" x2="{hx - 10:.1f}" y2="{gy + 12:.1f}" '
            f'stroke="#b7a24a" stroke-width="1"/>'
        )
        hx += 18

    # --- polar-axis centreline (through RA housing to DEC head) ---
    p_ra = geo["anchors"]["p_ra"]
    u_ax = geo["u_axis"]
    a0 = _add(p_ra, _mul(u_ax, -0.12))
    a1 = _add(geo["anchors"]["c_dec"], _mul(u_ax, 0.20))
    parts.append(
        f'<line x1="{tx(a0[0]):.1f}" y1="{ty(a0[1]):.1f}" '
        f'x2="{tx(a1[0]):.1f}" y2="{ty(a1[1]):.1f}" '
        f'stroke="#c0392b" stroke-width="1.3" stroke-dasharray="9 5"/>'
    )

    # --- parts (draw pier first so the head overlaps it) ---
    order = ["pier", "top_plate", "adapter", "cw_shaft", "ra_housing", "dec_housing", "ota_tube"]
    for name in order:
        fill, stroke = _STYLE[name]
        parts.append(
            f'<polygon points="{poly_svg(geo["parts"][name])}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>'
        )

    # counterweight discs
    for d in geo["discs"]:
        parts.append(
            f'<polygon points="{poly_svg(d)}" fill="#111318" stroke="#000" stroke-width="1"/>'
        )

    # --- dimension annotations (real numbers) ---
    dims = geo["dims"]

    def dim_line(x1, y1, x2, y2, text, ty_off=-6, color="#20232a"):
        out = [
            f'<line x1="{tx(x1):.1f}" y1="{ty(y1):.1f}" x2="{tx(x2):.1f}" y2="{ty(y2):.1f}" '
            f'stroke="{color}" stroke-width="1" marker-start="url(#a)" marker-end="url(#a)"/>'
        ]
        mx = (tx(x1) + tx(x2)) / 2.0
        my = (ty(y1) + ty(y2)) / 2.0 + ty_off
        out.append(
            f'<text x="{mx:.1f}" y="{my:.1f}" font-size="13" fill="{color}" '
            f'text-anchor="middle">{text}</text>'
        )
        return "".join(out)

    # arrow marker
    parts.append(
        '<defs><marker id="a" markerWidth="9" markerHeight="9" refX="4.5" refY="4.5" '
        'orient="auto"><path d="M1,1 L8,4.5 L1,8 Z" fill="#20232a"/></marker></defs>'
    )

    # pier height dimension (left of pier)
    xdim = -P.PIER.diameter_m / 2 - 0.30
    parts.append(dim_line(xdim, 0.0, xdim, dims["pier_h"],
                          f'pier {_fmt_m(dims["pier_h"])} ({dims["pier_h"] / u.IN_TO_M:.0f}")',
                          ty_off=0, color="#4a463d"))
    parts.append(
        f'<text x="{tx(xdim) - 8:.1f}" y="{ty(dims["pier_h"] / 2):.1f}" font-size="12" '
        f'fill="#4a463d" text-anchor="end" transform="rotate(-90 {tx(xdim) - 8:.1f} {ty(dims["pier_h"] / 2):.1f})">'
        f'&#216; {_fmt_m(dims["pier_d"])}</text>'
    )

    # OTA tube length dimension (along the tube axis)
    ota_poly = geo["parts"]["ota_tube"]
    up = _perp_up(geo["lat"])
    tl_a = _add(ota_poly[3], _mul(up, 0.12))  # near end top-left corner
    tl_b = _add(ota_poly[2], _mul(up, 0.12))  # far end
    parts.append(dim_line(tl_a[0], tl_a[1], tl_b[0], tl_b[1],
                          f'OTA {ota.name.split("(")[0].strip()}: L {_fmt_m(dims["tube_len"])}',
                          ty_off=-8, color="#20232a"))

    # counterweight shaft length
    cw_poly = geo["parts"]["cw_shaft"]
    parts.append(dim_line(cw_poly[0][0], cw_poly[0][1], cw_poly[3][0], cw_poly[3][1],
                          f'CW shaft {_fmt_m(dims["cw_len"])} ({dims["cw_len"] / u.IN_TO_M:.0f}")',
                          ty_off=14, color="#101014"))

    # latitude callout at the RA housing
    parts.append(
        f'<text x="{tx(p_ra[0]) + 14:.1f}" y="{ty(p_ra[1]) + 4:.1f}" font-size="13" '
        f'fill="#c0392b">polar axis @ lat {geo["lat"]:.1f}&#176;</text>'
    )

    # --- title + legend block (top-left) ---
    tube_od_txt = _fmt_m(dims["tube_od"])
    parts.append(
        '<text x="14" y="26" font-size="19" font-weight="bold" fill="#20232a">'
        'NIGHTWATCH GEM — meridian elevation (park pose)</text>'
    )
    parts.append(
        f'<text x="14" y="46" font-size="13" fill="#555">'
        f'OTA {ota.name} &#183; tube &#216; {tube_od_txt} &#183; '
        f'mass {ota.mass_kg:.0f} kg + {P.IMAGING_TRAIN.mass_kg:.0f} kg train &#183; '
        f'drawn to scale from params.py</text>'
    )

    legend = [
        ("pier", "concrete pier 12\" &#216;"),
        ("adapter", "adapter 10x10x0.75\""),
        ("ra_housing", "RA housing (CSF-32, 6008)"),
        ("dec_housing", "DEC housing + Losmandy-D (CSF-25, 6006)"),
        ("ota_tube", "OTA tube"),
        ("cw_shaft", "counterweight shaft"),
    ]
    ly = 64
    for key, txt in legend:
        fill, stroke = _STYLE[key]
        parts.append(
            f'<rect x="14" y="{ly - 10:.0f}" width="16" height="12" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="1"/>'
        )
        parts.append(f'<text x="36" y="{ly:.0f}" font-size="12" fill="#333">{txt}</text>')
        ly += 18

    parts.append("</svg>")
    return "\n".join(parts)


def main(out_path: str | Path = DEFAULT_OUT, ota: P.OTA | None = None) -> Path:
    out_path = Path(out_path)
    svg = render_svg(ota)
    out_path.write_text(svg, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    p = main()
    geo = build_geometry()
    print(f"wrote {p}  ({p.stat().st_size} bytes)")
    print(f"  OTA        : {geo['ota'].name}")
    print(f"  pier height: {geo['dims']['pier_h']:.3f} m")
    print(f"  tube length: {geo['dims']['tube_len']:.3f} m")
    print(f"  CW shaft   : {geo['dims']['cw_len']:.3f} m")
