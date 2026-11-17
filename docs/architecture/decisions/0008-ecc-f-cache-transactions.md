# 0008 — ECC-F : sérialiser les transactions et séparer la rétention

- Date : 2026-11-17
- Statut : retenu pour l'implémentation locale ECC-F
- Plan : `a814a49`, ECC-F.1 à ECC-F.5

## Contexte

Le renommage atomique protège la publication d'une génération. Il ne protège
pas la décision prise avant le téléchargement : deux processus peuvent lire le
même état fournisseur et envoyer la même requête. Satellites et débris partagent
leur état CelesTrak; un verrou distinct par alias laisserait subsister ce risque.
Les générations historiques s'accumulent sans rétention automatique.

## Décision

Utiliser un fichier stable `.catalog.lock` par cache local. Une section
réentrante par thread enveloppe un verrou OS exclusif non bloquant, attendu
avec un délai borné : `msvcrt.locking` sous Windows et `fcntl.flock` sous POSIX.
Le descripteur est fermé dans tous les chemins de sortie. Un arrêt du processus
libère le verrou OS sans nettoyage manuel. Le fichier n'est jamais supprimé.
Après `fork`, les descripteurs hérités sont fermés dans l'enfant et la
réentrance locale est réinitialisée, sans déverrouiller le parent.

Les fonctions publiques valident leurs paramètres avant tout effet, puis
appellent les transactions internes protégées par le décorateur commun.
Les signatures publiques sont conservées et l'imbrication de `refresh_catalogs`
avec `refresh_satellite_catalog` reste réentrante. `never/offline` évitent toute
création et tout verrou. L'état
des tentatives CelesTrak reste écrit avant l'envoi. Les délais, pauses et
blocages existants restent l'autorité sur l'autorisation des demandes.

Fournir séparément `python -m gnu_astrolist.cache_admin`, avec cache explicite,
simulation par défaut et `--apply` volontaire. Sous le même verrou, recalculer
les candidats et garder au moins `keep >= 1` générations réellement validées
par famille; satellites et débris constituent une famille. Réutiliser le même
validateur de génération satellitaire pour lecture et rétention. Refuser toute
famille sans repli valide et tout chemin non reconnu, lié, spécial ou protégé.
N'inspecter les générations qu'après acquisition du verrou d'application; un
écrivain actif doit pouvoir terminer ses temporaires. Exiger les réponses brutes
déclarées, avec la seule exception des métadonnées SATCAT sans brut strictement
identiques à celles du paquet. Retirer uniquement les fichiers explicitement
inventoriés, sans purge récursive.
Conserver l'état fournisseur et le fichier de verrou.

## Conséquences et limites

Le verrou global privilégie la simplicité et la sécurité fournisseur au débit.
Une actualisation longue peut faire échouer un autre écrivain après 120 secondes
d'attente. Les caches distincts restent indépendants. Le verrou est coopératif,
prévu pour un dossier privé sur système de fichiers local; il ne constitue pas
une défense contre un acteur disposant des mêmes droits de modification.

La suppression n'est pas une transaction globale : une panne peut laisser une
génération partiellement retirée. La liste blanche et le refus des temporaires
inconnus privilégient l'inspection à une purge agressive. Les lectures hors
ligne ne réservent pas de génération pour la durée du calcul : l'utilisateur
exécute la rétention après ces travaux. Aucune rétention n'est lancée par la CLI
d'observation. Aucun changement d'installation ni service externe n'est requis.

## Vérification

Tests déterministes hors réseau avec processus distincts, fournisseur synthétique,
arrêt brutal, repli, délais CelesTrak, contenu de générations corrompu et chemins
protégés. Voir [CACHE.md](../../CACHE.md) pour l'usage et les limites. Les essais
Windows locaux ne constituent pas une exécution des branches POSIX sous Linux.
