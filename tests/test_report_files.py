# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""ECC-A : préservation des entrées et publication des rapports, sans USB réel."""

import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfReader

from gnu_astrolist import cli, pdf_output

INPUT_OPTIONS = (
    "--catalog-config",
    "--asteroids-file",
    "--comets-file",
    "--cbat-file",
    "--satellite-elements-file",
    "--satcat-file",
    "--unoosa-file",
)


def arguments():
    return [
        "--date",
        "2026-08-15",
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


def forbid_processing(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Le refus de destination doit précéder tout traitement")

    for name in ("refresh_catalogs", "compute_weather_summary", "_run"):
        monkeypatch.setattr(cli, name, forbidden)


@pytest.mark.parametrize("input_option", INPUT_OPTIONS)
@pytest.mark.parametrize("output_option", ("--output-txt", "--output-pdf"))
def test_cli_rejects_every_input_output_collision_before_processing(
    tmp_path,
    monkeypatch,
    capsys,
    input_option,
    output_option,
):
    source = tmp_path / "source.json"
    source.write_bytes(b'{"mode":"never"}')
    forbid_processing(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(
            arguments() + [input_option, str(source), output_option, str(source), "--overwrite"]
        )
    assert exc.value.code == 2
    assert "entrée" in capsys.readouterr().err
    assert source.read_bytes() == b'{"mode":"never"}'


def test_same_resolved_output_paths_are_rejected_before_processing(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    forbid_processing(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(arguments() + ["--output-txt", "report", "--output-pdf", str(tmp_path / "report")])
    assert exc.value.code == 2
    assert "distinct" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("link_kind", ("hard", "symbolic"))
def test_input_alias_is_rejected_even_with_overwrite(tmp_path, monkeypatch, capsys, link_kind):
    source, alias = tmp_path / "source.json", tmp_path / "alias.txt"
    source.write_text('{"mode":"never"}', encoding="utf-8")
    try:
        os.link(source, alias) if link_kind == "hard" else alias.symlink_to(source)
    except OSError:
        pytest.skip("Création du lien non autorisée sur cette plateforme")
    forbid_processing(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(
            arguments()
            + ["--catalog-config", str(source), "--output-txt", str(alias), "--overwrite"]
        )
    assert exc.value.code == 2
    assert source.read_text(encoding="utf-8") == '{"mode":"never"}'


@pytest.mark.parametrize("option", ("--output-txt", "--output-pdf"))
def test_existing_report_requires_explicit_overwrite(tmp_path, monkeypatch, capsys, option):
    report = tmp_path / "report"
    report.write_bytes(b"Old report")
    forbid_processing(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(arguments() + [option, str(report)])
    assert exc.value.code == 2
    assert "--overwrite" in capsys.readouterr().err
    assert report.read_bytes() == b"Old report"


@pytest.mark.parametrize("destination", ("absent/report.txt", "directory", "cache/report.txt"))
def test_invalid_parent_directory_or_cache_is_rejected(tmp_path, monkeypatch, capsys, destination):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "directory").mkdir()
    (tmp_path / "cache").mkdir()
    forbid_processing(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(arguments() + ["--output-txt", destination, "--catalog-cache-dir", "cache"])
    assert exc.value.code == 2
    assert "refusé" in capsys.readouterr().err


def test_bundled_resource_is_protected_before_processing(monkeypatch, capsys):
    source = Path(cli.__file__).parent / "data" / "messier.csv.gz"
    original = source.read_bytes()
    forbid_processing(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(arguments() + ["--output-txt", str(source), "--overwrite"])
    assert exc.value.code == 2
    assert source.read_bytes() == original


def test_overwrite_exports_terminal_text_and_pdf(tmp_path, capsys):
    text, pdf = tmp_path / "report.txt", tmp_path / "report.pdf"
    text.write_bytes(b"Old TXT")
    pdf.write_bytes(b"Old PDF")
    assert (
        cli.main(arguments() + ["--output-txt", str(text), "--output-pdf", str(pdf), "--overwrite"])
        == 0
    )
    terminal = capsys.readouterr().out
    assert text.read_text(encoding="utf-8") == terminal
    assert "SOIRÉE D'OBSERVATION" in "".join(p.extract_text() for p in PdfReader(pdf).pages)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["report.pdf", "report.txt"]


def test_pdf_failure_preserves_old_report_and_removes_temporary(tmp_path, monkeypatch, capsys):
    report = tmp_path / "report.pdf"
    report.write_bytes(b"Original PDF")

    def broken(path, **kwargs):
        path.write_bytes(b"Incomplete PDF")
        raise OSError("Synthetic write failure")

    monkeypatch.setattr(pdf_output, "_build_pdf", broken)
    with pytest.raises(SystemExit) as exc:
        cli.main(arguments() + ["--output-pdf", str(report), "--overwrite"])
    assert exc.value.code == 2
    assert report.read_bytes() == b"Original PDF"
    assert list(tmp_path.iterdir()) == [report]


def test_atomic_text_failure_preserves_old_report(tmp_path):
    from gnu_astrolist.report_files import staged_report

    report = tmp_path / "report.txt"
    report.write_bytes(b"Original text")
    with pytest.raises(OSError, match="Synthetic"):
        with staged_report(report, overwrite=True) as temporary:
            temporary.write_bytes(b"Incomplete text")
            raise OSError("Synthetic write failure")
    assert report.read_bytes() == b"Original text"
    assert list(tmp_path.iterdir()) == [report]


def test_concurrent_creation_is_not_overwritten(tmp_path):
    from gnu_astrolist.report_files import staged_report

    report = tmp_path / "report.txt"
    with pytest.raises((ValueError, FileExistsError)):
        with staged_report(report) as temporary:
            temporary.write_bytes(b"Our report")
            report.write_bytes(b"Other report")
    assert report.read_bytes() == b"Other report"
    assert list(tmp_path.iterdir()) == [report]


def test_publication_error_preserves_old_file(tmp_path, monkeypatch):
    from gnu_astrolist import report_files

    report = tmp_path / "report.txt"
    report.write_bytes(b"Original")

    def failure(*args):
        raise OSError("Synthetic publication failure")

    monkeypatch.setattr(report_files.os, "replace", failure)
    with pytest.raises(OSError, match="publication"):
        with report_files.staged_report(report, overwrite=True) as temporary:
            temporary.write_bytes(b"New")
    assert report.read_bytes() == b"Original"
    assert list(tmp_path.iterdir()) == [report]


def test_configuration_collision_without_overwrite_precedes_processing(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "config.json"
    source.write_text('{"mode":"never"}', encoding="utf-8")
    forbid_processing(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(arguments() + ["--catalog-config", "config.json", "--output-txt", str(source)])
    assert exc.value.code == 2
    assert "entrée" in capsys.readouterr().err
    assert source.read_text(encoding="utf-8") == '{"mode":"never"}'


def test_linked_outputs_are_rejected_before_processing(tmp_path, monkeypatch, capsys):
    first, second = tmp_path / "first", tmp_path / "second"
    first.write_bytes(b"Old report")
    try:
        os.link(first, second)
    except OSError:
        pytest.skip("Liens physiques indisponibles")
    forbid_processing(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(
            arguments() + ["--output-txt", str(first), "--output-pdf", str(second), "--overwrite"]
        )
    assert exc.value.code == 2
    assert first.read_bytes() == second.read_bytes() == b"Old report"


def test_reparse_parent_is_rejected_before_creating_temporary(tmp_path, monkeypatch):
    from gnu_astrolist.report_files import staged_report

    original = Path.lstat

    def simulated_junction(path, *args, **kwargs):
        info = original(path, *args, **kwargs)
        if path == tmp_path:
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
        return info

    monkeypatch.setattr(Path, "lstat", simulated_junction)
    with pytest.raises(ValueError, match="jonction"):
        with staged_report(tmp_path / "report.txt"):
            pytest.fail("Ne pas créer un temporaire sous une jonction")
    assert list(tmp_path.iterdir()) == []


def test_destination_rechecked_if_it_becomes_an_input_alias(tmp_path):
    from gnu_astrolist.report_files import staged_report

    source, report = tmp_path / "source", tmp_path / "report"
    source.write_bytes(b"Source")
    with pytest.raises(ValueError, match="entrée"):
        with staged_report(report, inputs=(source,), overwrite=True) as temporary:
            temporary.write_bytes(b"New report")
            os.link(source, report)
    assert source.read_bytes() == report.read_bytes() == b"Source"
    assert len(list(tmp_path.iterdir())) == 2


def test_creation_during_publication_is_not_overwritten(tmp_path, monkeypatch):
    from gnu_astrolist import report_files

    report = tmp_path / "report.txt"
    name = "rename" if os.name == "nt" else "link"
    publish = getattr(report_files.os, name)

    def competing_publication(source, destination):
        Path(destination).write_bytes(b"Concurrent report")
        publish(source, destination)

    monkeypatch.setattr(report_files.os, name, competing_publication)
    with pytest.raises(FileExistsError):
        with report_files.staged_report(report) as temporary:
            temporary.write_bytes(b"Our report")
    assert report.read_bytes() == b"Concurrent report"
    assert list(tmp_path.iterdir()) == [report]


def test_cli_text_write_failure_preserves_old_report(tmp_path, monkeypatch, capsys):
    report = tmp_path / "report.txt"
    report.write_bytes(b"Original TXT")
    original = Path.write_text

    def incomplete_write(path, *args, **kwargs):
        if path.name.startswith(".report-"):
            path.write_bytes(b"Incomplete TXT")
            raise OSError("Synthetic text failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", incomplete_write)
    with pytest.raises(SystemExit) as exc:
        cli.main(arguments() + ["--output-txt", str(report), "--overwrite"])
    assert exc.value.code == 2
    assert report.read_bytes() == b"Original TXT"
    assert list(tmp_path.iterdir()) == [report]


@pytest.mark.parametrize("option", ("--output-txt", "--output-pdf"))
def test_overwrite_never_bypasses_seestar_protection(tmp_path, monkeypatch, capsys, option):
    root = tmp_path / "MyWorks"
    root.mkdir()
    photo = root / "Stacked_20_M31_10.0s_LP_20260815.fit"
    photo.write_bytes(b"Synthetic acquisition")
    forbid_processing(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(arguments() + ["--seestar-path", str(root), option, str(photo), "--overwrite"])
    assert exc.value.code == 2
    assert "protégées" in capsys.readouterr().err
    assert photo.read_bytes() == b"Synthetic acquisition"
    assert list(root.iterdir()) == [photo]


@pytest.mark.skipif(os.name == "nt", reason="FIFO POSIX seulement")
def test_special_file_is_rejected_without_opening_it(tmp_path):
    from gnu_astrolist.report_files import staged_report

    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match="ordinaire"):
        with staged_report(fifo, overwrite=True):
            pytest.fail("Une FIFO ne doit jamais être ouverte pour l'export")
