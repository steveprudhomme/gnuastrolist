# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Désignations réelles, composants partagés, génération et rapports hors ligne."""

import csv
import gzip
from pathlib import Path

import pytest
from pypdf import PdfReader

from gnu_astrolist.catalog import load_bayer_catalog, load_flamsteed_catalog
from gnu_astrolist.cli import main
from gnu_astrolist.models import VisibilityResult
from gnu_astrolist.seestar import annotate_results, object_keys, scan_seestar
from gnu_astrolist.selection import load_catalog_selection
from gnu_astrolist.stellar_names import normalize_stellar_name


def test_pdf_fonts_cover_greek_and_component_indices():
    from reportlab.pdfbase import pdfmetrics

    from gnu_astrolist.pdf_output import _register_fonts
    from gnu_astrolist.stellar_names import GREEK

    _register_fonts()
    for name in ("AstrolistSans", "AstrolistSansBold"):
        cmap = pdfmetrics.getFont(name).face.charToGlyph
        assert all(ord(char) in cmap for char in "".join(GREEK.values()) + "⁰¹²³⁴⁵⁶⁷⁸⁹")


def test_real_designations_coordinates_and_provenance():
    bayer, flam = load_bayer_catalog(), load_flamsteed_catalog()
    assert len(bayer) == 1537 and len(flam) == 2737
    assert len({s.hyg_id for s in bayer}) == len(bayer)
    assert len({s.name for s in bayer}) == len(bayer)
    assert len({s.name for s in flam}) == len(flam)
    assert all(0 <= s.ra_deg < 360 and -90 <= s.dec_deg <= 90 for s in (*bayer, *flam))
    vega = next(s for s in bayer if s.common_name == "Vega")
    assert vega.name == "α Lyr" and vega.flamsteed_name == "3 Lyr"
    assert vega.hyg_id == 90979
    assert vega.ra_deg == pytest.approx(18.61564 * 15)
    assert vega.magnitude_v == 0.03 and vega.magnitude_source == "HYG 4.1"
    sirius = next(s for s in bayer if s.common_name == "Sirius")
    assert sirius.name == "α CMa" and sirius.flamsteed_name == "9 CMa"
    assert sirius.magnitude_v == -1.44


def test_union_uses_source_identity_and_preserves_components():
    stars, selection = load_catalog_selection(["bayer", "flamsteed", "bayer"])
    reverse, _ = load_catalog_selection(["flamsteed", "bayer"])
    assert selection.kinds == ("bayer", "flamsteed")
    assert selection.limits == (None, None)
    assert stars == reverse and len(stars) == 3321
    vega = next(s for s in stars if s.common_name == "Vega")
    assert vega.name == "α Lyr" and vega.aliases == ("3 Lyr",)
    castor = [s for s in stars if s.bayer_name == "α Gem"]
    assert len(castor) == 2 and len({s.hyg_id for s in castor}) == 2
    assert all("[HYG " in s.name and "α Gem" in s.ambiguous_names for s in castor)
    limited, _ = load_catalog_selection(["bayer", "flamsteed"], max_magnitude=0)
    assert limited and all(s.magnitude_v <= 0 for s in limited)
    combined, limits = load_catalog_selection(["variable_stars", "bayer", "ngc"], max_magnitude=-20)
    assert limits.limits == (-20, -20, -20) and not combined


@pytest.mark.parametrize("value", ["Alp Lyr", "alpha Lyr", "α Lyr", "ALF lyr"])
def test_bayer_explicit_spellings(value):
    assert normalize_stellar_name(value) == normalize_stellar_name("α Lyr")
    assert normalize_stellar_name("Alp-1 Lyr") != normalize_stellar_name("α Lyr")
    assert normalize_stellar_name("α¹ CVn") == normalize_stellar_name("alpha-1 CVn")
    assert normalize_stellar_name("3 Lyr") != normalize_stellar_name("30 Lyr")


def test_seestar_shared_names_are_ambiguous_but_source_ids_are_specific(tmp_path):
    file = tmp_path / "Stacked_20_66 Gem_10.0s_LP_20261117-210000.fit"
    file.write_bytes(b"Synthetic acquisition")
    castor = [s for s in load_bayer_catalog() if s.bayer_name == "α Gem"]
    results = [VisibilityResult(s, 30, 40, 90, 100) for s in castor]
    checked = annotate_results(results, scan_seestar(tmp_path))
    assert all(r.seestar_status == "Indéterminé (nom partagé)" for r in checked)
    (tmp_path / f"Stacked_20_HYG {castor[0].hyg_id}_10.0s_LP_20261117-210000.fit").write_bytes(
        b"Test"
    )
    checked = annotate_results(results, scan_seestar(tmp_path))
    assert checked[0].seestar_status == "Fait (empilé)"
    assert checked[1].seestar_status == "Indéterminé (nom partagé)"
    assert object_keys(castor[0]) != object_keys(castor[1])


@pytest.mark.parametrize("kinds", [("bayer",), ("flamsteed",), ("bayer", "flamsteed")])
def test_cli_reports_and_seestar(tmp_path, capsys, kinds):
    root = tmp_path / "MyWorks"
    root.mkdir()
    (root / "Stacked_20_Alp Lyr_10.0s_LP_20261117-210000.fit").write_bytes(b"Synthetic")
    txt, pdf = tmp_path / "stellar.txt", tmp_path / "stellar.pdf"
    assert (
        main(
            [
                "--date",
                "2026-11-17",
                "--time-range",
                "21:00-22:00",
                "--timezone",
                "America/Toronto",
                "--lat",
                "45.57",
                "--lon",
                "-73.68",
                "--az-min",
                "0",
                "--az-max",
                "360",
                "--min-altitude",
                "20",
                "--objects",
                *kinds,
                "--offline",
                "--limit",
                "3",
                "--details",
                "--seestar-path",
                str(root),
                "--output-txt",
                str(txt),
                "--output-pdf",
                str(pdf),
            ]
        )
        == 0
    )
    report = capsys.readouterr().out
    assert txt.read_text(encoding="utf-8") == report
    for text in (report, "\n".join(p.extract_text() for p in PdfReader(pdf).pages)):
        text = " ".join(text.split())
        assert "HYG 4.1" in text and "Fait (empilé)" in text
        assert "priorité SIMBAD" not in text
        if "bayer" in kinds:
            assert "α Lyr" in text
        if "flamsteed" in kinds:
            assert "3 Lyr" in text
    assert len(list(root.iterdir())) == 1


def test_builder_reproducible_ambiguous_names_missing_v_and_bad_hash(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    from build_stellar_catalogs import build

    source = tmp_path / "hyg.csv"
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["id", "bayer", "flam", "con", "ra", "dec", "mag", "proper"])
        writer.writerows(
            [
                [1, "Alp", "3", "Lyr", 1, 10, 1, "Synthetic A"],
                [2, "Alp", "3", "Lyr", 2, 11, 2, "Synthetic B"],
                [3, "Bet-1", "", "Ori", 3, 12, "", ""],
            ]
        )
    result = build(source, tmp_path, expected_sha256=None)
    assert result["bayer"] == 3 and result["flamsteed"] == 2 and result["union"] == 3
    first = (tmp_path / "bayer.csv.gz").read_bytes()
    build(source, tmp_path, expected_sha256=None)
    assert (tmp_path / "bayer.csv.gz").read_bytes() == first
    with gzip.open(tmp_path / "bayer.csv.gz", "rt", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["ra_deg"] == "15.00000000" and "[HYG 1]" in rows[0]["name"]
    assert rows[-1]["magnitude_v"] == "" and rows[-1]["bayer_name"] == "β¹ Ori"
    with pytest.raises(ValueError, match="Empreinte"):
        build(source, tmp_path, expected_sha256="invalid")
    assert (tmp_path / "bayer.csv.gz").read_bytes() == first
