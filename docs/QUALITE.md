# Vérifications automatiques — ECC-E

Les tests ordinaires restent hors réseau. Les archives Seestar utilisées sont
synthétiques et les fichiers temporaires restent dans le projet.

## Couverture mesurée

La première mesure isolée Python 3.13 donne 90 % (lignes et branches combinées,
566 tests). Le seuil combiné initial est 88 %, avec des seuils séparés de
90 % des lignes et 82 % des branches (mesure initiale : 91,71 % et 84,85 %).
Les modules critiques exigent 90 % des lignes ET 90 % des branches sur `validation.py`,
`report_files.py` et `weather.py`. Les générateurs anciens restent inclus :
aucune exclusion artificielle ne gonfle le résultat. Les seuils ne remplacent
pas les tests de sécurité et de sorties publiques.

```powershell
python -m pytest --basetemp=local/test-tmp --cov --cov-branch --cov-report=json:local/coverage.json
python scripts/check_coverage.py local/coverage.json
python -m mypy
python -m ruff check .
python scripts/check_secrets.py
```

Le typage strict commence par le module de validation et le modèle de rapport partagé. Les dépendances Astropy
et NumPy sont hors de ce périmètre initial; leur typage complet n'est pas
revendiqué. Ruff ajoute les règles B006/B008/B018/B019 (défauts de valeurs par
défaut, expressions sans effet, caches de méthodes).

## Secrets et dépendances

Le détecteur local vise clés privées et formats de jetons courants dans les
fichiers suivis. Il imprime uniquement fichier et règle, jamais le secret.
Il ne détecte pas tous les secrets; son passage ne certifie pas l'historique.

L'audit actualisé consulte les avis publics pour chaque verrou complet :

```powershell
python -m pip_audit -r requirements/py313-windows.txt --require-hashes --disable-pip
```

Ce contrôle demande le réseau et reste distinct de pytest. Une absence d'avis
connus à une date donnée ne garantit pas l'absence de vulnérabilité.
La CI exécute les quatre combinaisons Python/OS, installe avec empreintes,
borne chaque job à 15 minutes et vérifie types, secrets et dépendances.
Les actions GitHub sont épinglées à des révisions officielles vérifiées.

Après accord du propriétaire, la matrice cible Python 3.11/3.13. Les verrous
3.10 vulnérables sont retirés; aucun avis n’est ignoré pour faire réussir le contrôle.
