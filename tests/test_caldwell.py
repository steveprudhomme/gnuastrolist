# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Contrat du catalogue Caldwell et intégration hors ligne des sorties."""

import math
import os
import subprocess
import sys
from dataclasses import replace

import pytest
from astropy.utils import iers
from pypdf import PdfReader

from gnu_astrolist.catalog import filter_by_magnitude, load_caldwell_catalog
from gnu_astrolist.cli import main
from gnu_astrolist.models import FieldOfView
from gnu_astrolist.time_utils import parse_observation_window
from gnu_astrolist.visibility import compute_visibility


@pytest.mark.skipif(sys.platform != "win32", reason="Encodage des sorties redirigées Windows")
def test_windows_redirected_report_uses_utf8():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "gnu_astrolist",
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
            "--objects",
            "caldwell",
            "--max-magnitude",
            "-20",
            "--offline",
        ],
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "SOIRÉE D'OBSERVATION" in result.stdout.decode("utf-8")


def test_complete_caldwell_catalog_and_provenance():
    objects = load_caldwell_catalog()
    assert [obj.name for obj in objects] == [f"C{n}" for n in range(1, 110)]
    assert all(0 <= obj.ra_deg < 360 and -90 <= obj.dec_deg <= 90 for obj in objects)
    assert all(obj.passband == "V" and obj.constellation for obj in objects)
    assert all(obj.magnitude_v is None or math.isfinite(obj.magnitude_v) for obj in objects)
    assert objects[0].catalog_designation == "NGC0188"
    assert objects[13].catalog_designation == "C014"  # Double amas, une seule entrée.
    assert objects[40].catalog_designation == "C041"  # Hyades.
    assert objects[98].object_type == "DrkN"  # Sac à charbon.
    assert objects[-1].catalog_designation == "NGC3195"
    c27 = objects[26]
    assert c27.magnitude_v == 7.5
    assert c27.magnitude_source == "SIMBAD"
    assert c27.magnitude_reference == "2002yCat.2237....0D"
    assert all(
        obj.magnitude_source and obj.magnitude_reference and obj.magnitude_retrieved_on
        for obj in objects
        if obj.magnitude_v is not None
    )


def test_unknown_magnitude_is_retained_only_without_a_limit():
    objects = load_caldwell_catalog()
    assert len(filter_by_magnitude(objects, None)) == 109
    assert any(obj.magnitude_v is None for obj in objects)
    assert all(
        obj.magnitude_v is not None and obj.magnitude_v <= 8
        for obj in filter_by_magnitude(objects, 8)
    )
    assert filter_by_magnitude(objects, -20) == []


def test_visibility_sorts_unknown_magnitude_after_known_values():
    # Même position publique pour isoler le tri de la sélection géométrique.
    reference = load_caldwell_catalog()[0]
    stars = [replace(reference, name="Sans V", magnitude_v=None), reference]
    # Le tri ne teste pas la précision des tables IERS. Définir sa politique
    # explicitement, même si aucun test CLI n'a encore configuré le mode offline.
    with (
        iers.conf.set_temp("auto_download", False),
        iers.conf.set_temp("auto_max_age", None),
        iers.conf.set_temp("iers_degraded_accuracy", "warn"),
    ):
        results = compute_visibility(
            stars,
            parse_observation_window("2026-08-15", "21:00-22:00", "UTC"),
            85,
            0,
            0,
            FieldOfView(180, 45, 360, 90),
        )
    assert [result.star.name for result in results] == ["C1", "Sans V"]


@pytest.mark.parametrize("limit", [None, "-20"])
def test_caldwell_cli_and_exports(tmp_path, capsys, monkeypatch, limit):
    def network_forbidden(*args, **kwargs):
        raise AssertionError("Le mode hors ligne a tenté une connexion")

    monkeypatch.setattr("gnu_astrolist.weather.urlopen", network_forbidden)
    args = [
        "--date",
        "2026-08-15",
        "--time-range",
        "21:00-22:00",
        "--timezone",
        "UTC",
        "--lat",
        "85",
        "--lon",
        "0",
        "--az-min",
        "0",
        "--az-max",
        "360",
        "--min-altitude",
        "0",
        "--objects",
        "caldwell",
        "--offline",
        "--details",
        "--output-txt",
        str(tmp_path / "caldwell.txt"),
        "--output-pdf",
        str(tmp_path / "caldwell.pdf"),
    ]
    if limit:
        args += ["--max-magnitude", limit]
    assert main(args) == 0
    report = capsys.readouterr().out
    assert (tmp_path / "caldwell.txt").read_text(encoding="utf-8") == report
    pdf = "\n".join(p.extract_text() for p in PdfReader(tmp_path / "caldwell.pdf").pages)
    for text in (report, pdf):
        assert "Objets Caldwell (OpenNGC" in text
        assert "complément de magnitude V SIMBAD" in text
        assert "priorité SIMBAD, repli OpenNGC" not in text
        if limit:
            assert "Aucun objet" in text
        else:
            assert "C1" in text
            assert "non disponible" in text
