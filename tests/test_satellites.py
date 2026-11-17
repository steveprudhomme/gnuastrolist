# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Contrôles hors réseau : références Vallado et géométries synthétiques identifiées."""
from __future__ import annotations

import csv
import gzip
import io
import json
from datetime import datetime, timedelta, timezone
from importlib import resources

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import ITRS, TEME, AltAz, CartesianRepresentation, EarthLocation, get_sun
from astropy.time import Time
from astropy.utils import iers
from sgp4.api import Satrec

from gnu_astrolist import satellites
from gnu_astrolist.models import FieldOfView, ObservationWindow
from gnu_astrolist.satellites import (
    compute_satellite_visibility,
    eligible_elements,
    load_satellite_elements,
    parse_gp,
)


@pytest.fixture(autouse=True)
def offline_iers():
    with iers.conf.set_temp('auto_download', False), iers.conf.set_temp('auto_max_age', None):
        yield


@pytest.fixture
def record():
    # Cas public Vanguard 1, SGP4-VER.TLE de Vallado livré avec sgp4 2.25.
    return dict(OBJECT_NAME='VANGUARD 1', OBJECT_ID='1958-002B',
                EPOCH='2000-06-27T18:50:19.733568', MEAN_MOTION=10.82419157,
                ECCENTRICITY=0.1859667, INCLINATION=34.2682, RA_OF_ASC_NODE=348.7242,
                ARG_OF_PERICENTER=331.7664, MEAN_ANOMALY=19.3264, EPHEMERIS_TYPE=0,
                CLASSIFICATION_TYPE='U', NORAD_CAT_ID=5, ELEMENT_SET_NO=475,
                REV_AT_EPOCH=41366, BSTAR=0.000028098, MEAN_MOTION_DOT=0.00000023,
                MEAN_MOTION_DDOT=0)


def as_csv(records):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(records[0]))
    writer.writeheader()
    writer.writerows(records)
    return stream.getvalue()


def test_csv_and_json_normalization(record):
    left, = parse_gp([record])
    right, = parse_gp(as_csv([record]))
    assert left.record == right.record
    assert left.norad_id == 5
    assert left.cospar_id == '1958-002B'
    assert isinstance(left.epoch_jd_utc, float)
    assert left.record['TIME_SYSTEM'] == 'UTC'
    assert left.record['REF_FRAME'] == 'TEME'
    assert left.record['MEAN_ELEMENT_THEORY'] == 'SGP4'
    assert left.record['CENTER_NAME'] == 'EARTH'
    assert 'TIME_SYSTEM' not in record  # L'entrée n'est pas modifiée.


@pytest.mark.parametrize('suffix', ['', 'Z', '+00:00'])
@pytest.mark.parametrize('fraction', ['', '.123456789'])
def test_epoch_formats(record, suffix, fraction):
    record['EPOCH'] = '2026-11-17T00:00:00' + fraction + suffix
    element, = parse_gp([record])
    assert element.record['EPOCH'] == '2026-11-17T00:00:00' + fraction
    assert element.epoch_jd_utc == Time('2026-11-17T00:00:00' + fraction).jd


@pytest.mark.parametrize('number', [1, 100000, 339999, 340000, 123456789, 999999999])
def test_extended_norad_is_not_alpha5(record, number):
    record['NORAD_CAT_ID'] = number
    item, = parse_gp([record])
    assert item.norad_id == number
    assert item.record['NORAD_CAT_ID'] == number
    times = Time(['2000-06-27T18:50:19.733568'])
    assert np.all(np.isfinite(satellites._propagate_teme(item, times).cartesian.xyz))


@pytest.mark.parametrize('key,value', [
    ('TIME_SYSTEM', 'TAI'), ('REF_FRAME', 'GCRF'), ('MEAN_ELEMENT_THEORY', 'SDP4'),
    ('CENTER_NAME', 'SUN'), ('REF_FRAME', ''), ('EPOCH', '2026-02-30T00:00:00'),
    ('EPOCH', '2026-11-17T00:00:00-05:00'), ('NORAD_CAT_ID', 'A0001'),
    ('NORAD_CAT_ID', 1.5), ('NORAD_CAT_ID', True), ('NORAD_CAT_ID', 0),
    ('NORAD_CAT_ID', 1000000000), ('ECCENTRICITY', 1), ('MEAN_MOTION', 0),
    ('INCLINATION', 181), ('BSTAR', float('nan')), ('MEAN_MOTION_DDOT', float('inf')),
    ('OBJECT_ID', '98067A'), ('OBJECT_NAME', None), ('EPHEMERIS_TYPE', 2),
    ('ELEMENT_SET_NO', -1), ('REV_AT_EPOCH', 1.2), ('CLASSIFICATION_TYPE', ''),
    ('RA_OF_ASC_NODE', 360),
])
def test_reject_malformed_fields(record, key, value):
    record[key] = value
    with pytest.raises(ValueError):
        parse_gp([record])


@pytest.mark.parametrize('identity', ['', None, '  '])
def test_missing_cospar_not_invented(record, identity):
    record['OBJECT_ID'] = identity
    item, = parse_gp([record])
    assert item.cospar_id is None
    assert item.record['OBJECT_ID'] == ''
    other = dict(record, NORAD_CAT_ID=6)
    assert len(parse_gp([record, other])) == 2


def test_duplicates_and_schema(record):
    with pytest.raises(ValueError, match='dupliquée'):
        parse_gp([record, record])
    with pytest.raises(ValueError, match='dupliquée'):
        parse_gp([record, dict(record, NORAD_CAT_ID=6)])
    with pytest.raises(ValueError, match='dupliquée'):
        parse_gp([record, dict(record, OBJECT_ID='1958-002C')])
    for payload in ({}, [None], [dict(record, EPOCH=None)]):
        with pytest.raises(ValueError):
            parse_gp(payload)
    for key in record:
        incomplete = dict(record)
        del incomplete[key]
        with pytest.raises(ValueError):
            parse_gp([incomplete])
    with pytest.raises(ValueError):
        parse_gp(as_csv([record]).replace('OBJECT_NAME,', 'OBJECT_ID,'))
    with pytest.raises(ValueError):
        parse_gp(as_csv([record]).rstrip() + ',unexpected')


@pytest.mark.parametrize('compressed', [False, True])
@pytest.mark.parametrize('kind', ['csv', 'json', 'bundle'])
def test_local_loading(record, tmp_path, compressed, kind):
    content = as_csv([record]) if kind == 'csv' else json.dumps(
        [record] if kind == 'json' else dict(schema_version=1, gp=[record], satcat=[], sources={}))
    data = content.encode('utf-8')
    path = tmp_path / ('gp.' + kind + ('.gz' if compressed else ''))
    path.write_bytes(gzip.compress(data) if compressed else data)
    assert load_satellite_elements(path)[0].norad_id == 5


def test_missing_local_file(tmp_path):
    path = tmp_path / 'missing.csv'
    with pytest.raises(ValueError, match='Fichier GP local illisible') as caught:
        load_satellite_elements(path)
    assert isinstance(caught.value.__cause__, FileNotFoundError)
    assert str(path) in str(caught.value)


@pytest.mark.parametrize('data', [
    b'\xff',
    b'\x1f\x8b',
    b'\x1f\x8b\x00' + b'\x00' * 10,
    b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03\x07' + b'\x00' * 8,
])
def test_unreadable_local_file(tmp_path, data):
    path = tmp_path / 'broken.gp'
    path.write_bytes(data)
    with pytest.raises(ValueError, match='Fichier GP local illisible') as caught:
        load_satellite_elements(path)
    assert caught.value.__cause__ is not None


def test_bundle_default_and_version(record, tmp_path, monkeypatch):
    path = tmp_path / 'space_objects.json.gz'
    path.write_bytes(gzip.compress(json.dumps(dict(schema_version=1, gp=[record])).encode()))
    calls = []

    def resource(name):
        calls.append(name)
        return path

    monkeypatch.setattr(satellites, 'catalog_resource', resource)
    assert load_satellite_elements()[0].norad_id == 5
    assert calls == ['space_objects.json.gz']
    for version in (2, True, None):
        path.write_bytes(gzip.compress(json.dumps(dict(schema_version=version, gp=[record])).encode()))
        with pytest.raises(ValueError, match='Version'):
            load_satellite_elements()


def test_packaged_snapshot_has_unique_identities():
    elements = load_satellite_elements()
    assert len(elements) == 737
    assert len({item.norad_id for item in elements}) == len(elements)
    identities = [item.cospar_id for item in elements if item.cospar_id]
    assert len(set(identities)) == len(identities)
    assert all(np.isfinite(item.epoch_jd_utc) for item in elements)


def test_age_entire_window_and_both_directions(record):
    element, = parse_gp([record])
    epoch = element.epoch_jd_utc
    for offsets, expected in [([-7, 7], True), ([-7.001, 0], False),
                              ([0, 7.001], False), ([8, 9], False)]:
        usable, excluded = eligible_elements((element,), Time(epoch + np.array(offsets), format='jd'))
        assert usable == ((element,) if expected else ())
        assert excluded == (() if expected else (element,))
    for limit in (0, -1, float('nan'), float('inf')):
        with pytest.raises(ValueError):
            eligible_elements((element,), Time(epoch, format='jd'), limit)
    with pytest.raises(ValueError):
        eligible_elements((element,), Time([], format='jd'))


def test_vallado_reference_teme_vectors(record):
    # Référence indépendante numérique tcppver.out, cas 5, 0/360/720 minutes.
    text = resources.files('sgp4').joinpath('tcppver.out').read_text()
    expected = np.array([[float(x) for x in line.split()[1:4]]
                         for line in text.splitlines()[1:4]])
    element, = parse_gp([record])
    times = Time(element._satrec.jdsatepoch, element._satrec.jdsatepochF
                 + np.array([0, 360, 720]) / 1440, format='jd', scale='utc')
    propagated = satellites._propagate_teme(element, times).cartesian.xyz.to_value(u.km).T
    np.testing.assert_allclose(propagated, expected, atol=2e-7, rtol=0)


def test_topocentric_origin_manual_rotation(record):
    element, = parse_gp([record])
    times = Time(['2000-06-27T18:50:19.733568', '2000-06-27T18:50:24.733568'])
    lat, lon = np.deg2rad([45.57, -73.68])
    location = EarthLocation.from_geodetic(lon * u.rad, lat * u.rad, 20 * u.m)
    horizontal, _ = satellites._horizontal(element, times, location)
    # Propagation de référence TLE, puis rotation ENU manuelle après ITRS-site.
    tle = resources.files('sgp4').joinpath('SGP4-VER.TLE').read_text().splitlines()
    satellite = Satrec.twoline2rv(tle[2], tle[3])
    errors, positions, _ = satellite.sgp4_array(times.jd1, times.jd2)
    assert not np.any(errors)
    earth_fixed = TEME(CartesianRepresentation(positions.T * u.km), obstime=times).transform_to(
        ITRS(obstime=times)).cartesian.xyz.to_value(u.km)
    x, y, z = earth_fixed - location.get_itrs(times).cartesian.xyz.to_value(u.km)
    east = -np.sin(lon) * x + np.cos(lon) * y
    north = -np.sin(lat) * np.cos(lon) * x - np.sin(lat) * np.sin(lon) * y + np.cos(lat) * z
    up = np.cos(lat) * np.cos(lon) * x + np.cos(lat) * np.sin(lon) * y + np.sin(lat) * z
    np.testing.assert_allclose(horizontal.alt.deg, np.rad2deg(np.arctan2(up, np.hypot(east, north))),
                               atol=1e-8, rtol=0)
    np.testing.assert_allclose(horizontal.az.deg, np.rad2deg(np.arctan2(east, north)) % 360,
                               atol=1e-8, rtol=0)
    np.testing.assert_allclose(horizontal.distance.to_value(u.km), np.sqrt(x*x + y*y + z*z),
                               atol=1e-8, rtol=0)


@pytest.fixture
def synthetic_geometry(record, monkeypatch):
    """Positions Alt/Az synthétiques, sans prétendre à un passage observé."""
    element, = parse_gp([record])
    start = datetime(2000, 6, 27, 18, 50, tzinfo=timezone.utc)
    window = ObservationWindow(start, start + timedelta(seconds=20), 'UTC')
    fov = FieldOfView(100, 45, 20, 90)
    seen = []

    def horizontal(item, times, location):
        seen.append(times)
        altaz = AltAz(az=np.array([100, 100, 200, 100, 100]) * u.deg,
                     alt=np.array([20, 40, 80, 30, 10]) * u.deg,
                     distance=np.array([1000, 900, 800, 700, 600]) * u.km,
                     obstime=times, location=location, pressure=0 * u.hPa)
        return altaz, None

    monkeypatch.setattr(satellites, '_horizontal', horizontal)
    monkeypatch.setattr(satellites, '_solar_conditions', lambda *args: (
        np.array([-10, 0, -10, -10, -10]), np.array([False, True, True, True, True])))
    return element, window, fov, seen


def test_infield_maximum_unknown_magnitude_and_no_season(synthetic_geometry):
    element, window, fov, _ = synthetic_geometry
    result, = compute_satellite_visibility((element,), window, 45, -73, 0, fov)
    assert result.position_reference_time == window.start_local + timedelta(seconds=5)
    assert result.star.norad_id == 5
    assert result.star.object_type == 'Satellite'
    assert result.star.magnitude_v is None
    assert result.star.passband == ''
    assert result.star.magnitude_source == ''
    assert result.magnitude_reference_time is None
    assert not result.magnitude_estimated
    assert result.opposition_date is None
    assert result.maximum_solar_separation_date is None
    assert result.best_seasonal_visibility_date is None
    assert result.rises_above_minimum_local is None
    assert result.sets_below_minimum_local is None
    assert '900.0 km' in result.satellite_details
    assert '40.00°' in result.satellite_details
    assert 'échantillons' in result.satellite_details
    assert 'continu non établi' in result.satellite_details
    assert compute_satellite_visibility((element,), window, 45, -73, 0, fov, max_magnitude=100) == []


def test_optical_criteria_must_coincide(synthetic_geometry):
    element, window, fov, _ = synthetic_geometry
    result, = compute_satellite_visibility((element,), window, 45, -73, 0, fov, optical_only=True)
    assert result.position_reference_time == window.start_local + timedelta(seconds=15)
    assert '700.0 km' in result.satellite_details
    assert 'Soleil -10.00°' in result.satellite_details
    assert 'éclairé' in result.satellite_details
    # Aucun échantillon accepté si le seuil est abaissé sous -10°.
    assert compute_satellite_visibility((element,), window, 45, -73, 0, fov,
                                        optical_only=True, max_sun_altitude=-11) == []


def test_no_infield_sample(synthetic_geometry):
    element, window, _, _ = synthetic_geometry
    assert compute_satellite_visibility((element,), window, 45, -73, 0,
                                        FieldOfView(0, 45, 10, 90)) == []


def test_cylindrical_shadow_same_itrs_frame():
    times = Time(['2000-06-27T18:50:19'] * 3)
    site = EarthLocation.from_geodetic(0 * u.deg, 45 * u.deg)
    direction = get_sun(times).transform_to(ITRS(obstime=times)).cartesian.xyz.to_value(u.km)
    direction /= np.linalg.norm(direction, axis=0)
    perpendicular = np.cross(direction[:, 0], [0, 0, 1])
    perpendicular /= np.linalg.norm(perpendicular)
    position = np.column_stack([7000 * direction[:, 0], -7000 * direction[:, 1],
                                -7000 * direction[:, 2] + 7000 * perpendicular])
    geocentric = ITRS(CartesianRepresentation(position * u.km), obstime=times)
    sun_alt, sunlit = satellites._solar_conditions(times, site, geocentric)
    assert sunlit.tolist() == [True, False, True]
    assert np.all(np.isfinite(sun_alt))


@pytest.mark.parametrize('kwargs', [dict(lat=91), dict(lon=-181), dict(elevation_m=np.nan),
    dict(sample_seconds=0), dict(sample_seconds=np.inf), dict(max_sun_altitude=91),
    dict(max_magnitude=np.nan), dict(sample_seconds=0.0001), dict(sample_seconds=1e-320)])
def test_visibility_input_validation(synthetic_geometry, kwargs):
    element, window, fov, _ = synthetic_geometry
    arguments = dict(elements=(element,), window=window, lat=45, lon=-73, elevation_m=0, fov=fov)
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        compute_satellite_visibility(**arguments)


def test_window_and_endpoint_validation(record, monkeypatch):
    element, = parse_gp([record])
    start = datetime(2000, 6, 27, 18, 50, tzinfo=timezone.utc)
    fov = FieldOfView(180, 45, 360, 90)
    for end in (start, start - timedelta(seconds=1)):
        with pytest.raises(ValueError):
            compute_satellite_visibility((element,), ObservationWindow(start, end, 'UTC'),
                                         45, -73, 0, fov)
    with pytest.raises(ValueError, match='fuseau'):
        compute_satellite_visibility((), ObservationWindow(start.replace(tzinfo=None),
                                    start + timedelta(seconds=1), 'UTC'), 45, -73, 0, fov)
    seen = []
    real = satellites._horizontal

    def capture(item, times, location):
        seen.append(times)
        return real(item, times, location)

    monkeypatch.setattr(satellites, '_horizontal', capture)
    compute_satellite_visibility((element,), ObservationWindow(start, start + timedelta(seconds=11),
                                  'UTC'), 45, -73, 0, fov)
    np.testing.assert_allclose((seen[0] - Time(start)).sec, [0, 5, 10, 11], atol=1e-9)


def test_sgp4_errors_are_identified(record):
    element, = parse_gp([dict(record, NORAD_CAT_ID=999999999, MEAN_MOTION=40, ECCENTRICITY=0.01)])
    with pytest.raises(ValueError, match=r'NORAD 999999999 : SGP4 [1-6]'):
        satellites._propagate_teme(element, Time([record['EPOCH']]))


def test_nonfinite_sgp4_position_rejected(record):
    class BadSatellite:
        def sgp4_array(self, *args):
            return np.array([0]), np.full((1, 3), np.nan), np.zeros((1, 3))

    element, = parse_gp([record])
    bad = satellites.SatelliteElements(element.norad_id, element.cospar_id, element.name,
                                       element.epoch_jd_utc, element.record, BadSatellite())
    with pytest.raises(ValueError, match='non finie'):
        satellites._propagate_teme(bad, Time([record['EPOCH']]))


def test_real_public_result_at_subsatellite_site(record):
    # Site synthétique choisi sous le satellite, sans prétendre à une observation.
    element, = parse_gp([dict(record, NORAD_CAT_ID=123456789)])
    instant = Time([record['EPOCH']])
    earth_fixed = satellites._propagate_teme(element, instant).transform_to(ITRS(obstime=instant))
    position = earth_fixed.cartesian.xyz[:, 0]
    subpoint = EarthLocation.from_geocentric(*position)
    start = instant[0].to_datetime(timezone=timezone.utc)
    window = ObservationWindow(start, start + timedelta(seconds=10), 'UTC')
    result, = compute_satellite_visibility((element,), window, subpoint.lat.deg, subpoint.lon.deg,
                                           0, FieldOfView(180, 45, 360, 90))
    assert result.star.norad_id == 123456789
    assert result.star.catalog_designation == 'NORAD 123456789'
    assert result.altitude_start_deg > 89.99
    assert np.isfinite(result.star.ra_deg)
    assert np.isfinite(result.star.dec_deg)
    assert result.position_reference_time == start
    assert result.star.magnitude_v is None
