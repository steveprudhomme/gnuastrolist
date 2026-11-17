# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Régressions du verrou OS sur caches synthétiques locaux."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

import pytest

from gnu_astrolist.cache_lock import LOCK_FILE, cache_lock


def child(cache, code, *arguments):
    return subprocess.Popen(
        [sys.executable, '-c', code, str(cache), *map(str, arguments)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src')},
    )


def test_reentrant_and_other_process_excluded(tmp_path):
    with cache_lock(tmp_path):
        with cache_lock(tmp_path):
            process = child(tmp_path, '''
import sys
from pathlib import Path
from gnu_astrolist.cache_lock import cache_lock
try:
    with cache_lock(Path(sys.argv[1]), timeout=.2):
        sys.exit(3)
except TimeoutError:
    print('excluded')
''')
            out, err = process.communicate(timeout=15)
            assert process.returncode == 0, err
            assert out.strip() == 'excluded'
    with cache_lock(tmp_path, timeout=.2):
        assert (tmp_path / LOCK_FILE).is_file()


def test_os_releases_after_termination(tmp_path):
    process = child(tmp_path, '''
import sys, time
from pathlib import Path
from gnu_astrolist.cache_lock import cache_lock
with cache_lock(Path(sys.argv[1])):
    print('locked', flush=True)
    time.sleep(60)
''')
    try:
        assert process.stdout.readline().strip() == 'locked'
        process.kill()
        process.communicate(timeout=15)
        with cache_lock(tmp_path, timeout=1):
            pass
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=15)


def test_linked_lock_refused(tmp_path):
    source = tmp_path / 'source'
    source.write_text('untouched')
    os.link(source, tmp_path / LOCK_FILE)
    with pytest.raises(ValueError, match='liens physiques'):
        with cache_lock(tmp_path):
            pytest.fail('unsafe lock acquired')
    assert source.read_text() == 'untouched'


def test_thread_timeout_and_recovery(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    def contender():
        with cache_lock(tmp_path, timeout=.05):
            return 'acquired'

    with ThreadPoolExecutor(max_workers=1) as pool:
        with cache_lock(tmp_path):
            future = pool.submit(contender)
            with pytest.raises(TimeoutError):
                future.result(timeout=5)
        assert pool.submit(contender).result(timeout=5) == 'acquired'


@pytest.mark.parametrize('timeout', [-1, float('inf'), float('nan')])
def test_invalid_timeout_does_not_create_cache(tmp_path, timeout):
    root = tmp_path / 'absent'
    with pytest.raises(ValueError):
        with cache_lock(root, timeout=timeout):
            pass
    assert not root.exists()


def test_exception_releases_nested_lock(tmp_path):
    with pytest.raises(RuntimeError):
        with cache_lock(tmp_path):
            with cache_lock(tmp_path):
                raise RuntimeError('synthetic interruption')
    process = child(tmp_path, '''
import sys
from pathlib import Path
from gnu_astrolist.cache_lock import cache_lock
with cache_lock(Path(sys.argv[1]), timeout=.2):
    print('released')
''')
    out, err = process.communicate(timeout=15)
    assert process.returncode == 0, err
    assert out.strip() == 'released'


@pytest.mark.skipif(os.name == 'nt', reason='fork is a POSIX primitive')
def test_fork_does_not_inherit_reentrancy(tmp_path):
    with cache_lock(tmp_path):
        pid = os.fork()
        if pid == 0:
            try:
                with cache_lock(tmp_path, timeout=.1):
                    os._exit(3)
            except TimeoutError:
                os._exit(0)
            except BaseException:
                os._exit(4)
        _, status = os.waitpid(pid, 0)
        assert os.waitstatus_to_exitcode(status) == 0


@pytest.mark.parametrize('error', [11, 5])
def test_os_lock_failure_releases_resources(tmp_path, monkeypatch, error):
    import errno

    from gnu_astrolist import cache_lock as locking

    def fail(fd):
        raise OSError(errno.EAGAIN if error == 11 else errno.EIO, 'synthetic OS failure')

    with monkeypatch.context() as patch:
        patch.setattr(locking, '_os_lock', fail)
        with pytest.raises(TimeoutError if error == 11 else OSError):
            with cache_lock(tmp_path, timeout=0):
                pytest.fail('failed lock entered')
    with cache_lock(tmp_path, timeout=.1):
        pass


@pytest.mark.parametrize('entry', ['general', 'satellite'])
@pytest.mark.parametrize('damage', ['mode', 'ages', 'kind'])
def test_invalid_refresh_does_not_create_lock_or_cache(tmp_path, entry, damage):
    from gnu_astrolist import satellite_updates, updates

    root = tmp_path / 'absent'
    kwargs = {'cache_dir': root, 'mode': 'force'}
    if damage == 'mode':
        kwargs['mode'] = 'invalid'
    elif damage == 'ages':
        kwargs['max_age_hours'] = {'unknown': 1}
    if entry == 'general':
        def action():
            return updates.refresh_catalogs(
                ['unknown' if damage == 'kind' else 'bayer'], **kwargs)
    else:
        if damage == 'kind':
            kwargs['max_age_hours'] = {'gp': float('nan')}
        def action():
            return satellite_updates.refresh_satellite_catalog(**kwargs)
    with pytest.raises((ValueError, argparse.ArgumentTypeError)):
        action()
    assert not root.exists()
