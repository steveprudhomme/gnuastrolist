# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Contrat NGC, génération déterministe et intégration des rapports hors ligne."""

import csv
import gzip
import math
from pathlib import Path

import pytest
from pypdf import PdfReader

from gnu_astrolist.catalog import filter_by_magnitude, load_ngc_catalog
from gnu_astrolist.cli import main


def test_embedded_ngc_scope_and_reference_objects():
    objects = load_ngc_catalog()
    by_name = {obj.name: obj for obj in objects}
    assert len(objects) == len(by_name) == 8098
    assert all(obj.name.startswith("NGC") for obj in objects)
    assert all(obj.object_type not in {"Dup", "NonEx"} for obj in objects)
    assert all(0 <= obj.ra_deg < 360 and -90 <= obj.dec_deg <= 90 for obj in objects)
    assert sum(obj.magnitude_v is None for obj in objects) == 4592
    assert all(obj.magnitude_v is None or math.isfinite(obj.magnitude_v) for obj in objects)
    assert by_name["NGC224"].catalog_designation == "NGC0224"
    assert by_name["NGC224"].magnitude_v == 3.44
    assert by_name["NGC224"].ra_deg == pytest.approx(10.68479167)
    assert by_name["NGC224"].magnitude_source == "OpenNGC"
    assert by_name["NGC224"].magnitude_reference.startswith("doi:")
    assert by_name["NGC224"].magnitude_retrieved_on == "2026-11-16"
    assert by_name["NGC1976"].object_type == "Cl+N"
    assert "NGC61A" in by_name and "NGC61B" in by_name
    assert len(filter_by_magnitude(objects, None)) == 8098
    assert all(
        obj.magnitude_v is not None and obj.magnitude_v <= 5
        for obj in filter_by_magnitude(objects, 5)
    )


@pytest.mark.parametrize("threshold", ["-20", "5"])
def test_ngc_cli_exports_and_no_network(tmp_path, capsys, monkeypatch, threshold):
    def forbidden(*args, **kwargs):
        raise AssertionError("Connexion réseau interdite en mode hors ligne")

    monkeypatch.setattr("gnu_astrolist.weather.urlopen", forbidden)
    txt, pdf = tmp_path / "ngc.txt", tmp_path / "ngc.pdf"
    assert (
        main(
            [
                "--date",
                "2026-08-15",
                "--time-range",
                "21:00-02:00",
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
                "ngc",
                "--offline",
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
    pdf_text = "\n".join(page.extract_text() for page in PdfReader(pdf).pages)
    for text in (report, pdf_text):
        assert "Objets NGC (OpenNGC)" in text
        assert "composants distincts inclus" in text
        assert "complément de magnitude V SIMBAD" not in text
        if threshold == "-20":
            assert "Aucun objet" in text
        else:
            assert "NGC869" in text
            assert "OpenNGC" in text


def test_generator_filters_scope_and_is_deterministic(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    from build_ngc_catalog import build

    source = tmp_path / "source.csv"
    fields = ["Name", "Type", "RA", "Dec", "Const", "MajAx", "MinAx", "V-Mag", "Common names"]
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(fields)
        for name, kind, v in [
            ("NGC0010", "G", "5"),
            ("NGC0002B", "G", ""),
            ("NGC0002A", "G", ""),
            ("IC0001", "G", "4"),
            ("NGC0003", "Dup", ""),
            ("NGC0004", "NonEx", ""),
        ]:
            writer.writerow([name, kind, "01:00:00", "-10:00:00", "Cet", "1", "", v, "Test"])
    output = tmp_path / "ngc.csv.gz"
    stats = build(source, output, "2000-01-01", expected_sha256=None)
    first = output.read_bytes()
    build(source, output, "2000-01-01", expected_sha256=None)
    assert output.read_bytes() == first
    assert stats["count"] == 3 and stats["excluded"] == 2
    with gzip.open(output, "rt", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["name"] for row in rows] == ["NGC2A", "NGC2B", "NGC10"]
    assert rows[0]["magnitude_v"] == "" and rows[0]["magnitude_source"] == ""
    assert rows[-1]["ra_deg"] == "15.00000000"
    with pytest.raises(ValueError, match="Empreinte"):
        build(source, output, "2000-01-01", expected_sha256="incorrect")
    assert output.read_bytes() == first
    with source.open("a", encoding="utf-8") as stream:
        stream.write("NGC0002A;G;01:00:00;-10:00:00;Cet;1;;;Test\n")
    with pytest.raises(ValueError, match="dupliqué"):
        build(source, output, "2000-01-01", expected_sha256=None)
