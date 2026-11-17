# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Géométrie et sélection communes des petits corps mobiles, sans réseau."""

import astropy.units as u
import numpy as np
from astropy.constants import GM_sun, c
from astropy.coordinates import (
    GCRS,
    AltAz,
    CartesianRepresentation,
    EarthLocation,
    SkyCoord,
    get_body_barycentric,
    solar_system_ephemeris,
)
from astropy.time import Time

from .models import FieldOfView, ObservationWindow, VisibilityResult, apparent_magnitude
from .visibility import _interpolate_crossing, _sample_datetimes

MU = GM_sun.to_value(u.au**3 / u.day**2)
LIGHT_SPEED = c.to_value(u.au / u.day)
OBLIQUITY = np.deg2rad(23.439291111)


def orbit_geometry(orbits, times, location, positions):
    if not orbits:
        raise ValueError("Au moins une orbite est requise")
    if np.any((times.utc.jyear < 1900) | (times.utc.jyear > 2100)):
        raise ValueError("Le modèle planétaire intégré est limité à 1900–2100")
    with solar_system_ephemeris.set("builtin"):
        site_pos, site_vel = location.get_gcrs_posvel(times)
        earth = get_body_barycentric("earth", times).xyz.to_value(u.au)
        observer = earth + site_pos.xyz.to_value(u.au)
        delay = np.zeros((len(orbits), times.size))
        for _ in range(6):
            retarded = Time(times.tdb.jd - delay, format="jd", scale="tdb")
            helio = positions(orbits, retarded.jd)
            body = helio + get_body_barycentric("sun", retarded).xyz.to_value(u.au)
            vector = body - observer[:, None, :]
            distance = np.linalg.norm(vector, axis=0)
            updated = distance / LIGHT_SPEED
            if np.max(np.abs(updated - delay)) < 1e-10:
                break
            delay = updated
        else:
            raise ValueError("La correction du temps de lumière ne converge pas")
        icrs = SkyCoord(CartesianRepresentation(body * u.au), frame="icrs")
        gcrs = icrs.transform_to(GCRS(obstime=times, obsgeoloc=site_pos, obsgeovel=site_vel))
        horizontal = icrs.transform_to(AltAz(obstime=times, location=location, pressure=0 * u.hPa))
    radius = np.linalg.norm(helio, axis=0)
    cosine = np.sum(helio * vector, axis=0) / (radius * distance)
    phase = np.arccos(np.clip(cosine, -1, 1))
    return gcrs, horizontal, radius, distance, phase


def compute_moving_visibility(
    orbits,
    window: ObservationWindow,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    field_of_view: FieldOfView,
    sample_minutes: float = 10,
    max_magnitude: float | None = None,
    *,
    calculate,
    make_target,
) -> list[VisibilityResult]:
    dates = _sample_datetimes(window, sample_minutes)
    times = Time(dates)
    location = EarthLocation.from_geodetic(
        longitude_deg * u.deg, latitude_deg * u.deg, elevation_m * u.m
    )
    results = []
    for offset in range(0, len(orbits), 128):
        chunk = orbits[offset : offset + 128]
        gcrs, horizontal, magnitudes = calculate(chunk, times, location)
        altitude, azimuth = horizontal.alt.deg, horizontal.az.deg
        in_field = field_of_view.contains(azimuth, altitude)
        passing = in_field if max_magnitude is None else in_field & (magnitudes <= max_magnitude)
        for row in np.flatnonzero(np.any(passing, axis=1)):
            orbit = chunk[row]
            valid = np.flatnonzero(passing[row] & np.isfinite(magnitudes[row]))
            index = (
                int(valid[np.argmin(magnitudes[row, valid])])
                if valid.size
                else int(np.flatnonzero(passing[row])[0])
            )
            target = make_target(
                orbit,
                float(gcrs.ra.deg[row, index]),
                float(gcrs.dec.deg[row, index]),
                float(magnitudes[row, index]) if valid.size else None,
            )
            rises, sets = [], []
            above = altitude[row] >= field_of_view.altitude_lower_deg
            for j in range(len(dates) - 1):
                if above[j] != above[j + 1]:
                    crossing = _interpolate_crossing(
                        dates, altitude[row], j, field_of_view.altitude_lower_deg
                    )
                    (rises if above[j + 1] else sets).append(
                        crossing.astimezone(window.start_local.tzinfo)
                    )
            results.append(
                VisibilityResult(
                    target,
                    float(altitude[row, 0]),
                    float(altitude[row, -1]),
                    float(azimuth[row, 0]),
                    float(azimuth[row, -1]),
                    constellation=str(gcrs[row, index].get_constellation(short_name=True)),
                    rises_above_minimum_local=rises[0] if rises else None,
                    sets_below_minimum_local=sets[0] if sets else None,
                    magnitude_estimated=True,
                    magnitude_reference_time=dates[index].astimezone(window.start_local.tzinfo),
                )
            )
    return sorted(
        results,
        key=lambda r: (
            apparent_magnitude(r.star) if apparent_magnitude(r.star) is not None else float("inf"),
            r.star.name.casefold(),
        ),
    )
