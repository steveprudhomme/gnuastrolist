# ADR 0007 — Service d’application et rapport partagé (ECC-G)

- Statut : accepté dans le périmètre local du plan `a814a49`, sous revue du pilote.
- Date : 2026-11-17.
- Lots : ECC-G.1 à ECC-G.5.

## Contexte

La CLI chargeait les données, orchestrait les calculs et construisait deux fois
les paramètres du rapport. Le PDF importait six fonctions privées du texte.
Les mutations globales de configuration IERS survivaient à une commande et
pouvaient modifier les suivantes, y compris lorsqu’une commande échouait.
Les protections ECC-A/C et les monkeypatchs publics existants doivent rester
opérationnels. Les moteurs astronomiques sont hors périmètre.

## Décision

Extraire `ObservationApplication`, sa requête typée et ses collaborateurs
explicitement injectables dans `application.py`. Le service prépare un
`ReportData` sans parseur, terminal ni export. La CLI reste l’adaptateur pour
les arguments, l’actualisation et le contexte de catalogues, les erreurs de
commande et les destinations protégées. Elle injecte ses symboles courants
à chaque invocation pour préserver les monkeypatchs publics.

Adopter un DTO partagé dans `report_data.py`. Son adaptateur `to_kwargs()`
préserve les API historiques TXT/PDF et l’identité des objets métier. Ne pas
utiliser `dataclasses.asdict`, qui effectuerait des copies profondes inutiles.
Le service capture les résultats dans un tuple après limitation et annotation.
Les interfaces de rendu n’exigent pas la migration immédiate des appelants.

Déplacer les formats communs, sans changement de règles, dans le module public
`report_formatting.py`. Le PDF dépend de cette API et plus du rendu texte.
Conserver les alias privés historiques dans `output.py` pour compatibilité.

Encadrer les réglages IERS par `set_temp` et un verrou réentrant. Le contexte
couvre toute l’exécution après précontrôle de la CLI, et le service l’utilise
également pour ses appels directs. Une sortie normale, `ValueError`,
`RuntimeError` ou `SystemExit` déclenche la restauration. Le contexte existant
de ressources reste indépendant et conserve son mécanisme de restauration.

## Conséquences et alternatives

L’application possède une frontière testable sans CLI ni calcul astronomique
réel. L’injection comporte plusieurs fonctions, mais rend visibles les points
de collaboration; elle évite une résolution implicite dans les globals.
Un module utilitaire simplement appelé depuis l’ancien `_run` aurait laissé
l’essentiel de l’orchestration couplé au parseur et aux exports.

Remplacer directement les signatures des rendus par le DTO aurait cassé les
appelants. L’adaptateur permet une migration progressive. Un gel profond de
tous les modèles serait plus invasif et n’est pas nécessaire à ce lot.

La configuration Astropy reste globale. Le verrou protège seulement les appels
qui utilisent notre contexte; il ne garantit pas l’isolation d’un tiers modifiant
Astropy directement. Les caches internes de tables IERS ne sont pas réinitialisés.
Aucune promesse nouvelle de précision scientifique ou de concurrence entre
processus n’est faite. Aucun moteur, catalogue, service ou dépendance n’est ajouté.

## Preuves attendues avant intégration

Tests déterministes du DTO, des collaborateurs injectés, des succès et erreurs,
des contextes imbriqués et des commandes successives hors ligne/en ligne simulée.
Régression CLI/TXT/PDF, protections ECC-A/C, ressources après erreur et Ruff.
Voir [le guide d’application](../../APPLICATION.md) et les tests ECC-G dédiés.
