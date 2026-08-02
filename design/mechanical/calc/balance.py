"""
Mass-balance proof — can the mount be balanced, and can the counterweights be
deleted entirely?

Two questions, one module:

Counterweighted (classical GEM)
    Solve the RA moment balance ``m_cw * r_cw = m_payload * r_payload`` for the
    shaft position of the available 12.5 kg of weights, and check it lands inside
    the 18" (0.457 m) counterweight shaft. DEC fore-aft balance is qualitative:
    it is set by sliding the OTA in its dovetail saddle, needs no counterweight,
    and leaves only a small residual lever (``torque.DEC_RESIDUAL_LEVER_M``).

Counterweight-FREE (the recommended configuration)
    A strain-wave drive back-drives so poorly that the torque proof
    (``torque.evaluate(..., counterweight_free=True)``) already shows the RA
    harmonic holds the *unbalanced* payload with margin. This module quantifies
    what deleting the counterweight buys: the removed mass (weights + the 303-SS
    shaft's own ``rho*A*L``) and the reduced RA polar-axis inertia.

Headline decision: the mount balances comfortably within the existing shaft, AND
the counterweight-free option is viable (per the torque proof) — deleting ~15 kg
of steel and ~29% of the RA slewing inertia.
"""

from __future__ import annotations

import math

from . import params as P
from . import torque
from . import units as u
from .budget import BudgetResult, Verdict


def _payload_mass(ota: P.OTA) -> float:
    """OTA + lumped rear imaging train (single source: params)."""
    return ota.mass_kg + P.IMAGING_TRAIN.mass_kg


def shaft_mass_kg(cw: P.CounterweightSystem = P.COUNTERWEIGHTS) -> float:
    """Mass of the solid 303-SS counterweight shaft = rho * A * L. DERIVED."""
    area = math.pi / 4.0 * cw.shaft_dia_m ** 2
    return cw.material.rho * area * cw.shaft_len_m


def deleted_mass_kg(cw: P.CounterweightSystem = P.COUNTERWEIGHTS) -> float:
    """Mass removed by going counterweight-FREE: the weights + the shaft itself."""
    return cw.weights_available_kg + shaft_mass_kg(cw)


def required_counterweight_position_m(
    ota: P.OTA = P.MN78,
    m_cw: float | None = None,
    r_payload: float | None = None,
) -> float:
    """
    Solve ``m_cw * r_cw = m_payload * r_payload`` for the shaft position r_cw.

    Treats the weights as a point mass (ignores the shaft's own distributed
    restoring moment) — CONSERVATIVE: crediting the shaft moment would only pull
    r_cw inward, so the point-mass answer is the furthest-out (worst) case.
    """
    if m_cw is None:
        m_cw = P.COUNTERWEIGHTS.weights_available_kg
    if r_payload is None:
        r_payload = torque.RA_CG_OFFSET_M
    return _payload_mass(ota) * r_payload / m_cw


def _ra_payload_inertia_kgm2(ota: P.OTA) -> float:
    """RA polar-axis inertia of the payload alone (same model as torque.py)."""
    return _payload_mass(ota) * torque.RA_CG_OFFSET_M ** 2 + \
        (1.0 / 12.0) * ota.mass_kg * ota.tube_length_m ** 2


def deleted_ra_inertia_kgm2(
    ota: P.OTA = P.MN78, cw: P.CounterweightSystem = P.COUNTERWEIGHTS
) -> float:
    """
    RA polar-axis inertia removed with the counterweight system: the weights as
    a point mass at r_cw, plus the shaft as a uniform rod about the axis end
    (I = 1/3 m L^2). DERIVED.
    """
    r_cw = required_counterweight_position_m(ota, cw.weights_available_kg)
    i_weights = cw.weights_available_kg * r_cw ** 2
    i_shaft = (1.0 / 3.0) * shaft_mass_kg(cw) * cw.shaft_len_m ** 2
    return i_weights + i_shaft


def evaluate(ota_key: str = "MN78") -> BudgetResult:
    ota = P.OTA_CASES[ota_key]
    cw = P.COUNTERWEIGHTS

    # --- Counterweighted RA moment balance ---
    m_pay = _payload_mass(ota)
    r_pay = torque.RA_CG_OFFSET_M
    payload_moment = m_pay * r_pay                     # kg*m
    r_cw = required_counterweight_position_m(ota)      # m
    shaft_len = cw.shaft_len_m
    fits = r_cw <= shaft_len
    fit_factor = shaft_len / r_cw                      # >1 => inside the shaft

    # --- DEC fore-aft (qualitative) ---
    # Rear imaging stack hangs behind the DEC axis; balanced by sliding the OTA
    # in the saddle. Residual lever after adjustment = torque.DEC_RESIDUAL_LEVER_M.
    dec_rear_moment_Nm = u.weight_N(P.IMAGING_TRAIN.mass_kg) * P.IMAGING_TRAIN.offset_behind_tube_m
    dec_residual_moment_Nm = u.weight_N(m_pay) * torque.DEC_RESIDUAL_LEVER_M

    # --- Counterweight-FREE deletion ---
    del_mass = deleted_mass_kg(cw)
    del_I = deleted_ra_inertia_kgm2(ota, cw)
    i_pay = _ra_payload_inertia_kgm2(ota)
    inertia_reduction_frac = del_I / (i_pay + del_I)

    # Counterweight-free viability is decided by the torque proof, not re-derived.
    tq = torque.evaluate(ota_key, counterweight_free=True)
    cwfree_ok = tq.verdict in (Verdict.PASS, Verdict.MARGINAL)

    if fits and cwfree_ok:
        verdict = Verdict.PASS
    elif fits:
        verdict = Verdict.MARGINAL   # balances, but torque proof did not clear cw-free
    else:
        verdict = Verdict.FAIL       # cannot balance within the shaft

    res = BudgetResult(
        key="balance",
        title="Mass-balance proof (counterweighted & counterweight-free)",
        verdict=verdict,
        headline=(
            f"{ota.name}: {cw.weights_available_kg:.1f} kg balances the {m_pay:.0f} kg payload at "
            f"r_cw={r_cw*1000:.0f} mm on the {shaft_len*1000:.0f} mm shaft (fit factor {fit_factor:.2f}). "
            f"Counterweight-FREE deletes {del_mass:.1f} kg and {inertia_reduction_frac*100:.0f}% of RA "
            f"inertia — viable per the torque proof (RA SF {tq.safety_factor:.1f})."
        ),
        target="RA balance achievable within shaft length AND counterweight-free viable (torque proof)",
        safety_factor=fit_factor,
    )

    # --- Counterweighted balance ---
    res.add("Payload mass (OTA + train)", m_pay, "kg")
    res.add("Payload CG offset from polar axis (r_payload)", r_pay, "m", "torque.RA_CG_OFFSET_M")
    res.add("Payload moment about RA axis", payload_moment, "kg*m", "m_payload * r_payload")
    res.add("Counterweights available", cw.weights_available_kg, "kg", "2x5 + 1x2.5 kg")
    res.add("Required shaft position r_cw", r_cw, "m", "m_cw * r_cw = m_pay * r_pay")
    res.add("Shaft length available", shaft_len, "m", '18" 303-SS shaft')
    res.add("Fit factor (shaft_len / r_cw)", fit_factor, "x", ">1 => fits")

    # --- DEC fore-aft (qualitative) ---
    res.add("DEC rear-stack imbalance moment", dec_rear_moment_Nm, "Nm",
            "train weight x 150 mm; nulled by dovetail slide")
    res.add("DEC residual moment after adjust", dec_residual_moment_Nm, "Nm",
            "residual lever 20 mm (torque.DEC_RESIDUAL_LEVER_M)")

    # --- Counterweight-FREE deletion ---
    res.add("Counterweight shaft mass (rho*A*L)", shaft_mass_kg(cw), "kg", "303-SS solid rod")
    res.add("Total deleted mass (cw-free)", del_mass, "kg", "weights + shaft")
    res.add("RA payload inertia (polar axis)", i_pay, "kg*m^2")
    res.add("Deleted RA inertia (weights+shaft)", del_I, "kg*m^2")
    res.add("RA inertia reduction (cw-free)", inertia_reduction_frac * 100.0, "%")
    res.add("Counterweight-free viable (torque)", 1.0 if cwfree_ok else 0.0, "bool",
            f"torque verdict {tq.verdict.value}")

    res.assumptions = [
        f"r_payload = RA CG offset {r_pay*1000:.0f} mm (imported from torque.RA_CG_OFFSET_M, DERIVED).",
        "Counterweights modelled as a point mass; the shaft's own distributed moment is NOT "
        "credited toward balance -> conservative (pushes r_cw outward, not inward).",
        f"Counterweight shaft mass = rho*A*L of 303-SS "
        f"(rho={cw.material.rho:.0f} kg/m^3, d={cw.shaft_dia_m*1000:.1f} mm, L={cw.shaft_len_m*1000:.0f} mm) "
        f"= {shaft_mass_kg(cw):.2f} kg, DERIVED.",
        "DEC fore-aft balance is set by sliding the OTA in its dovetail saddle (no DEC counterweight); "
        f"residual lever {torque.DEC_RESIDUAL_LEVER_M*1000:.0f} mm from torque.DEC_RESIDUAL_LEVER_M, ASSUMED.",
        "Deleted RA inertia = weights as point mass at r_cw + shaft as a rod about the axis end "
        "(I = 1/3 m L^2), DERIVED.",
        f"Counterweight-free viability is inherited from the torque proof "
        f"(torque.evaluate('{ota_key}', counterweight_free=True) => {tq.verdict.value}), not re-derived here.",
    ]
    return res


if __name__ == "__main__":
    r = evaluate()
    print(r.verdict.symbol, r.headline)
    print(r.markdown_table())
