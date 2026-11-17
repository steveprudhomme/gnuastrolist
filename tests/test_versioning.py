# SPDX-FileCopyrightText: 2026 Steve Prud'Homme
# SPDX-License-Identifier: GPL-3.0-or-later
"""Versions et copies de dépôt synthétiques : aucun tag, réseau ou disque source."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import versioning as v

POLICY = '''schema_version = 1
scheme = "semver"
breaking = "major"
[types]
bug = "patch"
improvement = "minor"
feature = "minor"
'''


@pytest.fixture
def project(tmp_path):
    (tmp_path / 'changes').mkdir()
    (tmp_path / 'src/gnu_astrolist').mkdir(parents=True)
    (tmp_path / 'versioning.toml').write_text(POLICY, encoding='utf-8')
    (tmp_path / 'pyproject.toml').write_text(
        '[project]\nname = "gnu-astrolist"\nversion = "0.11.0"\n', encoding='utf-8')
    (tmp_path / 'src/gnu_astrolist/__init__.py').write_text(
        '__version__ = "0.11.0"\n', encoding='utf-8')
    (tmp_path / 'CHANGELOG.md').write_text(
        '# Changements\n\n## [Non publié]\n\nNotes historiques conservées.\n\n'
        '## [0.11.0] - 2026-08-03\n\nVersion antérieure.\n', encoding='utf-8')
    return tmp_path


def change(root, kind='bug', *, breaking=False, name='example', extra=''):
    path = root / 'changes' / f'{name}.toml'
    path.write_text(f'type = "{kind}"\nsummary = "Exemple public synthétique."\n'
                    f'breaking = {str(breaking).lower()}\n' + extra, encoding='utf-8')
    return path


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob('*') if p.is_file() and '.git' not in p.parts}


@pytest.mark.parametrize('kind,expected', [
    ('bug', '0.11.1'), ('improvement', '0.12.0'), ('feature', '0.12.0'),
])
def test_category_calculates_expected_version_without_writing(project, kind, expected):
    change(project, kind)
    before = snapshot(project)
    assert v.preview(project)['next'] == expected
    assert snapshot(project) == before


def test_highest_impact_and_breaking_marker_take_priority(project):
    change(project, 'bug', name='bug')
    change(project, 'feature', name='feature')
    assert v.preview(project)['next'] == '0.12.0'
    change(project, 'improvement', breaking=True, name='breaking')
    assert v.preview(project)['next'] == '1.0.0'


@pytest.mark.parametrize('version', ['01.2.3', '1.2', 'v1.2.3', '1.2.3.dev1', '-1.2.3', '1.2.3٤'])
def test_noncanonical_release_versions_are_rejected(version):
    with pytest.raises(v.VersioningError):
        v.parse_version(version)


@pytest.mark.parametrize('extra', ['breaking = "yes"\n', 'unknown = true\n',
                                   'released_in = "9.0.0"\n'])
def test_invalid_fragment_is_rejected(project, extra):
    path = change(project)
    text = path.read_text(encoding='utf-8')
    if extra.startswith('breaking'):
        text = text.replace('breaking = false\n', '')
    path.write_text(text + extra, encoding='utf-8')
    with pytest.raises(v.VersioningError):
        v.validate(project)


def test_prepare_synchronizes_versions_changelog_and_processed_fragments(project):
    fragment = change(project, 'improvement')
    before = snapshot(project)
    plan = v.plan_release(project, '2026-11-17')
    assert snapshot(project) == before
    v.apply_release(plan)
    assert 'version = "0.12.0"' in (project / 'pyproject.toml').read_text()
    assert '__version__ = "0.12.0"' in (project / 'src/gnu_astrolist/__init__.py').read_text()
    text = (project / 'CHANGELOG.md').read_text(encoding='utf-8')
    assert '## [Non publié]' in text and '## [0.12.0] - 2026-11-17' in text
    assert '### Amélioré' in text and 'Notes historiques conservées.' in text
    assert '## [0.11.0] - 2026-08-03' in text
    assert 'released_in = "0.12.0"' in fragment.read_text()
    v.validate(project)
    assert v.preview(project)['next'] is None
    with pytest.raises(v.VersioningError):
        v.plan_release(project, '2026-11-18')


def test_changed_input_aborts_without_overwriting_user_changes(project):
    fragment = change(project)
    plan = v.plan_release(project, '2026-11-17')
    fragment.write_text(fragment.read_text() + '# Modification utilisateur\n')
    before = snapshot(project)
    with pytest.raises(v.VersioningError, match='modifi'):
        v.apply_release(plan)
    assert snapshot(project) == before


def test_failed_publication_restores_all_previous_files(project, monkeypatch):
    change(project)
    before = snapshot(project)
    plan = v.plan_release(project, '2026-11-17')
    original = v.os.replace
    calls = []

    def fail_once(source, target):
        calls.append(target)
        if len(calls) == 2:
            raise OSError('Synthetic publication failure')
        return original(source, target)

    monkeypatch.setattr(v.os, 'replace', fail_once)
    with pytest.raises(v.VersioningError):
        v.apply_release(plan)
    assert snapshot(project) == before


def test_interrupt_restores_previous_files(project, monkeypatch):
    change(project)
    before = snapshot(project)
    plan = v.plan_release(project, '2026-11-17')
    original = v.os.replace
    calls = []

    def interrupted(source, target):
        calls.append(target)
        if len(calls) == 2:
            raise KeyboardInterrupt
        return original(source, target)

    monkeypatch.setattr(v.os, 'replace', interrupted)
    with pytest.raises(KeyboardInterrupt):
        v.apply_release(plan)
    assert snapshot(project) == before


def test_failed_rollback_keeps_original_backup(project, monkeypatch):
    change(project)
    original_bytes = (project / 'pyproject.toml').read_bytes()
    plan = v.plan_release(project, '2026-11-17')
    original = v.os.replace
    calls = []

    def failed_restore(source, target):
        calls.append(target)
        if len(calls) >= 2:
            raise OSError('Synthetic rollback failure')
        return original(source, target)

    monkeypatch.setattr(v.os, 'replace', failed_restore)
    with pytest.raises(v.VersioningError, match='copies conservées'):
        v.apply_release(plan)
    assert [p.read_bytes() for p in project.glob('.release-*.tmp')] == [original_bytes]


def test_interrupt_during_rollback_preserves_every_unrestored_backup(project, monkeypatch):
    change(project)
    plan = v.plan_release(project, '2026-11-17')
    originals = [plan.project.inputs[path] for path in list(plan.updates)[:2]]
    original = v.os.replace
    calls = []

    def interrupted_restore(source, target):
        calls.append(target)
        if len(calls) == 3:
            raise OSError('Synthetic publication failure')
        if len(calls) == 4:
            raise KeyboardInterrupt
        return original(source, target)

    monkeypatch.setattr(v.os, 'replace', interrupted_restore)
    with pytest.raises(KeyboardInterrupt):
        v.apply_release(plan)
    remaining = [p.read_bytes() for p in project.rglob('.release-*.tmp')]
    assert sorted(remaining) == sorted(originals)


def test_interrupt_immediately_after_replace_keeps_previous_version(project, monkeypatch):
    change(project)
    plan = v.plan_release(project, '2026-11-17')
    before = snapshot(project)
    original = v.os.replace
    calls = []

    def replace_then_interrupt(source, target):
        original(source, target)
        calls.append(target)
        if len(calls) == 1:
            raise KeyboardInterrupt

    monkeypatch.setattr(v.os, 'replace', replace_then_interrupt)
    with pytest.raises(KeyboardInterrupt):
        v.apply_release(plan)
    assert snapshot(project) == before


def test_hardlinked_source_is_refused_without_touching_its_alias(project):
    path = project / 'pyproject.toml'
    alias = project / 'alias.toml'
    try:
        os.link(path, alias)
    except OSError:
        pytest.skip('Liens physiques indisponibles')
    before = snapshot(project)
    with pytest.raises(v.VersioningError):
        v.plan_release(project, '2026-11-17')
    assert snapshot(project) == before


@pytest.mark.parametrize('value', ['2026-02-30', '20261117', None])
def test_invalid_date_does_not_write(project, value):
    change(project)
    before = snapshot(project)
    with pytest.raises(v.VersioningError):
        v.plan_release(project, value)
    assert snapshot(project) == before


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def commit_fixture(root):
    git(root, 'add', '.')
    git(root, '-c', 'user.name=GNU Astrolist synthetic tests',
        '-c', 'user.email=tests@example.invalid', '-c', 'commit.gpgsign=false',
        '-c', f'core.hooksPath={root / ".git/no-hooks"}',
        'commit', '-m', 'Synthetic fixture')
    return git(root, 'rev-parse', 'HEAD')


def test_ci_requires_new_pending_fragment_for_a_code_change(project):
    git(project, 'init')
    base = commit_fixture(project)
    (project / 'src/gnu_astrolist/example.py').write_text('VALUE = 1\n')
    commit_fixture(project)
    with pytest.raises(v.VersioningError, match='fragment'):
        v.validate(project, base=base)
    change(project, 'feature')
    commit_fixture(project)
    v.validate(project, base=base)


def test_ci_accepts_prepared_release_and_rejects_unexplained_bump(project):
    change(project, 'feature')
    git(project, 'init')
    base = commit_fixture(project)
    v.apply_release(v.plan_release(project, '2026-11-17'))
    commit_fixture(project)
    before = snapshot(project)
    v.validate(project, base=base)
    assert snapshot(project) == before
    path = project / 'pyproject.toml'
    path.write_text(path.read_text().replace('0.12.0', '0.13.0'))
    (project / 'src/gnu_astrolist/__init__.py').write_text('__version__ = "0.13.0"\n')
    commit_fixture(project)
    with pytest.raises(v.VersioningError):
        v.validate(project, base=base)


def test_cli_preview_is_machine_readable_and_no_apply_by_default(project, monkeypatch, capsys):
    change(project, 'feature')
    monkeypatch.setattr(v, 'ROOT', project)
    before = snapshot(project)
    assert v.main(['preview']) == 0
    assert json.loads(capsys.readouterr().out)['next'] == '0.12.0'
    assert v.main(['prepare', '--date', '2026-11-17']) == 0
    assert snapshot(project) == before


@pytest.mark.parametrize('kind,breaking,expected', [
    ('bug', False, '1.2.10'), ('improvement', False, '1.3.0'), ('feature', True, '2.0.0'),
])
def test_stable_versions_increment_and_reset_components(project, kind, breaking, expected):
    for name in ('pyproject.toml', 'src/gnu_astrolist/__init__.py', 'CHANGELOG.md'):
        path = project / name
        path.write_text(path.read_text().replace('0.11.0', '1.2.9'))
    change(project, kind, breaking=breaking)
    assert v.preview(project)['next'] == expected


@pytest.mark.parametrize('fault', ['policy', 'mismatch', 'missing_unreleased', 'duplicate_target'])
def test_bad_project_state_is_rejected_without_writing(project, fault):
    change(project, 'feature')
    if fault == 'policy':
        path = project / 'versioning.toml'
        path.write_text(POLICY.replace('bug = "patch"', 'bug = "major"'))
    elif fault == 'mismatch':
        (project / 'src/gnu_astrolist/__init__.py').write_text('__version__ = "1.0.0"\n')
    else:
        path = project / 'CHANGELOG.md'
        text = path.read_text(encoding='utf-8')
        text = (text.replace('## [Non publié]', '## Autre') if fault == 'missing_unreleased'
                else text + '\n## [0.12.0] - 2026-11-17\n')
        path.write_text(text, encoding='utf-8')
    before = snapshot(project)
    with pytest.raises(v.VersioningError):
        v.plan_release(project, '2026-11-17')
    assert snapshot(project) == before


def test_new_fragment_after_planning_aborts(project):
    change(project)
    plan = v.plan_release(project, '2026-11-17')
    change(project, 'feature', name='added')
    before = snapshot(project)
    with pytest.raises(v.VersioningError, match='modifi'):
        v.apply_release(plan)
    assert snapshot(project) == before


def test_tampered_plan_cannot_write_to_an_unplanned_file(project):
    change(project)
    plan = v.plan_release(project, '2026-11-17')
    target = project / 'unrelated.txt'
    plan.updates[target] = b'Unexpected output'
    before = snapshot(project)
    with pytest.raises(v.VersioningError, match='uniquement'):
        v.apply_release(plan)
    assert snapshot(project) == before and not target.exists()


def test_staging_failure_leaves_all_files_unchanged(project, monkeypatch):
    change(project)
    plan = v.plan_release(project, '2026-11-17')
    before = snapshot(project)
    def failed_sync(fd):
        raise OSError('Synthetic staging failure')

    monkeypatch.setattr(v.os, 'fsync', failed_sync)
    with pytest.raises(v.VersioningError):
        v.apply_release(plan)
    assert snapshot(project) == before


def test_cli_apply_requires_clean_copy_then_prepares_without_tag(project, monkeypatch, capsys):
    change(project, 'feature')
    git(project, 'init')
    commit_fixture(project)
    monkeypatch.setattr(v, 'ROOT', project)
    extra = project / 'uncommitted.txt'
    extra.write_text('Synthetic uncommitted work')
    before = snapshot(project)
    assert v.main(['prepare', '--date', '2026-11-17', '--apply']) == 2
    assert snapshot(project) == before
    commit_fixture(project)
    assert v.main(['prepare', '--date', '2026-11-17', '--apply']) == 0
    assert git(project, 'tag', '--list') == ''
    assert '0.12.0' in (project / 'pyproject.toml').read_text()
    assert 'aucun tag' in capsys.readouterr().out


def test_apply_refuses_source_copy_inside_another_repository(project, monkeypatch):
    change(project, 'feature')
    git(project, 'init')
    commit_fixture(project)
    nested = project / 'nested-copy'
    for name, data in snapshot(project).items():
        target = nested / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    monkeypatch.setattr(v, 'ROOT', nested)
    before = snapshot(project)
    assert v.main(['prepare', '--date', '2026-11-17', '--apply']) == 2
    assert snapshot(project) == before


@pytest.mark.parametrize('extra_path', ['src/gnu_astrolist/extra.py',
                                        '.github/workflows/quality.yml', 'versioning.toml'])
def test_ci_rejects_runtime_code_added_to_release_preparation(project, extra_path):
    change(project, 'feature')
    git(project, 'init')
    base = commit_fixture(project)
    v.apply_release(v.plan_release(project, '2026-11-17'))
    path = project / extra_path
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.write_text(path.read_text() + '\n# Synthetic unrelated change\n')
    else:
        path.write_text('# Synthetic unrelated change\n')
    commit_fixture(project)
    with pytest.raises(v.VersioningError, match='Séparer'):
        v.validate(project, base=base)


@pytest.mark.parametrize('command', [
    ['preview', '--apply'], ['check', '--date', '2026-11-17'], ['preview', '--base', '0' * 40],
])
def test_cli_rejects_options_for_wrong_command(project, monkeypatch, command):
    monkeypatch.setattr(v, 'ROOT', project)
    before = snapshot(project)
    assert v.main(command) == 2
    assert snapshot(project) == before


def test_script_entry_point_is_usable_without_installed_application(project):
    change(project, 'feature')
    scripts = project / 'scripts'
    scripts.mkdir()
    source = Path(__file__).parents[1] / 'scripts'
    for name in ('versioning.py', '_local_output.py'):
        (scripts / name).write_bytes((source / name).read_bytes())
    before = snapshot(project)
    result = subprocess.run([sys.executable, '-B', str(scripts / 'versioning.py'), 'preview'],
                            capture_output=True, text=True, encoding='utf-8', check=True, cwd=project)
    assert json.loads(result.stdout)['next'] == '0.12.0'
    assert snapshot(project) == before
