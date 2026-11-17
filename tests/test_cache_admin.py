# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Rétention de générations synthétiques, sans données ni cache personnels."""
import json
import os
from datetime import datetime, timezone

import pytest

from gnu_astrolist import cache_admin, updates
from gnu_astrolist.cache_lock import LOCK_FILE


@pytest.fixture
def cache(tmp_path, monkeypatch):
    root = tmp_path / 'controlled-cache'
    root.mkdir()
    monkeypatch.setattr(updates, '_baseline_count', lambda kind: 0)
    return root


def generation(cache, number, kind='bayer', corrupt=False):
    directory = cache / f'{kind}-20260101T000000{number:06}-{number:032x}'
    directory.mkdir()
    source = directory.parent.parent / 'synthetic-hyg.csv'
    source.write_text('id,ra,dec,mag,con,bayer,flam,proper\n'
                      '1,1,10,,And,Alp,1,Synthetic\n', encoding='utf-8')
    output = updates._build(kind, directory, lambda *args: source, '2026-01-01')
    metadata = {'schema_version': 1, 'kind': kind, 'retrieved_at':
                datetime(2026, 1, 1, 0, 0, number, tzinfo=timezone.utc).isoformat(),
                'sha256': updates._sha(output.read_bytes()), 'count': 1, 'sources': []}
    (directory / 'metadata.json').write_text(json.dumps(metadata), encoding='utf-8')
    if corrupt:
        output.write_bytes(b'invalid gzip')
    return directory


def test_dry_run_is_read_only_and_apply_keeps_real_valid(cache):
    old = generation(cache, 1)
    good = generation(cache, 2)
    bad = generation(cache, 3, corrupt=True)
    before = {p: p.read_bytes() for p in cache.rglob('*') if p.is_file()}
    result = cache_admin.retain_cache(cache, keep=1)
    assert set(result.remove) == {old, bad}
    assert result.kept == (good,)
    assert before == {p: p.read_bytes() for p in cache.rglob('*') if p.is_file()}
    assert not (cache / LOCK_FILE).exists()
    applied = cache_admin.retain_cache(cache, keep=1, apply=True)
    assert applied.remove == result.remove
    assert good.is_dir() and not old.exists() and not bad.exists()
    assert updates._validate('bayer', good / 'bayer.csv.gz') == 1


def test_families_and_keep(cache):
    for kind in ('bayer', 'flamsteed'):
        for number in range(1, 4):
            generation(cache, number, kind)
    result = cache_admin.retain_cache(cache, keep=2)
    assert len(result.kept) == 4 and len(result.remove) == 2
    for value in (0, -1, True, 1.5):
        with pytest.raises(ValueError):
            cache_admin.retain_cache(cache, keep=value, apply=True)


def test_no_valid_generation_refuses_entire_operation(cache):
    generation(cache, 1, corrupt=True)
    with pytest.raises(ValueError, match='valid'):
        cache_admin.retain_cache(cache, apply=True)
    assert len(list(cache.glob('bayer-*'))) == 1


@pytest.mark.parametrize('location', ['root', 'generation'])
def test_unknown_content_refuses_before_deletion(cache, location):
    old = generation(cache, 1)
    generation(cache, 2)
    parent = cache if location == 'root' else old
    (parent / 'unknown.txt').write_text('preserve')
    with pytest.raises(ValueError, match='Unknown'):
        cache_admin.retain_cache(cache, apply=True)
    assert old.exists() and (parent / 'unknown.txt').read_text() == 'preserve'


def test_hardlink_in_old_generation_refused(cache):
    old = generation(cache, 1)
    generation(cache, 2)
    target = old / 'bayer.csv.gz'
    os.link(target, cache.parent / 'outside.gz')
    with pytest.raises(ValueError, match='liens physiques'):
        cache_admin.retain_cache(cache, apply=True)
    assert target.exists()


def test_seestar_protection_before_lock(cache):
    generation(cache, 1)
    with pytest.raises(ValueError, match='Seestar'):
        cache_admin.retain_cache(cache, apply=True, seestar_root=cache.parent)
    assert not (cache / LOCK_FILE).exists()


def test_cli_requires_explicit_root_and_explicit_apply(cache, capsys):
    generation(cache, 1)
    old = generation(cache, 2)
    assert cache_admin.main(['--cache-dir', str(cache)]) == 0
    assert 'DRY RUN' in capsys.readouterr().out
    assert old.exists() and not (cache / LOCK_FILE).exists()
    assert cache_admin.main(['--cache-dir', str(cache), '--keep', '0']) == 2
    with pytest.raises(SystemExit):
        cache_admin.main([])


def test_reparse_refused_without_any_change(cache, monkeypatch):
    from pathlib import Path
    generation(cache, 1)
    original = Path.lstat

    class Reparse:
        st_mode = 0o40755
        st_file_attributes = 0x400

    def lstat(path, *args, **kwargs):
        return Reparse() if path == cache else original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'lstat', lstat)
    with pytest.raises(ValueError, match='jonction'):
        cache_admin.retain_cache(cache, apply=True)
    assert not (cache / LOCK_FILE).exists()


def test_symlink_refused(cache):
    old = generation(cache, 1)
    generation(cache, 2)
    target = cache.parent / 'outside'
    target.write_text('preserve')
    try:
        (old / 'source-unknown').symlink_to(target)
    except OSError:
        pytest.skip('Windows account cannot create symlinks')
    with pytest.raises(ValueError, match='lien'):
        cache_admin.retain_cache(cache, apply=True)
    assert target.read_text() == 'preserve' and old.exists()


def test_state_preserved_byte_for_byte(cache):
    generation(cache, 1)
    generation(cache, 2)
    state = cache / 'celestrak-state.json'
    content = b'{"blocked": true, "synthetic": "never reset by retention"}'
    state.write_bytes(content)
    cache_admin.retain_cache(cache, apply=True)
    assert state.read_bytes() == content


def test_unlisted_raw_response_is_unknown(cache):
    old = generation(cache, 1)
    generation(cache, 2)
    (old / ('source-' + 'a' * 64)).write_bytes(b'unknown')
    with pytest.raises(ValueError, match='Unknown'):
        cache_admin.retain_cache(cache, apply=True)
    assert old.exists()


def test_apply_waits_for_another_process(cache):
    import subprocess
    import sys
    from pathlib import Path

    from gnu_astrolist.cache_lock import cache_lock

    old = generation(cache, 1)
    generation(cache, 2)
    worker = '''
import sys
from pathlib import Path
from gnu_astrolist import cache_admin, updates
updates._baseline_count = lambda kind: 0
print('started', flush=True)
result = cache_admin.retain_cache(Path(sys.argv[1]), apply=True)
print(len(result.remove), flush=True)
'''
    env = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src')}
    process = None
    try:
        with cache_lock(cache):
            pending = cache / '.pending-abcd1234'
            pending.mkdir()
            process = subprocess.Popen([sys.executable, '-c', worker, str(cache)],
                                       env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True)
            assert process.stdout.readline().strip() == 'started'
            with pytest.raises(subprocess.TimeoutExpired):
                process.wait(timeout=.2)
            assert old.exists()
            pending.rmdir()
        out, err = process.communicate(timeout=15)
        assert process.returncode == 0, err
        assert out.strip() == '1' and not old.exists()
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.communicate(timeout=15)


@pytest.mark.parametrize('damage,value', [
    ('schema_version', True), ('count', True), ('count', 2),
    ('retrieved_at', '2999-01-01T00:00:00+00:00'),
    ('sources', {}), ('sources', [None]),
    ('sources', [{'url': []}]), ('sources', [{'url': 'synthetic', 'request_data': []}]),
])
def test_metadata_claim_does_not_replace_valid_generation(cache, damage, value):
    good = generation(cache, 1)
    bad = generation(cache, 2)
    manifest = bad / 'metadata.json'
    metadata = json.loads(manifest.read_text())
    metadata[damage] = value
    manifest.write_text(json.dumps(metadata))
    result = cache_admin.retain_cache(cache, apply=True)
    assert result.kept == (good,) and result.remove == (bad,)
    assert good.exists() and not bad.exists()


def test_relative_seestar_root_is_validated_before_any_write(cache, monkeypatch):
    from pathlib import Path

    generation(cache, 1)
    monkeypatch.chdir(cache.parent)
    with pytest.raises(ValueError, match='Seestar'):
        cache_admin.retain_cache(cache, apply=True, seestar_root=Path('.'))
    assert not (cache / LOCK_FILE).exists()


def test_abandoned_pending_refused_after_lock_without_deletion(cache):
    from gnu_astrolist.cache_lock import cache_lock

    old = generation(cache, 1)
    generation(cache, 2)
    with cache_lock(cache):
        pass
    pending = cache / '.pending-synthetic-review'
    pending.mkdir()
    with pytest.raises(ValueError, match='Unknown'):
        cache_admin.retain_cache(cache, apply=True)
    assert pending.exists() and old.exists()
