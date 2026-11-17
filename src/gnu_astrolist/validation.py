# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""ECC-C : domaines numériques et budgets temporels, sans calcul ni écriture."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ObservationWindow

MAX_AGE_HOURS = timedelta.max.days * 24
MAX_STEP_SECONDS = 86_400
MIN_STEP_SECONDS = 1e-6


def finite_number(
    value: float, name: str, lower: float | None = None, upper: float | None = None
) -> float:
    if isinstance(value, (bool, str, bytes)):
        raise ValueError(f"{name} : nombre fini requis")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} : nombre fini requis") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} : nombre fini requis")
    if lower is not None and number < lower or upper is not None and number > upper:
        raise ValueError(f"{name} : valeur hors limites ({lower} à {upper})")
    return number


def validate_observer(latitude: float, longitude: float, elevation: float) -> None:
    finite_number(latitude, "latitude", -90, 90)
    finite_number(longitude, "longitude", -180, 180)
    finite_number(elevation, "altitude du site", -1000, 10000)


def validate_magnitude(value: float | None) -> None:
    if value is not None:
        finite_number(value, "magnitude")


def sampling_step(value: float, name: str, unit_seconds: float = 1) -> timedelta:
    number = finite_number(
        value, name, MIN_STEP_SECONDS / unit_seconds, MAX_STEP_SECONDS / unit_seconds
    )
    return timedelta(seconds=number * unit_seconds)


def sampling_plan(
    window: ObservationWindow,
    value: float,
    limit: int,
    name: str,
    unit_seconds: float = 1,
) -> tuple[datetime, datetime, timedelta, int]:
    """Compte en microsecondes entières avant toute allocation d'une grille."""
    step = sampling_step(value, name, unit_seconds)
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 2:
        raise ValueError("Budget d'échantillons invalide")
    start, end = window_bounds(window)
    microsecond = timedelta(microseconds=1)
    duration_us, step_us = (end - start) // microsecond, step // microsecond
    count = (duration_us + step_us - 1) // step_us + 1
    if count > limit:
        raise ValueError(f"{name} : fenêtre limitée à {limit} échantillons; augmentez le pas")
    return start, end, step, count


def window_bounds(window: ObservationWindow) -> tuple[datetime, datetime]:
    if window.start_local.utcoffset() is None or window.end_local.utcoffset() is None:
        raise ValueError("La fenêtre doit avoir un fuseau horaire")
    start, end = (v.astimezone(timezone.utc) for v in (window.start_local, window.end_local))
    if end <= start:
        raise ValueError("La fin doit suivre le début")
    return start, end


def sample_datetimes(
    window: ObservationWindow,
    value: float,
    limit: int,
    name: str,
    unit_seconds: float = 1,
) -> list[datetime]:
    start, end, step, count = sampling_plan(window, value, limit, name, unit_seconds)
    return [start + i * step for i in range(count - 1)] + [end]
