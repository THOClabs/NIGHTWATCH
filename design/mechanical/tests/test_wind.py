"""Wind-load proof: this module OWNS the authoritative drag calc. Two regimes --
tiny operational drag (roof open, 35 mph max) feeding the torque/pier budgets,
and the governing survival case (roof closed, 105 mph) where the near-flat roof
develops uplift far beyond its own weight -- an honest FAIL that surfaces the
repo's missing hold-down/anchorage spec."""

import math

from design.mechanical.calc import params as P
from design.mechanical.calc import torque, wind
from design.mechanical.calc.budget import Verdict


def test_dynamic_pressure_matches_half_rho_v2():
    V = P.ENV.wind_gust_close_ms
    q = wind.dynamic_pressure_Pa(V)
    assert math.isclose(q, 0.5 * P.SITE.air_density * V ** 2, rel_tol=1e-12)
    # At 1800 m the air is thinner than sea level -> q below the 1.225 figure.
    assert q < 0.5 * 1.225 * V ** 2


def test_drag_grows_with_square_of_speed():
    """Doubling wind speed quadruples drag."""
    f1 = wind.drag_force_N(10.0, P.MN78)
    f2 = wind.drag_force_N(20.0, P.MN78)
    assert math.isclose(f2 / f1, 4.0, rel_tol=1e-9)


def test_drag_is_authoritative_and_matches_torque_copy():
    """wind.py owns the drag; torque.py's private copy must agree exactly."""
    for V in (P.ENV.wind_park_ms, P.ENV.wind_gust_close_ms):
        for ota in (P.MN76, P.MN78):
            f_wind = wind.drag_force_N(V, ota)
            f_torque = torque._drag_force(V, ota, P.ENV, P.SITE)
            assert math.isclose(f_wind, f_torque, rel_tol=1e-12)


def test_operational_drag_is_small_but_heavier_tube_sees_more():
    """35 mph gust drag on the OTA is only tens of newtons; MN78 > MN76 (bigger tube)."""
    f_gust_78 = wind.drag_force_N(P.ENV.wind_gust_close_ms, P.MN78)
    f_gust_76 = wind.drag_force_N(P.ENV.wind_gust_close_ms, P.MN76)
    assert 20.0 < f_gust_78 < 60.0
    assert f_gust_78 > f_gust_76  # larger projected area


def test_park_threshold_lower_than_gust():
    assert wind.drag_force_N(P.ENV.wind_park_ms, P.MN78) < \
        wind.drag_force_N(P.ENV.wind_gust_close_ms, P.MN78)


def test_wind_moment_base_exceeds_top():
    """Moment at the pier base (longer lever) exceeds the pier-top moment."""
    ota = P.MN78
    f = wind.drag_force_N(P.ENV.wind_gust_close_ms, ota)
    m_base = wind.ota_wind_moment_Nm(P.ENV.wind_gust_close_ms, ota)
    m_top = f * wind.MOUNT_HEAD_HEIGHT_M
    assert m_base > m_top
    assert math.isclose(m_base, f * (P.PIER.height_above_m + wind.MOUNT_HEAD_HEIGHT_M),
                        rel_tol=1e-12)


def test_roof_uplift_formula_and_magnitude():
    """Survival uplift = q_survival * GCp * A_roof, several kN on the 9 m^2 roof."""
    q = wind.dynamic_pressure_Pa(P.ENV.survival_wind_ms)
    expect = q * P.ENV.roof_uplift_gcp * (P.ENCLOSURE.roof_span_m * P.ENCLOSURE.roof_length_m)
    assert math.isclose(wind.roof_uplift_N(), expect, rel_tol=1e-12)
    assert 8.0e3 < wind.roof_uplift_N() < 11.0e3


def test_roof_selfweight_cannot_resist_uplift():
    """The headline finding: roof dead weight resists only ~1/5 of the uplift."""
    sf = wind.roof_weight_N() / wind.roof_uplift_N()
    assert sf < 0.3
    # Net uplift the (unspecified) anchors must carry is the bulk of the gross.
    assert wind.roof_net_uplift_N() > 0.7 * wind.roof_uplift_N()


def test_assumed_anchors_would_remediate():
    """Four typical 2 klbf anchors turn the FAIL into a real margin -- the fix."""
    capacity = wind.ROOF_ANCHOR_COUNT * wind.ROOF_ANCHOR_ALLOW_N
    assert capacity / wind.roof_uplift_N() > 2.0


def test_survival_governs_over_operational():
    """Survival roof uplift dwarfs the operational gust drag by orders of magnitude."""
    f_gust = wind.drag_force_N(P.ENV.wind_gust_close_ms, P.MN78)
    assert wind.roof_uplift_N() > 100.0 * f_gust


def test_evaluate_fails_on_survival_uplift():
    """As-specified (no anchors in repo) the roof FAILS survival uplift -- the
    important, honest result. Assumptions must disclose the ASSUMED survival wind."""
    r = wind.evaluate("MN78")
    assert r.verdict is Verdict.FAIL
    assert r.safety_factor is not None and r.safety_factor < 1.0
    assert any("uplift" in ln.label.lower() for ln in r.lines)
    assert any("ASSUMED" in a and "mph" in a for a in r.assumptions)
