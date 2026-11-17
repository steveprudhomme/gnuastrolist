# Verrous de développement et livraison — ECC-D

Ces quatre fichiers fixent les versions et empreintes pour Windows/Linux x86-64,
Python 3.10/3.13. Ils incluent les outils de développement; ce ne sont pas des
contraintes universelles pour toutes les plateformes ou architectures.
Les plages compatibles de l'application restent dans `pyproject.toml`.

Création d'un environnement sans paquets système, depuis la racine du projet :

```powershell
py -3.13 -m venv local/ecc-dev
local/ecc-dev/Scripts/python -m pip install --require-hashes -r requirements/py313-windows.txt
local/ecc-dev/Scripts/python -m pip install --no-deps --no-build-isolation -e .
local/ecc-dev/Scripts/python -m pip check
```

Sous Linux, utiliser `python3.13 -m venv local/ecc-dev`, les chemins `bin/python`
et le verrou `py313-linux.txt`. Pour Python 3.10, choisir le verrou `py310-*`.
Ne pas utiliser `--system-site-packages`. L'environnement historique `.venv`
reste conservé mais ne prouve plus la reproductibilité de la livraison.

Pour reconstruire les quatre verrous après une mise à jour décidée :

```powershell
local/ecc-dev/Scripts/python -m pip install uv==0.13.9
local/ecc-dev/Scripts/python scripts/lock_dependencies.py
```

Relire les différences, exécuter les audits et les tests des quatre cibles,
puis committer les verrous ensemble. Ne pas modifier à la main les empreintes
ni ignorer un échec d'audit. La résolution consulte les métadonnées publiques
PyPI; les tests ordinaires ne les interrogent pas.

Après construction, `scripts/environment_manifest.py` produit dans `local/`
l'inventaire des dépendances d'exécution, licences déclarées et empreintes des
archives et verrous. Les licences inconnues restent inconnues. Cet inventaire
n'est pas une attestation signée ni un SBOM normalisé validé; un SBOM approprié
reste requis avant une distribution incluant des dépendances/exécutables embarqués.


### Avis de sécurité au 17 novembre 2026

Les verrous 3.10 sont conservés pour les tests de compatibilité. L'audit échoue
sur Pillow/filelock, dont les versions corrigées exigent Python 3.11. Ils ne
valident pas une livraison sûre. Utiliser Python 3.13 pour la livraison actuelle;
la décision de relever la version minimale a été soumise au propriétaire.
