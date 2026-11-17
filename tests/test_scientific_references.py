# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Références Skyfield gelées : aucune dépendance de comparaison à l'exécution."""
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import EarthLocation, angular_separation
from astropy.table import QTable
from astropy.time import Time
from astropy.utils import iers
from sgp4.api import Satrec
from sgp4.exporter import export_omm

from gnu_astrolist.models import FieldOfView, ObservationWindow
from gnu_astrolist.satellites import _horizontal, compute_satellite_visibility, parse_gp

REFERENCE = json.loads((Path(__file__).parent / "data/satellite_reference.json").read_text("utf-8"))


@pytest.fixture
def reference_eop():
    rows = np.array(REFERENCE["eop_rows"])
    table = QTable()
    for index, (key, unit) in enumerate([
        ("MJD", u.d), ("PM_x", u.arcsec), ("PM_y", u.arcsec), ("UT1_UTC", u.s),
    ]):
        table[key] = rows[:, index] * unit
    with iers.conf.set_temp("auto_download", False), iers.earth_orientation_table.set(iers.IERS(table)):
        yield


def element_for(number):
    tle = next(item for item in REFERENCE["tles"] if item["norad_id"] == number)
    sat = Satrec.twoline2rv(tle["line1"], tle["line2"])
    return parse_gp([export_omm(sat, f"Reference {number}")])[0]


@pytest.mark.parametrize("case", REFERENCE["cases"], ids=lambda case: case["id"])
def test_independent_satellite_horizontal(case, reference_eop):
    site = REFERENCE["sites"][case["site_index"]]
    location = EarthLocation.from_geodetic(site["longitude_deg"] * u.deg,
                                          site["latitude_deg"] * u.deg,
                                          site["elevation_m"] * u.m)
    instant = Time([datetime.fromisoformat(case["utc"])])
    horizontal, _ = _horizontal(element_for(case["norad_id"]), instant, location)
    separation = angular_separation(horizontal.az, horizontal.alt,
                                    case["azimuth_deg"] * u.deg, case["altitude_deg"] * u.deg)
    # Great-circle separation handles north wrapping and the zenith singularity.
    assert separation.to_value(u.arcsec)[0] < REFERENCE["tolerance"]["direction_arcsec"]
    assert abs(horizontal.distance.to_value(u.km)[0] - case["distance_km"]) < 0.01


def test_reference_coverage_and_generator_integrity():
    assert len(REFERENCE["cases"]) == 38
    assert len(REFERENCE["sites"]) == 3
    assert {case["norad_id"] for case in REFERENCE["cases"]} == {5, 6251, 8195, 14128}
    horizon = [c for c in REFERENCE["cases"] if "horizon" in c["id"]]
    assert -1 < horizon[0]["altitude_deg"] < 0 < horizon[1]["altitude_deg"] < 1
    generator = Path(__file__).parents[1] / "scripts/generate_satellite_reference.py"
    normalized = generator.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(normalized).hexdigest() == REFERENCE["generator_sha256"]


def test_public_visibility_horizon_sampling(reference_eop):
    before, after = [c for c in REFERENCE["cases"] if "horizon" in c["id"]]
    start = datetime.fromisoformat(before["utc"])
    end = datetime.fromisoformat(after["utc"])
    site = REFERENCE["sites"][0]
    window = ObservationWindow(start, end, "UTC")
    results = compute_satellite_visibility(
        [element_for(6251)], window, site["latitude_deg"], site["longitude_deg"],
        site["elevation_m"], FieldOfView.from_automatic_center(
            azimuth_min_deg=0, azimuth_max_deg=360, minimum_altitude_deg=0), sample_seconds=4)
    assert len(results) == 1
    assert results[0].altitude_start_deg < 0 < results[0].altitude_end_deg
    assert results[0].position_reference_time == end
    assert results[0].star.magnitude_v is None
    # Coarse sampling is not proof of absence of a continuous pass.
    below = ObservationWindow(start - timedelta(seconds=4), start, "UTC")
    assert compute_satellite_visibility(
        [element_for(6251)], below, site["latitude_deg"], site["longitude_deg"],
        site["elevation_m"], FieldOfView.from_automatic_center(
            azimuth_min_deg=0, azimuth_max_deg=360, minimum_altitude_deg=0), sample_seconds=4) == []
