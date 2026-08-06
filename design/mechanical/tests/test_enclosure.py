"""Roll-off roof proof: the drive must overcome rolling friction plus the 35 mph
emergency-close gust (the wind, not the roof weight, sizes it) and traverse within
the open time; the closed flat roof carries ~6x its dead weight in snow, which is
the governing structural load and mandates a snow interlock / sloped shedding roof.
The drive PASSes with a ~2x margin over a garage-door-class opener; snow is the
loud finding."""

import math

from design.mechanical.calc import enclosure
from design.mechanical.calc import params as P
from design.mechanical.calc import units as u
from design.mechanical.calc.budget import Verdict


def test_zero_wind_force_is_rolling_only():
    """roof_move_force_N(0) must equal mu * m * g exactly."""
    f0 = enclosure.roof_move_force_N(0.0)
    expected = enclosure.ROLLING_MU * P.ENCLOSURE.roof_mass_kg * u.G0
    assert math.isclose(f0, expected, rel_tol=1e-12)
    assert math.isclose(f0, 88.26, abs_tol=0.5)


def test_wind_adds_and_dominates_the_tractive_load():
    """At the 35 mph gust the wind drag is added and is the majority of the load."""
    gust = P.ENV.wind_gust_close_ms
    f0 = enclosure.roof_move_force_N(0.0)
    fg = enclosure.roof_move_force_N(gust)
    f_wind = fg - f0
    assert fg > f0
    assert math.isclose(f_wind, enclosure.roof_wind_drag_N(gust), rel_tol=1e-12)
    # Wind is the bigger half of the tractive force -> the drive is wind-sized.
    assert f_wind > f0
    assert 0.55 < f_wind / fg < 0.70
    assert 220.0 < fg < 250.0


def test_wind_drag_scales_with_velocity_squared():
    """Doubling the wind must quadruple the drag term."""
    base = enclosure.roof_wind_drag_N(5.0)
    doubled = enclosure.roof_wind_drag_N(10.0)
    assert math.isclose(doubled / base, 4.0, rel_tol=1e-9)


def test_drive_torque_is_force_times_wheel_radius():
    gust = P.ENV.wind_gust_close_ms
    t = enclosure.roof_drive_torque_Nm(gust)
    assert math.isclose(t, enclosure.roof_move_force_N(gust) * enclosure.DRIVE_WHEEL_RADIUS_M, rel_tol=1e-12)
    assert 10.0 < t < 13.0


def test_required_speed_is_feasible_and_within_timeout():
    """Traversing 3 m in the 45 s open time is a gentle speed, well under the ceiling."""
    v = enclosure.roof_required_speed_ms()
    assert math.isclose(v, P.ENCLOSURE.roof_length_m / P.ENCLOSURE.open_time_s, rel_tol=1e-12)
    assert 0.0 < v < enclosure.FEASIBLE_ROOF_SPEED_MS
    # Nominal open time must clear the motor timeout.
    assert P.ENCLOSURE.open_time_s < P.ENCLOSURE.motor_timeout_s


def test_snow_load_matches_pressure_times_area_and_dwarfs_dead_weight():
    """Closed-roof snow = ground snow pressure * plan area, ~6x the roof weight."""
    snow = enclosure.roof_snow_load_N()
    assert math.isclose(snow, P.ENV.ground_snow_load_Pa * enclosure.roof_area_m2(), rel_tol=1e-12)
    assert 10_000.0 < snow < 11_500.0
    roof_weight = u.weight_N(P.ENCLOSURE.roof_mass_kg)
    assert snow > 5.0 * roof_weight          # snow dominates the structure
    assert snow / roof_weight > 6.0


def test_snow_laden_roof_cannot_be_driven():
    """A fully snow-laden roof needs more tractive force than the drive can give ->
    it must never be commanded open under snow (interlock)."""
    f_snow = enclosure.snow_laden_rolling_force_N()
    assert f_snow > enclosure.DRIVE_FORCE_CAP_N
    # And it is far larger than the dry-roof rolling force.
    assert f_snow > 5.0 * enclosure.roof_move_force_N(0.0)


def test_evaluate_drive_passes_with_modest_margin_and_flags_snow():
    r = enclosure.evaluate()
    # Drive clears rolling + the 35 mph gust, but only ~2x over a garage-door opener.
    assert r.verdict in (Verdict.PASS, Verdict.MARGINAL)
    assert r.safety_factor is not None and 1.8 < r.safety_factor < 2.6
    text = (r.headline + " " + " ".join(r.assumptions)).lower()
    assert "snow" in text
    assert "sloped" in text or "shed" in text
    assert "interlock" in text
    assert "wind" in text
    # The key comparison lines are present.
    assert any("Total tractive force" in ln.label for ln in r.lines)
    assert any("snow load" in ln.label.lower() for ln in r.lines)


def test_evaluate_headline_reports_wind_dominance():
    """The finding that wind (not roof weight) sizes the drive must be stated."""
    r = enclosure.evaluate()
    assert any("Wind fraction" in ln.label for ln in r.lines)
    wind_line = next(ln for ln in r.lines if "Wind fraction" in ln.label)
    assert wind_line.value > 50.0
