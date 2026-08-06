"""
Fabrication control-drawing generator (SVG, one per fabricated part).

Each sheet is a *bid control drawing*: a to-scale envelope of the stock with the
controlling overall dimensions (dual inch + mm), a keyed feature/dimension table,
and an ASME-Y14-style title block carrying material, finish, tolerance, GD&T, and
the "ISSUED FOR BID / FOR PE REVIEW" status. The parametric ``cad/*.scad`` (and the
STEP exported from it) remain the machining master for 3-D features; this sheet is
the dimensioned, quotable summary a shop reviews to price the job.

Pure stdlib string templating (no CAD app, no third-party libs) so it regenerates
deterministically and a test can diff it against the parts registry.
"""

from __future__ import annotations

import html
import pathlib

from design.mechanical.tender.gen import partspec as ps

OUT = pathlib.Path(__file__).resolve().parents[1] / "drawings"
REV = "A"
STATUS = "ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION"

SHEET_W, SHEET_H = 1120, 792   # ~ ANSI B landscape, px
MARGIN = 16
TITLE_H = 150


def _in(mm: float) -> float:
    return round(mm / 25.4, 3)


def _dual(mm: float) -> str:
    return f"{mm:.1f} mm [{_in(mm):.3f} in]"


def _esc(s) -> str:
    return html.escape(str(s))


def _envelope_dims(p: ps.Part):
    """Return (label, width_mm, height_mm, depth_note) for the drawn envelope."""
    kind = p.stock[0]
    if kind == "plate":
        _, L, W, T = p.stock
        return "PLATE", L, W, f"THK {_dual(T)}"
    if kind == "round":
        _, dia, length = p.stock
        return "ROUND", length, dia, f"Ø{_dual(dia)}"
    if kind == "hss":
        _, o, wall, length = p.stock
        return "HSS", length, o, f"{_dual(o)} sq x {_dual(wall)} wall"
    return "ITEM", 100.0, 60.0, ""


def _svg_header() -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SHEET_W}" height="{SHEET_H}" '
        f'viewBox="0 0 {SHEET_W} {SHEET_H}" font-family="Helvetica,Arial,sans-serif">',
        f'<rect x="0" y="0" width="{SHEET_W}" height="{SHEET_H}" fill="white"/>',
        f'<rect x="{MARGIN}" y="{MARGIN}" width="{SHEET_W-2*MARGIN}" height="{SHEET_H-2*MARGIN}" '
        f'fill="none" stroke="black" stroke-width="2"/>',
    ]


def _dim_line(x1, y1, x2, y2, label, above=True):
    """A dimension line with arrow ticks and a centred label."""
    mid_x = (x1 + x2) / 2
    mid_y = (y1 + y2) / 2
    dy = -6 if above else 14
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#0645ad" stroke-width="1"/>'
        f'<line x1="{x1}" y1="{y1-4}" x2="{x1}" y2="{y1+4}" stroke="#0645ad" stroke-width="1"/>'
        f'<line x1="{x2}" y1="{y2-4}" x2="{x2}" y2="{y2+4}" stroke="#0645ad" stroke-width="1"/>'
        f'<text x="{mid_x}" y="{mid_y+dy}" font-size="12" fill="#0645ad" text-anchor="middle">{_esc(label)}</text>'
    )


def _title_block(p: ps.Part) -> list[str]:
    x0 = MARGIN
    y0 = SHEET_H - MARGIN - TITLE_H
    w = SHEET_W - 2 * MARGIN
    lines = [f'<rect x="{x0}" y="{y0}" width="{w}" height="{TITLE_H}" fill="none" stroke="black" stroke-width="2"/>']
    # horizontal rules
    for yy in (y0 + 26, y0 + 26 + 32, y0 + 26 + 64, y0 + 26 + 96):
        lines.append(f'<line x1="{x0}" y1="{yy}" x2="{x0+w}" y2="{yy}" stroke="black" stroke-width="1"/>')
    # vertical split
    xr = x0 + w - 300
    lines.append(f'<line x1="{xr}" y1="{y0}" x2="{xr}" y2="{y0+TITLE_H}" stroke="black" stroke-width="1"/>')

    def txt(x, y, s, size=12, weight="normal", fill="black"):
        return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                f'fill="{fill}">{_esc(s)}</text>')

    lines.append(txt(x0 + 10, y0 + 18, "NIGHTWATCH OBSERVATORY — MOUNT & ROLL-OFF TENDER", 13, "bold"))
    lines.append(txt(x0 + 10, y0 + 46, f"PART: {p.name}", 13, "bold"))
    lines.append(txt(x0 + 10, y0 + 46 + 26, f"MATERIAL: {p.material}"))
    lines.append(txt(x0 + 10, y0 + 46 + 26 + 26, f"FINISH: {p.finish}"))
    lines.append(txt(x0 + 10, y0 + 46 + 26 + 52, f"TOLERANCE: {p.tolerance}"))
    lines.append(txt(x0 + 10, y0 + 46 + 26 + 76,
                     f"SURFACE FINISH: Ra {p.ra_um} um" if p.ra_um else "SURFACE FINISH: n/a", 11))
    # right column
    lines.append(txt(xr + 10, y0 + 18, f"DWG {p.part_no}", 13, "bold"))
    lines.append(txt(xr + 10, y0 + 44, f"PKG {p.package} — {ps.PACKAGES[p.package][0]}", 10))
    lines.append(txt(xr + 10, y0 + 44 + 26, f"PROCESS: {p.process}", 10))
    lines.append(txt(xr + 10, y0 + 44 + 52, f"QTY: {p.qty}    REV: {REV}    UNITS: mm [in]", 10))
    lines.append(txt(xr + 10, y0 + 44 + 78, "STATUS:", 9, "bold", "#a00"))
    lines.append(txt(xr + 10, y0 + 44 + 92, STATUS, 8, "bold", "#a00"))
    return lines


# key_dims_mm entries whose *name* contains one of these are NOT linear dimensions
# and must not be rendered as "mm [in]" (they are counts, angles, pressures, etc.).
_NONLENGTH_TOKENS = (
    "hole", "member", "rail", "count", "angle", "deg", "psi", "f'c", "ratio",
    "torque", "nm", "(v)", "ach", "period", "obstruction", "(psf)", "spacing",
    "kg", "area", "(each)",
)


def _is_length_key(key: str) -> bool:
    k = key.lower()
    # "member length (each)" / "rail length (each)" ARE lengths despite the tokens
    if "length" in k:
        return True
    return not any(tok in k for tok in _NONLENGTH_TOKENS)


def _fmt_value(key: str, v) -> str:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return str(v)
    if _is_length_key(key) and v > 3:
        return _dual(float(v))
    return str(int(v)) if float(v).is_integer() else str(v)


def _feature_table(p: ps.Part, x0: int, y0: int) -> list[str]:
    lines = [f'<text x="{x0}" y="{y0-8}" font-size="13" font-weight="bold">KEY DIMENSIONS &amp; FEATURES</text>']
    y = y0 + 14
    for k, v in p.key_dims_mm.items():
        val = _fmt_value(k, v)
        lines.append(f'<text x="{x0}" y="{y}" font-size="12">• {_esc(k)}: {_esc(val)}</text>')
        y += 18
    lines.append(f'<text x="{x0}" y="{y+6}" font-size="11" fill="#555">PROVENANCE: {_esc(p.provenance)}</text>')
    if p.notes:
        lines.append(f'<text x="{x0}" y="{y+24}" font-size="11" fill="#555">NOTE: {_esc(p.notes)}</text>')
    return lines


def render_part(p: ps.Part) -> str:
    parts = _svg_header()
    label, w_mm, h_mm, depth_note = _envelope_dims(p)

    # Scale the envelope into the left drawing zone.
    zone_x, zone_y, zone_w, zone_h = 60, 90, 470, 420
    scale = min(zone_w / max(w_mm, 1), zone_h / max(h_mm, 1)) * 0.7
    rw, rh = w_mm * scale, h_mm * scale
    rx = zone_x + (zone_w - rw) / 2
    ry = zone_y + (zone_h - rh) / 2

    parts.append(f'<text x="{zone_x}" y="{zone_y-24}" font-size="14" font-weight="bold">'
                 f'{_esc(p.part_no)} — {_esc(p.name)}</text>')
    parts.append(f'<text x="{zone_x}" y="{zone_y-6}" font-size="11" fill="#555">'
                 f'Envelope ({label}) — bid control drawing; .scad/STEP is the 3-D master.</text>')

    if label == "ROUND":
        parts.append(f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" fill="#eef3fb" '
                     f'stroke="black" stroke-width="1.5"/>')
        parts.append(f'<line x1="{rx-10}" y1="{ry+rh/2}" x2="{rx+rw+10}" y2="{ry+rh/2}" '
                     f'stroke="#0645ad" stroke-width="0.7" stroke-dasharray="8 3 2 3"/>')
    else:
        parts.append(f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" fill="#eef3fb" '
                     f'stroke="black" stroke-width="1.5"/>')

    # overall dimensions
    parts.append(_dim_line(rx, ry - 18, rx + rw, ry - 18,
                           (f"L {_dual(w_mm)}" if label != "ROUND" else f"L {_dual(w_mm)}")))
    parts.append(_dim_line(rx + rw + 18, ry, rx + rw + 18, ry + rh,
                           (f"Ø {_dual(h_mm)}" if label == "ROUND" else f"W {_dual(h_mm)}"), above=False))
    parts.append(f'<text x="{rx+rw/2}" y="{ry+rh/2+4}" font-size="12" fill="#333" '
                 f'text-anchor="middle">{_esc(depth_note)}</text>')

    parts += _feature_table(p, 560, 120)
    parts += _title_block(p)
    parts.append("</svg>")
    return "\n".join(parts)


def generate_all() -> list[pathlib.Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for p in ps.fabricated_parts():
        path = OUT / f"{p.part_no}.svg"
        path.write_text(render_part(p))
        written.append(path)
    return written


if __name__ == "__main__":
    for pth in generate_all():
        print("wrote", pth.name)
    print(f"{len(list(OUT.glob('*.svg')))} drawings in {OUT}")
