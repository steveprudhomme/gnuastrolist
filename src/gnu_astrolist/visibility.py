"""Calcul vectorisé des positions horizontales avec Astropy."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence

import astropy.units as u
import numpy as np
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time

from .models import FieldOfView, ObservationWindow, VariableStar, VisibilityResult

MAX_TIME_SAMPLES = 2_000
CATALOG_CHUNK_SIZE = 2_048


def _sample_datetimes(window: ObservationWindow, interval_minutes: float) -> list[datetime]:
    if interval_minutes <= 0.0:
        raise ValueError("l'intervalle d'échantillonnage doit être supérieur à zéro")

    start_utc = window.start_local.astimezone(timezone.utc)
    end_utc = window.end_local.astimezone(timezone.utc)
    step = timedelta(minutes=interval_minutes)
    estimated_samples = int((end_utc - start_utc) / step) + 2
    if estimated_samples > MAX_TIME_SAMPLES:
        raise ValueError(
            "le pas demandé produirait plus de "
            f"{MAX_TIME_SAMPLES} instants; augmentez --sample-minutes"
        )
    samples = [start_utc]
    current = start_utc + step
    while current < end_utc:
        samples.append(current)
        current += step
    samples.append(end_utc)
    return samples


def compute_visibility(
    stars: Sequence[VariableStar],
    window: ObservationWindow,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    field_of_view: FieldOfView,
    sample_minutes: float = 10.0,
) -> list[VisibilityResult]:
    """Retourne les objets qui traversent le champ à un instant échantillonné.

    Les hauteurs sont géométriques : la réfraction atmosphérique n'est pas
    appliquée, car Astropy utilise ici une pression nulle.
    """

    if not stars:
        return []
    if not -90.0 <= latitude_deg <= 90.0:
        raise ValueError("la latitude doit être comprise entre -90 et 90 degrés")
    if not -180.0 <= longitude_deg <= 180.0:
        raise ValueError("la longitude doit être comprise entre -180 et 180 degrés")

    location = EarthLocation.from_geodetic(
        lon=longitude_deg * u.deg,
        lat=latitude_deg * u.deg,
        height=elevation_m * u.m,
    )
    times = Time(_sample_datetimes(window, sample_minutes))
    coordinates = SkyCoord(
        ra=np.fromiter((star.ra_deg for star in stars), dtype=float) * u.deg,
        dec=np.fromiter((star.dec_deg for star in stars), dtype=float) * u.deg,
        frame="icrs",
    )

    horizontal_frame = AltAz(
        obstime=times,
        location=location,
        pressure=0.0 * u.hPa,
    )
    results: list[VisibilityResult] = []
    for chunk_start in range(0, len(stars), CATALOG_CHUNK_SIZE):
        chunk_stop = min(chunk_start + CATALOG_CHUNK_SIZE, len(stars))
        horizontal = coordinates[chunk_start:chunk_stop, np.newaxis].transform_to(
            horizontal_frame
        )
        altitudes = np.asarray(horizontal.alt.deg)
        azimuths = np.asarray(horizontal.az.deg)
        inside = field_of_view.contains(azimuths, altitudes)
        selected_indices = np.flatnonzero(np.any(inside, axis=1))

        results.extend(
            VisibilityResult(
                star=stars[chunk_start + index],
                altitude_start_deg=float(altitudes[index, 0]),
                altitude_end_deg=float(altitudes[index, -1]),
                azimuth_start_deg=float(azimuths[index, 0]),
                azimuth_end_deg=float(azimuths[index, -1]),
            )
            for index in selected_indices
        )
    results.sort(key=lambda result: (result.star.mag_max, result.star.name.casefold()))
    return results
