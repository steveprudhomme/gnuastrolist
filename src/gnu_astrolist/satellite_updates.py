# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Cache CelesTrak partagé, transactionnel et soumis aux délais du fournisseur.

La date de récupération ne remplace jamais EPOCH. Les dates embarquées sans
heure sont documentaires (minuit UTC), pas une mesure précise d'âge réseau.
Supprimer manuellement celestrak-state.json après inspection lève un blocage.
"""
from __future__ import annotations

import csv
import gzip
import http.client
import io
import json
import os
import re
import tempfile
import urllib.error
import urllib.request
import zlib
from datetime import datetime, timedelta, timezone
from importlib import resources
from pathlib import Path
from uuid import uuid4

from . import __version__
from .updates import (
    MAX_DOWNLOAD_BYTES,
    SOURCE_REGISTRY,
    TIMEOUT_SECONDS,
    USER_AGENT,
    UpdateResult,
    _guard,
    _sha,
    parse_max_age_hours,
)

ARTIFACT = 'space_objects.json.gz'
STATE_FILE = 'celestrak-state.json'
SOURCE_URLS = SOURCE_REGISTRY['celestrak']
_ERRORS = (OSError, ValueError, KeyError, TypeError, RuntimeError, EOFError,
           csv.Error, zlib.error, http.client.HTTPException)


def _now() -> datetime:
    """Horloge UTC remplaçable dans les tests déterministes."""
    return datetime.now(timezone.utc)


def _timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError('Date de récupération invalide')
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('Date de récupération sans fuseau')
    return stamp.astimezone(timezone.utc)


def _source_time(source: dict) -> datetime:
    if not isinstance(source, dict):
        raise ValueError('Métadonnées de source invalides')
    if source.get('retrieved_at'):
        return _timestamp(source['retrieved_at'])
    documented = source['retrieved_on']
    if not isinstance(documented, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', documented):
        raise ValueError('Date documentaire invalide')
    return _timestamp(documented + 'T00:00:00+00:00')


def _is_gp(url: str) -> bool:
    return '/elements/gp.php?' in url


def _read_bundle(resource) -> dict:
    with resource.open('rb') as stream, gzip.GzipFile(fileobj=stream) as compressed:
        content = compressed.read(MAX_DOWNLOAD_BYTES + 1)
        if len(content) > MAX_DOWNLOAD_BYTES:
            raise ValueError('Conteneur spatial supérieur à 50 Mio')
    payload = json.loads(content)
    _validate_payload(payload)
    return payload


def _validate_payload(payload: dict) -> int:
    from .satcat import parse_satcat
    from .satellites import parse_gp

    if (not isinstance(payload, dict) or type(payload.get('schema_version')) is not int
            or payload['schema_version'] != 1):
        raise ValueError('Version du conteneur spatial invalide')
    gp = parse_gp(payload['gp'])
    satcat = parse_satcat(payload['satcat'])
    if not gp or len(gp) != len(payload['gp']) or len(satcat) != len(payload['satcat']):
        raise ValueError('Conteneur spatial vide ou identités dupliquées')
    for item in gp:
        record = satcat.get(item.norad_id)
        if (record is None or not item.cospar_id
                or item.cospar_id != record.cospar_id):
            raise ValueError(f'Association NORAD/COSPAR incohérente : {item.norad_id}')
    sources = payload['sources']
    if not isinstance(sources, list) or len(sources) != len(SOURCE_URLS):
        raise ValueError('Quatre sources CelesTrak requises')
    if {source['url'] for source in sources} != set(SOURCE_URLS):
        raise ValueError('URLs de sources CelesTrak inattendues')
    for source in sources:
        if not re.fullmatch('[0-9a-f]{64}', source['sha256']):
            raise ValueError('Empreinte de source invalide')
        if _source_time(source) > _now():
            raise ValueError('Date de récupération future')
    return len(gp)


def validate_bundle(resource) -> int:
    """Valide gzip, schéma, GP, SATCAT, provenances et jointure exacte."""
    return len(_read_bundle(resource)['gp'])


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _download(url: str) -> bytes:
    """Un seul GET CSV, sans redirection ni nouvelle tentative implicite."""
    request = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT, 'Accept-Encoding': 'gzip', 'Accept': 'text/csv',
    })
    opener = urllib.request.build_opener(_NoRedirect())
    with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise urllib.error.HTTPError(url, response.status, 'CelesTrak', response.headers, None)
        compressed = response.headers.get('Content-Encoding', '').lower()
        if compressed not in ('', 'identity', 'gzip'):
            raise ValueError('Encodage HTTP inconnu')
        raw = response.read(MAX_DOWNLOAD_BYTES + 1)
        if len(raw) > MAX_DOWNLOAD_BYTES:
            raise ValueError('Réponse supérieure à 50 Mio')
        if compressed == 'gzip':
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                raw = stream.read(MAX_DOWNLOAD_BYTES + 1)
        if not raw or len(raw) > MAX_DOWNLOAD_BYTES:
            raise ValueError('Réponse vide ou supérieure à 50 Mio après décompression')
        return raw


def _write_json(path: Path, payload: dict, seestar_root: Path | None) -> None:
    """Remplacement atomique, y compris pour l'état des échecs fournisseur."""
    _guard(path, seestar_root)
    temporary = path.with_name('.' + path.name + '-' + uuid4().hex)
    _guard(temporary, seestar_root)
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        _guard(path, seestar_root)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            _guard(temporary, seestar_root)
            temporary.unlink()


def _load_state(path: Path, seestar_root: Path | None) -> dict:
    _guard(path, seestar_root)
    if not path.exists():
        return {'schema_version': 1, 'provider': 'celestrak', 'requests': {}}
    state = json.loads(path.read_text(encoding='utf-8'))
    if (state['schema_version'] != 1 or state['provider'] != 'celestrak'
            or not isinstance(state['requests'], dict)):
        raise ValueError('État fournisseur invalide; inspection humaine requise')
    for url, stamp in state['requests'].items():
        if url not in SOURCE_URLS or _timestamp(stamp) > _now():
            raise ValueError('Historique fournisseur invalide; inspection humaine requise')
    if state.get('cooldown_until'):
        _timestamp(state['cooldown_until'])
    return state


def _merge(groups: list[list[dict]]) -> list[dict]:
    """Seuls les doublons strictement identiques d'un NORAD sont fusionnés."""
    merged = {}
    for rows in groups:
        for row in rows:
            number = int(row['NORAD_CAT_ID'])
            if number in merged and merged[number] != row:
                raise ValueError(f'Doublon NORAD contradictoire : {number}')
            merged[number] = row
    return list(merged.values())


def _local_copy(cache_dir, seestar_root, now, notes):
    bundled = None
    try:
        bundled = _read_bundle(resources.files('gnu_astrolist.data').joinpath(ARTIFACT))
    except _ERRORS:
        notes.append('satellites : copie embarquée absente ou invalide.')
    candidates = []
    discarded = 0
    for pattern in ('satellites-*', 'debris-*'):
        for generation in cache_dir.glob(pattern):
            try:
                path, manifest = generation / ARTIFACT, generation / 'metadata.json'
                for target in (generation, path, manifest):
                    _guard(target, seestar_root)
                info = json.loads(manifest.read_text(encoding='utf-8'))
                if (type(info['schema_version']) is not int or info['schema_version'] != 1
                        or info['kind'] not in {'satellites', 'debris'}
                        or info['sha256'] != _sha(path.read_bytes())):
                    raise ValueError('Métadonnées de génération invalides')
                stamp = _timestamp(info['retrieved_at'])
                payload = _read_bundle(path)
                if (stamp > now or info['count'] != len(payload['gp'])
                        or info['sources'] != payload['sources']
                        or any(_source_time(s) > stamp for s in payload['sources'])):
                    raise ValueError('Métadonnées de génération incohérentes')
                if bundled:
                    _check_population(payload, bundled)
                # L'ordre du nom d'alias ne doit pas masquer un cache plus récent.
                candidates.append((stamp, str(path), path, payload))
            except _ERRORS:
                discarded += 1
    if discarded:
        notes.append(f'satellites : {discarded} génération(s) non valide(s) ignorée(s).')
    if candidates:
        _, _, path, payload = max(candidates)
        return path, payload, bundled
    return None, bundled, bundled


def _check_population(payload, baseline):
    for key in ('gp', 'satcat'):
        if baseline and not len(baseline[key]) * .8 <= len(payload[key]) <= len(baseline[key]) * 1.2:
            raise ValueError(f'{key} : variation de population supérieure à 20 %')


def refresh_satellite_catalog(
    mode: str = 'never', offline: bool = False,
    cache_dir: Path = Path('local/catalog-cache'),
    max_age_hours: dict[str, float] | float | None = None,
    seestar_root: Path | None = None,
) -> UpdateResult:
    """Actualise une seule génération GP/SATCAT pour satellites et débris.

    Les GP sont demandés au plus toutes les deux heures; SATCAT est réutilisé
    pendant au moins 24 h, même en force. Tout statut non 200 arrête le fournisseur.
    Les 4xx/redirections exigent une inspection; les autres pannes attendent 15 min.
    Aucun état ni dossier n'est créé en mode never ou offline.
    """
    if mode not in {'never', 'if-stale', 'force'}:
        raise ValueError('Mode attendu : never, if-stale ou force')
    ages = ({'satellites': max_age_hours} if isinstance(max_age_hours, (int, float))
            else dict(max_age_hours or {}))
    for key, value in ages.items():
        if key not in {'satellites', 'debris', 'gp', 'satcat', 'celestrak'}:
            raise ValueError(f'Âge de source inconnu : {key}')
        ages[key] = parse_max_age_hours(value)
    gp_age = max(2, min([ages.get('satellites', 6), *(
        ages[key] for key in ('debris', 'gp', 'celestrak') if key in ages)]))
    satcat_age = max(24, ages.get('satcat', 24))
    cache_dir = Path(cache_dir)
    _guard(cache_dir, seestar_root)
    cache_dir = cache_dir.resolve()
    now, notes = _now(), []
    cached, payload, baseline = _local_copy(cache_dir, seestar_root, now, notes)
    active = {ARTIFACT: cached} if cached else {}
    sources = {s['url']: s for s in payload['sources']} if payload else {}
    labels = []
    due = {}
    for key, threshold in (('gp', gp_age), ('satcat', satcat_age)):
        stamps = [_source_time(s) for url, s in sources.items() if _is_gp(url) == (key == 'gp')]
        elapsed = (now - min(stamps)).total_seconds() / 3600 if stamps else float('inf')
        precise = bool(stamps) and all(s.get('retrieved_at') for url, s in sources.items()
                                      if _is_gp(url) == (key == 'gp'))
        date_label = min(stamps).isoformat() if stamps else 'inconnue'
        labels.append(f'{key.upper()} récupération {date_label}'
                      + ('' if precise else ' (date documentée, heure non connue)')
                      + f', âge {elapsed:.1f} h, seuil {threshold:g} h')
        due[key] = not stamps or elapsed >= (2 if key == 'gp' and mode == 'force' else threshold)
    local_note = ('ancien cache valide' if cached else 'copie embarquée') + '; ' + '; '.join(labels)
    if offline or mode == 'never' or not any(due.values()):
        notes.append('satellites/débris : ' + local_note + '.'
                     + (' Hors ligne : aucun réseau.' if offline else ''))
        return UpdateResult(active, tuple(notes))
    state_path = cache_dir / STATE_FILE
    try:
        state = _load_state(state_path, seestar_root)
        if state.get('blocked'):
            raise ValueError('CelesTrak bloqué; inspection humaine et réinitialisation locale requises')
        if state.get('cooldown_until') and now < _timestamp(state['cooldown_until']):
            raise ValueError('CelesTrak en pause de sécurité (au moins 15 minutes)')
        requested = [url for url in SOURCE_URLS if due['gp' if _is_gp(url) else 'satcat']]
        # Vérifier tous les délais AVANT la première requête ou écriture.
        for url in requested:
            if url in state['requests']:
                hours = 2 if _is_gp(url) else 24
                if now - _timestamp(state['requests'][url]) < timedelta(hours=hours):
                    raise ValueError(f'CelesTrak : délai minimal de {hours} h depuis la dernière requête')
        _guard(cache_dir, seestar_root)
        cache_dir.mkdir(parents=True, exist_ok=True)
        _guard(cache_dir, seestar_root)
        rows, raw_sources = {'gp': [], 'satcat': []}, {}
        for url in requested:
            state['requests'][url] = _now().isoformat()
            _write_json(state_path, state, seestar_root)
            try:
                raw = _download(url)
            except _ERRORS as exc:
                state['failure'] = str(exc)
                state['failed_at'] = _now().isoformat()
                status = getattr(exc, 'code', None)
                state['status'] = status
                if status is not None and 300 <= status < 500:
                    state['blocked'] = True
                else:
                    state['cooldown_until'] = (_now() + timedelta(minutes=15)).isoformat()
                _write_json(state_path, state, seestar_root)
                raise
            key = 'gp' if _is_gp(url) else 'satcat'
            text = raw.decode('utf-8-sig')
            # Valider immédiatement chaque réponse avant de demander la suivante.
            from .satcat import parse_satcat
            from .satellites import parse_gp
            reader = csv.DictReader(io.StringIO(text))
            fields = reader.fieldnames or []
            if len(fields) != len(set(fields)):
                raise ValueError('Colonnes CSV dupliquées')
            group_rows = list(reader)
            if not group_rows:
                raise ValueError('Source CelesTrak vide')
            if any(None in row or any(value is None for value in row.values()) for row in group_rows):
                raise ValueError('Ligne CSV incomplète ou trop longue')
            (parse_gp if key == 'gp' else parse_satcat)(_merge([group_rows]))
            rows[key].append(group_rows)
            sources[url] = {
                'url': url, 'sha256': _sha(raw), 'retrieved_at': _now().isoformat(),
                'count': len(group_rows), 'source': 'celestrak',
                'license': 'Conditions CelesTrak; https://celestrak.org/usage-policy.php',
                'filename': 'source-' + _sha(url.encode()),
            }
            raw_sources[sources[url]['filename']] = raw
        new_payload = {'schema_version': 1, 'sources': [sources[url] for url in SOURCE_URLS]}
        for key in ('gp', 'satcat'):
            new_payload[key] = _merge(rows[key]) if due[key] else payload[key]
        count = _validate_payload(new_payload)
        _check_population(new_payload, baseline)
        # Une source réutilisée garde sa date, son empreinte et sa réponse brute.
        if cached:
            for source in new_payload['sources']:
                name = source.get('filename')
                if name and name not in raw_sources:
                    if name != 'source-' + _sha(source['url'].encode()):
                        raise ValueError('Nom de réponse source invalide')
                    saved = cached.parent / name
                    _guard(saved, seestar_root)
                    if saved.is_file():
                        raw = saved.read_bytes()
                        if _sha(raw) != source['sha256']:
                            raise ValueError('Réponse source conservée corrompue')
                        raw_sources[name] = raw
        with tempfile.TemporaryDirectory(prefix='.pending-satellites-', dir=cache_dir) as temporary:
            directory = Path(temporary)
            _guard(directory, seestar_root)
            output = directory / ARTIFACT
            _guard(output, seestar_root)
            output.write_bytes(gzip.compress(json.dumps(new_payload, sort_keys=True).encode(), mtime=0))
            validate_bundle(output)
            for name, raw in raw_sources.items():
                target = directory / name
                _guard(target, seestar_root)
                target.write_bytes(raw)
            info = {
                'schema_version': 1, 'kind': 'satellites', 'retrieved_at': _now().isoformat(),
                'sha256': _sha(output.read_bytes()), 'count': count, 'sources': new_payload['sources'],
                'builder_version': __version__,
                'reconstruction': 'CSV sources -> fusion NORAD strictement identique -> '
                                  'parse_gp + parse_satcat + jointure NORAD/COSPAR exacte',
            }
            _write_json(directory / 'metadata.json', info, seestar_root)
            destination = cache_dir / f'satellites-{now.strftime("%Y%m%dT%H%M%S%f")}-{uuid4().hex}'
            _guard(destination, seestar_root)
            _guard(directory, seestar_root)
            os.replace(directory, destination)
            active[ARTIFACT] = destination / ARTIFACT
        notes.append(f'satellites/débris : nouvelle copie validée ({count} GP, '
                     f'{len(new_payload["satcat"])} SATCAT); '
                     f'seuil GP {gp_age:g} h, SATCAT {satcat_age:g} h; '
                     'époques orbitales conservées; dates de récupération dans les sources.')
        for key in ('gp', 'satcat'):
            stamps = [_source_time(s) for s in new_payload['sources']
                      if _is_gp(s['url']) == (key == 'gp')]
            stamp = min(stamps)
            documented = any(not s.get('retrieved_at') for s in new_payload['sources']
                             if _is_gp(s['url']) == (key == 'gp'))
            notes.append(f'{key.upper()} : récupération {stamp.isoformat()}, '
                         f'âge {(now - stamp).total_seconds() / 3600:.1f} h'
                         + (' environ (date documentée).' if documented else '.'))
    except _ERRORS as exc:
        notes.append(f'satellites/débris : actualisation impossible ({exc}); {local_note} conservé.')
    return UpdateResult(active, tuple(notes))
