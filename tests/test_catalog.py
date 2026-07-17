from gnu_astrolist.catalog import filter_by_magnitude, load_catalog


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

