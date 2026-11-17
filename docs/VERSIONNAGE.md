# Versionnage par type de changement

Le propriétaire a choisi **SemVer**, le 17 novembre 2026. Le numéro s'écrit
`MAJEUR.MINEUR.CORRECTIF`. Le projet reste un prototype tant qu'il est en `0.x`;
les règles ci-dessous ne constituent pas une garantie scientifique ou matérielle.

| Changement livré | Type du fragment | Effet depuis 0.11.0 |
| --- | --- | --- |
| Correction d'un bug | `bug` | 0.11.1 |
| Amélioration compatible | `improvement` | 0.12.0 |
| Nouvelle fonctionnalité compatible | `feature` | 0.12.0 |
| Rupture de compatibilité, quel que soit le type | `breaking = true` | 1.0.0 |

Une livraison prend le niveau le plus élevé parmi les changements en attente.
Les composants inférieurs sont remis à zéro. Les trois catégories restent
distinctes dans les notes, même si amélioration et fonctionnalité ont le même
effet sur le numéro. Un ticket ouvert ne suffit pas à augmenter une version.

## Déclarer un changement

Dans une copie des sources, ajouter un fichier unique sous `changes/`, en même
temps que le code et ses tests :

```toml
type = "feature"
summary = "Ajouter une option utile à la préparation d'une soirée."
breaking = false
```

Le nom utilise minuscules, chiffres, tirets, points ou traits de soulignement,
et se termine par `.toml`. Le résumé est public, sur un paragraphe non vide.
Les clés inconnues et types invalides sont refusés. Voir [changes/README.md](../changes/README.md).

La CI exige un fragment en attente ajouté ou modifié pour les changements de
code (`src/`, `scripts/`), de dépendances/politique (`pyproject.toml`,
`versioning.toml`) ou de workflows. Une modification de documentation seule
peut ne pas préparer de livraison; ajouter un fragment si elle doit y figurer.

## Vérifier et voir le prochain numéro

Ces commandes se lancent depuis la racine des sources, avec Python 3.11 ou plus
récent. Elles n'exigent aucune dépendance supplémentaire :

```powershell
python -B scripts/versioning.py check
python -B scripts/versioning.py preview
```

`preview` produit un JSON avec la version courante, la prochaine et les changements.
Les modes de lecture ne modifient aucun fichier du projet. `-B` évite aussi la
création normale de caches Python. Avec les fragments initiaux ALTMAX et VERSION,
la prévision est **0.12.0**, mais la version courante reste **0.11.0**.

## Préparer une livraison explicitement

1. Faire valider les fonctionnalités et leurs fragments dans les PR habituelles.
2. Partir d'une copie propre et d'une branche dédiée à la livraison.
3. Examiner la préparation datée, sans appliquer :

   ```powershell
   python -B scripts/versioning.py prepare --date 2026-11-17
   ```

4. Sur instruction du mainteneur, remplacer la date d'exemple par celle de
   livraison et demander l'application :

   ```powershell
   python -B scripts/versioning.py prepare --date 2026-11-17 --apply
   ```

5. Relire le diff. L'outil synchronise `pyproject.toml`, `__version__` et
   `CHANGELOG.md`. Il conserve les notes existantes, ouvre une nouvelle section
   « Non publié » et marque les fragments traités avec `released_in`.
6. Commiter, ouvrir la PR de livraison et attendre revue et contrôles verts.
   La CI reconstruit en mémoire le plan depuis sa base Git, vérifie le numéro
   et les fichiers préparés, puis refuse du code supplémentaire dans cette PR.
7. Après fusion et validation du commit final, le mainteneur crée le tag
   correspondant et la Release selon [RELEASE.md](RELEASE.md), sur instruction
   explicite. Aucun tag, signature, push ou Release n'est créé par cet outil.

Les préversions et suffixes de développement ne sont pas automatisés par cette
première version du mécanisme : seules les livraisons canoniques `X.Y.Z` sont
acceptées. Le passage à une version majeure reste une décision de compatibilité.

## Protections et limites

Le chemin de travail est celui du script dans les sources; aucun chemin Seestar
ou fichier de rapport n'est accepté. La préparation refuse une copie Git sale,
les liens symboliques, jonctions et liens physiques dans les entrées. Les
versions incohérentes, dates invalides et changements d'entrées depuis le plan
sont refusés avant remplacement. Les fichiers sont préparés en voisins temporaires.

Le remplacement est atomique **par fichier**, pas pour toute la livraison.
Une erreur gérée restaure les fichiers précédents. Si la restauration est
elle-même interrompue ou impossible, les copies originales restantes sont
conservées et le processus échoue. Un arrêt brutal peut laisser une préparation
partielle : conserver les copies, examiner le diff et rétablir la cohérence
avant de continuer. Les contrôles de versions ne certifient pas les clés de
signature, la protection de main ou la validité scientifique du logiciel.
