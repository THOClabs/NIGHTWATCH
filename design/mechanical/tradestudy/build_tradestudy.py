"""
NIGHTWATCH mechanical trade study — morphological (Zwicky) box + weighted Pugh.

This is Phase B of the mechanical-design proof. It does NOT compute physics; it
*scores* the design permutations against the verdicts the Phase-C proof modules
(torque, stiffness, dynamics, encoder, balance, bearings, wind, pier, thermal,
enclosure, power) actually computed, so the selection is grounded, not asserted.

Scoring convention
------------------
Every criterion is "higher is better" on a 1..5 scale (5 = best):
    1 poor · 2 below par · 3 adequate/baseline · 4 good · 5 excellent
For the cost and sourcing criteria, 5 therefore means *cheapest* / *lowest
sourcing risk*. A weighted score is sum(weight_i * score_i), so it stays in 1..5.

Requirement gate
----------------
A weighted score can rank an option that FAILS a hard requirement above one that
meets it (see the encoder subsystem). Precision against the 1.0" tracking target
is a pass/fail GATE, not merely a weighted criterion: any option that fails the
gate is DISQUALIFIED from selection regardless of its weighted score. This is the
central lesson of the study and is encoded explicitly (``gate_fail``).

Outputs (written next to this file):
    morphological.csv   the Zwicky box: every option, its role, proof citation
    pugh_scores.csv     the six criteria scores + default weighted total + rank
    sensitivity.csv     default vs precision-heavy vs cost-heavy re-ranking
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Criteria and the three weighting schemes (each sums to 1.0).
# --------------------------------------------------------------------------
CRITERIA = ["stiffness", "precision", "cost", "buildability", "thermal", "sourcing"]

WEIGHTS = {
    # Task default weights.
    "default": {"stiffness": 0.22, "precision": 0.22, "cost": 0.15,
                "buildability": 0.15, "thermal": 0.10, "sourcing": 0.16},
    # Precision-heavy: the sub-arcsec imaging mission dominates.
    "precision": {"stiffness": 0.20, "precision": 0.40, "cost": 0.10,
                  "buildability": 0.10, "thermal": 0.08, "sourcing": 0.12},
    # Cost-heavy: amateur / grant-limited build, minimise spend and sourcing risk.
    "cost": {"stiffness": 0.12, "precision": 0.10, "cost": 0.35,
             "buildability": 0.15, "thermal": 0.08, "sourcing": 0.20},
}
for name, w in WEIGHTS.items():
    assert abs(sum(w.values()) - 1.0) < 1e-9, (name, sum(w.values()))


@dataclass
class Option:
    name: str
    role: str            # baseline | alternative | bold
    desc: str            # one-line morphological description
    proof: str           # grounding citation from the Phase-C proofs
    scores: dict         # criterion -> 1..5
    gate_fail: bool = False   # disqualified: fails a hard requirement


@dataclass
class Subsystem:
    key: str
    title: str
    options: list = field(default_factory=list)


def S(stiffness, precision, cost, build, thermal, sourcing):
    return {"stiffness": stiffness, "precision": precision, "cost": cost,
            "buildability": build, "thermal": thermal, "sourcing": sourcing}


# ==========================================================================
# The morphological matrix (Zwicky box): 7 subsystems, each baseline + alts.
# Scores are engineering judgement anchored to the proof verdicts cited.
# ==========================================================================
SUBSYSTEMS: list[Subsystem] = [
    Subsystem("ota", "Optical tube assembly", [
        Option("MN78 f/8 (14 kg)", "baseline",
               "180 mm Mak-Newt, 1440 mm tube, 0.134 obstruction; doc-'selected'",
               "stiffness: MN78 is the tube the FAIL is computed on (43.3\" vs 5\")",
               S(2, 4, 3, 3, 4, 2)),
        Option("MN76 f/6 (9 kg)", "alternative",
               "178 mm Mak-Newt, 700 mm tube, 0.25 obstruction; lighter/shorter",
               "torque: lighter tube => lower RA torque; stiffness: shorter CG lever",
               S(4, 3, 3, 4, 3, 2)),
        Option("MN86 f/6 (8-inch)", "alternative",
               "203 mm Mak-Newt; more aperture, heavier and longer tube",
               "stiffness/torque: heaviest tube => worst mount loading",
               S(1, 4, 2, 2, 3, 1)),
        Option("APM-LZOS apo triplet", "bold",
               "refractor, zero obstruction, premium optics; long/heavy/costly",
               "thermal: glass soak vs metal-tube focus walk; precision: no obstruction",
               S(2, 5, 1, 3, 3, 2)),
        Option("ES-MN152 f/4.8", "alternative",
               "152 mm Mak-Newt, in-production mass-market; cheap/light",
               "torque/stiffness: lightest, in-production; lowest sourcing risk",
               S(4, 3, 5, 4, 3, 5)),
    ]),
    Subsystem("topology", "Mount topology", [
        Option("Counterweighted GEM", "baseline",
               "German equatorial + 12.5 kg counterweight on 457 mm shaft",
               "balance: 12.5 kg balances 18 kg payload at r=288 mm (fit 1.59)",
               S(3, 3, 3, 4, 3, 4)),
        Option("Counterweight-FREE GEM", "bold",
               "delete the shaft+weights; harmonic back-drive holds the imbalance",
               "torque: RA SF 2.5 PASS; balance: deletes 15.4 kg + 29% RA inertia",
               S(3, 4, 4, 4, 3, 4)),
        Option("Fork + field derotator", "alternative",
               "symmetric fork, no meridian flip; derotator adds a rotation axis",
               "precision: derotator injects a continuous field-rotation error term",
               S(3, 2, 2, 2, 3, 2)),
    ]),
    Subsystem("drive", "Axis drive train", [
        Option("NEMA17 + 27:1 + harmonic", "baseline",
               "stepper + planetary + CSF harmonic (100:1 RA / 80:1 DEC)",
               "torque: PASS; encoder: on-axis ring moots upstream planetary PE",
               S(3, 2, 4, 4, 3, 4)),
        Option("Direct-to-harmonic", "alternative",
               "delete planetary; larger motor straight into the harmonic",
               "torque: 0.45 Nm x100 = 45 Nm ~ 49.9 Nm need => bigger motor required",
               S(3, 3, 3, 3, 3, 4)),
        Option("Torque-motor direct drive", "bold",
               "frameless torque motor on-axis, zero gear PE; needs on-axis encoder",
               "encoder: only DD+ring reaches seeing-limited; power: holding-heat cost",
               S(3, 5, 1, 2, 2, 2)),
    ]),
    Subsystem("encoder", "Feedback / encoder chain", [
        Option("AMT103 motor + AS5600 axis", "baseline",
               "fine motor encoder + 12-bit on-axis chip (homing-grade)",
               "encoder: 5.02\" RMS FAILS the 1.0\" target => DISQUALIFIED",
               S(3, 1, 5, 4, 3, 5), gate_fail=True),
        Option("On-axis high-res absolute ring", "bold",
               "Renishaw RESA-class absolute ring, sub-arcsec LSB, on the axis",
               "encoder: 0.54\" RMS => MEETS sub-arcsec (only option that does)",
               S(3, 5, 1, 2, 3, 2)),
        Option("Hybrid (motor + on-axis absolute)", "alternative",
               "motor encoder for velocity + on-axis absolute for position correction",
               "encoder: on-axis correction closes the PE+flexure gap the motor can't see",
               S(3, 4, 2, 3, 3, 3)),
    ]),
    Subsystem("pier", "Pier / foundation", [
        Option("Concrete Sonotube", "baseline",
               "12-inch x 36-inch concrete pier on a 36-inch embedment",
               "pier: governing SF 6.8 PASS, f_n 152 Hz (SF 15)",
               S(4, 3, 5, 4, 4, 5)),
        Option("Isolated pier-in-pier", "bold",
               "inner OTA pier isolated from the building slab / enclosure floor",
               "pier: core stiffness unchanged; isolates roof-drive/footfall vibration",
               S(4, 4, 3, 3, 4, 4)),
        Option("Steel-concrete hybrid", "alternative",
               "steel column on a concrete footing; faster to erect",
               "pier: slender steel column => lower f_n; thermal bending of the column",
               S(3, 3, 3, 3, 2, 3)),
    ]),
    Subsystem("enclosure", "Enclosure", [
        Option("Roll-off roof", "baseline",
               "flat roll-off roof, garage-door-class drive",
               "enclosure: drive SF 2.1 PASS; wind: uplift SF 0.19 => anchors mandatory",
               S(3, 3, 5, 5, 3, 5)),
        Option("Clamshell dome", "alternative",
               "rotating split-shell dome; better wind screen, worse flush",
               "thermal: enclosed dome traps the DGX 14 K heat dump",
               S(3, 3, 2, 2, 2, 2)),
        Option("Roll-off + active thermal", "bold",
               "roll-off base + insulation + forced ventilation + day pre-cooling",
               "thermal: FAIL focus-walk remedy; power: exhausts DGX 14 K enclosure dump",
               S(3, 4, 4, 4, 5, 4)),
    ]),
    Subsystem("frame", "Mount-head frame / housings", [
        Option("6061-T6 CNC plates", "baseline",
               "bolt-together CNC aluminium housings (E=68.9 GPa)",
               "stiffness: plates are NOT the governing compliance (bearings are)",
               S(3, 3, 4, 4, 4, 4)),
        Option("Steel weldment", "alternative",
               "welded steel frame, ~3x modulus; heavier, weld distortion",
               "stiffness: 3x E cuts only the small beam term; bearings still govern",
               S(4, 3, 3, 2, 3, 3)),
        Option("Cast housings", "bold",
               "cast iron/Al monolithic housings; best damping, integral bearing seats",
               "stiffness: integral large-span AC bearing seats attack the FAIL; foundry risk",
               S(4, 4, 2, 1, 3, 2)),
    ]),
]


# ==========================================================================
# Scoring
# ==========================================================================
def weighted(scores: dict, weights: dict) -> float:
    return round(sum(weights[c] * scores[c] for c in CRITERIA), 4)


def ranked(sub: Subsystem, weights: dict, apply_gate: bool = True):
    """Return options sorted best-first under a weighting.

    Gate-failed options are pushed below all qualifying options (they cannot be
    selected) but keep their raw weighted score for transparency.
    """
    def keyfn(o: Option):
        return (0 if (apply_gate and o.gate_fail) else 1, weighted(o.scores, weights))
    return sorted(sub.options, key=keyfn, reverse=True)


def selected(sub: Subsystem, weights: dict) -> Option:
    return ranked(sub, weights, apply_gate=True)[0]


# ==========================================================================
# CSV emitters
# ==========================================================================
HERE = os.path.dirname(os.path.abspath(__file__))


def write_morphological():
    path = os.path.join(HERE, "morphological.csv")
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["subsystem", "option", "role", "description", "proof_citation"])
        for sub in SUBSYSTEMS:
            for o in sub.options:
                w.writerow([sub.title, o.name, o.role, o.desc, o.proof])
    return path


def write_pugh():
    path = os.path.join(HERE, "pugh_scores.csv")
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["subsystem", "option", "role"] + CRITERIA +
                   ["weighted_default", "rank_default", "gate", "selected"])
        for sub in SUBSYSTEMS:
            order = ranked(sub, WEIGHTS["default"], apply_gate=True)
            rank_of = {id(o): i + 1 for i, o in enumerate(order)}
            sel = selected(sub, WEIGHTS["default"])
            for o in sub.options:
                w.writerow(
                    [sub.title, o.name, o.role] +
                    [o.scores[c] for c in CRITERIA] +
                    [weighted(o.scores, WEIGHTS["default"]),
                     rank_of[id(o)],
                     "DISQUALIFIED" if o.gate_fail else "ok",
                     "SELECTED" if o is sel else ""]
                )
    return path


def write_sensitivity():
    path = os.path.join(HERE, "sensitivity.csv")
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["subsystem", "option", "role",
                    "w_default", "w_precision", "w_cost",
                    "win_default", "win_precision", "win_cost"])
        for sub in SUBSYSTEMS:
            sel_d = selected(sub, WEIGHTS["default"])
            sel_p = selected(sub, WEIGHTS["precision"])
            sel_c = selected(sub, WEIGHTS["cost"])
            for o in sub.options:
                w.writerow([
                    sub.title, o.name, o.role,
                    weighted(o.scores, WEIGHTS["default"]),
                    weighted(o.scores, WEIGHTS["precision"]),
                    weighted(o.scores, WEIGHTS["cost"]),
                    "*" if o is sel_d else "",
                    "*" if o is sel_p else "",
                    "*" if o is sel_c else "",
                ])
    return path


def summary() -> str:
    lines = []
    for sub in SUBSYSTEMS:
        sel_d = selected(sub, WEIGHTS["default"])
        sel_p = selected(sub, WEIGHTS["precision"])
        sel_c = selected(sub, WEIGHTS["cost"])
        changed = "STABLE" if (sel_d is sel_p is sel_c) else "CHANGES"
        lines.append(
            f"{sub.title:32s} default={sel_d.name:34s} "
            f"prec={sel_p.name:34s} cost={sel_c.name:34s} [{changed}]"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    p1 = write_morphological()
    p2 = write_pugh()
    p3 = write_sensitivity()
    print("wrote:", p1, p2, p3, sep="\n  ")
    print("\nPer-subsystem winners under each weighting:")
    print(summary())
