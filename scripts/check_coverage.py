# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Planchers mesurés, lignes ET branches, sans exclure les générateurs historiques."""

import argparse
import json


def rates(summary):
    lines = summary['covered_lines'] / max(1, summary['num_statements']) * 100
    branches = (summary['covered_branches'] / summary['num_branches'] * 100
                if summary['num_branches'] else 100)
    return lines, branches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', help='Rapport JSON de coverage')
    args = parser.parse_args()
    with open(args.report, encoding='utf-8') as stream:
        data = json.load(stream)
    floors = {'validation.py': (90, 90), 'report_files.py': (90, 90),
              'weather.py': (90, 90), 'versioning.py': (90, 85)}
    failed = []
    if data.get('meta', {}).get('branch_coverage') is not True:
        failed.append('Mesure des branches absente du rapport')
    total = data['totals']['percent_covered']
    if total < 88:
        failed.append(f'ensemble : {total:.2f} % < 88 %')
    lines, branches = rates(data['totals'])
    if lines < 90 or branches < 82:
        failed.append('Planchers séparés : lignes 90 %, branches 82 % requis')
    for module, (line_floor, branch_floor) in floors.items():
        matches = [rates(item['summary']) for name, item in data['files'].items()
                   if name.replace('\\', '/').endswith('/' + module)]
        if (len(matches) != 1 or matches[0][0] < line_floor
                or matches[0][1] < branch_floor):
            failed.append(f'{module} : planchers lignes {line_floor} % / branches '
                          f'{branch_floor} % non atteints ou fichier absent')
    print('\n'.join(failed) if failed else 'Couverture globale et chemins critiques : OK')
    return bool(failed)


if __name__ == '__main__':
    raise SystemExit(main())
