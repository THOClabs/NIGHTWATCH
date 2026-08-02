"""
Single-source-of-truth guard: the committed MECHANICAL_DESIGN.md must equal what
the calculator generates right now. If a proof's number changes, the report must
be regenerated (python3 -m design.mechanical.calc.report) or this fails — so the
report can never silently disagree with the code the way the repo's docs do today.
"""

from design.mechanical.calc import report


def test_report_matches_calculator():
    generated = report.build_markdown()
    committed = report.OUT.read_text()
    assert generated == committed, (
        "MECHANICAL_DESIGN.md is stale — regenerate with "
        "`python3 -m design.mechanical.calc.report`."
    )


def test_every_proof_headline_present():
    """Each proof's computed headline must actually appear in the report."""
    md = report.OUT.read_text()
    for _num, mod in report.PROOFS:
        r = mod.evaluate()
        assert r.headline in md, f"{r.key} headline missing from report"


def test_verdict_counts_are_honest():
    """The at-a-glance summary must reflect the real verdict tally (6 PASS / 5 FAIL)."""
    from design.mechanical.calc.budget import Verdict
    results = [mod.evaluate() for _num, mod in report.PROOFS]
    passes = sum(1 for r in results if r.verdict is Verdict.PASS)
    fails = sum(1 for r in results if r.verdict is Verdict.FAIL)
    assert passes == 6 and fails == 5, f"verdict tally changed: {passes} PASS / {fails} FAIL"
    assert f"**{passes} PASS" in report.OUT.read_text()
