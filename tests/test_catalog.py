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


def test_magnitude_filter_also_accepts_messier_objects() -> None:
    objects = filter_by_magnitude(load_messier_catalog(), 2.0)

    assert [obj.name for obj in objects] == ["M45"]
