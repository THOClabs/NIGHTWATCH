"""First-mode dynamics proof: the structural first natural frequency must sit
well above the 10 Hz target and clear of the <2 Hz wind-gust and 1-5 Hz servo
bands. Unlike the static-deflection proof (which FAILS), the light payload keeps
sqrt(k/m) high, so dynamics PASSES -- two different physics, two verdicts."""

import math

from design.mechanical.calc import dynamics
from design.mechanical.calc import params as P
from design.mechanical.calc.budget import Verdict


def test_pier_stiffness_is_positive_and_sane():
    """A 12 in x 36 in exposed concrete pier is stiff (tens of MN/m)."""
    k = dynamics.pier_lateral_stiffness()
    assert 1.0e7 < k < 1.0e8


def test_bounce_mode_clears_target():
    """Translational bounce mode is well above 10 Hz (pier-dominated)."""
    f = dynamics.first_mode_hz(P.MN78, P.RA_HOUSING_12MM, P.DEC_HOUSING_12MM,
                               counterweighted=False)
    assert f > P.NATURAL_FREQ_TARGET_HZ


def test_counterweights_lower_the_frequency():
    """Adding counterweight mass raises m_eff and lowers f_n."""
    f_free = dynamics.first_mode_hz(P.MN78, P.RA_HOUSING_12MM, P.DEC_HOUSING_12MM,
                                    counterweighted=False)
    f_cw = dynamics.first_mode_hz(P.MN78, P.RA_HOUSING_12MM, P.DEC_HOUSING_12MM,
                                  counterweighted=True)
    assert f_cw < f_free
    # sqrt(m) scaling: 18 -> 30.5 kg should drop f by a factor ~sqrt(30.5/18).
    assert math.isclose(f_free / f_cw, math.sqrt(30.5 / 18.0), rel_tol=0.02)


def test_rocking_mode_is_the_governing_lower_mode():
    """The overhung rocking mode (short bearing spans) is lower than the bounce
    mode and is therefore the physically governing first mode -- yet still >10 Hz."""
    f_rock = dynamics.rocking_mode_hz(P.MN78, P.RA_HOUSING_12MM, P.DEC_HOUSING_12MM)
    f_bounce = dynamics.first_mode_hz(P.MN78, P.RA_HOUSING_12MM, P.DEC_HOUSING_12MM,
                                      counterweighted=False)
    assert f_rock < f_bounce
    assert f_rock > P.NATURAL_FREQ_TARGET_HZ


def test_governing_mode_is_the_minimum():
    g = dynamics.governing_first_mode_hz(P.MN78, P.RA_HOUSING_12MM, P.DEC_HOUSING_12MM,
                                         counterweighted=True)
    f_rock = dynamics.rocking_mode_hz(P.MN78, P.RA_HOUSING_12MM, P.DEC_HOUSING_12MM)
    f_cw = dynamics.first_mode_hz(P.MN78, P.RA_HOUSING_12MM, P.DEC_HOUSING_12MM,
                                  counterweighted=True)
    assert math.isclose(g, min(f_rock, f_cw), rel_tol=1e-12)


def test_first_mode_clears_wind_and_servo_bands():
    """The governing mode must be well above the 2 Hz wind and 5 Hz servo bands."""
    g = dynamics.governing_first_mode_hz(P.MN78, P.RA_HOUSING_12MM, P.DEC_HOUSING_12MM,
                                         counterweighted=True)
    assert g > 5.0 * 5.0   # comfortably above the ~5 Hz servo/guide bandwidth


def test_evaluate_passes_above_target():
    r = dynamics.evaluate("MN78")
    assert r.verdict is Verdict.PASS
    assert r.safety_factor is not None and r.safety_factor > 1.5
    # Governing mode line must exist and exceed the target.
    gov = [ln for ln in r.lines if ln.label == "Governing first mode"]
    assert gov and gov[0].value > P.NATURAL_FREQ_TARGET_HZ
