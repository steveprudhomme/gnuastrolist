#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Construit le catalogue compact à partir du fichier fixe GCVS de VizieR.

Ce script n'est pas requis pour utiliser GNU Astrolist. Il documente et rend
reproductible la génération des données distribuées dans le paquet.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

SOURCE_URL = "https://cdsarc.cds.unistra.fr/ftp/B/gcvs/gcvs_cat.dat.gz"
FIELDNAMES = (
    "name",
    "ra_deg",
    "dec_deg",
    "variable_type",
    "mag_max",
    "mag_max_limit",
    "mag_min",
    "passband",
)
COORDINATE_RE = re.compile(
    r"^\s*(?P<rah>\d{2})(?P<ram>\d{2})(?P<ras>\d{2}(?:\.\d+)?)\s+"
    r"(?P<sign>[+-])(?P<ded>\d{2})(?P<dem>\d{2})(?P<des>\d{2}(?:\.\d+)?)"
)
MAGNITUDE_RE = re.compile(r"^\s*(?P<limit>[<>()]?)\s*(?P<value>[+-]?\d+(?:\.\d+)?)")


@dataclass(frozen=True)
class ParsedStar:
    name: str
    ra_deg: float
    dec_deg: float
    variable_type: str
    mag_max: float
    mag_max_limit: str
    mag_min: float | None
    passband: str

    def csv_row(self) -> dict[str, str]:
        return {
            "name": self.name,
            "ra_deg": f"{self.ra_deg:.8f}",
            "dec_deg": f"{self.dec_deg:.8f}",
            "variable_type": self.variable_type,
            "mag_max": f"{self.mag_max:.3f}",
            "mag_max_limit": self.mag_max_limit,
            "mag_min": "" if self.mag_min is None else f"{self.mag_min:.3f}",
            "passband": self.passband,
        }


def _float(field: str) -> float | None:
    try:
        return float(field.strip())
    except ValueError:
        return None


def parse_gcvs_line(line: str) -> ParsedStar | None:
    """Analyse les colonnes décrites dans le ReadMe de VizieR B/gcvs."""

    if "|" in line:
        return _parse_pipe_line(line)
    if len(line) < 180:
        return None
    passband = line[88:90].strip()
    exists = line[168:180].strip()
    if passband != "V" or exists:
        return None

    name = line[226:237].strip() if len(line) >= 237 else ""
    name = " ".join((name or line[8:18].strip()).split())
    ra_h = _float(line[20:22])
    ra_m = _float(line[22:24])
    ra_s = _float(line[24:29])
    dec_d = _float(line[31:33])
    dec_m = _float(line[33:35])
    dec_s = _float(line[35:39])
    mag_max = _float(line[53:59])
    required = (ra_h, ra_m, ra_s, dec_d, dec_m, dec_s, mag_max)
    if not name or any(value is None for value in required):
        return None

    ra_deg = 15.0 * (ra_h + ra_m / 60.0 + ra_s / 3600.0)  # type: ignore[operator]
    dec_deg = dec_d + dec_m / 60.0 + dec_s / 3600.0  # type: ignore[operator]
    if line[30:31] == "-":
        dec_deg *= -1.0

    min_is_amplitude = "(" in line[62:64]
    min_uses_other_band = bool(line[71:73].strip())
    mag_min = None if min_is_amplitude or min_uses_other_band else _float(line[64:70])
    return ParsedStar(
        name=name,
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        variable_type=line[41:51].strip(),
        mag_max=mag_max,  # type: ignore[arg-type]
        mag_max_limit=line[52:53].strip(),
        mag_min=mag_min,
        passband=passband,
    )


def _parse_pipe_line(line: str) -> ParsedStar | None:
    """Analyse la variante actuelle de VizieR, séparée par des barres."""

    fields = line.split("|")
    if len(fields) < 21:
        return None
    passband = fields[7].strip()
    exists = fields[14].strip()
    if passband != "V" or exists:
        return None

    coordinate_match = COORDINATE_RE.match(fields[2])
    magnitude_match = MAGNITUDE_RE.match(fields[4])
    if coordinate_match is None or magnitude_match is None:
        return None

    values = coordinate_match.groupdict()
    ra_deg = 15.0 * (
        float(values["rah"]) + float(values["ram"]) / 60.0 + float(values["ras"]) / 3600.0
    )
    dec_deg = (
        float(values["ded"]) + float(values["dem"]) / 60.0 + float(values["des"]) / 3600.0
    )
    if values["sign"] == "-":
        dec_deg *= -1.0

    name = " ".join((fields[20].strip() or fields[1].strip()).split())
    minimum_match = MAGNITUDE_RE.match(fields[5])
    mag_min = None
    if minimum_match is not None and "(" not in fields[5]:
        mag_min = float(minimum_match.group("value"))
    return ParsedStar(
        name=name,
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        variable_type=fields[3].strip(),
        mag_max=float(magnitude_match.group("value")),
        mag_max_limit=magnitude_match.group("limit"),
        mag_min=mag_min,
        passband=passband,
    )


def obtain_source(source: str) -> bytes:
    path = Path(source)
    if path.exists():
        return path.read_bytes()
    request = urllib.request.Request(
        source,
        headers={"User-Agent": "gnu-astrolist-catalog-builder/0.1"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def build(source: str, output: Path) -> tuple[int, str]:
    compressed = obtain_source(source)
    digest = hashlib.sha256(compressed).hexdigest()
    with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb") as archive:
        text = io.TextIOWrapper(archive, encoding="ascii", errors="replace")
        stars = [star for line in text if (star := parse_gcvs_line(line.rstrip("\n"))) is not None]
    stars.sort(key=lambda star: (star.mag_max, star.name.casefold()))

    output.parent.mkdir(parents=True, exist_ok=True)
    with (
        output.open("wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as archive,
        io.TextIOWrapper(archive, encoding="utf-8", newline="") as text,
    ):
        writer = csv.DictWriter(text, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(star.csv_row() for star in stars)
    return len(stars), digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=SOURCE_URL, help="URL ou fichier gcvs_cat.dat.gz")
    parser.add_argument("--output", type=Path, required=True, help="destination .csv.gz")
    args = parser.parse_args()
    count, digest = build(args.source, args.output)
    print(f"{count} entrées écrites dans {args.output}")
    print(f"SHA-256 de la source : {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
