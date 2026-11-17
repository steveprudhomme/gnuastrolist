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

ECC-A est implémenté et publié dans la
[PR nº 9](https://github.com/steveprudhomme/gnuastrolist/pull/9); sa fusion reste
distincte. La prochaine étape de développement est **utiliser ECC pour réaliser
ECC-B — fiabiliser les données météo**, selon les cases du roadmap.
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
météo et numériques restent à traiter dans ECC-B et ECC-C.

L'environnement local héritait de paquets système et présentait deux conflits
extérieurs au projet, ce qui motive ECC-D. Les risques de concurrence des caches
proviennent de la lecture du code et demandent des tests dédiés dans ECC-F.
Les contrôles distants GitHub, les vulnérabilités à jour et une revue complète
de l'historique n'ont pas été effectués lors de cet audit local.

L'accord concerne le plan et son commit local. Il n'autorise pas l'activation
de services externes, des installations automatiques ou une publication GitHub.
Les archives Seestar restent strictement en lecture seule. Ne jamais fabriquer
de données, signatures ou attestations pour satisfaire un contrôle.
