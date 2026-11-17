# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Vérifie documents indispensables, liens locaux et cohérence de version."""

import re
import subprocess
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    required = (
        "README.md",
        "INSTALL.md",
        "CONTRIBUTING.md",
        "AGENTS.md",
        "LICENSE",
        "LICENSE-NOTICE.md",
        "DCO.md",
        "GOVERNANCE.md",
        "MAINTAINERS.md",
        "SECURITY.md",
        "PRIVACY.md",
        "CHANGELOG.md",
        "ROADMAP.md",
        "docs/ARCHITECTURE.md",
        "docs/TUTORIEL.md",
        "docs/VALIDATION.md",
        "docs/RELEASE.md",
        ".github/workflows/quality.yml",
        ".github/pull_request_template.md",
    )
    errors = [f"Fichier absent : {name}" for name in required if not (root / name).is_file()]
    files = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        text=True,
        encoding="utf-8",
    ).splitlines()
    for name in files:
        path = root / name
        if name.startswith(("local/", ".venv/")) or path.suffix.lower() in {".pem", ".key"}:
            errors.append(f"Fichier privé ou local dans le dépôt : {name}")
        if path.suffix == ".md" and path.is_file():
            text = path.read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)]+)\)", text):
                target = target.strip("<>").split("#")[0]
                if not target or ":" in target or target.startswith("//"):
                    continue
                if not (path.parent / target).exists():
                    errors.append(f"Lien local brisé : {name} → {target}")
    project = (root / "pyproject.toml").read_text(encoding="utf-8")
    module = (root / "src/gnu_astrolist/__init__.py").read_text(encoding="utf-8")
    if (
        re.search(r'^version = "([^"]+)"', project, re.M)[1]
        != re.search(r'^__version__ = "([^"]+)"', module, re.M)[1]
    ):
        errors.append("Versions pyproject.toml et __version__ divergentes")
    print("\n".join(errors) if errors else "Structure, liens locaux et versions : OK")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
