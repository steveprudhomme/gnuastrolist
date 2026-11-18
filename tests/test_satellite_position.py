# SPDX-FileCopyrightText: 2026 Steve Prud'Homme
# SPDX-License-Identifier: GPL-3.0-or-later
"""Coordonnées et rapports synthétiques : aucun passage réel revendiqué."""
from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from pypdf import PdfReader

from gnu_astrolist import cli
from gnu_astrolist.application import ObservationApplication
from gnu_astrolist.models import (
    DeepSkyObject,
    FieldOfView,
    MoonSummary,
    ObservationWindow,
    SatelliteTarget,
    VisibilityResult,
    WeatherPeriodSummary,
    WeatherSummary,
)
from gnu_astrolist.report_data import ReportData
from gnu_astrolist.report_formatting import position_angle_label
from gnu_astrolist.selection import CatalogSelection


@pytest.mark.parametrize('azimuth,altitude', [(231.456, 62.72), (0.0, 0.0),
                                           (180.0, None), (None, None)])
def test_coordinates_match_in_screen_text_and_pdf(tmp_path, monkeypatch, capsys,
                                                azimuth, altitude):
    instant = datetime(2026, 11, 17, 18, 33, 10, tzinfo=ZoneInfo('America/Toronto'))
    target = SatelliteTarget('Satellite synthétique', 0, 0, 'Satellite', None,
                             'NORAD 1', '', None, None, norad_id=1)
    result = VisibilityResult(target, -60.5, -48.1, 10, 20,
                              position_reference_time=instant,
                              position_azimuth_deg=azimuth, position_altitude_deg=altitude)
    period = WeatherPeriodSummary('Synthétique', instant, instant)
    data = ReportData(
        ObservationWindow(instant, instant, 'America/Toronto'), 45, 0, 0,
        FieldOfView(180, 50, 360, 60), None, 10,
        WeatherSummary(period, period, offline=True),
        MoonSummary('Synthétique', 0, 0, instant, None, None),
        # Ligne supplémentaire sans position : les colonnes doivent rester alignées.
        (result, replace(result, star=DeepSkyObject('Objet fixe synthétique', 0, 0,
                         'G', None, 'Synthetic', '', None, None),
                         position_reference_time=None, position_azimuth_deg=None,
                         position_altitude_deg=None)),
        2, CatalogSelection(('satellites', 'messier'), (None, None)),
    )
    monkeypatch.setattr(ObservationApplication, 'prepare_report', lambda *args, **kwargs: data)
    txt, pdf = tmp_path / 'synthetic.txt', tmp_path / 'synthetic.pdf'
    assert cli.main([
        '--date', '2026-11-17', '--time-range', '18:00-19:00', '--lat', '45', '--lon', '0',
        '--az-min', '0', '--az-max', '360', '--min-altitude', '20',
        '--objects', 'satellites', '--offline', '--output-txt', str(txt),
        '--output-pdf', str(pdf),
    ]) == 0
    screen = capsys.readouterr().out
    assert screen.strip() == txt.read_text(encoding='utf-8').strip()
    pdf_text = '\n'.join(page.extract_text() for page in PdfReader(pdf).pages)
    for output in (screen, pdf_text):
        assert '2026-11-17 18:33:10' in output
        assert '-60.5°' in output and '-48.1°' in output
        if azimuth is None and altitude is None:
            assert 'Azimut à cet instant' not in output
            assert 'Hauteur à cet instant' not in output
        else:
            assert 'Azimut à cet instant' in output
            assert 'Hauteur à cet instant' in output
            # Le PDF normalise les tirets typographiques avec le rendu partagé.
            assert position_angle_label(azimuth).replace('—', '-') in output.replace('—', '-')
            assert position_angle_label(altitude).replace('—', '-') in output.replace('—', '-')


def test_absence_and_zero_are_distinct():
    assert position_angle_label(None) == '—'
    assert position_angle_label(0) == '0.00°'
    assert position_angle_label(231.456) == '231.46°'
