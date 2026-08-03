# GNU Astrolist

GNU Astrolist est un prototype libre en ligne de commande qui prépare une soirée
d'observation astronomique. Il calcule la hauteur des objets au début et à la
fin d'une plage horaire, retient ceux qui traversent le champ de visée et les
trie par magnitude en bande V.

Le prototype est déjà fonctionnel : il contient 21 212 entrées visuelles du
General Catalogue of Variable Stars (GCVS) ainsi que les 110 objets Messier. Il
calcule les coordonnées Alt/Az avec Astropy et fonctionne hors ligne grâce aux
catalogues embarqués.

## Installation

Python 3.10 ou une version plus récente est requis.

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

### Linux ou macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

L'installation crée la commande `gnu-astrolist`. Il est également possible
d'utiliser `python -m gnu_astrolist`.

## Exemples pour Laval

### Étoiles variables

```bash
gnu-astrolist \
  --date 2026-08-15 \
  --time-range 21:00-02:00 \
  --timezone America/Toronto \
  --lat 45.57 \
  --lon -73.68 \
  --az-min 15 \
  --az-max 180 \
  --min-altitude 20 \
  --objects variable_stars \
  --max-magnitude 8 \
  --limit 50
```

La fin `02:00`, antérieure au début `21:00`, est automatiquement placée au
lendemain. Le fuseau IANA est indispensable pour convertir correctement l'heure
civile, y compris lors des changements d'heure.

### Objets Messier

```bash
gnu-astrolist \
  --date 2026-08-15 \
  --time-range 21:00-02:00 \
  --timezone America/Toronto \
  --lat 45.57 \
  --lon -73.68 \
  --az-min 15 \
  --az-max 180 \
  --min-altitude 20 \
  --objects messier
```

Les 110 objets Messier sont considérés par défaut. Ajoutez par exemple
`--max-magnitude 8` pour ne retenir que ceux dont la magnitude apparente V est
inférieure ou égale à 8. La convention retenue pour l'objet historiquement
ambigu M102 est NGC 5866.

Les tailles et magnitudes Messier privilégient les valeurs valides de SIMBAD et
utilisent OpenNGC comme repli hors ligne. Le catalogue choisi est indiqué entre
crochets à côté de chaque valeur. Ajoutez `--details` pour afficher également
le bibcode ou la référence et la date de récupération.

## Résumé de la Lune

Avant la liste d'observation, le rapport affiche un résumé lunaire comprenant :

- la phase de la Lune au début de la plage demandée;
- son pourcentage d'illumination à ce même instant;
- l'heure locale de son lever pendant la date civile choisie;
- l'heure locale de son coucher pendant cette date.

Les huit appellations utilisées sont : nouvelle lune, premier croissant,
premier quartier, lune gibbeuse croissante, pleine lune, lune gibbeuse
décroissante, dernier quartier et dernier croissant. La phase et l'illumination
sont calculées avec les éphémérides lunaires et solaires intégrées à Astropy.

Les heures de lever et de coucher correspondent au passage géométrique du
centre de la Lune à un horizon de 0°. Elles ne tiennent pas compte de la
réfraction atmosphérique, du relief ni d'un masque d'horizon local et peuvent
donc différer légèrement des horaires publiés utilisant une autre convention.
Lorsqu'aucun passage ne survient pendant la date locale, le rapport le précise;
il indique également si la Lune demeure levée ou couchée toute la journée.

## Informations du tableau

Le tableau indique désormais, pour chaque objet retenu :

- son type et sa constellation;
- sa taille apparente en minutes d'arc lorsqu'elle est publiée;
- sa magnitude V de référence;
- la date de séparation solaire maximale et, séparément, la date de meilleure
  visibilité saisonnière;
- l'heure où il monte au-dessus de `--min-altitude` et l'heure où il redescend
  sous ce seuil;
- sa hauteur au début et à la fin de la plage demandée.

Les heures de franchissement sont estimées à la minute avec un échantillonnage
de cinq minutes, dans le fuseau fourni par `--timezone`. Si un passage survient
un autre jour que la date de début, le tableau ajoute sa date au format
`MM-JJ`. La valeur `Toujours` désigne un objet qui reste au-dessus du seuil
pendant toute la période de recherche de 60 heures autour du début.

### Dates saisonnières

**Séparation solaire maximale** désigne le jour où la séparation angulaire
géométrique entre l'objet et le Soleil est la plus grande. GNU Astrolist estime
ce jour à partir d'un échantillon quotidien à 12 h UTC. Cette date est
indépendante du site d'observation et ne constitue pas une opposition physique
pour un objet du ciel profond.

**Meilleure visibilité saisonnière** désigne la date où la culmination
supérieure de l'objet est la plus proche de minuit civil local. Le calcul
compare le temps sidéral local à l'ascension droite de l'objet à chaque minuit
de l'année; il dépend donc de la longitude et du fuseau horaire fournis. Cette
date est une indication saisonnière, pas une prévision complète : elle ne tient
pas encore compte du crépuscule, de la Lune, de la météo, de la réfraction ni
d'un horizon local. L'heure civile et ses changements saisonniers peuvent aussi
décaler le résultat d'environ une journée.

Ces deux dates ne sont jamais fusionnées. Elles peuvent différer de plusieurs
semaines pour un objet éloigné de l'écliptique. Le terme **Opposition** est
réservé aux corps du Système solaire pour lesquels cette configuration est
physiquement applicable; aucun objet Messier ni aucune étoile variable ne
reçoit actuellement une date d'opposition.

## Sens du champ de vision

L'utilisateur choisit les deux limites horizontales du champ, mais n'a pas à
calculer ni à préciser son point central. GNU Astrolist le détermine ainsi :

- largeur horizontale : distance de `--az-min` à `--az-max`, dans le sens du
  nord vers l'est;
- centre horizontal : milieu exact entre ces deux limites;
- centre vertical : `(élévation minimale + 90°) ÷ 2`;
- hauteur verticale du champ : `90° - élévation minimale`.

Le champ vertical commence à `--min-altitude` et se termine au zénith (`90°`).
Ainsi, avec `--az-min 15 --az-max 180 --min-altitude 20`, le centre calculé est
situé à `97,5°` d'azimut et `55°` de hauteur. Le champ horizontal mesure `165°`
et le champ vertical mesure `70°`.

Les limites peuvent traverser le nord : `--az-min 350 --az-max 15` produit un
champ de `25°` centré à `2,5°`. Pour demander tout l'horizon, utilisez
`--az-min 0 --az-max 360`.

Le centre horizontal reste toujours déterminé par les deux limites choisies.
Un utilisateur qui veut réellement déplacer le centre vertical peut employer
l'option avancée `--alt-center`. L'ancien nom `--fov-v` reste accepté comme alias
de `--min-altitude` afin de préserver la compatibilité avec les premières
commandes du prototype.

Un objet est retenu s'il se trouve dans le champ Alt/Az à au moins un des
instants échantillonnés. Le pas est réglable avec `--sample-minutes`.

## Principales options

```text
--date AAAA-MM-JJ             Date locale de début
--time-range HH:MM-HH:MM     Plage horaire locale
--timezone ZONE              Fuseau IANA (défaut : UTC)
--lat / --lon                Coordonnées géographiques en degrés
--elevation-m M              Altitude du site
--az-min DEG                 Limite azimutale de départ
--az-max DEG                 Limite azimutale de fin
--min-altitude DEG           Élévation minimale; --fov-v est un alias
--alt-center DEG             Remplacement avancé facultatif du centre vertical
--objects CATALOGUE          variable_stars ou messier
--max-magnitude MAG          Limite V; défaut 8 pour les variables, aucune pour Messier
--all-magnitudes             Désactive la limite pour le catalogue choisi
--sample-minutes MIN         Pas de recherche (défaut : 10)
--limit N                    Tronque uniquement l'affichage après le tri
--offline                    Empêche Astropy de mettre à jour les données IERS
--details                    Affiche la provenance complète des tailles et magnitudes
```

La commande `gnu-astrolist --help` donne la liste à jour.

Le moteur traite le catalogue par blocs pour maîtriser la mémoire et refuse une
configuration qui dépasserait 2 000 instants d'échantillonnage.

## Sur quoi repose l'architecture?

L'architecture sépare volontairement cinq responsabilités : analyse des
arguments, gestion du temps civil, chargement des catalogues, calcul astronomique
et rendu. Cette séparation rend chaque partie testable et permettra d'ajouter
d'autres catalogues ou formats de sortie sans réécrire le moteur.

Les positions partent des coordonnées ICRS/J2000 des catalogues. Astropy réalise la
[transformation vers le repère horizontal `AltAz`](https://docs.astropy.org/en/stable/coordinates/index.html)
pour un lieu et un instant précis. Le calcul est vectorisé : toutes les étoiles
présélectionnées sont transformées pour tous les instants d'échantillonnage en
une seule opération.

Le paquet suit une structure `src/`, un fichier `pyproject.toml` et un point
d'entrée `console_scripts`, conformément au guide de la
[Python Packaging Authority](https://packaging.python.org/en/latest/guides/creating-command-line-tools/).

## Limites connues du prototype

- Pour les étoiles variables, la magnitude affichée est le **maximum d'éclat
  historique publié** par le GCVS. Ce n'est pas la magnitude prédite pour la
  date choisie.
- Pour les objets Messier, les dimensions et magnitudes V valides de SIMBAD
  sont prioritaires, puis OpenNGC sert de repli. Certaines dimensions ne sont
  disponibles dans aucune des deux sources. L'identification retenue pour M102
  est NGC 5866.
- Seules les entrées dont la bande principale est `V` sont incluses. Le GCVS
  regroupe sous ce code les mesures visuelles, photovisuelles ou Johnson V.
- La sélection est discrète. Un objet qui traverse très rapidement un petit
  champ entre deux échantillons peut être manqué; réduisez `--sample-minutes`.
- La réfraction atmosphérique, les obstacles, la météo, la Lune, le crépuscule,
  la pollution lumineuse et les limites réelles d'un instrument ne sont pas
  encore modélisés.
- Les étoiles sont traitées comme des positions ICRS fixes. Le catalogue fournit
  des coordonnées J2000; le prototype n'applique pas les mouvements propres.
- Les données GCVS distribuées datent de la version publiée par VizieR. VSX est
  une base vivante plus actuelle, mais son intégration réseau est hors de portée
  de cette première version.

## Tests et qualité

```bash
python -m pip install -e .[dev]
pytest
ruff check .
```

## Données et licences

Le code est distribué sous GNU GPL version 3 ou ultérieure. Les données du GCVS
restent attribuées à leurs auteurs et au service VizieR. Le catalogue Messier
dérivé d'OpenNGC demeure sous `CC BY-SA 4.0`. Ces données ne sont pas
relicenciées par la GPL du logiciel. Le cache SIMBAD reste attribué au CDS et
n'est pas placé sous GPL. Consultez
[`CATALOG_SOURCE.md`](src/gnu_astrolist/data/CATALOG_SOURCE.md) et
[`MESSIER_SOURCE.md`](src/gnu_astrolist/data/MESSIER_SOURCE.md), ainsi que
[`SIMBAD_SOURCE.md`](src/gnu_astrolist/data/SIMBAD_SOURCE.md).

## Contribuer

Les contributions sont bienvenues. Consultez [CONTRIBUTING.md](CONTRIBUTING.md),
[ROADMAP.md](ROADMAP.md) et [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
