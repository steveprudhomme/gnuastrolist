# Journal des changements

Ce projet suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le
[versionnage sémantique](https://semver.org/lang/fr/).

## [Non publié]

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
