from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from gnu_astrolist.models import ObservationWindow
from gnu_astrolist.weather import compute_weather_summary


def _window() -> ObservationWindow:
    timezone = ZoneInfo("America/Toronto")
    return ObservationWindow(
        start_local=datetime(2026, 8, 3, 21, 0, tzinfo=timezone),
        end_local=datetime(2026, 8, 3, 22, 0, tzinfo=timezone),
        timezone_name="America/Toronto",
    )


def _open_meteo_payload() -> dict:
    times = [
        "2026-08-03T20:00",
        "2026-08-03T21:00",
        "2026-08-03T22:00",
        "2026-08-03T23:00",
        "2026-08-04T03:00",
        "2026-08-04T04:00",
        "2026-08-04T05:00",
        "2026-08-04T06:00",
    ]
    return {
        "daily": {
            "sunset": ["2026-08-03T20:00", "2026-08-04T19:59"],
            "sunrise": ["2026-08-03T05:40", "2026-08-04T06:00"],
        },
        "hourly": {
            "time": times,
            "temperature_2m": [15, 14, 13, 12, 11, 10, 9, 8],
            "relative_humidity_2m": [70, 80, 85, 90, 91, 92, 93, 94],
            "dew_point_2m": [12, 12, 12, 11, 9, 9, 8, 7],
            "precipitation_probability": [10, 20, 30, 40, 5, 10, 15, 20],
            "cloud_cover": [10, 20, 30, 40, 50, 60, 70, 80],
            "visibility": [20000] * 8,
            "wind_speed_10m": [5, 6, 7, 8, 9, 10, 11, 12],
            "cape": [0] * 8,
        },
    }


def _seven_timer_payload() -> dict:
    return {
        "init": "2026080312",
        "dataseries": [
            {"timepoint": 12, "seeing": 2, "transparency": 3, "lifted_index": -1},
            {"timepoint": 15, "seeing": 4, "transparency": 5, "lifted_index": 6},
            {"timepoint": 19, "seeing": 6, "transparency": 7, "lifted_index": 10},
            {"timepoint": 22, "seeing": 8, "transparency": 8, "lifted_index": 15},
        ],
    }


def test_weather_summary_aggregates_both_periods(monkeypatch) -> None:
    def fake_read_json(url: str) -> dict:
        return _open_meteo_payload() if "open-meteo" in url else _seven_timer_payload()

    monkeypatch.setattr("gnu_astrolist.weather._read_json", fake_read_json)

    summary = compute_weather_summary(
        window=_window(),
        latitude_deg=45.57,
        longitude_deg=-73.68,
        offline=False,
    )

    assert summary.sources == "Open-Meteo + 7Timer! ASTRO"
    assert summary.evening.start_local.hour == 20
    assert summary.evening.end_local.hour == 23
    assert summary.predawn.start_local.hour == 3
    assert summary.predawn.end_local.hour == 6
    assert summary.evening.cloud_cover_percent == pytest.approx(25)
    assert summary.evening.temperature_c == pytest.approx(13.5)
    assert summary.evening.precipitation_probability_percent == 40
    assert summary.evening.dew_risk == "très élevé"
    assert summary.evening.seeing_quality_percent == pytest.approx(71.43, abs=0.01)
    assert summary.evening.seeing_description == "0.75–1″"
    assert summary.evening.transparency_quality_percent == pytest.approx(57.14, abs=0.01)
    assert summary.evening.stability_quality_percent == pytest.approx(57.14, abs=0.01)
    assert summary.predawn.cloud_cover_percent == pytest.approx(65)
    assert summary.predawn.seeing_quality_percent == pytest.approx(14.29, abs=0.01)


def test_weather_summary_offline_does_not_call_a_provider(monkeypatch) -> None:
    def fail_if_called(url: str) -> dict:
        raise AssertionError(url)

    monkeypatch.setattr("gnu_astrolist.weather._read_json", fail_if_called)

    summary = compute_weather_summary(
        window=_window(),
        latitude_deg=45.57,
        longitude_deg=-73.68,
        offline=True,
    )

    assert summary.offline is True
    assert summary.available is False
    assert summary.warnings == ("prévisions désactivées par --offline",)
