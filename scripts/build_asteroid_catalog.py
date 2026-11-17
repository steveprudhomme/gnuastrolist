#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Archive déterministe d'une réponse SBDB locale vérifiée, sans réseau."""

import argparse
import gzip
import hashlib
import json
from datetime import date
from pathlib import Path

from gnu_astrolist.asteroids import parse_sbdb

SOURCE_SHA256 = "5d14ee1a784dfba0e415fd58373a339dbe0ff820f8a0a7be0fdc0c78fa823157"


def build(source: Path, output: Path, retrieved_on: str, expected_sha256=SOURCE_SHA256):
    date.fromisoformat(retrieved_on)
    content = source.read_bytes()
    if expected_sha256 is not None and hashlib.sha256(content).hexdigest() != expected_sha256:
        raise ValueError("Empreinte SBDB incorrecte")
    data = json.loads(content)
    orbits = parse_sbdb(data)
    data["astrolist_retrieved_on"] = retrieved_on
    with (
        output.open("wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as stream,
    ):
        stream.write(
            json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
                "utf-8"
            )
        )
    return len(orbits)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--retrieved-on", required=True)
    parser.add_argument("--expected-sha256", default=SOURCE_SHA256)
    args = parser.parse_args()
    print(build(args.source, args.output, args.retrieved_on, args.expected_sha256))
