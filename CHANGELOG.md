# Journal des changements

Ce projet suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le
[versionnage sémantique](https://semver.org/lang/fr/).

## [Non publié]

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
