"""Chargement du sous-ensemble visuel du GCVS fourni avec le paquet."""

from __future__ import annotations

import csv
import gzip
from functools import lru_cache
from importlib import resources
from typing import Iterable

from .models import VariableStar


CATALOG_RESOURCE = "gcvs_visual.csv.gz"


def _optional_float(value: str) -> float | None:
    return float(value) if value else None


@lru_cache(maxsize=1)
def load_catalog() -> tuple[VariableStar, ...]:
    """Charge le catalogue embarqué une seule fois par processus."""

    resource = resources.files("gnu_astrolist.data").joinpath(CATALOG_RESOURCE)
    with resource.open("rb") as raw, gzip.open(
        raw, mode="rt", encoding="utf-8", newline=""
    ) as stream:
        rows = csv.DictReader(stream)
        stars = tuple(
            VariableStar(
                name=row["name"],
                ra_deg=float(row["ra_deg"]),
                dec_deg=float(row["dec_deg"]),
                variable_type=row["variable_type"],
                mag_max=float(row["mag_max"]),
                mag_min=_optional_float(row["mag_min"]),
                passband=row["passband"],
                mag_max_limit=row["mag_max_limit"],
            )
            for row in rows
        )
    if not stars:
        raise RuntimeError("le catalogue embarqué est vide")
    return stars


def filter_by_magnitude(
    stars: Iterable[VariableStar], max_magnitude: float | None
) -> list[VariableStar]:
    """Filtre sur la magnitude au maximum d'éclat publiée par le GCVS."""

    if max_magnitude is None:
        return list(stars)
    return [star for star in stars if star.mag_max <= max_magnitude]
