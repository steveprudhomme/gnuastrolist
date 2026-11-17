# ADR 0002 — Sélection de plusieurs catalogues

Statut : implémenté localement, soumis à revue.

## Interface et compatibilité

`--objects` accepte un ou plusieurs noms et peut être répété. Les répétitions
et l'alias `messier_objects` sont normalisés. Une commande à catalogue unique
garde ses règles, ses valeurs et ses libellés précédents.

## Identité et choix des valeurs

Les fiches du ciel profond sont réunies seulement si elles possèdent la même
désignation explicite, après normalisation des zéros initiaux NGC/IC/C et de
la casse. Les suffixes restent distincts. Une désignation absente ne prouve
jamais l'identité; aucune fusion n'est fondée sur la position ou le nom courant.

L'ordre de priorité est fixe : Messier, Caldwell, NGC. La fiche prioritaire est
conservée intégralement, avec coordonnées, dimensions, magnitude et provenance.
Les autres noms deviennent des alias affichés sur la même ligne. Aucun mélange
de valeurs entre fiches n'est effectué. Ce choix précède le filtre de magnitude :
une valeur plus favorable d'une fiche secondaire ne remplace pas la valeur retenue
pour franchir le seuil. Une V absente dans la fiche prioritaire reste absente.

Les groupes et leurs composants ne sont pas assimilés. Par exemple, C14 reste
distinct de NGC869 et NGC884. GCVS n'est pas rapproché du ciel profond sans
référentiel explicite. Le résultat n'est pas un inventaire dédoublonné de tous
les objets physiques du ciel.

## Filtres et rapports

Par défaut, GCVS garde V maximum publié ≤ 8, les autres catalogues n'ont aucune
limite. `--max-magnitude` applique la même limite à tous; `--all-magnitudes`
supprime toutes les limites. Une V absente ne passe pas un filtre numérique.

`selection.py` isole le chargement, l'identité et la politique de filtre.
`CatalogSelection` transmet aux rendus les catalogues et limites effectivement
utilisés. Les rapports mixtes distinguent les maxima GCVS des magnitudes de
référence du ciel profond et affichent les alias. La visibilité et le tri restent
communs, sans modification du moteur astronomique.
