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
