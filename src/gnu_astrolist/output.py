"""Rendu texte de la soirée d'observation."""

from __future__ import annotations

from collections.abc import Sequence

from .models import FieldOfView, ObservationWindow, VisibilityResult


def _magnitude_label(result: VisibilityResult) -> str:
    prefix = result.star.magnitude_limit or ""
    return f"{prefix}{result.star.magnitude_v:.3f}".rstrip("0").rstrip(".")


def _number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _apparent_size_label(result: VisibilityResult) -> str:
    major = result.star.apparent_major_arcmin
    minor = result.star.apparent_minor_arcmin
    if major is None:
        return "—"
    if minor is None:
        return f"{_number(major)}′"
    return f"{_number(major)}′ × {_number(minor)}′"


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


def _format_table(
    results: Sequence[VisibilityResult],
    object_kind: str,
    window: ObservationWindow,
    minimum_altitude_deg: float,
) -> str:
    magnitude_header = (
        "Mag. max V" if object_kind == "variable_stars" else "Mag. apparente V"
    )
    headers = (
        "Objet",
        "Type",
        "Constellation",
        "Taille apparente",
        magnitude_header,
        "Opposition",
        f"Monte ≥ {minimum_altitude_deg:g}°",
        f"Descend < {minimum_altitude_deg:g}°",
        "Hauteur début",
        "Hauteur fin",
    )
    rows = [
        (
            result.star.name,
            result.star.object_type or "—",
            result.constellation or "—",
            _apparent_size_label(result),
            _magnitude_label(result),
            (
                result.opposition_date.isoformat()
                if result.opposition_date is not None
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
    results: Sequence[VisibilityResult],
    matched_count: int,
    object_kind: str,
) -> str:
    """Produit une sortie lisible, déterministe et facile à copier."""

    start = window.start_local
    end = window.end_local
    variable_stars = object_kind == "variable_stars"
    catalog_text = (
        "Étoiles variables (GCVS)" if variable_stars else "Objets Messier (OpenNGC)"
    )
    if max_magnitude is None:
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
    else:
        lines.append("Aucun objet du catalogue ne satisfait les critères.")

    lines.extend(["-" * 78, "Note : hauteurs géométriques, sans réfraction atmosphérique."])
    if variable_stars:
        lines.extend(
            [
                "       La magnitude est la magnitude au maximum d'éclat publiée,",
                "       pas une prévision instantanée.",
            ]
        )
    else:
        lines.append("       Les magnitudes apparentes V proviennent d'OpenNGC.")
    lines.extend(
        [
            "       Les tailles apparentes sont exprimées en minutes d'arc (′).",
            "       L'opposition est le jour de séparation maximale avec le Soleil.",
            "       Les heures de franchissement sont des estimations à la minute",
            f"       dans le fuseau {window.timezone_name}; une date MM-JJ est ajoutée",
            "       lorsque le passage n'a pas lieu à la date de début.",
        ]
    )
    return "\n".join(lines)
