# Sélections Bayer et Flamsteed

Source : [HYG 4.1](https://github.com/astronexus/HYG-Database), David Nash /
Astronomy Nexus et contributeurs, fichier `hyg/CURRENT/hygdata_v41.csv` de la
révision `c7f7f883fe678cc7680169a50ccd7dcc49b060ce`, récupéré le 17 novembre 2026.
Les données dérivées restent sous **CC BY-SA 4.0** : voir [HYG_LICENSE.md](HYG_LICENSE.md).
Empreinte SHA-256 du fichier source :
`d9f69fd86bbf90a4e4d52b4c5c53eacfa6dfc0bfdef85bfd94f095e0bebe4ebd`.

Les champs `bayer`, `flam` et `con` définissent les sélections. L'ascension droite
est convertie d'heures en degrés; la déclinaison reste en degrés. Le champ `mag`
fournit la magnitude visuelle de référence. Il n'est ni un maximum GCVS ni une
prédiction pour la soirée; son homogénéité photométrique n'est pas garantie ici.
Les coordonnées de référence J2000 restent fixes, sans propagation des mouvements
propres. Les noms courants sont repris comme fournis; certains noms de composants
HYG sont des étiquettes pratiques, pas des noms officiels IAU.

## Résultat de la transformation

| Sélection | Fiches embarquées |
| --- | --- |
| Bayer | 1 537 |
| Flamsteed | 2 737 |
| Union par identifiant HYG | 3 321 |

Ces sélections ne sont pas des inventaires exhaustifs de toutes les désignations
historiques. Elles couvrent les champs explicites présents dans cette révision;
les Bayer disponibles ici utilisent les lettres grecques. Une étoile sans champ
correspondant n'est pas ajoutée à la sélection. La révision sélectionnée ne
présente aucune magnitude absente dans ces sélections, mais le format admet None.

Les noms affichés sont construits sans inventer de désignation : `Alp` devient
`α`, `Alp-1` devient `α¹`, et le numéro Flamsteed reste associé à sa constellation.
Les composants partageant une désignation gardent des fiches distinctes et un
suffixe `[HYG numéro]`. L'identifiant HYG est une clé de cette révision, pas une
preuve universelle d'identité entre versions ou avec d'autres catalogues.

Lors d'une sélection Bayer + Flamsteed, une même clé HYG donne une seule fiche,
avec priorité au nom Bayer et conservation du nom Flamsteed comme alias. Les
magnitudes et coordonnées ne sont pas mélangées. Aucune identité GCVS/NGC n'est
déduite de la position. Les noms partagés sont signalés au moteur Seestar pour
éviter d'attribuer une même acquisition à plusieurs composants sans preuve.

## Reconstruction locale

Après installation de développement, fournir la copie locale vérifiée de HYG :

```text
python scripts/build_stellar_catalogs.py --source local/hyg-source/hygdata_v41.csv --output-dir src/gnu_astrolist/data
```

Le générateur vérifie l'empreinte, les coordonnées, les magnitudes et les clés
répétées. Les gzip sont déterministes (horodatage nul). La copie source reste
dans `local/`, ignoré par Git; seuls les extraits et notices sont distribués.
Une mise à jour exige de réexaminer les compteurs, noms, références et tests.
