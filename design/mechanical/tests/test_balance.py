"""Mass-balance proof: the mount must balance the payload with the available
12.5 kg inside the 18" shaft, AND the counterweight-free option must be shown
viable (inherited from the torque proof), deleting real steel and RA inertia."""

import math

from design.mechanical.calc import balance, torque
from design.mechanical.calc import params as P
from design.mechanical.calc.budget import Verdict


def test_required_position_solves_the_moment_equation():
    """r_cw must satisfy m_cw * r_cw = m_payload * r_payload exactly."""
    r_cw = balance.required_counterweight_position_m(P.MN78)
    m_pay = P.MN78.mass_kg + P.IMAGING_TRAIN.mass_kg
    lhs = P.COUNTERWEIGHTS.weights_available_kg * r_cw
    rhs = m_pay * torque.RA_CG_OFFSET_M
    assert math.isclose(lhs, rhs, rel_tol=1e-12)


def test_counterweight_fits_within_the_shaft():
    """The 12.5 kg must balance the MN78 within the 18" (0.457 m) shaft."""
    r_cw = balance.required_counterweight_position_m(P.MN78)
    assert r_cw <= P.COUNTERWEIGHTS.shaft_len_m
    # Real seating margin, not right at the tip.
    assert P.COUNTERWEIGHTS.shaft_len_m / r_cw >= 1.3


def test_heavier_ota_needs_more_shaft():
    """MN78 (heavier) must need a longer r_cw than MN76 — model sanity."""
    r_light = balance.required_counterweight_position_m(P.MN76)
    r_heavy = balance.required_counterweight_position_m(P.MN78)
    assert r_heavy > r_light


def test_deleted_mass_is_weights_plus_shaft():
    """Counterweight-free deletes both the weights and the 303-SS shaft."""
    shaft = balance.shaft_mass_kg()
    deleted = balance.deleted_mass_kg()
    assert math.isclose(deleted, P.COUNTERWEIGHTS.weights_available_kg + shaft, rel_tol=1e-12)
    # Shaft is real, non-trivial steel (rho*A*L ~ 2.9 kg).
    assert 2.0 < shaft < 4.0
    # So total deleted noticeably exceeds the weights alone.
    assert deleted > P.COUNTERWEIGHTS.weights_available_kg + 2.0


def test_counterweight_free_cuts_ra_inertia_meaningfully():
    """Removing the counterweight drops a meaningful fraction of RA inertia."""
    del_I = balance.deleted_ra_inertia_kgm2(P.MN78)
    i_pay = balance._ra_payload_inertia_kgm2(P.MN78)
    assert del_I > 0.0
    reduction = del_I / (i_pay + del_I)
    # Deleting ~15 kg of steel at ~0.29 m should cut ~20-40% of RA inertia.
    assert 0.20 <= reduction <= 0.40


def test_evaluate_passes_and_ties_to_torque_proof():
    """PASS requires: balances within the shaft AND cw-free viable per torque."""
    r = balance.evaluate("MN78")
    assert r.verdict is Verdict.PASS
    # safety_factor is the shaft fit factor (>1 => fits).
    assert r.safety_factor is not None and r.safety_factor > 1.0
    # The counterweight-free verdict must be inherited, not silently asserted.
    tq = torque.evaluate("MN78", counterweight_free=True)
    assert tq.verdict in (Verdict.PASS, Verdict.MARGINAL)
    assert any("torque" in a.lower() for a in r.assumptions)
    assert any("Required shaft position r_cw" in ln.label for ln in r.lines)


def test_dec_balance_is_qualitative_and_small():
    """DEC needs no counterweight: residual moment after dovetail adjust is small."""
    r = balance.evaluate("MN78")
    residual = next(ln for ln in r.lines if "DEC residual moment" in ln.label)
    # Residual imbalance (18 kg x 20 mm ~ 3.5 Nm) is tiny vs the 70 Nm DEC drive.
    assert residual.value < 0.1 * P.DEC_DRIVE.rated_torque_Nm
