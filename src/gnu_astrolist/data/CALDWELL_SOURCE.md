# Catalogue Caldwell embarqué

Les 109 entrées C1 à C109 utilisent les coordonnées ICRS/J2000, types,
constellations, dimensions et magnitudes V disponibles dans
[OpenNGC](https://github.com/mattiaverga/OpenNGC), fichiers `NGC.csv` et
`addendum.csv`, récupérés le 16 novembre 2026. Mattia Verga et les contributeurs
OpenNGC : données dérivées sous **CC BY-SA 4.0**, référence
`doi:10.21938/y.1ejWUD_MQ6b_eDFoVbbw`. Les transformations consistent en une
sélection, conversion des coordonnées en degrés et normalisation CSV.

La correspondance des numéros est vérifiée avec la
[liste de l'Astronomical League](https://www.astroleague.org/caldwell-program-object-list/).
Cette liste sert à l'identification, sans reprendre ses descriptions ou magnitudes
de bande non précisée. Le générateur conserve explicitement les 109 correspondances.

Révision OpenNGC épinglée : `be3cd6c5498806a2fbb2f7e0452ef802dbb02be0`.

## Objets composés et données absentes

- C9 utilise l'entrée OpenNGC C009 (Sh 2-155).
- C14 utilise le centre du double amas C014, sans addition arbitraire des magnitudes.
- C41 utilise C041 (Hyades) et C99 utilise C099 (Sac à charbon).
- C33 (Dentelles orientales) utilise NGC6992 comme position représentative du
  complexe NGC6992/6995; C49 (Rosette) utilise NGC2237 pour le complexe NGC2237–2239.
  Le champ et les dimensions de ces entrées ne modélisent pas tout le complexe.

Les valeurs V absentes restent vides dans le CSV, puis `None` dans le modèle.
Le rendu indique « non disponible ». Sans filtre, les objets restent inclus,
après les magnitudes connues au tri; une limite de magnitude les exclut.
Ne pas substituer une magnitude B ni celle d'une étoile centrale.

## Complément SIMBAD

Une requête en lot des V manquantes a été effectuée le 16 novembre 2026 auprès
du miroir `https://simbad.harvard.edu/simbad/sim-tap/sync`, le serveur principal
étant inaccessible depuis l'environnement de travail. Le complément retenu est
**C27 / NGC6888 : V = 7,5**, qualité C, système V, référence
`2002yCat.2237....0D`. La valeur de NGC6885 de qualité E n'est pas retenue.
Il reste 31 entrées sans V exploitable dans ces sources et cette requête.
Seules les qualités SIMBAD A, B ou C et les valeurs finies sont acceptées.

Attribution : SIMBAD, CDS, Observatoire astronomique de Strasbourg.
Ce complément n'est pas placé sous GPL. La réponse brute est conservée dans
`caldwell_simbad_response.csv`; les flux et leurs références sont conservés sans
modification. Le catalogue final donne la provenance de chaque magnitude retenue.

## Reconstruction

```text
python scripts/build_caldwell_catalog.py --ngc-source NGC.csv --addendum-source addendum.csv --retrieved-on 2026-11-16 --simbad-response src/gnu_astrolist/data/caldwell_simbad_response.csv --output src/gnu_astrolist/data/caldwell.csv.gz
```

Les fichiers sources doivent correspondre à ces empreintes SHA-256 :

```text
NGC.csv       54abea0b57b0a103831bfc7a8e3a99a23acfbf4bb581fcf3d8af539cbb826c84
addendum.csv  c93f983dda6780b76b7b2e9271a856a892627710148a982ee98101a54c642fdd
```

Le gzip est déterministe (horodatage nul). Pour une nouvelle consultation,
ajouter `--fetch-simbad` et éventuellement `--simbad-endpoint URL`, puis examiner
la réponse, la qualité et les notices avant de remplacer les données publiées.
Le générateur accepte les fichiers locaux pour une reconstruction sans réseau.
