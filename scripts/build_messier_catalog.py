#!/usr/bin/env python3
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
FIELDNAMES = (
    "name",
    "ra_deg",
    "dec_deg",
    "object_type",
    "magnitude_v",
    "passband",
    "catalog_designation",
    "common_name",
)


@dataclass(frozen=True)
class ParsedMessierObject:
    number: int
    ra_deg: float
    dec_deg: float
    object_type: str
    magnitude_v: float
    catalog_designation: str
    common_name: str

    def csv_row(self) -> dict[str, str]:
        return {
            "name": f"M{self.number}",
            "ra_deg": f"{self.ra_deg:.8f}",
            "dec_deg": f"{self.dec_deg:.8f}",
            "object_type": self.object_type,
            "magnitude_v": f"{self.magnitude_v:.3f}",
            "passband": "V",
            "catalog_designation": self.catalog_designation,
            "common_name": self.common_name,
        }


def _right_ascension_degrees(value: str) -> float:
    hours, minutes, seconds = (float(part) for part in value.split(":"))
    return 15.0 * (hours + minutes / 60.0 + seconds / 3600.0)


def _declination_degrees(value: str) -> float:
    sign = -1.0 if value.startswith("-") else 1.0
    degrees, minutes, seconds = (float(part) for part in value.lstrip("+-").split(":"))
    return sign * (degrees + minutes / 60.0 + seconds / 3600.0)


def _parse_row(row: dict[str, str], number: int) -> ParsedMessierObject:
    return ParsedMessierObject(
        number=number,
        ra_deg=_right_ascension_degrees(row["RA"]),
        dec_deg=_declination_degrees(row["Dec"]),
        object_type=row["Type"],
        magnitude_v=float(row["V-Mag"]),
        catalog_designation=row["Name"],
        common_name=row["Common names"].replace(",", "; "),
    )


def obtain_source(source: str) -> bytes:
    path = Path(source)
    if path.exists():
        return path.read_bytes()
    request = urllib.request.Request(
        source,
        headers={"User-Agent": "gnu-astrolist-messier-builder/0.3"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _read_rows(content: bytes) -> list[dict[str, str]]:
    text = io.StringIO(content.decode("utf-8"), newline="")
    return list(csv.DictReader(text, delimiter=";"))


def build(ngc_source: str, addendum_source: str, output: Path) -> tuple[int, str, str]:
    ngc_content = obtain_source(ngc_source)
    addendum_content = obtain_source(addendum_source)
    rows = _read_rows(ngc_content) + _read_rows(addendum_content)

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
        objects[number] = _parse_row(row, number)

    # L'identification historique de M102 est incertaine. GNU Astrolist adopte
    # la convention fréquemment utilisée M102 = NGC 5866 afin de fournir les
    # 110 numéros de la liste Messier moderne.
    ngc_5866 = next(row for row in rows if row["Name"] == "NGC5866")
    objects[102] = _parse_row(ngc_5866, 102)

    expected_numbers = set(range(1, 111))
    if set(objects) != expected_numbers:
        missing = sorted(expected_numbers - set(objects))
        unexpected = sorted(set(objects) - expected_numbers)
        raise ValueError(f"liste Messier incomplète; absents={missing}, inattendus={unexpected}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as archive:
            with io.TextIOWrapper(archive, encoding="utf-8", newline="") as text:
                writer = csv.DictWriter(text, fieldnames=FIELDNAMES, lineterminator="\n")
                writer.writeheader()
                writer.writerows(objects[number].csv_row() for number in sorted(objects))

    return (
        len(objects),
        hashlib.sha256(ngc_content).hexdigest(),
        hashlib.sha256(addendum_content).hexdigest(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ngc-source", default=NGC_SOURCE_URL, help="URL ou fichier NGC.csv")
    parser.add_argument(
        "--addendum-source",
        default=ADDENDUM_SOURCE_URL,
        help="URL ou fichier addendum.csv",
    )
    parser.add_argument("--output", type=Path, required=True, help="destination .csv.gz")
    args = parser.parse_args()
    count, ngc_digest, addendum_digest = build(
        args.ngc_source, args.addendum_source, args.output
    )
    print(f"{count} objets écrits dans {args.output}")
    print(f"SHA-256 de NGC.csv : {ngc_digest}")
    print(f"SHA-256 de addendum.csv : {addendum_digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
