# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Vérifie les catalogues et notices réellement inclus dans la wheel et la sdist."""

import csv
import gzip
import io
import json
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
                            ("ngc", 8098), ('bayer', 1537), ('flamsteed', 2737)]:
            matches = [v for k, v in files.items() if k.endswith(f"/data/{name}.csv.gz")]
            assert len(matches) == 1, (path, name)
            rows = list(csv.DictReader(io.StringIO(gzip.decompress(matches[0]).decode("utf-8"))))
            assert len(rows) == count, (path, name, len(rows))
        assert any(k.endswith("/data/CALDWELL_SOURCE.md") for k in files), path
        assert any(k.endswith("/data/NGC_SOURCE.md") for k in files), path
        orbital = [v for k, v in files.items() if k.endswith('/data/asteroids.json.gz')]
        assert len(orbital) == 1 and len(json.loads(gzip.decompress(orbital[0]))['data']) == 1000
        assert any(k.endswith('/data/ASTEROID_SOURCE.md') for k in files), path
        assert any(k.endswith('gnu_astrolist/asteroids.py') for k in files), path
        comet_data = [v for k,v in files.items() if k.endswith('/data/comets.txt.gz')]
        assert len(comet_data)==1 and len(gzip.decompress(comet_data[0]).splitlines())==973
        assert any(k.endswith('/data/COMET_SOURCE.md') for k in files), path
        for module in ('comets.py','moving.py','updates.py','catalog_resources.py',
                       'data_builders/build_catalog.py','data_builders/build_messier_catalog.py',
                       'data_builders/build_caldwell_catalog.py','data_builders/build_ngc_catalog.py',
                       'data_builders/build_stellar_catalogs.py','data_builders/update_simbad_cache.py'):
            assert any(k.endswith('gnu_astrolist/'+module) for k in files), (path,module)
        for resource in ('STELLAR_SOURCE.md', 'HYG_LICENSE.md', 'FONT_SOURCE.md',
                         'fonts/DejaVuSans.ttf', 'fonts/DejaVuSans-Bold.ttf',
                         'fonts/LICENSE_DEJAVU.txt'):
            assert any(k.endswith(f'/data/{resource}') for k in files), (path, resource)
        assert any(k.endswith('gnu_astrolist/selection.py') for k in files), path
        assert any(k.endswith('gnu_astrolist/seestar.py') for k in files), path
        assert any(k.endswith("/LICENSE") or k == "LICENSE" for k in files), path
        assert not any("/local/" in k or k.endswith(("rapport.pdf", "rapport.txt")) for k in files)
        if path.name.endswith('.tar.gz'):
            assert any(k.endswith('/tests/data/asteroid_horizons.json') for k in files), path
            assert any(k.endswith('/tests/data/comet_horizons.json') for k in files), path
            for image in ('caldwell-parcours.svg', 'validation-locale.svg', 'ngc-selection.svg',
                          'multiple-catalogues.svg', 'seestar-lecture-seule.svg',
                          'premiers-pas.svg', 'bayer-flamsteed.svg', 'asteroides.svg',
                          'cometes-sources.svg','catalogues-mise-a-jour.svg'):
                assert any(k.endswith(f'/docs/images/{image}') for k in files), (path, image)
        print(f"{path.name} : catalogues, notice, licence et exclusions OK")


if __name__ == "__main__":
    main()
