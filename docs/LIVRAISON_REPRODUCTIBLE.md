# Environnements et livraison reproductibles — ECC-D

Le projet dispose de quatre verrous avec versions exactes et empreintes :
Windows/Linux x86-64, Python 3.10/3.13. NumPy est une dépendance directe, car le
code l'importe directement. La procédure de reconstruction est dans
[requirements/README.md](../requirements/README.md).

L'environnement historique `.venv` héritait de paquets système et présentait
des conflits provenant d'un autre logiciel. Il est conservé; les contrôles de
livraison utilisent désormais des environnements sans paquets système, créés
sous `local/`. Aucun outil n'est installé globalement.

## Procédure

1. Installer un correctif récent de la version Python choisie, puis créer
   l'environnement isolé selon le guide des verrous.
2. Installer le fichier correspondant avec `--require-hashes`.
3. Installer le projet avec `--no-deps --no-build-isolation` et vérifier
   `pip check` (ou `uv pip check` dans l'environnement géré).
4. Exécuter les tests et contrôles du dépôt, construire wheel/sdist et vérifier
   leur contenu. Installer la wheel dans un environnement distinct et lancer
   les dix sélections ainsi que les exports hors ligne, hors du dossier source.
5. Produire l'inventaire local :

```powershell
local/ecc-dev/Scripts/python scripts/environment_manifest.py --dist dist --output local/environment-manifest.json
```

Cet inventaire contient les dépendances d'exécution, leurs licences déclarées
et les empreintes des archives/verrous. Il ne contient ni chemins personnels,
ni inventaire Seestar. Il n'est pas un SBOM normalisé ou une signature. Un
paquet Python qui ne redistribue pas ses dépendances ne les relicencie pas;
une future distribution autonome devra produire le SBOM et les notices adaptés.

## Validation initiale

Windows, environnements isolés : 564 tests réussis, trois ignorés sous Python
3.13.6 (Astropy 8.0.2, NumPy 2.5.5) et Python 3.10.16 (Astropy 6.1.7,
NumPy 2.2.6). Le nombre d'avertissements IERS/ERFA varie selon les tables et
versions : 12 sous 3.13, 87 sous 3.10. Aucun avertissement n'est masqué.

L'ancien interpréteur 3.10.0 de cette machine échoue au démarrage de pytest
9.2.0, avant les tests de l'application. Il n'est pas utilisé comme environnement
de livraison validé. Le verrou de dépendances ne fige pas l'interpréteur lui-même :
sa version exacte est consignée dans l'inventaire. Les résultats Linux et les
derniers commits se vérifient dans la CI, pas par extrapolation des essais Windows.


## État de sécurité après ECC-E

Le verrou Python 3.13 Windows/Linux ne présente aucun avis connu lors de l'audit
du 17 novembre 2026. Python 3.10 reste testé pour compatibilité, mais son audit
échoue sur Pillow 12.3.0 et filelock 4.1.0 : les correctifs exigent Python 3.11.
Ce verrou ne constitue donc pas une livraison de sécurité validée. La décision
sur la version minimale est en attente; ne pas ignorer les avis pour publier.
L'inventaire exige un dossier parent existant sous `local/`, refuse liens et
collisions et publie atomiquement. Ajouter `--overwrite` pour remplacer un
inventaire existant, jamais pour autoriser l'écrasement d'une source.
