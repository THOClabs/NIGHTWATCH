"""Night-time energy budget proof: the load is DGX-dominated (~60%), the UPS covers
graceful shutdown with a huge margin but only ~5% of a night, and the specified
400 W / 100 Ah solar+battery gives only ~3.3 h autonomy at 12 V -> it FAILS a 10 h
winter night. A 48 V pack (4x energy) or duty-cycling the DGX fixes it. FAIL on
off-grid autonomy is the honest, important result."""

import math

from design.mechanical.calc import params as P
from design.mechanical.calc import power
from design.mechanical.calc.budget import Verdict


def test_mount_power_uses_params_currents_and_axis_count():
    """Mount draw = V_bus * I * n_axes, with IGOTO > IRUN."""
    idle = power.mount_power_W(slewing=False)
    slew = power.mount_power_W(slewing=True)
    assert math.isclose(idle, power.MOTOR_BUS_V * P.MOTOR.irun_A * power.N_AXIS_MOTORS, rel_tol=1e-12)
    assert math.isclose(slew, power.MOTOR_BUS_V * P.MOTOR.igoto_A * power.N_AXIS_MOTORS, rel_tol=1e-12)
    assert slew > idle
    assert math.isclose(idle, 36.0, abs_tol=1e-9)


def test_night_load_sums_all_stated_loads():
    """night_load_W must equal the sum of the itemised breakdown, ~287 W."""
    load = power.night_load_W()
    assert math.isclose(load, sum(power.load_breakdown_W().values()), rel_tol=1e-12)
    assert math.isclose(load, 287.0, abs_tol=1.0)
    # Slewing swaps mount idle->goto, raising the load a little.
    assert power.night_load_W(slewing=True) > load


def test_dgx_dominates_the_load():
    """The assumed 170 W DGX Spark is the majority of the night load."""
    load = power.night_load_W()
    assert power.DGX_SPARK_W / load > 0.5
    # Without the DGX the load more than halves.
    assert (load - power.DGX_SPARK_W) < power.DGX_SPARK_W


def test_ups_covers_shutdown_with_large_margin_but_not_the_night():
    """UPS rides park+close with >5x margin, yet holds only a small % of a night."""
    margin = power.ups_shutdown_margin()
    assert margin > 5.0
    assert math.isclose(
        margin,
        power.UPS_USABLE_WH / (power.night_load_W() * power.SHUTDOWN_TIME_MIN / 60.0),
        rel_tol=1e-12,
    )
    # The UPS cannot ride a full winter night.
    night_need_wh = power.night_load_W() * power.WINTER_NIGHT_HR
    assert 0.15 * night_need_wh > power.UPS_USABLE_WH
    # Its runtime at the night load is consistent with the ~30 min spec.
    assert 25.0 < power.ups_runtime_min() < 40.0


def test_solar_autonomy_fails_the_night_at_12v_but_passes_at_48v():
    """The decisive, unspecified parameter is pack voltage."""
    a12 = power.solar_autonomy_hours(12.0)
    a48 = power.solar_autonomy_hours(48.0)
    assert 3.0 < a12 < 3.7
    assert a12 < power.WINTER_NIGHT_HR          # 12 V pack FAILS a 10 h night
    assert a48 > power.WINTER_NIGHT_HR          # 48 V pack covers it
    # 48 V holds exactly 4x the energy of 12 V.
    assert math.isclose(a48 / a12, 4.0, rel_tol=1e-9)


def test_battery_energy_scales_with_pack_voltage():
    assert math.isclose(power.battery_usable_wh(12.0), 100.0 * 12.0 * power.BATTERY_USABLE_FRAC, rel_tol=1e-12)
    assert math.isclose(power.battery_usable_wh(48.0), 4.0 * power.battery_usable_wh(12.0), rel_tol=1e-12)


def test_winter_harvest_is_less_than_a_nights_energy():
    """The 400 W array cannot even harvest one night's worth of energy per day ->
    not self-sustaining off-grid with the DGX-dominated load."""
    harvest = power.solar_daily_harvest_wh()
    night_need = power.night_load_W() * power.WINTER_NIGHT_HR
    assert harvest < night_need
    assert 0.3 < harvest / night_need < 0.6


def test_dgx_thermal_needs_ventilation():
    """170 W at a natural ~2 ACH raises the enclosure by many kelvin -> ventilate."""
    dT = power.dgx_ventilation_dT()
    assert dT > 8.0                              # far above a benign rise
    # More air changes cut the rise (inverse in ACH).
    assert power.dgx_ventilation_dT(ach=10.0) < dT
    assert math.isclose(power.dgx_ventilation_dT(ach=10.0) * 10.0,
                        power.dgx_ventilation_dT(ach=2.0) * 2.0, rel_tol=1e-9)


def test_evaluate_fails_autonomy_and_names_the_culprit():
    r = power.evaluate()
    # Off-grid autonomy on the specified 12 V pack does NOT hold the night.
    assert r.verdict is Verdict.FAIL
    assert r.safety_factor is not None and r.safety_factor < 1.0
    text = (r.headline + " " + " ".join(r.assumptions)).lower()
    assert "dgx" in text
    assert "48" in text                          # the 48 V fix is called out
    assert "autonomy" in text
    # Load, UPS and solar lines are all present.
    assert any("Night load (steady)" in ln.label for ln in r.lines)
    assert any("UPS shutdown margin" in ln.label for ln in r.lines)
    assert any("Autonomy @ 12 V" in ln.label for ln in r.lines)
