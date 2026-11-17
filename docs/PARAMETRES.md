# Paramètres vérifiés avant traitement — ECC-C

La commande vérifie ses réglages numériques, son calendrier, son champ, ses
budgets et la configuration des actualisations avant de modifier la politique
IERS, d'actualiser les catalogues, de demander la météo ou de produire un rapport.
Un refus de ce précontrôle conserve donc les rapports et ne crée pas de cache.
Les protections d'entrées et de destinations [ECC-A](EXPORTS.md) restent actives.

## Domaines acceptés

| Réglage | Domaine |
| --- | --- |
| Latitude | −90 à 90 degrés |
| Longitude | −180 à 180 degrés |
| Azimuts minimal/maximal | 0 à 360 degrés |
| Élévations minimale/maximale et centre vertical du champ | 0 à 90 degrés; minimum ≤ maximum |
| Altitude du site terrestre | −1 000 à 10 000 mètres |
| Hauteur solaire maximale du filtre satellite | −90 à 90 degrés |
| Magnitude limite | Tout nombre fini, y compris négatif; absence permise |
| Pas temporel | 1 microseconde à 24 heures |
| Nombre de lignes `--limit` | Entier strictement positif, ou absence de limite |
| Âges de récupération/écart GP maximal | Strictement positifs, finis, au plus 23 999 999 976 heures |

NaN et les infinis sont refusés. Les API numériques refusent aussi les booléens
et les chaînes comme coordonnées, magnitudes ou pas. Le parseur des durées en
heures accepte les chaînes numériques de la CLI, mais pas les booléens JSON.
La borne des âges correspond aux jours représentables de `timedelta`; elle
n'est pas une garantie de précision d'une prévision aussi éloignée.

L'altitude est celle d'un site terrestre : le logiciel ne traite pas un
observateur embarqué dans un satellite. Les contrôles de saisie ne remplacent
pas les limites scientifiques documentées des modèles et des catalogues.

## Plafond du champ pour les télescopes intelligents

`--min-altitude 20 --max-altitude 80` définit une zone de 20° à 80°, bornes
incluses. Le plafond effectif vaut 90° sans nouvelle option. Le centre et la
hauteur du champ sont calculés depuis les deux limites. Une zone de largeur
nulle est acceptée, comme l'ancien cas `--min-altitude 90`; elle exige un
échantillon exactement sur cette hauteur, à la tolérance numérique près.

Les deux limites doivent être finies et respecter `0 ≤ minimum ≤ maximum ≤ 90`.
Un plafond explicite ne peut pas accompagner `--alt-center`, qui déplace le
champ. Sans `--max-altitude`, cet ancien réglage conserve son comportement,
y compris le déplacement de la limite basse. L'alias `--fov-v` reste accepté.

La même validation s'applique à `ObservationRequest.max_altitude` et à
`FieldOfView.from_automatic_center(maximum_altitude_deg=...)`. `None` signifie
absence de nouveau plafond : valeur effective 90° et centre avancé historique
encore permis. Le nouveau champ de requête est ajouté en dernier, sans modifier
les positions des paramètres Python existants.

Ce plafond règle la recherche, pas la monture. Un objet est proposé lorsqu'au
moins un échantillon est dans le champ; sa hauteur au début ou à la fin peut
dépasser le plafond. Les heures « monte/descend » existantes concernent toujours
la limite basse, pas le début/fin d'un passage complet sous le plafond.
Le programme ne certifie ni une pose entière ni l'accessibilité mécanique.

## Pas et budgets : deux limites distinctes

`--sample-minutes` règle les objets fixes, astéroïdes et comètes.
`--satellite-step-seconds` règle les satellites et débris. Leurs unités restent
différentes; la limite physique de représentation du pas est la même.

Le pas est validé avant conversion, puis arrondi à la microseconde de Python.
Le nombre exact d'instants est calculé **en UTC, avant allocation**, en incluant
le début et la fin, sans dupliquer une borne :

```text
nombre = plafond(durée_en_microsecondes / pas_en_microsecondes) + 1
```

- Objets fixes et petits corps : au plus **2 000 instants**.
- Satellites et débris : au plus **20 000 instants**.

Un pas représentable peut encore dépasser le budget sur une longue plage.
Augmenter le pas ou raccourcir la plage. `--limit 3` ne réduit que l'affichage,
pas le travail de calcul; il ne contourne pas ce budget. En sélection mixte,
chaque famille doit respecter son budget. Le budget d'une famille absente n'est
pas imposé, mais un pas numérique invalide reste une erreur de saisie.

Les fenêtres sont converties en UTC avant le comptage. Une période de même
heure civile peut durer 23 ou 25 heures lors d'un changement d'heure; ce sont
les heures réellement écoulées qui comptent. Les dates/heures civiles ambiguës
ou inexistantes restent refusées par le lecteur de calendrier.

## Exemples

Commande valide pour une liste volontairement vide, sans réseau :

```powershell
gnu-astrolist --date 2026-11-17 --time-range 21:00-22:00 --lat 45 --lon 0 --az-min 0 --az-max 360 --min-altitude 10 --objects messier --max-magnitude -20 --sample-minutes 10 --offline
```

Sur une heure, dix minutes donnent sept instants. Une minute en donne 61.
Au contraire, `--sample-minutes 1e-20` est trop petit pour être représenté et
`--sample-minutes 0.001` dépasse le budget de 2 000 instants sur cette heure.
Ces commandes sont refusées avant l'actualisation, même avec
`--update-catalogs force`. La date de l'exemple doit être adaptée à l'observation.

## Configuration des catalogues

Le mode, les chemins et les âges sont vérifiés avant d'appeler l'actualisation.
Un chemin de cache vide ou contenant un caractère nul, une source inconnue,
un type incorrect ou un âge non valide est refusé. Par exemple, dans un JSON,
`true` n'est pas un délai d'une heure. Les options explicites conservent leur
priorité sur le fichier de configuration; la valeur finalement appliquée est
validée. Voir [CATALOG_UPDATES.md](CATALOG_UPDATES.md).

## Portée des contrôles

Les moteurs des objets fixes, petits corps, satellites et Lune réutilisent les
contrôles du site et de fenêtre, y compris sur des sélections vides lorsqu'elles
existent dans leur API. Les échantillonnages partagent le même comptage.
Les fichiers de catalogues ne sont pas entièrement décodés pendant ce précontrôle :
leurs lecteurs gardent la validation du contenu, des orbites et de la provenance.
Une erreur de données découverte ensuite n'est donc pas une preuve que tous les
traitements précédents ont été annulés. Les exports restent atomiques par fichier.

Les tests utilisent des réglages, configurations et archives Seestar synthétiques.
Aucun test ne nécessite le vrai disque USB, qui reste source en lecture seule.
