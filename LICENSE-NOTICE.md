# Licences et attributions

Le logiciel original est sous **GPL-3.0-or-later**; le texte intégral est dans
[LICENSE](LICENSE). Les personnes contributrices conservent leurs droits.
Le nom du projet ne constitue pas une déclaration d'affiliation officielle GNU.

Les catalogues ont leurs propres conditions :

| Données | Attribution et conditions |
| --- | --- |
| GP et SATCAT CelesTrak | CelesTrak / T. S. Kelso et producteurs des données; conditions d'usage du fournisseur, attribution conservée, aucune licence CC/GPL ajoutée; voir SPACE_OBJECT_SOURCE.md |
| CometEls MPC | IAU Minor Planet Center; copyright conservé, redistribution du fichier public avec source spécifiée selon la politique CBAT/MPC; voir COMET_SOURCE.md |
| Orbites SBDB et références Horizons | NASA/JPL Solar System Dynamics; données du domaine public selon la FAQ SSD, attribution et transformations documentées dans ASTEROID_SOURCE.md |
| GCVS | Auteurs GCVS et VizieR; voir CATALOG_SOURCE.md |
| Messier dérivé d'OpenNGC | Mattia Verga et contributeurs; CC BY-SA 4.0 |
| Caldwell dérivé d'OpenNGC | Mattia Verga et contributeurs; CC BY-SA 4.0 |
| NGC dérivé d'OpenNGC | Mattia Verga et contributeurs; CC BY-SA 4.0; voir NGC_SOURCE.md |
| Bayer/Flamsteed dérivés de HYG 4.1 | David Nash / Astronomy Nexus et contributeurs; CC BY-SA 4.0; voir STELLAR_SOURCE.md |
| Polices DejaVu Sans | Notices Bitstream/DejaVu/Arev conservées dans data/fonts/LICENSE_DEJAVU.txt; voir FONT_SOURCE.md |
| Compléments SIMBAD | CDS, Observatoire astronomique de Strasbourg; attribution conservée |

Les notices détaillées sont dans `src/gnu_astrolist/data/`, notamment
[CALDWELL_SOURCE.md](src/gnu_astrolist/data/CALDWELL_SOURCE.md).
Ces données ne sont pas relicenciées sous GPL par leur inclusion dans le paquet.
Toute nouvelle source ou dépendance doit être examinée avant redistribution.
Les dépendances Python gardent leurs licences et notices propres; le présent
document n'est ni un SBOM ni un audit juridique automatisé.

La dépendance SGP4 de Brandon Rhodes et contributeurs est sous MIT. Aucune
fiche réelle UNOOSA n'est distribuée : l'import local du registre reste soumis
aux droits des données fournies par l'utilisateur.


Les références de tests ECC-H conservent les textes MIT SGP4 et BSD-3-Clause
IERS dans `tests/data/`; [la notice scientifique](docs/SCIENCE_SATELLITE_REFERENCES.md)
précise l'origine, l'extraction et les conditions sans relicencier les données.
Les avis ajoutés aux anciens fichiers originaux suivent l'auteur vérifié dans
Git; aucun avis de tiers n'est supprimé ni aucune attestation DCO fabriquée.
