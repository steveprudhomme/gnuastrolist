"""Rendu texte de la soirée d'observation."""

from __future__ import annotations

from collections.abc import Sequence

from .models import FieldOfView, ObservationWindow, VisibilityResult


def _magnitude_label(result: VisibilityResult) -> str:
    prefix = result.star.mag_max_limit or ""
    return f"{prefix}{result.star.mag_max:.3f}".rstrip("0").rstrip(".")


def _format_table(results: Sequence[VisibilityResult]) -> str:
    headers = ("Objet", "Mag. max V", "Type", "Hauteur début", "Hauteur fin")
    rows = [
        (
            result.star.name,
            _magnitude_label(result),
            result.star.variable_type or "—",
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
) -> str:
    """Produit une sortie lisible, déterministe et facile à copier."""

    start = window.start_local
    end = window.end_local
    magnitude_text = (
        "aucune"
        if max_magnitude is None
        else f"≤ {max_magnitude:g} au maximum d'éclat"
    )
    lines = [
        "=" * 78,
        "SOIRÉE D'OBSERVATION — GNU ASTROLIST",
        "=" * 78,
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
        lines.append(_format_table(results))
        if len(results) < matched_count:
            lines.append(f"\n{len(results)} objet(s) affiché(s) sur {matched_count} trouvé(s).")
        else:
            lines.append(f"\n{matched_count} objet(s) trouvé(s).")
    else:
        lines.append("Aucun objet du catalogue ne satisfait les critères.")

    lines.extend(
        [
            "-" * 78,
            "Note : hauteurs géométriques, sans réfraction atmosphérique. La magnitude",
            "       est la magnitude au maximum d'éclat publiée, "
            "pas une prévision instantanée.",
        ]
    )
    return "\n".join(lines)
