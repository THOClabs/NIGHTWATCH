"""
Roll-off roof mechanics — can the drive move the roof against rolling friction
AND the 35 mph emergency-close gust within the open/close time, and what does the
closed-roof snow load do to the structure?

Two questions, one honest answer each:

Drive
-----
The moving element is the framed roof panel (P.ENCLOSURE.roof_mass_kg) on level
track. The tractive force the drive must overcome is:

    F_move = mu * m * g            (rolling resistance, level track)
           + 0.5*rho*V^2*Cd*A      (along-track wind drag on the roof end/fascia)

evaluated at the 35 mph gust (P.ENV.wind_gust_close_ms) because the roof MUST be
able to *close* against the worst wind it is allowed to be open in. Drive torque
at the wheel is F_move * wheel_radius. A residential garage-door-opener-class
chain drive (~500 N pull) is the reference capacity. The finding: at 35 mph the
wind drag alone is ~60% of the required tractive force — the drive is sized by
wind, not by the roof's own weight — so the margin over a garage-door opener is
only ~2x, sensitive to the roof's frontal height.

Snow
----
The CLOSED flat roof carries the full ground snow load:

    F_snow = P.ENV.ground_snow_load_Pa * roof_area

At 25 psf over a 3x3 m roof this is ~10.8 kN (~1.1 tonne), ~6x the roof's own
dead weight — the snow case, not the wind case, is the structural design driver
for the roof panel and its supports. A FLAT roll-off roof must carry all of it; a
SLOPED, slippery roof sheds most of it (ASCE 7 slope factor Cs -> ~0 for a steep
metal roof), which is a strong argument for a pitched roof or a positive snow
interlock. A fully snow-laden roof also cannot be driven (rolling force exceeds
the opener), so the roof must never be commanded open under snow.

Headline verdict is on the DRIVE (the mechanism this module can size from params);
the snow load is reported as the governing structural finding + interlock need,
the same way bearings.py PASSes on load capacity while flagging the real driver.
"""

from __future__ import annotations

from . import params as P
from . import units as u
from .budget import BudgetResult, Verdict, verdict_from_sf

# --------------------------------------------------------------------------
# Modelled constants (params.py is silent on roof drive geometry).
# --------------------------------------------------------------------------
# Rolling-resistance coefficient, wheel-on-track. Ideal steel-on-steel is
# ~0.001-0.005, but a real roll-off with V-groove wheels, misalignment, seal drag
# and dirt runs far higher; 0.05 is a conservative ASSUMED value. ASSUMED.
ROLLING_MU = 0.05

# Drive-wheel (or friction/chain sprocket) pitch radius. ASSUMED (stated: 0.05 m).
DRIVE_WHEEL_RADIUS_M = 0.05

# Frontal height of the roof structure (fascia + rafter depth) that presents an
# along-track area to a head/tail wind while the roof is moving. The repo does not
# specify roof section; 0.30 m is an ASSUMED framed-panel depth. ASSUMED.
ROOF_FASCIA_HEIGHT_M = 0.30

# Bluff flat-panel drag coefficient for the roof end. ENV.cd_cylinder (1.1) is for
# a round tube; a flat/square bluff face is higher (~1.2-2.0). 1.3 ASSUMED.
CD_ROOF_FLAT = 1.3

# Reference drive capacity: a residential garage-door-opener-class chain drive
# pulls ~500 N. Conservative COTS figure; commercial roof drives are stronger.
# ASSUMED (reference capacity).
DRIVE_FORCE_CAP_N = 500.0

# Comfortable / safe maximum roof traverse speed (people & pinch hazard). The
# required speed must sit well under this. 0.30 m/s ASSUMED.
FEASIBLE_ROOF_SPEED_MS = 0.30

# Pass gate on the drive safety factor (capacity / required tractive force).
DRIVE_SF_PASS = 2.0


# --------------------------------------------------------------------------
# Pure helpers (the tests call these).
# --------------------------------------------------------------------------
def roof_area_m2() -> float:
    """Plan area of the roof (m^2), from the assumed footprint in params."""
    return P.ENCLOSURE.roof_span_m * P.ENCLOSURE.roof_length_m


def roof_frontal_area_m2() -> float:
    """Along-track frontal area the wind pushes on while the roof moves (m^2)."""
    return P.ENCLOSURE.roof_span_m * ROOF_FASCIA_HEIGHT_M


def roof_rolling_force_N(mass_kg: float | None = None) -> float:
    """Rolling resistance on level track: mu * m * g (N)."""
    m = P.ENCLOSURE.roof_mass_kg if mass_kg is None else mass_kg
    return ROLLING_MU * m * u.G0


def roof_wind_drag_N(wind_ms: float) -> float:
    """Along-track wind drag on the roof end/fascia: 0.5*rho*V^2*Cd*A (N)."""
    return 0.5 * P.SITE.air_density * wind_ms ** 2 * CD_ROOF_FLAT * roof_frontal_area_m2()


def roof_move_force_N(wind_ms: float) -> float:
    """
    Total tractive force to move the roof at a given wind speed (N):
    rolling resistance + along-track wind drag. At wind=0 this is rolling only.
    """
    return roof_rolling_force_N() + roof_wind_drag_N(wind_ms)


def roof_drive_torque_Nm(wind_ms: float) -> float:
    """Drive torque at the wheel to produce roof_move_force_N: F * wheel_radius."""
    return roof_move_force_N(wind_ms) * DRIVE_WHEEL_RADIUS_M


def roof_required_speed_ms() -> float:
    """Average roof speed to traverse roof_length within open_time (m/s)."""
    return P.ENCLOSURE.roof_length_m / P.ENCLOSURE.open_time_s


def roof_snow_load_N() -> float:
    """Total closed-roof snow force = ground snow pressure * roof plan area (N)."""
    return P.ENV.ground_snow_load_Pa * roof_area_m2()


def snow_laden_rolling_force_N() -> float:
    """Rolling force to move the roof with the full design snow load sitting on it:
    mu * (m_roof + m_snow) * g (N). If this exceeds the drive, the roof cannot be
    opened while snow-laden -> a snow interlock is mandatory."""
    m_snow = roof_snow_load_N() / u.G0
    return roof_rolling_force_N(P.ENCLOSURE.roof_mass_kg + m_snow)


# --------------------------------------------------------------------------
# Budget
# --------------------------------------------------------------------------
def evaluate() -> BudgetResult:
    gust = P.ENV.wind_gust_close_ms                     # 35 mph emergency-close

    f_roll = roof_rolling_force_N()
    f_wind = roof_wind_drag_N(gust)
    f_move = roof_move_force_N(gust)
    torque = roof_drive_torque_Nm(gust)
    wind_frac = f_wind / f_move

    v_req = roof_required_speed_ms()
    speed_ok = v_req < FEASIBLE_ROOF_SPEED_MS

    sf_drive = DRIVE_FORCE_CAP_N / f_move

    # Snow (structural + operational).
    snow_N = roof_snow_load_N()
    snow_mass = snow_N / u.G0
    roof_weight = u.weight_N(P.ENCLOSURE.roof_mass_kg)
    snow_over_dead = snow_N / roof_weight
    f_snow_roll = snow_laden_rolling_force_N()
    snow_stalls_drive = f_snow_roll > DRIVE_FORCE_CAP_N

    # Module verdict is the DRIVE feasibility (the mechanism sizeable from params);
    # a too-slow-to-be-safe roof would degrade it. Snow is the loud structural
    # finding carried in the headline/assumptions (no roof section in params to
    # certify against — see notes), mirroring bearings.py.
    verdict = verdict_from_sf(sf_drive, pass_at=DRIVE_SF_PASS, marginal_at=1.0)
    if not speed_ok and verdict is Verdict.PASS:
        verdict = Verdict.MARGINAL

    res = BudgetResult(
        key="enclosure",
        title="Roll-off roof drive + snow load",
        verdict=verdict,
        headline=(
            f"Drive {verdict.value}: moving the {P.ENCLOSURE.roof_mass_kg:.0f} kg roof against rolling + "
            f"the 35 mph close gust needs {f_move:.0f} N ({torque:.1f} Nm @ {DRIVE_WHEEL_RADIUS_M*100:.0f} cm "
            f"wheel), SF {sf_drive:.1f} vs a ~{DRIVE_FORCE_CAP_N:.0f} N garage-door-class drive — and wind is "
            f"{wind_frac*100:.0f}% of that load, so the drive is WIND-sized. FINDING: the closed flat roof "
            f"carries {snow_N/1000:.1f} kN of snow (~{snow_over_dead:.1f}x its dead weight) — the snow case is "
            f"the roof's structural design driver; a sloped roof sheds it, and a snow-laden roof "
            f"{'CANNOT' if snow_stalls_drive else 'can'} be driven -> snow interlock required."
        ),
        target=f"Roof drive overcomes rolling + 35 mph gust with SF >= {DRIVE_SF_PASS:.0f} and traverses within open_time",
        safety_factor=sf_drive,
    )

    # Drive.
    res.add("Roof mass", P.ENCLOSURE.roof_mass_kg, "kg", "ASSUMED (params)")
    res.add("Rolling resistance force", f_roll, "N", f"mu={ROLLING_MU} * m * g")
    res.add("Wind drag @ 35 mph gust", f_wind, "N", f"0.5*rho*V^2*Cd*A, Cd={CD_ROOF_FLAT}")
    res.add("Frontal area (wind)", roof_frontal_area_m2(), "m^2", f"span x {ROOF_FASCIA_HEIGHT_M} m fascia")
    res.add("Total tractive force", f_move, "N", "rolling + wind")
    res.add("Wind fraction of tractive force", wind_frac * 100.0, "%", "drive is wind-sized")
    res.add("Drive torque @ wheel", torque, "Nm", f"F * {DRIVE_WHEEL_RADIUS_M} m")
    res.add("Drive capacity (reference)", DRIVE_FORCE_CAP_N, "N", "garage-door-opener class, ASSUMED")
    res.add("Drive safety factor", sf_drive, "x", f"capacity / tractive (pass >= {DRIVE_SF_PASS:.0f})")
    res.add("Required roof speed", v_req, "m/s", f"{P.ENCLOSURE.roof_length_m:.0f} m / {P.ENCLOSURE.open_time_s:.0f} s")
    res.add("Feasible speed ceiling", FEASIBLE_ROOF_SPEED_MS, "m/s", f"speed ok = {speed_ok}")
    res.add("Open time vs motor timeout", P.ENCLOSURE.open_time_s, "s", f"< {P.ENCLOSURE.motor_timeout_s:.0f} s timeout")
    # Snow.
    res.add("Ground snow pressure", P.ENV.ground_snow_load_Pa, "Pa", "25 psf, ASSUMED (params)")
    res.add("Roof plan area", roof_area_m2(), "m^2", "span x length")
    res.add("Closed-roof snow load", snow_N, "N", "pressure x area")
    res.add("Snow mass on roof", snow_mass, "kg", "~1.1 tonne")
    res.add("Snow / roof dead weight", snow_over_dead, "x", "snow dominates the structure")
    res.add("Snow-laden rolling force", f_snow_roll, "N", f"mu*(m_roof+m_snow)*g {'> drive' if snow_stalls_drive else '< drive'}")

    res.assumptions = [
        f"Rolling resistance coefficient mu = {ROLLING_MU} (ASSUMED): far above ideal steel-on-steel "
        "(~0.001-0.005) to cover V-groove wheels, misalignment, seal drag and grit — conservative.",
        f"Drive-wheel radius {DRIVE_WHEEL_RADIUS_M} m (ASSUMED, stated). Drive torque = F * radius.",
        f"Wind drag uses the 35 mph emergency-close gust (P.ENV.wind_gust_close_ms, SOURCED) on a frontal "
        f"area = roof span x {ROOF_FASCIA_HEIGHT_M} m fascia height (ASSUMED) with a flat-panel Cd={CD_ROOF_FLAT} "
        f"(ASSUMED; ENV.cd_cylinder=1.1 is for a round tube). Air density {P.SITE.air_density:.3f} kg/m^3 at "
        "1800 m (DERIVED). The result is sensitive to the assumed fascia height: a taller roof profile pushes "
        "the drive SF toward MARGINAL.",
        f"Drive capacity {DRIVE_FORCE_CAP_N:.0f} N is a residential garage-door-opener-class chain drive "
        "(ASSUMED reference); a commercial roof drive is stronger. FINDING: at 35 mph the WIND is "
        f"{wind_frac*100:.0f}% of the tractive load, so the drive is sized by wind, not roof weight — a "
        "positive close against the gust is the governing drive requirement.",
        f"Required roof speed {v_req:.3f} m/s ({P.ENCLOSURE.roof_length_m:.0f} m in {P.ENCLOSURE.open_time_s:.0f} s) "
        f"is well under the {FEASIBLE_ROOF_SPEED_MS:.2f} m/s comfort/safety ceiling (ASSUMED), and open_time "
        f"{P.ENCLOSURE.open_time_s:.0f} s < {P.ENCLOSURE.motor_timeout_s:.0f} s motor timeout (SOURCED), so travel "
        "time is not the constraint.",
        f"SNOW (structural): the closed flat roof carries the full ground snow load "
        f"({P.ENV.ground_snow_load_Pa/u.PSF_TO_PA:.0f} psf, ASSUMED) = {snow_N/1000:.1f} kN over {roof_area_m2():.0f} m^2, "
        f"~{snow_over_dead:.1f}x the roof's own {roof_weight/1000:.1f} kN dead weight. The snow case, not wind, is "
        "the roof panel/support design driver. A SLOPED, slippery roof sheds most of it (ASCE 7 slope factor "
        "Cs -> ~0 for a steep metal roof); a FLAT roll-off roof must carry all of it.",
        f"SNOW (operational): a fully snow-laden roof needs {f_snow_roll:.0f} N to roll, which "
        f"{'EXCEEDS' if snow_stalls_drive else 'is within'} the {DRIVE_FORCE_CAP_N:.0f} N drive -> the roof must "
        "never be commanded open under snow. A snow/ice interlock (or a pitched shedding roof) is required; the "
        "safety monitor should hold the roof CLOSED while snow-loaded.",
        "OPEN ITEM: params.py specifies no roof structural section, so the snow load here is reported as the "
        "governing DESIGN LOAD, not certified against a computed roof capacity — see notes (recommend a POS "
        "Enclosure roof-structure entry).",
    ]
    return res


if __name__ == "__main__":
    r = evaluate()
    print(r.verdict.symbol, r.headline)
    print(r.markdown_table())
