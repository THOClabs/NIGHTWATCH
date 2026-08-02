"""Bearing proof: rolling fatigue (L10) is astronomically long because the mount
barely turns, static safety is comfortable, and the governing finding is that the
'angular contact' 60xx are actually DEEP-GROOVE — angular-contact pairs are needed
for moment stiffness. FAIL is not expected here; the load capacity is a non-issue."""

import math

from design.mechanical.calc import bearings
from design.mechanical.calc import params as P
from design.mechanical.calc.budget import Verdict


def test_load_model_adds_weight_and_moment_couple():
    """P = W + M/span; the moment couple must dominate the tiny direct weight."""
    W = 176.5
    lever = 0.20
    span = 0.0762
    P_load = bearings.bearing_radial_load(W, lever, span)
    assert math.isclose(P_load, W + (W * lever) / span, rel_tol=1e-12)
    # The overturning couple is the real driver, not the direct weight.
    assert (W * lever) / span > W


def test_l10_life_is_astronomically_large():
    """At ~1 rev/sidereal day, L10 must exceed a million years on both axes."""
    ra = bearings.l10_years(P.BRG_RA_6008, bearings.ra_output_load(P.MN78))
    dec = bearings.l10_years(P.BRG_DEC_6006, bearings.dec_output_load(P.MN78))
    assert ra > 1.0e6
    assert dec > 1.0e6


def test_fatigue_is_not_the_constraint():
    """L10 dwarfs any realistic service life (>> 1000x a 100-year observatory)."""
    ra = bearings.l10_years(P.BRG_RA_6008, bearings.ra_output_load(P.MN78))
    assert ra > 1000 * 100  # >> 1000 service lifetimes of 100 years each


def test_l10_scales_with_load_cubed():
    """Doubling the load must cut L10 revolutions by ~8x (the (C/P)^3 law)."""
    base = bearings.l10_revolutions(P.BRG_RA_6008, 500.0)
    doubled = bearings.l10_revolutions(P.BRG_RA_6008, 1000.0)
    assert math.isclose(base / doubled, 8.0, rel_tol=1e-9)


def test_static_safety_is_comfortable():
    """S0 = C0/P should clear the pass gate with real margin on both axes."""
    ra_S0 = bearings.static_safety(P.BRG_RA_6008, bearings.ra_output_load(P.MN78))
    dec_S0 = bearings.static_safety(P.BRG_DEC_6006, bearings.dec_output_load(P.MN78))
    assert ra_S0 >= bearings.STATIC_SAFETY_PASS
    assert dec_S0 >= bearings.STATIC_SAFETY_PASS
    # Genuinely comfortable, not marginal.
    assert min(ra_S0, dec_S0) > 5.0


def test_evaluate_passes_with_the_angular_contact_finding():
    """Verdict PASS on load capacity, but the deep-groove caveat must be loud."""
    r = bearings.evaluate("MN78")
    assert r.verdict is Verdict.PASS
    assert r.safety_factor is not None and r.safety_factor >= bearings.STATIC_SAFETY_PASS
    text = (r.headline + " " + " ".join(r.assumptions)).lower()
    assert "deep-groove" in text
    assert "7008" in text and "7006" in text
    assert "angular" in text
    assert "stiffness" in text


def test_load_is_well_below_dynamic_rating():
    """Sanity: modelled loads are a small fraction of the dynamic ratings."""
    ra_load = bearings.ra_output_load(P.MN78)
    dec_load = bearings.dec_output_load(P.MN78)
    assert ra_load < 0.1 * P.BRG_RA_6008.C_dynamic_N
    assert dec_load < 0.1 * P.BRG_DEC_6006.C_dynamic_N
