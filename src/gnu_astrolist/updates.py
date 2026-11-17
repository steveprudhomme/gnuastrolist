# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Actualisations explicites, séquentielles et transactionnelles des catalogues.

Le mode never et offline ne font aucun accès réseau. Les générations validées
restent disponibles comme repli; aucune source Seestar ne reçoit d'écriture.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import http.client
import io
import json
import math
import os
import stat
import tempfile
import urllib.parse
import urllib.request
import zlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from uuid import uuid4

from . import __version__, catalog
from .catalog_resources import use_catalog_resources
from .data_builders import build_caldwell_catalog as caldwell
from .data_builders import build_catalog as gcvs
from .data_builders import build_messier_catalog as messier
from .data_builders import build_ngc_catalog as ngc
from .data_builders import build_stellar_catalogs as stellar
from .data_builders import update_simbad_cache as simbad
from .seestar import protect_outputs

MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
TIMEOUT_SECONDS = 30
USER_AGENT = (f'GNU-Astrolist/{__version__} '
              '(https://github.com/steveprudhomme/gnuastrolist; '
              'contact: https://github.com/steveprudhomme/gnuastrolist/issues)')
JPL_URL = ('https://ssd-api.jpl.nasa.gov/sbdb_query.api?fields=spkid%2Cpdes%2Cname%2Cepoch'
           '%2Cequinox%2Ca%2Ce%2Ci%2Com%2Cw%2Cma%2CH%2CG%2Corbit_id&sb-kind=a&sb-ns=n'
           '&sort=spkid&limit=1000&full-prec=true')
MPC_URL = 'https://minorplanetcenter.net/iau/MPCORB/CometEls.txt'
HYG_URL = 'https://raw.githubusercontent.com/astronexus/HYG-Database/main/hyg/CURRENT/hygdata_v41.csv'


SOURCE_REGISTRY = {
    'gcvs': (gcvs.SOURCE_URL,),
    'openngc': (messier.NGC_SOURCE_URL, messier.ADDENDUM_SOURCE_URL),
    'simbad': (simbad.SIMBAD_TAP_URL,),
    'hyg': (HYG_URL,),
    'jpl': (JPL_URL,),
    'mpc': (MPC_URL,),
    'celestrak': tuple(
        f'https://celestrak.org/{endpoint}?GROUP={group}&FORMAT=CSV'
        for group in ('visual', 'cosmos-2251-debris')
        for endpoint in ('NORAD/elements/gp.php', 'satcat/records.php')
    ),
}


def parse_max_age_hours(value: str | float) -> float:
    """Analyse une durée strictement positive et finie, utilisable avec argparse."""
    try:
        age = float(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError('Durée en heures attendue') from exc
    if not math.isfinite(age) or age <= 0:
        raise argparse.ArgumentTypeError('Durée strictement positive et finie requise')
    return age


@dataclass(frozen=True)
class CatalogSpec:
    filename: str
    sources: tuple[str, ...]
    max_age_hours: float


CATALOG_REGISTRY = {
    'variable_stars': CatalogSpec('gcvs_visual.csv.gz', ('gcvs',), 720),
    'messier': CatalogSpec('messier.csv.gz', ('openngc', 'simbad'), 720),
    'caldwell': CatalogSpec('caldwell.csv.gz', ('openngc', 'simbad'), 720),
    'ngc': CatalogSpec('ngc.csv.gz', ('openngc', 'simbad'), 720),
    'bayer': CatalogSpec('bayer.csv.gz', ('hyg',), 720),
    'flamsteed': CatalogSpec('flamsteed.csv.gz', ('hyg',), 720),
    'asteroids': CatalogSpec('asteroids.json.gz', ('jpl',), 24),
    'comets': CatalogSpec('comets.txt.gz', ('mpc',), 24),
    'satellites': CatalogSpec('space_objects.json.gz', ('celestrak',), 6),
    'debris': CatalogSpec('space_objects.json.gz', ('celestrak',), 6),
}
DEFAULT_MAX_AGE_HOURS = {kind: spec.max_age_hours for kind, spec in CATALOG_REGISTRY.items()}


@dataclass(frozen=True)
class UpdateResult:
    resources: Mapping[str, Path]
    notes: tuple[str, ...]


def _download(url: str, data: bytes | None = None) -> bytes:
    request = urllib.request.Request(url, data=data, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        content = response.read(MAX_DOWNLOAD_BYTES + 1)
    if not content or len(content) > MAX_DOWNLOAD_BYTES:
        raise ValueError('Réponse vide ou supérieure à 50 Mio')
    return content


def _guard(path: Path, seestar_root: Path | None) -> None:
    # Inspecter le chemin lexical AVANT resolve: une jonction ne doit pas disparaître.
    absolute = path.absolute()
    if seestar_root is not None:
        protect_outputs(seestar_root, (absolute,))
    for component in (*reversed(absolute.parents), absolute):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Cache refusé : lien ou jonction dans le chemin')
        if stat.S_ISREG(info.st_mode) and info.st_nlink > 1:
            raise ValueError('Cache refusé : fichier avec liens physiques')


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _validate(kind: str, path: Path | None = None) -> int:
    overrides = {CATALOG_REGISTRY[kind].filename: path} if path is not None else {}
    resource = path or resources.files('gnu_astrolist.data').joinpath(
        CATALOG_REGISTRY[kind].filename)
    if kind in {'satellites', 'debris'}:
        from .satellite_updates import validate_bundle
        return validate_bundle(resource)
    if kind == 'asteroids':
        from .asteroids import parse_sbdb
        return len(parse_sbdb(json.loads(gzip.decompress(resource.read_bytes()))))
    if kind == 'comets':
        from .comets import parse_mpc
        return len(parse_mpc(gzip.decompress(resource.read_bytes()).decode('ascii')))
    loaders = {
        'variable_stars': catalog.load_variable_star_catalog,
        'messier': catalog.load_messier_catalog,
        'caldwell': catalog.load_caldwell_catalog,
        'ngc': catalog.load_ngc_catalog,
        'bayer': catalog.load_bayer_catalog,
        'flamsteed': catalog.load_flamsteed_catalog,
    }
    with use_catalog_resources(overrides):
        objects = loaders[kind]()
    names = [obj.name for obj in objects]
    identities = ([(obj.name, obj.ra_deg, obj.dec_deg) for obj in objects]
                  if kind == 'variable_stars' else names)
    if not names or any(not name.strip() for name in names) or len(set(identities)) != len(names):
        raise ValueError('Catalogue vide ou identifiants dupliqués')
    for obj in objects:
        if not (0 <= obj.ra_deg < 360 and -90 <= obj.dec_deg <= 90):
            raise ValueError('Coordonnées invalides')
        if obj.magnitude_v is not None and not math.isfinite(obj.magnitude_v):
            raise ValueError('Magnitude non finie')
    # Vérifier également les champs facultatifs et la bande, sans conversion photométrique.
    with resource.open('rb') as raw, gzip.open(
        raw, 'rt', encoding='utf-8', newline=''
    ) as stream:
        for row in csv.DictReader(stream):
            if 'passband' in row and row['passband'] != 'V':
                raise ValueError('Bande V requise')
            for field in ('mag_min', 'major_axis_arcmin', 'minor_axis_arcmin'):
                if row.get(field) and not math.isfinite(float(row[field])):
                    raise ValueError('Mesure non finie')
    expected = {'messier': 110, 'caldwell': 109}.get(kind)
    prefix = {'messier': 'M', 'caldwell': 'C'}.get(kind)
    if expected is not None and (len(objects) != expected or
            set(names) != {f'{prefix}{number}' for number in range(1, expected + 1)}):
        raise ValueError(f'Catalogue incomplet : {expected} objets requis')
    if kind in {'bayer', 'flamsteed'}:
        identifiers = [obj.hyg_id for obj in objects]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError('Identifiants HYG dupliqués')
    return len(objects)


def _baseline_count(kind: str) -> int:
    resource = resources.files('gnu_astrolist.data').joinpath(CATALOG_REGISTRY[kind].filename)
    if not resource.is_file():
        return 0
    return _validate(kind)


def _check_count(kind: str, count: int, baseline: int) -> None:
    if count <= 0 or (baseline and not baseline * .8 <= count <= baseline * 1.2):
        raise ValueError(f'{kind} : variation de population supérieure à 20 %')


def _write_gzip(path: Path, content: bytes) -> None:
    path.write_bytes(gzip.compress(content, mtime=0))


def _tap(query: str) -> bytes:
    return urllib.parse.urlencode({
        'request': 'doQuery', 'lang': 'adql', 'format': 'csv', 'query': query,
    }).encode('ascii')


def _build(kind: str, directory: Path, fetch, retrieved_on: str) -> Path:
    output = directory / CATALOG_REGISTRY[kind].filename
    if kind == 'variable_stars':
        source = fetch('gcvs', gcvs.SOURCE_URL)
        gcvs.build(str(source), output)
    elif kind in ('bayer', 'flamsteed'):
        source = fetch('hyg', HYG_URL)
        stellar.build(source, directory, expected_sha256=None)
    elif kind == 'asteroids':
        from .asteroids import parse_sbdb
        payload = json.loads(fetch('jpl', JPL_URL).read_bytes())
        parse_sbdb(payload)
        payload['astrolist_retrieved_on'] = retrieved_on
        _write_gzip(output, json.dumps(payload, sort_keys=True).encode('utf-8'))
    elif kind == 'comets':
        source = fetch('mpc', MPC_URL)
        _write_gzip(output, source.read_bytes())
    else:
        source = fetch('openngc', messier.NGC_SOURCE_URL)
        addendum = None
        if kind in ('messier', 'caldwell'):
            addendum = fetch('openngc', messier.ADDENDUM_SOURCE_URL)
        if kind == 'messier':
            response = fetch('simbad', simbad.SIMBAD_TAP_URL, _tap(simbad.TAP_QUERY))
            cache = directory / 'simbad_messier_cache.csv.gz'
            simbad.write_cache(simbad.parse_rows(response.read_bytes(), retrieved_on), cache)
            # La date OpenNGC du générateur reproductible est remplacée dans le résultat.
            messier.build(str(source), str(addendum), output, cache)
        elif kind == 'caldwell':
            caldwell.build(argparse.Namespace(
                ngc_source=str(source), addendum_source=str(addendum), output=output,
                retrieved_on=retrieved_on, fetch_simbad=False, simbad_response=None,
            ))
        else:
            ngc.build(source, output, retrieved_on, expected_sha256=None)
        with gzip.open(output, 'rt', encoding='utf-8', newline='') as stream:
            reader = csv.DictReader(stream)
            fields = reader.fieldnames
            rows = list(reader)
        if kind != 'messier':
            identifiers = []
            for number, row in enumerate(rows, 1):
                designation = row['catalog_designation']
                identifier = (caldwell.simbad_id(number, designation) if kind == 'caldwell'
                              else 'NGC ' + designation[3:].lstrip('0'))
                identifiers.append(identifier)
            quoted = ','.join("'" + value.replace("'", "''") + "'" for value in identifiers)
            query = ('SELECT i.id, f.flux, f.bibcode, f.qual, f.system FROM ident AS i '
                     'JOIN flux AS f ON i.oidref=f.oidref '
                     f"WHERE f.filter='V' AND i.id IN ({quoted})")
            response = fetch('simbad', simbad.SIMBAD_TAP_URL, _tap(query))
            reader = csv.DictReader(io.StringIO(response.read_text(encoding='utf-8')))
            if not {'id', 'flux', 'bibcode', 'qual', 'system'}.issubset(reader.fieldnames or ()):
                raise ValueError('Schéma SIMBAD invalide')
            supplements = {}
            for extra in reader:
                identifier = ' '.join(extra['id'].split())
                if identifier in supplements:
                    raise ValueError('Identifiant SIMBAD dupliqué')
                supplements[identifier] = extra
            for row, identifier in zip(rows, identifiers):
                extra = supplements.get(identifier)
                if (not row['magnitude_v'] and extra and extra['flux'].strip()
                        and extra['qual'] in {'A', 'B', 'C'}):
                    magnitude = float(extra['flux'])
                    if not math.isfinite(magnitude):
                        raise ValueError('Magnitude SIMBAD non finie')
                    row.update(magnitude_v=str(magnitude), magnitude_source='SIMBAD',
                               magnitude_reference=extra['bibcode'] or 'SIMBAD TAP',
                               magnitude_retrieved_on=retrieved_on)
        for row in rows:
            for field in ('size', 'magnitude'):
                if row[f'{field}_source'] == 'OpenNGC':
                    row[f'{field}_retrieved_on'] = retrieved_on
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        _write_gzip(output, stream.getvalue().encode('utf-8'))
    return output


def refresh_catalogs(
    kinds: Iterable[str], mode: str = 'never', offline: bool = False,
    cache_dir: Path = Path('local/catalog-cache'),
    max_age_hours: Mapping[str, float] | None = None,
    seestar_root: Path | None = None,
) -> UpdateResult:
    """Actualise seulement les types sélectionnés; les âges acceptent type ou source.

    L'appelant doit fournir la racine Seestar déjà validée avant cet appel,
    et protéger aussi ses autres sorties. CBAT reste une saisie locale séparée.
    """
    if mode not in {'never', 'if-stale', 'force'}:
        raise ValueError('Mode attendu : never, if-stale ou force')
    selected = tuple(dict.fromkeys(kinds))
    if any(kind not in CATALOG_REGISTRY for kind in selected):
        raise ValueError('Catalogue non enregistré')
    ages = dict(max_age_hours or {})
    for key, value in ages.items():
        if key not in {*CATALOG_REGISTRY, *SOURCE_REGISTRY, 'satcat', 'gp'}:
            raise ValueError(f'Âge de source inconnu : {key}')
        try:
            ages[key] = parse_max_age_hours(value)
        except argparse.ArgumentTypeError as exc:
            raise ValueError(str(exc)) from exc
    # Aucun mkdir, fichier temporaire ou téléchargement avant cette protection.
    _guard(cache_dir, seestar_root)
    cache_dir = cache_dir.resolve()
    now = datetime.now(timezone.utc)
    active, notes = {}, []
    satellite_kinds = tuple(kind for kind in selected if kind in {'satellites', 'debris'})
    if satellite_kinds:
        from .satellite_updates import refresh_satellite_catalog
        satellite_ages = {key: value for key, value in ages.items()
                          if key in {*satellite_kinds, 'celestrak', 'gp', 'satcat'}}
        # Une seule génération partagée; un alias absent ne réduit pas le délai.
        satellite_ages['satellites'] = min(
            ages.get(kind, CATALOG_REGISTRY[kind].max_age_hours) for kind in satellite_kinds)
        result = refresh_satellite_catalog(mode, offline, cache_dir, satellite_ages, seestar_root)
        active.update(result.resources)
        notes.extend(result.notes)
        selected = tuple(kind for kind in selected if kind not in satellite_kinds)
    downloads = {}
    failures = {}
    source_metadata = {}

    for kind in selected:
        spec = CATALOG_REGISTRY[kind]
        baseline = _baseline_count(kind)
        cached = None
        metadata = None
        discarded = 0
        for generation in sorted(cache_dir.glob(f'{kind}-*'), reverse=True):
            discarded += 1
            try:
                _guard(generation, seestar_root)
                manifest = generation / 'metadata.json'
                path = generation / spec.filename
                _guard(manifest, seestar_root)
                _guard(path, seestar_root)
                info = json.loads(manifest.read_text(encoding='utf-8'))
                if info['schema_version'] != 1 or info['kind'] != kind:
                    continue
                if _sha(path.read_bytes()) != info['sha256']:
                    continue
                _check_count(kind, _validate(kind, path), baseline)
                timestamp = datetime.fromisoformat(info['retrieved_at'])
                if timestamp.tzinfo is None or timestamp > now:
                    continue
                cached, metadata = path, info
                discarded -= 1
                break
            except (OSError, ValueError, KeyError, RuntimeError, EOFError, TypeError,
                    csv.Error, zlib.error):
                continue
        if discarded:
            notes.append(f'{kind} : {discarded} génération(s) de cache illisible(s) ou non valide(s) ignorée(s).')
        if cached is not None:
            active[spec.filename] = cached
        age = ages.get(kind, spec.max_age_hours)
        threshold = min([age, *(ages[s] for s in spec.sources if s in ages)])
        stale = metadata is None or (now - datetime.fromisoformat(
            metadata['retrieved_at'])).total_seconds() >= threshold * 3600
        bundled_date = {
            'variable_stars': '2026-07-17', 'messier': '2026-08-03',
            'caldwell': '2026-11-16', 'ngc': '2026-11-16', 'bayer': '2026-11-17',
            'flamsteed': '2026-11-17', 'asteroids': '2026-11-17', 'comets': '2026-11-17',
        }[kind]
        retrieved_at = metadata['retrieved_at'] if metadata else bundled_date + 'T00:00:00+00:00'
        elapsed = (now - datetime.fromisoformat(retrieved_at)).total_seconds() / 3600
        date_label = retrieved_at if cached else bundled_date + ' (date documentée)'
        age_label = f'{elapsed:.1f}' if cached else f'environ {elapsed:.1f}'
        local_note = (('cache' if cached else 'copie embarquée')
                      + f', récupération {date_label}, âge {age_label} h, seuil {threshold:g} h')
        if offline or mode == 'never' or (mode == 'if-stale' and not stale):
            notes.append(f'{kind} : {local_note}.' + (
                f' Hors ligne : mode {mode} neutralisé, aucun réseau.' if offline else ''))
            continue
        try:
            _guard(cache_dir, seestar_root)
            cache_dir.mkdir(parents=True, exist_ok=True)
            _guard(cache_dir, seestar_root)
            with tempfile.TemporaryDirectory(prefix='.pending-', dir=cache_dir) as temporary:
                directory = Path(temporary)
                _guard(directory, seestar_root)
                used = {}

                def fetch(source, url, data=None):
                    key = (url, data)
                    if key in failures:
                        raise ValueError('Source déjà indisponible pendant cet appel')
                    if key not in downloads:
                        try:
                            content = _download(url, data)
                        except (OSError, ValueError, http.client.HTTPException) as exc:
                            failures[key] = str(exc)
                            raise
                        downloads[key] = content
                        source_metadata[key] = {
                            'source': source, 'url': url, 'sha256': _sha(content),
                            'retrieved_at': now.isoformat(),
                            'filename': 'source-' + _sha(url.encode() + (data or b'')),
                            'license': {
                                'openngc': 'CC-BY-SA-4.0', 'hyg': 'CC-BY-SA-4.0',
                                'gcvs': 'Conditions GCVS / VizieR-CDS',
                                'simbad': 'Conditions SIMBAD / CDS',
                                'jpl': 'Domaine public NASA/JPL, attribution recommandée',
                                'mpc': 'Conditions Minor Planet Center; voir COMET_SOURCE.md',
                            }[source],
                            'request_data': data.decode('ascii') if data else None,
                        }
                    used[key] = source_metadata[key]
                    path = directory / ('source-' + _sha(url.encode() + (data or b'')))
                    _guard(path, seestar_root)
                    path.write_bytes(downloads[key])
                    return path

                output = _build(kind, directory, fetch, now.date().isoformat())
                count = _validate(kind, output)
                _check_count(kind, count, baseline)
                info = {
                    'schema_version': 1, 'kind': kind, 'retrieved_at': now.isoformat(),
                    'builder_version': __version__,
                    'reconstruction': 'gnu_astrolist.updates._build(kind, directory, '
                                      'fetch_from_saved_sources, retrieved_on)',
                    'sha256': _sha(output.read_bytes()), 'count': count,
                    'sources': list(used.values()),
                    'provenance': 'Notices de sources : gnu_astrolist/data/*_SOURCE.md',
                }
                manifest = directory / 'metadata.json'
                _guard(manifest, seestar_root)
                manifest.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
                destination = cache_dir / f'{kind}-{now.strftime("%Y%m%dT%H%M%S%f")}-{uuid4().hex}'
                _guard(destination, seestar_root)
                _guard(directory, seestar_root)
                os.replace(directory, destination)
                active[spec.filename] = destination / spec.filename
                notes.append(f'{kind} : nouvelle copie validée ({count} objets); '
                             f'récupération {now.isoformat()}, âge 0 h, seuil {threshold:g} h.')
        except (OSError, ValueError, KeyError, RuntimeError, EOFError, TypeError,
                StopIteration, http.client.HTTPException, csv.Error, zlib.error) as exc:
            notes.append(f'{kind} : actualisation impossible ({exc}); '
                         + ('ancien cache valide conservé; ' if cached else 'copie embarquée conservée; ')
                         + local_note + '.')
    return UpdateResult(active, tuple(notes))
