"""Calcul du résumé lunaire affiché avant la liste d'observation."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, time, timedelta, timezone

import astropy.units as u
import numpy as np
from astropy.coordinates import (
    AltAz,
    EarthLocation,
    GeocentricTrueEcliptic,
    get_body,
    get_sun,
)
from astropy.time import Time

from .models import MoonSummary, ObservationWindow

MOON_EVENT_SAMPLE_MINUTES = 5.0
STANDARD_HORIZON_REFRACTION_DEG = 34.0 / 60.0
MOON_REFERENCE_RADIUS_KM = 1_737.4
PHASE_NAMES = (
    "Nouvelle lune",
    "Premier croissant",
    "Premier quartier",
    "Lune gibbeuse croissante",
    "Pleine lune",
    "Lune gibbeuse décroissante",
    "Dernier quartier",
    "Dernier croissant",
)


def _phase_name(cycle_degrees: float) -> str:
    """Retourne l'une des huit phases à partir de l'élongation orientée."""

    phase_index = int(((cycle_degrees % 360.0) + 22.5) // 45.0) % len(PHASE_NAMES)
    return PHASE_NAMES[phase_index]


def _local_day_samples(window: ObservationWindow) -> list[datetime]:
    timezone_info = window.start_local.tzinfo
    if timezone_info is None:
        raise ValueError("la plage d'observation doit avoir un fuseau horaire")

    local_date = window.start_local.date()
    start_local = datetime.combine(local_date, time.min, tzinfo=timezone_info)
    end_local = datetime.combine(
        local_date + timedelta(days=1), time.min, tzinfo=timezone_info
    )
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)
    step = timedelta(minutes=MOON_EVENT_SAMPLE_MINUTES)
    samples = [start_utc]
    current = start_utc + step
    while current < end_utc:
        samples.append(current)
        current += step
    samples.append(end_utc)
    return samples


def _interpolate_horizon_crossing(
    samples: Sequence[datetime], apparent_upper_limb_altitudes: np.ndarray, index: int
) -> datetime:
    lower_altitude = float(apparent_upper_limb_altitudes[index])
    upper_altitude = float(apparent_upper_limb_altitudes[index + 1])
    difference = upper_altitude - lower_altitude
    fraction = 0.5 if difference == 0.0 else -lower_altitude / difference
    fraction = min(1.0, max(0.0, fraction))
    return samples[index] + (samples[index + 1] - samples[index]) * fraction


def _round_to_minute(instant: datetime) -> datetime:
    rounded = instant + timedelta(seconds=30)
    return rounded.replace(second=0, microsecond=0)


def _apparent_upper_limb_altitudes(
    geometric_center_altitudes_deg: np.ndarray, moon_distances_km: np.ndarray
) -> np.ndarray:
    """Applique le demi-diamètre variable et la réfraction standard de 34′."""

    semidiameters_deg = np.degrees(
        np.arcsin(MOON_REFERENCE_RADIUS_KM / moon_distances_km)
    )
    return (
        geometric_center_altitudes_deg
        + semidiameters_deg
        + STANDARD_HORIZON_REFRACTION_DEG
    )


def _daily_illumination_reference(window: ObservationWindow) -> datetime:
    """Retourne le midi local de la date de soirée associée à l'observation."""

    timezone_info = window.start_local.tzinfo
    if timezone_info is None:
        raise ValueError("la plage d'observation doit avoir un fuseau horaire")
    evening_date = window.start_local.date()
    if window.start_local.hour < 12:
        evening_date -= timedelta(days=1)
    return datetime.combine(evening_date, time(hour=12), tzinfo=timezone_info)


def _phase_and_illumination(reference: datetime) -> tuple[str, float]:
    instant = Time(reference)
    moon = get_body("moon", instant)
    sun = get_sun(instant)

    ecliptic_frame = GeocentricTrueEcliptic(equinox=instant)
    moon_longitude = moon.transform_to(ecliptic_frame).lon
    sun_longitude = sun.transform_to(ecliptic_frame).lon
    cycle_degrees = float((moon_longitude - sun_longitude).wrap_at(360 * u.deg).deg)

    elongation_radians = float(moon.separation(sun).rad)
    sun_distance_km = float(sun.distance.to_value(u.km))
    moon_distance_km = float(moon.distance.to_value(u.km))
    phase_angle = np.arctan2(
        sun_distance_km * np.sin(elongation_radians),
        moon_distance_km - sun_distance_km * np.cos(elongation_radians),
    )
    illumination_percent = float((1.0 + np.cos(phase_angle)) * 50.0)
    return _phase_name(cycle_degrees), illumination_percent


def compute_moon_summary(
    *,
    window: ObservationWindow,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
) -> MoonSummary:
    """Calcule la phase, l'illumination et les passages lunaires du jour local."""

    if not -90.0 <= latitude_deg <= 90.0:
        raise ValueError("la latitude doit être comprise entre -90 et 90 degrés")
    if not -180.0 <= longitude_deg <= 180.0:
        raise ValueError("la longitude doit être comprise entre -180 et 180 degrés")

    location = EarthLocation.from_geodetic(
        lon=longitude_deg * u.deg,
        lat=latitude_deg * u.deg,
        height=elevation_m * u.m,
    )
    samples = _local_day_samples(window)
    times = Time(samples)
    frame = AltAz(obstime=times, location=location, pressure=0.0 * u.hPa)
    moon = get_body("moon", times, location=location)
    geometric_center_altitudes = np.asarray(moon.transform_to(frame).alt.deg)
    moon_distances_km = np.asarray(moon.distance.to_value(u.km))
    apparent_upper_limb_altitudes = _apparent_upper_limb_altitudes(
        geometric_center_altitudes, moon_distances_km
    )
    above_horizon = apparent_upper_limb_altitudes >= 0.0

    rising_indices = np.flatnonzero((~above_horizon[:-1]) & above_horizon[1:])
    setting_indices = np.flatnonzero(above_horizon[:-1] & (~above_horizon[1:]))
    timezone_info = window.start_local.tzinfo
    if timezone_info is None:
        raise ValueError("la plage d'observation doit avoir un fuseau horaire")

    moonrise = (
        _round_to_minute(
            _interpolate_horizon_crossing(
                samples, apparent_upper_limb_altitudes, int(rising_indices[0])
            )
        ).astimezone(timezone_info)
        if rising_indices.size
        else None
    )
    moonset = (
        _round_to_minute(
            _interpolate_horizon_crossing(
                samples, apparent_upper_limb_altitudes, int(setting_indices[0])
            )
        ).astimezone(timezone_info)
        if setting_indices.size
        else None
    )
    phase_name, illumination_percent = _phase_and_illumination(window.start_local)
    daily_reference = _daily_illumination_reference(window)
    _, daily_illumination_percent = _phase_and_illumination(daily_reference)
    return MoonSummary(
        phase_name=phase_name,
        illumination_percent=illumination_percent,
        daily_illumination_percent=daily_illumination_percent,
        daily_illumination_reference_local=daily_reference,
        moonrise_local=moonrise,
        moonset_local=moonset,
        always_above_horizon=bool(np.all(above_horizon)),
        always_below_horizon=bool(np.all(~above_horizon)),
    )
