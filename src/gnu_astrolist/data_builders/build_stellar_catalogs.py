#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Construit Bayer et Flamsteed depuis une copie HYG 4.1 locale vérifiée."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import math
from collections import Counter
from pathlib import Path

from gnu_astrolist.stellar_names import bayer_label, normalize_stellar_name

SOURCE_SHA256 = "d9f69fd86bbf90a4e4d52b4c5c53eacfa6dfc0bfdef85bfd94f095e0bebe4ebd"
FIELDS = (
    "name",
    "ra_deg",
    "dec_deg",
    "magnitude_v",
    "hyg_id",
    "constellation",
    "bayer_name",
    "flamsteed_name",
    "common_name",
    "ambiguous_names",
)


def build(source: Path, output_dir: Path, expected_sha256: str | None = SOURCE_SHA256) -> dict:
    content = source.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError("Empreinte HYG différente de la source attendue")
    rows = list(csv.DictReader(io.StringIO(content.decode("utf-8"))))
    stars = []
    ids = set()
    for row in rows:
        if not row["con"] or not (row["bayer"] or row["flam"]):
            continue
        hyg_id = int(row["id"])
        if hyg_id in ids:
            raise ValueError(f"Identifiant HYG dupliqué : {hyg_id}")
        ids.add(hyg_id)
        ra, dec = float(row["ra"]) * 15, float(row["dec"])
        mag = float(row["mag"]) if row["mag"].strip() else None
        if not (0 <= ra < 360 and -90 <= dec <= 90) or (mag is not None and not math.isfinite(mag)):
            raise ValueError(f"Coordonnées ou magnitude invalides pour HYG {hyg_id}")
        if row["flam"] and (not row["flam"].isdigit() or int(row["flam"]) < 1):
            raise ValueError(f"Numéro Flamsteed invalide : {row['flam']}")
        stars.append(
            dict(
                name="",
                ra_deg=f"{ra:.8f}",
                dec_deg=f"{dec:.8f}",
                magnitude_v="" if mag is None else str(mag),
                hyg_id=str(hyg_id),
                constellation=row["con"],
                bayer_name=bayer_label(row["bayer"], row["con"]) if row["bayer"] else "",
                flamsteed_name=f"{int(row['flam'])} {row['con']}" if row["flam"] else "",
                common_name=row["proper"],
                ambiguous_names="",
            )
        )
    counts = Counter(
        normalize_stellar_name(s[field])
        for s in stars
        for field in ("bayer_name", "flamsteed_name")
        if s[field]
    )
    proper_counts = Counter(row["proper"].strip().casefold() for row in rows if row["proper"])
    for star in stars:
        ambiguous = [
            star[field]
            for field in ("bayer_name", "flamsteed_name")
            if star[field] and counts[normalize_stellar_name(star[field])] > 1
        ]
        if star["common_name"] and proper_counts[star["common_name"].strip().casefold()] > 1:
            ambiguous.append(star["common_name"])
        star["ambiguous_names"] = "|".join(ambiguous)
    result = {"source_sha256": digest, "union": len(stars)}
    if not stars:
        raise ValueError("Aucune désignation Bayer ou Flamsteed exploitable")
    for kind, field in (("bayer", "bayer_name"), ("flamsteed", "flamsteed_name")):
        selected = []
        for star in stars:
            if not star[field]:
                continue
            name = star[field]
            if name in star["ambiguous_names"].split("|"):
                name += f" [HYG {star['hyg_id']}]"
            selected.append({**star, "name": name})
        selected.sort(key=lambda s: int(s["hyg_id"]))
        with (
            (output_dir / f"{kind}.csv.gz").open("wb") as raw,
            gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as archive,
            io.TextIOWrapper(archive, encoding="utf-8", newline="") as stream,
        ):
            writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(selected)
        result[kind] = len(selected)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-sha256", default=SOURCE_SHA256)
    args = parser.parse_args()
    print(build(args.source, args.output_dir, args.expected_sha256))
