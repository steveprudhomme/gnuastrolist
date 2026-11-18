# Satellites artificiels, débris, COSPAR, SATCAT et UNOOSA

`--objects satellites` retient les charges utiles PAY décrites dans SATCAT.
`--objects debris` retient les débris DEB et les corps de fusées R/B. Ces choix
se combinent entre eux et avec les autres catalogues. La copie embarquée est
partielle : 737 éléments GP et 1 873 fiches SATCAT des groupes CelesTrak `visual`
et `cosmos-2251-debris`. Voir la [notice source](../src/gnu_astrolist/data/SPACE_OBJECT_SOURCE.md).

Créer `local` dans le projet sur l'ordinateur, puis :

```powershell
.venv\Scripts\python -m gnu_astrolist --date 2026-11-17 --time-range 21:00-21:20 --timezone America/Toronto --lat 45.57 --lon -73.68 --az-min 0 --az-max 360 --min-altitude 10 --objects satellites debris --satellite-step-seconds 5 --offline --limit 5 --output-txt local/satellites.txt --output-pdf local/satellites.pdf
```

## Trois identités, trois rôles

| Source ou identifiant | Rôle dans le programme |
| --- | --- |
| COSPAR, par exemple `1998-067A` | Identifiant international : année, lancement, pièce. Ce n'est pas un catalogue de positions. |
| SATCAT/NORAD, par exemple `25544` | Identifiant numérique stable et fiche descriptive : type, dates, propriétaire codé. Jusqu'à neuf chiffres sont conservés. |
| United Nations Register of Objects Launched into Outer Space | Informations administratives d'immatriculation, importées localement par COSPAR. Aucun élément SGP4 n'en est déduit. |

Les identifiants complets apparaissent dans les noms des résultats. Les pièces
et fragments restent distincts. Le nom d'une famille de débris ou d'un étage
ne permet pas de réunir ses différentes fiches. Le code propriétaire SATCAT
n'est pas traité comme l'État d'immatriculation ONU.

## Calculs de passage

Le chargeur lit un CSV GP ou une liste JSON OMM de CelesTrak, avec ou sans gzip.
Les conventions requises sont UTC, TEME, SGP4 et centre EARTH. Il accepte les
conventions omises comme documenté par CelesTrak, refuse les autres valeurs
explicites et valide les champs, identités, nombres finis et doublons.
Les anciens TLE à colonnes fixes ne sont pas importés par cette interface.

La dépendance `sgp4` propage les éléments; Astropy transforme TEME en ITRS,
soustrait la position du site puis transforme le rayon topocentrique en Alt/Az.
La méthode évite d'ajouter une aberration géocentrique inadaptée au rayon local.
Les hauteurs sont géométriques, sans réfraction. Une erreur SGP4 est annoncée
avec numéro NORAD et code; elle ne devient pas une prédiction valide.

Les éléments doivent être à **±168 heures**, par défaut, de toute la plage.
`--satellite-max-epoch-hours` règle cette borne; elle ne garantit pas la précision,
notamment après une manœuvre ou près d'une rentrée. Les éléments trop éloignés,
fiches absentes, types non demandés, objets non terrestres/dockés et rentrées
déjà signalées sont écartés avec leurs motifs. Si aucun élément choisi n'est
assez récent, le programme demande une actualisation.

Le pas propre aux satellites est **5 secondes** par défaut, réglable avec
`--satellite-step-seconds`. Les autres catalogues gardent `--sample-minutes`.
Une limite de 20 000 échantillons protège la mémoire : réduire la plage ou
augmenter le pas lorsque nécessaire. Un passage rapide entre les échantillons
peut être manqué. Le rapport retient, par objet, le plus haut échantillon admis
dans le champ, son heure locale, sa distance et ses conditions d'éclairage.
Les premières/dernières présences sont des échantillons, pas les bornes garanties
d'un passage continu. Les dates saisonnières/oppositions ne sont pas calculées.

## Présence géométrique et observation optique

### Coordonnées à l'instant retenu

Après « Instant position (local) », les sorties écran, TXT et PDF affichent :

- **Azimut à cet instant** : direction depuis le nord vers l'est,
  0° = nord, 90° = est, 180° = sud, 270° = ouest.
- **Hauteur à cet instant** : angle au-dessus de l'horizon, 0° = horizon,
  90° = zénith (juste au-dessus de vous).

Les deux valeurs proviennent directement des coordonnées topocentriques Alt/Az
calculées par la chaîne SGP4/Astropy décrite ci-dessus, au même échantillon
que le maximum retenu. Ce sont des hauteurs géométriques sans réfraction,
affichées avec deux décimales; cet affichage ne garantit pas cette précision.
Aucun nouveau catalogue ou jeu de mesures n'est ajouté. Les sources, dates de
récupération, licences et reconstruction des données orbitales restent celles
de la [notice existante](../src/gnu_astrolist/data/SPACE_OBJECT_SOURCE.md).

Le point retenu respecte le champ et, si demandé, le filtre optique. Il peut
donc différer du sommet complet du passage. Ce n'est ni la position du début
ni celle de la fin de la plage. Les coordonnées absentes restent des tirets;
les objets fixes d'une sélection mixte ne reçoivent pas de valeur inventée.

Ces coordonnées aident à choisir une direction pour la photographie à l'heure
indiquée. Le satellite se déplace : un point de passage ne fournit pas une
trajectoire de suivi, une durée de pose ou une commande pour le Seestar.
Pour une séance réelle, utiliser des éléments récents et vérifier les capacités
de suivi de son matériel. Les premiers/derniers échantillons dans le champ
peuvent encadrer plusieurs passages et ne garantissent pas une fenêtre continue.

Par défaut, être dans le champ suffit. Un satellite peut être dans l'ombre et
ne pas être visible. Ajouter `--satellite-optical-only` pour exiger au même
échantillon : champ, éclairage solaire et Soleil sous −6° au site.
`--satellite-max-sun-altitude` règle ce dernier seuil.

L'ombre terrestre est un cylindre approximatif, sans pénombre. Ces conditions
ne prédisent ni brillance, orientation, éclat spéculaire, météo, ni détection.
Aucune magnitude optique n'est fournie : un `--max-magnitude` explicite exclut
donc ces objets. En sélection mixte, enlever ce seuil ou utiliser
`--all-magnitudes` pour les conserver. La surface radar RCS ne devient pas V.
Ces calculs ne servent pas à l'évaluation des collisions ou à la navigation.

## Fichiers locaux et registre ONU

Les options facultatives sont :

```text
--satellite-elements-file local/gp.csv
--satcat-file local/satcat.csv
--unoosa-file local/registre-onu.csv
```

Un fichier GP peut aussi être une liste JSON OMM ou une copie `.gz`.
Le SATCAT accepte son CSV officiel, une liste JSON, ou le conteneur local documenté.
Un fichier orbital ou SATCAT explicite désactive la mise à jour CelesTrak pour
cette commande, afin de respecter la copie fournie. Les identités NORAD doivent
correspondre; les COSPAR présents des deux côtés doivent concorder. Les fichiers
ne sont jamais modifiés. Fournir GP et SATCAT ensemble permet d'étendre le périmètre.

L'import UNOOSA est une transcription locale **sans format officiel d'export revendiqué**.
Colonnes requises :

```csv
cospar_id,state_of_registry,registration_document,source_url,retrieved_on
```

Colonnes facultatives : `object_name`, `registration_date`, `norad_id`.
Dates ISO 8601, `retrieved_on` au format AAAA-MM-JJ. Une URL officielle UNOOSA/ONU
et la référence documentaire sont requises; elles sont conservées sans lecture
distante ni authentification de l'extrait. Les contradictions NORAD/COSPAR et
les doublons sont refusés. Plusieurs documents distincts peuvent décrire un objet.
Une désignation partagée par plusieurs fiches SATCAT laisse la jointure indéterminée.

Les extraits administratifs ne remplacent ni les éléments orbitaux ni la fiche
SATCAT. Un registre absent, ou sans correspondance, signifie **statut inconnu**.
Aucune fiche réelle UNOOSA n'est livrée, l'index ayant refusé l'accès automatisé;
les exemples de tests sont synthétiques. Respecter les conditions des données
que l'on fournit; le logiciel ne publie pas ces extraits.

Seestar utilise `NORAD25544`, `SATCAT25544` ou `1998-067A`, éventuellement précédé
de COSPAR, comme identité explicite. Un numéro seul et un nom courant partagé
ne sont pas assimilés à une cible. Les acquisitions restent en lecture seule.

## Actualisations et politique CelesTrak

Ajouter `--update-catalogs if-stale --catalog-age satellites=6` pour un contrôle
au démarrage; enlever `--offline` afin d'autoriser les connexions. Les deux
sélections partagent une génération GP/SATCAT et leurs délais applicables les
plus courts. `--catalog-age debris=6`, `gp=6`, `celestrak=6` sont aussi reconnus;
`--catalog-age satcat=24` règle la fraîcheur administrative SATCAT.

Le fournisseur impose une utilisation limitée. Le programme applique **au moins
2 heures entre requêtes GP** et **24 heures pour SATCAT**, même avec `force`.
Une demande inférieure est relevée à ces minimums, affichés dans les notes.
Les CSV sont compressés, les téléchargements séquentiels, sans redirection.
SATCAT est réutilisé quand seul GP doit être renouvelé.

Tout statut HTTP différent de 200 arrête immédiatement le fournisseur. Un
blocage 4xx ou une redirection est conservé dans `celestrak-state.json` du cache;
examiner la cause avant de supprimer manuellement ce fichier pour réinitialiser.
Les autres pannes imposent au moins 15 minutes de pause. Ne pas supprimer cet
état pour relancer en boucle. La copie valide précédente reste disponible;
`--offline` et `never` ne créent ni état ni connexion. Le cache reste sur
l'ordinateur et bénéficie des protections Seestar avant toute écriture.

Voir [les réglages communs](CATALOG_UPDATES.md) et la
[politique CelesTrak](https://celestrak.org/usage-policy.php).

## Vérifications scientifiques

Les tests comparent les vecteurs TEME aux cas Vallado publiés et livrés avec
SGP4, vérifient la géométrie topocentrique, les identifiants étendus, les bornes,
les erreurs SGP4 et les filtres simultanés. Ils ne constituent pas une validation
observationnelle de toute la sélection. Les tests réseau simulent les réponses;
une protection globale interdit désormais toute connexion réelle dans pytest.

Références : [SGP4](https://pypi.org/project/sgp4/),
[exemple Astropy pour satellites](https://docs.astropy.org/en/stable/coordinates/satellites.html),
[formats SATCAT](https://celestrak.org/satcat/satcat-format.php),
[registre UNOOSA](https://www.unoosa.org/oosa/en/spaceobjectregister/resources/index.html).
