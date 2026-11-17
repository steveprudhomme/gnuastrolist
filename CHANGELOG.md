# Journal des changements

Ce projet suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le
[versionnage sémantique](https://semver.org/lang/fr/).

## [Non publié]

### Ajouté — ECC-D, livraison reproductible

- NumPy déclaré directement; quatre verrous Windows/Linux Python 3.10/3.13
  avec versions et empreintes, outil de reconstruction uv épinglé.
- Environnements locaux sans paquets système, contrôles de dépendances et
  inventaire de livraison avec licences déclarées et empreintes, sans faux SBOM.
- Guide et tutoriel illustré; versions et limites des essais consignées.

### Corrigé — ECC-C, précontrôle des paramètres

- Validation partagée des nombres finis, du site terrestre, du champ, des
  magnitudes, des pas et des réglages d'actualisation avant les opérations à effets.
- Refus contrôlé de NaN/infini, pas infime ou trop grand, booléens JSON utilisés
  comme âges et chemins de cache vides, sans modifier les réglages IERS.
- Comptage exact des instants en UTC avant allocation, bornes incluses, limité
  à 2 000 pour les objets fixes/petits corps et 20 000 pour les satellites;
  correction de la borne exacte de 2 000 instants précédemment trop restrictive.
- Contrôles réutilisés par les API, même sans objet; modèles, calculs et
  protections ECC-A/ECC-B préservés. Guide et tutoriel illustré dès 10 ans.
- Plan ECC-C publié avant code sur une branche dépendante d'ECC-B encore ouvert.

### Corrigé — ECC-B, météo partielle et calcul de rosée

- Calcul de rosée sur les trios température/point de rosée/humidité du même
  instant; valeurs manquantes conservées comme inconnues, sans décalage des listes.
- Validation des réponses Open-Meteo/7Timer : structures, chronologies, unités,
  nombres finis et domaines, tailles et longueurs de séries, sans masquer les
  erreurs de programmation inattendues.
- Seeing nul et erreurs de fournisseur traités sans interrompre la liste
  astronomique; conservation des variables et périodes valides, même sans
  nuages ni seeing, et avertissements partagés par terminal/TXT/PDF.
- Périodes de repli annoncées lorsque les horaires solaires manquent; décalages
  UTC respectés et heures civiles ambiguës/inexistantes refusées.
- Réponses bornées à 2 Mio, séries à 1 000 échantillons, JSON strict et absence
  de décompression implicite. Tutoriel illustré et tests entièrement synthétiques.
- Plan ECC-B commité et publié avant les nouveaux tests et le correctif.

### Corrigé — ECC-A, entrées et exports protégés

- Refus des collisions entre les sept fichiers d'entrée et les sorties TXT/PDF,
  des sorties identiques, des liens/jonctions et des destinations dans les
  ressources, le cache ou les archives Seestar protégées, avant traitement.
- Rapports existants conservés par défaut; `--overwrite` autorise explicitement
  leur remplacement sans contourner les autres protections.
- TXT et PDF publiés atomiquement par fichier, avec nouvelle validation avant
  publication, refus des créations concurrentes sans remplacement autorisé et
  nettoyage des temporaires en cas d'erreur. Les exports restent indépendants.
- Tests de régression hors réseau, guide des exports et tutoriel illustré dès
  10 ans. Le plan ECC-A a été commité et publié avant les tests nouveaux et le code.

### Planifié — améliorations approuvées avec ECC

- Lots ECC-A à ECC-I inscrits au roadmap après approbation du propriétaire,
  avec priorités, sous-étapes et critères de validation avant implémentation.
- Consigne persistante : annoncer explicitement l'usage d'ECC et le premier
  lot incomplet lorsqu'une prochaine étape est demandée.
- Guide de développement ECC et explication illustrée dans le tutoriel;
  aucun correctif applicatif ni changement GitHub dans ce lot de planification.

### Corrigé — compatibilité Python 3.10

- Validation des époques GP indépendante des restrictions de `datetime` sur
  les fractions de seconde; Astropy reçoit toujours la chaîne complète.

### Ajouté — satellites artificiels et débris

- Sélections `satellites` et `debris`, éléments GP/OMM, propagation SGP4 TEME
  et géométrie topocentrique; pas en secondes, borne d'époque et filtre optique
  simultané facultatif, sans magnitude ou visibilité garantie inventée.
- Identités COSPAR et SATCAT/NORAD jusqu'à neuf chiffres; copie partielle de
  737 jeux GP et 1 873 fiches SATCAT, avec types PAY/R/B/DEB et provenance.
- Imports locaux GP/SATCAT et extraits UNOOSA transcrits dans un CSV documenté;
  statut administratif inconnu sans donnée, sans téléchargement de l'index refusé.
- Rapports écran/TXT/PDF et identités Seestar explicites en lecture seule.
- Actualisations CelesTrak partagées entre sélections : CSV/gzip, délais GP/SATCAT,
  arrêt sur toute réponse non 200, pause/blocage persistants et cache atomique.
- Cas de référence Vallado, tests de métadonnées/rapports/pannes, protection
  réseau globale des tests, MD et tutoriel illustré accessibles dès 10 ans.

### Ajouté — comètes et mises à jour configurables

- Sélection `comets`, copie MPC locale (958 entrées cométaires sur 973 lignes),
  import `--comets-file`, coniques elliptiques/paraboliques/hyperboliques et
  magnitude totale estimée distincte de V; exclusions d'époque annoncées.
- Import `--cbat-file` d'observations datées transcrites dans un CSV documenté,
  sans substitution à la prévision; aucune observation CBAT réelle téléchargée
  ni connexion automatique CBAT annoncée, le site étant inaccessible pendant ce lot.
- Sélections mixtes, rapports TXT/PDF, identifiants Seestar complets et fragments
  distincts; moteur de géométrie partagé avec les astéroïdes.
- Actualisations au démarrage configurables pour GCVS, OpenNGC/SIMBAD, HYG,
  JPL et MPC : modes never/if-stale/force, délais globaux/par source, cache local
  validé atomiquement et fichier JSON facultatif; priorité absolue de `--offline`.
- Générateurs réutilisables dans le paquet installé, tests de pannes et de lecture
  seule, comparaisons JPL figées et tutoriel illustré accessible à 10 ans.

### Ajouté — astéroïdes

- Catalogue orbital JPL local des 1 000 premiers astéroïdes numérotés;
  `--objects asteroids`, sélection multiple et remplacement par `--asteroids-file`.
- Positions topocentriques par échantillon, propagation à deux corps et temps de
  lumière; magnitude H-G estimée, heure de référence et filtre champ/V simultané.
- Estimations distinguées dans les rapports écran/TXT/PDF, hypothèses documentées,
  refus au-delà de ±365 jours de l'époque; pas de dates saisonnières fixes appliquées.
- Identifiants Seestar `MPC` distincts de Messier/Caldwell, toujours en lecture seule.
- Comparaisons JPL Horizons figées, tests hors réseau, génération reproductible,
  notices et tutoriel illustré accessible à 10 ans.

### Ajouté — Bayer et Flamsteed

- Sélections `bayer` et `flamsteed` issues de HYG 4.1, utilisables seules ou avec
  les autres catalogues, avec regroupement par clé HYG et préservation des composants.
- Génération locale déterministe, notices de provenance/licence et tutoriel illustré.
- Reconnaissance Seestar des variantes explicites et signalement des noms partagés.

### Corrigé — alphabet grec PDF

- Polices DejaVu Sans régulière et grasse incorporées avec leurs notices pour
  préserver les lettres grecques et indices de composants Bayer dans les PDF.

### Corrigé — validation Windows

- Fichiers temporaires des tests CI placés sur le volume du logiciel, pour
  distinguer les copies synthétiques locales d'un disque source externe protégé.
  Les protections Seestar en lecture seule restent inchangées.
- Guide de démarrage illustré accessible dès 10 ans, séparé du journal technique.

### Ajouté — archives Seestar

- Option `--seestar-path DOSSIER`, inventaire des noms et métadonnées en lecture
  seule, correspondances par identifiants et alias connus, sans ouverture d'images.
- Statuts empilé, brutes seules, non trouvé et indéterminé dans les sorties
  terminal/TXT/PDF, avec signalement des lectures incomplètes.
- Protection des destinations d'export, des liens et des jonctions; tests sur
  archives synthétiques et tutoriel illustré, sans données personnelles publiées.

### Ajouté — sélection multiple

- `--objects` accepte plusieurs catalogues et peut être répété; les commandes
  à catalogue unique restent compatibles.
- Regroupement par désignation explicite avec priorité Messier/Caldwell/NGC,
  conservation de la provenance de la fiche et affichage des alias en TXT/PDF.
- Filtres cohérents par catalogue, sans confondre maxima GCVS et ciel profond.
- Tests de recouvrement, filtres et exports, tutoriel illustré et décision de conception.

### Ajouté — NGC

- Catalogue NGC local avec 8 098 entrées OpenNGC : `--objects ngc`, rapports
  terminal/TXT/PDF, provenance et reconstruction déterministe sans réseau.
- Conservation des composants identifiés distinctement et des magnitudes V
  absentes; exclusion des doublons, entrées inexistantes et entrées IC.
- Tests du générateur, identifications de référence et exports, contrôle des
  distributions et tutoriel illustré pour le périmètre NGC.

### Corrigé

- Configuration IERS temporaire et explicite du test de tri Caldwell pour le
  rendre indépendant de l'ordre d'exécution, notamment sous Python 3.10.

### Ajouté

- Tutoriel illustré par des schémas SVG versionnés, inclus dans l'archive source.
- Procédure de finalisation exclusivement locale avec commit de planification.

- Catalogue Caldwell complet (109 objets) avec l'option `--objects caldwell`,
  données locales OpenNGC, complément V SIMBAD vérifié et notice de provenance.
- Générateur reproductible et tests du catalogue, des filtres et des exports.
- Cadre de contribution : AGENTS, DCO, gouvernance, confidentialité, sécurité,
  notices de licences, installation, architecture, tutoriel et préparation des versions.
- Modèles GitHub, CI Windows/Linux, mises à jour Dependabot et contrôles de
  structure et de contenu des distributions.

### Modifié

- Sortie terminal UTF-8 sous Windows, y compris lorsqu'elle est redirigée.
- Modèle commun du ciel profond, avec alias MessierObject compatible.
- Les magnitudes V absentes sont explicites : conservées sans filtre, exclues
  avec une limite numérique et triées après les magnitudes connues.

## [0.11.0] - 2026-08-03

### Ajouté

- Option `--output-pdf FICHIER` produisant un rapport au format lettre
  8,5 x 11 pouces.
- Mise en page PDF structurée avec renseignements généraux, panneaux météo,
  résumé lunaire, fiches d'objets, notes méthodologiques et pagination.
- Polices Unicode intégrées à ReportLab afin de préserver les accents et les
  symboles astronomiques sur toutes les plateformes.
- Écriture atomique du PDF afin de ne pas laisser un rapport incomplet lorsque
  la génération échoue.
- Test du contenu textuel et des dimensions physiques de la page PDF.

### Modifié

- Ajout de ReportLab aux dépendances d'exécution et de pypdf aux dépendances de
  développement.
- La feuille de route indique maintenant que l'export PDF est terminé.

## [0.10.0] - 2026-08-03

### Ajouté

- Option `--output-txt FICHIER` enregistrant le rapport complet de la soirée
  d'observation dans un fichier texte UTF-8.
- Test confirmant que le fichier exporté est identique au rapport affiché dans
  le terminal et qu'il conserve correctement les caractères français.

### Modifié

- La feuille de route indique maintenant que l'export TXT est terminé.

## [0.9.0] - 2026-08-03

### Ajouté

- Deux résumés météo au début du rapport : les trois heures suivant le coucher
  du Soleil et les trois heures précédant le lever suivant.
- Couverture nuageuse, température, humidité, vent, risque de précipitation et
  estimation du risque de rosée à partir des prévisions Open-Meteo.
- Indices normalisés de qualité du seeing, de la transparence et de la
  stabilité atmosphérique à partir de 7Timer! ASTRO.
- Tolérance aux pannes partielles des fournisseurs : les données encore
  disponibles sont conservées et accompagnées d'un avertissement.
- Tests déterministes des périodes, agrégations, conversions d'indices et du
  fonctionnement hors ligne.

### Modifié

- L'option `--offline` désactive aussi les requêtes météo, sans interrompre le
  rapport.

### Documenté

- Sources, périodes d'agrégation, convention des indices de qualité, méthode
  d'estimation de la rosée et limites des prévisions.

## [0.8.0] - 2026-08-03

### Ajouté

- Illumination quotidienne à midi local de la date de soirée, affichée en plus
  de l'illumination calculée au début de l'observation.
- Tests de comparaison des levers et couchers lunaires avec les éphémérides
  2026 du Griffith Observatory préparées à partir des données de l'US Naval
  Observatory.
- Test confirmant la variation du demi-diamètre apparent avec la distance de la
  Lune.

### Modifié

- Calcul du lever et du coucher à partir du bord supérieur apparent du disque
  lunaire, avec une réfraction horizontale standard de 34 minutes d'arc.
- Prise en compte du demi-diamètre variable à partir d'un rayon lunaire de
  référence de 1 737,4 km et de la distance topocentrique instantanée.
- Affichage explicite de la date et de l'heure de référence de chaque valeur
  d'illumination.

### Documenté

- Convention de l'Astronomical Almanac, méthode de calcul, références et limites
  liées aux conditions atmosphériques et à l'horizon local.

## [0.7.0] - 2026-08-03

### Ajouté

- Résumé de la Lune placé avant la liste d'observation, avec phase en français,
  illumination, lever et coucher dans le fuseau horaire demandé.
- Gestion explicite des dates locales sans lever ou sans coucher, y compris les
  cas où la Lune demeure au-dessus ou au-dessous de l'horizon toute la journée.
- Tests des huit phases lunaires et d'un calcul complet pour Laval.

### Documenté

- Instant de référence de la phase et de l'illumination, méthode géométrique de
  calcul des passages à l'horizon et limites liées à la réfraction et au relief.

## [0.6.0] - 2026-08-03

### Ajouté

- Colonne **Meilleure visibilité saisonnière**, calculée à partir de la date où
  la culmination supérieure de l'objet est la plus proche de minuit civil
  local.
- Tests couvrant un objet éloigné de l'écliptique dont les deux dates
  saisonnières diffèrent de plusieurs semaines.

### Modifié

- Renommage de l'ancienne colonne **Opposition** en **Séparation solaire
  maximale**, sans fusion avec la meilleure période d'observation.
- Réservation du terme **Opposition** aux corps du Système solaire pour lesquels
  cette configuration est physiquement applicable.
- Documentation des définitions, méthodes de calcul et limites des deux dates.

## [0.5.0] - 2026-08-03

### Ajouté

- Cache local reproductible des 110 objets Messier obtenu par une seule requête
  TAP vers SIMBAD.
- Priorité aux dimensions et magnitudes V valides de SIMBAD, avec repli
  automatique vers OpenNGC pour chaque valeur manquante.
- Provenance indépendante des tailles et magnitudes : catalogue, bibcode ou
  référence et date de récupération.
- Option `--details` affichant la provenance complète de chaque valeur.
- Tests de comparaison explicites pour M39, M15 et M52.

### Modifié

- Affichage de la source directement à côté des tailles et magnitudes dans le
  tableau principal.

## [0.4.0] - 2026-08-03

### Ajouté

- Colonnes de taille apparente, magnitude apparente, constellation et date
  annuelle d'opposition dans le tableau des résultats.
- Heures estimées de montée au-dessus et de descente sous l'élévation minimale
  choisie, dans le fuseau horaire de l'observation.
- Dimensions angulaires et constellations OpenNGC dans le catalogue Messier
  embarqué.

### Corrigé

- Le mode `--offline` accepte maintenant les données prédictives IERS
  embarquées âgées de plus de 30 jours au lieu d'interrompre le calcul.

## [0.3.0] - 2026-07-17

### Ajouté

- Catalogue embarqué des 110 objets Messier avec coordonnées ICRS/J2000,
  type et magnitude apparente V provenant d'OpenNGC.
- Sélection du catalogue avec `--objects messier`; `messier_objects` est aussi
  accepté comme alias.
- Script reproductible de génération, provenance, attribution `CC BY-SA 4.0`
  et convention explicite M102 = NGC 5866.

### Modifié

- Adaptation du moteur de visibilité, du filtre photométrique et du rapport aux
  étoiles variables comme aux objets Messier.
- Absence de limite de magnitude par défaut pour Messier; la valeur par défaut
  de 8 est conservée pour les étoiles variables.

## [0.2.0] - 2026-07-17

### Modifié

- Remplacement de la largeur horizontale unique par deux limites azimutales
  obligatoires : `--az-min` et `--az-max`.
- Calcul automatique du centre horizontal entre les limites choisies, y compris
  lorsque le champ traverse le nord.
- Remplacement de la hauteur verticale par une élévation minimale; le champ
  s'étend automatiquement jusqu'à 90° et son centre est calculé.
- Conservation de `--fov-v` comme alias temporaire de `--min-altitude`.
- Conservation de `--alt-center` comme remplacement vertical avancé facultatif.
- Affichage des limites, des dimensions et du centre calculé dans le rapport.

## [0.1.0] - 2026-07-17

### Ajouté

- CLI installable `gnu-astrolist` et exécution comme module Python.
- Analyse des dates, plages traversant minuit et fuseaux IANA.
- Catalogue embarqué de 21 212 étoiles variables en bande V provenant du GCVS.
- Transformation vectorisée ICRS vers Alt/Az avec Astropy.
- Champ de visée centré, sélection pendant la plage et tri par magnitude.
- Validation des entrées, mode hors ligne, limite d'affichage et tests.


### ECC-E — Contrôles de qualité

- Couverture mesurée et planchers globaux/chemins critiques; typage strict initial
  de la validation et règles Ruff supplémentaires.
- Recherche ciblée de secrets sans contenu dans les diagnostics; CI avec verrous,
  actions épinglées et durée bornée; audit de tous les verrous.
- Python 3.11 minimum, avec correctifs Pillow/filelock et verrous audités;
  aucun avis ignoré.


### ECC-G — Service et rapport partagé

- Service de préparation testable, objet `ReportData` et formats publics communs
  aux rendus; CLI/TXT/PDF préservés.
- Contexte IERS temporaire restauré après succès, erreur et appels imbriqués;
  décision ADR 0007, régressions d'appels successifs et guide illustré.


### ECC-H — Références scientifiques et performances

- 38 références topocentriques Skyfield gelées, trois sites et quatre TLE publics;
  générateur, versions, empreintes, licences et tolérances documentés.
- Vérification des franchissements d'horizon; mesures temps/mémoire des
  catalogues, satellites, rapports et 10 000 fichiers Seestar synthétiques.
- SGP4 demeure commun aux deux chaînes; aucune observation réelle revendiquée.


### ECC-I — Documentation et pratiques open source

- Confidentialité des fournisseurs et caches, User-Agent issu de la version,
  19 avis SPDX attribués à l'auteur vérifié et notices des références conservées.
- Anciens rapports retirés du suivi courant, conservés sur le poste et dans
  l'historique; exemples synthétiques et audit ciblé sans divulguer de contenu.
- Checklist des dix sélections et relevé GitHub en lecture seule : `main` non
  protégée et signalement privé désactivé, sans changement de réglage.


### ECC-F — Concurrence et rétention des caches

- Verrou OS réentrant sur toute la transaction fournisseur, libéré après arrêt;
  validation avant création, modes never/offline sans écriture de verrou.
- Commande distincte `gnu-astrolist-cache`, simulation par défaut, retrait explicite,
  conservation des générations réellement reconstructibles et état CelesTrak.
- Tests concurrents, interruption et refus de liens, chemins inconnus et archives
  sources; ADR 0008 et tutoriel illustré, aucune purge automatique.

Revue ECC-G : verrou de contexte commun, précontrôle strict de la limite/âge GP
du service direct et erreur CLI lisible en cas de délai du cache dépassé.

Revue finale ECC-H/D : sorties des outils scientifiques et du manifeste locales,
atomiques et protégées; contexte IERS corrigé pour le benchmark Python 3.10.


### ECC-E.6 — Python 3.11 minimum (changement de compatibilité)

- Après accord du propriétaire, minimum Python relevé de 3.10 à 3.11 et matrice
  Windows/Linux 3.11/3.13; retrait des verrous 3.10 vulnérables.
- Versions minimales corrigées Pillow 13 et filelock 4.2.1; quatre verrous
  régénérés avec empreintes. Aucun avis de vulnérabilité ignoré.

Revue croisée ECC-F/G : ordre commun contexte → cache pour les actualisations
directes et la rétention; deux régressions concurrentes supplémentaires.

Clôture ECC-D à ECC-I : 716 tests locaux réussis sur Python 3.11/3.13,
couverture 90,34 %, quatre audits sans avis connu et cinq contrôles GitHub
verts sur `a3804fe`. PR nº 12 proposée à la revue; aucune fusion effectuée.


### Intégration des PR nº 10, nº 11 et nº 12

- Fusions autorisées dans cet ordre, avec conservation de l'historique;
  les PR dépendantes sont replacées sur main et actualisées dans des copies locales.
- Cinq contrôles vérifiés avant chaque fusion; contrôle final de main.
- Documentation et tutoriel réconciliés; aucune modification du code, des
  réglages GitHub ou des archives Seestar réelles pendant cette intégration.
