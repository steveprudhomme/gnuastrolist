#!/usr/bin/env python3
"""Met à jour en une requête TAP le cache SIMBAD des objets Messier."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SIMBAD_TAP_URL = "https://simbad.cds.unistra.fr/simbad/sim-tap/sync"
TAP_QUERY = """
SELECT i.id, b.main_id,
       b.galdim_majaxis, b.galdim_minaxis, b.galdim_bibcode,
       f.flux AS vmag, f.bibcode AS vmag_bibcode,
       f.qual AS vmag_quality, f.system AS vmag_system
FROM ident AS i
JOIN basic AS b ON i.oidref = b.oid
LEFT OUTER JOIN flux AS f ON b.oid = f.oidref AND f.filter = 'V'
WHERE i.id LIKE 'M %'
""".strip()
FIELDNAMES = (
    "name",
    "main_id",
    "major_axis_arcmin",
    "minor_axis_arcmin",
    "size_bibcode",
    "magnitude_v",
    "magnitude_bibcode",
    "magnitude_quality",
    "magnitude_system",
    "retrieved_on",
)
MESSIER_IDENTIFIER = re.compile(r"^M\s+(?P<number>\d+)$")


def query_simbad(source_url: str = SIMBAD_TAP_URL) -> bytes:
    """Exécute une seule requête TAP pour tous les identifiants Messier."""

    payload = urllib.parse.urlencode(
        {
            "request": "doQuery",
            "lang": "adql",
            "format": "csv",
            "query": TAP_QUERY,
        }
    ).encode("ascii")
    request = urllib.request.Request(
        source_url,
        data=payload,
        headers={"User-Agent": "gnu-astrolist-simbad-cache/0.5"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def parse_rows(content: bytes, retrieved_on: str) -> list[dict[str, str]]:
    """Valide et normalise la réponse CSV de SIMBAD."""

    source = csv.DictReader(io.StringIO(content.decode("utf-8"), newline=""))
    objects: dict[int, dict[str, str]] = {}
    for row in source:
        match = MESSIER_IDENTIFIER.fullmatch(row["id"].strip())
        if match is None:
            continue
        number = int(match.group("number"))
        if not 1 <= number <= 110:
            continue
        if number in objects:
            raise ValueError(f"réponse SIMBAD dupliquée pour M{number}")
        objects[number] = {
            "name": f"M{number}",
            "main_id": row["main_id"].strip(),
            "major_axis_arcmin": row["galdim_majaxis"].strip(),
            "minor_axis_arcmin": row["galdim_minaxis"].strip(),
            "size_bibcode": row["galdim_bibcode"].strip(),
            "magnitude_v": row["vmag"].strip(),
            "magnitude_bibcode": row["vmag_bibcode"].strip(),
            "magnitude_quality": row["vmag_quality"].strip(),
            "magnitude_system": row["vmag_system"].strip(),
            "retrieved_on": retrieved_on,
        }

    expected = set(range(1, 111))
    if set(objects) != expected:
        missing = sorted(expected - set(objects))
        unexpected = sorted(set(objects) - expected)
        raise ValueError(
            f"réponse SIMBAD incomplète; absents={missing}, inattendus={unexpected}"
        )
    return [objects[number] for number in sorted(objects)]


def write_cache(rows: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with (
        output.open("wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as archive,
        io.TextIOWrapper(archive, encoding="utf-8", newline="") as text,
    ):
        writer = csv.DictWriter(text, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-url", default=SIMBAD_TAP_URL, help="service TAP SIMBAD")
    parser.add_argument("--response", type=Path, help="réponse CSV locale au lieu du réseau")
    parser.add_argument("--output", type=Path, required=True, help="destination .csv.gz")
    parser.add_argument(
        "--retrieved-on",
        default=datetime.now(timezone.utc).date().isoformat(),
        help="date de récupération AAAA-MM-JJ",
    )
    args = parser.parse_args()
    content = args.response.read_bytes() if args.response else query_simbad(args.source_url)
    rows = parse_rows(content, args.retrieved_on)
    write_cache(rows, args.output)
    size_count = sum(bool(row["major_axis_arcmin"]) for row in rows)
    magnitude_count = sum(bool(row["magnitude_v"]) for row in rows)
    print(f"{len(rows)} objets écrits dans {args.output}")
    print(f"Dimensions SIMBAD disponibles : {size_count}")
    print(f"Magnitudes V SIMBAD disponibles : {magnitude_count}")
    print(f"Date de récupération : {args.retrieved_on} UTC")
    return 0


if __name__ == "__main__":
    sys.exit(main())
