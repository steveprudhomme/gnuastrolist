"""Interface en ligne de commande de GNU Astrolist."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from astropy.utils import iers

from . import __version__
from .models import FieldOfView
from .moon import compute_moon_summary
from .output import render_report
from .pdf_output import PdfExportError, export_pdf_report
from .seestar import annotate_results, protect_outputs, scan_seestar, validate_root
from .selection import load_catalog_selection
from .time_utils import parse_observation_window
from .visibility import compute_visibility
from .weather import compute_weather_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gnu-astrolist",
        description=(
            "Liste les objets astronomiques qui traversent un champ Alt/Az pendant une soirée."
        ),
    )
    parser.add_argument(
        "--date", required=True, help="date locale de l'observation (AAAA-MM-JJ)"
    )
    parser.add_argument(
        "--time-range",
        required=True,
        metavar="HH:MM-HH:MM",
        help="plage horaire locale; une fin plus petite passe au lendemain",
    )
    parser.add_argument(
        "--timezone",
        default="UTC",
        help="fuseau IANA, par exemple America/Toronto (défaut : UTC)",
    )
    parser.add_argument("--lat", required=True, type=float, help="latitude en degrés (-90 à 90)")
    parser.add_argument(
        "--lon", required=True, type=float, help="longitude en degrés (-180 à 180)"
    )
    parser.add_argument(
        "--elevation-m", type=float, default=0.0, help="altitude du site en mètres (défaut : 0)"
    )
    parser.add_argument(
        "--az-min",
        required=True,
        type=float,
        help="limite azimutale de départ en degrés (0 à 360)",
    )
    parser.add_argument(
        "--az-max",
        required=True,
        type=float,
        help="limite azimutale de fin en degrés (0 à 360)",
    )
    parser.add_argument(
        "--min-altitude",
        "--fov-v",
        dest="min_altitude",
        required=True,
        type=float,
        help=(
            "élévation minimale du champ en degrés (0 à 90); "
            "--fov-v reste accepté comme ancien nom"
        ),
    )
    advanced = parser.add_argument_group("réglages avancés du centre de visée")
    advanced.add_argument(
        "--alt-center",
        type=float,
        default=None,
        help="remplace le centre vertical calculé automatiquement",
    )
    parser.add_argument(
        "--objects",
        required=True,
        nargs="+",
        action="extend",
        choices=("variable_stars", "messier", "messier_objects", "caldwell", "ngc", 'bayer', 'flamsteed'),
        help="un ou plusieurs catalogues; option répétable (messier_objects : alias de messier)",
    )
    magnitudes = parser.add_mutually_exclusive_group()
    magnitudes.add_argument(
        "--max-magnitude",
        type=float,
        default=None,
        help=(
            "magnitude V maximale (défaut : 8 pour variable_stars; "
            "aucune limite pour les autres catalogues)"
        ),
    )
    magnitudes.add_argument(
        "--all-magnitudes",
        action="store_true",
        help="désactive les limites de magnitude dans tous les catalogues choisis",
    )
    parser.add_argument(
        "--sample-minutes",
        type=float,
        default=10.0,
        help="pas de recherche dans la plage horaire (défaut : 10 min)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="nombre maximal de lignes affichées après le tri (aucune limite par défaut)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="désactive les prévisions météo et la mise à jour réseau des données IERS",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="affiche la provenance détaillée des tailles et magnitudes",
    )
    parser.add_argument(
        "--output-txt",
        type=Path,
        metavar="FICHIER",
        help="enregistre une copie UTF-8 du rapport complet dans un fichier texte",
    )
    parser.add_argument(
        "--output-pdf",
        type=Path,
        metavar="FICHIER",
        help="crée un rapport PDF mis en page au format lettre 8,5 x 11 po",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        '--seestar-path', type=Path, metavar='DOSSIER',
        help='vérifie les archives Seestar en lecture seule, par exemple E:\\MyWorks',
    )
    return parser


def _validate_arguments(args: argparse.Namespace) -> None:
    if not -90.0 <= args.lat <= 90.0:
        raise ValueError("--lat doit être compris entre -90 et 90")
    if not -180.0 <= args.lon <= 180.0:
        raise ValueError("--lon doit être compris entre -180 et 180")
    if args.sample_minutes <= 0.0:
        raise ValueError("--sample-minutes doit être supérieur à zéro")
    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit doit être un entier supérieur à zéro")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        _validate_arguments(args)
        seestar_root = validate_root(args.seestar_path) if args.seestar_path is not None else None
        if seestar_root is not None:
            protect_outputs(seestar_root, (args.output_txt, args.output_pdf))
        window = parse_observation_window(args.date, args.time_range, args.timezone)
        field_of_view = FieldOfView.from_automatic_center(
            azimuth_min_deg=args.az_min,
            azimuth_max_deg=args.az_max,
            minimum_altitude_deg=args.min_altitude,
            altitude_center_deg=args.alt_center,
        )
    except ValueError as exc:
        parser.error(str(exc))

    iers.conf.auto_download = not args.offline
    # En mode hors ligne, accepter la table prédictive embarquée même si elle
    # a plus de 30 jours; Astropy émettra au besoin l'avertissement configuré.
    iers.conf.auto_max_age = None if args.offline else 30.0
    iers.conf.iers_degraded_accuracy = "warn"

    weather_summary = compute_weather_summary(
        window=window,
        latitude_deg=args.lat,
        longitude_deg=args.lon,
        offline=args.offline,
    )

    stars, selection = load_catalog_selection(
        args.objects, args.max_magnitude, args.all_magnitudes
    )
    object_kind = selection.kinds[0] if len(selection.kinds) == 1 else selection
    max_magnitude = selection.limits[0] if len(selection.kinds) == 1 else args.max_magnitude
    try:
        moon_summary = compute_moon_summary(
            window=window,
            latitude_deg=args.lat,
            longitude_deg=args.lon,
            elevation_m=args.elevation_m,
        )
        results = compute_visibility(
            stars=stars,
            window=window,
            latitude_deg=args.lat,
            longitude_deg=args.lon,
            elevation_m=args.elevation_m,
            field_of_view=field_of_view,
            sample_minutes=args.sample_minutes,
        )
    except ValueError as exc:
        parser.error(str(exc))
    matched_count = len(results)
    displayed_results = results[: args.limit] if args.limit is not None else results
    try:
        inventory = scan_seestar(seestar_root) if seestar_root is not None else None
    except ValueError as exc:
        parser.error(str(exc))
    if inventory is not None:
        displayed_results = annotate_results(displayed_results, inventory)
    report = render_report(
        window=window,
        latitude_deg=args.lat,
        longitude_deg=args.lon,
        elevation_m=args.elevation_m,
        field_of_view=field_of_view,
        max_magnitude=max_magnitude,
        sample_minutes=args.sample_minutes,
        weather_summary=weather_summary,
        moon_summary=moon_summary,
        results=displayed_results,
        matched_count=matched_count,
        object_kind=object_kind,
        show_details=args.details,
        seestar_inventory=inventory,
    )
    if args.output_txt is not None:
        try:
            if seestar_root is not None:
                protect_outputs(seestar_root, (args.output_txt,))
            args.output_txt.write_text(f"{report}\n", encoding="utf-8")
        except (OSError, ValueError) as exc:
            parser.error(
                f"impossible d'écrire le rapport dans {args.output_txt}: {exc}"
            )
    if args.output_pdf is not None:
        try:
            export_pdf_report(
                args.output_pdf,
                window=window,
                latitude_deg=args.lat,
                longitude_deg=args.lon,
                elevation_m=args.elevation_m,
                field_of_view=field_of_view,
                max_magnitude=max_magnitude,
                sample_minutes=args.sample_minutes,
                weather_summary=weather_summary,
                moon_summary=moon_summary,
                results=displayed_results,
                matched_count=matched_count,
                object_kind=object_kind,
                show_details=args.details,
                seestar_inventory=inventory,
            )
        except PdfExportError as exc:
            parser.error(str(exc))
    # Sous Windows, les sorties redirigées héritent parfois de cp1252, qui ne
    # peut pas représenter les flèches et symboles astronomiques du rapport.
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(report)
    return 0
