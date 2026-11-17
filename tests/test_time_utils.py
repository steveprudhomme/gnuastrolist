# SPDX-FileCopyrightText: 2026 Steve Prud'Homme
# SPDX-License-Identifier: GPL-3.0-or-later
from datetime import timedelta

import pytest

from gnu_astrolist.time_utils import parse_observation_window


def test_range_crosses_midnight() -> None:
    window = parse_observation_window("2026-08-15", "21:00-02:00", "America/Toronto")

    assert window.start_local.isoformat().startswith("2026-08-15T21:00:00")
    assert window.end_local.isoformat().startswith("2026-08-16T02:00:00")
    assert window.end_local - window.start_local == timedelta(hours=5)


def test_equal_times_mean_twenty_four_hours() -> None:
    window = parse_observation_window("2026-01-15", "20:00-20:00", "UTC")

    assert window.duration_seconds == 24 * 60 * 60


@pytest.mark.parametrize("value", ["21h00-02h00", "21:00", "-"])
def test_invalid_range_is_rejected(value: str) -> None:
    with pytest.raises(ValueError):
        parse_observation_window("2026-08-15", value, "UTC")


def test_nonexistent_dst_time_is_rejected() -> None:
    with pytest.raises(ValueError, match="n'existe pas"):
        parse_observation_window("2026-03-08", "02:30-04:00", "America/Toronto")


def test_ambiguous_dst_time_is_rejected() -> None:
    with pytest.raises(ValueError, match="ambiguë"):
        parse_observation_window("2026-11-01", "01:30-03:00", "America/Toronto")
