# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compresse sans modifier les éléments MPC, avec contrôle d'empreinte."""

import argparse
import gzip
import hashlib
from pathlib import Path

from gnu_astrolist.comets import parse_mpc

SOURCE_SHA256 = "25d1886242a6d1761c07a49311195bf1fd1eef066be5d67d9257a815368213f8"


def build(source, output, expected_sha256=SOURCE_SHA256):
    content = source.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected_sha256:
        raise ValueError("Empreinte MPC incorrecte")
    orbits = parse_mpc(content.decode("ascii"))
    with (
        output.open("wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as stream,
    ):
        stream.write(content)
    return len(orbits)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-sha256", default=SOURCE_SHA256)
    args = parser.parse_args()
    print(build(args.source, args.output, args.expected_sha256))
