"""Prévisions météo civiles et astronomiques pour la nuit d'observation."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import ObservationWindow, WeatherPeriodSummary, WeatherSummary

OPEN_METEO_ENDPOINT = "https://api.open-meteo.com/v1/forecast"
SEVEN_TIMER_ENDPOINT = "https://www.7timer.info/bin/api.pl"
WEATHER_TIMEOUT_SECONDS = 10
USER_AGENT = "GNU-Astrolist/0.9"
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
    '< 0.5″',
    '0.5–0.75″',
    '0.75–1″',
    '1–1.25″',
    '1.25–1.5″',
    '1.5–2″',
    '2–2.5″',
    '> 2.5″',
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


class WeatherDataError(RuntimeError):
    """Erreur de récupération ou de structure d'une source météo."""


def _read_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=WEATHER_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except Exception as exc:
        raise WeatherDataError("service inaccessible") from exc
    if not isinstance(payload, dict):
        raise WeatherDataError("réponse JSON inattendue")
    return payload


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
    predawn_end = datetime.combine(
        evening_date + timedelta(days=1), time(6), tzinfo=timezone_info
    )
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
    return datetime.fromisoformat(value).replace(tzinfo=timezone_info)


def _periods_from_open_meteo(
    payload: dict[str, Any], window: ObservationWindow
) -> tuple[WeatherPeriodSummary, WeatherPeriodSummary]:
    timezone_info = window.start_local.tzinfo
    if timezone_info is None:
        raise ValueError("la plage d'observation doit avoir un fuseau horaire")
    try:
        daily = payload["daily"]
        sunset = _local_datetime(str(daily["sunset"][0]), timezone_info)
        next_sunrise = _local_datetime(str(daily["sunrise"][1]), timezone_info)
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
    return sum(values) / len(values) if values else None


def _hourly_values(
    payload: dict[str, Any],
    variable: str,
    period: WeatherPeriodSummary,
    timezone_info: tzinfo,
) -> list[float]:
    try:
        hourly = payload["hourly"]
        times = hourly["time"]
        values = hourly[variable]
    except (KeyError, TypeError) as exc:
        raise WeatherDataError(f"variable {variable} manquante") from exc
    selected: list[float] = []
    for raw_time, raw_value in zip(times, values, strict=False):
        if raw_value is None:
            continue
        instant = _local_datetime(str(raw_time), timezone_info)
        if period.start_local <= instant <= period.end_local:
            selected.append(float(raw_value))
    return selected


def _dew_risk(
    temperatures: Sequence[float],
    dew_points: Sequence[float],
    humidity: Sequence[float],
) -> str:
    if not temperatures or not dew_points or not humidity:
        return ""
    minimum_spread = min(
        temperature - dew_point
        for temperature, dew_point in zip(temperatures, dew_points, strict=False)
    )
    maximum_humidity = max(humidity)
    if minimum_spread <= 1.0 or maximum_humidity >= 95.0:
        return "très élevé"
    if minimum_spread <= 2.0 or maximum_humidity >= 90.0:
        return "élevé"
    if minimum_spread <= 4.0 or maximum_humidity >= 80.0:
        return "modéré"
    return "faible"


def _add_open_meteo_data(
    period: WeatherPeriodSummary,
    payload: dict[str, Any],
    timezone_info: tzinfo,
) -> WeatherPeriodSummary:
    temperatures = _hourly_values(payload, "temperature_2m", period, timezone_info)
    humidity = _hourly_values(payload, "relative_humidity_2m", period, timezone_info)
    dew_points = _hourly_values(payload, "dew_point_2m", period, timezone_info)
    cloud_cover = _hourly_values(payload, "cloud_cover", period, timezone_info)
    wind = _hourly_values(payload, "wind_speed_10m", period, timezone_info)
    precipitation = _hourly_values(
        payload, "precipitation_probability", period, timezone_info
    )
    return replace(
        period,
        cloud_cover_percent=_mean(cloud_cover),
        temperature_c=_mean(temperatures),
        humidity_percent=_mean(humidity),
        wind_kmh=_mean(wind),
        dew_risk=_dew_risk(temperatures, dew_points, humidity),
        precipitation_probability_percent=(
            max(precipitation) if precipitation else None
        ),
    )


def _astro_samples(
    payload: dict[str, Any], period: WeatherPeriodSummary
) -> list[dict[str, Any]]:
    try:
        initialized = datetime.strptime(str(payload["init"]), "%Y%m%d%H").replace(
            tzinfo=timezone.utc
        )
        data = payload["dataseries"]
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherDataError("prévision astronomique mal formée") from exc
    samples: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            instant = initialized + timedelta(hours=float(item["timepoint"]))
        except (KeyError, TypeError, ValueError):
            continue
        local_instant = instant.astimezone(period.start_local.tzinfo)
        if period.start_local <= local_instant <= period.end_local:
            samples.append(item)
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


def _add_astro_data(
    period: WeatherPeriodSummary, payload: dict[str, Any]
) -> WeatherPeriodSummary:
    samples = _astro_samples(payload, period)
    seeing = [float(sample["seeing"]) for sample in samples if "seeing" in sample]
    transparency = [
        float(sample["transparency"])
        for sample in samples
        if "transparency" in sample
    ]
    lifted_indices = [
        float(sample["lifted_index"])
        for sample in samples
        if "lifted_index" in sample
    ]
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
            _category_quality(mean_transparency)
            if mean_transparency is not None
            else None
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
    try:
        open_meteo = _read_json(
            _open_meteo_url(
                window=window,
                latitude_deg=latitude_deg,
                longitude_deg=longitude_deg,
            )
        )
        evening, predawn = _periods_from_open_meteo(open_meteo, window)
        timezone_info = window.start_local.tzinfo
        evening = _add_open_meteo_data(evening, open_meteo, timezone_info)
        predawn = _add_open_meteo_data(predawn, open_meteo, timezone_info)
        sources.append("Open-Meteo")
    except (WeatherDataError, ValueError):
        warnings.append("données météorologiques Open-Meteo indisponibles")

    try:
        seven_timer = _read_json(_seven_timer_url(latitude_deg, longitude_deg))
        evening = _add_astro_data(evening, seven_timer)
        predawn = _add_astro_data(predawn, seven_timer)
        if any(
            value is not None
            for value in (
                evening.seeing_quality_percent,
                predawn.seeing_quality_percent,
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
