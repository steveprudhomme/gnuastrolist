# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Orbits elliptiques JPL, modèle à deux corps et éphémérides topocentriques locales."""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from astropy.coordinates import EarthLocation
from astropy.time import Time

from .catalog_resources import catalog_resource
from .models import AsteroidTarget
from .moving import MU, OBLIQUITY, compute_moving_visibility, orbit_geometry

MAX_EPOCH_DAYS = 365.0


@dataclass(frozen=True)
class AsteroidOrbit:
    number: int
    name: str
    epoch: float
    a: float
    e: float
    i: float
    node: float
    peri: float
    mean_anomaly: float
    h: float | None
    g: float | None
    orbit_id: str
    retrieved_on: str = ""


def parse_sbdb(payload: dict) -> tuple[AsteroidOrbit, ...]:
    """Lit une réponse SBDB Query 1.0, sans téléchargement ni acceptation implicite d'unités."""
    if not isinstance(payload, dict) or not isinstance(payload.get("signature"), dict):
        raise ValueError("Réponse SBDB Query invalide")
    if payload["signature"].get("version") != "1.0":
        raise ValueError("Version SBDB Query non prise en charge (1.0 requise)")
    fields = payload.get("fields", [])
    required = {
        "pdes",
        "name",
        "epoch",
        "equinox",
        "a",
        "e",
        "i",
        "om",
        "w",
        "ma",
        "H",
        "G",
        "orbit_id",
    }
    if (
        not isinstance(fields, list)
        or not all(isinstance(f, str) for f in fields)
        or len(fields) != len(set(fields))
        or not required.issubset(fields)
    ):
        raise ValueError("Champs orbitaux SBDB absents ou dupliqués")
    if not isinstance(payload.get("data"), list):
        raise ValueError("Lignes SBDB absentes")
    orbits = []
    numbers = set()
    for row in payload.get("data", []):
        if not isinstance(row, list) or len(row) != len(fields):
            raise ValueError("Ligne SBDB de longueur incorrecte")
        data = dict(zip(fields, row))
        try:
            if not str(data["pdes"]).isascii() or not str(data["pdes"]).isdecimal():
                raise ValueError("Numéro mineur invalide")
            number = int(data["pdes"])
            values = {key: float(data[key]) for key in ("epoch", "a", "e", "i", "om", "w", "ma")}
            h = None if data["H"] is None else float(data["H"])
            g = None if data["G"] is None else float(data["G"])
        except (ValueError, TypeError) as exc:
            raise ValueError("Valeur SBDB invalide; astéroïdes numérotés requis") from exc
        if (
            number < 1
            or number in numbers
            or data["equinox"] != "J2000"
            or not all(np.isfinite(x) for x in values.values())
            or not (values["a"] > 0 and 0 <= values["e"] < 1 and 0 <= values["i"] <= 180)
            or (h is not None and not np.isfinite(h))
            or (g is not None and not np.isfinite(g))
        ):
            raise ValueError(f"Orbite SBDB non prise en charge ou dupliquée : {number}")
        if data["name"] is not None and not isinstance(data["name"], str):
            raise ValueError("Nom SBDB invalide")
        numbers.add(number)
        orbits.append(
            AsteroidOrbit(
                number,
                data["name"] or "",
                values["epoch"],
                values["a"],
                values["e"],
                values["i"],
                values["om"],
                values["w"],
                values["ma"],
                h,
                g,
                str(data["orbit_id"]),
                payload.get("astrolist_retrieved_on", ""),
            )
        )
    if not orbits:
        raise ValueError("Le catalogue orbital est vide")
    return tuple(sorted(orbits, key=lambda orbit: orbit.number))


def load_asteroid_catalog(path: Path | None = None) -> tuple[AsteroidOrbit, ...]:
    if path is not None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError(f"Fichier orbital local illisible : {path}") from exc
    else:
        resource = catalog_resource("asteroids.json.gz")
        with resource.open("rb") as raw, gzip.open(raw, "rt", encoding="utf-8") as stream:
            payload = json.load(stream)
    return parse_sbdb(payload)


def heliocentric_positions(orbits: tuple[AsteroidOrbit, ...], jd: np.ndarray) -> np.ndarray:
    """Vecteurs équatoriaux J2000 en AU, forme (3, objets, instants)."""
    a = np.array([o.a for o in orbits])[:, None]
    e = np.array([o.e for o in orbits])[:, None]
    epoch = np.array([o.epoch for o in orbits])[:, None]
    mean = (
        np.deg2rad([o.mean_anomaly for o in orbits])[:, None]
        + np.sqrt(MU / a**3) * (jd - epoch)
        + np.pi
    ) % (2 * np.pi) - np.pi
    eccentric = np.where(e < 0.8, mean, np.pi * np.sign(mean))
    for _ in range(80):
        correction = (eccentric - e * np.sin(eccentric) - mean) / (1 - e * np.cos(eccentric))
        eccentric -= correction
        if np.max(np.abs(correction)) < 1e-12:
            break
    else:
        raise ValueError("La résolution de Kepler ne converge pas")
    x = a * (np.cos(eccentric) - e)
    y = a * np.sqrt(1 - e**2) * np.sin(eccentric)
    inc, node, peri = (
        np.deg2rad([getattr(o, key) for o in orbits])[:, None] for key in ("i", "node", "peri")
    )
    xx = (np.cos(node) * np.cos(peri) - np.sin(node) * np.sin(peri) * np.cos(inc)) * x
    xx += (-np.cos(node) * np.sin(peri) - np.sin(node) * np.cos(peri) * np.cos(inc)) * y
    yy = (np.sin(node) * np.cos(peri) + np.cos(node) * np.sin(peri) * np.cos(inc)) * x
    yy += (-np.sin(node) * np.sin(peri) + np.cos(node) * np.cos(peri) * np.cos(inc)) * y
    zz = np.sin(peri) * np.sin(inc) * x + np.cos(peri) * np.sin(inc) * y
    return np.array(
        [
            xx,
            yy * np.cos(OBLIQUITY) - zz * np.sin(OBLIQUITY),
            yy * np.sin(OBLIQUITY) + zz * np.cos(OBLIQUITY),
        ]
    )


def hg_magnitude(
    h: np.ndarray, g: np.ndarray, r: np.ndarray, delta: np.ndarray, phase: np.ndarray
) -> np.ndarray:
    """Estimation H-G exponentielle; phase en radians, distances en AU."""
    tangent = np.tan(np.clip(phase, 0, np.pi - 1e-12) / 2)
    flux = (1 - g) * np.exp(-3.33 * tangent**0.63) + g * np.exp(-1.87 * tangent**1.22)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(flux > 0, h + 5 * np.log10(r * delta) - 2.5 * np.log10(flux), np.nan)


def ephemerides(orbits: tuple[AsteroidOrbit, ...], times: Time, location: EarthLocation):
    """RA/Dec GCRS topocentriques, Alt/Az sans réfraction et magnitude à chaque instant."""
    if not orbits:
        raise ValueError("Au moins une orbite est requise")
    if np.any(np.abs(times.tdb.jd - np.array([o.epoch for o in orbits])[:, None]) > MAX_EPOCH_DAYS):
        raise ValueError(
            "Dates à plus de 365 jours des éléments orbitaux : actualisez le fichier SBDB"
        )
    if np.any((times.utc.jyear < 1900) | (times.utc.jyear > 2100)):
        raise ValueError("Le modèle planétaire intégré est limité à 1900–2100")
    gcrs, horizontal, radius, distance, phase = orbit_geometry(
        orbits, times, location, heliocentric_positions
    )
    h = np.array([o.h if o.h is not None else np.nan for o in orbits])[:, None]
    g = np.array([o.g if o.g is not None else 0.15 for o in orbits])[:, None]
    magnitude = hg_magnitude(h, g, radius, distance, phase)
    return gcrs, horizontal, magnitude


def _asteroid_target(orbit, ra, dec, magnitude):
    assumed = " (supposé)" if orbit.g is None else ""
    return AsteroidTarget(
        name=f"({orbit.number}) {orbit.name}".strip(),
        number=orbit.number,
        asteroid_name=orbit.name,
        epoch_jd_tdb=orbit.epoch,
        ra_deg=ra,
        dec_deg=dec,
        object_type="Asteroid",
        magnitude_v=magnitude,
        catalog_designation=f"MPC{orbit.number}",
        constellation="",
        apparent_major_arcmin=None,
        apparent_minor_arcmin=None,
        magnitude_source="JPL SBDB / H-G",
        magnitude_reference=f"Orbite {orbit.orbit_id}; H={orbit.h}; G={orbit.g if orbit.g is not None else 0.15}{assumed}",
        magnitude_retrieved_on=orbit.retrieved_on,
    )


def compute_asteroid_visibility(
    orbits,
    window,
    latitude_deg,
    longitude_deg,
    elevation_m,
    field_of_view,
    sample_minutes=10,
    max_magnitude=None,
):
    return compute_moving_visibility(
        orbits,
        window,
        latitude_deg,
        longitude_deg,
        elevation_m,
        field_of_view,
        sample_minutes,
        max_magnitude,
        calculate=ephemerides,
        make_target=_asteroid_target,
    )
