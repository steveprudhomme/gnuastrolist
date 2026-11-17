# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""ECC-G : données communes aux rendus texte et PDF."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, fields

from .models import (
    FieldOfView,
    MoonSummary,
    ObservationWindow,
    VisibilityResult,
    WeatherSummary,
)
from .seestar import SeestarInventory
from .selection import CatalogSelection


@dataclass(frozen=True)
class ReportData:
    """Enveloppe du rapport; les objets métier sont transmis sans copie profonde."""

    window: ObservationWindow
    latitude_deg: float
    longitude_deg: float
    elevation_m: float
    field_of_view: FieldOfView
    max_magnitude: float | None
    sample_minutes: float
    weather_summary: WeatherSummary
    moon_summary: MoonSummary
    results: Sequence[VisibilityResult]
    matched_count: int
    object_kind: str | CatalogSelection
    show_details: bool = False
    seestar_inventory: SeestarInventory | None = None

    def to_kwargs(self) -> dict[str, object]:
        """Adapte le rapport aux API historiques render_report et export_pdf_report."""
        return {field.name: getattr(self, field.name) for field in fields(self)}
