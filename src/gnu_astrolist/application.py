# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""ECC-G : orchestration du rapport, indépendante des entrées et sorties CLI."""
from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path

from astropy.time import Time
from astropy.utils import iers

from .asteroids import compute_asteroid_visibility, load_asteroid_catalog
from .catalog_resources import application_context_lock
from .comets import (
    annotate_cbat,
    compute_comet_visibility,
    eligible_orbits,
    load_cbat_observations,
    load_comet_catalog,
)
from .models import FieldOfView, apparent_magnitude
from .moon import compute_moon_summary
from .report_data import ReportData
from .satcat import annotate_space_catalog, load_satcat, load_unoosa_records, select_space_elements
from .satellites import (
    MAX_SAMPLES,
    compute_satellite_visibility,
    eligible_elements,
    load_satellite_elements,
)
from .seestar import annotate_results, scan_seestar
from .selection import load_catalog_selection, normalize_catalogs
from .time_utils import parse_observation_window
from .validation import (
    MAX_AGE_HOURS,
    finite_number,
    sampling_plan,
    sampling_step,
    validate_magnitude,
    validate_observer,
)
from .visibility import MAX_TIME_SAMPLES, compute_visibility
from .weather import compute_weather_summary


@contextmanager
def astronomical_context(offline: bool) -> Iterator[None]:
    """Restaure les trois réglages IERS, même après une exception ou une imbrication."""
    with (
        application_context_lock,
        iers.conf.set_temp('auto_download', not offline),
        iers.conf.set_temp('auto_max_age', None if offline else 30.0),
        iers.conf.set_temp('iers_degraded_accuracy', 'warn'),
    ):
        yield


@dataclass(frozen=True)
class ObservationRequest:
    """Paramètres du calcul; aucun parseur, export ou flux de terminal."""

    date: str
    time_range: str
    timezone: str
    lat: float
    lon: float
    elevation_m: float
    az_min: float
    az_max: float
    min_altitude: float
    alt_center: float | None
    objects: Sequence[str]
    max_magnitude: float | None = None
    all_magnitudes: bool = False
    sample_minutes: float = 10.0
    satellite_step_seconds: float = 5.0
    satellite_max_epoch_hours: float = 168.0
    satellite_optical_only: bool = False
    satellite_max_sun_altitude: float = -6.0
    asteroids_file: Path | None = None
    comets_file: Path | None = None
    cbat_file: Path | None = None
    satcat_file: Path | None = None
    satellite_elements_file: Path | None = None
    unoosa_file: Path | None = None
    limit: int | None = None
    offline: bool = False
    details: bool = False
    max_altitude: float | None = None

    def validate(self) -> None:
        """Vérifie la requête avant de solliciter un collaborateur."""
        validate_observer(self.lat, self.lon, self.elevation_m)
        validate_magnitude(self.max_magnitude)
        sampling_step(self.sample_minutes, '--sample-minutes', 60)
        sampling_step(self.satellite_step_seconds, '--satellite-step-seconds')
        finite_number(self.satellite_max_sun_altitude, '--satellite-max-sun-altitude', -90, 90)
        age = finite_number(self.satellite_max_epoch_hours,
                            '--satellite-max-epoch-hours', 0, MAX_AGE_HOURS)
        if age <= 0:
            raise ValueError('--satellite-max-epoch-hours doit être positif')
        if self.limit is not None and (type(self.limit) is not int or self.limit <= 0):
            raise ValueError('--limit doit être un entier supérieur à zéro')
        selected = normalize_catalogs(self.objects)
        if (self.satellite_elements_file or self.satcat_file or self.unoosa_file
                or self.satellite_optical_only) and not {'satellites', 'debris'}.intersection(selected):
            raise ValueError('Les options satellitaires exigent --objects satellites ou debris')
        if (self.comets_file or self.cbat_file) and 'comets' not in selected:
            raise ValueError('--comets-file et --cbat-file exigent --objects comets')
        if self.asteroids_file and 'asteroids' not in selected:
            raise ValueError('--asteroids-file exige --objects asteroids')
        window = parse_observation_window(self.date, self.time_range, self.timezone)
        if set(selected) - {'satellites', 'debris'}:
            sampling_plan(window, self.sample_minutes, MAX_TIME_SAMPLES, '--sample-minutes', 60)
        if {'satellites', 'debris'}.intersection(selected):
            sampling_plan(window, self.satellite_step_seconds, MAX_SAMPLES,
                          '--satellite-step-seconds')
        FieldOfView.from_automatic_center(
            azimuth_min_deg=self.az_min, azimuth_max_deg=self.az_max,
            minimum_altitude_deg=self.min_altitude, altitude_center_deg=self.alt_center,
            maximum_altitude_deg=self.max_altitude,
        )


@dataclass(frozen=True)
class ApplicationDependencies:
    """Collaborateurs remplaçables explicitement, sans modifier les modules métier."""

    load_asteroid_catalog: Callable = load_asteroid_catalog
    eligible_orbits: Callable = eligible_orbits
    load_comet_catalog: Callable = load_comet_catalog
    load_satcat: Callable = load_satcat
    load_satellite_elements: Callable = load_satellite_elements
    select_space_elements: Callable = select_space_elements
    eligible_elements: Callable = eligible_elements
    load_unoosa_records: Callable = load_unoosa_records
    load_cbat_observations: Callable = load_cbat_observations
    compute_weather_summary: Callable = compute_weather_summary
    load_catalog_selection: Callable = load_catalog_selection
    compute_moon_summary: Callable = compute_moon_summary
    compute_visibility: Callable = compute_visibility
    compute_asteroid_visibility: Callable = compute_asteroid_visibility
    compute_comet_visibility: Callable = compute_comet_visibility
    annotate_cbat: Callable = annotate_cbat
    compute_satellite_visibility: Callable = compute_satellite_visibility
    annotate_space_catalog: Callable = annotate_space_catalog
    scan_seestar: Callable = scan_seestar
    annotate_results: Callable = annotate_results


class ObservationApplication:
    """Prépare le même rapport pour tous les rendus; ne produit aucun export."""

    def __init__(self, dependencies: ApplicationDependencies | None = None):
        self.dependencies = dependencies if dependencies is not None else ApplicationDependencies()

    def prepare_report(
        self, request: ObservationRequest, *, source_notes: Sequence[str] = (),
        seestar_root: Path | None = None,
    ) -> ReportData:
        """Calcule le rapport sous contexte IERS temporaire; laisse remonter les erreurs."""
        request.validate()
        with astronomical_context(request.offline):
            return _prepare_report(request, source_notes, seestar_root, self.dependencies)


def _prepare_report(
    args: ObservationRequest, source_notes: Sequence[str], seestar_root: Path | None,
    dependencies: ApplicationDependencies,
) -> ReportData:
    orbits = dependencies.load_asteroid_catalog(args.asteroids_file) if "asteroids" in args.objects else ()
    window = parse_observation_window(args.date, args.time_range, args.timezone)
    comet_orbits, excluded = (
        dependencies.eligible_orbits(
            dependencies.load_comet_catalog(args.comets_file), Time([window.start_local, window.end_local])
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
        space_records = dependencies.load_satcat(args.satcat_file)
        all_elements = dependencies.load_satellite_elements(args.satellite_elements_file)
        chosen, skip_types = dependencies.select_space_elements(
            all_elements, space_records, args.objects, window
        )
        space_elements, old = dependencies.eligible_elements(
            chosen, Time([window.start_local, window.end_local]), args.satellite_max_epoch_hours
        )
        if chosen and not space_elements:
            raise ValueError(
                "Aucun élément GP assez récent pour cette plage; actualisez les éléments satellitaires"
            )
        registry_records = dependencies.load_unoosa_records(args.unoosa_file) if args.unoosa_file else ()
        space_notes = [
            f"GP/SATCAT : {len(all_elements)} éléments, {len(space_records)} fiches; {len(space_elements)} orbites sélectionnées, {len(old)} exclues pour âge; autres exclusions : {skip_types}.",
            f"Pas satellite : {args.satellite_step_seconds:g} s; âge maximal GP ±{args.satellite_max_epoch_hours:g} h. Copie partielle, sans garantie d’exhaustivité.",
            f"Filtre optique satellite : {'activé' if args.satellite_optical_only else 'désactivé'}; plafond Soleil {args.satellite_max_sun_altitude:g}° lorsqu’activé.",
            f"UNOOSA : {len(registry_records)} extrait(s) local(aux); aucune lecture du registre en ligne.",
        ]
    cbat = dependencies.load_cbat_observations(args.cbat_file) if args.cbat_file else ()
    field_of_view = FieldOfView.from_automatic_center(
        azimuth_min_deg=args.az_min,
        azimuth_max_deg=args.az_max,
        minimum_altitude_deg=args.min_altitude,
        altitude_center_deg=args.alt_center,
        maximum_altitude_deg=args.max_altitude,
    )
    weather_summary = dependencies.compute_weather_summary(
        window=window,
        latitude_deg=args.lat,
        longitude_deg=args.lon,
        offline=args.offline,
    )

    stars, selection = dependencies.load_catalog_selection(args.objects, args.max_magnitude, args.all_magnitudes)
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
    if source_notes:
        selection = replace(selection, source_notes=(*selection.source_notes, *source_notes))
    if has_space:
        selection = replace(selection, source_notes=(*selection.source_notes, *space_notes))
    object_kind = (
        selection.kinds[0]
        if len(selection.kinds) == 1
        and not orbits
        and not comet_orbits
        and not has_space
        and not source_notes
        else selection
    )
    max_magnitude = selection.limits[0] if len(selection.kinds) == 1 else args.max_magnitude
    moon_summary = dependencies.compute_moon_summary(
        window=window,
        latitude_deg=args.lat,
        longitude_deg=args.lon,
        elevation_m=args.elevation_m,
    )
    results = dependencies.compute_visibility(
        stars=stars,
        window=window,
        latitude_deg=args.lat,
        longitude_deg=args.lon,
        elevation_m=args.elevation_m,
        field_of_view=field_of_view,
        sample_minutes=args.sample_minutes,
    ) if stars else []
    if orbits:
        results.extend(
            dependencies.compute_asteroid_visibility(
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
            dependencies.compute_comet_visibility(
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
            results = dependencies.annotate_cbat(results, cbat, window.start_local)
    if space_elements:
        for kind in ("satellites", "debris"):
            if kind not in selection.kinds:
                continue
            chosen, _ = dependencies.select_space_elements(space_elements, space_records, (kind,), window)
            results.extend(
                dependencies.compute_satellite_visibility(
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
        results = dependencies.annotate_space_catalog(results, space_records, registry_records)
    if orbits or comet_orbits or has_space:
        results.sort(
            key=lambda result: (
                apparent_magnitude(result.star)
                if apparent_magnitude(result.star) is not None
                else float("inf"),
                result.star.name.casefold(),
            )
        )
    matched_count = len(results)
    displayed_results = results[: args.limit] if args.limit is not None else results
    inventory = dependencies.scan_seestar(seestar_root) if seestar_root is not None else None
    if inventory is not None:
        displayed_results = dependencies.annotate_results(displayed_results, inventory)
    return ReportData(
        window=window,
        latitude_deg=args.lat,
        longitude_deg=args.lon,
        elevation_m=args.elevation_m,
        field_of_view=field_of_view,
        max_magnitude=max_magnitude,
        sample_minutes=args.sample_minutes,
        weather_summary=weather_summary,
        moon_summary=moon_summary,
        results=tuple(displayed_results),
        matched_count=matched_count,
        object_kind=object_kind,
        show_details=args.details,
        seestar_inventory=inventory,
    )
