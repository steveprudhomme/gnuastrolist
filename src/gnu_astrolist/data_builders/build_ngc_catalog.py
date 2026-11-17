#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Construit le sous-ensemble NGC depuis un fichier OpenNGC local, sans réseau."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import math
import re
from datetime import date
from pathlib import Path

from .build_messier_catalog import (
    FIELDNAMES,
    OPENNGC_REFERENCE,
    _declination_degrees,
    _read_rows,
    _right_ascension_degrees,
)

SOURCE_SHA256 = "54abea0b57b0a103831bfc7a8e3a99a23acfbf4bb581fcf3d8af539cbb826c84"
IDENTIFIER = re.compile(r"^NGC(\d+)(.*)$")


def optional_number(value: str, *, positive: bool = False) -> str:
    if not value.strip():
        return ""
    number = float(value)
    if not math.isfinite(number) or (positive and number <= 0):
        raise ValueError(f"Valeur numérique invalide : {value}")
    return value.strip()


def build(
    source: Path, output: Path, retrieved_on: str, expected_sha256: str | None = SOURCE_SHA256
) -> dict[str, int | str]:
    date.fromisoformat(retrieved_on)
    content = source.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError("Empreinte OpenNGC différente de la source attendue")
    objects = {}
    excluded = 0
    missing_coordinates = 0
    for row in _read_rows(content):
        match = IDENTIFIER.fullmatch(row["Name"])
        if match is None:
            continue
        if row["Type"] in {"Dup", "NonEx"}:
            excluded += 1
            continue
        if not row["RA"].strip() or not row["Dec"].strip():
            missing_coordinates += 1
            continue
        ra = _right_ascension_degrees(row["RA"])
        dec = _declination_degrees(row["Dec"])
        if not (0 <= ra < 360 and -90 <= dec <= 90):
            raise ValueError(f"Coordonnées invalides : {row['Name']}")
        name = f"NGC{int(match[1])}{match[2]}"
        if name in objects:
            raise ValueError(f"Identifiant NGC dupliqué : {name}")
        obj = dict.fromkeys(FIELDNAMES, "")
        obj.update(
            name=name,
            ra_deg=f"{ra:.8f}",
            dec_deg=f"{dec:.8f}",
            object_type=row["Type"],
            catalog_designation=row["Name"],
            constellation={"Se1": "Ser", "Se2": "Ser"}.get(row["Const"], row["Const"]),
            major_axis_arcmin=optional_number(row["MajAx"], positive=True),
            minor_axis_arcmin=optional_number(row["MinAx"], positive=True),
            magnitude_v=optional_number(row["V-Mag"]),
            passband="V",
            common_name=row["Common names"].replace(",", "; "),
        )
        for field, present in [
            ("size", obj["major_axis_arcmin"]),
            ("magnitude", obj["magnitude_v"]),
        ]:
            if present:
                obj.update(
                    {
                        f"{field}_source": "OpenNGC",
                        f"{field}_reference": OPENNGC_REFERENCE,
                        f"{field}_retrieved_on": retrieved_on,
                    }
                )
        objects[name] = obj
    if not objects:
        raise ValueError("Le catalogue NGC construit est vide")
    ordered = sorted(
        objects.values(),
        key=lambda obj: (
            int(IDENTIFIER.fullmatch(obj["name"])[1]),
            IDENTIFIER.fullmatch(obj["name"])[2].casefold(),
        ),
    )
    with (
        output.open("wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as archive,
        io.TextIOWrapper(archive, encoding="utf-8", newline="") as stream,
    ):
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(ordered)
    return {
        "count": len(ordered),
        "excluded": excluded,
        "missing_coordinates": missing_coordinates,
        "missing_v": sum(not obj["magnitude_v"] for obj in ordered),
        "source_sha256": digest,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="fichier OpenNGC NGC.csv local")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--retrieved-on", required=True)
    parser.add_argument("--expected-sha256", default=SOURCE_SHA256)
    args = parser.parse_args()
    print(build(args.source, args.output, args.retrieved_on, args.expected_sha256))
