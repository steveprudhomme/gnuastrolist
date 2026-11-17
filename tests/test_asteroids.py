# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Références JPL figées et cas synthétiques; aucune requête réseau."""

import gzip
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time
from astropy.utils import iers
from pypdf import PdfReader

from gnu_astrolist import asteroids
from gnu_astrolist.asteroids import (
    MU,
    OBLIQUITY,
    compute_asteroid_visibility,
    ephemerides,
    heliocentric_positions,
    hg_magnitude,
    load_asteroid_catalog,
    parse_sbdb,
)
from gnu_astrolist.cli import main
from gnu_astrolist.models import FieldOfView
from gnu_astrolist.seestar import object_keys, scan_seestar
from gnu_astrolist.selection import load_catalog_selection
from gnu_astrolist.time_utils import parse_observation_window
from gnu_astrolist.visibility import compute_visibility
from scripts.build_asteroid_catalog import build

iers.conf.auto_download = False
iers.conf.auto_max_age = None
WINDOW = parse_observation_window("2026-11-17", "21:00-22:00", "America/Toronto")
FIELD = FieldOfView.from_automatic_center(
    azimuth_min_deg=0, azimuth_max_deg=360, minimum_altitude_deg=10
)
SITE = EarthLocation.from_geodetic(-73.68 * u.deg, 45.57 * u.deg)
SOURCE = Path(__file__).parents[1] / "src/gnu_astrolist/data/asteroids.json.gz"


def payload():
    data = json.loads(gzip.decompress(SOURCE.read_bytes()))
    data["data"] = data["data"][:1]
    return data


def visible(orbits, **kwargs):
    return compute_asteroid_visibility(orbits, WINDOW, 45.57, -73.68, 0, FIELD, **kwargs)


def test_catalog_scope_and_h_is_not_apparent_v():
    orbits = load_asteroid_catalog()
    assert len(orbits) == 1000
    assert [o.number for o in orbits] == list(range(1, 1001))
    assert orbits[0].name == "Ceres" and orbits[432].name == "Eros"
    assert orbits[0].h == 3.34
    assert sum(o.g is None for o in orbits) == 896
    assert visible(orbits[:1], max_magnitude=4) == []
    result = visible(orbits[:1])[0]
    assert 7 < result.star.magnitude_v < 9
    assert result.magnitude_estimated and result.magnitude_reference_time is not None
    assert result.maximum_solar_separation_date is None
    assert result.best_seasonal_visibility_date is None and result.opposition_date is None
    assert WINDOW.start_local <= result.rises_above_minimum_local <= WINDOW.end_local
    with pytest.raises(ValueError, match="moteur orbital"):
        compute_visibility([result.star], WINDOW, 45.57, -73.68, 0, FIELD)


def test_independent_horizons_positions_and_photometry():
    reference = json.loads(
        Path(__file__).with_name("data").joinpath("asteroid_horizons.json").read_text()
    )
    catalog = {o.number: o for o in load_asteroid_catalog()}
    for body in reference["references"]:
        samples = np.array(body["samples"])
        times = Time(samples[:, 0], format="jd", scale="utc")
        gcrs, horizontal, mag = ephemerides((catalog[body["number"]],), times, SITE)
        # Comparaison angulaire sur la sphère, y compris sous l'horizon (Eros).
        expected = SkyCoord(
            az=samples[:, 1] * u.deg, alt=samples[:, 2] * u.deg, frame=horizontal.frame
        )
        assert np.max(horizontal.separation(expected).arcsec) < 20
        assert np.max(np.abs(mag[0] - samples[:, 3])) < 0.01
        assert abs(gcrs.ra.deg[0, 1] - gcrs.ra.deg[0, 0]) > 0.001


def test_circular_orbit_quarter_period_and_high_eccentricity():
    base = replace(load_asteroid_catalog()[0], a=1, e=0, i=0, node=0, peri=0, mean_anomaly=0)
    period = 2 * np.pi / np.sqrt(MU)
    positions = heliocentric_positions((base,), np.array([base.epoch, base.epoch + period / 4]))
    np.testing.assert_allclose(positions[:, 0, 0], [1, 0, 0], atol=1e-10)
    np.testing.assert_allclose(
        positions[:, 0, 1], [0, np.cos(OBLIQUITY), np.sin(OBLIQUITY)], atol=1e-10
    )
    eccentric = replace(base, e=0.999, mean_anomaly=0.001)
    assert np.all(np.isfinite(heliocentric_positions((eccentric,), np.array([base.epoch]))))
    assert hg_magnitude(10, 0.15, 1, 1, 0) == pytest.approx(10)
    assert hg_magnitude(10, 0.15, 2, 2, 0) == pytest.approx(10 + 5 * np.log10(4))


@pytest.mark.parametrize(
    "bad", [None, [], {}, {"signature": None}, {"signature": {"version": "9"}}]
)
def test_bad_envelope(bad):
    with pytest.raises(ValueError):
        parse_sbdb(bad)


@pytest.mark.parametrize(
    "field,value",
    [
        ("e", 1),
        ("a", -1),
        ("i", 181),
        ("H", "nan"),
        ("G", "inf"),
        ("epoch", None),
        ("equinox", "J2050"),
        ("pdes", "C/2026 A1"),
    ],
)
def test_bad_orbits(field, value):
    data = payload()
    data["data"][0][data["fields"].index(field)] = value
    with pytest.raises(ValueError):
        parse_sbdb(data)


def test_duplicate_fields_rows_and_empty_catalog():
    for mutate in (
        lambda d: d["fields"].append("a"),
        lambda d: d["data"].append(d["data"][0]),
        lambda d: d.update(data=[]),
        lambda d: d.update(data=[None]),
    ):
        data = payload()
        mutate(data)
        with pytest.raises(ValueError):
            parse_sbdb(data)


def test_unknown_h_and_default_g_are_explicit():
    orbit = replace(load_asteroid_catalog()[0], h=None, g=None)
    result = visible((orbit,))[0]
    assert result.star.magnitude_v is None
    assert "supposé" in result.star.magnitude_reference
    assert visible((orbit,), max_magnitude=99) == []
    with pytest.raises(ValueError, match="365 jours"):
        ephemerides((orbit,), Time([orbit.epoch + 366], format="jd", scale="tdb"), SITE)
    ancient = replace(orbit, epoch=2400000.5)
    with pytest.raises(ValueError, match="1900"):
        ephemerides((ancient,), Time([ancient.epoch], format="jd", scale="tdb"), SITE)


def test_magnitude_and_field_must_match_at_same_sample(monkeypatch):
    orbit = load_asteroid_catalog()[0]

    def synthetic(orbits, times, location):
        assert times.size == 2
        gcrs = SkyCoord(ra=[[0, 1]] * u.deg, dec=[[0, 0]] * u.deg, frame="gcrs")
        altaz = SkyCoord(az=[[180, 180]] * u.deg, alt=[[5, 45]] * u.deg, frame="altaz")
        return gcrs, altaz, np.array([[1, 12]])

    monkeypatch.setattr(asteroids, "ephemerides", synthetic)
    assert visible((orbit,), sample_minutes=60, max_magnitude=10) == []
    result = visible((orbit,), sample_minutes=60)[0]
    assert result.star.magnitude_v == 12
    assert result.magnitude_reference_time == WINDOW.end_local


def test_local_import_and_deterministic_rebuild(tmp_path):
    source, out1, out2 = (tmp_path / n for n in ("source.json", "one.gz", "two.gz"))
    source.write_text(json.dumps(payload()), encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert build(source, out1, "2026-11-17", digest) == 1
    build(source, out2, "2026-11-17", digest)
    assert out1.read_bytes() == out2.read_bytes()
    assert len(load_asteroid_catalog(source)) == 1
    with pytest.raises(ValueError, match="Empreinte"):
        build(source, out2, "2026-11-17", "wrong")
    source.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        load_asteroid_catalog(source)
    with pytest.raises(ValueError, match="illisible"):
        load_asteroid_catalog(tmp_path / "missing.json")


def test_asteroid_seestar_identity_never_matches_messier_or_bare_number(tmp_path):
    vesta = visible((load_asteroid_catalog()[3],))[0].star
    keys = object_keys(vesta)
    assert "MPC4" in keys and "VESTA" in keys
    assert not keys & {"4", "M4", "C4"}
    assert object_keys(replace(vesta, name='(4)', asteroid_name='')) == {'MPC4'}
    root = tmp_path / "MyWorks"
    root.mkdir()
    image = root / "Stacked_20_M4_10.0s_LP_20261117.fit"
    image.write_bytes(b"Synthetic")
    assert scan_seestar(root).status(keys) == "Non trouvé"
    image.rename(root / "Stacked_20_MPC4_10.0s_LP_20261117.fit")
    assert scan_seestar(root).status(keys) == "Fait (empilé)"


def test_cli_mixed_text_pdf_and_local_catalog(tmp_path, capsys):
    data = payload()
    source = tmp_path / "orbites.json"
    source.write_text(json.dumps(data), encoding="utf-8")
    text, pdf = tmp_path / "report.txt", tmp_path / "report.pdf"
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
        "asteroids",
        "messier",
        "--max-magnitude",
        "8",
        "--asteroids-file",
        str(source),
        "--offline",
        "--details",
        "--output-txt",
        str(text),
        "--output-pdf",
        str(pdf),
    ]
    assert main(args) == 0
    report = capsys.readouterr().out
    assert text.read_text(encoding="utf-8").strip() == report.strip()
    assert "(1) Ceres" in report and "Instant V estimée" in report and "≈7." in report
    assert "M31" in report
    extracted = "\n".join(p.extract_text() for p in PdfReader(pdf).pages)
    assert "(1) Ceres" in extracted and "≈7." in extracted and "2026-11-17 22:00" in extracted
    assert "365 jours" in extracted and "supposé" in extracted
    assert source.read_text(encoding="utf-8") == json.dumps(data)


def test_selection_defers_orbital_filter_and_requires_option_context(capsys):
    fixed, selection = load_catalog_selection(["asteroids"], max_magnitude=8)
    assert fixed == [] and selection.limits == (8,)
    assert "H-G" in " ".join(selection.notes)
    with pytest.raises(SystemExit):
        main(
            [
                "--date",
                "2026-11-17",
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
                "10",
                "--objects",
                "messier",
                "--asteroids-file",
                "missing.json",
                "--offline",
            ]
        )
    assert "exige --objects asteroids" in capsys.readouterr().err
