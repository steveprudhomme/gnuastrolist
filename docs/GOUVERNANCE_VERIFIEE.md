# État observé de la gouvernance — ECC-I

Vérification en lecture seule par l'API GitHub le **17 novembre 2026**.
Aucun réglage n'a été modifié.

| Élément | État renvoyé |
| --- | --- |
| Branche par défaut | `main` |
| Protection de `main` | `protected: false` |
| Recherche de secrets | activée |
| Protection des publications contre les secrets | activée |
| Mises à jour de sécurité Dependabot | désactivées |
| Signalement privé des vulnérabilités | désactivé |

Une CI verte n'impose donc pas une revue avant fusion et ne protège pas la
branche. Ces réglages relèvent d'une action distincte du propriétaire : activer
une protection/règle avec contrôles requis et revue, puis choisir le canal privé
et la politique Dependabot. L'observation peut devenir périmée; la revérifier
avant chaque livraison. Aucun canal confidentiel n'est présenté comme actif.

## Historique et confidentialité

Les deux anciens rapports de la racine ont été examinés localement uniquement
pour leurs catégories de données. Ils contiennent des informations de lieu,
de date et de soirée. Leur contenu n'est ni recopié ni déclaré anonymisé.
Ils sont retirés de l'index courant et ignorés, mais conservés sur le poste.
Ils restent accessibles dans l'historique Git : **aucune réécriture effectuée**.

La recherche ciblée de secrets a porté sur les fichiers suivis courants et les
blobs historiques textuels avec les mêmes règles. Les diagnostics ne publient
aucune valeur. Ce détecteur ne couvre pas tous les formats de secret, les images,
les pièces binaires ou les données personnelles; il ne certifie pas l'historique.
Le contrôle historique sélectionne les extensions `.py`, `.md`, `.txt`, `.toml`,
`.yml`, `.yaml`, `.json` et `.csv`. Il ignore notamment `.env`, `.ini`, `.sh`
et les fichiers sans extension; le décompte ne couvre donc pas tout texte Git.
Les exemples futurs sont produits par les tests à partir de données synthétiques,
et les rapports restent sous `local/`.

## Attributions

Les 19 fichiers Python sans avis ont un auteur Git unique vérifié :
Steve Prud'Homme. Ils reçoivent son avis SPDX GPL-3.0-or-later, sans signature
DCO ajoutée. Les avis collectifs existants sont conservés. Le logiciel original
et les données de tiers restent distincts; voir [les licences](../LICENSE-NOTICE.md)
et les notices `*_SOURCE.md`. Les références ECC-H conservent séparément les
notices MIT SGP4 et BSD-3-Clause du paquet de données IERS.
