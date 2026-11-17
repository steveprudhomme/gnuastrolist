# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Options de démarrage et priorité du mode hors ligne, sans réseau."""

import json

import pytest

from gnu_astrolist import cli
from gnu_astrolist.updates import UpdateResult


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
        "20",
        "--objects",
        "messier",
        "--max-magnitude",
        "-20",
        "--offline",
    ]


def test_config_file_cli_priority_and_alias(tmp_path, monkeypatch, capsys):
    config = tmp_path / "settings.json"
    config.write_text(
        json.dumps(
            {
                "mode": "force",
                "cache_dir": str(tmp_path / "cache"),
                "max_age_hours": {"mpc": 1, "messier": 720},
            }
        ),
        encoding="utf-8",
    )
    calls = []

    def refresh(kinds, **kwargs):
        calls.append((kinds, kwargs))
        return UpdateResult({}, ("Test de configuration synthétique.",))

    monkeypatch.setattr(cli, "refresh_catalogs", refresh)
    args = arguments()
    args[args.index("messier")] = "messier_objects"
    assert (
        cli.main(
            args
            + [
                "--catalog-config",
                str(config),
                "--update-catalogs",
                "never",
                "--catalog-max-age-hours",
                "48",
                "--catalog-age",
                "messier=12",
            ]
        )
        == 0
    )
    kinds, settings = calls[0]
    assert kinds == ("messier",) and settings["mode"] == "never" and settings["offline"]
    assert settings["max_age_hours"]["messier"] == 12
    assert settings["max_age_hours"]["mpc"] == 1
    assert settings["cache_dir"] == tmp_path / "cache"
    assert "Test de configuration synthétique" in capsys.readouterr().out


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"unexpected": 1},
        {"mode": []},
        {"max_age_hours": []},
        {"max_age_hours": {"unknown": 24}},
        {"max_age_hours": {"comets": 0}},
    ],
)
def test_invalid_configuration_refused_before_any_export(tmp_path, payload):
    config = tmp_path / "settings.json"
    config.write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "must-not-exist.txt"
    with pytest.raises(SystemExit):
        cli.main(arguments() + ["--catalog-config", str(config), "--output-txt", str(out)])
    assert not out.exists()


def test_offline_force_all_registered_catalogs_never_connects(tmp_path, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("Aucune connexion en mode hors ligne")

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    args = arguments()
    index = args.index("messier")
    args[index : index + 1] = [
        "variable_stars",
        "messier",
        "caldwell",
        "ngc",
        "bayer",
        "flamsteed",
        "asteroids",
        "comets",
        "satellites",
        "debris",
    ]
    cache = tmp_path / "cache"
    assert cli.main(args + ["--update-catalogs", "force", "--catalog-cache-dir", str(cache)]) == 0
    report = capsys.readouterr().out
    assert "Aucun objet" in report and "comets" in report and "variable_stars" in report
    assert not cache.exists()


def test_protected_cache_is_rejected_before_any_write(tmp_path):
    source = tmp_path / "MyWorks"
    source.mkdir()
    cache = source / "cache"
    with pytest.raises(SystemExit):
        cli.main(
            arguments()
            + [
                "--seestar-path",
                str(source),
                "--catalog-cache-dir",
                str(cache),
                "--update-catalogs",
                "force",
            ]
        )
    assert list(source.iterdir()) == []
