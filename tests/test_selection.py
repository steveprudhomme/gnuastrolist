# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sélection multiple, identité explicite, filtres et rapports publics."""

from dataclasses import replace

import pytest
from pypdf import PdfReader

from gnu_astrolist.catalog import load_messier_catalog
from gnu_astrolist.cli import build_parser, main
from gnu_astrolist.models import DeepSkyObject, VariableStar
from gnu_astrolist.selection import load_catalog_selection, normalize_catalogs


def test_normalization_and_repeated_arguments():
    required = [
        "--date",
        "2026-08-15",
        "--time-range",
        "21:00-22:00",
        "--lat",
        "45",
        "--lon",
        "0",
        "--az-min",
        "0",
        "--az-max",
        "360",
        "--min-altitude",
        "20",
    ]
    args = build_parser().parse_args(
        required
        + [
            "--objects",
            "messier",
            "ngc",
            "--objects",
            "messier_objects",
            "caldwell",
        ]
    )
    assert normalize_catalogs(args.objects) == ("messier", "ngc", "caldwell")
    assert (
        load_catalog_selection(["messier"])[0]
        == load_catalog_selection(["messier", "messier_objects", "messier"])[0]
    )
    with pytest.raises(ValueError, match="Au moins"):
        normalize_catalogs([])
    with pytest.raises(SystemExit):
        build_parser().parse_args(required + ["--objects", "messier", "inconnu"])


def test_real_overlap_preserves_priority_aliases_and_components():
    objects, _ = load_catalog_selection(["ngc", "caldwell", "messier"])
    reverse, _ = load_catalog_selection(["messier", "caldwell", "ngc"])
    assert objects == reverse
    by_name = {obj.name: obj for obj in objects}
    m31 = by_name["M31"]
    original = next(obj for obj in load_messier_catalog() if obj.name == "M31")
    assert replace(m31, aliases=()) == original
    assert m31.aliases == ("NGC224",)
    assert "NGC224" not in by_name
    assert by_name["C1"].aliases == ("NGC188",)
    assert all(name in by_name for name in ("C14", "NGC869", "NGC884"))
    assert len(objects) < 8098 + 110 + 109


def test_mixed_filters_keep_variable_default_and_apply_overrides():
    default, selection = load_catalog_selection(["variable_stars", "ngc"])
    assert selection.limits == (8, None)
    assert all(obj.mag_max <= 8 for obj in default if isinstance(obj, VariableStar))
    assert any(obj.magnitude_v is None for obj in default if isinstance(obj, DeepSkyObject))
    assert any(
        obj.magnitude_v > 8
        for obj in default
        if isinstance(obj, DeepSkyObject) and obj.magnitude_v is not None
    )
    unrestricted, selection = load_catalog_selection(["variable_stars", "ngc"], all_magnitudes=True)
    assert sum(isinstance(obj, VariableStar) for obj in unrestricted) == 21212
    assert selection.limits == (None, None)
    limited, selection = load_catalog_selection(["variable_stars", "ngc"], max_magnitude=5)
    assert selection.limits == (5, 5)
    assert all(obj.magnitude_v is not None and obj.magnitude_v <= 5 for obj in limited)


@pytest.mark.parametrize("primary_v", [None, 9.0])
def test_priority_is_resolved_before_magnitude_filter(monkeypatch, primary_v):
    reference = load_messier_catalog()[0]
    primary = replace(
        reference, name="Primary", catalog_designation="NGC 0001", magnitude_v=primary_v
    )
    secondary = replace(reference, name="Secondary", catalog_designation="NGC1", magnitude_v=1)
    monkeypatch.setattr("gnu_astrolist.selection.load_messier_catalog", lambda: (primary,))
    monkeypatch.setattr("gnu_astrolist.selection.load_ngc_catalog", lambda: (secondary,))
    assert load_catalog_selection(["ngc", "messier"], max_magnitude=5)[0] == []
    objects, _ = load_catalog_selection(["ngc", "messier"], all_magnitudes=True)
    assert len(objects) == 1 and objects[0].magnitude_v == primary_v
    assert objects[0].aliases == ("Secondary",)


def test_positions_and_empty_identifiers_do_not_prove_identity(monkeypatch):
    reference = load_messier_catalog()[0]
    a = replace(reference, name="A", catalog_designation="NGC1A")
    b = replace(reference, name="B", catalog_designation="NGC1B")
    empty = replace(reference, name="Unknown", catalog_designation="")
    monkeypatch.setattr("gnu_astrolist.selection.load_messier_catalog", lambda: (a, empty))
    monkeypatch.setattr("gnu_astrolist.selection.load_ngc_catalog", lambda: (b, empty))
    objects, _ = load_catalog_selection(["messier", "ngc"])
    assert len(objects) == 4
    assert all(not obj.aliases for obj in objects)


@pytest.mark.parametrize("threshold", ["5", "-20"])
def test_multiple_catalogs_cli_and_exports(tmp_path, capsys, monkeypatch, threshold):
    def forbidden(*args, **kwargs):
        raise AssertionError("Connexion interdite en mode hors ligne")

    monkeypatch.setattr("gnu_astrolist.weather.urlopen", forbidden)
    txt, pdf = tmp_path / "combined.txt", tmp_path / "combined.pdf"
    assert (
        main(
            [
                "--date",
                "2026-08-15",
                "--time-range",
                "21:00-22:00",
                "--lat",
                "45",
                "--lon",
                "0",
                "--az-min",
                "0",
                "--az-max",
                "360",
                "--min-altitude",
                "20",
                "--offline",
                "--objects",
                "messier",
                "ngc",
                "--objects",
                "messier_objects",
                "--max-magnitude",
                threshold,
                "--limit",
                "3",
                "--details",
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
        assert "Objets Messier" in text and "Objets NGC" in text
        assert "priorité Messier puis Caldwell puis NGC" in text
        if threshold == "5":
            assert "M31 / NGC224" in text
            assert "NGC869" in text
        else:
            assert "Aucun objet" in text


@pytest.mark.parametrize("all_magnitudes", [False, True])
def test_mixed_variable_reports_show_effective_limits(tmp_path, capsys, all_magnitudes):
    pdf = tmp_path / "mixed.pdf"
    args = [
        "--date",
        "2026-08-15",
        "--time-range",
        "21:00-22:00",
        "--lat",
        "45",
        "--lon",
        "0",
        "--az-min",
        "0",
        "--az-max",
        "360",
        "--min-altitude",
        "20",
        "--offline",
        "--objects",
        "variable_stars",
        "ngc",
        "--limit",
        "1",
        "--output-pdf",
        str(pdf),
    ]
    if all_magnitudes:
        args += ["--all-magnitudes"]
    assert main(args) == 0
    report = capsys.readouterr().out
    assert "Mag. V (max si GCVS)" in report
    pdf_text = "\n".join(p.extract_text() for p in PdfReader(pdf).pages)
    for text in (report, pdf_text):
        assert "GCVS (maximum publié)" in text
        assert "NGC : aucune limite" in text
        assert "Les magnitudes GCVS sont les maxima" in text
        if all_magnitudes:
            assert "GCVS (maximum publié) : aucune limite" in text
        else:
            assert "≤ 8" in text
