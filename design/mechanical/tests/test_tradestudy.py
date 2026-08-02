"""
Trade-study invariants (Phase B).

The morphological box and weighted-Pugh scores are a pure function of the score
matrix in ``build_tradestudy.py``; these tests lock the load-bearing claims the
report makes so a silent edit to a score cannot drift the narrative:

  * every weighting scheme is a valid (sums-to-1) simplex, every score in 1..5;
  * the encoder baseline is DISQUALIFIED by the hard 1.0" tracking gate and can
    never be selected, even though its raw weighted score is high;
  * the bold counterweight-FREE GEM wins under ALL three weightings (grounded in
    torque RA SF 2.5 and balance deleting 15.4 kg + 29% RA inertia);
  * the three documented sensitivity FLIPS actually occur (drive, encoder,
    enclosure) and the STABLE picks actually stay put (topology, pier, frame);
  * the three CSVs regenerate with the expected shape.
"""

from __future__ import annotations

import csv
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.normpath(os.path.join(HERE, "..", "tradestudy", "build_tradestudy.py"))


def _load():
    spec = importlib.util.spec_from_file_location("build_tradestudy", GEN)
    mod = importlib.util.module_from_spec(spec)
    # Register before exec so dataclass field-type resolution can find the module.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


TS = _load()


def _sub(key):
    return next(s for s in TS.SUBSYSTEMS if s.key == key)


def test_weighting_schemes_are_valid_simplexes():
    for name, w in TS.WEIGHTS.items():
        assert set(w) == set(TS.CRITERIA), name
        assert abs(sum(w.values()) - 1.0) < 1e-9, (name, sum(w.values()))


def test_all_scores_in_range():
    for sub in TS.SUBSYSTEMS:
        for o in sub.options:
            assert set(o.scores) == set(TS.CRITERIA), o.name
            for c, v in o.scores.items():
                assert 1 <= v <= 5, (o.name, c, v)


def test_seven_subsystems_each_with_a_bold_option():
    assert len(TS.SUBSYSTEMS) == 7
    for sub in TS.SUBSYSTEMS:
        roles = {o.role for o in sub.options}
        assert "baseline" in roles, sub.key
        assert "bold" in roles, sub.key


def test_encoder_baseline_is_gated_out_despite_high_score():
    """The as-specified encoder scores well but FAILS the 1.0" target => gated."""
    enc = _sub("encoder")
    base = next(o for o in enc.options if o.role == "baseline")
    assert base.gate_fail is True
    # Its raw weighted score is actually the highest in the subsystem ...
    raw = {o.name: TS.weighted(o.scores, TS.WEIGHTS["default"]) for o in enc.options}
    assert raw[base.name] == max(raw.values()), "baseline should be the raw-score leader"
    # ... yet it is never selected under any weighting because of the gate.
    for scheme in TS.WEIGHTS:
        assert TS.selected(enc, TS.WEIGHTS[scheme]) is not base


def test_encoder_selection_requires_on_axis_feedback():
    """Every qualifying encoder option carries an on-axis absolute element."""
    enc = _sub("encoder")
    for scheme in TS.WEIGHTS:
        sel = TS.selected(enc, TS.WEIGHTS[scheme])
        assert "on-axis" in sel.name.lower(), (scheme, sel.name)


def test_counterweight_free_gem_wins_everywhere():
    """The bold topology pick is robust across all three weightings."""
    top = _sub("topology")
    bold = next(o for o in top.options if o.role == "bold")
    assert "FREE" in bold.name
    for scheme in TS.WEIGHTS:
        assert TS.selected(top, TS.WEIGHTS[scheme]) is bold, scheme


def test_documented_sensitivity_flips_occur():
    """Precision-heavy weighting must flip drive, encoder, and enclosure."""
    d, p = TS.WEIGHTS["default"], TS.WEIGHTS["precision"]

    drive = _sub("drive")
    assert TS.selected(drive, d).role == "baseline"          # NEMA17+planetary+harmonic
    assert TS.selected(drive, p).name == "Torque-motor direct drive"

    enc = _sub("encoder")
    assert "Hybrid" in TS.selected(enc, d).name
    assert TS.selected(enc, p).name == "On-axis high-res absolute ring"

    enc_sub = _sub("enclosure")
    assert TS.selected(enc_sub, d).role == "baseline"        # plain roll-off
    assert TS.selected(enc_sub, p).name == "Roll-off + active thermal"


def test_stable_picks_do_not_move():
    """Topology, pier, and frame winners are weighting-invariant."""
    for key, want in [("topology", "Counterweight-FREE GEM"),
                      ("pier", "Concrete Sonotube"),
                      ("frame", "6061-T6 CNC plates")]:
        sub = _sub(key)
        picks = {TS.selected(sub, TS.WEIGHTS[s]).name for s in TS.WEIGHTS}
        assert picks == {want}, (key, picks)


def test_mechanical_ota_winner_is_the_light_in_production_tube():
    """On the six mechanical axes alone, the lightest in-production tube wins;
    the program's retention of the heavier MN78 is a science override, not a
    mechanical result (this is why the stiffness proof FAILs on MN78)."""
    ota = _sub("ota")
    for scheme in TS.WEIGHTS:
        assert TS.selected(ota, TS.WEIGHTS[scheme]).name == "ES-MN152 f/4.8", scheme
    mn78 = next(o for o in ota.options if o.role == "baseline")
    mn76 = next(o for o in ota.options if "MN76" in o.name)
    # Among the sourced Intes pair, the lighter MN76 out-scores the doc-selected MN78.
    assert (TS.weighted(mn76.scores, TS.WEIGHTS["default"])
            > TS.weighted(mn78.scores, TS.WEIGHTS["default"]))


def test_csvs_regenerate_with_expected_shape():
    p1 = TS.write_morphological()
    p2 = TS.write_pugh()
    p3 = TS.write_sensitivity()
    n_opts = sum(len(s.options) for s in TS.SUBSYSTEMS)

    for path in (p1, p2, p3):
        assert os.path.exists(path)

    with open(p1) as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ["subsystem", "option", "role", "description", "proof_citation"]
    assert len(rows) == 1 + n_opts

    with open(p2) as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == n_opts
    # Exactly one SELECTED per subsystem (7 total).
    assert sum(1 for r in rows if r["selected"] == "SELECTED") == 7
    assert sum(1 for r in rows if r["gate"] == "DISQUALIFIED") == 1

    with open(p3) as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == n_opts
    for scheme_col in ("win_default", "win_precision", "win_cost"):
        assert sum(1 for r in rows if r[scheme_col] == "*") == 7
