"""Tracking-error budget proof: the as-specified encoder chain must be shown to
MISS < 1 arcsec RMS, and the on-axis absolute ring to reach it. FAIL for the
baseline is the correct, intended result."""

import math

from design.mechanical.calc import encoder
from design.mechanical.calc import params as P
from design.mechanical.calc.budget import Verdict


def test_quantization_rms_is_lsb_over_sqrt12():
    for enc in (P.ENC_MOTOR_AMT103, P.ENC_AXIS_AS5600, P.ENC_AXIS_RESA):
        assert math.isclose(
            encoder.quant_rms_arcsec(enc),
            enc.resolution_arcsec / math.sqrt(12.0),
            rel_tol=1e-12,
        )


def test_as5600_on_axis_quantization_is_about_316_arcsec():
    """The cheap 12-bit on-axis chip resolves only ~316" — a coarse homing
    reference, ~91" quant RMS, useless for sub-arcsec tracking."""
    res = P.ENC_AXIS_AS5600.resolution_arcsec
    assert 300.0 < res < 330.0, f"AS5600 resolution {res:.1f}\" not ~316\""
    assert math.isclose(res, 316.4, abs_tol=1.0)
    # Its quantisation RMS alone dwarfs the whole 1 arcsec budget.
    assert encoder.quant_rms_arcsec(P.ENC_AXIS_AS5600) > 50.0


def test_motor_and_resa_resolutions_bracket_the_problem():
    assert math.isclose(P.ENC_MOTOR_AMT103.resolution_arcsec, 1.58, abs_tol=0.05)
    assert P.ENC_AXIS_RESA.resolution_arcsec < 0.1  # genuinely sub-arcsec


def test_baseline_exceeds_one_arcsec_and_fails():
    base = encoder.tracking_rms_arcsec("baseline")
    assert base > 1.0, f"baseline should miss the target, got {base:.2f}\""
    # Sanity on the dominant terms: harmonic PE + flexure, not quantisation.
    c = encoder.tracking_components("baseline")
    assert c["pe_residual"] > c["quant"]
    assert c["flexure"] > c["quant"]
    # Ballpark the RSS so the model can't silently drift.
    assert 4.0 < base < 6.0


def test_proposed_meets_sub_arcsecond():
    prop = encoder.tracking_rms_arcsec("proposed")
    assert prop < 1.0, f"proposed on-axis ring should meet target, got {prop:.2f}\""
    # RESA quantisation must be negligible vs the servo/flexure floor.
    c = encoder.tracking_components("proposed")
    assert c["quant"] < 0.01
    assert prop < 0.9  # real margin below 1 arcsec


def test_proposed_beats_baseline_by_a_wide_margin():
    assert encoder.tracking_rms_arcsec("baseline") > \
        5.0 * encoder.tracking_rms_arcsec("proposed")


def test_evaluate_baseline_verdict_is_fail():
    r = encoder.evaluate("baseline")
    assert r.verdict is Verdict.FAIL
    assert r.safety_factor is not None and r.safety_factor < 1.0


def test_evaluate_proposed_verdict_passes():
    r = encoder.evaluate("proposed")
    assert r.verdict is Verdict.PASS
    assert r.safety_factor is not None and r.safety_factor > 1.0


def test_evaluate_compare_reports_both_and_flags_the_requirement():
    r = encoder.evaluate()  # default: compare
    # As-specified design fails, so the module's verdict is FAIL.
    assert r.verdict is Verdict.FAIL
    # Headline names both numbers and the bold conclusion.
    assert "REQUIRED" in r.headline
    assert "FAIL" in r.headline.upper()
    # Both totals are present as lines.
    labels = [ln.label for ln in r.lines]
    assert any("Baseline total tracking RMS" in x for x in labels)
    assert any("Proposed total tracking RMS" in x for x in labels)
    # Assumptions are stated (PE residual + flexure at minimum).
    joined = " ".join(r.assumptions).lower()
    assert "pe" in joined or "periodic" in joined or "repeatability" in joined
    assert "flexure" in joined


def test_target_comes_from_params_not_hardcoded():
    assert P.TRACKING_RMS_TARGET_ARCSEC == 1.0
    r = encoder.evaluate()
    assert str(P.TRACKING_RMS_TARGET_ARCSEC) in r.target or "1.0" in r.target
