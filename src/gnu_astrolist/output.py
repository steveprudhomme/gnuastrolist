"""Rendu texte de la soirée d'observation."""

from __future__ import annotations

from collections.abc import Sequence

from .models import (
    FieldOfView,
    MoonSummary,
    ObservationWindow,
    VisibilityResult,
    WeatherPeriodSummary,
    WeatherSummary,
)
from .seestar import SeestarInventory
from .selection import ASTEROID_NOTES, NOTES, CatalogSelection, catalog_label


def _object_name(result: VisibilityResult) -> str:
    return ' / '.join((result.star.name, *getattr(result.star, 'aliases', ())))


def _magnitude_label(result: VisibilityResult) -> str:
    if result.star.magnitude_v is None:
        return "non disponible"
    prefix = "≈" if result.magnitude_estimated else result.star.magnitude_limit or ""
    value = f"{prefix}{result.star.magnitude_v:.3f}".rstrip("0").rstrip(".")
    source = result.star.magnitude_source
    return f"{value} [{source}]" if source else value


def _number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _apparent_size_label(result: VisibilityResult) -> str:
    major = result.star.apparent_major_arcmin
    minor = result.star.apparent_minor_arcmin
    if major is None:
        return "—"
    if minor is None:
        value = f"{_number(major)}′"
    else:
        value = f"{_number(major)}′ × {_number(minor)}′"
    source = result.star.size_source
    return f"{value} [{source}]" if source else value


def _reference_label(reference: str) -> str:
    if not reference:
        return "référence non disponible"
    if reference.startswith("doi:"):
        return f"référence {reference}"
    if len(reference) == 19 and reference[:4].isdigit():
        return f"bibcode {reference}"
    return f"référence {reference}"


def _format_provenance_details(results: Sequence[VisibilityResult]) -> str:
    lines = ["PROVENANCE DÉTAILLÉE"]
    for result in results:
        star = result.star
        size = _apparent_size_label(result).rsplit(" [", maxsplit=1)[0]
        magnitude = _magnitude_label(result).rsplit(" [", maxsplit=1)[0]
        lines.append(f"{_object_name(result)} :")
        if star.size_source:
            lines.append(
                "  Taille      : "
                f"{size}; catalogue {star.size_source}; "
                f"{_reference_label(star.size_reference)}; "
                f"récupéré le {star.size_retrieved_on}."
            )
        else:
            lines.append("  Taille      : non disponible.")
        lines.append(
            "  Magnitude V : "
            f"{magnitude}; catalogue {star.magnitude_source or 'inconnu'}; "
            f"{_reference_label(star.magnitude_reference)}; "
            f"récupéré le {star.magnitude_retrieved_on or 'date inconnue'}."
        )
    return "\n".join(lines)


def _crossing_time_label(
    instant, *, reference_date, always_above: bool
) -> str:
    if always_above:
        return "Toujours"
    if instant is None:
        return "—"
    if instant.date() == reference_date:
        return f"{instant:%H:%M}"
    return f"{instant:%m-%d %H:%M}"


def _moon_event_label(instant, summary: MoonSummary) -> str:
    if instant is not None:
        return f"{instant:%H:%M}"
    if summary.always_above_horizon:
        return "aucun — Lune levée toute la journée"
    if summary.always_below_horizon:
        return "aucun — Lune couchée toute la journée"
    return "aucun passage ce jour"


def _format_moon_summary(
    summary: MoonSummary, window: ObservationWindow
) -> list[str]:
    start = window.start_local
    daily_reference = summary.daily_illumination_reference_local
    entries = (
        (f"Phase au début ({start:%Y-%m-%d %H:%M})", summary.phase_name),
        (
            f"Illumination au début ({start:%Y-%m-%d %H:%M})",
            f"{summary.illumination_percent:.1f} %",
        ),
        (
            f"Illumination quotidienne ({daily_reference:%Y-%m-%d %H:%M})",
            f"{summary.daily_illumination_percent:.1f} %",
        ),
        (
            f"Lever apparent le {start:%Y-%m-%d}",
            _moon_event_label(summary.moonrise_local, summary),
        ),
        (
            f"Coucher apparent le {start:%Y-%m-%d}",
            _moon_event_label(summary.moonset_local, summary),
        ),
    )
    label_width = max(len(label) for label, _ in entries)
    return [
        "RÉSUMÉ DE LA LUNE",
        *(f"{label.ljust(label_width)} : {value}" for label, value in entries),
    ]


def _weather_number(value: float | None, unit: str, decimals: int = 0) -> str:
    if value is None:
        return "—"
    return f"{value:.{decimals}f} {unit}".rstrip()


def _quality_label(value: float | None, description: str = "") -> str:
    label = _weather_number(value, "%")
    return f"{label} ({description})" if value is not None and description else label


def _format_weather_period(period: WeatherPeriodSummary) -> list[str]:
    entries = (
        ("Couverture nuageuse", _weather_number(period.cloud_cover_percent, "%")),
        (
            "Seeing — qualité",
            _quality_label(period.seeing_quality_percent, period.seeing_description),
        ),
        (
            "Transparence — qualité",
            _quality_label(
                period.transparency_quality_percent,
                period.transparency_description,
            ),
        ),
        ("Stabilité — qualité", _quality_label(period.stability_quality_percent)),
        ("Température", _weather_number(period.temperature_c, "°C", 1)),
        ("Humidité", _weather_number(period.humidity_percent, "%")),
        ("Vent", _weather_number(period.wind_kmh, "km/h", 1)),
        ("Risque de rosée", period.dew_risk or "—"),
        (
            "Risque de précipitation",
            _weather_number(period.precipitation_probability_percent, "%"),
        ),
    )
    label_width = max(len(label) for label, _ in entries)
    return [
        (
            f"{period.name} "
            f"({period.start_local:%Y-%m-%d %H:%M} → {period.end_local:%H:%M})"
        ),
        *(f"  {label.ljust(label_width)} : {value}" for label, value in entries),
    ]


def _format_weather_summary(summary: WeatherSummary) -> list[str]:
    lines = ["CONDITIONS MÉTÉO"]
    if summary.offline:
        lines.append("Prévisions indisponibles : mode --offline.")
    elif not summary.available:
        lines.append("Prévisions indisponibles pour les périodes demandées.")
    else:
        lines.extend(_format_weather_period(summary.evening))
        lines.extend(["", *_format_weather_period(summary.predawn)])
    if summary.sources:
        lines.append(f"Sources : {summary.sources}")
    if not summary.offline:
        lines.extend(f"Avertissement : {warning}." for warning in summary.warnings)
    return lines


def _format_table(
    results: Sequence[VisibilityResult],
    object_kind: str | CatalogSelection,
    window: ObservationWindow,
    minimum_altitude_deg: float,
) -> str:
    magnitude_header = (
        "Mag. max V" if object_kind == "variable_stars" else "Mag. apparente V"
    )
    if isinstance(object_kind, CatalogSelection) and 'variable_stars' in object_kind.kinds:
        magnitude_header = 'Mag. V (max si GCVS)'
    headers = (
        "Objet",
        "Type",
        "Constellation",
        "Taille apparente",
        magnitude_header,
        "Séparation solaire maximale",
        "Meilleure visibilité saisonnière",
        f"Monte ≥ {minimum_altitude_deg:g}°",
        f"Descend < {minimum_altitude_deg:g}°",
        "Hauteur début",
        "Hauteur fin",
    )
    rows = [
        (
            _object_name(result),
            result.star.object_type or "—",
            result.constellation or "—",
            _apparent_size_label(result),
            _magnitude_label(result),
            (
                result.maximum_solar_separation_date.isoformat()
                if result.maximum_solar_separation_date is not None
                else "—"
            ),
            (
                result.best_seasonal_visibility_date.isoformat()
                if result.best_seasonal_visibility_date is not None
                else "—"
            ),
            _crossing_time_label(
                result.rises_above_minimum_local,
                reference_date=window.start_local.date(),
                always_above=result.always_above_minimum,
            ),
            _crossing_time_label(
                result.sets_below_minimum_local,
                reference_date=window.start_local.date(),
                always_above=result.always_above_minimum,
            ),
            f"{result.altitude_start_deg:+.1f}°",
            f"{result.altitude_end_deg:+.1f}°",
        )
        for result in results
    ]
    if any(result.magnitude_estimated for result in results):
        headers += ("Instant V estimée (local)",)
        rows = [(*row, result.magnitude_reference_time.strftime("%Y-%m-%d %H:%M")
                 if result.magnitude_reference_time is not None else "—")
                for row, result in zip(rows, results)]
    if any(result.seestar_status is not None for result in results):
        headers += ('Seestar',)
        rows = [(*row, result.seestar_status or 'Non vérifié')
                for row, result in zip(rows, results)]
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]

    def render(row: tuple[str, ...]) -> str:
        return " | ".join(value.ljust(widths[index]) for index, value in enumerate(row))

    separator = "-+-".join("-" * width for width in widths)
    return "\n".join((render(headers), separator, *(render(row) for row in rows)))


def render_report(
    *,
    window: ObservationWindow,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    field_of_view: FieldOfView,
    max_magnitude: float | None,
    sample_minutes: float,
    weather_summary: WeatherSummary,
    moon_summary: MoonSummary,
    results: Sequence[VisibilityResult],
    matched_count: int,
    object_kind: str | CatalogSelection,
    show_details: bool = False,
    seestar_inventory: SeestarInventory | None = None,
) -> str:
    """Produit une sortie lisible, déterministe et facile à copier."""

    start = window.start_local
    end = window.end_local
    variable_stars = object_kind == "variable_stars"
    catalog_text = catalog_label(object_kind)
    if isinstance(object_kind, CatalogSelection):
        magnitude_text = object_kind.filter_label
    elif max_magnitude is None:
        magnitude_text = "aucune limite"
    elif variable_stars:
        magnitude_text = f"≤ {max_magnitude:g} au maximum d'éclat"
    else:
        magnitude_text = f"apparente ≤ {max_magnitude:g}"
    lines = [
        "=" * 78,
        "SOIRÉE D'OBSERVATION — GNU ASTROLIST",
        "=" * 78,
        f"Catalogue             : {catalog_text}",
        f"Date et heures       : {start:%Y-%m-%d %H:%M} → {end:%Y-%m-%d %H:%M}",
        f"Fuseau horaire       : {window.timezone_name} ({start.tzname()} → {end.tzname()})",
        (
            "Coordonnées          : "
            f"lat. {latitude_deg:.5f}°, lon. {longitude_deg:.5f}°, "
            f"alt. {elevation_m:g} m"
        ),
        (
            "Centre de visée      : "
            f"azimut {field_of_view.azimuth_center_deg:g}°, "
            f"hauteur {field_of_view.altitude_center_deg:g}°"
        ),
        (
            "Champ de vision      : "
            "azimuts "
            f"{field_of_view.azimuth_start_deg:g}° à "
            f"{field_of_view.azimuth_end_deg:g}° "
            f"({field_of_view.horizontal_deg:g}°) / "
            "hauteurs "
            f"{field_of_view.altitude_lower_deg:g}° à "
            f"{field_of_view.altitude_upper_deg:g}° "
            f"({field_of_view.vertical_deg:g}°)"
        ),
        f"Filtre photométrique : bande V; magnitude {magnitude_text}",
        (
            "Critère d'inclusion : présent dans le champ à au moins un échantillon "
            f"de {sample_minutes:g} min"
        ),
        "-" * 78,
    ]
    if seestar_inventory is not None:
        lines.extend([
            seestar_inventory.summary,
            "Seestar : présence d'acquisitions reconnues, sans validation de qualité des images.",
            'Non trouvé ne signifie pas jamais photographié; les noms non reconnus sont ignorés.',
            '-' * 78,
        ])
    lines.extend(_format_weather_summary(weather_summary))
    lines.append("-" * 78)
    lines.extend(_format_moon_summary(moon_summary, window))
    lines.append("-" * 78)
    if results:
        lines.append(
            _format_table(
                results,
                object_kind,
                window,
                field_of_view.altitude_lower_deg,
            )
        )
        if len(results) < matched_count:
            lines.append(f"\n{len(results)} objet(s) affiché(s) sur {matched_count} trouvé(s).")
        else:
            lines.append(f"\n{matched_count} objet(s) trouvé(s).")
        if show_details:
            lines.extend(["", _format_provenance_details(results)])
    else:
        lines.append("Aucun objet du catalogue ne satisfait les critères.")

    lines.extend(
        [
            "-" * 78,
            "Note : hauteurs du tableau géométriques, sans réfraction atmosphérique.",
        ]
    )
    if isinstance(object_kind, CatalogSelection):
        lines.extend(f'       {note}' for note in object_kind.notes)
    elif object_kind == "asteroids":
        lines.extend(f"       {note}" for note in (NOTES[object_kind], *ASTEROID_NOTES))
    elif variable_stars:
        lines.extend(
            [
                "       La magnitude est la magnitude au maximum d'éclat publiée,",
                "       pas une prévision instantanée.",
            ]
        )
    elif object_kind in ('bayer', 'flamsteed'):
        lines.append(f'       {NOTES[object_kind]}')
        lines.append('       Positions J2000 fixes; mouvements propres non appliqués.')
    elif object_kind == "ngc":
        lines.append("       Données NGC : OpenNGC; composants distincts inclus, hors doublons.")
    elif object_kind == "caldwell":
        lines.append("       Données OpenNGC; complément de magnitude V SIMBAD si exploitable.")
    else:
        lines.append("       Dimensions et magnitudes : priorité SIMBAD, repli OpenNGC.")
    lines.extend(
        [
            "       Les tailles apparentes sont exprimées en minutes d'arc (′).",
            "       Lever et coucher lunaires : bord supérieur apparent, avec",
            "       demi-diamètre variable et réfraction standard de 34′.",
            "       Aucun relief, masque d'horizon ni météo locale n'est appliqué",
            "       au calcul lunaire.",
            "       Seeing, transparence et stabilité : indices de qualité",
            "       normalisés de 0 à 100 à partir des catégories 7Timer!;",
            "       une valeur élevée est favorable et ne représente pas une probabilité.",
            "       Risque de rosée : estimation fondée sur l'écart température-point",
            "       de rosée et l'humidité relative prévus par Open-Meteo.",
            "       Séparation solaire maximale : maximum angulaire géométrique;",
            "       ce calcul ne constitue pas une opposition pour le ciel profond.",
            "       Meilleure visibilité saisonnière : culmination supérieure la",
            "       plus proche de minuit civil local, sans Lune, météo ni crépuscule.",
            "       Le terme opposition est réservé aux corps du Système solaire",
            "       pour lesquels cette notion est physiquement applicable.",
            "       Les heures de franchissement sont des estimations à la minute",
            f"       dans le fuseau {window.timezone_name}; une date MM-JJ est ajoutée",
            "       lorsque le passage n'a pas lieu à la date de début.",
        ]
    )
    return "\n".join(lines)
