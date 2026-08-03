# Feuille de route

## Prochaine version

- [ ] Exporter les résultats en CSV et JSON.
- [ ] Ajouter un mode « visible au début », « visible à la fin » ou « visible
      pendant toute la plage ».
- [x] Enrichir le tableau des résultats avec les colonnes suivantes :
  - taille apparente de l'objet (dimensions angulaires);
  - magnitude apparente;
  - dates distinctes de séparation solaire maximale et de meilleure visibilité
    saisonnière;
  - constellation;
  - heure du passage au-dessus de l'élévation minimale choisie par
    l'utilisateur;
  - heure du passage sous cette élévation minimale.
- [x] Corriger et documenter la provenance des tailles et magnitudes des objets
      du ciel profond en enrichissant le catalogue local avec SIMBAD :
  - conserver OpenNGC comme catalogue local principal et comme solution de
    repli hors ligne;
  - interroger SIMBAD en lot, de préférence par TAP ou `astroquery`, plutôt
    qu'objet par objet;
  - utiliser en priorité les dimensions apparentes valides de SIMBAD
    (axes majeur et mineur), puis celles d'OpenNGC si SIMBAD ne fournit aucune
    valeur exploitable;
  - appliquer la même stratégie à la magnitude apparente en bande V lorsque
    celle-ci est disponible;
  - enregistrer et afficher la provenance de chaque valeur : catalogue,
    référence bibliographique ou bibcode et date de récupération;
  - ajouter un cache local afin de limiter les requêtes réseau, de respecter
    les limites de service et de permettre le fonctionnement hors ligne;
  - afficher les dimensions sous la forme `axe majeur × axe mineur` et préciser
    explicitement la source dans les sorties détaillées;
  - ajouter des tests de comparaison sur des objets de référence, notamment
    M39, M15 et M52.
- [x] Clarifier et corriger la colonne actuellement appelée **Opposition** pour
      les objets du ciel profond :
  - renommer le calcul géométrique actuel **Séparation solaire maximale**;
  - ajouter séparément une date de **Meilleure visibilité saisonnière**, fondée
    sur la période où l'objet culmine près du milieu de la nuit;
  - réserver le terme **Opposition** aux objets pour lesquels cette notion est
    physiquement applicable, notamment certains corps du Système solaire;
  - documenter clairement les définitions, les méthodes de calcul et les limites
    de chacune de ces dates;
  - éviter de fusionner dans une même colonne la séparation solaire maximale et
    la meilleure période d'observation;
  - ajouter des tests pour les objets éloignés de l'écliptique, pour lesquels
    les deux dates peuvent différer de plusieurs semaines.
- [ ] Ajouter, au début du rapport et avant la liste d'observation, un résumé
      de la Lune comprenant :
  - phase de la Lune;
  - illumination (%);
  - heure du lever de la Lune;
  - heure du coucher de la Lune.
- [ ] Ajouter, au début du rapport, deux résumés des conditions météo, l'un pour
      la soirée et l'autre pour la période précédant l'aube, comprenant chacun :
  - couverture nuageuse (%);
  - seeing (%);
  - transparence (%);
  - stabilité atmosphérique (%);
  - température (°C);
  - humidité (%);
  - vent (km/h);
  - risque de rosée;
  - risque de précipitation (%).
- [ ] Calculer le crépuscule et la séparation avec la Lune.
- [ ] Permettre la mise à jour contrôlée du catalogue.

## Moyen terme

- [ ] Intégrer VSX/AAVSO avec cache, provenance et gestion des pannes réseau.
- [ ] Ajouter les catalogues complets NGC/IC et d'autres familles d'objets.
- [ ] Prendre en compte la réfraction et un masque d'horizon local.
- [ ] Exporter des listes vers des télescopes intelligents.

## Long terme

- [ ] Ajouter une interface graphique ou web au-dessus du même moteur.
- [ ] Prédire les magnitudes lorsque des éphémérides fiables sont disponibles.
- [ ] Modéliser la météo, la pollution lumineuse et les caractéristiques de
      l'instrument.
