# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""ECC-A : destinations protégées et publication atomique de chaque rapport."""

from __future__ import annotations

import os
import stat
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

from .seestar import protect_outputs


def _same_file(left: Path, right: Path) -> bool:
    if left.resolve() == right.resolve():
        return True
    try:
        return left.samefile(right)
    except FileNotFoundError:
        return False


def validate_report_paths(
    outputs: Sequence[Path | None],
    *,
    inputs: Sequence[Path] = (),
    overwrite: bool = False,
    seestar_root: Path | None = None,
    protected_roots: Sequence[Path] = (),
) -> None:
    """Refuse les collisions et destinations dangereuses, sans aucune écriture."""
    destinations = tuple(path for path in outputs if path is not None)
    if not destinations:
        return
    try:
        if seestar_root is not None:
            protect_outputs(seestar_root, destinations)
        roots = (Path(__file__).resolve().parent, *protected_roots)
        for index, output in enumerate(destinations):
            for source in inputs:
                if _same_file(output, source):
                    raise ValueError(f"Export refusé : la sortie {output} correspond à une entrée")
            if any(_same_file(output, other) for other in destinations[:index]):
                raise ValueError("Export refusé : les sorties TXT et PDF doivent être distinctes")
            absolute = output.absolute()
            for component in (*reversed(absolute.parents), absolute):
                try:
                    info = component.lstat()
                except FileNotFoundError:
                    continue
                if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                    raise ValueError("Export refusé : lien ou jonction dans le chemin de sortie")
            resolved = output.resolve()
            if any(resolved.is_relative_to(root.resolve()) for root in roots):
                raise ValueError(
                    "Export refusé : destination dans les ressources ou le cache protégés"
                )
            if not output.parent.is_dir():
                raise ValueError("Export refusé : le dossier parent doit déjà exister")
            try:
                info = output.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("Export refusé : la destination doit être un fichier ordinaire")
            if info.st_nlink > 1:
                raise ValueError("Export refusé : le fichier de sortie possède des liens physiques")
            if not overwrite:
                raise ValueError(
                    f"Export refusé : {output} existe déjà; choisir un autre nom ou utiliser --overwrite"
                )
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"Export refusé : destination inaccessible ({exc})") from exc


@contextmanager
def staged_report(
    path: Path,
    *,
    inputs: Sequence[Path] = (),
    overwrite: bool = False,
    seestar_root: Path | None = None,
    protected_roots: Sequence[Path] = (),
) -> Iterator[Path]:
    """Prépare un fichier voisin puis publie atomiquement, sans tronquer l'ancien.

    Sans remplacement autorisé, rename Windows ou link POSIX refuse aussi un
    fichier apparu après le dernier contrôle. Aucune transaction multirapport.
    """
    policy = dict(
        inputs=inputs,
        overwrite=overwrite,
        seestar_root=seestar_root,
        protected_roots=protected_roots,
    )
    validate_report_paths((path,), **policy)
    temporary_path = None
    try:
        with NamedTemporaryFile(
            prefix=f".{path.stem}-", suffix=path.suffix, dir=path.parent, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
        yield temporary_path
        validate_report_paths((path,), **policy)
        if overwrite:
            os.replace(temporary_path, path)
        elif os.name == "nt":
            os.rename(temporary_path, path)
        else:
            os.link(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
