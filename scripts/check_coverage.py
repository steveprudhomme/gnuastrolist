# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Planchers mesurés, lignes ET branches, sans exclure les générateurs historiques."""

import argparse
import json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', help='Rapport JSON de coverage')
    args = parser.parse_args()
    with open(args.report, encoding='utf-8') as stream:
        data = json.load(stream)
    floors = {'validation.py': 90, 'report_files.py': 90, 'weather.py': 90}
    failed = []
    total = data['totals']['percent_covered']
    if total < 88:
        failed.append(f'ensemble : {total:.2f} % < 88 %')
    for module, floor in floors.items():
        matches = [item['summary']['percent_covered'] for name, item in data['files'].items()
                   if name.replace('\\', '/').endswith('/' + module)]
        if len(matches) != 1 or matches[0] < floor:
            failed.append(f'{module} : plancher {floor} % non atteint ou fichier absent')
    print('\n'.join(failed) if failed else 'Couverture globale et chemins critiques : OK')
    return bool(failed)


if __name__ == '__main__':
    raise SystemExit(main())
