# ADR 0001 — Catalogues du ciel profond et magnitudes absentes

Statut : implémenté localement, soumis à revue.

## Contexte

L'ajout Caldwell réutilise la sélection et les sorties Messier, mais plusieurs
nébuleuses et amas n'ont pas de magnitude V exploitable dans les sources retenues.

## Décision

Utiliser un modèle commun `DeepSkyObject`, en conservant `MessierObject` comme
alias compatible. Charger les catalogues locaux séparément, avec leurs noms,
désignations, coordonnées et provenance. Une magnitude absente vaut `None`;
elle apparaît « non disponible », passe après les valeurs connues au tri et
est exclue d'un filtre numérique. Sans filtre, l'objet reste sélectionnable.

Conserver OpenNGC comme base Caldwell et consulter SIMBAD en lot pour les V
absentes. Écarter les qualités D/E du complément. Ne pas substituer une bande B,
une magnitude d'étoile centrale ou une estimation sans bande documentée.

## Conséquences

Les consommateurs du modèle doivent gérer l'absence de V. Les sorties TXT/PDF
partagent le formatage de cette absence. Les tests doivent démontrer sélection,
tri et export d'un objet sans V. L'enrichissement SIMBAD reste un outil explicite
de préparation des données; il n'ajoute aucune connexion au mode hors ligne.
