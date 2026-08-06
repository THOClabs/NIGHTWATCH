"""
Bearing proof — L10 rolling-fatigue life and static safety of the axis output
bearings, and the finding that matters more than either number.

Load model (per axis)
    The output bearing pair carries the cantilevered payload. Each pair sees a
    direct transverse (radial) load ~ payload weight, plus a couple that reacts
    the overturning moment M = W * lever across the bearing span s: F = M / s.
    The governing bearing load is taken as ``P = W + M/s`` (conservative: the
    direct component is not credited with load-sharing between the two rows).

L10 fatigue
    ``L10 = (C / P)**3 * 1e6`` revolutions, C = dynamic rating. The RA axis turns
    only ~1 rev per sidereal day; converting L10 to YEARS shows the fatigue life
    is astronomical (~1e7-1e8 yr). Rolling fatigue is NOT the constraint on this
    mount and never will be.

Static safety
    ``S0 = C0 / P`` (C0 = static rating). Comfortable (~14-18x) at these loads.

THE FINDING (headline + assumptions): the Build Package calls the 6008/6006 units
"angular contact", but 60xx are DEEP-GROOVE ball bearings. Deep-groove bearings
have poor MOMENT (tilting) stiffness — and moment stiffness, not load rating, is
what sets a telescope mount's pointing deflection. The recommendation is to use
matched ANGULAR-CONTACT pairs (7008 on RA, 7006 on DEC) in a back-to-back (O)
arrangement, which ties directly to the stiffness proof. The load-capacity verdict
here is PASS with room to spare; the real bearing decision is a stiffness decision.
"""

from __future__ import annotations

from . import params as P
from . import torque
from . import units as u
from .budget import BudgetResult, verdict_from_sf

# Sidereal tracking rate: the RA axis completes ~1 revolution per sidereal day.
# Used for the L10 revolutions -> years conversion. DEC turns far less, so 1/day
# is a conservative (over-cycled) common figure for both. SOURCED (sidereal rate).
TRACK_REV_PER_DAY = 1.0
DAYS_PER_YEAR = 365.25

# Transverse offset from the DEC axis to the OTA CG (tube centreline sits above
# the DEC bearing face). Modelled as tube radius + a dovetail/ring saddle stack.
# The saddle stack is ASSUMED; the tube radius is SOURCED (params tube_od_m).
DEC_SADDLE_STACK_M = 0.05  # ASSUMED: dovetail saddle + ring height, DEC face -> tube surface

# Static-safety pass threshold. ISO 76 wants S0 ~1-2 for smooth rotation, higher
# for shock; 2.0 is a conservative pass gate here. ASSUMED design gate.
STATIC_SAFETY_PASS = 2.0


def _payload_mass(ota: P.OTA) -> float:
    return ota.mass_kg + P.IMAGING_TRAIN.mass_kg


def bearing_radial_load(weight_N: float, lever_m: float, span_m: float) -> float:
    """
    Governing output-bearing radial load: direct transverse weight plus the
    moment-couple reaction M/span. Conservative (no load-sharing credit on W).
    """
    moment = weight_N * lever_m
    couple = moment / span_m
    return weight_N + couple


def ra_output_load(ota: P.OTA) -> float:
    """RA output-bearing load: payload weight cantilevered at the RA CG offset."""
    W = u.weight_N(_payload_mass(ota))
    return bearing_radial_load(W, torque.RA_CG_OFFSET_M, P.RA_HOUSING.depth_m)


def dec_output_load(ota: P.OTA) -> float:
    """DEC output-bearing load: OTA weight offset from the DEC axis (tube CG above axis)."""
    W = u.weight_N(_payload_mass(ota))
    lever = ota.tube_od_m / 2.0 + DEC_SADDLE_STACK_M
    return bearing_radial_load(W, lever, P.DEC_HOUSING.depth_m)


def l10_revolutions(bearing: P.Bearing, load_N: float) -> float:
    """Basic rating life L10 = (C/P)^3 * 1e6 revolutions (ball bearings)."""
    return (bearing.C_dynamic_N / load_N) ** 3 * 1.0e6


def l10_years(bearing: P.Bearing, load_N: float, rev_per_day: float = TRACK_REV_PER_DAY) -> float:
    """L10 expressed in YEARS at a given revolutions-per-day duty."""
    return l10_revolutions(bearing, load_N) / (rev_per_day * DAYS_PER_YEAR)


def static_safety(bearing: P.Bearing, load_N: float) -> float:
    """Static safety factor S0 = C0 / P (ISO 76)."""
    return bearing.C0_static_N / load_N


def evaluate(ota_key: str = "MN78") -> BudgetResult:
    ota = P.OTA_CASES[ota_key]

    ra_load = ra_output_load(ota)
    dec_load = dec_output_load(ota)

    ra_L10_yr = l10_years(P.BRG_RA_6008, ra_load)
    dec_L10_yr = l10_years(P.BRG_DEC_6006, dec_load)

    ra_S0 = static_safety(P.BRG_RA_6008, ra_load)
    dec_S0 = static_safety(P.BRG_DEC_6006, dec_load)

    ra_moment = u.weight_N(_payload_mass(ota)) * torque.RA_CG_OFFSET_M
    dec_moment = u.weight_N(_payload_mass(ota)) * (ota.tube_od_m / 2.0 + DEC_SADDLE_STACK_M)

    governing_S0 = min(ra_S0, dec_S0)
    # Load-capacity verdict (fatigue + static). Fatigue is a non-issue by ~1e7
    # years, so static safety governs. The moment-stiffness caveat below is the
    # real design driver and is flagged loudly, but it belongs to stiffness.py.
    verdict = verdict_from_sf(governing_S0, pass_at=STATIC_SAFETY_PASS, marginal_at=1.0)

    res = BudgetResult(
        key="bearings",
        title="Axis bearing L10 fatigue + static safety",
        verdict=verdict,
        headline=(
            f"Load capacity is NOT the constraint: L10 ~ {ra_L10_yr:.0e} yr (RA) / {dec_L10_yr:.0e} yr "
            f"(DEC) at ~1 rev/sidereal-day, static S0 {ra_S0:.0f}x / {dec_S0:.0f}x. FINDING: the repo "
            f"calls the 6008/6006 'angular contact' but 60xx are DEEP-GROOVE with poor moment stiffness "
            f"— use matched angular-contact 7008/7006 pairs (back-to-back) for moment stiffness (see stiffness proof)."
        ),
        target=f"L10 >> service life AND static S0 >= {STATIC_SAFETY_PASS:.0f} (fatigue not the constraint)",
        safety_factor=governing_S0,
    )

    res.add("Payload mass (OTA + train)", _payload_mass(ota), "kg")
    # RA
    res.add("RA overturning moment (W x CG offset)", ra_moment, "Nm", "lever = RA_CG_OFFSET_M")
    res.add("RA bearing span (housing depth)", P.RA_HOUSING.depth_m, "m", "sets couple arm")
    res.add("RA output bearing load P", ra_load, "N", "W + M/span (6008)")
    res.add("RA dynamic rating C", P.BRG_RA_6008.C_dynamic_N, "N")
    res.add("RA L10 life", l10_revolutions(P.BRG_RA_6008, ra_load), "rev", "(C/P)^3 x 1e6")
    res.add("RA L10 life", ra_L10_yr, "yr", "@ ~1 rev/sidereal day")
    res.add("RA static safety S0 = C0/P", ra_S0, "x", f"C0={P.BRG_RA_6008.C0_static_N:.0f} N")
    # DEC
    res.add("DEC overturning moment (W x lever)", dec_moment, "Nm", "lever = tube r + saddle stack")
    res.add("DEC bearing span (housing depth)", P.DEC_HOUSING.depth_m, "m")
    res.add("DEC output bearing load P", dec_load, "N", "W + M/span (6006)")
    res.add("DEC dynamic rating C", P.BRG_DEC_6006.C_dynamic_N, "N")
    res.add("DEC L10 life", dec_L10_yr, "yr", "@ ~1 rev/sidereal day")
    res.add("DEC static safety S0 = C0/P", dec_S0, "x", f"C0={P.BRG_DEC_6006.C0_static_N:.0f} N")

    res.assumptions = [
        "Governing bearing load P = W + M/span (direct transverse weight + moment couple); "
        "no load-sharing credit on the direct term -> conservative.",
        f"RA lever = RA_CG_OFFSET_M {torque.RA_CG_OFFSET_M*1000:.0f} mm (from torque, DERIVED); "
        f"DEC lever = tube radius {ota.tube_od_m/2*1000:.0f} mm + saddle stack {DEC_SADDLE_STACK_M*1000:.0f} mm "
        f"(saddle stack ASSUMED).",
        "Bearing span = housing depth (P.RA_HOUSING.depth_m / P.DEC_HOUSING.depth_m); axis tilt at "
        "latitude would reduce the transverse component, so vertical W is conservative.",
        f"L10 = (C/P)^3 x 1e6 rev; converted to years at {TRACK_REV_PER_DAY:.0f} rev/sidereal day "
        f"(~1/day). Both axes exceed 1e7 years -> rolling fatigue is NOT a lifetime constraint.",
        "FINDING: params labels BRG_RA_6008 / BRG_DEC_6006 'angular contact', but 60xx are DEEP-GROOVE "
        "ball bearings (params.py already flags the deep-groove C ratings). Deep-groove bearings have "
        "poor moment/tilting stiffness.",
        "RECOMMENDATION: replace with matched ANGULAR-CONTACT pairs — 7008 (RA) / 7006 (DEC) — in a "
        "back-to-back (O) arrangement with preload, which provides the moment stiffness that sets "
        "pointing deflection. This is a STIFFNESS decision, not a load-rating one (see stiffness proof).",
        "The RA output bearing additionally carries DEC-head and (if fitted) counterweight dead weight "
        "not modelled here; even at 2-3x the modelled load, S0 stays > 5 and L10 > 1e6 yr, so the "
        "conclusion is robust.",
    ]
    return res


if __name__ == "__main__":
    r = evaluate()
    print(r.verdict.symbol, r.headline)
    print(r.markdown_table())
