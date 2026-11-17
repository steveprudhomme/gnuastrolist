# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Construit une copie GP/SATCAT à partir de quatre réponses CSV locales vérifiées."""

import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

from gnu_astrolist.satcat import parse_satcat
from gnu_astrolist.satellites import parse_gp


def build(source_dir: Path, output: Path):
    manifest = json.loads((source_dir / "manifest.json").read_text(encoding="utf-8"))
    collected = {"gp": {}, "satcat": {}}
    for source in manifest:
        content = (source_dir / source["file"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != source["sha256"]:
            raise ValueError("Empreinte de source CelesTrak incorrecte")
        category = "satcat" if source["file"].endswith("-satcat.csv") else "gp"
        for row in csv.DictReader(io.StringIO(content.decode("utf-8-sig"))):
            number = int(row["NORAD_CAT_ID"])
            previous = collected[category].get(number)
            if previous is not None and previous != row:
                raise ValueError("Sources CelesTrak contradictoires")
            collected[category][number] = row
    if len(manifest) != 4 or not collected["gp"] or not collected["satcat"]:
        raise ValueError("Quatre réponses GP/SATCAT sont requises")
    payload = {
        "schema_version": 1,
        "sources": manifest,
        **{kind: [values[key] for key in sorted(values)] for kind, values in collected.items()},
    }
    records=parse_satcat(payload["satcat"])
    for element in parse_gp(payload['gp']):
        record=records.get(element.norad_id)
        if record is None or element.cospar_id!=record.cospar_id:
            raise ValueError('Jointure GP/SATCAT contradictoire')
    output.write_bytes(
        gzip.compress(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            ),
            mtime=0,
        )
    )
    return len(payload["gp"]), len(payload["satcat"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(build(args.source_dir, args.output))
