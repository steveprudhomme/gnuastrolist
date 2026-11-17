# 0005 — Séparer les passages SGP4 des identités et registres

Statut : accepté localement, 2026-11-17.

Les éléments moyens des satellites artificiels exigent SGP4 et un repère TEME.
Le moteur héliocentrique des petits corps n'est pas adapté à ce calcul.
Un identifiant COSPAR, une fiche SATCAT ou une immatriculation ONU ne fournit
pas à lui seul une position actuelle ni une luminosité optique.

`satellites.py` possède son parseur GP/OMM, son contrôle d'époque et son
échantillonnage rapide. Il partage le modèle de résultat et les rendus, sans
appliquer de dates saisonnières ou de magnitude fictive. SGP4 est une dépendance
déclarée, MIT, vérifiée avec les cas de référence Vallado et les repères Astropy.

`satcat.py` conserve les numéros NORAD étendus et COSPAR complets, vérifie leur
cohérence et garde les types PAY/R/B/DEB distincts. UNOOSA est un enrichissement
administratif importé localement, sans format officiel d'export revendiqué ni
affirmation de non-immatriculation en l'absence d'extrait.

La copie embarquée est une sélection annoncée de deux groupes CelesTrak.
Les mises à jour des deux sélections partagent une génération atomique contenant
GP, SATCAT et provenance. Le fournisseur a des règles propres : CSV/gzip,
cadence minimale, arrêt immédiat après statut non 200 et état persistant
de blocage ou pause. Le mode hors ligne reste absolu.

Le coût de cette décision est une dépendance SGP4, un contrôle d'époque plus
court et un risque de passages manqués entre échantillons. Éclairage et hauteur
du Soleil sont des conditions géométriques, sans garantie de détection. Aucun
calcul de collision ou emploi pour la navigation n'est fourni.

Voir [le guide](../../SATELLITES.md) et [la provenance](../../../src/gnu_astrolist/data/SPACE_OBJECT_SOURCE.md).
