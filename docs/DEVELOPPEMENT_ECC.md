# Développer les lots approuvés avec ECC

Le 17 novembre 2026, le propriétaire a approuvé les neuf suggestions de l'audit
de développement du commit `db2f48b`, puis demandé le préfixe ECC pour les
retrouver lors des prochaines étapes. Le plan détaillé est dans
[ROADMAP.md](../ROADMAP.md); les règles persistantes sont dans
[AGENTS.md](../AGENTS.md).

## Retrouver la prochaine étape

1. Lire les cases du roadmap, dans l'ordre **ECC-A à ECC-I**.
2. Choisir le premier lot dont des critères restent à vérifier.
3. Annoncer : **« Utiliser ECC pour réaliser ECC-X — objectif du lot. »**
4. Si le lot est commencé, nommer sa première sous-étape incomplète,
   par exemple **ECC-A.1**, sans recommencer le travail terminé.

ECC-A est fusionné dans `main` par la
[PR nº 9](https://github.com/steveprudhomme/gnuastrolist/pull/9), commit `1d75522`.
ECC-B est réalisé et publié dans la
[PR nº 10](https://github.com/steveprudhomme/gnuastrolist/pull/10), avec cinq
contrôles réussis sur le correctif; sa fusion reste distincte. ECC-C est publié
dans la [PR nº 11](https://github.com/steveprudhomme/gnuastrolist/pull/11), basée
sur ECC-B, avec cinq contrôles réussis sur le correctif. Intégrer ECC-B avant
de revoir la base et la fusion d'ECC-C dans `main`.
Les lots ECC-D à ECC-I sont réalisés dans la PR nº 12, sur une branche
autonome basée sur ECC-C. Les cases et preuves courantes sont dans ROADMAP.md.
Aucun lot ECC terminé ne doit être recommandé de nouveau; la revue et les
fusions restent des décisions distinctes.
Une demande d'information sur la prochaine étape ne déclenche pas sa réalisation.

## Périmètre des lots

| Identifiant | Objectif | Priorité |
| --- | --- | --- |
| ECC-A | Protéger les entrées et fiabiliser les exports | Haute |
| ECC-B | Fiabiliser les données météo et le risque de rosée | Haute |
| ECC-C | Valider les paramètres avant les effets de la commande | Haute |
| ECC-D | Reproduire l'environnement et les livraisons | Haute |
| ECC-E | Renforcer les contrôles de qualité automatisés | Moyenne |
| ECC-F | Coordonner les caches et leur rétention | Moyenne |
| ECC-G | Séparer orchestration, rapport et contexte astronomique | Moyenne |
| ECC-H | Étendre validation scientifique et mesures de performance | Moyenne |
| ECC-I | Réconcilier documentation et pratiques open source | Moyenne |

Les sous-étapes gardent toujours le préfixe ECC : `ECC-A.1`, `ECC-A.2`, etc.
Conserver ces identifiants dans les plans, commits et comptes rendus.

## Utiliser ECC pour réaliser un lot

Lire les méthodes ECC disponibles et pertinentes pour le travail demandé :

- `python-testing` pour concevoir des tests de régression déterministes;
- `python-patterns` pour la lisibilité, les responsabilités et le typage Python;
- `security-review` pour les entrées, les fichiers et les services externes;
- `verification-loop` pour les vérifications et la revue finale.

Adapter ces méthodes à Python, Windows et aux contraintes du dépôt. Les recettes
JavaScript ou Linux ne sont pas des commandes à exécuter telles quelles.
Ne pas prétendre utiliser une méthode inaccessible; signaler une absence d'ECC.
La présence du plugin n'établit pas qu'une revue ou un contrôle a été exécuté.

Avant de coder, vérifier que le plan approuvé est enregistré dans un commit
local. Si le périmètre change substantiellement, proposer les ajouts avant de
modifier le roadmap. Un lot est terminé lorsque ses critères sont vérifiés,
les tests pertinents exécutés et les documents mis à jour.

Maintenir le tutoriel avec des explications simples et des images versionnées
pour les changements d'usage. Documenter les contrôles purement internes dans
les guides de développement et validation sans allonger inutilement le démarrage.

## Contexte de l'audit et limites

L'audit local a constaté 350 tests réussis, un ignoré et 26 avertissements
IERS/ERFA; Ruff, liens et contenu des distributions réussissaient. Quatre défauts
ont été reproduits avec des données synthétiques : collision configuration/export,
seeing nul non géré, séries météo désalignées et pas numérique extrême.
Ces constats motivent ECC-A, ECC-B et ECC-C. ECC-A apporte maintenant les
contrôles de fichiers et les exports décrits dans [EXPORTS.md](EXPORTS.md);
voir les résultats et limites dans [VALIDATION.md](VALIDATION.md). Les défauts
météo sont traités par ECC-B, décrit dans [METEO.md](METEO.md); les paramètres
numériques sont traités par ECC-C, décrit dans [PARAMETRES.md](PARAMETRES.md).

L'environnement local héritait de paquets système et présentait deux conflits
extérieurs au projet, ce qui motive ECC-D. Les risques de concurrence des caches
proviennent de la lecture du code et demandent des tests dédiés dans ECC-F.
Les contrôles distants GitHub, les vulnérabilités à jour et une revue complète
de l'historique n'ont pas été effectués lors de cet audit local.

L'accord concerne le plan et son commit local. Il n'autorise pas l'activation
de services externes, des installations automatiques ou une publication GitHub.
Les archives Seestar restent strictement en lecture seule. Ne jamais fabriquer
de données, signatures ou attestations pour satisfaire un contrôle.


## Autorisation du lot autonome du 17 novembre 2026

Le propriétaire a explicitement demandé de publier le plan avant le code et de
mettre GitHub à jour pour ECC-D à ECC-I. Cette autorisation remplace la consigne
locale par défaut pour cette branche seulement. Les calculs et modifications
se font dans les copies locales; aucune fusion ni modification de réglage GitHub
n'est incluse. Les installations nécessaires restent dans les environnements
locaux du projet, sans service permanent. Le plan publié est `a814a49`.
