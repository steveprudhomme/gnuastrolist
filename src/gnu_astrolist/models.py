"""Modèles de données indépendants de l'interface en ligne de commande."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

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
class FieldOfView:
    """Champ rectangulaire en coordonnées horizontales Alt/Az.

    L'azimut est mesuré depuis le nord vers l'est. Le calcul de la largeur
    horizontale tient compte du passage par 0/360 degrés.
    """

    azimuth_center_deg: float
    altitude_center_deg: float
    horizontal_deg: float
    vertical_deg: float

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

    star: VariableStar
    altitude_start_deg: float
    altitude_end_deg: float
    azimuth_start_deg: float
    azimuth_end_deg: float
