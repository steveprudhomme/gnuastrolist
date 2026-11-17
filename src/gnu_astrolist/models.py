"""Modèles de données indépendants de l'interface en ligne de commande."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import TypeAlias

import numpy as np
from numpy.typing import ArrayLike, NDArray


@dataclass(frozen=True, slots=True)
class VariableStar:
    """Une étoile variable issue du catalogue embarqué."""

    name: str
    ra_deg: float
    dec_deg: float
    variable_type: str
    mag_max: float
    mag_min: float | None
    passband: str
    mag_max_limit: str = ""
    constellation: str = ""
    apparent_major_arcmin: float | None = None
    apparent_minor_arcmin: float | None = None
    size_source: str = ""
    size_reference: str = ""
    size_retrieved_on: str = ""
    magnitude_source: str = "GCVS"
    magnitude_reference: str = "2017ARep...61...80S"
    magnitude_retrieved_on: str = "2026-07-17"

    @property
    def object_type(self) -> str:
        return self.variable_type

    @property
    def magnitude_v(self) -> float:
        return self.mag_max

    @property
    def magnitude_limit(self) -> str:
        return self.mag_max_limit


@dataclass(frozen=True, slots=True)
class DeepSkyObject:
    """Un objet du ciel profond issu d'un catalogue embarqué."""

    name: str
    ra_deg: float
    dec_deg: float
    object_type: str
    magnitude_v: float | None
    catalog_designation: str
    constellation: str
    apparent_major_arcmin: float | None
    apparent_minor_arcmin: float | None
    size_source: str = ""
    size_reference: str = ""
    size_retrieved_on: str = ""
    magnitude_source: str = ""
    magnitude_reference: str = ""
    magnitude_retrieved_on: str = ""
    common_name: str = ""
    passband: str = "V"
    aliases: tuple[str, ...] = ()

    @property
    def magnitude_limit(self) -> str:
        return ""


MessierObject = DeepSkyObject  # Compatibilité avec les utilisateurs du modèle initial.
CaldwellObject = DeepSkyObject


@dataclass(frozen=True, slots=True)
class NamedStar:
    """Étoile HYG nommée en Bayer ou Flamsteed; identité liée à la révision HYG."""

    name: str
    ra_deg: float
    dec_deg: float
    magnitude_v: float | None
    hyg_id: int
    constellation: str
    bayer_name: str = ''
    flamsteed_name: str = ''
    common_name: str = ''
    ambiguous_names: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    object_type: str = 'Star'
    passband: str = 'V'
    magnitude_limit: str = ''
    magnitude_source: str = 'HYG 4.1'
    magnitude_reference: str = 'HYG 4.1 / mag'
    magnitude_retrieved_on: str = '2026-11-17'
    apparent_major_arcmin: float | None = None
    apparent_minor_arcmin: float | None = None
    size_source: str = ''
    size_reference: str = ''
    size_retrieved_on: str = ''


@dataclass(frozen=True, slots=True)
class AsteroidTarget(DeepSkyObject):
    """Fiche d'affichage issue d'une éphéméride, jamais une position fixe à propager."""

    number: int = 0
    asteroid_name: str = ''
    epoch_jd_tdb: float = 0.0


@dataclass(frozen=True, slots=True)
class CometTarget(DeepSkyObject):
    """Fiche cométaire calculée, magnitude totale distincte de V."""

    designation: str = ''
    magnitude_total: float | None = None


@dataclass(frozen=True, slots=True)
class SatelliteTarget(DeepSkyObject):
    """Objet artificiel calculé avec SGP4; aucune magnitude optique inventée."""

    norad_id: int = 0
    cospar_id: str = ''
    epoch_jd_utc: float = 0.0


CatalogObject: TypeAlias = VariableStar | DeepSkyObject | NamedStar | AsteroidTarget | CometTarget | SatelliteTarget


def apparent_magnitude(obj: CatalogObject) -> float | None:
    """Valeur à afficher/trier, sans placer une magnitude totale dans le champ V."""
    return obj.magnitude_total if isinstance(obj, CometTarget) else obj.magnitude_v


@dataclass(frozen=True, slots=True)
class ObservationWindow:
    """Plage d'observation exprimée dans le fuseau civil choisi."""

    start_local: datetime
    end_local: datetime
    timezone_name: str

    @property
    def duration_seconds(self) -> float:
        start_utc = self.start_local.astimezone(timezone.utc)
        end_utc = self.end_local.astimezone(timezone.utc)
        return (end_utc - start_utc).total_seconds()


@dataclass(frozen=True, slots=True)
class MoonSummary:
    """État de la Lune et passages à l'horizon pour la date locale."""

    phase_name: str
    illumination_percent: float
    daily_illumination_percent: float
    daily_illumination_reference_local: datetime
    moonrise_local: datetime | None
    moonset_local: datetime | None
    always_above_horizon: bool = False
    always_below_horizon: bool = False


@dataclass(frozen=True, slots=True)
class WeatherPeriodSummary:
    """Conditions moyennes prévues pendant une période de la nuit."""

    name: str
    start_local: datetime
    end_local: datetime
    cloud_cover_percent: float | None = None
    seeing_quality_percent: float | None = None
    seeing_description: str = ""
    transparency_quality_percent: float | None = None
    transparency_description: str = ""
    stability_quality_percent: float | None = None
    temperature_c: float | None = None
    humidity_percent: float | None = None
    wind_kmh: float | None = None
    dew_risk: str = ""
    precipitation_probability_percent: float | None = None


@dataclass(frozen=True, slots=True)
class WeatherSummary:
    """Prévisions de soirée et d'avant l'aube, avec état des sources."""

    evening: WeatherPeriodSummary
    predawn: WeatherPeriodSummary
    sources: str = ""
    warnings: tuple[str, ...] = ()
    offline: bool = False

    @property
    def available(self) -> bool:
        fields = (
            "cloud_cover_percent", "seeing_quality_percent", "transparency_quality_percent",
            "stability_quality_percent", "temperature_c", "humidity_percent", "wind_kmh",
            "precipitation_probability_percent",
        )
        return any(getattr(period, field) is not None
                   for period in (self.evening, self.predawn) for field in fields) or any(
                       period.dew_risk for period in (self.evening, self.predawn))


@dataclass(frozen=True, slots=True)
class FieldOfView:
    """Champ rectangulaire en coordonnées horizontales Alt/Az.

    L'azimut est mesuré depuis le nord vers l'est. Le calcul de la largeur
    horizontale tient compte du passage par 0/360 degrés.
    """

    azimuth_center_deg: float
    altitude_center_deg: float
    horizontal_deg: float
    vertical_deg: float

    @classmethod
    def from_automatic_center(
        cls,
        *,
        azimuth_min_deg: float,
        azimuth_max_deg: float,
        minimum_altitude_deg: float,
        altitude_center_deg: float | None = None,
    ) -> FieldOfView:
        """Construit un champ centré automatiquement, sauf remplacement explicite.

        Le champ horizontal suit le sens nord vers est entre les deux limites.
        Le champ vertical s'étend de l'élévation minimale choisie jusqu'à 90°.
        """

        if not 0.0 <= azimuth_min_deg <= 360.0:
            raise ValueError("l'azimut minimal doit être compris entre 0 et 360 degrés")
        if not 0.0 <= azimuth_max_deg <= 360.0:
            raise ValueError("l'azimut maximal doit être compris entre 0 et 360 degrés")
        if not 0.0 <= minimum_altitude_deg <= 90.0:
            raise ValueError("l'élévation minimale doit être comprise entre 0 et 90 degrés")

        normalized_minimum = azimuth_min_deg % 360.0
        normalized_maximum = azimuth_max_deg % 360.0
        raw_span = azimuth_max_deg - azimuth_min_deg
        horizontal_deg = (
            360.0
            if abs(raw_span) == 360.0
            else (normalized_maximum - normalized_minimum) % 360.0
        )
        automatic_azimuth_center = (
            normalized_minimum + horizontal_deg / 2.0
        ) % 360.0
        automatic_altitude_center = (minimum_altitude_deg + 90.0) / 2.0
        return cls(
            azimuth_center_deg=automatic_azimuth_center,
            altitude_center_deg=(
                automatic_altitude_center
                if altitude_center_deg is None
                else altitude_center_deg
            ),
            horizontal_deg=horizontal_deg,
            vertical_deg=90.0 - minimum_altitude_deg,
        )

    @property
    def azimuth_start_deg(self) -> float:
        return (self.azimuth_center_deg - self.horizontal_deg / 2.0) % 360.0

    @property
    def azimuth_end_deg(self) -> float:
        if self.horizontal_deg == 360.0:
            return 360.0
        return (self.azimuth_center_deg + self.horizontal_deg / 2.0) % 360.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.azimuth_center_deg < 360.0:
            raise ValueError(
                "le centre azimutal doit être compris entre 0 (inclus) et 360 (exclus)"
            )
        if not 0.0 <= self.altitude_center_deg <= 90.0:
            raise ValueError("le centre vertical doit être compris entre 0 et 90 degrés")
        if not 0.0 <= self.horizontal_deg <= 360.0:
            raise ValueError("le champ horizontal doit être compris entre 0 et 360 degrés")
        if not 0.0 <= self.vertical_deg <= 90.0:
            raise ValueError("le champ vertical doit être compris entre 0 et 90 degrés")

    @property
    def altitude_lower_deg(self) -> float:
        return max(0.0, self.altitude_center_deg - self.vertical_deg / 2.0)

    @property
    def altitude_upper_deg(self) -> float:
        return min(90.0, self.altitude_center_deg + self.vertical_deg / 2.0)

    def contains(self, azimuth_deg: ArrayLike, altitude_deg: ArrayLike) -> NDArray[np.bool_]:
        """Retourne un masque indiquant les positions comprises dans le champ."""

        azimuth = np.asarray(azimuth_deg, dtype=float)
        altitude = np.asarray(altitude_deg, dtype=float)
        if self.horizontal_deg == 360.0:
            inside_azimuth = np.ones(np.broadcast_shapes(azimuth.shape, altitude.shape), dtype=bool)
        else:
            angular_distance = np.abs(
                (azimuth - self.azimuth_center_deg + 180.0) % 360.0 - 180.0
            )
            inside_azimuth = angular_distance <= self.horizontal_deg / 2.0 + 1e-12

        inside_altitude = (
            (altitude >= self.altitude_lower_deg - 1e-12)
            & (altitude <= self.altitude_upper_deg + 1e-12)
        )
        return np.asarray(inside_azimuth & inside_altitude, dtype=bool)


@dataclass(frozen=True, slots=True)
class VisibilityResult:
    """Position d'un objet au début et à la fin de la plage."""

    star: CatalogObject
    altitude_start_deg: float
    altitude_end_deg: float
    azimuth_start_deg: float
    azimuth_end_deg: float
    constellation: str = ""
    maximum_solar_separation_date: date | None = None
    best_seasonal_visibility_date: date | None = None
    # Réservé aux futurs corps du Système solaire pour lesquels l'opposition
    # est physiquement applicable. Les objets du ciel profond laissent ce champ vide.
    opposition_date: date | None = None
    rises_above_minimum_local: datetime | None = None
    sets_below_minimum_local: datetime | None = None
    always_above_minimum: bool = False
    seestar_status: str | None = None
    magnitude_estimated: bool = False
    magnitude_reference_time: datetime | None = None
    comet_observation: str | None = None
    position_reference_time: datetime | None = None
    satellite_details: str | None = None
    space_catalog_details: str | None = None
