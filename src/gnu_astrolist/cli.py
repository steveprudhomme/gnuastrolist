"""Interface en ligne de commande de GNU Astrolist."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from astropy.time import Time
from astropy.utils import iers

from . import __version__
from .asteroids import compute_asteroid_visibility, load_asteroid_catalog
from .catalog_resources import use_catalog_resources
from .comets import (
    annotate_cbat,
    compute_comet_visibility,
    eligible_orbits,
    load_cbat_observations,
    load_comet_catalog,
)
from .models import FieldOfView, apparent_magnitude
from .moon import compute_moon_summary
from .output import render_report
from .pdf_output import PdfExportError, export_pdf_report
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
from .updates import DEFAULT_MAX_AGE_HOURS, parse_max_age_hours, refresh_catalogs
from .visibility import compute_visibility
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
        type=parse_max_age_hours,
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
        "--seestar-path",
        type=Path,
        metavar="DOSSIER",
        help="vérifie les archives Seestar en lecture seule, par exemple E:\\MyWorks",
    )
    return parser


def _validate_arguments(args: argparse.Namespace) -> None:
    if (
        args.satellite_elements_file
        or args.satcat_file
        or args.unoosa_file
        or args.satellite_optical_only
    ) and not {"satellites", "debris"}.intersection(args.objects):
        raise ValueError("Les options satellitaires exigent --objects satellites ou debris")
    if not -90 <= args.satellite_max_sun_altitude <= 90:
        raise ValueError("--satellite-max-sun-altitude doit être entre -90 et 90")
    if (
        args.comets_file is not None or args.cbat_file is not None
    ) and "comets" not in args.objects:
        raise ValueError("--comets-file et --cbat-file exigent --objects comets")
    if args.asteroids_file is not None and "asteroids" not in args.objects:
        raise ValueError("--asteroids-file exige --objects asteroids")
    if not -90.0 <= args.lat <= 90.0:
        raise ValueError("--lat doit être compris entre -90 et 90")
    if not -180.0 <= args.lon <= 180.0:
        raise ValueError("--lon doit être compris entre -180 et 180")
    if args.sample_minutes <= 0.0:
        raise ValueError("--sample-minutes doit être supérieur à zéro")
    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit doit être un entier supérieur à zéro")


def _run(args, parser, update_result, seestar_root) -> int:
    try:
        _validate_arguments(args)
        orbits = load_asteroid_catalog(args.asteroids_file) if "asteroids" in args.objects else ()
        if seestar_root is not None:
            protect_outputs(seestar_root, (args.output_txt, args.output_pdf))
        window = parse_observation_window(args.date, args.time_range, args.timezone)
        comet_orbits, excluded = (
            eligible_orbits(
                load_comet_catalog(args.comets_file), Time([window.start_local, window.end_local])
            )
            if "comets" in args.objects
            else ((), 0)
        )
        if "comets" in args.objects and not comet_orbits:
            raise ValueError("Aucune orbite MPC à époque exploitable; actualisez --comets-file")
        has_space = bool({"satellites", "debris"}.intersection(args.objects))
        space_elements, space_records, registry_records = (), {}, ()
        space_notes = []
        if has_space:
            space_records = load_satcat(args.satcat_file)
            all_elements = load_satellite_elements(args.satellite_elements_file)
            chosen, skip_types = select_space_elements(
                all_elements, space_records, args.objects, window
            )
            space_elements, old = eligible_elements(
                chosen, Time([window.start_local, window.end_local]), args.satellite_max_epoch_hours
            )
            if chosen and not space_elements:
                raise ValueError(
                    "Aucun élément GP assez récent pour cette plage; actualisez les éléments satellitaires"
                )
            registry_records = load_unoosa_records(args.unoosa_file) if args.unoosa_file else ()
            space_notes = [
                f"GP/SATCAT : {len(all_elements)} éléments, {len(space_records)} fiches; {len(space_elements)} orbites sélectionnées, {len(old)} exclues pour âge; autres exclusions : {skip_types}.",
                f"Pas satellite : {args.satellite_step_seconds:g} s; âge maximal GP ±{args.satellite_max_epoch_hours:g} h. Copie partielle, sans garantie d’exhaustivité.",
                f"Filtre optique satellite : {'activé' if args.satellite_optical_only else 'désactivé'}; plafond Soleil {args.satellite_max_sun_altitude:g}° lorsqu’activé.",
                f"UNOOSA : {len(registry_records)} extrait(s) local(aux); aucune lecture du registre en ligne.",
            ]
        cbat = load_cbat_observations(args.cbat_file) if args.cbat_file else ()
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

    stars, selection = load_catalog_selection(args.objects, args.max_magnitude, args.all_magnitudes)
    if orbits:
        origin = "Fichier orbital fourni" if args.asteroids_file else "Copie orbitale embarquée"
        selection = replace(
            selection,
            source_notes=(
                f"{origin} : {len(orbits)} astéroïdes; époques JD TDB "
                f"{min(o.epoch for o in orbits):.6f} à {max(o.epoch for o in orbits):.6f}.",
            ),
        )
    if comet_orbits:
        selection = replace(
            selection,
            source_notes=(
                *selection.source_notes,
                f"MPC : {len(comet_orbits)} orbites exploitables; {excluded} exclues (époque absente ou éloignée de plus de 365 jours).",
                f"CBAT : {len(cbat)} observation(s) locale(s) chargée(s); seules les observations antérieures au début sont affichables."
                if cbat
                else "CBAT : aucune observation locale fournie; aucune mesure téléchargée.",
            ),
        )
    if update_result.notes:
        selection = replace(selection, source_notes=(*selection.source_notes, *update_result.notes))
    if has_space:
        selection = replace(selection, source_notes=(*selection.source_notes, *space_notes))
    object_kind = (
        selection.kinds[0]
        if len(selection.kinds) == 1
        and not orbits
        and not comet_orbits
        and not has_space
        and not update_result.notes
        else selection
    )
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
        if orbits:
            results.extend(
                compute_asteroid_visibility(
                    orbits,
                    window,
                    args.lat,
                    args.lon,
                    args.elevation_m,
                    field_of_view,
                    args.sample_minutes,
                    selection.limits[selection.kinds.index("asteroids")],
                )
            )
        if comet_orbits:
            results.extend(
                compute_comet_visibility(
                    comet_orbits,
                    window,
                    args.lat,
                    args.lon,
                    args.elevation_m,
                    field_of_view,
                    args.sample_minutes,
                    selection.limits[selection.kinds.index("comets")],
                )
            )
            if cbat:
                results = annotate_cbat(results, cbat, window.start_local)
        if space_elements:
            for kind in ("satellites", "debris"):
                if kind not in selection.kinds:
                    continue
                chosen, _ = select_space_elements(space_elements, space_records, (kind,), window)
                results.extend(
                    compute_satellite_visibility(
                        chosen,
                        window,
                        args.lat,
                        args.lon,
                        args.elevation_m,
                        field_of_view,
                        args.satellite_step_seconds,
                        selection.limits[selection.kinds.index(kind)],
                        args.satellite_optical_only,
                        args.satellite_max_sun_altitude,
                    )
                )
            results = annotate_space_catalog(results, space_records, registry_records)
        if orbits or comet_orbits or has_space:
            results.sort(
                key=lambda result: (
                    apparent_magnitude(result.star)
                    if apparent_magnitude(result.star) is not None
                    else float("inf"),
                    result.star.name.casefold(),
                )
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
            parser.error(f"impossible d'écrire le rapport dans {args.output_txt}: {exc}")
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
    return mode, Path(directory), ages


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # Priorité absolue au mode hors ligne avant conversions et import des sources.
    iers.conf.auto_download = not args.offline
    iers.conf.auto_max_age = None if args.offline else 30.0
    iers.conf.iers_degraded_accuracy = "warn"
    try:
        _validate_arguments(args)
        root = validate_root(args.seestar_path) if args.seestar_path is not None else None
        if root is not None:
            protect_outputs(root, (args.output_txt, args.output_pdf))
        checked_window = parse_observation_window(args.date, args.time_range, args.timezone)
        if {'satellites','debris'}.intersection(args.objects) and checked_window.duration_seconds > args.satellite_step_seconds*(MAX_SAMPLES-1):
            raise ValueError(f'Fenêtre satellitaire limitée à {MAX_SAMPLES} échantillons; augmentez le pas ou réduisez la plage')
        FieldOfView.from_automatic_center(
            azimuth_min_deg=args.az_min,
            azimuth_max_deg=args.az_max,
            minimum_altitude_deg=args.min_altitude,
            altitude_center_deg=args.alt_center,
        )
        mode, directory, ages = _update_settings(args)
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
            return _run(args, parser, result, root)
    except ValueError as exc:
        parser.error(str(exc))
