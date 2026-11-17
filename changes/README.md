# Changements en attente d'une version

Un petit fichier TOML décrit chaque changement destiné à une livraison.
Utiliser un nom unique en minuscules, par exemple `correction-export.toml`.

```toml
type = "bug"
summary = "Corriger le refus d'un export dans une situation documentée."
breaking = false
```

Types : `bug` (correctif), `improvement` (amélioration compatible), `feature`
(nouvelle fonctionnalité compatible). `breaking = true` signale une rupture
de compatibilité et impose une version majeure. La politique SemVer approuvée
est dans [versioning.toml](../versioning.toml).

Le résumé tient sur un paragraphe de 500 caractères maximum, sans donnée
personnelle ni secret. Le champ `released_in` est réservé à l'outil de préparation;
ne pas le remplir pour contourner un contrôle. Les fragments traités restent
versionnés pour garder la trace des catégories et des versions.

Un ticket signalé ou fermé sans correction ne crée pas de version. Les fragments
décrivent les changements effectivement livrés. Deux fonctionnalités dans la
même livraison produisent une seule augmentation mineure.

Voir le [guide du versionnage](../docs/VERSIONNAGE.md) pour les commandes.
