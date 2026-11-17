# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Mises à jour simulées : aucun test ne contacte de service distant."""
import argparse
import csv
import gzip
import io
import json
from importlib import resources
from pathlib import Path

import pytest

from gnu_astrolist import catalog, seestar, updates
from gnu_astrolist.catalog_resources import catalog_resource, use_catalog_resources


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Réseau interdit dans les tests')
    monkeypatch.setattr(updates.urllib.request, 'urlopen', forbidden)


@pytest.fixture
def successful_builder(monkeypatch):
    calls = []

    def build(kind, directory, fetch, retrieved_on):
        calls.append(kind)
        spec = updates.CATALOG_REGISTRY[kind]
        fetch(spec.sources[0], 'https://example.invalid/shared')
        output = directory / spec.filename
        content = resources.files('gnu_astrolist.data').joinpath(spec.filename).read_bytes()
        if kind == 'variable_stars':
            # Données de transport synthétiques : identifiants uniques pour
            # ne pas réutiliser les doublons du catalogue historique.
            reader = csv.DictReader(io.StringIO(gzip.decompress(content).decode('utf-8')))
            stream = io.StringIO()
            writer = csv.DictWriter(stream, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows({**row, 'name': f'SYNTHETIC {n}'}
                             for n, row in enumerate(reader))
            content = gzip.compress(stream.getvalue().encode('utf-8'))
        output.write_bytes(content)
        return output

    monkeypatch.setattr(updates, '_download', lambda *args: b'synthetic source')
    monkeypatch.setattr(updates, '_build', build)
    return calls


@pytest.mark.parametrize('mode,offline', [('never', False), ('force', True), ('if-stale', True)])
def test_no_network_or_cache_creation(tmp_path, mode, offline):
    cache = tmp_path / 'absent'
    result = updates.refresh_catalogs(updates.CATALOG_REGISTRY, mode, offline, cache)
    assert not cache.exists()
    assert result.resources == {}
    # Les deux sélections satellitaires partagent une seule génération et une note.
    assert len(result.notes) == len(updates.CATALOG_REGISTRY)-1


@pytest.mark.parametrize('kind', [kind for kind in updates.CATALOG_REGISTRY
                                 if kind not in {'satellites','debris'}])
def test_generation_metadata_and_offline_reuse(tmp_path, successful_builder, kind):
    first = updates.refresh_catalogs([kind], 'force', cache_dir=tmp_path)
    filename = updates.CATALOG_REGISTRY[kind].filename
    assert filename in first.resources
    path = first.resources[filename]
    metadata = json.loads((path.parent / 'metadata.json').read_text(encoding='utf-8'))
    assert metadata['sha256'] == updates._sha(path.read_bytes())
    assert metadata['count'] > 0
    assert metadata['sources'][0]['retrieved_at']
    assert metadata['sources'][0]['license']
    assert (path.parent / metadata['sources'][0]['filename']).read_bytes() == b'synthetic source'
    assert not list(tmp_path.glob('.pending-*'))
    second = updates.refresh_catalogs([kind], 'force', True, tmp_path)
    assert second.resources == first.resources
    assert successful_builder == [kind]


def test_age_per_source_and_shared_download(tmp_path, monkeypatch, successful_builder):
    downloads = []
    monkeypatch.setattr(updates, '_download', lambda *args: downloads.append(args) or b'source')
    result = updates.refresh_catalogs(['messier', 'caldwell', 'messier'], 'force', cache_dir=tmp_path)
    assert len(downloads) == 1
    assert successful_builder == ['messier', 'caldwell']
    updates.refresh_catalogs(['messier'], 'if-stale', cache_dir=tmp_path)
    assert successful_builder == ['messier', 'caldwell']
    path = result.resources['messier.csv.gz'].parent / 'metadata.json'
    info = json.loads(path.read_text(encoding='utf-8'))
    info['retrieved_at'] = '2000-01-01T00:00:00+00:00'
    path.write_text(json.dumps(info), encoding='utf-8')
    updates.refresh_catalogs(['messier'], 'if-stale', cache_dir=tmp_path,
                             max_age_hours={'messier': 1e9, 'simbad': 1})
    assert successful_builder == ['messier', 'caldwell', 'messier']


def test_failure_fallback_and_hash_corruption(tmp_path, monkeypatch, successful_builder):
    first = updates.refresh_catalogs(['bayer'], 'force', cache_dir=tmp_path)
    second = updates.refresh_catalogs(['bayer'], 'force', cache_dir=tmp_path)
    second.resources['bayer.csv.gz'].write_bytes(b'truncated')

    def unavailable(*args):
        raise OSError('synthetic outage')
    monkeypatch.setattr(updates, '_download', unavailable)
    fallback = updates.refresh_catalogs(['bayer'], 'force', cache_dir=tmp_path)
    assert fallback.resources == first.resources
    assert any('ancien cache valide' in note for note in fallback.notes)
    assert any('non valide' in note for note in fallback.notes)
    first.resources['bayer.csv.gz'].write_bytes(b'truncated')
    bundled = updates.refresh_catalogs(['bayer'], 'force', cache_dir=tmp_path)
    assert bundled.resources == {}
    assert any('embarquée' in note for note in bundled.notes)


@pytest.mark.parametrize('value', ['nan', 'inf', '-inf', '0', '-1', 'oops'])
def test_invalid_age(value, tmp_path):
    with pytest.raises(argparse.ArgumentTypeError):
        updates.parse_max_age_hours(value)
    with pytest.raises(ValueError):
        updates.refresh_catalogs(['bayer'], cache_dir=tmp_path, max_age_hours={'hyg': value})


def test_invalid_configuration(tmp_path):
    assert updates.parse_max_age_hours('1.5') == 1.5
    for kwargs in ({'mode': 'always'}, {'max_age_hours': {'unknown': 24}}):
        with pytest.raises(ValueError):
            updates.refresh_catalogs(['bayer'], cache_dir=tmp_path, **kwargs)
    with pytest.raises(ValueError):
        updates.refresh_catalogs(['cbat'], cache_dir=tmp_path)


def test_protect_before_any_write_or_download(tmp_path, monkeypatch):
    source = tmp_path / 'synthetic-seestar'
    source.mkdir()
    cache = source / 'cache'
    with pytest.raises(ValueError, match='Seestar'):
        updates.refresh_catalogs(['bayer'], 'force', cache_dir=cache, seestar_root=source)
    assert list(source.iterdir()) == []
    calls = []
    def protected(root, outputs):
        calls.append(outputs)
        raise ValueError('synthetic whole disk protection')
    monkeypatch.setattr(updates, 'protect_outputs', protected)
    with pytest.raises(ValueError, match='whole disk'):
        updates.refresh_catalogs(['bayer'], 'force', cache_dir=tmp_path / 'cache',
                                 seestar_root=source)
    assert calls
    assert not (tmp_path / 'cache').exists()


def test_reparse_directory_is_rejected(tmp_path, monkeypatch):
    original = Path.lstat
    class Junction:
        st_mode = 0o40755
        st_file_attributes = 0x400
    def lstat(path, *args, **kwargs):
        return Junction() if path == tmp_path else original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'lstat', lstat)
    with pytest.raises(ValueError, match='jonction'):
        updates.refresh_catalogs(['bayer'], 'force', cache_dir=tmp_path / 'cache')


def test_overrides_clear_lru_and_aliases_on_entry_exit(tmp_path):
    original = catalog.load_messier_catalog()
    seestar._known_aliases()
    path = tmp_path / 'messier.csv.gz'
    raw = resources.files('gnu_astrolist.data').joinpath(path.name).read_bytes()
    text = gzip.decompress(raw).decode('utf-8').replace('M1,', 'SYNTHETIC,', 1)
    path.write_bytes(gzip.compress(text.encode('utf-8')))
    with pytest.raises(RuntimeError):
        with use_catalog_resources({path.name: path}):
            assert seestar._known_aliases.cache_info().currsize == 0
            assert catalog.load_messier_catalog()[0].name == 'SYNTHETIC'
            with use_catalog_resources({}):
                assert catalog.load_messier_catalog()[0].name == 'M1'
            assert catalog.load_messier_catalog()[0].name == 'SYNTHETIC'
            raise RuntimeError('synthetic error')
    assert catalog.load_messier_catalog() == original
    assert catalog_resource(path.name) != path
    assert seestar._known_aliases.cache_info().currsize == 0


def test_real_caldwell_builder_with_mock_downloads(tmp_path, monkeypatch):
    fields = ['Name', 'Type', 'RA', 'Dec', 'Const', 'MajAx', 'MinAx', 'V-Mag', 'Common names']
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields, delimiter=';')
    writer.writeheader()
    for name in updates.caldwell.DESIGNATIONS:
        writer.writerow(dict(zip(fields, [name, 'G', '00:00:00', '+10:00:00', 'And',
                                          '1', '1', '', 'Synthetic'])))
    ngc = stream.getvalue().encode('utf-8')
    seen = []
    def download(url, data=None):
        seen.append(url)
        if url == updates.messier.NGC_SOURCE_URL:
            return ngc
        if url == updates.messier.ADDENDUM_SOURCE_URL:
            return (';'.join(fields) + '\n').encode('utf-8')
        return b'id,flux,bibcode,qual,system\nNGC 188,7.5,SYNTHETIC,A,V\n'
    monkeypatch.setattr(updates, '_download', download)
    result = updates.refresh_catalogs(['caldwell'], 'force', cache_dir=tmp_path)
    assert 'caldwell.csv.gz' in result.resources
    with use_catalog_resources(result.resources):
        objects = catalog.load_caldwell_catalog()
        assert len(objects) == 109
        assert objects[0].magnitude_v == 7.5
        assert objects[1].magnitude_v is None
    assert len(seen) == 3


@pytest.mark.parametrize('damage', ['count', 'nan', 'duplicate', 'coordinates', 'band'])
def test_invalid_generation_never_published(tmp_path, monkeypatch, damage):
    def build(kind, directory, fetch, retrieved_on):
        output = directory / 'ngc.csv.gz'
        raw = resources.files('gnu_astrolist.data').joinpath(output.name).read_bytes()
        reader = csv.DictReader(io.StringIO(gzip.decompress(raw).decode('utf-8')))
        fields = reader.fieldnames
        rows = list(reader)
        if damage == 'count':
            rows = rows[:10]
        elif damage == 'nan':
            rows[0]['magnitude_v'] = 'nan'
        elif damage == 'duplicate':
            rows[0]['name'] = rows[1]['name']
        elif damage == 'coordinates':
            rows[0]['ra_deg'] = '360'
        else:
            rows[0]['passband'] = 'B'
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        output.write_bytes(gzip.compress(stream.getvalue().encode('utf-8')))
        return output
    monkeypatch.setattr(updates, '_build', build)
    result = updates.refresh_catalogs(['ngc'], 'force', cache_dir=tmp_path)
    assert result.resources == {}
    assert not list(tmp_path.glob('ngc-*'))
    assert not list(tmp_path.glob('.pending-*'))


def test_downloader_limits_timeout_and_identity(monkeypatch):
    captured = []
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self, limit):
            captured.append(limit)
            return b'X' * (updates.MAX_DOWNLOAD_BYTES + 1)
    def urlopen(request, timeout):
        assert timeout == 30
        assert updates.__version__ in request.get_header('User-agent')
        assert 'https://' in request.get_header('User-agent')
        return Response()
    monkeypatch.setattr(updates.urllib.request, 'urlopen', urlopen)
    with pytest.raises(ValueError, match='50 Mio'):
        updates._download('https://example.invalid/catalog')
    assert captured == [50 * 1024 * 1024 + 1]

@pytest.mark.parametrize('kind', ['variable_stars', 'bayer', 'flamsteed', 'asteroids', 'comets'])
def test_real_builders_accept_synthetic_sources(tmp_path, kind):
    if kind == 'variable_stars':
        fields = [''] * 21
        fields[1] = 'SYNTHETIC And'
        fields[2] = '000000.0 +100000'
        fields[3] = 'SR'
        fields[4] = '5.5'
        fields[7] = 'V'
        fields[20] = 'SYNTHETIC And'
        content = gzip.compress(('|'.join(fields) + '\n').encode('ascii'))
    elif kind in {'bayer', 'flamsteed'}:
        content = (b'id,ra,dec,mag,con,bayer,flam,proper\n'
                   b'1,1,10,,And,Alp,1,Synthetic\n')
    elif kind == 'asteroids':
        payload = {
            'signature': {'version': '1.0'},
            'fields': ['pdes', 'name', 'epoch', 'equinox', 'a', 'e', 'i', 'om', 'w',
                       'ma', 'H', 'G', 'orbit_id'],
            'data': [['1', 'Synthetic', '2461200.5', 'J2000', '2', '.1', '10', '20',
                      '30', '40', None, None, 'synthetic']],
        }
        content = json.dumps(payload).encode('ascii')
    else:
        row = [' '] * 180
        def put(start, end, value):
            row[start:end] = value.ljust(end - start)
        put(0, 5, '0001P')
        put(14, 18, '2026')
        put(19, 21, '01')
        put(22, 29, '01.000')
        for start, end, value in [(30, 39, '1.0'), (41, 49, '0.1'), (51, 59, '10'),
                                  (61, 69, '20'), (71, 79, '30')]:
            put(start, end, value)
        put(81, 89, '20260101')
        put(102, 158, '1P/Synthetic')
        content = ''.join(row).encode('ascii')
    source = tmp_path / 'synthetic-source'
    source.write_bytes(content)
    output = updates._build(kind, tmp_path, lambda *args: source, '2000-01-01')
    assert updates._validate(kind, output) == 1
    if kind == 'variable_stars':
        with use_catalog_resources({output.name: output}):
            assert catalog.load_variable_star_catalog()[0].name == 'SYNTHETIC And'
    elif kind in {'bayer', 'flamsteed'}:
        with use_catalog_resources({output.name: output}):
            assert catalog._load_named_stars(kind)[0].magnitude_v is None


def test_real_messier_builder_all_numbers_and_missing_v(tmp_path, monkeypatch):
    fields = ['Name', 'Type', 'RA', 'Dec', 'Const', 'MajAx', 'MinAx', 'V-Mag',
              'Common names', 'M']
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields, delimiter=';')
    writer.writeheader()
    for number in range(1, 111):
        designation = 'NGC5866' if number == 102 else f'NGC{number:04}'
        writer.writerow(dict(zip(fields, [designation, 'G', '00:00:00', '+10:00:00', 'And',
                                          '1', '1', '', 'Synthetic', str(number)])))
    ngc = stream.getvalue().encode('utf-8')
    response = io.StringIO()
    writer = csv.DictWriter(response, fieldnames=[
        'id', 'main_id', 'galdim_majaxis', 'galdim_minaxis', 'galdim_bibcode',
        'vmag', 'vmag_bibcode', 'vmag_quality', 'vmag_system',
    ])
    writer.writeheader()
    for number in range(1, 111):
        writer.writerow({'id': f'M {number}', 'main_id': 'Synthetic'})
    def download(url, data=None):
        if url == updates.messier.NGC_SOURCE_URL:
            return ngc
        if url == updates.messier.ADDENDUM_SOURCE_URL:
            return (';'.join(fields) + '\n').encode('utf-8')
        return response.getvalue().encode('utf-8')
    monkeypatch.setattr(updates, '_download', download)
    result = updates.refresh_catalogs(['messier'], 'force', cache_dir=tmp_path)
    assert result.resources
    with use_catalog_resources(result.resources):
        objects = catalog.load_messier_catalog()
        assert len(objects) == 110
        assert all(obj.magnitude_v is None for obj in objects)


def test_failed_shared_source_is_not_retried(tmp_path, monkeypatch):
    seen = []
    def unavailable(url, data=None):
        seen.append(url)
        raise OSError('synthetic outage')
    monkeypatch.setattr(updates, '_download', unavailable)
    result = updates.refresh_catalogs(['messier', 'caldwell', 'ngc'], 'force', cache_dir=tmp_path)
    assert not result.resources
    assert len(seen) == 1


def test_truncated_http_response_falls_back(tmp_path, monkeypatch):
    import http.client
    def incomplete(*args):
        raise http.client.IncompleteRead(b'synthetic truncated response')
    monkeypatch.setattr(updates, '_download', incomplete)
    result = updates.refresh_catalogs(['asteroids'], 'force', cache_dir=tmp_path)
    assert not result.resources
    assert 'embarquée' in result.notes[0]

@pytest.mark.parametrize('kind', ['variable_stars', 'bayer', 'flamsteed'])
def test_cached_provenance_date_and_notes(tmp_path, successful_builder, kind):
    result = updates.refresh_catalogs([kind], 'force', cache_dir=tmp_path)
    path = next(iter(result.resources.values()))
    manifest = path.parent / 'metadata.json'
    info = json.loads(manifest.read_text(encoding='utf-8'))
    info['retrieved_at'] = '2001-02-03T04:05:06+00:00'
    manifest.write_text(json.dumps(info), encoding='utf-8')
    from gnu_astrolist.catalog_resources import catalog_retrieved_on
    with use_catalog_resources(result.resources):
        assert catalog_retrieved_on(path.name, '2000-01-01') == '2001-02-03'
        objects = (catalog.load_variable_star_catalog() if kind == 'variable_stars'
                   else catalog._load_named_stars(kind))
        assert objects[0].magnitude_retrieved_on == '2001-02-03'
    reused = updates.refresh_catalogs([kind], 'force', True, tmp_path)
    assert '2001-02-03T04:05:06+00:00' in reused.notes[0]
    assert 'âge ' in reused.notes[0] and ' h' in reused.notes[0]
    assert 'mode force neutralisé' in reused.notes[0]
    assert catalog_retrieved_on(path.name, '2000-01-01') == '2000-01-01'


@pytest.mark.parametrize('kind', ['asteroids', 'comets'])
def test_orbital_default_resource_override_and_explicit_file(tmp_path, kind):
    from gnu_astrolist.asteroids import load_asteroid_catalog
    from gnu_astrolist.comets import load_comet_catalog
    filename = updates.CATALOG_REGISTRY[kind].filename
    original = resources.files('gnu_astrolist.data').joinpath(filename).read_bytes()
    output = tmp_path / filename
    if kind == 'asteroids':
        payload = json.loads(gzip.decompress(original))
        payload['data'] = payload['data'][:1]
        payload['data'][0][payload['fields'].index('name')] = 'Synthetic override'
        output.write_bytes(gzip.compress(json.dumps(payload).encode('ascii')))
        explicit = tmp_path / 'explicit.json'
        explicit.write_text(json.dumps(json.loads(gzip.decompress(original))), encoding='utf-8')
        loader = load_asteroid_catalog
    else:
        text = gzip.decompress(original).decode('ascii')
        lines = [line for line in text.splitlines() if line.strip() and not line.startswith('#')]
        text = '\n'.join(line for line in lines if line[4] != 'A')
        output.write_bytes(gzip.compress((text.splitlines()[0] + '\n').encode('ascii')))
        explicit = tmp_path / 'explicit.txt'
        explicit.write_text(gzip.decompress(original).decode('ascii'), encoding='ascii')
        loader = load_comet_catalog
    with use_catalog_resources({filename: output}):
        assert len(loader()) == 1
        assert len(loader(explicit)) > 1
    assert len(loader()) > 1


def test_gcvs_distinct_positions_allowed_exact_duplicate_rejected(tmp_path):
    fields = updates.gcvs.FIELDNAMES
    rows = [dict(zip(fields, ['SYNTHETIC', str(ra), '10', 'SR', '5', '', '', 'V']))
            for ra in (1, 2)]
    def write(items):
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(items)
        path = tmp_path / 'gcvs_visual.csv.gz'
        path.write_bytes(gzip.compress(stream.getvalue().encode('utf-8')))
        return path
    assert updates._validate('variable_stars', write(rows)) == 2
    with pytest.raises(ValueError, match='dupliqués'):
        updates._validate('variable_stars', write(rows + rows[:1]))


def test_future_cache_manifest_is_not_accepted(tmp_path, successful_builder):
    first = updates.refresh_catalogs(['bayer'], 'force', cache_dir=tmp_path)
    path = first.resources['bayer.csv.gz'].parent / 'metadata.json'
    info = json.loads(path.read_text(encoding='utf-8'))
    info['retrieved_at'] = '2999-01-01T00:00:00+00:00'
    path.write_text(json.dumps(info), encoding='utf-8')
    assert not updates.refresh_catalogs(['bayer'], offline=True, cache_dir=tmp_path).resources


def test_real_ngc_builder_uses_current_hash_and_simbad_missing_v(tmp_path):
    source = tmp_path / 'ngc-source'
    source.write_text('Name;Type;RA;Dec;Const;MajAx;MinAx;V-Mag;Common names\n'
                      'NGC0001;G;00:00:00;+10:00:00;And;1;1;;Synthetic\n', encoding='utf-8')
    supplement = tmp_path / 'simbad-source'
    supplement.write_text('id,flux,bibcode,qual,system\nNGC 1,7.5,SYNTHETIC,A,V\n',
                          encoding='utf-8')
    def fetch(provider, *args):
        return source if provider == 'openngc' else supplement
    output = updates._build('ngc', tmp_path, fetch, '2000-01-01')
    assert updates._validate('ngc', output) == 1
    with use_catalog_resources({output.name: output}):
        obj = catalog.load_ngc_catalog()[0]
        assert obj.magnitude_v == 7.5
        assert obj.magnitude_source == 'SIMBAD'
        assert obj.magnitude_retrieved_on == '2000-01-01'
