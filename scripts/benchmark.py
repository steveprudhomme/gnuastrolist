# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Mesure hors réseau, processus neuf par charge; résultats JSON sans seuil CI."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import socket
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path

from _local_output import publish_json, validate_output

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ("catalogs", "satellites", "reports", "seestar")


def peak_rss_bytes():
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        *[(name, ctypes.c_size_t) for name in (
                            "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                            "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                            "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]]

        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return counters.PeakWorkingSetSize
    import resource
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform == "darwin" else value * 1024


def prepare(scenario, directory):
    from gnu_astrolist.models import (
        FieldOfView,
        MoonSummary,
        ObservationWindow,
        VisibilityResult,
        WeatherPeriodSummary,
        WeatherSummary,
    )
    from gnu_astrolist.selection import load_catalog_selection

    start = datetime(2026, 11, 17, 22, tzinfo=timezone.utc)
    window = ObservationWindow(start, start + timedelta(hours=2), "UTC")
    fov = FieldOfView.from_automatic_center(
        azimuth_min_deg=0, azimuth_max_deg=360, minimum_altitude_deg=85)
    kinds = ["messier", "caldwell", "ngc", "variable_stars", "bayer", "flamsteed"]
    if scenario == "catalogs":
        from gnu_astrolist.visibility import compute_visibility

        def run():
            objects, _ = load_catalog_selection(kinds, all_magnitudes=True)
            results = compute_visibility(objects, window, 51.4779, 0, 46, fov, sample_minutes=10)
            return dict(input_objects=len(objects), samples=13, selected=len(results))
        return run
    if scenario == "satellites":
        from gnu_astrolist.satellites import compute_satellite_visibility, load_satellite_elements

        def run():
            elements = load_satellite_elements()
            short = ObservationWindow(start, start + timedelta(minutes=20), "UTC")
            broad = FieldOfView.from_automatic_center(
                azimuth_min_deg=0, azimuth_max_deg=360, minimum_altitude_deg=0)
            results = compute_satellite_visibility(
                elements, short, 51.4779, 0, 46, broad, sample_seconds=30)
            return dict(input_objects=len(elements), samples=41, selected=len(results),
                        age_filter="deliberately bypassed: numerical workload, not observing advice")
        return run
    if scenario == "reports":
        from gnu_astrolist.output import render_report
        from gnu_astrolist.pdf_output import export_pdf_report

        objects, selection = load_catalog_selection(kinds, all_magnitudes=True)
        # Synthetic alt/az, explicitly not computed astronomical references.
        results = [VisibilityResult(obj, 30, 40, 100, 120) for obj in objects[:1000]]
        weather = WeatherSummary(WeatherPeriodSummary("Synthetic", start, window.end_local),
                                 WeatherPeriodSummary("Synthetic", start, window.end_local), offline=True)
        moon = MoonSummary("Synthetic workload", 0, 0, start, None, None)
        kwargs = dict(window=window, latitude_deg=51.4779, longitude_deg=0, elevation_m=46,
                      field_of_view=fov, max_magnitude=None, sample_minutes=10,
                      weather_summary=weather, moon_summary=moon, results=results,
                      matched_count=len(results), object_kind=selection, show_details=True)

        def run():
            txt = directory / "synthetic.txt"
            pdf = directory / "synthetic.pdf"
            txt.write_text(render_report(**kwargs), encoding="utf-8")
            export_pdf_report(pdf, **kwargs)
            return dict(rows=len(results), txt_bytes=txt.stat().st_size, pdf_bytes=pdf.stat().st_size)
        return run
    from gnu_astrolist.seestar import scan_seestar

    root = directory / "synthetic-seestar"
    root.mkdir()
    for number in range(1, 1001):
        folder = root / f"NGC {number}"
        folder.mkdir()
        for image in range(10):
            (folder / f"Stacked_{image}_NGC {number}_10.0s_LP_20260815-210000.fit").write_bytes(
                b"Synthetic benchmark; not FITS data\n")

    def run():
        inventory = scan_seestar(root)
        statuses = [inventory.status({f"NGC{number}"}) for number in range(1, 1001)]
        assert all(status == "Fait (empilé)" for status in statuses)
        return dict(folders=1000, files=10000, recognized=len(statuses))
    return run


def worker(scenario, memory):
    def forbidden(*args, **kwargs):
        raise RuntimeError("Benchmark hors réseau")
    socket.socket.connect = forbidden
    socket.socket.connect_ex = forbidden
    socket.create_connection = forbidden
    from astropy.utils import iers

    local = ROOT / "local/benchmark"
    local.mkdir(parents=True, exist_ok=True)
    # Every input/output is generated here; never accept an external archive path.
    with tempfile.TemporaryDirectory(dir=local) as folder:
        run = prepare(scenario, Path(folder))
        with (iers.conf.set_temp("auto_download", False),
              iers.conf.set_temp("auto_max_age", None),
              iers.conf.set_temp("iers_degraded_accuracy", "warn")):
            gc.collect()
            if memory:
                tracemalloc.start()
            started = time.perf_counter()
            counts = run()
            elapsed = time.perf_counter() - started
            peak_python = tracemalloc.get_traced_memory()[1] if memory else None
            if memory:
                tracemalloc.stop()
            return dict(seconds=elapsed, python_peak_bytes=peak_python,
                        process_peak_rss_bytes=peak_rss_bytes(), workload=counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--output", type=Path, default=ROOT / "local/benchmark-results.json")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--worker", choices=SCENARIOS)
    parser.add_argument("--memory", action="store_true")
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker, args.memory)))
        return
    if args.repeat < 1:
        parser.error("--repeat doit être positif")
    try:
        output_path = validate_output(ROOT, args.output, overwrite=args.overwrite)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONHASHSEED="0")
    output = dict(schema_version=1, measured_on=datetime.now(timezone.utc).isoformat(),
                  platform=platform.platform(),
                  python=platform.python_version(), processor=platform.processor(),
                  versions={name: version(name) for name in ("astropy", "numpy", "sgp4", "reportlab")},
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), scenarios={})
    for scenario in SCENARIOS:
        runs = []
        for memory in [False] * args.repeat + [True]:
            command = [sys.executable, str(Path(__file__).resolve()), "--worker", scenario]
            if memory:
                command.append("--memory")
            result = subprocess.run(command, env=env, cwd=ROOT, check=True, capture_output=True, text=True)
            run = json.loads(result.stdout)
            run["warnings"] = result.stderr.strip()
            runs.append(run)
        output["scenarios"][scenario] = dict(
            wall_runs=runs[:-1], median_seconds=statistics.median(r["seconds"] for r in runs[:-1]),
            memory_run=runs[-1])
        print(f"{scenario}: {output['scenarios'][scenario]['median_seconds']:.3f} s", flush=True)
    publish_json(ROOT, output_path, json.dumps(output, indent=2, ensure_ascii=False) + "\n",
                 overwrite=args.overwrite)


if __name__ == "__main__":
    main()
