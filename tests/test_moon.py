from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pytest
from astropy.utils import iers

from gnu_astrolist.moon import (
    STANDARD_HORIZON_REFRACTION_DEG,
    _apparent_upper_limb_altitudes,
    _phase_name,
    compute_moon_summary,
)
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
    assert summary.daily_illumination_percent == pytest.approx(84.1, abs=0.2)
    assert summary.daily_illumination_reference_local == datetime(
        2026, 8, 2, 12, 0, tzinfo=timezone
    )
    assert summary.moonrise_local == datetime(2026, 8, 3, 22, 18, tzinfo=timezone)
    assert summary.moonset_local == datetime(2026, 8, 3, 11, 6, tzinfo=timezone)
    assert summary.always_above_horizon is False
    assert summary.always_below_horizon is False


def test_variable_semidiameter_changes_the_apparent_upper_limb() -> None:
    geometric_altitudes = np.array([0.0, 0.0])
    distances_km = np.array([356_500.0, 406_700.0])

    apparent_altitudes = _apparent_upper_limb_altitudes(
        geometric_altitudes, distances_km
    )

    assert apparent_altitudes[0] > apparent_altitudes[1]
    assert apparent_altitudes[0] - STANDARD_HORIZON_REFRACTION_DEG == pytest.approx(
        0.2792, abs=0.0001
    )
    assert apparent_altitudes[1] - STANDARD_HORIZON_REFRACTION_DEG == pytest.approx(
        0.2448, abs=0.0001
    )


@pytest.mark.parametrize(
    ("local_date", "expected_rise", "expected_set"),
    [
        ("2026-08-02", (22, 6), (10, 0)),
        ("2026-08-03", (22, 34), (11, 2)),
    ],
)
def test_moon_events_match_usno_reference_ephemerides(
    local_date: str,
    expected_rise: tuple[int, int],
    expected_set: tuple[int, int],
) -> None:
    """Compare aux données USNO publiées par le Griffith Observatory."""

    window = parse_observation_window(
        local_date, "00:00-01:00", "America/Los_Angeles"
    )
    summary = compute_moon_summary(
        window=window,
        latitude_deg=34 + 7 / 60 + 7.05 / 3600,
        longitude_deg=-(118 + 18 / 60 + 1.5 / 3600),
        elevation_m=357,
    )
    timezone = ZoneInfo("America/Los_Angeles")
    year, month, day = (int(value) for value in local_date.split("-"))

    assert summary.moonrise_local == datetime(
        year, month, day, *expected_rise, tzinfo=timezone
    )
    assert summary.moonset_local == datetime(
        year, month, day, *expected_set, tzinfo=timezone
    )
