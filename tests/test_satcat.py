# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Identités orbitales et registre : données publiques ou explicitement synthétiques."""

import csv
import json
from dataclasses import replace

import pytest
from astropy.utils import iers
from pypdf import PdfReader

from gnu_astrolist.cli import main
from gnu_astrolist.models import FieldOfView
from gnu_astrolist.satcat import (
    annotate_space_catalog,
    load_satcat,
    load_space_bundle,
    load_unoosa_records,
    norad_number,
    normalize_cospar,
    parse_satcat,
    select_space_elements,
)
from gnu_astrolist.satellites import compute_satellite_visibility, load_satellite_elements
from gnu_astrolist.seestar import normalize_name, object_keys
from gnu_astrolist.time_utils import parse_observation_window

iers.conf.auto_download=False
iers.conf.auto_max_age=None
WINDOW = parse_observation_window("2026-11-17", "21:00-21:20", "America/Toronto")


def test_embedded_scope_and_immutable_identity():
    bundle = load_space_bundle()
    records = load_satcat()
    assert len(bundle["gp"]) == 737 and len(records) == 1873
    assert sum(r.object_type == "PAY" for r in records.values()) == 68
    assert sum(r.object_type == "R/B" for r in records.values()) == 90
    assert sum(r.object_type == "DEB" for r in records.values()) == 1715
    assert records[25544].cospar_id == "1998-067A"
    assert records[33768].cospar_id == "1993-036R"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1998067A", "1998-067A"),
        ("1998_067a", "1998-067A"),
        ("1998-067", None),
        ("1998-067I", None),
        ("1998-067O", None),
        ("1998-000A", None),
    ],
)
def test_cospar_normalization(value, expected):
    assert normalize_cospar(value) == expected


@pytest.mark.parametrize("value", [0, -1, 1.5, True, "A0001", "١٢٣", 1000000000])
def test_invalid_norad(value):
    with pytest.raises(ValueError):
        norad_number(value)


def test_extended_norad_and_bad_satcat_rows():
    row = load_space_bundle()["satcat"][0]
    assert next(iter(parse_satcat([{**row, "NORAD_CAT_ID": "123456789"}]))) == 123456789
    for data in (
        [],
        [row, row],
        [{**row, "OBJECT_ID": "not-cospar"}],
        [{**row, "OBJECT_TYPE": "GUESS"}],
        [{**row, "RCS": "nan"}],
        [{**row, "DECAY_DATE": "tomorrow"}],
        [{**row, "INCLINATION": "inf"}],
    ):
        with pytest.raises(ValueError):
            parse_satcat(data)


def test_metadata_selection_not_inferred_from_names():
    elements = load_satellite_elements()
    records = load_satcat()
    selected, skipped = select_space_elements(elements, records, ("debris",), WINDOW)
    assert selected and all(records[e.norad_id].object_type in {"R/B", "DEB"} for e in selected)
    assert skipped["type non sélectionné"] > 0
    item = next(e for e in elements if e.norad_id == 25544)
    record = records[item.norad_id]
    with pytest.raises(ValueError, match="Conflit COSPAR"):
        select_space_elements(
            (item,),
            {item.norad_id: replace(record, cospar_id="1998-067B")},
            ("satellites",),
            WINDOW,
        )
    assert select_space_elements((item,), {}, ("satellites",), WINDOW)[0] == ()
    for changed in (
        replace(record, decay_date="2026-11-16"),
        replace(record, orbit_center="SU"),
        replace(record, orbit_type="DOC"),
        replace(record, object_type="UNK"),
    ):
        assert (
            select_space_elements((item,), {item.norad_id: changed}, ("satellites",), WINDOW)[0]
            == ()
        )


def registry_row(**changes):
    return {
        "cospar_id": "1992-094A",
        "state_of_registry": "État synthétique",
        "registration_document": "Document synthétique",
        "source_url": "https://www.unoosa.org/oosa/en/spaceobjectregister/resources/index.html",
        "retrieved_on": "2026-11-17",
        "registration_date": "2026-11-16",
        "norad_id": "22286",
        **changes,
    }


def write_registry(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.parametrize(
    "change",
    [
        {"source_url": "https://example.com/"},
        {"cospar_id": "1992-094"},
        {"retrieved_on": "yesterday"},
        {"state_of_registry": ""},
        {"norad_id": "1.5"},
    ],
)
def test_invalid_unoosa_rows(tmp_path, change):
    source = tmp_path / "register.csv"
    write_registry(source, [registry_row(**change)])
    with pytest.raises(ValueError, match="UNOOSA"):
        load_unoosa_records(source)


def test_unoosa_never_proves_absence_and_rejects_conflicts(tmp_path):
    source = tmp_path / "register.csv"
    write_registry(source, [registry_row(), registry_row()])
    with pytest.raises(ValueError, match="dupliqué"):
        load_unoosa_records(source)
    write_registry(source, [registry_row()])
    registry = load_unoosa_records(source)
    elements = tuple(e for e in load_satellite_elements() if e.norad_id == 22286)
    results = compute_satellite_visibility(
        elements, WINDOW, 45.57, -73.68, 0, FieldOfView(180, 45, 360, 90)
    )
    assert results
    enriched = annotate_space_catalog(results, load_satcat(), registry)
    assert "État synthétique" in enriched[0].space_catalog_details
    absent = annotate_space_catalog(results, load_satcat(), ())
    assert "statut inconnu" in absent[0].space_catalog_details
    conflicting = (replace(registry[0], norad_id=99999),)
    with pytest.raises(ValueError, match="Conflit NORAD"):
        annotate_space_catalog(results, load_satcat(), conflicting)
    keys = object_keys(results[0].star)
    assert keys == {"NORAD22286", "1992-094A"}
    assert normalize_name("SATCAT 22286") in keys and normalize_name("COSPAR 1992_094A") in keys
    assert not keys & {"22286", "M22286", "COSMOS 2228"}


def arguments():
    return [
        "--date",
        "2026-11-17",
        "--time-range",
        "21:00-21:20",
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
        "10",
        "--objects",
        "satellites",
        "debris",
        "--offline",
    ]


def test_cli_reports_unoosa_and_seestar_read_only(tmp_path, capsys):
    bundle = load_space_bundle()
    numbers = {"22286", "33768"}
    gp = tmp_path / "gp.json"
    gp.write_text(
        json.dumps([r for r in bundle["gp"] if str(r["NORAD_CAT_ID"]) in numbers]), encoding="utf-8"
    )
    satcat = tmp_path / "satcat.json"
    satcat.write_text(
        json.dumps([r for r in bundle["satcat"] if str(r["NORAD_CAT_ID"]) in numbers]),
        encoding="utf-8",
    )
    registry = tmp_path / "unoosa.csv"
    write_registry(registry, [registry_row()])
    source = tmp_path / "MyWorks"
    source.mkdir()
    acquisition = source / "Stacked_20_NORAD22286_10.0s_LP_20261117.fit"
    acquisition.write_bytes(b"Synthetic, not a FITS image")
    before = {p: p.read_bytes() for p in (gp, satcat, registry, acquisition)}
    txt, pdf = tmp_path / "report.txt", tmp_path / "report.pdf"
    assert (
        main(
            arguments()
            + [
                "--satellite-elements-file",
                str(gp),
                "--satcat-file",
                str(satcat),
                "--unoosa-file",
                str(registry),
                "--seestar-path",
                str(source),
                "--output-txt",
                str(txt),
                "--output-pdf",
                str(pdf),
                "--details",
            ]
        )
        == 0
    )
    report = capsys.readouterr().out
    assert "NORAD 22286" in report and "1993-036R" in report and "Fait (empilé)" in report
    assert "État synthétique" in report and "non disponible" in report
    assert "Instant position (local)" in report and "pas 5 s" in report
    assert txt.read_text(encoding="utf-8").strip() == report.strip()
    extracted = "\n".join(page.extract_text() for page in PdfReader(pdf).pages)
    assert "NORAD 22286" in extracted and "État synthétique" in extracted and "SGP4" in extracted
    assert all(p.read_bytes() == content for p, content in before.items())
    assert list(source.iterdir()) == [acquisition]


def test_cli_unknown_magnitude_filter_and_missing_files(tmp_path, capsys):
    assert main(arguments() + ["--max-magnitude", "8"]) == 0
    assert "Aucun objet" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(arguments() + ["--satellite-elements-file", str(tmp_path / "missing.csv")])
    with pytest.raises(SystemExit):
        main(arguments() + ["--unoosa-file", str(tmp_path / "missing.csv")])
