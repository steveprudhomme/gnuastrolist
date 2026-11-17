# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""ECC-B : fournisseurs synthétiques, aucune connexion réseau réelle."""

import io
import json
import re
from copy import deepcopy
from urllib.error import URLError

import pytest

from gnu_astrolist import weather
from gnu_astrolist.time_utils import parse_observation_window


def window():
    return parse_observation_window("2026-08-03", "21:00-22:00", "UTC")


def meteo():
    return {
        "daily": {
            "sunset": ["2026-08-03T21:00", "2026-08-04T21:00"],
            "sunrise": ["2026-08-03T06:00", "2026-08-04T06:00"],
        },
        "hourly": {
            "time": [
                "2026-08-03T21:00",
                "2026-08-03T22:00",
                "2026-08-04T03:00",
                "2026-08-04T06:00",
            ],
            "temperature_2m": [14, 13, 10, 9],
            "dew_point_2m": [12, 12, 8, 7],
            "relative_humidity_2m": [70, 80, 90, 91],
            "cloud_cover": [10, 20, 30, 40],
            "wind_speed_10m": [5, 6, 7, 8],
            "precipitation_probability": [0, 10, 20, 30],
        },
    }


def astro():
    return {
        "init": "2026080312",
        "dataseries": [
            {"timepoint": 9, "seeing": 2, "transparency": 3, "lifted_index": -1},
            {"timepoint": 18, "seeing": 4, "transparency": 5, "lifted_index": 6},
        ],
    }


def summary(monkeypatch, civil=None, astronomy=None, observation=None):
    def read(url):
        payload = civil if "open-meteo" in url else astronomy
        if isinstance(payload, Exception):
            raise payload
        return deepcopy(payload)

    monkeypatch.setattr(weather, "_read_json", read)
    return weather.compute_weather_summary(
        window=observation or window(), latitude_deg=45, longitude_deg=0, offline=False
    )


def test_dew_risk_uses_same_instant_triplets(monkeypatch):
    payload = meteo()
    payload["hourly"]["temperature_2m"][:2] = [5, 20]
    payload["hourly"]["dew_point_2m"][:2] = [None, 10]
    payload["hourly"]["relative_humidity_2m"][:2] = [70, 70]
    result = summary(monkeypatch, payload, astro())
    assert result.evening.dew_risk == "faible"
    assert any("partiell" in warning for warning in result.warnings)


@pytest.mark.parametrize("value", [None, True, "2", float("nan"), float("inf"), 0, 9, 2.5])
def test_invalid_seeing_does_not_hide_transparency_or_crash(monkeypatch, value):
    payload = astro()
    payload["dataseries"][0]["seeing"] = value
    result = summary(monkeypatch, meteo(), payload)
    assert result.evening.seeing_quality_percent is None
    assert result.evening.transparency_quality_percent is not None
    assert "7Timer! ASTRO" in result.sources
    assert any("partiell" in warning for warning in result.warnings)


@pytest.mark.parametrize(
    "field,value",
    [
        ("temperature_2m", float("inf")),
        ("temperature_2m", -300),
        ("dew_point_2m", True),
        ("relative_humidity_2m", 101),
        ("relative_humidity_2m", -1),
        ("cloud_cover", float("nan")),
        ("wind_speed_10m", -1),
        ("precipitation_probability", "20"),
    ],
)
def test_invalid_civil_measurements_are_omitted(monkeypatch, field, value):
    payload = meteo()
    payload["hourly"][field] = [value] * 4
    result = summary(monkeypatch, payload, astro())
    assert result.available
    assert result.warnings
    if field == "cloud_cover":
        assert result.evening.cloud_cover_percent is None
    if field in {"temperature_2m", "dew_point_2m", "relative_humidity_2m"}:
        assert result.evening.dew_risk == ""


def test_mismatched_series_is_not_silently_truncated(monkeypatch):
    payload = meteo()
    payload["hourly"]["relative_humidity_2m"] = [99]
    result = summary(monkeypatch, payload, astro())
    assert result.evening.humidity_percent is None
    assert result.evening.dew_risk == ""
    assert result.evening.temperature_c == 13.5
    assert any("longueur" in warning for warning in result.warnings)


def test_temperature_only_is_still_available(monkeypatch):
    payload = meteo()
    payload["hourly"] = {
        k: v for k, v in payload["hourly"].items() if k in {"time", "temperature_2m"}
    }
    result = summary(monkeypatch, payload, weather.WeatherDataError("simulé"))
    assert result.available
    assert result.evening.temperature_c == 13.5
    assert result.evening.dew_risk == ""
    assert "Open-Meteo" in result.sources


@pytest.mark.parametrize("payload", [None, [], "invalid", {}, {"hourly": []}])
def test_invalid_civil_structure_preserves_astronomical_provider(monkeypatch, payload):
    result = summary(monkeypatch, payload, astro())
    assert result.evening.seeing_quality_percent is not None
    assert result.evening.temperature_c is None
    assert "indisponibles" in " ".join(result.warnings)


@pytest.mark.parametrize(
    "payload",
    [None, [], {}, {"init": "bad", "dataseries": []}, {"init": "2026080312", "dataseries": {}}],
)
def test_invalid_astronomical_structure_preserves_civil_provider(monkeypatch, payload):
    result = summary(monkeypatch, meteo(), payload)
    assert result.evening.temperature_c == 13.5
    assert result.evening.seeing_quality_percent is None
    assert "indisponibles" in " ".join(result.warnings)


def test_missing_solar_times_keep_valid_hourly_values_and_warn(monkeypatch):
    payload = meteo()
    payload["daily"] = None
    result = summary(monkeypatch, payload, astro())
    assert result.evening.start_local.hour == 20
    assert result.evening.temperature_c == 13.5
    assert any("repli" in warning for warning in result.warnings)


def test_explicit_offset_is_converted_not_replaced():
    from zoneinfo import ZoneInfo

    instant = weather._local_datetime("2026-08-03T21:00:00Z", ZoneInfo("America/Toronto"))
    assert instant.hour == 17


@pytest.mark.parametrize("value", ["2026-11-01T01:30", "2026-03-08T02:30"])
def test_ambiguous_or_nonexistent_local_time_is_rejected(value):
    from zoneinfo import ZoneInfo

    with pytest.raises(weather.WeatherDataError):
        weather._local_datetime(value, ZoneInfo("America/Toronto"))


def test_duplicate_times_reject_civil_series_without_affecting_other_source(monkeypatch):
    payload = meteo()
    payload["hourly"]["time"][1] = payload["hourly"]["time"][0]
    result = summary(monkeypatch, payload, astro())
    assert result.evening.temperature_c is None
    assert result.evening.seeing_quality_percent is not None


@pytest.mark.parametrize("value", [None, -1, float("inf"), 1e308, True])
def test_invalid_forecast_timepoints_do_not_overflow(monkeypatch, value):
    payload = astro()
    payload["dataseries"][0]["timepoint"] = value
    result = summary(monkeypatch, meteo(), payload)
    assert result.evening.seeing_quality_percent is None
    assert result.predawn.seeing_quality_percent is not None
    assert result.warnings


def test_unexpected_programming_error_is_not_hidden(monkeypatch):
    with pytest.raises(AssertionError, match="programming"):
        summary(monkeypatch, AssertionError("programming error"), astro())


class Response(io.BytesIO):
    status = 200
    headers = {}


@pytest.mark.parametrize(
    "body", [b"invalid json", b"[]", b'{"value":NaN}', b"\xff", b'{"duplicate":1,"duplicate":2}']
)
def test_read_json_rejects_invalid_payload(monkeypatch, body):
    monkeypatch.setattr(weather, "urlopen", lambda *a, **kw: Response(body))
    with pytest.raises(weather.WeatherDataError):
        weather._read_json(weather.OPEN_METEO_ENDPOINT)


def test_read_json_is_bounded_and_timeout_is_explicit(monkeypatch):
    reads = []

    class Oversized(Response):
        def read(self, size=-1):
            reads.append(size)
            assert size == weather.MAX_WEATHER_BYTES + 1
            return b" " * size

    def fetch(request, *, timeout):
        assert timeout == weather.WEATHER_TIMEOUT_SECONDS
        return Oversized()

    monkeypatch.setattr(weather, "urlopen", fetch)
    with pytest.raises(weather.WeatherDataError, match="taille"):
        weather._read_json(weather.OPEN_METEO_ENDPOINT)
    assert len(reads) == 1


def test_transport_failure_is_a_weather_error(monkeypatch):
    def unavailable(*args, **kwargs):
        raise URLError("synthetic")

    monkeypatch.setattr(weather, "urlopen", unavailable)
    with pytest.raises(weather.WeatherDataError):
        weather._read_json(weather.OPEN_METEO_ENDPOINT)


def test_transport_does_not_mask_unexpected_programming_error(monkeypatch):
    def broken(*args, **kwargs):
        raise AssertionError("programming error")

    monkeypatch.setattr(weather, "urlopen", broken)
    with pytest.raises(AssertionError, match="programming"):
        weather._read_json(weather.OPEN_METEO_ENDPOINT)


def test_read_json_accepts_ordinary_object(monkeypatch):
    payload = {"synthetic": True}
    monkeypatch.setattr(weather, "urlopen", lambda *a, **kw: Response(json.dumps(payload).encode()))
    assert weather._read_json(weather.OPEN_METEO_ENDPOINT) == payload


def test_incompatible_temperature_unit_is_not_converted_or_displayed(monkeypatch):
    payload = meteo()
    payload["hourly_units"] = dict(weather.MEASURE_UNITS, temperature_2m="°F")
    result = summary(monkeypatch, payload, astro())
    assert result.evening.temperature_c is None
    assert result.evening.cloud_cover_percent == 15
    assert result.evening.dew_risk == ""
    assert "unité" in " ".join(result.warnings)


def test_explicit_valid_units_preserve_values_without_warning(monkeypatch):
    payload = meteo()
    payload["hourly_units"] = dict(weather.MEASURE_UNITS)
    result = summary(monkeypatch, payload, astro())
    assert result.evening.temperature_c == 13.5
    assert result.warnings == ()


def test_partial_second_period_does_not_erase_first_period(monkeypatch):
    payload = meteo()
    payload["hourly"]["temperature_2m"][2:] = [None, None]
    result = summary(monkeypatch, payload, astro())
    assert result.evening.temperature_c == 13.5
    assert result.predawn.temperature_c is None
    assert result.predawn.humidity_percent == 90.5
    assert result.predawn.dew_risk == ""


def test_no_complete_triplet_never_means_low_risk(monkeypatch):
    payload = meteo()
    payload["hourly"]["temperature_2m"] = [14, None, 10, None]
    payload["hourly"]["dew_point_2m"] = [None, 12, None, 7]
    result = summary(monkeypatch, payload, astro())
    assert result.evening.temperature_c == 14
    assert result.evening.dew_risk == result.predawn.dew_risk == ""


def test_transparency_only_provider_is_available(monkeypatch):
    payload = astro()
    for row in payload["dataseries"]:
        row["seeing"] = row["lifted_index"] = None
    result = summary(monkeypatch, weather.WeatherDataError("synthetic"), payload)
    assert result.available
    assert result.evening.transparency_quality_percent is not None
    assert result.sources == "7Timer! ASTRO"


@pytest.mark.parametrize("mutation", ["descending", "date-only", "bad-date"])
def test_invalid_hourly_timeline_is_not_guessed(monkeypatch, mutation):
    payload = meteo()
    if mutation == "descending":
        payload["hourly"]["time"][:2] = list(reversed(payload["hourly"]["time"][:2]))
    else:
        payload["hourly"]["time"][0] = (
            "2026-08-03" if mutation == "date-only" else "2026-02-30T21:00"
        )
    result = summary(monkeypatch, payload, astro())
    assert result.evening.temperature_c is None
    assert result.evening.seeing_quality_percent is not None


def test_too_many_civil_samples_is_graceful(monkeypatch):
    payload = meteo()
    payload["hourly"]["time"] *= weather.MAX_WEATHER_SAMPLES
    result = summary(monkeypatch, payload, astro())
    assert result.evening.temperature_c is None
    assert result.predawn.seeing_quality_percent is not None


def test_astronomical_samples_limit_is_enforced(monkeypatch):
    payload = astro()
    payload["dataseries"] *= weather.MAX_WEATHER_SAMPLES
    result = summary(monkeypatch, meteo(), payload)
    assert result.evening.temperature_c == 13.5
    assert result.evening.seeing_quality_percent is None


def test_duplicated_astronomical_timepoints_do_not_double_weight_data(monkeypatch):
    payload = astro()
    payload["dataseries"].append(dict(payload["dataseries"][-1]))
    result = summary(monkeypatch, meteo(), payload)
    assert result.evening.seeing_quality_percent is None
    assert result.evening.temperature_c == 13.5


def test_no_sources_is_unavailable_and_has_no_invented_values(monkeypatch):
    result = summary(
        monkeypatch, weather.WeatherDataError("civil"), weather.WeatherDataError("astro")
    )
    assert not result.available
    assert result.sources == ""
    assert result.evening.dew_risk == ""
    assert len(result.warnings) == 3
    assert "repli" in " ".join(result.warnings)


def test_http_declared_oversize_is_rejected_before_reading(monkeypatch):
    class DeclaredOversize(Response):
        headers = {"Content-Length": str(weather.MAX_WEATHER_BYTES + 1)}

        def read(self, *args):
            pytest.fail("Ne pas lire une réponse déclarée trop grande")

    monkeypatch.setattr(weather, "urlopen", lambda *a, **kw: DeclaredOversize())
    with pytest.raises(weather.WeatherDataError, match="taille"):
        weather._read_json(weather.OPEN_METEO_ENDPOINT)


def test_exact_response_size_limit_is_accepted(monkeypatch):
    content = b"{}" + b" " * (weather.MAX_WEATHER_BYTES - 2)
    monkeypatch.setattr(weather, "urlopen", lambda *a, **kw: Response(content))
    assert weather._read_json(weather.OPEN_METEO_ENDPOINT) == {}


def test_unexpected_compression_is_rejected_without_decompression(monkeypatch):
    response = Response(b"synthetic gzip")
    response.headers = {"Content-Encoding": "gzip"}
    monkeypatch.setattr(weather, "urlopen", lambda *a, **kw: response)
    with pytest.raises(weather.WeatherDataError, match="encodage"):
        weather._read_json(weather.OPEN_METEO_ENDPOINT)


def test_http_failure_does_not_remove_the_astronomical_list(tmp_path, monkeypatch, capsys):
    from pypdf import PdfReader

    from gnu_astrolist import cli

    result = summary(
        monkeypatch, weather.WeatherDataError("civil"), weather.WeatherDataError("astro")
    )
    # La météo est simulée, tandis qu'Astropy reste explicitement hors réseau.
    monkeypatch.setattr(cli, "compute_weather_summary", lambda **kwargs: result)
    txt, pdf = tmp_path / "failure.txt", tmp_path / "failure.pdf"
    code = cli.main(
        [
            "--date",
            "2026-08-03",
            "--time-range",
            "21:00-22:00",
            "--lat",
            "45",
            "--lon",
            "0",
            "--az-min",
            "0",
            "--az-max",
            "360",
            "--min-altitude",
            "0",
            "--objects",
            "messier",
            "--limit",
            "1",
            "--offline",
            "--output-txt",
            str(txt),
            "--output-pdf",
            str(pdf),
        ]
    )
    assert code == 0
    terminal = capsys.readouterr().out
    assert txt.read_text(encoding="utf-8") == terminal
    for text in (terminal, " ".join(page.extract_text() for page in PdfReader(pdf).pages)):
        assert re.search(r"\bM\d{1,3}\b", text)
        assert "indisponibles" in text and "Open-Meteo" in text
        assert "7Timer!" in text


def test_partial_weather_warning_and_valid_values_reach_all_outputs(tmp_path, monkeypatch, capsys):
    from pypdf import PdfReader

    from gnu_astrolist import cli

    payload = meteo()
    payload["hourly"]["cloud_cover"] = [None] * 4
    result = summary(monkeypatch, payload, weather.WeatherDataError("astro"))
    monkeypatch.setattr(cli, "compute_weather_summary", lambda **kwargs: result)
    txt, pdf = tmp_path / "partial.txt", tmp_path / "partial.pdf"
    assert (
        cli.main(
            [
                "--date",
                "2026-08-03",
                "--time-range",
                "21:00-22:00",
                "--lat",
                "45",
                "--lon",
                "0",
                "--az-min",
                "0",
                "--az-max",
                "360",
                "--min-altitude",
                "0",
                "--objects",
                "messier",
                "--max-magnitude",
                "-20",
                "--offline",
                "--output-txt",
                str(txt),
                "--output-pdf",
                str(pdf),
            ]
        )
        == 0
    )
    terminal = capsys.readouterr().out
    assert txt.read_text(encoding="utf-8") == terminal
    for text in (terminal, " ".join(page.extract_text() for page in PdfReader(pdf).pages)):
        assert "13.5" in text and "partielles" in text and "Open-Meteo" in text


def test_explicit_fall_back_offsets_keep_distinct_instants():
    from zoneinfo import ZoneInfo

    payload = meteo()
    payload["hourly"]["time"] = ["2026-11-01T01:30-04:00", "2026-11-01T01:30-05:00"]
    for field in weather.MEASURE_LIMITS:
        payload["hourly"][field] = payload["hourly"][field][:2]
    samples = weather._hourly_samples(payload, ZoneInfo("America/Toronto"), [])
    instants = list(samples)
    assert len(instants) == 2
    assert (instants[1] - instants[0]).total_seconds() == 3600


def test_valid_solar_times_survive_unusable_hourly_table(monkeypatch):
    payload = meteo()
    payload["daily"]["sunset"][0] = "2026-08-03T19:00"
    payload["hourly"] = None
    result = summary(monkeypatch, payload, astro())
    assert result.evening.start_local.hour == 19
    assert result.evening.seeing_quality_percent is not None
    assert not any("repli" in warning for warning in result.warnings)


def test_wrong_solar_day_uses_announced_fallback(monkeypatch):
    payload = meteo()
    payload["daily"]["sunrise"][1] = "2026-08-03T06:00"
    result = summary(monkeypatch, payload, astro())
    assert result.evening.start_local.hour == 20
    assert result.evening.temperature_c == 13.5
    assert any("repli" in warning for warning in result.warnings)


def test_zero_is_a_real_measurement_not_missing_data(monkeypatch):
    payload = meteo()
    payload["hourly"] = {"time": payload["hourly"]["time"], "temperature_2m": [0] * 4}
    result = summary(monkeypatch, payload, weather.WeatherDataError("astro"))
    assert result.available and result.evening.temperature_c == 0


def test_exact_sample_limit_is_accepted():
    from datetime import datetime, timedelta, timezone

    payload = meteo()
    start = datetime(2026, 8, 3, 12)
    payload["hourly"]["time"] = [
        (start + timedelta(minutes=i)).isoformat() for i in range(weather.MAX_WEATHER_SAMPLES)
    ]
    for field in weather.MEASURE_LIMITS:
        payload["hourly"][field] = [payload["hourly"][field][0]] * weather.MAX_WEATHER_SAMPLES
    assert len(weather._hourly_samples(payload, timezone.utc, [])) == weather.MAX_WEATHER_SAMPLES
