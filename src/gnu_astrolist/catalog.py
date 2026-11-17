"""Chargement des catalogues astronomiques fournis avec le paquet."""

from __future__ import annotations

import csv
import gzip
from collections.abc import Iterable
from functools import lru_cache

from .catalog_resources import catalog_resource, catalog_retrieved_on
from .models import CatalogObject, DeepSkyObject, MessierObject, NamedStar, VariableStar

VARIABLE_STAR_CATALOG_RESOURCE = "gcvs_visual.csv.gz"
MESSIER_CATALOG_RESOURCE = "messier.csv.gz"


def _optional_float(value: str) -> float | None:
    return float(value) if value else None


@lru_cache(maxsize=1)
def load_catalog() -> tuple[VariableStar, ...]:
    """Charge le catalogue GCVS; alias conservé pour compatibilité."""

    return load_variable_star_catalog()


@lru_cache(maxsize=1)
def load_variable_star_catalog() -> tuple[VariableStar, ...]:
    """Charge le sous-ensemble visuel du GCVS une fois par processus."""

    resource = catalog_resource(
        VARIABLE_STAR_CATALOG_RESOURCE
    )
    retrieved_on = catalog_retrieved_on(VARIABLE_STAR_CATALOG_RESOURCE, "2026-07-17")
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
                magnitude_retrieved_on=retrieved_on,
            )
            for row in rows
        )
    if not stars:
        raise RuntimeError("le catalogue GCVS embarqué est vide")
    return stars


@lru_cache(maxsize=1)
def load_messier_catalog() -> tuple[MessierObject, ...]:
    """Charge les 110 objets Messier une fois par processus."""

    return _load_deep_sky_catalog(MESSIER_CATALOG_RESOURCE)


@lru_cache(maxsize=1)
def load_caldwell_catalog() -> tuple[DeepSkyObject, ...]:
    """Charge les 109 objets Caldwell, y compris ceux sans magnitude V."""
    return _load_deep_sky_catalog("caldwell.csv.gz")


@lru_cache(maxsize=1)
def load_ngc_catalog() -> tuple[DeepSkyObject, ...]:
    """Charge les entrées NGC exploitables, composants distincts inclus."""
    return _load_deep_sky_catalog("ngc.csv.gz")


def _load_deep_sky_catalog(filename: str) -> tuple[DeepSkyObject, ...]:
    resource = catalog_resource(filename)
    with resource.open("rb") as raw, gzip.open(
        raw, mode="rt", encoding="utf-8", newline=""
    ) as stream:
        rows = csv.DictReader(stream)
        objects = tuple(
            DeepSkyObject(
                name=row["name"],
                ra_deg=float(row["ra_deg"]),
                dec_deg=float(row["dec_deg"]),
                object_type=row["object_type"],
                magnitude_v=_optional_float(row["magnitude_v"]),
                passband=row["passband"],
                catalog_designation=row["catalog_designation"],
                constellation=row["constellation"],
                apparent_major_arcmin=_optional_float(row["major_axis_arcmin"]),
                apparent_minor_arcmin=_optional_float(row["minor_axis_arcmin"]),
                size_source=row["size_source"],
                size_reference=row["size_reference"],
                size_retrieved_on=row["size_retrieved_on"],
                magnitude_source=row["magnitude_source"],
                magnitude_reference=row["magnitude_reference"],
                magnitude_retrieved_on=row["magnitude_retrieved_on"],
                common_name=row["common_name"],
            )
            for row in rows
        )
    if not objects:
        raise RuntimeError(f"le catalogue embarqué {filename} est vide")
    return objects


def filter_by_magnitude(
    objects: Iterable[CatalogObject], max_magnitude: float | None
) -> list[CatalogObject]:
    """Filtre les objets selon leur magnitude V de référence."""

    if max_magnitude is None:
        return list(objects)
    return [
        obj for obj in objects
        if obj.magnitude_v is not None and obj.magnitude_v <= max_magnitude
    ]


@lru_cache(maxsize=2)
def _load_named_stars(kind: str) -> tuple[NamedStar, ...]:
    resource = catalog_resource(f'{kind}.csv.gz')
    retrieved_on = catalog_retrieved_on(f'{kind}.csv.gz', '2026-11-17')
    with resource.open('rb') as raw, gzip.open(raw, 'rt', encoding='utf-8', newline='') as stream:
        return tuple(NamedStar(
            name=row['name'], ra_deg=float(row['ra_deg']), dec_deg=float(row['dec_deg']),
            magnitude_v=_optional_float(row['magnitude_v']), hyg_id=int(row['hyg_id']),
            constellation=row['constellation'], bayer_name=row['bayer_name'],
            flamsteed_name=row['flamsteed_name'], common_name=row['common_name'],
            ambiguous_names=tuple(filter(None, row['ambiguous_names'].split('|'))),
            magnitude_retrieved_on=retrieved_on,
        ) for row in csv.DictReader(stream))


def load_bayer_catalog() -> tuple[NamedStar, ...]:
    """Étoiles HYG possédant une désignation Bayer explicite."""
    return _load_named_stars('bayer')


def load_flamsteed_catalog() -> tuple[NamedStar, ...]:
    """Étoiles HYG possédant un numéro Flamsteed explicite."""
    return _load_named_stars('flamsteed')
