# Comètes : MPC et observations CBAT

Le catalogue `comets` charge les orbites du Minor Planet Center. Le fichier
embarqué compte 958 entrées cométaires après exclusion des 15 objets A/.
La [notice source](../src/gnu_astrolist/data/COMET_SOURCE.md) conserve les droits,
unités, date, empreinte et méthode de reconstruction.

Créer `local` dans le dossier du projet, puis utiliser par exemple :

```powershell
.venv\Scripts\python -m gnu_astrolist --date 2026-11-17 --time-range 21:00-22:00 --timezone America/Toronto --lat 45.57 --lon -73.68 --az-min 0 --az-max 360 --min-altitude 10 --objects comets asteroids --max-magnitude 18 --offline --limit 20 --output-txt local/cometes.txt --output-pdf local/cometes.pdf
```

On peut combiner les comètes avec tous les autres catalogues. Le même seuil
numérique s'applique à la **magnitude totale estimée des comètes**, et à V pour
les autres objets (maximum publié pour GCVS). Ce n'est pas une conversion entre
bandes. Les intitulés et les valeurs des rapports expliquent cette différence.
`--all-magnitudes` désactive le filtre; une magnitude inconnue reste inconnue.

## Position et lumière

Le moteur résout les variables universelles de Kepler à partir du périhélie :
fonctions de Stumpff et encadrement monotone, pour les ellipses, paraboles et
hyperboles. Les tests analytiques incluent une parabole exacte et la continuité
près de e=1; la copie MPC actuelle contient des ellipses et hyperboles.
Le Soleil et la Terre utilisent le modèle Astropy intégré. Temps de lumière,
position du site et transformations vers Alt/Az sont communs aux astéroïdes.
Les coordonnées RA/Dec de la fiche calculée sont GCRS à l'instant retenu.

La magnitude totale est estimée avec les paramètres du fichier MPC :
`m ≈ H + 5 log10(Δ) + 2,5 k log10(r)`, distances en AU. Ici k est l'exposant
cométaire du fichier, d'où le facteur 2,5. Il ne s'agit ni du modèle H-G des
astéroïdes ni d'une mesure V. H ou k absent donne une magnitude inconnue.
Le modèle ignore les sursauts, la fragmentation, la queue, le dégazage,
l'extinction et les perturbations planétaires : vérifier Horizons pour un
pointage précis. Il ne prédit pas si un noyau est encore actif ou intact.

Le programme filtre champ et magnitude au **même échantillon**; l'instant local
affiché correspond à la valeur la plus brillante retenue dans le champ. Un
passage entre deux échantillons peut être manqué. Réduire le pas pour un objet
rapide. Les franchissements de hauteur sont recherchés seulement dans la plage.
Les dates saisonnières et d'opposition ne sont pas calculées pour les comètes.

Une époque MPC est requise à ±365 jours de toute la plage, avec le modèle
planétaire limité à 1900–2100. Les orbites sans époque ou périmées sont exclues
**avec effectif annoncé**, sans inventer d'époque. Si aucune n'est exploitable,
le programme refuse le calcul. Cette borne n'est pas une garantie de précision.
Actualiser le téléchargement ne rend pas récente une époque ancienne.

## Actualiser les orbites ou utiliser son fichier

Ajouter `--update-catalogs if-stale --catalog-age comets=24` pour une vérification
au démarrage, en enlevant `--offline` afin d'autoriser la connexion. Voir les
[réglages de tous les catalogues](CATALOG_UPDATES.md).

`--comets-file local/CometEls.txt` ou un fichier `.gz` remplace la copie orbitale
par un fichier MPC local. Cette option garde la priorité sur les mises à jour
du cache pour les comètes. Le fichier fourni n'est jamais modifié.

## Observations CBAT/ICQ locales

`--cbat-file local/cbat.csv` ajoute un complément d'observations. Le format
est une transcription locale documentée, **pas un format officiel d'export CBAT**.
En-tête obligatoire :

```csv
designation,observed_at,magnitude,band,observer,reference,url
```

- `designation` : identifiant complet comme `C/2023 A3`, `161P` ou `73P-B`.
- `observed_at` : date et heure ISO 8601 avec fuseau, idéalement UTC avec `Z`.
- `magnitude`, `band` : valeur observée finie et bande originale; aucune conversion V.
- `observer`, `reference`, `url` : attribution, référence de la mesure et URL
  publique CBAT/ICQ/Harvard. Une URL saisie n'est pas une preuve d'authenticité;
  le programme la conserve sans la contacter ni vérifier l'observation à distance.

Tous les champs sont requis. Les doublons exacts et dates sans fuseau sont
refusés. Pour chaque comète, la plus récente observation **antérieure ou égale
au début de la plage** est affichée dans un champ séparé, avec sa date UTC,
sa bande et sa provenance. Elle ne change ni le filtre ni la magnitude calculée.
Il n'y a pas de limite d'âge automatique des observations : toujours lire la date.
Les fragments sont distincts et les noms partagés (ATLAS, PANSTARRS...) seuls ne
sont jamais utilisés pour réunir des objets. Seestar suit la même règle,
en lecture seule; `C_2023_A3` et `C/2023 A3` sont rapprochés explicitement.

Le site CBAT/ICQ n'ayant pas pu être lu pendant ce lot, aucune mesure réelle
CBAT n'est fournie avec le paquet. Aucune connexion CBAT automatique n'est promise.
Respecter les droits propres aux extraits des circulaires; ne pas publier son
CSV sans autorisation. Les tests et le schéma du tutoriel sont synthétiques.

## Références indépendantes

[Quatre positions JPL Horizons](../tests/data/comet_horizons.json) sont figées
pour 67P et C/2023 A3 aux 18 novembre 2026, 02:00 et 03:00 UTC, Laval, altitude 0.
Les requêtes, empreintes et valeurs numériques sont conservées; élévation sans
réfraction. Sous Astropy 7.2, les écarts angulaires sont inférieurs à 10″.
Le test n'impose pas un accord photométrique : les paramètres MPC/JPL ne sont
pas toujours les mêmes, notamment pour 67P. Ces cas ne valident pas toutes les
comètes. Les tests ordinaires ne contactent aucun service.

Références : [format MPC](https://docs.minorplanetcenter.net/mpc-ops-docs/orbits/comet-orbit-format/),
[orbites à deux corps et précautions Skyfield](https://rhodesmill.org/skyfield/kepler-orbits.html),
[API Horizons](https://ssd-api.jpl.nasa.gov/doc/horizons.html).
