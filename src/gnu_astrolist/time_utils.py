# SPDX-FileCopyrightText: 2026 Steve Prud'Homme
# SPDX-License-Identifier: GPL-3.0-or-later
"""Analyse fiable des dates, heures et fuseaux horaires."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .models import ObservationWindow


def parse_date(value: str) -> date:
    """Analyse une date ISO ``AAAA-MM-JJ``."""

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("la date doit respecter le format AAAA-MM-JJ") from exc


def parse_clock(value: str) -> time:
    """Analyse une heure civile ``HH:MM`` ou ``HH:MM:SS``."""

    try:
        parsed = time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("les heures doivent respecter le format HH:MM ou HH:MM:SS") from exc
    if parsed.tzinfo is not None:
        raise ValueError("n'ajoutez pas de décalage UTC dans --time-range; utilisez --timezone")
    return parsed


def _validated_local_datetime(day: date, clock: time, zone: ZoneInfo) -> datetime:
    candidate = datetime.combine(day, clock, tzinfo=zone)
    round_trip = candidate.astimezone(timezone.utc).astimezone(zone)
    if round_trip.replace(tzinfo=None) != candidate.replace(tzinfo=None):
        raise ValueError(
            f"l'heure locale {candidate:%Y-%m-%d %H:%M:%S} n'existe pas dans le fuseau {zone.key}"
        )
    alternate = candidate.replace(fold=1)
    if candidate.utcoffset() != alternate.utcoffset():
        raise ValueError(
            f"l'heure locale {candidate:%Y-%m-%d %H:%M:%S} est ambiguë dans le fuseau "
            f"{zone.key} à cause du changement d'heure"
        )
    return candidate


def parse_observation_window(
    observation_date: str,
    time_range: str,
    timezone_name: str,
) -> ObservationWindow:
    """Construit une plage; une fin antérieure ou égale passe au lendemain."""

    parts = time_range.split("-")
    if len(parts) != 2 or not all(part.strip() for part in parts):
        raise ValueError("la plage horaire doit respecter le format HH:MM-HH:MM")

    day = parse_date(observation_date)
    start_clock, end_clock = (parse_clock(part.strip()) for part in parts)
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"fuseau horaire IANA inconnu : {timezone_name}") from exc

    end_day = day + timedelta(days=1) if end_clock <= start_clock else day
    start = _validated_local_datetime(day, start_clock, zone)
    end = _validated_local_datetime(end_day, end_clock, zone)
    if end.astimezone(timezone.utc) <= start.astimezone(timezone.utc):
        raise ValueError("la plage horaire doit avoir une durée positive")

    return ObservationWindow(start, end, timezone_name)
