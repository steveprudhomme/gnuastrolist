from datetime import date, datetime
from zoneinfo import ZoneInfo

from gnu_astrolist.models import (
    FieldOfView,
    MessierObject,
    ObservationWindow,
    VisibilityResult,
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
        opposition_date=date(2026, 9, 28),
        rises_above_minimum_local=datetime(2026, 8, 2, 23, 12, tzinfo=timezone),
        sets_below_minimum_local=datetime(2026, 8, 3, 7, 46, tzinfo=timezone),
    )

    report = render_report(
        window=window,
        latitude_deg=45.57,
        longitude_deg=-73.68,
        elevation_m=20,
        field_of_view=FieldOfView(90, 70, 90, 40),
        max_magnitude=None,
        sample_minutes=10,
        results=[result],
        matched_count=1,
        object_kind="messier",
        show_details=True,
    )

    assert "Taille apparente" in report
    assert "Mag. apparente V" in report
    assert "Constellation" in report
    assert "Opposition" in report
    assert "Monte ≥ 50°" in report
    assert "Descend < 50°" in report
    assert "177.83′ × 69.66′ [SIMBAD]" in report
    assert "3.44 [SIMBAD]" in report
    assert "2026-09-28" in report
    assert "08-02 23:12" in report
    assert "07:46" in report
    assert "PROVENANCE DÉTAILLÉE" in report
    assert "bibcode 2003A&A...412...45P" in report
    assert "récupéré le 2026-08-03" in report
