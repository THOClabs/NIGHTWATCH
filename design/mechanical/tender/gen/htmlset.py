"""
Drawing-set bundler — inlines every SVG control drawing into ONE self-contained,
print-to-PDF HTML document (a cover + drawing register + one drawing per page).

Pure stdlib. This is the single "drawing package" file to hand a vendor: open in
any browser, File > Print > Save as PDF gives an ANSI-B drawing set. Run:
    python3 -m design.mechanical.tender.gen.htmlset
"""

from __future__ import annotations

import pathlib

from design.mechanical.tender.gen import partspec as ps

DRAW = pathlib.Path(__file__).resolve().parents[1] / "drawings"
OUT = DRAW / "DRAWING_SET.html"

CSS = """
* { box-sizing: border-box; }
body { font-family: Helvetica, Arial, sans-serif; margin: 0; color: #111; }
.page { page-break-after: always; padding: 24px; }
.cover h1 { color: #1F3864; margin: 0 0 4px; }
.status { color: #a00; font-weight: bold; letter-spacing: .5px; }
table { border-collapse: collapse; width: 100%; font-size: 12px; margin-top: 12px; }
th, td { border: 1px solid #bbb; padding: 5px 7px; text-align: left; vertical-align: top; }
th { background: #1F3864; color: #fff; }
.drawing svg { width: 100%; height: auto; border: 1px solid #ccc; }
.cap { font-size: 12px; color: #555; margin: 6px 0 0; }
@media print { .page { padding: 0; } @page { size: 1120px 792px; margin: 8mm; } }
"""


def _register_rows() -> str:
    rows = []
    for p in ps.fabricated_parts():
        m = p.stock_mass_kg()
        rows.append(
            f"<tr><td>{p.part_no}</td><td>{p.name}</td><td>{p.package}</td>"
            f"<td>{p.material}</td><td>{p.finish}</td>"
            f"<td>{'' if m is None else f'{m:.1f}'}</td></tr>"
        )
    return "\n".join(rows)


def build() -> pathlib.Path:
    parts = [f"<!doctype html><html><head><meta charset='utf-8'>",
             f"<title>NIGHTWATCH Tender — Drawing Set</title><style>{CSS}</style></head><body>"]

    # Cover + register
    parts.append(
        "<div class='page cover'>"
        "<h1>NIGHTWATCH Observatory</h1>"
        "<h2>Mount &amp; Roll-off 'Turret' — Fabrication Drawing Set</h2>"
        "<p class='status'>ISSUED FOR BID / FOR PE REVIEW — NOT FOR CONSTRUCTION</p>"
        "<p class='cap'>Control drawings generated from design/mechanical/calc/params.py. "
        "The parametric <code>cad/*.scad</code> (and STEP exported from it) is the 3-D machining "
        "master; these sheets are the dimensioned, quotable summary. Dimensions are dual-unit "
        "(mm [inch]). Rev A.</p>"
        "<h3>Drawing register</h3>"
        "<table><tr><th>Drawing</th><th>Part</th><th>Pkg</th><th>Material</th>"
        "<th>Finish</th><th>Stock kg</th></tr>"
        f"{_register_rows()}</table>"
        "</div>"
    )

    for p in ps.fabricated_parts():
        svg = (DRAW / f"{p.part_no}.svg")
        if not svg.exists():
            continue
        body = svg.read_text()
        # strip the XML declaration if present so it inlines cleanly
        if body.startswith("<?xml"):
            body = body.split("?>", 1)[1]
        parts.append(f"<div class='page drawing'>{body}</div>")

    parts.append("</body></html>")
    OUT.write_text("\n".join(parts))
    return OUT


if __name__ == "__main__":
    print("wrote", build())
