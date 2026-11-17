# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Réponses CelesTrak locales et transport simulé, jamais de réseau réel."""
import csv
import gzip
import io
import json
import urllib.error
from datetime import datetime, timedelta, timezone
from importlib import resources

import pytest

from gnu_astrolist import satellite_updates as satellite
from gnu_astrolist import updates


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Réseau réel interdit')
    monkeypatch.setattr(satellite.urllib.request, 'build_opener', forbidden)
    monkeypatch.setattr(satellite.urllib.request, 'urlopen', forbidden)


@pytest.fixture
def clock(monkeypatch):
    instant = [datetime(2026, 11, 20, 12, tzinfo=timezone.utc)]
    monkeypatch.setattr(satellite, '_now', lambda: instant[0])
    return instant


@pytest.fixture
def local_sources():
    # Réponses CSV de test reconstruites depuis les valeurs versionnées.
    # Ne dépend ni du répertoire local ignoré ni des octets d'une réponse future.
    payload=json.loads(gzip.decompress(resources.files('gnu_astrolist.data').joinpath(satellite.ARTIFACT).read_bytes()))
    debris={str(row['NORAD_CAT_ID']) for row in payload['satcat'] if row['OBJECT_TYPE']=='DEB'}
    result={}
    for url in satellite.SOURCE_URLS:
        category='gp' if '/NORAD/' in url else 'satcat'
        want_debris='cosmos-2251-debris' in url
        rows=[row for row in payload[category] if (str(row['NORAD_CAT_ID']) in debris)==want_debris]
        stream=io.StringIO(newline='')
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        result[url]=stream.getvalue().encode('utf-8')
    return result


@pytest.fixture
def fetch(monkeypatch, local_sources):
    calls = []
    def download(url):
        calls.append(url)
        return local_sources[url]
    monkeypatch.setattr(satellite, '_download', download)
    return calls


def unpack(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def test_bundled_validation_and_shared_registry(clock):
    assert updates._validate('satellites') == updates._validate('debris') == 737
    assert updates.CATALOG_REGISTRY['satellites'] == updates.CATALOG_REGISTRY['debris']
    payload = unpack(resources.files('gnu_astrolist.data').joinpath(satellite.ARTIFACT))
    assert len(payload['satcat']) == 1873
    assert {s['url'] for s in payload['sources']} == set(satellite.SOURCE_URLS)


@pytest.mark.parametrize('mode,offline', [('never', False), ('force', True), ('if-stale', True)])
def test_disabled_no_creation(tmp_path, clock, fetch, mode, offline):
    cache = tmp_path / 'absent'
    result = updates.refresh_catalogs(['satellites', 'debris'], mode, offline, cache)
    assert not cache.exists()
    assert not fetch
    assert not result.resources
    assert any('heure non connue' in note for note in result.notes)


def test_atomic_shared_generation_sources_and_epoch(tmp_path, clock, fetch, local_sources):
    result = updates.refresh_catalogs(['debris', 'satellites', 'debris'], 'force', cache_dir=tmp_path)
    assert fetch == list(satellite.SOURCE_URLS)
    assert list(result.resources) == [satellite.ARTIFACT]
    path = result.resources[satellite.ARTIFACT]
    assert path.parent.name.startswith('satellites-')
    payload = unpack(path)
    assert len(payload['gp']) == 737 and len(payload['satcat']) == 1873
    metadata = json.loads((path.parent / 'metadata.json').read_text())
    assert metadata['kind'] == 'satellites'
    assert metadata['sha256'] == updates._sha(path.read_bytes())
    assert metadata['sources'] == payload['sources']
    original = unpack(resources.files('gnu_astrolist.data').joinpath(satellite.ARTIFACT))
    assert {r['NORAD_CAT_ID']: r['EPOCH'] for r in payload['gp']} == {
        r['NORAD_CAT_ID']: r['EPOCH'] for r in original['gp']}
    for source in payload['sources']:
        assert source['retrieved_at'] == clock[0].isoformat()
        assert source['license']
        assert (path.parent / source['filename']).read_bytes() == local_sources[source['url']]
    assert not list(tmp_path.glob('.pending-*'))


def test_force_clamped_and_satcat_reused(tmp_path, clock, fetch):
    first = satellite.refresh_satellite_catalog('force', cache_dir=tmp_path)
    first_payload = unpack(first.resources[satellite.ARTIFACT])
    fetch.clear()
    clock[0] += timedelta(hours=1, minutes=59)
    second = satellite.refresh_satellite_catalog('force', cache_dir=tmp_path, max_age_hours=.01)
    assert second.resources == first.resources and not fetch
    clock[0] += timedelta(minutes=1)
    third = satellite.refresh_satellite_catalog('force', cache_dir=tmp_path)
    assert len(fetch) == 2 and all('/elements/gp.php?' in url for url in fetch)
    third_payload = unpack(third.resources[satellite.ARTIFACT])
    assert third_payload['satcat'] == first_payload['satcat']
    old_satcat = [s for s in first_payload['sources'] if not satellite._is_gp(s['url'])]
    assert [s for s in third_payload['sources'] if not satellite._is_gp(s['url'])] == old_satcat
    for source in old_satcat:
        assert (third.resources[satellite.ARTIFACT].parent / source['filename']).is_file()
    assert len(list(tmp_path.glob('satellites-*'))) == 2
    fetch.clear()
    clock[0] += timedelta(hours=22)
    satellite.refresh_satellite_catalog('force', cache_dir=tmp_path)
    assert fetch == list(satellite.SOURCE_URLS)


def test_min_selected_age_one_call_no_alias_shadow(tmp_path, clock, fetch):
    first = updates.refresh_catalogs(['satellites'], 'force', cache_dir=tmp_path)
    fetch.clear()
    clock[0] += timedelta(hours=3)
    second = updates.refresh_catalogs(['satellites', 'debris'], 'if-stale', cache_dir=tmp_path,
                                      max_age_hours={'satellites': 9, 'debris': 2, 'celestrak': 8})
    assert len(fetch) == 2
    assert second.resources != first.resources
    fetch.clear()
    # Une génération d'alias plus ancienne, triée après « satellites », reste ancienne.
    old = first.resources[satellite.ARTIFACT].parent
    alias = old.with_name('debris-zzzz')
    old.rename(alias)
    metadata_path = alias / 'metadata.json'
    info = json.loads(metadata_path.read_text())
    info['kind'] = 'debris'
    metadata_path.write_text(json.dumps(info))
    third = updates.refresh_catalogs(['debris'], 'if-stale', cache_dir=tmp_path)
    assert third.resources == second.resources and not fetch


@pytest.mark.parametrize('key', ['gp', 'celestrak'])
def test_provider_age_recognized_and_two_hour_minimum(tmp_path, clock, fetch, key):
    first = updates.refresh_catalogs(['debris'], 'force', cache_dir=tmp_path)
    fetch.clear()
    clock[0] += timedelta(hours=1)
    fresh = updates.refresh_catalogs(['debris'], 'if-stale', cache_dir=tmp_path,
                                     max_age_hours={key: .01})
    assert fresh.resources == first.resources and not fetch
    clock[0] += timedelta(hours=1)
    updates.refresh_catalogs(['debris'], 'if-stale', cache_dir=tmp_path,
                             max_age_hours={key: .01, 'satcat': .01})
    assert len(fetch) == 2


@pytest.mark.parametrize('status', [201, 301, 302, 403, 404, 429, 500, 503])
def test_first_non200_stops_provider_persistently(tmp_path, clock, monkeypatch, status):
    calls = []
    def fail(url):
        calls.append(url)
        raise urllib.error.HTTPError(url, status, 'simulated', {}, None)
    monkeypatch.setattr(satellite, '_download', fail)
    result = updates.refresh_catalogs(['satellites', 'debris'], 'force', cache_dir=tmp_path)
    assert len(calls) == 1 and not result.resources
    state = json.loads((tmp_path / satellite.STATE_FILE).read_text())
    assert state['status'] == status
    if 300 <= status < 500:
        assert state['blocked'] is True
        clock[0] += timedelta(days=10)
    else:
        assert satellite._timestamp(state['cooldown_until']) - clock[0] >= timedelta(minutes=15)
        clock[0] += timedelta(minutes=14)
    # Un autre type dans un autre appel partage exactement le même blocage.
    second = updates.refresh_catalogs(['debris'], 'force', cache_dir=tmp_path)
    assert len(calls) == 1
    assert any('inspection humaine' in note if 300 <= status < 500 else 'pause' in note
               for note in second.notes)


def test_second_request_failure_stops_remaining_urls(tmp_path, clock, local_sources, monkeypatch):
    calls = []
    def download(url):
        calls.append(url)
        if len(calls) == 2:
            raise urllib.error.HTTPError(url, 403, 'simulated', {}, None)
        return local_sources[url]
    monkeypatch.setattr(satellite, '_download', download)
    result = satellite.refresh_satellite_catalog('force', cache_dir=tmp_path)
    assert len(calls) == 2 and not result.resources
    assert not list(tmp_path.glob('satellites-*'))
    assert json.loads((tmp_path / satellite.STATE_FILE).read_text())['blocked']


def test_cooldown_recovery_still_respects_attempt_interval(tmp_path, clock, fetch, monkeypatch,
                                                         local_sources):
    def fail(url):
        raise urllib.error.HTTPError(url, 503, 'simulated', {}, None)
    monkeypatch.setattr(satellite, '_download', fail)
    satellite.refresh_satellite_catalog('force', cache_dir=tmp_path)
    monkeypatch.setattr(satellite, '_download', lambda url: fetch.append(url) or local_sources[url])
    clock[0] += timedelta(minutes=16)
    result = satellite.refresh_satellite_catalog('force', cache_dir=tmp_path)
    assert not fetch and any('délai minimal de 2 h' in note for note in result.notes)
    clock[0] += timedelta(hours=2)
    result = satellite.refresh_satellite_catalog('force', cache_dir=tmp_path)
    assert satellite.ARTIFACT in result.resources and len(fetch) == 4


@pytest.mark.parametrize('damage', ['crc', 'metadata', 'sha', 'future', 'join'])
def test_corrupt_generation_falls_back_to_older_valid(tmp_path, clock, fetch, damage):
    first = satellite.refresh_satellite_catalog('force', cache_dir=tmp_path)
    clock[0] += timedelta(hours=3)
    second = satellite.refresh_satellite_catalog('force', cache_dir=tmp_path)
    path = second.resources[satellite.ARTIFACT]
    manifest = path.parent / 'metadata.json'
    info = json.loads(manifest.read_text())
    if damage == 'crc':
        raw = bytearray(path.read_bytes())
        raw[-8] ^= 1
        path.write_bytes(raw)
        info['sha256'] = updates._sha(raw)
    elif damage == 'metadata':
        info['sources'] = []
    elif damage == 'sha':
        info['sha256'] = '0' * 64
    elif damage == 'future':
        info['retrieved_at'] = (clock[0] + timedelta(hours=1)).isoformat()
    else:
        payload = unpack(path)
        payload['satcat'][0]['OBJECT_ID'] = '2099-001A'
        path.write_bytes(gzip.compress(json.dumps(payload).encode()))
        info['sha256'] = updates._sha(path.read_bytes())
    manifest.write_text(json.dumps(info))
    fetch.clear()
    state_before = (tmp_path / satellite.STATE_FILE).read_bytes()
    fallback = satellite.refresh_satellite_catalog('force', True, tmp_path)
    assert fallback.resources == first.resources and not fetch
    assert any('non valide' in note for note in fallback.notes)
    assert state_before == (tmp_path / satellite.STATE_FILE).read_bytes()


def test_invalid_response_retains_good_copy(tmp_path, clock, fetch, monkeypatch):
    first = satellite.refresh_satellite_catalog('force', cache_dir=tmp_path)
    clock[0] += timedelta(hours=3)
    calls = []
    monkeypatch.setattr(satellite, '_download', lambda url: calls.append(url) or b'<html>bad</html>')
    result = satellite.refresh_satellite_catalog('force', cache_dir=tmp_path)
    assert len(calls) == 1 and result.resources == first.resources
    assert any('ancien cache valide' in note for note in result.notes)
    assert not list(tmp_path.glob('.pending-*'))


@pytest.mark.parametrize('status', [403, 503])
def test_http_failure_keeps_cache_and_offline_does_not_change_state(tmp_path, clock, fetch,
                                                                  monkeypatch, status):
    first = satellite.refresh_satellite_catalog('force', cache_dir=tmp_path)
    clock[0] += timedelta(hours=3)
    def fail(url):
        raise urllib.error.HTTPError(url, status, 'simulated', {}, None)
    monkeypatch.setattr(satellite, '_download', fail)
    failed = satellite.refresh_satellite_catalog('force', cache_dir=tmp_path)
    assert failed.resources == first.resources
    state_path = tmp_path / satellite.STATE_FILE
    state_before = state_path.read_bytes()
    offline = satellite.refresh_satellite_catalog('force', True, tmp_path)
    assert offline.resources == first.resources and state_path.read_bytes() == state_before


def test_exact_duplicates_only():
    a = {'NORAD_CAT_ID': '123', 'OBJECT_ID': '2000-001A'}
    assert satellite._merge([[a], [dict(a)]]) == [a]
    with pytest.raises(ValueError, match='contradictoire'):
        satellite._merge([[a], [{**a, 'OBJECT_ID': '2000-002A'}]])


def test_protected_root_and_state_before_writes(tmp_path, clock, fetch):
    protected = tmp_path / 'synthetic-seestar'
    protected.mkdir()
    with pytest.raises(ValueError, match='Seestar'):
        satellite.refresh_satellite_catalog('force', cache_dir=protected / 'cache',
                                             seestar_root=protected)
    assert not fetch and not list(protected.iterdir())


def test_corrupt_state_fails_closed_and_offline_ignores_it(tmp_path, clock, fetch):
    state = tmp_path / satellite.STATE_FILE
    state.write_text('corrupt')
    first = satellite.refresh_satellite_catalog('force', cache_dir=tmp_path)
    assert not fetch and not first.resources
    assert state.read_text() == 'corrupt'
    second = satellite.refresh_satellite_catalog('force', True, tmp_path)
    assert not fetch and not second.resources and state.read_text() == 'corrupt'


class Response(io.BytesIO):
    def __init__(self, content, status=200, encoding=''):
        super().__init__(content)
        self.status = status
        self.headers = {'Content-Encoding': encoding}


def transport(monkeypatch, response):
    calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append((request, timeout))
            return response
    handlers = []
    def build(handler):
        handlers.append(handler)
        return Opener()
    monkeypatch.setattr(satellite.urllib.request, 'build_opener', build)
    return calls, handlers


def test_transport_csv_gzip_headers_and_no_redirect(monkeypatch):
    calls, handlers = transport(monkeypatch, Response(gzip.compress(b'A,B\n1,2\n'), encoding='gzip'))
    assert satellite._download(satellite.SOURCE_URLS[0]) == b'A,B\n1,2\n'
    request, timeout = calls[0]
    assert request.get_header('Accept-encoding') == 'gzip'
    assert request.get_header('Accept') == 'text/csv'
    assert 'GNU-Astrolist/' in request.get_header('User-agent')
    assert 'contact:' in request.get_header('User-agent') and timeout == 30
    assert len(handlers) == 1 and isinstance(handlers[0], satellite._NoRedirect)
    assert handlers[0].redirect_request(None, None, 301, '', {}, 'https://example.invalid') is None


@pytest.mark.parametrize('status', [201, 301, 403, 404, 500, 503])
def test_transport_rejects_every_non200(monkeypatch, status):
    calls, _ = transport(monkeypatch, Response(b'body', status=status))
    with pytest.raises(urllib.error.HTTPError) as exc:
        satellite._download(satellite.SOURCE_URLS[0])
    assert exc.value.code == status and len(calls) == 1


def test_gzip_decompression_size_limit_and_crc(monkeypatch):
    monkeypatch.setattr(satellite, 'MAX_DOWNLOAD_BYTES', 100)
    transport(monkeypatch, Response(gzip.compress(b'x' * 101), encoding='gzip'))
    with pytest.raises(ValueError, match='décompression'):
        satellite._download(satellite.SOURCE_URLS[0])
    broken = bytearray(gzip.compress(b'x'))
    broken[-8] ^= 1
    transport(monkeypatch, Response(broken, encoding='gzip'))
    with pytest.raises(OSError):
        satellite._download(satellite.SOURCE_URLS[0])
