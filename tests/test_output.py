# SPDX-FileCopyrightText: 2026 Steve Prud'Homme
# SPDX-License-Identifier: GPL-3.0-or-later
from datetime import date, datetime
from zoneinfo import ZoneInfo

from gnu_astrolist.models import (
    FieldOfView,
    MessierObject,
    MoonSummary,
    ObservationWindow,
    VisibilityResult,
    WeatherPeriodSummary,
    WeatherSummary,
)
from gnu_astrolist.output import render_report


def test_report_contains_the_enriched_result_columns() -> None:
    timezone = ZoneInfo("America/Toronto")
    window = ObservationWindow(
        start_local=datetime(2026, 8, 3, 0, 0, tzinfo=timezone),
        end_local=datetime(2026, 8, 3, 1, 0, tzinfo=timezone),
        timezone_name="America/Toronto",
    )
    messier = MessierObject(
        name="M31",
        ra_deg=10.6848,
        dec_deg=41.2691,
        object_type="G",
        magnitude_v=3.44,
        catalog_designation="NGC0224",
        constellation="And",
        apparent_major_arcmin=177.83,
        apparent_minor_arcmin=69.66,
        size_source="SIMBAD",
        size_reference="2003A&A...412...45P",
        size_retrieved_on="2026-08-03",
        magnitude_source="SIMBAD",
        magnitude_reference="2007ApJS..173..185G",
        magnitude_retrieved_on="2026-08-03",
    )
    result = VisibilityResult(
        star=messier,
        altitude_start_deg=52.4,
        altitude_end_deg=61.1,
        azimuth_start_deg=48.0,
        azimuth_end_deg=60.0,
        constellation="And",
        maximum_solar_separation_date=date(2026, 9, 28),
        best_seasonal_visibility_date=date(2026, 10, 3),
        rises_above_minimum_local=datetime(2026, 8, 2, 23, 12, tzinfo=timezone),
        sets_below_minimum_local=datetime(2026, 8, 3, 7, 46, tzinfo=timezone),
    )
    moon_summary = MoonSummary(
        phase_name="Lune gibbeuse décroissante",
        illumination_percent=80.0,
        daily_illumination_percent=84.1,
        daily_illumination_reference_local=datetime(
            2026, 8, 2, 12, 0, tzinfo=timezone
        ),
        moonrise_local=datetime(2026, 8, 3, 22, 18, tzinfo=timezone),
        moonset_local=datetime(2026, 8, 3, 11, 6, tzinfo=timezone),
    )
    weather_summary = WeatherSummary(
        evening=WeatherPeriodSummary(
            name="SOIRÉE",
            start_local=datetime(2026, 8, 2, 20, 20, tzinfo=timezone),
            end_local=datetime(2026, 8, 2, 23, 20, tzinfo=timezone),
            cloud_cover_percent=25,
            seeing_quality_percent=71,
            seeing_description="0.75–1″",
            transparency_quality_percent=57,
            transparency_description="0.5–0.6 mag/masse d'air",
            stability_quality_percent=43,
            temperature_c=21.4,
            humidity_percent=77,
            wind_kmh=8.5,
            dew_risk="modéré",
            precipitation_probability_percent=15,
        ),
        predawn=WeatherPeriodSummary(
            name="AVANT L'AUBE",
            start_local=datetime(2026, 8, 3, 2, 41, tzinfo=timezone),
            end_local=datetime(2026, 8, 3, 5, 41, tzinfo=timezone),
            cloud_cover_percent=40,
        ),
        sources="Open-Meteo + 7Timer! ASTRO",
    )

    report = render_report(
        window=window,
        latitude_deg=45.57,
        longitude_deg=-73.68,
        elevation_m=20,
        field_of_view=FieldOfView(90, 70, 90, 40),
        max_magnitude=None,
        sample_minutes=10,
        weather_summary=weather_summary,
        moon_summary=moon_summary,
        results=[result],
        matched_count=1,
        object_kind="messier",
        show_details=True,
    )

    assert "Taille apparente" in report
    assert "Mag. apparente V" in report
    assert "Constellation" in report
    assert "Séparation solaire maximale" in report
    assert "Meilleure visibilité saisonnière" in report
    assert "| Opposition |" not in report
    assert "Monte ≥ 50°" in report
    assert "Descend < 50°" in report
    assert "177.83′ × 69.66′ [SIMBAD]" in report
    assert "3.44 [SIMBAD]" in report
    assert "2026-09-28" in report
    assert "2026-10-03" in report
    assert "08-02 23:12" in report
    assert "07:46" in report
    assert "PROVENANCE DÉTAILLÉE" in report
    assert "bibcode 2003A&A...412...45P" in report
    assert "récupéré le 2026-08-03" in report
    assert "RÉSUMÉ DE LA LUNE" in report
    assert "CONDITIONS MÉTÉO" in report
    assert "SOIRÉE (2026-08-02 20:20 → 23:20)" in report
    assert "AVANT L'AUBE (2026-08-03 02:41 → 05:41)" in report
    assert "Couverture nuageuse" in report
    assert "Seeing — qualité" in report
    assert "Transparence — qualité" in report
    assert "Stabilité — qualité" in report
    assert "Risque de rosée" in report
    assert "Risque de précipitation" in report
    assert "Lune gibbeuse décroissante" in report
    assert "80.0 %" in report
    assert "Illumination quotidienne (2026-08-02 12:00) : 84.1 %" in report
    assert "22:18" in report
    assert "11:06" in report
    assert report.index("CONDITIONS MÉTÉO") < report.index("RÉSUMÉ DE LA LUNE")
    assert report.index("RÉSUMÉ DE LA LUNE") < report.index("Objet | Type")
