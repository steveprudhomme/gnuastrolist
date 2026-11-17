# SPDX-FileCopyrightText: 2026 Steve Prud'Homme
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prépare des versions SemVer à partir de changements publics, sans tag ni publication."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

if __package__:
    from ._local_output import reject_links
else:
    from _local_output import reject_links

ROOT = Path(__file__).resolve().parents[1]
POLICY = {'bug': 'patch', 'improvement': 'minor', 'feature': 'minor'}
LEVELS = {'patch': 0, 'minor': 1, 'major': 2}
TITLES = {'bug': 'Corrigé', 'improvement': 'Amélioré', 'feature': 'Ajouté'}
FILES = ('pyproject.toml', 'src/gnu_astrolist/__init__.py', 'CHANGELOG.md', 'versioning.toml')


class VersioningError(ValueError):
    """Contrat de version ou préparation refusée sans publication distante."""


@dataclass(frozen=True)
class Change:
    path: Path
    kind: str
    summary: str
    breaking: bool
    released_in: str | None = None


@dataclass(frozen=True)
class Project:
    root: Path
    version: str
    changes: tuple[Change, ...]
    inputs: dict[Path, bytes]


@dataclass(frozen=True)
class ReleasePlan:
    project: Project
    version: str
    updates: dict[Path, bytes]


def parse_version(value: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', value):
        raise VersioningError('Version de livraison attendue : MAJOR.MINOR.PATCH, sans préfixe')
    return tuple(map(int, value.split('.')))


def _guard(path: Path) -> None:
    try:
        reject_links(path.absolute())
        if not path.is_file():
            raise VersioningError(f'Fichier ordinaire requis : {path.name}')
    except (OSError, ValueError) as exc:
        raise VersioningError(f'Fichier inaccessible : {path.name}') from exc


def _read(path: Path) -> bytes:
    _guard(path)
    return path.read_bytes()


def _version(text: str, key: str) -> str:
    matches = re.findall(rf'(?m)^{key}\s*=\s*"([^"]+)"\s*$', text)
    if len(matches) != 1:
        raise VersioningError(f'Une déclaration {key} entre guillemets doubles est requise')
    parse_version(matches[0])
    return matches[0]


def _policy(text: str) -> None:
    config = tomllib.loads(text)
    if (set(config) != {'schema_version', 'scheme', 'breaking', 'types'}
            or type(config['schema_version']) is not int or config['schema_version'] != 1
            or config['scheme'] != 'semver' or config['breaking'] != 'major'
            or config['types'] != POLICY):
        raise VersioningError('Politique SemVer invalide ou différente des règles approuvées')


def read_project(root: Path) -> Project:
    root = Path(root).absolute()
    directory = root / 'changes'
    reject_links(directory)
    if not directory.is_dir():
        raise VersioningError('Le dossier changes est requis')
    inputs = {root / name: _read(root / name) for name in FILES}
    inputs.update({path: _read(path) for path in sorted(directory.glob('*.toml'))})
    return _parse_project(root, inputs)


def _parse_project(root: Path, inputs: dict[Path, bytes]) -> Project:
    try:
        texts = {Path(name).name: inputs[root / name].decode('utf-8') for name in FILES}
        _policy(texts['versioning.toml'])
        metadata = tomllib.loads(texts['pyproject.toml'])['project']
        if metadata['name'] != 'gnu-astrolist':
            raise VersioningError('Cet outil est réservé au projet GNU Astrolist')
        version = _version(texts['pyproject.toml'], 'version')
        if metadata['version'] != version or _version(texts['__init__.py'], '__version__') != version:
            raise VersioningError('Versions pyproject.toml et __version__ divergentes')
        log = texts['CHANGELOG.md']
        if len(re.findall(r'^## \[Non publié\]\s*$', log, re.M)) != 1:
            raise VersioningError('Une section Non publié est requise dans CHANGELOG')
        if not re.search(rf'^## \[{re.escape(version)}\](?:\s|$)', log, re.M):
            raise VersioningError('La version courante doit figurer dans CHANGELOG')
        changes = []
        for path in sorted(path for path in inputs if path.parent == root / 'changes'):
            if not re.fullmatch(r'[a-z0-9][a-z0-9_.-]*\.toml', path.name):
                raise VersioningError('Nom de fragment invalide')
            data = tomllib.loads(inputs[path].decode('utf-8'))
            if (set(data) - {'type', 'summary', 'breaking', 'released_in'}
                    or not {'type', 'summary'} <= set(data)
                    or data['type'] not in POLICY
                    or not isinstance(data['summary'], str) or not data['summary'].strip()
                    or len(data['summary']) > 500
                    or any(ord(char) < 32 for char in data['summary'])
                    or type(data.get('breaking', False)) is not bool):
                raise VersioningError(f'Fragment invalide : {path.name}')
            released = data.get('released_in')
            if released is not None:
                if parse_version(released) > parse_version(version) or not re.search(
                        rf'^## \[{re.escape(released)}\](?:\s|$)', log, re.M):
                    raise VersioningError(f'Version publiée incohérente : {path.name}')
            changes.append(Change(path, data['type'], data['summary'].strip(),
                                  data.get('breaking', False), released))
        return Project(root, version, tuple(changes), inputs)
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
        raise VersioningError('Structure du projet ou fragment invalide') from exc


def _pending(project: Project) -> tuple[Change, ...]:
    return tuple(item for item in project.changes if item.released_in is None)


def _next(project: Project) -> str | None:
    changes = _pending(project)
    if not changes:
        return None
    level = max(2 if item.breaking else LEVELS[POLICY[item.kind]] for item in changes)
    major, minor, patch = parse_version(project.version)
    return (f'{major + 1}.0.0' if level == 2 else
            f'{major}.{minor + 1}.0' if level == 1 else f'{major}.{minor}.{patch + 1}')


def preview(root: Path) -> dict:
    project = read_project(root)
    return {'current': project.version, 'next': _next(project),
            'changes': [{'type': item.kind, 'summary': item.summary, 'breaking': item.breaking}
                        for item in _pending(project)]}


def plan_release(root: Path, release_date: str) -> ReleasePlan:
    return _plan_release(read_project(root), release_date)


def _plan_release(project: Project, release_date: str) -> ReleasePlan:
    try:
        if date.fromisoformat(release_date).isoformat() != release_date:
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise VersioningError('Date de livraison requise au format AAAA-MM-JJ') from exc
    version = _next(project)
    if version is None:
        raise VersioningError('Aucun changement en attente')
    updates = {}
    for name, key in ((FILES[0], 'version'), (FILES[1], '__version__')):
        path = project.root / name
        text = project.inputs[path].decode('utf-8')
        updates[path] = re.sub(rf'(?m)^({key}\s*=\s*")[^"]+("\s*)$',
                               lambda match: match[1] + version + match[2], text).encode('utf-8')
    path = project.root / 'CHANGELOG.md'
    text = project.inputs[path].decode('utf-8')
    if re.search(rf'^## \[{re.escape(version)}\]', text, re.M):
        raise VersioningError('La version cible existe déjà dans CHANGELOG')
    notes = []
    for kind, title in TITLES.items():
        entries = [item for item in _pending(project) if item.kind == kind]
        if entries:
            notes += [f'### {title}', '']
            notes += [f'- {"**Incompatible :** " if item.breaking else ""}{item.summary}'
                      for item in entries]
            notes.append('')
    replacement = (f'## [Non publié]\n\n## [{version}] - {release_date}\n\n'
                   + '\n'.join(notes).rstrip() + '\n\n')
    updates[path] = re.sub(r'^## \[Non publié\]\s*$', lambda _: replacement,
                           text, count=1, flags=re.M).encode('utf-8')
    for item in _pending(project):
        old = project.inputs[item.path].decode('utf-8').rstrip('\r\n')
        updates[item.path] = (old + f'\nreleased_in = "{version}"\n').encode('utf-8')
    return ReleasePlan(project, version, updates)


def _assert_snapshot(plan: ReleasePlan, expected: dict[Path, bytes]) -> None:
    if set(plan.project.root.joinpath('changes').glob('*.toml')) != {
            item.path for item in plan.project.changes}:
        raise VersioningError('Les fragments ont été modifiés pendant la préparation')
    for path, data in expected.items():
        if _read(path) != data:
            raise VersioningError(f'Fichier modifié pendant la préparation : {path.name}')


def _stage(path: Path, data: bytes) -> Path:
    descriptor, name = tempfile.mkstemp(prefix='.release-', suffix='.tmp', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def apply_release(plan: ReleasePlan) -> None:
    allowed = {plan.project.root / name for name in FILES[:3]}
    allowed.update(item.path for item in _pending(plan.project))
    if set(plan.updates) != allowed:
        raise VersioningError('Le plan doit modifier uniquement les fichiers de livraison prévus')
    expected = dict(plan.project.inputs)
    _assert_snapshot(plan, expected)
    staged, backups, applied, keep = {}, {}, [], set()
    try:
        for path, data in plan.updates.items():
            staged[path] = _stage(path, data)
            backups[path] = _stage(path, expected[path])
            keep.add(backups[path])
        for path in plan.updates:
            _assert_snapshot(plan, expected)
            # Enregistrer la tentative avant l'appel système : un signal peut
            # arriver après replace mais avant la prochaine instruction Python.
            applied.append(path)
            os.replace(staged[path], path)
            expected[path] = plan.updates[path]
    except BaseException as exc:
        failures = []
        # Toute sauvegarde non restaurée doit survivre à une seconde interruption.
        keep.update(backups[path] for path in applied)
        keep.difference_update(backup for path, backup in backups.items() if path not in applied)
        for path in reversed(applied):
            try:
                # Ne pas écraser une modification tierce après notre écriture.
                current = _read(path)
                if current == plan.project.inputs[path]:
                    keep.discard(backups[path])
                    continue
                if current != plan.updates[path]:
                    raise VersioningError('Modification concurrente')
                os.replace(backups[path], path)
                keep.discard(backups[path])
            except (OSError, ValueError):
                keep.add(backups[path])
                failures.append(f'{path.name} : copie précédente dans {backups[path].name}')
        if failures:
            raise VersioningError('Restauration partielle; copies conservées : '
                                  + '; '.join(failures)) from exc
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        raise VersioningError('Préparation refusée; fichiers précédents restaurés') from exc
    else:
        # Point de validation : tous les fichiers de la version sont cohérents.
        keep.clear()
    finally:
        for temporary in (*staged.values(), *backups.values()):
            if temporary not in keep:
                temporary.unlink(missing_ok=True)


def _git(root: Path, *args: str) -> bytes:
    try:
        return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        raise VersioningError('Impossible de vérifier la référence Git demandée') from exc


def _release_relevant(name: str) -> bool:
    return (name.startswith(('src/', 'scripts/', '.github/workflows/'))
            or name in {'pyproject.toml', 'versioning.toml'})


def _require_repository(root: Path) -> None:
    top = Path(_git(root, 'rev-parse', '--show-toplevel').decode('utf-8').strip())
    if top.resolve() != root.resolve():
        raise VersioningError('La copie doit être la racine de son propre dépôt Git')


def validate(root: Path, *, base: str | None = None) -> None:
    project = read_project(root)
    if not base or base == '0' * 40:
        return
    if not re.fullmatch(r'[0-9a-f]{40}', base):
        raise VersioningError('La base doit être un identifiant de commit Git complet')
    _require_repository(root)
    old_project = _git(root, 'show', f'{base}:pyproject.toml').decode('utf-8')
    old_version = _version(old_project, 'version')
    paths = set(_git(root, 'diff', '--name-only', '-z', base, 'HEAD').decode('utf-8').split('\0'))
    if old_version == project.version:
        code_changed = any(_release_relevant(name) for name in paths)
        new_fragment = any(item.path.relative_to(project.root).as_posix() in paths
                           for item in _pending(project))
        if code_changed and not new_fragment:
            raise VersioningError('Un fragment de changement en attente est requis pour cette PR')
        return
    # Une PR de livraison doit reproduire la préparation de sa base, sans code ajouté.
    base_files = _git(root, 'ls-tree', '-r', '--name-only', base).decode('utf-8').splitlines()
    base_inputs = {project.root / name: _git(root, 'show', f'{base}:{name}') for name in (
        *FILES, *(n for n in base_files if re.fullmatch(r'changes/[^/]+\.toml', n)))}
    log = project.inputs[project.root / 'CHANGELOG.md'].decode('utf-8')
    match = re.search(rf'^## \[{re.escape(project.version)}\] - (\d{{4}}-\d{{2}}-\d{{2}})\r?$',
                      log, re.M)
    if match is None:
        raise VersioningError('Notes datées de la version manquantes')
    plan = _plan_release(_parse_project(project.root, base_inputs), match[1])
    if plan.version != project.version:
        raise VersioningError('Le numéro ne correspond pas aux changements de la base')
    for path, expected in plan.updates.items():
        if _read(path).replace(b'\r\n', b'\n') != expected.replace(b'\r\n', b'\n'):
            raise VersioningError('La livraison ne correspond pas au plan de sa base')
    allowed = {'pyproject.toml', 'src/gnu_astrolist/__init__.py', 'CHANGELOG.md'}
    if any(_release_relevant(name) and name not in allowed for name in paths):
        raise VersioningError('Séparer les changements de code de la PR de livraison')


def main(argv=None) -> int:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'preview', 'prepare'))
    parser.add_argument('--base', help='Commit de base complet pour le contrôle CI')
    parser.add_argument('--date', help='Date de livraison AAAA-MM-JJ')
    parser.add_argument('--apply', action='store_true', help='Appliquer la préparation locale')
    args = parser.parse_args(argv)
    try:
        if args.apply and args.command != 'prepare':
            raise VersioningError('--apply est réservé à prepare')
        if args.date and args.command != 'prepare' or args.base and args.command != 'check':
            raise VersioningError('Options incompatibles avec la commande choisie')
        if args.command == 'check':
            validate(ROOT, base=args.base)
            print('Politique, versions et fragments : OK')
        elif args.command == 'preview':
            print(json.dumps(preview(ROOT), ensure_ascii=False, indent=2))
        else:
            plan = plan_release(ROOT, args.date)
            if args.apply:
                _require_repository(ROOT)
                if _git(ROOT, 'status', '--porcelain', '--untracked-files=normal').strip():
                    raise VersioningError('Enregistrer les modifications avant préparation de version')
                apply_release(plan)
            print(f'{plan.project.version} -> {plan.version}; '
                  + ('préparé localement, aucun tag créé' if args.apply else 'aperçu sans écriture'))
        return 0
    except (ValueError, OSError) as exc:
        print(f'Version refusée : {exc}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
