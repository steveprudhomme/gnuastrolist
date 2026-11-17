# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Références Skyfield gelées : aucune dépendance de comparaison à l'exécution."""
import hashlib
import importlib.util
import io
import json
import os
import socket
import sys
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import EarthLocation, angular_separation
from astropy.table import QTable
from astropy.time import Time
from astropy.utils import iers
from sgp4.api import Satrec
from sgp4.exporter import export_omm

from gnu_astrolist.models import FieldOfView, ObservationWindow
from gnu_astrolist.satellites import _horizontal, compute_satellite_visibility, parse_gp

REFERENCE = json.loads((Path(__file__).parent / "data/satellite_reference.json").read_text("utf-8"))


@pytest.fixture
def reference_eop():
    rows = np.array(REFERENCE["eop_rows"])
    table = QTable()
    for index, (key, unit) in enumerate([
        ("MJD", u.d), ("PM_x", u.arcsec), ("PM_y", u.arcsec), ("UT1_UTC", u.s),
    ]):
        table[key] = rows[:, index] * unit
    with iers.conf.set_temp("auto_download", False), iers.earth_orientation_table.set(iers.IERS(table)):
        yield


def element_for(number):
    tle = next(item for item in REFERENCE["tles"] if item["norad_id"] == number)
    sat = Satrec.twoline2rv(tle["line1"], tle["line2"])
    return parse_gp([export_omm(sat, f"Reference {number}")])[0]


@pytest.mark.parametrize("case", REFERENCE["cases"], ids=lambda case: case["id"])
def test_independent_satellite_horizontal(case, reference_eop):
    site = REFERENCE["sites"][case["site_index"]]
    location = EarthLocation.from_geodetic(site["longitude_deg"] * u.deg,
                                          site["latitude_deg"] * u.deg,
                                          site["elevation_m"] * u.m)
    instant = Time([datetime.fromisoformat(case["utc"])])
    horizontal, _ = _horizontal(element_for(case["norad_id"]), instant, location)
    separation = angular_separation(horizontal.az, horizontal.alt,
                                    case["azimuth_deg"] * u.deg, case["altitude_deg"] * u.deg)
    # Great-circle separation handles north wrapping and the zenith singularity.
    assert separation.to_value(u.arcsec)[0] < REFERENCE["tolerance"]["direction_arcsec"]
    assert abs(horizontal.distance.to_value(u.km)[0] - case["distance_km"]) < 0.01


def test_reference_coverage_and_generator_integrity():
    assert len(REFERENCE["cases"]) == 38
    assert len(REFERENCE["sites"]) == 3
    assert {case["norad_id"] for case in REFERENCE["cases"]} == {5, 6251, 8195, 14128}
    horizon = [c for c in REFERENCE["cases"] if "horizon" in c["id"]]
    assert -1 < horizon[0]["altitude_deg"] < 0 < horizon[1]["altitude_deg"] < 1
    generator = Path(__file__).parents[1] / "scripts/generate_satellite_reference.py"
    normalized = generator.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(normalized).hexdigest() == REFERENCE["generator_sha256"]
    helper = generator.with_name("_local_output.py").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(helper).hexdigest() == REFERENCE["output_helper_sha256"]


def test_public_visibility_horizon_sampling(reference_eop):
    before, after = [c for c in REFERENCE["cases"] if "horizon" in c["id"]]
    start = datetime.fromisoformat(before["utc"])
    end = datetime.fromisoformat(after["utc"])
    site = REFERENCE["sites"][0]
    window = ObservationWindow(start, end, "UTC")
    results = compute_satellite_visibility(
        [element_for(6251)], window, site["latitude_deg"], site["longitude_deg"],
        site["elevation_m"], FieldOfView.from_automatic_center(
            azimuth_min_deg=0, azimuth_max_deg=360, minimum_altitude_deg=0), sample_seconds=4)
    assert len(results) == 1
    assert results[0].altitude_start_deg < 0 < results[0].altitude_end_deg
    assert results[0].position_reference_time == end
    assert results[0].star.magnitude_v is None
    # Coarse sampling is not proof of absence of a continuous pass.
    below = ObservationWindow(start - timedelta(seconds=4), start, "UTC")
    assert compute_satellite_visibility(
        [element_for(6251)], below, site["latitude_deg"], site["longitude_deg"],
        site["elevation_m"], FieldOfView.from_automatic_center(
            azimuth_min_deg=0, azimuth_max_deg=360, minimum_altitude_deg=0), sample_seconds=4) == []


@pytest.fixture
def script_modules(tmp_path, monkeypatch):
    scripts = Path(__file__).parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    # The generation dependency is never installed/imported by ordinary tests.
    api = ModuleType("skyfield.api")
    api.EarthSatellite = Mock()
    api.load = Mock()
    api.wgs84 = Mock()
    monkeypatch.setitem(sys.modules, "skyfield.api", api)
    modules = {}
    for name in ("benchmark", "generate_satellite_reference"):
        spec = importlib.util.spec_from_file_location(f"review_{name}", scripts / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        monkeypatch.setattr(module, "ROOT", tmp_path)
        modules[name] = module
    (tmp_path / "local").mkdir()
    package = tmp_path / "synthetic-sgp4-package"
    package.mkdir()
    (package / "SGP4-VER.TLE").write_text("synthetic resource, generation is mocked")
    monkeypatch.setattr(modules["generate_satellite_reference"], "resources",
                        SimpleNamespace(files=lambda name: package))
    return modules


@pytest.mark.parametrize("script", ["benchmark", "generate_satellite_reference"])
@pytest.mark.parametrize("destination", ["external", "project", "existing", "hardlink"])
def test_scripts_reject_unsafe_output_before_work(script_modules, tmp_path, monkeypatch,
                                                 script, destination):
    module = script_modules[script]
    source = tmp_path / "local/iers.txt"
    source.write_text("source must survive")
    paths = {"external": tmp_path.parent / "outside.json", "project": tmp_path / "pyproject.toml",
             "existing": tmp_path / "local/existing.json", "hardlink": tmp_path / "local/link.json"}
    output = paths[destination]
    if destination in {"existing", "project"}:
        output.write_text("preserve")
    if destination == "hardlink":
        os.link(source, output)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    argv = [script, "--output", str(output)]
    if destination == "hardlink":
        argv += ["--overwrite"]
    if script == "benchmark":
        work = Mock(side_effect=AssertionError("Measurements must not begin"))
        monkeypatch.setattr(module.subprocess, "run", work)
    else:
        argv += ["--iers-file", str(source)]
        work = Mock(side_effect=AssertionError("Generation must not begin"))
        monkeypatch.setattr(module, "generate", work)
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 2
    work.assert_not_called()
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


@pytest.mark.parametrize("alias", ["direct", "relative", "hardlink"])
def test_generator_refuses_input_output_alias_even_with_overwrite(
        script_modules, tmp_path, monkeypatch, alias):
    module = script_modules["generate_satellite_reference"]
    source = tmp_path / "local/iers.json"
    source.write_text("preserve input")
    output = source
    monkeypatch.chdir(tmp_path)
    if alias == "relative":
        output = Path("local/../local/iers.json")
    if alias == "hardlink":
        output = tmp_path / "local/alias.json"
        os.link(source, output)
    work = Mock(side_effect=AssertionError("Generation must not begin"))
    monkeypatch.setattr(module, "generate", work)
    monkeypatch.setattr(sys, "argv", ["generate", "--iers-file", str(source), "--output",
                                      str(output), "--overwrite"])
    with pytest.raises(SystemExit):
        module.main()
    work.assert_not_called()
    assert source.read_text() == "preserve input"


@pytest.mark.parametrize("linked", ["source", "output", "parent"])
def test_script_paths_reject_symlinks(script_modules, tmp_path, linked):
    from _local_output import validate_output

    source = tmp_path / "local/source.json"
    source.write_text("preserve")
    target = tmp_path / "local/result.json"
    alias = tmp_path / "local/alias"
    try:
        alias.symlink_to(source.parent if linked == "parent" else source,
                         target_is_directory=linked == "parent")
    except OSError:
        pytest.skip("Windows account cannot create symlinks")
    if linked == "source":
        source = alias
    else:
        target = alias / "result.json" if linked == "parent" else alias
    with pytest.raises(ValueError, match="Lien"):
        validate_output(tmp_path, target, overwrite=True, sources=(source,))


def test_script_paths_reject_windows_junction_metadata(script_modules, tmp_path, monkeypatch):
    from _local_output import validate_output

    original = Path.lstat
    local = tmp_path / "local"

    def lstat(path, *args, **kwargs):
        if path == local:
            return SimpleNamespace(st_mode=0o40755, st_file_attributes=0x400)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", lstat)
    with pytest.raises(ValueError, match="jonction"):
        validate_output(tmp_path, local / "result.json")


def test_atomic_publication_preserves_target_on_failure_and_race(script_modules, tmp_path, monkeypatch):
    from _local_output import publish_json

    output = tmp_path / "local/result.json"
    output.write_text("old")
    original_replace = os.replace

    def failing_replace(temporary, target):
        assert output.read_text() == "old"
        assert json.loads(Path(temporary).read_text()) == {"new": True}
        raise OSError("synthetic publication failure")

    monkeypatch.setattr(os, "replace", failing_replace)
    with pytest.raises(OSError, match="publication failure"):
        publish_json(tmp_path, output, '{"new": true}', overwrite=True)
    assert output.read_text() == "old"
    assert list(output.parent.glob(".json-*")) == []
    monkeypatch.setattr(os, "replace", original_replace)
    publish_json(tmp_path, output, '{"new": true}', overwrite=True)
    assert json.loads(output.read_text()) == {"new": True}
    output.unlink()
    original_link = os.link

    def competing_link(temporary, target):
        Path(target).write_text("competing writer")
        original_link(temporary, target)

    monkeypatch.setattr(os, "link", competing_link)
    with pytest.raises(FileExistsError):
        publish_json(tmp_path, output, "{}")
    assert output.read_text() == "competing writer"
    assert list(output.parent.glob(".json-*")) == []


@pytest.mark.parametrize("script", ["benchmark", "generate_satellite_reference"])
def test_scripts_publish_local_json_with_explicit_overwrite(script_modules, tmp_path, monkeypatch, script):
    module = script_modules[script]
    output = tmp_path / "local/result.json"
    output.write_text("old")
    argv = [script, "--output", str(output), "--overwrite"]
    if script == "benchmark":
        from datetime import timezone

        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2031, 2, 3, 4, 5, tzinfo=timezone.utc)

        monkeypatch.setattr(module, "datetime", Clock)
        monkeypatch.setattr(module.subprocess, "run", Mock(return_value=SimpleNamespace(
            stdout=json.dumps(dict(seconds=1, workload={})), stderr="")))
        argv += ["--repeat", "1"]
    else:
        source = tmp_path / "local/iers.txt"
        source.write_text("source")
        argv += ["--iers-file", str(source)]
        monkeypatch.setattr(module, "generate", lambda path: {"calculated": True})
    monkeypatch.setattr(sys, "argv", argv)
    with redirect_stdout(io.StringIO()):
        module.main()
    result = json.loads(output.read_text())
    if script == "benchmark":
        assert result["measured_on"] == "2031-02-03T04:05:00+00:00"
        assert len(result["scenarios"]) == 4
    else:
        assert result == {"calculated": True}
    assert list(output.parent.glob(".json-*")) == []


def test_benchmark_sets_and_restores_offline_iers_policy(script_modules, monkeypatch):
    module = script_modules["benchmark"]
    for owner, name in ((socket.socket, "connect"), (socket.socket, "connect_ex"),
                        (socket, "create_connection")):
        monkeypatch.setattr(owner, name, getattr(owner, name))

    def run():
        assert iers.conf.auto_download is False
        assert iers.conf.auto_max_age is None
        assert iers.conf.iers_degraded_accuracy == "warn"
        with pytest.warns(iers.IERSDegradedAccuracyWarning):
            iers.IERS_B.open().ut1_utc(Time("1900-01-01"))
        return {"synthetic": True}

    monkeypatch.setattr(module, "prepare", lambda *args: run)
    with iers.conf.set_temp("iers_degraded_accuracy", "error"):
        result = module.worker("catalogs", False)
        assert result["workload"] == {"synthetic": True}
        assert iers.conf.iers_degraded_accuracy == "error"
        monkeypatch.setattr(module, "prepare", lambda *args: Mock(side_effect=RuntimeError("failed")))
        with pytest.raises(RuntimeError, match="failed"):
            module.worker("catalogs", False)
        assert iers.conf.iers_degraded_accuracy == "error"
