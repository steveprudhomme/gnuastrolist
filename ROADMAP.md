# Feuille de route

## Finalisation PR nº 6 — tests Windows et tutoriel accessible

- [x] Identifier le refus d'export Windows : code sur D:, fausses archives
      pytest sur C:, donc protection correcte de tout le volume C:.
- [x] Enregistrer ce plan avant le correctif.
- [x] Placer les fichiers temporaires de la CI dans le dossier de travail
      pour tester les copies locales sur le même volume, sans affaiblir la protection.
- [x] Ajouter un test explicite de protection d'un volume Windows distinct.
- [x] Ajouter un parcours débutant lisible à 10 ans, une image simple et les
      consignes persistantes de documentation; actualiser les MD concernés.
- [x] Vérifier les tests locaux : 90 réussis, un ignoré, dix avertissements IERS.

Plan préalable : `de320c5`. Les cinq nouveaux contrôles GitHub doivent réussir
avant la fusion autorisée. Le résultat et l'état final de fusion sont consultables
dans la PR nº 6; les résultats de la première CI ne valent pas validation de ce correctif.

## Lot Seestar S50 — présence dans les archives en lecture seule

- [x] Examiner le code et la racine MyWorks autorisée, sans écriture externe.
- [x] Enregistrer le plan avant le développement.
- [x] Ajouter `--seestar-path CHEMIN` et un inventaire des acquisitions locales
      uniquement en lecture; ignorer les liens/jonctions et gérer les erreurs
      d'accès sans transformer une vérification incomplète en absence certaine.
- [x] Identifier les objets par noms de catalogue explicites dans les fichiers
      d'acquisition; utiliser les correspondances Messier/Caldwell/NGC
      connues, sans rapprochement arbitraire par position ou nom courant.
- [x] Distinguer archive trouvée, aucune archive trouvée et vérification
      incomplète. La présence d'un fichier n'atteste pas la qualité ou l'achèvement
      scientifique d'une photographie; un dossier vide ne suffit pas.
- [x] Ajouter le statut aux rapports écran, TXT et PDF; préserver les sorties
      existantes sans cette option. Interdire les rapports/caches sous la racine
      protégée, y compris via des liens ou le dossier courant.
- [x] Tester identifiants et alias, faux positifs, dossiers vides, erreurs,
      liens et absence d'écriture. Utiliser des archives synthétiques locales.
- [x] Documenter les limites, la confidentialité et la procédure dans les MD
      et le tutoriel illustré; vérifier les archives et committer localement.

Plan préalable : `a52ad62`. Résultats locaux : 89 tests réussis, un test de lien
symbolique ignoré par manque de permission Windows, dix avertissements IERS.
Les jonctions sont vérifiées séparément sur attributs synthétiques. Le scanner
réel a été essayé uniquement en lecture; les rapports restent dans `local/`.
Ruff, structure, distributions et installation hors des sources vérifiés.
Aucune publication distante ni donnée d'acquisition personnelle dans le dépôt.

## Lot multicatalogue — ligne de commande locale

- [x] Définir les conventions et le périmètre, sans publication distante.
- [x] Enregistrer le plan avant le développement.
- [x] Accepter plusieurs noms après `--objects` et plusieurs occurrences de
      cette option, en normalisant les alias et répétitions de catalogues.
- [x] Combiner les catalogues et dédoublonner les objets du ciel profond par
      désignation de catalogue explicite, jamais par simple proximité angulaire.
      Priorité stable : Messier, Caldwell, NGC; conserver les noms secondaires.
- [x] Préserver le filtre par défaut des variables (V max 8), même en sélection
      mixte; les catalogues du ciel profond restent sans limite par défaut.
      Une limite explicite ou `--all-magnitudes` s'applique à tous.
- [x] Adapter les rapports terminal/TXT/PDF : catalogues, alias, conventions
      photométriques et provenance par valeur, sans modifier les commandes simples.
- [x] Tester répétitions, alias, recouvrements réels, composants distincts,
      filtres mixtes et exports hors ligne; exécuter les contrôles locaux.
- [x] Mettre à jour les MD et le tutoriel avec un schéma et un exemple réel;
      vérifier les archives et enregistrer les commits locaux.

Plan préalable : `02b5c55`. Validation locale : 75 tests réussis; huit
avertissements IERS connus; Ruff, liens et distributions contrôlés. La commande
installée a été exécutée hors des sources. Aucune publication distante du lot.

## Lot NGC — intégration locale

- [x] Examiner le chargement des catalogues et définir le périmètre.
- [x] Enregistrer le plan dans un commit avant le développement.
- [x] Examiner la copie OpenNGC locale déjà utilisée pour Caldwell : empreinte,
      types, entrées composées, doublons, objets inexistants et valeurs absentes.
- [x] Construire un catalogue NGC reproductible depuis ce fichier, en excluant
      IC, doublons et objets inexistants; conserver les composants identifiés
      distinctement et les coordonnées exploitables, sans inventer de magnitude V.
- [x] Ajouter `--objects ngc`, le chargement local, les libellés et notes TXT/PDF,
      sans limite de magnitude par défaut.
- [x] Tester le générateur, des identifications de référence, les filtres et
      les exports hors ligne; vérifier le contenu des distributions.
- [x] Documenter source, licence, conventions et limites; mettre à jour les MD
      et ajouter un schéma NGC dans le tutoriel.
- [x] Exécuter les contrôles locaux, reconstruire les archives et enregistrer
      le lot dans des commits locaux; aucune publication distante dans ce lot.

Plan préalable : `3651c6e`. Résultats : 65 tests réussis, Ruff et contrôles de
structure/distribution réussis, essai de la wheel hors des sources réussi.
Les 4 592 magnitudes V absentes restent explicites. La validation CI distante
du lot NGC reste à effectuer lors d'une publication ultérieure autorisée.

## Correctif avant fusion — autonomie du test de tri Caldwell

- [x] Identifier l'échec Python 3.10 dans la CI : le test de tri utilise une
      date hors couverture IERS sans définir sa propre politique hors ligne.
- [x] Enregistrer ce plan avant le correctif.
- [x] Configurer temporairement IERS dans ce test, sans dépendre des tests CLI
      précédents ni modifier durablement les paramètres astronomiques.
- [x] Documenter le correctif dans le tutoriel, la validation et le journal.
- [x] Exécuter le test isolé et les contrôles locaux : 61 tests réussis.
- [x] Confirmer la nouvelle CI Windows/Linux et la distribution sur GitHub.

Le correctif IERS a passé les cinq contrôles et la PR nº 1 a été fusionnée
dans main au commit `79724f3`, avant le démarrage du lot NGC.

La fusion de la PR nº 1 est autorisée par l'utilisateur et doit suivre la
réussite des cinq contrôles. Son état final est consultable dans GitHub.

## Lot en cours — finalisation locale Caldwell et cadre open source

Périmètre : travailler exclusivement sur la copie locale. Aucun push, aucune
demande d'intégration distante, aucune fusion sur GitHub ni modification des
réglages distants. Le lot Caldwell et son cadre de développement sont déjà
implémentés dans l'arbre de travail; ce plan précède leur finalisation.

- [x] Examiner les changements présents et définir le périmètre local.
- [x] Enregistrer ce plan dans un commit distinct avant les opérations suivantes.
- [x] Relire le code, la provenance Caldwell et les contrôles de développement.
- [x] Illustrer le tutoriel avec des images de l'architecture et du parcours de
      validation locale, clairement identifiées comme des schémas.
- [x] Mettre à jour les consignes persistantes, les Markdown et les fichiers
      de distribution pour inclure les illustrations.
- [x] Exécuter les tests et contrôles pertinents, puis consigner les résultats
      et leurs limites dans le tutoriel et le document de validation.
- [x] Enregistrer séparément la fonctionnalité Caldwell et le cadre de
      développement/documentation dans des commits locaux cohérents.
- [x] Vérifier l'historique et l'état final; préparer une synthèse de revue
      locale avec les opérations distantes explicitement différées.

Historique local vérifié : plan `f737e4d`, fonctionnalité `8015cc8`, cadre de
développement et tutoriel illustré `f308106`. L'arbre de travail était propre
après ces trois commits. La clôture documentaire consigne ce résultat.

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
- [x] Ajouter les entrées NGC exploitables d'OpenNGC, composants distincts inclus.
- [ ] Ajouter le catalogue IC et d'autres familles d'objets.
- [ ] Prendre en compte la réfraction et un masque d'horizon local.
- [ ] Exporter des listes vers des télescopes intelligents.

## Long terme

- [ ] Ajouter une interface graphique ou web au-dessus du même moteur.
- [ ] Prédire les magnitudes lorsque des éphémérides fiables sont disponibles.
- [ ] Modéliser la météo, la pollution lumineuse et les caractéristiques de
      l'instrument.
