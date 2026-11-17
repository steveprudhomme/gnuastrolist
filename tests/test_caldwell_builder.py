# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reconstruction déterministe et contrôle qualité sur des données synthétiques."""

import argparse
import csv
import gzip
from pathlib import Path

import pytest


@pytest.fixture
def builder_inputs(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    import build_caldwell_catalog as builder

    source = tmp_path / "source.csv"
    fields = ["Name", "Type", "RA", "Dec", "Const", "MajAx", "MinAx", "V-Mag", "Common names"]
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter=";")
        writer.writeheader()
        for name in builder.DESIGNATIONS:
            writer.writerow(
                dict(
                    zip(
                        fields,
                        [name, "G", "00:00:00", "+10:00:00", "And", "1", "1", "", "Synthetic"],
                    )
                )
            )
    addendum = tmp_path / "addendum.csv"
    addendum.write_text(";".join(fields) + "\n", encoding="utf-8")
    response = tmp_path / "response.csv"
    response.write_text(
        "id,flux,bibcode,qual,system\n"
        "NGC  6888,7.5,SYNTHETIC,C,V\n"
        "NGC  6885,8.1,SYNTHETIC,E,V\n"
        "NGC  7000,nan,SYNTHETIC,A,V\n",
        encoding="utf-8",
    )
    args = argparse.Namespace(
        ngc_source=str(source),
        addendum_source=str(addendum),
        fetch_simbad=False,
        simbad_response=response,
        retrieved_on="2000-01-01",
        output=tmp_path / "catalog.csv.gz",
    )
    return builder, args


def test_builder_is_reproducible_and_rejects_unreliable_photometry(builder_inputs):
    builder, args = builder_inputs
    builder.build(args)
    first = args.output.read_bytes()
    builder.build(args)
    assert args.output.read_bytes() == first
    with gzip.open(args.output, "rt", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 109
    assert rows[26]["magnitude_v"] == "7.5"
    assert rows[26]["magnitude_reference"] == "SYNTHETIC"
    assert rows[36]["magnitude_v"] == ""
    assert rows[19]["magnitude_v"] == ""


def test_builder_rejects_ambiguous_simbad_values(builder_inputs):
    builder, args = builder_inputs
    with args.simbad_response.open("a", encoding="utf-8") as stream:
        stream.write("NGC 6888,9.0,SYNTHETIC,A,V\n")
    with pytest.raises(ValueError, match="ambiguë"):
        builder.build(args)
    assert not args.output.exists()


def test_builder_does_not_silently_ignore_missing_supplement(builder_inputs):
    builder, args = builder_inputs
    args.simbad_response = args.simbad_response.with_name("absent.csv")
    with pytest.raises(FileNotFoundError):
        builder.build(args)
