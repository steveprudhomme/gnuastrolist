# ECC-F — Cache local, concurrence et rétention

Le cache contient des copies reconstruites des catalogues et leur provenance.
Une **génération** est un dossier qui réunit une copie, ses métadonnées et les
réponses sources disponibles. Les fichiers livrés avec le logiciel restent intacts.

## Deux commandes en même temps

Les actualisations `if-stale` et `force` prennent le même verrou exclusif dans
le cache, nommé `.catalog.lock`. Le verrou couvre lecture des générations,
lecture et autorisation de l'état fournisseur, requêtes, reconstruction et
activation. L'appel général et l'appel spécialisé satellites partagent ce
verrou. Un appel imbriqué dans le même thread peut le reprendre sans se bloquer.
Deux caches distincts sont indépendants.

L'attente dure au maximum 120 secondes. Après ce délai, l'appel échoue sans
entrer dans la transaction. Aucun contournement du verrou n'est tenté. Le
système libère le verrou quand le processus ferme son fichier ou s'arrête,
y compris après une interruption brutale. Le fichier reste présent : il ne
faut **jamais le supprimer** pour débloquer une commande. Son existence ne
signifie pas qu'un processus le détient.

`never` et `offline` ne prennent ni ne créent de verrou et n'écrivent aucun état.
Ils peuvent toujours lire les copies locales validées. Ils n'attendent donc
pas une actualisation réseau en cours. Les générations publiées ne changent
plus de contenu; la publication continue d'utiliser un renommage atomique.

Les règles CelesTrak sont conservées : au moins deux heures entre demandes GP,
24 heures pour SATCAT, blocage après les erreurs qui l'exigent et pause après
les autres pannes. L'intention de requête est enregistrée **avant** la requête.
Un processus interrompu ne permet donc pas au suivant d'ignorer cet intervalle.
La rétention conserve `celestrak-state.json` octet pour octet.

Les modes, catalogues et durées sont validés avant toute création de dossier
ou de verrou. La lecture des générations et les décisions fournisseur restent
ensuite dans la transaction protégée.

## Examiner le cache avant de retirer des copies

Cette commande est distincte de la préparation d'une soirée. Elle ne contacte
aucun fournisseur. Le dossier est toujours obligatoire : il n'existe pas de
purge implicite du cache personnel.

1. Choisir un cache local que vous contrôlez, hors des archives Seestar.
2. Arrêter les calculs et rapports qui utilisent ses anciennes générations.
3. Examiner la simulation, qui ne crée ni dossier ni fichier de verrou :

   ```powershell
   python -m gnu_astrolist.cache_admin --cache-dir local/catalog-cache --keep 2
   ```

4. Lire les lignes `KEEP` (conserver) et `WOULD REMOVE` (retirer).
5. Si ce résultat convient, demander explicitement l'application :

   ```powershell
   python -m gnu_astrolist.cache_admin --cache-dir local/catalog-cache --keep 2 --apply
   ```

`--keep` doit être un entier supérieur ou égal à 1; sa valeur par défaut est 1.
Il compte les générations **réellement valides**, par famille. Satellites et
débris forment une seule famille GP/SATCAT. Une copie corrompue plus récente
ne remplace pas la dernière bonne copie dans ce compte. La date de récupération
validée détermine l'ordre, puis le nom départage les égalités.

Les validations contrôlent notamment SHA-256, schéma, date, effectif et contenu
avec les parseurs existants. Les contrôles de population et la jointure
NORAD/COSPAR restent applicables. Les réponses brutes présentes sont également
vérifiées. Seules les sources SATCAT sans nom de brut et identiques aux
métadonnées du paquet peuvent ne pas avoir de réponse brute locale. Une réponse
GP déclarée mais absente, ou une provenance documentaire différente, rend la
génération invalide pour la rétention.

Si une famille n'a aucune génération valide, l'opération entière est refusée.
Sinon, les anciennes copies excédentaires et les générations reconnues mais
invalides sont proposées au retrait. Le nombre demandé est un minimum de copies
valides à garder, pas une limite qui justifierait de perdre le dernier repli.

## Chemins refusés et application

La commande n'accepte que les dossiers de génération nommés par les écrivains
du cache : famille connue, horodatage et identifiant hexadécimal. Dans chaque
génération, seuls les artefacts attendus, métadonnées et réponses sources déclarées
avec noms dérivés de leurs requêtes sont reconnus. Les fichiers auxiliaires
connus des générateurs HYG et Messier sont admis.

Un fichier inconnu, sous-dossier inattendu, fichier spécial, lien symbolique,
jonction, point de réanalyse Windows ou fichier avec plusieurs liens physiques
fait refuser l'opération avant toute suppression. Les dossiers `.pending-*`
et les temporaires d'état interrompus sont laissés à une inspection humaine;
ils ne sont jamais effacés automatiquement. Une métadonnée illisible ne permet
pas d'autoriser la suppression de réponses sources non identifiables.

Le dossier doit déjà exister. La racine d'un volume et le dossier personnel
lui-même sont refusés. `--seestar-path DOSSIER` applique la protection Seestar
existante, y compris celle du volume distinct lorsqu'elle s'applique. Fournir
cette option lorsqu'une source Seestar fait partie du contexte. Cette commande
ne recherche jamais de disque USB et ne découvre pas automatiquement les archives.

`--apply` utilise le même verrou que les actualisations et calcule son plan
après acquisition; une simulation antérieure peut donc différer. Si le verrou
existe déjà, la commande protège sa racine puis attend sans inspecter les
générations ni les temporaires de l'écrivain. Après cette attente, tout temporaire
qui subsiste fait refuser l'application. Les parents
sont ouverts pendant l'application. Windows refuse leur renommage; POSIX utilise
des descripteurs de dossiers sans suivi de lien pour retirer les fichiers.
Les identités sont revérifiées avant chaque génération. Les fichiers sont
retirés un par un, puis le dossier vide; aucune suppression récursive générale
n'est utilisée. Un arrêt ou une erreur peut laisser une génération partiellement
retirée. La commande s'arrête alors; elle ne promet pas de retour arrière global.

Le modèle est celui d'un cache local privé avec écrivains coopérants. Il ne
remplace pas les permissions du système contre un autre utilisateur hostile
capable de modifier ces dossiers. Ne pas utiliser de partage réseau : les
garanties des verrous dépendent de son système de fichiers. Les lecteurs
`never/offline` ne réservent pas leurs générations après leur sélection; lancer
la rétention quand ces calculs sont terminés.

## Contrôles locaux

Les tests ECC-F créent uniquement des caches et réponses synthétiques. Ils
vérifient réentrance, exclusion entre processus et threads, délai d'attente,
arrêt brutal, règles CelesTrak sous concurrence, lecture puis activation
`if-stale`, rétention sous verrou, refus des chemins et conservation d'un vrai
repli. Le test POSIX `fork` est réservé aux systèmes correspondants; la création
d'un lien symbolique peut être indisponible pour un compte Windows. Le refus
des réanalyses Windows est aussi testé par simulation de métadonnées.

Ces essais ne publient rien et ne prouvent ni le comportement d'un fournisseur
réel ni une validation scientifique externe. Voir la
[décision ECC-F](architecture/decisions/0008-ecc-f-cache-transactions.md).

Contrôles locaux après les trois corrections de la revue indépendante du
17 novembre 2026 : 612 tests réussis et 5 ignorés sous Windows, aussi bien avec
Python 3.13.6 qu'avec Python 3.10.16. Deux exclusions ECC-F concernent `fork`
POSIX et la création de liens symboliques non autorisée pour ce compte Windows.
La couverture des deux nouveaux modules est de 90 % (rétention 91 %, verrou
87 %). Ruff et le typage ciblé de ces modules passent. Les branches POSIX ont
été relues, sans exécution Linux dans cette vérification.
