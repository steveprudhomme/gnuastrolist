# Préparer une observation d'astéroïdes

`--objects asteroids` utilise les 1 000 premiers astéroïdes numérotés de la
copie JPL embarquée. Les orbites et leurs noms sont locaux. Aucun téléchargement
n'est nécessaire pendant le calcul. Ce catalogue peut être combiné avec
`messier`, `caldwell`, `ngc`, `bayer`, `flamsteed` et `variable_stars`.

```powershell
.venv\Scripts\python -m gnu_astrolist --date 2026-11-17 --time-range 21:00-22:00 --timezone America/Toronto --lat 45.57 --lon -73.68 --az-min 0 --az-max 360 --min-altitude 10 --objects asteroids messier --max-magnitude 10 --offline --limit 20 --output-txt local/asteroides.txt --output-pdf local/asteroides.pdf
```

Créer `local` dans le projet avant l'export. Les sorties restent sur l'ordinateur.
`--seestar-path "E:\MyWorks"` est facultatif et consulte uniquement les noms et
métadonnées des archives en lecture seule. La présence d'une archive n'indique
pas qu'un astéroïde est encore au même endroit dans le ciel.

## Ce qui est calculé

Pour chaque échantillon horaire, le moteur résout l'équation de Kepler avec
le paramètre gravitationnel solaire Astropy, propage les éléments osculateurs
à deux corps en TDB, convertit l'écliptique J2000 en équatorial J2000, puis utilise
les positions Terre/Soleil du modèle intégré Astropy. Il applique le temps de
lumière itératif et transforme les coordonnées vers le site d'observation.
Les hauteurs sont topocentriques et sans réfraction atmosphérique.
La rotation utilise une obliquité J2000 constante de 23,439291111°.

La magnitude visuelle est estimée par la forme exponentielle H-G de Bowell
(1989), avec distances héliocentrique/observateur et angle de phase :

```text
V ≈ H + 5 log10(r Δ) − 2,5 log10((1−G) Φ1 + G Φ2)
Φ1 = exp(−3,33 tan(α/2)^0,63)
Φ2 = exp(−1,87 tan(α/2)^1,22)
```

Ce modèle ne prévoit ni rotation de l'objet, ni extinction atmosphérique,
ni variations physiques particulières. La valeur G=0,15 est supposée si elle
manque, et cette hypothèse apparaît avec `--details`. Sans H, aucune magnitude
n'est inventée : l'objet reste admissible sans limite V, mais est exclu si une
limite est demandée. `--all-magnitudes` désactive le filtre.

Le symbole **≈** distingue cette estimation des magnitudes publiées des autres
catalogues. Le tri retient la magnitude la plus brillante parmi les échantillons
dans le champ. L'**Instant V estimée (local)** indique cet échantillon. Avec une
limite V, il faut être dans le champ et assez brillant au même instant.
Cela ne garantit pas un passage entre deux échantillons; réduire
`--sample-minutes` pour un objet rapide. Les coordonnées RA/Dec de la fiche interne
sont topocentriques GCRS à cet instant, pas des coordonnées ICRS fixes.

## Limites temporelles et précision

Les dates doivent rester à **±365 jours de chaque époque orbitale**, et entre
1900 et 2100 pour le modèle planétaire intégré. Pour cette copie, l'époque est
le **9 juin 2026 à 00:00 TDB**, soit une plage admise du 9 juin 2025 au 9 juin 2027
en TDB. Les dates CLI sont converties depuis l'heure locale : attention aux bords.
Si une orbite est périmée, le calcul échoue explicitement avant les exports.

Cette borne est une précaution de fonctionnement, **pas une garantie de précision**.
Le modèle ignore les perturbations planétaires, les incertitudes orbitales et
les effets non gravitationnels. Un passage proche d'une planète peut rendre
l'approximation mauvaise, même près de l'époque. Vérifier la position dans
JPL Horizons pour le pointage précis, les objets géocroiseurs et les approches
rapprochées. Le logiciel ne calcule aucun risque d'impact.

Les franchissements de hauteur des astéroïdes sont interpolés uniquement dans
la plage demandée. Une case vide ne signifie pas « toujours au-dessus ».
Les dates de visibilité saisonnière, séparation solaire maximale et opposition
restent vides : les formules des objets fixes ne leur sont pas appliquées.

## Actualiser ou étendre avec un fichier local

Préparer une réponse JSON de SBDB Query 1.0 avec les champs décrits dans la
[notice source](../src/gnu_astrolist/data/ASTEROID_SOURCE.md), puis ajouter :

```text
--objects asteroids --asteroids-file local/orbites-sbdb.json
```

Ce fichier **remplace** la sélection embarquée; il n'est jamais modifié.
Il peut contenir davantage de numéros ou des éléments plus récents. Toutes les
orbites doivent être valides pour la plage demandée; une erreur ou un doublon
fait refuser le fichier entier. Les comètes, objets non numérotés, orbites ouvertes
et autres formats ne sont pas pris en charge. Le rapport indique l'effectif et
les époques du fichier réellement utilisé. La date de récupération reste inconnue
si le fichier ne contient pas `astrolist_retrieved_on`.

## Comparaison indépendante reproductible

Les tests réutilisent six échantillons publics JPL Horizons : Ceres (1), Vesta (4)
et Eros (433), aux JD UTC 2461362.583333333 et 2461362.625, soit le 18 novembre
2026 à 02:00 et 03:00 UTC. Site géodésique : longitude −73,68°, latitude 45,57°,
altitude 0 km; centre `coord@399`; élévation sans réfraction `APPARENT=AIRLESS`.
Le fichier [de référence](../tests/data/asteroid_horizons.json) conserve paramètres,
valeurs extraites, date et empreintes des réponses brutes. `COMMAND='1;'`, `'4;'`
ou `'433;'` distingue bien les astéroïdes des planètes. `CSV_FORMAT=YES` et
`CAL_FORMAT=JD`; quantités `4,9,20`; API Horizons 1.3. Données publiques JPL.

Sous Astropy 7.2, le plus grand écart angulaire des six positions est inférieur
à **13,2 secondes d'arc**; l'écart de magnitude est inférieur à **0,001**.
Les seuils de régression sont 20″ et 0,01 magnitude pour absorber les différences
de tables terrestres et de versions Astropy. Ces quelques cas ne valident pas
toutes les orbites ni toute la plage de dates. Aucun appel réseau dans ces tests.

Références : [SBDB Query](https://ssd-api.jpl.nasa.gov/doc/sbdb_query.html),
[Horizons](https://ssd-api.jpl.nasa.gov/doc/horizons.html),
[avertissements SSD sur la propagation](https://ssd.jpl.nasa.gov/faq.html),
[modèle H-G et référence Bowell dans sbpy](https://sbpy.readthedocs.io/en/latest/api/sbpy.photometry.HG.html),
[positions des corps Astropy](https://docs.astropy.org/en/stable/api/astropy.coordinates.get_body_barycentric.html).
