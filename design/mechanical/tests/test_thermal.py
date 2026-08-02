"""Thermal focus-stability proof: the f/8 has a larger depth of focus than the
f/6 (a point in its favour), but the 6061-T6 tube walks the focus by many depths
of focus across the diurnal swing -> passive focus FAILS and a temperature-
compensated focuser is required. The Astrositall mirror term is negligible and a
sub-2 W dew heater suffices. FAIL (for passive focus) is the honest verdict."""

import math

from design.mechanical.calc import params as P
from design.mechanical.calc import thermal
from design.mechanical.calc.budget import Verdict


def test_depth_of_focus_f8_larger_than_f6():
    """DoF = 2*lambda*N^2 -> the slower f/8 tolerates more axial error than f/6."""
    dof_f6 = thermal.depth_of_focus_um(P.MN76)
    dof_f8 = thermal.depth_of_focus_um(P.MN78)
    assert dof_f8 > dof_f6
    # Scales as N^2: ratio must match (8/6)^2 within tight tolerance.
    assert math.isclose(dof_f8 / dof_f6, (8.0 / 6.0) ** 2, rel_tol=1e-9)


def test_depth_of_focus_formula_values():
    """Absolute check against 2*lambda*N^2 in micrometres."""
    lam = P.OPTICAL.wavelength_m
    assert math.isclose(thermal.depth_of_focus_um(P.MN76), 2 * lam * 36 * 1e6, rel_tol=1e-9)
    assert math.isclose(thermal.depth_of_focus_um(P.MN78), 2 * lam * 64 * 1e6, rel_tol=1e-9)
    # ~40 um at f/6, ~70 um at f/8.
    assert 39.0 < thermal.depth_of_focus_um(P.MN76) < 40.0
    assert 70.0 < thermal.depth_of_focus_um(P.MN78) < 71.0


def test_tube_defocus_per_kelvin_uses_aluminium_cte_and_tube_length():
    per_k = thermal.defocus_per_kelvin_um(P.MN78)
    cte = P.MATERIALS["6061-T6"].cte
    assert math.isclose(per_k, cte * P.MN78.tube_length_m * 1e6, rel_tol=1e-12)
    # Longer MN78 tube expands more per K than the shorter MN76 tube.
    assert thermal.defocus_per_kelvin_um(P.MN78) > thermal.defocus_per_kelvin_um(P.MN76)


def test_tube_defocus_exceeds_dof_within_diurnal_swing():
    """The governing claim: within the diurnal swing the aluminium tube walks the
    focus past the depth of focus, for BOTH tubes (f/8's larger DoF still loses)."""
    swing = P.ENV.diurnal_swing_c
    for ota in (P.MN76, P.MN78):
        defocus_over_swing = thermal.tube_defocus_um(ota, swing)
        assert defocus_over_swing > thermal.depth_of_focus_um(ota)
        # Equivalent statement: fewer kelvin to defocus than the swing spans.
        assert thermal.kelvin_to_defocus(ota) < swing


def test_only_a_couple_kelvin_before_out_of_focus():
    """K-to-defocus is only ~2 K on both tubes -> passive focus is fragile."""
    for ota in (P.MN76, P.MN78):
        k_edge = thermal.kelvin_to_defocus(ota)
        assert 1.5 < k_edge < 3.0
        assert k_edge < thermal.DEW_MARGIN_K  # even a small dew swing defocuses it


def test_tube_walks_many_depths_of_focus_over_swing():
    """Over the full ~22 K swing the tube should walk ~9-11 depths of focus."""
    swing = P.ENV.diurnal_swing_c
    for ota in (P.MN76, P.MN78):
        n_dof = thermal.tube_defocus_um(ota, swing) / thermal.depth_of_focus_um(ota)
        assert n_dof > 5.0  # comfortably more than a single DoF
        assert 8.0 < n_dof < 12.0


def test_astrositall_mirror_term_is_negligible():
    """The low-expansion primary contributes ~2 orders of magnitude less than the
    aluminium tube; on its own the mirror stays well inside the depth of focus."""
    for ota in (P.MN76, P.MN78):
        mir_per_k = thermal.mirror_defocus_per_kelvin_um(ota)
        tube_per_k = thermal.defocus_per_kelvin_um(ota)
        assert mir_per_k < 0.01 * tube_per_k          # >100x smaller
        # Mirror-only focus shift over the whole swing stays within the DoF.
        assert mir_per_k * P.ENV.diurnal_swing_c < thermal.depth_of_focus_um(ota)


def test_dew_heater_fits_within_the_all_sky_ring():
    """Holding the corrector a few K above dewpoint costs < the 2 W ring."""
    for ota in (P.MN76, P.MN78):
        w = thermal.dew_heater_power_w(ota)
        assert 0.0 < w < thermal.ALL_SKY_RING_W
    # P = h*A*dT relationship holds.
    w = thermal.dew_heater_power_w(P.MN78, h=10.0, dT=5.0)
    assert math.isclose(w, 10.0 * thermal.corrector_area_m2(P.MN78) * 5.0, rel_tol=1e-12)


def test_evaluate_fails_passive_focus_and_flags_the_fix():
    r = thermal.evaluate("MN78")
    # Passive focus does NOT hold the swing -> honest FAIL.
    assert r.verdict is Verdict.FAIL
    assert r.safety_factor is not None and r.safety_factor < 1.0
    text = (r.headline + " " + " ".join(r.assumptions)).lower()
    assert "compensat" in text          # temperature-compensated focuser
    assert "required" in text
    assert "astrositall" in text
    assert "dew" in text or "heater" in text
    # The comparison lines must be present.
    assert any("Depth of focus" in ln.label for ln in r.lines)
    assert any("per K" in ln.label for ln in r.lines)


def test_evaluate_both_ota_keys_fail_passive():
    for key in ("MN76", "MN78"):
        assert thermal.evaluate(key).verdict is Verdict.FAIL
