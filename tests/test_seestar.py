# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Archives synthétiques uniquement : identité, lecture seule et sorties."""

import os
import stat
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfReader

from gnu_astrolist.catalog import load_caldwell_catalog, load_messier_catalog, load_ngc_catalog
from gnu_astrolist.cli import main
from gnu_astrolist.pdf_output import PdfExportError, export_pdf_report
from gnu_astrolist.seestar import object_keys, protect_outputs, scan_seestar


def acquisition(root, name, *, target="M 31", kind="Stacked", thumbnail=False, empty=False):
    folder = root / name
    folder.mkdir(parents=True, exist_ok=True)
    prefix = "Stacked_20" if kind == "Stacked" else "Light"
    path = folder / f"{prefix}_{target}_10.0s_LP_20260815-210000{'_thn' if thumbnail else ''}.fit"
    path.write_bytes(b"" if empty else b"Synthetic acquisition, not a scientific FITS")
    return path


def test_names_and_metadata_only_no_file_open_or_change(tmp_path, monkeypatch):
    root = tmp_path / "MyWorks"
    path = acquisition(root, "M 31")
    before = path.stat()

    def forbidden(*args, **kwargs):
        raise AssertionError("Le scanner ne doit ouvrir aucun fichier")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    for operation in (
        "open",
        "mkdir",
        "makedirs",
        "unlink",
        "remove",
        "rename",
        "replace",
        "rmdir",
        "chmod",
        "utime",
    ):
        monkeypatch.setattr(f"gnu_astrolist.seestar.os.{operation}", forbidden)
    inventory = scan_seestar(root)
    assert inventory.status({"M31"}) == "Fait (empilé)"
    assert inventory.status({"M3"}) == "Non trouvé"
    assert path.stat().st_mtime_ns == before.st_mtime_ns
    assert path.stat().st_size == before.st_size
    assert list(root.rglob("*")) == [path.parent, path]


def test_empty_folders_thumbnails_empty_files_and_arbitrary_names_are_not_evidence(tmp_path):
    acquisition(tmp_path, "M 31", thumbnail=True)
    acquisition(tmp_path, "M 32", target="M 32", empty=True)
    folder = tmp_path / "M 33"
    folder.mkdir()
    (folder / "notes.fit").write_bytes(b"No acquisition naming pattern")
    inventory = scan_seestar(tmp_path)
    assert all(inventory.status({name}) == "Non trouvé" for name in ("M31", "M32", "M33"))


def test_raw_stacked_aliases_and_component_boundaries(tmp_path):
    acquisition(tmp_path, "M31-sub", kind="Light")
    acquisition(tmp_path, "C27", target="C 27")
    acquisition(tmp_path, "component", target="NGC 61A")
    inventory = scan_seestar(tmp_path)
    ngc = {obj.name: obj for obj in load_ngc_catalog()}
    assert inventory.status(object_keys(ngc["NGC224"])) == "Brutes seules"
    assert inventory.status(object_keys(ngc["NGC6888"])) == "Fait (empilé)"
    assert inventory.status(object_keys(ngc["NGC61A"])) == "Fait (empilé)"
    assert inventory.status(object_keys(ngc["NGC61B"])) == "Non trouvé"
    c14 = next(obj for obj in load_caldwell_catalog() if obj.name == "C14")
    acquisition(tmp_path, "member", target="NGC869")
    assert scan_seestar(tmp_path).status(object_keys(c14)) == "Non trouvé"
    acquisition(tmp_path, "stacked")
    assert scan_seestar(tmp_path).status(object_keys(ngc["NGC224"])) == "Fait (empilé)"


def test_read_errors_never_become_certain_absence(tmp_path, monkeypatch):
    acquisition(tmp_path, "raw", kind="Light")
    (tmp_path / "blocked").mkdir()
    original = os.scandir

    def restricted(path):
        if Path(path).name == "blocked":
            raise PermissionError("Synthetic access denial")
        return original(path)

    monkeypatch.setattr("gnu_astrolist.seestar.os.scandir", restricted)
    inventory = scan_seestar(tmp_path)
    assert inventory.issues == 1
    assert inventory.status({"M31"}) == "Brutes (incomplet)"
    assert inventory.status({"M42"}) == "Indéterminé"


def test_links_are_not_followed_and_are_reported_as_incomplete(tmp_path):
    root, outside = tmp_path / "root", tmp_path / "outside"
    root.mkdir()
    acquisition(outside, "M31")
    link = root / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Création de liens non autorisée sur cette plateforme")
    inventory = scan_seestar(root)
    assert inventory.issues == 1
    assert inventory.status({"M31"}) == "Indéterminé"
    with pytest.raises(ValueError, match="sans lien"):
        scan_seestar(link)
    with pytest.raises(ValueError, match="protégées"):
        protect_outputs(outside, (link / "report.txt",))


def test_output_guard_blocks_source_tree_and_hardlink_aliases(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    with pytest.raises(ValueError, match="protégées"):
        protect_outputs(root, (root / "new" / "report.pdf",))
    source = acquisition(root, "M31")
    alias = tmp_path / "report.txt"
    try:
        os.link(source, alias)
    except OSError:
        pytest.skip("Liens physiques indisponibles")
    with pytest.raises(ValueError, match="liens physiques"):
        protect_outputs(root, (alias,))
    assert source.read_bytes().startswith(b"Synthetic")


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
        "--offline",
        "--objects",
        "messier",
        "ngc",
        "--max-magnitude",
        "5",
        "--limit",
        "3",
    ]


def test_cli_reports_screen_txt_pdf_and_preserves_source(tmp_path, capsys):
    root = tmp_path / "MyWorks"
    source = acquisition(root, "M 31")
    acquisition(root, "NGC869-sub", target="NGC 869", kind="Light")
    original = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    txt, pdf = tmp_path / "report.txt", tmp_path / "report.pdf"
    assert (
        main(
            arguments()
            + ["--seestar-path", str(root), "--output-txt", str(txt), "--output-pdf", str(pdf)]
        )
        == 0
    )
    report = capsys.readouterr().out
    assert txt.read_text(encoding="utf-8") == report
    for text in (report, "\n".join(p.extract_text() for p in PdfReader(pdf).pages)):
        assert "Seestar" in text
        assert "lecture seule" in text
        assert "M31 / NGC224" in text
        assert "Fait (empilé)" in text
        assert "Brutes seules" in text
        assert "Non trouvé" in text
    assert source.exists()
    assert original == {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("option", ["--output-txt", "--output-pdf"])
def test_cli_refuses_protected_outputs_before_processing(tmp_path, option):
    root = tmp_path / "MyWorks"
    root.mkdir()
    target = root / "report.txt"
    target.write_bytes(b"Existing acquisition must not change")
    with pytest.raises(SystemExit) as error:
        main(arguments() + ["--seestar-path", str(root), option, str(target)])
    assert error.value.code == 2
    assert target.read_bytes() == b"Existing acquisition must not change"
    assert list(root.iterdir()) == [target]


def test_missing_root_and_file_root_are_explicit_errors(tmp_path):
    with pytest.raises(SystemExit) as error:
        main(arguments() + ["--seestar-path", str(tmp_path / "absent")])
    assert error.value.code == 2
    file = tmp_path / "file"
    file.write_text("Synthetic", encoding="utf-8")
    with pytest.raises(ValueError, match="dossier"):
        scan_seestar(file)


def test_no_option_keeps_existing_output(tmp_path, capsys):
    assert main(arguments()) == 0
    assert "Seestar" not in capsys.readouterr().out


def test_positive_evidence_survives_incomplete_scan(tmp_path):
    acquisition(tmp_path, "M31")
    inventory = replace(scan_seestar(tmp_path), issues=1)
    obj = next(obj for obj in load_messier_catalog() if obj.name == "M31")
    assert inventory.status(object_keys(obj)) == "Fait (empilé)"


def test_windows_reparse_directory_is_never_descended(tmp_path, monkeypatch):
    calls = []

    class Junction:
        def stat(self, *, follow_symlinks):
            assert follow_symlinks is False
            return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)

    @contextmanager
    def entries(path):
        calls.append(Path(path))
        yield iter([Junction()])

    monkeypatch.setattr("gnu_astrolist.seestar.os.scandir", entries)
    inventory = scan_seestar(tmp_path)
    assert calls == [tmp_path.resolve()]
    assert inventory.issues == 1
    assert inventory.status({"M31"}) == "Indéterminé"


def test_pdf_api_blocks_source_before_creating_a_temporary_file(tmp_path):
    inventory = scan_seestar(tmp_path)
    with pytest.raises(PdfExportError, match="protégées"):
        export_pdf_report(
            tmp_path / "report.pdf",
            window=None,
            latitude_deg=0,
            longitude_deg=0,
            elevation_m=0,
            field_of_view=None,
            max_magnitude=None,
            sample_minutes=10,
            weather_summary=None,
            moon_summary=None,
            results=[],
            matched_count=0,
            object_kind="messier",
            show_details=False,
            seestar_inventory=inventory,
        )
    assert list(tmp_path.iterdir()) == []


def test_relative_output_from_archive_directory_is_blocked(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as error:
        main(arguments() + ["--seestar-path", str(tmp_path), "--output-txt", "report.txt"])
    assert error.value.code == 2
    assert list(tmp_path.iterdir()) == []
