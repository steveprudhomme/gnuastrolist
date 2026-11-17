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
Les tests ne doivent pas dépendre de leurs services distants. Une nouvelle
méthode ou source doit avoir une notice, des exemples vérifiables et des tests.
