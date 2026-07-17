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
            "--fov-h",
            "10",
            "--fov-v",
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

