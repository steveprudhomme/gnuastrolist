# Validation

## ECC-A — Entrées protégées et exports atomiques

Le plan détaillé a été commité et publié avant les nouveaux tests et le code :
`8276bb4`, empreinte distante vérifiée. Les méthodes ECC `python-testing`,
`python-patterns`, `security-review` et `verification-loop` ont guidé les
régressions, les contrôles partagés des fichiers et la revue finale locale.

Windows/Python 3.13.6 : **385 tests réussis, trois ignorés, 26 avertissements**.
Les 35 nouveaux tests réussis couvrent les sept entrées × deux sorties, les
chemins équivalents, liens physiques et jonctions simulées, refus avant effets,
protection Seestar malgré `--overwrite`, remplacement explicite, pannes d'écriture
TXT/PDF et de publication, et créations concurrentes avant/pendant publication.
Les trois cas ignorés sont les deux créations de liens symboliques non
autorisées localement et le test de FIFO réservé à POSIX. Les avertissements
IERS/ERFA sont ceux des modèles/dates déjà documentés, sans nouveau masquage.

Ruff, contrôle du dépôt, différences sans erreurs d'espacement et XML du schéma
réussis. Wheel et sdist construites sans téléchargement, puis vérifiées avec le
contrôleur existant dirigé en mémoire vers `local/ecc-a-dist/`. La wheel a été
réinstallée sans dépendances ni réseau dans `.wheel-check`, environnement distinct
sans paquets système; `pip check` y réussit. Cette opération ne corrige pas
l'environnement de développement principal, objet du futur lot ECC-D.

Exécutée hors des sources, cette installation produit un TXT/PDF de trois objets,
refuse leur remplacement implicite, accepte `--overwrite`, protège le fichier de
configuration et exécute les dix sélections ensemble hors ligne. L'empreinte de
l'acquisition Seestar synthétique reste identique. Le schéma du tutoriel et les
deux pages du PDF de démonstration ont été rendus et inspectés visuellement.
Aucun disque USB réel n'a été parcouru ni modifié.

L'atomicité est par fichier, pas pour la paire TXT/PDF. Les limites de panne
matérielle, d'arrêt brutal et de changement malveillant de chemin sont explicites
dans [EXPORTS.md](EXPORTS.md). Couverture et typage statique supplémentaires
restent au lot ECC-E; leur réussite n'est pas revendiquée ici. Le correctif
`f37c3c0` et ses documents sont publiés dans la
[PR nº 9](https://github.com/steveprudhomme/gnuastrolist/pull/9). Pour le commit
`97b7671`, les cinq contrôles distants ont réussi : Windows/Linux en Python
3.10 et 3.13, puis distributions et essais installés hors des sources. Voir
l'[exécution vérifiée](https://github.com/steveprudhomme/gnuastrolist/actions/runs/44057483487).
Avant toute fusion, vérifier également les contrôles du dernier commit de la PR;
la réussite d'un commit précédent ne remplace pas cette vérification.

## Publication GitHub — compatibilité des époques GP

La première CI de la PR nº 7 a détecté trois échecs sous Python 3.10 pour les
fractions de neuf chiffres, alors que Python 3.13 et les paquets réussissaient.
Le calendrier est désormais validé sans la fraction dans une copie temporaire;
la chaîne originale complète reste transmise à Astropy. Les tests couvrent
également les fractions de 1, 3, 5 et 6 chiffres. Aucune valeur orbitale de la
source n'est modifiée. Le plan du correctif a été commité avant le code.

Après le correctif `9cc0d57`, **350 tests locaux réussissent, un est ignoré**,
avec 26 avertissements IERS/ERFA documentés. Les cinq contrôles de la
[PR nº 7](https://github.com/steveprudhomme/gnuastrolist/pull/7) ont réussi :
tests Windows/Linux en Python 3.10 et 3.13, puis construction et vérification
des distributions. Voir l'[exécution GitHub](https://github.com/steveprudhomme/gnuastrolist/actions/runs/44045350000).
Cette publication et sa fusion dans main ont été explicitement demandées par
le propriétaire; la consigne de travail local reste le défaut des autres lots.

## Satellites artificiels, SATCAT et registre ONU

Validation Windows/Python 3.13.6 : **338 tests réussis, un ignoré**, avec
26 avertissements IERS/ERFA déjà liés aux dates des autres catalogues.
Les 38 tests des actualisations satellitaires passent également avec des
réponses CSV reconstruites depuis les seules valeurs versionnées : aucun
dossier `local/` privé n'est nécessaire à leur exécution dans la CI.

Les cas Vallado livrés avec SGP4 vérifient les vecteurs TEME et la propagation.
Les tests contrôlent le rayon topocentrique, les formats GP/OMM, les conventions
de temps et repère, les numéros NORAD étendus, les erreurs SGP4 et les critères
champ/éclairage/hauteur solaire appliqués au même instant. Ils ne représentent
pas une validation observationnelle de chaque objet réel.

La sélection embarquée est contrôlée : 737 GP, 1 873 SATCAT, jointures
NORAD/COSPAR cohérentes, types PAY/R/B/DEB préservés. Les époques trop éloignées,
rentrées et types non choisis sont exclus explicitement. Les tests UNOOSA sont
synthétiques et couvrent sources, dates, contradictions, pièces distinctes et
statut inconnu. Les rapports terminal/TXT/PDF sont vérifiés avec un inventaire
Seestar synthétique, sans modification des fichiers sources.

L'actualisation partagée est testée pour compression HTTP, limites de taille,
délais GP/SATCAT, blocages 3xx/4xx, pause après panne, cache corrompu, repli,
publication atomique et protections avant écriture. Une protection globale
dans `tests/conftest.py` bloque les connexions réelles au niveau socket : elle
couvre aussi les clients HTTP qui ne passent pas par `urlopen`.

Ruff, liens et structure réussis. Wheel et sdist contiennent moteur, données,
notices, tests et illustration. La dépendance SGP4 2.25 a été installée depuis
une wheel locale dans l'environnement isolé, sans modification des dépendances
existantes. La version installée a exécuté, hors du dépôt, le rapport satellitaire
TXT/PDF et les dix sélections avec `--offline --update-catalogs force`.
Le contrôle des dépendances est réussi; aucun cache n'est créé hors ligne.
Les deux pages du PDF d'exemple et le schéma SVG ont été rendus et inspectés.

Les réponses publiques CelesTrak ont été récupérées dans `local/` et leurs
empreintes sont documentées. Aucun extrait réel UNOOSA n'a été téléchargé ni
redistribué : l'index a refusé l'accès automatisé. Aucun accès au disque Seestar
réel ni publication GitHub n'a été nécessaire.

## Comètes MPC/CBAT et actualisations au démarrage

Sur Windows, Python 3.13.6 / Astropy 7.2 / ReportLab 4.4 : **202 tests réussis,
un ignoré**, 26 avertissements (tables IERS prédictives et conversions de dates
historiques volontairement présentes dans les éléments cométaires). Le test
ignoré exige la création de liens symboliques Windows. Les 55 tests des mises
à jour et options de démarrage passent aussi après la revue du signalement
des générations corrompues.

Les coniques sont vérifiées par équation de Barker, hyperbole analytique,
équivalence avec le moteur elliptique et continuité autour de e=1. Quatre
positions JPL Horizons indépendantes pour 67P et C/2023 A3 sont figées avec
paramètres et empreintes : écarts inférieurs à 10″. La photométrie MPC/JPL
n'est pas forcée à concorder lorsque les paramètres sources diffèrent.

Les tests CBAT sont synthétiques et contrôlent date/fuseau, attribution,
bande, observations futures, doublons, fragments et séparation de la prévision.
Aucune mesure CBAT réelle n'a été récupérée : les pages publiques ont échoué
en TLS/passerelle. Le fichier MPC public a été récupéré localement et son
empreinte est documentée dans COMET_SOURCE.md.

Les huit catalogues évolutifs sont couverts par le registre de mise à jour,
avec réseau simulé : modes never/if-stale/force, âges par catalogue/fournisseur,
configuration et priorité des options, délais invalides, pannes, tailles limites,
générations tronquées/corrompues, intégrité, publication atomique, repli, dates de
provenance et isolation des caches mémoire. Les générateurs réels sont exercés
sur sources synthétiques; les protections Seestar refusent le cache avant écriture.
`--offline --update-catalogs force` est testé sur les huit catalogues sans connexion.

Un essai supplémentaire reconstruit le cache cométaire avec la copie MPC déjà
récupérée, sans réseau, puis produit un rapport de trois comètes et le relit hors
ligne. Les deux pages PDF et les deux schémas SVG du tutoriel sont rendus et
vérifiés visuellement. Ruff, liens/versions et contenu wheel/sdist réussis.
Les essais ne prouvent pas la disponibilité future de chaque service réseau.
Le disque Seestar réel et GitHub n'ont reçu aucune modification de ce lot.

La wheel finale a été installée dans un environnement distinct (Astropy 8,
ReportLab 4.5) et exécutée hors du dossier source : huit catalogues sélectionnés
avec mise à jour forcée mais mode hors ligne prioritaire, puis un rapport de
trois comètes avec exports TXT/PDF. Aucun cache n'a été créé en mode hors ligne;
l'extraction du PDF confirme la magnitude totale et l'état des actualisations.

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
