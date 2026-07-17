# GNU Astrolist

GNU Astrolist est un prototype libre en ligne de commande qui prépare une soirée
d'observation d'étoiles variables. Il calcule leur hauteur au début et à la fin
d'une plage horaire, retient celles qui traversent le champ de visée et les trie
par magnitude maximale en bande V.

Le prototype est déjà fonctionnel : il contient 21 212 entrées visuelles du
General Catalogue of Variable Stars (GCVS), calcule les coordonnées Alt/Az avec
Astropy et fonctionne hors ligne grâce au catalogue embarqué.

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

## Exemple pour Laval

```bash
gnu-astrolist \
  --date 2026-08-15 \
  --time-range 21:00-02:00 \
  --timezone America/Toronto \
  --lat 45.57 \
  --lon -73.68 \
  --fov-h 180 \
  --fov-v 45 \
  --az-center 180 \
  --alt-center 45 \
  --objects variable_stars \
  --max-magnitude 8 \
  --limit 50
```

La fin `02:00`, antérieure au début `21:00`, est automatiquement placée au
lendemain. Le fuseau IANA est indispensable pour convertir correctement l'heure
civile, y compris lors des changements d'heure.

## Sens du champ de vision

Les deux dimensions demandées dans le cahier des charges ne suffisent pas à
indiquer où pointe l'instrument. GNU Astrolist ajoute donc deux paramètres :

- `--az-center` : direction horizontale, mesurée du nord vers l'est;
- `--alt-center` : hauteur du centre au-dessus de l'horizon.

`--fov-h` et `--fov-v` sont les largeurs autour de ce centre. Par défaut, le
centre pointe plein sud (`180°`) à `45°` de hauteur. Un objet est retenu s'il se
trouve dans ce rectangle Alt/Az à au moins un des instants échantillonnés. Le pas
est réglable avec `--sample-minutes`.

## Principales options

```text
--date AAAA-MM-JJ             Date locale de début
--time-range HH:MM-HH:MM     Plage horaire locale
--timezone ZONE              Fuseau IANA (défaut : UTC)
--lat / --lon                Coordonnées géographiques en degrés
--elevation-m M              Altitude du site
--fov-h / --fov-v            Dimensions du champ en degrés
--az-center / --alt-center   Centre de visée Alt/Az
--max-magnitude MAG          Limite au maximum d'éclat (défaut : 8)
--all-magnitudes             Utilise les 21 212 entrées visuelles
--sample-minutes MIN         Pas de recherche (défaut : 10)
--limit N                    Tronque uniquement l'affichage après le tri
--offline                    Empêche Astropy de mettre à jour les données IERS
```

La commande `gnu-astrolist --help` donne la liste à jour.

Le moteur traite le catalogue par blocs pour maîtriser la mémoire et refuse une
configuration qui dépasserait 2 000 instants d'échantillonnage.

## Sur quoi repose l'architecture?

L'architecture sépare volontairement cinq responsabilités : analyse des
arguments, gestion du temps civil, chargement du catalogue, calcul astronomique
et rendu. Cette séparation rend chaque partie testable et permettra d'ajouter
d'autres catalogues ou formats de sortie sans réécrire le moteur.

Les positions partent des coordonnées ICRS/J2000 du GCVS. Astropy réalise la
[transformation vers le repère horizontal `AltAz`](https://docs.astropy.org/en/stable/coordinates/index.html)
pour un lieu et un instant précis. Le calcul est vectorisé : toutes les étoiles
présélectionnées sont transformées pour tous les instants d'échantillonnage en
une seule opération.

Le paquet suit une structure `src/`, un fichier `pyproject.toml` et un point
d'entrée `console_scripts`, conformément au guide de la
[Python Packaging Authority](https://packaging.python.org/en/latest/guides/creating-command-line-tools/).

## Limites connues du prototype

- La magnitude affichée est le **maximum d'éclat historique publié** par le
  GCVS. Ce n'est pas la magnitude prédite pour la date choisie.
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
restent attribuées à leurs auteurs et au service VizieR; elles ne sont pas
relicenciées par la GPL du logiciel. Consultez
[`src/gnu_astrolist/data/CATALOG_SOURCE.md`](src/gnu_astrolist/data/CATALOG_SOURCE.md).

## Contribuer

Les contributions sont bienvenues. Consultez [CONTRIBUTING.md](CONTRIBUTING.md),
[ROADMAP.md](ROADMAP.md) et [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
