# Validation

## Correctif de la première CI

Python 3.10 sur Windows et Linux a révélé une dépendance du test de tri Caldwell
à la configuration IERS laissée par d'autres tests. Le test fixe maintenant ses
paramètres dans des contextes temporaires qui les restaurent en sortie. Les
avertissements de précision restent visibles. Les résultats CI précédents ne
doivent pas être présentés comme tous réussis; une nouvelle exécution est requise.
Le test isolé, les 61 tests locaux, Ruff et le contrôle de structure ont réussi
après le correctif sous Windows/Python 3.13.6.

Exécuter depuis un environnement installé avec `pip install -e ".[dev]"` :

```text
python -m pytest
python -m ruff check .
python scripts/check_repository.py
python -m build
python scripts/check_distribution.py
```

Les tests couvrent les catalogues, filtres, limites du champ, heures civiles,
conventions lunaires, agrégations météo simulées, interface et exports TXT/PDF.
Les tests Caldwell vérifient la liste C1–C109, des identifications de référence,
les magnitudes absentes, le tri, la provenance et les sorties réelles.

Les tests ordinaires utilisent les catalogues publics et des cas synthétiques,
sans requête météo ni mise à jour IERS. Les avertissements IERS sur les dates
hors couverture des tables embarquées sont distincts des échecs de tests : ils
signalent une précision astronomique dégradée possible.

La CI définie dans `.github/workflows/quality.yml` vérifie Windows et Linux,
Python 3.10 et 3.13, et construit les archives sur Linux. Son résultat distant
ne peut être confirmé avant exécution sur GitHub. La vérification d'une archive
confirme son contenu et son installation; elle ne remplace pas une comparaison
astrométrique et photométrique avec des références indépendantes.

## Vérification locale du lot Caldwell

Sur Windows, Python 3.13.6 : **61 tests réussis**, Ruff et contrôle de structure
réussis. L'environnement de tests utilise Astropy 7.2.0 et ReportLab 4.4.7.
Quatre avertissements IERS sont émis sur les cas hors couverture prédictive.
Les sources OpenNGC épinglées reconstruisent exactement le gzip distribué.
La wheel et la sdist incluent les trois catalogues, la notice Caldwell et la GPL,
sans les anciens rapports d'exemple présents à la racine du dépôt.

Un environnement neuf a installé la wheel avec Astropy 8.0.2 et ReportLab 4.5.1;
la commande Caldwell hors ligne a fonctionné hors du répertoire des sources.
Le cas d'exemple de Laval trouve 35 objets, dont les trois premières lignes
sont C28, C13 et C16. La sortie Windows redirigée est également testée en UTF-8.

Les résultats Linux et Python 3.10 attendent l'exécution de la CI GitHub.
Le verrouillage des dépendances, le SBOM et l'audit des anciens avis de licence
restent des tâches de livraison explicites dans ROADMAP.md.

## Finalisation exclusivement locale

Après le commit de planification `f737e4d`, les 61 tests et les contrôles Ruff,
structure et distributions ont de nouveau réussi. La construction utilise
`--no-isolation` avec setuptools 84.2.1 récupéré dans le cache local, sans
téléchargement. Le contrôle de l'archive source exige aussi les deux images SVG
du tutoriel. Les opérations GitHub sont différées selon la consigne utilisateur.

La revue locale a confirmé la séparation du plan (`f737e4d`), de la fonctionnalité
(`8015cc8`) et du cadre/documentation (`f308106`), puis un arbre de travail propre.
Les 31 magnitudes V absentes, les avertissements IERS et la CI distante non
exécutée restent des limites explicites. L'archive météo n'est pas implémentée.
