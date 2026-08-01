"""
Catalog identity regression tests (fix S2-4).

(a) The Cor Caroli (Alpha CVn) entry was mislabeled "Alioth" and carried
    Alkaid's coordinates.
(b) The Hipparcos id "HIP 677" was reused by two different stars (Caph and
    Eta Cassiopeiae), so loading the catalog into the id-unique store silently
    overwrote one of them.
"""

import pytest

from services.catalog.catalog_data import get_named_stars, get_double_stars


def _all_stars():
    return list(get_named_stars()) + list(get_double_stars())


# The same physical star may legitimately appear in both the named-star and
# double-star lists. When it does under an identical name it is harmless; the
# only pre-existing case where it appears under two names is Alpha Centauri /
# Rigil Kentaurus, which is genuinely one object. That known pair is not a
# collision and is excluded from the distinct-star guard below.
_KNOWN_SAME_STAR_ALIASES = {
    "HIP 71683": {"Alpha Centauri", "Rigil Kentaurus"},
}


def test_no_catalog_id_shared_by_distinct_stars():
    """A given catalog_id must never map to two genuinely different stars.

    This is the S2-4 regression guard: before the fix, "HIP 677" was shared by
    Caph and Eta Cassiopeiae (two different stars), so loading the catalog into
    the id-unique store silently dropped one of them.
    """
    by_id = {}
    for obj in _all_stars():
        by_id.setdefault(obj.catalog_id, set()).add(obj.name)

    conflicts = {
        cid: names
        for cid, names in by_id.items()
        if len(names) > 1 and names != _KNOWN_SAME_STAR_ALIASES.get(cid)
    }
    assert not conflicts, f"catalog_id reused by distinct stars: {conflicts}"


def test_caph_and_eta_cassiopeiae_are_distinct_rows():
    stars = _all_stars()
    caph = [o for o in stars if o.name == "Caph"]
    eta_cas = [o for o in stars if o.name == "Eta Cassiopeiae"]

    assert len(caph) == 1
    assert len(eta_cas) == 1
    assert caph[0].catalog_id == "HIP 746"
    assert eta_cas[0].catalog_id == "HIP 3821"
    assert caph[0].catalog_id != eta_cas[0].catalog_id


def test_alpheratz_id():
    stars = _all_stars()
    alpheratz = [o for o in stars if o.name == "Alpheratz"]
    assert len(alpheratz) == 1
    assert alpheratz[0].catalog_id == "HIP 677"


def test_cor_caroli_resolves_correctly():
    named = list(get_named_stars())
    cor_caroli = [o for o in named if o.name == "Cor Caroli"]

    assert len(cor_caroli) == 1
    obj = cor_caroli[0]
    assert obj.catalog_id == "HIP 63125"
    assert obj.dec_degrees == pytest.approx(38.3184, abs=1e-3)
    assert obj.ra_hours == pytest.approx(12.9338, abs=1e-3)
    assert "COR CAROLI" in obj.aliases
