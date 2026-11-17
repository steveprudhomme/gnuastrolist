# 0006 — Précontrôle numérique et grilles temporelles partagés

Statut : accepté pour le lot ECC-C, le 17 novembre 2026.

## Contexte

La CLI pouvait actualiser les catalogues avant de découvrir un budget temporel
dépassé. Certains pas provoquaient une division par zéro ou un dépassement au
lieu d'une erreur de saisie. Les moteurs ne contrôlaient pas tous le site de
la même manière, notamment avec une liste vide.

## Décision

Regrouper dans `validation.py` les domaines numériques, le site terrestre,
les bornes UTC des fenêtres et le calcul du budget en microsecondes entières.
Le précontrôle compte les instants sans les allouer. Le moteur génère ensuite
la grille avec la même règle, début et fin inclus, pour éviter un désaccord
entre validation et calcul.

La CLI valide aussi les réglages d'actualisation avant d'activer sa politique
IERS et de lancer les fournisseurs. Les lecteurs conservent leur validation
scientifique des catalogues. Aucun résultat calculé n'est remplacé par une
valeur fictive en cas d'erreur de paramètre.

`models.py` peut appeler ces fonctions pures; l'import de `ObservationWindow`
dans `validation.py` reste réservé au typage pour éviter un cycle à l'exécution.

## Conséquences

Les API et la CLI partagent les limites décrites dans [PARAMETRES.md](../../PARAMETRES.md).
La borne exacte de 2 000 instants devient utilisable. Les réglages invalides
sont refusés avant effets; une erreur ultérieure de contenu scientifique ne
constitue pas une transaction annulant les opérations précédentes. Les tests
restent déterministes, hors réseau, sur des archives synthétiques.
