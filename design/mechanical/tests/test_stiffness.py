"""Static-deflection proof: the mount head must hold the optical axis within the
5 arcsec pointing target under gravity. This is where the repo's asserted
'< 5 arcsec' is finally computed -- and it FAILS, governed by the short-span
deep-groove bearings, which is the finding worth surfacing."""

import math

from design.mechanical.calc import params as P
from design.mechanical.calc import stiffness
from design.mechanical.calc.budget import Verdict


def test_box_section_I_thicker_wall_is_stiffer():
    """12 mm walls give a larger second moment than 8 mm walls."""
    assert stiffness.box_section_I(P.RA_HOUSING_12MM) > stiffness.box_section_I(P.RA_HOUSING)
    assert stiffness.box_section_I(P.DEC_HOUSING_12MM) > stiffness.box_section_I(P.DEC_HOUSING)


def test_8mm_baseline_worse_than_12mm():
    """The bold 12 mm variant must deflect less than the 8 mm baseline."""
    d8 = stiffness.total_deflection_arcsec(P.MN78, P.RA_HOUSING, P.DEC_HOUSING)
    d12 = stiffness.total_deflection_arcsec(P.MN78, P.RA_HOUSING_12MM, P.DEC_HOUSING_12MM)
    assert d8 > d12


def test_both_variants_fail_5_arcsec_target():
    """Honest finding: neither wall thickness meets 5 arcsec -- both are ~8-9x over."""
    d8 = stiffness.total_deflection_arcsec(P.MN78, P.RA_HOUSING, P.DEC_HOUSING)
    d12 = stiffness.total_deflection_arcsec(P.MN78, P.RA_HOUSING_12MM, P.DEC_HOUSING_12MM)
    assert d8 > P.DEFLECTION_TARGET_ARCSEC
    assert d12 > P.DEFLECTION_TARGET_ARCSEC
    # Both blow the budget by a large factor (bearing-dominated), not marginally.
    assert d8 > 8.0 * P.DEFLECTION_TARGET_ARCSEC
    assert d12 > 8.0 * P.DEFLECTION_TARGET_ARCSEC


def test_bearing_compliance_dominates():
    """The short 63.5/76.2 mm bearing spans, not the beams, govern the deflection."""
    b = stiffness.deflection_breakdown(P.MN78, P.RA_HOUSING, P.DEC_HOUSING)
    assert b["bearing_rad"] > b["beam_rad"]
    # Bearings are the overwhelming majority of the error budget.
    assert b["bearing_rad"] / b["total_rad"] > 0.90
    # And within the bearings, the softer/short-span DEC (6006) dominates the RA (6008).
    assert b["dec_bearing_rad"] > b["ra_bearing_rad"]


def test_12mm_only_helps_the_beam_term():
    """Thicker walls stiffen the beams but not the bearings, so the win is tiny."""
    b8 = stiffness.deflection_breakdown(P.MN78, P.RA_HOUSING, P.DEC_HOUSING)
    b12 = stiffness.deflection_breakdown(P.MN78, P.RA_HOUSING_12MM, P.DEC_HOUSING_12MM)
    # Bearing terms are identical between wall thicknesses.
    assert math.isclose(b8["bearing_rad"], b12["bearing_rad"], rel_tol=1e-9)
    # Beam term improves, but the total barely moves (< 1 arcsec).
    assert b12["beam_rad"] < b8["beam_rad"]
    assert (b8["total_arcsec"] - b12["total_arcsec"]) < 1.0


def test_heavier_ota_deflects_more():
    """MN78 (18 kg payload, longer lever) must deflect more than MN76."""
    d_light = stiffness.total_deflection_arcsec(P.MN76, P.RA_HOUSING, P.DEC_HOUSING)
    d_heavy = stiffness.total_deflection_arcsec(P.MN78, P.RA_HOUSING, P.DEC_HOUSING)
    assert d_heavy > d_light


def test_total_helper_matches_breakdown():
    b = stiffness.deflection_breakdown(P.MN78, P.RA_HOUSING, P.DEC_HOUSING)
    d = stiffness.total_deflection_arcsec(P.MN78, P.RA_HOUSING, P.DEC_HOUSING)
    assert math.isclose(d, b["total_arcsec"], rel_tol=1e-12)


def test_evaluate_reports_fail_with_sf_below_one():
    r = stiffness.evaluate("MN78")
    assert r.verdict is Verdict.FAIL
    assert r.safety_factor is not None and r.safety_factor < 1.0
    assert any("TOTAL deflection" in ln.label for ln in r.lines)
    # The assumptions must disclose the ASSUMED bearing stiffness (honesty check).
    assert any("N/um" in a for a in r.assumptions)
