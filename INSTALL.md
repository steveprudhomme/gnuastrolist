# Installation et développement

Python 3.10 ou plus récent est requis. Depuis la racine du dépôt, créer un
environnement isolé; les catalogues sont inclus dans le paquet.

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m build
```

Sous Linux/macOS, utiliser `python3 -m venv .venv`, puis remplacer
`.venv\Scripts\python` par `.venv/bin/python`.

L'installation initiale télécharge les dépendances. Le calcul astronomique et
les catalogues fonctionnent ensuite avec `--offline`. Sans cette option, les
coordonnées demandées sont envoyées aux fournisseurs météo; voir PRIVACY.md.

Voir le [tutoriel](docs/TUTORIEL.md) pour un exemple complet et les
[contrôles de validation](docs/VALIDATION.md) pour la portée des tests.
