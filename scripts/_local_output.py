# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sorties JSON locales protégées, sans dépendance astronomique ou applicative."""
from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path


def reject_links(path: Path) -> None:
    for component in (*reversed(path.parents), path):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Lien symbolique ou jonction interdit")
        if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise ValueError("Fichier avec liens physiques interdit")


def validate_output(root: Path, output: Path, *, overwrite=False, sources=()) -> Path:
    output = Path(output).absolute()
    # Inspect lexical paths before resolve, which would hide links/junctions.
    reject_links(output)
    local = root.resolve() / "local"
    reject_links(local)
    target = output.resolve()
    if local not in target.parents:
        raise ValueError("La sortie doit rester dans le dossier local/ du projet")
    for source in sources:
        source = Path(source).absolute()
        reject_links(source)
        if target == source.resolve() or (target.exists() and source.exists()
                                          and os.path.samefile(target, source)):
            raise ValueError("La sortie ne peut pas remplacer une source")
    if not target.parent.is_dir():
        raise ValueError("Le dossier parent de sortie doit déjà exister")
    if target.exists():
        if not stat.S_ISREG(target.lstat().st_mode):
            raise ValueError("La sortie doit être un fichier ordinaire")
        if not overwrite:
            raise FileExistsError("La sortie existe; utiliser --overwrite pour la remplacer")
    return target


def publish_json(root: Path, output: Path, content: str, *, overwrite=False, sources=()) -> None:
    target = validate_output(root, output, overwrite=overwrite, sources=sources)
    descriptor, name = tempfile.mkstemp(prefix=".json-", suffix=".tmp", dir=target.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        validate_output(root, output, overwrite=overwrite, sources=sources)
        if overwrite:
            os.replace(temporary, target)
        else:
            # Atomic no-clobber publication, including a competing new output.
            os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
