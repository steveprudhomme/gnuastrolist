# Satellites artificiels et débris : sources et conditions

Source numérique : **CelesTrak / T. S. Kelso**, éléments GP et SATCAT publics,
récupérés le **2026-11-17**. Les quatre réponses CSV ont été conservées localement.
Leur provenance et leurs empreintes figurent aussi dans `space_objects.json.gz`.

| Réponse CSV | Lignes | SHA-256 |
| --- | --- | --- |
| `GROUP=visual`, GP | 156 | `452b25c37a4c48efc174d5661ba11e422381bd9714087b72db2f734197de8b45` |
| `GROUP=visual`, SATCAT | 158 | `fabeafb5d3edbc44f7c96847054d6e1b0002cca3761d8bb27623af507823aed6` |
| `GROUP=cosmos-2251-debris`, GP | 581 | `51f0f256c4e045084c673723ff292ef9738c94f75837096c0beee5255913bb46` |
| `GROUP=cosmos-2251-debris`, SATCAT | 1 715 | `ae48ddcf56fd6404bdb71aa1d68426e8193f9316c4f904b158740ba182e05068` |

Adresses :

```text
https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=CSV
https://celestrak.org/satcat/records.php?GROUP=visual&FORMAT=CSV
https://celestrak.org/NORAD/elements/gp.php?GROUP=cosmos-2251-debris&FORMAT=CSV
https://celestrak.org/satcat/records.php?GROUP=cosmos-2251-debris&FORMAT=CSV
```

## Périmètre et transformation

Cette sélection partielle contient **737 jeux GP** et **1 873 fiches SATCAT**.
Les fiches SATCAT comptent 68 charges utiles PAY, 90 corps de fusées R/B et
1 715 débris DEB, y compris des entrées historiques sans éléments GP actuels.
Ce ne sont ni le SATCAT complet ni tous les objets immatriculés à l'ONU.
Le groupe `visual` est une sélection du fournisseur; aucune magnitude n'est
déduite de son nom. Les 737 époques vont du 29 octobre au 17 novembre 2026 UTC.

Les réponses CSV deviennent des dictionnaires JSON, sans correction des valeurs,
triés par NORAD. Seuls des doublons strictement identiques entre groupes peuvent
être réunis; toute contradiction est refusée. Les éléments GP, métadonnées
SATCAT et identités sont validés avant compression gzip déterministe.
La version interne du conteneur est 1; les types PAY/R/B/DEB viennent de SATCAT.

```powershell
python scripts/build_space_catalog.py --source-dir local/satellite-source --output src/gnu_astrolist/data/space_objects.json.gz
```

Le répertoire source contient les quatre CSV et un `manifest.json` avec, pour
chacun, `file`, `url`, `sha256`, `count`, `retrieved_on`. Le générateur vérifie les
empreintes. La réponse en ligne évolue : garder les sources historiques pour
reproduire cette copie. Ne pas remplacer sa date par celle d'une reconstruction.

## Conventions et droits

Les [champs GP](https://celestrak.org/NORAD/documentation/gp-data-formats.php)
utilisent les noms OMM : époque UTC, éléments moyens SGP4, repère TEME,
centre EARTH. Ces quatre conventions peuvent être omises par CelesTrak et
sont alors appliquées comme documenté; une valeur explicite incompatible
est refusée. Les [champs SATCAT](https://celestrak.org/satcat/satcat-format.php)
décrivent les identifiants internationaux, types, propriétaire codé et dates.
La surface radar RCS n'est jamais convertie en magnitude optique.

Les droits des producteurs et l'attribution CelesTrak sont conservés. Aucune
licence CC ou déclaration de domaine public n'est ajoutée à ces données.
Les pages consultées publient une politique d'usage, sans licence SPDX propre
au jeu numérique. Le logiciel original reste GPL-3.0-or-later; ces données
ne sont pas relicenciées par leur inclusion. Le contenu éditorial, les logos
et les pages HTML du fournisseur ne sont pas reproduits.

La [politique CelesTrak](https://celestrak.org/usage-policy.php), mise à jour
le 16 novembre 2026, demande des requêtes utiles, compressées et peu fréquentes.
Le logiciel utilise CSV/gzip, une génération partagée, des délais minimaux
(GP 2 h, SATCAT 24 h), sans redirection ni répétition après erreur.
Toute réponse non 200 arrête les requêtes du fournisseur. Une erreur client
ou redirection exige une inspection; une panne serveur impose au moins 15 min.
Les réglages et le repli sont décrits dans [le guide](../../../docs/SATELLITES.md).

## Registre UNOOSA

Le [registre des objets lancés dans l'espace](https://www.unoosa.org/oosa/en/spaceobjectregister/resources/index.html)
est une source administrative, pas une éphéméride. Son index de recherche a
répondu HTTP 403 pendant ce lot; aucun export exploitable n'a été validé.
Les [conditions UNOOSA](https://www.unoosa.org/oosa/en/aboutus/terms-of-use.html)
distinguent consultation personnelle et redistribution des contenus.
Aucune fiche réelle UNOOSA ni copie de page ou document ONU n'est donc distribuée.

L'import `--unoosa-file` accepte un CSV local transcrit selon le format du
[guide](../../../docs/SATELLITES.md), fourni par l'utilisateur selon les droits
dont il dispose. Ce format n'est pas présenté comme un export officiel.
Les tests de registre sont synthétiques, identifiés comme tels. L'absence de
ligne locale laisse le statut inconnu : elle ne prouve pas une non-immatriculation.

SGP4 2.25, dépendance de Brandon Rhodes et contributeurs, garde sa licence MIT.
Les comparaisons numériques utilisent les cas Vallado livrés avec cette
dépendance, sans les présenter comme des observations du ciel.
