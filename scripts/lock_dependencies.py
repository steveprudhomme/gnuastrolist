# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reconstruit les quatre verrous avec uv épinglé, sans installer globalement."""

import subprocess
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    (root / "requirements").mkdir(exist_ok=True)
    for version in ("3.11", "3.13"):
        for platform in ("windows", "linux"):
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "uv",
                    "pip",
                    "compile",
                    "pyproject.toml",
                    "--extra",
                    "dev",
                    "--python-version",
                    version,
                    "--python-platform",
                    platform,
                    "--generate-hashes",
                    "--only-binary",
                    ":all:",
                    "--no-header",
                    "--output-file",
                    f"requirements/py{version.replace('.', '')}-{platform}.txt",
                ],
                cwd=root,
                check=True,
            )


if __name__ == "__main__":
    main()
