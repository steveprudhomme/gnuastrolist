# Mises à jour configurables des catalogues

Le programme contrôle les copies **au démarrage d'une commande**, lorsqu'on
active l'option. Ce n'est pas une tâche de fond : si on ne lance pas le logiciel,
aucune vérification n'a lieu. Les ressources livrées dans le paquet restent intactes.

```text
--update-catalogs never|if-stale|force
--catalog-max-age-hours HEURES
--catalog-age SOURCE=HEURES
--catalog-cache-dir DOSSIER
--catalog-config FICHIER_JSON
```

Le mode par défaut est `never`. Il peut utiliser un cache valide déjà présent,
mais ne télécharge rien. `if-stale` actualise une copie absente ou trop ancienne.
`force` demande une nouvelle copie. **`--offline` interdit toute connexion** dans
les trois modes; la météo et les mises à jour IERS sont aussi désactivées.
Il peut utiliser les copies locales vérifiées. Les orbites gardent leurs propres
limites scientifiques, indépendamment de la fraîcheur du téléchargement.

## Catalogues et délais

| Catalogue (`--objects`) | Sources utilisées | Délai par défaut |
| --- | --- | --- |
| `variable_stars` | GCVS via VizieR/CDS (`gcvs`) | 720 h, soit 30 jours |
| `messier`, `caldwell`, `ngc` | OpenNGC (`openngc`), compléments SIMBAD (`simbad`) | 720 h |
| `bayer`, `flamsteed` | HYG 4.1 (`hyg`) | 720 h |
| `asteroids` | JPL SBDB (`jpl`), sélection de 1 000 numéros | 24 h |
| `comets` | Fichier orbital MPC (`mpc`) | 24 h |
| `satellites`, `debris` | CelesTrak GP et SATCAT, génération partagée (`celestrak`, `gp`, `satcat`) | GP 6 h, SATCAT 24 h |
| Observations CBAT/ICQ | `--cbat-file`, import local documenté | Pas de connexion automatique validée |

Les délais sont des propositions réglables, pas des fréquences garanties par
les fournisseurs. HYG reste à la version 4.1 : une révision de format/version
demanderait une évolution du chargeur. Toutes les sources ont une notice dans
`src/gnu_astrolist/data/`; leurs conditions propres restent applicables.

Seuls les catalogues sélectionnés sont vérifiés. Pour un passage sur tous les
catalogues, sélectionner les dix noms. Les options `--comets-file` et
`--asteroids-file` sont prioritaires : le fichier local explicite est lu sans
mise à jour réseau du catalogue orbital correspondant.

Un fichier `--satellite-elements-file` ou `--satcat-file` désactive l'actualisation
CelesTrak de la commande. Les extraits UNOOSA restent locaux; aucun accès
automatique à son index n'est validé. Satellites et débris partagent leur copie,
et des délais minimaux du fournisseur s'appliquent même en mode forcé : GP 2 h,
SATCAT 24 h. Les délais trop courts sont relevés. Toute erreur HTTP arrête
le fournisseur, avec état persistant de pause ou blocage; voir le
[guide spécialisé](SATELLITES.md) avant toute réinitialisation manuelle.

`--catalog-age` est répétable et accepte un catalogue ou un fournisseur. Exemple :
`--catalog-age comets=12 --catalog-age asteroids=48 --catalog-age openngc=720`.
Les nombres doivent être finis et strictement positifs. Une source inconnue est
une erreur. Quand un délai de catalogue et de fournisseur s'appliquent ensemble,
le plus court l'emporte.

## Exemple de commande

```powershell
.venv\Scripts\python -m gnu_astrolist --date 2026-11-17 --time-range 21:00-22:00 --timezone America/Toronto --lat 45.57 --lon -73.68 --az-min 0 --az-max 360 --min-altitude 10 --objects comets asteroids messier --max-magnitude 16 --update-catalogs if-stale --catalog-age comets=24 --catalog-age asteroids=48 --catalog-age messier=720 --catalog-cache-dir local/catalog-cache --limit 20
```

Pour travailler sans Internet, ajouter `--offline`. Un fichier JSON facultatif
évite de recopier les réglages :

```json
{
  "mode": "if-stale",
  "cache_dir": "local/catalog-cache",
  "max_age_hours": {
    "comets": 24,
    "asteroids": 48,
    "gcvs": 720,
    "openngc": 720,
    "simbad": 720,
    "hyg": 720
  }
}
```

Enregistrer ce JSON dans `local/catalogues.json`, puis ajouter
`--catalog-config local/catalogues.json`. Il n'est pas recherché implicitement.
Les chemins relatifs se rapportent au dossier courant de la commande.
Les options explicites de mode/cache ont priorité sur le fichier. Le délai
global en ligne de commande remplace les délais des catalogues; les réglages
`--catalog-age` explicites sont ensuite appliqués. Les délais par fournisseur
restent également des plafonds (minimum des délais applicables).

## Validation, historique et pannes

Le cache par défaut est `local/catalog-cache` sur l'ordinateur, dossier ignoré
par Git. Ne pas l'installer sur le disque Seestar. Avec `--seestar-path`, les
destinations sont protégées avant toute création; liens et jonctions sont refusés.

Les téléchargements sont séquentiels, limités en taille et en durée. Une réponse
est conservée avec URL, date et SHA-256. Les générateurs installés reconstruisent
les catalogues et contrôlent coordonnées, bandes, valeurs finies, identifiants,
effectifs et schémas. Une variation d'effectif supérieure à 20 % de la copie
embarquée est refusée automatiquement, afin de ne pas activer une réponse tronquée;
une grande évolution légitime nécessite alors une révision de la copie de référence.
Messier et Caldwell doivent rester complets (110 et 109).

Chaque génération validée reçoit ses métadonnées et est publiée atomiquement
dans le cache. Les anciennes générations sont conservées; il n'y a pas de purge
automatique de cet historique. Les appels réutilisent les réponses partagées
OpenNGC/HYG lorsqu'elles sont nécessaires à plusieurs catalogues dans la même
commande. Un échec de source n'est pas relancé en boucle.

En cas de panne réseau, de schéma invalide ou de copie corrompue, le programme
signale le problème et conserve le dernier cache validé, sinon la copie embarquée.
Cela ne lève pas les limites d'âge orbitales : le calcul peut encore être refusé
si aucune orbite n'est exploitable. L'âge du cache concerne sa récupération,
pas la précision d'une prévision ni la date de mesure de chaque valeur.

Les modes et pannes sont testés avec réseau simulé. Les vérifications du présent
lot ne constituent pas un essai réel de tous les services externes à leur état
futur. Les nouvelles générations restent locales tant qu'elles ne sont pas
explicitement intégrées à une prochaine version du projet.
