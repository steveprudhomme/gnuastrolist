"""Interface en ligne de commande de GNU Astrolist."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from astropy.utils import iers

from . import __version__
from .catalog import filter_by_magnitude, load_catalog
from .models import FieldOfView
from .output import render_report
from .time_utils import parse_observation_window
from .visibility import compute_visibility


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gnu-astrolist",
        description=(
            "Liste les étoiles variables qui traversent un champ Alt/Az pendant une soirée."
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
        "--fov-h", required=True, type=float, help="largeur horizontale en degrés (0 à 360)"
    )
    parser.add_argument(
        "--fov-v", required=True, type=float, help="hauteur du champ en degrés (0 à 90)"
    )
    parser.add_argument(
        "--az-center",
        type=float,
        default=180.0,
        help="azimut du centre, nord=0°, est=90° (défaut : 180, sud)",
    )
    parser.add_argument(
        "--alt-center",
        type=float,
        default=45.0,
        help="hauteur du centre au-dessus de l'horizon (défaut : 45)",
    )
    parser.add_argument(
        "--objects",
        required=True,
        choices=("variable_stars",),
        help="type d'objets (prototype : variable_stars)",
    )
    parser.add_argument(
        "--max-magnitude",
        type=float,
        default=8.0,
        help="magnitude V maximale au maximum d'éclat (défaut : 8)",
    )
    parser.add_argument(
        "--all-magnitudes",
        action="store_true",
        help="désactive --max-magnitude et utilise tout le catalogue visuel",
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
        field_of_view = FieldOfView(
            azimuth_center_deg=args.az_center,
            altitude_center_deg=args.alt_center,
            horizontal_deg=args.fov_h,
            vertical_deg=args.fov_v,
        )
    except ValueError as exc:
        parser.error(str(exc))

    iers.conf.auto_download = not args.offline
    iers.conf.iers_degraded_accuracy = "warn"

    max_magnitude = None if args.all_magnitudes else args.max_magnitude
    stars = filter_by_magnitude(load_catalog(), max_magnitude)
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
        )
    )
    return 0
