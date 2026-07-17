# Provenance du catalogue embarqué

- Catalogue : General Catalogue of Variable Stars, GCVS 5.1
- Auteurs : N. N. Samus, E. V. Kazarovets, O. V. Durlevich, N. N. Kireeva et E. N. Pastukhova
- Référence : *Astronomy Reports*, 61, 80 (2017), bibcode `2017ARep...61...80S`
- Diffusion : VizieR `B/gcvs`, Centre de données astronomiques de Strasbourg
- Fichier source : `gcvs_cat.dat.gz`
- URL : <https://cdsarc.cds.unistra.fr/ftp/B/gcvs/gcvs_cat.dat.gz>
- Version décrite par VizieR : GCVS 5.1, octobre 2020
- Empreinte SHA-256 du fichier utilisé :
  `b8e16ea0a5b37b644922c328b4b9b40fa46ea057003db075b5f15fcd74400d31`
- Date de récupération : 2026-07-17

## Transformation

Le script `scripts/build_catalog.py` conserve les entrées galactiques qui :

1. possèdent des coordonnées équatoriales J2000 complètes;
2. possèdent une magnitude maximale numérique;
3. utilisent la bande principale `V` du GCVS;
4. ne sont pas marquées comme inexistantes, dupliquées ou remplacées.

Le fichier résultant contient 21 212 lignes. Les colonnes conservées sont le
nom, l'ascension droite, la déclinaison, le type de variabilité, les magnitudes
maximale et minimale disponibles, le symbole éventuel de limite et la bande.

La documentation du GCVS précise que le code `V` recouvre les magnitudes
visuelles, photovisuelles ou Johnson V. Une magnitude minimale peut être omise
du fichier dérivé lorsque le champ du GCVS représente une amplitude ou une
autre bande photométrique.

## Attribution et conditions

Ces données astronomiques sont attribuées aux auteurs du GCVS et à VizieR/CDS.
Elles ne sont pas placées sous GPL par GNU Astrolist. Toute redistribution ou
utilisation scientifique doit respecter les conditions de la source et citer
le catalogue ainsi que VizieR : <https://cdsarc.cds.unistra.fr/viz-bin/cat/B/gcvs>.

