# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Inventaire de livraison reproductible, sans chemins personnels ni faux SBOM."""

import argparse
import hashlib
import json
import platform
from importlib import metadata
from pathlib import Path

from _local_output import publish_json, validate_output
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def runtime_components(name="gnu-astrolist"):
    pending, found = [name], {}
    while pending:
        current = canonicalize_name(pending.pop())
        if current in found:
            continue
        distribution = metadata.distribution(current)
        found[current] = {
            "name": current,
            "version": distribution.version,
            "license": distribution.metadata.get("License-Expression")
            or distribution.metadata.get("License")
            or None,
        }
        for item in distribution.requires or ():
            requirement = Requirement(item)
            if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
                pending.append(requirement.name)
    return [found[key] for key in sorted(found)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--output", type=Path, default=Path("local/environment-manifest.json"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    artifacts = [path for path in args.dist.glob("*") if path.suffix in {".whl", ".gz"}]
    try:
        output = validate_output(root, args.output, overwrite=args.overwrite, sources=artifacts)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if not artifacts:
        parser.error("Construire les distributions avant de créer l'inventaire")
    payload = {
        "schema_version": 1,
        "kind": "release-inventory-not-a-signed-sbom",
        "python": platform.python_version(),
        "platform": platform.system(),
        "runtime_components": runtime_components(),
        "artifacts": [
            {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in sorted(artifacts)
        ],
        "locks": [
            {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in sorted((root / "requirements").glob("*.txt"))
        ],
    }
    publish_json(root, output, json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                 overwrite=args.overwrite, sources=artifacts)
    print(
        f"Inventaire : {len(payload['runtime_components'])} composants; {len(artifacts)} archives"
    )


if __name__ == "__main__":
    main()
