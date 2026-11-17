# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Point d’entrée compatible du générateur installé."""
import runpy

if __name__ == "__main__":
    runpy.run_module("gnu_astrolist.data_builders.build_ngc_catalog", run_name="__main__")
else:
    from gnu_astrolist.data_builders import build_ngc_catalog as _builder

    globals().update({key: value for key, value in vars(_builder).items()
                      if not key.startswith("__")})
