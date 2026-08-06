"""
Common result type for every budget module.

Each proof (`torque`, `stiffness`, ...) exposes ``evaluate() -> BudgetResult``.
The report is then a pure function of these results, and a test can regenerate
the report tables and diff them against the calculator so no hand-typed number
can drift from the computation.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class Verdict(enum.Enum):
    PASS = "PASS"
    MARGINAL = "MARGINAL"
    FAIL = "FAIL"

    @property
    def symbol(self) -> str:
        return {"PASS": "✅", "MARGINAL": "⚠️", "FAIL": "❌"}[self.value]


@dataclass(frozen=True)
class Line:
    """One computed quantity in a budget table."""
    label: str
    value: float
    unit: str
    note: str = ""

    def fmt(self, sig: int = 4) -> str:
        v = self.value
        if v == 0:
            s = "0"
        elif abs(v) >= 1e5 or (abs(v) < 1e-3 and v != 0):
            s = f"{v:.{sig - 1}e}"
        else:
            s = f"{v:.{sig}g}"
        return s


@dataclass
class BudgetResult:
    key: str                       # stable id, e.g. "torque"
    title: str
    verdict: Verdict
    headline: str                  # one-line human summary
    lines: list[Line] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    safety_factor: float | None = None
    target: str = ""               # the requirement being checked

    def add(self, label: str, value: float, unit: str, note: str = "") -> None:
        self.lines.append(Line(label, value, unit, note))

    def markdown_table(self) -> str:
        rows = ["| Quantity | Value | Unit | Note |", "|---|---:|---|---|"]
        for ln in self.lines:
            rows.append(f"| {ln.label} | {ln.fmt()} | {ln.unit} | {ln.note} |")
        return "\n".join(rows)

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "title": self.title,
            "verdict": self.verdict.value,
            "headline": self.headline,
            "safety_factor": None if self.safety_factor is None else round(self.safety_factor, 4),
            "target": self.target,
            "lines": [
                {"label": ln.label, "value": ln.value, "unit": ln.unit, "note": ln.note}
                for ln in self.lines
            ],
            "assumptions": list(self.assumptions),
        }


def verdict_from_sf(sf: float, pass_at: float = 2.0, marginal_at: float = 1.0) -> Verdict:
    """Standard mapping from a safety factor to a verdict."""
    if sf >= pass_at:
        return Verdict.PASS
    if sf >= marginal_at:
        return Verdict.MARGINAL
    return Verdict.FAIL
