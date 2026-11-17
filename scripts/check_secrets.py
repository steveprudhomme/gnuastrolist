# SPDX-FileCopyrightText: 2026 Contributeurs de GNU Astrolist
# SPDX-License-Identifier: GPL-3.0-or-later
"""Détecteur local ciblé : fichiers suivis, diagnostics sans contenu des secrets."""

import re
import subprocess
from pathlib import Path

RULES = {
    'cle-privee': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'jeton-github': re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{50,255})\b'),
    'cle-aws': re.compile(rb'\bAKIA[A-Z0-9]{16}\b'),
    'cle-openai': re.compile(rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{40,}\b'),
}


def findings(data: bytes) -> list[str]:
    return [name for name, pattern in RULES.items() if pattern.search(data)]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).split(b'\0')
    failed = False
    for name in names:
        if not name:
            continue
        path = root / name.decode('utf-8')
        if not path.is_file():
            continue
        for rule in findings(path.read_bytes()):
            # Ne jamais afficher la valeur ni la ligne qui contient le secret.
            print(f'{path.relative_to(root)} : {rule}')
            failed = True
    print('Recherche ciblée de secrets : ' + ('ÉCHEC' if failed else 'OK'))
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
