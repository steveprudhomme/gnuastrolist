# SPDX-FileCopyrightText: 2026 Steve Prud'Homme
# SPDX-License-Identifier: GPL-3.0-or-later
"""Plafond du champ : réglages publics et géométries explicitement synthétiques."""

from dataclasses import fields
from unittest.mock import Mock

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time
from pypdf import PdfReader

from gnu_astrolist import asteroids, cli, comets, satellites
from gnu_astrolist.application import (
    ApplicationDependencies,
    ObservationApplication,
    ObservationRequest,
    astronomical_context,
)
from gnu_astrolist.models import FieldOfView, VariableStar
from gnu_astrolist.time_utils import parse_observation_window
from gnu_astrolist.visibility import compute_visibility


@pytest.fixture(autouse=True)
def offline_context():
    with astronomical_context(True):
        yield


def bounded_field(minimum=20, maximum=80, **kwargs):
    return FieldOfView.from_automatic_center(
        azimuth_min_deg=0, azimuth_max_deg=360, minimum_altitude_deg=minimum,
        maximum_altitude_deg=maximum, **kwargs,
    )


def arguments():
    return ['--date', '2026-11-17', '--time-range', '21:00-21:01',
            '--lat', '45', '--lon', '0', '--az-min', '0', '--az-max', '360',
            '--min-altitude', '20', '--objects', 'messier', '--offline']


def test_maximum_preserves_lower_bound_and_includes_both_edges():
    field = bounded_field()
    assert field.altitude_lower_deg == 20
    assert field.altitude_upper_deg == 80
    assert field.contains([180] * 6, [19.99, 20, 50, 80, 80.01, 90]).tolist() == [
        False, True, True, True, False, False,
    ]


@pytest.mark.parametrize('maximum', [-0.1, 90.1, float('nan'), float('inf'),
                                     -float('inf'), True, '80'])
def test_api_rejects_invalid_maximum(maximum):
    with pytest.raises(ValueError, match='maximale'):
        bounded_field(maximum=maximum)


def test_reversed_interval_and_ambiguous_center_are_rejected():
    with pytest.raises(ValueError, match='minimale'):
        bounded_field(81, 80)
    with pytest.raises(ValueError, match='centre'):
        bounded_field(20, 80, altitude_center_deg=50)


@pytest.mark.parametrize('minimum,maximum', [(0, 0), (80, 80), (90, 90), (0, 90)])
def test_extreme_and_zero_width_ranges(minimum, maximum):
    field = bounded_field(minimum, maximum)
    assert field.altitude_lower_deg == minimum
    assert field.altitude_upper_deg == maximum
    assert field.contains([0, 359], [minimum, maximum]).all()


def test_default_and_legacy_center_are_preserved():
    assert FieldOfView.from_automatic_center(
        azimuth_min_deg=0, azimuth_max_deg=360, minimum_altitude_deg=20,
    ) == bounded_field(20, 90)
    legacy = FieldOfView.from_automatic_center(
        azimuth_min_deg=0, azimuth_max_deg=360, minimum_altitude_deg=20, altitude_center_deg=45,
    )
    assert (legacy.altitude_lower_deg, legacy.altitude_upper_deg) == (10, 80)


@pytest.mark.parametrize('extra', [
    ['--max-altitude=nan'], ['--max-altitude=inf'], ['--max-altitude=-inf'],
    ['--max-altitude=-1'], ['--max-altitude=91'], ['--max-altitude=19'],
    ['--max-altitude=80', '--alt-center=50'],
])
def test_cli_rejects_invalid_ceiling_before_effects(extra, tmp_path, monkeypatch, capsys):
    report = tmp_path / 'existing.txt'
    report.write_bytes(b'Existing synthetic report')
    cache = tmp_path / 'cache'
    for name in ('refresh_catalogs', 'compute_weather_summary', 'compute_moon_summary', '_run'):
        monkeypatch.setattr(cli, name, Mock(side_effect=AssertionError('Traitement prématuré')))
    with pytest.raises(SystemExit) as caught:
        cli.main(arguments() + extra + ['--update-catalogs', 'force',
                 '--catalog-cache-dir', str(cache), '--output-txt', str(report), '--overwrite'])
    assert caught.value.code == 2
    assert 'unrecognized arguments' not in capsys.readouterr().err
    assert report.read_bytes() == b'Existing synthetic report'
    assert not cache.exists()


@pytest.mark.parametrize('maximum', [float('nan'), 19, 91])
def test_direct_service_validates_ceiling_before_collaborators(maximum):
    dependencies = ApplicationDependencies(**{
        field.name: Mock(side_effect=AssertionError('Collaborateur prématuré'))
        for field in fields(ApplicationDependencies)
    })
    request = ObservationRequest(
        date='2026-11-17', time_range='21:00-21:01', timezone='UTC', lat=45, lon=0,
        elevation_m=0, az_min=0, az_max=360, min_altitude=20, alt_center=None,
        objects=('messier',), offline=True, max_altitude=maximum,
    )
    with pytest.raises(ValueError):
        ObservationApplication(dependencies).prepare_report(request)
    assert all(not getattr(dependencies, field.name).called for field in fields(dependencies))


@pytest.mark.parametrize('minimum_flag', ['--min-altitude', '--fov-v'])
def test_cli_displays_same_bounds_in_screen_text_and_pdf(tmp_path, capsys, minimum_flag):
    txt, pdf = tmp_path / 'report.txt', tmp_path / 'report.pdf'
    command = [minimum_flag if value == '--min-altitude' else value for value in arguments()]
    assert cli.main(command + ['--max-altitude', '80', '--max-magnitude', '-20',
                    '--output-txt', str(txt), '--output-pdf', str(pdf)]) == 0
    screen = capsys.readouterr().out
    text = txt.read_text(encoding='utf-8')
    pdf_text = ' '.join(page.extract_text() for page in PdfReader(pdf).pages)
    assert 'autres instants' in PdfReader(pdf).pages[0].extract_text()
    for output in (screen, text, pdf_text):
        assert '20° à 80°' in output
        assert 'autres instants' in output
    assert 'hauteur 50°' in screen


def test_fixed_objects_above_ceiling_are_not_selected():
    window = parse_observation_window('2026-11-17', '21:00-21:01', 'UTC')
    location = EarthLocation.from_geodetic(0 * u.deg, 45 * u.deg)
    positions = SkyCoord(az=[180, 180, 270] * u.deg, alt=[75, 85, 80.05] * u.deg,
                         frame=AltAz(obstime=Time(window.start_local), location=location,
                                     pressure=0 * u.hPa)).icrs
    stars = [VariableStar(name, position.ra.deg, position.dec.deg, 'Synthetic', 2, None, 'V')
             for name, position in zip(
                 ('Within ceiling', 'Above ceiling', 'Crossing ceiling'), positions)]
    results = compute_visibility(stars, window, 45, 0, 0, bounded_field(), sample_minutes=1)
    assert {result.star.name for result in results} == {'Within ceiling', 'Crossing ceiling'}
    crossing = next(result for result in results if result.star.name == 'Crossing ceiling')
    assert crossing.altitude_start_deg > 80 > crossing.altitude_end_deg


@pytest.mark.parametrize('kind', ['asteroids', 'comets'])
@pytest.mark.parametrize('heights,expected', [([85, 86], 0), ([85, 75], 1)])
def test_small_bodies_use_ceiling_at_same_sample(monkeypatch, kind, heights, expected):
    module = asteroids if kind == 'asteroids' else comets
    window = parse_observation_window('2026-11-17', '21:00-21:01', 'UTC')

    def geometry(orbits, times, location):
        coordinates = SkyCoord(ra=[[0, 1]] * u.deg, dec=[[0, 0]] * u.deg, frame='gcrs')
        horizontal = SkyCoord(az=[[180, 180]] * u.deg, alt=[heights] * u.deg, frame='altaz')
        return coordinates, horizontal, np.array([[2, 2]])

    monkeypatch.setattr(module, 'ephemerides', geometry)
    if kind == 'asteroids':
        orbit = module.load_asteroid_catalog()[0]
        compute = module.compute_asteroid_visibility
    else:
        orbit = next(orbit for orbit in module.load_comet_catalog() if orbit.epoch_tt is not None)
        compute = module.compute_comet_visibility
    results = compute((orbit,), window, 45, 0, 0, bounded_field(), sample_minutes=1)
    assert len(results) == expected
    if results:
        assert results[0].magnitude_reference_time == window.end_local


@pytest.mark.parametrize('heights,expected', [([85, 86], 0), ([85, 75], 1)])
def test_satellites_and_debris_use_ceiling_at_reference_time(monkeypatch, heights, expected):
    window = parse_observation_window('2026-11-17', '21:00-21:01', 'UTC')

    def geometry(element, times, location):
        return AltAz(az=[180, 180] * u.deg, alt=heights * u.deg,
                     distance=[1000, 1000] * u.km, obstime=times, location=location,
                     pressure=0 * u.hPa), None

    monkeypatch.setattr(satellites, '_horizontal', geometry)
    monkeypatch.setattr(satellites, '_solar_geometry', lambda *args: None)
    monkeypatch.setattr(satellites, '_solar_conditions', lambda *args: (
        np.array([-10, -10]), np.array([True, True])))
    results = satellites.compute_satellite_visibility(
        satellites.load_satellite_elements()[:1], window, 45, 0, 0, bounded_field(),
        sample_seconds=60,
    )
    assert len(results) == expected
    if results:
        assert results[0].position_reference_time == window.end_local
        assert results[0].position_azimuth_deg == 180
        assert results[0].position_altitude_deg == 75
