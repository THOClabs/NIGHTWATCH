"""Torque-budget proof: the drives must carry the payload with margin, and the
counterweight-free configuration must be shown feasible (or not)."""

from design.mechanical.calc import params as P
from design.mechanical.calc import torque
from design.mechanical.calc.budget import Verdict


def test_counterweight_free_ra_holding_has_margin():
    """The bold claim: harmonic holding torque covers the unbalanced payload."""
    ra = torque.ra_required_torque(P.MN78, counterweight_free=True)
    sf = P.RA_DRIVE.rated_torque_Nm / ra["total"]
    # Must clear the payload imbalance with a real continuous margin.
    assert sf >= 2.0, f"counterweight-free RA SF too low: {sf:.2f}"
    # Gravity imbalance should dominate the budget (it's the whole point).
    assert ra["gravity"] > ra["wind"]
    assert ra["gravity"] > ra["inertia"]


def test_dec_drive_covers_payload():
    dec = torque.dec_required_torque(P.MN78)
    assert P.DEC_DRIVE.rated_torque_Nm / dec["total"] >= 2.0


def test_peak_torque_covers_goto_transient():
    ra = torque.ra_required_torque(P.MN78, counterweight_free=True)
    assert P.RA_DRIVE.peak_torque_Nm / ra["total"] >= 3.0


def test_heavier_ota_still_passes_but_lower_sf():
    """MN78 (heavier) must have a lower SF than MN76 — sanity on the model."""
    light = torque.ra_required_torque(P.MN76, counterweight_free=True)["total"]
    heavy = torque.ra_required_torque(P.MN78, counterweight_free=True)["total"]
    assert heavy > light


def test_evaluate_returns_pass():
    r = torque.evaluate("MN78", counterweight_free=True)
    assert r.verdict in (Verdict.PASS, Verdict.MARGINAL)
    assert r.safety_factor is not None and r.safety_factor > 1.5
    assert any("RA total required" in ln.label for ln in r.lines)
