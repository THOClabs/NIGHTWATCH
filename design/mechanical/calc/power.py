"""
Night-time energy budget — the repo's open power question, resolved.

The observatory's power story has three layers, and this module sizes each and
gives the honest verdict:

Load tally
----------
Every night-time draw, stated with provenance:

    mount (idle/track)  12 V * IRUN * 2 axes   (params: MOTOR.irun_A)
    camera              ~36 W                   (cooled CMOS + TEC, ASSUMED)
    focuser             ~5  W                   (ASSUMED)
    controllers / Pi    ~15 W                   (OnStepX + Raspberry Pi, ASSUMED)
    weather / sensors   ~10 W                   (ASSUMED)
    network             ~15 W                   (switch/router/PoE, ASSUMED)
    DGX Spark           ~170 W                  (Grace+Blackwell class, ASSUMED)

The DGX Spark figure is the single biggest number and is ASSUMED — the repo names
the box (README "NVIDIA DGX Spark") but gives no wattage. It alone is ~60% of the
whole night load, so it dominates every downstream sizing decision.

UPS (graceful shutdown, SOURCED spec)
-------------------------------------
A 1500 VA / 900 W UPS with ~30 min runtime rides the load only long enough to
park + close + flush (~2 min) — a ~15x energy margin on the shutdown, but it does
NOT run a full ~10 h night (it holds ~5% of one). This matches the power_manager
design (park at 50%, emergency close at 20%).

Solar + battery (autonomy)
--------------------------
A 400 W panel + 100 Ah LiFePO4. Battery energy depends on pack voltage, which the
repo does NOT state: 12 V -> 1.2 kWh, 48 V -> 4.8 kWh. Autonomy = usable Wh /
night load. At 12 V the pack gives only ~3.3 h — it FAILS a 10 h winter night;
at 48 V it gives ~13 h and passes. The pack voltage is therefore a decisive,
unspecified design parameter, and the 170 W DGX is why it matters.

DGX thermal
-----------
170 W dumped into the enclosure raises the interior ~14 K above ambient at a
natural ~2 ACH — enough to wreck local seeing and invite dew — so the DGX needs
forced ventilation or, better, to live OUTSIDE the optical enclosure.

Headline verdict is on AUTONOMY (the open question): with the specified 12 V pack
and the assumed DGX load the observatory CANNOT run a winter night off-grid. That
is the honest, important result — and it is fixed by a 48 V pack and/or by
duty-cycling the DGX instead of idling it all night.
"""

from __future__ import annotations

from . import params as P
from .budget import BudgetResult, verdict_from_sf

# --------------------------------------------------------------------------
# Load model (params has no power dataclass -> modelled here; see notes).
# --------------------------------------------------------------------------
# Motor bus voltage. Repo firmware runs the TMC5160/NEMA17 rail at 12 V but this
# is not in params.py. ASSUMED. (V_bus * I_run over-estimates supply draw because
# the driver chops the phase current, so the mount figures are conservative.)
MOTOR_BUS_V = 12.0            # ASSUMED

# RA + DEC = two axis motors (the two HarmonicDrive entries in params). DERIVED.
N_AXIS_MOTORS = 2

LOAD_CAMERA_W = 36.0          # ASSUMED: cooled CMOS with TEC at full cooling
LOAD_FOCUSER_W = 5.0          # ASSUMED
LOAD_CONTROLLERS_W = 15.0     # ASSUMED: OnStepX controller + Raspberry Pi host
LOAD_WEATHER_W = 10.0         # ASSUMED: weather station + sky/safety sensors
LOAD_NETWORK_W = 15.0         # ASSUMED: managed switch / router / PoE
DGX_SPARK_W = 170.0           # ASSUMED: NVIDIA DGX Spark (Grace+Blackwell class);
#                               repo names the box (README) but gives NO wattage.

# --------------------------------------------------------------------------
# UPS (COTS design spec; not in params.py -> see notes). Tagged SOURCED (spec).
# --------------------------------------------------------------------------
UPS_VA = 1500.0               # SOURCED (UPS spec)
UPS_W = 900.0                 # SOURCED (UPS spec)
UPS_RUNTIME_MIN_RATED = 30.0  # SOURCED (UPS spec, nominal)
# Usable battery energy of this UPS class (~2x 12 V 9 Ah AGM, ~80% usable). ASSUMED;
# cross-checked below: 150 Wh / night-load ~ 31 min, consistent with the 30-min spec.
UPS_USABLE_WH = 150.0         # ASSUMED
# Time to park + close + flush before power-down. ASSUMED (power_manager sequence).
SHUTDOWN_TIME_MIN = 2.0       # ASSUMED

# --------------------------------------------------------------------------
# Solar + battery (COTS design spec; not in params.py -> see notes).
# --------------------------------------------------------------------------
PANEL_W = 400.0               # SOURCED (spec)
BATTERY_AH = 100.0            # SOURCED (spec)
DEFAULT_PACK_V = 12.0         # ASSUMED: repo silent; 48 V would be 4x the energy
BATTERY_USABLE_FRAC = 0.80    # ASSUMED: LiFePO4 depth-of-discharge for cycle life
WINTER_PEAK_SUN_HR = 4.5      # ASSUMED: central-Nevada winter peak-sun-hours
PV_DERATE = 0.75              # ASSUMED: temperature + soiling + MPPT + wiring
WINTER_NIGHT_HR = 10.0        # ASSUMED: imaging-night length to cover (astro dark
#                               is ~14 h in Dec, so 10 h is a generous target)
AUTONOMY_SF_PASS = 1.0        # cover exactly one night to PASS
AUTONOMY_SF_MARGINAL = 0.8

# --------------------------------------------------------------------------
# DGX thermal (enclosure heat load).
# --------------------------------------------------------------------------
ENCLOSURE_WALL_HEIGHT_M = 2.4  # ASSUMED wall height (roof footprint from params)
AIR_EXCHANGE_ACH = 2.0         # ASSUMED natural air changes per hour
CP_AIR = 1005.0                # ASSUMED specific heat of air (J/kg-K)


# --------------------------------------------------------------------------
# Pure helpers (the tests call these).
# --------------------------------------------------------------------------
def mount_power_W(slewing: bool = False) -> float:
    """Mount electrical draw: V_bus * I * n_axes, I = IGOTO slewing else IRUN."""
    current = P.MOTOR.igoto_A if slewing else P.MOTOR.irun_A
    return MOTOR_BUS_V * current * N_AXIS_MOTORS


def load_breakdown_W(slewing: bool = False) -> dict[str, float]:
    """Every night-time load in watts, keyed by name."""
    return {
        "mount": mount_power_W(slewing),
        "camera": LOAD_CAMERA_W,
        "focuser": LOAD_FOCUSER_W,
        "controllers": LOAD_CONTROLLERS_W,
        "weather": LOAD_WEATHER_W,
        "network": LOAD_NETWORK_W,
        "dgx": DGX_SPARK_W,
    }


def night_load_W(slewing: bool = False) -> float:
    """Steady night-time load (W). slewing=True swaps mount idle -> goto current."""
    return sum(load_breakdown_W(slewing).values())


def ups_shutdown_margin() -> float:
    """UPS usable energy / energy needed to park+close+flush = shutdown margin (x)."""
    shutdown_wh = night_load_W() * (SHUTDOWN_TIME_MIN / 60.0)
    return UPS_USABLE_WH / shutdown_wh


def ups_runtime_min(load_W: float | None = None) -> float:
    """Approximate UPS runtime at a given load (min); default = night load."""
    load = night_load_W() if load_W is None else load_W
    return UPS_USABLE_WH / load * 60.0


def battery_usable_wh(pack_v: float = DEFAULT_PACK_V) -> float:
    """Usable battery energy = Ah * V * usable-fraction (Wh)."""
    return BATTERY_AH * pack_v * BATTERY_USABLE_FRAC


def solar_autonomy_hours(pack_v: float = DEFAULT_PACK_V) -> float:
    """Battery-only autonomy at the night load (h) for a given pack voltage."""
    return battery_usable_wh(pack_v) / night_load_W()


def solar_daily_harvest_wh() -> float:
    """Energy a 400 W panel harvests on a winter day (Wh) = W * PSH * derate."""
    return PANEL_W * WINTER_PEAK_SUN_HR * PV_DERATE


def enclosure_volume_m3() -> float:
    """Enclosure air volume from the roof footprint x assumed wall height (m^3)."""
    return P.ENCLOSURE.roof_span_m * P.ENCLOSURE.roof_length_m * ENCLOSURE_WALL_HEIGHT_M


def dgx_ventilation_dT(ach: float = AIR_EXCHANGE_ACH, heat_W: float = DGX_SPARK_W) -> float:
    """
    Steady interior temperature rise from a heat load with a given air-change
    rate: dT = Q / (rho * cp * Vdot), Vdot = ACH * volume / 3600 (K).
    """
    vdot = ach * enclosure_volume_m3() / 3600.0
    return heat_W / (P.SITE.air_density * CP_AIR * vdot)


# --------------------------------------------------------------------------
# Budget
# --------------------------------------------------------------------------
def evaluate() -> BudgetResult:
    loads = load_breakdown_W(slewing=False)
    load = night_load_W()                      # steady tracking load
    load_slew = night_load_W(slewing=True)     # transient during a goto
    dgx_frac = DGX_SPARK_W / load

    ups_margin = ups_shutdown_margin()
    ups_rt = ups_runtime_min()
    night_need_wh = load * WINTER_NIGHT_HR
    ups_night_frac = UPS_USABLE_WH / night_need_wh

    autonomy_12 = solar_autonomy_hours(12.0)
    autonomy_48 = solar_autonomy_hours(48.0)
    harvest = solar_daily_harvest_wh()
    harvest_frac = harvest / night_need_wh

    dT = dgx_ventilation_dT()

    # Governing verdict = AUTONOMY on the specified (12 V) pack: this is the repo's
    # open question and the honest failure. UPS-shutdown is a separate PASS.
    autonomy_sf = autonomy_12 / WINTER_NIGHT_HR
    verdict = verdict_from_sf(autonomy_sf, pass_at=AUTONOMY_SF_PASS, marginal_at=AUTONOMY_SF_MARGINAL)

    res = BudgetResult(
        key="power",
        title="Night-time energy budget (UPS + solar autonomy)",
        verdict=verdict,
        headline=(
            f"Night load ~{load:.0f} W, {dgx_frac*100:.0f}% of it the ASSUMED {DGX_SPARK_W:.0f} W DGX Spark. "
            f"The 1500 VA/900 W UPS rides shutdown with {ups_margin:.0f}x margin (~{ups_rt:.0f} min) but only "
            f"~{ups_night_frac*100:.0f}% of a night. Off-grid AUTONOMY {verdict.value}: the specified 400 W + "
            f"100 Ah pack gives only {autonomy_12:.1f} h at 12 V (< {WINTER_NIGHT_HR:.0f} h night) — a 48 V pack "
            f"gives {autonomy_48:.1f} h — and the panel harvests ~{harvest/1000:.1f} kWh/day vs ~{night_need_wh/1000:.1f} "
            f"kWh needed. Drop/duty-cycle the DGX or go 48 V for true autonomy. (DGX dumps ~{dT:.0f} K into the "
            f"enclosure at {AIR_EXCHANGE_ACH:.0f} ACH -> ventilate or locate it outside.)"
        ),
        target=f"Solar+battery sustains the ~{WINTER_NIGHT_HR:.0f} h winter night on the specified pack (SF = autonomy / night)",
        safety_factor=autonomy_sf,
    )

    # Load tally.
    res.add("Mount (idle/track)", loads["mount"], "W", f"{MOTOR_BUS_V:.0f} V * {P.MOTOR.irun_A} A * {N_AXIS_MOTORS} axes")
    res.add("Mount (goto slew)", mount_power_W(True), "W", f"IGOTO {P.MOTOR.igoto_A} A (transient)")
    res.add("Camera", loads["camera"], "W", "cooled CMOS + TEC, ASSUMED")
    res.add("Focuser", loads["focuser"], "W", "ASSUMED")
    res.add("Controllers / Pi", loads["controllers"], "W", "ASSUMED")
    res.add("Weather / sensors", loads["weather"], "W", "ASSUMED")
    res.add("Network", loads["network"], "W", "ASSUMED")
    res.add("DGX Spark", loads["dgx"], "W", "ASSUMED (repo gives no wattage)")
    res.add("Night load (steady)", load, "W", "sum, mount idle")
    res.add("Night load (during goto)", load_slew, "W", "mount at IGOTO")
    res.add("DGX share of night load", dgx_frac * 100.0, "%", "the load is DGX-dominated")
    # UPS.
    res.add("UPS rating", UPS_W, "W", f"{UPS_VA:.0f} VA, SOURCED spec")
    res.add("UPS usable energy", UPS_USABLE_WH, "Wh", "~2x12V9Ah class, ASSUMED")
    res.add("UPS runtime @ night load", ups_rt, "min", f"validates ~{UPS_RUNTIME_MIN_RATED:.0f} min spec")
    res.add("Shutdown time (park+close)", SHUTDOWN_TIME_MIN, "min", "ASSUMED")
    res.add("UPS shutdown margin", ups_margin, "x", "usable / shutdown energy")
    res.add("UPS fraction of a night", ups_night_frac * 100.0, "%", f"of {WINTER_NIGHT_HR:.0f} h -> NOT overnight")
    # Solar + battery.
    res.add("Solar panel", PANEL_W, "W", "SOURCED spec")
    res.add("Battery capacity", BATTERY_AH, "Ah", "LiFePO4, SOURCED spec")
    res.add("Battery energy @ 12 V", battery_usable_wh(12.0), "Wh", f"{BATTERY_USABLE_FRAC*100:.0f}% usable")
    res.add("Battery energy @ 48 V", battery_usable_wh(48.0), "Wh", "4x -> voltage is decisive")
    res.add("Autonomy @ 12 V", autonomy_12, "h", f"< {WINTER_NIGHT_HR:.0f} h night -> FAILS")
    res.add("Autonomy @ 48 V", autonomy_48, "h", f"> {WINTER_NIGHT_HR:.0f} h night -> passes")
    res.add("Daily solar harvest (winter)", harvest, "Wh", f"{PANEL_W:.0f}W*{WINTER_PEAK_SUN_HR}PSH*{PV_DERATE}")
    res.add("Night energy need", night_need_wh, "Wh", f"load * {WINTER_NIGHT_HR:.0f} h")
    res.add("Harvest / night need", harvest_frac * 100.0, "%", "< 100% -> not fully self-sustaining")
    # DGX thermal.
    res.add("Enclosure volume", enclosure_volume_m3(), "m^3", f"footprint x {ENCLOSURE_WALL_HEIGHT_M} m")
    res.add("DGX interior dT @ 2 ACH", dT, "K", "forced ventilation needed")

    res.assumptions = [
        f"Motor bus {MOTOR_BUS_V:.0f} V (ASSUMED; not in params) x IRUN {P.MOTOR.irun_A} A / IGOTO "
        f"{P.MOTOR.igoto_A} A (params) x {N_AXIS_MOTORS} axes. V_bus*I over-estimates supply draw (the TMC "
        "driver chops the phase current, and DEC holds at reduced current), so the mount figure is conservative.",
        "Device wattages ASSUMED (repo gives none): camera 36 W (cooled CMOS+TEC), focuser 5 W, "
        "controllers/Pi 15 W, weather/sensors 10 W, network 15 W. These sum to ~117 W of non-DGX load.",
        f"DGX Spark {DGX_SPARK_W:.0f} W is ASSUMED — the README names 'NVIDIA DGX Spark' (Grace+Blackwell class) "
        f"but states NO wattage. It is ~{dgx_frac*100:.0f}% of the whole night load and therefore dominates the UPS, "
        "battery and thermal sizing. Every autonomy conclusion below hinges on this one assumed number.",
        f"UPS 1500 VA / 900 W, ~{UPS_RUNTIME_MIN_RATED:.0f} min runtime (SOURCED spec, not in params). Usable "
        f"energy {UPS_USABLE_WH:.0f} Wh (ASSUMED, ~2x12V9Ah at 80% DoD); cross-check: {UPS_USABLE_WH:.0f} Wh / "
        f"{night_load_W():.0f} W ~ {ups_rt:.0f} min, consistent with the 30-min spec. Park+close+flush "
        f"{SHUTDOWN_TIME_MIN:.0f} min (ASSUMED) -> {ups_margin:.0f}x shutdown margin, but the UPS holds only "
        f"~{ups_night_frac*100:.0f}% of a {WINTER_NIGHT_HR:.0f} h night: it is a graceful-shutdown store, not an "
        "overnight supply (matches power_manager: park at 50%, emergency close at 20%).",
        f"Battery energy = {BATTERY_AH:.0f} Ah x pack V x {BATTERY_USABLE_FRAC*100:.0f}% usable. Pack voltage is "
        "UNSPECIFIED in the repo and DECISIVE: 12 V -> 1.2 kWh (~3.3 h autonomy, FAILS the night); 48 V -> 4.8 kWh "
        "(~13 h, passes). The headline verdict uses the lower, specified-by-default 12 V case — flag and resolve "
        "the pack voltage.",
        f"Autonomy = usable Wh / night load; target = one {WINTER_NIGHT_HR:.0f} h winter imaging night (ASSUMED; "
        "astronomical dark is ~14 h in December, so 10 h is a generous target). SF = autonomy / night; pass at "
        f"{AUTONOMY_SF_PASS:.1f}. At 12 V SF = {autonomy_sf:.2f} -> FAIL.",
        f"Winter solar harvest = {PANEL_W:.0f} W x {WINTER_PEAK_SUN_HR} PSH x {PV_DERATE} derate = {harvest:.0f} Wh/day "
        f"(all ASSUMED), vs {night_need_wh:.0f} Wh/night -> harvest is only ~{harvest_frac*100:.0f}% of a night's "
        "energy, so even a bigger battery drains over successive nights without grid. The 400 W array cannot "
        "sustain the DGX-dominated load off-grid; duty-cycling the DGX (run inference on demand, not idle all "
        "night) is the highest-leverage fix.",
        f"DGX thermal: {DGX_SPARK_W:.0f} W into a {enclosure_volume_m3():.0f} m^3 enclosure (footprint x "
        f"{ENCLOSURE_WALL_HEIGHT_M} m, ASSUMED) at {AIR_EXCHANGE_ACH:.0f} natural ACH (ASSUMED) gives "
        f"dT = Q/(rho*cp*Vdot) ~ {dT:.0f} K rise — enough to spoil local seeing and drive dew. Force ~10 ACH of "
        "ventilation, or locate the DGX OUTSIDE the optical enclosure. cp_air 1005 J/kg-K, rho "
        f"{P.SITE.air_density:.3f} kg/m^3 at 1800 m (DERIVED).",
        "CONCLUSION (open question resolved): graceful shutdown is comfortably covered; full off-grid autonomy "
        "on the specified 12 V / 400 W system is NOT — the assumed 170 W DGX Spark is the reason. Specify the "
        "pack at 48 V and/or duty-cycle the DGX to make a winter night off-grid feasible.",
    ]
    return res


if __name__ == "__main__":
    r = evaluate()
    print(r.verdict.symbol, r.headline)
    print(r.markdown_table())
