from astropy.utils import iers
from pypdf import PdfReader

from gnu_astrolist.cli import main


def test_cli_prints_header_and_empty_result(capsys) -> None:
    previous_iers = (iers.conf.auto_download, iers.conf.auto_max_age)
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
    assert "RÉSUMÉ DE LA LUNE" in output
    assert "CONDITIONS MÉTÉO" in output
    assert "Prévisions indisponibles : mode --offline" in output
    assert "Illumination quotidienne" in output
    assert "Lever apparent le 2026-08-15" in output
    assert "Coucher apparent le 2026-08-15" in output
    assert (iers.conf.auto_download, iers.conf.auto_max_age) == previous_iers


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


def test_cli_exports_the_complete_report_as_utf8_text(tmp_path, capsys) -> None:
    output_path = tmp_path / "soirée-observation.txt"

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
            "--output-txt",
            str(output_path),
        ]
    )

    terminal_report = capsys.readouterr().out
    exported_report = output_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert exported_report == terminal_report
    assert "SOIRÉE D'OBSERVATION — GNU ASTROLIST" in exported_report
    assert "CONDITIONS MÉTÉO" in exported_report
    assert "RÉSUMÉ DE LA LUNE" in exported_report
    assert "Aucun objet" in exported_report


def test_cli_exports_a_letter_size_pdf_report(tmp_path, capsys) -> None:
    output_path = tmp_path / "soirée-observation.pdf"

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
            "--output-pdf",
            str(output_path),
        ]
    )

    terminal_report = capsys.readouterr().out
    reader = PdfReader(output_path)
    first_page = reader.pages[0]
    extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert exit_code == 0
    assert "SOIRÉE D'OBSERVATION" in terminal_report
    assert float(first_page.mediabox.width) == 612
    assert float(first_page.mediabox.height) == 792
    assert "SOIRÉE D'OBSERVATION" in extracted_text
    assert "CONDITIONS MÉTÉO" in extracted_text
    assert "RÉSUMÉ DE LA LUNE" in extracted_text
    assert "Aucun objet du catalogue ne satisfait les critères" in extracted_text
