# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""ECC-G : formats publics communs aux rapports TXT et PDF."""
from __future__ import annotations

from .models import CometTarget, MoonSummary, SatelliteTarget, VisibilityResult, apparent_magnitude

ALTITUDE_CEILING_NOTE = (
    "Le plafond limite les positions retenues, pas toute la trajectoire; "
    "un objet peut dépasser ce plafond à d'autres instants."
)


def object_name(result: VisibilityResult) -> str:
    if isinstance(result.star,SatelliteTarget):
        return f'{result.star.name} [NORAD {result.star.norad_id}; COSPAR {result.star.cospar_id or "—"}]'
    return ' / '.join((result.star.name, *getattr(result.star, 'aliases', ())))


def magnitude_label(result: VisibilityResult) -> str:
    magnitude = apparent_magnitude(result.star)
    if magnitude is None:
        return "non disponible"
    prefix = "≈" if result.magnitude_estimated else result.star.magnitude_limit or ""
    value = f"{prefix}{magnitude:.3f}".rstrip("0").rstrip(".")
    if isinstance(result.star, CometTarget):
        value += " (totale)"
    source = result.star.magnitude_source
    return f"{value} [{source}]" if source else value


def number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def apparent_size_label(result: VisibilityResult) -> str:
    major = result.star.apparent_major_arcmin
    minor = result.star.apparent_minor_arcmin
    if major is None:
        return "—"
    if minor is None:
        value = f"{number(major)}′"
    else:
        value = f"{number(major)}′ × {number(minor)}′"
    source = result.star.size_source
    return f"{value} [{source}]" if source else value


def reference_label(reference: str) -> str:
    if not reference:
        return "référence non disponible"
    if reference.startswith("doi:"):
        return f"référence {reference}"
    if len(reference) == 19 and reference[:4].isdigit():
        return f"bibcode {reference}"
    return f"référence {reference}"


def crossing_time_label(
    instant, *, reference_date, always_above: bool
) -> str:
    if always_above:
        return "Toujours"
    if instant is None:
        return "—"
    if instant.date() == reference_date:
        return f"{instant:%H:%M}"
    return f"{instant:%m-%d %H:%M}"


def moon_event_label(instant, summary: MoonSummary) -> str:
    if instant is not None:
        return f"{instant:%H:%M}"
    if summary.always_above_horizon:
        return "aucun — Lune levée toute la journée"
    if summary.always_below_horizon:
        return "aucun — Lune couchée toute la journée"
    return "aucun passage ce jour"

