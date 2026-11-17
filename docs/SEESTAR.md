# Vérifier la présence d'acquisitions Seestar

L'option `--seestar-path DOSSIER` ajoute une vérification des archives dans les
rapports terminal, TXT et PDF, sans filtrer la liste d'observation. Le chemin
désigne le dossier MyWorks, par exemple `E:\MyWorks`; il peut changer à chaque usage.
Sans cette option, aucune vérification Seestar n'est effectuée et les rapports
gardent leurs colonnes précédentes.

## Lecture seule

Le scanner parcourt uniquement les noms et métadonnées des dossiers et fichiers.
Il n'ouvre pas les images ni les FITS, ne crée aucun cache, et ne renomme, déplace,
supprime ou modifie aucun fichier source ni ses attributs. Il n'exécute aucun
programme présent dans les archives. Les dossiers `.git`, `.cache` et
`__pycache__` sont ignorés. Les liens symboliques et jonctions ne sont pas suivis;
leur présence rend l'inventaire incomplet, de façon conservatrice.

Les destinations TXT/PDF sont résolues avant traitement puis revérifiées avant
écriture. Un export sous la racine source est refusé, y compris par un lien ou
un chemin relatif. Si le volume Windows source est distinct de celui du logiciel,
le volume source entier est protégé contre les exports. Les fichiers de sortie
existants possédant plusieurs liens physiques sont refusés. L'API PDF applique
aussi cette protection avant de créer son fichier temporaire.

Il s'agit d'une politique applicative : le logiciel ne remonte pas le disque
en lecture seule et ne change pas ses permissions. Une redirection de sortie
réalisée par le shell est extérieure à cette protection; ne pas rediriger le
terminal vers le disque source. Placer les rapports dans `local/` sur le disque
du projet, jamais dans les archives.

## Reconnaissance

Le scanner reconnaît les noms d'acquisition Seestar commençant par `Stacked_`
ou `Light_`, suivis du nom de cible et d'une durée comme `_10.0s_`. Un nombre
d'images peut suivre le préfixe. Exemples **synthétiques** :

```text
MyWorks/M 31/Stacked_20_M 31_10.0s_LP_20260815-210000.fit
MyWorks/NGC 869-sub/Light_NGC 869_10.0s_LP_20260815-210000.fit
```

Les extensions admises sont `.fit`, `.fits`, `.fts`, `.jpg`, `.jpeg`, `.png`,
`.tif` et `.tiff`, sans distinction de casse. Les fichiers vides et les vignettes
terminant par `_thn`, `_thumb` ou `_thumbnail` sont exclus. Un dossier portant
le nom d'un objet sans acquisition reconnue ne suffit pas.

Les identifiants M, NGC, IC et C sont normalisés : espaces, zéros initiaux et
casse, avec préservation des suffixes de composants. Le nom retenu, la désignation
de catalogue et les alias affichés sont utilisés. Les correspondances explicites
Messier/Caldwell des données embarquées sont disponibles même en mode catalogue
unique : une acquisition `M 31` peut donc être trouvée pour NGC224.

Il n'y a pas de rapprochement par proximité angulaire, ni d'interprétation des
noms courants, ni de lecture de l'en-tête FITS `OBJECT`. Un fichier nommé autrement
peut être ignoré. Les groupes et leurs composants restent distincts : une image
de NGC869 n'atteste pas une acquisition du groupe C14 entier. Pour GCVS, seul le
nom explicite du catalogue est rapproché; ses autres dénominations ne sont pas
déduites.

## Sens des statuts

| Statut | Interprétation |
| --- | --- |
| Fait (empilé) | Au moins un fichier `Stacked_` reconnu et non vide correspond à la cible. |
| Brutes seules | Au moins un `Light_` reconnu, sans empilement trouvé lors d'une lecture complète. |
| Brutes (incomplet) | Des brutes ont été trouvées, mais un empilement pourrait être dans une partie illisible. |
| Non trouvé | Aucune acquisition reconnue ne correspond après une lecture complète. |
| Indéterminé | Aucune preuve trouvée et lecture incomplète, par exemple à cause d'un accès refusé. |

Le résumé donne la racine consultée et le nombre d'incidents sans publier la
liste de fichiers. Une preuve positive reste positive si un autre dossier est
illisible. Un chemin racine absent, un fichier à la place du dossier ou une racine
elle-même liée sont des erreurs explicites avant traitement des rapports.

« Fait » indique la présence d'une archive reconnue, pas sa validité scientifique,
son temps d'intégration, son cadrage, son contenu ou sa qualité. « Non trouvé »
ne signifie pas « jamais photographié ».

## Vérification et confidentialité

Les tests ordinaires utilisent des archives synthétiques sous les répertoires
temporaires de tests. Ils n'utilisent pas le disque Seestar de l'utilisateur.
L'essai manuel réel autorisé ne conserve ses rapports que dans `local/`, ignoré
par Git. La présence d'archives et leur chemin peuvent être des informations
personnelles : ne pas les joindre automatiquement aux contributions publiques.
