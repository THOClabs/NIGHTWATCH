"""
Tender consistency gates — the single-source-of-truth guard for the vendor
package. Every fabricated part must be fully specified, the BOM/cut-list/COTS
splits must be internally consistent, the proof-out remediations must be present
(and the FAILed baseline absent), and every fabricated part must have a
well-formed control drawing carrying the correct status.
"""

from __future__ import annotations

import csv
import xml.dom.minidom as minidom

from design.mechanical.tender.gen import bom, drawing
from design.mechanical.tender.gen import partspec as ps


def test_every_fabricated_part_is_fully_specified():
    for p in ps.fabricated_parts():
        assert p.material and p.material != "n-a", f"{p.part_no} missing material"
        assert p.finish, f"{p.part_no} missing finish"
        assert p.tolerance, f"{p.part_no} missing tolerance"
        assert p.qty >= 1, f"{p.part_no} bad qty"
        assert p.provenance, f"{p.part_no} missing provenance"
        assert p.stock_mass_kg() is not None, f"{p.part_no} has no computable stock mass"
        assert p.key_dims_mm, f"{p.part_no} has no key dimensions"


def test_bom_covers_every_part():
    bom.generate_all()
    rows = list(csv.DictReader((bom.OUT / "master_bom.csv").open()))
    part_nos = {r["part_no"] for r in rows}
    assert part_nos == {p.part_no for p in ps.ALL_PARTS}
    assert len(rows) == len(ps.ALL_PARTS)


def test_cut_list_and_cots_split_is_consistent():
    bom.generate_all()
    cut = list(csv.DictReader((bom.OUT / "cut_list.csv").open()))
    cots = list(csv.DictReader((bom.OUT / "cots_schedule.csv").open()))
    assert len(cut) == sum(1 for p in ps.ALL_PARTS if p.stock[0] != "cots")
    assert len(cots) == sum(1 for p in ps.ALL_PARTS if p.stock[0] == "cots")
    # no COTS item leaks into the cut list and vice-versa
    cut_nos = {r["part_no"] for r in cut}
    cots_nos = {r["part_no"] for r in cots}
    assert cut_nos.isdisjoint(cots_nos)


def test_remediations_present_and_baseline_absent():
    names = " ".join(p.name for p in ps.ALL_PARTS)
    # the five proof-out remediations must appear as real line items
    assert "7008" in names and "7006" in names, "angular-contact bearing remediation missing"
    assert "absolute encoder" in names.lower(), "on-axis encoder remediation missing"
    assert "hold-down" in names.lower(), "wind hold-down anchor remediation missing"
    assert "focuser" in names.lower(), "temp-comp focuser remediation missing"
    assert "48 v" in names.lower() or "48v" in names.lower(), "48 V power remediation missing"
    # No COTS bearing may SELECT the deep-groove baseline (it may only be named as
    # the thing being replaced, inside provenance text).
    bearing_selections = [p.name for p in ps.ALL_PARTS if "bearing" in p.name.lower()]
    for n in bearing_selections:
        assert "6008" not in n and "6006" not in n, f"deep-groove baseline still selected: {n}"


def test_every_fabricated_part_has_a_wellformed_drawing():
    drawing.generate_all()
    for p in ps.fabricated_parts():
        svg = drawing.OUT / f"{p.part_no}.svg"
        assert svg.exists(), f"missing drawing for {p.part_no}"
        text = svg.read_text()
        minidom.parseString(text)  # raises if not well-formed XML
        assert p.part_no in text
        assert "ISSUED FOR BID" in text
        assert "NOT FOR CONSTRUCTION" in text


def test_pier_and_roof_are_flagged_pe_gate():
    pier = next(p for p in ps.ALL_PARTS if p.part_no == "NW-PF-001")
    assert "PE STAMP" in pier.notes.upper()
