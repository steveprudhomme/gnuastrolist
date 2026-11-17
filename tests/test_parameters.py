# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""ECC-C : paramètres invalides refusés avant effets, sans réseau ni USB réel."""

import argparse
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from astropy.utils import iers

from gnu_astrolist import asteroids, cli, comets, moon, moving, satellites, updates, visibility
from gnu_astrolist.models import FieldOfView, ObservationWindow
from gnu_astrolist.time_utils import parse_observation_window


def arguments():
    return [
        "--date",
        "2026-11-17",
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
        "10",
        "--objects",
        "messier",
        "--offline",
    ]


def forbid_effects(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Aucune actualisation, météo, calcul ou export avant validation")

    for name in ("refresh_catalogs", "compute_weather_summary", "compute_moon_summary", "_run"):
        monkeypatch.setattr(cli, name, forbidden)


@pytest.mark.parametrize(
    "option",
    [
        "--lat",
        "--lon",
        "--elevation-m",
        "--az-min",
        "--az-max",
        "--min-altitude",
        "--alt-center",
        "--max-magnitude",
        "--sample-minutes",
        "--satellite-max-sun-altitude",
    ],
)
@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_nonfinite_cli_values_are_rejected_before_effects(monkeypatch, capsys, option, value):
    forbid_effects(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(arguments() + [f"{option}={value}"])
    assert exc.value.code == 2
    assert "error:" in capsys.readouterr().err


@pytest.mark.parametrize(
    "option,value",
    [
        ("--sample-minutes", "1e-20"),
        ("--sample-minutes", "1e308"),
        ("--sample-minutes", "0.001"),
        ("--elevation-m", "-1001"),
        ("--elevation-m", "10001"),
        ("--lat", "91"),
        ("--lon", "-181"),
        ("--sample-minutes", "0"),
        ("--limit", "0"),
        ("--catalog-age", "unknown=24"),
    ],
)
def test_invalid_domains_and_budget_precede_updates(monkeypatch, capsys, option, value):
    forbid_effects(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(arguments() + [f"{option}={value}", "--update-catalogs", "force"])
    assert exc.value.code == 2


@pytest.mark.parametrize(
    "config",
    [
        {"max_age_hours": {"mpc": True}},
        {"max_age_hours": {"mpc": float("nan")}},
        {"max_age_hours": {"mpc": None}},
        {"max_age_hours": {"unknown": 24}},
        {"max_age_hours": {"mpc": 1e308}},
        {"cache_dir": ""},
        {"cache_dir": "\u0000"},
    ],
)
def test_invalid_configuration_precedes_refresh(tmp_path, monkeypatch, capsys, config):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    forbid_effects(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(arguments() + ["--catalog-config", str(path)])
    assert exc.value.code == 2
    assert list(tmp_path.iterdir()) == [path]


def test_invalid_command_does_not_change_iers_policy(monkeypatch, capsys):
    forbid_effects(monkeypatch)
    with iers.conf.set_temp("auto_download", True):
        with pytest.raises(SystemExit):
            cli.main(arguments() + ["--sample-minutes=1e-20"])
        assert iers.conf.auto_download is True


def test_satellite_budget_is_checked_before_refresh(monkeypatch, capsys):
    forbid_effects(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(arguments() + ["--objects", "satellites", "--satellite-step-seconds", "0.001"])
    assert exc.value.code == 2


@pytest.mark.parametrize("engine", ["fixed", "asteroids", "comets", "satellites", "moon"])
@pytest.mark.parametrize("height", [float("inf"), float("nan"), -1001, 10001, True])
def test_engine_observer_validation_precedes_astropy(monkeypatch, engine, height):
    module = {
        "fixed": visibility,
        "asteroids": moving,
        "comets": moving,
        "satellites": satellites,
        "moon": moon,
    }[engine]

    def forbidden(*args, **kwargs):
        pytest.fail("Ne pas appeler Astropy avec un site invalide")

    monkeypatch.setattr(module, "EarthLocation", SimpleNamespace(from_geodetic=forbidden))
    window = parse_observation_window("2026-11-17", "21:00-22:00", "UTC")
    fov = FieldOfView(180, 45, 360, 90)
    with pytest.raises(ValueError):
        if engine == "moon":
            moon.compute_moon_summary(
                window=window, latitude_deg=45, longitude_deg=0, elevation_m=height
            )
        elif engine == "satellites":
            satellites.compute_satellite_visibility((), window, 45, 0, height, fov)
        else:
            function = {
                "fixed": visibility.compute_visibility,
                "asteroids": asteroids.compute_asteroid_visibility,
                "comets": comets.compute_comet_visibility,
            }[engine]
            function((), window, 45, 0, height, fov)


@pytest.mark.parametrize("step", [float("inf"), float("nan"), 1e-20, 1e308, 0, -1])
def test_time_grid_errors_are_value_errors_not_arithmetic_crashes(step):
    window = parse_observation_window("2026-11-17", "21:00-22:00", "UTC")
    with pytest.raises(ValueError):
        visibility._sample_datetimes(window, step)


def test_exact_slow_budget_accepts_two_thousand_samples():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    window = ObservationWindow(start, start + timedelta(seconds=1999), "UTC")
    samples = visibility._sample_datetimes(window, 1 / 60)
    assert len(samples) == 2000
    assert samples[0] == start and samples[-1] == window.end_local
    with pytest.raises(ValueError):
        visibility._sample_datetimes(
            ObservationWindow(start, window.end_local + timedelta(microseconds=1), "UTC"), 1 / 60
        )


@pytest.mark.parametrize("day,expected", [("2026-03-07", 24), ("2026-10-31", 26)])
def test_time_grid_uses_elapsed_utc_across_dst(day, expected):
    window = parse_observation_window(day, "20:00-20:00", "America/Toronto")
    samples = visibility._sample_datetimes(window, 60)
    assert len(samples) == expected
    assert samples[-1] == window.end_local.astimezone(timezone.utc)
    assert all(b > a for a, b in zip(samples, samples[1:]))


@pytest.mark.parametrize("value", [True, False, None, 1e308, [], {}])
def test_invalid_update_age_types_are_controlled(value):
    with pytest.raises(argparse.ArgumentTypeError):
        updates.parse_max_age_hours(value)


def test_exact_satellite_budget_and_minimum_step():
    from gnu_astrolist.validation import sample_datetimes

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    window = ObservationWindow(start, start + timedelta(seconds=19999), "UTC")
    dates = sample_datetimes(window, 1, 20000, "pas")
    assert len(dates) == 20000 and dates[-1] == window.end_local
    with pytest.raises(ValueError):
        satellites.compute_satellite_visibility(
            (),
            ObservationWindow(start, start + timedelta(seconds=20000), "UTC"),
            45,
            0,
            0,
            FieldOfView(180, 45, 360, 90),
            sample_seconds=1,
        )
    tiny = ObservationWindow(start, start + timedelta(microseconds=2), "UTC")
    assert len(sample_datetimes(tiny, 1e-6, 3, "pas")) == 3
    with pytest.raises(ValueError):
        sample_datetimes(tiny, 0.9e-6, 3, "pas")


@pytest.mark.parametrize("end", [None, "before", "naive"])
def test_invalid_windows_are_rejected_by_sampling_and_moon(end):
    from gnu_astrolist.validation import sampling_plan

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    finish = start if end is None else start - timedelta(seconds=1)
    if end == "naive":
        finish = (start + timedelta(seconds=1)).replace(tzinfo=None)
    window = ObservationWindow(start, finish, "UTC")
    with pytest.raises(ValueError):
        sampling_plan(window, 1, 2000, "pas")
    with pytest.raises(ValueError):
        moon.compute_moon_summary(window=window, latitude_deg=45, longitude_deg=0, elevation_m=0)


@pytest.mark.parametrize(
    "engine",
    [
        asteroids.compute_asteroid_visibility,
        comets.compute_comet_visibility,
        satellites.compute_satellite_visibility,
    ],
)
@pytest.mark.parametrize("magnitude", [True, float("nan"), float("inf")])
def test_engine_magnitude_is_checked_even_without_objects(engine, magnitude):
    window = parse_observation_window("2026-11-17", "21:00-22:00", "UTC")
    with pytest.raises(ValueError):
        engine((), window, 45, 0, 0, FieldOfView(180, 45, 360, 90), max_magnitude=magnitude)


def test_field_rejects_boolean_inputs():
    with pytest.raises(ValueError):
        FieldOfView.from_automatic_center(
            azimuth_min_deg=True, azimuth_max_deg=360, minimum_altitude_deg=10
        )


def test_cli_validation_preserves_existing_reports_and_synthetic_archive(
    tmp_path, monkeypatch, capsys
):
    root = tmp_path / "MyWorks"
    root.mkdir()
    photo = root / "Stacked_20_M31_10.0s_LP_20261117.fit"
    photo.write_bytes(b"Synthetic")
    report = tmp_path / "old.txt"
    report.write_bytes(b"Old report")
    forbid_effects(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(
            arguments()
            + [
                "--sample-minutes=1e-20",
                "--seestar-path",
                str(root),
                "--output-txt",
                str(report),
                "--overwrite",
                "--catalog-cache-dir",
                str(tmp_path / "cache"),
                "--update-catalogs",
                "force",
            ]
        )
    assert exc.value.code == 2
    assert photo.read_bytes() == b"Synthetic" and report.read_bytes() == b"Old report"
    assert not (tmp_path / "cache").exists()


def test_settings_priority_remains_explicit(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"max_age_hours": {"messier": True}, "mode": "never"}), encoding="utf-8"
    )
    args = cli.build_parser().parse_args(
        arguments() + ["--catalog-config", str(path), "--catalog-age", "messier=12"]
    )
    assert cli._update_settings(args)[2]["messier"] == 12


@pytest.mark.parametrize("age", [True, float("nan"), 1e308])
def test_gp_age_is_validated_in_direct_api(age):
    with pytest.raises(ValueError):
        satellites.eligible_elements((), ["2026-11-17T21:00:00"], age)
