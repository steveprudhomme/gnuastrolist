# Catalogue orbital des astéroïdes

NASA/JPL Solar System Dynamics, Small-Body Database Query API **1.0**.
Données récupérées le **2026-11-17**. Attribution NASA/JPL-Caltech; aucune
affiliation ni approbation de ce logiciel n'est revendiquée.

La [FAQ SSD, rubrique publication](https://ssd.jpl.nasa.gov/faq.html)
indique que les données du site sont du domaine public, réutilisables sans
permission, avec citation recommandée et signalement des modifications.
Ce statut concerne les données factuelles, pas les logos ni le code du site.
Le code original du générateur et du moteur reste GPL-3.0-or-later.

## Sélection et empreinte

La copie embarquée contient **1 000 astéroïdes numérotés**, de (1) Ceres à
(1000) Piazzia, triés par identifiant SPK. Ce n'est ni un catalogue exhaustif,
ni une sélection de tous les objets les plus brillants. Les noms anglais de la
source sont conservés. Une copie JSON locale permet d'étendre la sélection.

Requête exacte :

```text
https://ssd-api.jpl.nasa.gov/sbdb_query.api?fields=spkid%2Cpdes%2Cname%2Cepoch%2Cequinox%2Ca%2Ce%2Ci%2Com%2Cw%2Cma%2CH%2CG%2Corbit_id&sb-kind=a&sb-ns=n&sort=spkid&limit=1000&full-prec=true
```

SHA-256 de la réponse brute avant transformation :
`5d14ee1a784dfba0e415fd58373a339dbe0ff820f8a0a7be0fdc0c78fa823157`.
Les données sources évoluent : une nouvelle requête ne reproduira pas forcément
cette empreinte. Garder sa réponse locale pour pouvoir reconstruire la même copie.

Transformation : validation du schéma et des orbites, ajout de
`astrolist_retrieved_on`, sérialisation JSON canonique UTF-8, compression gzip
sans nom de fichier ni date interne. Aucune valeur orbitale n'est corrigée.

```powershell
python scripts/build_asteroid_catalog.py --source local/asteroid-source/sbdb.json --output src/gnu_astrolist/data/asteroids.json.gz --retrieved-on 2026-11-17
```

Le générateur exige l'empreinte ci-dessus par défaut. Pour une nouvelle réponse
vérifiée, fournir son empreinte réelle avec `--expected-sha256` et mettre à jour
la présente notice ainsi que les références et tests concernés.

## Unités et conventions

Voir la [documentation SBDB Query](https://ssd-api.jpl.nasa.gov/doc/sbdb_query.html).

| Champ | Convention |
| --- | --- |
| `pdes`, `name`, `spkid`, `orbit_id` | Numéro mineur, nom, identifiant SPK et solution orbitale |
| `epoch` | Jour julien TDB; 2461200.5 pour toutes les orbites embarquées |
| `equinox` | J2000, éléments héliocentriques dans l'écliptique J2000 |
| `a`, `e` | Demi-grand axe en AU, excentricité sans unité |
| `i`, `om`, `w`, `ma` | Inclinaison, nœud ascendant, argument du périhélie, anomalie moyenne en degrés |
| `H`, `G` | Magnitude absolue et pente H-G; valeurs absentes conservées |

Seules les orbites elliptiques numérotées, avec `a > 0`, `0 ≤ e < 1` et
inclinaison entre 0 et 180°, sont acceptées. Les doublons sont des erreurs.
La version API est contrôlée. `H` ne remplace jamais la magnitude apparente.
Pour les **896 valeurs G manquantes**, le moteur suppose explicitement 0,15.
Une valeur H absente laisse la magnitude apparente inconnue.

## Accès responsable

Le programme, les générateurs et les tests ordinaires ne téléchargent aucune
orbite. Pour acquérir une nouvelle réponse, respecter la
[politique d'accès JPL](https://ssd-api.jpl.nasa.gov/doc/index.php) : requêtes
séquentielles, cache local, en-tête User-Agent identifiant réellement
l'application, sa version et un contact, temporisation en cas d'erreur.
Ne pas interroger l'API pour chaque astéroïde ou à chaque lancement.

Les limites scientifiques et les comparaisons indépendantes sont décrites dans
[le guide astéroïdes](../../../docs/ASTEROIDS.md).
