# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Les diagnostics de sécurité ne doivent pas recopier la donnée sensible."""

import runpy
from pathlib import Path


def test_secret_rules_recognize_synthetic_tokens_without_returning_values():
    scan = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/check_secrets.py'))
    for prefix, suffix, expected in [
        (b'ghp_', b'A' * 36, 'jeton-github'),
        (b'AKIA', b'B' * 16, 'cle-aws'),
        (b'sk-proj-', b'C' * 48, 'cle-openai'),
        (b'-----BEGIN ', b'PRIVATE KEY-----', 'cle-privee'),
        (b'-----BEGIN ENCRYPTED ', b'PRIVATE KEY-----', 'cle-privee'),
    ]:
        token = prefix + suffix
        result = scan['findings'](b'exemple synthetique ' + token)
        assert result == [expected]
        assert token.decode() not in repr(result)
    assert scan['findings'](b'aucun secret dans cet exemple public') == []


def test_coverage_control_rejects_report_without_branch_measurement(tmp_path, monkeypatch):
    import json
    import sys

    report = tmp_path / 'lines-only.json'
    summary = {'percent_covered': 100, 'covered_lines': 100, 'num_statements': 100,
               'covered_branches': 2, 'num_branches': 2}
    report.write_text(json.dumps({
        'meta': {'branch_coverage': False}, 'totals': summary,
        'files': {f'src/gnu_astrolist/{name}.py': {'summary': summary}
                  for name in ('validation', 'report_files', 'weather')},
    }), encoding='utf-8')
    script = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/check_coverage.py'))
    monkeypatch.setattr(sys, 'argv', ['check_coverage.py', str(report)])
    assert script['main']() is True


def test_line_coverage_cannot_hide_uncovered_branches(tmp_path, monkeypatch):
    import json
    import sys

    report = tmp_path / 'missing-branches.json'
    summary = {'percent_covered': 98.04, 'covered_lines': 100, 'num_statements': 100,
               'covered_branches': 0, 'num_branches': 2}
    report.write_text(json.dumps({
        'meta': {'branch_coverage': True}, 'totals': summary,
        'files': {f'src/gnu_astrolist/{name}.py': {'summary': summary}
                  for name in ('validation', 'report_files', 'weather')},
    }), encoding='utf-8')
    script = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/check_coverage.py'))
    monkeypatch.setattr(sys, 'argv', ['check_coverage.py', str(report)])
    assert script['main']() is True
