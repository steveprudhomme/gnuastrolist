# Provenance du catalogue Messier embarqué

- Catalogue source : OpenNGC
- Auteur et mainteneur : Mattia Verga et contributeurs
- Dépôt : <https://github.com/mattiaverga/OpenNGC>
- Fichiers sources : `database_files/NGC.csv` et `database_files/addendum.csv`
- DOI : <https://doi.org/10.21938/y.1ejWUD_MQ6b_eDFoVbbw>
- Licence des données : Creative Commons Attribution-Partage dans les mêmes
  conditions 4.0 International (`CC BY-SA 4.0`)
- Date de récupération : 2026-08-03
- Empreinte SHA-256 de `NGC.csv` :
  `be150bdaa1997dacbcb39f303074403edec7a953b589b36d5f1c4522c0cc6fae`
- Empreinte SHA-256 de `addendum.csv` :
  `1d8f0914e643ada325a5a94d88d8fefad6a4937a2f77cc34f21483af22b11983`

## Transformation

Le script `scripts/build_messier_catalog.py` sélectionne les entrées portant un
numéro Messier, convertit les coordonnées sexagésimales ICRS/J2000 en degrés et
conserve le numéro Messier, la désignation OpenNGC, le type, la constellation,
les dimensions angulaires disponibles, le nom usuel éventuel et la magnitude
apparente en bande V. Le fichier résultant contient les numéros M1 à M110,
ordonnés numériquement.

Depuis la version 0.5.0, les dimensions et magnitudes V sont enrichies avec un
cache SIMBAD. Une valeur SIMBAD valide est prioritaire; OpenNGC demeure la
source principale des autres champs et le repli hors ligne pour les valeurs
absentes. La provenance est enregistrée séparément pour chaque taille et chaque
magnitude. Consultez `SIMBAD_SOURCE.md` pour la requête, le cache et les règles
de sélection.

Les codes de type (`G`, `GCl`, `OCl`, `PN`, `Neb`, etc.) sont ceux d'OpenNGC.
Le guide du projet OpenNGC en donne la signification complète.

## Cas particulier de M102

L'identification de M102 reste historiquement incertaine. OpenNGC marque son
entrée M102 comme un doublon de M101 et ne lui attribue aucune magnitude V. Pour
fournir la liste moderne de 110 numéros, GNU Astrolist suit la convention
courante qui identifie M102 à NGC 5866. Cette décision est explicite dans le
script de génération et dans les tests.

## Attribution et conditions

Le fichier dérivé `messier.csv.gz` demeure soumis à la licence `CC BY-SA 4.0`
d'OpenNGC et n'est pas relicencié sous la GPL du logiciel. Toute redistribution
doit conserver l'attribution à OpenNGC et respecter les conditions de partage à
l'identique de cette licence :
<https://creativecommons.org/licenses/by-sa/4.0/>.
