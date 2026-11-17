"""Interface en ligne de commande de GNU Astrolist."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import fields, replace
from pathlib import Path

from . import __version__
from .application import (
    ApplicationDependencies,
    ObservationApplication,
    ObservationRequest,
    astronomical_context,
)
from .asteroids import compute_asteroid_visibility, load_asteroid_catalog
from .catalog_resources import use_catalog_resources
from .comets import (
    annotate_cbat,
    compute_comet_visibility,
    eligible_orbits,
    load_cbat_observations,
    load_comet_catalog,
)
from .models import FieldOfView
from .moon import compute_moon_summary
from .output import render_report
from .pdf_output import PdfExportError, export_pdf_report
from .report_files import staged_report, validate_report_paths
from .satcat import annotate_space_catalog, load_satcat, load_unoosa_records, select_space_elements
from .satellites import (
    MAX_SAMPLES,
    compute_satellite_visibility,
    eligible_elements,
    load_satellite_elements,
)
from .seestar import annotate_results, protect_outputs, scan_seestar, validate_root
from .selection import load_catalog_selection, normalize_catalogs
from .time_utils import parse_observation_window
from .updates import DEFAULT_MAX_AGE_HOURS, parse_max_age_hours, refresh_catalogs, validate_max_ages
from .validation import (
    finite_number,
    sampling_plan,
    sampling_step,
    validate_magnitude,
    validate_observer,
)
from .visibility import MAX_TIME_SAMPLES, compute_visibility
from .weather import compute_weather_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gnu-astrolist",
        description=(
            "Liste les objets astronomiques qui traversent un champ Alt/Az pendant une soirée."
        ),
    )
    parser.add_argument("--date", required=True, help="date locale de l'observation (AAAA-MM-JJ)")
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
    parser.add_argument("--lon", required=True, type=float, help="longitude en degrés (-180 à 180)")
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
            "élévation minimale du champ en degrés (0 à 90); --fov-v reste accepté comme ancien nom"
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
        choices=(
            "variable_stars",
            "messier",
            "messier_objects",
            "caldwell",
            "ngc",
            "bayer",
            "flamsteed",
            "asteroids",
            "comets",
            "satellites",
            "debris",
        ),
        help="un ou plusieurs catalogues; option répétable (messier_objects : alias de messier)",
    )
    parser.add_argument(
        "--asteroids-file",
        type=Path,
        metavar="FICHIER_JSON",
        help="réponse JPL SBDB Query locale pour actualiser ou étendre les orbites embarquées",
    )
    parser.add_argument(
        "--comets-file",
        type=Path,
        metavar="FICHIER_MPC",
        help="remplace les orbites cométaires par un fichier MPC local",
    )
    parser.add_argument(
        "--cbat-file",
        type=Path,
        metavar="FICHIER_CSV",
        help="observations CBAT/ICQ datées transcrites dans le format CSV documenté",
    )
    updates = parser.add_argument_group("actualisation des catalogues")
    artificial = parser.add_argument_group("satellites et débris")
    artificial.add_argument(
        "--satellite-elements-file",
        type=Path,
        metavar="GP_CSV_JSON",
        help="éléments GP/OMM locaux; remplace la sélection embarquée",
    )
    artificial.add_argument(
        "--satcat-file", type=Path, metavar="SATCAT_CSV", help="métadonnées SATCAT locales"
    )
    artificial.add_argument(
        "--unoosa-file",
        type=Path,
        metavar="REGISTRE_CSV",
        help="extraits locaux du registre ONU dans le CSV documenté",
    )
    artificial.add_argument(
        "--satellite-step-seconds",
        type=float,
        default=5.0,
        help="pas des passages en secondes (défaut : 5)",
    )
    artificial.add_argument(
        "--satellite-max-epoch-hours",
        type=parse_max_age_hours,
        default=168.0,
        help="écart maximal aux éléments GP (défaut : 168 h; aucune garantie de précision)",
    )
    artificial.add_argument(
        "--satellite-optical-only",
        action="store_true",
        help="garde simultanément champ, éclairage solaire et ciel suffisamment sombre; pas une garantie de détection",
    )
    artificial.add_argument(
        "--satellite-max-sun-altitude",
        type=float,
        default=-6.0,
        help="hauteur solaire maximale du filtre optique (défaut : -6 degrés)",
    )
    updates.add_argument(
        "--update-catalogs",
        choices=("never", "if-stale", "force"),
        default=None,
        help="jamais (défaut), si périmé, ou forcé; --offline interdit toute connexion",
    )
    updates.add_argument(
        "--catalog-cache-dir",
        type=Path,
        help="cache sur l’ordinateur (défaut : local/catalog-cache)",
    )
    updates.add_argument(
        "--catalog-max-age-hours", type=parse_max_age_hours, help="âge maximal commun en heures"
    )
    updates.add_argument(
        "--catalog-age",
        action="append",
        default=[],
        metavar="SOURCE=HEURES",
        help="délai propre à un catalogue ou fournisseur; répétable",
    )
    updates.add_argument(
        "--catalog-config",
        type=Path,
        metavar="FICHIER_JSON",
        help="configuration locale des actualisations; les options explicites ont priorité",
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
        "--overwrite", action="store_true",
        help="autorise le remplacement des rapports existants; les entrées restent protégées",
    )
    parser.add_argument(
        "--seestar-path",
        type=Path,
        metavar="DOSSIER",
        help="vérifie les archives Seestar en lecture seule, par exemple E:\\MyWorks",
    )
    return parser


def _validate_numeric_arguments(args: argparse.Namespace) -> None:
    validate_observer(args.lat, args.lon, args.elevation_m)
    validate_magnitude(args.max_magnitude)
    sampling_step(args.sample_minutes, '--sample-minutes', 60)
    sampling_step(args.satellite_step_seconds, '--satellite-step-seconds')
    finite_number(args.satellite_max_sun_altitude, '--satellite-max-sun-altitude', -90, 90)
    FieldOfView.from_automatic_center(
        azimuth_min_deg=args.az_min, azimuth_max_deg=args.az_max,
        minimum_altitude_deg=args.min_altitude, altitude_center_deg=args.alt_center,
    )
    if args.limit is not None and args.limit <= 0:
        raise ValueError('--limit doit être un entier supérieur à zéro')


def _validate_arguments(args: argparse.Namespace) -> None:
    _validate_numeric_arguments(args)
    if (
        args.satellite_elements_file
        or args.satcat_file
        or args.unoosa_file
        or args.satellite_optical_only
    ) and not {"satellites", "debris"}.intersection(args.objects):
        raise ValueError("Les options satellitaires exigent --objects satellites ou debris")
    if (
        args.comets_file is not None or args.cbat_file is not None
    ) and "comets" not in args.objects:
        raise ValueError("--comets-file et --cbat-file exigent --objects comets")
    if args.asteroids_file is not None and "asteroids" not in args.objects:
        raise ValueError("--asteroids-file exige --objects asteroids")


def _export_policy(args, seestar_root, cache_dir=None):
    inputs = tuple(path for path in (
        args.catalog_config, args.asteroids_file, args.comets_file, args.cbat_file,
        args.satellite_elements_file, args.satcat_file, args.unoosa_file,
    ) if path is not None)
    return dict(inputs=inputs, overwrite=args.overwrite, seestar_root=seestar_root,
                protected_roots=(cache_dir,) if cache_dir is not None else ())


def _run(args, parser, update_result, seestar_root, cache_dir) -> int:
    try:
        _validate_arguments(args)
        if seestar_root is not None:
            protect_outputs(seestar_root, (args.output_txt, args.output_pdf))
        request = ObservationRequest(**{
            field.name: getattr(args, field.name) for field in fields(ObservationRequest)
        })
        application = ObservationApplication(ApplicationDependencies(
            load_asteroid_catalog=load_asteroid_catalog,
            eligible_orbits=eligible_orbits,
            load_comet_catalog=load_comet_catalog,
            load_satcat=load_satcat,
            load_satellite_elements=load_satellite_elements,
            select_space_elements=select_space_elements,
            eligible_elements=eligible_elements,
            load_unoosa_records=load_unoosa_records,
            load_cbat_observations=load_cbat_observations,
            compute_weather_summary=compute_weather_summary,
            load_catalog_selection=load_catalog_selection,
            compute_moon_summary=compute_moon_summary,
            compute_visibility=compute_visibility,
            compute_asteroid_visibility=compute_asteroid_visibility,
            compute_comet_visibility=compute_comet_visibility,
            annotate_cbat=annotate_cbat,
            compute_satellite_visibility=compute_satellite_visibility,
            annotate_space_catalog=annotate_space_catalog,
            scan_seestar=scan_seestar,
            annotate_results=annotate_results,
        ))
        report_data = application.prepare_report(
            request, source_notes=update_result.notes, seestar_root=seestar_root,
        )
    except ValueError as exc:
        parser.error(str(exc))
    report = render_report(**report_data.to_kwargs())
    if args.output_txt is not None:
        try:
            policy = _export_policy(args, seestar_root, cache_dir)
            policy["inputs"] += (args.output_pdf,) if args.output_pdf is not None else ()
            with staged_report(args.output_txt, **policy) as temporary:
                temporary.write_text(f"{report}\n", encoding="utf-8")
        except (OSError, ValueError) as exc:
            parser.error(f"impossible d'écrire le rapport dans {args.output_txt}: {exc}")
    if args.output_pdf is not None:
        try:
            export_pdf_report(
                args.output_pdf,
                **report_data.to_kwargs(),
                overwrite=args.overwrite,
                input_paths=(*_export_policy(args, seestar_root)["inputs"],
                             *((args.output_txt,) if args.output_txt is not None else ())),
                protected_roots=(cache_dir,),
            )
        except PdfExportError as exc:
            parser.error(str(exc))
    # Sous Windows, les sorties redirigées héritent parfois de cp1252, qui ne
    # peut pas représenter les flèches et symboles astronomiques du rapport.
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(report)
    return 0


def _update_settings(args):
    config = {}
    if args.catalog_config:
        try:
            config = json.loads(args.catalog_config.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError("Configuration de catalogues illisible") from exc
        if not isinstance(config, dict) or set(config) - {"mode", "cache_dir", "max_age_hours"}:
            raise ValueError("Clés de configuration de catalogues incorrectes")
    ages = config.get("max_age_hours", {})
    if not isinstance(ages, dict):
        raise ValueError("max_age_hours doit associer une source à un nombre d’heures")
    ages = dict(ages)
    if args.catalog_max_age_hours is not None:
        ages.update(dict.fromkeys(DEFAULT_MAX_AGE_HOURS, args.catalog_max_age_hours))
    for setting in args.catalog_age:
        key, separator, value = setting.partition("=")
        if not separator:
            raise ValueError("--catalog-age attend SOURCE=HEURES")
        try:
            ages[key] = parse_max_age_hours(value)
        except argparse.ArgumentTypeError as exc:
            raise ValueError(str(exc)) from exc
    directory = args.catalog_cache_dir or config.get("cache_dir", "local/catalog-cache")
    if not isinstance(directory, (str, Path)):
        raise ValueError("cache_dir doit désigner un dossier local")
    mode = args.update_catalogs or config.get("mode", "never")
    if not isinstance(mode, str) or mode not in {"never", "if-stale", "force"}:
        raise ValueError("Mode de mise à jour inconnu : never, if-stale ou force requis")
    if not str(directory).strip() or '\0' in str(directory):
        raise ValueError('cache_dir doit désigner un chemin non vide sans caractère nul')
    return mode, Path(directory), validate_max_ages(ages)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        _validate_numeric_arguments(args)
        root = validate_root(args.seestar_path) if args.seestar_path is not None else None
        validate_report_paths((args.output_txt, args.output_pdf), **_export_policy(args, root))
        _validate_arguments(args)
        checked_window = parse_observation_window(args.date, args.time_range, args.timezone)
        selected = normalize_catalogs(args.objects)
        if set(selected) - {'satellites', 'debris'}:
            sampling_plan(checked_window, args.sample_minutes, MAX_TIME_SAMPLES, '--sample-minutes', 60)
        if {'satellites', 'debris'}.intersection(selected):
            sampling_plan(checked_window, args.satellite_step_seconds, MAX_SAMPLES,
                          '--satellite-step-seconds')
        FieldOfView.from_automatic_center(
            azimuth_min_deg=args.az_min,
            azimuth_max_deg=args.az_max,
            minimum_altitude_deg=args.min_altitude,
            altitude_center_deg=args.alt_center,
        )
        mode, directory, ages = _update_settings(args)
        validate_report_paths((args.output_txt, args.output_pdf),
                              **_export_policy(args, root, directory))
        kinds = tuple(
            kind
            for kind in normalize_catalogs(args.objects)
            if not (kind == "asteroids" and args.asteroids_file is not None)
            and not (kind == "comets" and args.comets_file is not None)
            and not (
                kind in ("satellites", "debris")
                and (args.satellite_elements_file or args.satcat_file)
            )
        )
        # Activer la politique réseau seulement après le précontrôle complet,
        # avant toute conversion Astropy ou actualisation susceptible d'en utiliser.
        with astronomical_context(args.offline):
            result = refresh_catalogs(
                kinds,
                mode=mode,
                offline=args.offline,
                cache_dir=directory,
                max_age_hours=ages,
                seestar_root=root,
            )
            configured = (
                args.catalog_config
                or args.update_catalogs
                or args.catalog_age
                or args.catalog_max_age_hours is not None
                or args.catalog_cache_dir
            )
            if not configured and not result.resources:
                result = replace(result, notes=())
            with use_catalog_resources(result.resources):
                return _run(args, parser, result, root, directory)
    except ValueError as exc:
        parser.error(str(exc))
