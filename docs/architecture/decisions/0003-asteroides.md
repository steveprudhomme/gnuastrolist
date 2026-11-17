# 0003 — Séparer les orbites mobiles des catalogues fixes

Statut : accepté localement, 2026-11-17.

Les astéroïdes changent de position et de luminosité. Les filtrer sur une
magnitude absolue H ou réutiliser une coordonnée fixe donnerait des listes fausses.

`AsteroidOrbit` conserve les éléments JPL; `asteroids.py` calcule position et
magnitude à chaque instant, par lots, avec les dépendances déjà utilisées.
`AsteroidTarget` conserve seulement la fiche de rendu à l'instant de référence.
Le moteur fixe refuse explicitement ce type. `selection.py` reporte le filtre V
au moteur mobile. La CLI réunit ensuite les résultats pour un tri commun.

Une copie compressée des premiers 1 000 numéros garantit le fonctionnement
hors ligne. Un JSON SBDB local peut la remplacer, sans mutation ni réseau caché.
Le schéma, les unités, les doublons et les limites temporelles sont contrôlés.
Les archives installables incluent données, notices et fixtures de comparaison.

Le coût de ce choix est une précision limitée par la propagation à deux corps,
explicitement affichée, et une actualisation manuelle des éléments. Il ne remplace
pas Horizons pour le pointage précis. Le modèle n'ajoute aucune date saisonnière
calculée avec la méthode des objets fixes. L'identifiant Seestar `MPC4` distingue
Vesta de `M4`; un numéro seul ne prouve jamais une identité.

Voir [le guide et ses limites](../../ASTEROIDS.md).
