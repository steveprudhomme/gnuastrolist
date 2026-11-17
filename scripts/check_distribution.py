# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Vérifie les catalogues et notices réellement inclus dans la wheel et la sdist."""

import csv
import gzip
import io
import tarfile
import zipfile
from pathlib import Path


def main() -> None:
    dist = Path(__file__).resolve().parents[1] / "dist"
    wheels, sources = sorted(dist.glob("*.whl")), sorted(dist.glob("*.tar.gz"))
    if not wheels or not sources:
        raise SystemExit("Construire wheel et sdist avec python -m build avant ce contrôle")
    for path in wheels + sources:
        if path.suffix == ".whl":
            with zipfile.ZipFile(path) as archive:
                files = {n: archive.read(n) for n in archive.namelist() if not n.endswith("/")}
        else:
            with tarfile.open(path) as archive:
                files = {n.name: archive.extractfile(n).read() for n in archive if n.isfile()}
        for name, count in [("caldwell", 109), ("messier", 110), ("gcvs_visual", 21212),
                            ("ngc", 8098)]:
            matches = [v for k, v in files.items() if k.endswith(f"/data/{name}.csv.gz")]
            assert len(matches) == 1, (path, name)
            rows = list(csv.DictReader(io.StringIO(gzip.decompress(matches[0]).decode("utf-8"))))
            assert len(rows) == count, (path, name, len(rows))
        assert any(k.endswith("/data/CALDWELL_SOURCE.md") for k in files), path
        assert any(k.endswith("/data/NGC_SOURCE.md") for k in files), path
        assert any(k.endswith('gnu_astrolist/selection.py') for k in files), path
        assert any(k.endswith("/LICENSE") or k == "LICENSE" for k in files), path
        assert not any("/local/" in k or k.endswith(("rapport.pdf", "rapport.txt")) for k in files)
        if path.name.endswith('.tar.gz'):
            for image in ('caldwell-parcours.svg', 'validation-locale.svg', 'ngc-selection.svg',
                          'multiple-catalogues.svg'):
                assert any(k.endswith(f'/docs/images/{image}') for k in files), (path, image)
        print(f"{path.name} : catalogues, notice, licence et exclusions OK")


if __name__ == "__main__":
    main()
