# Feuille de route

## Lot en cours — finalisation locale Caldwell et cadre open source

Périmètre : travailler exclusivement sur la copie locale. Aucun push, aucune
demande d'intégration distante, aucune fusion sur GitHub ni modification des
réglages distants. Le lot Caldwell et son cadre de développement sont déjà
implémentés dans l'arbre de travail; ce plan précède leur finalisation.

- [x] Examiner les changements présents et définir le périmètre local.
- [ ] Enregistrer ce plan dans un commit distinct avant les opérations suivantes.
- [ ] Relire le code, la provenance Caldwell et les contrôles de développement.
- [ ] Illustrer le tutoriel avec des images de l'architecture et du parcours de
      validation locale, clairement identifiées comme des schémas.
- [ ] Mettre à jour les consignes persistantes, les Markdown et les fichiers
      de distribution pour inclure les illustrations.
- [ ] Exécuter les tests et contrôles pertinents, puis consigner les résultats
      et leurs limites dans le tutoriel et le document de validation.
- [ ] Enregistrer séparément la fonctionnalité Caldwell et le cadre de
      développement/documentation dans des commits locaux cohérents.
- [ ] Vérifier l'historique et l'état final; préparer une synthèse de revue
      locale avec les opérations distantes explicitement différées.

## Lot suivant proposé — conception de l'archive météo

Ce lot n'est pas implémenté pendant la finalisation Caldwell. Son démarrage
demande un plan détaillé et un commit de planification préalables.

- [ ] Inventorier les données météo actuelles et leurs métadonnées disponibles.
- [ ] Définir les exigences de provenance, site, unités, qualité, heure de
      collecte, heure d'émission et heure de validité, sans confondre ces dates.
- [ ] Comparer les formats de stockage et documenter une décision avant de coder.
- [ ] Définir des exemples synthétiques et les tests d'intégrité/relecture.
- [ ] Planifier séparément chaque fournisseur supplémentaire et ses conditions
      d'utilisation; ne pas présumer un accès réseau pendant le travail local.

## Prochaine version

- [ ] Exporter les résultats en CSV et JSON.
- [x] Ajouter un paramètre en ligne de commande permettant d'exporter le rapport
      complet de la soirée d'observation dans un fichier texte (`.txt`).
- [x] Ajouter un paramètre en ligne de commande permettant d'exporter le rapport
      complet de la soirée d'observation dans un document PDF (`.pdf`).
- [ ] Ajouter la possibilité de fournir une liste d'objets dans un fichier afin
      de limiter strictement la recherche aux objets présents dans cette liste :
  - rechercher les formats normalisés ou couramment utilisés dans le monde pour
    échanger des listes d'objets ou des listes d'observation astronomiques;
  - étudier notamment VOTable, OpenAstronomyLog, ECSV, les formats CSV enrichis
    et les formats employés par les principaux logiciels d'astronomie;
  - comparer les formats selon leur statut normatif, leur interopérabilité, leur
    lisibilité, leur extensibilité, leur facilité de validation, leur prise en
    charge par Astropy et leur aptitude au fonctionnement hors ligne;
  - documenter les avantages, les limites et la compatibilité de chaque
    proposition sans retenir prématurément une solution;
  - choisir le format existant le mieux adapté après cette analyse ou, si aucun
    ne répond adéquatement au besoin, concevoir et versionner un format propre à
    GNU Astrolist;
  - définir seulement après ce choix le schéma des identifiants, alias, types
    d'objets et coordonnées facultatives;
  - ajouter ensuite un paramètre en ligne de commande pour charger ce fichier et
    appliquer la liste comme filtre aux catalogues sélectionnés;
  - prévoir la détection des doublons, des entrées invalides et des objets
    introuvables, ainsi que des exemples et des tests d'interopérabilité.
- [ ] Ajouter un mode « visible au début », « visible à la fin » ou « visible
      pendant toute la plage ».
- [ ] Ajouter les astéroïdes comme type d'objet, avec des éphémérides adaptées
      à leur déplacement et à leur magnitude variable.
- [x] Ajouter les 109 objets Caldwell comme type d'objet, hors ligne, avec
      provenance et prise en charge des magnitudes V absentes.
- [ ] Ajouter les nébuleuses planétaires comme type d'objet.
- [ ] Ajouter les amas ouverts comme type d'objet.
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
- [x] Ajouter, au début du rapport et avant la liste d'observation, un résumé
      de la Lune comprenant :
  - phase de la Lune;
  - illumination (%);
  - heure du lever de la Lune;
  - heure du coucher de la Lune.
- [x] Harmoniser les conventions lunaires avec celles des éphémérides publiées :
  - calculer le lever et le coucher à partir du bord supérieur apparent du
    disque lunaire plutôt qu'au passage géométrique de son centre à 0°;
  - intégrer une réfraction atmosphérique standard afin d'obtenir un lever plus
    tôt et un coucher plus tard, tout en documentant les paramètres retenus et
    leurs limites;
  - tenir compte du diamètre apparent variable de la Lune et ajouter des tests
    de comparaison avec des éphémérides de référence;
  - afficher explicitement l'instant auquel le pourcentage d'illumination est
    calculé et permettre une convention quotidienne comparable aux
    planificateurs, par exemple midi local, en plus du début de l'observation;
  - conserver l'illumination comme une grandeur géométrique indépendante de la
    réfraction : la convention du bord supérieur apparent s'applique uniquement
    aux heures de lever et de coucher.
- [x] Ajouter, au début du rapport, deux résumés des conditions météo, l'un pour
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

- [ ] Compléter les magnitudes V Caldwell à partir de sources scientifiques
      vérifiables, en distinguant bande, qualité et objet mesuré.
- [ ] Auditer progressivement les anciens fichiers Python pour leurs avis SPDX.
- [ ] Vérifier les protections GitHub et la CI distante avant publication.
- [ ] Définir un verrouillage reproductible des dépendances de livraison et
      une production de SBOM si des dépendances sont distribuées.

## Remise à niveau du cadre de développement

- [x] Consulter les conventions de gnu-astrophotography-recycle et gnu-apmg.
- [x] Documenter installation, architecture, tutoriel et portée de validation.
- [x] Ajouter gouvernance, DCO, confidentialité, sécurité et notices de licences.
- [x] Ajouter modèles d'issues/PR, CI Windows/Linux et mises à jour de dépendances.
- [x] Définir les contrôles de structure et du contenu des distributions.
- [x] Exécuter et consigner les vérifications finales locales du lot.

Les premiers changements Caldwell avaient commencé avant l'élargissement du lot
à ce cadre de développement. Les prochains lots suivent le plan préalable et
les commits de planification décrits dans AGENTS.md.

## Évolutions des données

- [ ] Intégrer VSX/AAVSO avec cache, provenance et gestion des pannes réseau.
- [ ] Ajouter les catalogues complets NGC/IC et d'autres familles d'objets.
- [ ] Prendre en compte la réfraction et un masque d'horizon local.
- [ ] Exporter des listes vers des télescopes intelligents.

## Long terme

- [ ] Ajouter une interface graphique ou web au-dessus du même moteur.
- [ ] Prédire les magnitudes lorsque des éphémérides fiables sont disponibles.
- [ ] Modéliser la météo, la pollution lumineuse et les caractéristiques de
      l'instrument.
