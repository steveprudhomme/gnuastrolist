# SPDX-FileCopyrightText: 2026 Steve Prud'Homme
# SPDX-License-Identifier: GPL-3.0-or-later
import numpy as np
import pytest

from gnu_astrolist.models import FieldOfView


def test_horizontal_field_wraps_through_north() -> None:
    field = FieldOfView(
        azimuth_center_deg=0,
        altitude_center_deg=45,
        horizontal_deg=20,
        vertical_deg=20,
    )

    mask = field.contains(np.array([355, 5, 20]), np.array([45, 45, 45]))

    assert mask.tolist() == [True, True, False]


def test_full_horizontal_field_accepts_all_azimuths() -> None:
    field = FieldOfView(180, 45, 360, 90)

    assert field.contains([0, 90, 180, 359.9], [0, 30, 60, 90]).all()


def test_automatic_center_uses_azimuth_bounds_and_minimum_altitude() -> None:
    field = FieldOfView.from_automatic_center(
        azimuth_min_deg=15,
        azimuth_max_deg=180,
        minimum_altitude_deg=20,
    )

    assert field.azimuth_center_deg == 97.5
    assert field.horizontal_deg == 165
    assert field.azimuth_start_deg == 15
    assert field.azimuth_end_deg == 180
    assert field.altitude_center_deg == 55
    assert field.vertical_deg == 70
    assert field.altitude_lower_deg == 20
    assert field.altitude_upper_deg == 90


def test_horizontal_bounds_can_cross_north() -> None:
    field = FieldOfView.from_automatic_center(
        azimuth_min_deg=350,
        azimuth_max_deg=15,
        minimum_altitude_deg=20,
    )

    assert field.azimuth_center_deg == 2.5
    assert field.horizontal_deg == 25
    assert field.contains([349, 350, 0, 15, 16], [55] * 5).tolist() == [
        False,
        True,
        True,
        True,
        False,
    ]


def test_zero_to_360_selects_the_full_horizon() -> None:
    field = FieldOfView.from_automatic_center(
        azimuth_min_deg=0,
        azimuth_max_deg=360,
        minimum_altitude_deg=20,
    )

    assert field.azimuth_center_deg == 180
    assert field.horizontal_deg == 360
    assert field.azimuth_start_deg == 0
    assert field.azimuth_end_deg == 360
    assert field.contains([0, 90, 180, 359.9], [55] * 4).all()


def test_vertical_center_can_be_explicitly_overridden() -> None:
    field = FieldOfView.from_automatic_center(
        azimuth_min_deg=15,
        azimuth_max_deg=180,
        minimum_altitude_deg=20,
        altitude_center_deg=45,
    )

    assert field.azimuth_center_deg == 97.5
    assert field.altitude_center_deg == 45
    assert field.vertical_deg == 70


@pytest.mark.parametrize("minimum", [-0.1, 90.1])
def test_invalid_minimum_altitude_is_rejected(minimum: float) -> None:
    with pytest.raises(ValueError, match="élévation minimale"):
        FieldOfView.from_automatic_center(
            azimuth_min_deg=15,
            azimuth_max_deg=180,
            minimum_altitude_deg=minimum,
        )


@pytest.mark.parametrize(
    "minimum,maximum",
    [(-0.1, 180), (15, 360.1)],
)
def test_invalid_azimuth_bounds_are_rejected(minimum: float, maximum: float) -> None:
    with pytest.raises(ValueError, match="azimut"):
        FieldOfView.from_automatic_center(
            azimuth_min_deg=minimum,
            azimuth_max_deg=maximum,
            minimum_altitude_deg=20,
        )


@pytest.mark.parametrize(
    "arguments",
    [
        (-1, 45, 10, 10),
        (0, 91, 10, 10),
        (0, 45, 361, 10),
        (0, 45, 10, 91),
    ],
)
def test_invalid_field_is_rejected_during_construction(arguments: tuple[float, ...]) -> None:
    with pytest.raises(ValueError):
        FieldOfView(*arguments)
