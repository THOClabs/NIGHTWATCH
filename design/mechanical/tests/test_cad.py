"""
CAD proof: the parametric geometry is driven by params.py (not hand-typed), the
GEM elevation is physically sensible, the SVG previewer actually writes a valid
file, and every OpenSCAD part carries its render command + params.py traceability.
"""

import math
from pathlib import Path

from design.mechanical.cad import svg_preview as sp
from design.mechanical.calc import params as P

CAD_DIR = Path(sp.__file__).resolve().parent
SCAD_FILES = ["ra_housing.scad", "dec_housing.scad", "pier_adapter.scad",
              "counterweight_shaft.scad", "assembly.scad"]


# --------------------------------------------------------------------------
# Vector maths of the polar axis.
# --------------------------------------------------------------------------
def test_polar_axis_is_unit_at_latitude():
    ux, uy = sp.polar_axis_unit(P.SITE.latitude_deg)
    assert math.isclose(math.hypot(ux, uy), 1.0, rel_tol=1e-12)
    # Altitude of the polar axis equals the site latitude.
    assert math.isclose(math.degrees(math.atan2(uy, ux)), P.SITE.latitude_deg, rel_tol=1e-9)


def test_perp_vectors_are_orthogonal_to_axis():
    lat = P.SITE.latitude_deg
    ax = sp.polar_axis_unit(lat)
    for perp in (sp._perp_up(lat), sp._perp_down(lat)):
        dot = ax[0] * perp[0] + ax[1] * perp[1]
        assert abs(dot) < 1e-12
    # up side points up, down side points down.
    assert sp._perp_up(lat)[1] > 0
    assert sp._perp_down(lat)[1] < 0


# --------------------------------------------------------------------------
# Geometry is sourced from params.py, not hardcoded.
# --------------------------------------------------------------------------
def test_dimensions_come_from_params():
    g = sp.build_geometry(P.MN78)
    d = g["dims"]
    assert d["pier_h"] == P.PIER.height_above_m
    assert d["pier_d"] == P.PIER.diameter_m
    assert d["tube_len"] == P.MN78.tube_length_m
    assert d["tube_od"] == P.MN78.tube_od_m
    assert d["cw_len"] == P.COUNTERWEIGHTS.shaft_len_m
    assert d["cw_dia"] == P.COUNTERWEIGHTS.shaft_dia_m


def test_ota_case_changes_geometry():
    """Swapping the OTA case must change the drawn tube — proof it's parametric."""
    assert sp.build_geometry(P.MN76)["dims"]["tube_len"] != \
        sp.build_geometry(P.MN78)["dims"]["tube_len"]


# --------------------------------------------------------------------------
# The elevation is physically sensible.
# --------------------------------------------------------------------------
def _ymin(poly):
    return min(p[1] for p in poly)


def _ymax(poly):
    return max(p[1] for p in poly)


def test_head_sits_above_pier_top():
    g = sp.build_geometry()
    pier_top = _ymax(g["parts"]["pier"])
    # RA housing and DEC head are carried above the pier top.
    assert _ymin(g["parts"]["ra_housing"]) >= pier_top - 1e-6
    assert g["anchors"]["c_dec"][1] > pier_top


def test_ota_reaches_toward_pole_above_dec():
    """OTA points at the pole: its top must clear the DEC head (up the polar axis)."""
    g = sp.build_geometry()
    assert _ymax(g["parts"]["ota_tube"]) > _ymax(g["parts"]["dec_housing"])


def test_counterweight_hangs_on_the_down_side():
    """CW shaft must sit below the DEC head and on the opposite side of the polar
    axis from the OTA (classical GEM). 'Sides' are measured perpendicular to the
    inclined axis, not by raw x — both parts shift up the +x polar axis."""
    g = sp.build_geometry()
    c_dec = g["anchors"]["c_dec"]
    up = sp._perp_up(g["lat"])   # unit vector _|_ axis, OTA side

    def perp_proj(poly):
        cx = sum(p[0] for p in poly) / 4.0 - c_dec[0]
        cy = sum(p[1] for p in poly) / 4.0 - c_dec[1]
        return cx * up[0] + cy * up[1]

    assert _ymin(g["parts"]["cw_shaft"]) < c_dec[1]              # hangs below the head
    assert perp_proj(g["parts"]["ota_tube"]) > 0                 # OTA on the up side
    assert perp_proj(g["parts"]["cw_shaft"]) < 0                 # CW on the down side


# --------------------------------------------------------------------------
# SVG output: valid, dimensioned with the real numbers, and it writes.
# --------------------------------------------------------------------------
def test_render_svg_is_valid_and_dimensioned():
    svg = sp.render_svg(P.MN78)
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    assert "<polygon" in svg
    # Real dimensions, formatted from params.py, must appear as annotations.
    assert f"{P.PIER.height_above_m:.3f} m" in svg          # 0.914 m
    assert f"{P.MN78.tube_length_m:.3f} m" in svg           # 1.400 m
    assert f"{P.COUNTERWEIGHTS.shaft_len_m:.3f} m" in svg   # 0.457 m
    assert f"{P.SITE.latitude_deg:.1f}" in svg              # 38.9
    assert "Losmandy-D" in svg
    assert "CSF-32" in svg


def test_main_writes_svg(tmp_path):
    out = sp.main(tmp_path / "preview.svg")
    assert out.exists() and out.stat().st_size > 2000
    assert out.read_text(encoding="utf-8").startswith("<svg")


def test_committed_preview_exists_and_matches():
    """The checked-in preview_assembly.svg must be present and current."""
    committed = CAD_DIR / "preview_assembly.svg"
    assert committed.exists(), "run svg_preview.py to generate preview_assembly.svg"
    assert committed.read_text(encoding="utf-8") == sp.render_svg()


# --------------------------------------------------------------------------
# OpenSCAD parts: present, render-documented, and traceable to params.py.
# --------------------------------------------------------------------------
def test_all_scad_parts_present():
    for f in SCAD_FILES:
        assert (CAD_DIR / f).exists(), f"missing CAD part {f}"


def test_scad_parts_have_render_cmd_and_param_trace():
    for f in SCAD_FILES:
        text = (CAD_DIR / f).read_text(encoding="utf-8")
        assert "openscad -o" in text, f"{f} lacks a render command"
        assert "params.py" in text, f"{f} lacks params.py traceability"
        assert "MILLIMETRES" in text, f"{f} lacks a units declaration"


def test_scad_key_dimensions_trace_to_params():
    """Spot-check that headline dims in the .scad match u.mm/u.inch of params.py."""
    ra = (CAD_DIR / "ra_housing.scad").read_text(encoding="utf-8")
    assert f"{P.RA_HOUSING.outer_x_m * 1000:.1f}" in ra          # 203.2
    assert f"{P.RA_DRIVE.bore_m * 1000:.1f}" in ra               # 80.0
    dec = (CAD_DIR / "dec_housing.scad").read_text(encoding="utf-8")
    assert f"{P.DEC_DRIVE.bore_m * 1000:.1f}" in dec             # 64.0
    assert "Losmandy" in dec
    cw = (CAD_DIR / "counterweight_shaft.scad").read_text(encoding="utf-8")
    assert f"{P.COUNTERWEIGHTS.shaft_dia_m * 1000:.2f}" in cw    # 31.75
    assembly = (CAD_DIR / "assembly.scad").read_text(encoding="utf-8")
    for part in ("ra_housing.scad", "dec_housing.scad", "pier_adapter.scad",
                 "counterweight_shaft.scad"):
        assert f"use <{part}>" in assembly
