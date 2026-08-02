"""
Pier / foundation structural proof — is the concrete pier stiff enough (pointing
tilt), high enough in frequency, and stable enough (seismic overturning + soil
embedment + concrete stress) to carry the mount?

The pier is modelled as a solid circular concrete cantilever fixed at grade:
    I = pi*d^4/64,   k = 3*E*I/L^3   (L = exposed height above the top plate)

Four independent checks, each with its own safety factor; the module reports the
governing (minimum) one:

  1. TILT   — pointing rotation of the pier top under the operational (35 mph)
              OTA drag. Must be a small fraction of the 5 arcsec pointing budget.
  2. FREQ   — pier-substructure first mode f = (1/2pi) sqrt(k/m_tip) with the
              full tip mass (head + payload + counterweights). Must clear 10 Hz.
              (The coupled head/bearing rocking mode is dynamics.py's job; here we
              confirm the pier itself is not the soft element.)
  3. SEISMIC — simplified equivalent-lateral-force base shear V = S_DS*W, its
              overturning moment, and stability from soil embedment + dead weight.
  4. CONCRETE — axial bearing + flexural extreme-fibre stress vs f'c and the
              derived modulus of rupture (tension/cracking).

Plus a frost-depth note: the 0.914 m embedment vs the assumed central-NV frost
line (0.3-0.6 m).

Honest expectation: a squat 12"x36" concrete pier is very stiff and stable — all
four checks PASS — but seismic overturning relies on soil embedment: dead weight
ALONE would not resist it (SF < 1), which is the one result worth stating plainly.
"""

from __future__ import annotations

import math

from . import params as P
from . import units as u
from . import wind
from .budget import BudgetResult, verdict_from_sf

_TWO_PI = 2.0 * math.pi

# --------------------------------------------------------------------------
# Modelled constants the repo does not provide (tagged in .assumptions too).
# --------------------------------------------------------------------------
# Mount head mechanical mass (RA+DEC housings, drives, saddle, top plate) as a
# lumped figure — the repo dimensions the parts but gives no assembled head mass.
MOUNT_HEAD_MASS_KG = 12.0             # ASSUMED

# Soil for the embedded-pier stability check (repo gives no geotech data).
SOIL_UNIT_WEIGHT_N_M3 = 18000.0      # ASSUMED medium dense granular (~18 kN/m^3)
SOIL_KP = 3.0                        # ASSUMED Rankine passive coeff (phi ~ 30 deg)

# Assumed central-Nevada high-desert frost penetration depth range.
FROST_DEPTH_TYPICAL_M = 0.6          # ASSUMED conservative upper end (0.3-0.6 m)

# Concrete modulus-of-rupture coefficient (ACI: f_r = 0.62*sqrt(f'c[MPa]) MPa).
MODULUS_OF_RUPTURE_COEFF = 0.62      # ASSUMED (code value)


# --------------------------------------------------------------------------
# Pier section / stiffness helpers.
# --------------------------------------------------------------------------
def pier_second_moment_m4(pier: P.Pier = P.PIER) -> float:
    """Second moment of area of the solid circular pier (m^4): I = pi*d^4/64."""
    return math.pi * pier.diameter_m ** 4 / 64.0


def pier_area_m2(pier: P.Pier = P.PIER) -> float:
    return math.pi * (pier.diameter_m / 2.0) ** 2


def pier_lateral_stiffness_N_per_m(pier: P.Pier = P.PIER) -> float:
    """Exposed pier as a lateral cantilever: k = 3*E*I/L^3 (N/m)."""
    E = pier.material.E
    return 3.0 * E * pier_second_moment_m4(pier) / pier.height_above_m ** 3


# --------------------------------------------------------------------------
# Tilt (pointing) helpers.
# --------------------------------------------------------------------------
def pier_tip_deflection_m(force_N: float, pier: P.Pier = P.PIER) -> float:
    """Cantilever tip deflection under a tip force: delta = F*L^3/(3EI) (m)."""
    E = pier.material.E
    I = pier_second_moment_m4(pier)
    return force_N * pier.height_above_m ** 3 / (3.0 * E * I)


def pier_tilt_arcsec(force_N: float, pier: P.Pier = P.PIER) -> float:
    """Pointing rotation of the pier top under a tip force (arcsec).

    Uses the cantilever tip *slope* theta = F*L^2/(2EI) — the angle the mount
    base (and hence the optical axis) actually rotates through. This is the
    physically correct, conservative pointing metric (it is 1.5x the naive
    delta/L estimate of the same deflection).
    """
    E = pier.material.E
    I = pier_second_moment_m4(pier)
    theta = force_N * pier.height_above_m ** 2 / (2.0 * E * I)
    return u.rad_to_arcsec(theta)


# --------------------------------------------------------------------------
# Mass / frequency helpers.
# --------------------------------------------------------------------------
def counterweight_shaft_mass_kg(cw: P.CounterweightSystem = P.COUNTERWEIGHTS) -> float:
    """Solid 303-SS shaft mass derived from its geometry (kg)."""
    r = cw.shaft_dia_m / 2.0
    volume = math.pi * r ** 2 * cw.shaft_len_m
    return volume * cw.material.rho


def tip_mass_kg(ota: P.OTA, counterweighted: bool = True) -> float:
    """Lumped mass riding on the pier top (kg): head + payload (+ counterweights)."""
    m = MOUNT_HEAD_MASS_KG + ota.mass_kg + P.IMAGING_TRAIN.mass_kg
    if counterweighted:
        m += counterweight_shaft_mass_kg() + P.COUNTERWEIGHTS.weights_available_kg
    return m


def pier_first_mode_hz(m_tip_kg: float, pier: P.Pier = P.PIER) -> float:
    """Pier-substructure first mode f = (1/2pi) sqrt(k/m_tip) (Hz)."""
    k = pier_lateral_stiffness_N_per_m(pier)
    return math.sqrt(k / m_tip_kg) / _TWO_PI


# --------------------------------------------------------------------------
# Mass bookkeeping for seismic / stress.
# --------------------------------------------------------------------------
def pier_exposed_mass_kg(pier: P.Pier = P.PIER) -> float:
    return pier_area_m2(pier) * pier.height_above_m * pier.material.rho


def pier_total_mass_kg(pier: P.Pier = P.PIER) -> float:
    return pier_area_m2(pier) * (pier.height_above_m + pier.embed_depth_m) * pier.material.rho


# --------------------------------------------------------------------------
# Seismic (simplified equivalent lateral force).
# --------------------------------------------------------------------------
def seismic_base_shear_N(w_total_kg: float, env: P.Environment = P.ENV) -> float:
    """Simplified ELF base shear V = S_DS * W (N), W = seismic weight."""
    return env.seismic_sds_g * u.weight_N(w_total_kg)


def seismic_overturning_Nm(ota: P.OTA, pier: P.Pier = P.PIER,
                           env: P.Environment = P.ENV) -> float:
    """Overturning moment about grade from the ELF distribution (N.m).

    Two lumped masses: the exposed pier at its mid-height and the tip mass at the
    OTA height above grade. M = S_DS * g * sum(m_i * h_i).
    """
    m_tip = tip_mass_kg(ota, counterweighted=True)
    m_pier = pier_exposed_mass_kg(pier)
    h_tip = pier.height_above_m + wind.MOUNT_HEAD_HEIGHT_M
    h_pier = pier.height_above_m / 2.0
    return env.seismic_sds_g * u.G0 * (m_pier * h_pier + m_tip * h_tip)


def soil_passive_resultant_N(pier: P.Pier = P.PIER) -> float:
    """Rankine passive resistance developed over the embedded length (N):
    Pp = 1/2 * Kp * gamma * D^2 * b (triangular, resultant at 2D/3 depth)."""
    D = pier.embed_depth_m
    b = pier.diameter_m
    return 0.5 * SOIL_KP * SOIL_UNIT_WEIGHT_N_M3 * D ** 2 * b


# --------------------------------------------------------------------------
# Concrete stress.
# --------------------------------------------------------------------------
def modulus_of_rupture_Pa(pier: P.Pier = P.PIER) -> float:
    """Concrete flexural tensile strength f_r = 0.62*sqrt(f'c[MPa]) (Pa)."""
    fc_MPa = pier.fc_Pa / 1.0e6
    return MODULUS_OF_RUPTURE_COEFF * math.sqrt(fc_MPa) * 1.0e6


# --------------------------------------------------------------------------
# Budget
# --------------------------------------------------------------------------
def evaluate(ota_key: str = "MN78") -> BudgetResult:
    ota = P.OTA_CASES[ota_key]

    k = pier_lateral_stiffness_N_per_m()
    I = pier_second_moment_m4()
    A = pier_area_m2()

    # 1) Tilt under operational (35 mph gust) OTA drag. The drag acts at the
    #    elevated mount head, so it applies to the pier cantilever both a tip
    #    force AND a tip moment M = F*h_head; include the moment slope M*L/(EI).
    f_wind = wind.drag_force_N(P.ENV.wind_gust_close_ms, ota)
    E = P.PIER.material.E
    L = P.PIER.height_above_m
    moment_slope_arcsec = u.rad_to_arcsec(f_wind * wind.MOUNT_HEAD_HEIGHT_M * L / (E * I))
    tilt = pier_tilt_arcsec(f_wind) + moment_slope_arcsec
    delta = pier_tip_deflection_m(f_wind)
    sf_tilt = P.DEFLECTION_TARGET_ARCSEC / tilt

    # 2) First-mode frequency with full tip mass.
    m_tip = tip_mass_kg(ota, counterweighted=True)
    f_pier = pier_first_mode_hz(m_tip)
    sf_freq = f_pier / P.NATURAL_FREQ_TARGET_HZ

    # 3) Seismic base shear + overturning stability.
    w_seismic_kg = m_tip + pier_exposed_mass_kg()
    V_shear = seismic_base_shear_N(w_seismic_kg)
    M_ot = seismic_overturning_Nm(ota)
    Pp = soil_passive_resultant_N()
    D = P.PIER.embed_depth_m
    M_resist_passive = Pp * (2.0 * D / 3.0)                    # about grade
    W_total = u.weight_N(pier_total_mass_kg() + m_tip)
    M_resist_weight = W_total * (P.PIER.diameter_m / 2.0)      # dead-weight about toe
    sf_seismic_ot = (M_resist_passive + M_resist_weight) / M_ot
    sf_seismic_ot_deadwt = M_resist_weight / M_ot              # embedment-neglected
    sf_seismic_shear = Pp / V_shear

    # 4) Concrete stress: axial bearing + flexure from the governing lateral
    #    moment (seismic overturning governs; the OTA is shielded at survival wind).
    M_flex = M_ot
    sigma_axial = u.weight_N(m_tip) / A
    sigma_bend = M_flex * (P.PIER.diameter_m / 2.0) / I
    sigma_comp = sigma_axial + sigma_bend
    sigma_tens = sigma_bend - sigma_axial
    f_r = modulus_of_rupture_Pa()
    sf_conc_comp = P.PIER.fc_Pa / sigma_comp
    sf_conc_tens = f_r / sigma_tens

    # Frost embedment adequacy.
    sf_frost = P.PIER.embed_depth_m / FROST_DEPTH_TYPICAL_M

    # Governing = worst of the four structural checks (frost reported separately).
    governing_sf = min(sf_tilt, sf_freq, sf_seismic_shear, sf_seismic_ot, sf_conc_tens)
    verdict = verdict_from_sf(governing_sf, pass_at=2.0, marginal_at=1.0)

    res = BudgetResult(
        key="pier",
        title="Pier / foundation (tilt, frequency, seismic, concrete)",
        verdict=verdict,
        headline=(
            f"12\"x36\" concrete pier: tilt {tilt:.2f}\" (SF {sf_tilt:.0f}), "
            f"f_n {f_pier:.0f} Hz (SF {sf_freq:.0f}), seismic overturning SF "
            f"{sf_seismic_ot:.1f} (dead-weight-only {sf_seismic_ot_deadwt:.2f} -> embedment "
            f"governs), concrete SF {min(sf_conc_comp, sf_conc_tens):.0f}. Governing SF "
            f"{governing_sf:.1f} ({verdict.value})."
        ),
        target="Tilt << 5\"; f_n > 10 Hz; seismic stable (embed+weight); "
               "concrete < f'c & modulus of rupture",
        safety_factor=governing_sf,
    )
    res.add("Pier I (pi d^4/64)", I, "m^4")
    res.add("Pier lateral stiffness k", k, "N/m", "3EI/L^3 cantilever")
    res.add("-- tilt (35 mph gust) --", 0.0, "", "")
    res.add("OTA drag @ 35 mph", f_wind, "N", "from wind.py")
    res.add("Pier tip deflection", delta * 1e6, "um", "F L^3/3EI")
    res.add("Pier pointing tilt", tilt, "arcsec", "tip slope F L^2/2EI")
    res.add("Tilt budget / actual (SF)", sf_tilt, "x", "vs 5\" pointing budget")
    res.add("-- frequency --", 0.0, "", "")
    res.add("Tip mass (head+payload+CW)", m_tip, "kg")
    res.add("Pier first mode", f_pier, "Hz", "sqrt(k/m)/2pi")
    res.add("f_n / target (SF)", sf_freq, "x", "vs 10 Hz")
    res.add("-- seismic (S_DS=0.5) --", 0.0, "", "")
    res.add("Seismic weight W", u.weight_N(w_seismic_kg), "N", "tip + exposed pier")
    res.add("Base shear V = S_DS W", V_shear, "N")
    res.add("Overturning moment", M_ot, "Nm", "about grade")
    res.add("Soil passive resultant Pp", Pp, "N", "assumed granular, Kp=3")
    res.add("Overturning SF (embed+weight)", sf_seismic_ot, "x")
    res.add("Overturning SF (dead-weight only)", sf_seismic_ot_deadwt, "x",
            "< 1 -> embedment required")
    res.add("Sliding SF (Pp / V)", sf_seismic_shear, "x")
    res.add("-- concrete stress --", 0.0, "", "")
    res.add("Axial bearing stress", sigma_axial, "Pa")
    res.add("Flexural stress (seismic)", sigma_bend, "Pa", "M c / I")
    res.add("Net compression / f'c (SF)", sf_conc_comp, "x")
    res.add("Net tension / modulus rupture (SF)", sf_conc_tens, "x", "cracking check")
    res.add("-- frost --", 0.0, "", "")
    res.add("Embedment / frost depth (SF)", sf_frost, "x",
            f"0.914 m vs assumed {FROST_DEPTH_TYPICAL_M} m frost")
    res.add("Governing safety factor", governing_sf, "x", verdict.value)

    res.assumptions = [
        "Pier modelled as a solid circular concrete cantilever fixed at grade "
        "(I = pi*d^4/64, k = 3EI/L^3); soil-spring base fixity and pier self-mass in "
        "the frequency term are neglected (slightly non-conservative on stiffness).",
        "Pointing tilt uses the cantilever tip SLOPE F*L^2/2EI (the true mount-base "
        "rotation), 1.5x the delta/L estimate of the tip deflection F*L^3/3EI.",
        "Tilt driven by the 35 mph operational gust (roof-open max); the OTA is shielded "
        "at survival wind, so wind never governs the pier structurally.",
        f"Tip mass = assumed {MOUNT_HEAD_MASS_KG:.0f} kg head + payload "
        f"({ota.mass_kg + P.IMAGING_TRAIN.mass_kg:.0f} kg) + counterweights "
        f"({counterweight_shaft_mass_kg() + P.COUNTERWEIGHTS.weights_available_kg:.1f} kg, "
        "shaft mass DERIVED from geometry); head mass ASSUMED.",
        f"Seismic S_DS = {P.ENV.seismic_sds_g} g is ASSUMED (Walker Lane vicinity; repo "
        "silent). Simplified ELF: V = S_DS*W, two-mass overturning distribution.",
        f"Soil ASSUMED medium-dense granular: gamma = {SOIL_UNIT_WEIGHT_N_M3/1000:.0f} kN/m^3, "
        f"Kp = {SOIL_KP} (phi ~ 30 deg); passive resultant over the {P.PIER.embed_depth_m:.3f} m "
        "embedment provides the overturning resistance — dead weight alone would not.",
        f"Concrete f'c = {P.PIER.fc_Pa/1e6:.1f} MPa (SOURCED); modulus of rupture "
        f"f_r = 0.62*sqrt(f'c) = {modulus_of_rupture_Pa()/1e6:.2f} MPa (ASSUMED code value) "
        "used for the tension/cracking check.",
        f"Frost line ASSUMED 0.3-0.6 m for central-NV high desert; the {P.PIER.embed_depth_m:.3f} m "
        "embedment (SOURCED) exceeds it.",
        "Coupled head/bearing rocking (the true system first mode) is owned by dynamics.py; "
        "this module only confirms the pier itself is not the soft/low-frequency element.",
    ]
    return res


if __name__ == "__main__":
    r = evaluate()
    print(r.verdict.symbol, r.headline)
    print(r.markdown_table())
    for a in r.assumptions:
        print("  -", a)
