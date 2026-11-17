#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Construit les 109 Caldwell depuis OpenNGC, avec complément V SIMBAD facultatif."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from build_messier_catalog import (
    FIELDNAMES,
    OPENNGC_REFERENCE,
    _declination_degrees,
    _read_rows,
    _right_ascension_degrees,
    obtain_source,
)

OPENNGC_COMMIT = "be3cd6c5498806a2fbb2f7e0452ef802dbb02be0"
SOURCE_BASE = f"https://raw.githubusercontent.com/mattiaverga/OpenNGC/{OPENNGC_COMMIT}"
NGC_SOURCE_URL = f"{SOURCE_BASE}/database_files/NGC.csv"
ADDENDUM_SOURCE_URL = f"{SOURCE_BASE}/database_files/addendum.csv"

# Correspondances vérifiées avec la liste du programme Caldwell de l'Astronomical League.
# Les entrées composées utilisent le centre représentatif OpenNGC documenté.
DESIGNATIONS = """
NGC0188 NGC0040 NGC4236 NGC7023 IC0342 NGC6543 NGC2403 NGC0559 C009 NGC0663
NGC7635 NGC6946 NGC0457 C014 NGC6826 NGC7243 NGC0147 NGC0185 IC5146 NGC7000
NGC4449 NGC7662 NGC0891 NGC1275 NGC2419 NGC4244 NGC6888 NGC0752 NGC5005 NGC7331
IC0405 NGC4631 NGC6992 NGC6960 NGC4889 NGC4559 NGC6885 NGC4565 NGC2392 NGC3626
C041 NGC7006 NGC7814 NGC7479 NGC5248 NGC2261 NGC6934 NGC2775 NGC2237 NGC2244
IC1613 NGC4697 NGC3115 NGC2506 NGC7009 NGC0246 NGC6822 NGC2360 NGC3242 NGC4038
NGC4039 NGC0247 NGC7293 NGC2362 NGC0253 NGC5694 NGC1097 NGC6729 NGC6302 NGC0300
NGC2477 NGC0055 NGC1851 NGC3132 NGC6124 NGC6231 NGC5128 NGC6541 NGC3201 NGC5139
NGC6352 NGC6193 NGC4945 NGC5286 IC2391 NGC6397 NGC1261 NGC5823 NGC6087 NGC2867
NGC3532 NGC3372 NGC6752 NGC4755 NGC6025 NGC2516 NGC3766 NGC4609 C099 IC2944
NGC6744 IC2602 NGC2070 NGC0362 NGC4833 NGC0104 NGC6101 NGC4372 NGC3195
""".split()

SIMBAD_IDS = {9: "Sh 2-155", 14: "h and chi Per", 41: "Cl Melotte 25", 99: "Coalsack"}


def simbad_id(number: int, designation: str) -> str:
    if number in SIMBAD_IDS:
        return SIMBAD_IDS[number]
    prefix = "NGC" if designation.startswith("NGC") else "IC"
    return f"{prefix} {int(designation[len(prefix) :])}"


def fetch_simbad_missing(rows: list[dict[str, str]], output: Path, endpoint: str) -> None:
    """Une requête en lot; conserve la réponse brute pour une reconstruction hors ligne."""
    identifiers = [
        simbad_id(n, designation)
        for n, designation in enumerate(DESIGNATIONS, 1)
        if not rows[n - 1]["V-Mag"]
    ]
    variants = set(identifiers)
    for identifier in identifiers:
        if identifier.startswith(("NGC ", "IC ")):
            prefix, number = identifier.split()
            variants.update(prefix + " " * spaces + number for spaces in range(1, 5))
    quoted = ",".join("'" + value.replace("'", "''") + "'" for value in sorted(variants))
    query = (
        "SELECT i.id, f.flux, f.bibcode, f.qual, f.system FROM ident AS i "
        "JOIN flux AS f ON i.oidref=f.oidref "
        f"WHERE f.filter='V' AND i.id IN ({quoted})"
    )
    url = endpoint + "?"
    url += urlencode({"request": "doQuery", "lang": "adql", "format": "csv", "query": query})
    with urlopen(url, timeout=60) as response:
        output.write_bytes(response.read())


def build(args: argparse.Namespace) -> None:
    contents = [obtain_source(args.ngc_source), obtain_source(args.addendum_source)]
    sources = {row["Name"]: row for content in contents for row in _read_rows(content)}
    rows = [sources[name] for name in DESIGNATIONS]
    if args.fetch_simbad:
        fetch_simbad_missing(rows, args.simbad_response, args.simbad_endpoint)
    supplement = {}
    if args.simbad_response:
        with args.simbad_response.open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                identifier = " ".join(row["id"].split())
                if identifier in supplement:
                    raise ValueError(f"Magnitude SIMBAD ambiguë : {identifier}")
                supplement[identifier] = row
    objects = []
    for number, row in enumerate(rows, 1):
        obj = dict.fromkeys(FIELDNAMES, "")
        obj.update(
            name=f"C{number}",
            ra_deg=f"{_right_ascension_degrees(row['RA']):.8f}",
            dec_deg=f"{_declination_degrees(row['Dec']):.8f}",
            object_type=row["Type"],
            catalog_designation=row["Name"],
            constellation=row["Const"],
            major_axis_arcmin=row["MajAx"],
            minor_axis_arcmin=row["MinAx"],
            magnitude_v=row["V-Mag"],
            passband="V",
            common_name=row["Common names"].replace(",", "; "),
        )
        if obj["major_axis_arcmin"]:
            obj.update(
                size_source="OpenNGC",
                size_reference=OPENNGC_REFERENCE,
                size_retrieved_on=args.retrieved_on,
            )
        if obj["magnitude_v"]:
            obj.update(
                magnitude_source="OpenNGC",
                magnitude_reference=OPENNGC_REFERENCE,
                magnitude_retrieved_on=args.retrieved_on,
            )
        else:
            extra = supplement.get(simbad_id(number, row["Name"]))
            if (
                extra
                and extra["flux"].strip()
                and extra["qual"].strip() in {"A", "B", "C"}
                and math.isfinite(float(extra["flux"]))
            ):
                obj.update(
                    magnitude_v=str(float(extra["flux"])),
                    magnitude_source="SIMBAD",
                    magnitude_reference=extra["bibcode"].strip() or "SIMBAD TAP",
                    magnitude_retrieved_on=args.retrieved_on,
                )
        objects.append(obj)
    if len(objects) != 109:
        raise ValueError("Le catalogue Caldwell doit contenir 109 objets")
    with (
        args.output.open("wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as archive,
        io.TextIOWrapper(archive, encoding="utf-8", newline="") as stream,
    ):
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(objects)
    print(
        json.dumps(
            {
                "count": len(objects),
                "missing_v": [o["name"] for o in objects if not o["magnitude_v"]],
                "simbad_v": [o["name"] for o in objects if o["magnitude_source"] == "SIMBAD"],
                "source_sha256": [hashlib.sha256(c).hexdigest() for c in contents],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ngc-source", default=NGC_SOURCE_URL)
    parser.add_argument("--addendum-source", default=ADDENDUM_SOURCE_URL)
    parser.add_argument("--retrieved-on", required=True, help="date de récupération AAAA-MM-JJ")
    parser.add_argument("--simbad-response", type=Path)
    parser.add_argument("--fetch-simbad", action="store_true")
    parser.add_argument(
        "--simbad-endpoint", default="https://simbad.cds.unistra.fr/simbad/sim-tap/sync"
    )
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    if options.fetch_simbad and options.simbad_response is None:
        parser.error("--fetch-simbad exige --simbad-response")
    build(options)
