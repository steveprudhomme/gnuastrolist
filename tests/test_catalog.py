# SPDX-FileCopyrightText: 2026 Steve Prud'Homme
# SPDX-License-Identifier: GPL-3.0-or-later
import pytest

from gnu_astrolist.catalog import (
    filter_by_magnitude,
    load_catalog,
    load_messier_catalog,
)


def test_embedded_catalog_is_substantial_and_valid() -> None:
    stars = load_catalog()

    assert len(stars) == 21_212
    assert all(star.passband == "V" for star in stars)
    assert all(0 <= star.ra_deg < 360 for star in stars)
    assert all(-90 <= star.dec_deg <= 90 for star in stars)


def test_magnitude_filter_uses_maximum_brightness() -> None:
    stars = filter_by_magnitude(load_catalog(), 0.0)

    assert stars
    assert all(star.mag_max <= 0.0 for star in stars)


def test_messier_catalog_contains_the_complete_numbered_list() -> None:
    objects = load_messier_catalog()

    assert len(objects) == 110
    assert [obj.name for obj in objects] == [f"M{number}" for number in range(1, 111)]
    assert all(obj.passband == "V" for obj in objects)
    assert all(0 <= obj.ra_deg < 360 for obj in objects)
    assert all(-90 <= obj.dec_deg <= 90 for obj in objects)


def test_m102_uses_the_documented_ngc_5866_convention() -> None:
    m102 = next(obj for obj in load_messier_catalog() if obj.name == "M102")

    assert m102.catalog_designation == "NGC5866"
    assert m102.magnitude_v == 9.89


def test_messier_catalog_contains_constellations_and_apparent_sizes() -> None:
    m31 = next(obj for obj in load_messier_catalog() if obj.name == "M31")
    m40 = next(obj for obj in load_messier_catalog() if obj.name == "M40")

    assert m31.constellation == "And"
    assert m31.apparent_major_arcmin == 199.53
    assert m31.apparent_minor_arcmin == 70.79
    assert m31.size_source == "SIMBAD"
    assert m31.size_reference == "2003A&A...412...45P"
    assert m40.apparent_major_arcmin is None
    assert m40.apparent_minor_arcmin is None


@pytest.mark.parametrize(
    "name,major,minor,size_bibcode,magnitude,magnitude_source",
    [
        ("M39", 120.4, 120.4, "2020A&A...633A..99C", 4.6, "OpenNGC"),
        ("M15", 12.3, 12.3, "1989Sci...246.1066D", 6.3, "OpenNGC"),
        ("M52", 16.0, 16.0, "2020A&A...633A..99C", 6.9, "OpenNGC"),
    ],
)
def test_simbad_priority_and_openngc_fallback_for_reference_objects(
    name: str,
    major: float,
    minor: float,
    size_bibcode: str,
    magnitude: float,
    magnitude_source: str,
) -> None:
    obj = next(item for item in load_messier_catalog() if item.name == name)

    assert obj.apparent_major_arcmin == major
    assert obj.apparent_minor_arcmin == minor
    assert obj.size_source == "SIMBAD"
    assert obj.size_reference == size_bibcode
    assert obj.size_retrieved_on == "2026-08-03"
    assert obj.magnitude_v == magnitude
    assert obj.magnitude_source == magnitude_source
    assert obj.magnitude_reference == "doi:10.21938/y.1ejWUD_MQ6b_eDFoVbbw"


def test_magnitude_filter_also_accepts_messier_objects() -> None:
    objects = filter_by_magnitude(load_messier_catalog(), 2.0)

    assert [obj.name for obj in objects] == ["M45"]
