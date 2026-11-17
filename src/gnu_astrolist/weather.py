# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prévisions validées et agrégées par instant, avec repli par fournisseur."""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from http.client import HTTPException
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from . import __version__
from .models import ObservationWindow, WeatherPeriodSummary, WeatherSummary

OPEN_METEO_ENDPOINT = "https://api.open-meteo.com/v1/forecast"
SEVEN_TIMER_ENDPOINT = "https://www.7timer.info/bin/api.pl"
WEATHER_TIMEOUT_SECONDS = 10
MAX_WEATHER_BYTES = 2 * 1024 * 1024
MAX_WEATHER_SAMPLES = 1_000
SOLAR_FALLBACK_WARNING = (
    "Open-Meteo : horaires solaires indisponibles; périodes de repli 20–23 h et 3–6 h locales"
)
USER_AGENT = f"GNU-Astrolist/{__version__}"
HOURLY_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation_probability",
    "cloud_cover",
    "visibility",
    "wind_speed_10m",
    "cape",
)
SEEING_DESCRIPTIONS = (
    "< 0.5″",
    "0.5–0.75″",
    "0.75–1″",
    "1–1.25″",
    "1.25–1.5″",
    "1.5–2″",
    "2–2.5″",
    "> 2.5″",
)
TRANSPARENCY_DESCRIPTIONS = (
    "< 0.3 mag/masse d'air",
    "0.3–0.4 mag/masse d'air",
    "0.4–0.5 mag/masse d'air",
    "0.5–0.6 mag/masse d'air",
    "0.6–0.7 mag/masse d'air",
    "0.7–0.85 mag/masse d'air",
    "0.85–1 mag/masse d'air",
    "> 1 mag/masse d'air",
)
LIFTED_INDEX_LEVELS = (-10, -6, -4, -1, 2, 6, 10, 15)
MEASURE_LIMITS = {
    "temperature_2m": (-150.0, 100.0),
    "dew_point_2m": (-150.0, 100.0),
    "relative_humidity_2m": (0.0, 100.0),
    "cloud_cover": (0.0, 100.0),
    "wind_speed_10m": (0.0, 1_000.0),
    "precipitation_probability": (0.0, 100.0),
}
MEASURE_UNITS = {
    "temperature_2m": "°C",
    "dew_point_2m": "°C",
    "relative_humidity_2m": "%",
    "cloud_cover": "%",
    "wind_speed_10m": "km/h",
    "precipitation_probability": "%",
}
MEASURE_LABELS = {
    "temperature_2m": "température",
    "dew_point_2m": "point de rosée",
    "relative_humidity_2m": "humidité",
    "cloud_cover": "nuages",
    "wind_speed_10m": "vent",
    "precipitation_probability": "précipitations",
    "seeing": "seeing",
    "transparency": "transparence",
    "lifted_index": "stabilité",
}
Samples = dict[datetime, dict[str, float | None]]


class WeatherDataError(RuntimeError):
    """Erreur de récupération ou de structure d'une source météo."""


def _read_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    try:
        with urlopen(request, timeout=WEATHER_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise WeatherDataError("statut HTTP inattendu")
            if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                raise WeatherDataError("encodage HTTP non pris en charge")
            length = response.headers.get("Content-Length")
            if length is not None and (int(length) < 0 or int(length) > MAX_WEATHER_BYTES):
                raise WeatherDataError("taille de réponse excessive")
            content = response.read(MAX_WEATHER_BYTES + 1)
        if not content or len(content) > MAX_WEATHER_BYTES:
            raise WeatherDataError("taille de réponse vide ou excessive")
        payload = json.loads(
            content.decode("utf-8-sig"),
            parse_constant=_invalid_constant,
            object_pairs_hook=_unique_keys,
        )
    except (OSError, HTTPException, ValueError, UnicodeError, RecursionError) as exc:
        raise WeatherDataError("service inaccessible ou réponse JSON invalide") from exc
    if not isinstance(payload, dict):
        raise WeatherDataError("réponse JSON inattendue")
    return payload


def _invalid_constant(value: str):
    raise ValueError("Constante JSON non finie")


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Clé JSON dupliquée")
        result[key] = value
    return result


def _warn(warnings: list[str], message: str) -> None:
    if message not in warnings:
        warnings.append(message)


def _number(value: Any, low: float, high: float) -> float | None:
    if type(value) not in (int, float):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    return number if math.isfinite(number) and low <= number <= high else None


def _series(value: Any) -> list:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_WEATHER_SAMPLES:
        raise WeatherDataError("série absente, invalide ou trop longue")
    return value


def _evening_date(window: ObservationWindow) -> date:
    local_date = window.start_local.date()
    return local_date - timedelta(days=1) if window.start_local.hour < 12 else local_date


def _fallback_periods(
    window: ObservationWindow,
) -> tuple[WeatherPeriodSummary, WeatherPeriodSummary]:
    timezone_info = window.start_local.tzinfo
    if timezone_info is None:
        raise ValueError("la plage d'observation doit avoir un fuseau horaire")
    evening_date = _evening_date(window)
    evening_start = datetime.combine(evening_date, time(20), tzinfo=timezone_info)
    predawn_end = datetime.combine(evening_date + timedelta(days=1), time(6), tzinfo=timezone_info)
    return (
        WeatherPeriodSummary(
            name="SOIRÉE",
            start_local=evening_start,
            end_local=evening_start + timedelta(hours=3),
        ),
        WeatherPeriodSummary(
            name="AVANT L'AUBE",
            start_local=predawn_end - timedelta(hours=3),
            end_local=predawn_end,
        ),
    )


def _open_meteo_url(
    *,
    window: ObservationWindow,
    latitude_deg: float,
    longitude_deg: float,
) -> str:
    evening_date = _evening_date(window)
    params = {
        "latitude": f"{latitude_deg:.5f}",
        "longitude": f"{longitude_deg:.5f}",
        "hourly": ",".join(HOURLY_VARIABLES),
        "daily": "sunrise,sunset",
        "timezone": window.timezone_name,
        "start_date": evening_date.isoformat(),
        "end_date": (evening_date + timedelta(days=1)).isoformat(),
        "wind_speed_unit": "kmh",
        "temperature_unit": "celsius",
    }
    return f"{OPEN_METEO_ENDPOINT}?{urlencode(params)}"


def _seven_timer_url(latitude_deg: float, longitude_deg: float) -> str:
    params = {
        "lon": f"{longitude_deg:.3f}",
        "lat": f"{latitude_deg:.3f}",
        "product": "astro",
        "output": "json",
    }
    return f"{SEVEN_TIMER_ENDPOINT}?{urlencode(params)}"


def _local_datetime(value: str, timezone_info: tzinfo) -> datetime:
    if not isinstance(value, str) or not 16 <= len(value) <= 64 or value[10] != "T":
        raise WeatherDataError("horodatage invalide")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
        if parsed.tzinfo is not None:
            return parsed.astimezone(timezone_info)
        candidate = parsed.replace(tzinfo=timezone_info)
        round_trip = candidate.astimezone(timezone.utc).astimezone(timezone_info)
        if round_trip.replace(tzinfo=None) != parsed:
            raise WeatherDataError("heure civile inexistante")
        if candidate.utcoffset() != candidate.replace(fold=1).utcoffset():
            raise WeatherDataError("heure civile ambiguë")
        return candidate
    except (ValueError, OverflowError) as exc:
        raise WeatherDataError("horodatage invalide") from exc


def _periods_from_open_meteo(
    payload: dict[str, Any], window: ObservationWindow
) -> tuple[WeatherPeriodSummary, WeatherPeriodSummary]:
    timezone_info = window.start_local.tzinfo
    if timezone_info is None:
        raise ValueError("la plage d'observation doit avoir un fuseau horaire")
    try:
        daily = payload["daily"]
        sunset = _local_datetime(_series(daily["sunset"])[0], timezone_info)
        next_sunrise = _local_datetime(_series(daily["sunrise"])[1], timezone_info)
        if sunset.date() != _evening_date(window) or next_sunrise.date() != _evening_date(
            window
        ) + timedelta(days=1):
            raise WeatherDataError("dates solaires incohérentes")
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise WeatherDataError("heures solaires manquantes") from exc
    return (
        WeatherPeriodSummary(
            name="SOIRÉE",
            start_local=sunset,
            end_local=sunset + timedelta(hours=3),
        ),
        WeatherPeriodSummary(
            name="AVANT L'AUBE",
            start_local=next_sunrise - timedelta(hours=3),
            end_local=next_sunrise,
        ),
    )


def _mean(values: Sequence[float]) -> float | None:
    return math.fsum(values) / len(values) if values else None


def _hourly_samples(payload: dict, zone: tzinfo, warnings: list[str]) -> Samples:
    if not isinstance(payload, dict) or not isinstance(payload.get("hourly"), dict):
        raise WeatherDataError("table horaire manquante")
    hourly = payload["hourly"]
    times = [
        _local_datetime(value, zone).astimezone(timezone.utc)
        for value in _series(hourly.get("time"))
    ]
    if any(right <= left for left, right in zip(times, times[1:])):
        raise WeatherDataError("horodatages horaires dupliqués ou non croissants")
    units = payload.get("hourly_units")
    if units is not None and not isinstance(units, dict):
        raise WeatherDataError("unités horaires invalides")
    rows: Samples = {instant: {} for instant in times}
    for field, bounds in MEASURE_LIMITS.items():
        label = MEASURE_LABELS[field]
        values = hourly.get(field)
        if not isinstance(values, list) or len(values) != len(times):
            _warn(
                warnings, f"Open-Meteo : données partielles, {label} absent ou longueur incohérente"
            )
            numbers = [None] * len(times)
        elif units is not None and units.get(field) != MEASURE_UNITS[field]:
            _warn(warnings, f"Open-Meteo : données partielles, unité invalide pour {label}")
            numbers = [None] * len(times)
        else:
            numbers = [_number(value, *bounds) for value in values]
            if any(value is None for value in numbers):
                _warn(
                    warnings,
                    f"Open-Meteo : données partielles, valeurs absentes ou invalides pour {label}",
                )
        for instant, value in zip(times, numbers, strict=True):
            rows[instant][field] = value
    return rows


def _period_rows(samples: Samples, period: WeatherPeriodSummary) -> list[dict[str, float | None]]:
    start, end = (
        value.astimezone(timezone.utc) for value in (period.start_local, period.end_local)
    )
    return [row for instant, row in samples.items() if start <= instant <= end]


def _values(rows: list[dict[str, float | None]], field: str) -> list[float]:
    return [row[field] for row in rows if row[field] is not None]


def _dew_risk(triplets: Sequence[tuple[float, float, float]]) -> str:
    if not triplets:
        return ""
    minimum_spread = min(temperature - dew_point for temperature, dew_point, _ in triplets)
    maximum_humidity = max(humidity for _, _, humidity in triplets)
    if minimum_spread <= 1.0 or maximum_humidity >= 95.0:
        return "très élevé"
    if minimum_spread <= 2.0 or maximum_humidity >= 90.0:
        return "élevé"
    if minimum_spread <= 4.0 or maximum_humidity >= 80.0:
        return "modéré"
    return "faible"


def _add_open_meteo_data(
    period: WeatherPeriodSummary,
    samples: Samples,
) -> WeatherPeriodSummary:
    rows = _period_rows(samples, period)
    precipitation = _values(rows, "precipitation_probability")
    triplets = [
        (row["temperature_2m"], row["dew_point_2m"], row["relative_humidity_2m"])
        for row in rows
        if all(
            row[field] is not None
            for field in ("temperature_2m", "dew_point_2m", "relative_humidity_2m")
        )
    ]
    return replace(
        period,
        cloud_cover_percent=_mean(_values(rows, "cloud_cover")),
        temperature_c=_mean(_values(rows, "temperature_2m")),
        humidity_percent=_mean(_values(rows, "relative_humidity_2m")),
        wind_kmh=_mean(_values(rows, "wind_speed_10m")),
        dew_risk=_dew_risk(triplets),
        precipitation_probability_percent=(max(precipitation) if precipitation else None),
    )


def _astro_samples(payload: dict, warnings: list[str]) -> Samples:
    if not isinstance(payload, dict) or not isinstance(payload.get("init"), str):
        raise WeatherDataError("initialisation astronomique manquante")
    try:
        if len(payload["init"]) != 10:
            raise WeatherDataError("initialisation astronomique invalide")
        initialized = datetime.strptime(payload["init"], "%Y%m%d%H").replace(tzinfo=timezone.utc)
        data = _series(payload.get("dataseries"))
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherDataError("prévision astronomique mal formée") from exc
    samples: Samples = {}
    for item in data:
        if not isinstance(item, dict):
            _warn(warnings, "7Timer! : données partielles, échantillon invalide")
            continue
        offset = _number(item.get("timepoint"), 0, 72)
        if offset is None:
            _warn(warnings, "7Timer! : données partielles, échéance invalide")
            continue
        try:
            instant = initialized + timedelta(hours=offset)
        except OverflowError:
            _warn(warnings, "7Timer! : données partielles, échéance hors calendrier")
            continue
        if samples and instant <= next(reversed(samples)):
            raise WeatherDataError("échéances astronomiques dupliquées ou non croissantes")
        row = {}
        for field in ("seeing", "transparency", "lifted_index"):
            value = (
                _number(item.get(field), -10, 15)
                if field == "lifted_index"
                else _number(item.get(field), 1, 8)
            )
            allowed = LIFTED_INDEX_LEVELS if field == "lifted_index" else range(1, 9)
            if value not in allowed:
                value = None
                _warn(
                    warnings,
                    f"7Timer! : données partielles, valeur absente ou invalide pour {MEASURE_LABELS[field]}",
                )
            row[field] = value
        samples[instant] = row
    return samples


def _category_quality(category: float) -> float:
    return max(0.0, min(100.0, (8.0 - category) / 7.0 * 100.0))


def _category_description(category: float, descriptions: Sequence[str]) -> str:
    index = max(1, min(8, round(category))) - 1
    return descriptions[index]


def _stability_quality(lifted_index: float) -> float:
    nearest_index = min(
        range(len(LIFTED_INDEX_LEVELS)),
        key=lambda index: abs(LIFTED_INDEX_LEVELS[index] - lifted_index),
    )
    return nearest_index / (len(LIFTED_INDEX_LEVELS) - 1) * 100.0


def _add_astro_data(period: WeatherPeriodSummary, samples: Samples) -> WeatherPeriodSummary:
    rows = _period_rows(samples, period)
    seeing = _values(rows, "seeing")
    transparency = _values(rows, "transparency")
    lifted_indices = _values(rows, "lifted_index")
    mean_seeing = _mean(seeing)
    mean_transparency = _mean(transparency)
    return replace(
        period,
        seeing_quality_percent=(
            _category_quality(mean_seeing) if mean_seeing is not None else None
        ),
        seeing_description=(
            _category_description(mean_seeing, SEEING_DESCRIPTIONS)
            if mean_seeing is not None
            else ""
        ),
        transparency_quality_percent=(
            _category_quality(mean_transparency) if mean_transparency is not None else None
        ),
        transparency_description=(
            _category_description(mean_transparency, TRANSPARENCY_DESCRIPTIONS)
            if mean_transparency is not None
            else ""
        ),
        stability_quality_percent=(
            _mean([_stability_quality(value) for value in lifted_indices])
            if lifted_indices
            else None
        ),
    )


def compute_weather_summary(
    *,
    window: ObservationWindow,
    latitude_deg: float,
    longitude_deg: float,
    offline: bool,
) -> WeatherSummary:
    """Récupère et agrège les conditions de soirée et d'avant l'aube."""

    evening, predawn = _fallback_periods(window)
    if offline:
        return WeatherSummary(
            evening=evening,
            predawn=predawn,
            warnings=("prévisions désactivées par --offline",),
            offline=True,
        )

    warnings: list[str] = []
    sources: list[str] = []
    solar_times_known = False
    try:
        open_meteo = _read_json(
            _open_meteo_url(
                window=window,
                latitude_deg=latitude_deg,
                longitude_deg=longitude_deg,
            )
        )
        timezone_info = window.start_local.tzinfo
        try:
            evening, predawn = _periods_from_open_meteo(open_meteo, window)
            solar_times_known = True
        except WeatherDataError:
            _warn(warnings, SOLAR_FALLBACK_WARNING)
        samples = _hourly_samples(open_meteo, timezone_info, warnings)
        evening, predawn = (_add_open_meteo_data(period, samples) for period in (evening, predawn))
        if WeatherSummary(evening, predawn).available:
            sources.append("Open-Meteo")
        else:
            _warn(warnings, "Open-Meteo : aucune mesure valide dans les périodes demandées")
    except WeatherDataError:
        warnings.append("données météorologiques Open-Meteo indisponibles")
        if not solar_times_known:
            _warn(warnings, SOLAR_FALLBACK_WARNING)

    try:
        seven_timer = _read_json(_seven_timer_url(latitude_deg, longitude_deg))
        samples = _astro_samples(seven_timer, warnings)
        evening, predawn = (_add_astro_data(period, samples) for period in (evening, predawn))
        if any(
            value is not None
            for value in (
                evening.seeing_quality_percent,
                predawn.seeing_quality_percent,
                evening.transparency_quality_percent,
                predawn.transparency_quality_percent,
                evening.stability_quality_percent,
                predawn.stability_quality_percent,
            )
        ):
            sources.append("7Timer! ASTRO")
        else:
            warnings.append("indices astronomiques hors de la plage de prévision")
    except WeatherDataError:
        warnings.append("indices astronomiques 7Timer! indisponibles")

    return WeatherSummary(
        evening=evening,
        predawn=predawn,
        sources=" + ".join(sources),
        warnings=tuple(warnings),
    )
