"""
First-mode dynamics proof — is the mount's lowest natural frequency safely above
P.NATURAL_FREQ_TARGET_HZ (10 Hz)?

Why 10 Hz matters: wind-gust energy on a compact tube is concentrated below ~2 Hz
and the OnStepX servo/guide loop operates at ~1-5 Hz. A structural resonance near
those bands would be excited by both the wind and the controller, wrecking
tracking. The first mode must sit well clear -- the repo asserts > 10 Hz.

Two complementary models, both built from the same beam/bearing stiffnesses used
by ``stiffness.py``:

  1. Translational bounce (the prescribed model): the payload rides on a series
     stack of pier-lateral, housing-beam and bearing-radial springs.
         k_eff = series(k_pier, k_ra_beam, k_dec_beam, k_ra_brg, k_dec_brg)
         f_n   = (1/2pi) * sqrt(k_eff / m_eff)

  2. Overhung rocking (physical cross-check): the payload swings on the *angular*
     compliance of the same beams/bearings at lever L_cg. Because the bearing
     spans are short, this rotational mode is the true first mode and comes out
     lower than the bounce mode -- so the honest verdict is taken on the minimum
     of the two.

We run a counterweight-FREE case (light payload) and a counterweighted case
(payload + counterweights), the latter being the lower-frequency case.
"""

from __future__ import annotations

import math

from . import params as P
from . import stiffness as S
from .budget import BudgetResult, verdict_from_sf

_TWO_PI = 2.0 * math.pi


# --------------------------------------------------------------------------
# Stiffness terms (reuse stiffness.py; add the pier).
# --------------------------------------------------------------------------
def pier_lateral_stiffness() -> float:
    """Concrete pier as a lateral cantilever: k = 3*E*I/H^3 (N/m).

    Solid circular section I = pi*D^4/64, height = exposed pier height.
    """
    mat = P.PIER.material
    I = math.pi * P.PIER.diameter_m ** 4 / 64.0
    return 3.0 * mat.E * I / P.PIER.height_above_m ** 3


def _series(*ks: float) -> float:
    return 1.0 / sum(1.0 / k for k in ks)


def effective_stiffness(ra_housing: P.Housing, dec_housing: P.Housing) -> float:
    """Series translational stiffness of the whole head on the pier (N/m)."""
    k_pier = pier_lateral_stiffness()
    k_ra_beam = S.beam_translational_stiffness_N_per_m(ra_housing)
    k_dec_beam = S.beam_translational_stiffness_N_per_m(dec_housing)
    k_ra_brg = S.bearing_pair_stiffness_N_per_m(S.K_RA_BEARING)
    k_dec_brg = S.bearing_pair_stiffness_N_per_m(S.K_DEC_BEARING)
    return _series(k_pier, k_ra_beam, k_dec_beam, k_ra_brg, k_dec_brg)


def effective_mass(ota: P.OTA, counterweighted: bool) -> float:
    """Modal mass (kg): payload alone, or payload + counterweights."""
    m = S.payload_mass(ota)
    if counterweighted:
        m += P.COUNTERWEIGHTS.weights_available_kg
    return m


def first_mode_hz(ota: P.OTA, ra_housing: P.Housing, dec_housing: P.Housing,
                  counterweighted: bool = False) -> float:
    """Translational bounce mode f_n = (1/2pi) sqrt(k_eff/m_eff) (Hz)."""
    k = effective_stiffness(ra_housing, dec_housing)
    m = effective_mass(ota, counterweighted)
    return math.sqrt(k / m) / _TWO_PI


# --------------------------------------------------------------------------
# Rocking cross-check (angular version of the same beam/bearing model).
# --------------------------------------------------------------------------
def beam_angular_stiffness(housing: P.Housing) -> float:
    """M/theta for a box cantilever under an end moment: E*I/L (N.m/rad)."""
    return housing.material.E * S.box_section_I(housing) / housing.depth_m


def bearing_angular_stiffness(span: float, k: float) -> float:
    """M/theta for a bearing pair reacting a moment couple: k*span^2/2 (N.m/rad)."""
    return k * span ** 2 / 2.0


def support_angular_stiffness(ra_housing: P.Housing, dec_housing: P.Housing) -> float:
    """Series rotational stiffness of the overhung load path (N.m/rad)."""
    return _series(
        beam_angular_stiffness(dec_housing),
        beam_angular_stiffness(ra_housing),
        bearing_angular_stiffness(dec_housing.depth_m, S.K_DEC_BEARING),
        bearing_angular_stiffness(ra_housing.depth_m, S.K_RA_BEARING),
    )


def rocking_mode_hz(ota: P.OTA, ra_housing: P.Housing, dec_housing: P.Housing) -> float:
    """Overhung rocking mode of the payload about the support (Hz).

    J = m * L_cg^2 (payload as a point mass at its gravity lever).
    """
    k_theta = support_angular_stiffness(ra_housing, dec_housing)
    J = S.payload_mass(ota) * S.cg_lever_m(ota) ** 2
    return math.sqrt(k_theta / J) / _TWO_PI


def governing_first_mode_hz(ota: P.OTA, ra_housing: P.Housing,
                            dec_housing: P.Housing, counterweighted: bool = False) -> float:
    """The honest first mode = lower of the bounce and rocking modes (Hz)."""
    return min(first_mode_hz(ota, ra_housing, dec_housing, counterweighted),
               rocking_mode_hz(ota, ra_housing, dec_housing))


# --------------------------------------------------------------------------
# Budget
# --------------------------------------------------------------------------
def evaluate(ota_key: str = "MN78") -> BudgetResult:
    ota = P.OTA_CASES[ota_key]
    # Bold 12 mm housings are the recommended build; use them for the head beams.
    ra_h, dec_h = P.RA_HOUSING_12MM, P.DEC_HOUSING_12MM

    k_eff = effective_stiffness(ra_h, dec_h)
    k_pier = pier_lateral_stiffness()

    f_bounce_free = first_mode_hz(ota, ra_h, dec_h, counterweighted=False)
    f_bounce_cw = first_mode_hz(ota, ra_h, dec_h, counterweighted=True)
    f_rock = rocking_mode_hz(ota, ra_h, dec_h)

    # Governing = lowest of every mode/mass case we examined.
    f_governing = min(f_bounce_free, f_bounce_cw, f_rock)
    tgt = P.NATURAL_FREQ_TARGET_HZ
    sf = f_governing / tgt
    verdict = verdict_from_sf(sf, pass_at=1.5, marginal_at=1.0)

    res = BudgetResult(
        key="dynamics",
        title="First natural frequency (structural first mode)",
        verdict=verdict,
        headline=(
            f"{ota.name}: governing first mode {f_governing:.0f} Hz "
            f"(rocking {f_rock:.0f} Hz, bounce {f_bounce_cw:.0f}-{f_bounce_free:.0f} Hz) "
            f"vs {tgt:.0f} Hz target -- SF {sf:.1f}, clear of the <2 Hz wind and "
            f"1-5 Hz servo bands."
        ),
        target=f"First mode > {tgt:.0f} Hz (Hedrick), SF>=1.5 to PASS; must clear 1-5 Hz servo",
        safety_factor=sf,
    )
    res.add("Pier lateral stiffness", k_pier, "N/m", "concrete cantilever 3EI/H^3")
    res.add("Head series stiffness k_eff", k_eff, "N/m", "pier+beams+bearings in series")
    res.add("Payload mass (CW-free)", effective_mass(ota, False), "kg")
    res.add("Payload + counterweights", effective_mass(ota, True), "kg")
    res.add("Bounce mode, CW-free", f_bounce_free, "Hz", "translational")
    res.add("Bounce mode, counterweighted", f_bounce_cw, "Hz", "heavier -> lower f")
    res.add("Rocking mode (governing)", f_rock, "Hz", "overhung on bearing angular stiffness")
    res.add("Governing first mode", f_governing, "Hz", "min of all modes")
    res.add("Governing / target (SF)", sf, "x", verdict.value)
    res.add("Wind-gust excitation band", 2.0, "Hz", "must stay below f_n")
    res.add("Servo/guide bandwidth", 5.0, "Hz", "must stay below f_n")

    res.assumptions = [
        "Pier modelled as a solid concrete lateral cantilever (I = pi*D^4/64); its own "
        "mass and soil/footing compliance are neglected (stiffer, non-conservative for "
        "the pier term but it is not governing).",
        "Bearing radial stiffness 6008~250 N/um, 6006~180 N/um (ASSUMED, shared with "
        "stiffness.py); rocking uses the derived angular stiffness k*span^2/2.",
        "Modal mass = payload (+ 12.5 kg counterweights); head/drive masses and pier "
        "participation neglected -> the true modes are slightly lower.",
        "Rocking inertia J = m*L_cg^2 with L_cg the same gravity lever as stiffness.py "
        "(233 mm CG + 50 mm saddle); point-mass approximation.",
        "12 mm bold housings used for the head beams (recommended build); beam terms are "
        "negligible vs pier and bearing terms either way.",
        "Verdict taken on the lowest mode found (rocking), not the higher bounce mode -- "
        "the honest first mode.",
    ]
    return res


if __name__ == "__main__":
    r = evaluate()
    print(r.verdict.symbol, r.headline)
    print(r.markdown_table())
    for a in r.assumptions:
        print("  -", a)
