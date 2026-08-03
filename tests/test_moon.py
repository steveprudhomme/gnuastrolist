from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from astropy.utils import iers

from gnu_astrolist.moon import _phase_name, compute_moon_summary
from gnu_astrolist.time_utils import parse_observation_window

iers.conf.auto_download = False
iers.conf.auto_max_age = None


@pytest.mark.parametrize(
    ("cycle_degrees", "expected"),
    [
        (0.0, "Nouvelle lune"),
        (45.0, "Premier croissant"),
        (90.0, "Premier quartier"),
        (135.0, "Lune gibbeuse croissante"),
        (180.0, "Pleine lune"),
        (225.0, "Lune gibbeuse décroissante"),
        (270.0, "Dernier quartier"),
        (315.0, "Dernier croissant"),
    ],
)
def test_phase_names_cover_the_lunar_cycle(
    cycle_degrees: float, expected: str
) -> None:
    assert _phase_name(cycle_degrees) == expected


def test_moon_summary_for_laval_uses_local_date_and_timezone() -> None:
    window = parse_observation_window(
        "2026-08-03", "00:00-01:00", "America/Toronto"
    )

    summary = compute_moon_summary(
        window=window,
        latitude_deg=45.57,
        longitude_deg=-73.68,
        elevation_m=20,
    )

    timezone = ZoneInfo("America/Toronto")
    assert summary.phase_name == "Lune gibbeuse décroissante"
    assert summary.illumination_percent == pytest.approx(80.0, abs=0.2)
    assert summary.moonrise_local == datetime(2026, 8, 3, 22, 23, tzinfo=timezone)
    assert summary.moonset_local == datetime(2026, 8, 3, 11, 1, tzinfo=timezone)
    assert summary.always_above_horizon is False
    assert summary.always_below_horizon is False
