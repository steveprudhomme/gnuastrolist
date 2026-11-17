#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Construit le catalogue Messier compact à partir des fichiers OpenNGC.

Ce script n'est pas requis pour utiliser GNU Astrolist. Il documente et rend
reproductible la génération des données distribuées dans le paquet.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

NGC_SOURCE_URL = (
    "https://raw.githubusercontent.com/mattiaverga/OpenNGC/master/database_files/NGC.csv"
)
ADDENDUM_SOURCE_URL = (
    "https://raw.githubusercontent.com/mattiaverga/OpenNGC/master/database_files/addendum.csv"
)
DEFAULT_SIMBAD_CACHE = Path("src/gnu_astrolist/data/simbad_messier_cache.csv.gz")
OPENNGC_REFERENCE = "doi:10.21938/y.1ejWUD_MQ6b_eDFoVbbw"
OPENNGC_RETRIEVED_ON = "2026-08-03"
FIELDNAMES = (
    "name",
    "ra_deg",
    "dec_deg",
    "object_type",
    "magnitude_v",
    "passband",
    "catalog_designation",
    "constellation",
    "major_axis_arcmin",
    "minor_axis_arcmin",
    "size_source",
    "size_reference",
    "size_retrieved_on",
    "magnitude_source",
    "magnitude_reference",
    "magnitude_retrieved_on",
    "common_name",
)


@dataclass(frozen=True)
class ParsedMessierObject:
    number: int
    ra_deg: float
    dec_deg: float
    object_type: str
    magnitude_v: float | None
    catalog_designation: str
    constellation: str
    major_axis_arcmin: float | None
    minor_axis_arcmin: float | None
    size_source: str
    size_reference: str
    size_retrieved_on: str
    magnitude_source: str
    magnitude_reference: str
    magnitude_retrieved_on: str
    common_name: str

    def csv_row(self) -> dict[str, str]:
        return {
            "name": f"M{self.number}",
            "ra_deg": f"{self.ra_deg:.8f}",
            "dec_deg": f"{self.dec_deg:.8f}",
            "object_type": self.object_type,
            "magnitude_v": "" if self.magnitude_v is None else f"{self.magnitude_v:.3f}",
            "passband": "V",
            "catalog_designation": self.catalog_designation,
            "constellation": self.constellation,
            "major_axis_arcmin": (
                "" if self.major_axis_arcmin is None else f"{self.major_axis_arcmin:.2f}"
            ),
            "minor_axis_arcmin": (
                "" if self.minor_axis_arcmin is None else f"{self.minor_axis_arcmin:.2f}"
            ),
            "size_source": self.size_source,
            "size_reference": self.size_reference,
            "size_retrieved_on": self.size_retrieved_on,
            "magnitude_source": self.magnitude_source,
            "magnitude_reference": self.magnitude_reference,
            "magnitude_retrieved_on": self.magnitude_retrieved_on,
            "common_name": self.common_name,
        }


def _right_ascension_degrees(value: str) -> float:
    hours, minutes, seconds = (float(part) for part in value.split(":"))
    return 15.0 * (hours + minutes / 60.0 + seconds / 3600.0)


def _declination_degrees(value: str) -> float:
    sign = -1.0 if value.startswith("-") else 1.0
    degrees, minutes, seconds = (float(part) for part in value.lstrip("+-").split(":"))
    return sign * (degrees + minutes / 60.0 + seconds / 3600.0)


def _optional_float(value: str) -> float | None:
    return float(value) if value.strip() else None


def _valid_size(major: float | None, minor: float | None) -> bool:
    return (
        major is not None
        and minor is not None
        and major > 0.0
        and minor > 0.0
        and major >= minor
    )


def _read_simbad_cache(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None or not path.exists():
        return {}
    with path.open("rb") as raw, gzip.open(
        raw, mode="rt", encoding="utf-8", newline=""
    ) as stream:
        return {row["name"]: row for row in csv.DictReader(stream)}


def _parse_row(
    row: dict[str, str],
    number: int,
    simbad: dict[str, str] | None,
) -> ParsedMessierObject:
    openngc_major = _optional_float(row["MajAx"])
    openngc_minor = _optional_float(row["MinAx"])
    simbad_major = _optional_float(simbad["major_axis_arcmin"]) if simbad else None
    simbad_minor = _optional_float(simbad["minor_axis_arcmin"]) if simbad else None
    if _valid_size(simbad_major, simbad_minor):
        major_axis = simbad_major
        minor_axis = simbad_minor
        size_source = "SIMBAD"
        size_reference = simbad["size_bibcode"] or "SIMBAD TAP"
        size_retrieved_on = simbad["retrieved_on"]
    else:
        major_axis = openngc_major
        minor_axis = openngc_minor
        size_source = "OpenNGC" if major_axis is not None else ""
        size_reference = OPENNGC_REFERENCE if major_axis is not None else ""
        size_retrieved_on = OPENNGC_RETRIEVED_ON if major_axis is not None else ""

    simbad_magnitude = _optional_float(simbad["magnitude_v"]) if simbad else None
    if simbad_magnitude is not None:
        magnitude_v = simbad_magnitude
        magnitude_source = "SIMBAD"
        magnitude_reference = simbad["magnitude_bibcode"] or "SIMBAD TAP"
        magnitude_retrieved_on = simbad["retrieved_on"]
    else:
        magnitude_v = _optional_float(row["V-Mag"])
        magnitude_source = "OpenNGC"
        magnitude_reference = OPENNGC_REFERENCE
        magnitude_retrieved_on = OPENNGC_RETRIEVED_ON

    return ParsedMessierObject(
        number=number,
        ra_deg=_right_ascension_degrees(row["RA"]),
        dec_deg=_declination_degrees(row["Dec"]),
        object_type=row["Type"],
        magnitude_v=magnitude_v,
        catalog_designation=row["Name"],
        constellation={"Se1": "Ser", "Se2": "Ser"}.get(row["Const"], row["Const"]),
        major_axis_arcmin=major_axis,
        minor_axis_arcmin=minor_axis,
        size_source=size_source,
        size_reference=size_reference,
        size_retrieved_on=size_retrieved_on,
        magnitude_source=magnitude_source,
        magnitude_reference=magnitude_reference,
        magnitude_retrieved_on=magnitude_retrieved_on,
        common_name=row["Common names"].replace(",", "; "),
    )


def obtain_source(source: str) -> bytes:
    path = Path(source)
    if path.exists():
        return path.read_bytes()
    request = urllib.request.Request(
        source,
        headers={"User-Agent": "gnu-astrolist-messier-builder/0.5"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _read_rows(content: bytes) -> list[dict[str, str]]:
    text = io.StringIO(content.decode("utf-8"), newline="")
    return list(csv.DictReader(text, delimiter=";"))


def build(
    ngc_source: str,
    addendum_source: str,
    output: Path,
    simbad_cache: Path | None = DEFAULT_SIMBAD_CACHE,
) -> tuple[int, str, str, int, int]:
    ngc_content = obtain_source(ngc_source)
    addendum_content = obtain_source(addendum_source)
    rows = _read_rows(ngc_content) + _read_rows(addendum_content)
    simbad_objects = _read_simbad_cache(simbad_cache)

    objects: dict[int, ParsedMessierObject] = {}
    for row in rows:
        messier_number = row["M"].strip()
        if not messier_number:
            continue
        number = int(messier_number)
        # OpenNGC marque M102 comme doublon de M101. Cette ligne ne possède
        # d'ailleurs pas de magnitude V et ne doit pas remplacer M101.
        if row["Type"] == "Dup":
            continue
        if number in objects:
            raise ValueError(f"numéro Messier dupliqué dans les sources : M{number}")
        objects[number] = _parse_row(row, number, simbad_objects.get(f"M{number}"))

    # L'identification historique de M102 est incertaine. GNU Astrolist adopte
    # la convention fréquemment utilisée M102 = NGC 5866 afin de fournir les
    # 110 numéros de la liste Messier moderne.
    ngc_5866 = next(row for row in rows if row["Name"] == "NGC5866")
    objects[102] = _parse_row(ngc_5866, 102, simbad_objects.get("M102"))

    expected_numbers = set(range(1, 111))
    if set(objects) != expected_numbers:
        missing = sorted(expected_numbers - set(objects))
        unexpected = sorted(set(objects) - expected_numbers)
        raise ValueError(f"liste Messier incomplète; absents={missing}, inattendus={unexpected}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with (
        output.open("wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as archive,
        io.TextIOWrapper(archive, encoding="utf-8", newline="") as text,
    ):
        writer = csv.DictWriter(text, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(objects[number].csv_row() for number in sorted(objects))

    return (
        len(objects),
        hashlib.sha256(ngc_content).hexdigest(),
        hashlib.sha256(addendum_content).hexdigest(),
        sum(obj.size_source == "SIMBAD" for obj in objects.values()),
        sum(obj.magnitude_source == "SIMBAD" for obj in objects.values()),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ngc-source", default=NGC_SOURCE_URL, help="URL ou fichier NGC.csv")
    parser.add_argument(
        "--addendum-source",
        default=ADDENDUM_SOURCE_URL,
        help="URL ou fichier addendum.csv",
    )
    parser.add_argument(
        "--simbad-cache",
        type=Path,
        default=DEFAULT_SIMBAD_CACHE,
        help="cache SIMBAD local .csv.gz; OpenNGC est utilisé s'il est absent",
    )
    parser.add_argument("--output", type=Path, required=True, help="destination .csv.gz")
    args = parser.parse_args()
    count, ngc_digest, addendum_digest, simbad_sizes, simbad_magnitudes = build(
        args.ngc_source, args.addendum_source, args.output, args.simbad_cache
    )
    print(f"{count} objets écrits dans {args.output}")
    print(f"SHA-256 de NGC.csv : {ngc_digest}")
    print(f"SHA-256 de addendum.csv : {addendum_digest}")
    print(f"Dimensions choisies depuis SIMBAD : {simbad_sizes}")
    print(f"Magnitudes V choisies depuis SIMBAD : {simbad_magnitudes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
