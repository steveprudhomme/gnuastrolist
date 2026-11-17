# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Contrats de livraison : empreintes obligatoires et inventaire sans chemins privés."""

import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_four_target_locks_pin_every_dependency_with_hashes():
    for python in ("310", "313"):
        for platform in ("windows", "linux"):
            text = (ROOT / "requirements" / f"py{python}-{platform}.txt").read_text()
            blocks = re.split(r"\n(?=[a-zA-Z0-9])", text)
            assert len(blocks) > 10
            for block in blocks:
                assert re.match(r"[A-Za-z0-9_.-]+==[^\s]+", block)
                assert re.search(r"--hash=sha256:[a-f0-9]{64}", block)
            assert not any(word in text for word in ("file:///", "git+", "C:\\Users\\"))


def test_runtime_inventory_includes_direct_numpy_but_not_development_tools(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'scripts'))
    script = runpy.run_path(str(ROOT / "scripts" / "environment_manifest.py"))
    components = script["runtime_components"]()
    names = {item["name"] for item in components}
    assert {"gnu-astrolist", "numpy", "astropy", "reportlab", "sgp4"} <= names
    assert not {"pytest", "mypy", "pip-audit", "uv"} & names
    assert all(set(item) == {"name", "version", "license"} for item in components)
