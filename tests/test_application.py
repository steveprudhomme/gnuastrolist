# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""ECC-G : orchestration et isolation; valeurs de calcul exclusivement synthétiques."""
from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from astropy.utils import iers
from pypdf import PdfReader

from gnu_astrolist import cli
from gnu_astrolist.application import (
    ApplicationDependencies,
    ObservationApplication,
    ObservationRequest,
    astronomical_context,
)
from gnu_astrolist.catalog_resources import catalog_resource
from gnu_astrolist.models import MoonSummary, VariableStar, VisibilityResult
from gnu_astrolist.output import render_report
from gnu_astrolist.pdf_output import PdfExportError, export_pdf_report
from gnu_astrolist.report_data import ReportData
from gnu_astrolist.selection import CatalogSelection
from gnu_astrolist.updates import UpdateResult
from gnu_astrolist.weather import compute_weather_summary


def request(**changes):
    return replace(ObservationRequest(
        date='2026-08-15', time_range='21:00-22:00', timezone='UTC',
        lat=45, lon=0, elevation_m=0, az_min=0, az_max=360,
        min_altitude=20, alt_center=None, objects=('messier',), offline=True,
    ), **changes)


def iers_state():
    return (iers.conf.auto_download, iers.conf.auto_max_age, iers.conf.iers_degraded_accuracy)


def fake_moon(**kwargs):
    return MoonSummary('Phase synthétique', 0, 0,
                       datetime(2026, 8, 15, tzinfo=timezone.utc), None, None)


def fake_weather(**kwargs):
    return compute_weather_summary(**{**kwargs, 'offline': True})


def dependencies(**changes):
    return replace(ApplicationDependencies(
        load_catalog_selection=lambda *args: ((), CatalogSelection(('messier',), (None,))),
        compute_weather_summary=fake_weather, compute_moon_summary=fake_moon,
    ), **changes)


@pytest.mark.parametrize('offline', [True, False])
@pytest.mark.parametrize('failure', [False, True])
def test_context_restores_nondefault_settings_and_nested_calls(offline, failure):
    with (iers.conf.set_temp('auto_download', True),
          iers.conf.set_temp('auto_max_age', 72.0),
          iers.conf.set_temp('iers_degraded_accuracy', 'error')):
        original = iers_state()
        def run():
            with astronomical_context(offline):
                active = (not offline, None if offline else 30.0, 'warn')
                assert iers_state() == active
                with astronomical_context(not offline):
                    assert iers.conf.auto_download == offline
                assert iers_state() == active
                if failure:
                    raise RuntimeError('échec synthétique')
        if failure:
            with pytest.raises(RuntimeError, match='synthétique'):
                run()
        else:
            run()
        assert iers_state() == original


def test_service_returns_shared_data_with_count_before_limit_and_no_output(capsys):
    star = VariableStar('Objet synthétique', 0, 0, 'Test', 1, None, 'V')
    result = VisibilityResult(star, 30, 40, 0, 10)
    raw = [result, result]
    deps = dependencies(
        load_catalog_selection=lambda *args: ((star,), CatalogSelection(('messier',), (None,))),
        compute_visibility=lambda **kwargs: raw,
    )
    before = iers_state()
    data = ObservationApplication(deps).prepare_report(request(limit=1), source_notes=('Test',))
    assert isinstance(data, ReportData)
    assert data.matched_count == 2 and data.results == (result,)
    assert data.results[0] is result
    assert data.object_kind.source_notes == ('Test',)
    kwargs = data.to_kwargs()
    assert kwargs['weather_summary'] is data.weather_summary
    kwargs.pop('results')
    raw.clear()
    assert data.results == (result,)
    assert iers_state() == before
    assert capsys.readouterr().out == ''


@pytest.mark.parametrize('stage', ['load_catalog_selection', 'compute_weather_summary',
                                    'compute_moon_summary', 'compute_visibility', 'scan_seestar'])
@pytest.mark.parametrize('error_type', [ValueError, RuntimeError])
def test_service_restores_context_after_failure_and_can_be_reused(stage, error_type):
    star = VariableStar('Objet synthétique', 0, 0, 'Test', 1, None, 'V')
    calls = []
    def fail(*args, **kwargs):
        calls.append(iers_state())
        raise error_type('échec synthétique')
    deps = dependencies(
        load_catalog_selection=lambda *args: ((star,), CatalogSelection(('messier',), (None,))),
        compute_visibility=lambda **kwargs: [],
    )
    application = ObservationApplication(replace(deps, **{stage: fail}))
    before = iers_state()
    with pytest.raises(error_type, match='synthétique'):
        application.prepare_report(request(), seestar_root='source-synthetique')
    assert calls == [(False, None, 'warn')]
    assert iers_state() == before
    application.dependencies = deps
    assert application.prepare_report(request()).matched_count == 0
    assert iers_state() == before


@pytest.mark.parametrize('changes', [dict(lat=float('nan')), dict(limit=0),
                                    dict(limit=0.5), dict(limit=True), dict(limit=float('nan')),
                                    dict(satellite_max_epoch_hours=0),
                                    dict(satellite_max_epoch_hours=1e20),
                                    dict(sample_minutes=1e-9), dict(objects=('inconnu',))])
def test_direct_service_rejects_invalid_request_before_dependencies(changes):
    weather = Mock(side_effect=AssertionError('collaborateur sollicité'))
    before = iers_state()
    with pytest.raises(ValueError):
        ObservationApplication(dependencies(compute_weather_summary=weather)).prepare_report(
            request(**changes))
    weather.assert_not_called()
    assert iers_state() == before


def test_catalog_and_iers_contexts_use_same_reentrant_lock():
    from gnu_astrolist import application, catalog_resources

    assert application.application_context_lock is catalog_resources.application_context_lock
    # Ces deux ordres publics ne peuvent plus inverser deux verrous distincts.
    with astronomical_context(True), catalog_resources.use_catalog_resources({}):
        with catalog_resources.use_catalog_resources({}), astronomical_context(True):
            assert iers.conf.auto_download is False


def test_cli_reports_cache_lock_timeout_without_traceback(monkeypatch, capsys):
    def timeout(*args, **kwargs):
        raise TimeoutError('Cache lock timeout')

    monkeypatch.setattr(cli, 'refresh_catalogs', timeout)
    with pytest.raises(SystemExit) as caught:
        cli.main(['--date', '2026-11-17', '--time-range', '21:00-22:00',
                  '--lat', '45', '--lon', '0', '--az-min', '0', '--az-max', '360',
                  '--min-altitude', '10', '--objects', 'messier', '--offline'])
    assert caught.value.code == 2
    assert 'Cache lock timeout' in capsys.readouterr().err


def test_shared_data_adapts_to_both_existing_render_apis(tmp_path):
    data = ObservationApplication(dependencies()).prepare_report(request())
    text = render_report(**data.to_kwargs())
    path = tmp_path / 'synthetic.pdf'
    export_pdf_report(path, **data.to_kwargs())
    pdf_text = '\n'.join(page.extract_text() for page in PdfReader(path).pages)
    for phrase in ('SOIRÉE', 'Phase synthétique', 'Aucun objet'):
        assert phrase in text and phrase in pdf_text


def arguments():
    return ['--date', '2026-08-15', '--time-range', '21:00-22:00',
            '--lat', '45', '--lon', '0', '--az-min', '0', '--az-max', '360',
            '--min-altitude', '20', '--objects', 'messier', '--max-magnitude', '-20']


@pytest.mark.parametrize('error_type', [ValueError, RuntimeError])
@pytest.mark.parametrize('failure_stage', ['refresh', 'weather', 'moon', 'render', 'txt', 'pdf'])
def test_cli_restores_iers_and_resources_then_accepts_next_command(
    failure_stage, error_type, tmp_path, monkeypatch, capsys,
):
    resource_name = 'ecc-g-synthetic.txt'
    resource_path = tmp_path / resource_name
    resource_path.write_text('synthétique', encoding='utf-8')
    original_resource = catalog_resource(resource_name)
    original_iers = iers_state()
    seen = []
    def refresh(*args, **kwargs):
        seen.append(iers_state())
        if failure_stage == 'refresh':
            raise error_type('échec synthétique')
        return UpdateResult({resource_name: resource_path}, ())
    def fail(*args, **kwargs):
        assert catalog_resource(resource_name) == resource_path
        raise error_type('échec synthétique')
    def render(*args, **kwargs):
        fail()
    def fail_pdf(*args, **kwargs):
        assert catalog_resource(resource_name) == resource_path
        raise (PdfExportError if error_type is ValueError else error_type)('échec synthétique')
    with monkeypatch.context() as patch:
        patch.setattr(cli, 'refresh_catalogs', refresh)
        patch.setattr(cli, 'compute_weather_summary', fake_weather)
        patch.setattr(cli, 'compute_moon_summary', fake_moon)
        patch.setattr(cli, 'render_report', lambda **kwargs: 'Rapport synthétique')
        argv = arguments() + ['--offline']
        if failure_stage == 'weather':
            patch.setattr(cli, 'compute_weather_summary', fail)
        elif failure_stage == 'moon':
            patch.setattr(cli, 'compute_moon_summary', fail)
        elif failure_stage == 'render':
            patch.setattr(cli, 'render_report', render)
        elif failure_stage == 'pdf':
            patch.setattr(cli, 'export_pdf_report', fail_pdf)
            argv += ['--output-pdf', str(tmp_path / 'synthetic.pdf')]
        elif failure_stage == 'txt':
            # Failure during staged write, after preflight and calculation.
            patch.setattr(cli, 'staged_report', fail)
            argv += ['--output-txt', str(tmp_path / 'synthetic.txt')]
        expected = SystemExit if error_type is ValueError else error_type
        with pytest.raises(expected):
            cli.main(argv)
    assert iers_state() == original_iers
    assert catalog_resource(resource_name) == original_resource
    assert seen == [(False, None, 'warn')]
    with monkeypatch.context() as patch:
        def second_refresh(*args, **kwargs):
            assert iers_state() == (True, 30.0, 'warn')
            assert catalog_resource(resource_name) == original_resource
            return UpdateResult({}, ())
        patch.setattr(cli, 'refresh_catalogs', second_refresh)
        patch.setattr(cli, 'compute_weather_summary', fake_weather)
        patch.setattr(cli, 'compute_moon_summary', fake_moon)
        assert cli.main(arguments()) == 0
    assert iers_state() == original_iers
    assert catalog_resource(resource_name) == original_resource
    capsys.readouterr()


def test_successful_commands_restore_active_resources_and_iers(tmp_path, monkeypatch, capsys):
    name = 'ecc-g-success-synthetic.txt'
    path = tmp_path / name
    path.write_text('synthétique', encoding='utf-8')
    before_resource, before_iers = catalog_resource(name), iers_state()
    seen = []
    def refresh(*args, **kwargs):
        assert catalog_resource(name) == before_resource
        return UpdateResult({name: path}, ())
    def render(**kwargs):
        assert catalog_resource(name) == path
        seen.append(iers_state())
        return 'Rapport synthétique'
    monkeypatch.setattr(cli, 'refresh_catalogs', refresh)
    monkeypatch.setattr(cli, 'compute_weather_summary', fake_weather)
    monkeypatch.setattr(cli, 'compute_moon_summary', fake_moon)
    monkeypatch.setattr(cli, 'render_report', render)
    for suffix in (['--offline'], []):
        assert cli.main(arguments() + suffix) == 0
        assert catalog_resource(name) == before_resource
        assert iers_state() == before_iers
    assert seen == [(False, None, 'warn'), (True, 30.0, 'warn')]
    capsys.readouterr()
