"""Export PDF lettre du rapport d'observation."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from tempfile import NamedTemporaryFile
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    CondPageBreak,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .models import (
    FieldOfView,
    MoonSummary,
    ObservationWindow,
    VisibilityResult,
    WeatherPeriodSummary,
    WeatherSummary,
)
from .output import (
    _apparent_size_label,
    _crossing_time_label,
    _magnitude_label,
    _moon_event_label,
    _object_name,
    _reference_label,
)
from .selection import CatalogSelection, catalog_label

NAVY = colors.HexColor("#18344A")
TEAL = colors.HexColor("#2B7282")
PALE_TEAL = colors.HexColor("#E7F1F3")
PALE_BLUE = colors.HexColor("#F2F6F8")
MID_GREY = colors.HexColor("#64727D")
LIGHT_GREY = colors.HexColor("#D6DEE3")
GOLD = colors.HexColor("#D5A33B")


class PdfExportError(RuntimeError):
    """Erreur contrôlée pendant la création du rapport PDF."""


def _register_fonts() -> None:
    fonts_directory = Path(reportlab.__file__).resolve().parent / "fonts"
    fonts = {
        "AstrolistSans": "Vera.ttf",
        "AstrolistSansBold": "VeraBd.ttf",
    }
    for name, filename in fonts.items():
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(fonts_directory / filename)))
    pdfmetrics.registerFontFamily(
        "AstrolistSans",
        normal="AstrolistSans",
        bold="AstrolistSansBold",
    )


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "AstrolistTitle",
            parent=base["Title"],
            fontName="AstrolistSansBold",
            fontSize=20,
            leading=24,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "AstrolistSubtitle",
            parent=base["Normal"],
            fontName="AstrolistSans",
            fontSize=9,
            leading=12,
            textColor=MID_GREY,
            spaceAfter=12,
        ),
        "section": ParagraphStyle(
            "AstrolistSection",
            parent=base["Heading2"],
            fontName="AstrolistSansBold",
            fontSize=11,
            leading=14,
            textColor=NAVY,
            spaceBefore=8,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "AstrolistBody",
            parent=base["BodyText"],
            fontName="AstrolistSans",
            fontSize=8.2,
            leading=10.5,
            textColor=colors.HexColor("#26343D"),
        ),
        "small": ParagraphStyle(
            "AstrolistSmall",
            parent=base["BodyText"],
            fontName="AstrolistSans",
            fontSize=7,
            leading=9,
            textColor=MID_GREY,
        ),
        "label": ParagraphStyle(
            "AstrolistLabel",
            parent=base["BodyText"],
            fontName="AstrolistSansBold",
            fontSize=7.2,
            leading=9,
            textColor=NAVY,
        ),
        "value": ParagraphStyle(
            "AstrolistValue",
            parent=base["BodyText"],
            fontName="AstrolistSans",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#26343D"),
        ),
        "card_title": ParagraphStyle(
            "AstrolistCardTitle",
            parent=base["BodyText"],
            fontName="AstrolistSansBold",
            fontSize=9.5,
            leading=11,
            textColor=colors.white,
        ),
        "card_meta": ParagraphStyle(
            "AstrolistCardMeta",
            parent=base["BodyText"],
            fontName="AstrolistSans",
            fontSize=7.5,
            leading=9,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
    }


def _paragraph(text: object, style: ParagraphStyle) -> Paragraph:
    normalized = (
        str(text)
        .replace("′", "'")
        .replace("″", '"')
        .replace("–", "-")
        .replace("—", "-")
        .replace("‑", "-")
        .replace("→", " à ")
    )
    return Paragraph(escape(normalized), style)


def _section(title: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return _paragraph(title.upper(), styles["section"])


def _number(value: float | None, unit: str, decimals: int = 0) -> str:
    if value is None:
        return "-"
    return f"{value:.{decimals}f} {unit}".rstrip()


def _quality(value: float | None, description: str = "") -> str:
    label = _number(value, "%")
    return f"{label} ({description})" if value is not None and description else label


def _metadata_rows(
    *,
    window: ObservationWindow,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float,
    field_of_view: FieldOfView,
    max_magnitude: float | None,
    sample_minutes: float,
    object_kind: str | CatalogSelection,
) -> tuple[tuple[str, str], ...]:
    variable_stars = object_kind == "variable_stars"
    catalog = catalog_label(object_kind)
    if isinstance(object_kind, CatalogSelection):
        magnitude = object_kind.filter_label
    elif max_magnitude is None:
        magnitude = "Aucune limite"
    elif variable_stars:
        magnitude = f"Maximum d'éclat <= {max_magnitude:g}"
    else:
        magnitude = f"Magnitude apparente <= {max_magnitude:g}"
    return (
        ("Catalogue", catalog),
        (
            "Date et heures",
            f"{window.start_local:%Y-%m-%d %H:%M} à {window.end_local:%Y-%m-%d %H:%M}",
        ),
        (
            "Fuseau horaire",
            (
                f"{window.timezone_name} ({window.start_local.tzname()} à "
                f"{window.end_local.tzname()})"
            ),
        ),
        (
            "Coordonnées",
            f"{latitude_deg:.5f}°, {longitude_deg:.5f}°; altitude {elevation_m:g} m",
        ),
        (
            "Centre de visée",
            (
                f"Azimut {field_of_view.azimuth_center_deg:g}°; "
                f"hauteur {field_of_view.altitude_center_deg:g}°"
            ),
        ),
        (
            "Champ de vision",
            (
                f"Azimuts {field_of_view.azimuth_start_deg:g}° à "
                f"{field_of_view.azimuth_end_deg:g}°; hauteurs "
                f"{field_of_view.altitude_lower_deg:g}° à "
                f"{field_of_view.altitude_upper_deg:g}°"
            ),
        ),
        ("Filtre photométrique", f"Bande V; {magnitude}"),
        (
            "Critère d'inclusion",
            (
                f"Présent dans le champ à au moins un échantillon de "
                f"{sample_minutes:g} min"
            ),
        ),
    )


def _key_value_table(
    rows: Sequence[tuple[str, str]],
    styles: dict[str, ParagraphStyle],
    *,
    label_width: float,
    total_width: float,
) -> Table:
    data = [
        [_paragraph(label, styles["label"]), _paragraph(value, styles["value"])]
        for label, value in rows
    ]
    table = Table(data, colWidths=[label_width, total_width - label_width])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), PALE_TEAL),
                ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, PALE_BLUE]),
                ("GRID", (0, 0), (-1, -1), 0.35, LIGHT_GREY),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _weather_rows(period: WeatherPeriodSummary) -> tuple[tuple[str, str], ...]:
    return (
        ("Période", f"{period.start_local:%Y-%m-%d %H:%M} à {period.end_local:%H:%M}"),
        ("Nuages", _number(period.cloud_cover_percent, "%")),
        ("Seeing - qualité", _quality(period.seeing_quality_percent, period.seeing_description)),
        (
            "Transparence - qualité",
            _quality(
                period.transparency_quality_percent,
                period.transparency_description,
            ),
        ),
        ("Stabilité - qualité", _quality(period.stability_quality_percent)),
        ("Température", _number(period.temperature_c, "°C", 1)),
        ("Humidité", _number(period.humidity_percent, "%")),
        ("Vent", _number(period.wind_kmh, "km/h", 1)),
        ("Risque de rosée", period.dew_risk or "-"),
        (
            "Risque de précipitation",
            _number(period.precipitation_probability_percent, "%"),
        ),
    )


def _weather_panel(
    summary: WeatherSummary,
    styles: dict[str, ParagraphStyle],
    available_width: float,
) -> list[object]:
    if summary.offline:
        return [_paragraph("Prévisions indisponibles : mode --offline.", styles["body"])]
    if not summary.available:
        lines: list[object] = [
            _paragraph("Prévisions indisponibles pour les périodes demandées.", styles["body"])
        ]
    else:
        panel_width = (available_width - 8) / 2
        evening = _key_value_table(
            _weather_rows(summary.evening),
            styles,
            label_width=1.15 * inch,
            total_width=panel_width,
        )
        predawn = _key_value_table(
            _weather_rows(summary.predawn),
            styles,
            label_width=1.15 * inch,
            total_width=panel_width,
        )
        evening_title = _paragraph(summary.evening.name, styles["label"])
        predawn_title = _paragraph(summary.predawn.name, styles["label"])
        panels = Table(
            [[evening_title, predawn_title], [evening, predawn]],
            colWidths=[panel_width, panel_width],
            hAlign="LEFT",
        )
        panels.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), GOLD),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, 0), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
                ]
            )
        )
        lines = [panels]
    if summary.sources:
        lines.extend(
            [Spacer(1, 4), _paragraph(f"Sources : {summary.sources}", styles["small"])]
        )
    lines.extend(
        _paragraph(f"Avertissement : {warning}.", styles["small"])
        for warning in summary.warnings
        if not summary.offline
    )
    return lines


def _moon_rows(
    summary: MoonSummary, window: ObservationWindow
) -> tuple[tuple[str, str], ...]:
    start = window.start_local
    daily = summary.daily_illumination_reference_local
    return (
        (f"Phase au début ({start:%Y-%m-%d %H:%M})", summary.phase_name),
        ("Illumination au début", f"{summary.illumination_percent:.1f} %"),
        (
            f"Illumination quotidienne ({daily:%Y-%m-%d %H:%M})",
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


def _result_card(
    result: VisibilityResult,
    *,
    styles: dict[str, ParagraphStyle],
    window: ObservationWindow,
    minimum_altitude_deg: float,
    show_details: bool,
    available_width: float,
) -> KeepTogether:
    star = result.star
    title = _object_name(result)
    common_name = getattr(star, "common_name", "")
    if common_name:
        title = f"{title} - {common_name}"
    data: list[list[object]] = [
        [
            _paragraph(title, styles["card_title"]),
            "",
            _paragraph(
                f"{star.object_type or '-'} | {result.constellation or '-'}",
                styles["card_meta"],
            ),
            "",
        ],
        [
            _paragraph("Taille apparente", styles["label"]),
            _paragraph(_apparent_size_label(result), styles["value"]),
            _paragraph("Magnitude V", styles["label"]),
            _paragraph(_magnitude_label(result), styles["value"]),
        ],
        [
            _paragraph("Séparation solaire maximale", styles["label"]),
            _paragraph(
                result.maximum_solar_separation_date.isoformat()
                if result.maximum_solar_separation_date is not None
                else "-",
                styles["value"],
            ),
            _paragraph("Meilleure visibilité saisonnière", styles["label"]),
            _paragraph(
                result.best_seasonal_visibility_date.isoformat()
                if result.best_seasonal_visibility_date is not None
                else "-",
                styles["value"],
            ),
        ],
        [
            _paragraph(f"Monte >= {minimum_altitude_deg:g}°", styles["label"]),
            _paragraph(
                _crossing_time_label(
                    result.rises_above_minimum_local,
                    reference_date=window.start_local.date(),
                    always_above=result.always_above_minimum,
                ),
                styles["value"],
            ),
            _paragraph(f"Descend < {minimum_altitude_deg:g}°", styles["label"]),
            _paragraph(
                _crossing_time_label(
                    result.sets_below_minimum_local,
                    reference_date=window.start_local.date(),
                    always_above=result.always_above_minimum,
                ),
                styles["value"],
            ),
        ],
        [
            _paragraph("Hauteur au début", styles["label"]),
            _paragraph(f"{result.altitude_start_deg:+.1f}°", styles["value"]),
            _paragraph("Hauteur à la fin", styles["label"]),
            _paragraph(f"{result.altitude_end_deg:+.1f}°", styles["value"]),
        ],
    ]
    if show_details:
        if star.size_source:
            size_detail = (
                f"Taille : catalogue {star.size_source}; "
                f"{_reference_label(star.size_reference)}; "
                f"récupéré le {star.size_retrieved_on}."
            )
        else:
            size_detail = "Taille : provenance non disponible."
        magnitude_detail = (
            f"Magnitude : catalogue {star.magnitude_source or 'inconnu'}; "
            f"{_reference_label(star.magnitude_reference)}; récupéré le "
            f"{star.magnitude_retrieved_on or 'date inconnue'}."
        )
        data.extend(
            [
                [_paragraph(size_detail, styles["small"]), "", "", ""],
                [_paragraph(magnitude_detail, styles["small"]), "", "", ""],
            ]
        )
    label_width = 1.35 * inch
    value_width = available_width / 2 - label_width
    card = Table(
        data,
        colWidths=[label_width, value_width, label_width, value_width],
        hAlign="LEFT",
    )
    commands: list[tuple] = [
        ("SPAN", (0, 0), (1, 0)),
        ("SPAN", (2, 0), (3, 0)),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 1), (0, -1), PALE_TEAL),
        ("BACKGROUND", (2, 1), (2, -1), PALE_TEAL),
        ("ROWBACKGROUNDS", (1, 1), (1, -1), [colors.white, PALE_BLUE]),
        ("ROWBACKGROUNDS", (3, 1), (3, -1), [colors.white, PALE_BLUE]),
        ("GRID", (0, 1), (-1, -1), 0.3, LIGHT_GREY),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if show_details:
        detail_start = len(data) - 2
        commands.extend(
            [
                ("SPAN", (0, detail_start), (3, detail_start)),
                ("SPAN", (0, detail_start + 1), (3, detail_start + 1)),
                ("BACKGROUND", (0, detail_start), (-1, -1), PALE_BLUE),
            ]
        )
    card.setStyle(TableStyle(commands))
    return KeepTogether([card, Spacer(1, 6)])


def _notes(object_kind: str | CatalogSelection) -> tuple[str, ...]:
    notes = [
        "Les hauteurs du tableau sont géométriques, sans réfraction atmosphérique.",
        (
            "Le lever et le coucher lunaires utilisent le bord supérieur apparent, "
            "le demi-diamètre variable et une réfraction standard de 34 minutes d'arc."
        ),
        (
            "Le seeing, la transparence et la stabilité sont des indices de qualité "
            "normalisés de 0 à 100; une valeur élevée est favorable."
        ),
        (
            "Le risque de rosée est estimé à partir de l'écart température-point de "
            "rosée et de l'humidité relative prévus par Open-Meteo."
        ),
        (
            "La séparation solaire maximale est un maximum angulaire géométrique et "
            "ne constitue pas une opposition pour un objet du ciel profond."
        ),
        (
            "La meilleure visibilité saisonnière correspond à la culmination "
            "supérieure la plus proche de minuit civil local, sans Lune, météo ni "
            "crépuscule."
        ),
    ]
    if isinstance(object_kind, CatalogSelection):
        notes.extend(object_kind.notes)
    elif object_kind == "variable_stars":
        notes.append(
            "La magnitude des étoiles variables est le maximum d'éclat publié, "
            "et non une prévision instantanée."
        )
    elif object_kind == "ngc":
        notes.append("Données NGC : OpenNGC; composants distincts inclus, hors doublons.")
    else:
        notes.append(
            "Données OpenNGC; complément de magnitude V SIMBAD si exploitable."
            if object_kind == "caldwell"
            else "Les dimensions et magnitudes privilégient SIMBAD, avec repli OpenNGC."
        )
    return tuple(notes)


def _decorate_page(canvas, document) -> None:
    canvas.saveState()
    width, height = letter
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 0.16 * inch, width, 0.16 * inch, fill=1, stroke=0)
    canvas.setStrokeColor(TEAL)
    canvas.setLineWidth(0.6)
    canvas.line(0.55 * inch, 0.42 * inch, width - 0.55 * inch, 0.42 * inch)
    canvas.setFillColor(MID_GREY)
    canvas.setFont("AstrolistSans", 7)
    canvas.drawString(0.55 * inch, 0.25 * inch, "GNU Astrolist - Rapport d'observation")
    canvas.drawRightString(width - 0.55 * inch, 0.25 * inch, f"Page {document.page}")
    canvas.restoreState()


def _build_pdf(
    path: Path,
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
    show_details: bool,
) -> None:
    _register_fonts()
    styles = _styles()
    document = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.46 * inch,
        bottomMargin=0.55 * inch,
        title="GNU Astrolist - Rapport d'observation",
        author="GNU Astrolist",
        subject="Planification d'une soirée d'observation astronomique",
    )
    available_width = letter[0] - document.leftMargin - document.rightMargin
    story: list[object] = [
        _paragraph("SOIRÉE D'OBSERVATION", styles["title"]),
        _paragraph(
            f"GNU ASTROLIST | {window.start_local:%Y-%m-%d} | "
            f"{window.timezone_name}",
            styles["subtitle"],
        ),
        _key_value_table(
            _metadata_rows(
                window=window,
                latitude_deg=latitude_deg,
                longitude_deg=longitude_deg,
                elevation_m=elevation_m,
                field_of_view=field_of_view,
                max_magnitude=max_magnitude,
                sample_minutes=sample_minutes,
                object_kind=object_kind,
            ),
            styles,
            label_width=1.45 * inch,
            total_width=available_width,
        ),
        _section("Conditions météo", styles),
    ]
    story.extend(_weather_panel(weather_summary, styles, available_width))
    story.extend(
        [
            _section("Résumé de la Lune", styles),
            _key_value_table(
                _moon_rows(moon_summary, window),
                styles,
                label_width=2.55 * inch,
                total_width=available_width,
            ),
            CondPageBreak(2.1 * inch),
            _section("Liste d'observation", styles),
        ]
    )
    if results:
        for result in results:
            story.append(
                _result_card(
                    result,
                    styles=styles,
                    window=window,
                    minimum_altitude_deg=field_of_view.altitude_lower_deg,
                    show_details=show_details,
                    available_width=available_width,
                )
            )
        if len(results) < matched_count:
            count = f"{len(results)} objet(s) affiché(s) sur {matched_count} trouvé(s)."
        else:
            count = f"{matched_count} objet(s) trouvé(s)."
        story.append(_paragraph(count, styles["body"]))
    else:
        story.append(
            _paragraph(
                "Aucun objet du catalogue ne satisfait les critères.",
                styles["body"],
            )
        )
    story.extend([_section("Notes méthodologiques", styles)])
    for note in _notes(object_kind):
        story.append(_paragraph(f"• {note}", styles["small"]))
        story.append(Spacer(1, 2))
    document.build(story, onFirstPage=_decorate_page, onLaterPages=_decorate_page)


def export_pdf_report(
    path: Path,
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
    show_details: bool,
) -> None:
    """Crée atomiquement un PDF portrait au format lettre 8,5 x 11 pouces."""

    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            prefix=f".{path.stem}-",
            suffix=".pdf",
            dir=path.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        _build_pdf(
            temporary_path,
            window=window,
            latitude_deg=latitude_deg,
            longitude_deg=longitude_deg,
            elevation_m=elevation_m,
            field_of_view=field_of_view,
            max_magnitude=max_magnitude,
            sample_minutes=sample_minutes,
            weather_summary=weather_summary,
            moon_summary=moon_summary,
            results=results,
            matched_count=matched_count,
            object_kind=object_kind,
            show_details=show_details,
        )
        temporary_path.replace(path)
    except Exception as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise PdfExportError(f"impossible de créer le rapport PDF {path}: {exc}") from exc
