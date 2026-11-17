# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sélection de catalogues, identité explicite et politique photométrique."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace

from .catalog import (
    filter_by_magnitude,
    load_bayer_catalog,
    load_caldwell_catalog,
    load_flamsteed_catalog,
    load_messier_catalog,
    load_ngc_catalog,
    load_variable_star_catalog,
)
from .models import CatalogObject, DeepSkyObject, NamedStar

LABELS = {
    "comets": "Comètes (orbites MPC, observations CBAT facultatives)",
    "asteroids": "Astéroïdes numérotés (JPL SBDB, fichier orbital local)",
    "variable_stars": "Étoiles variables (GCVS)",
    "messier": "Objets Messier (SIMBAD, repli OpenNGC)",
    "caldwell": "Objets Caldwell (OpenNGC, complément SIMBAD)",
    "ngc": "Objets NGC (OpenNGC)",
    "bayer": "Étoiles Bayer (HYG 4.1)",
    "flamsteed": "Étoiles Flamsteed (HYG 4.1)",
}
NOTES = {
    "comets": "Comètes : positions MPC et magnitude totale estimée H,k, distincte de la bande V.",
    "asteroids": "Astéroïdes : orbites JPL SBDB, positions recalculées et magnitude V estimée H-G.",
    "variable_stars": "Les magnitudes GCVS sont les maxima d'éclat publiés, pas des prévisions.",
    "messier": "Messier : priorité SIMBAD, repli OpenNGC.",
    "caldwell": "Caldwell : données OpenNGC; complément de magnitude V SIMBAD si exploitable.",
    "ngc": "NGC : données OpenNGC; composants distincts inclus, hors doublons.",
    "bayer": "Bayer : désignations HYG; magnitude visuelle de référence, pas un maximum GCVS.",
    "flamsteed": "Flamsteed : désignations HYG; magnitude visuelle de référence, pas un maximum GCVS.",
}

ASTEROID_NOTES = (
    "Modèle à deux corps sans perturbations planétaires, avec temps de lumière; approximation de planification.",
    "Éléments utilisés à ±365 jours de leur époque; cette limite ne garantit pas la précision.",
    "≈ : magnitude H-G estimée; G=0,15 supposé si absent. H n'est pas une magnitude apparente.",
    "Instant V : échantillon le plus brillant dans le champ; le filtre V s'applique au même instant.",
    "Astéroïdes : franchissements recherchés seulement dans la plage; dates saisonnières et opposition non calculées.",
)

COMET_NOTES = (
    "Comètes : modèle à deux corps, temps de lumière et position topocentrique; perturbations et dégazage ignorés.",
    "Magnitude totale ≈ H + 5 log10(Δ) + 2,5 k log10(r); aucun H ou k absent n'est inventé.",
    "Instant estimé : meilleur échantillon dans le champ; filtre de magnitude simultané, valeur totale pour les comètes.",
    "Époque MPC requise à ±365 jours; borne de fonctionnement sans garantie de précision ni d'activité de la comète.",
    "Franchissements cométaires dans la plage seulement; dates saisonnières et opposition non calculées.",
    "CBAT : observation datée séparée, jamais substituée à la magnitude prévue; fragments conservés distincts.",
)


@dataclass(frozen=True)
class CatalogSelection:
    """Catalogues demandés et limites réellement appliquées, dans le même ordre."""

    kinds: tuple[str, ...]
    limits: tuple[float | None, ...]
    source_notes: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return " + ".join(LABELS[kind] for kind in self.kinds)

    @property
    def filter_label(self) -> str:
        parts = []
        for kind, limit in zip(self.kinds, self.limits):
            name = (
                "Astéroïdes (V estimée)"
                if kind == "asteroids"
                else "Comètes (totale estimée)"
                if kind == "comets"
                else "GCVS (maximum publié)"
                if kind == "variable_stars"
                else "NGC"
                if kind == "ngc"
                else kind.capitalize()
            )
            parts.append(f"{name} : " + ("aucune limite" if limit is None else f"≤ {limit:g}"))
        return "; ".join(parts)

    @property
    def notes(self) -> tuple[str, ...]:
        notes = tuple(NOTES[kind] for kind in self.kinds)
        if "asteroids" in self.kinds:
            notes += ASTEROID_NOTES
        if "comets" in self.kinds:
            notes += COMET_NOTES
        if any(kind in self.kinds for kind in ("messier", "caldwell", "ngc")):
            notes += (
                "Même désignation : une ligne, priorité Messier puis Caldwell puis NGC; alias conservés.",
                "Les groupes et leurs composants restent distincts; aucun rapprochement par position.",
            )
        if any(kind in self.kinds for kind in ("bayer", "flamsteed")):
            notes += (
                "Étoiles HYG réunies par identifiant source; priorité Bayer, alias Flamsteed conservés.",
                "Les composants de même désignation restent distincts; aucun lien GCVS/NGC déduit.",
                'Positions stellaires J2000 fixes; mouvements propres non appliqués.',
            )
        return notes + self.source_notes


def catalog_label(kind: str | CatalogSelection) -> str:
    return kind.label if isinstance(kind, CatalogSelection) else LABELS[kind]


def normalize_catalogs(names: Sequence[str]) -> tuple[str, ...]:
    result = []
    for name in names:
        name = "messier" if name == "messier_objects" else name
        if name not in LABELS:
            raise ValueError(f"Catalogue inconnu : {name}")
        if name not in result:
            result.append(name)
    if not result:
        raise ValueError("Au moins un catalogue est requis")
    return tuple(result)


def _identity(obj: DeepSkyObject) -> str | None:
    identifier = obj.catalog_designation.strip().upper()
    match = re.fullmatch(r"(NGC|IC|C)\s*(\d+)(.*)", identifier)
    if match:
        return f"{match[1]}{int(match[2])}{match[3].strip()}"
    # Les désignations vides ne constituent jamais une preuve d'identité.
    return identifier or None


def load_catalog_selection(
    names: Sequence[str],
    max_magnitude: float | None = None,
    all_magnitudes: bool = False,
) -> tuple[list[CatalogObject], CatalogSelection]:
    # Les orbites mobiles sont calculées séparément, jamais filtrées sur H.
    kinds = normalize_catalogs(names)
    limits = tuple(
        None
        if all_magnitudes
        else max_magnitude
        if max_magnitude is not None
        else 8.0
        if kind == "variable_stars"
        else None
        for kind in kinds
    )
    selection = CatalogSelection(kinds, limits)
    loaders = {
        "comets": lambda: (),
        "asteroids": lambda: (),
        "messier": load_messier_catalog,
        "caldwell": load_caldwell_catalog,
        "ngc": load_ngc_catalog,
        "variable_stars": load_variable_star_catalog,
        "bayer": load_bayer_catalog,
        "flamsteed": load_flamsteed_catalog,
    }
    if len(kinds) == 1:
        return filter_by_magnitude(loaders[kinds[0]](), limits[0]), selection

    # Le choix de la fiche précède le filtre : ne pas remplacer ses valeurs
    # par celles d'un autre catalogue uniquement pour franchir un seuil V.
    deep_sky: dict[str, tuple[DeepSkyObject, str]] = {}
    for kind in ("messier", "caldwell", "ngc"):
        if kind not in kinds:
            continue
        for obj in loaders[kind]():
            key = _identity(obj) or f"{kind}:{obj.name}"
            if key in deep_sky:
                existing, origin = deep_sky[key]
                if obj.name != existing.name and obj.name not in existing.aliases:
                    deep_sky[key] = (
                        replace(existing, aliases=(*existing.aliases, obj.name)),
                        origin,
                    )
            else:
                deep_sky[key] = (obj, kind)
    limit_by_kind = dict(zip(kinds, limits))
    objects: list[CatalogObject] = [
        obj
        for obj, kind in deep_sky.values()
        if limit_by_kind[kind] is None
        or (obj.magnitude_v is not None and obj.magnitude_v <= limit_by_kind[kind])
    ]
    if "variable_stars" in kinds:
        # Aucune identité croisée GCVS/ciel profond n'est présumée.
        objects.extend(
            filter_by_magnitude(load_variable_star_catalog(), limit_by_kind["variable_stars"])
        )
    stellar: dict[int, tuple[NamedStar, str]] = {}
    for kind in ("bayer", "flamsteed"):
        if kind not in kinds:
            continue
        for star in loaders[kind]():
            if star.hyg_id in stellar:
                existing, origin = stellar[star.hyg_id]
                stellar[star.hyg_id] = (
                    replace(existing, aliases=(*existing.aliases, star.name)),
                    origin,
                )
            else:
                stellar[star.hyg_id] = (star, kind)
    for star, kind in stellar.values():
        objects.extend(filter_by_magnitude((star,), limit_by_kind[kind]))
    return objects, selection
