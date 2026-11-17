# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Deux points d'entrée réels, fournisseur synthétique et processus indépendants."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_WORKER = r'''
import csv, io, json, socket, sys, urllib.error
from datetime import datetime, timezone
from pathlib import Path
from gnu_astrolist import satellite_updates as satellite, updates
root, gate, entry, failure = Path(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4])
def forbidden(*args, **kwargs):
    raise AssertionError('No real network allowed')
socket.socket.connect = forbidden
socket.create_connection = forbidden
satellite.urllib.request.build_opener = forbidden
satellite._now = lambda: datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
satellite._check_population = lambda *args: None  # population entièrement synthétique
sources = json.loads((root.parent / 'synthetic-responses.json').read_text())
calls = []
def download(url):
    calls.append(url)
    with (root.parent / 'requests.txt').open('a') as stream:
        stream.write(url + '\n')
    if gate == 'wait' and len(calls) == 1:
        print('request', flush=True)
        sys.stdin.readline()
    if failure:
        raise urllib.error.HTTPError(url, failure, 'synthetic failure', {}, None)
    rows = sources['gp' if satellite._is_gp(url) else 'satcat']
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()
satellite._download = download
print('started', flush=True)
if entry == 'general':
    result = updates.refresh_catalogs(['satellites', 'debris'], 'force', cache_dir=root)
else:
    result = satellite.refresh_satellite_catalog('force', cache_dir=root)
print(json.dumps({'calls': len(calls), 'resources': {k: str(v) for k, v in result.resources.items()},
                  'notes': result.notes}), flush=True)
'''


@pytest.fixture
def synthetic_provider(tmp_path):
    # Orbite arbitraire valide pour le parseur, sans valeur observationnelle.
    gp = dict(OBJECT_NAME='SYNTHETIC', OBJECT_ID='2026-001A', NORAD_CAT_ID=1,
              EPOCH='2026-11-01T00:00:00', MEAN_MOTION=15, ECCENTRICITY=.001,
              INCLINATION=30, RA_OF_ASC_NODE=20, ARG_OF_PERICENTER=40, MEAN_ANOMALY=50,
              EPHEMERIS_TYPE=0, CLASSIFICATION_TYPE='U', ELEMENT_SET_NO=1,
              REV_AT_EPOCH=1, BSTAR=0, MEAN_MOTION_DOT=0, MEAN_MOTION_DDOT=0)
    satcat = dict(NORAD_CAT_ID=1, OBJECT_ID='2026-001A', OBJECT_NAME='SYNTHETIC',
                  OBJECT_TYPE='PAY', OWNER='', LAUNCH_DATE='', DECAY_DATE='',
                  ORBIT_CENTER='EA', ORBIT_TYPE='ORB')
    (tmp_path / 'synthetic-responses.json').write_text(
        json.dumps({'gp': [gp], 'satcat': [satcat]}), encoding='utf-8')
    return tmp_path / 'cache'


def launch(root, gate='go', entry='general', failure=0):
    return subprocess.Popen(
        [sys.executable, '-c', _WORKER, str(root), gate, entry, str(failure)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src')})


def finish(process, release=False):
    out, err = process.communicate('\n' if release else None, timeout=30)
    assert process.returncode == 0, err
    return json.loads(out.strip().splitlines()[-1])


def stop(process):
    if process.poll() is None:
        process.kill()
        process.communicate(timeout=15)


@pytest.mark.parametrize('failure', [0, 403, 503])
def test_shared_transaction_general_and_direct(synthetic_provider, failure):
    root = synthetic_provider
    first = launch(root, 'wait', 'general', failure)
    second = None
    try:
        assert first.stdout.readline().strip() == 'started'
        assert first.stdout.readline().strip() == 'request'
        second = launch(root, entry='direct')
        assert second.stdout.readline().strip() == 'started'
        left = finish(first, release=True)
        right = finish(second)
        assert left['calls'] == (4 if failure == 0 else 1)
        assert right['calls'] == 0
        assert left['resources'] == right['resources']
        assert len((root.parent / 'requests.txt').read_text().splitlines()) == left['calls']
        state = json.loads((root / 'celestrak-state.json').read_text())
        if failure == 403:
            assert state['blocked'] is True
        elif failure == 503:
            assert state['cooldown_until']
        else:
            assert len(list(root.glob('satellites-*'))) == 1
    finally:
        stop(first)
        if second:
            stop(second)


def test_killed_request_keeps_provider_interval(synthetic_provider):
    root = synthetic_provider
    first = launch(root, 'wait')
    try:
        assert first.stdout.readline().strip() == 'started'
        assert first.stdout.readline().strip() == 'request'
        first.kill()
        first.communicate(timeout=15)
        second = launch(root, entry='direct')
        try:
            result = finish(second)
            assert result['calls'] == 0 and not result['resources']
            assert any('2 h' in note for note in result['notes'])
            assert len((root.parent / 'requests.txt').read_text().splitlines()) == 1
        finally:
            stop(second)
    finally:
        stop(first)


def test_satellite_alias_retention_uses_payload_validation(synthetic_provider, monkeypatch):
    import gzip
    import shutil

    from gnu_astrolist import cache_admin, updates
    from gnu_astrolist import satellite_updates as satellite

    root = synthetic_provider
    worker = launch(root)
    try:
        created = finish(worker)
    finally:
        stop(worker)
    monkeypatch.setattr(satellite, '_check_population', lambda *args: None)
    first = Path(created['resources'][satellite.ARTIFACT]).parent
    alias = first.with_name('debris-' + first.name.split('-', 1)[1])
    shutil.copytree(first, alias)
    metadata = json.loads((alias / 'metadata.json').read_text())
    metadata.update(kind='debris', retrieved_at='2026-11-10T13:00:00+00:00')
    (alias / 'metadata.json').write_text(json.dumps(metadata))
    bad = first.with_name('satellites-20261110T140000000000-' + 'f' * 32)
    shutil.copytree(first, bad)
    payload = json.loads(gzip.decompress((bad / satellite.ARTIFACT).read_bytes()))
    payload['gp'][0]['OBJECT_ID'] = '2026-002A'  # jointure GP/SATCAT incorrecte
    artifact = bad / satellite.ARTIFACT
    artifact.write_bytes(gzip.compress(json.dumps(payload).encode()))
    metadata.update(kind='satellites', retrieved_at='2026-11-10T14:00:00+00:00',
                    sha256=updates._sha(artifact.read_bytes()))
    (bad / 'metadata.json').write_text(json.dumps(metadata))
    result = cache_admin.retain_cache(root, apply=True)
    assert result.kept == (alias,)
    assert set(result.remove) == {first, bad}
    assert satellite.validate_bundle(alias / satellite.ARTIFACT) == 1


_STELLAR_WORKER = r'''
import socket, sys
from pathlib import Path
from gnu_astrolist import updates
root = Path(sys.argv[1])
updates._baseline_count = lambda kind: 0
def forbidden(*args, **kwargs):
    raise AssertionError('No real network allowed')
socket.socket.connect = forbidden
socket.create_connection = forbidden
def download(*args):
    with (root.parent / 'stellar-requests.txt').open('a') as stream:
        stream.write('request\n')
    if sys.argv[2] == 'wait':
        print('request', flush=True)
        sys.stdin.readline()
    return b'id,ra,dec,mag,con,bayer,flam,proper\n1,1,10,,And,Alp,1,Synthetic\n'
updates._download = download
print('started', flush=True)
result = updates.refresh_catalogs(['bayer'], 'if-stale', cache_dir=root)
assert result.resources
'''


def test_stellar_if_stale_serializes_read_check_and_activation(tmp_path):
    root = tmp_path / 'cache'
    env = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src')}

    def start(gate):
        return subprocess.Popen([sys.executable, '-c', _STELLAR_WORKER, str(root), gate],
                                env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)

    first, second = start('wait'), None
    try:
        assert first.stdout.readline().strip() == 'started'
        assert first.stdout.readline().strip() == 'request'
        second = start('go')
        assert second.stdout.readline().strip() == 'started'
        for process, value in ((first, '\n'), (second, None)):
            _, err = process.communicate(value, timeout=30)
            assert process.returncode == 0, err
        assert (tmp_path / 'stellar-requests.txt').read_text().splitlines() == ['request']
        assert len(list(root.glob('bayer-*'))) == 1
    finally:
        stop(first)
        if second:
            stop(second)


@pytest.mark.parametrize('damage', ['missing-gp', 'undeclared-gp', 'missing-satcat'])
def test_missing_declared_response_cannot_displace_reconstructible_cache(
        synthetic_provider, monkeypatch, damage):
    import gzip
    import shutil

    from gnu_astrolist import cache_admin, updates
    from gnu_astrolist import satellite_updates as satellite

    root = synthetic_provider
    worker = launch(root)
    try:
        created = finish(worker)
    finally:
        stop(worker)
    monkeypatch.setattr(satellite, '_check_population', lambda *args: None)
    first = Path(created['resources'][satellite.ARTIFACT]).parent
    bad = first.with_name('satellites-20261110T140000000000-' + 'e' * 32)
    shutil.copytree(first, bad)
    artifact = bad / satellite.ARTIFACT
    payload = json.loads(gzip.decompress(artifact.read_bytes()))
    for source in payload['sources']:
        if satellite._is_gp(source['url']) == (damage != 'missing-satcat'):
            (bad / source['filename']).unlink()
            if damage == 'undeclared-gp':
                del source['filename']
    artifact.write_bytes(gzip.compress(json.dumps(payload).encode()))
    metadata = json.loads((bad / 'metadata.json').read_text())
    metadata.update(retrieved_at='2026-11-10T14:00:00+00:00', sources=payload['sources'],
                    sha256=updates._sha(artifact.read_bytes()))
    (bad / 'metadata.json').write_text(json.dumps(metadata))
    result = cache_admin.retain_cache(root, apply=True)
    assert result.kept == (first,) and result.remove == (bad,)
    assert first.exists() and not bad.exists()


def test_only_exact_bundled_satcat_can_omit_raw_response(synthetic_provider, monkeypatch):
    import copy
    import gzip

    from gnu_astrolist import cache_admin, updates
    from gnu_astrolist import satellite_updates as satellite

    root = synthetic_provider
    worker = launch(root)
    try:
        created = finish(worker)
    finally:
        stop(worker)
    monkeypatch.setattr(satellite, '_check_population', lambda *args: None)
    directory = Path(created['resources'][satellite.ARTIFACT]).parent
    artifact = directory / satellite.ARTIFACT
    payload = json.loads(gzip.decompress(artifact.read_bytes()))
    for source in payload['sources']:
        if not satellite._is_gp(source['url']):
            (directory / source['filename']).unlink()
            source.pop('filename')
            source.pop('retrieved_at')
            source['retrieved_on'] = '2026-11-09'
            source['file'] = 'synthetic-satcat.csv'
    bundled = copy.deepcopy(payload)
    original = satellite._read_bundle
    bundled_resource = satellite.resources.files('gnu_astrolist.data').joinpath(satellite.ARTIFACT)

    def read_bundle(resource):
        return bundled if resource == bundled_resource else original(resource)

    monkeypatch.setattr(satellite, '_read_bundle', read_bundle)
    artifact.write_bytes(gzip.compress(json.dumps(payload).encode()))
    manifest = directory / 'metadata.json'
    info = json.loads(manifest.read_text())
    info.update(sources=payload['sources'], sha256=updates._sha(artifact.read_bytes()))
    manifest.write_text(json.dumps(info))
    result = cache_admin.retain_cache(root)
    assert result.kept == (directory,) and not result.remove
    # Une fausse provenance documentaire ne suffit pas : comparaison exacte.
    for source in payload['sources']:
        if not satellite._is_gp(source['url']):
            source['sha256'] = '0' * 64
    artifact.write_bytes(gzip.compress(json.dumps(payload).encode()))
    info.update(sources=payload['sources'], sha256=updates._sha(artifact.read_bytes()))
    manifest.write_text(json.dumps(info))
    with pytest.raises(ValueError, match='No valid generation'):
        cache_admin.retain_cache(root, apply=True)
