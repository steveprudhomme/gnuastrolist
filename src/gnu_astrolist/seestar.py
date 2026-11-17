# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Inventaire Seestar en lecture de noms et métadonnées seulement, sans cache."""

from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

from .catalog import load_caldwell_catalog, load_messier_catalog
from .models import CatalogObject, DeepSkyObject, NamedStar, VisibilityResult
from .stellar_names import normalize_stellar_name

ACQUISITION = re.compile(
    r"^(?P<kind>Stacked|Light)_(?:\d+_)?(?P<target>.+?)_\d+(?:\.\d+)?s_", re.IGNORECASE
)
EXTENSIONS = {".fit", ".fits", ".fts", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}
IGNORED_DIRECTORIES = {".git", ".cache", "__pycache__"}


def normalize_name(value: str) -> str:
    stellar = normalize_stellar_name(value)
    if stellar:
        return stellar
    value = value.strip().upper()
    match = re.fullmatch(r"(NGC|IC|M|C|HYG)[ _-]*(\d+)([A-Z]{0,2}|\s+NED\d+)?", value)
    if match:
        return f"{match[1]}{int(match[2])}{(match[3] or '').strip()}"
    return " ".join(value.split())


def _reparse(info: os.stat_result) -> bool:
    return bool(getattr(info, "st_file_attributes", 0) & 0x400)


def validate_root(path: Path) -> Path:
    try:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or _reparse(info):
            raise ValueError("La racine Seestar doit être un dossier direct, sans lien ou jonction")
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("Le chemin Seestar doit désigner un dossier")
        return path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"Dossier Seestar inaccessible : {path}") from exc


def protect_outputs(root: Path, outputs: tuple[Path | None, ...]) -> None:
    # Pour un volume Windows externe distinct du volume du logiciel, protéger
    # tout le volume. Pour une copie sur le même volume, protéger l'arbre source.
    boundary = (
        Path(root.anchor)
        if root.drive and root.drive.casefold() != Path(__file__).drive.casefold()
        else root
    )
    for output in outputs:
        if output is None:
            continue
        try:
            destination = output.resolve()
            if destination.is_relative_to(boundary):
                raise ValueError("Export refusé : destination dans les archives Seestar protégées")
            if destination.exists() and destination.stat().st_nlink > 1:
                raise ValueError("Export refusé : le fichier de sortie possède des liens physiques")
        except (OSError, RuntimeError) as exc:
            raise ValueError(f"Destination de rapport inaccessible : {output}") from exc


@dataclass(frozen=True)
class SeestarInventory:
    root: Path
    stacked: frozenset[str]
    light: frozenset[str]
    issues: int = 0

    @property
    def summary(self) -> str:
        state = "lecture incomplète" if self.issues else "lecture terminée"
        return f"Seestar : {self.root} — lecture seule; {state}; {self.issues} incident(s)."

    def status(self, keys: set[str]) -> str:
        if keys & self.stacked:
            return "Fait (empilé)"
        if keys & self.light:
            return "Brutes (incomplet)" if self.issues else "Brutes seules"
        return "Indéterminé" if self.issues else "Non trouvé"


def scan_seestar(root: Path) -> SeestarInventory:
    """Énumère les noms et tailles; n'ouvre ni image, ni FITS, ni fichier en écriture."""
    root = validate_root(root)
    stacked, light = set(), set()
    pending = [root]
    issues = 0
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    try:
                        info = entry.stat(follow_symlinks=False)
                        if stat.S_ISLNK(info.st_mode) or _reparse(info):
                            issues += 1
                            continue
                        if stat.S_ISDIR(info.st_mode):
                            if entry.name.casefold() not in IGNORED_DIRECTORIES:
                                pending.append(Path(entry.path))
                            continue
                        if not stat.S_ISREG(info.st_mode) or info.st_size == 0:
                            continue
                        path = Path(entry.name)
                        if path.suffix.casefold() not in EXTENSIONS:
                            continue
                        if re.search(r"_(?:thn|thumb|thumbnail)$", path.stem, re.IGNORECASE):
                            continue
                        match = ACQUISITION.match(entry.name)
                        if match:
                            target = normalize_name(match["target"])
                            (stacked if match["kind"].casefold() == "stacked" else light).add(
                                target
                            )
                    except OSError:
                        issues += 1
        except OSError:
            issues += 1
    return SeestarInventory(root, frozenset(stacked), frozenset(light), issues)


@lru_cache(maxsize=1)
def _known_aliases() -> dict[str, frozenset[str]]:
    aliases: dict[str, set[str]] = {}
    for reference in (*load_messier_catalog(), *load_caldwell_catalog()):
        designation = normalize_name(reference.catalog_designation)
        if designation:
            aliases.setdefault(designation, set()).add(normalize_name(reference.name))
    return {key: frozenset(values) for key, values in aliases.items()}


def object_keys(obj: CatalogObject) -> set[str]:
    keys = {normalize_name(obj.name)}
    if isinstance(obj, NamedStar):
        keys.update(normalize_name(name) for name in (
            obj.bayer_name, obj.flamsteed_name, obj.common_name, f'HYG{obj.hyg_id}', *obj.aliases,
        ) if name)
        keys.difference_update(normalize_name(name) for name in obj.ambiguous_names)
    if isinstance(obj, DeepSkyObject):
        keys.add(normalize_name(obj.catalog_designation))
        keys.update(normalize_name(alias) for alias in obj.aliases)
        # Correspondances explicites des catalogues embarqués, y compris lorsque
        # l'utilisateur n'a sélectionné que NGC, Messier ou Caldwell.
        designation = normalize_name(obj.catalog_designation)
        if designation:
            keys.update(_known_aliases().get(designation, ()))
    keys.discard("")
    return keys


def annotate_results(
    results: list[VisibilityResult],
    inventory: SeestarInventory,
) -> list[VisibilityResult]:
    annotated = []
    for result in results:
        status = inventory.status(object_keys(result.star))
        if isinstance(result.star, NamedStar) and status in ('Non trouvé', 'Indéterminé'):
            ambiguous = {normalize_name(name) for name in result.star.ambiguous_names}
            if ambiguous & (inventory.stacked | inventory.light):
                status = 'Indéterminé (nom partagé)'
        annotated.append(replace(result, seestar_status=status))
    return annotated
