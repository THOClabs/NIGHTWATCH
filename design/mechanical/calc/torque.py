"""
Axis torque budget — does each harmonic drive have the holding + dynamic torque
to carry the payload, and can the ~9 kg of counterweights be deleted?

Worst-case axis torque = gravity imbalance + wind + goto inertia + drive/bearing
friction, compared against the CSF drives' rated (continuous) and peak torques.

Headline decision: a strain-wave drive resists back-drive, so a *counterweight-
free* GEM only needs holding torque >= payload_weight x CG-offset. We compute
that and show the safety factor vs the 127 Nm (RA) / 70 Nm (DEC) ratings — the
same principle the ZWO AM5 / RST-135 exploit to run without counterweights.
"""

from __future__ import annotations

import math

from . import params as P
from . import units as u
from .budget import BudgetResult, Verdict, verdict_from_sf

# Modelled geometry (DERIVED estimates; the pier/stiffness modules refine these).
RA_CG_OFFSET_M = 0.20          # horizontal CG offset of payload from the polar axis
DEC_RESIDUAL_LEVER_M = 0.02    # along-tube imbalance left after balancing
DEC_WIND_LEVER_FRAC = 0.34     # center-of-pressure lever about DEC as frac of tube length
BALANCE_ERROR_FRAC = 0.02      # residual imbalance when counterweighted & balanced
FRICTION_FRACTION = 0.05       # harmonic + bearing seal drag, frac of rated torque


def _drag_force(V_ms: float, ota: P.OTA, env: P.Environment, site: P.Site) -> float:
    """Broadside wind drag on the tube (N). wind.py owns the structural version."""
    area = ota.tube_od_m * ota.tube_length_m
    return 0.5 * site.air_density * V_ms ** 2 * env.cd_cylinder * area


def _payload_mass(ota: P.OTA) -> float:
    return ota.mass_kg + P.IMAGING_TRAIN.mass_kg


def ra_required_torque(ota: P.OTA, counterweight_free: bool) -> dict[str, float]:
    W = u.weight_N(_payload_mass(ota))
    if counterweight_free:
        t_gravity = W * RA_CG_OFFSET_M
    else:
        t_gravity = W * RA_CG_OFFSET_M * BALANCE_ERROR_FRAC
    f_wind = _drag_force(P.ENV.wind_gust_close_ms, ota, P.ENV, P.SITE)
    t_wind = f_wind * RA_CG_OFFSET_M
    # Inertia about polar axis (payload ~ point mass at offset + tube self-inertia).
    i_axis = _payload_mass(ota) * RA_CG_OFFSET_M ** 2 + \
        (1.0 / 12.0) * ota.mass_kg * ota.tube_length_m ** 2
    alpha = math.radians(P.MOTOR.accel_dps2)
    t_inertia = i_axis * alpha
    t_friction = FRICTION_FRACTION * P.RA_DRIVE.rated_torque_Nm
    total = t_gravity + t_wind + t_inertia + t_friction
    return {"gravity": t_gravity, "wind": t_wind, "inertia": t_inertia,
            "friction": t_friction, "total": total}


def dec_required_torque(ota: P.OTA) -> dict[str, float]:
    W = u.weight_N(_payload_mass(ota))
    t_gravity = W * DEC_RESIDUAL_LEVER_M
    f_wind = _drag_force(P.ENV.wind_gust_close_ms, ota, P.ENV, P.SITE)
    t_wind = f_wind * DEC_WIND_LEVER_FRAC * ota.tube_length_m
    i_axis = (1.0 / 12.0) * ota.mass_kg * ota.tube_length_m ** 2 + \
        P.IMAGING_TRAIN.mass_kg * (0.5 * ota.tube_length_m) ** 2
    alpha = math.radians(P.MOTOR.accel_dps2)
    t_inertia = i_axis * alpha
    t_friction = FRICTION_FRACTION * P.DEC_DRIVE.rated_torque_Nm
    total = t_gravity + t_wind + t_inertia + t_friction
    return {"gravity": t_gravity, "wind": t_wind, "inertia": t_inertia,
            "friction": t_friction, "total": total}


def evaluate(ota_key: str = "MN78", counterweight_free: bool = True) -> BudgetResult:
    ota = P.OTA_CASES[ota_key]
    ra = ra_required_torque(ota, counterweight_free)
    dec = dec_required_torque(ota)

    ra_sf_rated = P.RA_DRIVE.rated_torque_Nm / ra["total"]
    ra_sf_peak = P.RA_DRIVE.peak_torque_Nm / ra["total"]
    dec_sf_rated = P.DEC_DRIVE.rated_torque_Nm / dec["total"]
    dec_sf_peak = P.DEC_DRIVE.peak_torque_Nm / dec["total"]

    governing_sf = min(ra_sf_rated, dec_sf_rated)
    verdict = verdict_from_sf(governing_sf, pass_at=2.0, marginal_at=1.5)

    mode = "counterweight-FREE" if counterweight_free else "counterweighted"
    res = BudgetResult(
        key="torque",
        title="Axis torque budget",
        verdict=verdict,
        headline=(
            f"{ota.name}, {mode}: RA needs {ra['total']:.1f} Nm vs 127 Nm rated "
            f"(SF {ra_sf_rated:.1f}); DEC needs {dec['total']:.1f} Nm vs 70 Nm rated "
            f"(SF {dec_sf_rated:.1f})."
        ),
        target="Required axis torque < rated (SF>=2 continuous, peak covers goto)",
        safety_factor=governing_sf,
    )
    res.add("Payload mass (OTA + train)", _payload_mass(ota), "kg")
    res.add("RA gravity imbalance torque", ra["gravity"], "Nm", "payload weight x CG offset")
    res.add("RA wind torque @ 35 mph gust", ra["wind"], "Nm")
    res.add("RA goto-inertia torque", ra["inertia"], "Nm")
    res.add("RA friction torque", ra["friction"], "Nm")
    res.add("RA total required", ra["total"], "Nm")
    res.add("RA rated / required (SF)", ra_sf_rated, "x")
    res.add("RA peak / required (SF)", ra_sf_peak, "x")
    res.add("DEC total required", dec["total"], "Nm")
    res.add("DEC rated / required (SF)", dec_sf_rated, "x")
    res.add("DEC peak / required (SF)", dec_sf_peak, "x")
    res.assumptions = [
        f"RA CG offset from polar axis = {RA_CG_OFFSET_M*1000:.0f} mm (GEM geometry estimate, DERIVED)",
        f"Balance residual (counterweighted) = {BALANCE_ERROR_FRAC*100:.0f}% (ASSUMED)",
        f"Drive+bearing friction = {FRICTION_FRACTION*100:.0f}% of rated torque (ASSUMED)",
        "Wind torque uses the 35 mph emergency-close gust (max wind while open), SOURCED.",
        f"Air density {P.SITE.air_density:.3f} kg/m^3 at 1800 m (DERIVED), 17% below sea level.",
    ]
    return res


if __name__ == "__main__":
    r = evaluate()
    print(r.verdict.symbol, r.headline)
    print(r.markdown_table())
