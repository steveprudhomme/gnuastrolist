# Architecture

Le paquet suit une structure `src/` et expose `gnu-astrolist` ainsi que
`python -m gnu_astrolist`. `cli.py` orchestre les composants :

```text
arguments → time_utils + models → catalog → visibilité → output / pdf_output
                                    moon et weather → résumés du rapport
```

`models.py` définit les objets indépendamment des fournisseurs. `catalog.py`
charge les CSV compressés via les ressources Python, puis filtre en magnitude.
`visibility.py` calcule les positions avec Astropy et enrichit les objets
retenus. `moon.py` traite les conventions lunaires. `weather.py` isole les
appels météo et leurs pannes. Les rendus texte et PDF utilisent les mêmes valeurs.

Depuis ECC-B, `weather.py` valide le transport et normalise les mesures sous
forme de lignes indexées par instant UTC. Les agrégations par période gardent
les variables indépendantes; la rosée exige un trio complet au même instant.
Les erreurs attendues deviennent `WeatherDataError`, les données partielles
produisent des avertissements et les erreurs de programmation restent visibles.
`WeatherSummary.available` reconnaît toute grandeur affichable, pas seulement
nuages/seeing. Les rendus partagent ces états sans nouveau format de rapport.
Voir les [contrôles, unités et périodes de repli](METEO.md).

`validation.py` fournit les domaines numériques, la validation du site et des
fenêtres, ainsi que le comptage entier des grilles temporelles UTC. La CLI appelle
le précontrôle avant la configuration IERS et l'actualisation; les moteurs
réutilisent ces fonctions avant Astropy. Les âges CLI/JSON sont normalisés par
`updates.validate_max_ages()` avant toute actualisation. Les lecteurs gardent la
validation scientifique des données, distincte de ce précontrôle ECC-C.
Voir [PARAMETRES.md](PARAMETRES.md).

Les générateurs de catalogues dans `scripts/` ne sont pas appelés au démarrage.
`build_ngc_catalog.py` exige un fichier source local et contrôle son empreinte;
`load_ngc_catalog()` réutilise le modèle du ciel profond et le chargeur commun.
`selection.py` normalise les catalogues demandés, regroupe les désignations
identiques et définit les filtres par catalogue. Les rendus utilisent
`CatalogSelection` pour décrire une sélection multiple et les alias des fiches.
`seestar.py` inventorie en mémoire les noms et métadonnées des acquisitions,
protège l'espace source contre les exports et annote les résultats affichés.
Les statuts sont partagés par les rendus TXT/PDF. Sans option Seestar, cet
inventaire n'est pas lancé et les sorties gardent leur format précédent.

`report_files.py` centralise les contrôles ECC-A des entrées et destinations,
avant les effets de la CLI puis avant chaque publication. Il protège également
le paquet installé et le cache de la commande. `staged_report()` prépare un
fichier voisin et publie chaque rapport atomiquement, avec remplacement explicite
uniquement (`--overwrite` dans la CLI). TXT et PDF restent indépendants; le rendu
PDF réutilise ce composant. Voir les [règles et limites des exports](EXPORTS.md).

`NamedStar` représente les fiches HYG, indépendamment des maxima GCVS et des
objets du ciel profond. `stellar_names.py` normalise les désignations explicites.
La sélection multiple réunit Bayer/Flamsteed par clé HYG de la révision embarquée;
les identités GCVS/NGC ne sont pas inférées. Le moteur astronomique stellaire reste commun.

`asteroids.py` sépare les orbites mobiles des objets fixes. Il lit une réponse
SBDB locale, propage les positions par échantillon et estime les magnitudes H-G.
Le filtre V est appliqué simultanément au champ; la fiche `AsteroidTarget` est
créée après ce calcul, avec l'instant de référence. Les rendus partagent le
symbole d'estimation et cet instant. Le moteur fixe refuse ces fiches pour éviter
tout calcul saisonnier erroné. Voir la [décision 0003](architecture/decisions/0003-asteroides.md)
et les [limites scientifiques](ASTEROIDS.md).
Les tests ne doivent pas dépendre de leurs services distants. Une nouvelle
méthode ou source doit avoir une notice, des exemples vérifiables et des tests.

`moving.py` partage la géométrie Terre/Soleil/site, le temps de lumière et la
sélection simultanée champ/magnitude des astéroïdes et comètes. `comets.py`
lit les colonnes MPC, propage les trois coniques par variables universelles
et garde la photométrie totale distincte de V. Les observations CBAT locales
restent un enrichissement daté du résultat; elles ne servent pas au filtre.

`updates.py` décrit les sources évolutives et construit des générations de cache
validées avant activation atomique. `data_builders/` contient les générateurs
installables; les anciens scripts restent des points d'entrée compatibles.
`catalog_resources.py` active temporairement les copies de la commande et
vide les caches mémoire à l'entrée et à la sortie. Les ressources distribuées
ne sont pas écrasées. La CLI valide ses paramètres et protège les destinations
Seestar avant tout appel d'actualisation. Le mode hors ligne est fixé avant
les conversions temporelles, la météo ou les téléchargements de catalogues.

Voir la [décision 0004](architecture/decisions/0004-cometes-actualisations.md).

`satellites.py` utilise SGP4 et le repère TEME pour les objets artificiels,
avec soustraction du site en ITRS avant Alt/Az. Son pas en secondes est distinct
des catalogues lents. `satcat.py` joint les métadonnées par NORAD et COSPAR,
puis les extraits administratifs UNOOSA par COSPAR explicite. `SatelliteTarget`
reste sans magnitude; géométrie solaire et immatriculation ne sont pas de la photométrie.

`satellite_updates.py` maintient une génération GP/SATCAT commune et l'état des
requêtes du fournisseur. Les règles CelesTrak (délais minimaux, compression,
arrêt sur statut non 200) s'appliquent avant publication dans le cache protégé.
La [décision 0005](architecture/decisions/0005-satellites-registres.md) décrit les limites.
