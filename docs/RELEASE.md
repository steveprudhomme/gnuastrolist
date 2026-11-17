# Préparer une version

Le [guide du versionnage](VERSIONNAGE.md) définit la politique SemVer et les
fragments `bug`, `improvement`, `feature`. Examiner d'abord le calcul :

```powershell
python -B scripts/versioning.py check
python -B scripts/versioning.py preview
python -B scripts/versioning.py prepare --date 2026-11-17
```

La date est un exemple. Sur instruction explicite et depuis une branche de
livraison propre, ajouter `--apply` à la dernière commande. Relire le diff et
soumettre une PR de préparation : l'outil ne crée aucun commit, tag, signature
ou Release. Les étapes ci-dessous restent à vérifier avant publication.

- [ ] Vérifier les fragments en attente, le niveau calculé et les ruptures.
- [ ] Préparer les numéros, notes datées et marqueurs `released_in` avec l'outil;
      garder séparée la PR de livraison des changements fonctionnels.

- [ ] Relire les changements, la provenance, les licences et les données publiées.
- [ ] Vérifier les protections de main et les contrôles requis sur GitHub.
- [ ] Vérifier tests, Ruff et contrôle du dépôt sous Windows/Linux.
- [ ] Mettre à jour ensemble pyproject.toml, __version__ et CHANGELOG.md.
- [ ] Construire sdist et wheel; contrôler leur contenu et installer la wheel
      dans un environnement neuf, hors du répertoire des sources.
- [ ] Exécuter hors ligne les dix sélections (`variable_stars`, `messier`,
      `caldwell`, `ngc`, `bayer`, `flamsteed`, `asteroids`, `comets`, `satellites`,
      `debris`), seules et combinées; exporter TXT/PDF hors des sources.
- [ ] Vérifier le verrou du cache, la simulation de rétention et le refus des
      archives sources synthétiques; aucun accès au disque Seestar réel.
- [ ] Exécuter couverture avec branches, typage progressif, contrôle de secrets
      courant/historique et audit actualisé de chaque verrou.
- [ ] Comparer les références satellitaires gelées; relire les limites et budgets
      de performance sans prétendre valider toutes les observations.
- [ ] Vérifier les exports ECC-A : nouveau TXT/PDF, refus d'un rapport existant,
      remplacement explicite `--overwrite` et préservation des entrées/archives
      avec des fichiers Seestar synthétiques; voir [EXPORTS.md](EXPORTS.md).
- [ ] Vérifier les états météo ECC-B avec réponses synthétiques : valeurs
      partielles, panne des fournisseurs et mode hors ligne; vérifier la
      conservation des objets et des avertissements dans le TXT/PDF.
- [ ] Vérifier ECC-C : un paramètre invalide avec mise à jour forcée est refusé
      sans réseau, cache ni remplacement d'un rapport; vérifier une commande
      valide et les budgets depuis la wheel installée hors des sources.
- [ ] Établir les empreintes SHA-256 des fichiers réellement distribués.
- [ ] Vérifier les dépendances distribuées et leurs notices; produire un SBOM
      si la distribution inclut des dépendances ou exécutables embarqués.
- [ ] Installer le verrou avec empreintes correspondant à Python/OS, puis le
      projet sans résolution implicite; exécuter `uv pip check` et générer
      `scripts/environment_manifest.py`. Voir [LIVRAISON_REPRODUCTIBLE.md](LIVRAISON_REPRODUCTIBLE.md).
- [ ] Effectuer une revue de secrets et des données personnelles, y compris
      l'historique avant toute première publication d'une archive complète.
- [ ] Faire relire la demande d'intégration et vérifier la CI distante.
- [ ] Créer le tag et les signatures avec les clés du mainteneur, puis publier
      uniquement sur son instruction. Ne jamais inventer de signature.

La présence de cette liste n'indique pas que ses étapes ont été effectuées.


Pour ALTMAX, vérifier une commande sans plafond (90°), une zone 20°–80°,
les bornes refusées avant actualisation et le refus `--alt-center` avec plafond.
Comparer écran/TXT/PDF et la note d'inclusion partielle depuis la wheel installée.
Le schéma `plafond-hauteur.svg` et les régressions doivent figurer dans la sdist.
