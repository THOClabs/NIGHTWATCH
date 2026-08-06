"""Pier / foundation proof: a squat 12"x36" concrete pier is stiff, high in
frequency, and stable -- all four checks PASS -- but seismic overturning relies
on soil embedment (dead weight ALONE would not resist it), the one result worth
stating plainly."""

import math

from design.mechanical.calc import dynamics, pier, wind
from design.mechanical.calc import params as P
from design.mechanical.calc import units as u
from design.mechanical.calc.budget import Verdict


def test_pier_stiffness_matches_dynamics_single_source():
    """pier.py and dynamics.py must compute the identical pier stiffness."""
    assert math.isclose(pier.pier_lateral_stiffness_N_per_m(),
                        dynamics.pier_lateral_stiffness(), rel_tol=1e-12)


def test_pier_stiffness_is_tens_of_MN_per_m():
    k = pier.pier_lateral_stiffness_N_per_m()
    assert 1.0e7 < k < 1.0e8


def test_tilt_is_a_small_fraction_of_pointing_budget():
    """Operational-wind pier tilt is well under an arcsec -- << the 5" budget."""
    f = wind.drag_force_N(P.ENV.wind_gust_close_ms, P.MN78)
    tilt = pier.pier_tilt_arcsec(f)
    assert 0.0 < tilt < 1.0
    assert P.DEFLECTION_TARGET_ARCSEC / tilt > 5.0


def test_tilt_uses_conservative_tip_slope():
    """pier_tilt_arcsec is the tip slope (F L^2/2EI) = 1.5x the delta/L estimate."""
    f = 50.0
    delta = pier.pier_tip_deflection_m(f)
    naive = u.rad_to_arcsec(delta / P.PIER.height_above_m)   # delta/L
    slope = pier.pier_tilt_arcsec(f)
    assert math.isclose(slope / naive, 1.5, rel_tol=1e-9)


def test_shaft_mass_derived_from_geometry():
    """Counterweight shaft mass comes from its 303-SS geometry, ~3 kg."""
    m = pier.counterweight_shaft_mass_kg()
    assert 2.0 < m < 4.0


def test_first_mode_far_above_target():
    """Pier substructure first mode is hundreds of Hz -- pier is not the soft element."""
    m_tip = pier.tip_mass_kg(P.MN78, counterweighted=True)
    f = pier.pier_first_mode_hz(m_tip)
    assert f > 5.0 * P.NATURAL_FREQ_TARGET_HZ
    # Heavier tip mass lowers frequency (sqrt scaling).
    f_light = pier.pier_first_mode_hz(pier.tip_mass_kg(P.MN78, counterweighted=False))
    assert f_light > f


def test_seismic_base_shear_scales_with_sds_and_weight():
    V = pier.seismic_base_shear_N(200.0)
    assert math.isclose(V, P.ENV.seismic_sds_g * u.weight_N(200.0), rel_tol=1e-12)
    assert math.isclose(pier.seismic_base_shear_N(400.0) / V, 2.0, rel_tol=1e-9)


def test_embedment_is_what_makes_seismic_stable():
    """Honest finding: dead weight ALONE cannot resist overturning (SF < 1);
    soil passive resistance over the embedment is what provides stability."""
    M_ot = pier.seismic_overturning_Nm(P.MN78)
    Pp = pier.soil_passive_resultant_N()
    D = P.PIER.embed_depth_m
    W_total = u.weight_N(pier.pier_total_mass_kg() + pier.tip_mass_kg(P.MN78))
    M_resist_weight = W_total * (P.PIER.diameter_m / 2.0)
    M_resist_passive = Pp * (2.0 * D / 3.0)
    # Dead weight alone fails; embedment brings it comfortably over 2.
    assert M_resist_weight / M_ot < 1.0
    assert (M_resist_passive + M_resist_weight) / M_ot > 2.0


def test_sliding_resisted_by_passive_soil():
    """Passive soil resistance dwarfs the seismic base shear."""
    m_tip = pier.tip_mass_kg(P.MN78)
    V = pier.seismic_base_shear_N(m_tip + pier.pier_exposed_mass_kg())
    assert pier.soil_passive_resultant_N() / V > 2.0


def test_concrete_stress_far_below_capacity():
    """Axial + flexural stresses are tiny vs f'c and the modulus of rupture."""
    I = pier.pier_second_moment_m4()
    A = pier.pier_area_m2()
    M = pier.seismic_overturning_Nm(P.MN78)
    sigma_bend = M * (P.PIER.diameter_m / 2.0) / I
    sigma_axial = u.weight_N(pier.tip_mass_kg(P.MN78)) / A
    # No net tension cracking: bending tension stays under modulus of rupture.
    assert (sigma_bend - sigma_axial) < pier.modulus_of_rupture_Pa()
    # Compression nowhere near f'c.
    assert (sigma_bend + sigma_axial) < 0.05 * P.PIER.fc_Pa


def test_frost_embedment_adequate():
    """0.914 m embedment exceeds the assumed central-NV frost line."""
    assert P.PIER.embed_depth_m > pier.FROST_DEPTH_TYPICAL_M


def test_evaluate_passes_with_seismic_governing():
    r = pier.evaluate("MN78")
    assert r.verdict is Verdict.PASS
    assert r.safety_factor is not None and r.safety_factor > 2.0
    # The governing (minimum) SF should be a seismic term, not tilt/frequency
    # (those are enormous), so the governing SF is well under the frequency SF.
    m_tip = pier.tip_mass_kg(P.MN78)
    sf_freq = pier.pier_first_mode_hz(m_tip) / P.NATURAL_FREQ_TARGET_HZ
    assert r.safety_factor < sf_freq
    assert any("Governing safety factor" in ln.label for ln in r.lines)
    # Honesty: assumptions disclose the ASSUMED seismic S_DS and soil.
    assert any("S_DS" in a for a in r.assumptions)
