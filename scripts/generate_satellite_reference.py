# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reconstruit les références calculées avec Skyfield, sans importer Astropy."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from importlib import metadata, resources
from pathlib import Path

import numpy as np
from skyfield.api import EarthSatellite, load, wgs84

SITES = [
    dict(name="Greenwich public example", latitude_deg=51.4779, longitude_deg=0.0, elevation_m=46),
    dict(name="Equator public grid", latitude_deg=0.0, longitude_deg=0.0, elevation_m=0),
    dict(name="Sydney public example", latitude_deg=-33.8688, longitude_deg=151.2093, elevation_m=0),
]
SATELLITES = (5, 6251, 8195, 14128)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def generate(iers_path):
    tle_bytes = resources.files("sgp4").joinpath("SGP4-VER.TLE").read_bytes()
    lines = tle_bytes.decode("ascii").splitlines()
    tles = [(line[:69], lines[i + 1][:69]) for i, line in enumerate(lines)
            if line.startswith("1 ") and int(line[2:7]) in SATELLITES]
    # Read the documented C04 columns directly; no Astropy transformations or API.
    eop_bytes = iers_path.read_bytes()
    if digest(tle_bytes) != "d246d1d9d768ace445a38a965713fa9ba52d80fd8a41a0502ff83d7acffe2881":
        raise ValueError("Unexpected SGP4-VER.TLE; use sgp4 2.25")
    if digest(eop_bytes) != "d7c84f0357d6b60f99884ccb8bb6efd8ca1c6415d684383bf2dc58951dee14c0":
        raise ValueError("Unexpected C04; use astropy-iers-data 0.2025.12.22.0.40.30")
    all_rows = [[float(v) for v in line.split()[4:8]]
                for line in eop_bytes.decode("ascii").splitlines() if not line.startswith("#")]
    base = load.timescale(builtin=True)
    epochs = [EarthSatellite(a, b, ts=base).epoch.utc_datetime() for a, b in tles]
    mjds = [(epoch - datetime(1858, 11, 17, tzinfo=timezone.utc)).total_seconds() / 86400
            for epoch in epochs]
    rows = [r for r in all_rows if any(abs(r[0] - mjd) < 3 for mjd in mjds)]
    mjd, xp, yp, dut1 = np.array(rows).T
    utc = base.utc(1858, 11, 17 + mjd)
    # TT-UT1 = (TT-UTC) - (UT1-UTC), all in seconds.
    delta_t = utc.delta_t + utc.dut1 - dut1
    ts = load.timescale(builtin=True)
    ts.delta_t_function = lambda tt: np.interp(tt, utc.tt, delta_t)
    ts.polar_motion_table = (utc.tt, xp, yp)
    cases = []

    def add(satellite, epoch, site_index, label):
        site = SITES[site_index]
        observer = wgs84.latlon(site["latitude_deg"], site["longitude_deg"],
                               elevation_m=site["elevation_m"])
        instant = ts.from_datetime(epoch)
        position = (satellite - observer).at(instant)
        if position.message:
            raise ValueError(position.message)
        alt, az, distance = position.altaz()  # No refraction, no light time.
        cases.append(dict(id=f"{satellite.model.satnum}-{site_index}-{label}",
                          norad_id=satellite.model.satnum, site_index=site_index,
                          utc=epoch.isoformat(), altitude_deg=float(alt.degrees),
                          azimuth_deg=float(az.degrees), distance_km=float(distance.km)))

    for (a, b), epoch in zip(tles, epochs):
        sat = EarthSatellite(a, b, ts=ts)
        for site_index in range(len(SITES)):
            for minutes in (0, 30, 90):
                add(sat, epoch + timedelta(minutes=minutes), site_index, str(minutes))
        if sat.model.satnum == 6251:
            observer = wgs84.latlon(SITES[0]["latitude_deg"], 0, elevation_m=46)

            def altitude(seconds):
                return (sat - observer).at(ts.from_datetime(
                    epoch + timedelta(seconds=seconds))).altaz()[0].degrees

            for left in range(0, 86400, 60):
                right = left + 60
                if altitude(left) < 0 < altitude(right):
                    for _ in range(30):
                        middle = (left + right) / 2
                        if altitude(middle) < 0:
                            left = middle
                        else:
                            right = middle
                    for shift in (-2, 2):
                        add(sat, epoch + timedelta(seconds=(left + right) / 2 + shift),
                            0, f"horizon{shift:+}")
                    break
            else:
                raise ValueError("No rising horizon crossing found")
    return dict(
        schema_version=1, kind="computed references, not observations", retrieved_on="2026-11-17",
        versions={name: metadata.version(name) for name in ("skyfield", "sgp4", "numpy", "jplephem")},
        generator_sha256=digest(Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
        tle_source="https://pypi.org/project/sgp4/2.25/", tle_file_sha256=digest(tle_bytes),
        eop_source="https://hpiers.obspm.fr/iers/eop/eopc04/eopc04.1962-now",
        eop_file_sha256=digest(eop_bytes), eop_columns=["mjd_utc", "xp_arcsec", "yp_arcsec", "dut1_s"],
        eop_rows=rows, sites=SITES,
        tles=[dict(norad_id=int(a[2:7]), line1=a, line2=b) for a, b in tles], cases=cases,
        tolerance=dict(direction_arcsec=1.0, distance_km=0.01),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iers-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(generate(args.iers_file), indent=2, ensure_ascii=False)
                           + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
