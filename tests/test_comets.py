# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Coniques analytiques et références JPL; observations CBAT synthétiques."""

import csv
import gzip
import json
from dataclasses import replace
from importlib import resources
from pathlib import Path

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time
from astropy.utils import iers
from pypdf import PdfReader

from gnu_astrolist import comets
from gnu_astrolist.asteroids import heliocentric_positions as asteroid_positions
from gnu_astrolist.asteroids import load_asteroid_catalog
from gnu_astrolist.cli import main
from gnu_astrolist.comets import (
    annotate_cbat,
    compute_comet_visibility,
    eligible_orbits,
    ephemerides,
    heliocentric_positions,
    load_cbat_observations,
    load_comet_catalog,
    normalize_comet_name,
    parse_mpc,
)
from gnu_astrolist.models import FieldOfView
from gnu_astrolist.moving import MU, OBLIQUITY
from gnu_astrolist.seestar import normalize_name, object_keys, scan_seestar
from gnu_astrolist.time_utils import parse_observation_window
from gnu_astrolist.visibility import compute_visibility
from scripts.build_comet_catalog import build

iers.conf.auto_download = False
iers.conf.auto_max_age = None
WINDOW = parse_observation_window("2026-11-17", "21:00-22:00", "America/Toronto")
FIELD = FieldOfView(180, 45, 360, 90)


def raw_rows():
    return (
        gzip.decompress(
            resources.files("gnu_astrolist.data").joinpath("comets.txt.gz").read_bytes()
        )
        .decode("ascii")
        .splitlines()
    )


def test_mpc_catalog_scope_epochs_and_fragments():
    catalog = load_comet_catalog()
    assert len(catalog) == 958 and len(raw_rows()) == 973
    assert not any(o.designation.startswith("A/") for o in catalog)
    assert any(o.e > 1 for o in catalog) and any(o.e < 1 for o in catalog)
    assert any(o.designation == "332P-B" for o in catalog)
    usable, excluded = eligible_orbits(catalog, Time([WINDOW.start_local, WINDOW.end_local]))
    assert len(usable) == 952 and excluded == 6
    assert "1I" not in {o.designation for o in usable}
    assert sum(o.epoch_tt is None for o in catalog) == 5


def test_three_conics_analytically_and_continuity():
    orbit = replace(load_comet_catalog()[0], q=1, e=1, peri=0, node=0, i=0)
    # Équation de Barker, paramètre D=tan(v/2)=0,5.
    d = 0.5
    dt = np.sqrt(2 / MU) * (d + d**3 / 3)
    jd = np.array([orbit.perihelion_tdb - dt, orbit.perihelion_tdb, orbit.perihelion_tdb + dt])
    actual = heliocentric_positions((orbit,), jd)[:, 0, :]
    expected_y = np.array([-2 * d, 0, 2 * d])
    expected = np.array(
        [[1 - d * d, 1, 1 - d * d], expected_y * np.cos(OBLIQUITY), expected_y * np.sin(OBLIQUITY)]
    )
    np.testing.assert_allclose(actual, expected, atol=1e-10)
    for e in (1 - 1e-10, 1 + 1e-10):
        np.testing.assert_allclose(
            heliocentric_positions((replace(orbit, e=e),), jd)[:, 0, :], expected, atol=1e-8
        )
    # Hyperbole e=1,5, |a|=2, anomalie hyperbolique F=0,5.
    e, f, a = 1.5, 0.5, 2
    dt = np.sqrt(a**3 / MU) * (e * np.sinh(f) - f)
    x, y = a * (e - np.cosh(f)), a * np.sqrt(e * e - 1) * np.sinh(f)
    p = heliocentric_positions((replace(orbit, e=e),), np.array([orbit.perihelion_tdb + dt]))[
        :, 0, 0
    ]
    np.testing.assert_allclose(p, [x, y * np.cos(OBLIQUITY), y * np.sin(OBLIQUITY)], atol=1e-10)
    # Même ellipse vue par deux formulations indépendantes de Kepler.
    asteroid = replace(
        load_asteroid_catalog()[0],
        epoch=orbit.perihelion_tdb,
        a=2,
        e=0.5,
        i=0,
        node=0,
        peri=0,
        mean_anomaly=0,
    )
    np.testing.assert_allclose(
        heliocentric_positions((replace(orbit, e=0.5),), jd),
        asteroid_positions((asteroid,), jd),
        atol=1e-10,
    )


def test_independent_jpl_horizons_positions():
    reference = json.loads(
        Path(__file__).with_name("data").joinpath("comet_horizons.json").read_text()
    )
    assert len(reference["references"]) == 2
    catalog = {o.designation: o for o in load_comet_catalog()}
    site = EarthLocation.from_geodetic(-73.68 * u.deg, 45.57 * u.deg)
    for body in reference["references"]:
        rows = np.array(body["samples"])
        _, altaz, magnitude = ephemerides(
            (catalog[body["designation"]],), Time(rows[:, 0], format="jd", scale="utc"), site
        )
        expected = SkyCoord(az=rows[:, 1] * u.deg, alt=rows[:, 2] * u.deg, frame=altaz.frame)
        assert np.max(altaz.separation(expected).arcsec) < 10
        assert np.all(np.isfinite(magnitude))
        # Les paramètres photométriques MPC/JPL diffèrent : ne pas forcer leur accord.


@pytest.mark.parametrize(
    "start,end,value",
    [(30, 39, "nan"), (41, 49, "-0.5"), (71, 79, "181"), (91, 95, "nan"), (14, 18, "bad")],
)
def test_mpc_invalid_fields(start, end, value):
    row = raw_rows()[0]
    bad = row[:start] + value.rjust(end - start) + row[end:]
    with pytest.raises(ValueError, match="Ligne MPC"):
        parse_mpc(bad)


def test_mpc_duplicate_empty_and_unknown_format(tmp_path):
    row = raw_rows()[0]
    for text in ("", row + "\n" + row, "<html>error</html>"):
        with pytest.raises(ValueError):
            parse_mpc(text)
    with pytest.raises(ValueError, match="illisible"):
        load_comet_catalog(tmp_path / "absent.txt")
    source = tmp_path / "CometEls.txt"
    source.write_text(row + "\n", encoding="ascii")
    with pytest.raises(ValueError, match="Empreinte"):
        build(source, tmp_path / "out.gz")


def test_filter_total_magnitude_missing_parameters_and_epoch(monkeypatch):
    orbit = replace(
        load_comet_catalog()[0], designation="161P", epoch_tt=Time(WINDOW.start_local).tt.jd
    )

    def synthetic(orbits, times, location):
        coordinates = SkyCoord(ra=[[0, 1]] * u.deg, dec=[[0, 0]] * u.deg, frame="gcrs")
        horizontal = SkyCoord(az=[[180, 180]] * u.deg, alt=[[-5, 45]] * u.deg, frame="altaz")
        return coordinates, horizontal, np.array([[1, 12]])

    monkeypatch.setattr(comets, "ephemerides", synthetic)
    args = ((orbit,), WINDOW, 45.57, -73.68, 0, FIELD, 60)
    assert compute_comet_visibility(*args, max_magnitude=10) == []
    result = compute_comet_visibility(*args)[0]
    assert result.star.passband == "total" and result.star.magnitude_total == 12
    assert result.star.magnitude_v is None
    assert result.magnitude_reference_time == WINDOW.end_local
    assert result.maximum_solar_separation_date is None and result.opposition_date is None
    with pytest.raises(ValueError, match="moteur orbital"):
        compute_visibility([result.star], WINDOW, 45.57, -73.68, 0, FIELD)
    monkeypatch.undo()
    site = EarthLocation.from_geodetic(0 * u.deg, 45 * u.deg)
    times = Time([WINDOW.start_local, WINDOW.end_local])
    _, _, mag = ephemerides((replace(orbit, h=None),), times, site)
    assert np.isnan(mag).all()
    with pytest.raises(ValueError, match="Époque"):
        ephemerides((replace(orbit, epoch_tt=None),), times, site)


@pytest.mark.parametrize(
    "name,expected",
    [
        ("C_2023_A3", "C/2023 A3"),
        ("0067P", "67P"),
        ("73P-B/Schwassmann-Wachmann", "73P-B"),
        ("ATLAS", None),
        ("M4", None),
    ],
)
def test_comet_identity(name, expected):
    assert normalize_comet_name(name) == expected
    if expected:
        assert normalize_name(name) == expected


def write_cbat(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "designation",
                "observed_at",
                "magnitude",
                "band",
                "observer",
                "reference",
                "url",
            ),
        )
        writer.writeheader()
        writer.writerows(rows)


def observation(**overrides):
    # Mesure synthétique, jamais présentée comme une observation réelle.
    return {
        "designation": "161P",
        "observed_at": "2026-11-16T02:00:00Z",
        "magnitude": "11.2",
        "band": "R",
        "observer": "Observateur synthétique",
        "reference": "Exemple synthétique",
        "url": "https://www.icq.eps.harvard.edu/CometMags.html",
        **overrides,
    }


def test_cbat_is_dated_not_a_forecast_and_fragments_are_distinct(tmp_path):
    orbit = next(o for o in load_comet_catalog() if o.designation == "161P")
    result = compute_comet_visibility((orbit,), WINDOW, 45.57, -73.68, 0, FIELD)[0]
    path = tmp_path / "cbat.csv"
    write_cbat(
        path, [observation(), observation(observed_at="2027-01-01T00:00:00Z", magnitude="1")]
    )
    observations = load_cbat_observations(path)
    annotated = annotate_cbat([result], observations, WINDOW.start_local)[0]
    assert annotated.star.magnitude_total == result.star.magnitude_total
    assert annotated.star.magnitude_v is None
    assert "11.2 [R]" in annotated.comet_observation and "2026-11-16" in annotated.comet_observation
    fragmented = replace(result, star=replace(result.star, designation="161P-B"))
    assert (
        annotate_cbat([fragmented], observations, WINDOW.start_local)[0].comet_observation is None
    )
    assert object_keys(fragmented.star) == {"161P-B"}
    root = tmp_path / "MyWorks"
    root.mkdir()
    (root / "Stacked_20_161P_10.0s_LP_20261117.fit").write_bytes(b"Synthetic")
    assert scan_seestar(root).status(object_keys(result.star)) == "Fait (empilé)"
    assert scan_seestar(root).status(object_keys(fragmented.star)) == "Non trouvé"


@pytest.mark.parametrize(
    "changes",
    [
        {"observed_at": "2026-11-16"},
        {"magnitude": "nan"},
        {"reference": ""},
        {"url": "https://example.com/"},
        {"designation": "ATLAS"},
    ],
)
def test_bad_cbat_observations(tmp_path, changes):
    path = tmp_path / "cbat.csv"
    write_cbat(path, [observation(**changes)])
    with pytest.raises(ValueError, match="CSV CBAT"):
        load_cbat_observations(path)


def test_cli_mixed_reports_and_immutable_import(tmp_path, capsys):
    row = next(r for r in raw_rows() if r[102:158].startswith("161P/"))
    source = tmp_path / "CometEls.txt"
    source.write_text(row + "\n", encoding="ascii")
    cbat = tmp_path / "cbat.csv"
    write_cbat(cbat, [observation()])
    txt, pdf = tmp_path / "report.txt", tmp_path / "report.pdf"
    args = [
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
        "10",
        "--objects",
        "comets",
        "asteroids",
        "--comets-file",
        str(source),
        "--cbat-file",
        str(cbat),
        "--offline",
        "--details",
        "--output-txt",
        str(txt),
        "--output-pdf",
        str(pdf),
    ]
    assert main(args) == 0
    report = capsys.readouterr().out
    assert "161P/Hartley-IRAS" in report and "(4) Vesta" in report
    assert "(totale)" in report and "11.2 [R]" in report and "CBAT (observation datée)" in report
    assert txt.read_text(encoding="utf-8").strip() == report.strip()
    extracted = "\n".join(p.extract_text() for p in PdfReader(pdf).pages)
    assert "Magnitude totale" in extracted and "11.2 [R]" in extracted
    assert source.read_text(encoding="ascii") == row + "\n"
