# SPDX-FileCopyrightText: 2026 Steve Prud'Homme
# SPDX-License-Identifier: GPL-3.0-or-later
"""Permet l'exécution avec ``python -m gnu_astrolist``."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())

