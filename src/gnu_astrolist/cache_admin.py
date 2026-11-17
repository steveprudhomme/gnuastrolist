# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Rétention explicite et conservatrice, sans réseau ni purge automatique."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import stat
import sys
import zlib
from contextlib import ExitStack, contextmanager, nullcontext
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import satellite_updates as satellite
from . import updates
from .cache_lock import LOCK_FILE, cache_lock
from .seestar import validate_root

_GENERATION = re.compile(
    r'(' + '|'.join(updates.CATALOG_REGISTRY) + r')-\d{8}T\d{12}-[0-9a-f]{32}'
)
_SOURCE = re.compile(r'source-[0-9a-f]{64}')
_INVALID = (OSError, ValueError, KeyError, TypeError, RuntimeError, EOFError,
            csv.Error, zlib.error, OverflowError)


@dataclass(frozen=True)
class RetentionResult:
    kept: tuple[Path, ...]
    remove: tuple[Path, ...]
    applied: bool


def _regular(path, seestar_root):
    updates._guard(path, seestar_root)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f'Unknown or special cache file: {path.name}')
    return info


def _inventory(root, seestar_root):
    """Liste blanche complète avant toute suppression, sans suivre de lien."""
    updates._guard(root, seestar_root)
    if not root.is_dir() or root == Path(root.anchor) or root == Path.home():
        raise ValueError('An existing controlled cache directory is required')
    generations, identities = {}, {root: root.lstat()}
    for entry in root.iterdir():
        updates._guard(entry, seestar_root)
        if entry.name in {LOCK_FILE, satellite.STATE_FILE}:
            identities[entry] = _regular(entry, seestar_root)
            continue
        match = _GENERATION.fullmatch(entry.name)
        if not match or not stat.S_ISDIR(entry.lstat().st_mode):
            raise ValueError(f'Unknown cache entry: {entry.name}')
        kind = match[1]
        allowed = {updates.CATALOG_REGISTRY[kind].filename, 'metadata.json'}
        # Les générateurs HYG produisent toujours les deux sélections ensemble.
        if kind in {'bayer', 'flamsteed'}:
            allowed.update({'bayer.csv.gz', 'flamsteed.csv.gz'})
        if kind == 'messier':
            allowed.add('simbad_messier_cache.csv.gz')
        files = []
        identities[entry] = entry.lstat()
        for item in entry.iterdir():
            identities[item] = _regular(item, seestar_root)
            if item.name not in allowed and not _SOURCE.fullmatch(item.name):
                raise ValueError(f'Unknown generation file: {item.name}')
            files.append(item)
        raw_files = {item.name for item in files if _SOURCE.fullmatch(item.name)}
        if raw_files:
            try:
                metadata = json.loads((entry / 'metadata.json').read_text(encoding='utf-8'))
                declared = set()
                urls = {url for provider in updates.CATALOG_REGISTRY[kind].sources
                        for url in updates.SOURCE_REGISTRY[provider]}
                for source in metadata['sources']:
                    if source['url'] not in urls:
                        raise ValueError('Unknown source URL')
                    name = 'source-' + updates._sha(
                        source['url'].encode() + (source.get('request_data') or '').encode('ascii'))
                    if source.get('filename') == name:
                        declared.add(name)
                if not raw_files.issubset(declared):
                    raise ValueError('Unknown saved source')
            except (KeyError, TypeError, AttributeError, ValueError) as exc:
                raise ValueError('Unknown generation source files; retention refused') from exc
        generations[entry] = (kind, tuple(files))
    return generations, identities


def _preflight(root, seestar_root):
    """Reconnaît la racine sans explorer des générations qu'un écrivain retire.

    Un verrou déjà présent permet l'attente sans lecture de contenu transitoire.
    Sous verrou, l'inventaire strict refuse tous les temporaires qui subsistent.
    """
    updates._guard(root, seestar_root)
    if not root.is_dir() or root == Path(root.anchor) or root == Path.home():
        raise ValueError('An existing controlled cache directory is required')
    existing_lock = root / LOCK_FILE
    if existing_lock.exists():
        _regular(existing_lock, seestar_root)
        return
    for entry in root.iterdir():
        # Un écrivain peut avoir commencé depuis le premier contrôle.
        if existing_lock.exists():
            _regular(existing_lock, seestar_root)
            return
        updates._guard(entry, seestar_root)
        if entry.name in {LOCK_FILE, satellite.STATE_FILE}:
            _regular(entry, seestar_root)
        elif _GENERATION.fullmatch(entry.name) and entry.is_dir():
            continue
        else:
            raise ValueError(f'Unknown cache entry: {entry.name}')


def _validated_stamp(directory, kind, now, seestar_root):
    manifest = json.loads((directory / 'metadata.json').read_text(encoding='utf-8'))
    if (type(manifest['schema_version']) is not int or manifest['schema_version'] != 1
            or manifest['kind'] != kind):
        raise ValueError('Invalid generation metadata')
    stamp = satellite._timestamp(manifest['retrieved_at'])
    if stamp > now:
        raise ValueError('Future generation')
    artifact = directory / updates.CATALOG_REGISTRY[kind].filename
    if updates._sha(artifact.read_bytes()) != manifest['sha256']:
        raise ValueError('Invalid generation checksum')
    if kind in {'satellites', 'debris'}:
        baseline = satellite._read_bundle(
            satellite.resources.files('gnu_astrolist.data').joinpath(satellite.ARTIFACT))
        satellite.validate_generation(directory, seestar_root, now, baseline)
        count = satellite.validate_bundle(artifact)
    else:
        count = updates._validate(kind, artifact)
        updates._check_count(kind, count, updates._baseline_count(kind))
    if type(manifest['count']) is not int or manifest['count'] != count or count <= 0:
        raise ValueError('Invalid generation count')
    if (not isinstance(manifest['sources'], list)
            or not all(isinstance(source, dict) for source in manifest['sources'])):
        raise ValueError('Invalid generation sources')
    for source in manifest['sources']:
        if (not isinstance(source.get('url'), str)
                or source.get('request_data') is not None
                and not isinstance(source['request_data'], str)):
            raise ValueError('Invalid source request')
        # Seul SATCAT explicitement hérité du paquet peut n'avoir aucun brut.
        if (kind in {'satellites', 'debris'} and not satellite._is_gp(source['url'])
                and not source.get('filename') and source in baseline['sources']):
            continue
        data = (source.get('request_data') or '').encode('ascii')
        expected = 'source-' + updates._sha(source['url'].encode() + data)
        if source['filename'] != expected:
            raise ValueError('Invalid source filename')
        raw = directory / expected
        if updates._sha(raw.read_bytes()) != source['sha256']:
            raise ValueError('Invalid saved source checksum')
    return stamp


def _plan(root, keep, seestar_root):
    generations, identities = _inventory(root, seestar_root)
    families = {}
    now = datetime.now(timezone.utc)
    for directory, (kind, _) in generations.items():
        family = 'satellites' if kind == 'debris' else kind
        valid, invalid = families.setdefault(family, ([], []))
        try:
            stamp = _validated_stamp(directory, kind, now, seestar_root)
        except _INVALID:
            invalid.append(directory)
        else:
            valid.append((stamp, directory.name, directory))
    kept, remove = [], []
    for family, (valid, invalid) in families.items():
        if not valid:
            raise ValueError(f'No valid generation for family {family}; retention refused')
        ordered = [item[2] for item in sorted(valid, reverse=True)]
        kept.extend(ordered[:keep])
        remove.extend([*ordered[keep:], *invalid])
    return tuple(sorted(kept)), tuple(sorted(remove)), generations, identities


@contextmanager
def _pinned_directory(path):
    """Garde les parents ouverts: sans renommage Windows, sans suivi POSIX."""
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        create = kernel.CreateFileW
        create.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                           wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
        create.restype = wintypes.HANDLE
        close = kernel.CloseHandle
        close.argtypes = (wintypes.HANDLE,)
        close.restype = wintypes.BOOL
        # Share READ/WRITE, jamais DELETE: empêcher le remplacement des parents.
        handle = create(str(path), 0, 3, None, 3, 0x02200000, None)
        if handle == wintypes.HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            yield None
        finally:
            close(handle)
    else:
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            yield fd
        finally:
            os.close(fd)


def retain_cache(cache_dir: Path, *, keep: int = 1, apply: bool = False,
                 seestar_root: Path | None = None) -> RetentionResult:
    """Ne supprime que des générations reconnues dans une racine explicite.

    Tout contenu inconnu, lié ou spécial fait échouer l'opération entière.
    Une famille sans génération réellement valide empêche toute suppression.
    """
    if type(keep) is not int or keep < 1:
        raise ValueError('keep must be an integer >= 1')
    if seestar_root is not None:
        seestar_root = validate_root(Path(seestar_root))
    root = Path(cache_dir).absolute()
    updates._guard(root, seestar_root)
    root = root.resolve(strict=True)
    # Refuser les chemins inconnus avant même de créer le verrou d'application.
    if apply:
        _preflight(root, seestar_root)
    with ExitStack() as stack:
        # Épingler toute la chaîne parentale avant d'ouvrir le verrou ou de relire.
        root_fd = None
        if apply:
            for parent in (*reversed(root.parents), root):
                root_fd = stack.enter_context(_pinned_directory(parent))
        stack.enter_context(cache_lock(root, seestar_root) if apply else nullcontext())
        kept, remove, generations, identities = _plan(root, keep, seestar_root)
        if apply:
            for directory in remove:
                with _pinned_directory(directory) as fd:
                    if fd is not None and not os.path.samestat(
                            identities[directory], os.fstat(fd)):
                        raise ValueError('Cache directory identity changed')
                    # Revalider les identités de tous les chemins avant chaque lot.
                    for path in (root, directory, *generations[directory][1]):
                        updates._guard(path, seestar_root)
                        if not os.path.samestat(identities[path], path.lstat()):
                            raise ValueError('Cache identity changed; retention stopped')
                    for item in generations[directory][1]:
                        _regular(item, seestar_root)
                        if fd is None:
                            item.unlink()
                        else:
                            os.unlink(item.name, dir_fd=fd)
                if root_fd is None:
                    directory.rmdir()
                else:
                    os.rmdir(directory.name, dir_fd=root_fd)
        return RetentionResult(kept, remove, apply)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Inspect or trim a controlled local catalog cache')
    parser.add_argument('--cache-dir', type=Path, required=True)
    parser.add_argument('--keep', type=int, default=1)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--seestar-path', type=Path)
    args = parser.parse_args(argv)
    try:
        result = retain_cache(args.cache_dir, keep=args.keep, apply=args.apply,
                              seestar_root=args.seestar_path)
    except (OSError, ValueError, TimeoutError) as exc:
        print(f'Cache retention refused: {exc}', file=sys.stderr)
        return 2
    print('APPLIED' if result.applied else 'DRY RUN (no changes)')
    for path in result.kept:
        print(f'KEEP {path.name}')
    for path in result.remove:
        print(f'{"REMOVED" if result.applied else "WOULD REMOVE"} {path.name}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
