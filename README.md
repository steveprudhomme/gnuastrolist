# GNU Astrolist

Pour commencer sans connaître le programme, suivre le
[tutoriel illustré pas à pas](docs/TUTORIEL.md), écrit pour être compris dès 10 ans.

GNU Astrolist est un prototype libre en ligne de commande qui prépare une soirée
d'observation astronomique. Il calcule la hauteur des objets au début et à la
fin d'une plage horaire, retient ceux qui traversent le champ de visée et les
trie par magnitude indiquée : V pour les catalogues stellaires et du ciel
profond, magnitude totale estimée pour les comètes.

Le prototype est déjà fonctionnel : il contient 21 212 entrées visuelles du
General Catalogue of Variable Stars (GCVS), les 110 objets Messier et les
109 objets Caldwell, 8 098 entrées NGC et les sélections stellaires Bayer/Flamsteed. Il
calcule les coordonnées Alt/Az avec Astropy et fonctionne hors ligne grâce aux
catalogues embarqués. Il propose aussi les **1 000 premiers astéroïdes numérotés**,
avec positions recalculées et magnitudes estimées pendant la soirée.
Voir [le guide astéroïdes](docs/ASTEROIDS.md) pour les limites du modèle et
l'actualisation des éléments orbitaux avec un fichier local.

```powershell
gnu-astrolist --date 2026-11-17 --time-range 21:00-22:00 --timezone America/Toronto --lat 45.57 --lon -73.68 --az-min 0 --az-max 360 --min-altitude 10 --objects asteroids messier --max-magnitude 10 --offline --limit 20
```

`asteroids` peut être utilisé seul. `--asteroids-file local/orbites-sbdb.json`
remplace la copie embarquée par une réponse SBDB locale plus récente ou plus
étendue. La magnitude précédée de `≈` est une estimation H-G, associée à un
instant dans le champ. Le modèle à deux corps accepte les dates à ±365 jours
des éléments : cette borne ne garantit pas la précision du pointage.

Les **comètes MPC** sont disponibles avec `--objects comets`, seules ou mélangées
aux autres catalogues. La copie embarquée contient 958 entrées cométaires;
les orbites sans époque exploitable sont écartées avec un effectif annoncé.
`--comets-file` accepte un fichier orbital MPC local; `--cbat-file` ajoute des
observations CBAT/ICQ datées dans un CSV documenté, séparées des prévisions.
Aucune mesure CBAT réelle n'est fournie avec le paquet : voir le
[guide des comètes](docs/COMETS.md).

Les **satellites artificiels et débris** sont disponibles avec
`--objects satellites debris`. COSPAR et SATCAT/NORAD relient la description
aux éléments orbitaux GP propagés par SGP4. La copie partielle contient
737 jeux GP et 1 873 fiches SATCAT. Le registre administratif UNOOSA peut être
enrichi par un extrait local; aucune fiche réelle ONU n'est livrée.

```powershell
gnu-astrolist --date 2026-11-17 --time-range 21:00-21:20 --timezone America/Toronto --lat 45.57 --lon -73.68 --az-min 0 --az-max 360 --min-altitude 10 --objects satellites debris --satellite-step-seconds 5 --offline --limit 5
```

La magnitude reste inconnue : enlever un seuil `--max-magnitude` pour conserver
ces objets. `--satellite-optical-only` exige au même instant champ, éclairage
solaire et ciel suffisamment sombre; il ne garantit pas la détection.
Voir [le guide des satellites, SATCAT et UNOOSA](docs/SATELLITES.md).

Les rapports écran, TXT et PDF affichent l'**azimut** et la **hauteur** du satellite
à l'« Instant position (local) », le maximum échantillonné retenu après les filtres.
Ces coordonnées servent à repérer la direction à cette heure, sans commander
le suivi du télescope. Voir [comment les lire](docs/SATELLITES.md#coordonnées-à-linstant-retenu).

### Garder les catalogues à jour au démarrage

Tous les catalogues évolutifs ont une politique configurable. Ajouter à sa
commande, par exemple :

```text
--update-catalogs if-stale --catalog-age comets=24 --catalog-age asteroids=48 --catalog-age openngc=720
```

Cela contrôle uniquement les catalogues sélectionnés, au lancement. Les délais
sont en heures; un [fichier de configuration local](docs/CATALOG_UPDATES.md)
peut mémoriser les réglages. Le mode par défaut `never` ne télécharge rien;
`--offline` interdit toujours les connexions, même avec `force`.
Le cache reste sur l'ordinateur et garde la dernière copie validée en cas de
panne. Les observations CBAT restent importées localement tant qu'aucun accès
automatique fiable n'est validé.

## Installation

Python 3.11 ou une version plus récente est requis.

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

## Désignations de Bayer et Flamsteed

Utilisez `--objects bayer`, `--objects flamsteed` ou les deux ensemble :

```powershell
gnu-astrolist --date 2026-11-17 --time-range 21:00-22:00 --timezone America/Toronto --lat 45.57 --lon -73.68 --az-min 0 --az-max 360 --min-altitude 20 --objects bayer flamsteed --offline --limit 20
```

Les extraits HYG embarqués contiennent 1 537 fiches Bayer et 2 737 Flamsteed.
Ensemble, ils donnent 3 321 fiches HYG distinctes, dont certaines à plusieurs noms :
`α Lyr / 3 Lyr` pour Véga. Les composants qui partagent un nom ne sont pas fusionnés.
Les deux choix fonctionnent aussi avec `messier`, `caldwell`, `ngc` et `variable_stars`.

Aucune limite de magnitude n'est appliquée à ces sélections par défaut.
`--max-magnitude` et `--all-magnitudes`, les rapports TXT/PDF et l'option Seestar
sont pris en charge. Les lettres grecques sont conservées dans les PDF grâce aux
polices libres incorporées. Voir la [notice des données](src/gnu_astrolist/data/STELLAR_SOURCE.md)
et le [tutoriel illustré](docs/TUTORIEL.md). Ces extraits ne couvrent pas toutes
les désignations historiques; les coordonnées restent fixes à leur référence J2000.

## Vérifier les acquisitions du Seestar S50

Ajoutez `--seestar-path "E:\MyWorks"` pour voir une colonne **Seestar** à
l'écran, dans le TXT et dans les fiches PDF. Le chemin peut varier à chaque usage.

```powershell
gnu-astrolist --date 2026-08-15 --time-range 21:00-02:00 --timezone America/Toronto --lat 45.57 --lon -73.68 --az-min 15 --az-max 180 --min-altitude 20 --objects messier caldwell ngc --offline --max-magnitude 8 --limit 20 --seestar-path "E:\MyWorks"
```

Les statuts distinguent un empilement trouvé, des brutes seules, une absence
d'acquisition reconnue et une vérification incomplète. Le scanner ne lit que les
noms et métadonnées : aucune écriture, aucun cache ni modification des archives.
Les exports dans l'espace source protégé sont refusés. Les rapports doivent être
écrits ailleurs, par exemple dans `local/` sur le disque du projet.

Un dossier vide ne compte pas; « Non trouvé » ne signifie pas « jamais
photographié ». Voir les [règles de reconnaissance Seestar](docs/SEESTAR.md) et
le [tutoriel illustré](docs/TUTORIEL.md) pour les statuts et les limites.

## Utiliser plusieurs catalogues

Fournissez plusieurs noms après `--objects`, ou répétez cette option :

```powershell
gnu-astrolist --date 2026-08-15 --time-range 21:00-02:00 --timezone America/Toronto --lat 45.57 --lon -73.68 --az-min 15 --az-max 180 --min-altitude 20 --objects messier caldwell ngc --offline --max-magnitude 8 --limit 20
```

`--objects messier --objects ngc` est également accepté. Les répétitions et
`messier_objects` n'ajoutent pas de doublons. Les objets du ciel profond de même
désignation explicite sont réunis : `M31 / NGC224` occupe une ligne. La fiche
Messier est prioritaire sur Caldwell, puis NGC, indépendamment de l'ordre demandé;
sa provenance est conservée. Les composants distincts restent séparés.

`variable_stars` peut être ajouté. Par défaut, ses variables gardent la limite
V maximum publié ≤ 8, tandis que le ciel profond reste sans limite.
`--max-magnitude` fixe une limite commune et `--all-magnitudes` les supprime toutes.
Le [tutoriel](docs/TUTORIEL.md) et la [décision de conception](docs/architecture/decisions/0002-selection-multiple.md)
détaillent les alias, les valeurs absentes et les limites du regroupement.

## Nouveau Catalogue Général (NGC)

L'option `--objects ngc` charge **8 098 entrées NGC** issues de la copie OpenNGC
locale, dont les composants identifiés séparément. Les doublons et objets
marqués inexistants sont exclus. IC n'est pas inclus dans cette option.

```powershell
gnu-astrolist --date 2026-08-15 --time-range 21:00-02:00 --timezone America/Toronto --lat 45.57 --lon -73.68 --az-min 15 --az-max 180 --min-altitude 20 --objects ngc --offline --max-magnitude 8 --limit 20
```

Sans `--max-magnitude`, aucune limite n'est appliquée; les 4 592 entrées sans V
restent disponibles et s'affichent « non disponible ». Une limite numérique les
exclut. `--limit` tronque l'affichage après la sélection et le tri, sans réduire
les calculs. Les exports TXT/PDF et `--details` sont pris en charge.
Voir la [notice NGC](src/gnu_astrolist/data/NGC_SOURCE.md) et le
[tutoriel illustré](docs/TUTORIEL.md) pour les conventions et limites.

## Objets Caldwell

Les **109 objets Caldwell** sont disponibles hors ligne avec `--objects caldwell`.
Ils utilisent OpenNGC, avec un complément de magnitude V SIMBAD lorsqu'il est
exploitable. La [notice des données](src/gnu_astrolist/data/CALDWELL_SOURCE.md)
précise les sources, licences, objets composés et limites.

```powershell
gnu-astrolist --date 2026-08-15 --time-range 21:00-02:00 --timezone America/Toronto --lat 45.57 --lon -73.68 --az-min 15 --az-max 180 --min-altitude 20 --objects caldwell --offline
```

Aucune limite de magnitude n'est appliquée par défaut. Les objets sans magnitude
V publiée restent inclus, sont triés après ceux dont la magnitude est connue et
affichent « non disponible ». `--max-magnitude 8` les exclut et retient les V ≤ 8.
Les options `--details`, `--output-txt` et `--output-pdf` fonctionnent également.

## Export du rapport en fichier texte

Ajoutez `--output-txt` et le chemin du fichier voulu pour enregistrer une copie
UTF-8 du rapport complet. Le rapport demeure également affiché dans le terminal.
Le dossier parent doit déjà exister.

Un fichier existant est refusé par défaut. Choisissez un nouveau nom ou ajoutez
`--overwrite` pour remplacer volontairement les rapports. Les entrées, le cache,
les ressources du logiciel et les archives Seestar protégées restent interdits,
même avec cette option. TXT et PDF doivent avoir des chemins distincts. Chaque
rapport est publié atomiquement; les deux exports ne forment pas une transaction
commune. Voir le [guide des exports protégés](docs/EXPORTS.md).

```powershell
gnu-astrolist --date 2026-08-15 --time-range 21:00-02:00 --timezone America/Toronto --lat 45.57 --lon -73.68 --az-min 15 --az-max 180 --min-altitude 20 --objects messier --output-txt soiree-2026-08-15.txt
```

## Export du rapport en PDF

L'option `--output-pdf` produit un document PDF au format lettre nord-américain
de 8,5 x 11 pouces. La mise en page comprend les paramètres d'observation, les
deux résumés météo, le résumé de la Lune, une fiche lisible par objet, les notes
méthodologiques ainsi qu'un pied de page numéroté. Les polices sont incorporées
au document pour conserver les accents et les symboles astronomiques.

```powershell
gnu-astrolist --date 2026-08-15 --time-range 21:00-02:00 --timezone America/Toronto --lat 45.57 --lon -73.68 --az-min 15 --az-max 180 --min-altitude 20 --objects messier --output-pdf soiree-2026-08-15.pdf
```

Le rapport demeure affiché dans le terminal. `--output-txt` et `--output-pdf`
peuvent être employés simultanément. Pour les très longues listes, utilisez
`--limit` afin de contrôler le nombre de fiches incluses dans les deux sorties.
Le dossier parent de chaque fichier doit déjà exister.

## Conditions météo

Au début du rapport, GNU Astrolist affiche deux résumés prévisionnels :

- **Soirée** : les trois premières heures suivant le coucher du Soleil;
- **Avant l'aube** : les trois dernières heures précédant le lever du Soleil
  suivant.

Les valeurs civiles proviennent d'[Open-Meteo](https://open-meteo.com/en/docs).
La couverture nuageuse, la température, l'humidité et le vent sont moyennés sur
chaque période. Le risque de précipitation est le pourcentage maximal prévu
pendant la période. Le risque de rosée est une estimation en quatre niveaux,
fondée sur l'écart minimal entre la température et le point de rosée ainsi que
sur l'humidité maximale : faible au-delà de 4 °C et sous 80 %, modéré à 4 °C ou
80 %, élevé à 2 °C ou 90 %, et très élevé à 1 °C ou 95 %.

Depuis ECC-B, ces comparaisons utilisent uniquement les trios température,
point de rosée et humidité du **même instant**. Les valeurs manquantes ou invalides
sont signalées, jamais décalées vers une autre heure ni remplacées par zéro.
Sans trio complet, le risque reste inconnu. Les autres variables valides et la
liste astronomique restent disponibles lorsqu'une source météo échoue.
Si les horaires solaires manquent, le rapport annonce ses périodes de repli
20–23 h et 3–6 h locales. Voir le [guide météo](docs/METEO.md) et le
[tutoriel illustré](docs/TUTORIEL.md).

Le seeing et la transparence viennent du produit astronomique de
[7Timer! ASTRO](https://www.7timer.info/doc.php?lang=en), dérivé du modèle GFS.
Ses catégories 1 à 8 sont converties en un **indice de qualité** de 100 à 0 % :
une valeur élevée est donc favorable. La stabilité atmosphérique est convertie
de la même façon à partir des catégories de l'indice de soulèvement (*Lifted
Index*). Ces trois pourcentages sont des indices normalisés pour faciliter la
lecture; ils ne sont ni des probabilités ni des mesures faites au site.

La disponibilité dépend de l'horizon de prévision des services, notamment
environ trois jours pour 7Timer! ASTRO. Chaque source peut être indisponible
indépendamment et le rapport affiche alors les valeurs restantes avec un
avertissement. Les prévisions peuvent évoluer entre deux exécutions. L'option
`--offline` désactive tout accès météo et affiche clairement leur
indisponibilité sans empêcher les calculs astronomiques.

## Résumé de la Lune

Avant la liste d'observation, le rapport affiche un résumé lunaire comprenant :

- la phase de la Lune au début de la plage demandée;
- son pourcentage d'illumination à ce même instant;
- son illumination quotidienne à midi local de la date de soirée;
- l'heure locale de son lever pendant la date civile choisie;
- l'heure locale de son coucher pendant cette date.

Les huit appellations utilisées sont : nouvelle lune, premier croissant,
premier quartier, lune gibbeuse croissante, pleine lune, lune gibbeuse
décroissante, dernier quartier et dernier croissant. La phase et l'illumination
sont calculées avec les éphémérides lunaires et solaires intégrées à Astropy.
Chaque pourcentage est accompagné de son instant de référence. La convention
quotidienne à midi local suit celle du service de l'[US Naval
Observatory](https://aa.usno.navy.mil/data/api). GNU Astrolist l'associe à la
date de soirée : si l'observation commence avant midi, le midi de la veille est
utilisé. Une observation commençant le 3 août à 00:00 affiche ainsi également
la valeur quotidienne du 2 août à 12:00.

Les heures de lever et de coucher suivent la convention de l'[Astronomical
Almanac](https://aa.usno.navy.mil/faq/asa_glossary) : le bord supérieur apparent
de la Lune touche l'horizon astronomique. Le calcul additionne à la hauteur
géométrique topocentrique du centre :

- une réfraction horizontale standard fixe de 34 minutes d'arc;
- le demi-diamètre lunaire instantané, calculé avec un rayon de référence de
  1 737,4 km et la distance topocentrique fournie par Astropy.

Le rayon retenu est celui du modèle de référence lunaire de la
[NASA](https://svs.gsfc.nasa.gov/4720). La réfraction est appliquée sous forme de
constante d'almanach plutôt qu'avec le modèle `AltAz` d'Astropy, car la
[documentation d'Astropy](https://docs.astropy.org/en/stable/api/astropy.coordinates.AltAz.html)
précise que son modèle devient imprécis sous environ 5° et potentiellement non
physique près de l'horizon.

Cette convention standard ne tient pas compte de la température, de la
pression et de l'humidité réelles, du relief, de l'abaissement de l'horizon lié
à la hauteur de l'observateur ni d'un masque d'horizon local. Les horaires
peuvent donc encore différer de quelques minutes entre services publiés.
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
- centre vertical : `(élévation minimale + élévation maximale) ÷ 2`;
- hauteur verticale du champ : `élévation maximale - élévation minimale`.

Le champ vertical commence à `--min-altitude` et se termine à `--max-altitude`,
qui vaut **90° par défaut**.
Ainsi, avec `--az-min 15 --az-max 180 --min-altitude 20`, le centre calculé est
situé à `97,5°` d'azimut et `55°` de hauteur. Le champ horizontal mesure `165°`
et le champ vertical mesure `70°`.

Les limites peuvent traverser le nord : `--az-min 350 --az-max 15` produit un
champ de `25°` centré à `2,5°`. Pour demander tout l'horizon, utilisez
`--az-min 0 --az-max 360`.

Le centre horizontal reste toujours déterminé par les deux limites choisies.
Un utilisateur qui veut réellement déplacer le centre vertical peut employer
l'option avancée `--alt-center`, seulement sans `--max-altitude` explicite.
L'ancien nom `--fov-v` reste accepté comme alias
de `--min-altitude` afin de préserver la compatibilité avec les premières
commandes du prototype.

Pour un télescope qui évite le zénith, choisir par exemple une zone de **20° à 80°** :

```powershell
gnu-astrolist --date 2026-11-17 --time-range 21:00-22:00 --lat 45 --lon 0 --az-min 0 --az-max 360 --min-altitude 20 --max-altitude 80 --objects messier --offline --limit 20
```

Le centre est alors 50°, sans déplacer la limite basse de 20°. Les deux bornes
sont incluses et doivent vérifier `0 ≤ minimum ≤ maximum ≤ 90`. Les valeurs
non finies et l'association explicite `--max-altitude`/`--alt-center` sont refusées
avant réseau, cache ou export. Sans nouveau plafond, l'ancien centre avancé
conserve son comportement.

Un objet est retenu s'il se trouve dans le champ Alt/Az à au moins un des
instants échantillonnés. Le pas est réglable avec `--sample-minutes`.
Un objet peut donc dépasser le plafond à d'autres instants, y compris aux
heures de début/fin affichées. Ce filtre ne garantit pas toute la durée d'une
pose et ne pilote pas le télescope. Le pas satellite reste distinct.
Voir le [tutoriel illustré du plafond](docs/TUTORIEL.md#choisir-une-hauteur-maximale).


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
--max-altitude DEG           Élévation maximale (défaut : 90°)
--alt-center DEG             Remplacement avancé facultatif du centre vertical
--objects CATALOGUE [...]    variable_stars, messier, caldwell, ngc, bayer, flamsteed, asteroids, comets
                            satellites, debris
--asteroids-file JSON        Remplace les orbites embarquées par une réponse SBDB locale
--comets-file FICHIER        Remplace les orbites cométaires par un fichier MPC local
--cbat-file CSV              Ajoute des observations datées CBAT/ICQ transcrites localement
--satellite-elements-file F  Éléments GP locaux CSV/JSON, éventuellement gzip
--satcat-file F              Métadonnées SATCAT locales
--unoosa-file CSV            Extraits locaux du registre ONU dans le format documenté
--satellite-step-seconds S   Pas satellitaire en secondes (défaut : 5)
--satellite-max-epoch-hours H Écart maximal à EPOCH (défaut : 168 heures)
--satellite-optical-only     Filtre champ + éclairage + hauteur solaire simultanés
--satellite-max-sun-altitude DEG  Plafond solaire du filtre optique (défaut : -6)
--update-catalogs MODE       never (défaut), if-stale ou force; --offline reste prioritaire
--catalog-age SOURCE=HEURES  Délai par catalogue ou fournisseur; répétable
--catalog-max-age-hours H    Délai commun à tous les catalogues
--catalog-cache-dir DOSSIER  Cache de copies validées sur l'ordinateur
--catalog-config JSON       Configuration locale facultative des mises à jour
--max-magnitude MAG          Seuil V ou total cométaire; défaut 8 pour GCVS, aucun sinon
--all-magnitudes             Désactive la limite pour le catalogue choisi
--sample-minutes MIN         Pas de recherche (défaut : 10)
--limit N                    Tronque uniquement l'affichage après le tri
--offline                    Désactive la météo et les mises à jour réseau IERS
--details                    Affiche la provenance complète des tailles et magnitudes
--output-txt FICHIER         Enregistre le rapport complet en texte UTF-8
--output-pdf FICHIER         Crée un PDF lettre 8,5 x 11 po mis en page
--seestar-path DOSSIER       Vérifie les acquisitions Seestar en lecture seule
```

La commande `gnu-astrolist --help` donne la liste à jour.

Le moteur traite le catalogue par blocs pour maîtriser la mémoire et refuse une
configuration qui dépasserait 2 000 instants d'échantillonnage.

## Sur quoi repose l'architecture?

L'architecture sépare volontairement cinq responsabilités : analyse des
arguments, gestion du temps civil, chargement des catalogues, calcul astronomique
et rendu. Cette séparation rend chaque partie testable et permettra d'ajouter
d'autres catalogues ou formats de sortie sans réécrire le moteur.

Les positions fixes partent des coordonnées ICRS/J2000 des catalogues. Astropy réalise la
[transformation vers le repère horizontal `AltAz`](https://docs.astropy.org/en/stable/coordinates/index.html)
pour un lieu et un instant précis. Le calcul est vectorisé : toutes les étoiles
présélectionnées sont transformées pour tous les instants d'échantillonnage en
une seule opération.

Les astéroïdes utilisent un moteur orbital séparé, décrit dans le
[guide astéroïdes](docs/ASTEROIDS.md), puis rejoignent les mêmes rendus.

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
- La sélection des objets n'applique ni réfraction atmosphérique, ni obstacles,
  crépuscule, pollution lumineuse ou limites réelles d'un instrument. Le résumé
  météo est informatif et ne modifie pas la sélection.
  Le résumé lunaire applique seulement la réfraction standard fixe décrite
  ci-dessus; il ne modélise pas les conditions atmosphériques locales.
- Les étoiles sont traitées comme des positions ICRS fixes. Le catalogue fournit
  des coordonnées J2000; le prototype n'applique pas les mouvements propres.
- Les données GCVS distribuées datent de la version publiée par VizieR. VSX est
  une base vivante plus actuelle, mais son intégration réseau est hors de portée
  de cette première version.

## Tests et qualité

Pour reproduire les versions de développement/livraison, utiliser les
[quatre verrous avec empreintes](requirements/README.md) dans un environnement
sans paquets système. Voir [ECC-D](docs/LIVRAISON_REPRODUCTIBLE.md) pour les
versions testées, la reconstruction et l'inventaire de livraison.

Les réglages sont vérifiés avant les actualisations, la météo et les exports.
NaN/infini, les pas non représentables et les budgets dépassés sont refusés par
une erreur de commande. Les limites sont de 2 000 instants pour les objets
fixes/petits corps et 20 000 pour les satellites; `--limit` ne les réduit pas.
L'altitude du site terrestre doit être comprise entre −1 000 et 10 000 m.
Voir le [guide des paramètres ECC-C](docs/PARAMETRES.md) et le tutoriel illustré.

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
Les prévisions en ligne restent attribuées à Open-Meteo et à 7Timer!; consultez
leurs documentations liées plus haut pour connaître leurs sources et conditions
d'utilisation.

## Contribuer

Les contributions sont bienvenues. Consultez [CONTRIBUTING.md](CONTRIBUTING.md),
[ROADMAP.md](ROADMAP.md) et [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

Les améliorations approuvées après l'audit sont identifiées **ECC-A à ECC-I**
dans le roadmap et se réalisent avec ECC. Ils sont réalisés dans cette branche;
la revue et les fusions restent distinctes. Voir la [méthode ECC](docs/DEVELOPPEMENT_ECC.md).

Le cadre de développement est décrit dans [AGENTS.md](AGENTS.md),
[INSTALL.md](INSTALL.md) et l'[index documentaire](docs/README.md).
Consultez aussi [GOVERNANCE.md](GOVERNANCE.md), [DCO.md](DCO.md),
[PRIVACY.md](PRIVACY.md), [SECURITY.md](SECURITY.md) et
[LICENSE-NOTICE.md](LICENSE-NOTICE.md).

Le [tutoriel illustré](docs/TUTORIEL.md) décrit le parcours Caldwell et les
contrôles locaux. Le propriétaire a autorisé la publication du plan et des
lots ECC-D à ECC-I sur leur branche. Le travail reste dans les copies locales.
Les fusions nº 10 → nº 11 → nº 12 ont ensuite été explicitement autorisées,
avec contrôles verts avant chaque fusion; aucun réglage GitHub ne change.

Les [contrôles ECC-E](docs/QUALITE.md) mesurent lignes et branches, vérifient
progressivement les types et recherchent secrets et dépendances vulnérables.

ECC-G sépare le [service et les rapports](docs/APPLICATION.md), avec restauration
des réglages IERS à la sortie et préservation des commandes existantes.

ECC-H ajoute des [références satellitaires gelées](docs/SCIENCE_SATELLITE_REFERENCES.md)
et des [mesures temps/mémoire reproductibles](docs/PERFORMANCES.md).

ECC-I précise [la confidentialité](PRIVACY.md), les attributions,
[la livraison](docs/RELEASE.md) et [la gouvernance observée](docs/GOUVERNANCE_VERIFIEE.md).

ECC-F coordonne les mises à jour par verrou. La [rétention du cache](docs/CACHE.md)
se simule avec `gnu-astrolist-cache --cache-dir local/catalog-cache --keep 2`;
l’option `--apply` applique explicitement le retrait. Les archives Seestar sont protégées.

Validation ECC-D à ECC-I : 716 tests locaux réussis, couverture 90,34 % et
cinq contrôles GitHub verts sur `a3804fe`; [PR nº 12](https://github.com/steveprudhomme/gnuastrolist/pull/12).
Python 3.11 minimum, quatre verrous audités, aucune archive Seestar réelle utilisée.


Le parcours d'intégration dans `main` suit les PR nº 9 (ECC-A), nº 10 (ECC-B),
nº 11 (ECC-C), puis nº 12 (ECC-D à ECC-I). Les contrôles sont vérifiés sur
chaque nouvelle base et sur main après intégration. Voir [la feuille de route](ROADMAP.md).


## Versionnage des livraisons

Le projet utilise SemVer : bug corrigé → correctif; amélioration ou nouvelle
fonctionnalité compatible → mineure; rupture de compatibilité → majeure.
Les [fragments de changements](changes/README.md) gardent les catégories et
alimentent les notes. Le niveau le plus élevé s'applique une fois par livraison.

```powershell
python -B scripts/versioning.py check
python -B scripts/versioning.py preview
```

Ces commandes se lancent depuis les sources. L'aperçu propose actuellement
0.12.0 pour les changements en attente, sans modifier la version courante 0.11.0.
La préparation synchronisée est explicite; tag et Release restent distincts.
Voir le [guide du versionnage](docs/VERSIONNAGE.md).
