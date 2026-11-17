"""Calcul vectorisé des positions horizontales avec Astropy."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone, tzinfo

import astropy.units as u
import numpy as np
from astropy.coordinates import AltAz, EarthLocation, SkyCoord, get_sun
from astropy.time import Time

from .models import CatalogObject, FieldOfView, ObservationWindow, VisibilityResult

MAX_TIME_SAMPLES = 2_000
CATALOG_CHUNK_SIZE = 2_048
CROSSING_SAMPLE_MINUTES = 5.0
CROSSING_SEARCH_HOURS = 30.0


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


def _datetime_range(
    start: datetime, end: datetime, interval_minutes: float
) -> list[datetime]:
    step = timedelta(minutes=interval_minutes)
    samples = [start]
    current = start + step
    while current < end:
        samples.append(current)
        current += step
    samples.append(end)
    return samples


def _maximum_solar_separation_dates(
    stars: Sequence[CatalogObject], year: int
) -> list[date]:
    """Estime le jour de séparation angulaire maximale avec le Soleil."""

    first_day = datetime(year, 1, 1, 12, tzinfo=timezone.utc)
    day_count = (date(year + 1, 1, 1) - date(year, 1, 1)).days
    samples = [first_day + timedelta(days=offset) for offset in range(day_count)]
    sun = get_sun(Time(samples)).cartesian
    sun_vectors = np.vstack(
        (sun.x.to_value(u.AU), sun.y.to_value(u.AU), sun.z.to_value(u.AU))
    )
    sun_vectors /= np.linalg.norm(sun_vectors, axis=0)

    ra = np.deg2rad(np.fromiter((star.ra_deg for star in stars), dtype=float))
    dec = np.deg2rad(np.fromiter((star.dec_deg for star in stars), dtype=float))
    target_vectors = np.column_stack(
        (np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec))
    )
    dates: list[date] = []
    for chunk_start in range(0, len(stars), CATALOG_CHUNK_SIZE):
        chunk_stop = min(chunk_start + CATALOG_CHUNK_SIZE, len(stars))
        # Le produit scalaire minimal correspond à la séparation maximale.
        maximum_separation_indices = np.argmin(
            target_vectors[chunk_start:chunk_stop] @ sun_vectors,
            axis=1,
        )
        dates.extend(
            samples[int(index)].date() for index in maximum_separation_indices
        )
    return dates


def _best_seasonal_visibility_dates(
    stars: Sequence[CatalogObject],
    year: int,
    *,
    location: EarthLocation,
    timezone_info: tzinfo,
) -> list[date]:
    """Estime la date où chaque objet culmine le plus près de minuit local."""

    first_midnight = datetime(year, 1, 1, tzinfo=timezone_info)
    day_count = (date(year + 1, 1, 1) - date(year, 1, 1)).days
    local_midnights = [
        first_midnight + timedelta(days=offset) for offset in range(day_count)
    ]
    sidereal_degrees = np.asarray(
        Time(local_midnights).sidereal_time("apparent", longitude=location.lon).deg
    )
    right_ascensions = np.fromiter((star.ra_deg for star in stars), dtype=float)

    dates: list[date] = []
    for chunk_start in range(0, len(stars), CATALOG_CHUNK_SIZE):
        chunk_stop = min(chunk_start + CATALOG_CHUNK_SIZE, len(stars))
        hour_angles = (
            right_ascensions[chunk_start:chunk_stop, np.newaxis]
            - sidereal_degrees[np.newaxis, :]
            + 180.0
        ) % 360.0 - 180.0
        closest_transit_indices = np.argmin(np.abs(hour_angles), axis=1)
        dates.extend(
            local_midnights[int(index)].date() for index in closest_transit_indices
        )
    return dates


def _interpolate_crossing(
    samples: Sequence[datetime], altitudes: np.ndarray, index: int, threshold: float
) -> datetime:
    lower_altitude = float(altitudes[index])
    upper_altitude = float(altitudes[index + 1])
    difference = upper_altitude - lower_altitude
    fraction = 0.5 if difference == 0.0 else (threshold - lower_altitude) / difference
    fraction = min(1.0, max(0.0, fraction))
    return samples[index] + (samples[index + 1] - samples[index]) * fraction


def _threshold_crossings(
    results: Sequence[VisibilityResult],
    *,
    location: EarthLocation,
    reference: datetime,
    minimum_altitude_deg: float,
) -> tuple[list[datetime | None], list[datetime | None], list[bool]]:
    """Calcule les franchissements du seuil autour du début de l'observation."""

    reference_utc = reference.astimezone(timezone.utc)
    search_delta = timedelta(hours=CROSSING_SEARCH_HOURS)
    samples = _datetime_range(
        reference_utc - search_delta,
        reference_utc + search_delta,
        CROSSING_SAMPLE_MINUTES,
    )
    times = Time(samples)
    frame = AltAz(obstime=times, location=location, pressure=0.0 * u.hPa)
    coordinates = SkyCoord(
        ra=np.fromiter((result.star.ra_deg for result in results), dtype=float) * u.deg,
        dec=np.fromiter((result.star.dec_deg for result in results), dtype=float) * u.deg,
        frame="icrs",
    )

    rises: list[datetime | None] = [None] * len(results)
    sets: list[datetime | None] = [None] * len(results)
    always_above: list[bool] = [False] * len(results)
    local_timezone = reference.tzinfo

    for chunk_start in range(0, len(results), CATALOG_CHUNK_SIZE):
        chunk_stop = min(chunk_start + CATALOG_CHUNK_SIZE, len(results))
        horizontal = coordinates[chunk_start:chunk_stop, np.newaxis].transform_to(frame)
        chunk_altitudes = np.asarray(horizontal.alt.deg)
        for offset, altitudes in enumerate(chunk_altitudes):
            result_index = chunk_start + offset
            above = altitudes >= minimum_altitude_deg
            if bool(np.all(above)):
                always_above[result_index] = True
                continue

            upward_indices = np.flatnonzero((~above[:-1]) & above[1:])
            downward_indices = np.flatnonzero(above[:-1] & (~above[1:]))
            upward_times = [
                _interpolate_crossing(samples, altitudes, int(index), minimum_altitude_deg)
                for index in upward_indices
            ]
            downward_times = [
                _interpolate_crossing(samples, altitudes, int(index), minimum_altitude_deg)
                for index in downward_indices
            ]

            if results[result_index].altitude_start_deg >= minimum_altitude_deg:
                eligible_rises = [instant for instant in upward_times if instant <= reference_utc]
                eligible_sets = [instant for instant in downward_times if instant >= reference_utc]
                rise = eligible_rises[-1] if eligible_rises else None
                setting = eligible_sets[0] if eligible_sets else None
            else:
                eligible_rises = [instant for instant in upward_times if instant >= reference_utc]
                rise = eligible_rises[0] if eligible_rises else None
                eligible_sets = (
                    [instant for instant in downward_times if instant > rise]
                    if rise is not None
                    else []
                )
                setting = eligible_sets[0] if eligible_sets else None

            rises[result_index] = (
                rise.astimezone(local_timezone) if rise is not None else None
            )
            sets[result_index] = (
                setting.astimezone(local_timezone) if setting is not None else None
            )

    return rises, sets, always_above


def _enrich_results(
    results: Sequence[VisibilityResult],
    *,
    window: ObservationWindow,
    location: EarthLocation,
    minimum_altitude_deg: float,
) -> list[VisibilityResult]:
    if not results:
        return []

    stars = [result.star for result in results]
    coordinates = SkyCoord(
        ra=np.fromiter((star.ra_deg for star in stars), dtype=float) * u.deg,
        dec=np.fromiter((star.dec_deg for star in stars), dtype=float) * u.deg,
        frame="icrs",
    )
    computed_constellations = np.atleast_1d(
        coordinates.get_constellation(short_name=True)
    )
    maximum_solar_separation_dates = _maximum_solar_separation_dates(
        stars, window.start_local.year
    )
    if window.start_local.tzinfo is None:
        raise ValueError("la plage d'observation doit avoir un fuseau horaire")
    best_seasonal_visibility_dates = _best_seasonal_visibility_dates(
        stars,
        window.start_local.year,
        location=location,
        timezone_info=window.start_local.tzinfo,
    )
    rises, sets, always_above = _threshold_crossings(
        results,
        location=location,
        reference=window.start_local,
        minimum_altitude_deg=minimum_altitude_deg,
    )

    return [
        replace(
            result,
            constellation=(
                result.star.constellation or str(computed_constellations[index])
            ),
            maximum_solar_separation_date=maximum_solar_separation_dates[index],
            best_seasonal_visibility_date=best_seasonal_visibility_dates[index],
            opposition_date=None,
            rises_above_minimum_local=rises[index],
            sets_below_minimum_local=sets[index],
            always_above_minimum=always_above[index],
        )
        for index, result in enumerate(results)
    ]


def compute_visibility(
    stars: Sequence[CatalogObject],
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
    results.sort(
        key=lambda result: (
            result.star.magnitude_v if result.star.magnitude_v is not None else float("inf"),
            result.star.name.casefold(),
        )
    )
    return _enrich_results(
        results,
        window=window,
        location=location,
        minimum_altitude_deg=field_of_view.altitude_lower_deg,
    )
