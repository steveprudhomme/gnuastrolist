# Comètes MPC et informations CBAT/ICQ

Source orbitale : **IAU Minor Planet Center**, fichier public
[CometEls.txt](https://minorplanetcenter.net/iau/MPCORB/CometEls.txt), récupéré le
**2026-11-17**. SHA-256 brut :
`25d1886242a6d1761c07a49311195bf1fd1eef066be5d67d9257a815368213f8`.

Les données restent attribuées au MPC. La
[politique CBAT/MPC](https://tamkin3.eps.harvard.edu/iau/WWWPolicy.html) autorise
la redistribution des jeux de données librement accessibles avec indication
claire de leur source. Elle conserve leur copyright. Ces données ne sont donc
ni déclarées domaine public ni relicenciées GPL. Les circulaires CBET/IAUC et
les jeux sur abonnement ne bénéficient pas de cette autorisation générale.
Aucune circulaire ni page CBAT n'est distribuée avec ce logiciel.

## Copie embarquée et transformation

Les **973 lignes** du fichier brut sont conservées intégralement dans
`comets.txt.gz`, compression gzip déterministe sans date ni nom interne.
Le chargeur retient **958 entrées P/C/D/I** et écarte 15 entrées **A/**,
catégorie astéroïdale. Il ne prétend pas contenir toutes les comètes connues.
Les fragments et les objets perdus ou interstellaires gardent leurs désignations.
La présence d'une orbite ne garantit pas une activité ou une survie actuelle.

```powershell
python scripts/build_comet_catalog.py --source local/comet-source/CometEls.txt --output src/gnu_astrolist/data/comets.txt.gz
```

Pour une nouvelle source vérifiée, fournir son SHA-256 réel via
`--expected-sha256`. Le fichier et l'empreinte d'origine sont nécessaires pour
reproduire cette copie historique; le fichier MPC en ligne évolue.

Le [format officiel MPC](https://docs.minorplanetcenter.net/mpc-ops-docs/orbits/comet-orbit-format/)
est « Ephemerides and Orbital Elements », pas le format ECS. Colonnes en base 1 :

| Champs | Colonnes et unités |
| --- | --- |
| Périhélie | 15–18 année, 20–21 mois, 23–29 jour décimal TT |
| Distance au périhélie, excentricité | 31–39 AU; 42–49 sans unité |
| Argument, nœud, inclinaison | 52–59, 62–69, 72–79 degrés, écliptique J2000 |
| Époque des éléments | 82–89 AAAAMMJJ TT, parfois absente |
| H, k | 92–95 magnitude absolue totale; 97–100 pente cométaire |
| Désignation/nom, référence | 103–158; 160 et suivantes |

Le temps de périhélie TT est converti en TDB pour la propagation. L'époque
orbitale reste contrôlée en TT. Les valeurs absentes ne deviennent jamais zéro.
Une ligne incorrecte ou un doublon de désignation fait refuser le fichier.

Au 17 novembre 2026, pour la plage locale de l'exemple Laval, **952 orbites**
sont exploitables; cinq fragments n'ont pas d'époque et 1I a une époque trop
ancienne. Les six exclusions sont annoncées dans le rapport. Le choix des
orbites est recalculé pour chaque plage, sans utiliser la date du téléchargement
comme substitut à l'époque.

## CBAT : complément d'observations, pas seconde orbite fictive

Le CBAT annonce et documente les découvertes; son site renvoie aussi vers les
[magnitudes ICQ/CBAT](https://www.icq.eps.harvard.edu/CometMags.html).
Les tentatives de lecture de ces pages le 2026-11-17 ont rencontré des erreurs
de connexion TLS ou de passerelle. Aucune observation réelle CBAT n'est donc
embarquée ni présentée comme récupérée. Les exemples et tests CBAT sont synthétiques.

`--cbat-file` accepte des observations locales transcrites dans le CSV décrit
dans [le guide](../../../docs/COMETS.md), avec référence et URL de provenance.
Cela n'est ni un import automatique de page HTML ni un téléchargement CBET.
L'utilisateur doit disposer du droit d'utiliser ses extraits; le programme ne
publie ni ne redistribue automatiquement ce fichier. Une observation reste
séparée de la prévision et sa bande originale reste affichée.

Voir [le calcul et les références de validation](../../../docs/COMETS.md) et
[les mises à jour configurables](../../../docs/CATALOG_UPDATES.md).
