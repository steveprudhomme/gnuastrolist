# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ressources temporaires et isolation des caches entre deux commandes."""
from __future__ import annotations

import json
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from importlib import resources
from pathlib import Path
from threading import RLock

_overrides: dict[str, Path] = {}
_lock = RLock()


def catalog_resource(filename: str):
    """Retourne la copie active, ou la ressource embarquée."""
    return _overrides.get(filename) or resources.files('gnu_astrolist.data').joinpath(filename)



def catalog_retrieved_on(filename: str, bundled_date: str) -> str:
    """Date de la génération active; repli explicite pour les copies historiques."""
    path = _overrides.get(filename)
    if path is None:
        return bundled_date
    try:
        metadata = json.loads((path.parent / 'metadata.json').read_text(encoding='utf-8'))
        return datetime.fromisoformat(metadata['retrieved_at']).date().isoformat()
    except (OSError, ValueError, TypeError, KeyError):
        # Pendant la validation, la génération n'a pas encore de manifeste.
        return bundled_date


def _clear_caches() -> None:
    for name in ('catalog', 'seestar', 'asteroids', 'comets'):
        module = sys.modules.get(f'gnu_astrolist.{name}')
        if module is not None:
            for value in vars(module).values():
                clear = getattr(value, 'cache_clear', None)
                if clear is not None:
                    clear()


@contextmanager
def use_catalog_resources(overrides: Mapping[str, Path]) -> Iterator[None]:
    """Active des ressources pour une commande; restaure aussi les contextes imbriqués."""
    global _overrides
    with _lock:
        previous = _overrides
        _clear_caches()
        _overrides = {name: Path(path) for name, path in overrides.items()}
        try:
            yield
        finally:
            _overrides = previous
            _clear_caches()
