# Confidentialité

Avec `--seestar-path`, les noms et tailles des acquisitions sont examinés
localement, sans lire les images ou leurs en-têtes FITS et sans cache persistant.
Les rapports contiennent le chemin de la racine Seestar et les statuts par objet.
Les conserver dans `local/`, hors des archives et hors Git. Les tests utilisent
uniquement des archives synthétiques; aucun inventaire personnel n'est publié.

GNU Astrolist traite localement les catalogues et les calculs astronomiques.
Sans `--offline`, il contacte Open-Meteo et 7Timer! avec la latitude et la
longitude demandées. Astropy peut également actualiser ses tables IERS.
Les services reçoivent les informations habituelles d'une connexion réseau,
dont l'adresse IP. Aucun compte ni télémétrie applicative n'est ajouté.

`--offline` désactive ces connexions dans l'application. Les scripts de mise à
jour de catalogues sont des outils distincts : ils téléchargent explicitement
leurs sources lorsqu'une URL ou `--fetch-simbad` est utilisé.

Les rapports TXT/PDF contiennent notamment lieu et heures d'observation.
Conserver les sorties personnelles dans `local/`, ignoré par Git. Ne pas joindre
à une issue un rapport personnel ou des coordonnées de domicile sans les retirer.
Les coordonnées des exemples du README sont des exemples publics pour Laval.
Les anciens fichiers `rapport.txt` et `rapport.pdf` déjà suivis ne sont pas
supprimés ni présentés comme une revue de confidentialité de l'historique.
