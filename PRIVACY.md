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

`--offline` désactive ces connexions dans l'application, y compris les
actualisations de catalogues. `--update-catalogs never` désactive seulement
ces actualisations : la météo peut encore contacter ses fournisseurs.
Avec `if-stale` ou `force`, les fournisseurs des catalogues sélectionnés
(CDS/VizieR/SIMBAD, OpenNGC/GitHub, HYG/GitHub, NASA/JPL, MPC, CelesTrak)
reçoivent des requêtes et l'adresse IP, sans inventaire Seestar. Le registre
UNOOSA et les observations CBAT sont des imports locaux, sans lecture en ligne.
Les scripts de reconstruction constituent des outils distincts et peuvent
télécharger leurs sources lorsqu'une URL ou `--fetch-simbad` est utilisé.

Le cache conserve les réponses publiques, empreintes, dates et état fournisseur
dans le dossier choisi par `--catalog-cache-dir`. Ne jamais choisir le disque
Seestar. La commande de rétention ne transmet aucune donnée et simule ses
actions par défaut. Le cache peut révéler les catalogues consultés et leurs dates.

Les rapports TXT/PDF contiennent notamment lieu et heures d'observation.
Conserver les sorties personnelles dans `local/`, ignoré par Git. Ne pas joindre
à une issue un rapport personnel ou des coordonnées de domicile sans les retirer.
Les coordonnées des exemples du README sont des exemples publics pour Laval.
Les anciens `rapport.txt` et `rapport.pdf` sont retirés du suivi courant et
ignorés, tout en restant sur le poste et dans l'historique Git. Cette opération
n'efface pas une publication passée. La portée du contrôle de l'historique et
les réglages GitHub observés sont dans [GOUVERNANCE_VERIFIEE.md](docs/GOUVERNANCE_VERIFIEE.md).
