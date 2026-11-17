# Feuille de route

## Améliorations approuvées après l'audit ECC — 17 novembre 2026

Les neuf suggestions de l'audit local de `main` au commit `db2f48b` sont
approuvées par le propriétaire. Leurs identifiants permanents sont **ECC-A à
ECC-I**. Ce plan est enregistré avant toute implémentation; les cases restent
ouvertes tant que leurs critères ne sont pas vérifiés.

**Prochaine étape de développement : utiliser ECC pour réaliser ECC-D —
environnement et livraison reproductibles.** ECC-A est fusionné dans `main` par la
[PR nº 9](https://github.com/steveprudhomme/gnuastrolist/pull/9), commit `1d75522`.
ECC-B est publié dans la [PR nº 10](https://github.com/steveprudhomme/gnuastrolist/pull/10),
avec cinq contrôles réussis sur le correctif; sa fusion reste distincte.
ECC-C est publié dans la [PR nº 11](https://github.com/steveprudhomme/gnuastrolist/pull/11),
basée sur ECC-B. Ses cinq contrôles ont réussi sur le correctif; intégrer ECC-B
avant de revoir la base et de fusionner ECC-C dans `main`.
Choisir le premier lot incomplet
dans l'ordre ECC-A, ECC-B, ECC-C, ECC-D, ECC-E, ECC-F, ECC-G, ECC-H, ECC-I.
À chaque demande de prochaine étape, préciser explicitement l'usage d'ECC et
l'identifiant du lot, en tenant compte des cases réellement terminées.

La [méthode de développement ECC](docs/DEVELOPPEMENT_ECC.md) décrit le contexte,
les contrôles communs et les limites de cet accord. Les lots ECC-D à ECC-I
prolongent certaines tâches existantes : conserver les renvois et éviter de
compter deux fois le même travail. Les lots ci-dessous concernent le
développement local; ils n'autorisent pas, à eux seuls, une publication ou une
modification GitHub. Les instructions particulières de publication ECC-A,
ECC-B et ECC-C sont consignées ci-dessous; toute fusion reste distincte.

### ECC-A — Préserver les entrées et fiabiliser les exports — priorité haute

Plan d'exécution détaillé, à committer et publier **avant les tests nouveaux
et le code**, selon l'instruction du propriétaire du 17 novembre 2026 :

- [x] ECC-A.0 — Publier le commit de ce plan sur la branche dédiée et vérifier
      son empreinte distante avant toute implémentation.
- [x] ECC-A.1a — Centraliser le contrôle des sept entrées locales : configuration,
      orbites astéroïdes/comètes, observations CBAT, éléments GP, SATCAT et UNOOSA.
      Contrôler les destinations TXT/PDF entre elles, les ressources du logiciel
      et le cache utilisé; refuser collisions résolues et identités physiques.
- [x] ECC-A.1b — Effectuer ces contrôles avant actualisation, météo et calculs,
      puis avant publication de chaque rapport. Refuser sorties liées/jonctions,
      fichiers spéciaux et parents invalides; conserver la protection Seestar.
- [x] ECC-A.2a — Refuser par défaut un rapport existant. Ajouter `--overwrite`
      pour autoriser explicitement le remplacement des seuls rapports ordinaires;
      cette option ne contourne ni les entrées, ni le cache, ni les archives.
- [x] ECC-A.2b — Écrire TXT et PDF dans un fichier temporaire du dossier de
      destination, puis publier chaque fichier atomiquement après validation.
      En cas d'échec d'écriture ou de publication, préserver son ancien rapport
      et nettoyer le temporaire. Empêcher l'écrasement concurrent sans autorisation.
      L'atomicité porte sur chaque fichier, pas sur la paire TXT/PDF.
- [x] ECC-A.3a — Écrire d'abord les régressions ECC : sept entrées × deux sorties,
      collisions TXT/PDF, chemins relatifs et alias, liens physiques et jonctions,
      refus avant effets, remplacement explicite et pannes d'écriture/publication.
      Utiliser uniquement des fichiers et archives synthétiques sur le disque local.
- [x] ECC-A.3b — Vérifier terminal/TXT/PDF, protections USB simulées, tests complets,
      Ruff, liens, contenu des distributions et installation hors des sources;
      inspecter le schéma et un rapport PDF de démonstration.
- [x] ECC-A.3c — Mettre à jour README, CHANGELOG, architecture, guides Seestar,
      développement ECC et validation; expliquer le remplacement dans le tutoriel
      dès 10 ans avec une image SVG versionnée. Publier code et documents sur la
      branche dédiée et ouvrir une PR; la fusion de cette PR reste une étape distincte.

Suivi ECC-A : plan `8276bb4` publié avant code, correctif `f37c3c0`, PR nº 9.
Validation locale : 385 tests réussis, trois ignorés, 26 avertissements connus;
Ruff, liens, distributions et installation hors des sources réussis. Les
résultats distants sont consignés séparément dans [VALIDATION.md](docs/VALIDATION.md).

Méthodes ECC : `python-testing` (régression avant correctif), `python-patterns`
(contrôles partagés), `security-review` (destinations/entrées/USB) et
`verification-loop` (validation finale). Cette instruction autorise la publication
du plan et des changements ECC-A, en conservant le développement sur la copie locale.

- [x] ECC-A.1 — Recenser tous les fichiers d'entrée et de sortie; refuser
      entrée=sortie et TXT=PDF avant tout effet, avec chemins relatifs, chemins
      résolus et identités de fichiers/liens applicables.
- [x] ECC-A.2 — Rendre le TXT atomique, définir une politique explicite de
      remplacement des rapports et préserver les entrées et anciens rapports
      en cas d'erreur. Préserver toutes les protections Seestar.
- [x] ECC-A.3 — Ajouter les régressions du cas configuration=export et des
      collisions/échecs d'écriture avec sources synthétiques; vérifier les
      résultats terminal, TXT et PDF, puis documenter dans le tutoriel illustré.

### ECC-B — Fiabiliser les données météo — priorité haute

Suivi : plan `af9a639` publié avant code, correctif `3a17ac2`,
[PR nº 10](https://github.com/steveprudhomme/gnuastrolist/pull/10).
Validation locale : 456 tests réussis, trois ignorés, 27 avertissements IERS/ERFA;
Ruff, liens, archives et essais installés hors des sources réussis. Les cinq
contrôles GitHub du correctif ont réussi; voir [VALIDATION.md](docs/VALIDATION.md).

Plan détaillé demandé le 17 novembre 2026, à committer et publier avant les
nouveaux tests et le code. Méthodes ECC : `python-testing`, `python-patterns`,
`security-review` et `verification-loop`, adaptées à Python/Windows.

- [x] ECC-B.0 — Publier ce plan sur une branche dédiée et vérifier l'empreinte
      distante avant toute implémentation. ECC-A est désormais fusionné dans
      `main` par la PR nº 9; conserver ses protections d'export.
- [x] ECC-B.1a — Borner les réponses HTTP météo à 2 Mio et les séries à
      1 000 échantillons; valider JSON, structures, types numériques, valeurs
      finies, domaines et unités lorsqu'elles sont fournies. Normaliser les
      erreurs de transport/données attendues sans capturer toutes les exceptions.
- [x] ECC-B.1b — Valider les horodatages, les instants distincts et les longueurs
      de séries. Conserver les décalages UTC explicites; refuser les heures civiles
      impossibles ou ambiguës plutôt que leur inventer un instant. Garder des
      périodes de repli signalées si les horaires solaires manquent.
- [x] ECC-B.2a — Conserver les mesures par instant et calculer la rosée seulement
      sur les triplets température/point de rosée/humidité complets. Ne plus
      rapprocher les listes après suppression indépendante de leurs valeurs nulles.
- [x] ECC-B.2b — Conserver les variables valides indépendantes, signaler les
      données partielles et ne pas fabriquer de moyenne ni risque faible en
      l'absence de mesures. Une série de longueur incohérente est écartée,
      jamais tronquée silencieusement; les valeurs invalides isolées sont omises.
- [x] ECC-B.2c — Isoler les deux fournisseurs et les deux périodes; une panne
      météo ne doit pas supprimer la liste astronomique ni les données valides
      de l'autre source. Reconnaître la disponibilité de toute variable affichable,
      même sans nuages ni seeing. Préserver l'interdiction réseau de `--offline`.
- [x] ECC-B.3a — Écrire d'abord les régressions : seeing nul, rosée désalignée,
      JSON/structures invalides, valeurs non finies ou hors domaine, unités,
      séries incohérentes, dates/décalages/DST, doublons, tailles limites et pannes.
      Vérifier aussi qu'une erreur de programmation inattendue reste visible.
- [x] ECC-B.3b — Tester terminal/TXT/PDF avec prévisions synthétiques partielles
      et indisponibles, vérifier les catalogues et protections ECC-A, puis exécuter
      suite complète, Ruff, liens, construction et installation hors des sources.
- [x] ECC-B.3c — Actualiser README, CHANGELOG, architecture, guides de validation
      et développement ECC. Ajouter un guide météo et un tutoriel illustré dès
      10 ans expliquant mesures manquantes, avertissements et périodes de repli.
      Publier code et MD, ouvrir une PR et vérifier ses cinq contrôles; la fusion
      dans `main` reste une opération distincte. Aucun essai sur le disque USB réel.

L'instruction du propriétaire autorise la publication du plan et des changements
ECC-B développés dans la copie locale. L'archive météo, les nouveaux fournisseurs,
les nouveaux catalogues et les réglages GitHub restent hors de ce lot.

- [x] ECC-B.1 — Valider structures, types, nombres finis et domaines des
      réponses Open-Meteo/7Timer; borner leur taille et gérer les erreurs de
      données sans masquer les erreurs de programmation.
- [x] ECC-B.2 — Aligner température, point de rosée et humidité par instant;
      calculer la rosée sur les mesures compatibles et signaler les données
      partielles, sans associer des heures différentes.
- [x] ECC-B.3 — Tester au moins quatre cas dégradés : seeing nul, valeurs
      manquantes décalées, structure invalide et réponse trop grande; conserver
      la liste astronomique lorsqu'un fournisseur échoue. Documenter les
      avertissements et le tutoriel. L'archive météo reste un lot distinct.

### ECC-C — Valider les paramètres avant traitement — priorité haute

Suivi : plan `d9545c5` publié avant code, correctif `3eb2da9`,
[PR nº 11](https://github.com/steveprudhomme/gnuastrolist/pull/11) dépendante
de la PR nº 10. Validation locale : 564 tests réussis, trois ignorés,
27 avertissements IERS/ERFA; Ruff, liens, archives et essais installés réussis.
Les cinq contrôles GitHub du correctif ont réussi; voir
[VALIDATION.md](docs/VALIDATION.md). Aucune fusion n'a été effectuée pour ce lot.

Plan détaillé du 17 novembre 2026, à committer et publier avant les nouveaux
tests et le code. ECC-B (PR nº 10) n'étant pas encore fusionné, ECC-C part de
sa branche publiée; sa PR visera cette branche tant que la dépendance reste
ouverte. Aucune fusion d'ECC-B ou ECC-C n'est autorisée par ce lot.

- [x] ECC-C.0 — Publier le commit du plan et vérifier son empreinte distante
      avant toute implémentation; utiliser les méthodes ECC `python-testing`,
      `python-patterns`, `security-review` et `verification-loop`.
- [x] ECC-C.1a — Centraliser les nombres finis et domaines : latitude ±90°,
      longitude ±180°, azimuts 0–360°, hauteurs de champ 0–90°, Soleil ±90°,
      site terrestre de −1 000 à 10 000 m et magnitude finie sans borne imposée.
      Refuser aussi booléens et types non numériques dans les API numériques.
- [x] ECC-C.1b — Définir un pas représentable de 1 microseconde à 24 heures,
      partagé par les moteurs, et compter exactement les instants en UTC,
      bornes incluses : 2 000 au maximum pour les objets fixes/petits corps,
      20 000 pour les satellites. Refuser avant allocation les budgets dépassés;
      respecter les durées réelles lors des changements d'heure.
- [x] ECC-C.1c — Valider les âges positifs et finis, bornés par les jours
      représentables de `timedelta`, ainsi que clés, types et priorité des réglages
      CLI/JSON. Refuser les booléens JSON, chemins de cache vides et valeurs invalides
      avant d'appeler l'actualisation des catalogues.
- [x] ECC-C.2a — Effectuer le précontrôle CLI des nombres, du calendrier, du champ,
      des budgets et de la configuration avant mise à jour IERS, actualisation,
      météo, calculs et exports. Conserver les protections de destinations ECC-A.
- [x] ECC-C.2b — Réutiliser les contrôles dans les API des objets fixes, petits
      corps, satellites et Lune, même sur une liste d'objets vide. Conserver les
      messages utilisateur en français et ne pas masquer les erreurs inattendues.
- [x] ECC-C.3a — Écrire d'abord les régressions : NaN/infini, pas 1e-20 minute,
      valeurs extrêmes, limites exactes et dépassements, fenêtres invalides/DST,
      configuration invalide et preuve d'absence d'appel aux opérations à effets.
- [x] ECC-C.3b — Vérifier commandes valides, terminal/TXT/PDF, préservation des
      rapports/archives synthétiques, tests complets, Ruff, liens, distributions
      et installation hors des sources. Aucun essai sur le disque USB réel.
- [x] ECC-C.3c — Actualiser README, CHANGELOG, architecture, validation et guide
      ECC; ajouter un guide des paramètres et un schéma dans le tutoriel dès
      10 ans. Publier le code et les MD, ouvrir la PR dépendante d'ECC-B et vérifier
      ses cinq contrôles; consigner la dépendance avant toute fusion éventuelle.

Ce précontrôle porte sur les paramètres et la configuration. La validité
scientifique et le contenu des fichiers de catalogues restent contrôlés par
leurs lecteurs/moteurs. L'instruction du propriétaire autorise la publication
du plan et du lot ECC-C développés localement, sans installation de service
externe, réglage GitHub ni fusion distante.

- [x] ECC-C.1 — Définir les domaines des flottants par paramètre et refuser
      NaN/infini, pas nul après conversion et budgets d'échantillonnage dépassés.
- [x] ECC-C.2 — Effectuer ces contrôles avant réseau, cache et export;
      vérifier chaque famille de moteur et les entrées de configuration.
- [x] ECC-C.3 — Tester notamment les pas infini et 1e-20 minute; produire des
      erreurs utilisateur lisibles et documenter les limites dans le tutoriel.

### ECC-D — Environnement et livraison reproductibles — priorité haute

## Exécution autonome approuvée ECC-D à ECC-I — 17 novembre 2026

Le propriétaire demande de réaliser les six lots, avec plan commité et publié
avant code, puis tests, tutoriel illustré et publication à chaque lot. Le travail
part d'ECC-C (`bd53ad3`), dont la PR nº 11 dépend encore d'ECC-B (PR nº 10).
La nouvelle PR visera ECC-C tant que ces dépendances ne sont pas intégrées.
Aucune fusion distante ni modification des protections GitHub n'est incluse.

- [ ] ECC-DI.0 — Publier ce plan détaillé et vérifier son empreinte distante
      avant tests nouveaux, dépendances de développement et code.
- [ ] ECC-DI.1 — Employer les méthodes ECC de tests Python, revue de sécurité,
      architecture et vérification. Répartir exploration/implémentation/revue
      indépendantes en copies locales distinctes lorsque cela réduit les angles
      morts; conserver au pilote les décisions et l'intégration.
- [ ] ECC-D.4 — Ajouter NumPy directement, un environnement de développement
      isolé sans paquets système et des verrous avec versions/empreintes pour
      Windows/Linux, Python 3.10/3.13. Installer seulement les outils et dépendances
      nécessaires dans les environnements locaux du projet, jamais globalement.
- [ ] ECC-D.5 — Ajouter une reconstruction des verrous avec outil de résolution
      versionné, contrôler l'environnement installé, les archives et les dix
      sélections hors ligne; produire un inventaire de dépendances avec licences
      et empreintes des distributions sans prétendre signer une livraison.
- [ ] ECC-E.4 — Mesurer la couverture des lignes et branches; choisir un plancher
      initial démontré et des objectifs renforcés sur les chemins critiques.
      Compléter des régressions utiles si nécessaire, pas des tests miroirs.
- [ ] ECC-E.5 — Ajouter typage progressif sur les composants contrôlables,
      contrôles Ruff pertinents, vérification des dépendances et recherche de
      secrets sans afficher leur contenu. Borner la durée des jobs et utiliser
      les verrous dans la CI Windows/Linux 3.10/3.13. Distinguer examen local et
      audit en ligne actualisé; ne pas désactiver un contrôle pour obtenir du vert.
- [ ] ECC-F.4 — Ajouter un verrou interprocessus du cache couvrant lecture,
      autorisation, requête et activation; réentrance et libération après panne.
      Les modes never/offline ne créent ni état ni verrou; les règles CelesTrak
      restent applicables sous deux processus concurrents.
- [ ] ECC-F.5 — Ajouter une commande locale de rétention du cache, simulation
      par défaut, application explicite, conservation d'au moins une génération
      valide par famille, refus des chemins liés, inconnus ou protégés Seestar.
      Tester concurrence, arrêt brutal et rétention uniquement sur copies synthétiques.
- [ ] ECC-G.4 — Introduire un service d'application et un objet de rapport
      partagé sans casser CLI/TXT/PDF; déplacer les formats communs derrière
      une API publique plutôt que les imports de fonctions privées entre rendus.
- [ ] ECC-G.5 — Restaurer le contexte IERS après succès et erreur, avec tests
      d'appels successifs, erreurs et ressources. Documenter une décision
      d'architecture avant intégration du changement et conserver les contrôles
      numériques et de destinations ECC-A/C.
- [ ] ECC-H.4 — Ajouter des références gelées de positions satellitaires
      topocentriques calculées par une chaîne indépendante de la transformation
      Astropy actuelle (ex. Skyfield), à partir de sources publiques licenciées.
      Fournir générateur, versions, dates, conventions, empreintes et tolérances;
      ne pas présenter ces calculs comme des observations réelles.
- [ ] ECC-H.5 — Ajouter des mesures reproductibles temps/mémoire des catalogues
      combinés, satellites, rapports et inventaires Seestar synthétiques, avec
      budgets raisonnés d'après la mesure et contrôles non instables en CI.
      Les tests ordinaires restent entièrement hors réseau.
- [ ] ECC-I.6 — Réconcilier les tâches réalisées et leurs renvois ECC; compléter
      les avis SPDX des fichiers originaux vérifiés sans inventer de titulaires.
      Vérifier les notices des données sans leur attribuer de nouvelle licence.
- [ ] ECC-I.7 — Actualiser confidentialité (fournisseurs/cache/rapports), User-Agent
      issu de la version, gouvernance et livraison des dix catalogues. Examiner
      les anciens rapports suivis sans publier leur contenu; remplacer leur
      rôle d'exemple par des fichiers synthétiques documentés. Ne pas réécrire
      l'historique, fabriquer de signature ou prétendre qu'un canal privé est actif.
- [ ] ECC-DI.2 — À chaque lot : mettre à jour README, CHANGELOG, ROADMAP et
      guides concernés, ajouter un schéma au tutoriel dès 10 ans, exécuter les
      contrôles pertinents, consigner les résultats, committer et publier la branche.
- [ ] ECC-DI.3 — Terminer par revue indépendante, suite complète, typage,
      couverture, audits, archives et installation hors des sources; inspecter
      les schémas et un PDF. Publier une PR détaillée ciblant ECC-C et vérifier
      tous les contrôles distants du dernier commit avant de conclure.

L'instruction autorise ces installations locales nécessaires et la publication
des six lots, mais aucun service externe permanent, réglage GitHub ou fusion.
Les accès en ligne servent uniquement aux dépendances, références publiques,
audits de versions et publication autorisée; aucun inventaire Seestar n'est transmis.
Le disque USB réel ne sera ni parcouru ni modifié.

### ECC-D — Critères initiaux conservés

- [ ] ECC-D.1 — Créer un environnement neuf sans paquets système et obtenir
      un contrôle des dépendances réussi, indépendant des autres logiciels.
- [ ] ECC-D.2 — Déclarer NumPy comme dépendance directe et définir des
      contraintes/verrous adaptés aux plateformes et versions Python prises
      en charge, avec procédure de mise à jour documentée.
- [ ] ECC-D.3 — Construire et contrôler les archives; installer la wheel
      hors des sources et exercer les dix sélections et exports hors ligne.
      Actualiser les guides; prolonger la tâche de verrouillage et de SBOM
      conditionnel déjà prévue, sans créer de doublon.

### ECC-E — Renforcer les vérifications automatiques — priorité moyenne

- [ ] ECC-E.1 — Mesurer couverture et branches, puis fixer des objectifs
      justifiés sur les chemins critiques et les régressions de l'audit.
- [ ] ECC-E.2 — Introduire progressivement contrôle des types et règles Ruff
      pertinentes, sans réécriture générale ni tests miroirs de l'implémentation.
- [ ] ECC-E.3 — Préparer contrôles de dépendances/secrets, durées CI bornées
      et matrice cohérente avec le support Python annoncé; documenter les
      commandes et distinguer contrôles locaux et résultats distants exécutés.

### ECC-F — Coordonner et maîtriser les caches — priorité moyenne

- [ ] ECC-F.1 — Protéger par verrou interprocessus la transaction de lecture,
      autorisation, requête et écriture de l'état fournisseur partagé.
- [ ] ECC-F.2 — Tester deux commandes simultanées et une interruption avec
      fournisseur simulé; vérifier délais, blocages et repli sans requête réelle.
- [ ] ECC-F.3 — Définir une rétention configurable avec simulation de purge,
      conservation du dernier cache valide et protections Seestar; documenter
      son usage dans le tutoriel illustré et le guide des actualisations.

### ECC-G — Séparer orchestration, rapport et contexte — priorité moyenne

- [ ] ECC-G.1 — Définir un service d'application testable et un modèle de
      rapport partagé; documenter la décision avant une refactorisation ciblée.
- [ ] ECC-G.2 — Réduire les dépendances aux fonctions privées entre rendus
      et restaurer le contexte IERS après succès ou erreur.
- [ ] ECC-G.3 — Préserver CLI, TXT et PDF par les tests existants et les
      régressions nécessaires; mettre à jour le schéma d'architecture et les
      guides concernés sans surcharger le parcours débutant.

### ECC-H — Validation scientifique et performances — priorité moyenne

- [ ] ECC-H.1 — Étendre les références externes, notamment des passages
      satellitaires complets, avec site, époque, conventions, empreintes et
      tolérances; conserver les références Horizons, USNO et Vallado existantes.
- [ ] ECC-H.2 — Vérifier limites temporelles et d'échantillonnage; mesurer
      temps/mémoire des catalogues combinés, satellites, rapports volumineux
      et grands inventaires Seestar synthétiques, puis fixer des budgets mesurés.
- [ ] ECC-H.3 — Documenter précision, avertissements et limites, avec exemples
      illustrés; ne pas présenter les tests comme une garantie de détection
      ou une validation observationnelle exhaustive.

### ECC-I — Documentation et pratiques open source — priorité moyenne

- [ ] ECC-I.1 — Réconcilier les tâches déjà réalisées (astéroïdes et mises à
      jour contrôlées notamment), conserver l'historique et relier les dettes
      de SPDX, dépendances et livraison aux lots ECC correspondants.
- [ ] ECC-I.2 — Étendre la checklist de livraison aux dix sélections, maintenir
      un parcours débutant court avec images versionnées et séparer le journal
      technique des instructions utilisateur.
- [ ] ECC-I.3 — Actualiser la confidentialité pour les fournisseurs de
      catalogues et harmoniser le User-Agent avec la version du paquet.
- [ ] ECC-I.4 — Vérifier les avis SPDX avec titulaires réels, attributions
      et conditions des données; examiner les anciens rapports suivis et la
      portée d'une revue de secrets/historique sans publier de données privées.
- [ ] ECC-I.5 — Consigner les contrôles de gouvernance et sécurité restant
      à vérifier sur GitHub; différer les opérations distantes jusqu'à instruction
      explicite et ne jamais fabriquer d'attestation ou de signature.

## Correctif de publication — dates GP sous Python 3.10, PR nº 7

- [x] Identifier dans la CI l'échec de validation des fractions de seconde longues.
- [x] Valider le calendrier sans imposer les limites de fractions de `datetime`
      3.10; transmettre l'époque complète à Astropy sans altérer les données.
- [x] Vérifier les différentes longueurs de fraction et les quatre plateformes
      Python/OS avant de fusionner la PR; documenter le résultat de publication.

Correctif `9cc0d57` : 350 tests locaux réussis, un ignoré. Les cinq contrôles
de la PR nº 7 ont réussi sur GitHub, dont Windows/Linux en Python 3.10 et 3.13
et la construction des distributions.

## Lot satellites artificiels et débris — COSPAR, SATCAT et registre ONU

- [x] Examiner les sources officielles et distinguer identification, registre
      administratif et éléments orbitaux nécessaires aux passages.
- [x] Enregistrer ce plan avant le développement.
- [x] Vérifier les formats, les droits et l'accès CelesTrak/SATCAT/UNOOSA;
      conserver les réponses locales et leurs empreintes sans copier de contenu protégé.
- [x] Ajouter des sélections satellites et débris, avec numéros SATCAT/NORAD
      étendus et identifiants internationaux COSPAR; conserver les types et objets distincts.
- [x] Lire les éléments GP en JSON/OMM, propager avec SGP4 dans le repère TEME,
      calculer Alt/Az topocentriques avec un pas adapté et une limite d'âge explicite.
- [x] Distinguer présence géométrique, éclairage solaire et visibilité optique;
      ne pas inventer de magnitude, de date saisonnière ni de calcul de collision.
- [x] Relier SATCAT et les informations du registre UNOOSA par identifiants exacts;
      documenter le format d'import local si aucun export officiel exploitable n'est validé.
- [x] Intégrer sélections mixtes, rapports écran/TXT/PDF et identités Seestar
      explicites, toujours sans écriture sur les archives sources.
- [x] Étendre les actualisations configurables aux éléments satellitaires et
      métadonnées disponibles; préserver cache atomique, repli et mode hors ligne.
- [x] Tester les parseurs, époques, coniques SGP4 de référence, repères, filtres,
      identités, données absentes, mises à jour et exports hors réseau.
- [x] Mettre à jour les MD, le tutoriel illustré accessible dès 10 ans, les
      paquets et les vérifications locales avant le commit final, sans push.

Plan préalable : 764f819. Copie GP/SATCAT partielle et import UNOOSA local réalisés;
les limites et les sources sont documentées dans docs/SATELLITES.md.

COSPAR est une désignation d'objet; SATCAT décrit les objets suivis; le registre
ONU est administratif. Aucun de ces deux derniers ne remplace à lui seul une
éphéméride à jour. Le périmètre réel des copies et les sources indisponibles
devront être clairement annoncés.

## Lot actualisation configurable au démarrage — toutes les sources évolutives

Demande du 2026-11-17, implémentée localement. Modes et délais sont décrits
dans docs/CATALOG_UPDATES.md. Plans préalables : 051be12 puis d35bc21.

- [x] Enregistrer le plan de ce lot avant son implémentation.
- [x] Couvrir GCVS, OpenNGC (Messier/Caldwell/NGC), compléments SIMBAD,
      HYG (Bayer/Flamsteed), orbites JPL astéroïdes et MPC comètes. Traiter
      CBAT comme observations locales tant qu'aucun accès structuré n'est validé,
      et afficher explicitement cette limite plutôt qu'annoncer une mise à jour fictive.
- [x] Rendre les générateurs réutilisables depuis le paquet installé, sans
      dépendre du répertoire scripts du dépôt; préserver les commandes existantes.
- [x] Définir une politique par source : âge maximal réglable, proposition
      initiale de 24 h pour les comètes; ne pas confondre date de téléchargement
      et époque orbitale ni imposer la même cadence aux catalogues fixes.
- [x] Proposer une option de démarrage « jamais / si périmé / forcé », et des
      délais par catalogue; documenter leur priorité sur une configuration locale.
- [x] Faire de `--offline` une interdiction absolue de téléchargement, même en
      présence d'une demande de mise à jour forcée; expliquer la combinaison.
- [x] Conserver les ressources embarquées intactes; télécharger seulement dans
      un cache local au logiciel, hors de tout disque source Seestar protégé.
- [x] Valider format, unités, effectifs, empreinte et provenance avant remplacement
      atomique; garder la dernière copie exploitable et un historique minimal.
- [x] Respecter les limites et les droits propres à MPC, CBAT et JPL; connexions
      séquentielles, délais d'attente et reprise limitée sans requête par objet.
- [x] Afficher la copie utilisée, son âge, les mises à jour effectuées et les
      échecs réseau; refuser une orbite non exploitable plutôt que la masquer.
- [x] Tester temps simulé, réglages, pannes, cache corrompu, mode hors ligne et
      protections Seestar; compléter le tutoriel illustré et les MD.

Plans comètes : 75cee35. Catalogue MPC et import local CBAT réalisés;
l’accès automatique aux observations CBAT reste différé faute d’interface validée.

## Lot comètes — MPC et informations CBAT

- [x] Examiner les moteurs mobiles et les formats officiels disponibles.
- [x] Enregistrer ce plan localement avant l'implémentation.
- [x] Vérifier les rôles MPC/CBAT, l'accès aux fichiers, les unités, les dates
      et les droits; conserver les sources récupérées et leurs empreintes.
- [x] Ajouter la sélection `comets`, l'import local du format orbital MPC et
      une copie redistribuable si disponible; annoncer clairement toute source inaccessible.
- [x] Propager les orbites elliptiques, paraboliques et hyperboliques sans
      appliquer le modèle H-G des astéroïdes; contrôler époques et convergence.
- [x] Distinguer la magnitude totale cométaire estimée d'une magnitude V et
      conserver les observations CBAT datées séparément des prévisions.
- [x] Associer les données CBAT par désignation explicite, sans inventer de
      mesure ni fusionner des fragments; prévoir un import local si nécessaire.
- [x] Réunir comètes et autres catalogues, écran/TXT/PDF et Seestar en lecture
      seule, avec filtres simultanés et heure de référence.
- [x] Tester hors réseau les formats, coniques, filtres, sources absentes,
      identité, rapports et cas de référence indépendants.
- [x] Actualiser les MD, ajouter un tutoriel illustré accessible dès 10 ans,
      contrôler distributions et installation puis enregistrer le lot localement.

Contraintes : aucun abonnement CBAT contourné, aucune magnitude d'une autre
bande étiquetée V, aucun téléchargement implicite à l'exécution ni écriture Seestar.

## Lot astéroïdes — catalogue orbital et positions variables

- [x] Examiner le moteur actuel et identifier les calculs réservés aux objets fixes.
- [x] Enregistrer ce plan avant le développement.
- [x] Vérifier les sources orbitales publiques, leurs unités, leurs conditions
      d'utilisation et leur actualité; versionner une sélection numérotée utile
      avec empreinte et proposer l'import d'une copie locale pour l'étendre.
- [x] Ajouter `--objects asteroids` avec propagation orbitale hors ligne,
      correction du temps de lumière, position topocentrique par instant et
      magnitude estimée à partir des paramètres H/G disponibles.
- [x] Définir et afficher la validité du modèle, refuser les dates trop éloignées
      des éléments et ne jamais présenter des coordonnées fixes ou une magnitude H
      comme la position ou la luminosité apparente de l'astéroïde observé.
- [x] Filtrer les échantillons où champ et magnitude sont simultanément satisfaits;
      trier par luminosité estimée dans le champ, garder la date de référence et
      ne pas réutiliser les dates saisonnières/oppositions des objets fixes.
- [x] Permettre les sélections mixtes et les rapports terminal/TXT/PDF, avec
      identifiants mineurs distincts pour Seestar, toujours en lecture seule.
- [x] Comparer des positions calculées à une référence indépendante, puis tester
      orbites synthétiques, filtres, limites temporelles, import et exports hors ligne.
- [x] Documenter les limites dans les MD et le tutoriel illustré accessible à
      10 ans, vérifier les paquets et enregistrer les commits locaux sans push.

Plan préalable : `02cd97d`. Première sélection : 1 000 numéros JPL, extensible
par JSON local. Validation et limites dans [docs/ASTEROIDS.md](docs/ASTEROIDS.md).
La propagation perturbée, les comètes, les objets non numérotés et la mise à jour
automatique des orbites restent hors de ce lot.

## Lot Bayer et Flamsteed — sélections stellaires locales

- [x] Examiner les modèles, la sélection multiple et les protections Seestar.
- [x] Enregistrer le plan dans un commit avant le développement.
- [x] Choisir une source stellaire attribuable et redistribuable, vérifier ses
      champs Bayer/Flamsteed, coordonnées, magnitudes et licence; conserver une
      copie dans le projet local avec révision et empreinte documentées.
- [x] Générer deux sélections reproductibles, sans inventer de désignation ni
      substituer une autre bande à V; distinguer ces systèmes de noms d'un
      inventaire exhaustif de toutes les étoiles.
- [x] Ajouter `--objects bayer` et `--objects flamsteed`, seuls ou combinés;
      réunir une même étoile par identifiant source stable, conserver les noms
      secondaires et ne pas présumer une identité croisée avec GCVS ou NGC.
- [x] Afficher les désignations et la provenance dans les rapports écran/TXT/PDF;
      gérer le nom Bayer/Flamsteed et ses variantes explicites dans Seestar,
      sans modifier les archives ni déduire une correspondance par position.
- [x] Remplacer les polices PDF sans alphabet grec par DejaVu Sans régulier/gras
      redistribués sans modification avec leurs notices; vérifier les glyphes,
      la conservation des lettres grecques et leur présence dans les paquets.
- [x] Tester données réelles de référence, génération synthétique, doublons,
      filtres, rapports, lecture seule et distribution hors ligne.
- [x] Mettre à jour les MD et le tutoriel accessible dès 10 ans avec une image,
      exécuter les contrôles locaux et enregistrer le lot sans push.

Plans préalables : `691f039`, puis `d5c94af` pour les polices grecques.
Résultats : 102 tests réussis, un ignoré, treize avertissements IERS; Ruff,
structure, distributions et installation hors des sources vérifiés. Les données
et polices gardent leurs licences et empreintes. Aucune publication distante.

## Finalisation PR nº 6 — tests Windows et tutoriel accessible

- [x] Identifier le refus d'export Windows : code sur D:, fausses archives
      pytest sur C:, donc protection correcte de tout le volume C:.
- [x] Enregistrer ce plan avant le correctif.
- [x] Placer les fichiers temporaires de la CI dans le dossier de travail
      pour tester les copies locales sur le même volume, sans affaiblir la protection.
- [x] Créer explicitement le parent des fichiers temporaires sur une copie neuve
      avant d'exécuter pytest; vérifier un scénario local sans parent préexistant.
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
