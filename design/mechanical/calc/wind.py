"""
Wind structural-load proof — THE authoritative wind calculation for the whole
package (torque.py deliberately defers its own drag helper to this module).

Two regimes, two very different jobs:

  1. OPERATIONAL (roof OPEN, telescope exposed). The safety monitor parks at
     25 mph and emergency-closes at 35 mph, so 35 mph is the most wind the OTA
     ever sees while pointing. The broadside drag on the tube and the moment it
     puts into the pier top are what torque.py and pier.py consume for the
     tracking / pointing budgets. These loads are small.

  2. SURVIVAL (roof CLOSED, telescope shielded). The governing structural case
     is the roll-off enclosure at the ASCE-7 basic wind speed (105 mph, ASSUMED
     — the repo is silent). A near-flat roof develops large net UPLIFT, and the
     tall box develops large lateral drag. This is where the repo has a genuine
     void: no roof hold-down or enclosure anchorage is specified, and the roof's
     own weight resists only a fraction of the uplift.

Dynamic pressure throughout: q = 1/2 rho V^2 with rho = P.SITE.air_density (ISA
at 1800 m, ~1.03 kg/m^3 — 16% below sea level, which honestly *reduces* every
load below the usual sea-level assumption).

Honest expectation encoded below: SURVIVAL WIND GOVERNS, and the roll-off roof
FAILS to resist its own uplift by dead weight (SF ~0.19) — hold-down anchors are
mandatory and unspecified. That FAIL is the finding worth surfacing, exactly the
kind of structural void params.py flags survival wind as.
"""

from __future__ import annotations

from . import params as P
from . import units as u
from .budget import BudgetResult, verdict_from_sf

# --------------------------------------------------------------------------
# Modelled geometry / coefficients the repo does not provide.
# (All tagged again in result.assumptions.)
# --------------------------------------------------------------------------
# OTA optical-axis height above the pier top (mount head build height). The repo
# dimensions neither the head nor the saddle stack, so this is ASSUMED. Used only
# to turn the operational drag force into an overturning moment.
MOUNT_HEAD_HEIGHT_M = 0.50            # ASSUMED

# Roll-off enclosure box (footprint = roof span x length from params, height and
# cladding mass are unspecified -> ASSUMED).
WALL_HEIGHT_M = 2.4                   # ASSUMED enclosure wall height
WALL_AREAL_MASS_KG_M2 = 12.0          # ASSUMED light steel panel + framing
WALL_FORCE_COEFF = 1.2               # ASSUMED net force coefficient, low-rise box (windward+leeward)

# Hold-down anchorage used to demonstrate a *remediation*, since the repo omits
# it entirely. A common 1/2" wedge anchor into 4 ksi concrete carries ~2000 lbf
# allowable; four (one per roof corner) is the minimum credible scheme.
ROOF_ANCHOR_ALLOW_N = u.weight_N(u.lb(2000.0))  # ASSUMED ~2000 lbf allowable tension per anchor
ROOF_ANCHOR_COUNT = 4                 # ASSUMED (one per roof corner)


# --------------------------------------------------------------------------
# Pure helpers (the tests call these directly).
# --------------------------------------------------------------------------
def dynamic_pressure_Pa(V_ms: float, site: P.Site = P.SITE) -> float:
    """Stagnation dynamic pressure q = 1/2 rho V^2 (Pa) at the site air density."""
    return 0.5 * site.air_density * V_ms ** 2


def tube_area_m2(ota: P.OTA) -> float:
    """Broadside projected area of the closed tube (m^2) = OD x length."""
    return ota.tube_od_m * ota.tube_length_m


def drag_force_N(V_ms: float, ota: P.OTA,
                 env: P.Environment = P.ENV, site: P.Site = P.SITE) -> float:
    """Broadside wind drag on the OTA tube (N): F = q * Cd * A.

    This is the single authoritative drag used across the package (torque.py's
    private copy uses the identical formula and parameters).
    """
    return dynamic_pressure_Pa(V_ms, site) * env.cd_cylinder * tube_area_m2(ota)


def ota_wind_moment_Nm(V_ms: float, ota: P.OTA,
                       pier: P.Pier = P.PIER) -> float:
    """Overturning moment at the pier BASE from OTA drag (N.m).

    Lever = exposed pier height + mount-head height (OTA optical axis above the
    pier top). The moment resisted at the pier *top* alone is F*mount_head.
    """
    lever = pier.height_above_m + MOUNT_HEAD_HEIGHT_M
    return drag_force_N(V_ms, ota) * lever


def roof_area_m2(enc: P.Enclosure = P.ENCLOSURE) -> float:
    return enc.roof_span_m * enc.roof_length_m


def roof_uplift_N(env: P.Environment = P.ENV, enc: P.Enclosure = P.ENCLOSURE,
                  site: P.Site = P.SITE) -> float:
    """Gross survival wind uplift on the (near-flat) roll-off roof (N):
    U = q_survival * GCp_uplift * A_roof."""
    q = dynamic_pressure_Pa(env.survival_wind_ms, site)
    return q * env.roof_uplift_gcp * roof_area_m2(enc)


def roof_weight_N(enc: P.Enclosure = P.ENCLOSURE) -> float:
    return u.weight_N(enc.roof_mass_kg)


def roof_net_uplift_N() -> float:
    """Uplift the anchors must resist after crediting roof dead weight (N)."""
    return roof_uplift_N() - roof_weight_N()


def enclosure_wall_area_m2(enc: P.Enclosure = P.ENCLOSURE) -> float:
    """Windward wall projected area (m^2) = roof length x assumed wall height."""
    return enc.roof_length_m * WALL_HEIGHT_M


def enclosure_lateral_force_N(env: P.Environment = P.ENV, enc: P.Enclosure = P.ENCLOSURE,
                              site: P.Site = P.SITE) -> float:
    """Survival lateral drag on the enclosure box (N): q_survival * Cf * A_wall."""
    q = dynamic_pressure_Pa(env.survival_wind_ms, site)
    return q * WALL_FORCE_COEFF * enclosure_wall_area_m2(enc)


def enclosure_weight_N(enc: P.Enclosure = P.ENCLOSURE) -> float:
    """Roof + wall-cladding dead weight of the enclosure (N)."""
    perimeter = 2.0 * (enc.roof_span_m + enc.roof_length_m)
    wall_mass = perimeter * WALL_HEIGHT_M * WALL_AREAL_MASS_KG_M2
    return u.weight_N(enc.roof_mass_kg + wall_mass)


def enclosure_overturning_Nm(enc: P.Enclosure = P.ENCLOSURE) -> float:
    """Survival overturning moment of the box about its leeward base edge (N.m).
    Lateral resultant applied at wall mid-height."""
    return enclosure_lateral_force_N() * (WALL_HEIGHT_M / 2.0)


# --------------------------------------------------------------------------
# Budget
# --------------------------------------------------------------------------
def evaluate(ota_key: str = "MN78") -> BudgetResult:
    ota = P.OTA_CASES[ota_key]

    # --- operational (roof open): OTA drag at park and gust ---
    f_park = drag_force_N(P.ENV.wind_park_ms, ota)
    f_gust = drag_force_N(P.ENV.wind_gust_close_ms, ota)
    m_gust_base = ota_wind_moment_Nm(P.ENV.wind_gust_close_ms, ota)
    m_gust_top = f_gust * MOUNT_HEAD_HEIGHT_M

    # --- survival (roof closed): enclosure loads ---
    q_surv = dynamic_pressure_Pa(P.ENV.survival_wind_ms)
    uplift = roof_uplift_N()
    roof_wt = roof_weight_N()
    net_uplift = roof_net_uplift_N()
    lateral = enclosure_lateral_force_N()
    overturn = enclosure_overturning_Nm()

    # Roof hold-down: dead weight alone vs uplift, then the assumed anchor scheme.
    sf_selfweight = roof_wt / uplift
    anchor_capacity = ROOF_ANCHOR_COUNT * ROOF_ANCHOR_ALLOW_N
    sf_anchored = anchor_capacity / uplift

    # Enclosure overturning: dead-weight-only vs with windward anchors.
    enc_stab_weight = enclosure_weight_N() * (min(P.ENCLOSURE.roof_span_m,
                                                  P.ENCLOSURE.roof_length_m) / 2.0)
    sf_overturn_deadwt = enc_stab_weight / overturn

    # Governing verdict = the roof self-weight hold-down (the starkest survival
    # finding). As-specified (no anchors in repo) the roof CANNOT hold itself
    # down -> FAIL. The anchor line shows the remediation.
    governing_sf = sf_selfweight
    verdict = verdict_from_sf(governing_sf, pass_at=1.5, marginal_at=1.0)

    survival_governs = uplift > f_gust and overturn > m_gust_base

    res = BudgetResult(
        key="wind",
        title="Wind structural loads (operational drag + survival uplift)",
        verdict=verdict,
        headline=(
            f"Survival wind (105 mph) GOVERNS: {uplift/1e3:.1f} kN roof uplift vs "
            f"{roof_wt/1e3:.1f} kN roof self-weight (SF {sf_selfweight:.2f}) -- "
            f"hold-down anchors are MANDATORY and unspecified in the repo "
            f"(4x 2 klbf anchors -> SF {sf_anchored:.1f}). Operational gust drag "
            f"on {ota.name} is only {f_gust:.0f} N."
        ),
        target="Survival roof uplift resisted by hold-down (self-weight insufficient); "
               "operational drag feeds torque/pier budgets",
        safety_factor=governing_sf,
    )
    # Operational block.
    res.add("Air density @ 1800 m", P.SITE.air_density, "kg/m^3", "ISA, 16% below sea level")
    res.add("q @ 25 mph park", dynamic_pressure_Pa(P.ENV.wind_park_ms), "Pa")
    res.add("q @ 35 mph gust", dynamic_pressure_Pa(P.ENV.wind_gust_close_ms), "Pa")
    res.add("OTA drag @ 25 mph (park)", f_park, "N")
    res.add("OTA drag @ 35 mph (gust)", f_gust, "N", "max wind while open")
    res.add("Wind moment at pier TOP @ gust", m_gust_top, "Nm", "F x mount-head height")
    res.add("Wind moment at pier BASE @ gust", m_gust_base, "Nm", "F x (pier + head height)")
    # Survival block.
    res.add("-- survival, roof closed --", 0.0, "", "")
    res.add("q @ 105 mph survival", q_surv, "Pa")
    res.add("Roof gross uplift", uplift, "N", "q x GCp x A_roof")
    res.add("Roof self-weight", roof_wt, "N")
    res.add("Roof NET uplift (anchor demand)", net_uplift, "N", "uplift - self-weight")
    res.add("Roof self-weight / uplift (SF)", sf_selfweight, "x", verdict.value)
    res.add("Assumed anchor capacity (4x)", anchor_capacity, "N")
    res.add("Anchored hold-down (SF)", sf_anchored, "x", "remediation")
    res.add("Enclosure lateral drag", lateral, "N", "q x Cf x A_wall")
    res.add("Enclosure overturning moment", overturn, "Nm", "about leeward base edge")
    res.add("Overturning, dead-weight only (SF)", sf_overturn_deadwt, "x",
            "anchors required" if sf_overturn_deadwt < 1.0 else "")
    res.add("Survival governs vs operational", 1.0 if survival_governs else 0.0, "bool")

    res.assumptions = [
        f"Dynamic pressure uses site air density {P.SITE.air_density:.3f} kg/m^3 "
        f"(ISA @ 1800 m, DERIVED) — lower than sea level, so loads are honest not inflated.",
        "Operational max wind = 35 mph emergency-close gust (SOURCED safety monitor); the "
        "OTA is only exposed with the roof open, so it never sees survival wind.",
        f"Survival basic wind {P.ENV.survival_wind_ms/u.MPH_TO_MS:.0f} mph is ASSUMED "
        "(ASCE 7 central-NV Risk Cat I; repo is silent — a governing void).",
        f"Roof footprint {roof_area_m2():.0f} m^2 and mass {P.ENCLOSURE.roof_mass_kg:.0f} kg "
        "are ASSUMED (params flags roof geometry as unspecified).",
        f"Net uplift coefficient GCp = {P.ENV.roof_uplift_gcp} (SOURCED param); wall force "
        f"coefficient Cf = {WALL_FORCE_COEFF} on an assumed {WALL_HEIGHT_M} m wall (ASSUMED).",
        f"Mount-head height {MOUNT_HEAD_HEIGHT_M*1000:.0f} mm (OTA axis above pier top) is "
        "ASSUMED; sets the operational overturning lever.",
        "Repo specifies NO roof hold-down or enclosure anchorage; the anchor scheme "
        "(4x 2 klbf, ASSUMED) is shown only as remediation, not as an existing spec.",
        "The pier is assumed structurally isolated from the enclosure (standard observatory "
        "practice), so roof uplift loads the enclosure foundation, not the pier.",
    ]
    return res


if __name__ == "__main__":
    r = evaluate()
    print(r.verdict.symbol, r.headline)
    print(r.markdown_table())
    for a in r.assumptions:
        print("  -", a)
