"""
Static pointing-deflection proof — does the mount head hold the optical axis to
within P.DEFLECTION_TARGET_ARCSEC (5 arcsec) under gravity?

Worst case: the OTA is horizontal (pointing at the horizon), so gravity acts
perpendicular to the optical axis and the payload weight hangs off the DEC axis
at its full CG lever. That gravity moment bends the load path, and every micron
of compliance at the tiny bearing spans (63-76 mm) is amplified into arcseconds
of pointing error.

Load path modelled as a series compliance chain (each term adds pointing error):

    payload weight W --(lever L_cg)--> moment M at the DEC axis
        |-- DEC housing box-beam bends            theta = M*L / (E*I)
        |-- DEC bearing pair deflects radially     F = M/span, theta = 2*delta/span
        |-- RA  housing box-beam bends (overhung)  theta = M*L / (E*I)
        |-- RA  bearing pair deflects radially     F = M/span, theta = 2*delta/span

Sum the four angular terms, convert rad -> arcsec, compare to the 5 arcsec
target for BOTH the 8 mm baseline housings and the 12 mm bold-review variants.

Honest expectation: the deep-groove bearings the repo specifies, at the 63-76 mm
spans set by the housing depths, are the governing compliance and the beam-wall
upgrade (8 -> 12 mm) barely moves the number. This is where the repo's asserted
"< 5 arcsec" is finally computed rather than assumed.
"""

from __future__ import annotations

from . import params as P
from . import units as u
from .budget import BudgetResult, Verdict, verdict_from_sf

# --------------------------------------------------------------------------
# Modelled constants the repo does not provide (tagged in .assumptions too).
# --------------------------------------------------------------------------
# Radial stiffness of the output bearings. The repo lists only load ratings
# (C, C0), not stiffness, so these are ASSUMED from typical small deep-groove
# ball-bearing radial stiffness: 6008 ~ 250 N/um, 6006 ~ 180 N/um.
BEARING_RADIAL_STIFFNESS_N_PER_M: dict[str, float] = {
    "6008": 250.0e6,   # 250 N/um  (RA output) -- ASSUMED
    "6006": 180.0e6,   # 180 N/um  (DEC output) -- ASSUMED
}
K_RA_BEARING = BEARING_RADIAL_STIFFNESS_N_PER_M["6008"]
K_DEC_BEARING = BEARING_RADIAL_STIFFNESS_N_PER_M["6006"]

# The DEC rotation axis sits below the tube/CG plane by the dovetail + saddle
# stack. The repo does not dimension the saddle, so this radial offset is
# ASSUMED at 50 mm and added to the along-tube CG lever to form a worst-case
# combined gravity lever L_cg. DERIVED/ASSUMED geometry.
SADDLE_LEVER_M = u.mm(50.0)


# --------------------------------------------------------------------------
# Pure helpers (the tests call these directly).
# --------------------------------------------------------------------------
def box_section_I(housing: P.Housing) -> float:
    """Second moment of area of a rectangular box section (m^4).

    I = (b*h^3 - (b-2t)*(h-2t)^3)/12 for outer b x h and wall t.
    """
    b, h, t = housing.outer_x_m, housing.outer_y_m, housing.wall_m
    return (b * h ** 3 - (b - 2.0 * t) * (h - 2.0 * t) ** 3) / 12.0


def payload_mass(ota: P.OTA) -> float:
    """OTA tube + lumped rear imaging train (kg)."""
    return ota.mass_kg + P.IMAGING_TRAIN.mass_kg


def cg_lever_m(ota: P.OTA) -> float:
    """Worst-case gravity lever from the DEC axis to the payload CG (m).

    Along-tube CG offset (OTA.cg_from_saddle_m) + assumed saddle radial offset.
    """
    return ota.cg_from_saddle_m + SADDLE_LEVER_M


def payload_moment_Nm(ota: P.OTA) -> float:
    """Gravity moment about the DEC axis with the tube horizontal (N.m)."""
    return u.weight_N(payload_mass(ota)) * cg_lever_m(ota)


def beam_angular_deflection_rad(M: float, housing: P.Housing) -> float:
    """Tip rotation of a box cantilever of length = bearing span under end
    moment M: theta = M*L/(E*I) (rad)."""
    E = housing.material.E
    I = box_section_I(housing)
    return M * housing.depth_m / (E * I)


def bearing_angular_deflection_rad(M: float, span: float, k: float) -> float:
    """Angular tilt from a bearing pair reacting moment M as a force couple.

    F = M/span in each bearing, radial deflection delta = F/k, and the housing
    tilts by (delta + delta)/span = 2*delta/span (rad).
    """
    F = M / span
    delta = F / k
    return 2.0 * delta / span


def deflection_breakdown(ota: P.OTA, ra_housing: P.Housing,
                         dec_housing: P.Housing) -> dict[str, float]:
    """Every angular term (rad) plus the arcsec total for one configuration."""
    M = payload_moment_Nm(ota)
    dec_beam = beam_angular_deflection_rad(M, dec_housing)
    ra_beam = beam_angular_deflection_rad(M, ra_housing)
    dec_brg = bearing_angular_deflection_rad(M, dec_housing.depth_m, K_DEC_BEARING)
    ra_brg = bearing_angular_deflection_rad(M, ra_housing.depth_m, K_RA_BEARING)
    total = dec_beam + ra_beam + dec_brg + ra_brg
    return {
        "moment_Nm": M,
        "dec_beam_rad": dec_beam,
        "ra_beam_rad": ra_beam,
        "dec_bearing_rad": dec_brg,
        "ra_bearing_rad": ra_brg,
        "beam_rad": dec_beam + ra_beam,
        "bearing_rad": dec_brg + ra_brg,
        "total_rad": total,
        "total_arcsec": u.rad_to_arcsec(total),
    }


def total_deflection_arcsec(ota: P.OTA, ra_housing: P.Housing,
                            dec_housing: P.Housing) -> float:
    """Summed static pointing deflection (arcsec) for the given configuration."""
    return deflection_breakdown(ota, ra_housing, dec_housing)["total_arcsec"]


# --------------------------------------------------------------------------
# Translational helpers reused by dynamics.py (same beam/bearing model).
# --------------------------------------------------------------------------
def beam_translational_stiffness_N_per_m(housing: P.Housing) -> float:
    """Cantilever tip translational stiffness k = 3*E*I/L^3 (N/m)."""
    E = housing.material.E
    I = box_section_I(housing)
    return 3.0 * E * I / housing.depth_m ** 3


def bearing_pair_stiffness_N_per_m(k_single: float) -> float:
    """Two bearings share a lateral load in parallel -> 2x radial stiffness."""
    return 2.0 * k_single


# --------------------------------------------------------------------------
# Budget
# --------------------------------------------------------------------------
def _sf_and_verdict(total_arcsec: float) -> tuple[float, Verdict]:
    sf = P.DEFLECTION_TARGET_ARCSEC / total_arcsec
    # PASS only with a real 1.5x pointing margin; MARGINAL if merely inside 5".
    return sf, verdict_from_sf(sf, pass_at=1.5, marginal_at=1.0)


def evaluate(ota_key: str = "MN78") -> BudgetResult:
    ota = P.OTA_CASES[ota_key]
    base = deflection_breakdown(ota, P.RA_HOUSING, P.DEC_HOUSING)
    bold = deflection_breakdown(ota, P.RA_HOUSING_12MM, P.DEC_HOUSING_12MM)

    sf_base, v_base = _sf_and_verdict(base["total_arcsec"])
    sf_bold, v_bold = _sf_and_verdict(bold["total_arcsec"])

    # The bold 12 mm build is the design recommendation -> governing verdict,
    # but the headline reports both so a FAIL cannot hide behind the upgrade.
    verdict = v_bold
    tgt = P.DEFLECTION_TARGET_ARCSEC

    res = BudgetResult(
        key="stiffness",
        title="Static pointing deflection (OTA horizontal, worst case)",
        verdict=verdict,
        headline=(
            f"{ota.name}: 8 mm baseline {base['total_arcsec']:.1f}\" "
            f"({v_base.value}), 12 mm bold {bold['total_arcsec']:.1f}\" "
            f"({v_bold.value}) vs {tgt:.0f}\" target -- bearing compliance at the "
            f"{dec_span_mm(P.DEC_HOUSING):.1f}/{ra_span_mm(P.RA_HOUSING):.1f} mm "
            f"spans governs."
        ),
        target=f"Summed gravity deflection < {tgt:.0f} arcsec (Hedrick), SF>=1.5 to PASS",
        safety_factor=sf_bold,
    )
    res.add("Payload mass (OTA + train)", payload_mass(ota), "kg")
    res.add("Gravity lever L_cg (cg + saddle)", cg_lever_m(ota), "m",
            "along-tube CG + assumed 50 mm saddle offset")
    res.add("Gravity moment at DEC axis", base["moment_Nm"], "Nm", "W x L_cg, tube horizontal")
    res.add("-- 8 mm baseline housings --", 0.0, "", "")
    res.add("DEC housing beam deflection", u.rad_to_arcsec(base["dec_beam_rad"]), "arcsec")
    res.add("RA housing beam deflection", u.rad_to_arcsec(base["ra_beam_rad"]), "arcsec")
    res.add("DEC bearing-pair tilt", u.rad_to_arcsec(base["dec_bearing_rad"]), "arcsec",
            "6006 @ 180 N/um, 63.5 mm span")
    res.add("RA bearing-pair tilt", u.rad_to_arcsec(base["ra_bearing_rad"]), "arcsec",
            "6008 @ 250 N/um, 76.2 mm span")
    res.add("8 mm TOTAL deflection", base["total_arcsec"], "arcsec")
    res.add("8 mm target / actual (SF)", sf_base, "x", v_base.value)
    res.add("-- 12 mm bold housings --", 0.0, "", "")
    res.add("12 mm beam deflection (DEC+RA)", u.rad_to_arcsec(bold["beam_rad"]), "arcsec")
    res.add("12 mm bearing tilt (DEC+RA)", u.rad_to_arcsec(bold["bearing_rad"]), "arcsec",
            "unchanged -- wall does not stiffen bearings")
    res.add("12 mm TOTAL deflection", bold["total_arcsec"], "arcsec")
    res.add("12 mm target / actual (SF)", sf_bold, "x", v_bold.value)
    res.add("Bearing share of total (8 mm)", 100.0 * base["bearing_rad"] / base["total_rad"], "%")

    res.assumptions = [
        "Worst case: OTA horizontal, gravity perpendicular to the optical axis (SOURCED as the design case).",
        f"L_cg = OTA.cg_from_saddle ({ota.cg_from_saddle_m*1000:.0f} mm) + saddle offset "
        f"{SADDLE_LEVER_M*1000:.0f} mm (saddle undimensioned in repo, ASSUMED).",
        "Bearing radial stiffness 6008~250 N/um, 6006~180 N/um (repo lists only load "
        "ratings, not stiffness) -- ASSUMED.",
        "Bearing span = housing depth (bearings at the box faces): DEC 63.5 mm, RA 76.2 mm.",
        "The full payload moment is applied through BOTH the DEC and RA load paths "
        "(overhung bending on the RA bearings persists even when torque-balanced) -- "
        "a bounding assumption.",
        "Deep-groove bearings modelled; the repo labels them 'angular contact' (flagged "
        "in params) -- a preloaded angular-contact pair would raise stiffness materially.",
    ]
    return res


def ra_span_mm(h: P.Housing) -> float:
    return h.depth_m * 1000.0


def dec_span_mm(h: P.Housing) -> float:
    return h.depth_m * 1000.0


if __name__ == "__main__":
    r = evaluate()
    print(r.verdict.symbol, r.headline)
    print(r.markdown_table())
    for a in r.assumptions:
        print("  -", a)
