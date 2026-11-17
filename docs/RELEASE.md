# Préparer une version

- [ ] Relire les changements, la provenance, les licences et les données publiées.
- [ ] Vérifier les protections de main et les contrôles requis sur GitHub.
- [ ] Vérifier tests, Ruff et contrôle du dépôt sous Windows/Linux.
- [ ] Mettre à jour ensemble pyproject.toml, __version__ et CHANGELOG.md.
- [ ] Construire sdist et wheel; contrôler leur contenu et installer la wheel
      dans un environnement neuf, hors du répertoire des sources.
- [ ] Exécuter les exemples Caldwell hors ligne depuis cette installation.
- [ ] Vérifier les exports ECC-A : nouveau TXT/PDF, refus d'un rapport existant,
      remplacement explicite `--overwrite` et préservation des entrées/archives
      avec des fichiers Seestar synthétiques; voir [EXPORTS.md](EXPORTS.md).
- [ ] Vérifier les états météo ECC-B avec réponses synthétiques : valeurs
      partielles, panne des fournisseurs et mode hors ligne; vérifier la
      conservation des objets et des avertissements dans le TXT/PDF.
- [ ] Établir les empreintes SHA-256 des fichiers réellement distribués.
- [ ] Vérifier les dépendances distribuées et leurs notices; produire un SBOM
      si la distribution inclut des dépendances ou exécutables embarqués.
- [ ] Effectuer une revue de secrets et des données personnelles, y compris
      l'historique avant toute première publication d'une archive complète.
- [ ] Faire relire la demande d'intégration et vérifier la CI distante.
- [ ] Créer le tag et les signatures avec les clés du mainteneur, puis publier
      uniquement sur son instruction. Ne jamais inventer de signature.

La présence de cette liste n'indique pas que ses étapes ont été effectuées.
