# 0004 — Comètes mobiles et générations de catalogues au démarrage

Statut : accepté localement, 2026-11-17.

Les comètes ont des orbites ouvertes ou très excentriques. Leur luminosité
totale ne doit pas être étiquetée V. Le MPC fournit un fichier orbital public;
les mesures CBAT/ICQ sont des observations datées, pas un second modèle orbital.

Le moteur partage sa géométrie avec les astéroïdes et conserve un solveur
cométaire universel pour ellipse, parabole et hyperbole. La validité exige
une époque connue proche de la plage; les exclusions sont annoncées. Les
observations CBAT autorisées sont importées dans un CSV local documenté et
restent séparées, sans téléchargement d'abonnement ni faux format officiel.

Les mises à jour sont explicites au démarrage, pour tous les catalogues évolutifs.
Le mode jamais est le défaut; `--offline` interdit toute connexion. Les sources
partagées sont réutilisées dans une commande, avec délais réglables par catalogue
ou fournisseur. Les générateurs doivent fonctionner dans une installation wheel,
d'où leur déplacement dans `data_builders/` avec conservation des scripts compatibles.

Une génération de cache contient données reconstruites, réponses sources et
métadonnées d'intégrité/provenance. Elle est validée avant publication atomique.
Les anciens caches restent disponibles, les ressources embarquées intactes.
Un échec réseau est explicite et ne détruit pas une copie valide. Les caches
mémoire sont isolés entre commandes pour éviter une réutilisation silencieuse
d'une autre génération. Les protections Seestar précèdent toute écriture.

Conséquences : pas d'actualisation lorsque le logiciel est fermé; historique
local à gérer manuellement; versions de schéma contrôlées et évolutions importantes
à examiner avant intégration. L'âge de récupération ne prouve ni l'âge des
mesures ni la précision d'une orbite. CBAT reste local faute d'interface validée.

Voir [les comètes](../../COMETS.md) et [les réglages](../../CATALOG_UPDATES.md).
