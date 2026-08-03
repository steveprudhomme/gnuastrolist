"""Interface en ligne de commande de GNU Astrolist."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from astropy.utils import iers

from . import __version__
from .catalog import (
    filter_by_magnitude,
    load_messier_catalog,
    load_variable_star_catalog,
)
from .models import FieldOfView
from .output import render_report
from .time_utils import parse_observation_window
from .visibility import compute_visibility


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
        choices=("variable_stars", "messier", "messier_objects"),
        help="catalogue : variable_stars ou messier (messier_objects est un alias)",
    )
    magnitudes = parser.add_mutually_exclusive_group()
    magnitudes.add_argument(
        "--max-magnitude",
        type=float,
        default=None,
        help=(
            "magnitude V maximale (défaut : 8 pour variable_stars; "
            "aucune limite pour messier)"
        ),
    )
    magnitudes.add_argument(
        "--all-magnitudes",
        action="store_true",
        help="désactive la limite de magnitude et utilise tout le catalogue choisi",
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
        help="interdit la mise à jour réseau des données IERS par Astropy",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
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

    object_kind = "messier" if args.objects in {"messier", "messier_objects"} else args.objects
    if args.all_magnitudes:
        max_magnitude = None
    elif args.max_magnitude is not None:
        max_magnitude = args.max_magnitude
    else:
        max_magnitude = 8.0 if object_kind == "variable_stars" else None

    catalog = (
        load_variable_star_catalog()
        if object_kind == "variable_stars"
        else load_messier_catalog()
    )
    stars = filter_by_magnitude(catalog, max_magnitude)
    try:
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
    print(
        render_report(
            window=window,
            latitude_deg=args.lat,
            longitude_deg=args.lon,
            elevation_m=args.elevation_m,
            field_of_view=field_of_view,
            max_magnitude=max_magnitude,
            sample_minutes=args.sample_minutes,
            results=displayed_results,
            matched_count=matched_count,
            object_kind=object_kind,
        )
    )
    return 0
