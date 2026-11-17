# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Verrou OS du cache, réentrant par thread et libéré après arrêt brutal."""
from __future__ import annotations

import errno
import inspect
import math
import os
import stat
import threading
import time
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

LOCK_FILE = '.catalog.lock'
_registry_guard = threading.Lock()
_registry: dict[str, list] = {}


def _after_fork():
    global _registry_guard
    for entry in _registry.values():
        if entry[2] is not None:
            os.close(entry[2])
    _registry.clear()
    _registry_guard = threading.Lock()


if hasattr(os, 'register_at_fork'):
    os.register_at_fork(after_in_child=_after_fork)


def _os_lock(fd):
    if os.name == 'nt':
        import msvcrt
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _os_unlock(fd):
    if os.name == 'nt':
        import msvcrt
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_UN)


@contextmanager
def cache_lock(cache_dir: Path, seestar_root: Path | None = None, *, timeout: float = 120):
    """Sérialise la transaction entière; ne jamais supprimer le fichier de verrou.

    Le délai borné concerne l'attente, pas la durée de la transaction propriétaire.
    Les écrivains coopèrent dans un dossier local sous contrôle de l'utilisateur.
    """
    from .updates import _guard

    if not math.isfinite(timeout) or timeout < 0:
        raise ValueError('Lock timeout must be finite and nonnegative')
    cache_dir = Path(cache_dir)
    _guard(cache_dir, seestar_root)
    cache_dir.mkdir(parents=True, exist_ok=True)
    _guard(cache_dir, seestar_root)
    path = cache_dir.resolve() / LOCK_FILE
    key = os.path.normcase(str(path))
    with _registry_guard:
        entry = _registry.setdefault(key, [threading.RLock(), 0, None])
    deadline = time.monotonic() + timeout
    if not entry[0].acquire(timeout=timeout):
        raise TimeoutError('Cache lock timeout')
    fd = None
    entered = False
    try:
        if entry[1] == 0:
            _guard(path, seestar_root)
            if path.exists() and not stat.S_ISREG(path.lstat().st_mode):
                raise ValueError('Unsafe cache lock file')
            fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError('Unsafe cache lock file')
            _guard(path, seestar_root)
            if not os.path.samestat(info, path.stat()):
                raise ValueError('Cache lock identity changed')
            while True:
                try:
                    _os_lock(fd)
                    break
                except OSError as exc:
                    if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                        raise
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError('Cache lock timeout') from exc
                    time.sleep(min(.05, remaining))
            entry[2] = fd
            fd = None
        entry[1] += 1
        entered = True
        yield
    finally:
        try:
            if fd is not None:
                os.close(fd)
            if entered:
                entry[1] -= 1
                if entry[1] == 0:
                    held, entry[2] = entry[2], None
                    try:
                        _os_unlock(held)
                    finally:
                        os.close(held)
        finally:
            entry[0].release()


def cache_transaction(function):
    """Délimite la transaction; never/offline restent sans écriture ni verrou."""
    signature = inspect.signature(function)

    @wraps(function)
    def wrapped(*args, **kwargs):
        arguments = signature.bind(*args, **kwargs)
        arguments.apply_defaults()
        values = arguments.arguments
        if values['offline'] or values['mode'] not in {'if-stale', 'force'}:
            return function(*args, **kwargs)
        with cache_lock(values['cache_dir'], values['seestar_root']):
            return function(*args, **kwargs)

    return wrapped
