# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Identités COSPAR/SATCAT et extraits administratifs UNOOSA, sans réseau."""

from __future__ import annotations

import csv
import gzip
import io
import json
import math
import re
import zlib
from collections import Counter
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .catalog_resources import catalog_resource
from .models import SatelliteTarget


def normalize_cospar(value: str) -> str | None:
    match = re.fullmatch(r"(\d{4})[- _]?(\d{3})([A-HJ-NP-Z]{1,3})", value.strip().upper())
    return f"{match[1]}-{match[2]}{match[3]}" if match and int(match[2]) > 0 else None


def norad_number(value) -> int:
    text = str(value)
    if not text.isascii() or not text.isdecimal() or not 1 <= int(text) <= 999999999:
        raise ValueError("Numéro SATCAT/NORAD invalide (1 à 9 chiffres)")
    return int(text)


def _date(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if len(value) == 10:
        date.fromisoformat(value)
    else:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


@dataclass(frozen=True)
class SatcatRecord:
    norad_id: int
    cospar_id: str
    name: str
    object_type: str
    owner: str
    launch_date: str
    decay_date: str
    orbit_center: str
    orbit_type: str


def parse_satcat(payload) -> dict[int, SatcatRecord]:
    if isinstance(payload, str):
        reader = csv.DictReader(io.StringIO(payload))
        fields = reader.fieldnames or ()
        if len(fields)!=len(set(fields)):
            raise ValueError('Champs SATCAT dupliqués')
        rows = list(reader)
    elif isinstance(payload, list) and payload and all(isinstance(row, dict) for row in payload):
        rows = payload
        fields = rows[0].keys()
    else:
        raise ValueError("Réponse SATCAT vide ou de format inconnu")
    required = {
        "NORAD_CAT_ID",
        "OBJECT_ID",
        "OBJECT_NAME",
        "OBJECT_TYPE",
        "OWNER",
        "LAUNCH_DATE",
        "DECAY_DATE",
        "ORBIT_CENTER",
        "ORBIT_TYPE",
    }
    if not required.issubset(fields):
        raise ValueError("Champs CSV SATCAT absents")
    result = {}
    for row in rows:
        try:
            if not required.issubset(row):
                raise ValueError("Champs SATCAT absents dans une ligne")
            number = norad_number(row["NORAD_CAT_ID"])
            raw_id = (row["OBJECT_ID"] or "").strip()
            cospar = normalize_cospar(raw_id) if raw_id else ""
            if raw_id and cospar is None:
                raise ValueError("Désignation COSPAR invalide")
            if number in result or row["OBJECT_TYPE"] not in {"PAY", "R/B", "DEB", "UNK"}:
                raise ValueError("Identifiant dupliqué ou type SATCAT inconnu")
            if not isinstance(row["OBJECT_NAME"], str) or not row["OBJECT_NAME"].strip():
                raise ValueError("Nom SATCAT absent")
            for key in ("PERIOD", "INCLINATION", "APOGEE", "PERIGEE", "RCS"):
                if row.get(key) not in ("", None):
                    value = float(row[key])
                    if not math.isfinite(value) or key == "RCS" and value < 0:
                        raise ValueError("Mesure SATCAT non finie ou invalide")
            result[number] = SatcatRecord(
                number,
                cospar,
                row["OBJECT_NAME"].strip(),
                row["OBJECT_TYPE"],
                row["OWNER"] or "",
                _date(row["LAUNCH_DATE"] or ""),
                _date(row["DECAY_DATE"] or ""),
                row["ORBIT_CENTER"] or "",
                row["ORBIT_TYPE"] or "",
            )
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError(f"Ligne SATCAT invalide : {exc}") from exc
    if not result:
        raise ValueError("Catalogue SATCAT vide")
    return result


def load_space_bundle():
    resource = catalog_resource("space_objects.json.gz")
    try:
        payload = json.loads(gzip.decompress(resource.read_bytes()))
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError("Version de la copie satellitaire incorrecte")
        return payload
    except (OSError, ValueError, TypeError, zlib.error) as exc:
        raise ValueError("Copie satellitaire locale illisible") from exc


def load_satcat(path: Path | None = None):
    if path is None:
        return parse_satcat(load_space_bundle()["satcat"])
    try:
        content = path.read_bytes()
        if path.suffix == ".gz":
            content = gzip.decompress(content)
        text = content.decode("utf-8-sig")
        payload = json.loads(text) if text.lstrip().startswith(("[", "{")) else text
        if isinstance(payload, dict):
            payload = payload["satcat"]
        return parse_satcat(payload)
    except (OSError, ValueError, TypeError, KeyError, zlib.error) as exc:
        raise ValueError(f"Fichier SATCAT local invalide : {path}") from exc


@dataclass(frozen=True)
class RegistryRecord:
    cospar_id: str
    object_name: str
    state_of_registry: str
    registration_document: str
    registration_date: str
    source_url: str
    retrieved_on: str
    norad_id: int | None = None


def load_unoosa_records(path: Path) -> tuple[RegistryRecord, ...]:
    """CSV local transcrit, jamais déclaré format d'export officiel UNOOSA."""
    required = {
        "cospar_id",
        "state_of_registry",
        "registration_document",
        "source_url",
        "retrieved_on",
    }
    optional = {"object_name", "registration_date", "norad_id"}
    result, seen = [], set()
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            fields = set(reader.fieldnames or ())
            if len(fields)!=len(reader.fieldnames or ()):
                raise ValueError('Colonnes UNOOSA dupliquées')
            if not required.issubset(fields) or fields - required - optional:
                raise ValueError("Colonnes du CSV UNOOSA incorrectes")
            for row in reader:
                cospar = normalize_cospar(row["cospar_id"])
                if not cospar or any(not row[k].strip() for k in required):
                    raise ValueError("Extrait UNOOSA incomplet")
                url = urlparse(row["source_url"])
                if url.scheme not in {"http", "https"} or url.hostname not in {
                    "www.unoosa.org",
                    "unoosa.org",
                    "documents.un.org",
                    "docs.un.org",
                    "digitallibrary.un.org",
                }:
                    raise ValueError("URL de provenance officielle UNOOSA/ONU requise")
                date.fromisoformat(row["retrieved_on"])
                registration_date = _date(row.get("registration_date", "") or "")
                number = norad_number(row["norad_id"]) if row.get("norad_id") else None
                key = (cospar, row["state_of_registry"], row["registration_document"])
                if key in seen:
                    raise ValueError("Extrait UNOOSA dupliqué")
                seen.add(key)
                result.append(
                    RegistryRecord(
                        cospar,
                        row.get("object_name", "") or "",
                        row["state_of_registry"],
                        row["registration_document"],
                        registration_date,
                        row["source_url"],
                        row["retrieved_on"],
                        number,
                    )
                )
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ValueError(f"CSV UNOOSA local invalide : {exc}") from exc
    if not result:
        raise ValueError("CSV UNOOSA vide")
    return tuple(result)


def select_space_elements(elements, records, kinds, window):
    requested = set()
    if "satellites" in kinds:
        requested.add("PAY")
    if "debris" in kinds:
        requested.update(("R/B", "DEB"))
    selected = []
    skipped = Counter()
    for element in elements:
        record = records.get(element.norad_id)
        if record is None:
            skipped["sans fiche SATCAT"] += 1
            continue
        if element.cospar_id and record.cospar_id and element.cospar_id != record.cospar_id:
            raise ValueError(f"Conflit COSPAR GP/SATCAT pour NORAD {element.norad_id}")
        if record.object_type not in requested:
            skipped["type non sélectionné"] += 1
            continue
        if record.orbit_center not in ("", "EA") or record.orbit_type not in ("", "ORB"):
            skipped["hors orbite terrestre indépendante"] += 1
            continue
        if record.decay_date:
            decay = datetime.fromisoformat(record.decay_date.replace("Z", "+00:00"))
            if decay.tzinfo is None:
                decay = decay.replace(tzinfo=timezone.utc)
            if window.end_local >= decay:
                skipped["rentrée signalée avant la fin"] += 1
                continue
        selected.append(element)
    return tuple(selected), dict(skipped)


def annotate_space_catalog(results, records, registry_records=()):
    counts = Counter(record.cospar_id for record in records.values() if record.cospar_id)
    result = []
    for entry in results:
        target = entry.star
        if not isinstance(target, SatelliteTarget):
            result.append(entry)
            continue
        record = records[target.norad_id]
        cospar = record.cospar_id or target.cospar_id
        label = (
            f"SATCAT/NORAD {record.norad_id}; COSPAR {cospar or 'non fourni'}; "
            f"type {record.object_type}; propriétaire SATCAT {record.owner or 'non fourni'}; "
            f"lancement {record.launch_date or 'non fourni'}."
        )
        matches = [r for r in registry_records if r.cospar_id == cospar]
        if matches and counts[cospar] > 1:
            label += " Registre ONU : COSPAR partagé, correspondance administrative indéterminée."
        elif matches:
            for row in matches:
                if row.norad_id is not None and row.norad_id != target.norad_id:
                    raise ValueError("Conflit NORAD dans un extrait UNOOSA correspondant au COSPAR")
                label += (
                    f" Registre ONU (extrait local) : {row.state_of_registry}; "
                    f"{row.registration_document}; date {row.registration_date or 'non fournie'}; "
                    f"récupéré {row.retrieved_on}; {row.source_url}."
                )
        else:
            label += " Registre ONU : aucune information locale correspondante (statut inconnu)."
        target = replace(
            target,
            cospar_id=cospar,
            object_type={"PAY": "Satellite", "R/B": "Corps de fusée", "DEB": "Débris"}[
                record.object_type
            ],
        )
        result.append(replace(entry, star=target, space_catalog_details=label))
    return result
