from astropy.utils import iers

from gnu_astrolist.cli import main


def test_cli_prints_header_and_empty_result(capsys) -> None:
    exit_code = main(
        [
            "--date",
            "2026-08-15",
            "--time-range",
            "21:00-22:00",
            "--timezone",
            "America/Toronto",
            "--lat",
            "45.57",
            "--lon",
            "-73.68",
            "--az-min",
            "15",
            "--az-max",
            "180",
            "--min-altitude",
            "10",
            "--objects",
            "variable_stars",
            "--max-magnitude",
            "-20",
            "--offline",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "SOIRÉE D'OBSERVATION" in output
    assert "Aucun objet" in output
    assert "America/Toronto" in output
    assert iers.conf.auto_download is False
    assert iers.conf.auto_max_age is None


def test_cli_accepts_the_messier_catalog(capsys) -> None:
    exit_code = main(
        [
            "--date",
            "2026-08-15",
            "--time-range",
            "21:00-22:00",
            "--timezone",
            "America/Toronto",
            "--lat",
            "45.57",
            "--lon",
            "-73.68",
            "--az-min",
            "15",
            "--az-max",
            "180",
            "--min-altitude",
            "10",
            "--objects",
            "messier",
            "--max-magnitude",
            "-20",
            "--offline",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Objets Messier (SIMBAD, repli OpenNGC)" in output
    assert "magnitude apparente ≤ -20" in output
    assert "Aucun objet" in output
