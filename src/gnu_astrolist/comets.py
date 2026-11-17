# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Comètes MPC et observations CBAT locales, sans téléchargement implicite."""

from __future__ import annotations

import csv
import gzip
import math
import re
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from astropy.time import Time

from .catalog_resources import catalog_resource, catalog_retrieved_on
from .models import CometTarget
from .moving import MU, OBLIQUITY, compute_moving_visibility, orbit_geometry


def normalize_comet_name(name: str) -> str | None:
    value = name.strip().upper().replace("_", " ")
    periodic = re.fullmatch(r"0*(\d+)([PDI])(-[A-Z0-9]+)?(?:/[^/]+)?", value)
    if periodic and int(periodic[1]) > 0:
        return f"{int(periodic[1])}{periodic[2]}{periodic[3] or ''}"
    provisional = re.fullmatch(
        r"([CPDIXA])\s*/?\s*(\d{4})\s*([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)?)(?:\s+\([^()]+\))?", value
    )
    if provisional:
        return f"{provisional[1]}/{provisional[2]} {provisional[3]}"
    return None


@dataclass(frozen=True)
class CometOrbit:
    designation: str
    name: str
    perihelion_tdb: float
    q: float
    e: float
    peri: float
    node: float
    i: float
    epoch_tt: float | None
    h: float | None
    k: float | None
    reference: str
    retrieved_on: str = ''


def _date_tt(year, month, day):
    number = float(day)
    base = datetime(int(year), int(month), math.floor(number))
    instant = base + timedelta(days=number - math.floor(number))
    return Time(instant, scale="tt")


def parse_mpc(text: str) -> tuple[CometOrbit, ...]:
    """Format MPC Ephemerides and Orbital Elements, colonnes fixes officielles."""
    result, seen = [], set()
    for line_number, row in enumerate(text.splitlines(), 1):
        if not row.strip() or row.startswith("#"):
            continue
        try:
            if len(row) < 158 or row[4] not in "PCDIA":
                raise ValueError("format non reconnu")
            full_name = row[102:158].strip()
            designation = normalize_comet_name(full_name)
            if designation is None or designation in seen:
                raise ValueError("désignation absente ou dupliquée")
            seen.add(designation)
            q, e, peri, node, inc = (
                float(row[a:b]) for a, b in ((30, 39), (41, 49), (51, 59), (61, 69), (71, 79))
            )
            h = float(row[91:95]) if row[91:95].strip() else None
            k = float(row[96:100]) if row[96:100].strip() else None
            if (
                not all(math.isfinite(v) for v in (q, e, peri, node, inc))
                or q <= 0
                or e < 0
                or not 0 <= inc <= 180
            ):
                raise ValueError("éléments invalides")
            if any(v is not None and not math.isfinite(v) for v in (h, k)):
                raise ValueError("paramètre photométrique invalide")
            tp = _date_tt(row[14:18], row[19:21], row[22:29])
            epoch = _date_tt(row[81:85], row[85:87], row[87:89]).jd if row[81:89].strip() else None
            # A/ désigne un objet astéroïdal, pas une comète active.
            if row[4] == "A":
                continue
            result.append(
                CometOrbit(
                    designation,
                    full_name,
                    tp.tdb.jd,
                    q,
                    e,
                    peri,
                    node,
                    inc,
                    epoch,
                    h,
                    k,
                    row[159:].strip(),
                )
            )
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError(f"Ligne MPC {line_number} invalide : {exc}") from exc
    if not result:
        raise ValueError("Catalogue MPC cométaire vide")
    return tuple(result)


def load_comet_catalog(path: Path | None = None) -> tuple[CometOrbit, ...]:
    try:
        if path is None:
            resource = catalog_resource("comets.txt.gz")
            with resource.open("rb") as raw:
                content = gzip.decompress(raw.read()).decode("ascii")
        elif path.suffix == ".gz":
            content = gzip.decompress(path.read_bytes()).decode("ascii")
        else:
            content = path.read_text(encoding="ascii")
        date = catalog_retrieved_on('comets.txt.gz','2026-11-17') if path is None else ''
        return tuple(replace(orbit,retrieved_on=date) for orbit in parse_mpc(content))
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"Fichier MPC local illisible : {path}") from exc


def eligible_orbits(orbits, times):
    """Exclusions explicites, y compris les fragments sans époque, sans âge inventé."""
    usable = tuple(
        o
        for o in orbits
        if o.epoch_tt is not None and np.all(np.abs(times.tt.jd - o.epoch_tt) <= 365)
    )
    return usable, len(orbits) - len(usable)


def stumpff(z):
    z = np.asarray(z, dtype=float)
    c, s = np.empty_like(z), np.empty_like(z)
    small, positive, negative = abs(z) < 1e-4, z >= 1e-4, z <= -1e-4
    x = z[small]
    c[small] = 0.5 - x / 24 + x * x / 720 - x**3 / 40320 + x**4 / 3628800
    s[small] = 1 / 6 - x / 120 + x * x / 5040 - x**3 / 362880 + x**4 / 39916800
    x = np.sqrt(z[positive])
    c[positive] = 2 * np.sin(x / 2) ** 2 / z[positive]
    s[positive] = (x - np.sin(x)) / x**3
    x = np.sqrt(-z[negative])
    with np.errstate(over="ignore", invalid="ignore"):
        c[negative] = 2 * np.sinh(x / 2) ** 2 / (-z[negative])
        s[negative] = (np.sinh(x) - x) / x**3
    return c, s


def heliocentric_positions(orbits, jd):
    """Variables universelles au périhélie : ellipse, parabole, hyperbole."""
    q = np.array([o.q for o in orbits])[:, None]
    e = np.array([o.e for o in orbits])[:, None]
    dt = np.asarray(jd) - np.array([o.perihelion_tdb for o in orbits])[:, None]
    alpha = (1 - e) / q
    rhs = np.sqrt(MU) * np.abs(dt)
    lower, upper = np.zeros_like(dt), np.broadcast_to(np.sqrt(q), dt.shape).copy()

    def equation(chi):
        _, s = stumpff(alpha * chi**2)
        return q * chi + e * chi**3 * s

    for _ in range(64):
        extend = equation(upper) < rhs
        if not extend.any():
            break
        upper = np.where(extend, upper * 2, upper)
    else:
        raise ValueError("Encadrement orbital cométaire impossible")
    for _ in range(100):
        chi = (lower + upper) / 2
        below = equation(chi) < rhs
        lower, upper = np.where(below, chi, lower), np.where(below, upper, chi)
        if np.max(upper - lower) < 1e-12:
            break
    else:
        raise ValueError("Résolution orbitale cométaire non convergente")
    chi = (lower + upper) / 2 * np.sign(dt)
    c, s = stumpff(alpha * chi**2)
    x = q - chi**2 * c
    y = np.sqrt((1 + e) / q) * (q * chi + (e - 1) * chi**3 * s)
    inc, node, peri = (
        np.deg2rad([getattr(o, key) for o in orbits])[:, None] for key in ("i", "node", "peri")
    )
    xx = (np.cos(node) * np.cos(peri) - np.sin(node) * np.sin(peri) * np.cos(inc)) * x
    xx += (-np.cos(node) * np.sin(peri) - np.sin(node) * np.cos(peri) * np.cos(inc)) * y
    yy = (np.sin(node) * np.cos(peri) + np.cos(node) * np.sin(peri) * np.cos(inc)) * x
    yy += (-np.sin(node) * np.sin(peri) + np.cos(node) * np.cos(peri) * np.cos(inc)) * y
    zz = np.sin(peri) * np.sin(inc) * x + np.cos(peri) * np.sin(inc) * y
    positions = np.array(
        [
            xx,
            yy * np.cos(OBLIQUITY) - zz * np.sin(OBLIQUITY),
            yy * np.sin(OBLIQUITY) + zz * np.cos(OBLIQUITY),
        ]
    )
    if not np.isfinite(positions).all():
        raise ValueError("Position cométaire non finie")
    return positions


def ephemerides(orbits, times, location):
    valid, excluded = eligible_orbits(orbits, times)
    if excluded or not valid:
        raise ValueError("Époque MPC absente ou à plus de 365 jours : actualisez les éléments")
    gcrs, horizontal, r, delta, _ = orbit_geometry(orbits, times, location, heliocentric_positions)
    h = np.array([o.h if o.h is not None else np.nan for o in orbits])[:, None]
    k = np.array([o.k if o.k is not None else np.nan for o in orbits])[:, None]
    # Le paramètre k du fichier MPC est l'exposant : facteur 2,5 requis.
    mag = h + 5 * np.log10(delta) + 2.5 * k * np.log10(r)
    return gcrs, horizontal, mag


def _comet_target(orbit, ra, dec, magnitude):
    return CometTarget(
        name=orbit.name,
        designation=orbit.designation,
        ra_deg=ra,
        dec_deg=dec,
        object_type="Comet",
        magnitude_v=None,
        magnitude_total=magnitude,
        passband="total",
        catalog_designation=orbit.designation,
        constellation="",
        apparent_major_arcmin=None,
        apparent_minor_arcmin=None,
        magnitude_source="MPC / H,k (totale)",
        magnitude_reference=f"{orbit.reference}; H={orbit.h}; k={orbit.k}",
        magnitude_retrieved_on=orbit.retrieved_on,
    )


def compute_comet_visibility(
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
        make_target=_comet_target,
    )


@dataclass(frozen=True)
class CometObservation:
    designation: str
    observed_at: datetime
    magnitude: float
    band: str
    observer: str
    reference: str
    url: str


def load_cbat_observations(path: Path):
    """Import d'extraits autorisés transcrits dans un CSV documenté, pas de scraping CBET."""
    required = {"designation", "observed_at", "magnitude", "band", "observer", "reference", "url"}
    observations = []
    seen = set()
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if set(reader.fieldnames or ()) != required:
                raise ValueError("Colonnes CSV CBAT incorrectes")
            for row in reader:
                designation = normalize_comet_name(row["designation"])
                instant = datetime.fromisoformat(row["observed_at"].replace("Z", "+00:00"))
                magnitude = float(row["magnitude"])
                if (
                    not designation
                    or instant.tzinfo is None
                    or not math.isfinite(magnitude)
                    or any(not row[k].strip() for k in ("band", "observer", "reference", "url"))
                ):
                    raise ValueError("Observation CBAT incomplète")
                if not re.match(
                    r"https?://(?:www\.)?(?:cbat|icq|tamkin3)\.eps\.harvard\.edu/", row["url"]
                ):
                    raise ValueError("URL de provenance CBAT/ICQ requise")
                identity = (designation, instant, row["observer"], row["band"], row["reference"])
                if identity in seen:
                    raise ValueError("Observation CBAT dupliquée")
                seen.add(identity)
                observations.append(
                    CometObservation(
                        designation,
                        instant,
                        magnitude,
                        row["band"],
                        row["observer"],
                        row["reference"],
                        row["url"],
                    )
                )
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ValueError(f"CSV CBAT local invalide : {exc}") from exc
    if not observations:
        raise ValueError("CSV CBAT vide")
    return tuple(observations)


def annotate_cbat(results, observations, reference_time):
    latest = {}
    for observation in observations:
        if observation.observed_at > reference_time:
            continue
        previous = latest.get(observation.designation)
        if previous is None or observation.observed_at > previous.observed_at:
            latest[observation.designation] = observation
    annotated = []
    for result in results:
        observation = latest.get(getattr(result.star, "designation", ""))
        label = None
        if observation:
            label = (
                f"{observation.magnitude:g} [{observation.band}], "
                f"{observation.observed_at.astimezone(timezone.utc):%Y-%m-%d %H:%M} UTC; "
                f"{observation.observer}; {observation.reference}; {observation.url}"
            )
        annotated.append(replace(result, comet_observation=label))
    return annotated
