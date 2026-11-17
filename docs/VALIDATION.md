# Validation

## Lot astéroïdes

Validation locale Windows/Python 3.13.6 : **125 tests réussis, un ignoré**.
Les 15 avertissements comprennent les tables IERS prédictives hors couverture
et une date volontairement ancienne du test de borne. Le test ignoré concerne
la création d'un lien symbolique Windows, indisponible dans cet environnement.

Les nouveaux tests vérifient les 1 000 orbites, les schémas et éléments refusés,
les doublons, une orbite circulaire synthétique et une forte excentricité,
la magnitude H-G, H absent, G supposé, l'expiration et les filtres simultanés.
Ils couvrent la sélection mixte, les imports locaux immuables, la génération
déterministe, les rapports terminal/TXT/PDF et l'identité Seestar sur copie
synthétique. Aucun disque Seestar réel n'est consulté.

Six positions indépendantes JPL Horizons (Ceres, Vesta, Eros) sont figées avec
paramètres et empreintes. L'écart angulaire maximal est de 13,12″ sous Astropy 7.2;
l'écart de magnitude reste inférieur à 0,001. Voir [le protocole](ASTEROIDS.md).
Ces cas ne garantissent pas la précision de toutes les orbites.

Ruff et contrôle des liens/versions réussis. Construction locale sans
téléchargement avec `python -m build --no-isolation`; contrôle du contenu wheel/sdist,
y compris orbites, notice, fixture et illustration. Les deux pages du PDF
d'exemple et l'illustration SVG ont été rendues et vérifiées visuellement.
La CI locale est enrichie d'un essai du catalogue installé; son exécution
distante et toute publication restent différées.

La wheel installée dans un environnement distinct a aussi exécuté, hors du
dossier source, une sélection astéroïdes/Messier et ses exports TXT/PDF avec
Astropy 8 et ReportLab 4.5. Les sources du projet n'interviennent pas dans cet essai.

## Lot Bayer et Flamsteed

Validation locale : **102 tests réussis, un ignoré**, treize avertissements IERS.
Les tests contrôlent les 1 537 fiches Bayer et 2 737 Flamsteed, l'union de 3 321
clés HYG, les noms/coordonnées de référence, les composants partagés et les filtres.
Le générateur est testé sur des données synthétiques pour la reproductibilité,
les valeurs absentes, les noms ambigus et les empreintes incorrectes.

Les rapports terminal/TXT/PDF sont testés dans les trois modes Bayer seul,
Flamsteed seul et combinés, avec une archive Seestar synthétique. La reconnaissance
accepte les variantes explicites des lettres et préserve leurs indices. Une
désignation partagée ne devient pas une acquisition certaine de tous les composants.
Les 24 lettres grecques et les chiffres en exposant sont exigés dans les deux
polices PDF; l'extraction doit conserver `α Lyr`.

Ruff, structure et contenu des distributions réussis. La wheel installée hors
du dossier source a produit un rapport Bayer/Flamsteed et son PDF avec les polices
embarquées, sans dépendance à Matplotlib. Le disque Seestar réel n'a pas été
consulté pendant ce lot; les tests de lecture seule précédents restent inclus.
La source HYG a été téléchargée dans `local/`, puis les générateurs et contrôles
ont utilisé les copies locales. Aucune publication ou CI distante du lot.

## Finalisation de la PR nº 6

La première CI a réussi sur Linux et pour les distributions. Les tests Windows
Seestar ont révélé que les fichiers temporaires pytest étaient sur C: tandis
que le logiciel était sur D:. La protection du volume source a correctement
refusé les exports sur C:, ce qui ne correspondait pas au scénario synthétique
prévu par ces tests. La CI utilise désormais `--basetemp=.pytest_cache/ci-tmp`
sur le volume du logiciel. La protection applicative reste inchangée.

Un test Windows supplémentaire vérifie explicitement que les exports sur un
volume source distinct restent refusés, tandis qu'une copie locale permet un
rapport hors de son propre dossier. Le tutoriel commence par un guide illustré
accessible dès 10 ans, distinct du journal technique. Une nouvelle CI est requise
sur le commit contenant ces corrections avant la fusion autorisée.
Les contrôles locaux de cette finalisation ont réussi : 90 tests réussis,
un test de lien symbolique ignoré faute de permission Windows, dix avertissements
IERS; Ruff et contrôle de structure réussis.

Sur une copie GitHub neuve, le parent `.pytest_cache` n'existe pas encore.
La préparation de la CI le crée explicitement avant d'utiliser `--basetemp`;
pytest crée ensuite son dossier de tests. Cette étape ne touche que la copie
de travail, jamais les archives Seestar. Le test local précédent utilisait un
cache existant; un nouvel essai local part d'un parent dédié nouvellement créé.
Le chemin plus long de cet essai a également révélé un retour à la ligne dans
le texte extrait du PDF. Le test normalise les espaces avant de chercher les
libellés; la comparaison exacte entre sortie terminal et TXT reste inchangée.

## Lot Seestar S50 en lecture seule

Résultats locaux : **89 tests réussis, un test ignoré**, dix avertissements IERS.
Le test ignoré nécessite la création d'un lien symbolique, non autorisée dans
l'environnement Windows courant. Un test indépendant simule les attributs de
jonction Windows et vérifie qu'aucune descente n'est effectuée.

Les tests Seestar utilisent des acquisitions synthétiques : empilement, brutes,
fichiers vides, vignettes, motifs non reconnus, alias et composants distincts.
Ils vérifient les erreurs de lecture, les statuts incomplets, les sorties
terminal/TXT/PDF et les archives sources inchangées. Un test interdit toute
ouverture de fichier et les opérations d'écriture du scanner; les protections
d'export couvrent chemins relatifs, liens physiques et création temporaire PDF.

Ruff et contrôles de structure/distributions réussis. La wheel installée hors
du dossier source a exécuté l'option sur une archive synthétique locale, sans
téléchargement. Le contrôle exige `seestar.py` dans les paquets et l'illustration
dans l'archive source. La CI distante du lot n'a pas été exécutée.

Un essai manuel autorisé a consulté le véritable dossier MyWorks sans ouvrir
les images ni écrire sur son volume; les rapports personnels TXT/PDF restent
dans `local/`, ignoré par Git. Les statuts du PDF ont aussi été vérifiés par
extraction de texte. Ces vérifications ne constituent pas un audit matériel
du disque ni une validation scientifique des images.

## Lot sélection multiple

Résultats locaux : **75 tests réussis**, huit avertissements IERS, Ruff et
contrôles de structure/distributions réussis. Les tests couvrent les noms et
options répétés, l'alias `messier_objects`, l'ordre indépendant de priorité,
M31/NGC224, C1/NGC188, les composants distincts et les désignations absentes.
Ils vérifient aussi la priorité avant filtre, la limite GCVS par défaut, les
limites explicites, `--all-magnitudes` et les sorties terminal/TXT/PDF mixtes.

La wheel et l'archive source incluent `selection.py`; le schéma multicatalogue
est exigé dans l'archive source. Une installation de la wheel sans téléchargement
a exécuté la commande Messier/Caldwell/NGC hors du dossier source. Le résultat
de cette commande de contrôle (UTC, latitude 45°, seuil V=5) est de 10 entrées.
La CI distante de ce lot n'a pas été exécutée; aucun push n'est effectué.

## Lot NGC

Le générateur local exige l'empreinte de la copie OpenNGC documentée. Les tests
vérifient 8 098 identifiants uniques, 4 592 magnitudes absentes, NGC224 et
NGC1976, les composants NGC61A/B, le filtre de magnitude, l'ordre numérique,
les exclusions, la reproductibilité et le rejet des doublons et sources altérées.
Les tests d'intégration vérifient les rapports TXT/PDF non vides et vides hors ligne.
Le contrôle des distributions exige le catalogue, sa notice et le schéma NGC
dans l'archive source. Les résultats CI du précédent lot Caldwell ne valent pas
validation distante du nouveau lot NGC.

Résultats locaux NGC : 65 tests réussis, cinq avertissements IERS, Ruff et
contrôles des liens/structure/distributions réussis. Construction sans isolation
ni téléchargement avec les outils présents. La wheel installée hors des sources
charge 8 098 entrées et exécute la commande NGC hors ligne. Le tutoriel consigne
un essai complet sans filtre V (1 975 entrées sélectionnées pour l'exemple de
Laval). Aucun nouveau résultat CI distant n'est revendiqué pour ce lot.

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
