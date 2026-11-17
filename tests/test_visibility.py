import astropy.units as u
import pytest
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time
from astropy.utils import iers

from gnu_astrolist.catalog import load_messier_catalog
from gnu_astrolist.models import FieldOfView, VariableStar
from gnu_astrolist.time_utils import parse_observation_window
from gnu_astrolist.visibility import compute_visibility


@pytest.fixture(autouse=True)
def offline_iers_context():
    """ECC-G : rendre les tests indépendants des réglages laissés par la CLI."""
    with (
        iers.conf.set_temp('auto_download', False),
        iers.conf.set_temp('auto_max_age', None),
        iers.conf.set_temp('iers_degraded_accuracy', 'warn'),
    ):
        yield


def test_star_at_field_center_is_selected() -> None:
    window = parse_observation_window("2026-01-15", "21:00-21:01", "UTC")
    location = EarthLocation.from_geodetic(lon=-73.68 * u.deg, lat=45.57 * u.deg)
    start_time = Time(window.start_local)
    center = SkyCoord(
        az=180 * u.deg,
        alt=45 * u.deg,
        frame=AltAz(obstime=start_time, location=location, pressure=0 * u.hPa),
    ).icrs
    star = VariableStar(
        name="Étoile test",
        ra_deg=center.ra.deg,
        dec_deg=center.dec.deg,
        variable_type="TEST",
        mag_max=5.0,
        mag_min=6.0,
        passband="V",
    )

    results = compute_visibility(
        stars=[star],
        window=window,
        latitude_deg=45.57,
        longitude_deg=-73.68,
        elevation_m=0,
        field_of_view=FieldOfView(180, 45, 2, 2),
        sample_minutes=10,
    )

    assert len(results) == 1
    assert abs(results[0].altitude_start_deg - 45) < 1e-6
    assert results[0].constellation
    assert results[0].maximum_solar_separation_date is not None
    assert results[0].best_seasonal_visibility_date is not None
    assert results[0].opposition_date is None
    assert results[0].rises_above_minimum_local is not None
    assert results[0].sets_below_minimum_local is not None


def test_empty_input_short_circuits() -> None:
    window = parse_observation_window("2026-01-15", "21:00-22:00", "UTC")

    assert compute_visibility([], window, 45, -73, 0, FieldOfView(180, 45, 10, 10)) == []


def test_high_ecliptic_latitude_keeps_seasonal_dates_separate() -> None:
    window = parse_observation_window(
        "2026-08-03", "00:00-01:00", "America/Toronto"
    )
    m39 = next(obj for obj in load_messier_catalog() if obj.name == "M39")
    ecliptic_latitude = SkyCoord(
        ra=m39.ra_deg * u.deg,
        dec=m39.dec_deg * u.deg,
        frame="icrs",
    ).barycentrictrueecliptic.lat.deg

    results = compute_visibility(
        stars=[m39],
        window=window,
        latitude_deg=45.57,
        longitude_deg=-73.68,
        elevation_m=20,
        field_of_view=FieldOfView(180, 45, 360, 90),
        sample_minutes=10,
    )

    assert abs(ecliptic_latitude) > 45
    assert len(results) == 1
    result = results[0]
    assert result.maximum_solar_separation_date is not None
    assert result.best_seasonal_visibility_date is not None
    difference = abs(
        (result.maximum_solar_separation_date - result.best_seasonal_visibility_date).days
    )
    assert difference >= 14
    assert result.opposition_date is None
