# Contribuer à GNU Astrolist

Les lots approuvés **ECC-A à ECC-I** se réalisent avec ECC et gardent leur
identifiant dans le plan, les changements et les comptes rendus. Lire la
[méthode ECC](docs/DEVELOPPEMENT_ECC.md) et sélectionner le premier lot incomplet
dans ROADMAP.md. Une demande de prochaine étape doit mentionner explicitement
l'usage d'ECC; elle ne déclenche pas à elle seule l'implémentation.

Merci de contribuer à GNU Astrolist.

La consigne actuelle est de travailler uniquement dans les copies locales.
Documenter chaque lot dans le tutoriel avec des images explicatives versionnées.
Les opérations GitHub ci-dessous décrivent le processus de contribution futur;
elles restent différées tant que cette consigne locale est en vigueur. Une
instruction explicite de publication peut autoriser une branche donnée, comme
le lot autonome ECC-D à ECC-I; cela n’autorise pas sa fusion.

La documentation est en français; les identifiants Python restent en anglais.
Les contributions en code, documentation, traduction et validation scientifique
sont bienvenues. Le cycle est **Goal / Produce / Submit / Wait / Repeat** :
définir un résultat vérifiable, produire un changement ciblé, le soumettre,
laisser le temps à la revue puis corriger à partir des retours.

1. Créez une branche courte à partir de `main`.
2. Installez un environnement isolé avec le [verrou adapté](requirements/README.md).
3. Ajoutez ou adaptez les tests en même temps que le code.
4. Exécutez `pytest` et `ruff check .`.
5. Soumettez une demande d'intégration qui décrit le problème, la solution et
   les limites restantes.

Avant les prochains lots, détailler le plan dans ROADMAP.md et l'enregistrer
dans un commit local. Maintenir les Markdown concernés, notamment le tutoriel,
le journal des changements et les notices de données. Utiliser des branches
courtes et le modèle de demande d'intégration fourni.

Les contributions originales sont sous GPL-3.0-or-later, sans cession globale
des droits. Ajouter sa propre attestation `git commit -s` après lecture du
[DCO](DCO.md). Ne pas attester au nom d'un tiers. Préserver les avis de licence
et ajouter un en-tête SPDX aux nouveaux fichiers Python.

L'installation détaillée est dans [INSTALL.md](INSTALL.md). Exécuter aussi
`python scripts/check_repository.py` et, pour une livraison,
`python -m build` puis `python scripts/check_distribution.py`.
Les tests courants restent hors réseau; simuler les réponses des services.
Les exemples publics utilisent uniquement des données publiques ou synthétiques.
Respecter [PRIVACY.md](PRIVACY.md) et [SECURITY.md](SECURITY.md).

Une modification de méthode scientifique demande des références et des cas
de comparaison; un changement d'architecture demande une décision documentée.
Voir [GOVERNANCE.md](GOVERNANCE.md) et [docs/VALIDATION.md](docs/VALIDATION.md).

Le code doit rester lisible sous Python 3.11 et plus récent. Les nouvelles
données astronomiques doivent avoir une provenance, une version et des
conditions de redistribution documentées. Aucun résultat céleste ne doit être
inventé pour satisfaire un exemple ou un test.


Contrôles complémentaires : [qualité ECC-E](docs/QUALITE.md),
[état GitHub observé](docs/GOUVERNANCE_VERIFIEE.md) et [livraison](docs/RELEASE.md).
