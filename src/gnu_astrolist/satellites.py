# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Éléments GP et passages SGP4 géométriques, sans accès réseau.

Conventions CelesTrak GP : UTC, TEME, SGP4, EARTH lorsque ces champs
sont omis. La soustraction du site en ITRS suit l'exemple satellites
Astropy; l'ombre cylindrique ne modélise ni pénombre ni réfraction.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import math
import re
import zlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.coordinates import (
    GCRS,
    ITRS,
    TEME,
    AltAz,
    CartesianRepresentation,
    EarthLocation,
    get_sun,
)
from astropy.time import Time
from sgp4.api import SGP4_ERRORS, WGS72, Satrec

from .catalog_resources import catalog_resource
from .models import FieldOfView, ObservationWindow, SatelliteTarget, VisibilityResult
from .validation import (
    MAX_AGE_HOURS,
    finite_number,
    sample_datetimes,
    sampling_plan,
    validate_magnitude,
    validate_observer,
)

_REQUIRED = {
    'OBJECT_NAME', 'OBJECT_ID', 'EPOCH', 'MEAN_MOTION', 'ECCENTRICITY',
    'INCLINATION', 'RA_OF_ASC_NODE', 'ARG_OF_PERICENTER', 'MEAN_ANOMALY',
    'EPHEMERIS_TYPE', 'CLASSIFICATION_TYPE', 'NORAD_CAT_ID', 'ELEMENT_SET_NO',
    'REV_AT_EPOCH', 'BSTAR', 'MEAN_MOTION_DOT', 'MEAN_MOTION_DDOT',
}
_DEFAULTS = dict(TIME_SYSTEM='UTC', REF_FRAME='TEME', MEAN_ELEMENT_THEORY='SGP4',
                 CENTER_NAME='EARTH')
_FLOATS = ('MEAN_MOTION', 'ECCENTRICITY', 'INCLINATION', 'RA_OF_ASC_NODE',
           'ARG_OF_PERICENTER', 'MEAN_ANOMALY', 'BSTAR', 'MEAN_MOTION_DOT',
           'MEAN_MOTION_DDOT')
MAX_SAMPLES = 20000


@dataclass(frozen=True)
class SatelliteElements:
    """Identité publique indépendante du numéro interne utilisé par SGP4."""

    norad_id: int
    cospar_id: str | None
    name: str
    epoch_jd_utc: float
    record: dict
    _satrec: Satrec = field(repr=False, compare=False)


def _integer(value, key: str, lower: int, upper: int) -> int:
    text = str(value)
    if not re.fullmatch(r'[0-9]+', text):
        raise ValueError(f'{key} : entier décimal requis')
    number = int(text)
    if not lower <= number <= upper:
        raise ValueError(f'{key} hors limites')
    return number


def parse_gp(payload) -> tuple[SatelliteElements, ...]:
    """Valide une liste OMM JSON ou un CSV GP, sans déduire de photométrie.

    Les identifiants NORAD et COSPAR non vides doivent être uniques.
    L'époque sans suffixe est UTC par convention GP; seuls Z et +00:00
    sont acceptés comme suffixes explicites. Les fractions sont conservées.
    """
    if isinstance(payload, str):
        reader = csv.DictReader(io.StringIO(payload.lstrip('\ufeff')))
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not _REQUIRED.issubset(fields):
            raise ValueError('Champs CSV GP absents ou dupliqués')
        payload = list(reader)
    if not isinstance(payload, list):
        raise ValueError('Une liste OMM ou un CSV GP est requis')
    result, numbers, designations = [], set(), set()
    for raw in payload:
        if not isinstance(raw, dict) or not _REQUIRED.issubset(raw) or None in raw:
            raise ValueError('Champs GP absents ou ligne incorrecte')
        record = dict(raw)
        for key, expected in _DEFAULTS.items():
            if key in record and record[key] != expected:
                raise ValueError(f'{key} doit être {expected}')
            record[key] = expected
        number = _integer(record['NORAD_CAT_ID'], 'NORAD_CAT_ID', 1, 999999999)
        identity = record['OBJECT_ID']
        if identity is not None and not isinstance(identity, str):
            raise ValueError('OBJECT_ID invalide')
        identity = (identity.strip() or None) if identity else None
        if identity and not re.fullmatch(r'[0-9]{4}-[0-9]{3}[A-Z]{1,3}', identity):
            raise ValueError('OBJECT_ID COSPAR invalide')
        if number in numbers or (identity and identity in designations):
            raise ValueError(f'Identité NORAD/COSPAR dupliquée : {number} / {identity}')
        name = record['OBJECT_NAME']
        if not isinstance(name, str) or not name.strip():
            raise ValueError('OBJECT_NAME vide ou invalide')
        epoch = record['EPOCH']
        if not isinstance(epoch, str) or not re.fullmatch(
            r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}'
            r'(?:\.[0-9]+)?(?:Z|\+00:00)?', epoch
        ):
            raise ValueError('EPOCH UTC invalide')
        epoch = re.sub(r'(Z|\+00:00)$', '', epoch)
        try:
            # Python 3.10 limite les fractions acceptées par datetime. La regex
            # les a validées; ne vérifier ici que le calendrier, puis laisser
            # Astropy lire la chaîne complète sans perte de chiffres.
            datetime.fromisoformat(epoch.partition('.')[0])
            instant = Time(epoch, format='isot', scale='utc')
            values = {key: float(record[key]) for key in _FLOATS}
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError('Époque ou nombre GP invalide') from exc
        if not all(math.isfinite(value) for value in values.values()):
            raise ValueError('Valeur GP non finie')
        if not (values['MEAN_MOTION'] > 0 and 0 <= values['ECCENTRICITY'] < 1
                and 0 <= values['INCLINATION'] <= 180):
            raise ValueError('Orbite GP hors limites')
        if any(not 0 <= values[key] < 360 for key in
               ('RA_OF_ASC_NODE', 'ARG_OF_PERICENTER', 'MEAN_ANOMALY')):
            raise ValueError('Angle GP hors limites')
        for key in ('EPHEMERIS_TYPE', 'ELEMENT_SET_NO', 'REV_AT_EPOCH'):
            record[key] = _integer(record[key], key, 0, 999999999)
        if record['EPHEMERIS_TYPE'] != 0 or record['CLASSIFICATION_TYPE'] not in ('U', 'C', 'S'):
            raise ValueError('Type GP non pris en charge')
        record.update(values)
        record.update(NORAD_CAT_ID=number, OBJECT_ID=identity or '',
                      OBJECT_NAME=name.strip(), EPOCH=epoch)
        sat = Satrec()
        # Le numéro technique ne participe pas à la dynamique. Ne jamais passer
        # un NORAD étendu à l'encodage Alpha-5 interne de la bibliothèque.
        sat.sgp4init(
            WGS72, 'i', 1, float((instant.jd1 - 2433281.5) + instant.jd2),
            values['BSTAR'], values['MEAN_MOTION_DOT'] * 2 * math.pi / 1440**2,
            values['MEAN_MOTION_DDOT'] * 2 * math.pi / 1440**3,
            values['ECCENTRICITY'], math.radians(values['ARG_OF_PERICENTER']),
            math.radians(values['INCLINATION']), math.radians(values['MEAN_ANOMALY']),
            values['MEAN_MOTION'] * math.pi / 720,
            math.radians(values['RA_OF_ASC_NODE']),
        )
        result.append(SatelliteElements(number, identity, name.strip(), float(instant.jd),
                                        record, sat))
        numbers.add(number)
        if identity:
            designations.add(identity)
    return tuple(result)


def load_satellite_elements(path=None) -> tuple[SatelliteElements, ...]:
    """Charge le conteneur spatial embarqué ou un CSV/JSON local, avec ou sans gzip."""
    resource = catalog_resource('space_objects.json.gz') if path is None else Path(path)
    try:
        with resource.open('rb') as stream:
            data = stream.read()
        if data.startswith(b'\x1f\x8b'):
            data = gzip.decompress(data)
        text = data.decode('utf-8-sig')
    except (OSError, UnicodeError, EOFError, zlib.error) as exc:
        raise ValueError(f'Fichier GP local illisible : {resource}') from exc
    if text.lstrip().startswith(('[', '{')):
        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                if type(payload.get('schema_version')) is not int or payload['schema_version'] != 1:
                    raise ValueError('Version du conteneur spatial non prise en charge')
                payload = payload.get('gp')
            return parse_gp(payload)
        except json.JSONDecodeError as exc:
            raise ValueError('JSON GP invalide') from exc
    return parse_gp(text)


def eligible_elements(elements, times, max_epoch_hours=168):
    """Sépare les éléments selon leur âge absolu sur toute la fenêtre UTC."""
    max_epoch_hours = finite_number(max_epoch_hours, 'âge maximal GP', 0, MAX_AGE_HOURS)
    if max_epoch_hours <= 0:
        raise ValueError('max_epoch_hours doit être fini et positif')
    dates = np.atleast_1d(Time(times).utc.jd)
    if not dates.size or not np.all(np.isfinite(dates)):
        raise ValueError('Instants finis non vides requis')
    usable, excluded = [], []
    for item in elements:
        age = np.max(np.abs(dates - item.epoch_jd_utc)) * 24
        (usable if math.isfinite(age) and age <= max_epoch_hours else excluded).append(item)
    return tuple(usable), tuple(excluded)


def _propagate_teme(element, times):
    errors, positions, velocities = element._satrec.sgp4_array(
        np.atleast_1d(times.utc.jd1), np.atleast_1d(times.utc.jd2)
    )
    if np.any(errors):
        code = int(errors[np.flatnonzero(errors)[0]])
        raise ValueError(f'NORAD {element.norad_id} : SGP4 {code} '
                         f'({SGP4_ERRORS.get(code, "erreur inconnue")})')
    if not np.all(np.isfinite(positions)) or not np.all(np.isfinite(velocities)):
        raise ValueError(f'NORAD {element.norad_id} : position/vitesse SGP4 non finie')
    return TEME(CartesianRepresentation(positions.T * u.km), obstime=times)


def _horizontal(element, times, location):
    geocentric = _propagate_teme(element, times).transform_to(ITRS(obstime=times))
    relative = geocentric.cartesian.without_differentials() - location.get_itrs(times).cartesian
    topocentric = ITRS(relative, obstime=times, location=location)
    horizontal = topocentric.transform_to(AltAz(obstime=times, location=location,
                                               pressure=0 * u.hPa))
    if not np.all(np.isfinite(horizontal.cartesian.xyz.value)):
        raise ValueError(f'NORAD {element.norad_id} : coordonnées non finies')
    return horizontal, geocentric


def _solar_geometry(times, location):
    sun = get_sun(times)
    sun_altitude = sun.transform_to(AltAz(obstime=times, location=location,
                                        pressure=0 * u.hPa)).alt.deg
    sun_vector = sun.transform_to(ITRS(obstime=times)).cartesian.xyz.to_value(u.km)
    direction = sun_vector / np.linalg.norm(sun_vector, axis=0)
    if not np.all(np.isfinite(sun_altitude)) or not np.all(np.isfinite(direction)):
        raise ValueError('Géométrie solaire non finie')
    return sun_altitude, direction


def _solar_conditions(times, location, geocentric, solar_geometry=None):
    sun_altitude, direction = (
        _solar_geometry(times, location) if solar_geometry is None else solar_geometry
    )
    position = geocentric.cartesian.xyz.to_value(u.km)
    projection = np.sum(position * direction, axis=0)
    axis_distance = np.linalg.norm(position - direction * projection, axis=0)
    # Rayon équatorial WGS72; approximation cylindrique, Soleil à l'infini.
    sunlit = ~((projection < 0) & (axis_distance < 6378.135))
    if not np.all(np.isfinite(sun_altitude)) or not np.all(np.isfinite(axis_distance)):
        raise ValueError('Géométrie solaire non finie')
    return sun_altitude, sunlit


def compute_satellite_visibility(
    elements, window: ObservationWindow, lat: float, lon: float, elevation_m: float,
    fov: FieldOfView, sample_seconds=5, max_magnitude=None, optical_only=False,
    max_sun_altitude=-6,
) -> list[VisibilityResult]:
    """Retient un maximum échantillonné dans le champ, sans magnitude estimée.

    Le filtre optique exige simultanément champ, éclairage et hauteur solaire.
    Les premiers/derniers instants rapportés sont des échantillons, pas les
    bornes d'un passage continu. Le contrôle d'âge appartient à l'appelant.
    """
    validate_observer(lat, lon, elevation_m)
    validate_magnitude(max_magnitude)
    finite_number(max_sun_altitude, 'hauteur solaire', -90, 90)
    sampling_plan(window, sample_seconds, MAX_SAMPLES, '--satellite-step-seconds')
    start = window.start_local
    if max_magnitude is not None or not elements:
        return []
    dates = sample_datetimes(window, sample_seconds, MAX_SAMPLES, '--satellite-step-seconds')
    times = Time(dates)
    location = EarthLocation.from_geodetic(lon * u.deg, lat * u.deg, elevation_m * u.m)
    results = []
    solar_geometry = None
    for element in elements:
        horizontal, geocentric = _horizontal(element, times, location)
        altitude, azimuth = horizontal.alt.deg, horizontal.az.deg
        inside = fov.contains(azimuth, altitude)
        if not np.any(inside):
            continue
        if solar_geometry is None:
            solar_geometry = _solar_geometry(times, location)
        sun_altitude, sunlit = _solar_conditions(times, location, geocentric, solar_geometry)
        accepted = inside & sunlit & (sun_altitude <= max_sun_altitude) if optical_only else inside
        indices = np.flatnonzero(accepted)
        if not indices.size:
            continue
        best = int(indices[np.argmax(altitude[indices])])
        reference = dates[best].astimezone(start.tzinfo)
        # Transformation du rayon topocentrique, avec le site comme origine GCRS.
        site_pos, site_vel = location.get_gcrs_posvel(times[best])
        equatorial = horizontal[best].transform_to(GCRS(
            obstime=times[best], obsgeoloc=site_pos, obsgeovel=site_vel))
        target = SatelliteTarget(
            name=element.name, ra_deg=float(equatorial.ra.deg),
            dec_deg=float(equatorial.dec.deg), object_type='Satellite', magnitude_v=None,
            catalog_designation=f'NORAD {element.norad_id}', constellation='',
            apparent_major_arcmin=None, apparent_minor_arcmin=None, passband='',
            norad_id=element.norad_id, cospar_id=element.cospar_id or '',
            epoch_jd_utc=element.epoch_jd_utc,
        )
        in_indices = np.flatnonzero(inside)
        first = dates[int(in_indices[0])].astimezone(start.tzinfo).isoformat()
        last = dates[int(in_indices[-1])].astimezone(start.tzinfo).isoformat()
        details = (
            f'SGP4; maximum retenu échantillonné {altitude[best]:.2f}° à '
            f'{reference.isoformat()}; distance {horizontal.distance[best].to_value(u.km):.1f} km; '
            f'Soleil {sun_altitude[best]:.2f}°; '
            f'{"éclairé" if sunlit[best] else "dans l’ombre"} '
            f'(ombre cylindrique approximative); premier/dernier échantillons dans le champ : '
            f'{first} / {last}; pas {sample_seconds:g} s; passage continu non établi'
        )
        results.append(VisibilityResult(
            star=target, altitude_start_deg=float(altitude[0]),
            altitude_end_deg=float(altitude[-1]), azimuth_start_deg=float(azimuth[0]),
            azimuth_end_deg=float(azimuth[-1]), position_reference_time=reference,
            satellite_details=details,
        ))
    return results
