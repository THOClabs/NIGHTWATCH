"""
BOM + cut-list generator — turns the parts registry into the vendor-facing
material documents. Emits CSV (which the XLSX step renders to Excel):

  bom/master_bom.csv   — every line item, all packages
  bom/cut_list.csv     — fabricated stock to order & cut (dual inch + mm)
  bom/cots_schedule.csv— purchased (off-the-shelf) items

Dimensions are dual-unit (mm primary, inch in brackets) so a US shop can quote
directly while the SI design stays traceable. Masses are STOCK mass (what you
order), computed from stock volume x material density.
"""

from __future__ import annotations

import csv
import pathlib

from design.mechanical.calc import units as u
from design.mechanical.tender.gen import partspec as ps

OUT = pathlib.Path(__file__).resolve().parents[1] / "bom"
KERF_MM = 3.0  # ASSUMED saw/laser kerf allowance per cut


def _in(mm: float) -> float:
    return round(mm / 25.4, 3)


def _dual(mm: float) -> str:
    return f"{mm:.1f} mm ({_in(mm):.3f} in)"


def stock_description(p: ps.Part) -> str:
    kind = p.stock[0]
    if kind == "plate":
        _, L, W, T = p.stock
        return f"plate {_dual(L)} x {_dual(W)} x {_dual(T)}"
    if kind == "round":
        _, dia, length = p.stock
        return f"round bar Ø{_dual(dia)} x {_dual(length)}"
    if kind == "hss":
        _, o, wall, length = p.stock
        return f"HSS {_dual(o)} sq x {_dual(wall)} wall x {_dual(length)}"
    return "COTS"


def write_master_bom() -> pathlib.Path:
    path = OUT / "master_bom.csv"
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["part_no", "name", "package", "trade", "material", "process",
                    "finish", "qty", "stock_mass_kg", "drawing", "provenance"])
        for p in ps.ALL_PARTS:
            m = p.stock_mass_kg()
            w.writerow([p.part_no, p.name, p.package, ps.PACKAGES[p.package][1], p.material,
                        p.process, p.finish, p.qty, "" if m is None else f"{m:.2f}",
                        "Y" if p.drawing else "N", p.provenance])
    return path


def write_cut_list() -> pathlib.Path:
    path = OUT / "cut_list.csv"
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["part_no", "name", "package", "material", "stock_form",
                    "stock_size (mm / in)", "qty", "cut_allowance_mm", "stock_mass_kg", "finish", "notes"])
        for p in ps.ALL_PARTS:
            if p.stock[0] == "cots":
                continue
            m = p.stock_mass_kg()
            w.writerow([p.part_no, p.name, p.package, p.material, p.stock[0],
                        stock_description(p), p.qty, KERF_MM,
                        "" if m is None else f"{m:.2f}", p.finish, p.notes])
    return path


def write_cots_schedule() -> pathlib.Path:
    path = OUT / "cots_schedule.csv"
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["part_no", "name", "package", "supplier_class", "qty", "key_specs", "provenance", "notes"])
        for p in ps.ALL_PARTS:
            if p.stock[0] != "cots":
                continue
            specs = "; ".join(f"{k}={v}" for k, v in p.key_dims_mm.items())
            w.writerow([p.part_no, p.name, p.package, p.material, p.qty, specs, p.provenance, p.notes])
    return path


def totals() -> dict:
    fab_mass = sum((p.stock_mass_kg() or 0.0) for p in ps.ALL_PARTS if p.stock[0] != "cots")
    return {
        "line_items": len(ps.ALL_PARTS),
        "fabricated": sum(1 for p in ps.ALL_PARTS if p.stock[0] != "cots"),
        "cots": sum(1 for p in ps.ALL_PARTS if p.stock[0] == "cots"),
        "fab_stock_mass_kg": round(fab_mass, 1),
    }


def generate_all() -> list[pathlib.Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    return [write_master_bom(), write_cut_list(), write_cots_schedule()]


if __name__ == "__main__":
    for pth in generate_all():
        print("wrote", pth)
    print("totals:", totals())
