"""
Thermal focus-stability proof — over the site's diurnal temperature swing, does
the focus hold PASSIVELY, or is an active temperature-compensated focuser
required? And can a small dew heater keep the corrector above dewpoint?

Physics
-------
Depth of focus (the axial in-focus window, one-sided):

    DoF = +/- 2 * lambda * N**2          (lambda = wavelength, N = f-ratio)

The f/8 MN78 has a LARGER DoF than the f/6 MN76 (DoF scales as N^2), which is a
genuine point in the slower system's favour.

Tube-expansion defocus. The 6061-T6 aluminium tube is the metering structure
that separates the primary mirror cell from the focuser. When it grows by
dL = CTE_al * L_tube * dT the focuser (and the sensor bolted to it) walks away
from the fixed image plane by ~dL to first order (a Newtonian/Mak-Newt has no
strong secondary magnification, so the primary-to-focuser spacing maps ~1:1 to
defocus). We use the *tube length* rather than the focal length as the aluminium
metering length: it is the physical aluminium that expands, and for the folded
Mak-Newts the tube (700 / 1400 mm) is the honest — and less alarming — figure
(focal length would be 1068 / 1440 mm).

    defocus_per_K = CTE_al * L_tube

Astrositall mirror. The mirror substrate CTE (~1.5e-7 /K) is ~157x smaller than
aluminium, so the mirror's own focal-shift term (f * CTE_mirror * dT) is
negligible: the ENTIRE thermal focus error is the aluminium tube. That is the
whole reason the primary is low-expansion glass.

Dew. Heater power to hold the corrector a few K above dewpoint, P = h*A*dT with
h a lumped convective+radiative coefficient and A the corrector area from the
aperture; compared against a 2 W all-sky ring reference.

Conclusion (headline): over the ~22 K diurnal swing the aluminium tube walks the
focus by ~9-10 depths of focus (only ~2 K to leave best focus), so PASSIVE focus
is NOT enough — a temperature-compensated focuser is REQUIRED. The repo's focuser
already carries a temperature coefficient (-2.5 steps/C), so the fix exists; this
proof shows it is not optional.
"""

from __future__ import annotations

import math

from . import params as P
from .budget import BudgetResult, verdict_from_sf

# --------------------------------------------------------------------------
# Modelled constants (the repo's params.py is silent on these).
# --------------------------------------------------------------------------
# The aluminium tube is the metering structure; its CTE comes from params.
TUBE_MATERIAL_KEY = "6061-T6"

# Lumped heat-transfer coefficient corrector-glass -> still night air (natural
# convection + radiation to sky). 5-15 W/m^2K is the usual still-air band; 10 is
# a central ASSUMED value. ASSUMED.
HEAT_TRANSFER_COEFF_WM2K = 10.0

# Hold the corrector this many K above the dewpoint to suppress dew. ASSUMED.
DEW_MARGIN_K = 5.0

# Reference dew-heater ring power to compare against. A small all-sky / corrector
# dew ring is ~2 W. Stated engineering reference figure. ASSUMED (reference).
ALL_SKY_RING_W = 2.0

# Repo focuser default temperature coefficient (steps/C). NOT in params.py — it
# lives in the focuser service (tests/unit/test_focuser_service.py default
# -2.5; docs/API + telescope_tools note ~2.5 steps/C). SOURCED (repo, elsewhere).
FOCUSER_TEMP_COEFF_STEPS_PER_C = -2.5

# The POS retreat sim models MN78 defocus as 2.0 microns/C
# (pos/POS_RETREAT_SIMULATION.md TEMP_COEFFICIENT). First principles below give
# ~33 um/K for a BARE aluminium tube -> the POS figure implicitly assumes a
# low-CTE (carbon / compensated) tube or is optimistic. SOURCED (reference).
POS_TEMP_COEFF_UM_PER_C = 2.0


# --------------------------------------------------------------------------
# Pure helpers (the tests call these).
# --------------------------------------------------------------------------
def depth_of_focus_um(ota: P.OTA) -> float:
    """
    One-sided depth of focus (+/-), micrometres:  DoF = 2 * lambda * N^2.
    The full in-focus window is twice this value. Grows as N^2, so the slower
    f/8 tube tolerates more axial error than the f/6.
    """
    return 2.0 * P.OPTICAL.wavelength_m * ota.f_ratio ** 2 * 1.0e6


def defocus_per_kelvin_um(ota: P.OTA) -> float:
    """
    Focus shift per kelvin from the aluminium tube, micrometres/K:
    defocus_per_K = CTE_al * L_tube (1:1 tube-growth -> defocus, first order).
    """
    cte_al = P.MATERIALS[TUBE_MATERIAL_KEY].cte
    return cte_al * ota.tube_length_m * 1.0e6


def tube_defocus_um(ota: P.OTA, delta_t_c: float) -> float:
    """Total aluminium-tube defocus (micrometres) over a temperature change."""
    return defocus_per_kelvin_um(ota) * delta_t_c


def kelvin_to_defocus(ota: P.OTA) -> float:
    """
    Kelvin of tube temperature change to walk from best focus to the EDGE of the
    depth of focus, i.e. "how many K before out of focus":
        K_edge = DoF / defocus_per_K
    A small number here means passive focus is fragile.
    """
    return depth_of_focus_um(ota) / defocus_per_kelvin_um(ota)


def mirror_defocus_per_kelvin_um(ota: P.OTA) -> float:
    """
    Astrositall primary's own focus shift per kelvin, micrometres/K:
    ~ f * CTE_mirror (the radius, hence focal length, scales with CTE_mirror).
    Uses the system focal length as a conservative (upper-bound) proxy for the
    primary's focal length. Should be ~2 orders of magnitude below the tube term.
    """
    return P.OPTICAL.astrositall_cte * ota.focal_length_m * 1.0e6


def corrector_area_m2(ota: P.OTA) -> float:
    """Corrector clear area from the aperture (m^2). The meniscus glass is a few
    percent larger than the clear aperture, so this slightly under-estimates."""
    return math.pi * (ota.aperture_m / 2.0) ** 2


def dew_heater_power_w(
    ota: P.OTA,
    h: float = HEAT_TRANSFER_COEFF_WM2K,
    dT: float = DEW_MARGIN_K,
) -> float:
    """Steady heater power to hold the corrector dT above ambient: P = h*A*dT."""
    return h * corrector_area_m2(ota) * dT


# --------------------------------------------------------------------------
# Budget
# --------------------------------------------------------------------------
def evaluate(ota_key: str = "MN78") -> BudgetResult:
    ota = P.OTA_CASES[ota_key]
    swing = P.ENV.diurnal_swing_c

    # Depth of focus, both cases (the f/8 vs f/6 comparison is a design point).
    dof_mn76 = depth_of_focus_um(P.MN76)
    dof_mn78 = depth_of_focus_um(P.MN78)
    dof = depth_of_focus_um(ota)

    per_k = defocus_per_kelvin_um(ota)
    k_edge = kelvin_to_defocus(ota)                 # K to leave best focus
    defocus_swing = tube_defocus_um(ota, swing)     # um over the full swing
    n_dof = defocus_swing / dof                     # how many DoF the tube walks

    mir_per_k = mirror_defocus_per_kelvin_um(ota)
    mir_swing = mir_per_k * swing
    tube_over_mirror = per_k / mir_per_k

    heater_w = dew_heater_power_w(ota)

    # Passive-focus safety factor = allowable dT (to edge of DoF) / actual swing.
    # < 1 means the swing blows through the depth of focus -> passive fails.
    passive_sf = k_edge / swing
    verdict = verdict_from_sf(passive_sf, pass_at=2.0, marginal_at=1.0)

    res = BudgetResult(
        key="thermal",
        title="Thermal focus stability over the diurnal swing",
        verdict=verdict,
        headline=(
            f"Passive focus is NOT enough: over the {swing:.0f} K diurnal swing the 6061-T6 tube "
            f"walks focus ~{n_dof:.0f}x the f/{ota.f_ratio:.0f} depth of focus (only {k_edge:.1f} K "
            f"to leave best focus) -> a temperature-compensated focuser is REQUIRED (the repo focuser "
            f"has a {FOCUSER_TEMP_COEFF_STEPS_PER_C:.1f} steps/C coefficient). The Astrositall mirror "
            f"adds only ~{mir_swing:.0f} um ({100.0/tube_over_mirror:.1f}% of the tube term); a "
            f"~{heater_w:.1f} W corrector heater beats the {ALL_SKY_RING_W:.0f} W all-sky ring."
        ),
        target=f"Passive focus stays within +/- DoF over the {swing:.0f} K swing (SF = K_to_edge / swing)",
        safety_factor=passive_sf,
    )

    # Depth of focus (f/8 wins).
    res.add("Depth of focus, MN76 f/6 (+/-)", dof_mn76, "um", "2*lambda*N^2")
    res.add("Depth of focus, MN78 f/8 (+/-)", dof_mn78, "um", "larger -> f/8 more forgiving")
    res.add("DoF ratio f8/f6", dof_mn78 / dof_mn76, "x", "~(8/6)^2 = 1.78 (scales as N^2)")
    # Tube-driven defocus for the selected OTA.
    res.add(f"Tube length ({ota_key})", ota.tube_length_m, "m", "aluminium metering length (choice)")
    res.add("Aluminium CTE", P.MATERIALS[TUBE_MATERIAL_KEY].cte, "1/K", "6061-T6 (params)")
    res.add("Tube defocus per K", per_k, "um/K", "CTE_al * L_tube")
    res.add("K to leave best focus", k_edge, "K", "DoF / (defocus per K)")
    res.add("Diurnal swing", swing, "K", "P.ENV.diurnal_swing_c")
    res.add("Tube defocus over swing", defocus_swing, "um", f"= {n_dof:.1f} x DoF")
    res.add("Passive-focus SF", passive_sf, "x", "K_to_edge / swing (<1 => fails)")
    # Mirror residual (the big win).
    res.add("Astrositall CTE", P.OPTICAL.astrositall_cte, "1/K", "~157x below aluminium")
    res.add("Mirror defocus per K", mir_per_k, "um/K", "f * CTE_mirror")
    res.add("Mirror defocus over swing", mir_swing, "um", "negligible vs tube")
    res.add("Tube / mirror defocus ratio", tube_over_mirror, "x", "aluminium dominates")
    # Cross-check against the POS coefficient.
    res.add("POS modelled coeff (MN78)", POS_TEMP_COEFF_UM_PER_C, "um/K",
            "vs first-principles bare-Al tube -> optimistic")
    # Dew heater.
    res.add("Corrector area (from aperture)", corrector_area_m2(ota), "m^2", "pi*(D/2)^2")
    res.add(f"Dew heater P (hold +{DEW_MARGIN_K:.0f} K)", heater_w, "W",
            f"h={HEAT_TRANSFER_COEFF_WM2K:.0f} W/m^2K")
    res.add("All-sky ring reference", ALL_SKY_RING_W, "W", "heater fits inside this")

    res.assumptions = [
        "Depth of focus DoF = 2*lambda*N^2 (one-sided, +/-), lambda = P.OPTICAL.wavelength_m "
        "(0.55 um); the full in-focus window is twice this. DoF scales as N^2 so f/8 > f/6.",
        "Tube-expansion defocus uses the TUBE LENGTH (P.OTA.tube_length_m) as the aluminium "
        "metering length, not the focal length: it is the physical aluminium between the primary "
        "cell and the focuser, and for these folded Mak-Newts (700/1400 mm tube vs 1068/1440 mm "
        "focal) it is the more physical and less alarming choice. DERIVED.",
        "Tube growth maps ~1:1 to defocus (no strong secondary magnification in a Mak-Newt); a "
        "catadioptric focus-amplification factor would make passive focus WORSE, so 1:1 is "
        "non-conservative-favourable and the FAIL verdict is robust. ASSUMED.",
        "Mirror term ~ f * CTE_mirror with CTE_mirror = P.OPTICAL.astrositall_cte (1.5e-7/K); "
        "system focal length used as an upper-bound proxy for the primary's focal length. DERIVED.",
        f"Dew heater P = h*A*dT with h = {HEAT_TRANSFER_COEFF_WM2K:.0f} W/m^2K (still-air "
        f"convection+radiation, ASSUMED), dT = {DEW_MARGIN_K:.0f} K above dewpoint (ASSUMED), "
        "A = corrector area from the clear aperture (meniscus is a few % larger -> mild under-estimate).",
        f"All-sky dew ring reference = {ALL_SKY_RING_W:.0f} W (stated reference figure, ASSUMED).",
        f"Focuser temperature coefficient {FOCUSER_TEMP_COEFF_STEPS_PER_C:.1f} steps/C is SOURCED from "
        "the repo focuser service (tests/unit/test_focuser_service.py default; docs/telescope_tools "
        "note ~2.5 steps/C) but is NOT in params.py; a focuser step size would be needed to convert "
        "steps -> microns and confirm the compensation resolves the tube term. NOT in params (see notes).",
        f"FINDING: first-principles bare-6061-T6 defocus is ~{per_k:.0f} um/K, whereas the POS retreat "
        f"sim models MN78 at {POS_TEMP_COEFF_UM_PER_C:.0f} um/K "
        "(pos/POS_RETREAT_SIMULATION.md TEMP_COEFFICIENT) -> the POS figure implies a low-CTE "
        "(carbon-fibre / compensated) tube or is ~16x optimistic for bare aluminium. SOURCED cross-check.",
        "CONCLUSION: passive focus FAILS the diurnal swing by ~10x; a temperature-compensated focuser "
        "(which the repo has) is REQUIRED, not optional. The Astrositall primary and a <2 W corrector "
        "heater are genuine wins that make the residual tractable once the tube term is compensated.",
    ]
    return res


if __name__ == "__main__":
    r = evaluate()
    print(r.verdict.symbol, r.headline)
    print(r.markdown_table())
